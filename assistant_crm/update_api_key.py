#!/usr/bin/env python3
"""
Simple API key update function
"""

import frappe

def update_api_key():
    """Update API key in Assistant CRM Settings"""
    
    print("🔧 Updating API Key Configuration")
    
    # Update settings
    settings = frappe.get_single("Assistant CRM Settings")
    settings.api_key = "AIzaSyBWrNo4wqD6P-gmgFtq2oBlgjRqXGhPpbI"
    settings.model_name = "gemini-1.5-flash"
    settings.ai_provider = "Google Gemini"
    settings.enabled = 1
    settings.response_timeout = 30
    settings.save()
    frappe.db.commit()
    
    print("✅ API key updated successfully!")
    print(f"   Model: {settings.model_name}")
    print(f"   API Key: ***{settings.api_key[-4:]}")
    print(f"   Provider: {settings.ai_provider}")
    
    # Clear caches
    frappe.clear_cache()
    print("✅ Caches cleared")
    
    return True

# Run if called directly
if __name__ == "__main__":
    update_api_key()
