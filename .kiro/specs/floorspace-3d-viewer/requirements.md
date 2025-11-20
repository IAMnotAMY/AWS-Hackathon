# Requirements Document

## Introduction

The Floorspace 3D Viewer is a web application that enables users to create, manage, and visualize 2D floorplans using the NREL floorspace.js library and convert them to 3D models. The system provides user authentication, project management capabilities, and integration with AWS services for secure storage and API operations.

## Glossary

- **System**: The Floorspace 3D Viewer web application
- **User**: An authenticated person who creates and manages floorplan projects
- **Project**: A collection of floorspace data including 2D floorplan JSON and associated metadata
- **Floorspace JSON**: The JSON data format used by the NREL floorspace.js library to represent 2D floorplans
- **Cognito**: AWS authentication service used for user management
- **S3 Bucket**: AWS storage service for storing floorspace JSON files
- **DynamoDB**: AWS NoSQL database for storing project metadata
- **API Gateway**: AWS service for managing REST API endpoints
- **Lambda Function**: AWS serverless compute service for handling API requests
- **3D Model**: Three-dimensional representation of a floorplan

## Requirements

### Requirement 1

**User Story:** As a new user, I want to register for an account, so that I can access the application and create projects.

#### Acceptance Criteria

1. WHEN a user submits valid registration information THEN the System SHALL create a new account in Cognito with the provided credentials
2. WHEN a user submits registration information with an existing email THEN the System SHALL reject the registration and display an error message
3. WHEN a user submits registration information with invalid format THEN the System SHALL validate the input and display specific error messages
4. WHEN registration is successful THEN the System SHALL redirect the user to the login page

### Requirement 2

**User Story:** As a registered user, I want to log in to my account, so that I can access my projects and create new ones.

#### Acceptance Criteria

1. WHEN a user submits valid login credentials THEN the System SHALL authenticate the user through Cognito and grant access to the application
2. WHEN a user submits invalid login credentials THEN the System SHALL reject the authentication and display an error message
3. WHEN authentication is successful THEN the System SHALL store the authentication token and redirect the user to the project dashboard
4. WHEN a user session expires THEN the System SHALL redirect the user to the login page

### Requirement 3

**User Story:** As an authenticated user, I want to view a dashboard of all my projects, so that I can manage and access my floorplan work.

#### Acceptance Criteria

1. WHEN a user accesses the project dashboard THEN the System SHALL retrieve and display all projects associated with the user from DynamoDB
2. WHEN the project list is empty THEN the System SHALL display a message indicating no projects exist
3. WHEN project data is retrieved THEN the System SHALL display project name, creation date, and last modified date for each project
4. WHEN a user clicks on a project THEN the System SHALL navigate to the floorspace editor page for that project

### Requirement 4

**User Story:** As an authenticated user, I want to create a new project, so that I can start designing a floorplan.

#### Acceptance Criteria

1. WHEN a user initiates project creation THEN the System SHALL display a form to enter project details
2. WHEN a user submits valid project information THEN the System SHALL create a new project record in DynamoDB with a unique project identifier
3. WHEN a project is created THEN the System SHALL initialize an empty floorspace JSON structure in S3
4. WHEN project creation is successful THEN the System SHALL redirect the user to the floorspace editor page for the new project

### Requirement 5

**User Story:** As an authenticated user, I want to edit my floorplan using the floorspace.js editor, so that I can design and modify my 2D floorplan.

#### Acceptance Criteria

1. WHEN a user accesses a project THEN the System SHALL load the floorspace.js library in an iframe
2. WHEN the floorspace editor loads THEN the System SHALL retrieve the project floorspace JSON from S3 and load it into the editor
3. WHEN a user modifies the floorplan THEN the System SHALL capture the changes in the floorspace JSON format
4. WHEN a user saves changes THEN the System SHALL upload the updated floorspace JSON to S3 via the upload API endpoint

### Requirement 6

**User Story:** As an authenticated user, I want to view my floorplan in 3D, so that I can visualize the spatial design.

#### Acceptance Criteria

1. WHEN a user navigates to the 3D view page THEN the System SHALL display a placeholder for the 3D model viewer
2. WHEN the 3D view page loads THEN the System SHALL retrieve the associated floorspace JSON from S3
3. WHEN the page is accessed THEN the System SHALL provide navigation to return to the editor or dashboard

### Requirement 7

**User Story:** As an authenticated user, I want to delete projects I no longer need, so that I can keep my dashboard organized.

#### Acceptance Criteria

1. WHEN a user initiates project deletion THEN the System SHALL prompt for confirmation before proceeding
2. WHEN a user confirms deletion THEN the System SHALL remove the project record from DynamoDB via the DELETE API endpoint
3. WHEN a project is deleted from DynamoDB THEN the System SHALL remove the associated floorspace JSON file from S3
4. WHEN deletion is successful THEN the System SHALL update the project dashboard to reflect the removal

### Requirement 8

**User Story:** As a system architect, I want the API to handle project operations through Lambda functions, so that the system is scalable and maintainable.

#### Acceptance Criteria

1. WHEN a GET request is made to projects/{projectId} THEN the Lambda Function SHALL retrieve project details from DynamoDB and return them
2. WHEN a POST request is made to projects/{projectId} THEN the Lambda Function SHALL create or update the project record in DynamoDB
3. WHEN a DELETE request is made to projects/{projectId} THEN the Lambda Function SHALL remove the project from DynamoDB and delete associated S3 files
4. WHEN a POST request is made to projects/{projectId}/upload THEN the Lambda Function SHALL store the floorspace JSON to S3 and update the project metadata in DynamoDB
5. WHEN any API request fails THEN the Lambda Function SHALL return appropriate HTTP status codes and error messages

### Requirement 9

**User Story:** As a system architect, I want all API requests to be authenticated, so that only authorized users can access their projects.

#### Acceptance Criteria

1. WHEN an API request is received THEN the API Gateway SHALL validate the Cognito authentication token
2. WHEN an authentication token is invalid or expired THEN the API Gateway SHALL reject the request with a 401 Unauthorized status
3. WHEN an authenticated user requests a project THEN the System SHALL verify the user owns the project before allowing access
4. WHEN a user attempts to access another user's project THEN the System SHALL reject the request with a 403 Forbidden status

### Requirement 10

**User Story:** As a system architect, I want floorspace JSON files stored in a single S3 bucket with proper organization, so that data is secure and easily retrievable.

#### Acceptance Criteria

1. WHEN a floorspace JSON file is uploaded THEN the System SHALL store it in the S3 bucket with a key format of {userId}/{projectId}/floorspace.json
2. WHEN storing files THEN the System SHALL set appropriate access permissions to prevent unauthorized access
3. WHEN retrieving files THEN the System SHALL verify user ownership before granting access to the S3 object
4. WHEN a project is deleted THEN the System SHALL remove all associated files from the S3 bucket
