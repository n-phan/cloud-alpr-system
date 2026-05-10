from sqs import receive_messages, delete_message, parse_s3_event
from s3_client import download_image

def main():
    print("ECS worker started...")

    while True:
        messages = receive_messages()

        for msg in messages:
            try:
                bucket, key = parse_s3_event(msg)

                print(f"Processing: {bucket}/{key}")

                local_path = download_image(bucket, key)

                results = process_image(local_path)

                print("Results:", results)

                # delete ONLY after success
                delete_message(msg["ReceiptHandle"])

            except Exception as e:
                print("Processing failed:", e)

        time.sleep(2)