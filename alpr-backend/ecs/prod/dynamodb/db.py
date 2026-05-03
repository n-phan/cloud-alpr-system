import boto3
import time
import uuid
from decimal import Decimal
from botocore.exceptions import ClientError, BotoCoreError
from config import AWS_REGION, DYNAMODB_TABLE


dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)


def to_decimal(value):
    """
    Safely convert float/int → Decimal for DynamoDB
    """
    try:
        if value is None:
            return Decimal("0.0")
        return Decimal(str(value))
    except Exception:
        return Decimal("0.0")


def write_event(conf, plate_text, image_url, ocr_conf):
    try:
        item = {
            "vehicle_id": str(uuid.uuid4()),

            "confidence": to_decimal(conf),
            "plate_text": str(plate_text or "NOT_FOUND"),
            "image_url": str(image_url or ""),

            "ocr_confidence": to_decimal(ocr_conf),
            "event_type": "DETECTION",
            "permit_status": "UNKNOWN",
            "timestamp": int(time.time())
        }

        table.put_item(Item=item)

        return item

    except (ClientError, BotoCoreError) as e:
        print("[DB ERROR] write_event:", e)
        return None

    except Exception as e:
        print("[DB FATAL] write_event:", e)
        return None