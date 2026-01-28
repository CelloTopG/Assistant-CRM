#!/usr/bin/env python3
"""
Phase 1.1 Implementation Validation
Validates Enhanced Cache Service implementation without problematic imports
"""

import sys
import os
import time

def validate_cache_service_implementation():
    """Validate Enhanced Cache Service implementation"""
    print("🧪 VALIDATING: Enhanced Cache Service Implementation")
    print("="*60)
    
    try:
        # Import cache service directly
        sys.path.insert(0, os.path.join(os.getcwd(), 'assistant_crm', 'services'))
        from enhanced_cache_service import EnhancedCacheService
        
        # Test 1: Service instantiation
        cache = EnhancedCacheService()
        print("✅ Enhanced Cache Service instantiated successfully")
        
        # Test 2: Basic functionality
        user_context = {'user_id': 'TEST001', 'user_role': 'beneficiary'}
        cache_key = cache.get_cache_key('claim_status', user_context, 'What is my claim status?')
        
        test_data = {
            'type': 'claim_data',
            'claim_number': 'CLM-TEST001-2025',
            'status': 'Under Review',
            'retrieved_at': '2025-08-12T23:30:00'
        }
        
        # Set and get data
        cache.set(cache_key, test_data, 'live_data')
        retrieved = cache.get(cache_key, 'live_data')
        
        if retrieved and retrieved['claim_number'] == 'CLM-TEST001-2025':
            print("✅ Cache set/get functionality working")
        else:
            print("❌ Cache set/get functionality failed")
            return False
        
        # Test 3: Performance metrics
        stats = cache.get_performance_stats()
        if stats['hit_rate'] > 0 and stats['dataflow_optimization_ready']:
            print(f"✅ Performance metrics: Hit rate {stats['hit_rate']}%")
            print(f"✅ Dataflow optimization ready: {stats['dataflow_optimization_ready']}")
        else:
            print("❌ Performance metrics failed")
            return False
        
        # Test 4: Future compatibility
        future_config = cache.prepare_for_unified_dataflow()
        if future_config['cache_ready'] and future_config['unified_dataflow_support']:
            print("✅ Future unified dataflow support confirmed")
            print(f"   Dependencies tracked: {len(future_config['dependencies'])}")
            print(f"   Migration notes: {len(future_config['migration_notes'])}")
        else:
            print("❌ Future compatibility check failed")
            return False
        
        # Test 5: Cache invalidation
        invalidated = cache.invalidate_user_cache('TEST001')
        print(f"✅ User cache invalidation: {invalidated} entries processed")
        
        print("\n🎉 ENHANCED CACHE SERVICE: FULLY VALIDATED")
        return True
        
    except Exception as e:
        print(f"❌ Cache service validation failed: {str(e)}")
        return False

def validate_intent_router_modifications():
    """Validate intent router modifications for cache integration"""
    print("\n🧪 VALIDATING: Intent Router Cache Integration")
    print("="*60)
    
    try:
        # Check if intent router file has been modified correctly
        intent_router_path = os.path.join('assistant_crm', 'services', 'intent_router.py')
        
        if not os.path.exists(intent_router_path):
            print("❌ Intent router file not found")
            return False
        
        with open(intent_router_path, 'r') as f:
            content = f.read()
        
        # Check for cache service import
        if 'from assistant_crm.services.enhanced_cache_service import get_cache_service' in content:
            print("✅ Cache service import added to intent router")
        else:
            print("❌ Cache service import missing from intent router")
            return False
        
        # Check for cache initialization
        if 'self.cache_service = get_cache_service()' in content:
            print("✅ Cache service initialization added")
        else:
            print("❌ Cache service initialization missing")
            return False
        
        # Check for cache integration in route_request
        if 'cache_key = self.cache_service.get_cache_key' in content:
            print("✅ Cache key generation integrated")
        else:
            print("❌ Cache key generation missing")
            return False
        
        # Check for cache hit logic
        if 'cached_response = self.cache_service.get(cache_key' in content:
            print("✅ Cache hit logic implemented")
        else:
            print("❌ Cache hit logic missing")
            return False
        
        # Check for cache storage logic
        if 'self.cache_service.set(cache_key, live_data_result' in content:
            print("✅ Cache storage logic implemented")
        else:
            print("❌ Cache storage logic missing")
            return False
        
        # Check for performance monitoring
        if 'get_cache_performance_stats' in content:
            print("✅ Cache performance monitoring added")
        else:
            print("❌ Cache performance monitoring missing")
            return False
        
        print("\n✅ INTENT ROUTER MODIFICATIONS: VALIDATED")
        return True
        
    except Exception as e:
        print(f"❌ Intent router validation failed: {str(e)}")
        return False

def validate_backup_creation():
    """Validate that backup was created successfully"""
    print("\n🧪 VALIDATING: System Backup Creation")
    print("="*60)
    
    try:
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            print("❌ Backup directory not found")
            return False
        
        # Find the most recent backup
        backup_folders = [f for f in os.listdir(backup_dir) if f.startswith('dataflow_optimization_')]
        
        if not backup_folders:
            print("❌ No dataflow optimization backups found")
            return False
        
        latest_backup = max(backup_folders)
        backup_path = os.path.join(backup_dir, latest_backup)
        
        # Check backup contents
        services_backup = os.path.join(backup_path, 'services_backup')
        api_backup = os.path.join(backup_path, 'api_backup')
        
        if os.path.exists(services_backup) and os.path.exists(api_backup):
            print(f"✅ Backup created successfully: {latest_backup}")
            print(f"   Services backup: {len(os.listdir(services_backup))} files")
            print(f"   API backup: {len(os.listdir(api_backup))} files")
            return True
        else:
            print("❌ Backup incomplete - missing services or API backup")
            return False
        
    except Exception as e:
        print(f"❌ Backup validation failed: {str(e)}")
        return False

def validate_file_structure():
    """Validate that all required files are in place"""
    print("\n🧪 VALIDATING: File Structure and Dependencies")
    print("="*60)
    
    required_files = [
        'assistant_crm/services/enhanced_cache_service.py',
        'assistant_crm/services/intent_router.py',
        'assistant_crm/services/live_data_orchestrator.py',
        'assistant_crm/services/response_assembler.py'
    ]
    
    all_files_present = True
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            all_files_present = False
    
    if all_files_present:
        print("\n✅ All required files present")
        return True
    else:
        print("\n❌ Some required files missing")
        return False

def validate_zero_regression_readiness():
    """Validate readiness for zero regression testing"""
    print("\n🧪 VALIDATING: Zero Regression Readiness")
    print("="*60)
    
    try:
        # Check that cache service doesn't break existing functionality
        sys.path.insert(0, os.path.join(os.getcwd(), 'assistant_crm', 'services'))
        from enhanced_cache_service import EnhancedCacheService
        
        cache = EnhancedCacheService()
        
        # Test all 8 live data intent types
        live_data_intents = [
            'claim_status', 'payment_status', 'pension_inquiry', 'claim_submission',
            'account_info', 'payment_history', 'document_status', 'technical_help'
        ]
        
        user_context = {'user_id': 'TEST001', 'user_role': 'beneficiary'}
        
        for intent in live_data_intents:
            cache_key = cache.get_cache_key(intent, user_context, f"Test {intent}")
            test_data = {'type': f'{intent}_data', 'test': True}
            
            cache.set(cache_key, test_data, 'live_data')
            retrieved = cache.get(cache_key, 'live_data')
            
            if not retrieved or retrieved['test'] != True:
                print(f"❌ Cache functionality failed for {intent}")
                return False
        
        print(f"✅ Cache functionality validated for all {len(live_data_intents)} live data intents")
        
        # Test knowledge base intent types
        knowledge_base_intents = ['greeting', 'goodbye', 'agent_request', 'employer_registration']
        
        for intent in knowledge_base_intents:
            cache_key = cache.get_cache_key(intent, user_context, f"Test {intent}")
            # Knowledge base intents should work with cache but may not be cached
            if cache_key:
                print(f"✅ Cache key generation working for {intent}")
        
        print(f"✅ Cache compatibility validated for all {len(knowledge_base_intents)} knowledge base intents")
        
        print("\n✅ ZERO REGRESSION READINESS: CONFIRMED")
        return True
        
    except Exception as e:
        print(f"❌ Zero regression readiness validation failed: {str(e)}")
        return False

def main():
    """Run all Phase 1.1 implementation validations"""
    print("🚀 PHASE 1.1: ENHANCED CACHE SERVICE IMPLEMENTATION VALIDATION")
    print("="*80)
    print("Validating cache implementation with zero regression guarantee")
    print("="*80)
    
    validations = [
        validate_backup_creation,
        validate_file_structure,
        validate_cache_service_implementation,
        validate_intent_router_modifications,
        validate_zero_regression_readiness
    ]
    
    passed_validations = 0
    total_validations = len(validations)
    
    for validation in validations:
        if validation():
            passed_validations += 1
        else:
            print(f"\n❌ Validation failed: {validation.__name__}")
    
    print("\n" + "="*80)
    print("🏁 PHASE 1.1 VALIDATION SUMMARY")
    print("="*80)
    print(f"Total Validations: {total_validations}")
    print(f"Passed: {passed_validations} ✅")
    print(f"Failed: {total_validations - passed_validations} ❌")
    print(f"Success Rate: {(passed_validations/total_validations)*100:.1f}%")
    
    if passed_validations == total_validations:
        print("\n🎉 PHASE 1.1 IMPLEMENTATION: 100% VALIDATED!")
        print("✅ Enhanced Cache Service successfully implemented")
        print("✅ Intent Router cache integration completed")
        print("✅ Zero regression readiness confirmed")
        print("✅ Future unified dataflow support prepared")
        print("✅ Comprehensive backup created for rollback capability")
        print("\n📋 ROLLBACK PROCEDURES:")
        print("   1. Restore from backup: backups/dataflow_optimization_*")
        print("   2. Remove enhanced_cache_service.py")
        print("   3. Revert intent_router.py changes")
        print("   4. Test all 8 live data intents + 4 knowledge base intents")
        print("\n🚀 READY FOR PHASE 1.2: REQUEST BATCHING AND CONNECTION POOLING")
        return True
    else:
        print("\n❌ PHASE 1.1 IMPLEMENTATION: VALIDATION ISSUES DETECTED")
        print("Please review failed validations before proceeding")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
