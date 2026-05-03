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

from dotenv import load_dotenv
load_dotenv()
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

def extract_best_line(response):
    lines = [item for item in response.get("TextDetections", []) if item["Type"] == "LINE"]
    
    if not lines:
        return None, 0.0

    # Sort by height/area to find the most prominent text
    # Texas plates have 'TEXAS' at the top, which might have a large area.
    # We want the text that is most likely the plate (usually middle-center).
    lines.sort(key=lambda x: x["Geometry"]["BoundingBox"]["Height"], reverse=True)
    
    # Take the tallest LINE, but if there are multiple lines with similar height
    # located in the center, we may need to join them. 
    best_item = lines[0]
    return best_item["DetectedText"], best_item["Confidence"]

def detect_largest_text_rekognition(image_bytes):
    try:
        # Step 1: Detect on the RAW image first.
        # This prevents preprocessing from washing out the 'A' or '1'.
        response = rekognition.detect_text(Image={"Bytes": image_bytes})
        text, conf = extract_best_line(response)

        # Step 2: If the text looks too short (e.g., fewer than 5 characters), 
        # try again with light padding to help the OCR see the edges.
        if not text or len(text) < 5:
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is not None:
                h, w = img.shape[:2]
                # White padding is better for light plates
                pad = int(min(h, w) * 0.15)
                img = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255, 255, 255])
                _, buffer = cv2.imencode(".jpg", img)
                
                response = rekognition.detect_text(Image={"Bytes": buffer.tobytes()})
                text, conf = extract_best_line(response)

        return text, conf
    except Exception as e:
        logger.error(f"Rekognition error: {e}")
        return None, 0.0

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
    
def sanitize_for_dynamodb(data):
    if isinstance(data, list):
        return [sanitize_for_dynamodb(item) for item in data]
    if isinstance(data, dict):
        return {k: sanitize_for_dynamodb(v) for k, v in data.items()}
    if isinstance(data, (float, np.float32, np.float64)):
        return Decimal(str(data))
    return data

def write_result(vehicle_id, conf, plate_text, image_url, event_type="DETECTION", permit_status="UNKNOWN", ocr_conf=0.0):
    try:
        timestamp = int(time.time())
        # Build the initial dictionary
        raw_item = {
            "timestamp": timestamp,
            "vehicle_id": vehicle_id,
            "confidence": conf,
            "ocr_confidence": ocr_conf,
            "event_type": event_type,
            "permit_status": permit_status,
            "plate_text": plate_text if plate_text else "UNKNOWN",
            "image_url": image_url,
            "ttl": timestamp + TTL_SECONDS
        }

        # Use the sanitize function to convert all floats/numpy types to Decimals
        item = sanitize_for_dynamodb(raw_item)

        table.put_item(Item=item)
        logger.info(f"Successfully wrote record for {vehicle_id}")
        
    except Exception as e:
        logger.error(f"DynamoDB Write Error for {vehicle_id}: {e}")
        raise

def process_s3_image(bucket, key):
    try:
        image_url = f"https://{bucket}.s3.{REGION}.amazonaws.com/{key}"
        img = load_image_from_s3(bucket, key)
        if img is None: return

        results = model(img)
        detections = 0

        for box in results[0].boxes:
            try:
                conf = box.conf[0].item() # Standard Python float
                if conf < 0.5: continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                crop = img[max(0, y1):y2, max(0, x1):x2]
                
                if crop is None or crop.size == 0: continue

                success, buffer = cv2.imencode(".jpg", crop)
                if not success: continue

                # FIX: Unpack the tuple returned by Rekognition
                plate_text, ocr_conf = detect_largest_text_rekognition(buffer.tobytes())
                
                # Pass both values to write_result
                write_result(
                    vehicle_id=str(uuid.uuid4()), 
                    conf=conf, 
                    plate_text=plate_text, 
                    image_url=image_url,
                    ocr_conf=ocr_conf
                )
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