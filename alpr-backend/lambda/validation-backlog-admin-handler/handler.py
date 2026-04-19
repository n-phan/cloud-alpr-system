import base64
import json
import os
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "us-west-2")
TABLE_NAME = os.environ.get("VALIDATION_BACKLOG_TABLE", "ValidationBacklog")
LIST_DEFAULT_LIMIT = int(os.environ.get("LIST_DEFAULT_LIMIT", "50"))
LIST_MAX_LIMIT = int(os.environ.get("LIST_MAX_LIMIT", "100"))

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    """
    Admin API: list ValidationBacklog items (GET) or update a review (PUT).
    """
    method = _http_method(event)

    if method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": _cors_headers(),
            "body": "",
        }

    try:
        if method == "GET":
            return _list_reviews(event)
        if method == "PUT":
            return _update_review(event)
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


def _list_reviews(event):
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
    items = [_json_safe_item(item) for item in response.get("Items", [])]

    payload = {
        "items": items,
        "count": len(items),
    }
    lek = response.get("LastEvaluatedKey")
    if lek:
        payload["nextPageToken"] = base64.urlsafe_b64encode(
            json.dumps(lek, default=_json_serialize).encode("utf-8")
        ).decode("ascii")

    return {
        "statusCode": 200,
        "body": json.dumps(payload, default=_json_serialize),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    }


def _update_review(event):
    if isinstance(event.get("body"), str):
        body = json.loads(event["body"])
    else:
        body = event.get("body") or {}

    if "backlogId" not in body:
        return error_response(400, "Missing required field: backlogId")

    backlog_id = body["backlogId"]
    names = {}
    values = {}
    sets = []

    if "status" in body:
        sets.append("#st = :st")
        names["#st"] = "status"
        values[":st"] = body["status"]

    if "notes" in body:
        sets.append("#n = :n")
        names["#n"] = "notes"
        values[":n"] = body["notes"]

    if "reviewedBy" in body:
        sets.append("#rb = :rb")
        names["#rb"] = "reviewed_by"
        values[":rb"] = body["reviewedBy"]

    if not sets:
        return error_response(400, "Provide at least one of: status, notes, reviewedBy")

    now_ms = int(time.time() * 1000)
    sets.append("updated_at = :ua")
    values[":ua"] = now_ms

    if "status" in body:
        sets.append("reviewed_at = :ra")
        values[":ra"] = now_ms

    update_expression = "SET " + ", ".join(sets)

    try:
        resp = table.update_item(
            Key={"backlog_id": backlog_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ConditionExpression="attribute_exists(backlog_id)",
            ReturnValues="ALL_NEW",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return error_response(404, "Backlog item not found")
        raise

    item = _json_safe_item(resp["Attributes"])

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Review updated", "item": item}),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    }


def _json_serialize(o):
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError


def _json_safe_item(item):
    out = {}
    for k, v in item.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        else:
            out[k] = v
    return out


def _cors_headers():
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,PUT,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
    }


def error_response(status_code, message):
    return {
        "statusCode": status_code,
        "body": json.dumps({"error": message}),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    }
