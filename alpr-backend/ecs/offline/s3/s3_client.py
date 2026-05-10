import boto3
import os
from config import AWS_REGION

s3 = boto3.client("s3", region_name=AWS_REGION)


def download_image(bucket, key, local_dir="/tmp"):
    """
    Downloads an S3 object to local disk and returns file path.
    """
    os.makedirs(local_dir, exist_ok=True)

    filename = os.path.join(local_dir, os.path.basename(key))

    s3.download_file(bucket, key, filename)

    return filename