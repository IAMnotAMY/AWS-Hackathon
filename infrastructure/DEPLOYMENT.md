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

## Next Steps

After deploying the infrastructure:
1. Note the stack outputs
2. Configure frontend with the output values
3. Implement Lambda functions (Task 4)
4. Deploy Lambda functions and integrate with API Gateway (Task 5)
