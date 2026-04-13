import json
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('GateEvents')

def lambda_handler(event, context):
    """
    Retrieve recent gate events
    """
    try:
        # Get limit from query parameters (default 50)
        query_params = event.get('queryStringParameters') or {}
        limit = int(query_params.get('limit', 50))
        
        # Validate limit
        if limit < 1 or limit > 1000:
            limit = 50
        
        # Scan table to get events
        response = table.scan(
            Limit=limit
        )
        
        # Convert items and format response
        items = response.get('Items', [])
        events = []
        
        for item in items:
            events.append({
                'timestamp': int(item.get('timestamp', 0)),
                'vehicleId': item.get('vehicle_id'),
                'plateText': item.get('plate_text'),
                'confidence': float(item.get('confidence', 0)),
                'permitStatus': item.get('permit_status'),
                'eventType': item.get('event_type'),
                'imageUrl': item.get('image_url')
            })
        
        # Sort by timestamp descending (most recent first)
        events.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {
            'statusCode': 200,
            'body': json.dumps(events),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        
    except ValueError:
        return error_response(400, 'Invalid limit parameter')
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
