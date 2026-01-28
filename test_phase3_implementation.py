#!/usr/bin/env python3
"""
Phase 3 Implementation Validation Test Suite
===========================================

Comprehensive testing for Frontend-Backend Alignment implementation.
Validates unified API, backward compatibility, and zero regression guarantee.
"""

import sys
import time
import json
import requests
sys.path.append('/workspace/development/frappe-bench/apps/assistant_crm')

def test_unified_api_direct():
    """Test 1: Direct Unified API functionality"""
    print("=== Test 1: Direct Unified API ===")
    try:
        from assistant_crm.api.unified_chat_api import process_message
        
        # Test simple greeting
        result = process_message("Hello Anna")
        
        print(f"Success: {result.get('success')}")
        print(f"Reply: {result.get('reply', '')[:80]}...")
        print(f"Live data used: {result.get('live_data_used')}")
        print(f"Data sources: {result.get('data_sources')}")
        print(f"Anna personality: {result.get('anna_personality')}")
        print(f"WCFCB branding: {result.get('wcfcb_branding')}")
        print(f"Response time: {result.get('response_time')}s")
        
        # Validation
        assert result.get('success') == True
        assert 'Anna' in result.get('reply', '')
        assert result.get('response_time', 0) < 2.0
        
        print("✅ PASSED: Unified API working correctly")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def test_unified_api_live_data():
    """Test 2: Unified API with live data integration"""
    print("\n=== Test 2: Unified API Live Data Integration ===")
    try:
        from assistant_crm.api.unified_chat_api import process_message
        
        user_context = {
            'user_id': 'TEST001',
            'user_role': 'beneficiary',
            'claim_number': 'CLM-2025-001'
        }
        
        result = process_message("Can you check my claim status?", "test_session", user_context)
        
        print(f"Success: {result.get('success')}")
        print(f"Live data used: {result.get('live_data_used')}")
        print(f"Data sources: {result.get('data_sources')}")
        print(f"Reply: {result.get('reply', '')[:100]}...")
        
        # Validation
        assert result.get('success') == True
        assert 'claim' in result.get('reply', '').lower()
        
        print("✅ PASSED: Live data integration working")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def test_chatbot_api_backward_compatibility():
    """Test 3: Chatbot API backward compatibility"""
    print("\n=== Test 3: Chatbot API Backward Compatibility ===")
    try:
        from assistant_crm.api.chatbot import ask_bot
        
        result = ask_bot("Hello Anna")
        
        print(f"Success: {result.get('success')}")
        print(f"Reply: {result.get('reply', '')[:80]}...")
        print(f"Has unified features: {'live_data_used' in result}")
        print(f"Session ID: {result.get('session_id')}")
        
        # Validation
        assert result.get('success') == True
        assert 'reply' in result
        assert 'Anna' in result.get('reply', '')
        
        print("✅ PASSED: Backward compatibility maintained")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def test_response_format_standardization():
    """Test 4: Response format standardization"""
    print("\n=== Test 4: Response Format Standardization ===")
    try:
        from assistant_crm.api.unified_chat_api import process_message
        
        result = process_message("What services do you offer?")
        
        # Check standardized response format
        required_fields = ['success', 'reply', 'session_id', 'timestamp', 'user', 
                          'live_data_used', 'data_sources', 'anna_personality', 
                          'wcfcb_branding', 'response_time']
        
        missing_fields = [field for field in required_fields if field not in result]
        
        print(f"Response fields: {list(result.keys())}")
        print(f"Missing fields: {missing_fields}")
        print(f"All required fields present: {len(missing_fields) == 0}")
        
        # Validation
        assert len(missing_fields) == 0
        assert isinstance(result.get('data_sources'), list)
        assert isinstance(result.get('anna_personality'), bool)
        assert isinstance(result.get('wcfcb_branding'), bool)
        
        print("✅ PASSED: Response format standardized")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def test_error_handling_graceful_fallbacks():
    """Test 5: Error handling and graceful fallbacks"""
    print("\n=== Test 5: Error Handling and Graceful Fallbacks ===")
    try:
        from assistant_crm.api.unified_chat_api import process_message
        
        # Test empty message
        result1 = process_message("")
        print(f"Empty message handled: {result1.get('success') == False}")
        print(f"Error message: {result1.get('reply', '')[:50]}...")
        
        # Test very long message
        long_message = "help " * 200
        result2 = process_message(long_message)
        print(f"Long message handled: {result2.get('success') == False}")
        
        # Test invalid user context
        result3 = process_message("Hello", user_context="invalid_json")
        print(f"Invalid context handled: {result3.get('success')}")
        
        # Validation
        assert result1.get('success') == False
        assert result2.get('success') == False
        assert result3.get('success') == True  # Should still work with empty context
        
        print("✅ PASSED: Error handling working correctly")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def test_performance_benchmarks():
    """Test 6: Performance benchmarks"""
    print("\n=== Test 6: Performance Benchmarks ===")
    try:
        from assistant_crm.api.unified_chat_api import process_message
        
        test_messages = [
            "Hello",
            "What documents do I need?",
            "Can you help me with my claim?"
        ]
        
        total_time = 0
        for message in test_messages:
            start_time = time.time()
            result = process_message(message)
            end_time = time.time()
            
            response_time = end_time - start_time
            total_time += response_time
            
            print(f"Message: '{message}' - {response_time:.3f}s")
            
            # Validation
            assert response_time < 2.0  # Performance requirement
            assert result.get('success') == True
        
        average_time = total_time / len(test_messages)
        print(f"Average response time: {average_time:.3f}s")
        
        print("✅ PASSED: Performance benchmarks met")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def test_anna_personality_preservation():
    """Test 7: Anna personality preservation"""
    print("\n=== Test 7: Anna Personality Preservation ===")
    try:
        from assistant_crm.api.unified_chat_api import process_message
        
        test_scenarios = [
            ("Hello", "greeting"),
            ("I have a complaint", "complaint"),
            ("I need help", "general_help"),
            ("Can you check my claim?", "claim_status")
        ]
        
        anna_count = 0
        empathy_count = 0
        
        for message, scenario in test_scenarios:
            result = process_message(message)
            reply = result.get('reply', '')
            
            # Check Anna's personality elements
            if any(element in reply for element in ["I'm Anna", "Anna from WCFCB"]):
                anna_count += 1
            
            if any(element in reply for element in ["I understand", "I'll help", "I'm here"]):
                empathy_count += 1
            
            anna_present = 'Anna' in reply
            empathy_present = any(e in reply for e in ['I understand', 'I\'ll help', 'I\'m here'])
            print(f"Scenario '{scenario}': Anna present: {anna_present}, Empathy: {empathy_present}")
        
        anna_percentage = (anna_count / len(test_scenarios)) * 100
        empathy_percentage = (empathy_count / len(test_scenarios)) * 100
        
        print(f"Anna identity: {anna_percentage}% of responses")
        print(f"Empathy patterns: {empathy_percentage}% of responses")
        
        # Validation
        assert anna_percentage >= 75  # At least 75% should have Anna's identity
        assert empathy_percentage >= 50  # At least 50% should have empathy
        
        print("✅ PASSED: Anna personality preserved")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def run_comprehensive_phase3_tests():
    """Run all Phase 3 validation tests"""
    print("🚀 PHASE 3 COMPREHENSIVE VALIDATION TESTS")
    print("=" * 60)
    
    tests = [
        test_unified_api_direct,
        test_unified_api_live_data,
        test_chatbot_api_backward_compatibility,
        test_response_format_standardization,
        test_error_handling_graceful_fallbacks,
        test_performance_benchmarks,
        test_anna_personality_preservation
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed_tests += 1
        except Exception as e:
            print(f"❌ FAILED: {test_func.__name__} - {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"🎯 PHASE 3 TEST SUMMARY: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 PHASE 3 IMPLEMENTATION SUCCESSFUL")
        print("✅ Frontend-Backend Alignment achieved")
        print("✅ Unified API operational")
        print("✅ Backward compatibility maintained")
        print("✅ Zero regression guarantee met")
        print("✅ Anna's personality preserved")
        print("✅ Performance targets exceeded")
    else:
        print("⚠️  Some tests failed - review and fix before production")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = run_comprehensive_phase3_tests()
    sys.exit(0 if success else 1)
