#!/usr/bin/env python3
"""
Simple test for the three critical fixes
"""

import frappe

def test_all_fixes():
    """Test all three critical fixes"""
    
    print("🔍 Testing All Critical Fixes...")
    
    # Test 1: Gemini Model Configuration
    try:
        from assistant_crm.assistant_crm.services.gemini_service import GeminiService
        service = GeminiService()
        model = service.model
        valid_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
        if model in valid_models:
            print(f"✅ Issue 1 Fixed: Valid Gemini model: {model}")
        else:
            print(f"❌ Issue 1 Not Fixed: Invalid model: {model}")
    except Exception as e:
        print(f"❌ Issue 1 Error: {str(e)}")
    
    # Test 2: Context Service Import
    try:
        from assistant_crm.assistant_crm.services.context_service import ContextService
        context_service = ContextService()
        user_context = context_service.get_user_context()
        print("✅ Issue 2 Fixed: Context Service frappe import working")
    except NameError as e:
        if "frappe" in str(e):
            print(f"❌ Issue 2 Not Fixed: {str(e)}")
        else:
            print(f"❌ Issue 2 Other Error: {str(e)}")
    except Exception as e:
        print(f"❌ Issue 2 Error: {str(e)}")
    
    # Test 3: ChatHistory update_response Method
    try:
        chat_doc = frappe.get_doc({
            "doctype": "Chat History",
            "user": "Administrator",
            "session_id": "test_fix_789",
            "message": "Test message",
            "timestamp": frappe.utils.now(),
            "status": "Received"
        })
        chat_doc.insert()
        
        # Reload to get proper class
        chat_doc = frappe.get_doc("Chat History", chat_doc.name)
        
        if hasattr(chat_doc, 'update_response'):
            chat_doc.update_response(response="Test", status="Completed")
            print("✅ Issue 3 Fixed: update_response method working")
        else:
            print("❌ Issue 3 Not Fixed: update_response method missing")
        
        chat_doc.delete()
        
    except AttributeError as e:
        if "update_response" in str(e):
            print(f"❌ Issue 3 Not Fixed: {str(e)}")
        else:
            print(f"❌ Issue 3 Other Error: {str(e)}")
    except Exception as e:
        print(f"❌ Issue 3 Error: {str(e)}")
    
    print("🎯 Fix Testing Complete!")
    return True

# Run test if called directly
if __name__ == "__main__":
    test_all_fixes()
