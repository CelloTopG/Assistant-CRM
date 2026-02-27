# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from assistant_crm.services.sms_service import SMSService

def handle_notification_log_after_insert(doc, method):
    """
    Hook to intercept Notification Logs and send SMS if the notification 
    matches specified high-priority alerts.
    """
    # Only process "System Notification" type logs
    if not doc.for_user:
        return

    # Map of Notification names that should trigger an SMS
    SMS_ENABLED_NOTIFICATIONS = {
        "Contribution Overdue Alert": "WCFCB Alert: Contribution {cid} for {employer} is overdue. Please pay to avoid penalties."
    }

    notification_name = frappe.db.get_value("Notification", doc.notification_name, "name")
    
    if notification_name in SMS_ENABLED_NOTIFICATIONS:
        send_sms_for_notification(doc, notification_name, SMS_ENABLED_NOTIFICATIONS[notification_name])

def send_sms_for_notification(log_doc, notification_name, template):
    """Fetches employer or user phone and sends SMS via enterprise gateway."""
    try:
        # 1. Get the linked document (Employer Contributions)
        linked_doc = frappe.get_doc(log_doc.document_type, log_doc.document_name)
        recipient_phone = None
        
        # 2. Strategy A: Try to find the Employer's (Customer's) Primary Contact
        if linked_doc.doctype == "Employer Contributions" and linked_doc.employer_id:
            # Look for primary contact linked to this Customer
            contact_name = frappe.db.get_value("Contact", {"is_primary_contact": 1, "links": ["like", f"%{linked_doc.employer_id}%"]}, "name")
            if not contact_name:
                # Fallback to any contact linked to this customer
                contact_name = frappe.db.get_value("Contact", {"links": ["like", f"%{linked_doc.employer_id}%"]}, "name")
            
            if contact_name:
                recipient_phone = frappe.db.get_value("Contact", contact_name, "mobile_no")

        # 3. Strategy B: Fallback to the User designated in the Notification Log (System Manager)
        if not recipient_phone:
            recipient_phone = frappe.db.get_value("User", log_doc.for_user, "mobile_no")

        if not recipient_phone:
            if SMSService().debug:
                frappe.log_error(title="Notification SMS Warning", message=f"No phone number found for {log_doc.for_user} or Employer {getattr(linked_doc, 'employer_id', 'N/A')}")
            return

        # 4. Format the message for SMS (short and clear)
        message = template.format(
            cid=linked_doc.name,
            employer=getattr(linked_doc, 'employer_name', 'Employer'),
            amount=getattr(linked_doc, 'outstanding_amount', '0')
        )

        # 5. Send via Production Gateway
        sms = SMSService()
        sms.send_message(recipient_phone, message)

    except Exception as e:
        frappe.log_error(title="Notification SMS Hook Failed", message=f"Notification: {notification_name}\nError: {str(e)}\n\n{frappe.get_traceback()}")
