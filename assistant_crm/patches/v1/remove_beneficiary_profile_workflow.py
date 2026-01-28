"""
Patch: remove_beneficiary_profile_workflow

NOTE: This patch is now a NO-OP because Beneficiary Profile doctype has been removed.
The doctype functionality is now handled by ERPNext core.
"""
import frappe

WORKFLOW_NAME = "Beneficiary Profile Workflow"

def execute():
    # Beneficiary Profile doctype has been removed - still try to remove workflow if it exists
    try:
        if frappe.db.exists("Workflow", WORKFLOW_NAME):
            wf = frappe.get_doc("Workflow", WORKFLOW_NAME)
            wf.delete(ignore_permissions=True)
            frappe.db.commit()
    except Exception:
        # Log but don't block migrations
        pass

