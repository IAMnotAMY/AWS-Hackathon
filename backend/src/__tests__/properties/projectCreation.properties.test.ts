import * as fc from 'fast-check';
import { handler } from '../../functions/createUpdateProject';
import { APIGatewayProxyEvent } from 'aws-lambda';
import { DynamoDBDocumentClient, PutCommand, GetCommand } from '@aws-sdk/lib-dynamodb';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { mockClient } from 'aws-sdk-client-mock';

// Mock AWS SDK clients
const ddbMock = mockClient(DynamoDBDocumentClient);
const s3Mock = mockClient(S3Client);

describe('Project Creation - Property Tests', () => {
  beforeEach(() => {
    ddbMock.reset();
    s3Mock.reset();
    process.env.TABLE_NAME = 'floorspace-projects';
    process.env.BUCKET_NAME = 'test-bucket';
  });

  /**
   * Feature: floorspace-3d-viewer, Property 9: Project creation completeness
   * Validates: Requirements 4.2, 4.3
   */
  test('Property 9: For any valid project information submitted, system creates DynamoDB record with unique projectId AND initializes empty floorspace JSON in S3', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          userId: fc.uuid(),
          name: fc.string({ minLength: 1, maxLength: 100 }).filter(s => s.trim().length > 0),
          description: fc.option(fc.string({ maxLength: 500 })),
        }),
        async (projectData) => {
          // Reset mocks for each iteration
          ddbMock.reset();
          s3Mock.reset();

          // Setup: Mock DynamoDB GetCommand to return no existing project
          ddbMock.on(GetCommand).resolves({});

          // Mock DynamoDB PutCommand
          ddbMock.on(PutCommand).resolves({});

          // Mock S3 PutObjectCommand
          s3Mock.on(PutObjectCommand).resolves({});

          // Create event for new project
          const event: Partial<APIGatewayProxyEvent> = {
            pathParameters: {
              projectId: 'new',
            },
            requestContext: {
              authorizer: {
                claims: {
                  sub: projectData.userId,
                },
              },
            } as any,
            body: JSON.stringify({
              name: projectData.name,
              description: projectData.description,
            }),
          };

          // Execute
          const result = await handler(event as APIGatewayProxyEvent);

          // Verify: Should return 201 Created
          expect(result.statusCode).toBe(201);

          const body = JSON.parse(result.body);
          expect(body.projectId).toBeDefined();
          expect(body.name).toBe(projectData.name.trim());
          expect(body.createdAt).toBeDefined();
          expect(body.updatedAt).toBeDefined();

          // Verify DynamoDB PutCommand was called
          const ddbCalls = ddbMock.commandCalls(PutCommand);
          expect(ddbCalls.length).toBe(1);

          const ddbItem = ddbCalls[0].args[0].input.Item;
          expect(ddbItem).toBeDefined();
          expect(ddbItem?.userId).toBe(projectData.userId);
          expect(ddbItem?.projectId).toBeDefined();
          expect(ddbItem?.name).toBe(projectData.name.trim());
          expect(ddbItem?.s3Key).toBe(`${projectData.userId}/${ddbItem?.projectId}/floorspace.json`);

          // Verify S3 PutObjectCommand was called to initialize empty floorspace JSON
          const s3Calls = s3Mock.commandCalls(PutObjectCommand);
          expect(s3Calls.length).toBe(1);

          const s3Params = s3Calls[0].args[0].input;
          // The bucket name comes from environment variable
          expect(s3Params.Bucket).toBeDefined();
          expect(s3Params.Key).toBe(`${projectData.userId}/${ddbItem?.projectId}/floorspace.json`);
          expect(s3Params.ContentType).toBe('application/json');

          // Verify the S3 body contains valid empty floorspace JSON
          const s3Body = s3Params.Body as string;
          const floorspaceJson = JSON.parse(s3Body);
          expect(floorspaceJson.version).toBeDefined();
          expect(floorspaceJson.stories).toEqual([]);
          expect(floorspaceJson.building_units).toEqual([]);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('Property 9 (validation): For any invalid project information (empty name), system rejects creation', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          userId: fc.uuid(),
          name: fc.constantFrom('', '   ', '\t\n'),
        }),
        async (projectData) => {
          // Create event with invalid name
          const event: Partial<APIGatewayProxyEvent> = {
            pathParameters: {
              projectId: 'new',
            },
            requestContext: {
              authorizer: {
                claims: {
                  sub: projectData.userId,
                },
              },
            } as any,
            body: JSON.stringify({
              name: projectData.name,
            }),
          };

          // Execute
          const result = await handler(event as APIGatewayProxyEvent);

          // Verify: Should return 400 Bad Request
          expect(result.statusCode).toBe(400);

          const body = JSON.parse(result.body);
          expect(body.error.code).toBe('VALIDATION_ERROR');
        }
      ),
      { numRuns: 50 }
    );
  });
});
