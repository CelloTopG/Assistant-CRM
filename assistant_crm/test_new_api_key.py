#!/usr/bin/env python3
"""
Comprehensive test for new API key configuration
"""

import frappe

def test_new_api_key():
    """Test all components with new API key"""
    
    print("🧪 Testing New API Key Configuration")
    print("=" * 50)
    
    results = {
        "api_key_config": False,
        "context_service": False,
        "chat_history": False,
        "gemini_service": False,
        "connection_test": False,
        "complete_chat": False
    }
    
    # Test 1: API Key Configuration
    print("\n1️⃣ Testing API Key Configuration")
    try:
        settings = frappe.get_single("Assistant CRM Settings")
        print(f"   ✅ API Key: ***{settings.api_key[-4:] if settings.api_key else 'None'}")
        print(f"   ✅ Model: {settings.model_name}")
        print(f"   ✅ Provider: {settings.ai_provider}")
        print(f"   ✅ Enabled: {settings.enabled}")
        results["api_key_config"] = True
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 2: Context Service
    print("\n2️⃣ Testing Context Service")
    try:
        from assistant_crm.assistant_crm.services.context_service import ContextService
        cs = ContextService()
        user_context = cs.get_user_context()
        print(f"   ✅ Context Service working")
        print(f"   📝 User: {user_context.get('user', 'Unknown')}")
        results["context_service"] = True
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 3: ChatHistory update_response
    print("\n3️⃣ Testing ChatHistory update_response")
    try:
        from assistant_crm.assistant_crm.doctype.chat_history.chat_history import ChatHistory
        
        # Create test document
        test_doc = frappe.get_doc({
            "doctype": "Chat History",
            "user": "Administrator",
            "session_id": "new_api_test_123",
            "message": "Test with new API key",
            "timestamp": frappe.utils.now(),
            "status": "Received"
        })
        test_doc.insert()
        
        # Test update_response
        if hasattr(test_doc, 'update_response'):
            test_doc.update_response(
                response="Test response with new API key",
                status="Completed"
            )
            print("   ✅ update_response method working")
            results["chat_history"] = True
        else:
            print("   ❌ update_response method missing")
        
        # Clean up
        test_doc.delete()
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 4: Gemini Service
    print("\n4️⃣ Testing Gemini Service")
    try:
        from assistant_crm.assistant_crm.services.gemini_service import GeminiService
        gs = GeminiService()
        print(f"   ✅ Gemini Service loaded")
        print(f"   📝 Model: {gs.model}")
        print(f"   📝 API Key: ***{gs.api_key[-4:] if gs.api_key else 'None'}")
        results["gemini_service"] = True
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 5: Connection Test
    print("\n5️⃣ Testing Gemini API Connection")
    try:
        from assistant_crm.assistant_crm.services.gemini_service import GeminiService
        gs = GeminiService()
        connection_result = gs.test_connection()
        
        if connection_result.get('success'):
            print("   ✅ Gemini API connection successful!")
            print(f"   📝 Response: {connection_result.get('response', 'No response')[:50]}...")
            results["connection_test"] = True
        else:
            print(f"   ⚠️  Connection failed: {connection_result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 6: Complete Chat Flow
    print("\n6️⃣ Testing Complete Chat Flow")
    try:
        from assistant_crm.api.chat import send_message
        result = send_message(
            message="hi WorkCom",
            session_id="new_api_complete_test_456"
        )
        print("   ✅ Complete chat flow executed")
        
        if isinstance(result, dict):
            if result.get("success", True):
                print("   ✅ Chat flow completed successfully")
                results["complete_chat"] = True
            else:
                print(f"   ⚠️  Chat returned: {result.get('message', 'Unknown')}")
        else:
            print("   ✅ Chat flow completed")
            results["complete_chat"] = True
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! New API key configuration is working perfectly!")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return results

# Run test if called directly
if __name__ == "__main__":
    test_new_api_key()

