import * as fc from 'fast-check';
import { handler } from '../../functions/getProject';
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

describe('GetProject Lambda - Property Tests', () => {
  beforeEach(() => {
    ddbMock.reset();
    jest.clearAllMocks();
    process.env.TABLE_NAME = 'floorspace-projects';
    process.env.BUCKET_NAME = 'test-bucket';
  });

  /**
   * Feature: floorspace-3d-viewer, Property 16: GET returns project details
   * Validates: Requirements 8.1
   */
  test('Property 16: For any valid GET request with proper authentication and ownership, returns project metadata with presigned S3 URL', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          userId: fc.uuid(),
          projectId: fc.uuid(),
          name: fc.string({ minLength: 1, maxLength: 100 }),
          description: fc.option(fc.string({ maxLength: 500 })),
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
              description: project.description,
              createdAt: project.createdAt,
              updatedAt: project.updatedAt,
              s3Key: `${project.userId}/${project.projectId}/floorspace.json`,
            },
          });

          // Mock presigned URL generation
          const mockPresignedUrl = `https://s3.amazonaws.com/test-bucket/${project.userId}/${project.projectId}/floorspace.json?signature=mock`;
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
          const result = await handler(event as APIGatewayProxyEvent);

          // Verify: Should return 200 with project details
          expect(result.statusCode).toBe(200);

          const body = JSON.parse(result.body);
          expect(body.projectId).toBe(project.projectId);
          expect(body.name).toBe(project.name);
          expect(body.createdAt).toBe(project.createdAt);
          expect(body.updatedAt).toBe(project.updatedAt);
          expect(body.floorspaceUrl).toBe(mockPresignedUrl);

          // Verify description is included if present
          if (project.description !== null) {
            expect(body.description).toBe(project.description);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
