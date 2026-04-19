import json
import os
import time
import uuid
from decimal import Decimal

import boto3

REGION = os.environ.get("AWS_REGION", "us-west-2")
TABLE_NAME = os.environ.get("VALIDATION_BACKLOG_TABLE", "ValidationBacklog")


def _threshold() -> float:
    raw = os.environ.get("CONFIDENCE_THRESHOLD", "0.7")
    return float(raw)


dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    """
    Queue low-confidence plate detection results for manual review in ValidationBacklog.
    Items are written only when confidence is strictly below CONFIDENCE_THRESHOLD.
    """
    try:
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body") or {}

        required_fields = ["vehicleId", "plateText", "confidence"]
        for field in required_fields:
            if field not in body:
                return error_response(400, f"Missing required field: {field}")

        confidence = float(body["confidence"])
        threshold = _threshold()

        if confidence >= threshold:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "queued": False,
                        "reason": "confidence meets or exceeds threshold",
                        "confidence": confidence,
                        "threshold": threshold,
                    }
                ),
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
            }

        backlog_id = body.get("backlogId") or str(uuid.uuid4())
        ttl = int(time.time()) + (30 * 86400)  # 30 days, aligned with GateEvents pattern

        item = {
            "backlog_id": backlog_id,
            "vehicle_id": body["vehicleId"],
            "plate_text": body["plateText"],
            "confidence": Decimal(str(body["confidence"])),
            "threshold_used": Decimal(str(threshold)),
            "created_at": int(time.time() * 1000),
            "status": "pending_review",
            "ttl": ttl,
        }

        if "permitStatus" in body:
            item["permit_status"] = body["permitStatus"]
        if "eventType" in body:
            item["event_type"] = body["eventType"]
        if "imageUrl" in body:
            item["image_url"] = body["imageUrl"]
        if "notes" in body:
            item["notes"] = body["notes"]

        table.put_item(Item=item)

        return {
            "statusCode": 201,
            "body": json.dumps(
                {
                    "message": "Low-confidence result queued for review",
                    "backlogId": backlog_id,
                    "confidence": confidence,
                    "threshold": threshold,
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


def error_response(status_code, message):
    return {
        "statusCode": status_code,
        "body": json.dumps({"error": message}),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    }
