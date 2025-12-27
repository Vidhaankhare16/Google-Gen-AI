#!/usr/bin/env python3
"""
Simple test script to verify the Legal EASE API is working locally
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_health():
    """Test the health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_analyze_endpoint():
    """Test the analyze endpoint with a simple request"""
    print("\n🔍 Testing analyze endpoint...")
    try:
        # Create a simple test file
        test_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
        
        files = {'file': ('test.pdf', test_content, 'application/pdf')}
        response = requests.post(f"{BASE_URL}/api/analyze", files=files)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Analyze test failed: {e}")
        return False

def test_question_endpoint():
    """Test the question endpoint"""
    print("\n🔍 Testing question endpoint...")
    try:
        data = {
            "document_id": "test-id",
            "question": "What is this document about?"
        }
        response = requests.post(f"{BASE_URL}/api/question", json=data)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        return response.status_code in [200, 404]  # 404 is expected for invalid doc ID
    except Exception as e:
        print(f"❌ Question test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Legal EASE API locally...")
    print("=" * 50)
    
    health_ok = test_health()
    analyze_ok = test_analyze_endpoint()
    question_ok = test_question_endpoint()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Health endpoint: {'✅' if health_ok else '❌'}")
    print(f"Analyze endpoint: {'✅' if analyze_ok else '❌'}")
    print(f"Question endpoint: {'✅' if question_ok else '❌'}")
    
    if all([health_ok, analyze_ok, question_ok]):
        print("\n🎉 All tests passed! API is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the backend logs for details.")