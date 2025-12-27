#!/bin/bash

# Google Cloud Platform setup script for Lexi Simplify
set -e

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}
REGION=${REGION:-"us-central1"}
SERVICE_ACCOUNT_NAME="lexi-simplify-sa"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 Setting up Google Cloud Platform for Lexi Simplify${NC}"

# Check if project ID is set
if [ "$PROJECT_ID" = "your-project-id" ]; then
    echo -e "${RED}❌ Please set GOOGLE_CLOUD_PROJECT environment variable${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service Account: $SERVICE_ACCOUNT_NAME"

# Set the project
echo -e "${YELLOW}🎯 Setting project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Create service account for the application
echo -e "${YELLOW}👤 Creating service account...${NC}"
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name="Lexi Simplify Service Account" \
    --description="Service account for Lexi Simplify application" || true

# Grant necessary permissions to the service account
echo -e "${YELLOW}🔐 Granting permissions...${NC}"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Create a secret for Gemini API key (optional)
echo -e "${YELLOW}🔑 Creating secret for Gemini API key...${NC}"
echo "Please enter your Gemini API key (or press Enter to skip):"
read -s GEMINI_API_KEY

if [ ! -z "$GEMINI_API_KEY" ]; then
    echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
        --data-file=- \
        --replication-policy="automatic" || true
    
    # Grant access to the secret
    gcloud secrets add-iam-policy-binding gemini-api-key \
        --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor"
    
    echo -e "${GREEN}✅ Gemini API key stored in Secret Manager${NC}"
else
    echo -e "${YELLOW}⚠️  Skipping Gemini API key setup. You can add it later.${NC}"
fi

# Set up Cloud Build trigger (optional)
echo -e "${YELLOW}🏗️  Setting up Cloud Build trigger...${NC}"
read -p "Do you want to set up automatic deployment with Cloud Build? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # This would require a connected repository
    echo -e "${YELLOW}ℹ️  To set up Cloud Build trigger:${NC}"
    echo "  1. Connect your repository to Cloud Build"
    echo "  2. Create a trigger using cloudbuild.yaml"
    echo "  3. Configure trigger to run on push to main branch"
fi

# Create a sample environment file
echo -e "${YELLOW}📝 Creating sample environment file...${NC}"
cat > .env.production << EOF
# Production environment variables for Lexi Simplify
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
VERTEX_AI_LOCATION=$REGION
FLASK_ENV=production
MAX_FILE_SIZE=10485760
SESSION_TIMEOUT=3600
PORT=8080

# Uncomment and set if using Gemini API directly
# GEMINI_API_KEY=your-gemini-api-key-here
EOF

echo -e "${GREEN}✅ Google Cloud Platform setup completed!${NC}"
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "  1. Review the .env.production file and update as needed"
echo "  2. Run ./deploy.sh to deploy the application"
echo "  3. Configure your domain and SSL certificate if needed"
echo "  4. Set up monitoring and alerting"

echo -e "${YELLOW}🔗 Useful commands:${NC}"
echo "  Deploy: ./deploy.sh"
echo "  View logs: gcloud run services logs tail lexi-simplify --region=$REGION"
echo "  Update service: gcloud run services update lexi-simplify --region=$REGION"