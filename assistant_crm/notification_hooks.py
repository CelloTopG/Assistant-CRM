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
        "Contribution Overdue Alert": "WCFCB Alert: Contribution {cid} for {employer} is overdue. Please pay to avoid penalties.",
        "Conversation Assigned to Agent": "📱 WCFCB Alert: New conversation from {customer} ({platform}) assigned to you. Priority: {priority}. Check your inbox."
    }

    # NotificationLog docs do not always include notification_name (e.g., impersonation messages), so guard it.
    notification_ref = getattr(doc, "notification_name", None) or getattr(doc, "notification", None)
    if not notification_ref:
        return

    notification_name = frappe.db.get_value("Notification", notification_ref, "name")
    if not notification_name:
        return

    if notification_name in SMS_ENABLED_NOTIFICATIONS:
        send_sms_for_notification(doc, notification_name, SMS_ENABLED_NOTIFICATIONS[notification_name])

def send_sms_for_notification(log_doc, notification_name, template):
    """Fetches recipient phone and sends SMS via enterprise gateway."""
    try:
        # 1. Get the linked document
        linked_doc = frappe.get_doc(log_doc.document_type, log_doc.document_name)
        recipient_phone = None
        
        # 2. Handle Conversation Assigned to Agent
        if notification_name == "Conversation Assigned to Agent":
            # Get the assigned agent's phone number
            if linked_doc.assigned_agent:
                recipient_phone = frappe.db.get_value("User", linked_doc.assigned_agent, "mobile_no")
            
            if recipient_phone:
                # Format the message with conversation details
                message = template.format(
                    customer=linked_doc.customer_name or "Unknown",
                    platform=linked_doc.platform or "Unknown",
                    priority=linked_doc.priority or "Medium"
                )
                
                # Send SMS
                sms = SMSService()
                sms.send_message(recipient_phone, message)
                return
        
        # 3. Handle Contribution Overdue Alert (existing logic)
        if linked_doc.doctype == "Employer Contributions" and linked_doc.employer_id:
            # Look for primary contact linked to this Customer
            contact_name = frappe.db.get_value("Contact", {"is_primary_contact": 1, "links": ["like", f"%{linked_doc.employer_id}%"]}, "name")
            if not contact_name:
                # Fallback to any contact linked to this customer
                contact_name = frappe.db.get_value("Contact", {"links": ["like", f"%{linked_doc.employer_id}%"]}, "name")
            
            if contact_name:
                recipient_phone = frappe.db.get_value("Contact", contact_name, "mobile_no")

        # 4. Fallback to the User designated in the Notification Log
        if not recipient_phone:
            recipient_phone = frappe.db.get_value("User", log_doc.for_user, "mobile_no")

        if not recipient_phone:
            if SMSService().debug:
                frappe.log_error(
                    title="Notification SMS Warning", 
                    message=f"No phone number found for {log_doc.for_user} or in related document"
                )
            return

        # 5. Format and send the message
        if notification_name == "Contribution Overdue Alert":
            message = template.format(
                cid=linked_doc.name,
                employer=getattr(linked_doc, 'employer_name', 'Employer'),
                amount=getattr(linked_doc, 'outstanding_amount', '0')
            )
        else:
            # Generic message (if not handled above)
            message = template

        # 6. Send via SMS Service
        sms = SMSService()
        sms.send_message(recipient_phone, message)

    except Exception as e:
        frappe.log_error(
            title="Notification SMS Hook Failed", 
            message=f"Notification: {notification_name}\nError: {str(e)}\n\n{frappe.get_traceback()}"
        )
