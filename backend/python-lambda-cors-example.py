"""
Example Python Lambda with proper CORS handling
This shows the correct pattern for handling CORS in Python Lambda functions
"""

import json
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# CORS headers that must be included in EVERY response
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
}

def lambda_handler(event, context):
    """
    Main Lambda handler with CORS support
    """
    
    # IMPORTANT: Handle OPTIONS preflight request FIRST
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': ''
        }
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('3d-Viewer-UserDetails')
    
    try:
        # Parse input from event
        body = json.loads(event.get('body', '{}'))
        user = body.get('user')
        
        # Validate required input
        if not user:
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,  # CORS headers in error response
                'body': json.dumps({
                    'error': 'Missing required field: user'
                })
            }
        
        # Query DynamoDB
        response = table.query(
            KeyConditionExpression=Key('user').eq(user),
            Limit=100
        )
        
        # SUCCESS: Return with CORS headers
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,  # CORS headers in success response
            'body': json.dumps({
                'projects': response['Items'],
                'count': len(response['Items'])
            })
        }
        
    except ClientError as e:
        # ERROR: Return with CORS headers
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,  # CORS headers in error response
            'body': json.dumps({
                'error': str(e)
            })
        }
    except Exception as e:
        # UNEXPECTED ERROR: Return with CORS headers
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,  # CORS headers in error response
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }


# CHECKLIST for CORS in Python Lambda:
# ✅ 1. Define CORS_HEADERS constant at the top
# ✅ 2. Handle OPTIONS request FIRST (before any other logic)
# ✅ 3. Include CORS_HEADERS in ALL success responses (200, 201, etc.)
# ✅ 4. Include CORS_HEADERS in ALL error responses (400, 403, 404, 500, etc.)
# ✅ 5. Include CORS_HEADERS in ALL exception handlers
# ✅ 6. Make sure API Gateway has CORS enabled (already done in your CDK)

"""
Common CORS mistakes to avoid:

❌ WRONG: Only returning CORS headers in OPTIONS
❌ WRONG: Forgetting CORS headers in error responses
❌ WRONG: Different headers in Lambda vs API Gateway
❌ WRONG: Not handling OPTIONS method

✅ CORRECT: CORS headers in EVERY response
✅ CORRECT: Handle OPTIONS first
✅ CORRECT: Same headers everywhere
"""
