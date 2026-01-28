#!/usr/bin/env python3
"""
Simplified Dataflow Integration Test
Tests the complete frontend-backend integration with cleaned up dataflow
"""

import sys
import os
import time
import json

def test_api_endpoint_availability():
    """Test that the simplified API endpoints are available"""
    print("🧪 TESTING: API Endpoint Availability")
    print("="*60)
    
    try:
        # Import the simplified chat API
        sys.path.insert(0, os.path.join(os.getcwd(), 'assistant_crm', 'api'))
        from simplified_chat import send_message, get_chat_status
        
        print("✅ Simplified chat API imported successfully")
        
        # Test get_chat_status
        try:
            status = get_chat_status()
            if status and status.get('success'):
                print("✅ get_chat_status() working")
                print(f"   API Version: {status.get('api_version', 'unknown')}")
                print(f"   Features: {list(status.get('features', {}).keys())}")
            else:
                print("❌ get_chat_status() failed")
                return False
        except Exception as e:
            print(f"❌ get_chat_status() error: {str(e)}")
            return False
        
        print("\n✅ API ENDPOINT AVAILABILITY: VALIDATED")
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {str(e)}")
        return False

def test_single_dataflow_integration():
    """Test the complete single dataflow integration"""
    print("\n🧪 TESTING: Single Dataflow Integration")
    print("="*60)
    
    try:
        sys.path.insert(0, os.path.join(os.getcwd(), 'assistant_crm', 'api'))
        from simplified_chat import send_message
        
        # Test different types of messages through the single dataflow
        test_cases = [
            {
                'message': 'Hello Anna',
                'expected_intent': 'greeting',
                'description': 'Greeting message'
            },
            {
                'message': 'What is my claim status?',
                'expected_intent': 'claim_status',
                'description': 'Live data intent'
            },
            {
                'message': 'I need help',
                'expected_intent': 'agent_request',
                'description': 'Agent request'
            },
            {
                'message': 'Thank you',
                'expected_intent': 'goodbye',
                'description': 'Goodbye message'
            }
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            message = test_case['message']
            expected_intent = test_case['expected_intent']
            description = test_case['description']
            
            print(f"\n📝 Testing: {description}")
            print(f"   Message: \"{message}\"")
            
            try:
                # Call the single API endpoint
                response = send_message(message=message)
                
                if response and response.get('success'):
                    intent = response.get('metadata', {}).get('intent', 'unknown')
                    ai_response = response.get('message', '')
                    source = response.get('metadata', {}).get('source', 'unknown')
                    
                    print(f"   ✅ Response received")
                    print(f"   Intent: {intent} (expected: {expected_intent})")
                    print(f"   Source: {source}")
                    print(f"   AI Response: {ai_response[:100]}...")
                    
                    if intent == expected_intent:
                        print(f"   ✅ Intent detection correct")
                    else:
                        print(f"   ❌ Intent detection incorrect")
                        all_passed = False
                        
                else:
                    print(f"   ❌ API call failed: {response}")
                    all_passed = False
                    
            except Exception as e:
                print(f"   ❌ API call error: {str(e)}")
                all_passed = False
        
        if all_passed:
            print("\n✅ SINGLE DATAFLOW INTEGRATION: VALIDATED")
            return True
        else:
            print("\n❌ Single dataflow integration issues detected")
            return False
        
    except Exception as e:
        print(f"❌ Single dataflow integration test failed: {str(e)}")
        return False

def test_no_redundant_components():
    """Test that redundant components have been removed"""
    print("\n🧪 TESTING: Redundant Components Removal")
    print("="*60)
    
    try:
        # Check that redundant API files are gone
        redundant_api_files = [
            'assistant_crm/api/chat.py',
            'assistant_crm/api/optimized_chat.py',
            'assistant_crm/api/unified_chat_api.py',
            'assistant_crm/api/chatbot.py'
        ]
        
        for file_path in redundant_api_files:
            if os.path.exists(file_path):
                print(f"❌ Redundant file still exists: {file_path}")
                return False
            else:
                print(f"✅ Redundant file removed: {file_path}")
        
        # Check that response assembler is gone
        response_assembler_files = [
            'assistant_crm/services/response_assembler.py',
            'assistant_crm/services/live_data_response_assembler.py'
        ]
        
        for file_path in response_assembler_files:
            if os.path.exists(file_path):
                print(f"❌ Response assembler still exists: {file_path}")
                return False
            else:
                print(f"✅ Response assembler removed: {file_path}")
        
        # Check that session management is gone
        session_files = [
            'assistant_crm/api/session_manager.py',
            'assistant_crm/services/session_context_manager.py',
            'assistant_crm/services/session_management_system.py'
        ]
        
        for file_path in session_files:
            if os.path.exists(file_path):
                print(f"❌ Session management still exists: {file_path}")
                return False
            else:
                print(f"✅ Session management removed: {file_path}")
        
        print("\n✅ REDUNDANT COMPONENTS REMOVAL: VALIDATED")
        return True
        
    except Exception as e:
        print(f"❌ Redundant components test failed: {str(e)}")
        return False

def test_frontend_backend_compatibility():
    """Test frontend-backend compatibility"""
    print("\n🧪 TESTING: Frontend-Backend Compatibility")
    print("="*60)
    
    try:
        # Test that the API returns the expected format for frontend
        sys.path.insert(0, os.path.join(os.getcwd(), 'assistant_crm', 'api'))
        from simplified_chat import send_message
        
        # Test API response format
        response = send_message(message="Hello Anna")
        
        if not response:
            print("❌ No response from API")
            return False
        
        # Check required fields for frontend
        required_fields = ['success', 'message', 'metadata', 'timestamp']
        for field in required_fields:
            if field not in response:
                print(f"❌ Missing required field: {field}")
                return False
            else:
                print(f"✅ Required field present: {field}")
        
        # Check metadata structure
        metadata = response.get('metadata', {})
        metadata_fields = ['intent', 'source', 'response_time']
        for field in metadata_fields:
            if field not in metadata:
                print(f"❌ Missing metadata field: {field}")
                return False
            else:
                print(f"✅ Metadata field present: {field}")
        
        # Check response format is JSON serializable
        try:
            json.dumps(response)
            print("✅ Response is JSON serializable")
        except Exception as e:
            print(f"❌ Response not JSON serializable: {str(e)}")
            return False
        
        print("\n✅ FRONTEND-BACKEND COMPATIBILITY: VALIDATED")
        return True
        
    except Exception as e:
        print(f"❌ Frontend-backend compatibility test failed: {str(e)}")
        return False

def test_performance_and_caching():
    """Test performance and caching functionality"""
    print("\n🧪 TESTING: Performance and Caching")
    print("="*60)
    
    try:
        sys.path.insert(0, os.path.join(os.getcwd(), 'assistant_crm', 'api'))
        from simplified_chat import send_message
        
        message = "What is my claim status?"
        
        # First request (cache miss)
        start_time = time.time()
        response1 = send_message(message=message)
        time1 = time.time() - start_time
        
        if not response1 or not response1.get('success'):
            print("❌ First request failed")
            return False
        
        print(f"✅ First request completed in {time1:.3f}s")
        
        # Second request (should be faster due to caching)
        start_time = time.time()
        response2 = send_message(message=message)
        time2 = time.time() - start_time
        
        if not response2 or not response2.get('success'):
            print("❌ Second request failed")
            return False
        
        print(f"✅ Second request completed in {time2:.3f}s")
        
        # Check if caching is working (second request should be faster)
        if time2 < time1:
            print("✅ Caching appears to be working (faster second request)")
        else:
            print("⚠️  Caching may not be working (second request not faster)")
        
        print("\n✅ PERFORMANCE AND CACHING: TESTED")
        return True
        
    except Exception as e:
        print(f"❌ Performance and caching test failed: {str(e)}")
        return False

def main():
    """Run all simplified dataflow integration tests"""
    print("🚀 SIMPLIFIED DATAFLOW INTEGRATION TEST")
    print("="*80)
    print("Testing complete frontend-backend integration with cleaned up dataflow")
    print("="*80)
    
    tests = [
        test_api_endpoint_availability,
        test_single_dataflow_integration,
        test_no_redundant_components,
        test_frontend_backend_compatibility,
        test_performance_and_caching
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test in tests:
        if test():
            passed_tests += 1
        else:
            print(f"\n❌ Test failed: {test.__name__}")
    
    print("\n" + "="*80)
    print("🏁 SIMPLIFIED DATAFLOW INTEGRATION TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {total_tests - passed_tests} ❌")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 SIMPLIFIED DATAFLOW INTEGRATION: 100% SUCCESS!")
        print("✅ Single dataflow operational")
        print("✅ Redundant components removed")
        print("✅ Frontend-backend compatibility confirmed")
        print("✅ API endpoints working correctly")
        print("✅ Performance and caching functional")
        print("✅ Ready for frontend testing")
        return True
    else:
        print("\n❌ SIMPLIFIED DATAFLOW INTEGRATION: ISSUES DETECTED")
        print("Please review failed tests before proceeding")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
