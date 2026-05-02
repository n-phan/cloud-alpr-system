import json
import os
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key

GATE_EVENTS_TABLE = os.environ.get("GATE_EVENTS_TABLE", "GateEvents")
GATE_EVENTS_PLATE_TEXT_INDEX = os.environ.get("GATE_EVENTS_PLATE_TEXT_INDEX", "").strip()
MATCHING_WINDOW_MINUTES = int(os.environ.get("MATCHING_WINDOW_MINUTES", "240"))
GRACE_PERIOD_MINUTES = int(os.environ.get("GRACE_PERIOD_MINUTES", "15"))
ORPHAN_POLICY = os.environ.get("ORPHAN_POLICY", "review").strip().lower()
PERMIT_CHECKER_FUNCTION = os.environ.get("PERMIT_CHECKER_FUNCTION", "permit-checker")
VALIDATION_BACKLOG_FUNCTION = os.environ.get("VALIDATION_BACKLOG_FUNCTION", "validation-backlog-handler")
CITATION_CREATE_FUNCTION = os.environ.get("CITATION_CREATE_FUNCTION", "citation-create-handler")

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-west-2"))
gate_events_table = dynamodb.Table(GATE_EVENTS_TABLE)
lambda_client = boto3.client("lambda")


def lambda_handler(event, context):
    cutoff = int(time.time()) - _minutes_to_seconds(MATCHING_WINDOW_MINUTES)

    scan_kwargs = {
        "FilterExpression": (
            Attr("decision_reason").eq("waiting-for-counterpart")
            & Attr("timestamp").lt(cutoff)
        )
    }
    candidates = []
    while True:
        response = gate_events_table.scan(**scan_kwargs)
        candidates.extend(response.get("Items", []))
        lek = response.get("LastEvaluatedKey")
        if not lek:
            break
        scan_kwargs["ExclusiveStartKey"] = lek

    print(f"orphan-scan: found {len(candidates)} expired waiting-for-counterpart items")

    resolved = 0
    citations_created = 0
    routed_to_backlog = 0
    skipped_duplicate = 0

    for item in candidates:
        plate_raw = item.get("plate_text")
        plate_text = _normalize_plate(plate_raw)
        ddb_vehicle_id = _coerce_str(item.get("vehicle_id")) or plate_text
        event_ts = _to_int(item.get("timestamp"))
        event_direction = _event_kind(item.get("event_type"))
        confidence = _to_float(item.get("confidence"))
        permit_status = item.get("permit_status")
        event_type_raw = item.get("event_type")
        image_url = item.get("image_url")

        if plate_text is None or event_ts is None or event_direction not in {"entry", "exit"}:
            continue

        resolved += 1

        counterpart = _find_counterpart(
            events=_vehicle_events_for_pairing(plate_text, plate_raw),
            current_ts=event_ts,
            current_direction=event_direction,
        )

        if counterpart is None:
            if ORPHAN_POLICY == "review":
                _route_to_backlog(
                    vehicle_id=plate_text,
                    plate_text=plate_text,
                    confidence=confidence,
                    permit_status=permit_status,
                    event_type=event_type_raw,
                    image_url=image_url,
                    notes=f"orphan: no counterpart after {MATCHING_WINDOW_MINUTES}m window",
                )
                routed_to_backlog += 1
                _record_decision(
                    ddb_vehicle_id=ddb_vehicle_id,
                    timestamp=event_ts,
                    decision_reason="orphan-review",
                    decision_lane="high-confidence-automated",
                )
            else:
                occurrence_key = _occurrence_key(
                    vehicle_id=plate_text,
                    violation_type=f"orphan-{event_direction}",
                    anchor_ts=event_ts,
                )
                result = _create_citation(
                    vehicle_id=plate_text,
                    plate_text=plate_text,
                    reason=f"{event_direction}-only event (no counterpart within {MATCHING_WINDOW_MINUTES}m)",
                    occurrence_key=occurrence_key,
                    issued_by="orphan-scan-handler",
                    related_event_ts=event_ts,
                )
                if result.get("duplicate"):
                    skipped_duplicate += 1
                else:
                    citations_created += 1
                _record_decision(
                    ddb_vehicle_id=ddb_vehicle_id,
                    timestamp=event_ts,
                    decision_reason="orphan-citation",
                    decision_lane="high-confidence-automated",
                    occurrence_key=occurrence_key,
                )
            continue

        duration_sec = abs(event_ts - counterpart["timestamp"])

        if duration_sec <= _minutes_to_seconds(GRACE_PERIOD_MINUTES):
            _record_decision(
                ddb_vehicle_id=ddb_vehicle_id,
                timestamp=event_ts,
                decision_reason="grace-period",
                decision_lane="high-confidence-automated",
                counterpart_timestamp=counterpart["timestamp"],
                duration_seconds=duration_sec,
            )
            continue

        permit_response = _invoke(
            PERMIT_CHECKER_FUNCTION,
            {"queryStringParameters": {"vehicleId": plate_text}},
        )

        if _has_valid_permit(permit_response):
            _record_decision(
                ddb_vehicle_id=ddb_vehicle_id,
                timestamp=event_ts,
                decision_reason="valid-permit",
                decision_lane="high-confidence-automated",
                counterpart_timestamp=counterpart["timestamp"],
                duration_seconds=duration_sec,
            )
            continue

        occurrence_key = _occurrence_key(
            vehicle_id=plate_text,
            violation_type="invalid-permit",
            anchor_ts=min(event_ts, counterpart["timestamp"]),
        )
        result = _create_citation(
            vehicle_id=plate_text,
            plate_text=plate_text,
            reason="No valid permit",
            occurrence_key=occurrence_key,
            issued_by="orphan-scan-handler",
            related_event_ts=event_ts,
        )
        if result.get("duplicate"):
            skipped_duplicate += 1
        else:
            citations_created += 1
        _record_decision(
            ddb_vehicle_id=ddb_vehicle_id,
            timestamp=event_ts,
            decision_reason="invalid-permit-citation",
            decision_lane="high-confidence-automated",
            counterpart_timestamp=counterpart["timestamp"],
            duration_seconds=duration_sec,
            occurrence_key=occurrence_key,
        )

    return {
        "statusCode": 200,
        "scanned": len(candidates),
        "resolved": resolved,
        "citationsCreated": citations_created,
        "routedToBacklog": routed_to_backlog,
        "skippedDuplicate": skipped_duplicate,
        "matchingWindowMinutes": MATCHING_WINDOW_MINUTES,
        "orphanPolicy": ORPHAN_POLICY,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _vehicle_events_for_pairing(normalized_plate, raw_plate):
    if GATE_EVENTS_PLATE_TEXT_INDEX:
        plates = [normalized_plate]
        if raw_plate is not None:
            trimmed = str(raw_plate).strip()
            if trimmed and trimmed.upper() != normalized_plate:
                plates.append(trimmed)
        seen = set()
        items = []
        for plate in plates:
            for item in _query_by_plate(plate):
                key = (_to_int(item.get("timestamp")), item.get("vehicle_id"))
                if key in seen:
                    continue
                seen.add(key)
                items.append(item)
    else:
        expr = Attr("plate_text").eq(normalized_plate)
        if raw_plate is not None:
            trimmed = str(raw_plate).strip()
            if trimmed and trimmed.upper() != normalized_plate:
                expr = expr | Attr("plate_text").eq(trimmed)
        scan_kwargs = {"FilterExpression": expr}
        items = []
        while True:
            response = gate_events_table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))
            lek = response.get("LastEvaluatedKey")
            if not lek:
                break
            scan_kwargs["ExclusiveStartKey"] = lek

    return [
        item for item in items
        if _to_int(item.get("timestamp")) is not None
        and _event_kind(item.get("event_type")) in {"entry", "exit"}
    ]


def _query_by_plate(plate_text):
    kwargs = {
        "IndexName": GATE_EVENTS_PLATE_TEXT_INDEX,
        "KeyConditionExpression": Key("plate_text").eq(plate_text),
    }
    out = []
    while True:
        response = gate_events_table.query(**kwargs)
        out.extend(response.get("Items", []))
        lek = response.get("LastEvaluatedKey")
        if not lek:
            break
        kwargs["ExclusiveStartKey"] = lek
    return out


def _find_counterpart(events, current_ts, current_direction):
    opposite = "exit" if current_direction == "entry" else "entry"
    window_sec = _minutes_to_seconds(MATCHING_WINDOW_MINUTES)
    candidates = [
        {"timestamp": _to_int(item["timestamp"])}
        for item in events
        if _event_kind(item.get("event_type")) == opposite
        and abs(current_ts - _to_int(item["timestamp"])) <= window_sec
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda c: abs(current_ts - c["timestamp"]))[0]


def _route_to_backlog(vehicle_id, plate_text, confidence, permit_status, event_type, image_url, notes):
    body = {
        "vehicleId": vehicle_id,
        "plateText": plate_text,
        "confidence": confidence,
        "decisionLane": "high-confidence-automated",
        "notes": notes,
    }
    if permit_status is not None:
        body["permitStatus"] = permit_status
    if event_type is not None:
        body["eventType"] = event_type
    if image_url is not None:
        body["imageUrl"] = image_url
    _invoke(VALIDATION_BACKLOG_FUNCTION, {"body": json.dumps(body)})


def _create_citation(vehicle_id, plate_text, reason, occurrence_key, issued_by, related_event_ts):
    response = _invoke(
        CITATION_CREATE_FUNCTION,
        {
            "httpMethod": "POST",
            "body": json.dumps({
                "vehicleId": vehicle_id,
                "plateText": plate_text,
                "reason": reason,
                "status": "issued",
                "issuedBy": issued_by,
                "occurrenceKey": occurrence_key,
                "notes": f"relatedEventTs={related_event_ts}",
            }),
        },
    )
    body = response.get("body")
    try:
        body_json = json.loads(body) if isinstance(body, str) else (body or {})
    except json.JSONDecodeError:
        body_json = {}
    return {"duplicate": bool(body_json.get("duplicate"))}


def _record_decision(
    ddb_vehicle_id,
    timestamp,
    decision_reason,
    decision_lane,
    counterpart_timestamp=None,
    duration_seconds=None,
    occurrence_key=None,
):
    updates = ["decision_reason = :dr", "decision_lane = :dl", "decision_at = :da"]
    values = {
        ":dr": decision_reason,
        ":dl": decision_lane,
        ":da": int(time.time()),
    }
    if counterpart_timestamp is not None:
        updates.append("counterpart_timestamp = :ct")
        values[":ct"] = int(counterpart_timestamp)
    if duration_seconds is not None:
        updates.append("duration_seconds = :du")
        values[":du"] = int(duration_seconds)
    if occurrence_key is not None:
        updates.append("occurrence_key = :ok")
        values[":ok"] = occurrence_key

    gate_events_table.update_item(
        Key={"timestamp": int(timestamp), "vehicle_id": ddb_vehicle_id},
        UpdateExpression="SET " + ", ".join(updates),
        ExpressionAttributeValues=values,
    )


def _invoke(function_name, payload):
    resp = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    status_code = resp.get("StatusCode", 0)
    if status_code < 200 or status_code >= 300:
        raise RuntimeError(f"Invoke failed for {function_name}: {status_code}")
    raw = resp.get("Payload")
    if raw is None:
        return {}
    data = raw.read()
    return json.loads(data.decode("utf-8")) if data else {}


def _has_valid_permit(lambda_response):
    if lambda_response.get("statusCode") != 200:
        return False
    body = lambda_response.get("body")
    if not body:
        return False
    try:
        body_json = json.loads(body) if isinstance(body, str) else body
    except json.JSONDecodeError:
        return False
    return str(body_json.get("permitStatus", "")).upper() in {"VALID", "ACTIVE"}


def _occurrence_key(vehicle_id, violation_type, anchor_ts):
    day_bucket = int(anchor_ts) // (24 * 60 * 60)
    return f"{vehicle_id}#{violation_type}#{day_bucket}"


def _minutes_to_seconds(minutes):
    return int(minutes) * 60


def _event_kind(event_type):
    if not event_type:
        return None
    value = str(event_type).strip().lower()
    if value.startswith("entry"):
        return "entry"
    if value.startswith("exit"):
        return "exit"
    return None


def _normalize_plate(value):
    if value is None:
        return None
    s = str(value).strip().upper()
    return s if s else None


def _coerce_str(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(int(value)) if value % 1 == 0 else str(value)
    s = str(value).strip()
    return s if s else None


def _to_int(value):
    if value is None:
        return None
    return int(Decimal(str(value))) if isinstance(value, Decimal) else int(value)


def _to_float(value):
    if value is None:
        return None
    return float(value)
