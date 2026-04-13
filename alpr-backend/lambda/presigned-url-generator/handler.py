import json
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """
    Generate a pre-signed S3 URL for client-side image upload
    """
    try:
        # Initialize S3 client explicitly
        s3_client = boto3.client('s3', region_name='us-west-2')
        
        bucket_name = 'alpr-raw-data-1776056491'
        
        # Generate unique key
        timestamp = datetime.now().isoformat().replace(':', '-').replace('.', '-')
        key = f"uploads/{timestamp}.jpg"
        
        print(f"Generating presigned URL for bucket: {bucket_name}, key: {key}")
        
        # Generate presigned URL
        url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': key
            },
            ExpiresIn=3600
        )
        
        print(f"Generated URL: {url}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'uploadUrl': url,
                'expiresIn': 3600,
                'key': key,
                'bucket': bucket_name
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
