#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Unified Inbox Setup
=========================================

Installation and setup script for the unified inbox system.
Creates default settings, permissions, and initial configuration.

Author: WCFCB Development Team
Created: 2025-08-27
License: MIT
"""

import frappe
from frappe import _
from frappe.utils import now


def setup_unified_inbox():
    """
    Main setup function for the unified inbox system.
    """
    try:
        print("Setting up Unified Inbox System...")
        
        # Create default settings
        create_default_settings()
        
        # Set up permissions
        setup_permissions()
        
        # Create default escalation workflow
        create_default_escalation_workflow()
        
        # Create notification templates
        create_notification_templates()
        
        print("✅ Unified Inbox System setup completed successfully!")
        
        return {
            "status": "success",
            "message": "Unified Inbox System setup completed successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error setting up unified inbox: {str(e)}", "Unified Inbox Setup Error")
        print(f"❌ Error setting up unified inbox: {str(e)}")
        return {"status": "error", "message": str(e)}


def create_default_settings():
    """Create default unified inbox settings."""
    try:
        # Check if settings already exist
        if frappe.db.exists("Unified Inbox Settings", "Unified Inbox Settings"):
            print("📋 Unified Inbox Settings already exist, updating...")
            settings = frappe.get_single("Unified Inbox Settings")
        else:
            print("📋 Creating default Unified Inbox Settings...")
            settings = frappe.get_doc({
                "doctype": "Unified Inbox Settings",
                "name": "Unified Inbox Settings"
            })
        
        # Social Media Settings
        if frappe.db.exists("Social Media Settings", "Social Media Settings"):
            print("📋 Social Media Settings already exist, updating...")
            sm_settings = frappe.get_single("Social Media Settings")
        else:
            print("📋 Creating default Social Media Settings...")
            sm_settings = frappe.get_doc({
                "doctype": "Social Media Settings",
                "name": "Social Media Settings"
            })
        
        # Set default values
        settings.enable_unified_inbox = 1
        settings.auto_assign_agents = 1
        settings.default_priority = "Medium"
        settings.response_time_sla_minutes = 15
        settings.max_conversations_per_agent = 10
        settings.enable_real_time_notifications = 1
        
        # AI Settings
        settings.enable_ai_first_response = 1
        settings.ai_confidence_threshold = 0.7
        settings.auto_escalate_low_confidence = 1
        settings.ai_response_delay_seconds = 2
        settings.enable_ai_learning = 1
        settings.ai_model_preference = "WorkCom"
        
        # Tawk.to Settings in Social Media Settings
        # Credentials (api_key, property_id, webhook_secret) must be configured manually
        # in Social Media Settings after installation — never hardcode them here.
        sm_settings.tawk_to_enabled = 1
        sm_settings.tawk_to_sync_interval_minutes = 5
        sm_settings.bypass_ai_for_tawk_to = 1
        
        # Other platform defaults in Social Media Settings
        sm_settings.whatsapp_enabled = 0
        sm_settings.facebook_enabled = 0
        sm_settings.instagram_enabled = 0
        sm_settings.telegram_enabled = 0
        
        sm_settings.save(ignore_permissions=True)
        print("✅ Social Media settings created/updated successfully")
        
        # Escalation Settings
        settings.auto_escalate_after_minutes = 30
        settings.escalate_on_keywords = "urgent, emergency, complaint, manager, supervisor"
        settings.notify_managers_on_escalation = 1
        
        # Notification Settings
        settings.enable_email_notifications = 1
        settings.enable_sms_notifications = 0
        settings.notification_frequency_minutes = 5
        settings.notify_on_new_conversation = 1
        settings.notify_on_escalation = 1
        
        settings.save(ignore_permissions=True)
        print("✅ Default settings created/updated successfully")
        
    except Exception as e:
        frappe.log_error(f"Error creating default settings: {str(e)}", "Unified Inbox Setup Error")
        raise


def setup_permissions():
    """Set up permissions for unified inbox DocTypes."""
    try:
        print("🔐 Setting up permissions...")
        
        # DocTypes to set permissions for
        doctypes = [
            "Unified Inbox Conversation",
            "Unified Inbox Message",
            "Unified Inbox Settings"
        ]
        
        # Roles and their permissions
        role_permissions = {
            "System Manager": {
                "read": 1, "write": 1, "create": 1, "delete": 1,
                "submit": 0, "cancel": 0, "amend": 0,
                "report": 1, "export": 1, "import": 1, "print": 1, "email": 1, "share": 1
            },
            "Assistant CRM Manager": {
                "read": 1, "write": 1, "create": 1, "delete": 1,
                "submit": 0, "cancel": 0, "amend": 0,
                "report": 1, "export": 1, "import": 0, "print": 1, "email": 1, "share": 1
            },
            "Assistant CRM Agent": {
                "read": 1, "write": 1, "create": 1, "delete": 0,
                "submit": 0, "cancel": 0, "amend": 0,
                "report": 1, "export": 1, "import": 0, "print": 1, "email": 1, "share": 1
            }
        }
        
        for doctype in doctypes:
            if frappe.db.exists("DocType", doctype):
                # Clear existing permissions
                frappe.db.delete("Custom DocPerm", {"parent": doctype})
                
                # Add new permissions
                for role, perms in role_permissions.items():
                    # Skip settings permissions for agents
                    if doctype == "Unified Inbox Settings" and role == "Assistant CRM Agent":
                        continue
                    
                    perm_doc = frappe.get_doc({
                        "doctype": "Custom DocPerm",
                        "parent": doctype,
                        "parenttype": "DocType",
                        "parentfield": "permissions",
                        "role": role,
                        **perms
                    })
                    perm_doc.insert(ignore_permissions=True)
        
        print("✅ Permissions set up successfully")
        
    except Exception as e:
        frappe.log_error(f"Error setting up permissions: {str(e)}", "Unified Inbox Setup Error")
        raise


def create_default_escalation_workflow():
    """Create default escalation workflow if it doesn't exist."""
    try:
        print("🔄 Setting up default escalation workflow...")
        
        # Check if default escalation workflow exists
        if not frappe.db.exists("Escalation Workflow", {"query_id": "DEFAULT_UNIFIED_INBOX"}):
            escalation_doc = frappe.get_doc({
                "doctype": "Escalation Workflow",
                "query_id": "DEFAULT_UNIFIED_INBOX",
                "user_id": "system",
                "escalation_date": now(),
                "escalation_reason": "default_setup",
                "escalation_type": "automatic",
                "priority_level": "medium",
                "department": "customer_service",
                "status": "template",
                "query_text": "Default escalation workflow template for unified inbox",
                "confidence_score": 0.0,
                "is_template": 1
            })
            escalation_doc.insert(ignore_permissions=True)
            print("✅ Default escalation workflow created")
        else:
            print("📋 Default escalation workflow already exists")
        
    except Exception as e:
        frappe.log_error(f"Error creating escalation workflow: {str(e)}", "Unified Inbox Setup Error")
        raise


def create_notification_templates():
    """Create email notification templates."""
    try:
        print("📧 Creating notification templates...")
        
        templates = [
            {
                "name": "Unified Inbox - New Conversation",
                "subject": "New conversation assigned: {{ customer_name }}",
                "response": """
                <p>Hello {{ agent_name }},</p>
                <p>You have been assigned a new conversation:</p>
                <ul>
                    <li><strong>Customer:</strong> {{ customer_name }}</li>
                    <li><strong>Platform:</strong> {{ platform }}</li>
                    <li><strong>Priority:</strong> {{ priority }}</li>
                    <li><strong>Last Message:</strong> {{ last_message }}</li>
                </ul>
                <p>Please respond as soon as possible.</p>
                <p>Best regards,<br>WCFCB Assistant CRM</p>
                """
            },
            {
                "name": "Unified Inbox - Escalation Alert",
                "subject": "Conversation escalated: {{ customer_name }}",
                "response": """
                <p>Hello {{ manager_name }},</p>
                <p>A conversation has been escalated:</p>
                <ul>
                    <li><strong>Customer:</strong> {{ customer_name }}</li>
                    <li><strong>Platform:</strong> {{ platform }}</li>
                    <li><strong>Escalation Reason:</strong> {{ escalation_reason }}</li>
                    <li><strong>Assigned Agent:</strong> {{ assigned_agent }}</li>
                    <li><strong>Priority:</strong> {{ priority }}</li>
                </ul>
                <p>Please review and take appropriate action.</p>
                <p>Best regards,<br>WCFCB Assistant CRM</p>
                """
            }
        ]
        
        for template_data in templates:
            if not frappe.db.exists("Email Template", template_data["name"]):
                template_doc = frappe.get_doc({
                    "doctype": "Email Template",
                    "name": template_data["name"],
                    "subject": template_data["subject"],
                    "response": template_data["response"],
                    "use_html": 1
                })
                template_doc.insert(ignore_permissions=True)
                print(f"✅ Created template: {template_data['name']}")
            else:
                print(f"📋 Template already exists: {template_data['name']}")
        
    except Exception as e:
        frappe.log_error(f"Error creating notification templates: {str(e)}", "Unified Inbox Setup Error")
        raise


@frappe.whitelist()
def install_unified_inbox():
    """API endpoint to install unified inbox system."""
    return setup_unified_inbox()


@frappe.whitelist()
def get_setup_status():
    """Get the current setup status of the unified inbox system."""
    try:
        status = {
            "settings_created": frappe.db.exists("Unified Inbox Settings", "Unified Inbox Settings"),
            "permissions_set": bool(frappe.db.count("Custom DocPerm", {"parent": "Unified Inbox Conversation"})),
            "escalation_workflow_created": frappe.db.exists("Escalation Workflow", {"query_id": "DEFAULT_UNIFIED_INBOX"}),
            "notification_templates_created": frappe.db.exists("Email Template", "Unified Inbox - New Conversation"),
            "tawk_to_configured": False,
            "social_media_configured": False
        }
        
        # Check Tawk.to and Social Media configuration
        sm_settings = frappe.get_single("Social Media Settings")
        status["tawk_to_configured"] = bool(sm_settings.get_password("tawk_to_api_key") and sm_settings.tawk_to_property_id)
        status["social_media_configured"] = any([
            sm_settings.whatsapp_enabled and sm_settings.get_password("whatsapp_access_token"),
            sm_settings.facebook_enabled and sm_settings.get_password("facebook_page_access_token"),
            sm_settings.instagram_enabled and sm_settings.get_password("instagram_access_token"),
            sm_settings.telegram_enabled and sm_settings.get_password("telegram_bot_token")
        ])
        
        status["setup_complete"] = all([
            status["settings_created"],
            status["permissions_set"],
            status["escalation_workflow_created"],
            status["notification_templates_created"]
        ])
        
        return {
            "status": "success",
            "setup_status": status
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting setup status: {str(e)}", "Unified Inbox Setup Error")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    setup_unified_inbox()
