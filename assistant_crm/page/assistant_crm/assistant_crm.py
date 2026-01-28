# Copyright (c) 2025, Assistant CRM and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def get_settings():
    """Get Assistant CRM settings for the integration page"""
    try:
        # Try to get existing settings - handle both Single and regular DocType
        try:
            settings = frappe.get_single("Assistant CRM Settings")
            return {
                "enabled": getattr(settings, 'enabled', False),
                "ai_provider": getattr(settings, 'ai_provider', 'Google Gemini'),
                "model_name": getattr(settings, 'model_name', 'gemini-1.5-pro'),
                "api_key": "***" if settings.get_password("api_key") else "",
                "has_api_key": bool(settings.get_password("api_key")),
                "response_timeout": getattr(settings, 'response_timeout', 30),
                "welcome_message": getattr(settings, 'welcome_message', 'Hello! I\'m Anna, your WCFCB assistant. How can I help you today?'),
                "chat_bubble_position": getattr(settings, 'chat_bubble_position', 'Bottom Right')
            }
        except Exception:
            # If Single DocType fails, try regular DocType approach
            if frappe.db.exists("Assistant CRM Settings", "Assistant CRM Configuration"):
                settings = frappe.get_doc("Assistant CRM Settings", "Assistant CRM Configuration")
                return {
                    "enabled": getattr(settings, 'enabled', False),
                    "ai_provider": getattr(settings, 'ai_provider', 'Google Gemini'),
                    "model_name": getattr(settings, 'model_name', 'gemini-1.5-pro'),
                    "api_key": "***" if getattr(settings, 'api_key', '') else "",
                    "has_api_key": bool(getattr(settings, 'api_key', '')),
                    "response_timeout": getattr(settings, 'response_timeout', 30),
                    "welcome_message": getattr(settings, 'welcome_message', 'Hello! I\'m Anna, your WCFCB assistant. How can I help you today?'),
                    "chat_bubble_position": getattr(settings, 'chat_bubble_position', 'Bottom Right')
                }
            else:
                # Return default settings if none exist
                return {
                    "enabled": False,
                    "ai_provider": "Google Gemini",
                    "model_name": "gemini-1.5-pro",
                    "api_key": "",
                    "has_api_key": False,
                    "response_timeout": 30,
                    "welcome_message": "Hello! I'm Anna, your WCFCB assistant. How can I help you today?",
                    "chat_bubble_position": "Bottom Right"
                }
    except Exception as e:
        frappe.log_error(f"Error getting Assistant CRM settings: {str(e)}", "Assistant CRM Page")
        # Return default settings on error
        return {
            "enabled": False,
            "ai_provider": "Google Gemini",
            "model_name": "gemini-1.5-pro",
            "api_key": "",
            "has_api_key": False,
            "response_timeout": 30,
            "welcome_message": "Hello! I'm Anna, your WCFCB assistant. How can I help you today?",
            "chat_bubble_position": "Bottom Right"
        }


@frappe.whitelist()
def save_settings(**kwargs):
    """Save Assistant CRM settings from the integration page"""
    try:
        import json

        # Handle different parameter formats for HTTP requests
        settings = kwargs.get('settings')

        # Try multiple sources for settings data
        if not settings:
            settings = frappe.form_dict.get('settings')

        if not settings:
            # Try to get individual parameters from form data
            form_data = frappe.form_dict
            if any(key in form_data for key in ['enabled', 'ai_provider', 'model_name', 'api_key']):
                settings = {
                    'enabled': form_data.get('enabled', False),
                    'ai_provider': form_data.get('ai_provider', 'Google Gemini'),
                    'model_name': form_data.get('model_name', 'gemini-1.5-pro'),
                    'api_key': form_data.get('api_key', ''),
                    'response_timeout': form_data.get('response_timeout', 30),
                    'welcome_message': form_data.get('welcome_message', 'Hello! How can I help you today?'),
                    'chat_bubble_position': form_data.get('chat_bubble_position', 'Bottom Right')
                }

        if isinstance(settings, str):
            settings = json.loads(settings)
        elif not settings:
            # If still no settings, return error with more details
            return {
                "success": False,
                "message": "No settings data provided",
                "debug_info": {
                    "kwargs": list(kwargs.keys()),
                    "form_dict": list(frappe.form_dict.keys())
                }
            }
        
        # Get or create settings document (Single DocType)
        try:
            doc = frappe.get_single("Assistant CRM Settings")
        except Exception:
            # If Single DocType fails, create new document
            doc = frappe.new_doc("Assistant CRM Settings")
            doc.name = "Assistant CRM Settings"  # Single DocType name
        
        # Update settings
        doc.enabled = settings.get("enabled", False)
        doc.ai_provider = settings.get("ai_provider", "Google Gemini")
        doc.model_name = settings.get("model_name", "gemini-1.5-pro")
        doc.response_timeout = settings.get("response_timeout", 30)
        doc.welcome_message = settings.get("welcome_message", "Hello! I'm Anna, your WCFCB assistant. How can I help you today?")
        doc.chat_bubble_position = settings.get("chat_bubble_position", "Bottom Right")
        
        # Handle API key
        if settings.get("api_key") and settings.get("api_key") != "***":
            doc.api_key = settings.get("api_key")
        
        # Save the document (Single DocType)
        try:
            doc.save()
        except Exception as e:
            # If save fails, try insert for new Single DocType
            if "does not exist" in str(e).lower():
                doc.insert()
            else:
                raise e
        
        return {"success": True, "message": "Settings saved successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error saving Assistant CRM settings: {str(e)}", "Assistant CRM Page")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def test_connection():
    """Test the AI API connection"""
    try:
        from assistant_crm.services.settings_service import get_settings_service
        
        settings_service = get_settings_service()
        ai_config = settings_service.get_ai_config()
        
        if not ai_config.get("api_key"):
            return {"success": False, "message": "API key is required"}
        
        # Test based on provider
        if ai_config.get("provider") == "Google Gemini":
            return test_gemini_connection(ai_config)
        else:
            return {"success": False, "message": "Provider not supported for testing yet"}
            
    except Exception as e:
        return {"success": False, "message": str(e)}


def test_gemini_connection(ai_config):
    """Test Google Gemini connection"""
    try:
        import google.generativeai as genai

        genai.configure(api_key=ai_config.get("api_key"))
        model = genai.GenerativeModel(ai_config.get("model_name", "gemini-1.5-pro"))
        response = model.generate_content("Test connection")

        return {
            "success": True,
            "message": "Connection successful",
            "model": ai_config.get("model_name"),
            "response_preview": response.text[:100] + "..." if len(response.text) > 100 else response.text
        }

    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}


def get_context(context):
    """Get context for page template rendering"""
    try:
        # Add any context variables needed for the page template
        context.update({
            "app_name": "Assistant CRM",
            "app_version": "0.0.1",
            "page_title": "Assistant CRM Dashboard"
        })
        return context
    except Exception as e:
        frappe.log_error(f"Error getting page context: {str(e)}", "Assistant CRM Page")
        return context
