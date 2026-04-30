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

Images are fetched and decoded into OpenCV
