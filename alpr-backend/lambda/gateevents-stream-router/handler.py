import json
import os
from decimal import Decimal

import boto3

THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.85"))
PERMIT_CHECKER_FUNCTION = os.environ.get("PERMIT_CHECKER_FUNCTION", "permit-checker")
VALIDATION_BACKLOG_FUNCTION = os.environ.get(
    "VALIDATION_BACKLOG_FUNCTION", "validation-backlog-handler"
)

lambda_client = boto3.client("lambda")


def lambda_handler(event, context):
    processed = 0
    routed_to_permit_checker = 0
    routed_to_validation_backlog = 0

    for record in event.get("Records", []):
        # Only process newly inserted GateEvents items.
        if record.get("eventName") != "INSERT":
            continue

        new_image = (record.get("dynamodb") or {}).get("NewImage") or {}
        item = _from_ddb_image(new_image)
        vehicle_id = item.get("vehicle_id")
        plate_text = item.get("plate_text")
        confidence = _to_float(item.get("confidence"))
        permit_status = item.get("permit_status")
        event_type = item.get("event_type")
        image_url = item.get("image_url")

        if not vehicle_id or not plate_text or confidence is None:
            print(f"Skipping record with missing fields: {item}")
            continue

        processed += 1

        if confidence > THRESHOLD:
            payload = {
                "queryStringParameters": {
                    "vehicleId": vehicle_id,
                }
            }
            _invoke(PERMIT_CHECKER_FUNCTION, payload)
            routed_to_permit_checker += 1
        else:
            body = {
                "vehicleId": vehicle_id,
                "plateText": plate_text,
                "confidence": confidence,
            }
            if permit_status is not None:
                body["permitStatus"] = permit_status
            if event_type is not None:
                body["eventType"] = event_type
            if image_url is not None:
                body["imageUrl"] = image_url

            payload = {"body": json.dumps(body)}
            _invoke(VALIDATION_BACKLOG_FUNCTION, payload)
            routed_to_validation_backlog += 1

    return {
        "statusCode": 200,
        "processed": processed,
        "routedToPermitChecker": routed_to_permit_checker,
        "routedToValidationBacklog": routed_to_validation_backlog,
        "threshold": THRESHOLD,
    }


def _invoke(function_name, payload):
    resp = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    status_code = resp.get("StatusCode", 0)
    if status_code < 200 or status_code >= 300:
        raise RuntimeError(f"Invoke failed for {function_name}: {status_code}")


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
