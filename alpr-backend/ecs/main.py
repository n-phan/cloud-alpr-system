import os
import time
import uuid
import json
import logging
import urllib.parse
from decimal import Decimal

import boto3
import cv2
import numpy as np
from ultralytics import YOLO
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# =========================
# LOGGING
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================
# CONFIG
# =========================
MODEL_PATH = "best.pt"
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE")
REGION = os.environ.get("AWS_REGION")
QUEUE_URL = os.environ.get("SQS_QUEUE_URL")

MAX_RETRIES = 5
JOB_TIMEOUT = 30  # seconds
TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days

if not REGION:
    raise ValueError("AWS_REGION is required")

if not QUEUE_URL:
    raise ValueError("SQS_QUEUE_URL is required")

if not DYNAMODB_TABLE:
    raise ValueError("DYNAMODB_TABLE is required")

# =========================
# AWS SESSION
# =========================
session = boto3.Session(region_name=REGION)

s3 = session.client("s3")
rekognition = session.client("rekognition")
dynamodb = session.resource("dynamodb")
sqs = session.client("sqs")

table = dynamodb.Table(DYNAMODB_TABLE)

# =========================
# MODEL
# =========================
logger.info("Loading YOLO model...")
model = YOLO(MODEL_PATH)
logger.info("Model loaded successfully")

# =========================
# OCR
# =========================
def detect_largest_text_rekognition(image_bytes):
    response = rekognition.detect_text(Image={"Bytes": image_bytes})

    best_text = None
    best_area = 0

    for item in response.get("TextDetections", []):
        if item["Type"] != "WORD":
            continue

        box = item["Geometry"]["BoundingBox"]
        area = box["Width"] * box["Height"]

        if area > best_area:
            best_area = area
            best_text = item["DetectedText"]

    return best_text

# =========================
# IMAGE LOAD
# =========================
def load_image_from_s3(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    file_bytes = response["Body"].read()

    np_arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Failed to decode image")

    return img

# =========================
# WRITE RESULT (NEW SCHEMA)
# =========================
def write_result(vehicle_id, conf, plate_text, event_type="DETECTION", permit_status="UNKNOWN"):
    timestamp = int(time.time())

    item = {
        "timestamp": timestamp,
        "vehicle_id": vehicle_id,
        "confidence": Decimal(str(conf)),
        "event_type": event_type,
        "permit_status": permit_status,
        "plate_text": plate_text if plate_text else "UNKNOWN",
        "ttl": timestamp + TTL_SECONDS
    }

    table.put_item(Item=item)
    logger.info(f"DynamoDB write success: {vehicle_id}")

# =========================
# PIPELINE
# =========================
def process_s3_image(bucket, key):

    img = load_image_from_s3(bucket, key)
    results = model(img)

    detections = 0

    for box in results[0].boxes:
        conf = float(box.conf[0])

        if conf < 0.5:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        crop = img[y1:y2, x1:x2]

        if crop is None or crop.size == 0:
            continue

        _, buffer = cv2.imencode(".jpg", crop)
        crop_bytes = buffer.tobytes()

        plate_text = detect_largest_text_rekognition(crop_bytes)

        vehicle_id = str(uuid.uuid4())

        write_result(
            vehicle_id=vehicle_id,
            conf=conf,
            plate_text=plate_text
        )

        detections += 1

    logger.info(f"Processed {detections} detections for {key}")

# =========================
# SAFE EXECUTION WRAPPER
# =========================
def run_with_timeout(func, args):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args)
        return future.result(timeout=JOB_TIMEOUT)

# =========================
# SQS WORKER
# =========================
def poll_sqs():
    logger.info("Starting SQS worker...")

    while True:
        response = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10
        )

        messages = response.get("Messages", [])

        if not messages:
            continue

        for msg in messages:
            body = json.loads(msg["Body"])

            record = body["Records"][0]
            bucket = record["s3"]["bucket"]["name"]
            key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

            receipt = msg["ReceiptHandle"]

            retries = 0
            success = False

            while retries < MAX_RETRIES and not success:
                try:
                    logger.info(f"Processing attempt {retries+1}: s3://{bucket}/{key}")

                    run_with_timeout(process_s3_image, (bucket, key))

                    sqs.delete_message(
                        QueueUrl=QUEUE_URL,
                        ReceiptHandle=receipt
                    )

                    logger.info("Message processed and deleted")
                    success = True

                except TimeoutError:
                    retries += 1
                    logger.error(f"Timeout (attempt {retries})")

                except Exception as e:
                    retries += 1
                    logger.error(f"Error (attempt {retries}): {str(e)}")

            if not success:
                logger.error(f"FAILED after {MAX_RETRIES} retries: {key}")

# =========================
# ENTRYPOINT
# =========================
if __name__ == "__main__":
    poll_sqs()