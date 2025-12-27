#!/usr/bin/env python3
"""
Deployment readiness check for Lexi Simplify
Verifies that all components are ready for deployment
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} - NOT FOUND")
        return False

def check_directory_exists(dirpath, description):
    """Check if a directory exists"""
    if os.path.exists(dirpath) and os.path.isdir(dirpath):
        print(f"✅ {description}: {dirpath}")
        return True
    else:
        print(f"❌ {description}: {dirpath} - NOT FOUND")
        return False

def check_env_example():
    """Check if .env.example has required variables"""
    env_file = "backend/.env.example"
    if not os.path.exists(env_file):
        print(f"❌ Environment template: {env_file} - NOT FOUND")
        return False
    
    required_vars = [
        'GOOGLE_CLOUD_PROJECT',
        'VERTEX_AI_LOCATION',
        'GEMINI_API_KEY',
        'FLASK_ENV',
        'MAX_FILE_SIZE',
        'PORT'
    ]
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    missing_vars = []
    for var in required_vars:
        if var not in content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Environment template missing variables: {', '.join(missing_vars)}")
        return False
    else:
        print(f"✅ Environment template: All required variables present")
        return True

def check_package_json():
    """Check frontend package.json"""
    package_file = "frontend/package.json"
    if not os.path.exists(package_file):
        print(f"❌ Frontend package.json: NOT FOUND")
        return False
    
    try:
        with open(package_file, 'r') as f:
            package_data = json.load(f)
        
        required_deps = ['react', 'typescript', 'axios', '@mui/material']
        missing_deps = []
        
        dependencies = package_data.get('dependencies', {})
        for dep in required_deps:
            if dep not in dependencies:
                missing_deps.append(dep)
        
        if missing_deps:
            print(f"❌ Frontend missing dependencies: {', '.join(missing_deps)}")
            return False
        else:
            print(f"✅ Frontend package.json: All required dependencies present")
            return True
            
    except json.JSONDecodeError:
        print(f"❌ Frontend package.json: Invalid JSON")
        return False

def check_requirements_txt():
    """Check backend requirements.txt"""
    req_file = "backend/requirements.txt"
    if not os.path.exists(req_file):
        print(f"❌ Backend requirements.txt: NOT FOUND")
        return False
    
    with open(req_file, 'r') as f:
        content = f.read()
    
    required_packages = [
        'Flask',
        'Flask-CORS',
        'PyPDF2',
        'google-cloud-aiplatform',
        'google-generativeai',
        'gunicorn'
    ]
    
    missing_packages = []
    for package in required_packages:
        if package not in content:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Backend missing packages: {', '.join(missing_packages)}")
        return False
    else:
        print(f"✅ Backend requirements.txt: All required packages present")
        return True

def main():
    """Main deployment check"""
    print("🚀 Lexi Simplify Deployment Readiness Check")
    print("=" * 50)
    
    checks = []
    
    # Core files
    checks.append(check_file_exists("Dockerfile", "Docker configuration"))
    checks.append(check_file_exists("docker-compose.yml", "Docker Compose"))
    checks.append(check_file_exists(".dockerignore", "Docker ignore"))
    checks.append(check_file_exists("README.md", "Documentation"))
    checks.append(check_file_exists(".gitignore", "Git ignore"))
    
    # Backend files
    checks.append(check_file_exists("backend/app.py", "Backend main app"))
    checks.append(check_file_exists("backend/config.py", "Backend configuration"))
    checks.append(check_requirements_txt())
    checks.append(check_env_example())
    
    # Backend services
    checks.append(check_file_exists("backend/services/pdf_processor.py", "PDF processor"))
    checks.append(check_file_exists("backend/services/ai_analyzer.py", "AI analyzer"))
    checks.append(check_file_exists("backend/services/document_storage.py", "Document storage"))
    
    # Backend utilities
    checks.append(check_file_exists("backend/utils/validators.py", "Validators"))
    checks.append(check_file_exists("backend/utils/security.py", "Security utilities"))
    checks.append(check_file_exists("backend/utils/monitoring.py", "Monitoring"))
    
    # Frontend files
    checks.append(check_package_json())
    checks.append(check_file_exists("frontend/src/App.tsx", "Frontend main app"))
    checks.append(check_file_exists("frontend/src/index.tsx", "Frontend entry point"))
    checks.append(check_file_exists("frontend/public/index.html", "Frontend HTML template"))
    
    # Frontend components
    checks.append(check_file_exists("frontend/src/components/DocumentUpload.tsx", "Document upload component"))
    checks.append(check_file_exists("frontend/src/components/AnalysisResults.tsx", "Analysis results component"))
    checks.append(check_file_exists("frontend/src/components/QAInterface.tsx", "Q&A interface component"))
    
    # Frontend services
    checks.append(check_file_exists("frontend/src/services/api.ts", "API service"))
    checks.append(check_file_exists("frontend/src/types/api.ts", "API types"))
    
    # Deployment files
    checks.append(check_file_exists("deploy.sh", "Deployment script"))
    checks.append(check_file_exists("cloud-run-service.yaml", "Cloud Run configuration"))
    
    # Directories
    checks.append(check_directory_exists("backend/services", "Backend services directory"))
    checks.append(check_directory_exists("backend/utils", "Backend utils directory"))
    checks.append(check_directory_exists("frontend/src/components", "Frontend components directory"))
    
    print("\n" + "=" * 50)
    
    passed = sum(checks)
    total = len(checks)
    
    print(f"📊 Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All checks passed! Ready for deployment!")
        print("\n📋 Next steps:")
        print("1. Copy backend/.env.example to backend/.env and configure your Google Cloud credentials")
        print("2. Build and test locally: docker-compose up --build")
        print("3. Deploy to Google Cloud Run: ./deploy.sh")
        return 0
    else:
        print(f"⚠️  {total - passed} checks failed. Please fix the issues above before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())