# API Endpoints Testing Guide

## After Deployment

Once you run `cdk deploy`, you'll get an API URL. Use these examples to test each endpoint.

### Setup

```bash
# Save your values
export API_URL="<your-api-gateway-url>"
export TOKEN="<your-cognito-jwt-token>"
```

### 1. List Projects
```bash
curl -X GET "$API_URL/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response (200):**
```json
{
  "projects": []
}
```

### 2. Create a Project
```bash
curl -X POST "$API_URL/projects/project-123" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Project",
    "description": "Testing the API"
  }'
```

**Expected Response (200):**
```json
{
  "projectId": "project-123",
  "name": "My First Project",
  "description": "Testing the API",
  "createdAt": "2024-01-01T00:00:00.000Z",
  "updatedAt": "2024-01-01T00:00:00.000Z"
}
```

### 3. Get Project Details
```bash
curl -X GET "$API_URL/projects/project-123" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response (200):**
```json
{
  "projectId": "project-123",
  "name": "My First Project",
  "description": "Testing the API",
  "createdAt": "2024-01-01T00:00:00.000Z",
  "updatedAt": "2024-01-01T00:00:00.000Z",
  "floorspaceUrl": "https://s3.amazonaws.com/..."
}
```

### 4. Upload Floorspace JSON
```bash
curl -X POST "$API_URL/projects/project-123/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "floorspaceJson": {
      "version": "1.0",
      "stories": [],
      "building_units": []
    }
  }'
```

**Expected Response (200):**
```json
{
  "success": true,
  "updatedAt": "2024-01-01T00:00:00.000Z"
}
```

### 5. Delete Project
```bash
curl -X DELETE "$API_URL/projects/project-123" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response (200):**
```json
{
  "success": true
}
```

## Testing Authentication

### Test Invalid Token (Should return 401)
```bash
curl -X GET "$API_URL/projects" \
  -H "Authorization: Bearer invalid-token" \
  -H "Content-Type: application/json"
```

**Expected Response (401):**
```json
{
  "message": "Unauthorized"
}
```

### Test Missing Token (Should return 401)
```bash
curl -X GET "$API_URL/projects" \
  -H "Content-Type: application/json"
```

**Expected Response (401):**
```json
{
  "message": "Unauthorized"
}
```

## Testing Ownership

### Test Accessing Another User's Project (Should return 403)

1. Create a project with User A
2. Try to access it with User B's token

```bash
curl -X GET "$API_URL/projects/user-a-project" \
  -H "Authorization: Bearer $USER_B_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response (403):**
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "You don't have permission to access this resource"
  }
}
```

## Using Postman

1. Import these endpoints into Postman
2. Set up an environment variable for `API_URL` and `TOKEN`
3. Add `Authorization: Bearer {{TOKEN}}` to headers
4. Test each endpoint

## Getting a JWT Token

### Option 1: Use the Frontend
1. Register/login through your React app
2. Open browser DevTools → Application → Local Storage
3. Copy the token value

### Option 2: Use AWS Amplify CLI
```bash
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id <your-client-id> \
  --auth-parameters USERNAME=<email>,PASSWORD=<password>
```

The response will include an `IdToken` - use this as your Bearer token.
