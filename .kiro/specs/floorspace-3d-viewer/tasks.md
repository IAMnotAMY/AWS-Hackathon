# Implementation Plan

- [x] 1. Set up project structure and dependencies





  - Create React frontend project with TypeScript
  - Set up AWS CDK or Terraform for infrastructure
  - Configure build tools and linting
  - Install dependencies: React Router, AWS Amplify, Axios, Jest, fast-check
  - _Requirements: All_

- [x] 2. Implement AWS infrastructure





  - Define Cognito User Pool with email/password authentication
  - Create DynamoDB Projects table with userId (PK) and projectId (SK)
  - Create S3 bucket for floorspace JSON storage with private ACL
  - Set up API Gateway REST API with Cognito authorizer
  - Configure IAM roles and policies for Lambda functions
  - _Requirements: 1.1, 2.1, 3.1, 8.1-8.5, 9.1-9.4, 10.1-10.4_

- [x] 3. Implement authentication components





- [x] 3.1 Create RegisterPage component


  - Build registration form with email, password, and confirm password fields
  - Implement input validation for email format and password strength
  - Integrate with AWS Amplify Auth.signUp
  - Handle registration errors (existing email, invalid format)
  - Redirect to login page on success
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 3.2 Write property test for registration validation


  - **Property 2: Invalid input validation**
  - **Validates: Requirements 1.3**

- [x] 3.3 Create LoginPage component


  - Build login form with email and password fields
  - Integrate with AWS Amplify Auth.signIn
  - Store JWT token in localStorage on success
  - Handle authentication errors (invalid credentials)
  - Redirect to dashboard on success
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 3.4 Write property test for authentication


  - **Property 3: Valid credentials authenticate successfully**
  - **Property 4: Invalid credentials are rejected**
  - **Validates: Requirements 2.1, 2.2**

- [x] 3.5 Implement authentication context and protected routes


  - Create AuthContext for managing auth state
  - Implement ProtectedRoute component
  - Handle session expiration and redirect to login
  - _Requirements: 2.4_

- [x] 4. Implement Lambda functions for API





- [x] 4.1 Create GetProject Lambda function


  - Parse projectId from path parameters and userId from authorizer
  - Query DynamoDB for project by projectId and userId
  - Verify user ownership (return 403 if not owner)
  - Generate presigned S3 URL for floorspace JSON
  - Return project metadata with S3 URL
  - Handle errors: 404 if not found, 403 if not owner
  - _Requirements: 8.1, 9.3, 9.4_

- [x] 4.2 Write property test for GET project


  - **Property 16: GET returns project details**
  - **Validates: Requirements 8.1**

- [x] 4.3 Create ListProjects Lambda function


  - Extract userId from authorizer context
  - Query DynamoDB with userId as partition key
  - Return array of all user's projects
  - _Requirements: 3.1_

- [x] 4.4 Write property test for ownership verification


  - **Property 10: Ownership verification**
  - **Validates: Requirements 9.3, 9.4**

- [x] 4.5 Create CreateUpdateProject Lambda function


  - Parse projectId and request body
  - Generate unique projectId if creating new project
  - Create or update DynamoDB record with project metadata
  - If new project, initialize empty floorspace JSON in S3
  - Return project details
  - _Requirements: 4.2, 4.3, 8.2_

- [x] 4.6 Write property test for project creation



  - **Property 9: Project creation completeness**
  - **Validates: Requirements 4.2, 4.3**



- [x] 4.7 Create DeleteProject Lambda function

  - Parse projectId and userId from request
  - Verify user ownership in DynamoDB
  - Delete DynamoDB record
  - Delete S3 object at {userId}/{projectId}/floorspace.json
  - Return success status


  - Handle errors: 403 if not owner, 404 if not found
  - _Requirements: 7.2, 7.3, 8.3_

- [x] 4.8 Write property test for project deletion

  - **Property 11: Project deletion cleanup**
  - **Validates: Requirements 7.2, 7.3, 8.3, 10.4**

- [x] 4.9 Create UploadFloorspace Lambda function


  - Parse projectId, userId, and floorspace JSON from request body
  - Verify user ownership in DynamoDB
  - Validate JSON structure
  - Upload to S3 at {userId}/{projectId}/floorspace.json
  - Update lastModified timestamp in DynamoDB
  - Return success status
  - Handle errors: 403 if not owner, 400 if invalid JSON
  - _Requirements: 5.4, 8.4_

- [x] 4.10 Write property test for upload


  - **Property 15: Upload updates metadata**
  - **Validates: Requirements 8.4**

- [x] 4.11 Write property test for S3 key format


  - **Property 19: S3 key format consistency**
  - **Validates: Requirements 10.1**

- [x] 4.12 Write property test for API error handling


  - **Property 18: API errors return appropriate status codes**
  - **Validates: Requirements 8.5**

- [ ] 5. Deploy API Gateway and Lambda functions
  - Configure API Gateway endpoints with Lambda integrations
  - Attach Cognito authorizer to all endpoints
  - Deploy API to dev/staging environment
  - Test endpoints with Postman or curl
  - _Requirements: 8.1-8.5, 9.1-9.4_

- [ ] 5.1 Write property test for token validation
  - **Property 5: Token validation on API requests**
  - **Property 6: Invalid tokens return 401**
  - **Validates: Requirements 9.1, 9.2**

- [ ] 6. Implement project dashboard
- [ ] 6.1 Create ProjectDashboard component
  - Fetch user's projects from API on mount
  - Display loading state while fetching
  - Display "no projects" message when list is empty
  - Render ProjectCard components for each project
  - Handle API errors and display error messages
  - _Requirements: 3.1, 3.2_

- [ ] 6.2 Write property test for dashboard retrieval
  - **Property 7: Dashboard retrieves user projects**
  - **Validates: Requirements 3.1**

- [ ] 6.3 Create ProjectCard component
  - Display project name, creation date, and last modified date
  - Handle click to navigate to editor
  - Add delete button with confirmation modal
  - _Requirements: 3.3, 3.4_

- [ ] 6.4 Write property test for project display
  - **Property 8: Project display contains required fields**
  - **Validates: Requirements 3.3**

- [ ] 6.5 Create CreateProjectModal component
  - Build form with project name and description fields
  - Validate project name is not empty
  - Call API to create new project
  - Redirect to editor on success
  - Handle API errors
  - _Requirements: 4.1, 4.4_

- [ ] 6.6 Implement project deletion with confirmation
  - Add delete button to ProjectCard
  - Show confirmation dialog before deletion
  - Call DELETE API endpoint
  - Update dashboard to remove deleted project
  - _Requirements: 7.1, 7.4_

- [ ] 6.7 Write property test for dashboard update after deletion
  - **Property 12: Dashboard updates after deletion**
  - **Validates: Requirements 7.4**

- [ ] 7. Implement floorspace editor page
- [ ] 7.1 Create FloorspaceEditorPage component
  - Set up iframe to load floorspace.js library
  - Fetch project data from API on mount
  - Load floorspace JSON into iframe using postMessage
  - Implement auto-save functionality (every 30 seconds)
  - Handle save errors and display status
  - _Requirements: 5.1, 5.2_

- [ ] 7.2 Write property test for editor data loading
  - **Property 13: Editor loads project data**
  - **Validates: Requirements 5.2**

- [ ] 7.3 Implement iframe communication
  - Set up postMessage listener for floorspace changes
  - Capture floorspace JSON updates from iframe
  - Send JSON data to iframe on load
  - Handle communication errors
  - _Requirements: 5.3_

- [ ] 7.4 Create EditorToolbar component
  - Add save button to manually trigger save
  - Add back button to return to dashboard
  - Add "View in 3D" button to navigate to 3D viewer
  - Display save status (saving, saved, error)
  - _Requirements: 5.4_

- [ ] 7.5 Write property test for save round-trip
  - **Property 14: Save operation round-trip**
  - **Validates: Requirements 5.3, 5.4**

- [ ] 8. Implement 3D viewer page
- [ ] 8.1 Create ThreeDViewerPage component
  - Display placeholder message "3D Viewer - Coming Soon"
  - Fetch floorspace JSON from API
  - Add navigation buttons to return to editor or dashboard
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 8.2 Write property test for 3D viewer data retrieval
  - **Property 6.2: 3D view page loads and retrieves JSON**
  - **Validates: Requirements 6.2**

- [ ] 9. Implement API client and error handling
- [ ] 9.1 Create API client service
  - Configure Axios instance with base URL
  - Add request interceptor to include auth token
  - Add response interceptor for error handling
  - Implement retry logic for network failures
  - _Requirements: All API calls_

- [ ] 9.2 Implement centralized error handling
  - Create error handling utility functions
  - Map API error codes to user-friendly messages
  - Handle 401 errors by redirecting to login
  - Display error notifications to user
  - _Requirements: 8.5_

- [ ] 10. Add routing and navigation
  - Configure React Router with routes for all pages
  - Implement protected routes for authenticated pages
  - Set up navigation guards for session validation
  - Add 404 page for invalid routes
  - _Requirements: 1.4, 2.3, 3.4, 4.4_

- [ ] 11. Styling and UI polish
  - Apply consistent styling across all components
  - Implement responsive design for mobile/tablet
  - Add loading spinners and skeleton screens
  - Improve form validation feedback
  - Add animations and transitions
  - _Requirements: All UI requirements_

- [ ] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
