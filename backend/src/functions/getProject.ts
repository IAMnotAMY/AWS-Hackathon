import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, GetCommand } from '@aws-sdk/lib-dynamodb';
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

const dynamoClient = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(dynamoClient);
const s3Client = new S3Client({});

const TABLE_NAME = process.env.TABLE_NAME || 'floorspace-projects';
const BUCKET_NAME = process.env.BUCKET_NAME || '';

const CORS_HEADERS = {
  'Content-Type': 'application/json',
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
  'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
};

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
  // Handle OPTIONS preflight request
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers: CORS_HEADERS,
      body: '',
    };
  }

  try {
    // Parse projectId from path parameters
    const projectId = event.pathParameters?.projectId;
    if (!projectId) {
      return {
        statusCode: 400,
        headers: CORS_HEADERS,
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
        headers: CORS_HEADERS,
        body: JSON.stringify({
          error: {
            code: 'UNAUTHORIZED',
            message: 'User ID not found in token',
          },
        }),
      };
    }

    // Query DynamoDB for project
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
        headers: CORS_HEADERS,
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
        headers: CORS_HEADERS,
        body: JSON.stringify({
          error: {
            code: 'FORBIDDEN',
            message: "You don't have permission to access this resource",
          },
        }),
      };
    }

    // Generate presigned S3 URL
    const s3Key = project.s3Key || `${userId}/${projectId}/floorspace.json`;
    const command = new GetObjectCommand({
      Bucket: BUCKET_NAME,
      Key: s3Key,
    });

    const presignedUrl = await getSignedUrl(s3Client, command, { expiresIn: 900 }); // 15 minutes

    // Return project metadata with S3 URL
    return {
      statusCode: 200,
      headers: CORS_HEADERS,
      body: JSON.stringify({
        projectId: project.projectId,
        name: project.name,
        description: project.description,
        createdAt: project.createdAt,
        updatedAt: project.updatedAt,
        floorspaceUrl: presignedUrl,
      }),
    };
  } catch (error) {
    console.error('Error in getProject:', error);
    return {
      statusCode: 500,
      headers: CORS_HEADERS,
      body: JSON.stringify({
        error: {
          code: 'INTERNAL_ERROR',
          message: 'An unexpected error occurred',
        },
      }),
    };
  }
};
