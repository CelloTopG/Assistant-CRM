# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _

@frappe.whitelist()
def test_sms_configuration():
    """Test SMS configuration and send a test message."""
    try:
        from assistant_crm.services.sms_service import SMSService, diagnose_sms_configuration

        # First, run diagnostics
        diagnostics = diagnose_sms_configuration()
        if not diagnostics.get('success'):
            return {"success": False, "error": f"Diagnostics failed: {diagnostics.get('error')}"}

        diag = diagnostics.get('diagnostics', {})
        recommendations = diag.get('recommendations', [])

        if recommendations:
            return {
                "success": False,
                "error": "Configuration issues found",
                "recommendations": recommendations,
                "diagnostics": diag
            }

        # If diagnostics pass, try to send a test message
        service = SMSService()

        # Get current user for test recipient
        current_user = frappe.session.user
        user_doc = frappe.get_doc("User", current_user)
        test_phone = user_doc.mobile_no or user_doc.phone

        if not test_phone:
            return {
                "success": False,
                "error": "No phone number found for current user. Please add a mobile number to your user profile.",
                "diagnostics": diag
            }

        # Send test message
        test_message = f"Test SMS from Assistant CRM - {frappe.utils.now()}"
        result = service.send_message(test_phone, test_message, survey_id="TEST")

        if result.get("success"):
            return {
                "success": True,
                "message": f"Test SMS sent successfully to {test_phone}",
                "diagnostics": diag
            }
        else:
            return {
                "success": False,
                "error": f"Test SMS failed: {result.get('error')}",
                "diagnostics": diag
            }

    except Exception as e:
        frappe.log_error(title="SMS Test Failed", message=frappe.get_traceback())
        return {"success": False, "error": str(e)}