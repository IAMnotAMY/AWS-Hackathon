# Floorspace 3D Viewer - Infrastructure

This directory contains the AWS CDK infrastructure code for the Floorspace 3D Viewer application.

## Architecture

The infrastructure implements a serverless architecture using AWS services:

```
Frontend (React) → API Gateway → Lambda Functions → DynamoDB + S3
                        ↓
                   Cognito (Auth)
```

## Components

### 1. Authentication (Cognito)
- **User Pool**: Manages user registration and authentication
- **User Pool Client**: Enables frontend authentication flows
- **Features**:
  - Email-based sign-in
  - Password policy enforcement (8+ chars, mixed case, digits)
  - Email verification
  - Account recovery via email

### 2. Data Storage

#### DynamoDB Table: `floorspace-projects`
- **Purpose**: Store project metadata
- **Schema**:
  - `userId` (Partition Key): Cognito user ID
  - `projectId` (Sort Key): Unique project identifier
  - Additional attributes: name, description, createdAt, updatedAt, s3Key
- **Billing**: Pay-per-request (auto-scaling)

#### S3 Bucket: `floorspace-json-storage-{account}`
- **Purpose**: Store floorspace JSON files
- **Key Structure**: `{userId}/{projectId}/floorspace.json`
- **Security**:
  - Block all public access
  - S3-managed encryption
  - Access via presigned URLs only
- **CORS**: Configured for frontend access

### 3. API Gateway
- **Type**: REST API
- **Authorization**: Cognito User Pools Authorizer
- **CORS**: Enabled for all origins (configure for production)
- **Endpoints**: Ready for Lambda integration (implemented in Task 4-5)

### 4. IAM Roles
- **Lambda Execution Role**: Grants Lambda functions permission to:
  - Write logs to CloudWatch
  - Read/write DynamoDB table
  - Read/write S3 bucket

## Stack Outputs

The stack exports the following values for use by other components:

| Output | Description | Usage |
|--------|-------------|-------|
| `UserPoolId` | Cognito User Pool ID | Frontend authentication config |
| `UserPoolClientId` | Cognito Client ID | Frontend authentication config |
| `ApiUrl` | API Gateway endpoint | Frontend API calls |
| `BucketName` | S3 bucket name | Lambda functions |
| `TableName` | DynamoDB table name | Lambda functions |
| `LambdaRoleArn` | Lambda execution role ARN | Lambda function deployment |
| `AuthorizerId` | API Gateway authorizer ID | API endpoint configuration |

## Requirements Validation

This infrastructure satisfies the following requirements:

- ✅ **Requirement 1.1**: Cognito user registration
- ✅ **Requirement 2.1**: Cognito authentication
- ✅ **Requirement 3.1**: DynamoDB for project storage
- ✅ **Requirements 8.1-8.5**: API Gateway for Lambda functions
- ✅ **Requirements 9.1-9.4**: Cognito authorization on API
- ✅ **Requirements 10.1-10.4**: S3 storage with proper organization

## Development Workflow

1. **Make changes** to `lib/infrastructure-stack.ts`
2. **Build**: `npm run build`
3. **Review changes**: `npm run diff`
4. **Deploy**: `npm run deploy`

## Testing

Run infrastructure tests:
```bash
npm test
```

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions.

## Security Considerations

- All resources use least-privilege IAM policies
- S3 bucket blocks all public access
- DynamoDB encryption at rest enabled by default
- API Gateway requires valid Cognito tokens
- CORS should be restricted to frontend domain in production

## Cost Optimization

- DynamoDB uses on-demand billing (pay only for what you use)
- Lambda functions are serverless (pay per invocation)
- S3 charges based on storage and requests
- Cognito has a free tier for up to 50,000 MAUs

## Next Steps

1. Deploy this infrastructure stack
2. Implement Lambda functions (Task 4)
3. Integrate Lambda functions with API Gateway (Task 5)
4. Configure frontend with stack outputs
