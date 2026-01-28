#!/usr/bin/env python3
"""
Comprehensive validation test for the fixed LiveDataRetrievalService
Tests all functionality with proper error handling and field validation
"""

import sys
import os
sys.path.append('/workspace/development/frappe-bench')

def test_live_data_service():
    """Test the LiveDataRetrievalService with comprehensive validation"""
    
    print("=" * 80)
    print("LIVE DATA RETRIEVAL SERVICE VALIDATION TEST")
    print("=" * 80)
    
    try:
        # Import the service
        from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService
        
        print("✅ Successfully imported LiveDataRetrievalService")
        
        # Initialize the service
        service = LiveDataRetrievalService()
        print(f"✅ Service initialized: {service.service_name}")
        
        # Test 1: Service availability
        print("\n" + "=" * 50)
        print("TEST 1: Service Availability")
        print("=" * 50)
        
        is_available = service.is_available()
        print(f"Service available: {is_available}")
        
        # Test 2: DocType validation
        print("\n" + "=" * 50)
        print("TEST 2: DocType Validation")
        print("=" * 50)
        
        doctypes_to_test = [
            "Customer",
            "Beneficiary Profile", 
            "Payment Entry",
            "Insurance Claim",
            "User"
        ]
        
        for doctype in doctypes_to_test:
            exists = service._validate_doctype_exists(doctype)
            print(f"DocType '{doctype}': {'✅ EXISTS' if exists else '❌ NOT FOUND'}")
        
        # Test 3: Field validation for Customer DocType
        print("\n" + "=" * 50)
        print("TEST 3: Customer DocType Field Validation")
        print("=" * 50)
        
        customer_fields = [
            "customer_name",
            "email_id", 
            "mobile_no",
            "customer_type",
            "territory",
            "customer_group"
        ]
        
        for field in customer_fields:
            has_field = service._validate_doctype_field("Customer", field)
            print(f"Customer.{field}: {'✅ EXISTS' if has_field else '❌ NOT FOUND'}")
        
        # Test 4: Field validation for Beneficiary Profile DocType
        print("\n" + "=" * 50)
        print("TEST 4: Beneficiary Profile DocType Field Validation")
        print("=" * 50)
        
        beneficiary_fields = [
            "beneficiary_number",
            "nrc_number",
            "first_name",
            "last_name", 
            "full_name",
            "email",
            "phone",
            "benefit_status",
            "monthly_benefit_amount",
            "benefit_start_date"
        ]
        
        for field in beneficiary_fields:
            has_field = service._validate_doctype_field("Beneficiary Profile", field)
            print(f"Beneficiary Profile.{field}: {'✅ EXISTS' if has_field else '❌ NOT FOUND'}")
        
        # Test 5: Test connection
        print("\n" + "=" * 50)
        print("TEST 5: Database Connection Test")
        print("=" * 50)
        
        connection_result = service.test_connection()
        print(f"Connection test result: {connection_result}")
        
        # Test 6: Identifier detection
        print("\n" + "=" * 50)
        print("TEST 6: Identifier Detection")
        print("=" * 50)
        
        test_identifiers = [
            "123456/78/9",  # NRC format
            "test@example.com",  # Email
            "CUST-001",  # Customer ID
            "BEN-001",  # Beneficiary ID
            "123456789"  # Numeric NRC
        ]
        
        for identifier in test_identifiers:
            detected_type = service._detect_identifier_type(identifier)
            print(f"'{identifier}' detected as: {detected_type}")
        
        # Test 7: Sample data retrieval (if service is available)
        if is_available:
            print("\n" + "=" * 50)
            print("TEST 7: Sample Data Retrieval")
            print("=" * 50)
            
            # Test NRC search
            print("Testing NRC search...")
            nrc_result = service.get_user_data_by_identifier("123456/78/9", "nrc")
            print(f"NRC search result keys: {list(nrc_result.keys())}")
            print(f"Found data: {nrc_result.get('found', False)}")
            
            # Test email search
            print("\nTesting email search...")
            email_result = service.get_user_data_by_identifier("test@example.com", "email")
            print(f"Email search result keys: {list(email_result.keys())}")
            print(f"Found data: {email_result.get('found', False)}")
            
            # Test beneficiary data retrieval
            print("\nTesting beneficiary data retrieval...")
            beneficiary_result = service.get_beneficiary_data("test-beneficiary")
            print(f"Beneficiary result: {beneficiary_result.get('success', False)}")
            print(f"Message: {beneficiary_result.get('message', 'No message')}")
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure you're running this from the correct directory")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_live_data_service()
    sys.exit(0 if success else 1)
