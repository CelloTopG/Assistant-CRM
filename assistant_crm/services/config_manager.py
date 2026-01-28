#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Configuration Management Service
Secure credential storage and environment-specific configuration management
"""

import frappe
import os
import json
import base64
from cryptography.fernet import Fernet
from frappe import _
from frappe.utils import get_site_config
from typing import Dict, Any, Optional


class ConfigManager:
    """Secure configuration management for omnichannel integrations"""
    
    def __init__(self):
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self.environment = self._detect_environment()
        
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for secure credential storage"""
        try:
            # Try to get from environment variable first
            env_key = os.environ.get('ASSISTANT_CRM_ENCRYPTION_KEY')
            if env_key:
                return base64.urlsafe_b64decode(env_key.encode())
            
            # Try to get from site config
            site_config = get_site_config()
            config_key = site_config.get('assistant_crm_encryption_key')
            if config_key:
                return base64.urlsafe_b64decode(config_key.encode())
            
            # Generate new key if none exists
            new_key = Fernet.generate_key()
            
            # Save to site config
            site_config['assistant_crm_encryption_key'] = base64.urlsafe_b64encode(new_key).decode()
            
            # Write back to site_config.json
            config_path = frappe.get_site_path('site_config.json')
            with open(config_path, 'w') as f:
                json.dump(site_config, f, indent=2)
            
            frappe.log_error(
                "New encryption key generated for Assistant CRM. "
                "Please backup your site_config.json file.",
                "Config Manager"
            )
            
            return new_key
            
        except Exception as e:
            frappe.log_error(f"Error managing encryption key: {str(e)}", "Config Manager")
            # Fallback to a default key (not recommended for production)
            return Fernet.generate_key()
    
    def _detect_environment(self) -> str:
        """Detect current environment (development, staging, production)"""
        try:
            # Check environment variable
            env = os.environ.get('FRAPPE_ENV', '').lower()
            if env in ['development', 'staging', 'production']:
                return env
            
            # Check site config
            site_config = get_site_config()
            env = site_config.get('environment', '').lower()
            if env in ['development', 'staging', 'production']:
                return env
            
            # Check if developer mode is enabled
            if frappe.conf.get('developer_mode'):
                return 'development'
            
            # Default to production for safety
            return 'production'
            
        except Exception:
            return 'production'
    
    def encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential for secure storage"""
        try:
            if not credential:
                return ""
            
            encrypted_bytes = self.cipher_suite.encrypt(credential.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
            
        except Exception as e:
            frappe.log_error(f"Error encrypting credential: {str(e)}", "Config Manager")
            return credential  # Return original if encryption fails
    
    def decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a credential for use"""
        try:
            if not encrypted_credential:
                return ""
            
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_credential.encode())
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
            
        except Exception as e:
            frappe.log_error(f"Error decrypting credential: {str(e)}", "Config Manager")
            return encrypted_credential  # Return original if decryption fails
    
    def store_channel_credentials(self, channel_name: str, credentials: Dict[str, Any]) -> bool:
        """Store encrypted channel credentials"""
        try:
            # Get or create channel configuration
            channel_config = None
            
            if frappe.db.exists("Channel Configuration", {"channel_name": channel_name}):
                channel_config = frappe.get_doc("Channel Configuration", {"channel_name": channel_name})
            else:
                channel_config = frappe.new_doc("Channel Configuration")
                channel_config.channel_name = channel_name
            
            # Encrypt and store credentials
            for key, value in credentials.items():
                if key.endswith('_secret') or key.endswith('_token') or key.endswith('_key'):
                    # Encrypt sensitive credentials
                    encrypted_value = self.encrypt_credential(str(value))
                    channel_config.set_password(key, encrypted_value)
                else:
                    # Store non-sensitive data normally
                    setattr(channel_config, key, value)
            
            channel_config.save()
            return True
            
        except Exception as e:
            frappe.log_error(f"Error storing channel credentials: {str(e)}", "Config Manager")
            return False
    
    def get_channel_credentials(self, channel_name: str) -> Dict[str, Any]:
        """Retrieve and decrypt channel credentials"""
        try:
            if not frappe.db.exists("Channel Configuration", {"channel_name": channel_name}):
                return {}
            
            channel_config = frappe.get_doc("Channel Configuration", {"channel_name": channel_name})
            credentials = {}
            
            # Get all fields from the doctype
            meta = frappe.get_meta("Channel Configuration")
            
            for field in meta.fields:
                if field.fieldtype == "Password":
                    # Decrypt password fields
                    encrypted_value = channel_config.get_password(field.fieldname)
                    if encrypted_value:
                        credentials[field.fieldname] = self.decrypt_credential(encrypted_value)
                elif field.fieldtype in ["Data", "Text", "Select", "Int", "Float"]:
                    # Get regular fields
                    value = getattr(channel_config, field.fieldname, None)
                    if value:
                        credentials[field.fieldname] = value
            
            return credentials
            
        except Exception as e:
            frappe.log_error(f"Error retrieving channel credentials: {str(e)}", "Config Manager")
            return {}
    
    def get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration"""
        try:
            base_config = {
                "webhook_timeout": 30,
                "max_retry_attempts": 3,
                "rate_limit_per_minute": 100,
                "log_level": "INFO",
                "debug_mode": False,
                "ssl_verify": True
            }
            
            if self.environment == 'development':
                base_config.update({
                    "webhook_base_url": f"https://dev.{frappe.conf.get('site_name', 'localhost')}",
                    "debug_mode": True,
                    "log_level": "DEBUG",
                    "rate_limit_per_minute": 1000,  # Higher limit for testing
                    "ssl_verify": False  # For local development
                })
            elif self.environment == 'staging':
                base_config.update({
                    "webhook_base_url": f"https://staging.{frappe.conf.get('site_name', 'localhost')}",
                    "debug_mode": True,
                    "log_level": "DEBUG",
                    "rate_limit_per_minute": 500
                })
            else:  # production
                base_config.update({
                    "webhook_base_url": f"https://{frappe.conf.get('site_name', 'localhost')}",
                    "debug_mode": False,
                    "log_level": "INFO",
                    "rate_limit_per_minute": 100,
                    "ssl_verify": True
                })
            
            # Override with site-specific config
            site_config = get_site_config()
            assistant_crm_config = site_config.get('assistant_crm_settings', {})
            base_config.update(assistant_crm_config)
            
            return base_config
            
        except Exception as e:
            frappe.log_error(f"Error getting environment config: {str(e)}", "Config Manager")
            return {}
    
    def validate_channel_config(self, channel_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate channel configuration based on channel type"""
        validation_result = {"valid": True, "errors": [], "warnings": []}
        
        try:
            if channel_type == "WhatsApp":
                required_fields = [
                    "whatsapp_business_account_id",
                    "whatsapp_phone_number_id", 
                    "api_key",
                    "whatsapp_webhook_secret"
                ]
                
                for field in required_fields:
                    if not config.get(field):
                        validation_result["errors"].append(f"Missing required field: {field}")
                        validation_result["valid"] = False
                
                # Validate phone number format
                phone_number = config.get("phone_number", "")
                if phone_number and not phone_number.startswith("+"):
                    validation_result["warnings"].append("Phone number should include country code with +")
            
            elif channel_type == "Facebook":
                required_fields = [
                    "facebook_page_id",
                    "facebook_app_id",
                    "api_key",  # Page access token
                    "facebook_app_secret"
                ]
                
                for field in required_fields:
                    if not config.get(field):
                        validation_result["errors"].append(f"Missing required field: {field}")
                        validation_result["valid"] = False
            
            elif channel_type == "Telegram":
                required_fields = ["api_key"]  # Bot token
                
                for field in required_fields:
                    if not config.get(field):
                        validation_result["errors"].append(f"Missing required field: {field}")
                        validation_result["valid"] = False
                
                # Validate bot token format
                bot_token = config.get("api_key", "")
                if bot_token and ":" not in bot_token:
                    validation_result["errors"].append("Invalid Telegram bot token format")
                    validation_result["valid"] = False
            
            elif channel_type == "SMS":
                sms_provider = config.get("sms_provider")
                if not sms_provider:
                    validation_result["errors"].append("SMS provider must be specified")
                    validation_result["valid"] = False
                
                if sms_provider == "Twilio":
                    required_fields = ["api_key", "api_secret"]  # Account SID and Auth Token
                    for field in required_fields:
                        if not config.get(field):
                            validation_result["errors"].append(f"Missing Twilio field: {field}")
                            validation_result["valid"] = False
            
            return validation_result
            
        except Exception as e:
            frappe.log_error(f"Error validating channel config: {str(e)}", "Config Manager")
            return {"valid": False, "errors": [str(e)], "warnings": []}
    
    def setup_webhook_urls(self, channel_type: str) -> Dict[str, str]:
        """Generate webhook URLs for channel configuration"""
        try:
            env_config = self.get_environment_config()
            base_url = env_config.get("webhook_base_url", "https://localhost")
            
            webhook_urls = {
                "WhatsApp": f"{base_url}/api/omnichannel/webhook/whatsapp",
                "Facebook": f"{base_url}/api/omnichannel/webhook/facebook", 
                "Instagram": f"{base_url}/api/omnichannel/webhook/instagram",
                "Telegram": f"{base_url}/api/omnichannel/webhook/telegram",
                "SMS": f"{base_url}/api/omnichannel/webhook/sms",
                "Voice": f"{base_url}/api/omnichannel/webhook/voice"
            }
            
            return {
                "webhook_url": webhook_urls.get(channel_type, ""),
                "verify_url": f"{base_url}/api/omnichannel/verify/{channel_type.lower()}",
                "status_url": f"{base_url}/api/omnichannel/status/{channel_type.lower()}"
            }
            
        except Exception as e:
            frappe.log_error(f"Error setting up webhook URLs: {str(e)}", "Config Manager")
            return {}


# API endpoints for configuration management

@frappe.whitelist()
def setup_channel_integration(channel_type, channel_name, credentials):
    """Setup a new channel integration with secure credential storage"""
    try:
        config_manager = ConfigManager()
        
        # Validate configuration
        validation_result = config_manager.validate_channel_config(channel_type, credentials)
        if not validation_result["valid"]:
            return {
                "success": False,
                "errors": validation_result["errors"],
                "warnings": validation_result.get("warnings", [])
            }
        
        # Store credentials securely
        success = config_manager.store_channel_credentials(channel_name, credentials)
        if not success:
            return {"success": False, "error": "Failed to store credentials"}
        
        # Generate webhook URLs
        webhook_urls = config_manager.setup_webhook_urls(channel_type)
        
        return {
            "success": True,
            "webhook_urls": webhook_urls,
            "warnings": validation_result.get("warnings", []),
            "message": f"{channel_type} integration configured successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error setting up channel integration: {str(e)}", "Config Manager")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_channel_configuration(channel_name):
    """Get channel configuration (excluding sensitive credentials)"""
    try:
        config_manager = ConfigManager()
        credentials = config_manager.get_channel_credentials(channel_name)
        
        # Remove sensitive data from response
        safe_config = {}
        for key, value in credentials.items():
            if not (key.endswith('_secret') or key.endswith('_token') or key.endswith('_key')):
                safe_config[key] = value
            else:
                safe_config[key] = "***HIDDEN***" if value else ""
        
        return {"success": True, "configuration": safe_config}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def test_channel_connection(channel_name):
    """Test connection to a configured channel"""
    try:
        config_manager = ConfigManager()
        credentials = config_manager.get_channel_credentials(channel_name)
        
        if not credentials:
            return {"success": False, "error": "Channel not configured"}
        
        channel_type = credentials.get("channel_type")
        
        # Perform channel-specific connection test
        if channel_type == "WhatsApp":
            test_result = test_whatsapp_connection(credentials)
        elif channel_type == "Facebook":
            test_result = test_facebook_connection(credentials)
        elif channel_type == "Telegram":
            test_result = test_telegram_connection(credentials)
        else:
            test_result = {"success": False, "error": f"Testing not implemented for {channel_type}"}
        
        return test_result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_whatsapp_connection(credentials):
    """Test WhatsApp Business API connection"""
    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {credentials.get('api_key')}",
            "Content-Type": "application/json"
        }
        
        # Test API access by getting business profile
        url = f"https://graph.facebook.com/v18.0/{credentials.get('whatsapp_phone_number_id')}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return {"success": True, "message": "WhatsApp connection successful"}
        else:
            return {"success": False, "error": f"API returned status {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_facebook_connection(credentials):
    """Test Facebook Messenger API connection"""
    try:
        import requests
        
        # Test page access token
        url = f"https://graph.facebook.com/v18.0/{credentials.get('facebook_page_id')}"
        params = {"access_token": credentials.get("api_key")}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            return {"success": True, "message": "Facebook connection successful"}
        else:
            return {"success": False, "error": f"API returned status {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_telegram_connection(credentials):
    """Test Telegram Bot API connection"""
    try:
        import requests
        
        bot_token = credentials.get("api_key")
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get("ok"):
                return {"success": True, "message": f"Telegram bot connection successful: @{bot_info['result']['username']}"}
            else:
                return {"success": False, "error": "Bot API returned error"}
        else:
            return {"success": False, "error": f"API returned status {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}
