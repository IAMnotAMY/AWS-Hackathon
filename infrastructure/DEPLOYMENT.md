# Infrastructure Deployment Guide

## Overview

This infrastructure stack creates all the AWS resources needed for the Floorspace 3D Viewer application.

## Resources Created

### Authentication
- **Cognito User Pool**: `floorspace-user-pool`
  - Email-based authentication
  - Password requirements: 8+ characters, uppercase, lowercase, digits
  - Self sign-up enabled
  - Email verification enabled

### Data Storage
- **DynamoDB Table**: `floorspace-projects`
  - Partition Key: `userId` (STRING)
  - Sort Key: `projectId` (STRING)
  - Billing: Pay-per-request

- **S3 Bucket**: `floorspace-json-storage-{account-id}`
  - Private access only
  - S3-managed encryption
  - CORS enabled for frontend

### API
- **API Gateway**: REST API with Cognito authorization
  - CORS configured
  - Ready for Lambda integrations

### IAM
- **Lambda Execution Role**: With permissions for:
  - CloudWatch Logs
  - DynamoDB read/write
  - S3 read/write

## Prerequisites

1. AWS CLI configured with credentials
2. AWS CDK CLI installed: `npm install -g aws-cdk`
3. Node.js 18+ installed

## Deployment Commands

### First-time setup
```bash
cd infrastructure
npm install
cdk bootstrap
```

### Deploy the stack
```bash
cdk deploy
```

### View changes before deploying
```bash
cdk diff
```

### Destroy the stack
```bash
cdk destroy
```

## Stack Outputs

After deployment, the following values will be output:
- `UserPoolId`: Cognito User Pool ID
- `UserPoolClientId`: Cognito User Pool Client ID
- `ApiUrl`: API Gateway endpoint URL
- `BucketName`: S3 bucket name
- `TableName`: DynamoDB table name

These values should be used to configure the frontend application.

## Environment Variables

For local development, create a `.env` file in the frontend directory with:
```
VITE_USER_POOL_ID=<UserPoolId from stack output>
VITE_USER_POOL_CLIENT_ID=<UserPoolClientId from stack output>
VITE_API_URL=<ApiUrl from stack output>
VITE_REGION=<your-aws-region>
```

## Security Notes

- All S3 objects are private by default
- API Gateway requires valid Cognito JWT tokens
- Lambda functions have minimal IAM permissions
- DynamoDB uses encryption at rest
- CORS is configured - update `allowedOrigins` in production

## API Endpoints

The deployed API Gateway includes the following endpoints (all require Cognito authentication):

- `GET /projects` - List all user projects
- `GET /projects/{projectId}` - Get specific project details
- `POST /projects/{projectId}` - Create or update a project
- `DELETE /projects/{projectId}` - Delete a project
- `POST /projects/{projectId}/upload` - Upload floorspace JSON

## Complete Deployment Process

### Step 1: Build Backend Lambda Functions
```bash
cd backend
npm install
npm run build
```

This compiles TypeScript to JavaScript in `backend/dist/functions/`.

### Step 2: Deploy Infrastructure
```bash
cd ../infrastructure
npm install
cdk deploy
```

### Step 3: Save Output Values
After deployment, save the output values:
- UserPoolId
- UserPoolClientId
- ApiUrl
- BucketName
- TableName

### Step 4: Configure Frontend
Update `frontend/.env` with the output values:
```env
VITE_USER_POOL_ID=<UserPoolId>
VITE_USER_POOL_CLIENT_ID=<UserPoolClientId>
VITE_API_URL=<ApiUrl>
VITE_REGION=us-east-1
```

### Step 5: Test the API
See `test-api-endpoints.md` for testing instructions.

## Updating Lambda Functions

When you modify Lambda function code:

```bash
# Rebuild backend
cd backend
npm run build

# Redeploy infrastructure
cd ../infrastructure
cdk deploy
```

CDK will detect changes and update only the modified Lambda functions.

## Troubleshooting

### Build Errors
- Ensure TypeScript compiles: `cd backend && npm run build`
- Check for TypeScript errors: `cd backend && npx tsc --noEmit`

### Deployment Errors
- Verify AWS credentials: `aws sts get-caller-identity`
- Check CDK version: `cdk --version` (should be 2.x)
- Bootstrap if needed: `cdk bootstrap`

### Lambda Function Not Found
- Ensure `backend/dist/functions/` contains .js files
- Rebuild: `cd backend && npm run build`

### API Gateway 401 Errors
- Verify Cognito token is valid
- Check Authorization header format: `Bearer <token>`
- Ensure user is registered in Cognito

### API Gateway 403 Errors
- User doesn't own the requested resource
- Verify userId in token matches project owner

## Next Steps

After successful deployment:
1. ✅ Infrastructure deployed
2. ✅ Lambda functions deployed
3. ✅ API Gateway configured with Cognito authorizer
4. Configure frontend with output values
5. Test API endpoints (see `test-api-endpoints.md`)
6. Implement frontend dashboard (Task 6)
