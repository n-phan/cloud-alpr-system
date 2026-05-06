import time

from sqs.sqs import receive_messages, delete_message, parse_s3_event, retry_with_backoff
from s3.s3_client import download_image
from worker.processor import process_plate
from dynamodb.db import write_event
from config import AWS_REGION

def main():
    print("ECS worker started...")

    while True:
        try:
            messages = receive_messages()
            for msg in messages:
                try:
                    bucket, key = parse_s3_event(msg)
                    path = download_image(bucket, key)
                    results = process_plate(path)

                    for r in results:
                        write_event(
                            conf=r.get("confidence", 0.0),
                            plate_text=r.get("plate", "NOT_FOUND"),
                            image_url=f"https://{bucket}.s3.{AWS_REGION}.amazonaws.com/{key}",
                        )

                    delete_message(msg["ReceiptHandle"])

                except Exception as e:
                    print("[FAIL] letting SQS retry:", e)

        except Exception as e:
            print("[WORKER LOOP CRASH]", e)

        time.sleep(2)


if __name__ == "__main__":
    main()