#!/usr/bin/env python3
"""
Force update API key configuration
"""

import frappe

def force_update_api_key():
    """Force update the API key configuration"""
    
    print("🔧 FORCE UPDATING API KEY CONFIGURATION")
    print("=" * 60)
    
    working_api_key = "AIzaSyA2IkVNUOx_yG50ifz6T4p0FGwGYndqMe8"
    
    try:
        # Update Assistant CRM Settings
        print("📝 Updating Assistant CRM Settings...")
        settings = frappe.get_single("Assistant CRM Settings")
        
        print(f"   Current API Key: {settings.api_key}")
        print(f"   Current Model: {settings.model_name}")
        print(f"   Current Enabled: {settings.enabled}")
        
        # Force update
        settings.api_key = working_api_key
        settings.model_name = "gemini-1.5-flash"
        settings.ai_provider = "Google Gemini"
        settings.enabled = 1
        settings.response_timeout = 30
        settings.save()
        frappe.db.commit()
        
        print(f"✅ Settings updated!")
        print(f"   New API Key: {settings.api_key}")
        print(f"   New Model: {settings.model_name}")
        print(f"   New Enabled: {settings.enabled}")
        
        # Verify the update
        settings.reload()
        print(f"\n🔍 Verification after reload:")
        print(f"   Verified API Key: {settings.api_key}")
        print(f"   Verified Model: {settings.model_name}")
        print(f"   Verified Enabled: {settings.enabled}")
        
        # Test direct database query
        print(f"\n🔍 Direct database query:")
        db_result = frappe.db.get_value("Assistant CRM Settings", "Assistant CRM Settings", ["api_key", "model_name", "enabled"])
        print(f"   DB API Key: {db_result[0] if db_result else 'None'}")
        print(f"   DB Model: {db_result[1] if db_result else 'None'}")
        print(f"   DB Enabled: {db_result[2] if db_result else 'None'}")
        
        # Clear all caches
        print(f"\n🧹 Clearing all caches...")
        frappe.clear_cache()
        frappe.clear_website_cache()
        print("✅ Caches cleared!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# Run update if called directly
if __name__ == "__main__":
    force_update_api_key()
