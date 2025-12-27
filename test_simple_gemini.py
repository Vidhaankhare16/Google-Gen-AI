#!/usr/bin/env python3
"""
Simple test for Gemini API without complex model names
"""

import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

def test_simple_gemini():
    """Test Gemini API with simple approach"""
    api_key = os.getenv('GEMINI_API_KEY')
    
    print(f"🔑 API Key: {api_key[:10]}...{api_key[-10:] if api_key else 'None'}")
    
    if not api_key:
        print("❌ No API key found!")
        return False
    
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Try the simplest model name
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Simple test prompt
        prompt = "Respond with exactly: 'Gemini API is working correctly'"
        response = model.generate_content(prompt)
        
        print(f"✅ API Response: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        
        # Try with different model
        try:
            print("🔄 Trying with gemini-1.5-pro...")
            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content(prompt)
            print(f"✅ API Response: {response.text}")
            return True
        except Exception as e2:
            print(f"❌ Second attempt failed: {str(e2)}")
            
            # Try with basic gemini-pro
            try:
                print("🔄 Trying with gemini-pro...")
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
                print(f"✅ API Response: {response.text}")
                return True
            except Exception as e3:
                print(f"❌ Third attempt failed: {str(e3)}")
                return False

if __name__ == "__main__":
    print("🧪 Testing Simple Gemini API...")
    print("=" * 50)
    
    success = test_simple_gemini()
    
    if success:
        print("\n🎉 Gemini API is working!")
    else:
        print("\n⚠️ All Gemini API tests failed.")