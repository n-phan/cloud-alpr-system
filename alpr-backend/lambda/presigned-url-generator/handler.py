import json
import boto3
import os
from datetime import datetime

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    Generate a pre-signed S3 URL for client-side image upload
    """
    try:
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'alpr-images-bucket')
        
        # Generate unique key (filename) for the image
        timestamp = datetime.now().isoformat()
        key = f"uploads/{timestamp}.jpg"
        
        # Generate pre-signed URL (valid for 1 hour)
        url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': key
            },
            ExpiresIn=3600  # 1 hour
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'uploadUrl': url,
                'expiresIn': 3600,
                'key': key
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to generate pre-signed URL'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
