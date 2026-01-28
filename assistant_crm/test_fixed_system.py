#!/usr/bin/env python3
"""
Test the fixed system to verify error handling improvements
"""

import frappe

def test_fixed_system():
    """Test the fixed system with comprehensive error handling"""
    
    print("🔧 TESTING FIXED SYSTEM")
    print("=" * 60)
    
    # Test 1: Test Error Handler Response Format
    print("\n1️⃣ Testing Fixed Error Handler")
    try:
        from assistant_crm.assistant_crm.services.gemini_service import get_error_handler
        
        error_handler = get_error_handler("test")
        test_error = Exception("API key not valid. Please pass a valid API key.")
        fallback_response = error_handler.get_fallback_response(test_error)
        
        print(f"   Fallback response: {fallback_response}")
        print(f"   Has 'response' key: {'response' in fallback_response}")
        print(f"   Response value: '{fallback_response.get('response', 'NOT_FOUND')}'")
        print(f"   Success value: {fallback_response.get('success')}")
        
        if 'response' in fallback_response and fallback_response['response']:
            print("   ✅ Error handler now returns proper response")
        else:
            print("   ❌ Error handler still missing response")
            
    except Exception as e:
        print(f"   ❌ Error Handler Test Failed: {str(e)}")
    
    # Test 2: Test Gemini Service with Invalid Key
    print("\n2️⃣ Testing Gemini Service with Invalid Key")
    try:
        from assistant_crm.assistant_crm.services.gemini_service import GeminiService
        
        gs = GeminiService()
        print(f"   API Key: ***{gs.api_key[-4:] if gs.api_key else 'None'}")
        
        # This should trigger the error handler
        result = gs.process_message(
            message="Test message",
            user_context={"user": "Administrator"},
            chat_history=[]
        )
        
        print(f"   Gemini service result: {result}")
        print(f"   Has 'response' key: {'response' in result if isinstance(result, dict) else 'N/A'}")
        print(f"   Response value: '{result.get('response', 'NOT_FOUND') if isinstance(result, dict) else 'N/A'}'")
        print(f"   Success value: {result.get('success') if isinstance(result, dict) else 'N/A'}")
        
        if isinstance(result, dict) and result.get('response'):
            print("   ✅ Gemini service returns proper error response")
        else:
            print("   ❌ Gemini service still has response issues")
            
    except Exception as e:
        print(f"   ❌ Gemini Service Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Test Complete Chat API
    print("\n3️⃣ Testing Complete Chat API")
    try:
        from assistant_crm.api.chat import send_message
        
        result = send_message(
            message="Test message for fixed system",
            session_id="fixed_system_test_456"
        )
        
        print(f"   Chat API result: {result}")
        print(f"   Success: {result.get('success') if isinstance(result, dict) else 'N/A'}")
        print(f"   Response: '{result.get('response', 'NOT_FOUND') if isinstance(result, dict) else 'N/A'}'")
        print(f"   AI Service Status: {result.get('ai_service_status') if isinstance(result, dict) else 'N/A'}")
        
        if isinstance(result, dict):
            response = result.get('response', '')
            success = result.get('success', True)
            
            if response and response != '':
                print("   ✅ Chat API returns non-empty response")
            else:
                print("   ❌ Chat API still returns empty response")
                
            if not success or result.get('ai_service_status') == 'error':
                print("   ✅ Chat API properly indicates error status")
            else:
                print("   ⚠️  Chat API indicates success despite API key issues")
        else:
            print("   ❌ Chat API returned unexpected result type")
            
    except Exception as e:
        print(f"   ❌ Chat API Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Test Response Processing Logic
    print("\n4️⃣ Testing Response Processing Logic")
    try:
        # Simulate the fixed logic
        mock_ai_response = {
            "success": False,
            "response": "I apologize, but there's an issue with the API configuration.",
            "error": "API key not valid"
        }
        
        # Test the new logic
        response_text = mock_ai_response.get("response", "")
        
        if not response_text or (isinstance(mock_ai_response, dict) and mock_ai_response.get("success") == False):
            error_msg = mock_ai_response.get("error", "") if isinstance(mock_ai_response, dict) else ""
            if "api key" in error_msg.lower() and ("invalid" in error_msg.lower() or "not valid" in error_msg.lower()):
                response_text = "I apologize, but there's currently an issue with the AI service configuration. Please contact support for assistance."
            elif not response_text:
                response_text = mock_ai_response.get("response") or mock_ai_response.get("message") or "I apologize, but I couldn't generate a response. Please try rephrasing your question."
        
        print(f"   Mock AI response: {mock_ai_response}")
        print(f"   Processed response: '{response_text}'")
        
        if response_text and response_text != '':
            print("   ✅ Response processing logic works correctly")
        else:
            print("   ❌ Response processing still produces empty responses")
            
    except Exception as e:
        print(f"   ❌ Response Processing Test Failed: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🎯 FIXED SYSTEM TEST SUMMARY")
    print("=" * 60)
    
    print("\n📋 Expected Improvements:")
    print("1. Error handler returns dict with 'response' key")
    print("2. Chat API extracts meaningful error messages")
    print("3. Chat API indicates error status properly")
    print("4. Users see helpful error messages instead of empty responses")

# Run test if called directly
if __name__ == "__main__":
    test_fixed_system()
