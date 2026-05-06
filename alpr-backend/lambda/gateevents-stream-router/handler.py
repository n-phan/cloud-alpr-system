import json
import os
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key

#CONSTANTS
PERMIT_VALID = "VALID"
PERMIT_INVALID = "INVALID"
PERMIT_REVIEW = "PENDING REVIEW"

THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.7"))
DETECTION_AUTO_CITATION_CONFIDENCE = float(
    os.environ.get("DETECTION_AUTO_CITATION_CONFIDENCE", "0.7")
)
DETECTION_IDEMPOTENCY_BUCKET_MINUTES = int(
    os.environ.get("DETECTION_IDEMPOTENCY_BUCKET_MINUTES", "15")
)
GRACE_PERIOD_MINUTES = int(os.environ.get("GRACE_PERIOD_MINUTES", "15"))
MATCHING_WINDOW_MINUTES = int(os.environ.get("MATCHING_WINDOW_MINUTES", "240"))
ORPHAN_POLICY = os.environ.get("ORPHAN_POLICY", "review").strip().lower()  # cite|review
PERMIT_CHECKER_FUNCTION = os.environ.get("PERMIT_CHECKER_FUNCTION", "permit-checker")
VALIDATION_BACKLOG_FUNCTION = os.environ.get(
    "VALIDATION_BACKLOG_FUNCTION", "validation-backlog-handler"
)
CITATION_CREATE_FUNCTION = os.environ.get(
    "CITATION_CREATE_FUNCTION", "citation-create-handler"
)
GATE_EVENTS_TABLE = os.environ.get("GATE_EVENTS_TABLE", "GateEvents")
# Set to GSI name (PK plate_text, SK timestamp) to use Query; leave unset for paginated Scan.
GATE_EVENTS_PLATE_TEXT_INDEX = os.environ.get("GATE_EVENTS_PLATE_TEXT_INDEX", "").strip()

lambda_client = boto3.client("lambda")
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-west-2"))
gate_events_table = dynamodb.Table(GATE_EVENTS_TABLE)


class DownstreamLambdaError(RuntimeError):
    pass


def lambda_handler(event, context):
    processed = 0
    skipped_invalid_payload = 0
    high_confidence_events = 0
    low_confidence_events = 0
    routed_to_permit_checker = 0
    routed_to_validation_backlog = 0
    routed_to_citation_create = 0
    skipped_duplicate_citation = 0
    no_citation_grace_period = 0
    no_citation_valid_permit = 0
    waiting_for_counterpart = 0
    orphan_decisions = 0
    detection_events = 0
    detection_review_fallback = 0

    for record in event.get("Records", []):
        if record.get("eventName") != "INSERT":
            continue

        new_image = (record.get("dynamodb") or {}).get("NewImage") or {}
        item = _from_ddb_image(new_image)

        plate_raw = item.get("plate_text")
        plate_text = _normalize_plate(plate_raw)
        stored_vehicle_key = _coerce_ddb_vehicle_key(item.get("vehicle_id"))
        confidence = _to_float(item.get("confidence"))
        permit_status_in_event = item.get("permit_status")
        event_type_raw = item.get("event_type")
        image_url = item.get("image_url")
        event_ts = _to_int(item.get("timestamp"))
        event_kind = _event_kind(event_type_raw)
        event_direction = event_kind if event_kind in {"entry", "exit"} else None

        # Permit/citation/pairing use normalized plate; DynamoDB Keys still use writers' vehicle_id when set.
        ddb_vehicle_id = stored_vehicle_key if stored_vehicle_key else plate_text
        vehicle_id = plate_text

        if (
            plate_text is None
            or ddb_vehicle_id is None
            or confidence is None
            or event_ts is None
        ):
            print(f"Skipping record with missing/invalid fields: {item}")
            skipped_invalid_payload += 1
            continue

        processed += 1

        # Lane 1: Low-confidence review path
        if confidence <= THRESHOLD:
            low_confidence_events += 1
            _route_to_backlog(
                vehicle_id=vehicle_id,
                plate_text=plate_text,
                confidence=confidence,
                permit_status=permit_status_in_event,
                event_type=event_type_raw,
                image_url=image_url,
                notes="routed by two-lane flow: low-confidence review lane",
                decision_lane="low-confidence-review",
            )
            routed_to_validation_backlog += 1
            _record_decision(
                ddb_vehicle_id=ddb_vehicle_id,
                timestamp=event_ts,
                decision_reason="low-confidence-review",
                decision_lane="low-confidence-review",
                permit_status=PERMIT_REVIEW,
            )
            continue

        # Dedicated detection workflow: immediate permit/citation path.
        if event_kind == "detection":
            detection_events += 1
            if confidence < DETECTION_AUTO_CITATION_CONFIDENCE:
                detection_review_fallback += 1
                _route_to_backlog(
                    vehicle_id=vehicle_id,
                    plate_text=plate_text,
                    confidence=confidence,
                    permit_status=permit_status_in_event,
                    event_type=event_type_raw,
                    image_url=image_url,
                    notes="detection confidence below auto-citation threshold; routed to review",
                    decision_lane="low-confidence-detection",
                )
                routed_to_validation_backlog += 1
                _record_decision(
                    ddb_vehicle_id=ddb_vehicle_id,
                    timestamp=event_ts,
                    decision_reason="detection-review-fallback",
                    decision_lane="low-confidence-detection",
                    permit_status=PERMIT_REVIEW,
                )
                continue

            permit_check_response = _invoke(
                PERMIT_CHECKER_FUNCTION,
                {"queryStringParameters": {"vehicleId": vehicle_id}},
                expected_payload_statuses={200, 404},
            )
            routed_to_permit_checker += 1

            permit_decision = _permit_decision(permit_check_response)
            if permit_decision == "unknown":
                raise DownstreamLambdaError(
                    "Permit-checker returned indeterminate result for detection path"
                )
            if permit_decision == "valid":
                no_citation_valid_permit += 1
                _record_decision(
                    ddb_vehicle_id=ddb_vehicle_id,
                    timestamp=event_ts,
                    decision_reason="valid-permit",
                    decision_lane="high-confidence-detection",
                    permit_status=PERMIT_VALID,
                )
                continue

            occurrence_key = _occurrence_key_with_bucket(
                vehicle_id=vehicle_id,
                violation_type="invalid-permit-detection",
                anchor_ts=event_ts,
                bucket_minutes=DETECTION_IDEMPOTENCY_BUCKET_MINUTES,
            )
            create_result = _create_citation(
                vehicle_id=vehicle_id,
                plate_text=plate_text,
                reason="No valid permit (detection event)",
                occurrence_key=occurrence_key,
                issued_by="gateevents-stream-router",
                related_event_ts=event_ts,
                image_url=image_url,
            )
            if create_result.get("duplicate"):
                skipped_duplicate_citation += 1
            else:
                routed_to_citation_create += 1
            _record_decision(
                ddb_vehicle_id=ddb_vehicle_id,
                timestamp=event_ts,
                decision_reason="invalid-permit-citation",
                decision_lane="high-confidence-detection",
                occurrence_key=occurrence_key,
                permit_status=PERMIT_INVALID,
            )
            continue

        if not event_direction:
            detection_review_fallback += 1
            _route_to_backlog(
                vehicle_id=vehicle_id,
                plate_text=plate_text,
                confidence=confidence,
                permit_status=permit_status_in_event,
                event_type=event_type_raw,
                image_url=image_url,
                notes="unknown event direction/type; routed to review",
                decision_lane="high-confidence-automated",
            )
            routed_to_validation_backlog += 1
            _record_decision(
                ddb_vehicle_id=ddb_vehicle_id,
                timestamp=event_ts,
                decision_reason="unknown-event-type-review",
                decision_lane="high-confidence-automated",
                permit_status=PERMIT_REVIEW
            )
            continue

        # Lane 2: High-confidence automated enforcement
        high_confidence_events += 1
        counterpart = _find_counterpart(
            events=_vehicle_events_for_pairing(plate_text, plate_raw),
            current_ts=event_ts,
            current_direction=event_direction,
        )

        # If no pair exists, wait within matching window.
        if counterpart is None:
            age_sec = int(time.time()) - event_ts
            if age_sec < _minutes_to_seconds(MATCHING_WINDOW_MINUTES):
                waiting_for_counterpart += 1
                _record_decision(
                    ddb_vehicle_id=ddb_vehicle_id,
                    timestamp=event_ts,
                    decision_reason="waiting-for-counterpart",
                    decision_lane="high-confidence-automated",
                    permit_status=PERMIT_REVIEW,
                )
                continue

            orphan_decisions += 1
            if ORPHAN_POLICY == "review":
                _route_to_backlog(
                    vehicle_id=vehicle_id,
                    plate_text=plate_text,
                    confidence=confidence,
                    permit_status=permit_status_in_event,
                    event_type=event_type_raw,
                    image_url=image_url,
                    notes="orphan event routed for manual review",
                    decision_lane="high-confidence-automated",
                )
                routed_to_validation_backlog += 1
                _record_decision(
                    ddb_vehicle_id=ddb_vehicle_id,
                    timestamp=event_ts,
                    decision_reason="orphan-review",
                    decision_lane="high-confidence-automated",
                    permit_status=PERMIT_REVIEW,
                )
                continue

            occurrence_key = _occurrence_key(
                vehicle_id=vehicle_id,
                violation_type=f"orphan-{event_direction}",
                anchor_ts=event_ts,
            )
            create_result = _create_citation(
                vehicle_id=vehicle_id,
                plate_text=plate_text,
                reason=f"{event_direction}-only event (no counterpart in matching window)",
                occurrence_key=occurrence_key,
                issued_by="gateevents-stream-router",
                related_event_ts=event_ts,
                image_url=image_url,
            )
            if create_result.get("duplicate"):
                skipped_duplicate_citation += 1
            else:
                routed_to_citation_create += 1
            _record_decision(
                ddb_vehicle_id=ddb_vehicle_id,
                timestamp=event_ts,
                decision_reason="orphan-citation",
                decision_lane="high-confidence-automated",
                occurrence_key=occurrence_key,
                permit_status=PERMIT_INVALID,
            )
            continue

        duration_sec = abs(event_ts - counterpart["timestamp"])
        if duration_sec <= _minutes_to_seconds(GRACE_PERIOD_MINUTES):
            no_citation_grace_period += 1
            _record_decision(
                ddb_vehicle_id=ddb_vehicle_id,
                timestamp=event_ts,
                decision_reason="grace-period",
                decision_lane="high-confidence-automated",
                counterpart_timestamp=counterpart["timestamp"],
                duration_seconds=duration_sec,
                permit_status=PERMIT_VALID,
            )
            continue

        permit_check_response = _invoke(
            PERMIT_CHECKER_FUNCTION,
            {"queryStringParameters": {"vehicleId": vehicle_id}},
            expected_payload_statuses={200, 404},
        )
        routed_to_permit_checker += 1
        permit_decision = _permit_decision(permit_check_response)
        if permit_decision == "unknown":
            raise DownstreamLambdaError(
                "Permit-checker returned indeterminate result for paired-event path"
            )
        if permit_decision == "valid":
            no_citation_valid_permit += 1
            _record_decision(
                ddb_vehicle_id=ddb_vehicle_id,
                timestamp=event_ts,
                decision_reason="valid-permit",
                decision_lane="high-confidence-automated",
                counterpart_timestamp=counterpart["timestamp"],
                duration_seconds=abs(event_ts - counterpart["timestamp"]),
                permit_status=PERMIT_VALID,
            )
            continue

        occurrence_key = _occurrence_key(
            vehicle_id=vehicle_id,
            violation_type="invalid-permit",
            anchor_ts=min(event_ts, counterpart["timestamp"]),
        )
        create_result = _create_citation(
            vehicle_id=vehicle_id,
            plate_text=plate_text,
            reason="No valid permit",
            occurrence_key=occurrence_key,
            issued_by="gateevents-stream-router",
            related_event_ts=event_ts,
            image_url=image_url,
        )
        if create_result.get("duplicate"):
            skipped_duplicate_citation += 1
        else:
            routed_to_citation_create += 1

        _record_decision(
            ddb_vehicle_id=ddb_vehicle_id,
            timestamp=event_ts,
            decision_reason="invalid-permit-citation",
            decision_lane="high-confidence-automated",
            counterpart_timestamp=counterpart["timestamp"],
            duration_seconds=abs(event_ts - counterpart["timestamp"]),
            occurrence_key=occurrence_key,
            permit_status=PERMIT_INVALID,
        )

    return {
        "statusCode": 200,
        "processed": processed,
        "skippedInvalidPayload": skipped_invalid_payload,
        "highConfidenceLaneEvents": high_confidence_events,
        "lowConfidenceLaneEvents": low_confidence_events,
        "routedToPermitChecker": routed_to_permit_checker,
        "routedToValidationBacklog": routed_to_validation_backlog,
        "routedToCitationCreate": routed_to_citation_create,
        "skippedDuplicateCitation": skipped_duplicate_citation,
        "noCitationGracePeriod": no_citation_grace_period,
        "noCitationValidPermit": no_citation_valid_permit,
        "waitingForCounterpart": waiting_for_counterpart,
        "orphanDecisions": orphan_decisions,
        "detectionEvents": detection_events,
        "detectionReviewFallback": detection_review_fallback,
        "threshold": THRESHOLD,
        "detectionAutoCitationConfidence": DETECTION_AUTO_CITATION_CONFIDENCE,
        "detectionIdempotencyBucketMinutes": DETECTION_IDEMPOTENCY_BUCKET_MINUTES,
        "gracePeriodMinutes": GRACE_PERIOD_MINUTES,
        "matchingWindowMinutes": MATCHING_WINDOW_MINUTES,
        "orphanPolicy": ORPHAN_POLICY,
    }


def _route_to_backlog(
    vehicle_id, plate_text, confidence, permit_status, event_type, image_url, notes, decision_lane
):
    body = {
        "vehicleId": vehicle_id,
        "plateText": plate_text,
        "confidence": confidence,
        "decisionLane": decision_lane,
        "notes": notes,
    }
    if permit_status is not None:
        body["permitStatus"] = permit_status
    if event_type is not None:
        body["eventType"] = event_type
    if image_url is not None:
        body["imageUrl"] = image_url
    _invoke(
        VALIDATION_BACKLOG_FUNCTION,
        {"body": json.dumps(body)},
        require_payload_2xx=True,
    )


def _create_citation(vehicle_id, plate_text, reason, occurrence_key, issued_by, related_event_ts, image_url=None):
    payload = {
        "vehicleId": vehicle_id,
        "plateText": plate_text,
        "reason": reason,
        "status": "issued",
        "issuedBy": issued_by,
        "occurrenceKey": occurrence_key,
        "notes": f"relatedEventTs={related_event_ts}",
    }
    if image_url is not None:
        payload["imageUrl"] = image_url
    response = _invoke(
        CITATION_CREATE_FUNCTION,
        {
            "httpMethod": "POST",
            "body": json.dumps(payload),
        },
        require_payload_2xx=True,
    )
    body = response.get("body")
    try:
        body_json = json.loads(body) if isinstance(body, str) else (body or {})
    except json.JSONDecodeError:
        body_json = {}
    return {"duplicate": bool(body_json.get("duplicate"))}


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
            for item in _query_gate_events_by_plate_text(plate, GATE_EVENTS_PLATE_TEXT_INDEX):
                dedupe = (item.get("timestamp"), item.get("vehicle_id"))
                if dedupe in seen:
                    continue
                seen.add(dedupe)
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
    filtered = []
    for item in items:
        if _to_int(item.get("timestamp")) is None:
            continue
        kind = _event_kind(item.get("event_type"))
        if kind not in {"entry", "exit"}:
            continue
        filtered.append(item)
    return filtered


def _query_gate_events_by_plate_text(plate_text, index_name):
    """Paginated Query on GSI: partition plate_text, sort timestamp."""
    kwargs = {
        "IndexName": index_name,
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
    candidates = []
    for item in events:
        ts = _to_int(item.get("timestamp"))
        if ts is None:
            continue
        if _event_kind(item.get("event_type")) != opposite:
            continue
        if abs(current_ts - ts) <= window_sec:
            candidates.append({"timestamp": ts})
    if not candidates:
        return None
    return sorted(candidates, key=lambda c: abs(current_ts - c["timestamp"]))[0]


def _record_decision(
    ddb_vehicle_id,
    timestamp,
    decision_reason,
    decision_lane,
    counterpart_timestamp=None,
    duration_seconds=None,
    occurrence_key=None,
    permit_status=None,
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

    # Unified permit status model
    if permit_status is not None:
        updates.append("permit_status = :ps")
        values[":ps"] = str(permit_status).upper()

    response = gate_events_table.update_item(
        Key={"timestamp": int(timestamp), "vehicle_id": ddb_vehicle_id},
        UpdateExpression="SET " + ", ".join(updates),
        ExpressionAttributeValues=values,
    )

    print(response)



def _occurrence_key(vehicle_id, violation_type, anchor_ts):
    day_bucket = int(anchor_ts) // (24 * 60 * 60)
    return f"{vehicle_id}#{violation_type}#{day_bucket}"


def _occurrence_key_with_bucket(vehicle_id, violation_type, anchor_ts, bucket_minutes):
    bucket_sec = int(bucket_minutes) * 60
    bucket = int(anchor_ts) // bucket_sec
    return f"{vehicle_id}#{violation_type}#{bucket}"


def _minutes_to_seconds(minutes):
    return int(minutes) * 60


def _event_kind(event_type):
    if not event_type:
        return None
    value = str(event_type).strip().lower()
    if value.startswith("detection"):
        return "detection"
    if value.startswith("entry"):
        return "entry"
    if value.startswith("exit"):
        return "exit"
    return None


def _invoke(
    function_name,
    payload,
    require_payload_2xx=False,
    expected_payload_statuses=None,
):
    resp = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    status_code = resp.get("StatusCode", 0)
    if status_code < 200 or status_code >= 300:
        raise DownstreamLambdaError(
            f"Invoke transport failed for {function_name}: status={status_code}"
        )
    payload_stream = resp.get("Payload")
    if payload_stream is None:
        return {}
    raw = payload_stream.read()
    if not raw:
        return {}
    try:
        payload_data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise DownstreamLambdaError(
            f"Invoke payload was not valid JSON for {function_name}"
        ) from e

    function_error = resp.get("FunctionError")
    if function_error:
        raise DownstreamLambdaError(
            f"Invoked function errored for {function_name}: "
            f"{function_error}; payload={payload_data}"
        )

    payload_status = None
    if isinstance(payload_data, dict) and "statusCode" in payload_data:
        try:
            payload_status = int(payload_data["statusCode"])
        except (TypeError, ValueError):
            raise DownstreamLambdaError(
                f"Invalid payload statusCode for {function_name}: "
                f"{payload_data.get('statusCode')}"
            )

    if expected_payload_statuses is not None and payload_status is not None:
        if payload_status not in expected_payload_statuses:
            raise DownstreamLambdaError(
                f"Unexpected payload status for {function_name}: {payload_status}"
            )
    elif require_payload_2xx and payload_status is not None:
        if payload_status < 200 or payload_status >= 300:
            raise DownstreamLambdaError(
                f"Non-2xx payload status for {function_name}: {payload_status}"
            )

    return payload_data


def _permit_decision(lambda_response):
    """Classify permit-checker result as valid, invalid, or unknown."""
    status_code = lambda_response.get("statusCode")
    if status_code == 404:
        return "invalid"
    if status_code != 200:
        return "unknown"

    body = lambda_response.get("body")
    if not body:
        return "unknown"
    try:
        body_json = json.loads(body) if isinstance(body, str) else body
    except json.JSONDecodeError:
        return "unknown"
    permit_status = str(body_json.get("permitStatus", "")).upper()
    if permit_status in {"VALID", "ACTIVE"}:
        return "valid"
    if permit_status:
        return "invalid"
    return "unknown"

def _normalize_plate(value):
    """Match permit-admin style so permit-checker lookups align with Permits keys."""
    if value is None:
        return None
    s = str(value).strip().upper()
    return s if s else None


def _coerce_ddb_vehicle_key(value):
    """vehicle_id exactly as writers store it (DynamoDB table key component)."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return str(int(value))
        return format(value.normalize(), "f").rstrip("0").rstrip(".") or None
    s = str(value).strip()
    return s if s else None


def _from_ddb_image(image):
    out = {}
    for key, wrapped in image.items():
        if "S" in wrapped:
            out[key] = wrapped["S"]
        elif "N" in wrapped:
            out[key] = Decimal(wrapped["N"])
        elif "BOOL" in wrapped:
            out[key] = wrapped["BOOL"]
    return out


def _to_float(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _to_int(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return int(value)
    return int(value)
