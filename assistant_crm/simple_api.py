"""
Simple API endpoints for assistant_crm app
This file provides a workaround for the import issues
"""

import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def ping():
    """Simple ping endpoint to test if the app is working"""
    return {
        "success": True,
        "message": "Assistant CRM is working!",
        "timestamp": frappe.utils.now()
    }

@frappe.whitelist(allow_guest=True)
def ask_bot_simple(message=None):
    """Simplified version with WorkCom's empathetic personality"""
    if not message:
        return {
            "success": False,
            "error": "I understand you're trying to reach out. Please include your message so I can help you with your WCFCB needs."
        }

    try:
        # Try to use the improved reply service
        from assistant_crm.assistant_crm.services.reply_service import get_bot_reply
        reply = get_bot_reply(message)

        return {
            "success": True,
            "reply": reply,
            "message": message,
            "timestamp": frappe.utils.now(),
            "personality": "WorkCom - WCFCB Team Member"
        }
    except Exception as e:
        # Fallback with WorkCom's empathetic tone
        return {
            "success": True,
            "reply": f"I understand you're reaching out about: {message}. I'm WorkCom from the WCFCB team, and I want to help you with this. While I'm having some technical difficulties accessing all my resources right now, I'm still here to assist you. Could you tell me if this is about claims, payments, employer services, or something else? I'll do my best to guide you in the right direction.",
            "message": message,
            "timestamp": frappe.utils.now(),
            "personality": "WorkCom - WCFCB Team Member",
            "fallback_used": True
        }

