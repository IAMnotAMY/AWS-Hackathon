#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { FloorspaceInfrastructureStack } from '../lib/infrastructure-stack';

const app = new cdk.App();
new FloorspaceInfrastructureStack(app, 'FloorspaceInfrastructureStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});
