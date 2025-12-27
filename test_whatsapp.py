#!/usr/bin/env python3
"""
Test script for WhatsApp integration
Tests the webhook endpoints and message handling
"""
import requests
import json
import os

# Your deployed app URL - update this with your actual deployment URL
APP_URL = os.getenv('APP_URL', "https://your-app-name.us-central1.run.app")

def test_webhook_verification():
    """Test webhook verification endpoint"""
    print("🔍 Testing webhook verification...")
    
    try:
        response = requests.get(f"{APP_URL}/whatsapp/webhook")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook verification working!")
        else:
            print("❌ Webhook verification failed")
            
    except Exception as e:
        print(f"❌ Error testing webhook: {e}")

def test_webhook_message():
    """Test webhook message handling"""
    print("\n📱 Testing webhook message handling...")
    
    # Simulate a Twilio webhook request
    webhook_data = {
        'From': 'whatsapp:+1234567890',
        'Body': 'help',
        'MessageSid': 'test-message-id',
        'AccountSid': 'test-account-sid'
    }
    
    try:
        response = requests.post(
            f"{APP_URL}/whatsapp/webhook",
            data=webhook_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook message handling working!")
        else:
            print("❌ Webhook message handling failed")
            
    except Exception as e:
        print(f"❌ Error testing webhook message: {e}")

def test_health_check():
    """Test main API health"""
    print("\n🏥 Testing API health...")
    
    try:
        response = requests.get(f"{APP_URL}/api/health")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Service: {data.get('service')}")
            print(f"Status: {data.get('status')}")
            print("✅ API health check passed!")
        else:
            print("❌ API health check failed")
            
    except Exception as e:
        print(f"❌ Error testing health: {e}")

if __name__ == "__main__":
    print("🚀 Testing WhatsApp Integration for Legal EASE")
    print("=" * 50)
    
    test_health_check()
    test_webhook_verification()
    test_webhook_message()
    
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print("- Webhook verification endpoint should return 200")
    print("- Message handling should return 200 (even without Twilio credentials)")
    print("- Health check should show service status")
    print("\n🔧 Next Steps:")
    print("1. Get Twilio Account SID and Auth Token")
    print("2. Update environment variables in Cloud Run")
    print("3. Configure webhook URL in Twilio Console")
    print("4. Test with real WhatsApp messages!")