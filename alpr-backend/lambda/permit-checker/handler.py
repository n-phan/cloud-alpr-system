import json
from datetime import datetime, timezone

import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('Permits')

def lambda_handler(event, context):
    """
    Check permit status for a vehicle
    """
    try:
        # Get vehicleId from query parameters
        query_params = event.get('queryStringParameters') or {}
        
        vehicle_id = (query_params.get('vehicleId') or '').strip().upper()
        if not vehicle_id:
            return error_response(400, 'vehicleId parameter required')
        
        # Query DynamoDB
        response = table.get_item(
            Key={'vehicle_id': vehicle_id}
        )
        
        # Missing permit is treated as invalid.
        if 'Item' not in response:
            return permit_response(vehicle_id=vehicle_id, owner=None, permit_status='INVALID', expiry_date=None)
        
        item = response['Item']
        permit_status = str(item.get('permit_status') or '').upper() or 'INVALID'
        expiry_date_raw = item.get('expiry_date')

        if _is_expired(expiry_date_raw):
            permit_status = 'INVALID'
            table.update_item(
                Key={'vehicle_id': item.get('vehicle_id')},
                UpdateExpression='SET permit_status = :ps, updated_at = :ua',
                ExpressionAttributeValues={
                    ':ps': 'INVALID',
                    ':ua': int(datetime.now(timezone.utc).timestamp() * 1000),
                },
            )
        
        return permit_response(
            vehicle_id=item.get('vehicle_id'),
            owner=item.get('owner'),
            permit_status=permit_status,
            expiry_date=expiry_date_raw,
        )
        
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


def permit_response(vehicle_id, owner, permit_status, expiry_date):
    return {
        'statusCode': 200,
        'body': json.dumps({
            'vehicleId': vehicle_id,
            'owner': owner,
            'permitStatus': permit_status,
            'expiryDate': expiry_date,
        }),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
        },
    }


def _is_expired(expiry_date):
    if not expiry_date:
        return False

    raw = str(expiry_date).strip()
    now = datetime.now(timezone.utc)

    # Common admin format: YYYY-MM-DD (treated as end-of-day UTC).
    try:
        date_only = datetime.strptime(raw, '%Y-%m-%d')
        expires_at = date_only.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        return expires_at < now
    except ValueError:
        pass

    # ISO-8601 date/time support.
    try:
        normalized = raw.replace('Z', '+00:00')
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt < now
    except ValueError:
        # If value is unparsable, keep current status instead of forcing invalid.
        return False
