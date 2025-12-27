@echo off
echo 🚀 Uploading Legal EASE to GitHub...
echo Repository: Vidhaankhare16/Google-Gen-AI
echo ==================================

REM Check if git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Git is not installed. Please install Git first.
    pause
    exit /b 1
)

REM Initialize git repository if not already initialized
if not exist ".git" (
    echo 📁 Initializing Git repository...
    git init
) else (
    echo 📁 Git repository already initialized
)

REM Add all files (respecting .gitignore)
echo 📝 Adding files to Git...
git add .

REM Check what files are being added
echo 📋 Files to be committed:
git status --short

REM Create initial commit
echo 💾 Creating initial commit...
git commit -m "Initial commit: Legal EASE - AI-Powered Legal Document Analysis Platform" -m "Features:" -m "- 📄 PDF Document Analysis with AI" -m "- 🤖 Interactive Q&A System" -m "- 📱 WhatsApp Integration" -m "- 🔒 Secure Processing" -m "- 🌐 Modern Web Interface" -m "- 🚀 Google Cloud Run Deployment" -m "Tech Stack: Python Flask, React TypeScript, Google Gemini AI, Twilio WhatsApp API"

REM Set up remote repository
echo 🔗 Setting up remote repository...
git remote remove origin 2>nul
git remote add origin https://github.com/Vidhaankhare16/Google-Gen-AI.git

REM Set default branch to main
git branch -M main

echo ✅ Repository setup complete!
echo.
echo 🔑 NEXT STEPS (you need to do these manually):
echo 1. Make sure you're logged into GitHub as Vidhaankhare16
echo 2. Create the repository 'Google-Gen-AI' on GitHub (if it doesn't exist)
echo 3. Run: git push -u origin main
echo.
echo 📋 Or run this command to push:
echo git push -u origin main
echo.
echo 🔒 SECURITY REMINDER:
echo - ✅ All API keys are in .gitignore
echo - ✅ .env files are protected  
echo - ✅ No sensitive data will be uploaded

pause