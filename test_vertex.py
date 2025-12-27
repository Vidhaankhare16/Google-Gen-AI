#!/usr/bin/env python3
"""
Test script to verify Vertex AI is working
"""

import vertexai
from vertexai.preview.generative_models import GenerativeModel
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

def test_vertex_ai():
    """Test Vertex AI"""
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
    
    print(f"🔑 Project ID: {project_id}")
    print(f"📍 Location: {location}")
    
    if not project_id:
        print("❌ No project ID found!")
        return False
    
    try:
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        
        # Test with Gemini model
        model = GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Hello, can you respond with 'Vertex AI is working'?")
        
        print(f"✅ Vertex AI Response: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Vertex AI Error: {str(e)}")
        
        # Try with a different model
        try:
            print("🔄 Trying with gemini-1.5-pro-001...")
            model = GenerativeModel("gemini-1.5-pro")
            response = model.generate_content("Hello, can you respond with 'Vertex AI is working'?")
            print(f"✅ Vertex AI Response: {response.text}")
            return True
        except Exception as e2:
            print(f"❌ Second attempt failed: {str(e2)}")
            return False

if __name__ == "__main__":
    print("🧪 Testing Vertex AI...")
    print("=" * 50)
    
    success = test_vertex_ai()
    
    if success:
        print("\n🎉 Vertex AI is working correctly!")
    else:
        print("\n⚠️ Vertex AI test failed. Check your Google Cloud setup.")