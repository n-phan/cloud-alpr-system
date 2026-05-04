import base64
import json
import os
import time
import uuid
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "us-west-2")
TABLE_NAME = os.environ.get("CITATIONS_TABLE", "Citations")
LIST_DEFAULT_LIMIT = int(os.environ.get("LIST_DEFAULT_LIMIT", "50"))
LIST_MAX_LIMIT = int(os.environ.get("LIST_MAX_LIMIT", "200"))

VALID_STATUSES = {"issued", "paid", "disputed", "voided"}

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    method = _http_method(event)

    if method == "OPTIONS":
        return {"statusCode": 204, "headers": _cors_headers(), "body": ""}

    try:
        if method == "GET":
            return _list_citations(event)
        if method == "POST":
            return _create_citation_manual(event)
        if method == "PUT":
            return _update_citation(event)
        return error_response(405, f"Method not allowed: {method}")
    except ValueError as e:
        return error_response(400, str(e))
    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(500, "Internal server error")


def _http_method(event):
    if event.get("httpMethod"):
        return event["httpMethod"].upper()
    rc = event.get("requestContext") or {}
    if rc.get("http", {}).get("method"):
        return rc["http"]["method"].upper()
    return "GET"


def _list_citations(event):
    params = event.get("queryStringParameters") or {}
    raw_limit = int(params.get("limit", LIST_DEFAULT_LIMIT))
    limit = max(1, min(raw_limit, LIST_MAX_LIMIT))
    status_filter = params.get("status")

    scan_kwargs = {"Limit": limit}
    if status_filter:
        scan_kwargs["FilterExpression"] = Attr("status").eq(status_filter)

    page_token = params.get("pageToken")
    if page_token:
        try:
            scan_kwargs["ExclusiveStartKey"] = json.loads(
                base64.urlsafe_b64decode(page_token.encode("ascii")).decode("utf-8")
            )
        except (ValueError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid pageToken: {e}") from e

    response = table.scan(**scan_kwargs)
    items = [_json_safe(item) for item in response.get("Items", [])]

    payload = {"items": items, "count": len(items)}
    lek = response.get("LastEvaluatedKey")
    if lek:
        payload["nextPageToken"] = base64.urlsafe_b64encode(
            json.dumps(lek, default=_json_serialize).encode("utf-8")
        ).decode("ascii")

    return {
        "statusCode": 200,
        "body": json.dumps(payload, default=_json_serialize),
        "headers": _cors_headers(),
    }


def _create_citation_manual(event):
    if isinstance(event.get("body"), str):
        body = json.loads(event["body"])
    else:
        body = event.get("body") or {}

    for field in ("vehicleId", "plateText", "reason"):
        if not body.get(field):
            return error_response(400, f"Missing required field: {field}")

    related_backlog_id = body.get("relatedBacklogId")
    if related_backlog_id:
        # Deterministic ID keyed on backlog item → conditional put enforces one citation per backlog item
        citation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"backlog:{related_backlog_id}"))
    else:
        citation_id = str(uuid.uuid4())

    issued_at = int(time.time() * 1000)

    item = {
        "citation_id": citation_id,
        "vehicle_id": body["vehicleId"],
        "plate_text": body["plateText"],
        "reason": body["reason"],
        "issued_at": issued_at,
        "status": "issued",
    }

    raw_amount = body.get("amount", os.environ.get("DEFAULT_CITATION_AMOUNT", "100"))
    try:
        item["amount"] = Decimal(str(raw_amount))
    except Exception:
        item["amount"] = Decimal("100")

    if body.get("notes"):
        item["notes"] = body["notes"]
    if body.get("issuedBy"):
        item["issued_by"] = body["issuedBy"]
    if body.get("imageUrl"):
        item["image_url"] = body["imageUrl"]
    if related_backlog_id:
        item["related_backlog_id"] = related_backlog_id

    put_kwargs = {"Item": item}
    if related_backlog_id:
        put_kwargs["ConditionExpression"] = "attribute_not_exists(citation_id)"

    try:
        table.put_item(**put_kwargs)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Citation already exists for this backlog item", "duplicate": True, "citationId": citation_id}),
                "headers": _cors_headers(),
            }
        raise

    return {
        "statusCode": 201,
        "body": json.dumps(
            {"message": "Citation created", "citationId": citation_id, "issuedAt": issued_at},
            default=_json_serialize,
        ),
        "headers": _cors_headers(),
    }


def _update_citation(event):
    if isinstance(event.get("body"), str):
        body = json.loads(event["body"])
    else:
        body = event.get("body") or {}

    citation_id = (body.get("citationId") or "").strip()
    if not citation_id:
        return error_response(400, "Missing required field: citationId")

    names = {}
    values = {}
    sets = []

    if "status" in body:
        status = body["status"].lower()
        if status not in VALID_STATUSES:
            return error_response(400, f"status must be one of: {', '.join(sorted(VALID_STATUSES))}")
        sets.append("#st = :st")
        names["#st"] = "status"
        values[":st"] = status

    if "notes" in body:
        sets.append("#n = :n")
        names["#n"] = "notes"
        values[":n"] = body["notes"]

    if "processedBy" in body:
        sets.append("#pb = :pb")
        names["#pb"] = "processed_by"
        values[":pb"] = body["processedBy"]

    if not sets:
        return error_response(400, "Provide at least one of: status, notes, processedBy")

    now_ms = int(time.time() * 1000)
    sets.append("updated_at = :ua")
    values[":ua"] = now_ms

    if "status" in body:
        sets.append("processed_at = :pa")
        values[":pa"] = now_ms

    try:
        resp = table.update_item(
            Key={"citation_id": citation_id},
            UpdateExpression="SET " + ", ".join(sets),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ConditionExpression="attribute_exists(citation_id)",
            ReturnValues="ALL_NEW",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return error_response(404, f"Citation {citation_id} not found")
        raise

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": "Citation updated", "citation": _json_safe(resp["Attributes"])},
            default=_json_serialize,
        ),
        "headers": _cors_headers(),
    }


def _json_safe(item):
    return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in item.items()}


def _json_serialize(o):
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError


def _cors_headers():
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,PUT,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
    }


def error_response(status_code, message):
    return {
        "statusCode": status_code,
        "body": json.dumps({"error": message}),
        "headers": _cors_headers(),
    }
