# API Gateway Configuration Summary

## Overview

This document describes the API Gateway configuration deployed by the CDK stack.

## API Structure

```
Floorspace API (REST API)
├── Cognito User Pool Authorizer
│   └── User Pool: floorspace-user-pool
│
└── Resources
    └── /projects
        ├── GET (List Projects)
        │   └── Lambda: floorspace-listProjects
        │
        └── /{projectId}
            ├── GET (Get Project)
            │   └── Lambda: floorspace-getProject
            │
            ├── POST (Create/Update Project)
            │   └── Lambda: floorspace-createUpdateProject
            │
            ├── DELETE (Delete Project)
            │   └── Lambda: floorspace-deleteProject
            │
            └── /upload
                └── POST (Upload Floorspace JSON)
                    └── Lambda: floorspace-uploadFloorspace
```

## Lambda Functions

### 1. floorspace-getProject
- **Handler**: `getProject.handler`
- **Runtime**: Node.js 18.x
- **Timeout**: 30 seconds
- **Environment Variables**:
  - `TABLE_NAME`: DynamoDB table name
  - `BUCKET_NAME`: S3 bucket name
- **Permissions**:
  - DynamoDB: GetItem
  - S3: GetObject (generates presigned URLs)
  - CloudWatch: PutLogEvents

### 2. floorspace-listProjects
- **Handler**: `listProjects.handler`
- **Runtime**: Node.js 18.x
- **Timeout**: 30 seconds
- **Environment Variables**:
  - `TABLE_NAME`: DynamoDB table name
- **Permissions**:
  - DynamoDB: Query
  - CloudWatch: PutLogEvents

### 3. floorspace-createUpdateProject
- **Handler**: `createUpdateProject.handler`
- **Runtime**: Node.js 18.x
- **Timeout**: 30 seconds
- **Environment Variables**:
  - `TABLE_NAME`: DynamoDB table name
  - `BUCKET_NAME`: S3 bucket name
- **Permissions**:
  - DynamoDB: PutItem
  - S3: PutObject
  - CloudWatch: PutLogEvents

### 4. floorspace-deleteProject
- **Handler**: `deleteProject.handler`
- **Runtime**: Node.js 18.x
- **Timeout**: 30 seconds
- **Environment Variables**:
  - `TABLE_NAME`: DynamoDB table name
  - `BUCKET_NAME`: S3 bucket name
- **Permissions**:
  - DynamoDB: GetItem, DeleteItem
  - S3: DeleteObject
  - CloudWatch: PutLogEvents

### 5. floorspace-uploadFloorspace
- **Handler**: `uploadFloorspace.handler`
- **Runtime**: Node.js 18.x
- **Timeout**: 30 seconds
- **Environment Variables**:
  - `TABLE_NAME`: DynamoDB table name
  - `BUCKET_NAME`: S3 bucket name
- **Permissions**:
  - DynamoDB: GetItem, UpdateItem
  - S3: PutObject
  - CloudWatch: PutLogEvents

## Authentication Flow

1. User registers/logs in via Cognito
2. Frontend receives JWT token (IdToken)
3. Frontend includes token in API requests: `Authorization: Bearer <token>`
4. API Gateway validates token with Cognito User Pool
5. If valid, API Gateway extracts `sub` (userId) from token claims
6. Lambda function receives userId in `event.requestContext.authorizer.claims.sub`
7. Lambda function verifies ownership before accessing resources

## CORS Configuration

The API Gateway is configured with CORS to allow:
- **Origins**: All origins (`*`) - Update in production
- **Methods**: GET, POST, DELETE, OPTIONS
- **Headers**: Content-Type, Authorization

## Error Responses

### 401 Unauthorized
Returned by API Gateway when:
- No Authorization header
- Invalid JWT token
- Expired JWT token

### 403 Forbidden
Returned by Lambda when:
- User doesn't own the requested resource

### 404 Not Found
Returned by Lambda when:
- Project doesn't exist

### 400 Bad Request
Returned by Lambda when:
- Invalid input data
- Missing required fields

### 500 Internal Server Error
Returned by Lambda when:
- Unexpected errors occur
- AWS service errors

## Request/Response Examples

### GET /projects
**Request:**
```http
GET /projects HTTP/1.1
Host: <api-id>.execute-api.<region>.amazonaws.com
Authorization: Bearer <jwt-token>
```

**Response (200):**
```json
{
  "projects": [
    {
      "projectId": "uuid",
      "name": "Project Name",
      "description": "Description",
      "createdAt": "2024-01-01T00:00:00.000Z",
      "updatedAt": "2024-01-01T00:00:00.000Z"
    }
  ]
}
```

### POST /projects/{projectId}
**Request:**
```http
POST /projects/my-project-id HTTP/1.1
Host: <api-id>.execute-api.<region>.amazonaws.com
Authorization: Bearer <jwt-token>
Content-Type: application/json

{
  "name": "My Project",
  "description": "Project description"
}
```

**Response (200):**
```json
{
  "projectId": "my-project-id",
  "name": "My Project",
  "description": "Project description",
  "createdAt": "2024-01-01T00:00:00.000Z",
  "updatedAt": "2024-01-01T00:00:00.000Z"
}
```

## Monitoring

### CloudWatch Logs
Each Lambda function logs to:
- `/aws/lambda/floorspace-getProject`
- `/aws/lambda/floorspace-listProjects`
- `/aws/lambda/floorspace-createUpdateProject`
- `/aws/lambda/floorspace-deleteProject`
- `/aws/lambda/floorspace-uploadFloorspace`

### API Gateway Logs
Access logs can be enabled in the API Gateway console.

### Metrics to Monitor
- Lambda invocation count
- Lambda error rate
- Lambda duration
- API Gateway 4xx/5xx errors
- API Gateway latency
- DynamoDB read/write capacity
- S3 request count

## Security Best Practices

1. **Token Validation**: All endpoints require valid Cognito JWT tokens
2. **Ownership Verification**: Lambda functions verify user owns resources
3. **Least Privilege**: IAM roles have minimal required permissions
4. **Encryption**: DynamoDB and S3 use encryption at rest
5. **Private S3**: All S3 objects are private, accessed via presigned URLs
6. **CORS**: Update allowed origins in production to specific domain

## Deployment Checklist

- [x] Cognito User Pool created
- [x] DynamoDB table created
- [x] S3 bucket created
- [x] Lambda functions deployed
- [x] API Gateway configured
- [x] Cognito authorizer attached
- [x] IAM roles configured
- [ ] Test all endpoints
- [ ] Update CORS for production domain
- [ ] Configure custom domain (optional)
- [ ] Set up CloudWatch alarms
- [ ] Configure frontend with API URL
