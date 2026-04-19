import json
import os
import time
import uuid
from decimal import Decimal

import boto3

REGION = os.environ.get("AWS_REGION", "us-west-2")
TABLE_NAME = os.environ.get("CITATIONS_TABLE", "Citations")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    """
    Admin API: create a citation record in the Citations table (POST).
    """
    method = _http_method(event)

    if method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": _cors_headers(),
            "body": "",
        }

    if method != "POST":
        return error_response(405, f"Method not allowed: {method}")

    try:
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body") or {}

        required_fields = ["vehicleId", "plateText", "reason"]
        for field in required_fields:
            if field not in body:
                return error_response(400, f"Missing required field: {field}")

        citation_id = body.get("citationId") or str(uuid.uuid4())
        issued_at = int(body["issuedAt"]) if "issuedAt" in body else int(time.time() * 1000)

        item = {
            "citation_id": citation_id,
            "vehicle_id": body["vehicleId"],
            "plate_text": body["plateText"],
            "reason": body["reason"],
            "issued_at": issued_at,
            "status": body.get("status", "issued"),
        }

        if "amount" in body:
            item["amount"] = Decimal(str(body["amount"]))
        if "notes" in body:
            item["notes"] = body["notes"]
        if "imageUrl" in body:
            item["image_url"] = body["imageUrl"]
        if "relatedBacklogId" in body:
            item["related_backlog_id"] = body["relatedBacklogId"]
        if "issuedBy" in body:
            item["issued_by"] = body["issuedBy"]

        table.put_item(Item=item)

        return {
            "statusCode": 201,
            "body": json.dumps(
                {
                    "message": "Citation created",
                    "citationId": citation_id,
                    "issuedAt": issued_at,
                }
            ),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        }

    except ValueError as e:
        return error_response(400, f"Invalid value in request: {e}")
    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(500, "Internal server error")


def _http_method(event):
    if event.get("httpMethod"):
        return event["httpMethod"].upper()
    rc = event.get("requestContext") or {}
    if rc.get("http", {}).get("method"):
        return rc["http"]["method"].upper()
    return "POST"


def _cors_headers():
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
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
