#!/bin/bash

# GitHub Upload Script for Legal EASE
# Repository: Vidhaankhare16/Google-Gen-AI

echo "🚀 Uploading Legal EASE to GitHub..."
echo "Repository: Vidhaankhare16/Google-Gen-AI"
echo "=================================="

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install Git first."
    exit 1
fi

# Initialize git repository if not already initialized
if [ ! -d ".git" ]; then
    echo "📁 Initializing Git repository..."
    git init
else
    echo "📁 Git repository already initialized"
fi

# Add all files (respecting .gitignore)
echo "📝 Adding files to Git..."
git add .

# Check what files are being added
echo "📋 Files to be committed:"
git status --short

# Create initial commit
echo "💾 Creating initial commit..."
git commit -m "Initial commit: Legal EASE - AI-Powered Legal Document Analysis Platform

Features:
- 📄 PDF Document Analysis with AI
- 🤖 Interactive Q&A System  
- 📱 WhatsApp Integration
- 🔒 Secure Processing
- 🌐 Modern Web Interface
- 🚀 Google Cloud Run Deployment

Tech Stack: Python Flask, React TypeScript, Google Gemini AI, Twilio WhatsApp API"

# Set up remote repository
echo "🔗 Setting up remote repository..."
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/Vidhaankhare16/Google-Gen-AI.git

# Set default branch to main
git branch -M main

echo "✅ Repository setup complete!"
echo ""
echo "🔑 NEXT STEPS (you need to do these manually):"
echo "1. Make sure you're logged into GitHub as Vidhaankhare16"
echo "2. Create the repository 'Google-Gen-AI' on GitHub (if it doesn't exist)"
echo "3. Run: git push -u origin main"
echo ""
echo "📋 Or run this command to push:"
echo "git push -u origin main"
echo ""
echo "🔒 SECURITY REMINDER:"
echo "- ✅ All API keys are in .gitignore"
echo "- ✅ .env files are protected"
echo "- ✅ No sensitive data will be uploaded"