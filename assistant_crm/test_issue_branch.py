"""Test branch assignment on an actual Issue

NOTE: Beneficiary Profile doctype has been removed. This test now creates
an Issue directly without a linked beneficiary profile.
"""
import frappe

def execute():
    """
    Test the branch assignment flow by:
    1. Creating a test Issue with address fields
    2. Running the branch assignment
    3. Verifying the branch is set correctly

    NOTE: Beneficiary Profile doctype has been removed. Test now uses Issue custom fields directly.
    """
    from assistant_crm.services.branch_assignment_service import assign_branch_to_issue

    # NOTE: Beneficiary Profile doctype has been removed
    # Skipping beneficiary creation
    print("⚠️ Beneficiary Profile doctype has been removed - skipping beneficiary creation")
    
    # Create a test Issue linked to the beneficiary
    test_issue_id = "ISS-TEST-BRANCH-001"
    existing = frappe.db.exists("Issue", {"name": ["like", "ISS-%-BRANCH%"]})
    
    if not existing:
        issue = frappe.get_doc({
            "doctype": "Issue",
            "subject": "Test Branch Assignment",
            "raised_by": "test.branch@example.com",
            "custom_customer_nrc": "123456/78/1",
            "custom_customer_phone": "+260971234567",
            "status": "Open"
        })
        issue.flags.ignore_mandatory = True
        issue.insert(ignore_permissions=True)
        frappe.db.commit()
        test_issue_id = issue.name
        print(f"✅ Created test Issue: {test_issue_id}")
    else:
        test_issue_id = existing
        print(f"✅ Using existing test Issue: {test_issue_id}")
    
    # Check current branch value
    current_branch = frappe.db.get_value("Issue", test_issue_id, "custom_branch")
    print(f"📍 Current branch value: {current_branch or 'Not set'}")
    
    # Run the branch assignment
    print("🔄 Running branch assignment...")
    result = assign_branch_to_issue(test_issue_id)
    print(f"📊 Result: {result}")
    
    # Verify the branch was set
    new_branch = frappe.db.get_value("Issue", test_issue_id, "custom_branch")
    print(f"🏢 Assigned branch: {new_branch}")
    
    if new_branch == "Ndola":
        print("✅ SUCCESS! Branch correctly assigned based on address 'Chiwala, Ndola Rural'")
    else:
        print(f"⚠️ Expected 'Ndola' but got '{new_branch}'")
    
    return {
        "issue": test_issue_id,
        "branch": new_branch,
        "success": new_branch == "Ndola"
    }

