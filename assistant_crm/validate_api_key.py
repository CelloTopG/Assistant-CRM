#!/usr/bin/env python3
"""
Validate API key and diagnose issues
"""

import frappe
import requests
import json

def validate_api_key():
    """Validate the current API key configuration"""
    
    print("🔍 Validating API Key Configuration")
    print("=" * 50)
    
    try:
        # Get current settings
        settings = frappe.get_single("Assistant CRM Settings")
        api_key = settings.api_key
        model = settings.model_name
        
        print(f"📝 Current API Key: {api_key}")
        print(f"📝 Current Model: {model}")
        print(f"📝 Provider: {settings.ai_provider}")
        print(f"📝 Enabled: {settings.enabled}")
        
        # Test the API key with a simple request
        if api_key:
            print(f"\n🧪 Testing API Key: ***{api_key[-4:]}")
            
            # Test with list models endpoint first (simpler)
            list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            
            try:
                print("📡 Testing with list models endpoint...")
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
                        print(f"❌ Model '{model}' not found in available models")
                        print(f"📝 Available models: {available_models[:5]}...")  # Show first 5
                        
                elif response.status_code == 400:
                    error_data = response.json()
                    print(f"❌ API key validation failed: {error_data}")
                    
                    if "API_KEY_INVALID" in str(error_data):
                        print("🔧 The API key is invalid or has been revoked")
                        print("💡 Solution: Get a new API key from Google AI Studio")
                    
                else:
                    print(f"❌ Unexpected response: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"❌ API request error: {str(e)}")
        else:
            print("❌ No API key configured")
        
        # Check environment variables
        print(f"\n🔍 Checking Environment Variables")
        import os
        env_key = os.getenv("google_gemini_api_key")
        env_model = os.getenv("gemini_model")
        
        print(f"📝 ENV API Key: {env_key}")
        print(f"📝 ENV Model: {env_model}")
        
        # Check .env.ai file
        try:
            with open("/workspace/development/frappe-bench/.env.ai", "r") as f:
                env_content = f.read()
                print(f"\n📝 .env.ai content:\n{env_content}")
        except Exception as e:
            print(f"❌ Error reading .env.ai: {str(e)}")
        
        return api_key
        
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# Run validation if called directly
if __name__ == "__main__":
    validate_api_key()
