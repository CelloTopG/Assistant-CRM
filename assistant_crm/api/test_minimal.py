# Minimal test API to verify module loading
import frappe
from frappe.utils import now

@frappe.whitelist(allow_guest=True)
def test_minimal():
    """Minimal test endpoint"""
    return {
        "success": True,
        "message": "Minimal test endpoint is working",
        "timestamp": now()
    }
