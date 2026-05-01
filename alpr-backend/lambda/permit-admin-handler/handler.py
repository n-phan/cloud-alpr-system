import json
import os
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "us-west-2")
TABLE_NAME = os.environ.get("PERMITS_TABLE", "Permits")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    method = _http_method(event)

    if method == "OPTIONS":
        return {"statusCode": 204, "headers": _cors_headers(), "body": ""}

    try:
        if method == "GET":
            return _list_permits(event)
        if method == "POST":
            return _create_permit(event)
        if method == "PUT":
            return _update_permit(event)
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


def _list_permits(event):
    params = event.get("queryStringParameters") or {}
    limit = min(int(params.get("limit", 100)), 200)

    scan_kwargs = {"Limit": limit}
    response = table.scan(**scan_kwargs)
    items = [_to_api(item) for item in response.get("Items", [])]

    return {
        "statusCode": 200,
        "body": json.dumps({"items": items, "count": len(items)}, default=_json_serialize),
        "headers": _cors_headers(),
    }


def _create_permit(event):
    if isinstance(event.get("body"), str):
        body = json.loads(event["body"])
    else:
        body = event.get("body") or {}

    vehicle_id = (body.get("vehicleId") or "").strip().upper()
    owner = (body.get("owner") or "").strip()
    expiry_date = (body.get("expiryDate") or "").strip()

    if not vehicle_id:
        return error_response(400, "vehicleId is required")
    if not owner:
        return error_response(400, "owner is required")
    if not expiry_date:
        return error_response(400, "expiryDate is required")

    item = {
        "vehicle_id": vehicle_id,
        "owner": owner,
        "permit_status": "VALID",
        "expiry_date": expiry_date,
        "created_at": int(time.time() * 1000),
    }

    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(vehicle_id)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return error_response(409, f"Permit for {vehicle_id} already exists")
        raise

    return {
        "statusCode": 201,
        "body": json.dumps({"message": "Permit created", "permit": _to_api(item)}),
        "headers": _cors_headers(),
    }


def _update_permit(event):
    if isinstance(event.get("body"), str):
        body = json.loads(event["body"])
    else:
        body = event.get("body") or {}

    vehicle_id = (body.get("vehicleId") or "").strip().upper()
    if not vehicle_id:
        return error_response(400, "vehicleId is required")

    names = {}
    values = {}
    sets = []

    if "status" in body:
        valid_statuses = {"VALID", "EXPIRED", "REVOKED"}
        status = body["status"].upper()
        if status not in valid_statuses:
            return error_response(400, f"status must be one of: {', '.join(valid_statuses)}")
        sets.append("#ps = :ps")
        names["#ps"] = "permit_status"
        values[":ps"] = status

    if "owner" in body:
        sets.append("#ow = :ow")
        names["#ow"] = "owner"
        values[":ow"] = body["owner"]

    if "expiryDate" in body:
        sets.append("expiry_date = :ed")
        values[":ed"] = body["expiryDate"]

    if not sets:
        return error_response(400, "Provide at least one of: status, owner, expiryDate")

    sets.append("updated_at = :ua")
    values[":ua"] = int(time.time() * 1000)

    try:
        resp = table.update_item(
            Key={"vehicle_id": vehicle_id},
            UpdateExpression="SET " + ", ".join(sets),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ConditionExpression="attribute_exists(vehicle_id)",
            ReturnValues="ALL_NEW",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return error_response(404, f"Permit for {vehicle_id} not found")
        raise

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Permit updated", "permit": _to_api(resp["Attributes"])},
                           default=_json_serialize),
        "headers": _cors_headers(),
    }


def _to_api(item):
    return {
        "vehicleId": item.get("vehicle_id"),
        "owner": item.get("owner"),
        "permitStatus": item.get("permit_status"),
        "expiryDate": item.get("expiry_date"),
    }


def _json_serialize(o):
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError


def _cors_headers():
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
    }


def error_response(status_code, message):
    return {
        "statusCode": status_code,
        "body": json.dumps({"error": message}),
        "headers": _cors_headers(),
    }
