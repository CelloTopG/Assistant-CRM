# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from assistant_crm.utils import get_public_url


class UnifiedInboxSettings(Document):
    """
    Unified Inbox Settings DocType for configuring the unified inbox system.
    """
    
    def before_save(self):
        """Actions to perform before saving the settings."""
        # Validate settings
        self.validate_settings()
    

    
    def validate_settings(self):
        """Validate configuration settings."""
        # Validate AI confidence threshold
        if self.ai_confidence_threshold and (self.ai_confidence_threshold < 0 or self.ai_confidence_threshold > 1):
            frappe.throw("AI Confidence Threshold must be between 0 and 1")
        
        # Validate response time SLA
        if self.response_time_sla_minutes and self.response_time_sla_minutes < 1:
            frappe.throw("Response Time SLA must be at least 1 minute")
        
        # Validate max conversations per agent
        if self.max_conversations_per_agent and self.max_conversations_per_agent < 1:
            frappe.throw("Max Conversations per Agent must be at least 1")
    
    def get_platform_credentials(self, platform: str) -> dict:
        """Get credentials for a specific platform from Social Media Settings."""
        try:
            settings = frappe.get_single("Social Media Settings")
            return settings.get_platform_credentials(platform)
        except Exception:
            return {}
    
    def is_platform_enabled(self, platform: str) -> bool:
        """Check if a platform is enabled in Social Media Settings."""
        try:
            settings = frappe.get_single("Social Media Settings")
            return settings.is_platform_enabled(platform)
        except Exception:
            return False
    
    def get_escalation_rules(self) -> dict:
        """Get escalation rules configuration."""
        import json
        
        rules = {}
        
        if self.escalation_rules:
            try:
                rules = json.loads(self.escalation_rules) if isinstance(self.escalation_rules, str) else self.escalation_rules
            except (json.JSONDecodeError, TypeError):
                rules = {}
        
        # Add default rules
        default_rules = {
            "auto_escalate_after_minutes": self.auto_escalate_after_minutes or 30,
            "ai_confidence_threshold": self.ai_confidence_threshold or 0.7,
            "auto_escalate_low_confidence": self.auto_escalate_low_confidence,
            "escalate_on_keywords": [keyword.strip() for keyword in (self.escalate_on_keywords or "").split(",") if keyword.strip()],
            "notify_managers_on_escalation": self.notify_managers_on_escalation
        }
        
        rules.update(default_rules)
        return rules
    
    def get_notification_settings(self) -> dict:
        """Get notification settings configuration."""
        return {
            "enable_email_notifications": self.enable_email_notifications,
            "enable_sms_notifications": self.enable_sms_notifications,
            "notification_email_template": self.notification_email_template,
            "notification_frequency_minutes": self.notification_frequency_minutes or 5,
            "notify_on_new_conversation": self.notify_on_new_conversation,
            "notify_on_escalation": self.notify_on_escalation,
            "enable_real_time_notifications": self.enable_real_time_notifications
        }
    
    def get_ai_settings(self) -> dict:
        """Get AI settings configuration."""
        sm_settings = frappe.get_single("Social Media Settings")
        return {
            "enable_ai_first_response": self.enable_ai_first_response,
            "ai_confidence_threshold": self.ai_confidence_threshold or 0.7,
            "auto_escalate_low_confidence": self.auto_escalate_low_confidence,
            "ai_response_delay_seconds": self.ai_response_delay_seconds or 2,
            "enable_ai_learning": self.enable_ai_learning,
            "ai_model_preference": self.ai_model_preference or "WorkCom",
            "bypass_ai_for_tawk_to": sm_settings.bypass_ai_for_tawk_to
        }


@frappe.whitelist()
def get_unified_inbox_settings():
    """Get unified inbox settings."""
    try:
        settings = frappe.get_single("Unified Inbox Settings")
        return {
            "status": "success",
            "settings": settings.as_dict()
        }
    except Exception as e:
        frappe.log_error(f"Error getting unified inbox settings: {str(e)}", "Unified Inbox Settings Error")
        return {"status": "error", "message": "Failed to get settings"}


@frappe.whitelist()
def test_platform_connection(platform: str):
    """Test connection to a specific platform."""
    try:
        settings = frappe.get_single("Unified Inbox Settings")
        
        if not settings.is_platform_enabled(platform):
            return {"status": "error", "message": f"{platform} is not enabled"}
        
        credentials = settings.get_platform_credentials(platform)
        
        if not credentials:
            return {"status": "error", "message": f"No credentials configured for {platform}"}
        
        # Test connection based on platform
        if platform == "Tawk.to":
            from assistant_crm.api.tawk_to_integration import TawkToIntegration
            tawk_integration = TawkToIntegration()
            chats = tawk_integration.get_active_chats()
            return {"status": "success", "message": f"Connected to Tawk.to. Found {len(chats)} active chats."}
        
        elif platform in ["WhatsApp", "Facebook", "Instagram", "Telegram"]:
            from assistant_crm.api.social_media_ports import get_platform_integration
            platform_integration = get_platform_integration(platform)
            
            if platform_integration and platform_integration.is_configured:
                return {"status": "success", "message": f"{platform} is properly configured"}
            else:
                return {"status": "error", "message": f"{platform} configuration is incomplete"}
        
        else:
            return {"status": "error", "message": f"Platform {platform} not supported"}
        
    except Exception as e:
        frappe.log_error(f"Error testing {platform} connection: {str(e)}", "Platform Connection Test Error")
        return {"status": "error", "message": f"Failed to test {platform} connection"}


@frappe.whitelist()
def sync_platform_webhooks():
    """Sync webhook configurations for all enabled platforms."""
    try:
        settings = frappe.get_single("Unified Inbox Settings")
        results = {}
        
        # Generate webhook URLs
        base_url = get_public_url()

        # Social media webhook URL
        social_webhook_url = f"{base_url}/api/method/assistant_crm.api.social_media_ports.social_media_webhook"

        # Tawk.to webhook URL
        tawk_webhook_url = f"{base_url}/api/method/assistant_crm.api.tawk_to_integration.tawk_to_webhook"
        
        results["webhook_urls"] = {
            "social_media": social_webhook_url,
            "tawk_to": tawk_webhook_url
        }
        
        results["enabled_platforms"] = []
        
        for platform in ["WhatsApp", "Facebook", "Instagram", "Telegram"]:
            if settings.is_platform_enabled(platform):
                results["enabled_platforms"].append(platform)
        
        if settings.is_platform_enabled("Tawk.to"):
            results["enabled_platforms"].append("Tawk.to")
        
        return {
            "status": "success",
            "message": "Webhook URLs generated",
            "results": results
        }
        
    except Exception as e:
        frappe.log_error(f"Error syncing webhooks: {str(e)}", "Webhook Sync Error")
        return {"status": "error", "message": "Failed to sync webhooks"}
