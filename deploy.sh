#!/bin/bash

# Deployment script for Lexi Simplify to Google Cloud Run
set -e

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="lexi-simplify"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying Lexi Simplify to Google Cloud Run${NC}"

# Check if required tools are installed
command -v gcloud >/dev/null 2>&1 || { echo -e "${RED}❌ gcloud CLI is required but not installed.${NC}" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo -e "${RED}❌ Docker is required but not installed.${NC}" >&2; exit 1; }

# Check if project ID is set
if [ "$PROJECT_ID" = "your-project-id" ]; then
    echo -e "${RED}❌ Please set GOOGLE_CLOUD_PROJECT environment variable${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service: $SERVICE_NAME"
echo "  Image: $IMAGE_NAME"

# Authenticate with Google Cloud (if needed)
echo -e "${YELLOW}🔐 Checking authentication...${NC}"
gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 > /dev/null || {
    echo -e "${YELLOW}Please authenticate with Google Cloud:${NC}"
    gcloud auth login
}

# Set the project
echo -e "${YELLOW}🎯 Setting project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable aiplatform.googleapis.com

# Build and push the Docker image
echo -e "${YELLOW}🏗️  Building Docker image...${NC}"
docker build -t $IMAGE_NAME:latest .

echo -e "${YELLOW}📤 Pushing image to Container Registry...${NC}"
docker push $IMAGE_NAME:latest

# Deploy to Cloud Run
echo -e "${YELLOW}🚀 Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME:latest \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 1 \
    --timeout 300 \
    --concurrency 10 \
    --max-instances 10 \
    --set-env-vars "FLASK_ENV=production,MAX_FILE_SIZE=10485760,SESSION_TIMEOUT=3600" \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,VERTEX_AI_LOCATION=$REGION"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Service URL: $SERVICE_URL${NC}"
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "  1. Set up your Gemini API key in Cloud Run environment variables"
echo "  2. Configure service account permissions for Vertex AI"
echo "  3. Test the deployment by visiting: $SERVICE_URL"

# Optional: Open the service URL
read -p "Open the service URL in your browser? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v open >/dev/null 2>&1; then
        open $SERVICE_URL
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open $SERVICE_URL
    else
        echo "Please open $SERVICE_URL in your browser"
    fi
fi