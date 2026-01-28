# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe.utils import now
from typing import Dict, Any, List, Optional
import time


class TelegramService:
    """Telegram Bot Service for bulk messaging and chat"""
    
    def __init__(self):
        self.settings = self.get_telegram_settings()
        self.bot_token = self.settings.get("bot_token")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.rate_limit = self.settings.get("rate_limit", 30)  # messages per second
        self.last_request_time = 0
        
    def get_telegram_settings(self) -> Dict[str, Any]:
        """Get Telegram configuration from Assistant CRM Settings"""
        try:
            settings = frappe.get_single("Assistant CRM Settings")
            return {
                "bot_token": settings.get("telegram_bot_token"),
                "webhook_url": settings.get("telegram_webhook_url"),
                "rate_limit": settings.get("telegram_rate_limit", 30),
                "enabled": settings.get("telegram_enabled", 1)
            }
        except Exception as e:
            frappe.log_error(f"Error getting Telegram settings: {str(e)}")
            return {}
    
    def send_message(self, chat_id: str, message: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
        """Send single Telegram message"""
        try:
            if not self.bot_token:
                return {"success": False, "error": "Telegram bot token not configured"}
            
            # Rate limiting
            self._apply_rate_limit()
            
            url = f"{self.base_url}/sendMessage"
            
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    return {
                        "success": True,
                        "message_id": result["result"]["message_id"],
                        "chat_id": chat_id
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("description", "Unknown error")
                    }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            frappe.log_error(f"Telegram send error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_bulk_messages(self, recipients: List[Dict], message: str) -> Dict[str, Any]:
        """Send bulk Telegram messages"""
        results = {
            "total": len(recipients),
            "sent": 0,
            "failed": 0,
            "results": []
        }
        
        for recipient in recipients:
            # Try to get Telegram chat ID from recipient data
            chat_id = recipient.get("telegram_chat_id") or recipient.get("chat_id")
            
            if not chat_id:
                results["failed"] += 1
                results["results"].append({
                    "recipient": recipient.get("email_id", "Unknown"),
                    "success": False,
                    "error": "No Telegram chat ID"
                })
                continue
            
            result = self.send_message(chat_id, message)
            
            if result["success"]:
                results["sent"] += 1
            else:
                results["failed"] += 1
            
            results["results"].append({
                "recipient": recipient.get("email_id", chat_id),
                "chat_id": chat_id,
                **result
            })
        
        return results
    
    def send_photo(self, chat_id: str, photo_url: str, caption: str = "") -> Dict[str, Any]:
        """Send photo message"""
        try:
            url = f"{self.base_url}/sendPhoto"
            
            data = {
                "chat_id": chat_id,
                "photo": photo_url,
                "caption": caption
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return {"success": result.get("ok"), "data": result}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_document(self, chat_id: str, document_url: str, caption: str = "") -> Dict[str, Any]:
        """Send document message"""
        try:
            url = f"{self.base_url}/sendDocument"
            
            data = {
                "chat_id": chat_id,
                "document": document_url,
                "caption": caption
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return {"success": result.get("ok"), "data": result}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def set_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """Set webhook URL for receiving messages"""
        try:
            url = f"{self.base_url}/setWebhook"
            
            data = {
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query"]
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return {"success": result.get("ok"), "data": result}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_webhook_info(self) -> Dict[str, Any]:
        """Get current webhook information"""
        try:
            url = f"{self.base_url}/getWebhookInfo"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return {"success": result.get("ok"), "data": result}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_bot_info(self) -> Dict[str, Any]:
        """Get bot information"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return {"success": result.get("ok"), "data": result}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _apply_rate_limit(self):
        """Apply rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.rate_limit  # seconds between requests
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


# API endpoint for webhook setup
@frappe.whitelist()
def setup_telegram_webhook():
    """Setup Telegram webhook"""
    try:
        telegram = TelegramService()
        
        # Get site URL and construct webhook URL
        site_url = frappe.utils.get_url()
        webhook_url = f"{site_url}/api/method/assistant_crm.api.telegram_webhook.telegram_webhook"
        
        result = telegram.set_webhook(webhook_url)
        
        if result["success"]:
            # Update settings with webhook URL
            settings = frappe.get_single("Assistant CRM Settings")
            settings.telegram_webhook_url = webhook_url
            settings.save()
            
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


# API endpoint for testing
@frappe.whitelist()
def test_telegram_bot():
    """Test Telegram bot configuration"""
    try:
        telegram = TelegramService()
        
        # Get bot info
        bot_info = telegram.get_bot_info()
        
        # Get webhook info
        webhook_info = telegram.get_webhook_info()
        
        return {
            "success": True,
            "bot_info": bot_info,
            "webhook_info": webhook_info
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
