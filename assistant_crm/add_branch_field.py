"""Add custom_branch field to Issue DocType"""
import frappe

def execute():
    """Add custom_branch field to Issue if it doesn't exist"""
    # Check if custom_branch field already exists
    existing = frappe.db.exists("Custom Field", {"dt": "Issue", "fieldname": "custom_branch"})
    
    if existing:
        print("✅ custom_branch field already exists on Issue")
        return existing
    
    # Create custom field
    cf = frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Issue",
        "fieldname": "custom_branch",
        "fieldtype": "Link",
        "options": "Branch",
        "label": "Branch",
        "insert_after": "custom_customer_nrc",
        "description": "Automatically assigned based on beneficiary location",
        "in_list_view": 1,
        "in_standard_filter": 1
    })
    cf.insert(ignore_permissions=True)
    frappe.db.commit()
    print("✅ Custom field 'custom_branch' created successfully on Issue DocType")
    return cf.name

if __name__ == "__main__":
    frappe.connect()
    execute()
    frappe.destroy()

