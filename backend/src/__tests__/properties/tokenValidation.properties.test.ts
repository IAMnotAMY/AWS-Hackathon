import * as fc from 'fast-check';
import { handler as getProjectHandler } from '../../functions/getProject';
import { handler as listProjectsHandler } from '../../functions/listProjects';
import { APIGatewayProxyEvent } from 'aws-lambda';
import { DynamoDBDocumentClient, GetCommand, QueryCommand } from '@aws-sdk/lib-dynamodb';
import { mockClient } from 'aws-sdk-client-mock';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

// Mock AWS SDK clients
const ddbMock = mockClient(DynamoDBDocumentClient);

jest.mock('@aws-sdk/s3-request-presigner', () => ({
  getSignedUrl: jest.fn(),
}));

const mockedGetSignedUrl = getSignedUrl as jest.MockedFunction<typeof getSignedUrl>;

describe('Token Validation - Property Tests', () => {
  beforeEach(() => {
    ddbMock.reset();
    jest.clearAllMocks();
    process.env.TABLE_NAME = 'floorspace-projects';
    process.env.BUCKET_NAME = 'test-bucket';
  });

  /**
   * Feature: floorspace-3d-viewer, Property 5: Token validation on API requests
   * Validates: Requirements 9.1
   */
  test('Property 5: For any API request, the system validates the Cognito JWT token before processing', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          userId: fc.uuid(),
          projectId: fc.uuid(),
          name: fc.string({ minLength: 1, maxLength: 100 }),
          createdAt: fc.date().map(d => d.toISOString()),
          updatedAt: fc.date().map(d => d.toISOString()),
        }),
        async (project) => {
          // Setup: Mock DynamoDB to return the project
          ddbMock.on(GetCommand).resolves({
            Item: {
              userId: project.userId,
              projectId: project.projectId,
              name: project.name,
              createdAt: project.createdAt,
              updatedAt: project.updatedAt,
              s3Key: `${project.userId}/${project.projectId}/floorspace.json`,
            },
          });

          // Mock presigned URL generation
          const mockPresignedUrl = `https://s3.amazonaws.com/test-bucket/${project.userId}/${project.projectId}/floorspace.json`;
          mockedGetSignedUrl.mockResolvedValue(mockPresignedUrl);

          // Create event WITH valid token (authorizer context present with claims)
          const eventWithToken: Partial<APIGatewayProxyEvent> = {
            pathParameters: {
              projectId: project.projectId,
            },
            requestContext: {
              authorizer: {
                claims: {
                  sub: project.userId,
                  email: 'test@example.com',
                  exp: Math.floor(Date.now() / 1000) + 3600, // Valid for 1 hour
                },
              },
            } as any,
          };

          // Execute with valid token
          const result = await getProjectHandler(eventWithToken as APIGatewayProxyEvent);

          // Verify: Should process the request (not return 401)
          // The token is validated by API Gateway before reaching Lambda,
          // so Lambda expects the authorizer context to be present
          expect(result.statusCode).not.toBe(401);
          
          // Should either succeed (200) or fail for other reasons (403, 404)
          // but not due to missing/invalid token
          expect([200, 403, 404]).toContain(result.statusCode);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Feature: floorspace-3d-viewer, Property 6: Invalid tokens return 401
   * Validates: Requirements 9.2
   */
  test('Property 6: For any API request with invalid or expired token, the system rejects with 401 Unauthorized', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          projectId: fc.uuid(),
        }),
        fc.oneof(
          // Case 1: No authorizer context at all (token missing)
          fc.constant({ hasAuthorizer: false, hasClaims: false, hasSub: false }),
          // Case 2: Authorizer present but no claims (malformed token)
          fc.constant({ hasAuthorizer: true, hasClaims: false, hasSub: false }),
          // Case 3: Claims present but no sub (invalid token structure)
          fc.constant({ hasAuthorizer: true, hasClaims: true, hasSub: false })
        ),
        async (data, tokenState) => {
          // Setup: Mock DynamoDB (shouldn't be called for invalid tokens)
          ddbMock.on(GetCommand).resolves({
            Item: {
              userId: 'some-user',
              projectId: data.projectId,
              name: 'Test Project',
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              s3Key: `some-user/${data.projectId}/floorspace.json`,
            },
          });

          mockedGetSignedUrl.mockResolvedValue('https://mock-url.com');

          // Create event based on token state
          let event: Partial<APIGatewayProxyEvent> = {
            pathParameters: {
              projectId: data.projectId,
            },
          };

          if (tokenState.hasAuthorizer) {
            event.requestContext = {
              authorizer: tokenState.hasClaims
                ? {
                    claims: tokenState.hasSub
                      ? { sub: 'some-user-id' }
                      : {}, // Claims without sub
                  }
                : undefined, // Authorizer without claims
            } as any;
          } else {
            // No authorizer context at all
            event.requestContext = {} as any;
          }

          // Execute
          const result = await getProjectHandler(event as APIGatewayProxyEvent);

          // Verify: Should return 401 Unauthorized for missing/invalid token
          expect(result.statusCode).toBe(401);

          const body = JSON.parse(result.body);
          expect(body.error.code).toBe('UNAUTHORIZED');
          expect(body.error.message).toBeDefined();
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 6 (additional test): Test with listProjects endpoint to ensure
   * token validation applies across all API endpoints
   */
  test('Property 6 (cross-endpoint): Invalid tokens return 401 across different API endpoints', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.oneof(
          fc.constant({ hasAuthorizer: false }),
          fc.constant({ hasAuthorizer: true, hasClaims: false }),
          fc.constant({ hasAuthorizer: true, hasClaims: true, hasSub: false })
        ),
        async (tokenState) => {
          // Setup: Mock DynamoDB query
          ddbMock.on(QueryCommand).resolves({
            Items: [],
          });

          // Create event based on token state
          let event: Partial<APIGatewayProxyEvent> = {
            pathParameters: null,
          };

          if (tokenState.hasAuthorizer) {
            event.requestContext = {
              authorizer: 'hasClaims' in tokenState && tokenState.hasClaims
                ? {
                    claims: 'hasSub' in tokenState && tokenState.hasSub
                      ? { sub: 'some-user-id' }
                      : {},
                  }
                : undefined,
            } as any;
          } else {
            event.requestContext = {} as any;
          }

          // Execute
          const result = await listProjectsHandler(event as APIGatewayProxyEvent);

          // Verify: Should return 401 Unauthorized
          expect(result.statusCode).toBe(401);

          const body = JSON.parse(result.body);
          expect(body.error.code).toBe('UNAUTHORIZED');
        }
      ),
      { numRuns: 100 }
    );
  });
});
