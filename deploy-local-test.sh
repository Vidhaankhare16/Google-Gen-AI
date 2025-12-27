#!/bin/bash

# Deploy Legal EASE to Google Cloud Run
# Make sure to set your environment variables first!

echo "🚀 Deploying Legal EASE to Google Cloud Run..."

# Check if required environment variables are set
if [ -z "$GEMINI_API_KEY" ] || [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "❌ Error: Required environment variables not set!"
    echo "Please set the following environment variables:"
    echo "  export GEMINI_API_KEY=your-gemini-api-key"
    echo "  export GOOGLE_CLOUD_PROJECT=your-gcp-project-id"
    echo "  export TWILIO_ACCOUNT_SID=your-twilio-account-sid (optional)"
    echo "  export TWILIO_AUTH_TOKEN=your-twilio-auth-token (optional)"
    exit 1
fi

gcloud run deploy lexi-simplify \
  --source . \
  --region us-central1 \
  --set-env-vars "GEMINI_API_KEY=$GEMINI_API_KEY,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,VERTEX_AI_LOCATION=us-central1,FLASK_ENV=production,MAX_FILE_SIZE=10485760,SESSION_TIMEOUT=3600,TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID:-demo},TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN:-demo},TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886" \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --timeout 300 \
  --concurrency 10 \
  --max-instances 10

echo "✅ Deployment complete!"
echo "🌐 Your Legal EASE app will be available at the URL shown above"