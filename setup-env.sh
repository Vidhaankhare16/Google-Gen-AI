#!/bin/bash

# Environment Setup Script for Legal EASE
# This script helps you set up your environment variables

echo "🔧 Legal EASE Environment Setup"
echo "================================"

# Create backend .env file if it doesn't exist
if [ ! -f "backend/.env" ]; then
    echo "📝 Creating backend/.env file..."
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env from template"
else
    echo "ℹ️  backend/.env already exists"
fi

echo ""
echo "🔑 Please update the following files with your actual credentials:"
echo ""
echo "1. Edit backend/.env and set:"
echo "   - GEMINI_API_KEY=your-actual-gemini-api-key"
echo "   - GOOGLE_CLOUD_PROJECT=your-gcp-project-id"
echo "   - TWILIO_ACCOUNT_SID=your-twilio-sid (optional)"
echo "   - TWILIO_AUTH_TOKEN=your-twilio-token (optional)"
echo ""
echo "2. For deployment, set environment variables:"
echo "   export GEMINI_API_KEY=your-gemini-api-key"
echo "   export GOOGLE_CLOUD_PROJECT=your-gcp-project-id"
echo "   export TWILIO_ACCOUNT_SID=your-twilio-sid"
echo "   export TWILIO_AUTH_TOKEN=your-twilio-token"
echo ""
echo "3. Then run: ./deploy-local-test.sh"
echo ""
echo "⚠️  NEVER commit .env files or hardcode API keys!"
echo "✅ All sensitive files are already in .gitignore"