# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import requests
import base64
from frappe.utils import now
from typing import Dict, Any, Optional
import time
import json


class SMSService:
    """SMS Service using Twilio API for bulk messaging"""
    
    def __init__(self):
        self.settings = self.get_sms_settings()
        self.provider = self.settings.get("provider", "Twilio")
        self.account_sid = self.settings.get("account_sid")
        self.auth_token = self.settings.get("auth_token")
        self.from_number = self.settings.get("from_number")
        self.rate_limit = self.settings.get("rate_limit", 60)
        self.custom_url = self.settings.get("custom_url")
        self.custom_api_key = self.settings.get("custom_api_key")
        self.base_url = "https://api.twilio.com/2010-04-01"
        self.last_request_time = 0
        
    def get_sms_settings(self) -> Dict[str, Any]:
        """Get SMS configuration from Assistant CRM Settings"""
        try:
            settings = frappe.get_single("Assistant CRM Settings")
            return {
                "provider": settings.get("sms_provider", "Twilio"),
                "account_sid": settings.get("sms_account_sid"),
                "auth_token": settings.get("sms_auth_token"),
                "from_number": settings.get("sms_from_number"),
                "rate_limit": settings.get("sms_rate_limit", 60),
                "enabled": settings.get("sms_enabled", 1),
                "custom_url": settings.get("sms_custom_url"),
                "custom_api_key": settings.get("sms_custom_api_key")
            }
        except Exception as e:
            frappe.log_error(f"Error getting SMS settings: {str(e)}")
            return {}
    
    def send_message(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send single SMS message via configured provider"""
        if self.provider == "Custom Gateway":
            return self.send_via_custom_gateway(to_number, message)
        return self.send_via_twilio(to_number, message)

    def send_via_twilio(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send single SMS message via Twilio"""
        try:
            if not self.account_sid or not self.auth_token:
                return {"success": False, "error": "Twilio credentials not configured"}
            
            # Rate limiting
            self._apply_rate_limit()
            
            # Prepare authentication
            auth_string = f"{self.account_sid}:{self.auth_token}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            # Prepare request
            url = f"{self.base_url}/Accounts/{self.account_sid}/Messages.json"
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Clean phone number
            clean_number = self._clean_phone_number(to_number)
            
            data = {
                "From": self.from_number,
                "To": clean_number,
                "Body": message
            }
            
            # Send request
            response = requests.post(url, headers=headers, data=data, timeout=30)
            
            if response.status_code == 201:
                result = response.json()
                return {
                    "success": True,
                    "message_sid": result.get("sid"),
                    "status": result.get("status"),
                    "to": clean_number
                }
            else:
                error_data = response.json() if response.content else {}
                return {
                    "success": False,
                    "error": error_data.get("message", f"HTTP {response.status_code}"),
                    "error_code": error_data.get("code")
                }
                
        except Exception as e:
            frappe.log_error(f"Twilio SMS send error: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_via_custom_gateway(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send single SMS message via Custom Gateway endpoint"""
        try:
            if not self.custom_url:
                return {"success": False, "error": "Custom Gateway URL not configured"}

            clean_number = self._clean_phone_number(to_number)
            
            # Payload for saveBulkSms endpoint (expects a list of messages)
            payload = [{
                "mobileNumber": clean_number,
                "message": message,
                "source": self.from_number or "SurveyBot"
            }]
            
            headers = {
                "Content-Type": "application/json"
            }
            if self.custom_api_key:
                headers["X-API-Key"] = self.custom_api_key

            response = requests.post(self.custom_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code in (200, 201):
                return {
                    "success": True,
                    "status": "sent",
                    "to": clean_number
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            frappe.log_error(f"Custom SMS Gateway error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def send_bulk_messages(self, recipients: list, message: str) -> Dict[str, Any]:
        """Send bulk SMS messages. Efficiently uses the bulk endpoint if provider is Custom."""
        if self.provider == "Custom Gateway" and self.custom_url:
            return self.send_bulk_via_custom_gateway(recipients, message)
        
        # Fallback to loop for Twilio or if custom URL is missing
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
            
            result = self.send_message(phone, recipient.get('message', message))
            
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

    def send_bulk_via_custom_gateway(self, recipients: list, message: str) -> Dict[str, Any]:
        """Send all SMS messages in a single request for the Custom Gateway"""
        try:
            payload = []
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
                    continue
                
                clean_number = self._clean_phone_number(phone)
                payload.append({
                    "mobileNumber": clean_number,
                    "message": recipient.get('message', message),
                    "source": self.from_number or "SurveyBot"
                })

            if not payload:
                return results

            headers = {
                "Content-Type": "application/json"
            }
            if self.custom_api_key:
                headers["X-API-Key"] = self.custom_api_key

            response = requests.post(self.custom_url, json=payload, headers=headers, timeout=60)
            
            if response.status_code in (200, 201):
                results["sent"] = len(payload)
                return results
            else:
                results["failed"] = len(payload)
                frappe.log_error(f"Bulk Custom Gateway error: HTTP {response.status_code} - {response.text}")
                return results

        except Exception as e:
            frappe.log_error(f"Bulk Custom Gateway exception: {str(e)}")
            return {"success": False, "error": str(e)}

    def _clean_phone_number(self, phone: str) -> str:
        """Clean and format phone number"""
        # Remove all non-digit characters except +
        cleaned = ''.join(c for c in str(phone) if c.isdigit() or c == '+')
        
        # Add + if not present and number doesn't start with country code
        if not cleaned.startswith('+'):
            # Assume Zambian number if no country code
            if len(cleaned) == 9 and cleaned.startswith('9'):
                cleaned = '+260' + cleaned
            elif len(cleaned) == 10 and cleaned.startswith('09'):
                cleaned = '+260' + cleaned[1:]
            else:
                cleaned = '+' + cleaned
        
        return cleaned
    
    def _apply_rate_limit(self):
        """Apply rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 60.0 / self.rate_limit  # seconds between requests
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """Get status of sent message"""
        try:
            auth_string = f"{self.account_sid}:{self.auth_token}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            url = f"{self.base_url}/Accounts/{self.account_sid}/Messages/{message_sid}.json"
            headers = {"Authorization": f"Basic {auth_b64}"}
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}


# Webhook handler for delivery status updates
@frappe.whitelist(allow_guest=True, methods=["POST"])
def twilio_webhook():
    """Handle Twilio delivery status webhooks"""
    try:
        # Get webhook data
        form_data = frappe.form_dict
        
        message_sid = form_data.get("MessageSid")
        message_status = form_data.get("MessageStatus")
        error_code = form_data.get("ErrorCode")
        
        # Log delivery status
        frappe.log_error(
            f"SMS Delivery Status - SID: {message_sid}, Status: {message_status}, Error: {error_code}",
            "Twilio Webhook"
        )
        
        # Update message status in database if needed
        # This can be enhanced to update campaign statistics
        
        return {"status": "success"}
        
    except Exception as e:
        frappe.log_error(f"Twilio webhook error: {str(e)}")
        return {"status": "error"}
