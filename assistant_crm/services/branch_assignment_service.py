"""
Branch Assignment Service
Automatically assigns the nearest branch to an Issue based on beneficiary address location.
Uses the Zambia distance dataset to find the closest branch.
"""
import frappe
from frappe import _
import json
import re

# Branch column mapping from the dataset to actual Branch names in the system
BRANCH_COLUMN_MAP = {
    "km_to_Kawambwa": "Kawambwa",
    "km_to_Mkushi": "Mkushi",
    "km_to_Kabwe": "Kabwe",
    "km_to_Mansa": "Mansa",
    "km_to_Solwezi": "Solwezi",
    "km_to_Kabompo": "Kabompo",
    "km_to_Monze": "Monze",
    "km_to_Choma": "Choma",
    "km_to_Livingstone": "Livingstone",
    "km_to_Mazabuka": "Mazabuka",
    "km_to_Mpika": "Mpika",
    "km_to_Chinsali": "Chinsali",
    "km_to_Lusaka": "Lusaka",
    "km_to_Kafue": "Kafue",
    "km_to_Mongu": "Mongu",
    "km_to_Lusaka_Mt_Makulu": "Lusaka-Mount",
    "km_to_Lusaka_Cairo_Rd": "Lusaka-Cairo",
    "km_to_Kasama": "Kasama",
    "km_to_Petauke": "Petauke",
    "km_to_Chipata": "Chipata",
    "km_to_Ndola": "Ndola",
    "km_to_Mufulira": "Mufulira",
    "km_to_Luanshya": "Luanshya",
    "km_to_Kitwe": "Kitwe",
    "km_to_Chingola": "Chingola",
}

# Fallback province-to-branch mapping when location lookup fails
PROVINCE_BRANCH_FALLBACK = {
    "Lusaka": "Lusaka",
    "Central": "Kabwe",
    "Copperbelt": "Ndola",
    "Eastern": "Chipata",
    "Northern": "Kasama",
    "Luapula": "Mansa",
    "Muchinga": "Mpika",
    "North-Western": "Solwezi",
    "Southern": "Livingstone",
    "Western": "Mongu",
}

DEFAULT_BRANCH = "Head Office"


def get_location_data():
    """Load the Zambia location distance data from JSON file"""
    import os
    data_path = os.path.join(
        os.path.dirname(__file__),
        "..", "data", "zambia_locations.json"
    )
    try:
        with open(data_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        frappe.log_error(f"Location data file not found: {data_path}", "Branch Assignment")
        return []
    except json.JSONDecodeError as e:
        frappe.log_error(f"Error parsing location data: {e}", "Branch Assignment")
        return []


def normalize_text(text):
    """Normalize text for matching - lowercase and remove special chars"""
    if not text:
        return ""
    return re.sub(r'[^a-z0-9\s]', '', text.lower().strip())


def extract_location_tokens(address):
    """Extract potential location names from an address string"""
    if not address:
        return []
    # Split by common separators
    tokens = re.split(r'[,\.\-/\n]+', address)
    # Clean and normalize
    return [normalize_text(t) for t in tokens if t.strip()]


def find_location_in_data(address, locations_data):
    """
    Search for a location match in the dataset based on address text.
    Returns the matching location record or None.
    """
    tokens = extract_location_tokens(address)
    if not tokens:
        return None
    
    # Try to match each token against location names
    for location in locations_data:
        loc_name = normalize_text(location.get("name", ""))
        if not loc_name:
            continue
        
        for token in tokens:
            # Exact match or token contains location name
            if loc_name == token or loc_name in token or token in loc_name:
                return location
    
    return None


def find_closest_branch(location_record):
    """
    Given a location record with distances, find the closest branch.
    Returns the branch name.
    """
    if not location_record:
        return None
    
    min_distance = float('inf')
    closest_branch = None
    
    for col_name, branch_name in BRANCH_COLUMN_MAP.items():
        distance = location_record.get(col_name)
        if distance is not None and isinstance(distance, (int, float)):
            if distance < min_distance:
                min_distance = distance
                closest_branch = branch_name
    
    return closest_branch


def get_beneficiary_from_issue(issue_doc):
    """
    Try to find a Beneficiary Profile linked to the Issue.
    Uses: custom_customer_nrc, custom_customer_phone, raised_by email

    NOTE: Beneficiary Profile doctype has been removed - returns None.
    Beneficiary data is now managed externally.
    """
    # NOTE: Beneficiary Profile doctype has been removed
    # Beneficiary data is now managed externally
    _ = issue_doc  # Unused
    return None


def determine_branch_for_issue(issue_name):
    """
    Main function to determine the appropriate branch for an Issue.

    Strategy:
    1. Find beneficiary linked to Issue
    2. Get physical_address from beneficiary
    3. Parse address to find location in dataset
    4. Use distance data to find closest branch
    5. Fallback to province-based mapping
    6. Final fallback to Head Office

    Returns: branch name string
    """
    issue_doc = frappe.get_doc("Issue", issue_name)
    beneficiary = get_beneficiary_from_issue(issue_doc)

    if not beneficiary:
        frappe.log_error(
            f"No beneficiary found for Issue {issue_name}",
            "Branch Assignment"
        )
        return DEFAULT_BRANCH

    # Try physical address first
    address = beneficiary.get("physical_address") or ""
    city = beneficiary.get("city") or ""
    province = beneficiary.get("province") or ""

    # Combine address sources for better matching
    full_address = f"{address} {city}"

    locations_data = get_location_data()

    if locations_data:
        location_record = find_location_in_data(full_address, locations_data)

        if location_record:
            branch = find_closest_branch(location_record)
            if branch and frappe.db.exists("Branch", branch):
                return branch

    # Fallback: use province mapping
    if province and province in PROVINCE_BRANCH_FALLBACK:
        fallback_branch = PROVINCE_BRANCH_FALLBACK[province]
        if frappe.db.exists("Branch", fallback_branch):
            return fallback_branch

    return DEFAULT_BRANCH


def assign_branch_to_issue(issue_name):
    """
    Background job function to assign branch to an Issue.
    Called via frappe.enqueue() after Issue creation.
    """
    try:
        branch = determine_branch_for_issue(issue_name)

        # Update the Issue with the assigned branch
        frappe.db.set_value("Issue", issue_name, "custom_branch", branch, update_modified=False)
        frappe.db.commit()

        frappe.log_error(
            f"✅ Assigned branch '{branch}' to Issue {issue_name}",
            "Branch Assignment Success"
        )

        return {"success": True, "issue": issue_name, "branch": branch}

    except Exception as e:
        frappe.log_error(
            f"Error assigning branch to Issue {issue_name}: {str(e)}",
            "Branch Assignment Error"
        )
        return {"success": False, "issue": issue_name, "error": str(e)}


def enqueue_branch_assignment(issue_name):
    """
    Enqueue the branch assignment job for background processing.
    This is the function called from the Issue hook.
    """
    frappe.enqueue(
        "assistant_crm.services.branch_assignment_service.assign_branch_to_issue",
        issue_name=issue_name,
        queue="short",
        timeout=120,
        now=frappe.flags.in_test  # Run immediately during tests
    )


# For manual testing
@frappe.whitelist()
def test_branch_assignment(issue_name):
    """Manually trigger branch assignment for testing"""
    return assign_branch_to_issue(issue_name)

