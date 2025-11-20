@echo off
echo ========================================
echo   Floorspace 3D Viewer - AWS Deployment
echo ========================================
echo.

REM Build backend
echo Step 1: Building backend Lambda functions...
cd backend
call npm run build
if %errorlevel% neq 0 (
    echo ERROR: Backend build failed
    exit /b 1
)
echo Backend built successfully
echo.

REM Deploy infrastructure
echo Step 2: Deploying infrastructure to AWS...
cd ..\infrastructure
call npm run deploy -- --require-approval never

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   Deployment Successful!
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Copy the output values above
    echo 2. Update frontend/.env with these values
    echo 3. Check your AWS Console
) else (
    echo.
    echo ERROR: Deployment failed
    echo Check the error messages above
    exit /b 1
)

cd ..
