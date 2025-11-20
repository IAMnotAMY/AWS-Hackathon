import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as path from 'path';

export class FloorspaceInfrastructureStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Cognito User Pool for authentication
    const userPool = new cognito.UserPool(this, 'FloorspaceUserPool', {
      userPoolName: 'floorspace-user-pool',
      selfSignUpEnabled: true,
      signInAliases: {
        email: true,
      },
      autoVerify: {
        email: true,
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const userPoolClient = userPool.addClient('FloorspaceUserPoolClient', {
      authFlows: {
        userPassword: true,
        userSrp: true,
      },
    });

    // DynamoDB table for project metadata
    const projectsTable = new dynamodb.Table(this, 'ProjectsTable', {
      tableName: 'floorspace-projects',
      partitionKey: {
        name: 'userId',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'projectId',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // S3 bucket for floorspace JSON storage
    const floorspaceBucket = new s3.Bucket(this, 'FloorspaceBucket', {
      bucketName: `floorspace-json-storage-${this.account}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      cors: [
        {
          allowedMethods: [
            s3.HttpMethods.GET,
            s3.HttpMethods.PUT,
            s3.HttpMethods.POST,
            s3.HttpMethods.DELETE,
          ],
          allowedOrigins: ['*'], // Update with specific frontend domain in production
          allowedHeaders: ['*'],
        },
      ],
    });

    // Lambda execution role
    const lambdaRole = new iam.Role(this, 'LambdaExecutionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    // Grant Lambda permissions to DynamoDB and S3
    projectsTable.grantReadWriteData(lambdaRole);
    floorspaceBucket.grantReadWrite(lambdaRole);

    // Lambda Functions
    const getProjectFunction = new lambda.Function(this, 'GetProjectFunction', {
      functionName: 'floorspace-getProject',
      runtime: lambda.Runtime.NODEJS_18_X,
      handler: 'getProject.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../backend/dist/functions')),
      role: lambdaRole,
      environment: {
        TABLE_NAME: projectsTable.tableName,
        BUCKET_NAME: floorspaceBucket.bucketName,
      },
      timeout: cdk.Duration.seconds(30),
    });

    const listProjectsFunction = new lambda.Function(this, 'ListProjectsFunction', {
      functionName: 'floorspace-listProjects',
      runtime: lambda.Runtime.NODEJS_18_X,
      handler: 'listProjects.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../backend/dist/functions')),
      role: lambdaRole,
      environment: {
        TABLE_NAME: projectsTable.tableName,
      },
      timeout: cdk.Duration.seconds(30),
    });

    const createUpdateProjectFunction = new lambda.Function(this, 'CreateUpdateProjectFunction', {
      functionName: 'floorspace-createUpdateProject',
      runtime: lambda.Runtime.NODEJS_18_X,
      handler: 'createUpdateProject.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../backend/dist/functions')),
      role: lambdaRole,
      environment: {
        TABLE_NAME: projectsTable.tableName,
        BUCKET_NAME: floorspaceBucket.bucketName,
      },
      timeout: cdk.Duration.seconds(30),
    });

    const deleteProjectFunction = new lambda.Function(this, 'DeleteProjectFunction', {
      functionName: 'floorspace-deleteProject',
      runtime: lambda.Runtime.NODEJS_18_X,
      handler: 'deleteProject.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../backend/dist/functions')),
      role: lambdaRole,
      environment: {
        TABLE_NAME: projectsTable.tableName,
        BUCKET_NAME: floorspaceBucket.bucketName,
      },
      timeout: cdk.Duration.seconds(30),
    });

    const uploadFloorspaceFunction = new lambda.Function(this, 'UploadFloorspaceFunction', {
      functionName: 'floorspace-uploadFloorspace',
      runtime: lambda.Runtime.NODEJS_18_X,
      handler: 'uploadFloorspace.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../backend/dist/functions')),
      role: lambdaRole,
      environment: {
        TABLE_NAME: projectsTable.tableName,
        BUCKET_NAME: floorspaceBucket.bucketName,
      },
      timeout: cdk.Duration.seconds(30),
    });

    // API Gateway with Cognito authorizer
    const api = new apigateway.RestApi(this, 'FloorspaceApi', {
      restApiName: 'Floorspace API',
      description: 'API for Floorspace 3D Viewer',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization',
          'X-Api-Key',
          'X-Amz-Security-Token',
        ],
      },
    });

    const authorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'CognitoAuthorizer', {
      cognitoUserPools: [userPool],
    });

    // API Gateway Resources and Methods
    
    // /projects resource
    const projects = api.root.addResource('projects');
    
    // GET /projects - List all projects for user
    projects.addMethod(
      'GET',
      new apigateway.LambdaIntegration(listProjectsFunction),
      {
        authorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
      }
    );

    // /projects/{projectId} resource
    const project = projects.addResource('{projectId}');
    
    // GET /projects/{projectId} - Get specific project
    project.addMethod(
      'GET',
      new apigateway.LambdaIntegration(getProjectFunction),
      {
        authorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
      }
    );

    // POST /projects/{projectId} - Create or update project
    project.addMethod(
      'POST',
      new apigateway.LambdaIntegration(createUpdateProjectFunction),
      {
        authorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
      }
    );

    // DELETE /projects/{projectId} - Delete project
    project.addMethod(
      'DELETE',
      new apigateway.LambdaIntegration(deleteProjectFunction),
      {
        authorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
      }
    );

    // /projects/{projectId}/upload resource
    const upload = project.addResource('upload');
    
    // POST /projects/{projectId}/upload - Upload floorspace JSON
    upload.addMethod(
      'POST',
      new apigateway.LambdaIntegration(uploadFloorspaceFunction),
      {
        authorizer,
        authorizationType: apigateway.AuthorizationType.COGNITO,
      }
    );

    // Export resources for use in Lambda functions
    new cdk.CfnOutput(this, 'LambdaRoleArn', {
      value: lambdaRole.roleArn,
      description: 'Lambda Execution Role ARN',
      exportName: 'FloorspaceLambdaRoleArn',
    });

    new cdk.CfnOutput(this, 'AuthorizerId', {
      value: authorizer.authorizerId,
      description: 'Cognito Authorizer ID',
      exportName: 'FloorspaceAuthorizerId',
    });

    // Output values
    new cdk.CfnOutput(this, 'UserPoolId', {
      value: userPool.userPoolId,
      description: 'Cognito User Pool ID',
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: userPoolClient.userPoolClientId,
      description: 'Cognito User Pool Client ID',
    });

    new cdk.CfnOutput(this, 'ApiUrl', {
      value: api.url,
      description: 'API Gateway URL',
    });

    new cdk.CfnOutput(this, 'BucketName', {
      value: floorspaceBucket.bucketName,
      description: 'S3 Bucket Name',
    });

    new cdk.CfnOutput(this, 'TableName', {
      value: projectsTable.tableName,
      description: 'DynamoDB Table Name',
    });
  }
}
