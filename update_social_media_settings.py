#!/usr/bin/env python3
"""
Frappe Migration Script for Make.com Integration
===============================================

Run this script in Frappe console to update the Social Media Settings.

Usage in Frappe console:
    exec(open('update_social_media_settings.py').read())
"""

import frappe

def update_social_media_settings():
    """Update Social Media Settings with Make.com configuration"""
    try:
        # Get or create Social Media Settings
        if frappe.db.exists("Social Media Settings", "Social Media Settings"):
            settings = frappe.get_doc("Social Media Settings", "Social Media Settings")
            print("📋 Found existing Social Media Settings")
        else:
            settings = frappe.get_doc({
                "doctype": "Social Media Settings",
                "name": "Social Media Settings"
            })
            print("📋 Creating new Social Media Settings")
        
        # Update Make.com configuration
        settings.make_com_enabled = 1
        settings.make_com_api_key = "IlIVOae4oeiypMuTWyfvETHaWDiawS9L"
        settings.make_com_webhook_secret = "BFoCrVIpy%oulZ*IpFh5#aT5SzPsAPI73M9hlLnvrjfJbtmOUiR7u0Iz1G50wbjL"
        settings.make_com_webhook_url = "https://your-domain.com/api/method/assistant_crm.api.make_com_webhook.send_message_to_make_com"
        settings.make_com_rate_limit = 1000
        settings.make_com_timeout = 30
        
        # Save settings
        if settings.is_new():
            settings.insert(ignore_permissions=True)
            print("✅ Created new Social Media Settings with Make.com configuration")
        else:
            settings.save(ignore_permissions=True)
            print("✅ Updated existing Social Media Settings with Make.com configuration")
        
        frappe.db.commit()
        print("💾 Changes committed to database")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating settings: {str(e)}")
        frappe.log_error(f"Make.com settings update error: {str(e)}", "Make.com Setup")
        return False

# Run the update
if __name__ == "__main__":
    update_social_media_settings()
