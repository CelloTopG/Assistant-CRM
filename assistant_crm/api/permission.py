# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _

@frappe.whitelist()
def has_unified_inbox_permission():
    """
    Check if the current user has permission to access the Unified Inbox.
    """
    try:
        # Allow System Manager always
        if "System Manager" in frappe.get_roles():
            return True
        
        # Allow Assistant CRM roles
        user_roles = frappe.get_roles()
        allowed_roles = ["Assistant CRM Manager", "Assistant CRM Agent"]
        
        for role in allowed_roles:
            if role in user_roles:
                return True
        
        # For demo purposes, allow guest access
        if frappe.session.user == "Guest":
            return True
            
        return False
        
    except Exception as e:
        frappe.log_error(f"Error checking unified inbox permission: {str(e)}", "Permission Check")
        # For demo purposes, allow access on error
        return True

@frappe.whitelist()
def has_app_permission():
    """
    Check if the current user has permission to access the Assistant CRM app.
    """
    try:
        # Allow System Manager always
        if "System Manager" in frappe.get_roles():
            return True
        
        # Allow Assistant CRM roles
        user_roles = frappe.get_roles()
        allowed_roles = ["Assistant CRM Manager", "Assistant CRM Agent"]
        
        for role in allowed_roles:
            if role in user_roles:
                return True
                
        return False
        
    except Exception as e:
        frappe.log_error(f"Error checking app permission: {str(e)}", "Permission Check")
        return False
