"""Add branch field to Claim DocType"""
import frappe


def execute():
    """Add custom_branch field to Claim DocType if it doesn't exist"""
    
    # Check if field already exists
    existing = frappe.db.exists("Custom Field", {"dt": "Claim", "fieldname": "branch"})
    if existing:
        print(f"Field already exists: {existing}")
        return existing
    
    # Create custom field
    cf = frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Claim",
        "fieldname": "branch",
        "fieldtype": "Link",
        "options": "Branch",
        "label": "Branch",
        "insert_after": "approved_by",
        "description": "Branch associated with this claim",
        "in_list_view": 1,
        "in_standard_filter": 1
    })
    cf.insert()
    frappe.db.commit()
    print(f"Custom field 'branch' created on Claim DocType")
    return cf.name

