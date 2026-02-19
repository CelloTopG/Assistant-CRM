#!/usr/bin/env python3
"""
Simple Gemini test without complex services
"""

import frappe
import requests
import json
import time

def test_simple_gemini():
    """Test Gemini with simplified approach"""
    
    print("🧪 Testing Simple Gemini Implementation")
    print("=" * 50)
    
    # Get settings
    settings = frappe.get_single("Assistant CRM Settings")
    api_key = settings.api_key
    model = settings.model_name
    
    print(f"API Key: ***{api_key[-4:] if api_key else 'None'}")
    print(f"Model: {model}")
    
    # Simple message processing
    message = "Hello, please respond with a simple greeting."
    
    # Build simple payload
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"You are WorkCom, a helpful assistant. Please respond to: {message}"
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 1024,
        }
    }
    
    # Make API call
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    try:
        print("\n📡 Making API call...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"✅ API call successful!")
            
            if "candidates" in response_data and len(response_data["candidates"]) > 0:
                ai_response = response_data["candidates"][0]["content"]["parts"][0]["text"]
                print(f"✅ AI Response: {ai_response}")
                
                # Test the chat API with this working approach
                print("\n🧪 Testing Chat API with simple message...")
                from assistant_crm.api.chat import send_message
                
                result = send_message(
                    message="Hello WorkCom",
                    session_id="simple_test_123"
                )
                
                print(f"Chat API result: {result}")
                
                if isinstance(result, dict) and result.get('response'):
                    print(f"✅ Chat API working! Response: {result['response']}")
                else:
                    print(f"❌ Chat API returned empty response: {result}")
                
            else:
                print(f"❌ No candidates in response: {response_data}")
        else:
            print(f"❌ API call failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

# Run test if called directly
if __name__ == "__main__":
    test_simple_gemini()

