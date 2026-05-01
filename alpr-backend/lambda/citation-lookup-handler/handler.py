import json
import os

import boto3
from boto3.dynamodb.conditions import Attr

REGION = os.environ.get("AWS_REGION", "us-west-2")
TABLE_NAME = os.environ.get("CITATIONS_TABLE", "Citations")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    """
    Public API: look up citations by license plate text (GET).
    """
    method = _http_method(event)

    if method == "OPTIONS":
        return {"statusCode": 204, "headers": _cors_headers(), "body": ""}

    if method != "GET":
        return error_response(405, f"Method not allowed: {method}")

    params = event.get("queryStringParameters") or {}
    plate_text = (params.get("plateText") or "").strip().upper()

    if not plate_text:
        return error_response(400, "Missing required query parameter: plateText")

    try:
        response = table.scan(
            FilterExpression=Attr("plate_text").eq(plate_text)
        )
        items = response.get("Items", [])

        # Convert Decimal to float for JSON serialization
        citations = [_serialize(item) for item in items]
        citations.sort(key=lambda c: c.get("issued_at", 0), reverse=True)

        return {
            "statusCode": 200,
            "headers": _cors_headers(),
            "body": json.dumps({"citations": citations, "count": len(citations)}),
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(500, "Internal server error")


def _serialize(item):
    from decimal import Decimal
    result = {}
    for k, v in item.items():
        result[k] = float(v) if isinstance(v, Decimal) else v
    return result


def _http_method(event):
    if event.get("httpMethod"):
        return event["httpMethod"].upper()
    rc = event.get("requestContext") or {}
    return rc.get("http", {}).get("method", "GET").upper()


def _cors_headers():
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
    }


def error_response(status_code, message):
    return {
        "statusCode": status_code,
        "body": json.dumps({"error": message}),
        "headers": _cors_headers(),
    }
