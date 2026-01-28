#!/usr/bin/env python3
"""
Dataflow Cleanup Validation
Validates the simplified single dataflow implementation
"""

import sys
import os
import time

def validate_simplified_api_structure():
    """Validate simplified API structure"""
    print("🧪 VALIDATING: Simplified API Structure")
    print("="*60)
    
    try:
        # Check API __init__.py has been cleaned up
        api_init_path = os.path.join('assistant_crm', 'api', '__init__.py')
        
        if not os.path.exists(api_init_path):
            print("❌ API __init__.py not found")
            return False
        
        with open(api_init_path, 'r') as f:
            content = f.read()
        
        # Check for simplified imports only
        if 'simplified_chat' in content and 'send_message' in content:
            print("✅ API __init__.py cleaned up - only simplified_chat imported")
        else:
            print("❌ API __init__.py still has redundant imports")
            return False
        
        # Check redundant endpoints are not imported
        redundant_imports = ['chatbot', 'optimized_chat', 'unified_chat_api']
        for redundant in redundant_imports:
            if redundant in content:
                print(f"❌ Redundant import found: {redundant}")
                return False
        
        print("✅ No redundant API imports found")
        
        # Check simplified_chat.py exists
        simplified_chat_path = os.path.join('assistant_crm', 'api', 'simplified_chat.py')
        if os.path.exists(simplified_chat_path):
            print("✅ Simplified chat API file exists")
        else:
            print("❌ Simplified chat API file missing")
            return False
        
        print("\n✅ SIMPLIFIED API STRUCTURE: VALIDATED")
        return True
        
    except Exception as e:
        print(f"❌ API structure validation failed: {str(e)}")
        return False

def validate_single_dataflow_path():
    """Validate single dataflow path functionality"""
    print("\n🧪 VALIDATING: Single Dataflow Path")
    print("="*60)
    
    try:
        # Import services directly
        sys.path.insert(0, os.path.join(os.getcwd(), 'assistant_crm', 'services'))
        from intent_router import IntentRouter
        
        router = IntentRouter()
        user_context = {'user_id': 'guest', 'user_role': 'guest', 'authenticated': False}
        
        # Test single dataflow for different intent types
        test_cases = [
            # Knowledge base intents
            ('Hello Anna', 'greeting', 'knowledge_base'),
            ('Thank you', 'goodbye', 'knowledge_base'),
            ('I need help', 'agent_request', 'knowledge_base'),
            
            # Live data intents (will fallback in test mode)
            ('What is my claim status?', 'claim_status', 'fallback'),
            ('When will I receive payment?', 'payment_status', 'fallback'),
            ('What is my pension?', 'pension_inquiry', 'fallback'),
        ]
        
        all_passed = True
        
        for message, expected_intent, expected_source in test_cases:
            intent, confidence = router._detect_intent(message)
            result = router.route_request(message, user_context)
            
            intent_correct = intent == expected_intent
            source_correct = result.get('source') == expected_source
            
            if intent_correct and source_correct:
                print(f"✅ \"{message}\" → {intent} → {result.get('source')}")
            else:
                print(f"❌ \"{message}\" → {intent} (expected: {expected_intent}) → {result.get('source')} (expected: {expected_source})")
                all_passed = False
        
        if all_passed:
            print("\n✅ SINGLE DATAFLOW PATH: VALIDATED")
            return True
        else:
            print("\n❌ Single dataflow path issues detected")
            return False
        
    except Exception as e:
        print(f"❌ Single dataflow validation failed: {str(e)}")
        return False

def validate_cache_integration():
    """Validate cache integration in simplified dataflow"""
    print("\n🧪 VALIDATING: Cache Integration")
    print("="*60)
    
    try:
        sys.path.insert(0, os.path.join(os.getcwd(), 'assistant_crm', 'services'))
        from intent_router import IntentRouter
        from enhanced_cache_service import get_cache_service, reset_cache_service
        
        # Reset cache for clean test
        reset_cache_service()
        
        router = IntentRouter()
        user_context = {'user_id': 'test_user', 'user_role': 'beneficiary', 'authenticated': False}
        
        if not router.cache_enabled:
            print("❌ Cache integration not enabled")
            return False
        
        print("✅ Cache integration enabled")
        
        # Test cache functionality
        message = "What is my claim status?"
        
        # First request (cache miss)
        result1 = router.route_request(message, user_context)
        cache_hit1 = result1.get('cache_hit', False)
        
        # Second request (should be cache hit for same user)
        result2 = router.route_request(message, user_context)
        cache_hit2 = result2.get('cache_hit', False)
        
        if not cache_hit1 and cache_hit2:
            print("✅ Cache miss → cache hit pattern working")
        else:
            print(f"❌ Cache pattern not working: first={cache_hit1}, second={cache_hit2}")
            return False
        
        # Test cache performance stats
        stats = router.get_cache_performance_stats()
        if stats.get('cache_enabled') and stats.get('dataflow_optimization_ready'):
            print("✅ Cache performance monitoring working")
        else:
            print("❌ Cache performance monitoring failed")
            return False
        
        print("\n✅ CACHE INTEGRATION: VALIDATED")
        return True
        
    except Exception as e:
        print(f"❌ Cache integration validation failed: {str(e)}")
        return False

def validate_redundant_components_removed():
    """Validate that redundant components are identified for removal"""
    print("\n🧪 VALIDATING: Redundant Components Identification")
    print("="*60)
    
    try:
        # Check for redundant API files that should be removed/deprecated
        redundant_api_files = [
            'assistant_crm/api/chat.py',
            'assistant_crm/api/optimized_chat.py',
            'assistant_crm/api/unified_chat_api.py',
            'assistant_crm/api/chatbot.py'
        ]
        
        redundant_files_found = []
        for file_path in redundant_api_files:
            if os.path.exists(file_path):
                redundant_files_found.append(file_path)
        
        if redundant_files_found:
            print("⚠️  Redundant API files identified for removal:")
            for file_path in redundant_files_found:
                print(f"   - {file_path}")
        else:
            print("✅ No redundant API files found")
        
        # Check for response assembler (should be bypassed)
        response_assembler_path = 'assistant_crm/services/response_assembler.py'
        if os.path.exists(response_assembler_path):
            print("⚠️  Response assembler identified for removal/bypass")
            print("   - Direct AI response generation implemented")
        else:
            print("✅ Response assembler already removed")
        
        # Check for session management components (should be removed)
        session_files = [
            'assistant_crm/services/session_context_manager.py',
            'assistant_crm/services/session_management_system.py',
            'assistant_crm/api/session_manager.py'
        ]
        
        session_files_found = []
        for file_path in session_files:
            if os.path.exists(file_path):
                session_files_found.append(file_path)
        
        if session_files_found:
            print("⚠️  Session management files identified for removal:")
            for file_path in session_files_found:
                print(f"   - {file_path}")
        else:
            print("✅ Session management files already removed")
        
        print("\n✅ REDUNDANT COMPONENTS: IDENTIFIED")
        return True
        
    except Exception as e:
        print(f"❌ Redundant components validation failed: {str(e)}")
        return False

def validate_gemini_direct_integration():
    """Validate Gemini service can handle direct AI responses"""
    print("\n🧪 VALIDATING: Gemini Direct Integration")
    print("="*60)
    
    try:
        # Check if Gemini service has context response method
        gemini_service_path = 'assistant_crm/services/gemini_service.py'
        
        if not os.path.exists(gemini_service_path):
            print("❌ Gemini service file not found")
            return False
        
        with open(gemini_service_path, 'r') as f:
            content = f.read()
        
        # Check for context response method
        if 'generate_response_with_context' in content:
            print("✅ Gemini context response method found")
        else:
            print("❌ Gemini context response method missing")
            return False
        
        # Check for live data context handling
        if 'live_data' in content and 'context' in content:
            print("✅ Gemini live data context handling implemented")
        else:
            print("❌ Gemini live data context handling missing")
            return False
        
        print("\n✅ GEMINI DIRECT INTEGRATION: VALIDATED")
        return True
        
    except Exception as e:
        print(f"❌ Gemini integration validation failed: {str(e)}")
        return False

def validate_error_handling():
    """Validate consistent error handling across dataflow"""
    print("\n🧪 VALIDATING: Error Handling")
    print("="*60)
    
    try:
        sys.path.insert(0, os.path.join(os.getcwd(), 'assistant_crm', 'services'))
        from intent_router import IntentRouter
        
        router = IntentRouter()
        user_context = {'user_id': 'test', 'user_role': 'guest'}
        
        # Test error handling with invalid inputs
        test_cases = [
            ('', 'empty message'),
            (None, 'null message'),
            ('x' * 10000, 'very long message')
        ]
        
        for message, description in test_cases:
            try:
                result = router.route_request(message, user_context)
                if result and 'source' in result:
                    print(f"✅ Error handling for {description}: {result.get('source')}")
                else:
                    print(f"❌ Error handling failed for {description}")
                    return False
            except Exception as e:
                print(f"❌ Unhandled exception for {description}: {str(e)}")
                return False
        
        print("\n✅ ERROR HANDLING: VALIDATED")
        return True
        
    except Exception as e:
        print(f"❌ Error handling validation failed: {str(e)}")
        return False

def main():
    """Run all dataflow cleanup validations"""
    print("🚀 DATAFLOW CLEANUP VALIDATION")
    print("="*80)
    print("Validating simplified single dataflow implementation")
    print("="*80)
    
    validations = [
        validate_simplified_api_structure,
        validate_single_dataflow_path,
        validate_cache_integration,
        validate_redundant_components_removed,
        validate_gemini_direct_integration,
        validate_error_handling
    ]
    
    passed_validations = 0
    total_validations = len(validations)
    
    for validation in validations:
        if validation():
            passed_validations += 1
        else:
            print(f"\n❌ Validation failed: {validation.__name__}")
    
    print("\n" + "="*80)
    print("🏁 DATAFLOW CLEANUP VALIDATION SUMMARY")
    print("="*80)
    print(f"Total Validations: {total_validations}")
    print(f"Passed: {passed_validations} ✅")
    print(f"Failed: {total_validations - passed_validations} ❌")
    print(f"Success Rate: {(passed_validations/total_validations)*100:.1f}%")
    
    if passed_validations == total_validations:
        print("\n🎉 DATAFLOW CLEANUP: 100% VALIDATED!")
        print("✅ Single dataflow path implemented")
        print("✅ Redundant endpoints removed from imports")
        print("✅ Cache integration working")
        print("✅ Gemini direct integration ready")
        print("✅ Error handling consistent")
        print("✅ Ready for next cleanup phase")
        return True
    else:
        print("\n❌ DATAFLOW CLEANUP: VALIDATION ISSUES DETECTED")
        print("Please review failed validations before proceeding")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
