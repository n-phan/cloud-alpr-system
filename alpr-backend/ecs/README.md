# Vehicle Detection + License Plate Recognition Pipeline

This project is an AWS-based real-time computer vision pipeline that:

* Consumes image events from SQS
* Loads images from S3
* Runs YOLO object detection
* Extracts license plates using AWS Rekognition OCR
* Stores results in DynamoDB
* Supports retries and timeout safety for production reliability

---

# Architecture Overview

```
S3 Upload → SQS Event → Worker → YOLO Detection → OCR → DynamoDB
```

---

# Features

* Real-time SQS consumer
* YOLOv8 object detection
* AWS Rekognition OCR for license plates
* DynamoDB result storage
* Timeout protection per job
* Retry logic (resilient pipeline)
* Automatic TTL cleanup (7 days)

---

# Tech Stack

* Python 3.10+
* AWS S3
* AWS SQS
* AWS DynamoDB
* AWS Rekognition
* OpenCV
* Ultralytics YOLO
* NumPy

---

# Environment Variables

```bash
AWS_REGION=us-east-1
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/...
DYNAMODB_TABLE=vehicle-detections
```

---

# How It Works

---

## 1. SQS Worker Loop

The system continuously polls SQS for new image events.

```python
def poll_sqs():
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    )
```

Explanation:

* Long-polling reduces API cost
* Processes 1 message at a time for stability
* Waits up to 10 seconds for new jobs

---

## 2. Image Loading from S3

Images are fetched and decoded into OpenCV format.

```python
def load_image_from_s3(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    file_bytes = response["Body"].read()

    np_arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
```

Explanation:

* Downloads raw image bytes from S3
* Converts to NumPy array
* Decodes into OpenCV image

---

## 3. YOLO Object Detection

Detects vehicles or regions of interest.

```python
results = model(img)

for box in results[0].boxes:
    conf = float(box.conf[0])

    if conf < 0.5:
        continue
```

Explanation:

* Uses confidence threshold (0.5)
* Filters low-quality detections
* Extracts bounding boxes

---

## 4. Crop and Plate Extraction

Detected vehicle region is cropped for OCR.

```python
crop = img[y1:y2, x1:x2]

_, buffer = cv2.imencode(".jpg", crop)
crop_bytes = buffer.tobytes()
```

Explanation:

* Crops bounding box region
* Encodes image for OCR input

---

## 5. OCR with AWS Rekognition

Extracts the largest detected text (likely plate number).

```python
def detect_largest_text_rekognition(image_bytes):
    response = rekognition.detect_text(Image={"Bytes": image_bytes})
```

Explanation:

* Uses AWS OCR engine
* Filters WORD-level detections
* Selects largest bounding box text

---

## 6. DynamoDB Storage

Stores detection results with TTL cleanup.

```python
def write_result(vehicle_id, conf, plate_text):
    item = {
        "timestamp": timestamp,
        "vehicle_id": vehicle_id,
        "confidence": Decimal(str(conf)),
        "event_type": "DETECTION",
        "plate_text": plate_text or "UNKNOWN",
        "ttl": timestamp + TTL_SECONDS
    }

    table.put_item(Item=item)
```

Explanation:

* Each detection gets unique UUID
* Confidence stored as Decimal (DynamoDB requirement)
* TTL auto-deletes after 7 days

---

## 7. Timeout Protection

Prevents stuck jobs from blocking pipeline.

```python
def run_with_timeout(func, args):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args)
        return future.result(timeout=JOB_TIMEOUT)
```

Explanation:

* Limits execution to 30 seconds
* Prevents worker crashes or hangs

---

## 8. Retry Logic

Ensures reliability for failed jobs.

```python
while retries < MAX_RETRIES and not success:
    try:
        run_with_timeout(process_s3_image, (bucket, key))
        sqs.delete_message(...)
```

Explanation:

* Retries up to 5 times
* Deletes message only on success
* Logs failures for debugging

---

# Running the Service

```bash
python main.py
```

---

# Output Example (DynamoDB Item)

```json
{
  "timestamp": 1712345678,
  "vehicle_id": "uuid-123",
  "confidence": 0.92,
  "event_type": "DETECTION",
  "permit_status": "UNKNOWN",
  "plate_text": "ABC1234",
  "ttl": 1712950478
}
```

---

# Production Notes

* Do not expose AWS credentials in code
* Use IAM roles if running on EC2 or ECS
* Add DLQ (dead-letter queue) for failed messages
* Consider batching for high throughput
* Swap YOLO model to GPU instance for scale

---

# Possible Improvements

* Add FastAPI dashboard for results
* Store images with bounding boxes annotated
* Add Redis cache for duplicate plates
* Integrate alerting (Discord or email webhook)
* Switch to async processing pipeline

---

# Summary

This system is a real-time, cloud-native computer vision pipeline that:

* Detects vehicles using YOLO
* Extracts license plates using OCR
* Processes events from AWS SQS
* Stores structured results in DynamoDB
* Handles failures with retries and timeout safety
