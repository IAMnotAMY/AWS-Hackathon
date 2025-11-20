# Deployment Guide for Floorspace 3D Viewer

## Prerequisites

1. AWS CLI configured with credentials
2. AWS CDK CLI installed (`npm install -g aws-cdk`)
3. Node.js 18+ installed

## Deployment Steps

### 1. Build Backend Lambda Functions

```bash
cd backend
npm install
npm run build
```

This compiles TypeScript to JavaScript in the `backend/dist` directory.

### 2. Install Infrastructure Dependencies

```bash
cd ../infrastructure
npm install
```

### 3. Bootstrap CDK (First Time Only)

If this is your first time using CDK in your AWS account/region:

```bash
cdk bootstrap
```

### 4. Deploy the Stack

```bash
cdk deploy
```

You'll be prompted to approve IAM changes. Type `y` to proceed.

### 5. Note the Outputs

After deployment, CDK will output important values:

- **UserPoolId**: Cognito User Pool ID
- **UserPoolClientId**: Cognito Client ID
- **ApiUrl**: API Gateway endpoint URL
- **BucketName**: S3 bucket name
- **TableName**: DynamoDB table name

Save these values - you'll need them to configure the frontend.

## API Endpoints

After deployment, your API will be available at the `ApiUrl` with these endpoints:

- `GET /projects` - List all user projects
- `GET /projects/{projectId}` - Get specific project
- `POST /projects/{projectId}` - Create or update project
- `DELETE /projects/{projectId}` - Delete project
- `POST /projects/{projectId}/upload` - Upload floorspace JSON

All endpoints require a valid Cognito JWT token in the `Authorization` header.

## Testing the API

### 1. Register a User

Use the frontend or AWS Cognito console to create a test user.

### 2. Get an Auth Token

Sign in through the frontend or use AWS Amplify CLI to get a JWT token.

### 3. Test with curl

```bash
# Replace with your actual values
API_URL="https://your-api-id.execute-api.region.amazonaws.com/prod"
TOKEN="your-jwt-token"

# List projects
curl -X GET "$API_URL/projects" \
  -H "Authorization: Bearer $TOKEN"

# Create a project
curl -X POST "$API_URL/projects/test-project-123" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"My Test Project","description":"Testing the API"}'
```

## Updating the Deployment

When you make changes to Lambda functions:

```bash
# Rebuild backend
cd backend
npm run build

# Redeploy
cd ../infrastructure
cdk deploy
```

## Destroying the Stack

To remove all resources:

```bash
cd infrastructure
cdk destroy
```

**Warning**: This will delete all data in DynamoDB and S3!

## Troubleshooting

### Lambda Function Not Found

Ensure you've built the backend:
```bash
cd backend
npm run build
```

### Permission Errors

Check that your AWS credentials have sufficient permissions to create:
- Lambda functions
- API Gateway
- DynamoDB tables
- S3 buckets
- Cognito User Pools
- IAM roles

### API Gateway 403 Errors

Ensure you're including a valid JWT token in the Authorization header.

## Environment Variables

The Lambda functions use these environment variables (automatically set by CDK):

- `TABLE_NAME`: DynamoDB table name
- `BUCKET_NAME`: S3 bucket name

## Monitoring

After deployment, you can monitor your application:

- **CloudWatch Logs**: Lambda function logs
- **API Gateway Dashboard**: Request metrics
- **DynamoDB Metrics**: Table performance
- **S3 Metrics**: Storage usage

## Next Steps

1. Configure the frontend with the output values
2. Set up custom domain (optional)
3. Configure CloudWatch alarms
4. Set up CI/CD pipeline
