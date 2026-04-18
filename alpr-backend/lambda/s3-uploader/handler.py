import json
import boto3
import base64
from datetime import datetime

s3_client = boto3.client('s3', region_name='us-west-2')

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json'
}

def lambda_handler(event, context):
    """
    Upload image to S3 (receives base64 from frontend)
    """
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    try:
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        
        image_base64 = body.get('imageBase64')
        file_name = body.get('fileName', 'image.jpg')
        
        if not image_base64:
            return error_response(400, 'imageBase64 is required')
        
        # Decode base64
        image_bytes = base64.b64decode(image_base64)
        
        # Generate S3 key
        timestamp = datetime.now().isoformat().replace(':', '-')
        key = f"uploads/{timestamp}_{file_name}"
        
        # Upload to S3
        s3_client.put_object(
            Bucket='alpr-raw-data-cmpe281',
            Key=key,
            Body=image_bytes,
            ContentType='image/jpeg'
        )
        
        # Generate S3 URL
        image_url = f"https://alpr-raw-data-cmpe281.s3.amazonaws.com/{key}"
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'imageUrl': image_url,
                'key': key,
                'message': 'Image uploaded successfully'
            }),
            'headers': CORS_HEADERS
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(500, str(e))

def error_response(status_code, message):
    return {
        'statusCode': status_code,
        'body': json.dumps({'error': message}),
        'headers': CORS_HEADERS
    }
