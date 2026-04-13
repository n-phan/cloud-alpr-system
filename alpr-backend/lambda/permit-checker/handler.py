import json
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
        
        vehicle_id = query_params.get('vehicleId')
        if not vehicle_id:
            return error_response(400, 'vehicleId parameter required')
        
        # Query DynamoDB
        response = table.get_item(
            Key={'vehicle_id': vehicle_id}
        )
        
        # Check if item exists
        if 'Item' not in response:
            return error_response(404, f'Vehicle {vehicle_id} not found')
        
        item = response['Item']
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'vehicleId': item.get('vehicle_id'),
                'owner': item.get('owner'),
                'permitStatus': item.get('permit_status'),
                'expiryDate': item.get('expiry_date')
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        
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
