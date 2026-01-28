import frappe

def get_context(context):
    """Get context for Inbox page."""
    context.no_cache = 1
    context.title = "Inbox"
    
    # Check user permissions
    if not frappe.has_permission("Unified Inbox Conversation", "read"):
        frappe.throw("You don't have permission to access the Unified Inbox")
    
    # Get user info for the interface
    user = frappe.get_doc("User", frappe.session.user)
    context.user_info = {
        "name": user.name,
        "full_name": user.full_name or user.first_name or user.name,
        "email": user.email,
        "roles": frappe.get_roles(user.name)
    }
    
    # Get system settings
    try:
        settings = frappe.get_single("Assistant CRM Settings")
        context.system_settings = {
            "ai_enabled": getattr(settings, 'ai_enabled', True),
            "auto_response_enabled": getattr(settings, 'auto_response_enabled', True),
            "escalation_enabled": getattr(settings, 'escalation_enabled', True)
        }
    except:
        context.system_settings = {
            "ai_enabled": True,
            "auto_response_enabled": True,
            "escalation_enabled": True
        }
    
    # Get CoreBusiness integration status
    try:
        corebusiness_settings = frappe.get_single("CoreBusiness Settings")
        context.corebusiness_enabled = getattr(corebusiness_settings, 'enabled', False)
    except:
        context.corebusiness_enabled = False
    
    return context
