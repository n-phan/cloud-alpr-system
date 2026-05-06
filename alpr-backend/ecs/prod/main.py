import time

from sqs.sqs import receive_messages, delete_message, parse_s3_event
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
                    print(f"Processing: {bucket}/{key}")

                    local_path = download_image(bucket, key)

                    # -------------------------
                    # ML PIPELINE
                    # -------------------------
                    results = process_plate(local_path)

                    print("Results:", results)

                    # -------------------------
                    # WRITE TO DB (FIXED)
                    # -------------------------
                    for r in results:
                        write_event(
                            conf=r.get("confidence", 0.0),
                            plate_text=r.get("plate", "NOT_FOUND"),
                            image_url = f"https://{bucket}.s3.{AWS_REGION}.amazonaws.com/{key}",
                        )

                    delete_message(msg["ReceiptHandle"])

                except Exception as e:
                    print("[MESSAGE FAILED]", e)

        except Exception as e:
            print("[WORKER LOOP CRASH]", e)

        time.sleep(2)


if __name__ == "__main__":
    main()