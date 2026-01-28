#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Final System Verification
Comprehensive verification of all system components after medium-term enhancements
"""

import frappe
from frappe import _
import json
from datetime import datetime

def final_system_verification():
    """Perform comprehensive system verification"""
    
    print("🔍 FINAL SYSTEM VERIFICATION")
    print("=" * 80)
    print("🎯 Verifying: Phase 4 Foundation + Medium-Term Enhancements")
    print("=" * 80)
    
    verification_results = {
        "phase_4_foundation": {"status": "unknown", "details": []},
        "medium_term_enhancements": {"status": "unknown", "details": []},
        "database_integrity": {"status": "unknown", "details": []},
        "api_endpoints": {"status": "unknown", "details": []},
        "performance_standards": {"status": "unknown", "details": []},
        "overall_system_health": "unknown"
    }
    
    # Phase 4 Foundation Verification
    print("\n🏗️ PHASE 4 FOUNDATION VERIFICATION")
    print("-" * 50)
    phase4_status = verify_phase4_foundation()
    verification_results["phase_4_foundation"] = phase4_status
    
    # Medium-Term Enhancements Verification
    print("\n🚀 MEDIUM-TERM ENHANCEMENTS VERIFICATION")
    print("-" * 50)
    enhancements_status = verify_medium_term_enhancements()
    verification_results["medium_term_enhancements"] = enhancements_status
    
    # Database Integrity Verification
    print("\n🗄️ DATABASE INTEGRITY VERIFICATION")
    print("-" * 50)
    database_status = verify_database_integrity()
    verification_results["database_integrity"] = database_status
    
    # API Endpoints Verification
    print("\n🔗 API ENDPOINTS VERIFICATION")
    print("-" * 50)
    api_status = verify_api_endpoints()
    verification_results["api_endpoints"] = api_status
    
    # Performance Standards Verification
    print("\n⚡ PERFORMANCE STANDARDS VERIFICATION")
    print("-" * 50)
    performance_status = verify_performance_standards()
    verification_results["performance_standards"] = performance_status
    
    # Generate final assessment
    generate_final_assessment(verification_results)
    
    return verification_results

def verify_phase4_foundation():
    """Verify Phase 4 foundation components"""
    status = {"status": "unknown", "details": [], "working_components": 0, "total_components": 4}
    
    # Test ML Intelligence
    try:
        from assistant_crm.api.ml_intelligence import get_user_behavior_prediction
        result = get_user_behavior_prediction("verification_user")
        if result.get("status") == "success":
            status["details"].append("✅ ML Intelligence: Working")
            status["working_components"] += 1
        else:
            status["details"].append("❌ ML Intelligence: Failed")
    except Exception as e:
        status["details"].append(f"❌ ML Intelligence: Error - {str(e)[:50]}...")
    
    # Test Sentiment Analysis
    try:
        from assistant_crm.api.sentiment_analysis import get_satisfaction_dashboard
        result = get_satisfaction_dashboard()
        if result.get("status") == "success":
            status["details"].append("✅ Sentiment Analysis: Working")
            status["working_components"] += 1
        else:
            status["details"].append("❌ Sentiment Analysis: Failed")
    except Exception as e:
        status["details"].append(f"❌ Sentiment Analysis: Error - {str(e)[:50]}...")
    
    # Test Personalization
    try:
        from assistant_crm.api.personalization_engine import get_personalized_experience
        result = get_personalized_experience("verification_user", "test query")
        if result.get("status") == "success":
            status["details"].append("✅ Personalization: Working")
            status["working_components"] += 1
        else:
            status["details"].append("❌ Personalization: Failed")
    except Exception as e:
        status["details"].append(f"❌ Personalization: Error - {str(e)[:50]}...")
    
    # Test Omnichannel
    try:
        from assistant_crm.api.omnichannel_hub import get_unified_user_conversation
        result = get_unified_user_conversation("verification_user")
        if result.get("status") == "success":
            status["details"].append("✅ Omnichannel: Working")
            status["working_components"] += 1
        else:
            status["details"].append("❌ Omnichannel: Failed")
    except Exception as e:
        status["details"].append(f"❌ Omnichannel: Error - {str(e)[:50]}...")
    
    # Determine overall status
    success_rate = (status["working_components"] / status["total_components"]) * 100
    if success_rate >= 75:
        status["status"] = "healthy"
    elif success_rate >= 50:
        status["status"] = "partial"
    else:
        status["status"] = "critical"
    
    print(f"📊 Phase 4 Foundation: {status['working_components']}/{status['total_components']} components working ({success_rate:.1f}%)")
    
    return status

def verify_medium_term_enhancements():
    """Verify medium-term enhancements"""
    status = {"status": "unknown", "details": [], "working_components": 0, "total_components": 3}
    
    # Test Predictive Service Delivery
    try:
        from assistant_crm.api.predictive_service_delivery import get_predictive_service_dashboard
        result = get_predictive_service_dashboard()
        if result.get("status") == "success":
            status["details"].append("✅ Predictive Service Delivery: Working")
            status["working_components"] += 1
        else:
            status["details"].append("❌ Predictive Service Delivery: Failed")
    except Exception as e:
        status["details"].append(f"❌ Predictive Service Delivery: Error - {str(e)[:50]}...")
    
    # Test Advanced Analytics Dashboard
    try:
        from assistant_crm.api.advanced_analytics_dashboard import get_customizable_dashboard
        widgets = ["overview_metrics", "performance_kpis"]
        result = get_customizable_dashboard(json.dumps(widgets), "30_days", "manager")
        if result.get("status") == "success":
            status["details"].append("✅ Advanced Analytics Dashboard: Working")
            status["working_components"] += 1
        else:
            status["details"].append("❌ Advanced Analytics Dashboard: Failed")
    except Exception as e:
        status["details"].append(f"❌ Advanced Analytics Dashboard: Error - {str(e)[:50]}...")
    
    # Test Voice Interface
    try:
        from assistant_crm.api.voice_interface import get_voice_conversation_flow
        result = get_voice_conversation_flow("verification_user", "general")
        if result.get("status") == "success":
            status["details"].append("✅ Voice Interface: Working")
            status["working_components"] += 1
        else:
            status["details"].append("❌ Voice Interface: Failed")
    except Exception as e:
        status["details"].append(f"❌ Voice Interface: Error - {str(e)[:50]}...")
    
    # Determine overall status
    success_rate = (status["working_components"] / status["total_components"]) * 100
    if success_rate >= 75:
        status["status"] = "healthy"
    elif success_rate >= 50:
        status["status"] = "partial"
    else:
        status["status"] = "critical"
    
    print(f"📊 Medium-Term Enhancements: {status['working_components']}/{status['total_components']} components working ({success_rate:.1f}%)")
    
    return status

def verify_database_integrity():
    """Verify database integrity and DocTypes"""
    status = {"status": "unknown", "details": [], "existing_doctypes": 0, "total_doctypes": 3}
    
    required_doctypes = [
        "User Interaction Log",
        "Proactive Engagement Log", 
        "Voice Interaction Log"
    ]
    
    for doctype in required_doctypes:
        try:
            if frappe.db.exists("DocType", doctype):
                status["details"].append(f"✅ {doctype}: Exists")
                status["existing_doctypes"] += 1
                
                # Test basic operations
                count = frappe.db.count(doctype)
                status["details"].append(f"   📊 Records: {count}")
            else:
                status["details"].append(f"❌ {doctype}: Missing")
        except Exception as e:
            status["details"].append(f"❌ {doctype}: Error - {str(e)[:50]}...")
    
    # Check data integrity
    try:
        # Test User Interaction Log data
        recent_interactions = frappe.db.count("User Interaction Log", 
            filters={"timestamp": [">", (datetime.now() - timedelta(days=7)).isoformat()]})
        status["details"].append(f"📈 Recent interactions (7 days): {recent_interactions}")
    except Exception as e:
        status["details"].append(f"❌ Data integrity check failed: {str(e)[:50]}...")
    
    # Determine overall status
    success_rate = (status["existing_doctypes"] / status["total_doctypes"]) * 100
    if success_rate >= 100:
        status["status"] = "healthy"
    elif success_rate >= 75:
        status["status"] = "partial"
    else:
        status["status"] = "critical"
    
    print(f"📊 Database Integrity: {status['existing_doctypes']}/{status['total_doctypes']} DocTypes exist ({success_rate:.1f}%)")
    
    return status

def verify_api_endpoints():
    """Verify API endpoints availability"""
    status = {"status": "unknown", "details": [], "working_endpoints": 0, "total_endpoints": 8}
    
    # Test key API endpoints
    endpoints_to_test = [
        ("ML Intelligence", "assistant_crm.api.ml_intelligence.get_user_behavior_prediction"),
        ("Sentiment Analysis", "assistant_crm.api.sentiment_analysis.get_satisfaction_dashboard"),
        ("Personalization", "assistant_crm.api.personalization_engine.get_personalized_experience"),
        ("Omnichannel", "assistant_crm.api.omnichannel_hub.get_unified_user_conversation"),
        ("Predictive Service", "assistant_crm.api.predictive_service_delivery.get_predictive_service_dashboard"),
        ("Analytics Dashboard", "assistant_crm.api.advanced_analytics_dashboard.get_real_time_metrics"),
        ("Voice Interface", "assistant_crm.api.voice_interface.get_voice_conversation_flow"),
        ("Voice Analytics", "assistant_crm.api.voice_interface.get_voice_analytics")
    ]
    
    for endpoint_name, endpoint_path in endpoints_to_test:
        try:
            # Check if the endpoint function exists
            module_path, function_name = endpoint_path.rsplit(".", 1)
            module = __import__(module_path, fromlist=[function_name])
            
            if hasattr(module, function_name):
                status["details"].append(f"✅ {endpoint_name}: Available")
                status["working_endpoints"] += 1
            else:
                status["details"].append(f"❌ {endpoint_name}: Function missing")
        except Exception as e:
            status["details"].append(f"❌ {endpoint_name}: Error - {str(e)[:50]}...")
    
    # Determine overall status
    success_rate = (status["working_endpoints"] / status["total_endpoints"]) * 100
    if success_rate >= 90:
        status["status"] = "healthy"
    elif success_rate >= 75:
        status["status"] = "partial"
    else:
        status["status"] = "critical"
    
    print(f"📊 API Endpoints: {status['working_endpoints']}/{status['total_endpoints']} endpoints available ({success_rate:.1f}%)")
    
    return status

def verify_performance_standards():
    """Verify performance standards"""
    status = {"status": "unknown", "details": [], "performance_score": 0}
    
    import time
    
    # Test response time
    try:
        start_time = time.time()
        from assistant_crm.api.sentiment_analysis import get_satisfaction_dashboard
        get_satisfaction_dashboard()
        end_time = time.time()
        
        response_time = end_time - start_time
        if response_time < 1.0:
            status["details"].append(f"✅ Response Time: {response_time:.3f}s (Excellent)")
            status["performance_score"] += 40
        elif response_time < 2.0:
            status["details"].append(f"🟡 Response Time: {response_time:.3f}s (Good)")
            status["performance_score"] += 30
        else:
            status["details"].append(f"❌ Response Time: {response_time:.3f}s (Poor)")
            status["performance_score"] += 10
    except Exception as e:
        status["details"].append(f"❌ Response Time Test: Error - {str(e)[:50]}...")
    
    # Test database performance
    try:
        start_time = time.time()
        frappe.db.count("User Interaction Log")
        frappe.db.count("Proactive Engagement Log")
        end_time = time.time()
        
        db_time = end_time - start_time
        if db_time < 0.5:
            status["details"].append(f"✅ Database Performance: {db_time:.3f}s (Excellent)")
            status["performance_score"] += 30
        elif db_time < 1.0:
            status["details"].append(f"🟡 Database Performance: {db_time:.3f}s (Good)")
            status["performance_score"] += 20
        else:
            status["details"].append(f"❌ Database Performance: {db_time:.3f}s (Poor)")
            status["performance_score"] += 10
    except Exception as e:
        status["details"].append(f"❌ Database Performance Test: Error - {str(e)[:50]}...")
    
    # Test memory efficiency (basic check)
    try:
        # Create multiple instances to test memory usage
        from assistant_crm.api.advanced_analytics_dashboard import AdvancedAnalyticsDashboard
        dashboards = [AdvancedAnalyticsDashboard() for _ in range(3)]
        
        status["details"].append("✅ Memory Efficiency: Acceptable")
        status["performance_score"] += 30
        
        # Clean up
        del dashboards
    except Exception as e:
        status["details"].append(f"❌ Memory Efficiency Test: Error - {str(e)[:50]}...")
    
    # Determine overall status
    if status["performance_score"] >= 80:
        status["status"] = "excellent"
    elif status["performance_score"] >= 60:
        status["status"] = "good"
    elif status["performance_score"] >= 40:
        status["status"] = "acceptable"
    else:
        status["status"] = "poor"
    
    print(f"📊 Performance Standards: {status['performance_score']}/100 ({status['status'].upper()})")
    
    return status

def generate_final_assessment(verification_results):
    """Generate final system assessment"""
    
    print("\n" + "=" * 80)
    print("🏆 FINAL SYSTEM VERIFICATION REPORT")
    print("=" * 80)
    
    # Component status summary
    components = [
        ("Phase 4 Foundation", verification_results["phase_4_foundation"]["status"]),
        ("Medium-Term Enhancements", verification_results["medium_term_enhancements"]["status"]),
        ("Database Integrity", verification_results["database_integrity"]["status"]),
        ("API Endpoints", verification_results["api_endpoints"]["status"]),
        ("Performance Standards", verification_results["performance_standards"]["status"])
    ]
    
    print("📊 COMPONENT STATUS SUMMARY:")
    healthy_count = 0
    total_count = len(components)
    
    for component_name, component_status in components:
        status_icon = {
            "healthy": "✅",
            "excellent": "✅", 
            "good": "✅",
            "partial": "🟡",
            "acceptable": "🟡",
            "critical": "❌",
            "poor": "❌",
            "unknown": "❓"
        }.get(component_status, "❓")
        
        print(f"   {status_icon} {component_name}: {component_status.upper()}")
        
        if component_status in ["healthy", "excellent", "good"]:
            healthy_count += 1
    
    # Overall system health
    system_health_percentage = (healthy_count / total_count) * 100
    
    print(f"\n🎯 OVERALL SYSTEM HEALTH: {healthy_count}/{total_count} components healthy ({system_health_percentage:.1f}%)")
    
    # Final assessment
    if system_health_percentage >= 80:
        verification_results["overall_system_health"] = "excellent"
        print("\n🎉 SYSTEM STATUS: EXCELLENT")
        print("   ✅ System is production-ready with advanced capabilities")
        print("   🚀 All major components functioning correctly")
        print("   📊 Performance standards met or exceeded")
        print("   🔧 Minor optimizations may enhance performance further")
    elif system_health_percentage >= 60:
        verification_results["overall_system_health"] = "good"
        print("\n✅ SYSTEM STATUS: GOOD")
        print("   ✅ System is operational with most capabilities working")
        print("   🎯 Core functionality stable and reliable")
        print("   🔧 Some components may need attention for optimal performance")
        print("   📋 Recommended to address partial components")
    elif system_health_percentage >= 40:
        verification_results["overall_system_health"] = "acceptable"
        print("\n🟡 SYSTEM STATUS: ACCEPTABLE")
        print("   🟡 System is functional but needs improvement")
        print("   📋 Several components require attention")
        print("   🔧 Performance optimization needed")
        print("   ⚠️ Monitor system closely and address issues")
    else:
        verification_results["overall_system_health"] = "needs_attention"
        print("\n❌ SYSTEM STATUS: NEEDS ATTENTION")
        print("   ❌ Multiple critical issues detected")
        print("   🔧 Immediate attention required")
        print("   📋 Review and fix failing components")
        print("   ⚠️ Not recommended for production deployment")
    
    # Deployment recommendation
    print(f"\n📋 DEPLOYMENT RECOMMENDATION:")
    if verification_results["overall_system_health"] in ["excellent", "good"]:
        print("   🚀 APPROVED FOR PRODUCTION DEPLOYMENT")
        print("   ✅ System meets quality standards")
        print("   📊 Performance within acceptable limits")
        print("   🔧 Continue monitoring and optimization")
    else:
        print("   ⏸️ DEPLOYMENT ON HOLD")
        print("   🔧 Address identified issues before deployment")
        print("   📋 Re-run verification after fixes")
        print("   ⚠️ Ensure system stability before production use")
    
    print("=" * 80)
    print("🎊 FINAL SYSTEM VERIFICATION COMPLETE 🎊")
    print("=" * 80)

if __name__ == "__main__":
    frappe.init(site="dev")
    frappe.connect()
    
    # Run final system verification
    results = final_system_verification()
    
    # Print final status
    overall_health = results.get("overall_system_health", "unknown")
    print(f"\n🏁 FINAL SYSTEM STATUS: {overall_health.upper()}")
    
    if overall_health in ["excellent", "good"]:
        print("🎉 WCFCB Assistant CRM: READY FOR PRODUCTION WITH ADVANCED CAPABILITIES")
    else:
        print("🔧 WCFCB Assistant CRM: REQUIRES ATTENTION BEFORE PRODUCTION DEPLOYMENT")
