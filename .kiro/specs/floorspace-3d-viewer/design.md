# Design Document

## Overview

The Floorspace 3D Viewer is a serverless web application built on AWS infrastructure that provides user authentication, project management, and integration with the NREL floorspace.js library for 2D floorplan editing. The system follows a three-tier architecture with a React-based frontend, AWS API Gateway and Lambda for the backend, and AWS services (Cognito, DynamoDB, S3) for authentication and data persistence.

The application enables users to:
- Register and authenticate securely
- Create and manage multiple floorplan projects
- Edit floorplans using the embedded floorspace.js editor
- Store floorspace JSON data persistently
- View projects in a 3D viewer (placeholder for future implementation)

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Login/  │  │ Project  │  │Floorspace│  │   3D     │   │
│  │ Register │  │Dashboard │  │  Editor  │  │  Viewer  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                     AWS Cognito (Auth)                       │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway (REST)                      │
│  /projects/{projectId}         - GET, POST, DELETE          │
│  /projects/{projectId}/upload  - POST                       │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐
│  Lambda:         │  │  Lambda:         │  │  Lambda:     │
│  GetProject      │  │  CreateProject   │  │  Upload      │
│  DeleteProject   │  │  UpdateProject   │  │  Floorspace  │
└──────────────────┘  └──────────────────┘  └──────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                         DynamoDB                             │
│              Table: Projects (userId, projectId)             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                            S3                                │
│         Bucket: floorspace-json-storage                      │
│         Key: {userId}/{projectId}/floorspace.json            │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Frontend:**
- React 18+ for UI components
- React Router for navigation
- AWS Amplify SDK for Cognito integration
- Axios for API calls
- CSS Modules or Tailwind CSS for styling

**Backend:**
- AWS API Gateway (REST API)
- AWS Lambda (Node.js 18+ runtime)
- AWS SDK for JavaScript v3

**Data & Auth:**
- AWS Cognito User Pools for authentication
- AWS DynamoDB for project metadata
- AWS S3 for floorspace JSON storage

**External:**
- NREL floorspace.js (embedded via iframe)

## Components and Interfaces

### Frontend Components

#### 1. Authentication Components

**RegisterPage**
- Purpose: User registration interface
- Props: None
- State: email, password, confirmPassword, errors
- Methods:
  - `handleRegister()`: Calls Cognito signUp API
  - `validateInput()`: Validates email format and password strength
- Navigation: Redirects to login on success

**LoginPage**
- Purpose: User authentication interface
- Props: None
- State: email, password, errors
- Methods:
  - `handleLogin()`: Calls Cognito signIn API
  - `storeAuthToken()`: Stores JWT token in localStorage
- Navigation: Redirects to dashboard on success

#### 2. Project Management Components

**ProjectDashboard**
- Purpose: Display list of user projects
- Props: None
- State: projects[], loading, error
- Methods:
  - `fetchProjects()`: GET request to API for user's projects
  - `handleCreateProject()`: Opens create project modal
  - `handleDeleteProject(projectId)`: DELETE request to API
  - `handleProjectClick(projectId)`: Navigate to editor
- API Calls: GET /projects (list all user projects)

**CreateProjectModal**
- Purpose: Form to create new project
- Props: isOpen, onClose, onSuccess
- State: projectName, description, errors
- Methods:
  - `handleSubmit()`: POST request to create project
  - `validateForm()`: Validates project name is not empty
- API Calls: POST /projects/{projectId}

**ProjectCard**
- Purpose: Display individual project information
- Props: project (id, name, createdAt, updatedAt)
- Methods:
  - `handleClick()`: Navigate to editor
  - `handleDelete()`: Trigger delete confirmation

#### 3. Editor Components

**FloorspaceEditorPage**
- Purpose: Host floorspace.js editor in iframe
- Props: projectId (from route params)
- State: floorspaceData, loading, saveStatus
- Methods:
  - `loadFloorspaceData()`: Fetch JSON from S3 via API
  - `handleSave()`: POST floorspace JSON to upload endpoint
  - `setupIframeMessaging()`: Configure postMessage communication
- API Calls: 
  - GET /projects/{projectId} (get S3 URL)
  - POST /projects/{projectId}/upload
- Integration: Uses postMessage API to communicate with iframe

**EditorToolbar**
- Purpose: Provide save, back, and 3D view navigation
- Props: onSave, projectId
- Methods:
  - `handleSaveClick()`: Trigger parent save
  - `handleBackClick()`: Navigate to dashboard
  - `handle3DViewClick()`: Navigate to 3D viewer

#### 4. 3D Viewer Components

**ThreeDViewerPage**
- Purpose: Display 3D model (placeholder)
- Props: projectId (from route params)
- State: floorspaceData, loading
- Methods:
  - `loadFloorspaceData()`: Fetch JSON from S3 via API
  - `renderPlaceholder()`: Display "Coming Soon" message
- API Calls: GET /projects/{projectId}

### Backend Components

#### API Gateway Configuration

**Endpoints:**

1. `GET /projects` - List all projects for authenticated user
2. `GET /projects/{projectId}` - Get specific project details
3. `POST /projects/{projectId}` - Create or update project
4. `DELETE /projects/{projectId}` - Delete project
5. `POST /projects/{projectId}/upload` - Upload floorspace JSON

**Authorization:**
- Cognito User Pool Authorizer attached to all endpoints
- Validates JWT token in Authorization header
- Extracts userId from token claims

#### Lambda Functions

**1. GetProjectFunction**
- Trigger: GET /projects/{projectId}
- Purpose: Retrieve project metadata and generate S3 presigned URL
- Input: projectId (path param), userId (from authorizer)
- Process:
  1. Query DynamoDB for project by projectId and userId
  2. Verify user ownership
  3. Generate presigned URL for S3 object
  4. Return project metadata with S3 URL
- Output: { projectId, name, createdAt, updatedAt, floorspaceUrl }
- Error Handling: 404 if not found, 403 if not owner

**2. ListProjectsFunction**
- Trigger: GET /projects
- Purpose: List all projects for user
- Input: userId (from authorizer)
- Process:
  1. Query DynamoDB with userId as partition key
  2. Return array of projects
- Output: { projects: [...] }

**3. CreateUpdateProjectFunction**
- Trigger: POST /projects/{projectId}
- Purpose: Create new project or update existing
- Input: projectId, userId, body { name, description }
- Process:
  1. Generate projectId if creating new
  2. Create/update DynamoDB record
  3. If new project, initialize empty floorspace JSON in S3
  4. Return project details
- Output: { projectId, name, createdAt, updatedAt }

**4. DeleteProjectFunction**
- Trigger: DELETE /projects/{projectId}
- Purpose: Delete project and associated data
- Input: projectId, userId
- Process:
  1. Verify user ownership in DynamoDB
  2. Delete DynamoDB record
  3. Delete S3 object at {userId}/{projectId}/floorspace.json
  4. Return success status
- Output: { success: true }
- Error Handling: 403 if not owner, 404 if not found

**5. UploadFloorspaceFunction**
- Trigger: POST /projects/{projectId}/upload
- Purpose: Store floorspace JSON to S3
- Input: projectId, userId, body { floorspaceJson }
- Process:
  1. Verify user ownership in DynamoDB
  2. Validate JSON structure
  3. Upload to S3 at {userId}/{projectId}/floorspace.json
  4. Update lastModified timestamp in DynamoDB
  5. Return success status
- Output: { success: true, updatedAt }
- Error Handling: 403 if not owner, 400 if invalid JSON

## Data Models

### DynamoDB Schema

**Table: Projects**

```javascript
{
  userId: String,        // Partition Key (Cognito sub)
  projectId: String,     // Sort Key (UUID)
  name: String,          // Project name
  description: String,   // Optional description
  createdAt: String,     // ISO 8601 timestamp
  updatedAt: String,     // ISO 8601 timestamp
  s3Key: String          // S3 object key
}
```

**Indexes:**
- Primary Key: userId (PK) + projectId (SK)
- GSI: projectId (for direct lookup by ID with userId verification)

### S3 Storage Structure

**Bucket: floorspace-json-storage**

```
{userId}/
  {projectId}/
    floorspace.json
```

**Object Metadata:**
- ContentType: application/json
- ServerSideEncryption: AES256
- ACL: Private (access via presigned URLs only)

### Floorspace JSON Structure

The floorspace JSON follows the NREL floorspace.js schema:

```javascript
{
  version: String,
  stories: [
    {
      id: String,
      name: String,
      geometry: {
        vertices: [[x, y], ...],
        edges: [[v1, v2], ...],
        faces: [...]
      },
      spaces: [...],
      shading: [...]
    }
  ],
  building_units: [...],
  thermal_zones: [...],
  space_types: [...],
  construction_sets: [...]
}
```

### Authentication Token Structure

**Cognito JWT Claims:**
```javascript
{
  sub: String,           // User ID (used as userId)
  email: String,
  email_verified: Boolean,
  cognito:username: String,
  exp: Number,           // Expiration timestamp
  iat: Number            // Issued at timestamp
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Authentication Properties

**Property 1: Valid registration creates account**
*For any* valid user credentials (properly formatted email and strong password), submitting registration should successfully create a new Cognito account.
**Validates: Requirements 1.1**

**Property 2: Invalid input validation**
*For any* registration input with invalid format (malformed email, weak password, mismatched confirmation), the system should reject the registration and return specific validation error messages.
**Validates: Requirements 1.3**

**Property 3: Valid credentials authenticate successfully**
*For any* valid user credentials that exist in Cognito, submitting login should authenticate the user and return a valid JWT token.
**Validates: Requirements 2.1**

**Property 4: Invalid credentials are rejected**
*For any* invalid credential combination (wrong password, non-existent email), the authentication should fail and return an appropriate error message.
**Validates: Requirements 2.2**

**Property 5: Token validation on API requests**
*For any* API request, the system should validate the Cognito JWT token before processing the request.
**Validates: Requirements 9.1**

**Property 6: Invalid tokens return 401**
*For any* API request with an invalid or expired token, the system should reject the request with a 401 Unauthorized status.
**Validates: Requirements 9.2**

### Project Management Properties

**Property 7: Dashboard retrieves user projects**
*For any* authenticated user, accessing the project dashboard should retrieve and display all projects where the userId matches the authenticated user's ID from DynamoDB.
**Validates: Requirements 3.1**

**Property 8: Project display contains required fields**
*For any* project retrieved from DynamoDB, the displayed project card should contain the project name, creation date, and last modified date.
**Validates: Requirements 3.3**

**Property 9: Project creation completeness**
*For any* valid project information submitted, the system should create a DynamoDB record with a unique projectId AND initialize an empty floorspace JSON file in S3 at the correct path.
**Validates: Requirements 4.2, 4.3**

**Property 10: Ownership verification**
*For any* project access request, the system should verify that the requesting user's userId matches the project's userId before granting access, returning 403 Forbidden if ownership doesn't match.
**Validates: Requirements 9.3, 9.4, 10.3**

**Property 11: Project deletion cleanup**
*For any* project deletion, the system should remove both the DynamoDB record AND the associated S3 file at {userId}/{projectId}/floorspace.json.
**Validates: Requirements 7.2, 7.3, 8.3, 10.4**

**Property 12: Dashboard updates after deletion**
*For any* successful project deletion, the project dashboard should no longer display the deleted project in the project list.
**Validates: Requirements 7.4**

### Floorspace Editor Properties

**Property 13: Editor loads project data**
*For any* project accessed through the editor, the system should retrieve the floorspace JSON from S3 and load it into the iframe editor.
**Validates: Requirements 5.2**

**Property 14: Save operation round-trip**
*For any* floorspace modifications saved by the user, the system should capture the changes in JSON format AND successfully upload them to S3, such that retrieving the project immediately after should return the updated data.
**Validates: Requirements 5.3, 5.4**

**Property 15: Upload updates metadata**
*For any* floorspace JSON upload, the system should store the JSON to S3 AND update the project's lastModified timestamp in DynamoDB.
**Validates: Requirements 8.4**

### API Lambda Properties

**Property 16: GET returns project details**
*For any* valid GET request to /projects/{projectId} with proper authentication and ownership, the Lambda should retrieve the project from DynamoDB and return project metadata with a presigned S3 URL.
**Validates: Requirements 8.1**

**Property 17: POST creates or updates project**
*For any* valid POST request to /projects/{projectId}, the Lambda should create a new project record if it doesn't exist, or update the existing record if it does.
**Validates: Requirements 8.2**

**Property 18: API errors return appropriate status codes**
*For any* API request that fails (validation error, not found, unauthorized), the Lambda should return the appropriate HTTP status code (400, 404, 403) and a descriptive error message.
**Validates: Requirements 8.5**

### Storage Properties

**Property 19: S3 key format consistency**
*For any* floorspace JSON file uploaded, the S3 object key should follow the format {userId}/{projectId}/floorspace.json.
**Validates: Requirements 10.1**

**Property 20: S3 access permissions**
*For any* file stored in S3, the object should have private ACL and be accessible only via presigned URLs or authenticated API requests.
**Validates: Requirements 10.2**

## Error Handling

### Frontend Error Handling

**Authentication Errors:**
- Network failures: Display "Unable to connect. Please check your internet connection."
- Invalid credentials: Display "Invalid email or password."
- Expired session: Redirect to login with message "Your session has expired. Please log in again."
- Registration conflicts: Display "An account with this email already exists."

**API Errors:**
- 401 Unauthorized: Clear auth token, redirect to login
- 403 Forbidden: Display "You don't have permission to access this resource."
- 404 Not Found: Display "Project not found."
- 500 Server Error: Display "Something went wrong. Please try again later."
- Network timeout: Display "Request timed out. Please try again."

**Validation Errors:**
- Empty project name: "Project name is required."
- Invalid email format: "Please enter a valid email address."
- Weak password: "Password must be at least 8 characters with uppercase, lowercase, and numbers."

### Backend Error Handling

**Lambda Error Responses:**

```javascript
// Standard error response format
{
  error: {
    code: String,        // ERROR_CODE
    message: String,     // Human-readable message
    details: Object      // Optional additional context
  }
}
```

**Error Codes:**
- `UNAUTHORIZED`: Missing or invalid auth token (401)
- `FORBIDDEN`: User doesn't own resource (403)
- `NOT_FOUND`: Resource doesn't exist (404)
- `VALIDATION_ERROR`: Invalid input data (400)
- `CONFLICT`: Resource already exists (409)
- `INTERNAL_ERROR`: Unexpected server error (500)

**DynamoDB Error Handling:**
- `ConditionalCheckFailedException`: Return 409 Conflict
- `ResourceNotFoundException`: Return 404 Not Found
- `ProvisionedThroughputExceededException`: Retry with exponential backoff
- Generic errors: Log to CloudWatch, return 500

**S3 Error Handling:**
- `NoSuchKey`: Return 404 Not Found
- `AccessDenied`: Return 403 Forbidden
- `NoSuchBucket`: Log critical error, return 500
- Upload failures: Retry up to 3 times with exponential backoff

**Cognito Error Handling:**
- `UserNotFoundException`: Return "Invalid credentials" (don't reveal user existence)
- `NotAuthorizedException`: Return "Invalid credentials"
- `UsernameExistsException`: Return "Email already registered"
- `InvalidPasswordException`: Return specific password requirements

### Logging and Monitoring

**CloudWatch Logs:**
- All Lambda invocations logged with request ID
- Error logs include stack traces
- API Gateway access logs enabled

**Metrics to Track:**
- API request count and latency
- Lambda execution duration and errors
- DynamoDB read/write capacity usage
- S3 upload/download success rate
- Authentication success/failure rate

## Testing Strategy

### Unit Testing

The system will use **Jest** for unit testing on both frontend and backend components.

**Frontend Unit Tests:**
- Component rendering tests (React Testing Library)
- Form validation logic
- API client functions
- Authentication state management
- Navigation logic

**Backend Unit Tests:**
- Lambda handler functions with mocked AWS SDK calls
- Input validation functions
- Error handling logic
- S3 key generation
- DynamoDB query construction

**Example Unit Tests:**
- Test that CreateProjectModal validates empty project names
- Test that API client includes auth token in headers
- Test that Lambda returns 403 when userId doesn't match project owner
- Test that S3 key is correctly formatted as {userId}/{projectId}/floorspace.json

### Property-Based Testing

The system will use **fast-check** (JavaScript/TypeScript) for property-based testing.

**Configuration:**
- Minimum 100 iterations per property test
- Each property test tagged with format: `**Feature: floorspace-3d-viewer, Property {number}: {property_text}**`
- Each correctness property implemented as a single property-based test

**Property Test Coverage:**
- Authentication: Test valid/invalid credential combinations
- Project CRUD: Test project creation, retrieval, update, deletion with random data
- Ownership verification: Test access control with various user/project combinations
- S3 key format: Test key generation with random userId/projectId values
- API error responses: Test error handling with various failure scenarios
- Data persistence: Test round-trip operations (save then load)

**Generators:**
- `arbitraryEmail()`: Generate valid/invalid email formats
- `arbitraryPassword()`: Generate passwords of varying strength
- `arbitraryProjectData()`: Generate project objects with random valid data
- `arbitraryUserId()`: Generate UUID format user IDs
- `arbitraryFloorspaceJson()`: Generate valid floorspace JSON structures
- `arbitraryAuthToken()`: Generate valid/expired/malformed JWT tokens

**Example Property Tests:**
- For any valid project data, creating a project should result in both DynamoDB and S3 entries
- For any user attempting to access another user's project, the system should return 403
- For any floorspace JSON uploaded, retrieving it immediately should return equivalent data
- For any project deletion, both DynamoDB and S3 should no longer contain the project data

### Integration Testing

**API Integration Tests:**
- Test complete API flows with real AWS SDK calls (using LocalStack or test AWS account)
- Test authentication flow from registration through login to API access
- Test project lifecycle: create → edit → save → retrieve → delete
- Test error scenarios: unauthorized access, missing resources, invalid data

**End-to-End Tests:**
- Use Playwright or Cypress for browser automation
- Test complete user journeys:
  - New user registration and first project creation
  - Existing user login and project management
  - Floorspace editor integration and save functionality
  - Project deletion and dashboard update

### Test Organization

```
frontend/
  src/
    components/
      __tests__/
        LoginPage.test.tsx
        ProjectDashboard.test.tsx
        FloorspaceEditorPage.test.tsx
    __tests__/
      properties/
        auth.properties.test.ts
        projects.properties.test.ts
        
backend/
  src/
    functions/
      __tests__/
        getProject.test.ts
        createProject.test.ts
        deleteProject.test.ts
        uploadFloorspace.test.ts
    __tests__/
      properties/
        api.properties.test.ts
        storage.properties.test.ts
```

## Security Considerations

### Authentication & Authorization
- All passwords hashed by Cognito (never stored in plaintext)
- JWT tokens expire after 1 hour
- Refresh tokens used for extended sessions
- All API endpoints require valid authentication
- User can only access their own projects (enforced at Lambda level)

### Data Protection
- S3 bucket has private ACL (no public access)
- S3 objects accessed via presigned URLs (expire after 15 minutes)
- DynamoDB uses encryption at rest
- API Gateway uses HTTPS only
- CORS configured to allow only frontend domain

### Input Validation
- Email format validation on frontend and backend
- Password strength requirements enforced
- Project names sanitized to prevent injection
- JSON structure validated before S3 upload
- File size limits enforced (max 10MB per floorspace JSON)

### AWS IAM Policies
- Lambda execution role has minimal permissions:
  - DynamoDB: GetItem, PutItem, DeleteItem, Query on Projects table only
  - S3: GetObject, PutObject, DeleteObject on floorspace-json-storage bucket only
  - CloudWatch: PutLogEvents for logging
- API Gateway has permission to invoke Lambda functions only
- Cognito User Pool configured with MFA optional

## Deployment Strategy

### Infrastructure as Code
- Use AWS CDK or Terraform for infrastructure provisioning
- Separate stacks for dev, staging, and production environments
- Environment-specific configuration files

### CI/CD Pipeline
1. Code commit triggers build
2. Run unit tests and property tests
3. Run linting and type checking
4. Build frontend (React production build)
5. Package Lambda functions
6. Deploy to staging environment
7. Run integration tests against staging
8. Manual approval for production deployment
9. Deploy to production
10. Run smoke tests

### Environment Configuration

**Development:**
- Local DynamoDB (DynamoDB Local)
- LocalStack for S3 simulation
- Cognito test user pool

**Staging:**
- Dedicated AWS resources with "staging-" prefix
- Separate Cognito user pool
- Test data seeded

**Production:**
- Production AWS resources
- Monitoring and alerting enabled
- Automated backups configured

## Performance Considerations

### Frontend Optimization
- Code splitting for route-based lazy loading
- React.memo for expensive component renders
- Debounce save operations (auto-save every 30 seconds)
- Pagination for project list (20 projects per page)
- Image and asset optimization

### Backend Optimization
- DynamoDB on-demand pricing for variable workload
- Lambda memory allocation: 512MB (balance cost/performance)
- S3 presigned URL caching (15-minute expiry)
- API Gateway caching for GET requests (5-minute TTL)
- Connection pooling for DynamoDB client

### Scalability
- Lambda auto-scales based on request volume
- DynamoDB auto-scales with on-demand mode
- S3 handles unlimited storage
- CloudFront CDN for frontend static assets (future enhancement)
- API Gateway handles 10,000 requests per second default limit

## Future Enhancements

### 3D Viewer Implementation
- Integrate Three.js for 3D rendering
- Convert floorspace JSON to 3D geometry
- Add camera controls (pan, zoom, rotate)
- Support for textures and materials
- Export 3D models (OBJ, GLTF formats)

### Collaboration Features
- Share projects with other users (read-only or edit access)
- Real-time collaborative editing (WebSocket integration)
- Project version history
- Comments and annotations

### Advanced Features
- Project templates library
- Import/export floorspace files
- Batch operations (duplicate, archive projects)
- Advanced search and filtering
- Project tags and categories
- Analytics dashboard (project statistics)
