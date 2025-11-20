# Floorspace 3D Viewer

A web application for creating, managing, and visualizing 2D floorplans using the NREL floorspace.js library with 3D model conversion capabilities.

## Project Structure

```
.
├── frontend/           # React frontend application
├── backend/            # Lambda functions for API
├── infrastructure/     # AWS CDK infrastructure code
└── .kiro/             # Kiro specs and documentation
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- AWS CLI configured with appropriate credentials
- AWS CDK CLI (`npm install -g aws-cdk`)

### Installation

1. Install frontend dependencies:
```bash
cd frontend
npm install
```

2. Install backend dependencies:
```bash
cd backend
npm install
```

3. Install infrastructure dependencies:
```bash
cd infrastructure
npm install
```

### Development

#### Frontend Development
```bash
cd frontend
npm run dev
```

#### Infrastructure Deployment
```bash
cd infrastructure
npm run build
cdk synth
cdk deploy
```

### Testing

#### Frontend Tests
```bash
cd frontend
npm test
```

#### Backend Tests
```bash
cd backend
npm test
```

## Architecture

The application uses a serverless architecture on AWS:
- **Frontend**: React with TypeScript, hosted on S3/CloudFront
- **Authentication**: AWS Cognito User Pools
- **API**: AWS API Gateway with Lambda functions
- **Database**: DynamoDB for project metadata
- **Storage**: S3 for floorspace JSON files

## Documentation

See `.kiro/specs/floorspace-3d-viewer/` for detailed requirements, design, and implementation tasks.
