#!/usr/bin/env python3
"""
Test field mappings using bench execute command
"""

import frappe

def test_field_mappings():
    """Test LiveDataRetrievalService field mappings with real ERPNext data"""
    
    print("=" * 80)
    print("REAL ERPNEXT FIELD MAPPING VALIDATION")
    print("=" * 80)
    
    results = {
        "doctypes_tested": [],
        "field_validation": {},
        "data_counts": {},
        "errors": []
    }
    
    try:
        # Import the service
        from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService
        service = LiveDataRetrievalService()
        
        print(f"✅ Service initialized: {service.service_name}")
        
        # Test DocTypes
        doctypes_to_test = [
            "Customer",
            "Beneficiary Profile", 
            "Payment Entry",
            "Insurance Claim",
            "User"
        ]
        
        print("\n" + "=" * 60)
        print("DocType Validation Results:")
        print("=" * 60)
        
        for doctype in doctypes_to_test:
            try:
                exists = service._validate_doctype_exists(doctype)
                results["doctypes_tested"].append({"doctype": doctype, "exists": exists})
                
                if exists:
                    # Get field count
                    meta = frappe.get_meta(doctype)
                    field_count = len([f for f in meta.fields if f.fieldtype not in ['Section Break', 'Column Break', 'Tab Break']])
                    print(f"✅ {doctype}: EXISTS ({field_count} fields)")
                    
                    # Get record count
                    try:
                        count = frappe.db.count(doctype)
                        results["data_counts"][doctype] = count
                        print(f"   Records: {count}")
                    except Exception as e:
                        results["data_counts"][doctype] = f"Error: {str(e)}"
                        print(f"   Records: Error - {str(e)}")
                else:
                    print(f"❌ {doctype}: NOT FOUND")
                    
            except Exception as e:
                error_msg = f"Error testing {doctype}: {str(e)}"
                results["errors"].append(error_msg)
                print(f"❌ {doctype}: ERROR - {str(e)}")
        
        # Test Customer fields
        if service._validate_doctype_exists("Customer"):
            print("\n" + "=" * 60)
            print("Customer Field Validation:")
            print("=" * 60)
            
            customer_fields = [
                "customer_name", "email_id", "mobile_no", "customer_type",
                "territory", "customer_group", "phone", "website"
            ]
            
            results["field_validation"]["Customer"] = {}
            for field in customer_fields:
                has_field = service._validate_doctype_field("Customer", field)
                results["field_validation"]["Customer"][field] = has_field
                print(f"Customer.{field}: {'✅ EXISTS' if has_field else '❌ NOT FOUND'}")
        
        # Test Beneficiary Profile fields
        if service._validate_doctype_exists("Beneficiary Profile"):
            print("\n" + "=" * 60)
            print("Beneficiary Profile Field Validation:")
            print("=" * 60)
            
            beneficiary_fields = [
                "beneficiary_number", "nrc_number", "first_name", "last_name", 
                "full_name", "email", "phone", "mobile", "benefit_status", 
                "monthly_benefit_amount", "benefit_start_date", "date_of_birth"
            ]
            
            results["field_validation"]["Beneficiary Profile"] = {}
            for field in beneficiary_fields:
                has_field = service._validate_doctype_field("Beneficiary Profile", field)
                results["field_validation"]["Beneficiary Profile"][field] = has_field
                print(f"Beneficiary Profile.{field}: {'✅ EXISTS' if has_field else '❌ NOT FOUND'}")
        
        # Test service availability
        print("\n" + "=" * 60)
        print("Service Status:")
        print("=" * 60)
        
        is_available = service.is_available()
        print(f"Service available: {'✅ YES' if is_available else '❌ NO'}")
        
        # Test connection
        try:
            connection_result = service.test_connection()
            print(f"Connection test: {'✅ SUCCESS' if connection_result.get('success') else '❌ FAILED'}")
            if connection_result.get('doctypes_available'):
                print("DocTypes availability:")
                for doctype, available in connection_result['doctypes_available'].items():
                    status = "✅ AVAILABLE" if available else "❌ NOT AVAILABLE"
                    print(f"  {doctype}: {status}")
        except Exception as e:
            error_msg = f"Connection test error: {str(e)}"
            results["errors"].append(error_msg)
            print(f"Connection test: ❌ ERROR - {str(e)}")
        
        # Field cache info
        print(f"\nField cache entries: {len(service._field_cache)}")
        
        print("\n" + "=" * 80)
        print("✅ FIELD MAPPING VALIDATION COMPLETED")
        print("=" * 80)
        
        # Summary
        print("\nSUMMARY:")
        print(f"DocTypes tested: {len(results['doctypes_tested'])}")
        print(f"Errors encountered: {len(results['errors'])}")
        
        if results['errors']:
            print("\nErrors:")
            for error in results['errors']:
                print(f"  - {error}")
        
        return results
        
    except Exception as e:
        error_msg = f"Critical error: {str(e)}"
        results["errors"].append(error_msg)
        print(f"❌ Critical Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return results

# Execute the test
if __name__ == "__main__":
    test_results = test_field_mappings()
    print(f"\nTest completed with {len(test_results.get('errors', []))} errors")
