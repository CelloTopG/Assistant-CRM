# Test module to verify API discovery
import frappe
from frappe.utils import now

@frappe.whitelist(allow_guest=True)
def test_function():
    """Simple test function to verify module loading"""
    return {
        "success": True,
        "message": "Test module is working",
        "timestamp": now()
    }
