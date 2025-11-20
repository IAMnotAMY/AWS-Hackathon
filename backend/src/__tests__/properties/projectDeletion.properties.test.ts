import * as fc from 'fast-check';
import { handler } from '../../functions/deleteProject';
import { APIGatewayProxyEvent } from 'aws-lambda';
import { DynamoDBDocumentClient, GetCommand, DeleteCommand } from '@aws-sdk/lib-dynamodb';
import { S3Client, DeleteObjectCommand } from '@aws-sdk/client-s3';
import { mockClient } from 'aws-sdk-client-mock';

// Mock AWS SDK clients
const ddbMock = mockClient(DynamoDBDocumentClient);
const s3Mock = mockClient(S3Client);

describe('Project Deletion - Property Tests', () => {
  beforeEach(() => {
    ddbMock.reset();
    s3Mock.reset();
    process.env.TABLE_NAME = 'floorspace-projects';
    process.env.BUCKET_NAME = 'test-bucket';
  });

  /**
   * Feature: floorspace-3d-viewer, Property 11: Project deletion cleanup
   * Validates: Requirements 7.2, 7.3, 8.3, 10.4
   */
  test('Property 11: For any project deletion, system removes both DynamoDB record AND associated S3 file', async () => {
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
          // Reset mocks for each iteration
          ddbMock.reset();
          s3Mock.reset();

          const s3Key = `${project.userId}/${project.projectId}/floorspace.json`;

          // Setup: Mock DynamoDB GetCommand to return the project
          ddbMock.on(GetCommand).resolves({
            Item: {
              userId: project.userId,
              projectId: project.projectId,
              name: project.name,
              createdAt: project.createdAt,
              updatedAt: project.updatedAt,
              s3Key,
            },
          });

          // Mock DynamoDB DeleteCommand
          ddbMock.on(DeleteCommand).resolves({});

          // Mock S3 DeleteObjectCommand
          s3Mock.on(DeleteObjectCommand).resolves({});

          // Create event for deletion
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

          // Verify: Should return 200 Success
          expect(result.statusCode).toBe(200);

          const body = JSON.parse(result.body);
          expect(body.success).toBe(true);

          // Verify DynamoDB DeleteCommand was called
          const ddbDeleteCalls = ddbMock.commandCalls(DeleteCommand);
          expect(ddbDeleteCalls.length).toBe(1);

          const ddbDeleteParams = ddbDeleteCalls[0].args[0].input;
          expect(ddbDeleteParams.Key).toEqual({
            userId: project.userId,
            projectId: project.projectId,
          });

          // Verify S3 DeleteObjectCommand was called
          const s3DeleteCalls = s3Mock.commandCalls(DeleteObjectCommand);
          expect(s3DeleteCalls.length).toBe(1);

          const s3DeleteParams = s3DeleteCalls[0].args[0].input;
          expect(s3DeleteParams.Key).toBe(s3Key);
        }
      ),
      { numRuns: 100 }
    );
  });

  test('Property 11 (ownership check): For any deletion attempt by non-owner, system rejects with 403', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          ownerId: fc.uuid(),
          requesterId: fc.uuid(),
          projectId: fc.uuid(),
          name: fc.string({ minLength: 1, maxLength: 100 }),
          createdAt: fc.date().map(d => d.toISOString()),
          updatedAt: fc.date().map(d => d.toISOString()),
        }),
        async (data) => {
          // Ensure requester is different from owner
          fc.pre(data.ownerId !== data.requesterId);

          // Reset mocks for each iteration
          ddbMock.reset();
          s3Mock.reset();

          const s3Key = `${data.ownerId}/${data.projectId}/floorspace.json`;

          // Setup: Mock DynamoDB GetCommand to return project owned by ownerId
          ddbMock.on(GetCommand).resolves({
            Item: {
              userId: data.ownerId,
              projectId: data.projectId,
              name: data.name,
              createdAt: data.createdAt,
              updatedAt: data.updatedAt,
              s3Key,
            },
          });

          // Create event with different userId (not the owner)
          const event: Partial<APIGatewayProxyEvent> = {
            pathParameters: {
              projectId: data.projectId,
            },
            requestContext: {
              authorizer: {
                claims: {
                  sub: data.requesterId,
                },
              },
            } as any,
          };

          // Execute
          const result = await handler(event as APIGatewayProxyEvent);

          // Verify: Should return 403 Forbidden
          expect(result.statusCode).toBe(403);

          const body = JSON.parse(result.body);
          expect(body.error.code).toBe('FORBIDDEN');

          // Verify no deletion occurred
          const ddbDeleteCalls = ddbMock.commandCalls(DeleteCommand);
          expect(ddbDeleteCalls.length).toBe(0);

          const s3DeleteCalls = s3Mock.commandCalls(DeleteObjectCommand);
          expect(s3DeleteCalls.length).toBe(0);
        }
      ),
      { numRuns: 100 }
    );
  });
});
