import json
import boto3
import time
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('GateEvents')

def lambda_handler(event, context):
    """
    Submit a plate detection result to the gate events log
    """
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Validate required fields
        required_fields = ['vehicleId', 'plateText', 'confidence', 'permitStatus', 'eventType']
        for field in required_fields:
            if field not in body:
                return error_response(400, f'Missing required field: {field}')
        
        # Generate timestamp (milliseconds)
        timestamp = int(time.time() * 1000)
        ttl = int(time.time()) + (30 * 86400)  # 30 days from now
        
        # Prepare item for DynamoDB (use Decimal for numbers)
        item = {
            'timestamp': timestamp,
            'vehicle_id': body['vehicleId'],
            'plate_text': body['plateText'],
            'confidence': Decimal(str(body['confidence'])),  # Convert to Decimal
            'permit_status': body['permitStatus'],
            'event_type': body['eventType'],
            'ttl': ttl
        }
        
        # Add optional image URL if provided
        if 'imageUrl' in body:
            item['image_url'] = body['imageUrl']
        
        # Insert into DynamoDB
        table.put_item(Item=item)
        
        return {
            'statusCode': 201,
            'body': json.dumps({
                'message': 'Event recorded',
                'timestamp': timestamp
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        
    except ValueError:
        return error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(500, 'Internal server error')

def error_response(status_code, message):
    return {
        'statusCode': status_code,
        'body': json.dumps({'error': message}),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    }
