#!/usr/bin/env python3
"""
Test the new API key provided by user
"""

import frappe
import requests
import json

def validate_new_key():
    """Test the new API key: AIzaSyA2IkVNUOx_yG50ifz6T4p0FGwGYndqMe8"""
    
    print("🔧 Testing New API Key")
    print("=" * 50)
    
    new_api_key = "AIzaSyA2IkVNUOx_yG50ifz6T4p0FGwGYndqMe8"
    model = "gemini-1.5-flash"
    
    print(f"📝 Testing API Key: ***{new_api_key[-4:]}")
    print(f"📝 Model: {model}")
    
    # Test 1: List Models Endpoint
    print(f"\n🧪 Test 1: List Models Endpoint")
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={new_api_key}"
        response = requests.get(list_url, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API key is valid!")
            models_data = response.json()
            available_models = [model['name'] for model in models_data.get('models', [])]
            print(f"📝 Available models: {len(available_models)}")
            
            # Check if our model is available
            full_model_name = f"models/{model}"
            if full_model_name in available_models:
                print(f"✅ Model '{model}' is available")
            else:
                print(f"❌ Model '{model}' not found")
                print(f"📝 Available models: {[m.split('/')[-1] for m in available_models[:5]]}")
                
        elif response.status_code == 400:
            error_data = response.json()
            print(f"❌ API key validation failed: {error_data}")
            return False
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ List models test error: {str(e)}")
        return False
    
    # Test 2: Generate Content Endpoint
    print(f"\n🧪 Test 2: Generate Content Endpoint")
    try:
        generate_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={new_api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": "Hello! Please respond with a simple greeting to test the API."
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 100,
            }
        }
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(generate_url, headers=headers, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            
            if "candidates" in response_data and len(response_data["candidates"]) > 0:
                ai_response = response_data["candidates"][0]["content"]["parts"][0]["text"]
                print(f"✅ Content generation successful!")
                print(f"📝 AI Response: {ai_response}")
                return True
            else:
                print(f"❌ No candidates in response: {response_data}")
                return False
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"❌ Content generation failed: {error_data}")
            return False
            
    except Exception as e:
        print(f"❌ Content generation test error: {str(e)}")
        return False

# Run test if called directly
if __name__ == "__main__":
    validate_new_key()
