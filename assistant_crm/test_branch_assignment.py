"""Test script for branch assignment service"""
import frappe

def execute():
    """Test the branch assignment service with sample addresses"""
    from assistant_crm.services.branch_assignment_service import (
        get_location_data,
        find_location_in_data,
        find_closest_branch,
        extract_location_tokens,
        normalize_text
    )
    
    # Test addresses
    test_addresses = [
        "Maria Chimona, Chiwala, Ndola Rural",
        "123 Main Street, Lusaka",
        "Plot 45, Kitwe Central",
        "Kasama North District",
        "Mongu Town Center",
        "Livingstone Victoria Falls Road",
    ]
    
    locations_data = get_location_data()
    print(f"✅ Loaded {len(locations_data)} locations from data file")
    print()
    
    for address in test_addresses:
        print(f"📍 Testing address: '{address}'")
        tokens = extract_location_tokens(address)
        print(f"   Tokens: {tokens}")
        
        location = find_location_in_data(address, locations_data)
        if location:
            print(f"   ✅ Found location: {location.get('name')} (Province: {location.get('province')})")
            branch = find_closest_branch(location)
            print(f"   🏢 Closest branch: {branch}")
        else:
            print(f"   ❌ No location match found")
        print()
    
    return "Test completed"

if __name__ == "__main__":
    frappe.connect()
    execute()
    frappe.destroy()

