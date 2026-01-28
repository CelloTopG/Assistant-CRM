#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Complete Phase 4 Testing Suite
Tests all Phase 4 enhancements: ML, Omnichannel, Sentiment Analysis, Personalization
"""

import frappe
from frappe import _
import json
from datetime import datetime

def test_complete_phase4_implementation():
    """Test all Phase 4 enhancements comprehensively"""
    
    print("🚀 TESTING COMPLETE PHASE 4 IMPLEMENTATION")
    print("=" * 80)
    print("🎯 Testing: ML Intelligence, Omnichannel, Sentiment Analysis, Personalization")
    print("=" * 80)
    
    test_results = {
        "phase_4_1_ml": {"passed": 0, "total": 0, "details": []},
        "phase_4_2_omnichannel": {"passed": 0, "total": 0, "details": []},
        "phase_4_3_sentiment": {"passed": 0, "total": 0, "details": []},
        "phase_4_4_personalization": {"passed": 0, "total": 0, "details": []},
        "integration_tests": {"passed": 0, "total": 0, "details": []},
        "overall_success": False
    }
    
    # Phase 4.1: ML Intelligence Testing
    print("\n🤖 PHASE 4.1: ML INTELLIGENCE TESTING")
    print("-" * 50)
    ml_results = test_ml_intelligence()
    test_results["phase_4_1_ml"] = ml_results
    
    # Phase 4.2: Omnichannel Testing
    print("\n🌐 PHASE 4.2: OMNICHANNEL TESTING")
    print("-" * 50)
    omnichannel_results = test_omnichannel_capabilities()
    test_results["phase_4_2_omnichannel"] = omnichannel_results
    
    # Phase 4.3: Sentiment Analysis Testing
    print("\n🎭 PHASE 4.3: SENTIMENT ANALYSIS TESTING")
    print("-" * 50)
    sentiment_results = test_sentiment_analysis()
    test_results["phase_4_3_sentiment"] = sentiment_results
    
    # Phase 4.4: Personalization Testing
    print("\n👤 PHASE 4.4: PERSONALIZATION TESTING")
    print("-" * 50)
    personalization_results = test_personalization_engine()
    test_results["phase_4_4_personalization"] = personalization_results
    
    # Integration Testing
    print("\n🔗 INTEGRATION TESTING")
    print("-" * 50)
    integration_results = test_phase4_integration()
    test_results["integration_tests"] = integration_results
    
    # Generate comprehensive report
    generate_phase4_report(test_results)
    
    return test_results

def test_ml_intelligence():
    """Test ML Intelligence capabilities"""
    results = {"passed": 0, "total": 5, "details": []}
    
    # Test 1: User Behavior Prediction
    try:
        from assistant_crm.api.ml_intelligence import get_user_behavior_prediction
        
        result = get_user_behavior_prediction("test_ml_user")
        if result.get("status") == "success":
            results["passed"] += 1
            results["details"].append("✅ User Behavior Prediction: Working")
        else:
            results["details"].append("❌ User Behavior Prediction: Failed")
    except Exception as e:
        results["details"].append(f"❌ User Behavior Prediction: Error - {str(e)}")
    
    # Test 2: Query Intelligence Enhancement
    try:
        from assistant_crm.api.ml_intelligence import enhance_query_intelligence
        
        result = enhance_query_intelligence(
            "I need urgent help with my denied workers compensation claim",
            "test_ml_user",
            0.6
        )
        if result.get("status") == "success":
            results["passed"] += 1
            results["details"].append("✅ Query Intelligence Enhancement: Working")
        else:
            results["details"].append("❌ Query Intelligence Enhancement: Failed")
    except Exception as e:
        results["details"].append(f"❌ Query Intelligence Enhancement: Error - {str(e)}")
    
    # Test 3: Predictive Analytics Dashboard
    try:
        from assistant_crm.api.ml_intelligence import get_predictive_analytics_dashboard
        
        result = get_predictive_analytics_dashboard()
        if result.get("status") == "success":
            results["passed"] += 1
            results["details"].append("✅ Predictive Analytics Dashboard: Working")
        else:
            results["details"].append("❌ Predictive Analytics Dashboard: Failed")
    except Exception as e:
        results["details"].append(f"❌ Predictive Analytics Dashboard: Error - {str(e)}")
    
    # Test 4: ML-Enhanced Escalation
    try:
        from assistant_crm.api.ml_intelligence import get_ml_enhanced_escalation_prediction
        
        result = get_ml_enhanced_escalation_prediction(
            "This is extremely urgent and I'm very frustrated",
            "test_ml_user",
            0.4
        )
        if result.get("status") == "success":
            results["passed"] += 1
            results["details"].append("✅ ML-Enhanced Escalation: Working")
        else:
            results["details"].append("❌ ML-Enhanced Escalation: Failed")
    except Exception as e:
        results["details"].append(f"❌ ML-Enhanced Escalation: Error - {str(e)}")
    
    # Test 5: ML DocType Enhancements
    try:
        # Check if ML User Profile exists
        if frappe.db.exists("DocType", "ML User Profile"):
            # Try to create a test profile
            profile = frappe.new_doc("ML User Profile")
            profile.user_id = "test_ml_profile_001"
            profile.language_preference = "en"
            profile.total_interactions = 10
            profile.satisfaction_average = 4.2
            profile.escalation_tendency = 0.3
            profile.ml_confidence_score = 0.85
            
            profile.insert()
            frappe.db.commit()
            
            results["passed"] += 1
            results["details"].append("✅ ML DocType Enhancements: Working")
            
            # Clean up
            frappe.delete_doc("ML User Profile", profile.name)
            frappe.db.commit()
        else:
            results["details"].append("❌ ML DocType Enhancements: ML User Profile DocType missing")
    except Exception as e:
        results["details"].append(f"❌ ML DocType Enhancements: Error - {str(e)}")
    
    return results

def test_omnichannel_capabilities():
    """Test Omnichannel capabilities"""
    results = {"passed": 0, "total": 4, "details": []}
    
    # Test 1: Omnichannel Hub
    try:
        from assistant_crm.api.omnichannel_hub import process_omnichannel_message
        
        test_message = {
            "user_id": "test_omni_user",
            "query_text": "Test omnichannel message"
        }
        
        result = process_omnichannel_message("web", json.dumps(test_message))
        if result.get("status") == "success":
            results["passed"] += 1
            results["details"].append("✅ Omnichannel Hub: Working")
        else:
            results["details"].append("❌ Omnichannel Hub: Failed")
    except Exception as e:
        results["details"].append(f"❌ Omnichannel Hub: Error - {str(e)}")
    
    # Test 2: Unified Conversation
    try:
        from assistant_crm.api.omnichannel_hub import get_unified_user_conversation
        
        result = get_unified_user_conversation("test_omni_user")
        if result.get("status") == "success":
            results["passed"] += 1
            results["details"].append("✅ Unified Conversation: Working")
        else:
            results["details"].append("❌ Unified Conversation: Failed")
    except Exception as e:
        results["details"].append(f"❌ Unified Conversation: Error - {str(e)}")
    
    # Test 3: WhatsApp Handler
    try:
        from assistant_crm.api.omnichannel_hub import WhatsAppChannelHandler
        
        handler = WhatsAppChannelHandler()
        if hasattr(handler, 'process_message') and hasattr(handler, 'send_message'):
            results["passed"] += 1
            results["details"].append("✅ WhatsApp Handler: Structure OK")
        else:
            results["details"].append("❌ WhatsApp Handler: Missing methods")
    except Exception as e:
        results["details"].append(f"❌ WhatsApp Handler: Error - {str(e)}")
    
    # Test 4: SMS Handler
    try:
        from assistant_crm.api.omnichannel_hub import SMSChannelHandler
        
        handler = SMSChannelHandler()
        if hasattr(handler, 'process_message') and hasattr(handler, 'send_sms'):
            results["passed"] += 1
            results["details"].append("✅ SMS Handler: Structure OK")
        else:
            results["details"].append("❌ SMS Handler: Missing methods")
    except Exception as e:
        results["details"].append(f"❌ SMS Handler: Error - {str(e)}")
    
    return results

def test_sentiment_analysis():
    """Test Sentiment Analysis capabilities"""
    results = {"passed": 0, "total": 4, "details": []}
    
    # Test 1: Basic Sentiment Analysis
    try:
        from assistant_crm.api.sentiment_analysis import analyze_text_sentiment
        
        result = analyze_text_sentiment(
            "I am extremely frustrated with this terrible service and awful response time",
            "test_sentiment_user"
        )
        
        if result.get("status") == "success":
            sentiment_score = result.get("sentiment_analysis", {}).get("sentiment_score", 0)
            if sentiment_score < -0.3:  # Should detect negative sentiment
                results["passed"] += 1
                results["details"].append("✅ Basic Sentiment Analysis: Working (detected negative sentiment)")
            else:
                results["details"].append("❌ Basic Sentiment Analysis: Failed to detect negative sentiment")
        else:
            results["details"].append("❌ Basic Sentiment Analysis: Failed")
    except Exception as e:
        results["details"].append(f"❌ Basic Sentiment Analysis: Error - {str(e)}")
    
    # Test 2: Positive Sentiment Detection
    try:
        from assistant_crm.api.sentiment_analysis import analyze_text_sentiment
        
        result = analyze_text_sentiment(
            "Thank you so much! This is excellent service and I'm very satisfied",
            "test_sentiment_user"
        )
        
        if result.get("status") == "success":
            sentiment_score = result.get("sentiment_analysis", {}).get("sentiment_score", 0)
            if sentiment_score > 0.3:  # Should detect positive sentiment
                results["passed"] += 1
                results["details"].append("✅ Positive Sentiment Detection: Working")
            else:
                results["details"].append("❌ Positive Sentiment Detection: Failed")
        else:
            results["details"].append("❌ Positive Sentiment Detection: Failed")
    except Exception as e:
        results["details"].append(f"❌ Positive Sentiment Detection: Error - {str(e)}")
    
    # Test 3: Satisfaction Monitoring
    try:
        from assistant_crm.api.sentiment_analysis import monitor_user_satisfaction
        
        result = monitor_user_satisfaction(
            "test_sentiment_user",
            "I need help but this is confusing",
            "Here's some information to help you"
        )
        
        if result.get("status") == "success":
            results["passed"] += 1
            results["details"].append("✅ Satisfaction Monitoring: Working")
        else:
            results["details"].append("❌ Satisfaction Monitoring: Failed")
    except Exception as e:
        results["details"].append(f"❌ Satisfaction Monitoring: Error - {str(e)}")
    
    # Test 4: Satisfaction Dashboard
    try:
        from assistant_crm.api.sentiment_analysis import get_satisfaction_dashboard
        
        result = get_satisfaction_dashboard()
        if result.get("status") == "success":
            results["passed"] += 1
            results["details"].append("✅ Satisfaction Dashboard: Working")
        else:
            results["details"].append("❌ Satisfaction Dashboard: Failed")
    except Exception as e:
        results["details"].append(f"❌ Satisfaction Dashboard: Error - {str(e)}")
    
    return results

def test_personalization_engine():
    """Test Personalization Engine capabilities"""
    results = {"passed": 0, "total": 4, "details": []}
    
    # Test 1: Personalized Experience
    try:
        from assistant_crm.api.personalization_engine import get_personalized_experience
        
        result = get_personalized_experience(
            "test_personalization_user",
            "I need help with my workers compensation claim",
            json.dumps({"urgency": "high"})
        )
        
        if result.get("status") == "success":
            experience = result.get("personalized_experience", {})
            if "user_profile" in experience and "recommendations" in experience:
                results["passed"] += 1
                results["details"].append("✅ Personalized Experience: Working")
            else:
                results["details"].append("❌ Personalized Experience: Incomplete response")
        else:
            results["details"].append("❌ Personalized Experience: Failed")
    except Exception as e:
        results["details"].append(f"❌ Personalized Experience: Error - {str(e)}")
    
    # Test 2: User Preferences Update
    try:
        from assistant_crm.api.personalization_engine import update_user_preferences
        
        preferences = {
            "language_preference": "es",
            "preferred_topics": ["claims", "medical"],
            "optimal_response_style": "detailed"
        }
        
        result = update_user_preferences("test_personalization_user", json.dumps(preferences))
        if result.get("status") == "success":
            results["passed"] += 1
            results["details"].append("✅ User Preferences Update: Working")
        else:
            results["details"].append("❌ User Preferences Update: Failed")
    except Exception as e:
        results["details"].append(f"❌ User Preferences Update: Error - {str(e)}")
    
    # Test 3: Content Recommendations
    try:
        from assistant_crm.api.personalization_engine import get_content_recommendations
        
        result = get_content_recommendations("test_personalization_user", "claims", 3)
        if result.get("status") == "success":
            results["passed"] += 1
            results["details"].append("✅ Content Recommendations: Working")
        else:
            results["details"].append("❌ Content Recommendations: Failed")
    except Exception as e:
        results["details"].append(f"❌ Content Recommendations: Error - {str(e)}")
    
    # Test 4: Personalization Engine Structure
    try:
        from assistant_crm.api.personalization_engine import PersonalizationEngine
        
        engine = PersonalizationEngine()
        if hasattr(engine, 'get_personalized_experience'):
            results["passed"] += 1
            results["details"].append("✅ Personalization Engine Structure: OK")
        else:
            results["details"].append("❌ Personalization Engine Structure: Missing methods")
    except Exception as e:
        results["details"].append(f"❌ Personalization Engine Structure: Error - {str(e)}")
    
    return results

def test_phase4_integration():
    """Test integration between all Phase 4 components"""
    results = {"passed": 0, "total": 3, "details": []}
    
    # Test 1: ML + Sentiment Integration
    try:
        from assistant_crm.api.ml_intelligence import enhance_query_intelligence
        from assistant_crm.api.sentiment_analysis import analyze_text_sentiment
        
        query = "I'm really frustrated with my denied claim and need immediate help"
        user_id = "test_integration_user"
        
        # Get ML enhancement
        ml_result = enhance_query_intelligence(query, user_id, 0.5)
        
        # Get sentiment analysis
        sentiment_result = analyze_text_sentiment(query, user_id)
        
        if (ml_result.get("status") == "success" and 
            sentiment_result.get("status") == "success"):
            results["passed"] += 1
            results["details"].append("✅ ML + Sentiment Integration: Working")
        else:
            results["details"].append("❌ ML + Sentiment Integration: Failed")
    except Exception as e:
        results["details"].append(f"❌ ML + Sentiment Integration: Error - {str(e)}")
    
    # Test 2: Personalization + ML Integration
    try:
        from assistant_crm.api.personalization_engine import get_personalized_experience
        from assistant_crm.api.ml_intelligence import get_user_behavior_prediction
        
        user_id = "test_integration_user"
        
        # Get ML behavior prediction
        ml_prediction = get_user_behavior_prediction(user_id)
        
        # Get personalized experience
        personalized = get_personalized_experience(user_id, "Help with claim")
        
        if (ml_prediction.get("status") == "success" and 
            personalized.get("status") == "success"):
            results["passed"] += 1
            results["details"].append("✅ Personalization + ML Integration: Working")
        else:
            results["details"].append("❌ Personalization + ML Integration: Failed")
    except Exception as e:
        results["details"].append(f"❌ Personalization + ML Integration: Error - {str(e)}")
    
    # Test 3: Complete Workflow Integration
    try:
        # Simulate complete user interaction workflow
        user_id = "test_complete_workflow"
        query = "I need urgent help with my workers compensation claim status"
        
        # Step 1: ML Intelligence
        from assistant_crm.api.ml_intelligence import enhance_query_intelligence
        ml_result = enhance_query_intelligence(query, user_id, 0.7)
        
        # Step 2: Sentiment Analysis
        from assistant_crm.api.sentiment_analysis import analyze_text_sentiment
        sentiment_result = analyze_text_sentiment(query, user_id)
        
        # Step 3: Personalization
        from assistant_crm.api.personalization_engine import get_personalized_experience
        personalized_result = get_personalized_experience(user_id, query)
        
        # Step 4: Omnichannel Processing
        from assistant_crm.api.omnichannel_hub import process_omnichannel_message
        omni_result = process_omnichannel_message("web", json.dumps({
            "user_id": user_id,
            "query_text": query
        }))
        
        all_successful = all([
            ml_result.get("status") == "success",
            sentiment_result.get("status") == "success", 
            personalized_result.get("status") == "success",
            omni_result.get("status") == "success"
        ])
        
        if all_successful:
            results["passed"] += 1
            results["details"].append("✅ Complete Workflow Integration: Working")
        else:
            results["details"].append("❌ Complete Workflow Integration: Some components failed")
    except Exception as e:
        results["details"].append(f"❌ Complete Workflow Integration: Error - {str(e)}")
    
    return results

def generate_phase4_report(test_results):
    """Generate comprehensive Phase 4 test report"""
    
    print("\n" + "=" * 80)
    print("🏆 PHASE 4 COMPLETE IMPLEMENTATION TEST REPORT")
    print("=" * 80)
    
    total_passed = 0
    total_tests = 0
    
    # Calculate overall statistics
    for phase, results in test_results.items():
        if phase != "overall_success":
            total_passed += results["passed"]
            total_tests += results["total"]
    
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"📊 OVERALL RESULTS:")
    print(f"   Tests Passed: {total_passed}/{total_tests}")
    print(f"   Success Rate: {success_rate:.1f}%")
    
    # Phase-by-phase results
    phase_names = {
        "phase_4_1_ml": "🤖 Phase 4.1: ML Intelligence",
        "phase_4_2_omnichannel": "🌐 Phase 4.2: Omnichannel",
        "phase_4_3_sentiment": "🎭 Phase 4.3: Sentiment Analysis",
        "phase_4_4_personalization": "👤 Phase 4.4: Personalization",
        "integration_tests": "🔗 Integration Tests"
    }
    
    for phase_key, phase_name in phase_names.items():
        if phase_key in test_results:
            results = test_results[phase_key]
            phase_success = (results["passed"] / results["total"] * 100) if results["total"] > 0 else 0
            status = "✅ PASS" if phase_success >= 75 else "🟡 PARTIAL" if phase_success >= 50 else "❌ FAIL"
            
            print(f"\n{phase_name}: {status}")
            print(f"   Tests: {results['passed']}/{results['total']} ({phase_success:.1f}%)")
            
            for detail in results["details"]:
                print(f"   {detail}")
    
    # Overall assessment
    print(f"\n🎯 PHASE 4 ASSESSMENT:")
    if success_rate >= 90:
        print("   🎉 EXCELLENT - Phase 4 implementation is outstanding!")
        print("   ✅ All major components working correctly")
        print("   🚀 System ready for advanced AI/ML operations")
        test_results["overall_success"] = True
    elif success_rate >= 75:
        print("   ✅ GOOD - Phase 4 implementation is successful!")
        print("   🎯 Most components working correctly")
        print("   🔧 Minor issues may need attention")
        test_results["overall_success"] = True
    elif success_rate >= 50:
        print("   🟡 PARTIAL - Phase 4 implementation partially successful")
        print("   📋 Core functionality working")
        print("   🔧 Some components need troubleshooting")
        test_results["overall_success"] = False
    else:
        print("   ❌ NEEDS WORK - Phase 4 implementation needs attention")
        print("   🔧 Multiple components require fixes")
        print("   📋 Review implementation and dependencies")
        test_results["overall_success"] = False
    
    # Next steps
    print(f"\n📋 NEXT STEPS:")
    if test_results["overall_success"]:
        print("   1. ✅ Phase 4 implementation complete and successful")
        print("   2. 🚀 System enhanced with advanced AI/ML capabilities")
        print("   3. 📊 Monitor performance and user satisfaction")
        print("   4. 🔄 Continue with system optimization and fine-tuning")
    else:
        print("   1. 🔧 Address failing test components")
        print("   2. 📋 Review error logs and dependencies")
        print("   3. 🔄 Re-run tests after fixes")
        print("   4. 📊 Validate system performance")
    
    print("=" * 80)
    print("🎊 PHASE 4 TESTING COMPLETE 🎊")
    print("=" * 80)

if __name__ == "__main__":
    frappe.init(site="dev")
    frappe.connect()
    
    # Run complete Phase 4 testing
    results = test_complete_phase4_implementation()
    
    # Final status
    if results["overall_success"]:
        print("\n🎉 PHASE 4 IMPLEMENTATION: SUCCESS!")
        print("🚀 WCFCB Assistant CRM enhanced with advanced AI/ML capabilities")
    else:
        print("\n🔧 PHASE 4 IMPLEMENTATION: NEEDS ATTENTION")
        print("📋 Some components require troubleshooting")
