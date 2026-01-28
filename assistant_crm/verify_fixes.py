#!/usr/bin/env python3
"""
Simple verification script for chat fixes
"""

import frappe

def verify_chat_fixes():
    """Verify all three chat functionality fixes"""
    
    print("🔍 Verifying Chat Functionality Fixes...")
    
    # Test 1: Chat History Status Options
    try:
        # Check if "Received" is in the status options
        meta = frappe.get_meta("Chat History")
        status_field = None
        for field in meta.fields:
            if field.fieldname == "status":
                status_field = field
                break
        
        if status_field and "Received" in status_field.options:
            print("✅ Issue 1 Fixed: 'Received' status option added to Chat History")
        else:
            print("❌ Issue 1 Not Fixed: 'Received' status option missing")
            
    except Exception as e:
        print(f"❌ Error checking status options: {str(e)}")
    
    # Test 2: update_response Method
    try:
        from assistant_crm.assistant_crm.doctype.chat_history.chat_history import ChatHistory
        
        # Check if update_response method exists
        if hasattr(ChatHistory, 'update_response'):
            print("✅ Issue 2 Fixed: update_response method added to ChatHistory class")
        else:
            print("❌ Issue 2 Not Fixed: update_response method missing")
            
    except Exception as e:
        print(f"❌ Error checking update_response method: {str(e)}")
    
    # Test 3: Gemini Model Configuration
    try:
        from assistant_crm.assistant_crm.services.gemini_service import GeminiService
        
        service = GeminiService()
        model = service.model
        
        valid_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
        if model in valid_models:
            print(f"✅ Issue 3 Fixed: Valid Gemini model configured: {model}")
        else:
            print(f"❌ Issue 3 Not Fixed: Invalid model: {model}")
            
    except Exception as e:
        print(f"❌ Error checking Gemini model: {str(e)}")
    
    print("\n🎯 Verification Complete!")
    return True

# Run verification if called directly
if __name__ == "__main__":
    verify_chat_fixes()
