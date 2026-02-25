# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import requests
import base64
from frappe.utils import now
from typing import Dict, Any, Optional, List
import time
import json
from assistant_crm.gateways.sms.workers_gateway import WorkersNotifyGateway


class SMSService:
    """
    Enterprise SMS Service for Assistant CRM.
    Acts as an abstraction layer between various gateways (Twilio, Workers Notify).
    Supports logging, bulk sending, and asynchronous execution.
    """
    
    def __init__(self):
        self.settings = self.get_sms_settings()
        self.enabled = self.settings.get("enabled", False)
        self.provider = self.settings.get("provider", "Workers Notify")
        self.debug = self.settings.get("enable_debug_logging", False)
        
        # Initialize Workers Gateway if selected
        self.workers_gateway = None
        if self.provider == "Workers Notify" or self.provider == "Custom Gateway":
            self.workers_gateway = WorkersNotifyGateway()
            
        # Twilio config (legacy/fallback)
        self.account_sid = self.settings.get("account_sid")
        self.auth_token = self.settings.get("auth_token")
        self.from_number = self.settings.get("from_number")
        
    def get_sms_settings(self) -> Dict[str, Any]:
        """Get SMS configuration from Assistant CRM SMS Settings (preferred) or legacy settings."""
        try:
            # Try new production settings DocType first
            if frappe.db.exists("DocType", "Assistant CRM SMS Settings"):
                settings = frappe.get_single("Assistant CRM SMS Settings")
                return {
                    "enabled": settings.get("enabled"),
                    "provider": "Workers Notify", # Default for new settings
                    "environment": settings.get("environment"),
                    "timeout": settings.get("timeout", 30),
                    "enable_debug_logging": settings.get("enable_debug_logging"),
                    "use_bulk_for_surveys": settings.get("use_bulk_for_surveys"),
                    "api_key": settings.get("api_key")
                }
            
            # Fallback to legacy settings
            settings = frappe.get_single("Assistant CRM Settings")
            return {
                "enabled": settings.get("sms_enabled", 1),
                "provider": settings.get("sms_provider", "Twilio"),
                "account_sid": settings.get("sms_account_sid"),
                "auth_token": settings.get("sms_auth_token"),
                "from_number": settings.get("sms_from_number"),
                "custom_url": settings.get("sms_custom_url"),
                "custom_api_key": settings.get("sms_custom_api_key")
            }
        except Exception as e:
            frappe.log_error(title="SMSService.get_sms_settings Error", message=frappe.get_traceback())
            return {}
    
    def log_sms(self, recipient: str, message: str, status: str, response: Dict = None, survey_id: str = None, error: str = None):
        """Create an entry in Assistant CRM SMS Log for audit trail."""
        try:
            if not frappe.db.exists("DocType", "Assistant CRM SMS Log"):
                return
                
            log = frappe.get_doc({
                "doctype": "Assistant CRM SMS Log",
                "recipient": recipient,
                "message": message,
                "status": status,
                "sent_at": now() if status == "Sent" else None,
                "survey": survey_id,
                "gateway_response": json.dumps(response) if response else None,
                "response_code": response.get("responseCode") if response else None,
                "error_message": error
            })
            log.insert(ignore_permissions=True)
            frappe.db.commit() # Commit log immediately
        except Exception as e:
            frappe.log_error(title="SMS Logging Failed", message=frappe.get_traceback())

    def send_message(self, to_number: str, message: str, survey_id: str = None) -> Dict[str, Any]:
        """Send single SMS message via configured provider and log the attempt."""
        if not self.enabled:
            return {"success": False, "error": "SMS is disabled in Assistant CRM Settings"}
            
        result = {"success": False, "error": "Unknown Provider"}
        
        if self.provider == "Workers Notify" or self.provider == "Custom Gateway":
            if self.workers_gateway:
                try:
                    res = self.workers_gateway.send_single(to_number, message)
                    if res and res.get("success"):
                        result = {"success": True}
                        self.log_sms(to_number, message, "Sent", res, survey_id)
                    else:
                        error_msg = res.get("responseMessage") or res.get("error") or "Gateway reported failure"
                        result = {"success": False, "error": error_msg}
                        self.log_sms(to_number, message, "Failed", res, survey_id, error_msg)
                except Exception as e:
                    result = {"success": False, "error": str(e)}
                    self.log_sms(to_number, message, "Failed", survey_id=survey_id, error=str(e))
            
        elif self.provider == "Twilio":
            # Twilio logic (legacy)
            result = self.send_via_twilio(to_number, message)
            if result["success"]:
                self.log_sms(to_number, message, "Sent", result, survey_id)
            else:
                self.log_sms(to_number, message, "Failed", result, survey_id, result.get("error"))
                
        return result

    def send_bulk_messages(self, recipients: List[Dict], message: str, survey_id: str = None) -> Dict[str, Any]:
        """Send bulk SMS messages using the specialized bulk endpoint if available."""
        if not self.enabled:
            return {"total": len(recipients), "sent": 0, "failed": len(recipients), "error": "SMS is disabled"}
            
        # Use Bulk endpoint for Workers Notify
        if (self.provider == "Workers Notify" or self.provider == "Custom Gateway") and self.workers_gateway:
            try:
                # Format recipients for the gateway
                to_numbers = []
                for r in recipients:
                    phone = r.get("mobile_no") or r.get("phone")
                    if phone:
                        to_numbers.append(self._clean_phone_number(phone))
                
                if not to_numbers:
                    return {"success": False, "error": "No valid recipients"}

                res = self.workers_gateway.send_bulk(to_numbers, message)
                
                if res and res.get("success"):
                    # Log individually for audit trail
                    for phone in to_numbers:
                        self.log_sms(phone, message, "Sent", res, survey_id)
                    return {"success": True, "sent_count": len(to_numbers)}
                else:
                    error_msg = res.get("responseMessage") or "Bulk Gateway reported failure"
                    for phone in to_numbers:
                        self.log_sms(phone, message, "Failed", res, survey_id, error_msg)
                    return {"success": False, "error": error_msg}
            except Exception as e:
                frappe.log_error(title="Bulk SMS Failure", message=frappe.get_traceback())
                return {"success": False, "error": str(e)}

        # Fallback to loop
        results = {"total": len(recipients), "sent": 0, "failed": 0}
        for r in recipients:
            phone = r.get("mobile_no") or r.get("phone")
            if phone:
                res = self.send_message(phone, message, survey_id)
                if res["success"]:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
        return results

    def _clean_phone_number(self, phone: str) -> str:
        """Clean and format phone number to E.164-ish format."""
        cleaned = ''.join(c for c in str(phone) if c.isdigit() or c == '+')
        if not cleaned.startswith('+'):
            if len(cleaned) == 9 and cleaned.startswith('9'): # Zambia 9xxxxxxxx
                cleaned = '+260' + cleaned
            elif len(cleaned) == 10 and cleaned.startswith('09'): # Zambia 09xxxxxxxx
                cleaned = '+260' + cleaned[1:]
            else:
                cleaned = '+' + cleaned
        return cleaned

    def send_via_twilio(self, to_number: str, message: str) -> Dict[str, Any]:
        """Legacy Twilio implementation."""
        try:
            if not self.account_sid or not self.auth_token:
                return {"success": False, "error": "Twilio credentials not configured"}
            
            auth_string = f"{self.account_sid}:{self.auth_token}"
            auth_b64 = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
            
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            clean_number = self._clean_phone_number(to_number)
            data = {"From": self.from_number, "To": clean_number, "Body": message}
            
            response = requests.post(url, headers=headers, data=data, timeout=30)
            if response.status_code == 201:
                return {"success": True, "sid": response.json().get("sid")}
            else:
                return {"success": False, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}


@frappe.whitelist()
def send_survey_sms_async(recipient: dict, campaign_name: str, response_id: str):
    """
    Asynchronous task to send a single survey invitation via SMS.
    Called by SurveyService.distribute_survey to avoid blocking the request.
    """
    try:
        from assistant_crm.services.survey_service import SurveyService
        service = SurveyService()
        
        # Load the campaign document
        campaign = frappe.get_doc("Survey Campaign", campaign_name)
        
        # Check if campaign is still active
        if campaign.status not in ["Active", "In Progress"]:
            return
            
        # Re-send the invitation specifically for SMS
        result = service.send_survey_invitation(recipient, campaign, "SMS", response_id)
        
        if not result.get("success"):
            # Logging is already handled inside SMSService.send_message
            pass
            
    except Exception as e:
        frappe.log_error(title="Async SMS Survey Invitation Failed", message=f"Campaign: {campaign_name}\nError: {str(e)}\n\n{frappe.get_traceback()}")
