#!/usr/bin/env python3
"""
Test LiveDataRetrievalService with real ERPNext data to verify field mappings
"""

import sys
import os
import json

# Set up the environment for Frappe
sys.path.insert(0, '/workspace/development/frappe-bench')
os.chdir('/workspace/development/frappe-bench')

def test_real_erpnext_data():
    """Test the LiveDataRetrievalService with real ERPNext data"""
    
    print("=" * 80)
    print("REAL ERPNEXT DATA FIELD MAPPING VALIDATION TEST")
    print("=" * 80)
    
    try:
        # Initialize Frappe
        import frappe
        frappe.init(site='dev')
        frappe.connect()
        
        print("✅ Connected to ERPNext database")
        
        # Import the service
        from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService
        service = LiveDataRetrievalService()
        
        print(f"✅ Service initialized: {service.service_name}")
        
        # Test 1: Real DocType validation
        print("\n" + "=" * 60)
        print("TEST 1: Real DocType Validation")
        print("=" * 60)
        
        doctypes_to_test = [
            "Customer",
            "Beneficiary Profile", 
            "Payment Entry",
            "Insurance Claim",
            "User",
            "Account"
        ]
        
        for doctype in doctypes_to_test:
            try:
                exists = service._validate_doctype_exists(doctype)
                if exists:
                    # Get field list for existing DocTypes
                    meta = frappe.get_meta(doctype)
                    field_count = len([f for f in meta.fields if f.fieldtype not in ['Section Break', 'Column Break', 'Tab Break']])
                    print(f"✅ {doctype}: EXISTS ({field_count} fields)")
                else:
                    print(f"❌ {doctype}: NOT FOUND")
            except Exception as e:
                print(f"❌ {doctype}: ERROR - {str(e)}")
        
        # Test 2: Real Customer DocType fields
        print("\n" + "=" * 60)
        print("TEST 2: Customer DocType Field Validation")
        print("=" * 60)
        
        if service._validate_doctype_exists("Customer"):
            customer_fields = [
                "customer_name", "email_id", "mobile_no", "customer_type",
                "territory", "customer_group", "phone", "website"
            ]
            
            for field in customer_fields:
                has_field = service._validate_doctype_field("Customer", field)
                print(f"Customer.{field}: {'✅ EXISTS' if has_field else '❌ NOT FOUND'}")
        
        # Test 3: Real Beneficiary Profile fields
        print("\n" + "=" * 60)
        print("TEST 3: Beneficiary Profile Field Validation")
        print("=" * 60)
        
        if service._validate_doctype_exists("Beneficiary Profile"):
            beneficiary_fields = [
                "beneficiary_number", "nrc_number", "first_name", "last_name", 
                "full_name", "email", "phone", "mobile", "benefit_status", 
                "monthly_benefit_amount", "benefit_start_date", "date_of_birth"
            ]
            
            for field in beneficiary_fields:
                has_field = service._validate_doctype_field("Beneficiary Profile", field)
                print(f"Beneficiary Profile.{field}: {'✅ EXISTS' if has_field else '❌ NOT FOUND'}")
        
        # Test 4: Real data counts
        print("\n" + "=" * 60)
        print("TEST 4: Real Data Counts")
        print("=" * 60)
        
        try:
            customer_count = frappe.db.count("Customer")
            print(f"Customer records: {customer_count}")
        except:
            print("Customer records: ERROR")
        
        try:
            beneficiary_count = frappe.db.count("Beneficiary Profile")
            print(f"Beneficiary Profile records: {beneficiary_count}")
        except:
            print("Beneficiary Profile records: ERROR")
        
        try:
            payment_count = frappe.db.count("Payment Entry")
            print(f"Payment Entry records: {payment_count}")
        except:
            print("Payment Entry records: ERROR")
        
        # Test 5: Sample data retrieval
        print("\n" + "=" * 60)
        print("TEST 5: Sample Data Retrieval")
        print("=" * 60)
        
        # Test service availability
        is_available = service.is_available()
        print(f"Service available: {'✅ YES' if is_available else '❌ NO'}")
        
        if is_available:
            # Test with sample identifiers
            test_identifiers = [
                ("123456/78/9", "nrc"),
                ("test@example.com", "email"),
                ("sample-customer", "customer_id")
            ]
            
            for identifier, id_type in test_identifiers:
                print(f"\nTesting {id_type}: {identifier}")
                try:
                    result = service.get_user_data_by_identifier(identifier, id_type)
                    print(f"  Found: {result.get('found', False)}")
                    print(f"  Keys: {list(result.keys())}")
                    if result.get('error'):
                        print(f"  Error: {result['error']}")
                except Exception as e:
                    print(f"  Exception: {str(e)}")
        
        # Test 6: Connection test
        print("\n" + "=" * 60)
        print("TEST 6: Service Connection Test")
        print("=" * 60)
        
        try:
            connection_result = service.test_connection()
            print(f"Connection test success: {connection_result.get('success', False)}")
            if connection_result.get('doctypes_available'):
                print("DocTypes availability:")
                for doctype, available in connection_result['doctypes_available'].items():
                    status = "✅ AVAILABLE" if available else "❌ NOT AVAILABLE"
                    print(f"  {doctype}: {status}")
        except Exception as e:
            print(f"Connection test error: {str(e)}")
        
        # Test 7: Field cache performance
        print("\n" + "=" * 60)
        print("TEST 7: Field Cache Performance")
        print("=" * 60)
        
        print(f"Field cache entries: {len(service._field_cache)}")
        if service._field_cache:
            print("Sample cache entries:")
            for i, (key, value) in enumerate(list(service._field_cache.items())[:5]):
                print(f"  {key}: {value}")
                if i >= 4:
                    break
        
        print("\n" + "=" * 80)
        print("✅ REAL ERPNEXT DATA VALIDATION COMPLETED")
        print("=" * 80)
        
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure Frappe is properly installed and configured")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            frappe.destroy()
        except:
            pass

if __name__ == "__main__":
    success = test_real_erpnext_data()
    sys.exit(0 if success else 1)
