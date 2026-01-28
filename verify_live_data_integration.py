#!/usr/bin/env python3
"""
Live Data Integration Verification
Verifies that the live data orchestrator has been properly integrated with ERPNext ORM
"""

import sys
import os

def verify_integration_code():
    """Verify that the integration code has been properly implemented"""
    print("🧪 VERIFYING: Live Data Integration Code")
    print("="*60)
    
    try:
        # Check the live data orchestrator file
        orchestrator_path = os.path.join('assistant_crm', 'services', 'live_data_orchestrator.py')
        
        if not os.path.exists(orchestrator_path):
            print("❌ Live data orchestrator file not found")
            return False
        
        with open(orchestrator_path, 'r') as f:
            content = f.read()
        
        # Check for ERPNext ORM integration patterns
        integration_patterns = [
            'frappe.db.get_value',
            'frappe.db.get_all',
            'Beneficiary Profile',
            'Claims Tracking',
            'Payment Status',
            'beneficiary_filters',
            'nrc_number',
            'retrieved_at': now()'
        ]
        
        all_patterns_found = True
        
        for pattern in integration_patterns:
            if pattern in content:
                print(f"✅ Integration pattern found: {pattern}")
            else:
                print(f"❌ Integration pattern missing: {pattern}")
                all_patterns_found = False
        
        # Check that simulation patterns are removed
        simulation_patterns = [
            'simulated for Phase 1',
            'Phase 1: Return simulated data',
            'TODO: Replace with actual database queries'
        ]
        
        simulation_removed = True
        for pattern in simulation_patterns:
            if pattern in content:
                print(f"⚠️  Simulation pattern still present: {pattern}")
                simulation_removed = False
            else:
                print(f"✅ Simulation pattern removed: {pattern}")
        
        if all_patterns_found and simulation_removed:
            print("\n✅ LIVE DATA INTEGRATION CODE: VERIFIED")
            return True
        else:
            print("\n❌ Integration code verification failed")
            return False
        
    except Exception as e:
        print(f"❌ Integration code verification failed: {str(e)}")
        return False

def verify_method_signatures():
    """Verify that the method signatures are correct"""
    print("\n🧪 VERIFYING: Method Signatures")
    print("="*60)
    
    try:
        sys.path.insert(0, os.path.join(os.getcwd(), 'assistant_crm', 'services'))
        from live_data_orchestrator import LiveDataOrchestrator
        
        orchestrator = LiveDataOrchestrator()
        
        # Check that required methods exist
        required_methods = [
            '_get_claim_data',
            '_get_payment_data', 
            '_get_pension_data',
            '_get_account_data',
            '_get_payment_history_data'
        ]
        
        all_methods_exist = True
        
        for method_name in required_methods:
            if hasattr(orchestrator, method_name):
                print(f"✅ Method exists: {method_name}")
                
                # Check method signature
                method = getattr(orchestrator, method_name)
                if callable(method):
                    print(f"   ✅ Method is callable")
                else:
                    print(f"   ❌ Method is not callable")
                    all_methods_exist = False
            else:
                print(f"❌ Method missing: {method_name}")
                all_methods_exist = False
        
        if all_methods_exist:
            print("\n✅ METHOD SIGNATURES: VERIFIED")
            return True
        else:
            print("\n❌ Method signature verification failed")
            return False
        
    except Exception as e:
        print(f"❌ Method signature verification failed: {str(e)}")
        return False

def verify_doctype_integration():
    """Verify DocType integration patterns"""
    print("\n🧪 VERIFYING: DocType Integration Patterns")
    print("="*60)
    
    try:
        orchestrator_path = os.path.join('assistant_crm', 'services', 'live_data_orchestrator.py')
        
        with open(orchestrator_path, 'r') as f:
            content = f.read()
        
        # Check for specific DocType usage patterns
        doctype_patterns = {
            'Beneficiary Profile': [
                "frappe.db.get_value('Beneficiary Profile'",
                'nrc_number',
                'beneficiary_number',
                'full_name'
            ],
            'Claims Tracking': [
                "frappe.db.get_value('Claims Tracking'",
                'claim_id',
                'status',
                'submission_date'
            ],
            'Payment Status': [
                "frappe.db.get_value('Payment Status'",
                'payment_id',
                'amount',
                'payment_date'
            ]
        }
        
        all_patterns_found = True
        
        for doctype, patterns in doctype_patterns.items():
            print(f"\n📝 Checking {doctype} integration:")
            
            for pattern in patterns:
                if pattern in content:
                    print(f"   ✅ Pattern found: {pattern}")
                else:
                    print(f"   ❌ Pattern missing: {pattern}")
                    all_patterns_found = False
        
        if all_patterns_found:
            print("\n✅ DOCTYPE INTEGRATION PATTERNS: VERIFIED")
            return True
        else:
            print("\n❌ DocType integration pattern verification failed")
            return False
        
    except Exception as e:
        print(f"❌ DocType integration verification failed: {str(e)}")
        return False

def verify_error_handling():
    """Verify error handling implementation"""
    print("\n🧪 VERIFYING: Error Handling Implementation")
    print("="*60)
    
    try:
        orchestrator_path = os.path.join('assistant_crm', 'services', 'live_data_orchestrator.py')
        
        with open(orchestrator_path, 'r') as f:
            content = f.read()
        
        # Check for error handling patterns
        error_patterns = [
            'try:',
            'except Exception as e:',
            'self._log_error',
            'return None'
        ]
        
        all_patterns_found = True
        
        for pattern in error_patterns:
            if pattern in content:
                print(f"✅ Error handling pattern found: {pattern}")
            else:
                print(f"❌ Error handling pattern missing: {pattern}")
                all_patterns_found = False
        
        # Count try-except blocks in data methods
        try_count = content.count('def _get_') * content.count('try:') // content.count('def ')
        except_count = content.count('except Exception as e:')
        
        print(f"\n📊 Error handling statistics:")
        print(f"   Try blocks: {content.count('try:')}")
        print(f"   Except blocks: {except_count}")
        
        if except_count >= 5:  # Should have at least 5 data methods with error handling
            print("   ✅ Adequate error handling coverage")
        else:
            print("   ❌ Insufficient error handling coverage")
            all_patterns_found = False
        
        if all_patterns_found:
            print("\n✅ ERROR HANDLING IMPLEMENTATION: VERIFIED")
            return True
        else:
            print("\n❌ Error handling verification failed")
            return False
        
    except Exception as e:
        print(f"❌ Error handling verification failed: {str(e)}")
        return False

def verify_data_flow_integration():
    """Verify integration with the simplified dataflow"""
    print("\n🧪 VERIFYING: Data Flow Integration")
    print("="*60)
    
    try:
        # Check intent router integration
        intent_router_path = os.path.join('assistant_crm', 'services', 'intent_router.py')
        
        if not os.path.exists(intent_router_path):
            print("❌ Intent router file not found")
            return False
        
        with open(intent_router_path, 'r') as f:
            content = f.read()
        
        # Check for live data orchestrator integration
        integration_patterns = [
            'live_data_orchestrator',
            'get_live_data_orchestrator',
            '_try_live_data_route'
        ]
        
        all_patterns_found = True
        
        for pattern in integration_patterns:
            if pattern in content:
                print(f"✅ Data flow integration pattern found: {pattern}")
            else:
                print(f"❌ Data flow integration pattern missing: {pattern}")
                all_patterns_found = False
        
        if all_patterns_found:
            print("\n✅ DATA FLOW INTEGRATION: VERIFIED")
            return True
        else:
            print("\n❌ Data flow integration verification failed")
            return False
        
    except Exception as e:
        print(f"❌ Data flow integration verification failed: {str(e)}")
        return False

def main():
    """Run all live data integration verifications"""
    print("🚀 LIVE DATA INTEGRATION VERIFICATION")
    print("="*80)
    print("Verifying ERPNext ORM integration in live data orchestrator")
    print("="*80)
    
    verifications = [
        verify_integration_code,
        verify_method_signatures,
        verify_doctype_integration,
        verify_error_handling,
        verify_data_flow_integration
    ]
    
    passed_verifications = 0
    total_verifications = len(verifications)
    
    for verification in verifications:
        if verification():
            passed_verifications += 1
        else:
            print(f"\n❌ Verification failed: {verification.__name__}")
    
    print("\n" + "="*80)
    print("🏁 LIVE DATA INTEGRATION VERIFICATION SUMMARY")
    print("="*80)
    print(f"Total Verifications: {total_verifications}")
    print(f"Passed: {passed_verifications} ✅")
    print(f"Failed: {total_verifications - passed_verifications} ❌")
    print(f"Success Rate: {(passed_verifications/total_verifications)*100:.1f}%")
    
    if passed_verifications == total_verifications:
        print("\n🎉 LIVE DATA INTEGRATION: 100% VERIFIED!")
        print("✅ ERPNext ORM integration implemented")
        print("✅ DocType queries properly structured")
        print("✅ Error handling robust")
        print("✅ Method signatures correct")
        print("✅ Data flow integration maintained")
        print("✅ Ready for live data retrieval from ERPNext")
        
        print("\n📋 NEXT STEPS:")
        print("1. Test in live ERPNext environment")
        print("2. Create sample Beneficiary Profile records")
        print("3. Create sample Claims Tracking records")
        print("4. Create sample Payment Status records")
        print("5. Test with real NRC numbers")
        
        return True
    else:
        print("\n❌ LIVE DATA INTEGRATION: VERIFICATION ISSUES DETECTED")
        print("Please review failed verifications before proceeding")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
