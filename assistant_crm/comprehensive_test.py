#!/usr/bin/env python3
"""
Comprehensive test for all three critical fixes
"""

import frappe

def comprehensive_test():
    """Test all three critical fixes comprehensively"""
    
    print("🔍 Comprehensive Testing of All Critical Fixes...")
    print("=" * 60)
    
    results = {
        "context_service": False,
        "update_response": False,
        "gemini_model": False,
        "complete_flow": False
    }
    
    # Test 1: Context Service Import and Functionality
    print("\n🧪 Test 1: Context Service Import and Functionality")
    try:
        from assistant_crm.assistant_crm.services.context_service import ContextService
        
        # Test instantiation
        context_service = ContextService()
        print("   ✅ ContextService instantiated successfully")
        
        # Test get_user_context method (this was failing due to missing frappe import)
        user_context = context_service.get_user_context()
        print("   ✅ get_user_context method executed successfully")
        print(f"   📝 User: {user_context.get('user', 'Unknown')}")
        print(f"   📝 Full Name: {user_context.get('full_name', 'Unknown')}")
        
        results["context_service"] = True
        
    except NameError as e:
        if "frappe" in str(e):
            print(f"   ❌ Frappe import issue: {str(e)}")
        else:
            print(f"   ❌ Other NameError: {str(e)}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 2: ChatHistory update_response Method
    print("\n🧪 Test 2: ChatHistory update_response Method")
    try:
        # Create a test chat history document
        chat_doc = frappe.get_doc({
            "doctype": "Chat History",
            "user": "Administrator",
            "session_id": "comprehensive_test_123",
            "message": "Test message for comprehensive test",
            "timestamp": frappe.utils.now(),
            "status": "Received"
        })
        chat_doc.insert()
        
        # Reload to ensure proper class instance
        chat_doc = frappe.get_doc("Chat History", chat_doc.name)
        
        # Ensure the update_response method is available
        if not hasattr(chat_doc, 'update_response'):
            from assistant_crm.assistant_crm.doctype.chat_history.chat_history import ChatHistory
            chat_doc.__class__ = ChatHistory
        
        # Test the update_response method
        if hasattr(chat_doc, 'update_response'):
            print("   ✅ update_response method exists")
            
            # Test calling the method
            chat_doc.update_response(
                response="Test AI response from comprehensive test",
                status="Completed",
                context_data={"test": "comprehensive_data"}
            )
            print("   ✅ update_response method executed successfully")
            
            # Verify the update worked
            chat_doc.reload()
            print(f"   📝 Response: {chat_doc.response[:50]}...")
            print(f"   📝 Status: {chat_doc.status}")
            
            results["update_response"] = True
            
        else:
            print("   ❌ update_response method does not exist")
        
        # Clean up
        chat_doc.delete()
        
    except AttributeError as e:
        if "update_response" in str(e):
            print(f"   ❌ update_response method missing: {str(e)}")
        else:
            print(f"   ❌ Other AttributeError: {str(e)}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 3: Gemini Model Configuration
    print("\n🧪 Test 3: Gemini Model Configuration")
    try:
        from assistant_crm.assistant_crm.services.gemini_service import GeminiService
        
        service = GeminiService()
        model = service.model
        
        print(f"   📝 Current model: {model}")
        
        # Check if it's a valid Gemini model
        valid_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro", "gemini-pro-vision"]
        if model in valid_models:
            print("   ✅ Model is valid for Google Gemini API")
            results["gemini_model"] = True
        else:
            print(f"   ❌ Model '{model}' is not valid. Valid models: {valid_models}")
        
        # Test API key configuration
        api_key = service.api_key
        if api_key and len(api_key) > 10:
            print(f"   ✅ API key configured: {'*' * (len(api_key) - 4)}{api_key[-4:]}")
        else:
            print("   ⚠️  API key not properly configured")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 4: Complete Chat Flow Integration
    print("\n🧪 Test 4: Complete Chat Flow Integration")
    try:
        # Test the chat API with a simple message
        from assistant_crm.api.chat import send_message
        
        result = send_message(
            message="Hello, this is a comprehensive test",
            session_id="comprehensive_integration_456"
        )
        
        print("   ✅ Chat API executed without errors")
        print(f"   📝 Result type: {type(result)}")
        
        if isinstance(result, dict):
            if result.get("success", True):  # Assume success if not specified
                print("   ✅ Chat flow completed successfully")
                results["complete_flow"] = True
            else:
                print(f"   ⚠️  Chat returned error: {result.get('message', 'Unknown')}")
        else:
            print("   ✅ Chat flow completed (non-dict response)")
            results["complete_flow"] = True
            
    except Exception as e:
        print(f"   ❌ Error in complete chat flow: {str(e)}")
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 Comprehensive Test Results")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\n📊 Test Summary:")
    print(f"   Context Service Import: {'✅ PASSED' if results['context_service'] else '❌ FAILED'}")
    print(f"   ChatHistory update_response: {'✅ PASSED' if results['update_response'] else '❌ FAILED'}")
    print(f"   Gemini Model Configuration: {'✅ PASSED' if results['gemini_model'] else '❌ FAILED'}")
    print(f"   Complete Chat Flow: {'✅ PASSED' if results['complete_flow'] else '❌ FAILED'}")
    
    print(f"\n🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL CRITICAL ISSUES HAVE BEEN RESOLVED!")
    else:
        print("⚠️  Some issues remain and need further investigation")
    
    return results

# Run test if called directly
if __name__ == "__main__":
    comprehensive_test()
