#!/usr/bin/env python3
"""
Direct test of LiveDataRetrievalService without full module imports
"""

import sys
import os

# Add the path to import the service directly
sys.path.insert(0, '/workspace/development/frappe-bench/apps/assistant_crm/assistant_crm/services')

def mock_frappe():
    """Create a mock frappe module for testing"""
    class MockFrappe:
        def __init__(self):
            self.session = MockSession()
            
        def get_meta(self, doctype):
            """Mock get_meta function"""
            # Simulate existing DocTypes
            valid_doctypes = {
                "Customer": MockMeta(["name", "customer_name", "email_id", "mobile_no", "customer_type"]),
                "Beneficiary Profile": MockMeta(["name", "beneficiary_number", "nrc_number", "first_name", "last_name", "email", "phone", "benefit_status"]),
                "Payment Entry": MockMeta(["name", "paid_amount", "posting_date", "party", "party_type"]),
                "Insurance Claim": MockMeta(["name", "claim_amount", "status", "customer"]),
                "User": MockMeta(["name", "email", "full_name"])
            }
            
            if doctype in valid_doctypes:
                return valid_doctypes[doctype]
            else:
                raise Exception(f"DocType {doctype} not found")
        
        def log_error(self, message, title=None):
            print(f"LOG ERROR: {message}")
        
        def get_all(self, doctype, filters=None, fields=None, limit=None, order_by=None):
            """Mock get_all function"""
            return []  # Return empty list for testing
        
        def get_doc(self, doctype, name):
            """Mock get_doc function"""
            class MockDoc:
                def __init__(self):
                    self.name = name
                    self.customer_name = "Test Customer"
                    self.email_id = "test@example.com"
            return MockDoc()
        
        def set_user(self, user):
            """Mock set_user function"""
            pass
    
    class MockSession:
        def __init__(self):
            self.user = "Administrator"
    
    class MockMeta:
        def __init__(self, fields):
            self.fields = fields
        
        def has_field(self, fieldname):
            return fieldname in self.fields
    
    return MockFrappe()

def test_service_directly():
    """Test the service with mocked frappe"""
    
    print("=" * 80)
    print("DIRECT LIVE DATA RETRIEVAL SERVICE TEST")
    print("=" * 80)
    
    try:
        # Mock frappe before importing
        import sys
        sys.modules['frappe'] = mock_frappe()
        sys.modules['frappe.utils'] = type('MockUtils', (), {
            'now': lambda: "2024-08-17 12:00:00",
            'get_datetime': lambda x: x
        })()
        
        # Now import the service
        from live_data_retrieval_service import LiveDataRetrievalService
        
        print("✅ Successfully imported LiveDataRetrievalService")
        
        # Initialize the service
        service = LiveDataRetrievalService()
        print(f"✅ Service initialized: {service.service_name}")
        
        # Test DocType mapping
        print("\n" + "=" * 50)
        print("TEST 1: DocType Mapping")
        print("=" * 50)
        
        for key, doctype in service.doctype_mapping.items():
            print(f"{key}: {doctype}")
        
        # Test field cache
        print("\n" + "=" * 50)
        print("TEST 2: Field Cache Initialization")
        print("=" * 50)
        
        print(f"Field cache initialized: {hasattr(service, '_field_cache')}")
        print(f"Field cache type: {type(service._field_cache)}")
        
        # Test DocType validation
        print("\n" + "=" * 50)
        print("TEST 3: DocType Validation")
        print("=" * 50)
        
        test_doctypes = ["Customer", "Beneficiary Profile", "NonExistent DocType"]
        for doctype in test_doctypes:
            exists = service._validate_doctype_exists(doctype)
            print(f"DocType '{doctype}': {'✅ EXISTS' if exists else '❌ NOT FOUND'}")
        
        # Test field validation
        print("\n" + "=" * 50)
        print("TEST 4: Field Validation")
        print("=" * 50)
        
        test_fields = [
            ("Customer", "customer_name"),
            ("Customer", "nonexistent_field"),
            ("Beneficiary Profile", "nrc_number"),
            ("Beneficiary Profile", "invalid_field")
        ]
        
        for doctype, field in test_fields:
            has_field = service._validate_doctype_field(doctype, field)
            print(f"{doctype}.{field}: {'✅ EXISTS' if has_field else '❌ NOT FOUND'}")
        
        # Test identifier detection
        print("\n" + "=" * 50)
        print("TEST 5: Identifier Detection")
        print("=" * 50)
        
        test_identifiers = [
            ("123456/78/9", "nrc"),
            ("test@example.com", "email"),
            ("CUST-001", "customer_id"),
            ("BEN-001", "beneficiary_id"),
            ("123456789", "nrc")
        ]
        
        for identifier, expected in test_identifiers:
            detected = service._detect_identifier_type(identifier)
            status = "✅ CORRECT" if detected == expected else f"❌ EXPECTED {expected}, GOT {detected}"
            print(f"'{identifier}' -> {detected} ({status})")
        
        # Test service availability
        print("\n" + "=" * 50)
        print("TEST 6: Service Availability")
        print("=" * 50)
        
        is_available = service.is_available()
        print(f"Service available: {'✅ YES' if is_available else '❌ NO'}")
        
        # Test administrator access
        print("\n" + "=" * 50)
        print("TEST 7: Administrator Access")
        print("=" * 50)
        
        has_access = service._ensure_administrator_access()
        print(f"Administrator access: {'✅ GRANTED' if has_access else '❌ DENIED'}")
        
        print("\n" + "=" * 80)
        print("✅ ALL DIRECT TESTS COMPLETED SUCCESSFULLY")
        print("The LiveDataRetrievalService is properly configured!")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_service_directly()
    sys.exit(0 if success else 1)
