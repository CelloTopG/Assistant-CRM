#!/usr/bin/env python3
"""
Direct test of Gemini API
"""

import frappe
import requests
import json

def test_gemini_direct():
    """Test Gemini API directly"""
    
    print("🧪 Testing Gemini API Directly")
    print("=" * 40)
    
    # Get settings
    settings = frappe.get_single("Assistant CRM Settings")
    api_key = settings.api_key
    model = settings.model_name
    
    print(f"API Key: ***{api_key[-4:] if api_key else 'None'}")
    print(f"Model: {model}")
    
    # Test direct API call
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Hello, please respond with a simple greeting."
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
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print("\n📡 Making direct API call...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"✅ API call successful!")
            print(f"Response data keys: {list(response_data.keys())}")
            
            if "candidates" in response_data and len(response_data["candidates"]) > 0:
                ai_response = response_data["candidates"][0]["content"]["parts"][0]["text"]
                print(f"✅ AI Response: {ai_response}")
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
    test_gemini_direct()
