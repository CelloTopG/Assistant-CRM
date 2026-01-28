#!/usr/bin/env python3
"""
Check Phase 4 Status After Medium-Term Enhancements
"""

import frappe

def check_phase4_status():
    """Check that Phase 4 functionality is still working"""
    
    print("🔍 CHECKING PHASE 4 STATUS")
    print("=" * 40)
    
    phase4_status = {"working": 0, "total": 4}
    
    try:
        # Test sentiment analysis (the previously fixed component)
        from assistant_crm.api.sentiment_analysis import get_satisfaction_dashboard
        result = get_satisfaction_dashboard()
        if result.get("status") == "success":
            print("✅ Phase 4 Sentiment Analysis: Working")
            phase4_status["working"] += 1
        else:
            print("❌ Phase 4 Sentiment Analysis: Failed")
    except Exception as e:
        print(f"❌ Phase 4 Sentiment Analysis: Error - {str(e)}")
    
    try:
        # Test ML intelligence
        from assistant_crm.api.ml_intelligence import get_user_behavior_prediction
        result = get_user_behavior_prediction("test_user")
        if result.get("status") == "success":
            print("✅ Phase 4 ML Intelligence: Working")
            phase4_status["working"] += 1
        else:
            print("❌ Phase 4 ML Intelligence: Failed")
    except Exception as e:
        print(f"❌ Phase 4 ML Intelligence: Error - {str(e)}")
    
    try:
        # Test personalization
        from assistant_crm.api.personalization_engine import get_personalized_experience
        result = get_personalized_experience("test_user", "test query")
        if result.get("status") == "success":
            print("✅ Phase 4 Personalization: Working")
            phase4_status["working"] += 1
        else:
            print("❌ Phase 4 Personalization: Failed")
    except Exception as e:
        print(f"❌ Phase 4 Personalization: Error - {str(e)}")
    
    try:
        # Test omnichannel
        from assistant_crm.api.omnichannel_hub import get_unified_user_conversation
        result = get_unified_user_conversation("test_user")
        if result.get("status") == "success":
            print("✅ Phase 4 Omnichannel: Working")
            phase4_status["working"] += 1
        else:
            print("❌ Phase 4 Omnichannel: Failed")
    except Exception as e:
        print(f"❌ Phase 4 Omnichannel: Error - {str(e)}")
    
    phase4_status["total"] = 4
    success_rate = (phase4_status["working"] / phase4_status["total"]) * 100
    
    print(f"\n📊 Phase 4 Status: {phase4_status['working']}/{phase4_status['total']} ({success_rate:.1f}%)")
    
    if success_rate >= 75:
        print("✅ Phase 4 foundation remains stable")
        return True
    else:
        print("❌ Phase 4 foundation has issues")
        return False

if __name__ == "__main__":
    frappe.init(site="dev")
    frappe.connect()
    
    check_phase4_status()
