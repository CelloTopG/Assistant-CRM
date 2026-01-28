# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now, get_datetime
import json
import hashlib
import hmac
from typing import Dict, Any

# NOTE: Employer Profile, Employee Profile, Beneficiary Profile, and Assessment Record
# doctypes have been removed. These data sources now come from ERPNext/Frappe core.
# Webhook handlers now use ERPNext doctypes where possible.


@frappe.whitelist(allow_guest=True)
def corebusiness_webhook():
    """Main webhook endpoint for CoreBusiness events"""
    try:
        # Get request data
        data = frappe.local.form_dict
        headers = frappe.local.request.headers
        
        # Verify webhook signature if configured
        if not _verify_webhook_signature(data, headers):
            frappe.throw(_("Invalid webhook signature"), frappe.AuthenticationError)
        
        # Parse event data
        event_type = data.get("event_type")
        event_data = data.get("data", {})
        
        if not event_type:
            return {"success": False, "message": "Missing event_type"}
        
        # Route to appropriate handler
        result = _handle_webhook_event(event_type, event_data)
        
        # Log webhook event
        _log_webhook_event(event_type, event_data, result)
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Webhook processing error: {str(e)}")
        return {"success": False, "message": str(e)}


def _verify_webhook_signature(data: Dict[str, Any], headers: Dict[str, str]) -> bool:
    """Verify webhook signature for security"""
    try:
        # Get webhook secret from settings
        settings = frappe.get_single("CoreBusiness Settings")
        webhook_secret = getattr(settings, 'webhook_secret', '')
        
        if not webhook_secret:
            # If no secret configured, allow all webhooks (development mode)
            return True
        
        # Get signature from headers
        signature = headers.get("X-CoreBusiness-Signature") or headers.get("x-corebusiness-signature")
        if not signature:
            return False
        
        # Calculate expected signature
        payload = json.dumps(data, sort_keys=True)
        expected_signature = hmac.new(
            webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        frappe.log_error(f"Webhook signature verification error: {str(e)}")
        return False


def _handle_webhook_event(event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Route webhook events to appropriate handlers"""
    
    handlers = {
        "employer.updated": _handle_employer_updated,
        "employer.created": _handle_employer_created,
        "beneficiary.updated": _handle_beneficiary_updated,
        "beneficiary.created": _handle_beneficiary_created,
        "claim.status_changed": _handle_claim_status_changed,
        "claim.created": _handle_claim_created,
        "payment.processed": _handle_payment_processed,
        "payment.failed": _handle_payment_failed,
        "compliance.status_changed": _handle_compliance_status_changed,
        "system.maintenance": _handle_system_maintenance
    }
    
    handler = handlers.get(event_type)
    if handler:
        return handler(event_data)
    else:
        return {"success": False, "message": f"Unknown event type: {event_type}"}


def _handle_employer_updated(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle employer updated event - Uses ERPNext Customer doctype"""
    try:
        employer_code = event_data.get("employer_code")
        if not employer_code:
            return {"success": False, "message": "Missing employer_code"}

        # Update ERPNext Customer instead
        if frappe.db.exists("Customer", employer_code):
            customer = frappe.get_doc("Customer", employer_code)
            if "customer_name" in event_data:
                customer.customer_name = event_data["customer_name"]
            customer.save()
            frappe.db.commit()
            _trigger_employer_update_notifications(employer_code, event_data)
            return {"success": True, "message": "Employer updated via ERPNext Customer"}

        return {"success": False, "message": "Employer not found in ERPNext Customer"}

    except Exception as e:
        frappe.log_error(f"Error handling employer updated event: {str(e)}")
        return {"success": False, "message": str(e)}


def _handle_employer_created(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle employer created event - Uses ERPNext Customer doctype"""
    try:
        employer_code = event_data.get("employer_code")
        if not employer_code:
            return {"success": False, "message": "Missing employer_code"}

        # Create ERPNext Customer instead
        if not frappe.db.exists("Customer", employer_code):
            customer = frappe.new_doc("Customer")
            customer.name = employer_code
            customer.customer_name = event_data.get("employer_name", employer_code)
            customer.customer_type = "Company"
            customer.insert()
            frappe.db.commit()
            _trigger_employer_welcome_notifications(employer_code, event_data)
            return {"success": True, "message": "Employer created via ERPNext Customer"}

        return {"success": True, "message": "Employer already exists"}

    except Exception as e:
        frappe.log_error(f"Error handling employer created event: {str(e)}")
        return {"success": False, "message": str(e)}


def _handle_beneficiary_updated(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle beneficiary updated event"""
    try:
        beneficiary_id = event_data.get("beneficiary_id")
        if not beneficiary_id:
            return {"success": False, "message": "Missing beneficiary_id"}
        
        # Update local cache
        _update_beneficiary_cache(beneficiary_id, event_data)
        
        # Trigger notifications
        _trigger_beneficiary_update_notifications(beneficiary_id, event_data)
        
        return {"success": True, "message": "Beneficiary updated successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error handling beneficiary updated event: {str(e)}")
        return {"success": False, "message": str(e)}


def _handle_beneficiary_created(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle beneficiary created event"""
    try:
        beneficiary_id = event_data.get("beneficiary_id")
        if not beneficiary_id:
            return {"success": False, "message": "Missing beneficiary_id"}
        
        # Create local cache entry
        _create_beneficiary_cache(beneficiary_id, event_data)
        
        # Trigger welcome notifications
        _trigger_beneficiary_welcome_notifications(beneficiary_id, event_data)
        
        return {"success": True, "message": "Beneficiary created successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error handling beneficiary created event: {str(e)}")
        return {"success": False, "message": str(e)}


def _handle_claim_status_changed(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle claim status changed event"""
    try:
        claim_number = event_data.get("claim_number")
        new_status = event_data.get("new_status")
        
        if not claim_number or not new_status:
            return {"success": False, "message": "Missing claim_number or new_status"}
        
        # Update local claim tracking
        _update_claim_status(claim_number, event_data)
        
        # Trigger status change notifications
        _trigger_claim_status_notifications(claim_number, new_status, event_data)
        
        return {"success": True, "message": "Claim status updated successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error handling claim status changed event: {str(e)}")
        return {"success": False, "message": str(e)}


def _handle_claim_created(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle claim created event"""
    try:
        claim_number = event_data.get("claim_number")
        if not claim_number:
            return {"success": False, "message": "Missing claim_number"}
        
        # Create local claim tracking
        _create_claim_tracking(claim_number, event_data)
        
        # Trigger claim submission notifications
        _trigger_claim_submission_notifications(claim_number, event_data)
        
        return {"success": True, "message": "Claim created successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error handling claim created event: {str(e)}")
        return {"success": False, "message": str(e)}


def _handle_payment_processed(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle payment processed event"""
    try:
        payment_reference = event_data.get("payment_reference")
        if not payment_reference:
            return {"success": False, "message": "Missing payment_reference"}
        
        # Update payment status
        _update_payment_status(payment_reference, "Processed", event_data)
        
        # Trigger payment confirmation notifications
        _trigger_payment_processed_notifications(payment_reference, event_data)
        
        return {"success": True, "message": "Payment processed successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error handling payment processed event: {str(e)}")
        return {"success": False, "message": str(e)}


def _handle_payment_failed(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle payment failed event"""
    try:
        payment_reference = event_data.get("payment_reference")
        if not payment_reference:
            return {"success": False, "message": "Missing payment_reference"}
        
        # Update payment status
        _update_payment_status(payment_reference, "Failed", event_data)
        
        # Trigger payment failure notifications
        _trigger_payment_failed_notifications(payment_reference, event_data)
        
        return {"success": True, "message": "Payment failure processed successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error handling payment failed event: {str(e)}")
        return {"success": False, "message": str(e)}


def _handle_compliance_status_changed(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle compliance status changed event"""
    try:
        employer_code = event_data.get("employer_code")
        new_status = event_data.get("new_status")
        
        if not employer_code or not new_status:
            return {"success": False, "message": "Missing employer_code or new_status"}
        
        # Update employer compliance status
        _update_employer_compliance(employer_code, new_status, event_data)
        
        # Trigger compliance notifications
        _trigger_compliance_notifications(employer_code, new_status, event_data)
        
        return {"success": True, "message": "Compliance status updated successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error handling compliance status changed event: {str(e)}")
        return {"success": False, "message": str(e)}


def _handle_system_maintenance(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle system maintenance event"""
    try:
        maintenance_type = event_data.get("maintenance_type")
        start_time = event_data.get("start_time")
        end_time = event_data.get("end_time")
        
        # Log maintenance event
        frappe.log_error(f"CoreBusiness maintenance scheduled: {maintenance_type} from {start_time} to {end_time}")
        
        # Trigger maintenance notifications
        _trigger_maintenance_notifications(maintenance_type, start_time, end_time, event_data)
        
        return {"success": True, "message": "Maintenance event processed successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error handling system maintenance event: {str(e)}")
        return {"success": False, "message": str(e)}


# ==================== HELPER FUNCTIONS ====================

def _log_webhook_event(event_type: str, event_data: Dict[str, Any], result: Dict[str, Any]):
    """Log webhook event for audit trail"""
    try:
        # Create webhook log entry
        webhook_log = frappe.new_doc("Webhook Log")
        webhook_log.event_type = event_type
        webhook_log.event_data = json.dumps(event_data)
        webhook_log.processing_result = json.dumps(result)
        webhook_log.success = result.get("success", False)
        webhook_log.timestamp = now()
        webhook_log.insert()
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Error logging webhook event: {str(e)}")


def _update_beneficiary_cache(beneficiary_id: str, event_data: Dict[str, Any]):
    """Update beneficiary cache with webhook data - Beneficiary Profile doctype removed"""
    # NOTE: Beneficiary Profile doctype has been removed
    # Beneficiary data now comes from ERPNext/Frappe core
    frappe.log_error(f"Beneficiary webhook received but Beneficiary Profile doctype removed: {beneficiary_id}")


def _create_beneficiary_cache(beneficiary_id: str, event_data: Dict[str, Any]):
    """Create new beneficiary cache entry - Beneficiary Profile doctype removed"""
    # NOTE: Beneficiary Profile doctype has been removed
    # Beneficiary data now comes from ERPNext/Frappe core
    frappe.log_error(f"Beneficiary webhook received but Beneficiary Profile doctype removed: {beneficiary_id}")


def _update_claim_status(claim_number: str, event_data: Dict[str, Any]):
    """Update claim status from webhook"""
    try:
        if frappe.db.exists("Claims Tracking", claim_number):
            claim_doc = frappe.get_doc("Claims Tracking", claim_number)
        else:
            claim_doc = frappe.new_doc("Claims Tracking")
            claim_doc.claim_number = claim_number

        # Update status and related fields
        claim_doc.status = event_data.get("new_status", claim_doc.status)
        if "assessment_date" in event_data:
            claim_doc.assessment_date = get_datetime(event_data["assessment_date"])
        if "decision_date" in event_data:
            claim_doc.decision_date = get_datetime(event_data["decision_date"])
        if "amount_approved" in event_data:
            claim_doc.amount_approved = event_data["amount_approved"]

        claim_doc.last_updated = now()
        claim_doc.save()
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"Error updating claim status: {str(e)}")


def _create_claim_tracking(claim_number: str, event_data: Dict[str, Any]):
    """Create new claim tracking entry"""
    try:
        claim_doc = frappe.new_doc("Claims Tracking")
        claim_doc.claim_number = claim_number
        claim_doc.claim_type = event_data.get("claim_type", "")
        claim_doc.beneficiary_name = event_data.get("beneficiary_name", "")
        claim_doc.status = event_data.get("status", "Submitted")
        claim_doc.amount_claimed = event_data.get("amount_claimed", 0)
        if "submission_date" in event_data:
            claim_doc.submission_date = get_datetime(event_data["submission_date"])
        claim_doc.last_updated = now()
        claim_doc.insert()
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"Error creating claim tracking: {str(e)}")


def _update_payment_status(payment_reference: str, status: str, event_data: Dict[str, Any]):
    """Update payment status from webhook"""
    try:
        if frappe.db.exists("Payment Status", payment_reference):
            payment_doc = frappe.get_doc("Payment Status", payment_reference)
        else:
            payment_doc = frappe.new_doc("Payment Status")
            payment_doc.payment_reference = payment_reference

        payment_doc.status = status
        if "amount" in event_data:
            payment_doc.amount = event_data["amount"]
        if "payment_date" in event_data:
            payment_doc.payment_date = get_datetime(event_data["payment_date"])
        if "beneficiary_name" in event_data:
            payment_doc.beneficiary_name = event_data["beneficiary_name"]
        if "transaction_id" in event_data:
            payment_doc.transaction_id = event_data["transaction_id"]

        payment_doc.last_updated = now()
        payment_doc.save()
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"Error updating payment status: {str(e)}")


def _update_employer_compliance(employer_code: str, new_status: str, event_data: Dict[str, Any]):
    """Update employer compliance status - Uses Compliance Report doctype"""
    try:
        # Create a compliance report entry instead of updating Employer Profile
        if frappe.db.exists("DocType", "Compliance Report"):
            compliance_report = frappe.new_doc("Compliance Report")
            compliance_report.employer_code = employer_code
            compliance_report.compliance_status = new_status
            compliance_report.report_date = now()
            compliance_report.insert()
            frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"Error updating employer compliance: {str(e)}")


# ==================== NOTIFICATION TRIGGERS ====================

def _trigger_employer_update_notifications(employer_code: str, event_data: Dict[str, Any]):
    """Trigger notifications for employer updates"""
    try:
        # Implementation for employer update notifications
        # This would integrate with the notification system
        pass
    except Exception as e:
        frappe.log_error(f"Error triggering employer update notifications: {str(e)}")


def _trigger_employer_welcome_notifications(employer_code: str, event_data: Dict[str, Any]):
    """Trigger welcome notifications for new employers"""
    try:
        # Implementation for employer welcome notifications
        pass
    except Exception as e:
        frappe.log_error(f"Error triggering employer welcome notifications: {str(e)}")


def _trigger_beneficiary_update_notifications(beneficiary_id: str, event_data: Dict[str, Any]):
    """Trigger notifications for beneficiary updates"""
    try:
        # Implementation for beneficiary update notifications
        pass
    except Exception as e:
        frappe.log_error(f"Error triggering beneficiary update notifications: {str(e)}")


def _trigger_beneficiary_welcome_notifications(beneficiary_id: str, event_data: Dict[str, Any]):
    """Trigger welcome notifications for new beneficiaries"""
    try:
        # Implementation for beneficiary welcome notifications
        pass
    except Exception as e:
        frappe.log_error(f"Error triggering beneficiary welcome notifications: {str(e)}")


def _trigger_claim_status_notifications(claim_number: str, new_status: str, event_data: Dict[str, Any]):
    """Trigger notifications for claim status changes"""
    try:
        # Implementation for claim status notifications
        pass
    except Exception as e:
        frappe.log_error(f"Error triggering claim status notifications: {str(e)}")


def _trigger_claim_submission_notifications(claim_number: str, event_data: Dict[str, Any]):
    """Trigger notifications for claim submissions"""
    try:
        # Implementation for claim submission notifications
        pass
    except Exception as e:
        frappe.log_error(f"Error triggering claim submission notifications: {str(e)}")


def _trigger_payment_processed_notifications(payment_reference: str, event_data: Dict[str, Any]):
    """Trigger notifications for processed payments"""
    try:
        # Implementation for payment processed notifications
        pass
    except Exception as e:
        frappe.log_error(f"Error triggering payment processed notifications: {str(e)}")


def _trigger_payment_failed_notifications(payment_reference: str, event_data: Dict[str, Any]):
    """Trigger notifications for failed payments"""
    try:
        # Implementation for payment failed notifications
        pass
    except Exception as e:
        frappe.log_error(f"Error triggering payment failed notifications: {str(e)}")


def _trigger_compliance_notifications(employer_code: str, new_status: str, event_data: Dict[str, Any]):
    """Trigger notifications for compliance status changes"""
    try:
        # Implementation for compliance notifications
        pass
    except Exception as e:
        frappe.log_error(f"Error triggering compliance notifications: {str(e)}")


def _trigger_maintenance_notifications(maintenance_type: str, start_time: str, end_time: str, event_data: Dict[str, Any]):
    """Trigger notifications for system maintenance"""
    try:
        # Implementation for maintenance notifications
        pass
    except Exception as e:
        frappe.log_error(f"Error triggering maintenance notifications: {str(e)}")
