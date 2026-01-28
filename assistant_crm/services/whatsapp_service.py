# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe.utils import now
from typing import Dict, Any, List, Optional
import time


class WhatsAppService:
    """WhatsApp Business API Service for bulk messaging"""
    
    def __init__(self):
        self.settings = self.get_whatsapp_settings()
        self.access_token = self.settings.get("access_token")
        self.phone_number_id = self.settings.get("phone_number_id")
        self.business_account_id = self.settings.get("business_account_id")
        self.base_url = "https://graph.facebook.com/v18.0"
        self.rate_limit = self.settings.get("rate_limit", 1000)  # per hour
        self.last_request_time = 0
        
    def get_whatsapp_settings(self) -> Dict[str, Any]:
        """Get WhatsApp configuration from Assistant CRM Settings"""
        try:
            settings = frappe.get_single("Assistant CRM Settings")
            return {
                "access_token": settings.get("whatsapp_access_token"),
                "phone_number_id": settings.get("whatsapp_phone_number_id"),
                "business_account_id": settings.get("whatsapp_business_account_id"),
                "webhook_verify_token": settings.get("whatsapp_webhook_verify_token"),
                "rate_limit": settings.get("whatsapp_rate_limit", 1000),
                "enabled": settings.get("whatsapp_enabled", 1)
            }
        except Exception as e:
            frappe.log_error(f"Error getting WhatsApp settings: {str(e)}")
            return {}
    
    def send_message(self, to_number: str, message: str, message_type: str = "text") -> Dict[str, Any]:
        """Send single WhatsApp message"""
        try:
            if not self.access_token or not self.phone_number_id:
                return {"success": False, "error": "WhatsApp credentials not configured"}
            
            # Rate limiting
            self._apply_rate_limit()
            
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Clean phone number
            clean_number = self._clean_phone_number(to_number)
            
            # Prepare message data
            data = {
                "messaging_product": "whatsapp",
                "to": clean_number,
                "type": message_type
            }
            
            if message_type == "text":
                data["text"] = {"body": message}
            elif message_type == "template":
                # For template messages (requires pre-approved templates)
                data["template"] = message
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "message_id": result.get("messages", [{}])[0].get("id"),
                    "to": clean_number
                }
            else:
                error_data = response.json() if response.content else {}
                return {
                    "success": False,
                    "error": error_data.get("error", {}).get("message", f"HTTP {response.status_code}"),
                    "error_code": error_data.get("error", {}).get("code")
                }
                
        except Exception as e:
            frappe.log_error(f"WhatsApp send error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_template_message(self, to_number: str, template_name: str, parameters: List[str] = None) -> Dict[str, Any]:
        """Send WhatsApp template message"""
        try:
            template_data = {
                "name": template_name,
                "language": {"code": "en"}
            }
            
            if parameters:
                template_data["components"] = [{
                    "type": "body",
                    "parameters": [{"type": "text", "text": param} for param in parameters]
                }]
            
            return self.send_message(to_number, template_data, "template")
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_bulk_messages(self, recipients: List[Dict], message: str) -> Dict[str, Any]:
        """Send bulk WhatsApp messages"""
        results = {
            "total": len(recipients),
            "sent": 0,
            "failed": 0,
            "results": []
        }
        
        for recipient in recipients:
            phone = recipient.get("mobile_no") or recipient.get("phone")
            if not phone:
                results["failed"] += 1
                results["results"].append({
                    "recipient": recipient.get("email_id", "Unknown"),
                    "success": False,
                    "error": "No phone number"
                })
                continue
            
            result = self.send_message(phone, message)
            
            if result["success"]:
                results["sent"] += 1
            else:
                results["failed"] += 1
            
            results["results"].append({
                "recipient": recipient.get("email_id", phone),
                "phone": phone,
                **result
            })
        
        return results
    
    def send_media_message(self, to_number: str, media_url: str, media_type: str, caption: str = "") -> Dict[str, Any]:
        """Send media message (image, document, video, audio)"""
        try:
            clean_number = self._clean_phone_number(to_number)
            
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "messaging_product": "whatsapp",
                "to": clean_number,
                "type": media_type,
                media_type: {
                    "link": media_url
                }
            }
            
            if caption and media_type in ["image", "video", "document"]:
                data[media_type]["caption"] = caption
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "message_id": result.get("messages", [{}])[0].get("id"),
                    "to": clean_number
                }
            else:
                error_data = response.json() if response.content else {}
                return {
                    "success": False,
                    "error": error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_business_profile(self) -> Dict[str, Any]:
        """Get WhatsApp Business profile information"""
        try:
            url = f"{self.base_url}/{self.phone_number_id}/whatsapp_business_profile"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _clean_phone_number(self, phone: str) -> str:
        """Clean and format phone number for WhatsApp"""
        # Remove all non-digit characters except +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Remove + for WhatsApp API (it expects numbers without +)
        if cleaned.startswith('+'):
            cleaned = cleaned[1:]
        
        # Add Zambian country code if needed
        if len(cleaned) == 9 and cleaned.startswith('9'):
            cleaned = '260' + cleaned
        elif len(cleaned) == 10 and cleaned.startswith('09'):
            cleaned = '260' + cleaned[1:]
        
        return cleaned
    
    def _apply_rate_limit(self):
        """Apply rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 3600.0 / self.rate_limit  # seconds between requests (hourly limit)
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


# API endpoint for testing
@frappe.whitelist()
def test_whatsapp_connection():
    """Test WhatsApp Business API connection"""
    try:
        whatsapp = WhatsAppService()
        
        # Get business profile
        profile_info = whatsapp.get_business_profile()
        
        return {
            "success": True,
            "profile_info": profile_info,
            "settings": whatsapp.settings
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
