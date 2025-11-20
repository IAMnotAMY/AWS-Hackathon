# CORS Troubleshooting Guide

## Current Issue
Projects API is failing with CORS errors.

## Root Causes & Solutions

### 1. **Lambda Not Returning CORS Headers**

**Problem:** Your Python Lambda might not be returning CORS headers in all responses.

**Solution:** Ensure EVERY response includes CORS headers:

```python
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
}

# In EVERY return statement:
return {
    'statusCode': 200,
    'headers': CORS_HEADERS,  # ← Must be in EVERY response
    'body': json.dumps({...})
}
```

### 2. **API Gateway Not Deployed**

**Problem:** You updated the CDK infrastructure but didn't redeploy.

**Solution:**
```bash
cd infrastructure
cdk deploy
```

### 3. **API Gateway CORS Not Matching Lambda**

**Problem:** API Gateway and Lambda return different CORS headers.

**Solution:** Both must return the same headers. Your CDK already has:
```typescript
allowHeaders: [
  'Content-Type',
  'X-Amz-Date',
  'Authorization',
  'X-Api-Key',
  'X-Amz-Security-Token',
]
```

Make sure your Python Lambda has the exact same headers.

### 4. **OPTIONS Method Not Configured**

**Problem:** Browser sends OPTIONS preflight, but Lambda doesn't handle it.

**Solution:** Handle OPTIONS FIRST in your Lambda:
```python
if event.get('httpMethod') == 'OPTIONS':
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': ''
    }
```

### 5. **Cognito Authorizer Blocking OPTIONS**

**Problem:** API Gateway Cognito authorizer might be blocking OPTIONS requests.

**Solution:** In your CDK, OPTIONS should NOT require authorization. Check if you need to add:
```typescript
// OPTIONS should not require auth
const optionsIntegration = new apigateway.MockIntegration({
  integrationResponses: [{
    statusCode: '200',
    responseParameters: {
      'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
      'method.response.header.Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
      'method.response.header.Access-Control-Allow-Origin': "'*'"
    }
  }],
  requestTemplates: {
    'application/json': '{"statusCode": 200}'
  }
});
```

## Quick Diagnostic Steps

### Step 1: Check Browser Console
Open browser DevTools → Network tab → Look for the failing request:
- Is it an OPTIONS request? → Lambda needs to handle OPTIONS
- Is it a GET/POST request? → Lambda needs CORS headers in response
- What's the exact error message?

### Step 2: Check Response Headers
In Network tab, click the failed request → Headers tab:
- Does the response have `Access-Control-Allow-Origin`?
- Does it have all the required headers?

### Step 3: Test with curl
```bash
# Test OPTIONS
curl -X OPTIONS https://your-api-url/projects \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization" \
  -v

# Test GET
curl -X GET https://your-api-url/projects \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Origin: http://localhost:5173" \
  -v
```

Look for `Access-Control-Allow-*` headers in the response.

### Step 4: Check CloudWatch Logs
1. Go to AWS Console → CloudWatch → Log Groups
2. Find your Lambda function logs
3. Check if the Lambda is even being invoked
4. Look for any errors

## Common Error Messages & Fixes

### "No 'Access-Control-Allow-Origin' header is present"
**Fix:** Lambda is not returning CORS headers. Add them to ALL responses.

### "CORS policy: Response to preflight request doesn't pass"
**Fix:** OPTIONS request is not being handled correctly. Handle OPTIONS first in Lambda.

### "The 'Access-Control-Allow-Origin' header contains multiple values"
**Fix:** Both API Gateway and Lambda are adding CORS headers. Remove from one (keep in Lambda).

### "Request header field authorization is not allowed"
**Fix:** Add 'Authorization' to Access-Control-Allow-Headers.

## Recommended Fix for Your Setup

Since you're using Python Lambda with API Gateway:

1. **Update your Python Lambda** to include CORS headers in EVERY response (see `backend/python-lambda-cors-example.py`)

2. **Redeploy your Lambda** to AWS

3. **Verify API Gateway CORS** is configured (already done in your CDK)

4. **Test** with browser DevTools to confirm headers are present

## Alternative: Use API Gateway CORS Only

If you want API Gateway to handle CORS completely:

1. Remove CORS headers from your Python Lambda
2. In CDK, use `defaultCorsPreflightOptions` (already configured)
3. API Gateway will automatically add CORS headers to all responses

However, this requires API Gateway to be properly configured, which can be tricky with Cognito authorizers.

## Need More Help?

Share:
1. The exact error message from browser console
2. The response headers from Network tab
3. Your Python Lambda code
4. Whether you've redeployed after CDK changes
