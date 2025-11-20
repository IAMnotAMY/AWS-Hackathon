# AWS CDK Deployment Script with Credentials
# This script helps you deploy the infrastructure with AWS credentials

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Floorspace 3D Viewer - AWS Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if AWS credentials are already configured
$awsConfigured = $false

# Check for AWS CLI
try {
    $awsVersion = aws --version 2>$null
    if ($awsVersion) {
        Write-Host "✓ AWS CLI is installed" -ForegroundColor Green
        
        # Test if credentials work
        try {
            $identity = aws sts get-caller-identity 2>$null | ConvertFrom-Json
            if ($identity) {
                Write-Host "✓ AWS credentials are configured" -ForegroundColor Green
                Write-Host "  Account: $($identity.Account)" -ForegroundColor Gray
                Write-Host "  User: $($identity.Arn)" -ForegroundColor Gray
                $awsConfigured = $true
            }
        } catch {
            Write-Host "✗ AWS credentials not configured via AWS CLI" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "✗ AWS CLI not installed" -ForegroundColor Yellow
}

# If not configured via AWS CLI, check environment variables
if (-not $awsConfigured) {
    if ($env:AWS_ACCESS_KEY_ID -and $env:AWS_SECRET_ACCESS_KEY) {
        Write-Host "✓ AWS credentials found in environment variables" -ForegroundColor Green
        $awsConfigured = $true
    }
}

# If still not configured, prompt user
if (-not $awsConfigured) {
    Write-Host ""
    Write-Host "AWS credentials are not configured." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please choose an option:" -ForegroundColor Yellow
    Write-Host "1. Set credentials as environment variables (for this session only)"
    Write-Host "2. Exit and configure AWS CLI manually (recommended)"
    Write-Host ""
    
    $choice = Read-Host "Enter your choice (1 or 2)"
    
    if ($choice -eq "1") {
        Write-Host ""
        Write-Host "Enter your AWS credentials:" -ForegroundColor Cyan
        $accessKey = Read-Host "AWS Access Key ID"
        $secretKey = Read-Host "AWS Secret Access Key" -AsSecureString
        $region = Read-Host "AWS Region (e.g., us-east-1)"
        
        # Convert SecureString to plain text
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secretKey)
        $secretKeyPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        
        # Set environment variables
        $env:AWS_ACCESS_KEY_ID = $accessKey
        $env:AWS_SECRET_ACCESS_KEY = $secretKeyPlain
        $env:AWS_DEFAULT_REGION = $region
        
        Write-Host "✓ Credentials set for this session" -ForegroundColor Green
        $awsConfigured = $true
    } else {
        Write-Host ""
        Write-Host "Please configure AWS CLI by running:" -ForegroundColor Yellow
        Write-Host "  aws configure" -ForegroundColor White
        Write-Host ""
        Write-Host "Then run this script again." -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Build backend
Write-Host "Step 1: Building backend Lambda functions..." -ForegroundColor Cyan
Set-Location backend
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Backend build failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Backend built successfully" -ForegroundColor Green
Write-Host ""

# Deploy infrastructure
Write-Host "Step 2: Deploying infrastructure to AWS..." -ForegroundColor Cyan
Set-Location ../infrastructure
npm run deploy -- --require-approval never

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✓ Deployment Successful!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Copy the output values above" -ForegroundColor White
    Write-Host "2. Update frontend/.env with these values" -ForegroundColor White
    Write-Host "3. Check your AWS Console to see the deployed resources" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "✗ Deployment failed" -ForegroundColor Red
    Write-Host "Check the error messages above for details" -ForegroundColor Yellow
    exit 1
}
