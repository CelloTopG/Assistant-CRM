import frappe
from frappe import _
from datetime import datetime

@frappe.whitelist(allow_guest=True)
def trigger_escalation(query_id, user_id, query_text, confidence_score, escalation_reason="low_confidence"):
    """Trigger escalation workflow for a query with ML enhancement"""

    try:
        # Get ML-enhanced escalation prediction
        ml_prediction = get_ml_escalation_enhancement(query_text, user_id, confidence_score)

        # Determine escalation type and priority (enhanced with ML)
        escalation_type = determine_escalation_type(confidence_score, ml_prediction)
        priority_level = determine_priority_level_enhanced(query_text, escalation_reason, ml_prediction)
        department = determine_department_enhanced(query_text, ml_prediction)
        
        # Create escalation workflow record
        escalation = frappe.new_doc("Escalation Workflow")
        escalation.query_id = query_id
        escalation.user_id = user_id
        escalation.query_text = query_text
        escalation.confidence_score = float(confidence_score)
        escalation.escalation_reason = escalation_reason
        escalation.escalation_type = escalation_type
        escalation.priority_level = priority_level
        escalation.department = department
        escalation.status = "pending"
        escalation.escalation_date = frappe.utils.now()

        # Add ML prediction data
        if ml_prediction.get("status") == "success":
            escalation.ml_escalation_probability = ml_prediction.get("escalation_prediction", {}).get("escalation_probability", 0)
            escalation.ml_recommendation = ml_prediction.get("escalation_prediction", {}).get("recommendation", "standard_handling")

        escalation.insert()
        frappe.db.commit()

        return {
            "status": "success",
            "escalation_id": escalation.name,
            "department": department,
            "priority": priority_level,
            "estimated_response_time": get_estimated_response_time(priority_level),
            "ml_enhancement": ml_prediction.get("escalation_prediction", {}),
            "confidence_improvement": ml_prediction.get("enhancement", {}).get("confidence_adjustment", 0)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to trigger escalation",
            "details": str(e)
        }

def determine_priority_level(query_text, escalation_reason):
    """Determine priority level based on query content"""
    
    high_priority = ["emergency", "urgent", "legal", "lawsuit"]
    medium_priority = ["medical", "claim denied", "payment issue"]
    
    query_lower = query_text.lower()
    
    if any(keyword in query_lower for keyword in high_priority):
        return "urgent"
    elif any(keyword in query_lower for keyword in medium_priority):
        return "high"
    elif escalation_reason == "low_confidence":
        return "medium"
    else:
        return "low"

def determine_department(query_text):
    """Determine which department should handle the escalation"""
    
    query_lower = query_text.lower()
    
    if any(keyword in query_lower for keyword in ["legal", "lawsuit", "attorney"]):
        return "legal"
    elif any(keyword in query_lower for keyword in ["medical", "doctor", "hospital"]):
        return "medical"
    elif any(keyword in query_lower for keyword in ["system", "login", "website"]):
        return "technical"
    else:
        return "claims"

def get_estimated_response_time(priority_level):
    """Get estimated response time based on priority"""
    
    response_times = {
        "urgent": "1 hour",
        "high": "4 hours", 
        "medium": "24 hours",
        "low": "48 hours"
    }
    
    return response_times.get(priority_level, "48 hours")

# ML Enhancement Functions

def get_ml_escalation_enhancement(query_text, user_id, confidence_score):
    """Get ML enhancement for escalation decision"""
    try:
        # Import ML intelligence (avoid circular imports)
        from assistant_crm.api.ml_intelligence import get_ml_enhanced_escalation_prediction, enhance_query_intelligence

        # Get ML-enhanced escalation prediction
        escalation_prediction = get_ml_enhanced_escalation_prediction(query_text, user_id, confidence_score)

        # Get query intelligence enhancement
        query_enhancement = enhance_query_intelligence(query_text, user_id, confidence_score)

        return {
            "status": "success",
            "escalation_prediction": escalation_prediction.get("escalation_prediction", {}),
            "enhancement": query_enhancement.get("enhancement", {}),
            "user_context": query_enhancement.get("user_context", {}),
            "recommendations": query_enhancement.get("recommendations", [])
        }

    except Exception as e:
        frappe.log_error(f"ML Enhancement Error: {str(e)}")
        return {
            "status": "error",
            "message": "ML enhancement unavailable",
            "details": str(e)
        }

def determine_escalation_type(confidence_score, ml_prediction):
    """Determine escalation type with ML enhancement"""
    base_type = "automatic" if float(confidence_score) < 0.6 else "manual"

    # Enhance with ML prediction
    if ml_prediction.get("status") == "success":
        ml_recommendation = ml_prediction.get("escalation_prediction", {}).get("recommendation", "standard_handling")

        if ml_recommendation == "immediate_escalation":
            return "automatic"
        elif ml_recommendation == "prepare_escalation":
            return "automatic" if float(confidence_score) < 0.7 else "manual"

    return base_type

def determine_priority_level_enhanced(query_text, escalation_reason, ml_prediction):
    """Determine priority level with ML enhancement"""
    # Get base priority
    base_priority = determine_priority_level(query_text, escalation_reason)

    # Enhance with ML prediction
    if ml_prediction.get("status") == "success":
        escalation_probability = ml_prediction.get("escalation_prediction", {}).get("escalation_probability", 0)

        # Adjust priority based on ML prediction
        if escalation_probability > 0.8:
            if base_priority == "low":
                return "medium"
            elif base_priority == "medium":
                return "high"
        elif escalation_probability > 0.6:
            if base_priority == "low":
                return "medium"

    return base_priority

def determine_department_enhanced(query_text, ml_prediction):
    """Determine department with ML enhancement"""
    # Get base department
    base_department = determine_department(query_text)

    # Enhance with ML prediction if available
    if ml_prediction.get("status") == "success":
        suggested_dept = ml_prediction.get("escalation_prediction", {}).get("suggested_department")
        if suggested_dept:
            return suggested_dept

    return base_department

@frappe.whitelist(allow_guest=True)
def create_escalation(query_id=None, user_id=None, query_text=None, confidence_score=0.5, escalation_reason="low_confidence"):
    """Create escalation - wrapper for trigger_escalation for API compatibility"""
    return trigger_escalation(query_id, user_id, query_text, confidence_score, escalation_reason)

@frappe.whitelist()
def get_escalation_analytics():
    """Get escalation analytics with ML insights"""
    try:
        # Get recent escalations
        escalations = frappe.get_all("Escalation Workflow",
            filters={"escalation_date": [">", (datetime.now() - frappe.utils.timedelta(days=30)).isoformat()]},
            fields=["*"]
        )

        # Calculate analytics
        total_escalations = len(escalations)
        ml_enhanced = len([e for e in escalations if getattr(e, 'ml_escalation_probability', None)])

        analytics = {
            "total_escalations": total_escalations,
            "ml_enhanced_escalations": ml_enhanced,
            "ml_enhancement_rate": (ml_enhanced / total_escalations * 100) if total_escalations > 0 else 0,
            "average_ml_probability": sum([getattr(e, 'ml_escalation_probability', 0) for e in escalations]) / total_escalations if total_escalations > 0 else 0,
            "department_distribution": calculate_department_distribution(escalations),
            "priority_distribution": calculate_priority_distribution(escalations),
            "resolution_times": calculate_resolution_times(escalations)
        }

        return {
            "status": "success",
            "analytics": analytics,
            "period": "last_30_days",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to generate escalation analytics",
            "details": str(e)
        }

def calculate_department_distribution(escalations):
    """Calculate distribution of escalations by department"""
    dept_counts = {}
    for escalation in escalations:
        dept = escalation.department or "unknown"
        dept_counts[dept] = dept_counts.get(dept, 0) + 1
    return dept_counts

def calculate_priority_distribution(escalations):
    """Calculate distribution of escalations by priority"""
    priority_counts = {}
    for escalation in escalations:
        priority = escalation.priority_level or "unknown"
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    return priority_counts

def calculate_resolution_times(escalations):
    """Calculate average resolution times"""
    resolved = [e for e in escalations if e.status == "resolved" and e.resolution_date]

    if not resolved:
        return {"average_hours": 0, "resolved_count": 0}

    total_hours = 0
    for escalation in resolved:
        escalation_time = frappe.utils.get_datetime(escalation.escalation_date)
        resolution_time = frappe.utils.get_datetime(escalation.resolution_date)
        hours = (resolution_time - escalation_time).total_seconds() / 3600
        total_hours += hours

    return {
        "average_hours": total_hours / len(resolved),
        "resolved_count": len(resolved),
        "total_escalations": len(escalations)
    }
