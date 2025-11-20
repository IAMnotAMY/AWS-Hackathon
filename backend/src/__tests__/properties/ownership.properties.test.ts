import * as fc from 'fast-check';
import { handler as getProjectHandler } from '../../functions/getProject';
import { APIGatewayProxyEvent } from 'aws-lambda';
import { DynamoDBDocumentClient, GetCommand } from '@aws-sdk/lib-dynamodb';
import { mockClient } from 'aws-sdk-client-mock';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

// Mock AWS SDK clients
const ddbMock = mockClient(DynamoDBDocumentClient);

jest.mock('@aws-sdk/s3-request-presigner', () => ({
  getSignedUrl: jest.fn(),
}));

const mockedGetSignedUrl = getSignedUrl as jest.MockedFunction<typeof getSignedUrl>;

describe('Ownership Verification - Property Tests', () => {
  beforeEach(() => {
    ddbMock.reset();
    jest.clearAllMocks();
    process.env.TABLE_NAME = 'floorspace-projects';
    process.env.BUCKET_NAME = 'test-bucket';
  });

  /**
   * Feature: floorspace-3d-viewer, Property 10: Ownership verification
   * Validates: Requirements 9.3, 9.4
   */
  test('Property 10: For any project access request, system verifies requesting user owns the project, returning 403 if ownership does not match', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          projectOwnerId: fc.uuid(),
          requestingUserId: fc.uuid(),
          projectId: fc.uuid(),
          name: fc.string({ minLength: 1, maxLength: 100 }),
          createdAt: fc.date().map(d => d.toISOString()),
          updatedAt: fc.date().map(d => d.toISOString()),
        }),
        async (data) => {
          // Ensure the requesting user is different from the owner
          fc.pre(data.projectOwnerId !== data.requestingUserId);

          // Setup: Mock DynamoDB to return a project owned by projectOwnerId
          ddbMock.on(GetCommand).resolves({
            Item: {
              userId: data.projectOwnerId,
              projectId: data.projectId,
              name: data.name,
              createdAt: data.createdAt,
              updatedAt: data.updatedAt,
              s3Key: `${data.projectOwnerId}/${data.projectId}/floorspace.json`,
            },
          });

          // Mock presigned URL (shouldn't be called, but just in case)
          mockedGetSignedUrl.mockResolvedValue('https://mock-url.com');

          // Create event with different userId (not the owner)
          const event: Partial<APIGatewayProxyEvent> = {
            pathParameters: {
              projectId: data.projectId,
            },
            requestContext: {
              authorizer: {
                claims: {
                  sub: data.requestingUserId,
                },
              },
            } as any,
          };

          // Execute
          const result = await getProjectHandler(event as APIGatewayProxyEvent);

          // Verify: Should return 403 Forbidden
          expect(result.statusCode).toBe(403);

          const body = JSON.parse(result.body);
          expect(body.error.code).toBe('FORBIDDEN');
          expect(body.error.message).toContain('permission');
        }
      ),
      { numRuns: 100 }
    );
  });

  test('Property 10 (positive case): For any project access request where user owns the project, system grants access', async () => {
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

          // Mock presigned URL
          const mockPresignedUrl = `https://s3.amazonaws.com/test-bucket/${project.userId}/${project.projectId}/floorspace.json`;
          mockedGetSignedUrl.mockResolvedValue(mockPresignedUrl);

          // Create event with matching userId (owner)
          const event: Partial<APIGatewayProxyEvent> = {
            pathParameters: {
              projectId: project.projectId,
            },
            requestContext: {
              authorizer: {
                claims: {
                  sub: project.userId,
                },
              },
            } as any,
          };

          // Execute
          const result = await getProjectHandler(event as APIGatewayProxyEvent);

          // Verify: Should return 200 (access granted)
          expect(result.statusCode).toBe(200);

          const body = JSON.parse(result.body);
          expect(body.projectId).toBe(project.projectId);
        }
      ),
      { numRuns: 100 }
    );
  });
});
