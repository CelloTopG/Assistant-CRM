import frappe

@frappe.whitelist(allow_guest=True)
def test_endpoint():
    """Simple test endpoint to verify the app is working"""
    return {
        "success": True,
        "message": "Assistant CRM app is working!",
        "app_name": "assistant_crm"
    }
