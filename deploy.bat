@echo off
REM Deployment script for Lexi Simplify to Google Cloud Run (Windows)
setlocal enabledelayedexpansion

REM Configuration
if "%GOOGLE_CLOUD_PROJECT%"=="" (
    set PROJECT_ID=your-project-id
) else (
    set PROJECT_ID=%GOOGLE_CLOUD_PROJECT%
)

if "%REGION%"=="" (
    set REGION=us-central1
) else (
    set REGION=%REGION%
)

set SERVICE_NAME=lexi-simplify
set IMAGE_NAME=gcr.io/%PROJECT_ID%/%SERVICE_NAME%

echo 🚀 Deploying Lexi Simplify to Google Cloud Run

REM Check if required tools are installed
where gcloud >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ gcloud CLI is required but not installed.
    exit /b 1
)

where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Docker is required but not installed.
    exit /b 1
)

REM Check if project ID is set
if "%PROJECT_ID%"=="your-project-id" (
    echo ❌ Please set GOOGLE_CLOUD_PROJECT environment variable
    exit /b 1
)

echo 📋 Configuration:
echo   Project ID: %PROJECT_ID%
echo   Region: %REGION%
echo   Service: %SERVICE_NAME%
echo   Image: %IMAGE_NAME%

REM Set the project
echo 🎯 Setting project...
gcloud config set project %PROJECT_ID%

REM Enable required APIs
echo 🔧 Enabling required APIs...
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable aiplatform.googleapis.com

REM Build and push the Docker image
echo 🏗️ Building Docker image...
docker build -t %IMAGE_NAME%:latest .

echo 📤 Pushing image to Container Registry...
docker push %IMAGE_NAME%:latest

REM Deploy to Cloud Run
echo 🚀 Deploying to Cloud Run...
gcloud run deploy %SERVICE_NAME% ^
    --image %IMAGE_NAME%:latest ^
    --region %REGION% ^
    --platform managed ^
    --allow-unauthenticated ^
    --memory 2Gi ^
    --cpu 1 ^
    --timeout 300 ^
    --concurrency 10 ^
    --max-instances 10 ^
    --set-env-vars "FLASK_ENV=production,MAX_FILE_SIZE=10485760,SESSION_TIMEOUT=3600" ^
    --set-env-vars "GOOGLE_CLOUD_PROJECT=%PROJECT_ID%,VERTEX_AI_LOCATION=%REGION%"

REM Get the service URL
for /f "tokens=*" %%i in ('gcloud run services describe %SERVICE_NAME% --region %REGION% --format "value(status.url)"') do set SERVICE_URL=%%i

echo ✅ Deployment completed successfully!
echo 🌐 Service URL: %SERVICE_URL%
echo 📝 Next steps:
echo   1. Set up your Gemini API key in Cloud Run environment variables
echo   2. Configure service account permissions for Vertex AI
echo   3. Test the deployment by visiting: %SERVICE_URL%

pause