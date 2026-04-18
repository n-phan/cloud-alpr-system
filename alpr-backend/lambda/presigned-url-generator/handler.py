import json
import boto3
from datetime import datetime

s3_client = boto3.client('s3', region_name='us-west-2')

def lambda_handler(event, context):
    """
    Generate a pre-signed S3 URL for client-side image upload
    """
    try:
        bucket_name = 'alpr-raw-data-cmpe281'
        
        # Generate unique key (filename) for the image
        timestamp = datetime.now().isoformat().replace(':', '-')
        key = f"uploads/{timestamp}.jpg"
        
        # Generate pre-signed URL (valid for 1 hour)
        url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': key
            },
            ExpiresIn=3600
        )
        
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
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
