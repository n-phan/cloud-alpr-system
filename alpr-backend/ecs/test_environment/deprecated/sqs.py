import boto3
from config import AWS_REGION, SQS_QUEUE_URL

sqs = boto3.client("sqs", region_name=AWS_REGION)


def receive_messages(max_messages=5, wait_time=10):
    """
    Poll SQS queue for messages
    """
    response = sqs.receive_message(
        QueueUrl=SQS_QUEUE_URL,
        MaxNumberOfMessages=max_messages,
        WaitTimeSeconds=wait_time
    )

    return response.get("Messages", [])


def delete_message(receipt_handle):
    """
    Delete message after successful processing
    """
    sqs.delete_message(
        QueueUrl=SQS_QUEUE_URL,
        ReceiptHandle=receipt_handle
    )


def parse_s3_event(message):
    """
    Extract bucket + key from SQS message (S3 event format)
    """
    import json

    body = json.loads(message["Body"])

    # S3 event structure inside SQS
    record = body["Records"][0]

    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]

    return bucket, key