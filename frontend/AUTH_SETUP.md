# Authentication Setup Guide

## Current Status

The authentication UI components are fully implemented and functional. However, to enable actual authentication, you need to deploy the AWS infrastructure first.

## What's Working Now (Without Infrastructure)

✅ **UI Components:**
- Registration page with validation
- Login page with error handling
- Protected routes
- Authentication context
- Form validation (email format, password strength)

✅ **Property-Based Tests:**
- 12 passing tests validating authentication logic
- 100+ test iterations per property

## What Needs AWS Infrastructure

❌ **Actual Authentication:**
- User registration (requires Cognito User Pool)
- User login (requires Cognito User Pool)
- Session management (requires Cognito tokens)
- Protected route access (requires valid JWT tokens)

## Setup Instructions

### Step 1: Deploy Infrastructure

```bash
cd infrastructure
npm install
npm run deploy
```

This will create:
- Cognito User Pool for authentication
- DynamoDB table for project metadata
- S3 bucket for floorspace JSON storage
- API Gateway with Lambda functions

### Step 2: Configure Frontend

After deployment, CDK will output the following values:

```
Outputs:
FloorspaceInfrastructureStack.UserPoolId = us-east-1_XXXXXXXXX
FloorspaceInfrastructureStack.UserPoolClientId = XXXXXXXXXXXXXXXXXXXXXXXXXX
```

Copy these values:

1. Copy `frontend/.env.example` to `frontend/.env`
2. Update the values:

```env
VITE_USER_POOL_ID=us-east-1_XXXXXXXXX
VITE_USER_POOL_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
VITE_AWS_REGION=us-east-1
```

### Step 3: Restart Dev Server

```bash
cd frontend
npm run dev
```

## Testing the Authentication Flow

Once configured, you can test:

1. **Registration:**
   - Go to http://localhost:3000/register
   - Enter email and password
   - Receive verification email
   - Verify account

2. **Login:**
   - Go to http://localhost:3000/login
   - Enter credentials
   - Get redirected to dashboard

3. **Protected Routes:**
   - Try accessing /dashboard without login
   - Should redirect to /login
   - After login, can access /dashboard

## Development Mode

When running without infrastructure, you'll see a yellow banner explaining that Cognito is not configured. The UI will still render and you can test the form validation, but actual authentication calls will fail gracefully.

## Architecture

```
Frontend (React + Amplify)
    ↓
AWS Cognito User Pool
    ↓
JWT Token Storage (localStorage)
    ↓
Protected Routes (AuthContext)
    ↓
API Gateway (with Cognito Authorizer)
```

## Next Steps

After authentication is working:
- Implement project dashboard (Task 6)
- Implement Lambda functions for API (Task 4)
- Connect frontend to API endpoints
- Implement floorspace editor (Task 7)
