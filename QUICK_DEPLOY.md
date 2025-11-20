# Quick Deployment Guide

## Deploy Everything in 3 Steps

### 1. Build Backend
```bash
cd backend
npm install
npm run build
```

### 2. Deploy to AWS
```bash
cd ../infrastructure
npm install
cdk deploy
```

### 3. Save the Output
After deployment, you'll see output like:
```
Outputs:
FloorspaceInfrastructureStack.UserPoolId = us-east-1_XXXXXXX
FloorspaceInfrastructureStack.UserPoolClientId = XXXXXXXXXXXXXXXXXXXXXXXXXX
FloorspaceInfrastructureStack.ApiUrl = https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/
FloorspaceInfrastructureStack.BucketName = floorspace-json-storage-XXXXXXXXXXXX
FloorspaceInfrastructureStack.TableName = floorspace-projects
```

## What Gets Deployed

✅ **Cognito User Pool** - User authentication
✅ **DynamoDB Table** - Project metadata storage
✅ **S3 Bucket** - Floorspace JSON file storage
✅ **5 Lambda Functions** - API backend logic
✅ **API Gateway** - REST API with 5 endpoints
✅ **IAM Roles** - Secure permissions

## API Endpoints (All require authentication)

- `GET /projects` - List your projects
- `GET /projects/{id}` - Get project details
- `POST /projects/{id}` - Create/update project
- `DELETE /projects/{id}` - Delete project
- `POST /projects/{id}/upload` - Upload floorspace JSON

## View in AWS Console

After deployment, check:
- **API Gateway** → "Floorspace API"
- **Lambda** → 5 functions starting with "floorspace-"
- **Cognito** → "floorspace-user-pool"
- **DynamoDB** → "floorspace-projects" table
- **S3** → "floorspace-json-storage-*" bucket

## Next Steps

1. Configure frontend with the output values (see `frontend/.env.example`)
2. Test the API (see `infrastructure/test-api-endpoints.md`)
3. Register a user through the frontend
4. Start building the dashboard (Task 6)

## Update Deployment

When you change Lambda code:
```bash
cd backend && npm run build
cd ../infrastructure && cdk deploy
```

## Destroy Everything

```bash
cd infrastructure
cdk destroy
```

⚠️ **Warning**: This deletes all data!

## Need Help?

- Full deployment guide: `infrastructure/DEPLOYMENT.md`
- API testing guide: `infrastructure/test-api-endpoints.md`
- API configuration: `infrastructure/API_CONFIGURATION.md`
