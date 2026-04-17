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
                "gateway_response": json.dumps(response) if isinstance(response, dict) else str(response) if response else None,
                "response_code": response.get("responseCode") if isinstance(response, dict) else None,
                "error_message": error
            })
            log.insert(ignore_permissions=True)
            frappe.db.commit() 
            
            if self.debug:
                frappe.log_error(title="SMS Log Created", message=f"Log: {log.name} for {recipient}")
        except Exception as e:
            frappe.log_error(title="SMS Logging Failed", message=f"Error inserting SMS Log: {str(e)}\n\n{frappe.get_traceback()}")

    def send_message(self, to_number: str, message: str, survey_id: str = None) -> Dict[str, Any]:
        """Send single SMS message via configured provider and log the attempt."""
        # Ensure enabled is a clean boolean
        is_enabled = bool(self.enabled)

        if self.debug:
            frappe.log_error(title="SMSService.send_message Debug",
                           message=f"Sending to: {to_number}\nEnabled: {is_enabled}\nProvider: {self.provider}\nMessage length: {len(message)}")

        if not is_enabled:
            error_msg = "SMS is disabled in Assistant CRM SMS Settings"
            frappe.log_error(title="SMS Disabled Error",
                           message=f"Attempted to send SMS but service is disabled. Recipient: {to_number}")
            self.log_sms(to_number, message, "Failed", error=error_msg, survey_id=survey_id)
            return {"success": False, "error": error_msg}

        # Validate phone number
        if not to_number or not to_number.strip():
            error_msg = "Empty or invalid phone number provided"
            frappe.log_error(title="SMS Invalid Phone Error",
                           message=f"Invalid phone number: '{to_number}' for survey: {survey_id}")
            self.log_sms(to_number or "INVALID", message, "Failed", error=error_msg, survey_id=survey_id)
            return {"success": False, "error": error_msg}

        # Clean phone number
        try:
            clean_number = self._clean_phone_number(to_number)
            if self.debug:
                frappe.log_error(title="SMS Phone Cleaning",
                               message=f"Original: {to_number} -> Cleaned: {clean_number}")
        except Exception as e:
            error_msg = f"Phone number cleaning failed: {str(e)}"
            frappe.log_error(title="SMS Phone Cleaning Error",
                           message=f"Failed to clean phone {to_number}: {error_msg}")
            self.log_sms(to_number, message, "Failed", error=error_msg, survey_id=survey_id)
            return {"success": False, "error": error_msg}

        result = {"success": False, "error": "Unknown Provider"}
        start_time = frappe.utils.now()

        if self.provider == "Workers Notify" or self.provider == "Custom Gateway":
            if self.workers_gateway:
                try:
                    if self.debug:
                        frappe.log_error(title="SMS Workers Gateway Call",
                                       message=f"Calling send_single for {clean_number}")

                    res = self.workers_gateway.send_single(clean_number, message)

                    if self.debug:
                        frappe.log_error(title="SMS Workers Gateway Response",
                                       message=f"Response: {frappe.as_json(res)}")

                    if res and res.get("success"):
                        result = {"success": True, "message_id": res.get("message_id")}
                        self.log_sms(clean_number, message, "Sent", res, survey_id)

                        # Log success for monitoring
                        frappe.log_error(title="SMS Sent Successfully",
                                       message=f"SMS sent to {clean_number} via Workers Gateway. Survey: {survey_id}")

                    else:
                        error_msg = res.get("responseMessage") or res.get("error") or "Gateway reported failure"
                        result = {"success": False, "error": error_msg}

                        # Enhanced error logging
                        frappe.log_error(title="SMS Gateway Failure",
                                       message=f"SMS failed to {clean_number}. Error: {error_msg}\nResponse: {frappe.as_json(res)}\nSurvey: {survey_id}")

                        self.log_sms(clean_number, message, "Failed", res, survey_id, error_msg)

                except Exception as e:
                    error_msg = f"Workers Gateway exception: {str(e)}"
                    result = {"success": False, "error": error_msg}

                    frappe.log_error(title="SMS Gateway Exception",
                                   message=f"SMS exception for {clean_number}: {error_msg}\n{frappe.get_traceback()}\nSurvey: {survey_id}")

                    self.log_sms(clean_number, message, "Failed", survey_id=survey_id, error=str(e))

            else:
                error_msg = "Workers Gateway not initialized"
                frappe.log_error(title="SMS Gateway Init Error",
                               message=f"Workers Gateway not available for {clean_number}")
                result = {"success": False, "error": error_msg}
                self.log_sms(clean_number, message, "Failed", error=error_msg, survey_id=survey_id)

        elif self.provider == "Twilio":
            # Twilio logic (legacy)
            result = self.send_via_twilio(clean_number, message)
            if result["success"]:
                self.log_sms(clean_number, message, "Sent", result, survey_id)
                frappe.log_error(title="SMS Sent via Twilio",
                               message=f"SMS sent to {clean_number} via Twilio. Survey: {survey_id}")
            else:
                error_msg = result.get("error", "Twilio failed")
                frappe.log_error(title="SMS Twilio Failure",
                               message=f"SMS failed to {clean_number} via Twilio: {error_msg}")
                self.log_sms(clean_number, message, "Failed", result, survey_id, error_msg)

        else:
            error_msg = f"Unsupported SMS provider: {self.provider}"
            frappe.log_error(title="SMS Provider Error",
                           message=f"Unsupported provider '{self.provider}' for {clean_number}")
            result = {"success": False, "error": error_msg}
            self.log_sms(clean_number, message, "Failed", error=error_msg, survey_id=survey_id)

        # Log timing
        end_time = frappe.utils.now()
        duration = frappe.utils.time_diff_in_seconds(end_time, start_time)
        if duration > 10:  # Log slow requests
            frappe.log_error(title="SMS Slow Response",
                           message=f"SMS to {clean_number} took {duration:.2f} seconds")

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

    def diagnose_sms_configuration(self) -> Dict[str, Any]:
        """Diagnose SMS configuration and connectivity issues."""
        diagnostics = {
            "configuration": {},
            "connectivity": {},
            "recommendations": []
        }

        # Check basic configuration
        diagnostics["configuration"] = {
            "enabled": self.enabled,
            "provider": self.provider,
            "environment": self.settings.get("environment"),
            "debug_logging": self.debug,
            "timeout": self.settings.get("timeout")
        }

        if not self.enabled:
            diagnostics["recommendations"].append("SMS is disabled. Enable it in Assistant CRM SMS Settings.")

        if self.provider not in ["Workers Notify", "Custom Gateway", "Twilio"]:
            diagnostics["recommendations"].append(f"Unsupported provider: {self.provider}. Supported: Workers Notify, Custom Gateway, Twilio.")

        # Check provider-specific settings
        if self.provider in ["Workers Notify", "Custom Gateway"]:
            if not self.workers_gateway:
                diagnostics["recommendations"].append("Workers Gateway failed to initialize.")
            else:
                gateway_settings = {
                    "base_url": self.workers_gateway.base_url,
                    "has_api_key": bool(self.workers_gateway.api_key),
                    "timeout": self.workers_gateway.timeout
                }
                diagnostics["configuration"]["gateway"] = gateway_settings

                # Test connectivity
                try:
                    # Simple connectivity test
                    test_payload = {"recipient": "+260000000000", "text": "Test", "createdBy": "diagnostic"}
                    test_result = self.workers_gateway._post(f"{self.workers_gateway.base_url}/api/v1/notifier/sms", test_payload)
                    diagnostics["connectivity"]["gateway_test"] = {
                        "success": test_result.get("success", False),
                        "error": test_result.get("error", "Unknown")
                    }
                    if not test_result.get("success"):
                        diagnostics["recommendations"].append(f"Gateway connectivity test failed: {test_result.get('error')}")
                except Exception as e:
                    diagnostics["connectivity"]["gateway_test"] = {"success": False, "error": str(e)}
                    diagnostics["recommendations"].append(f"Gateway connectivity test exception: {str(e)}")

        elif self.provider == "Twilio":
            twilio_config = {
                "has_account_sid": bool(self.account_sid),
                "has_auth_token": bool(self.auth_token),
                "has_from_number": bool(self.from_number)
            }
            diagnostics["configuration"]["twilio"] = twilio_config

            missing = []
            if not self.account_sid: missing.append("Account SID")
            if not self.auth_token: missing.append("Auth Token")
            if not self.from_number: missing.append("From Number")

            if missing:
                diagnostics["recommendations"].append(f"Twilio configuration incomplete. Missing: {', '.join(missing)}")

        return diagnostics


@frappe.whitelist()
def diagnose_sms_configuration():
    """API endpoint to diagnose SMS configuration issues."""
    try:
        service = SMSService()
        diagnostics = service.diagnose_sms_configuration()
        return {"success": True, "diagnostics": diagnostics}
    except Exception as e:
        frappe.log_error(title="SMS Diagnostics Error", message=frappe.get_traceback())
        return {"success": False, "error": str(e)}


def send_survey_sms_async(recipient, campaign_name, response_id):
    """
    Asynchronous task to send a single survey invitation via SMS.
    Called by SurveyService.distribute_survey via frappe.enqueue to avoid blocking the request.
    """
    try:
        from assistant_crm.services.survey_service import SurveyService
        service = SurveyService()

        campaign = frappe.get_doc("Survey Campaign", campaign_name)

        if campaign.docstatus == 2:
            frappe.log_error(
                title="Async SMS Skipped — Campaign Cancelled",
                message=f"Campaign: {campaign_name} is cancelled (docstatus=2). SMS not sent to {recipient.get('mobile_no')}."
            )
            return

        result = service.send_survey_invitation(recipient, campaign, "SMS", response_id)

        if not result.get("success"):
            frappe.log_error(
                title="Async SMS Survey Invitation Failed",
                message=(
                    f"Campaign: {campaign_name}\n"
                    f"Response ID: {response_id}\n"
                    f"Recipient: {recipient.get('mobile_no')}\n"
                    f"Error: {result.get('error')}\n"
                    f"Gateway response: {result.get('response')}"
                )
            )
            try:
                frappe.db.set_value("Survey Response", response_id, "status", "Failed")
            except Exception:
                pass
        else:
            try:
                frappe.db.set_value("Survey Response", response_id, "status", "Sent")
            except Exception:
                pass

    except Exception as e:
        frappe.log_error(
            title="Async SMS Survey Invitation Failed",
            message=f"Campaign: {campaign_name}\nError: {str(e)}\n\n{frappe.get_traceback()}"
        )
