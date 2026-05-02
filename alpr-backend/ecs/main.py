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
from botocore.exceptions import ClientError
# =========================
# LOGGING
# =========================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =========================
# CONFIG
# =========================
MODEL_PATH = "best.pt"
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE")
REGION = os.environ.get("AWS_REGION")
QUEUE_URL = os.environ.get("SQS_QUEUE_URL")

MAX_RETRIES = 5
JOB_TIMEOUT = 30  
TTL_SECONDS = 60 * 60 * 24 * 7 

# Validation check on startup
for var in ["AWS_REGION", "SQS_QUEUE_URL", "DYNAMODB_TABLE"]:
    if not os.environ.get(var):
        raise EnvironmentError(f"Missing required environment variable: {var}")

# =========================
# AWS SESSION
# =========================
try:
    session = boto3.Session(region_name=REGION)
    s3 = session.client("s3")
    rekognition = session.client("rekognition")
    dynamodb = session.resource("dynamodb")
    sqs = session.client("sqs")
    table = dynamodb.Table(DYNAMODB_TABLE)
except Exception as e:
    logger.critical(f"Failed to initialize AWS clients: {e}")
    raise

# =========================
# MODEL LOAD
# =========================
try:
    logger.info("Loading YOLO model...")
    model = YOLO(MODEL_PATH)
except Exception as e:
    logger.critical(f"Model weight file not found or corrupt at {MODEL_PATH}: {e}")
    raise

# =========================
# LOGIC FUNCTIONS
# =========================

def detect_largest_text_rekognition(image_bytes):
    try:
        response = rekognition.detect_text(Image={"Bytes": image_bytes})
        best_text, best_area = None, 0

        for item in response.get("TextDetections", []):
            if item["Type"] != "WORD":
                continue
            
            box = item["Geometry"]["BoundingBox"]
            area = box["Width"] * box["Height"]
            if area > best_area:
                best_area = area
                best_text = item["DetectedText"]
        return best_text
    except ClientError as e:
        logger.error(f"Rekognition API error: {e}")
        return None

def load_image_from_s3(bucket, key):
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        file_bytes = response["Body"].read()
        np_arr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("CV2 failed to decode image bytes.")
        return img
    except Exception as e:
        logger.error(f"S3 Load Error for {key}: {e}")
        return None

def write_result(vehicle_id, conf, plate_text, image_url, event_type="DETECTION", permit_status="UNKNOWN"):
    try:
        timestamp = int(time.time())
        item = {
            "timestamp": timestamp,
            "vehicle_id": vehicle_id,
            "confidence": Decimal(str(round(conf, 4))),
            "event_type": event_type,
            "permit_status": permit_status,
            "plate_text": plate_text if plate_text else "UNKNOWN",
            "image_url": image_url,
            "ttl": timestamp + TTL_SECONDS
        }
        table.put_item(Item=item)
    except Exception as e:
        logger.error(f"DynamoDB Write Error for {vehicle_id}: {e}")
        raise # Re-raise to trigger retry in the main pipeline

def process_s3_image(bucket, key):
    try:
        image_url = f"https://{bucket}.s3.{REGION}.amazonaws.com/{key}"
        img = load_image_from_s3(bucket, key)
        if img is None: return

        results = model(img)
        detections = 0

        for box in results[0].boxes:
            try:
                conf = float(box.conf[0])
                if conf < 0.5: continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                crop = img[max(0, y1):y2, max(0, x1):x2] # Prevent negative indexing
                
                if crop is None or crop.size == 0: continue

                success, buffer = cv2.imencode(".jpg", crop)
                if not success: continue

                plate_text = detect_largest_text_rekognition(buffer.tobytes())
                write_result(str(uuid.uuid4()), conf, plate_text, image_url)
                detections += 1
            except Exception as e:
                logger.error(f"Error in single detection crop: {e}")
                continue

        logger.info(f"Finished {key}: {detections} vehicles found.")
    except Exception as e:
        logger.error(f"Pipeline failure for {key}: {e}")
        raise

# =========================
# SQS WORKER
# =========================

def run_with_timeout(func, args):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args)
        return future.result(timeout=JOB_TIMEOUT)

def poll_sqs():
    logger.info("Worker Online. Polling SQS...")
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20 # Maximize long-polling to save money
            )
            
            messages = response.get("Messages", [])
            if not messages: continue

            for msg in messages:
                receipt = msg["ReceiptHandle"]
                try:
                    body = json.loads(msg["Body"])
                    # Deep check for S3 Event structure
                    if "Records" not in body:
                        logger.warning("Message format not S3 Event. Deleting.")
                        sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt)
                        continue

                    record = body["Records"][0]
                    bucket = record["s3"]["bucket"]["name"]
                    key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

                    # Process with Retries
                    success = False
                    for attempt in range(MAX_RETRIES):
                        try:
                            run_with_timeout(process_s3_image, (bucket, key))
                            success = True
                            break
                        except TimeoutError:
                            logger.error(f"Timeout on {key} (Attempt {attempt+1})")
                        except Exception as e:
                            logger.error(f"Process Error on {key}: {e}")
                            time.sleep(1) # Backoff

                    if success:
                        sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt)
                    else:
                        logger.critical(f"Poison Pill: {key} failed after max retries.")
                        # Message will return to queue and eventually move to DLQ

                except Exception as e:
                    logger.error(f"Failed to parse message body: {e}")

        except Exception as e:
            logger.error(f"SQS Polling Loop Error: {e}")
            time.sleep(5) # Prevent rapid-fire logging if SQS is down

if __name__ == "__main__":
    poll_sqs()