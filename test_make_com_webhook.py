#!/usr/bin/env python3
"""
Make.com Integration Test Script
===============================

Test the Make.com webhook integration.
"""

import requests
import json

# Configuration
WEBHOOK_URL = "https://your-domain.com/api/omnichannel/webhook/make-com"
API_KEY = "IlIVOae4oeiypMuTWyfvETHaWDiawS9L"

def test_webhook_status():
    """Test webhook status endpoint"""
    print("🧪 Testing webhook status...")
    
    try:
        response = requests.get(WEBHOOK_URL, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Webhook is active and responding")
            print(f"   Response: {data.get('message', 'No message')}")
        else:
            print(f"❌ Webhook returned status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing webhook: {str(e)}")

def test_webhook_message():
    """Test webhook message processing"""
    print("\n🧪 Testing webhook message processing...")
    
    sample_data = {
        "platform": "facebook",
        "event_type": "message",
        "timestamp": "2025-01-10T12:00:00Z",
        "data": {
            "message": {
                "id": "test_123",
                "content": "Hello Anna, this is a test message",
                "type": "text"
            },
            "sender": {
                "id": "test_user",
                "name": "Test User"
            },
            "conversation": {
                "channel_id": "test_channel"
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=sample_data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Message processed successfully")
            print(f"   Response: {data.get('message', 'No message')}")
            if data.get('response'):
                print(f"   Anna's Reply: {data['response'].get('reply', 'No reply')}")
        else:
            print(f"❌ Message processing failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing message processing: {str(e)}")

if __name__ == "__main__":
    print("🚀 Make.com Integration Test")
    print("=" * 40)
    print("⚠️  Make sure to replace 'your-domain.com' with your actual domain")
    print()
    
    test_webhook_status()
    test_webhook_message()
