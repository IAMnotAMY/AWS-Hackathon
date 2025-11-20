import * as fc from 'fast-check';
import { handler as getProjectHandler } from '../../functions/getProject';
import { handler as createHandler } from '../../functions/createUpdateProject';
import { handler as uploadHandler } from '../../functions/uploadFloorspace';
import { APIGatewayProxyEvent } from 'aws-lambda';
import { DynamoDBDocumentClient, GetCommand } from '@aws-sdk/lib-dynamodb';
import { mockClient } from 'aws-sdk-client-mock';

// Mock AWS SDK clients
const ddbMock = mockClient(DynamoDBDocumentClient);

describe('API Error Handling - Property Tests', () => {
  beforeEach(() => {
    ddbMock.reset();
    process.env.TABLE_NAME = 'floorspace-projects';
    process.env.BUCKET_NAME = 'test-bucket';
  });

  /**
   * Feature: floorspace-3d-viewer, Property 18: API errors return appropriate status codes
   * Validates: Requirements 8.5
   */
  test('Property 18: For any API request that fails validation, Lambda returns 400 with descriptive error', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          userId: fc.uuid(),
        }),
        async (data) => {
          // Test 1: Missing projectId in GET request
          const getMissingIdEvent: Partial<APIGatewayProxyEvent> = {
            pathParameters: {},
            requestContext: {
              authorizer: { claims: { sub: data.userId } },
            } as any,
          };

          const getResult = await getProjectHandler(getMissingIdEvent as APIGatewayProxyEvent);
          expect(getResult.statusCode).toBe(400);
          const getBody = JSON.parse(getResult.body);
          expect(getBody.error.code).toBe('VALIDATION_ERROR');
          expect(getBody.error.message).toBeDefined();

          // Test 2: Missing body in CREATE request
          const createMissingBodyEvent: Partial<APIGatewayProxyEvent> = {
            pathParameters: { projectId: 'new' },
            requestContext: {
              authorizer: { claims: { sub: data.userId } },
            } as any,
            body: undefined,
          };

          const createResult = await createHandler(createMissingBodyEvent as APIGatewayProxyEvent);
          expect(createResult.statusCode).toBe(400);
          const createBody = JSON.parse(createResult.body);
          expect(createBody.error.code).toBe('VALIDATION_ERROR');
          expect(createBody.error.message).toBeDefined();

          // Test 3: Invalid JSON in UPLOAD request
          const uploadInvalidJsonEvent: Partial<APIGatewayProxyEvent> = {
            pathParameters: { projectId: 'test-project-id' },
            requestContext: {
              authorizer: { claims: { sub: data.userId } },
            } as any,
            body: 'invalid json{',
          };

          const uploadResult = await uploadHandler(uploadInvalidJsonEvent as APIGatewayProxyEvent);
          expect(uploadResult.statusCode).toBe(400);
          const uploadBody = JSON.parse(uploadResult.body);
          expect(uploadBody.error.code).toBe('VALIDATION_ERROR');
          expect(uploadBody.error.message).toBeDefined();
        }
      ),
      { numRuns: 50 }
    );
  });

  test('Property 18: For any API request for non-existent resource, Lambda returns 404 with descriptive error', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          userId: fc.uuid(),
          projectId: fc.uuid(),
        }),
        async (data) => {
          // Reset mocks for each iteration
          ddbMock.reset();

          // Mock DynamoDB to return no item (project not found)
          ddbMock.on(GetCommand).resolves({});

          const event: Partial<APIGatewayProxyEvent> = {
            pathParameters: { projectId: data.projectId },
            requestContext: {
              authorizer: { claims: { sub: data.userId } },
            } as any,
          };

          const result = await getProjectHandler(event as APIGatewayProxyEvent);

          expect(result.statusCode).toBe(404);
          const body = JSON.parse(result.body);
          expect(body.error.code).toBe('NOT_FOUND');
          expect(body.error.message).toBeDefined();
        }
      ),
      { numRuns: 50 }
    );
  });

  test('Property 18: For any API request without authentication, Lambda returns 401 with descriptive error', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          projectId: fc.uuid(),
        }),
        async (data) => {
          // Event without userId in authorizer context
          const event: Partial<APIGatewayProxyEvent> = {
            pathParameters: { projectId: data.projectId },
            requestContext: {
              authorizer: { claims: {} },
            } as any,
          };

          const result = await getProjectHandler(event as APIGatewayProxyEvent);

          expect(result.statusCode).toBe(401);
          const body = JSON.parse(result.body);
          expect(body.error.code).toBe('UNAUTHORIZED');
          expect(body.error.message).toBeDefined();
        }
      ),
      { numRuns: 50 }
    );
  });

  test('Property 18: For any API request to access another users resource, Lambda returns 403 with descriptive error', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          ownerId: fc.uuid(),
          requesterId: fc.uuid(),
          projectId: fc.uuid(),
        }),
        async (data) => {
          // Ensure requester is different from owner
          fc.pre(data.ownerId !== data.requesterId);

          // Reset mocks for each iteration
          ddbMock.reset();

          // Mock DynamoDB to return project owned by ownerId
          ddbMock.on(GetCommand).resolves({
            Item: {
              userId: data.ownerId,
              projectId: data.projectId,
              name: 'Test Project',
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              s3Key: `${data.ownerId}/${data.projectId}/floorspace.json`,
            },
          });

          // Request from different user
          const event: Partial<APIGatewayProxyEvent> = {
            pathParameters: { projectId: data.projectId },
            requestContext: {
              authorizer: { claims: { sub: data.requesterId } },
            } as any,
          };

          const result = await getProjectHandler(event as APIGatewayProxyEvent);

          expect(result.statusCode).toBe(403);
          const body = JSON.parse(result.body);
          expect(body.error.code).toBe('FORBIDDEN');
          expect(body.error.message).toBeDefined();
        }
      ),
      { numRuns: 50 }
    );
  });
});
