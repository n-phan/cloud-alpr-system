import boto3
import json
import time
from botocore.exceptions import ClientError, BotoCoreError
from config import AWS_REGION, SQS_QUEUE_URL, SQS_DLQ_URL


sqs = boto3.client("sqs", region_name=AWS_REGION)


# =========================================================
# RETRY WRAPPER
# =========================================================
def retry_with_backoff(func, args=(), kwargs=None, max_retries=5, base_delay=1):
    """
    Generic retry wrapper with exponential backoff.
    Used for AWS + pipeline operations.
    """
    if kwargs is None:
        kwargs = {}

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            last_error = e
            delay = base_delay * (2 ** (attempt - 1))

            print(f"[RETRY] {func.__name__} failed (attempt {attempt}/{max_retries}): {e}")
            print(f"[RETRY] sleeping {delay}s")

            time.sleep(delay)

    raise last_error


# =========================================================
# RECEIVE MESSAGES
# =========================================================
def receive_messages(max_messages=10, wait_time=10):
    try:
        response = sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time,
            VisibilityTimeout=60
        )

        return response.get("Messages", [])

    except (ClientError, BotoCoreError) as e:
        print("[SQS ERROR] receive_messages:", e)
        return []

    except Exception as e:
        print("[SQS FATAL] receive_messages:", e)
        return []


# =========================================================
# DELETE MESSAGE
# =========================================================
def delete_message(receipt_handle):
    try:
        sqs.delete_message(
            QueueUrl=SQS_QUEUE_URL,
            ReceiptHandle=receipt_handle
        )

    except (ClientError, BotoCoreError) as e:
        print("[SQS ERROR] delete_message:", e)

    except Exception as e:
        print("[SQS FATAL] delete_message:", e)


# =========================================================
# SEND TO DLQ
# =========================================================
def send_to_dlq(message, error_reason="processing_failed"):
    try:
        payload = {
            "original": message,
            "error": str(error_reason),
            "timestamp": int(time.time())
        }

        sqs.send_message(
            QueueUrl=SQS_DLQ_URL,
            MessageBody=json.dumps(payload)
        )

    except (ClientError, BotoCoreError) as e:
        print("[DLQ ERROR] send_to_dlq:", e)

    except Exception as e:
        print("[DLQ FATAL] send_to_dlq:", e)


# =========================================================
# PARSE S3 EVENT (SAFE + RETRYABLE)
# =========================================================
def parse_s3_event(message):
    body = json.loads(message.get("Body", "{}"))

    records = body.get("Records")
    if not records:
        raise ValueError("No S3 Records found")

    record = records[0]

    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]

    return bucket, key


# =========================================================
# SAFE SLEEP
# =========================================================
def safe_sleep(seconds=2):
    try:
        time.sleep(seconds)
    except Exception:
        pass