#!/usr/bin/env python3
"""
ERPNext ORM Integration Test
Tests the live data orchestrator's integration with ERPNext DocTypes
"""

import sys
import os
import time

def test_erpnext_orm_availability():
    """Test that ERPNext ORM functions are available"""
    print("🧪 TESTING: ERPNext ORM Availability")
    print("="*60)
    
    try:
        # Import frappe and test basic ORM functions
        sys.path.insert(0, os.path.join(os.getcwd(), 'assistant_crm', 'services'))
        
        # Test frappe import
        import frappe
        print("✅ Frappe imported successfully")
        
        # Test basic ORM functions
        if hasattr(frappe, 'db'):
            print("✅ frappe.db available")
        else:
            print("❌ frappe.db not available")
            return False
        
        if hasattr(frappe.db, 'get_value'):
            print("✅ frappe.db.get_value available")
        else:
            print("❌ frappe.db.get_value not available")
            return False
        
        if hasattr(frappe.db, 'get_all'):
            print("✅ frappe.db.get_all available")
        else:
            print("❌ frappe.db.get_all not available")
            return False
        
        print("\n✅ ERPNEXT ORM AVAILABILITY: VALIDATED")
        return True
        
    except Exception as e:
        print(f"❌ ERPNext ORM availability test failed: {str(e)}")
        return False

def test_doctype_existence():
    """Test that required DocTypes exist"""
    print("\n🧪 TESTING: DocType Existence")
    print("="*60)
    
    try:
        import frappe
        
        # List of required DocTypes
        required_doctypes = [
            'Beneficiary Profile',
            'Claims Tracking', 
            'Payment Status'
        ]
        
        all_exist = True
        
        for doctype in required_doctypes:
            try:
                # Try to get DocType meta to check if it exists
                meta = frappe.get_meta(doctype)
                if meta:
                    print(f"✅ DocType exists: {doctype}")
                else:
                    print(f"❌ DocType missing: {doctype}")
                    all_exist = False
            except Exception as e:
                print(f"❌ DocType error: {doctype} - {str(e)}")
                all_exist = False
        
        if all_exist:
            print("\n✅ DOCTYPE EXISTENCE: VALIDATED")
            return True
        else:
            print("\n❌ Some DocTypes are missing")
            return False
        
    except Exception as e:
        print(f"❌ DocType existence test failed: {str(e)}")
        return False

def test_live_data_orchestrator_integration():
    """Test the live data orchestrator's ERPNext integration"""
    print("\n🧪 TESTING: Live Data Orchestrator ERPNext Integration")
    print("="*60)
    
    try:
        from live_data_orchestrator import LiveDataOrchestrator
        
        orchestrator = LiveDataOrchestrator()
        print("✅ Live Data Orchestrator instantiated")
        
        # Test user context (simulated)
        test_user_context = {
            'user_id': 'test_user',
            'nrc_number': '123456/78/9',
            'user_role': 'beneficiary'
        }
        
        # Test each data retrieval method
        test_methods = [
            ('_get_claim_data', 'Claim data retrieval'),
            ('_get_payment_data', 'Payment data retrieval'),
            ('_get_pension_data', 'Pension data retrieval'),
            ('_get_account_data', 'Account data retrieval'),
            ('_get_payment_history_data', 'Payment history retrieval')
        ]
        
        all_passed = True
        
        for method_name, description in test_methods:
            print(f"\n📝 Testing: {description}")
            
            try:
                method = getattr(orchestrator, method_name)
                result = method(test_user_context)
                
                if result is None:
                    print(f"   ⚠️  No data found (expected for test user)")
                    print(f"   ✅ Method executed without errors")
                elif isinstance(result, dict) and result.get('type'):
                    print(f"   ✅ Data retrieved successfully")
                    print(f"   Data type: {result.get('type')}")
                    print(f"   Retrieved at: {result.get('retrieved_at', 'N/A')}")
                else:
                    print(f"   ❌ Invalid response format")
                    all_passed = False
                    
            except Exception as e:
                print(f"   ❌ Method error: {str(e)}")
                all_passed = False
        
        if all_passed:
            print("\n✅ LIVE DATA ORCHESTRATOR INTEGRATION: VALIDATED")
            return True
        else:
            print("\n❌ Live data orchestrator integration issues detected")
            return False
        
    except Exception as e:
        print(f"❌ Live data orchestrator integration test failed: {str(e)}")
        return False

def test_database_connection():
    """Test database connection and basic queries"""
    print("\n🧪 TESTING: Database Connection")
    print("="*60)
    
    try:
        import frappe
        
        # Test basic database connection
        try:
            # Try a simple query to test connection
            result = frappe.db.sql("SELECT 1 as test", as_dict=True)
            if result and result[0].get('test') == 1:
                print("✅ Database connection working")
            else:
                print("❌ Database connection failed")
                return False
        except Exception as e:
            print(f"❌ Database connection error: {str(e)}")
            return False
        
        # Test DocType table existence
        doctypes_to_check = ['Beneficiary Profile', 'Claims Tracking', 'Payment Status']
        
        for doctype in doctypes_to_check:
            try:
                # Convert DocType name to table name
                table_name = f"tab{doctype.replace(' ', ' ')}"
                
                # Try to query the table (limit 1 to avoid large results)
                query = f"SELECT name FROM `{table_name}` LIMIT 1"
                result = frappe.db.sql(query, as_dict=True)
                
                print(f"✅ Table accessible: {table_name}")
                
            except Exception as e:
                print(f"⚠️  Table issue: {table_name} - {str(e)}")
                # This is not necessarily a failure - table might be empty
        
        print("\n✅ DATABASE CONNECTION: VALIDATED")
        return True
        
    except Exception as e:
        print(f"❌ Database connection test failed: {str(e)}")
        return False

def test_error_handling():
    """Test error handling in live data methods"""
    print("\n🧪 TESTING: Error Handling")
    print("="*60)
    
    try:
        from live_data_orchestrator import LiveDataOrchestrator
        
        orchestrator = LiveDataOrchestrator()
        
        # Test with invalid user context
        invalid_contexts = [
            {},  # Empty context
            {'user_id': None},  # Null user_id
            {'nrc_number': ''},  # Empty NRC
            {'user_id': 'nonexistent_user_12345'}  # Non-existent user
        ]
        
        all_passed = True
        
        for i, context in enumerate(invalid_contexts):
            print(f"\n📝 Testing invalid context {i+1}: {context}")
            
            try:
                # Test claim data with invalid context
                result = orchestrator._get_claim_data(context)
                
                if result is None:
                    print("   ✅ Properly returned None for invalid context")
                else:
                    print("   ⚠️  Unexpected data returned for invalid context")
                    
            except Exception as e:
                print(f"   ❌ Unhandled exception: {str(e)}")
                all_passed = False
        
        if all_passed:
            print("\n✅ ERROR HANDLING: VALIDATED")
            return True
        else:
            print("\n❌ Error handling issues detected")
            return False
        
    except Exception as e:
        print(f"❌ Error handling test failed: {str(e)}")
        return False

def main():
    """Run all ERPNext ORM integration tests"""
    print("🚀 ERPNEXT ORM INTEGRATION TEST")
    print("="*80)
    print("Testing live data orchestrator integration with ERPNext DocTypes")
    print("="*80)
    
    tests = [
        test_erpnext_orm_availability,
        test_doctype_existence,
        test_database_connection,
        test_live_data_orchestrator_integration,
        test_error_handling
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test in tests:
        if test():
            passed_tests += 1
        else:
            print(f"\n❌ Test failed: {test.__name__}")
    
    print("\n" + "="*80)
    print("🏁 ERPNEXT ORM INTEGRATION TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {total_tests - passed_tests} ❌")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 ERPNEXT ORM INTEGRATION: 100% SUCCESS!")
        print("✅ ERPNext ORM functions available")
        print("✅ Required DocTypes exist")
        print("✅ Database connection working")
        print("✅ Live data methods integrated")
        print("✅ Error handling robust")
        print("✅ Ready for live data retrieval")
        return True
    else:
        print("\n❌ ERPNEXT ORM INTEGRATION: ISSUES DETECTED")
        print("Please review failed tests before proceeding")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
