#!/usr/bin/env python3
"""
Phase 2.4.1 Testing: Claim Submission Intent Integration
========================================================

Test script to validate claim_submission intent routing to live data integration.
"""

import sys
import os
sys.path.append('/workspace/development/frappe-bench/apps/assistant_crm')

from assistant_crm.services.intent_router import IntentRouter
from assistant_crm.services.live_data_orchestrator import get_live_data_orchestrator

def test_claim_submission_intent_routing():
    """Test that claim_submission intent routes to live data correctly."""
    print("🔍 PHASE 2.4.1 TESTING: Claim Submission Intent Routing")
    print("=" * 60)
    
    # Initialize components
    router = IntentRouter()
    orchestrator = get_live_data_orchestrator()
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Authenticated User - Claim Submission",
            "message": "How do I submit a claim?",
            "user_context": {
                "user_id": "TEST001",
                "user_role": "beneficiary",
                "permissions": ["view_public_info", "view_own_data", "submit_claims"]
            }
        },
        {
            "name": "Guest User - Claim Submission",
            "message": "How do I submit a claim?", 
            "user_context": {
                "user_id": "guest",
                "user_role": "guest"
            }
        }
    ]
    
    results = []
    
    for scenario in test_scenarios:
        print(f"\n📋 Testing: {scenario['name']}")
        print(f"Message: '{scenario['message']}'")
        
        try:
            # Test intent detection
            intent, confidence = router._detect_intent(scenario['message'])
            print(f"Intent detected: {intent} (confidence: {confidence})")
            
            # Test routing
            routing_result = router.route_request(scenario['message'], scenario['user_context'])
            print(f"Routing source: {routing_result['source']}")
            print(f"Response time: {routing_result['response_time']}s")
            
            # Validate results
            if scenario['user_context']['user_role'] != 'guest':
                expected_source = 'live_data'
                success = routing_result['source'] == expected_source and intent == 'claim_submission'
            else:
                expected_source = 'knowledge_base'
                success = routing_result['source'] == expected_source
            
            result = {
                'scenario': scenario['name'],
                'intent': intent,
                'confidence': confidence,
                'source': routing_result['source'],
                'expected_source': expected_source,
                'response_time': routing_result['response_time'],
                'success': success
            }
            
            results.append(result)
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"Result: {status}")
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            results.append({
                'scenario': scenario['name'],
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print(f"\n📊 PHASE 2.4.1 TEST SUMMARY")
    print("=" * 40)
    
    passed = sum(1 for r in results if r.get('success', False))
    total = len(results)
    
    for result in results:
        status = "✅" if result.get('success', False) else "❌"
        print(f"{status} {result['scenario']}")
        if 'error' in result:
            print(f"   Error: {result['error']}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 PHASE 2.4.1 CLAIM SUBMISSION INTENT: SUCCESS")
        return True
    else:
        print("⚠️  PHASE 2.4.1 CLAIM SUBMISSION INTENT: ISSUES DETECTED")
        return False

def test_regression_existing_intents():
    """Test that existing live data intents still work correctly."""
    print("\n🔍 REGRESSION TESTING: Existing Live Data Intents")
    print("=" * 50)
    
    router = IntentRouter()
    
    # Test existing intents
    existing_tests = [
        {"message": "What is my claim status?", "expected_intent": "claim_status"},
        {"message": "When will I receive my payment?", "expected_intent": "payment_status"},
        {"message": "What are my pension benefits?", "expected_intent": "pension_inquiry"}
    ]
    
    user_context = {
        "user_id": "TEST001",
        "user_role": "beneficiary",
        "permissions": ["view_public_info", "view_own_data", "submit_claims"]
    }
    
    regression_results = []
    
    for test in existing_tests:
        print(f"\n📋 Testing: {test['expected_intent']}")
        print(f"Message: '{test['message']}'")
        
        try:
            intent, confidence = router._detect_intent(test['message'])
            routing_result = router.route_request(test['message'], user_context)
            
            success = (intent == test['expected_intent'] and 
                      routing_result['source'] == 'live_data' and
                      routing_result['response_time'] < 2.0)
            
            regression_results.append({
                'intent': test['expected_intent'],
                'detected_intent': intent,
                'source': routing_result['source'],
                'response_time': routing_result['response_time'],
                'success': success
            })
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"Detected: {intent}, Source: {routing_result['source']}, Time: {routing_result['response_time']}s")
            print(f"Result: {status}")
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            regression_results.append({
                'intent': test['expected_intent'],
                'success': False,
                'error': str(e)
            })
    
    # Regression summary
    print(f"\n📊 REGRESSION TEST SUMMARY")
    print("=" * 30)
    
    passed = sum(1 for r in regression_results if r.get('success', False))
    total = len(regression_results)
    
    for result in regression_results:
        status = "✅" if result.get('success', False) else "❌"
        print(f"{status} {result['intent']}")
    
    print(f"\nRegression Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 REGRESSION TESTING: ALL EXISTING INTENTS WORKING")
        return True
    else:
        print("⚠️  REGRESSION TESTING: ISSUES DETECTED")
        return False

if __name__ == "__main__":
    print("🚀 STARTING PHASE 2.4.1 TESTING")
    print("=" * 50)
    
    # Test claim submission intent
    claim_submission_success = test_claim_submission_intent_routing()
    
    # Test regression
    regression_success = test_regression_existing_intents()
    
    # Overall result
    print(f"\n🎯 OVERALL PHASE 2.4.1 RESULT")
    print("=" * 35)
    
    if claim_submission_success and regression_success:
        print("✅ PHASE 2.4.1 IMPLEMENTATION: COMPLETE SUCCESS")
        print("✅ Zero regression guarantee maintained")
        print("✅ Ready to proceed to Sub-Phase 2.4.2")
    else:
        print("❌ PHASE 2.4.1 IMPLEMENTATION: ISSUES DETECTED")
        print("⚠️  Rollback recommended")
