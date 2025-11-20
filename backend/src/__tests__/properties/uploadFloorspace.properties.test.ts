import * as fc from 'fast-check';
import { handler } from '../../functions/uploadFloorspace';
import { APIGatewayProxyEvent } from 'aws-lambda';
import { DynamoDBDocumentClient, GetCommand, UpdateCommand } from '@aws-sdk/lib-dynamodb';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { mockClient } from 'aws-sdk-client-mock';

// Mock AWS SDK clients
const ddbMock = mockClient(DynamoDBDocumentClient);
const s3Mock = mockClient(S3Client);

describe('Upload Floorspace - Property Tests', () => {
  beforeEach(() => {
    ddbMock.reset();
    s3Mock.reset();
    process.env.TABLE_NAME = 'floorspace-projects';
    process.env.BUCKET_NAME = 'test-bucket';
  });

  /**
   * Feature: floorspace-3d-viewer, Property 15: Upload updates metadata
   * Validates: Requirements 8.4
   */
  test('Property 15: For any floorspace JSON upload, system stores JSON to S3 AND updates project lastModified timestamp in DynamoDB', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          userId: fc.uuid(),
          projectId: fc.uuid(),
          name: fc.string({ minLength: 1, maxLength: 100 }),
          createdAt: fc.date().map(d => d.toISOString()),
          updatedAt: fc.date().map(d => d.toISOString()),
          floorspaceJson: fc.record({
            version: fc.constantFrom('1.0', '2.0'),
            stories: fc.array(fc.record({
              id: fc.uuid(),
              name: fc.string({ minLength: 1, maxLength: 50 }),
            }), { maxLength: 5 }),
            building_units: fc.array(fc.anything(), { maxLength: 3 }),
          }),
        }),
        async (data) => {
          // Reset mocks for each iteration
          ddbMock.reset();
          s3Mock.reset();

          const s3Key = `${data.userId}/${data.projectId}/floorspace.json`;

          // Setup: Mock DynamoDB GetCommand to return the project
          ddbMock.on(GetCommand).resolves({
            Item: {
              userId: data.userId,
              projectId: data.projectId,
              name: data.name,
              createdAt: data.createdAt,
              updatedAt: data.updatedAt,
              s3Key,
            },
          });

          // Mock DynamoDB UpdateCommand
          ddbMock.on(UpdateCommand).resolves({});

          // Mock S3 PutObjectCommand
          s3Mock.on(PutObjectCommand).resolves({});

          // Create event for upload
          const event: Partial<APIGatewayProxyEvent> = {
            pathParameters: {
              projectId: data.projectId,
            },
            requestContext: {
              authorizer: {
                claims: {
                  sub: data.userId,
                },
              },
            } as any,
            body: JSON.stringify({
              floorspaceJson: data.floorspaceJson,
            }),
          };

          // Execute
          const result = await handler(event as APIGatewayProxyEvent);

          // Verify: Should return 200 Success
          expect(result.statusCode).toBe(200);

          const body = JSON.parse(result.body);
          expect(body.success).toBe(true);
          expect(body.updatedAt).toBeDefined();

          // Verify S3 PutObjectCommand was called
          const s3Calls = s3Mock.commandCalls(PutObjectCommand);
          expect(s3Calls.length).toBe(1);

          const s3Params = s3Calls[0].args[0].input;
          expect(s3Params.Key).toBe(s3Key);
          expect(s3Params.ContentType).toBe('application/json');

          // Verify the uploaded JSON matches the input
          // Note: JSON serialization converts undefined to null, so we compare via round-trip
          const uploadedJson = JSON.parse(s3Params.Body as string);
          const expectedJson = JSON.parse(JSON.stringify(data.floorspaceJson));
          expect(uploadedJson).toEqual(expectedJson);

          // Verify DynamoDB UpdateCommand was called to update timestamp
          const ddbUpdateCalls = ddbMock.commandCalls(UpdateCommand);
          expect(ddbUpdateCalls.length).toBe(1);

          const ddbUpdateParams = ddbUpdateCalls[0].args[0].input;
          expect(ddbUpdateParams.Key).toEqual({
            userId: data.userId,
            projectId: data.projectId,
          });
          expect(ddbUpdateParams.UpdateExpression).toContain('updatedAt');
        }
      ),
      { numRuns: 100 }
    );
  });

  test('Property 15 (validation): For any invalid JSON upload, system rejects with 400', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          userId: fc.uuid(),
          projectId: fc.uuid(),
        }),
        async (data) => {
          // Reset mocks for each iteration
          ddbMock.reset();
          s3Mock.reset();

          // Create event with missing floorspaceJson
          const event: Partial<APIGatewayProxyEvent> = {
            pathParameters: {
              projectId: data.projectId,
            },
            requestContext: {
              authorizer: {
                claims: {
                  sub: data.userId,
                },
              },
            } as any,
            body: JSON.stringify({}),
          };

          // Execute
          const result = await handler(event as APIGatewayProxyEvent);

          // Verify: Should return 400 Bad Request
          expect(result.statusCode).toBe(400);

          const body = JSON.parse(result.body);
          expect(body.error.code).toBe('VALIDATION_ERROR');

          // Verify no S3 or DynamoDB operations occurred
          expect(s3Mock.commandCalls(PutObjectCommand).length).toBe(0);
          expect(ddbMock.commandCalls(UpdateCommand).length).toBe(0);
        }
      ),
      { numRuns: 50 }
    );
  });
});
