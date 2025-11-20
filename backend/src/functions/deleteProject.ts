import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, GetCommand, DeleteCommand } from '@aws-sdk/lib-dynamodb';
import { S3Client, DeleteObjectCommand } from '@aws-sdk/client-s3';

const dynamoClient = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(dynamoClient);
const s3Client = new S3Client({});

const TABLE_NAME = process.env.TABLE_NAME || 'floorspace-projects';
const BUCKET_NAME = process.env.BUCKET_NAME || '';

interface Project {
  userId: string;
  projectId: string;
  name: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
  s3Key: string;
}

export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
  try {
    // Parse projectId from path parameters
    const projectId = event.pathParameters?.projectId;
    if (!projectId) {
      return {
        statusCode: 400,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error: {
            code: 'VALIDATION_ERROR',
            message: 'Project ID is required',
          },
        }),
      };
    }

    // Extract userId from authorizer context
    const userId = event.requestContext.authorizer?.claims?.sub;
    if (!userId) {
      return {
        statusCode: 401,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error: {
            code: 'UNAUTHORIZED',
            message: 'User ID not found in token',
          },
        }),
      };
    }

    // Get project from DynamoDB to verify ownership
    const result = await docClient.send(
      new GetCommand({
        TableName: TABLE_NAME,
        Key: {
          userId,
          projectId,
        },
      })
    );

    // Check if project exists
    if (!result.Item) {
      return {
        statusCode: 404,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error: {
            code: 'NOT_FOUND',
            message: 'Project not found',
          },
        }),
      };
    }

    const project = result.Item as Project;

    // Verify user ownership
    if (project.userId !== userId) {
      return {
        statusCode: 403,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error: {
            code: 'FORBIDDEN',
            message: "You don't have permission to access this resource",
          },
        }),
      };
    }

    // Delete S3 object
    const s3Key = project.s3Key || `${userId}/${projectId}/floorspace.json`;
    await s3Client.send(
      new DeleteObjectCommand({
        Bucket: BUCKET_NAME,
        Key: s3Key,
      })
    );

    // Delete DynamoDB record
    await docClient.send(
      new DeleteCommand({
        TableName: TABLE_NAME,
        Key: {
          userId,
          projectId,
        },
      })
    );

    // Return success status
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        success: true,
        message: 'Project deleted successfully',
      }),
    };
  } catch (error) {
    console.error('Error in deleteProject:', error);
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: {
          code: 'INTERNAL_ERROR',
          message: 'An unexpected error occurred',
        },
      }),
    };
  }
};
