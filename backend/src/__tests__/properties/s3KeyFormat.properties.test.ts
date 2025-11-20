import * as fc from 'fast-check';
import { handler as createHandler } from '../../functions/createUpdateProject';
import { handler as uploadHandler } from '../../functions/uploadFloorspace';
import { handler as deleteHandler } from '../../functions/deleteProject';
import { APIGatewayProxyEvent } from 'aws-lambda';
import { DynamoDBDocumentClient, PutCommand, GetCommand, DeleteCommand, UpdateCommand } from '@aws-sdk/lib-dynamodb';
import { S3Client, PutObjectCommand, DeleteObjectCommand } from '@aws-sdk/client-s3';
import { mockClient } from 'aws-sdk-client-mock';

// Mock AWS SDK clients
const ddbMock = mockClient(DynamoDBDocumentClient);
const s3Mock = mockClient(S3Client);

describe('S3 Key Format - Property Tests', () => {
  beforeEach(() => {
    ddbMock.reset();
    s3Mock.reset();
    process.env.TABLE_NAME = 'floorspace-projects';
    process.env.BUCKET_NAME = 'test-bucket';
  });

  /**
   * Feature: floorspace-3d-viewer, Property 19: S3 key format consistency
   * Validates: Requirements 10.1
   */
  test('Property 19: For any floorspace JSON file uploaded, S3 object key follows format {userId}/{projectId}/floorspace.json', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          userId: fc.uuid(),
          projectId: fc.uuid(),
          name: fc.string({ minLength: 1, maxLength: 100 }).filter(s => s.trim().length > 0),
          floorspaceJson: fc.record({
            version: fc.constantFrom('1.0', '2.0'),
            stories: fc.array(fc.anything(), { maxLength: 2 }),
          }),
        }),
        async (data) => {
          // Reset mocks for each iteration
          ddbMock.reset();
          s3Mock.reset();

          // Test 1: Create project - verify S3 key format
          ddbMock.on(GetCommand).resolves({});
          ddbMock.on(PutCommand).resolves({});
          s3Mock.on(PutObjectCommand).resolves({});

          const createEvent: Partial<APIGatewayProxyEvent> = {
            pathParameters: { projectId: 'new' },
            requestContext: {
              authorizer: { claims: { sub: data.userId } },
            } as any,
            body: JSON.stringify({ name: data.name }),
          };

          await createHandler(createEvent as APIGatewayProxyEvent);

          // Verify S3 key format for creation
          const createS3Calls = s3Mock.commandCalls(PutObjectCommand);
          expect(createS3Calls.length).toBeGreaterThan(0);

          const createS3Key = createS3Calls[createS3Calls.length - 1].args[0].input.Key;
          expect(createS3Key).toMatch(new RegExp(`^${data.userId}/[a-f0-9-]+/floorspace\\.json$`));

          // Extract the generated projectId
          const projectIdMatch = createS3Key?.match(/^[^/]+\/([^/]+)\/floorspace\.json$/);
          const generatedProjectId = projectIdMatch ? projectIdMatch[1] : data.projectId;

          // Reset mocks for upload test
          ddbMock.reset();
          s3Mock.reset();

          // Test 2: Upload floorspace - verify S3 key format
          const s3Key = `${data.userId}/${generatedProjectId}/floorspace.json`;
          ddbMock.on(GetCommand).resolves({
            Item: {
              userId: data.userId,
              projectId: generatedProjectId,
              name: data.name,
              s3Key,
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            },
          });
          ddbMock.on(UpdateCommand).resolves({});
          s3Mock.on(PutObjectCommand).resolves({});

          const uploadEvent: Partial<APIGatewayProxyEvent> = {
            pathParameters: { projectId: generatedProjectId },
            requestContext: {
              authorizer: { claims: { sub: data.userId } },
            } as any,
            body: JSON.stringify({ floorspaceJson: data.floorspaceJson }),
          };

          await uploadHandler(uploadEvent as APIGatewayProxyEvent);

          // Verify S3 key format for upload
          const uploadS3Calls = s3Mock.commandCalls(PutObjectCommand);
          expect(uploadS3Calls.length).toBe(1);

          const uploadS3Key = uploadS3Calls[0].args[0].input.Key;
          expect(uploadS3Key).toBe(`${data.userId}/${generatedProjectId}/floorspace.json`);

          // Reset mocks for delete test
          ddbMock.reset();
          s3Mock.reset();

          // Test 3: Delete project - verify S3 key format
          ddbMock.on(GetCommand).resolves({
            Item: {
              userId: data.userId,
              projectId: generatedProjectId,
              name: data.name,
              s3Key,
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            },
          });
          ddbMock.on(DeleteCommand).resolves({});
          s3Mock.on(DeleteObjectCommand).resolves({});

          const deleteEvent: Partial<APIGatewayProxyEvent> = {
            pathParameters: { projectId: generatedProjectId },
            requestContext: {
              authorizer: { claims: { sub: data.userId } },
            } as any,
          };

          await deleteHandler(deleteEvent as APIGatewayProxyEvent);

          // Verify S3 key format for deletion
          const deleteS3Calls = s3Mock.commandCalls(DeleteObjectCommand);
          expect(deleteS3Calls.length).toBe(1);

          const deleteS3Key = deleteS3Calls[0].args[0].input.Key;
          expect(deleteS3Key).toBe(`${data.userId}/${generatedProjectId}/floorspace.json`);
        }
      ),
      { numRuns: 100 }
    );
  });
});
