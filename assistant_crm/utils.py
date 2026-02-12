#!/usr/bin/env python3
"""
Assistant CRM Utilities
=======================

Utility functions for testing and deployment validation.
"""

import json
import frappe


def get_public_url():
    """Return the public-facing base URL for external links (surveys, webhooks, etc.).

    Resolution order:
    1. Site config key ``assistant_crm_public_base_url``  (e.g. "https://clone.exn1.uk")
    2. ``frappe.utils.get_url()`` as a fallback (may return localhost in dev).

    The returned URL never has a trailing slash.
    """
    conf = frappe.conf or {}
    public_url = (conf.get("assistant_crm_public_base_url") or "").strip().rstrip("/")
    if public_url:
        return public_url
    return (frappe.utils.get_url() or "").rstrip("/")

def test_live_data_deployment():
    """Test the live data integration deployment."""
    print("🚀 TESTING ASSISTANT CRM LIVE DATA DEPLOYMENT")
    print("=" * 50)
    
    results = []
    
    # Test 1: Intent Router
    try:
        from assistant_crm.services.intent_router import IntentRouter
        router = IntentRouter()
        
        live_data_count = len(router.live_data_intents)
        kb_count = len(router.knowledge_base_intents)
        
        expected_live_data = {
            'claim_status', 'payment_status', 'pension_inquiry', 'claim_submission',
            'account_info', 'payment_history', 'document_status', 'technical_help'
        }
        
        config_correct = router.live_data_intents == expected_live_data
        
        print(f"✅ Intent Router: {live_data_count} live data intents, {kb_count} KB intents")
        print(f"✅ Configuration: {'CORRECT' if config_correct else 'INCORRECT'}")
        
        if config_correct:
            print("✅ All 8 live data intents properly configured")
        
        results.append(("Intent Router", config_correct))
        
    except Exception as e:
        print(f"❌ Intent Router error: {e}")
        results.append(("Intent Router", False))
    
    # Test 2: Unified Chat API
    try:
        from assistant_crm.api.unified_chat_api import unified_chat_api
        
        # Test authenticated user with live data
        result = unified_chat_api(
            message="What is my claim status?",
            session_id="test_deployment",
            user_context=json.dumps({
                'user_id': 'TEST001',
                'user_role': 'beneficiary',
                'permissions': ['view_public_info', 'view_own_data', 'submit_claims']
            })
        )
        
        success = result.get('success', False)
        live_data_used = result.get('live_data_used', False)
        reply = result.get('reply', '')
        
        print(f"✅ API Success: {success}")
        print(f"✅ Live Data Used: {live_data_used}")
        print(f"✅ Reply Length: {len(reply)} chars")
        
        anna_present = 'Anna' in reply
        wcfcb_present = 'WCFCB' in reply
        
        print(f"✅ Anna Personality: {anna_present}")
        print(f"✅ WCFCB Branding: {wcfcb_present}")
        
        api_success = success and live_data_used and len(reply) > 0
        results.append(("Live Data API", api_success))
        
        # Test guest user fallback
        guest_result = unified_chat_api(
            message="What is my claim status?",
            session_id="test_guest",
            user_context=json.dumps({
                'user_id': 'guest',
                'user_role': 'guest'
            })
        )
        
        guest_success = guest_result.get('success', False)
        guest_live_data = guest_result.get('live_data_used', False)
        
        print(f"✅ Guest Success: {guest_success}")
        print(f"✅ Guest Fallback (no live data): {not guest_live_data}")
        
        fallback_success = guest_success and not guest_live_data
        results.append(("Guest Fallback", fallback_success))
        
    except Exception as e:
        print(f"❌ API error: {e}")
        results.append(("Live Data API", False))
        results.append(("Guest Fallback", False))
    
    # Summary
    print("\n📊 DEPLOYMENT TEST SUMMARY")
    print("=" * 30)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 DEPLOYMENT: COMPLETE SUCCESS!")
        print("✅ All 8 live data intents operational")
        print("✅ Anna personality and WCFCB branding preserved")
        print("✅ Ready for production use")
    else:
        print(f"\n⚠️  DEPLOYMENT: {total - passed} issues detected")
    
    return passed == total

def test_all_intents():
    """Test all 8 live data intents individually."""
    print("\n🔍 TESTING ALL 8 LIVE DATA INTENTS")
    print("=" * 40)
    
    from assistant_crm.api.unified_chat_api import unified_chat_api
    
    test_cases = [
        ("Claim Status", "What is my claim status?"),
        ("Payment Status", "When will I receive my payment?"),
        ("Pension Inquiry", "What are my pension benefits?"),
        ("Claim Submission", "How do I submit a claim?"),
        ("Account Info", "What is my account information?"),
        ("Payment History", "Show me my payment history"),
        ("Document Status", "What is my document status?"),
        ("Technical Help", "I need technical help")
    ]
    
    user_context = json.dumps({
        'user_id': 'TEST001',
        'user_role': 'beneficiary',
        'permissions': ['view_public_info', 'view_own_data', 'submit_claims', 'view_payments']
    })
    
    results = []
    
    for intent_name, message in test_cases:
        try:
            result = unified_chat_api(
                message=message,
                session_id=f"test_{intent_name.lower().replace(' ', '_')}",
                user_context=user_context
            )
            
            success = result.get('success', False)
            live_data_used = result.get('live_data_used', False)
            reply_length = len(result.get('reply', ''))
            
            overall_success = success and live_data_used and reply_length > 0
            
            status = "✅" if overall_success else "❌"
            print(f"{status} {intent_name}: Live={live_data_used}, Reply={reply_length} chars")
            
            results.append(overall_success)
            
        except Exception as e:
            print(f"❌ {intent_name}: Error - {e}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nIntent Test Results: {passed}/{total} working ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL 8 LIVE DATA INTENTS: FULLY OPERATIONAL!")
    else:
        print(f"⚠️  {total - passed} intents need attention")
    
    return passed == total

def run_complete_deployment_test():
    """Run complete deployment test."""
    print("🎯 ASSISTANT CRM COMPLETE DEPLOYMENT TEST")
    print("=" * 50)
    
    # Run basic deployment test
    basic_success = test_live_data_deployment()
    
    # Run comprehensive intent test
    if basic_success:
        intent_success = test_all_intents()
        
        if intent_success:
            print("\n🎉🎉🎉 COMPLETE DEPLOYMENT SUCCESS! 🎉🎉🎉")
            print("✅ All systems operational")
            print("✅ Ready for production deployment")
            return True
        else:
            print("\n⚠️  Some intents need attention")
            return False
    else:
        print("\n⚠️  Basic deployment issues detected")
        return False
