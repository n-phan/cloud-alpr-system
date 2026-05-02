import json
import os
import time
import uuid
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "us-west-2")
TABLE_NAME = os.environ.get("CITATIONS_TABLE", "Citations")


def _default_amount() -> Decimal:
    raw = os.environ.get("DEFAULT_CITATION_AMOUNT", "100")
    try:
        return Decimal(str(raw))
    except Exception:
        return Decimal("100")


def _citation_id_for_occurrence(occurrence_key: str) -> str:
    # Deterministic ID + conditional put enforces "one citation per occurrence"
    # under concurrency without relying on an occurrence_key GSI pre-check query.
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"occurrence:{occurrence_key}"))


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

        occurrence_key = body.get("occurrenceKey")
        citation_id = (
            _citation_id_for_occurrence(occurrence_key)
            if occurrence_key
            else (body.get("citationId") or str(uuid.uuid4()))
        )
        issued_at = int(body["issuedAt"]) if "issuedAt" in body else int(time.time())

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
        else:
            item["amount"] = _default_amount()
        if "notes" in body:
            item["notes"] = body["notes"]
        if "imageUrl" in body:
            item["image_url"] = body["imageUrl"]
        if "relatedBacklogId" in body:
            item["related_backlog_id"] = body["relatedBacklogId"]
        if "issuedBy" in body:
            item["issued_by"] = body["issuedBy"]
        if occurrence_key:
            # Keep occurrence_key as a query/reporting attribute. Any optional
            # occurrence_key-index is for lookup convenience, not write-time dedupe.
            item["occurrence_key"] = occurrence_key

        try:
            table.put_item(
                Item=item,
                # Atomic guardrail: if the deterministic citation_id already exists,
                # this write fails and we return duplicate=True below.
                ConditionExpression="attribute_not_exists(citation_id)",
            )
        except ClientError as e:
            code = (e.response.get("Error") or {}).get("Code")
            if code == "ConditionalCheckFailedException":
                if occurrence_key:
                    return {
                        "statusCode": 200,
                        "body": json.dumps(
                            {
                                "message": "Citation already exists for occurrence",
                                "duplicate": True,
                                "citationId": citation_id,
                                "occurrenceKey": occurrence_key,
                            }
                        ),
                        "headers": {
                            "Content-Type": "application/json",
                            "Access-Control-Allow-Origin": "*",
                        },
                    }
                return error_response(409, "Citation ID already exists")
            raise

        return {
            "statusCode": 201,
            "body": json.dumps(
                {
                    "message": "Citation created",
                    "citationId": citation_id,
                    "issuedAt": issued_at,
                    "amount": str(item["amount"]),
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
