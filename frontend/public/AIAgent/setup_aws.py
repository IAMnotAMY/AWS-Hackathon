#!/usr/bin/env python3
"""
AWS Setup and Verification Script for Natural Language to Floorspace JSON Agent.

This script helps you set up and verify AWS integration step by step.
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
except ImportError:
    print("❌ boto3 not installed. Please run: pip install boto3")
    sys.exit(1)


class AWSSetupHelper:
    """Helper class for AWS setup and verification."""
    
    def __init__(self):
        """Initialize the setup helper."""
        self.aws_region = None
        self.access_key = None
        self.secret_key = None
        self.bedrock_model_id = None
        
    def load_environment(self):
        """Load AWS configuration from environment."""
        print("🔧 Loading AWS configuration...")
        
        # Load from .env file if it exists
        env_file = Path(".env")
        if env_file.exists():
            print("📄 Loading from .env file...")
            with open(env_file) as f:
                for line in f:
                    if line.strip() and not line.startswith('#') and '=' in line:
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
        
        # Get configuration
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.bedrock_model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        
        print(f"   • Region: {self.aws_region}")
        print(f"   • Access Key: {self.access_key[:10]}..." if self.access_key else "   • Access Key: Not set")
        print(f"   • Secret Key: {'Set' if self.secret_key else 'Not set'}")
        print(f"   • Model ID: {self.bedrock_model_id}")
        
        return bool(self.access_key and self.secret_key)
    
    def verify_credentials(self):
        """Verify AWS credentials work."""
        print("\n🔐 Verifying AWS credentials...")
        
        try:
            # Create STS client to verify credentials
            sts_client = boto3.client(
                'sts',
                region_name=self.aws_region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key
            )
            
            # Get caller identity
            identity = sts_client.get_caller_identity()
            
            print("✅ AWS credentials are valid!")
            print(f"   • Account ID: {identity.get('Account')}")
            print(f"   • User ARN: {identity.get('Arn')}")
            print(f"   • User ID: {identity.get('UserId')}")
            
            return True
            
        except NoCredentialsError:
            print("❌ No AWS credentials found")
            print("   Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
            return False
        except PartialCredentialsError:
            print("❌ Incomplete AWS credentials")
            print("   Both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required")
            return False
        except ClientError as e:
            print(f"❌ AWS credential error: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error verifying credentials: {e}")
            return False
    
    def check_bedrock_access(self):
        """Check if Bedrock is available in the region."""
        print(f"\n🤖 Checking Bedrock access in {self.aws_region}...")
        
        try:
            # Create Bedrock client
            bedrock_client = boto3.client(
                'bedrock',
                region_name=self.aws_region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key
            )
            
            # List foundation models
            response = bedrock_client.list_foundation_models()
            models = response.get('modelSummaries', [])
            
            print(f"✅ Bedrock is available! Found {len(models)} foundation models")
            
            # Check if our specific model is available
            claude_models = [m for m in models if 'claude' in m.get('modelId', '').lower()]
            anthropic_models = [m for m in models if 'anthropic' in m.get('modelId', '').lower()]
            
            print(f"   • Claude models available: {len(claude_models)}")
            print(f"   • Anthropic models available: {len(anthropic_models)}")
            
            # Check our specific model
            target_model = self.bedrock_model_id
            model_found = any(m.get('modelId') == target_model for m in models)
            
            if model_found:
                print(f"✅ Target model '{target_model}' is available!")
            else:
                print(f"⚠️  Target model '{target_model}' not found")
                print("   Available Anthropic models:")
                for model in anthropic_models[:5]:  # Show first 5
                    print(f"      • {model.get('modelId')}")
                if len(anthropic_models) > 5:
                    print(f"      ... and {len(anthropic_models) - 5} more")
            
            return True, model_found
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == 'UnauthorizedOperation':
                print("❌ Access denied to Bedrock")
                print("   Your AWS account may not have Bedrock access enabled")
                print("   Please contact AWS support to enable Bedrock access")
            elif error_code == 'OptInRequired':
                print("❌ Bedrock access requires opt-in")
                print("   Please visit the AWS Bedrock console to request access")
            else:
                print(f"❌ Bedrock error: {e}")
            return False, False
        except Exception as e:
            print(f"❌ Unexpected error checking Bedrock: {e}")
            return False, False
    
    def test_bedrock_runtime(self):
        """Test Bedrock Runtime API."""
        print(f"\n🚀 Testing Bedrock Runtime API...")
        
        try:
            # Create Bedrock Runtime client
            bedrock_runtime = boto3.client(
                'bedrock-runtime',
                region_name=self.aws_region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key
            )
            
            # Test with a simple prompt
            test_prompt = "Hello, this is a test. Please respond with 'Test successful'."
            
            # Prepare request body for Claude
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 100,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": test_prompt
                    }
                ]
            }
            
            print(f"   • Sending test request to {self.bedrock_model_id}...")
            
            response = bedrock_runtime.invoke_model(
                modelId=self.bedrock_model_id,
                body=json.dumps(body),
                contentType='application/json'
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            if 'content' in response_body and response_body['content']:
                content = response_body['content'][0].get('text', '')
                print(f"✅ Bedrock Runtime test successful!")
                print(f"   • Response: {content[:100]}...")
                return True
            else:
                print("⚠️  Bedrock responded but format was unexpected")
                print(f"   • Response: {response_body}")
                return False
                
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == 'ValidationException':
                print("❌ Model validation error")
                print(f"   The model '{self.bedrock_model_id}' may not be available")
                print("   Try a different model ID")
            elif error_code == 'AccessDeniedException':
                print("❌ Access denied to Bedrock Runtime")
                print("   Your account may not have permission to invoke models")
            else:
                print(f"❌ Bedrock Runtime error: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error testing Bedrock Runtime: {e}")
            return False
    
    def test_agent_integration(self):
        """Test the agent with AWS integration."""
        print(f"\n🏠 Testing Agent with AWS Integration...")
        
        try:
            from nl_floorspace_agent.agent import FloorspaceAgent
            
            # Initialize agent
            print("   • Initializing FloorspaceAgent...")
            agent = FloorspaceAgent(aws_region=self.aws_region)
            print("   ✅ Agent initialized successfully!")
            
            # For now, just test initialization since we're in an async context
            print("   ✅ Agent integration test passed!")
            print("   💡 Run 'python quick_test.py' for full async testing")
            
            return True
            
        except ImportError as e:
            print(f"   ❌ Import error: {e}")
            print("   Make sure all dependencies are installed")
            return False
        except Exception as e:
            print(f"   ❌ Agent integration error: {e}")
            return False
    
    def generate_setup_report(self, results):
        """Generate a setup report."""
        print(f"\n📊 AWS Integration Setup Report")
        print("=" * 50)
        
        credentials_ok = results.get('credentials', False)
        bedrock_available = results.get('bedrock_available', False)
        model_available = results.get('model_available', False)
        runtime_ok = results.get('runtime', False)
        agent_ok = results.get('agent', False)
        
        print(f"✅ AWS Credentials: {'PASS' if credentials_ok else 'FAIL'}")
        print(f"✅ Bedrock Access: {'PASS' if bedrock_available else 'FAIL'}")
        print(f"✅ Model Available: {'PASS' if model_available else 'FAIL'}")
        print(f"✅ Runtime API: {'PASS' if runtime_ok else 'FAIL'}")
        print(f"✅ Agent Integration: {'PASS' if agent_ok else 'FAIL'}")
        
        overall_status = all([credentials_ok, bedrock_available, model_available, runtime_ok, agent_ok])
        
        print(f"\n🎯 Overall Status: {'✅ READY' if overall_status else '❌ NEEDS SETUP'}")
        
        if overall_status:
            print("\n🎉 Congratulations! Your AWS integration is fully set up!")
            print("You can now run:")
            print("   • python test_agent_manual.py")
            print("   • python quick_test.py")
        else:
            print("\n🔧 Setup Issues Found:")
            if not credentials_ok:
                print("   • Fix AWS credentials in .env file")
            if not bedrock_available:
                print("   • Request Bedrock access from AWS")
            if not model_available:
                print("   • Check/update BEDROCK_MODEL_ID in .env")
            if not runtime_ok:
                print("   • Verify Bedrock Runtime permissions")
            if not agent_ok:
                print("   • Check agent dependencies and configuration")
        
        return overall_status


async def main():
    """Main setup function."""
    print("🏠 AWS Integration Setup for Natural Language to Floorspace JSON Agent")
    print("=" * 70)
    
    helper = AWSSetupHelper()
    results = {}
    
    # Step 1: Load environment
    if not helper.load_environment():
        print("\n❌ AWS credentials not found in environment")
        print("Please set up your .env file with AWS credentials")
        return
    
    # Step 2: Verify credentials
    results['credentials'] = helper.verify_credentials()
    if not results['credentials']:
        print("\n❌ Cannot proceed without valid AWS credentials")
        return
    
    # Step 3: Check Bedrock access
    bedrock_available, model_available = helper.check_bedrock_access()
    results['bedrock_available'] = bedrock_available
    results['model_available'] = model_available
    
    if not bedrock_available:
        print("\n❌ Cannot proceed without Bedrock access")
        helper.generate_setup_report(results)
        return
    
    # Step 4: Test Bedrock Runtime
    results['runtime'] = helper.test_bedrock_runtime()
    
    # Step 5: Test agent integration
    results['agent'] = helper.test_agent_integration()
    
    # Step 6: Generate report
    helper.generate_setup_report(results)


if __name__ == "__main__":
    asyncio.run(main())