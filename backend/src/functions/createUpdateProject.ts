import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, PutCommand, GetCommand } from '@aws-sdk/lib-dynamodb';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { randomUUID } from 'crypto';

const dynamoClient = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(dynamoClient);
const s3Client = new S3Client({});

const TABLE_NAME = process.env.TABLE_NAME || 'floorspace-projects';
const BUCKET_NAME = process.env.BUCKET_NAME || '';

interface ProjectInput {
  name: string;
  description?: string;
}

export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
  try {
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

    // Parse request body
    if (!event.body) {
      return {
        statusCode: 400,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error: {
            code: 'VALIDATION_ERROR',
            message: 'Request body is required',
          },
        }),
      };
    }

    let projectInput: ProjectInput;
    try {
      projectInput = JSON.parse(event.body);
    } catch (error) {
      return {
        statusCode: 400,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error: {
            code: 'VALIDATION_ERROR',
            message: 'Invalid JSON in request body',
          },
        }),
      };
    }

    // Validate project name
    if (!projectInput.name || projectInput.name.trim().length === 0) {
      return {
        statusCode: 400,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error: {
            code: 'VALIDATION_ERROR',
            message: 'Project name is required',
          },
        }),
      };
    }

    // Parse projectId from path parameters or generate new one
    let projectId = event.pathParameters?.projectId;
    let isNewProject = false;
    let createdAt: string;

    if (!projectId || projectId === 'new') {
      // Generate unique projectId for new project
      projectId = randomUUID();
      isNewProject = true;
      createdAt = new Date().toISOString();
    } else {
      // Check if project exists for update
      const existingProject = await docClient.send(
        new GetCommand({
          TableName: TABLE_NAME,
          Key: {
            userId,
            projectId,
          },
        })
      );

      if (existingProject.Item) {
        // Verify ownership
        if (existingProject.Item.userId !== userId) {
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
        createdAt = existingProject.Item.createdAt;
      } else {
        // Project doesn't exist, treat as new
        isNewProject = true;
        createdAt = new Date().toISOString();
      }
    }

    const updatedAt = new Date().toISOString();
    const s3Key = `${userId}/${projectId}/floorspace.json`;

    // Create or update DynamoDB record
    await docClient.send(
      new PutCommand({
        TableName: TABLE_NAME,
        Item: {
          userId,
          projectId,
          name: projectInput.name.trim(),
          description: projectInput.description?.trim() || '',
          createdAt,
          updatedAt,
          s3Key,
        },
      })
    );

    // If new project, initialize empty floorspace JSON in S3
    if (isNewProject) {
      const emptyFloorspaceJson = {
        version: '1.0',
        stories: [],
        building_units: [],
        thermal_zones: [],
        space_types: [],
        construction_sets: [],
      };

      await s3Client.send(
        new PutObjectCommand({
          Bucket: BUCKET_NAME,
          Key: s3Key,
          Body: JSON.stringify(emptyFloorspaceJson),
          ContentType: 'application/json',
        })
      );
    }

    // Return project details
    return {
      statusCode: isNewProject ? 201 : 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        projectId,
        name: projectInput.name.trim(),
        description: projectInput.description?.trim() || '',
        createdAt,
        updatedAt,
      }),
    };
  } catch (error) {
    console.error('Error in createUpdateProject:', error);
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
