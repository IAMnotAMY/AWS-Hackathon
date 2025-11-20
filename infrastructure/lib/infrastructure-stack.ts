import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';

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

    // Placeholder for Lambda functions (to be implemented in later tasks)
    // Lambda functions will be added here

    // API Gateway with Cognito authorizer
    const api = new apigateway.RestApi(this, 'FloorspaceApi', {
      restApiName: 'Floorspace API',
      description: 'API for Floorspace 3D Viewer',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'Authorization'],
      },
    });

    const authorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'CognitoAuthorizer', {
      cognitoUserPools: [userPool],
    });

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
