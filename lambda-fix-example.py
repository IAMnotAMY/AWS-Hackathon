import json

def lambda_handler(event, context):
    # Access query string parameters correctly
    query_params = event.get('queryStringParameters', {})
    username = query_params.get('username') if query_params else None
    
    print(f"Username from query: {username}")
    
    # Access request body if it's a POST request
    body = {}
    if event.get('body'):
        body = json.loads(event['body'])
    
    # Access headers
    headers = event.get('headers', {})
    
    # Access path parameters
    path_params = event.get('pathParameters', {})
    
    # Access request context (for Cognito user info)
    request_context = event.get('requestContext', {})
    authorizer = request_context.get('authorizer', {})
    claims = authorizer.get('claims', {})
    
    # Get user ID from Cognito token
    user_id = claims.get('sub')
    cognito_username = claims.get('cognito:username')
    email = claims.get('email')
    
    print(f"User ID: {user_id}")
    print(f"Cognito Username: {cognito_username}")
    print(f"Email: {email}")
    
    # Your logic here
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'message': 'Success',
            'username': username,
            'userId': user_id
        })
    }
