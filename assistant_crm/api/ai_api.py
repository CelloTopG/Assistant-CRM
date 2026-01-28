# Copyright (c) 2024, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from typing import Dict, List, Any
import json


# ==================== AI MODEL TRAINING APIS ====================

@frappe.whitelist()
def train_contribution_forecasting_model() -> Dict[str, Any]:
    """Train contribution collection forecasting model"""
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()
        
        result = ai_service.train_contribution_forecasting_model()
        return result
        
    except Exception as e:
        frappe.log_error(f"Error training contribution forecasting model: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def train_compliance_risk_model() -> Dict[str, Any]:
    """Train compliance risk assessment model"""
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()
        
        result = ai_service.train_compliance_risk_model()
        return result
        
    except Exception as e:
        frappe.log_error(f"Error training compliance risk model: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def train_benefit_eligibility_model() -> Dict[str, Any]:
    """Train benefit eligibility prediction model"""
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()
        
        result = ai_service.train_benefit_eligibility_model()
        return result
        
    except Exception as e:
        frappe.log_error(f"Error training benefit eligibility model: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def train_anomaly_detection_model() -> Dict[str, Any]:
    """Train anomaly detection model for fraud prevention"""
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()
        
        result = ai_service.train_anomaly_detection_model()
        return result
        
    except Exception as e:
        frappe.log_error(f"Error training anomaly detection model: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def train_all_ai_models() -> Dict[str, Any]:
    """Train all AI models in sequence"""
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()
        
        results = {
            "contribution_forecasting": ai_service.train_contribution_forecasting_model(),
            "compliance_risk": ai_service.train_compliance_risk_model(),
            "benefit_eligibility": ai_service.train_benefit_eligibility_model(),
            "anomaly_detection": ai_service.train_anomaly_detection_model()
        }
        
        # Count successful trainings
        successful_trainings = sum(1 for result in results.values() if result.get("success", False))
        total_trainings = len(results)
        
        return {
            "success": True,
            "results": results,
            "summary": {
                "successful_trainings": successful_trainings,
                "total_trainings": total_trainings,
                "success_rate": (successful_trainings / total_trainings) * 100
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error training all AI models: {str(e)}")
        return {"success": False, "message": str(e)}


# ==================== AI PREDICTION APIS ====================

@frappe.whitelist()
def predict_contribution_collections(forecast_months: int = 12) -> Dict[str, Any]:
    """Predict future contribution collections"""
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()
        
        result = ai_service.predict_contribution_collections(forecast_months)
        return result
        
    except Exception as e:
        frappe.log_error(f"Error predicting contributions: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def assess_compliance_risk(employer_code: str) -> Dict[str, Any]:
    """Assess compliance risk for specific employer"""
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()
        
        result = ai_service.assess_compliance_risk(employer_code)
        return result
        
    except Exception as e:
        frappe.log_error(f"Error assessing compliance risk: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def predict_benefit_eligibility(employee_number: str) -> Dict[str, Any]:
    """Predict benefit eligibility for employee"""
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()
        
        result = ai_service.predict_benefit_eligibility(employee_number)
        return result
        
    except Exception as e:
        frappe.log_error(f"Error predicting benefit eligibility: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def analyze_stakeholder_behavior_patterns() -> Dict[str, Any]:
    """Analyze stakeholder behavior patterns"""
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()
        
        result = ai_service.analyze_stakeholder_behavior_patterns()
        return result
        
    except Exception as e:
        frappe.log_error(f"Error analyzing behavior patterns: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def predict_stakeholder_behavior(stakeholder_id: str, stakeholder_type: str) -> Dict[str, Any]:
    """Predict individual stakeholder behavior"""
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()
        
        result = ai_service.predict_stakeholder_behavior(stakeholder_id, stakeholder_type)
        return result
        
    except Exception as e:
        frappe.log_error(f"Error predicting stakeholder behavior: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def detect_anomalies(data_type: str = "recent") -> Dict[str, Any]:
    """Detect anomalies for fraud prevention"""
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()
        
        result = ai_service.detect_anomalies(data_type)
        return result
        
    except Exception as e:
        frappe.log_error(f"Error detecting anomalies: {str(e)}")
        return {"success": False, "message": str(e)}


# ==================== AI ANALYTICS APIS ====================

@frappe.whitelist()
def get_ai_model_performance() -> Dict[str, Any]:
    """Get performance metrics for all AI models"""
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()
        
        # Get model performance data
        performance_data = {
            "models": ai_service.model_performance,
            "available_models": list(ai_service.models.keys()),
            "last_updated": frappe.utils.now()
        }
        
        return {"success": True, "data": performance_data}
        
    except Exception as e:
        frappe.log_error(f"Error getting AI model performance: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_ai_insights_dashboard() -> Dict[str, Any]:
    """Get comprehensive AI insights dashboard"""
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()
        
        # Get various AI insights
        insights = {
            "contribution_forecast": ai_service.predict_contribution_collections(6),
            "recent_anomalies": ai_service.detect_anomalies("recent"),
            "behavior_patterns": ai_service.analyze_stakeholder_behavior_patterns(),
            "model_performance": ai_service.model_performance
        }
        
        # Calculate overall AI health score
        model_count = len(ai_service.models)
        trained_models = sum(1 for model in ai_service.models.values() if model is not None)
        ai_health_score = (trained_models / max(1, model_count)) * 100
        
        dashboard_data = {
            "insights": insights,
            "ai_health_score": ai_health_score,
            "trained_models": trained_models,
            "total_models": model_count,
            "generated_at": frappe.utils.now()
        }
        
        return {"success": True, "data": dashboard_data}
        
    except Exception as e:
        frappe.log_error(f"Error getting AI insights dashboard: {str(e)}")
        return {"success": False, "message": str(e)}


# ==================== BULK ANALYSIS APIS ====================

@frappe.whitelist()
def bulk_compliance_risk_assessment() -> Dict[str, Any]:
    """Perform bulk compliance risk assessment for all employers"""
    # NOTE: Employer Profile has been removed. Using ERPNext Customer instead.
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()

        # Get all Customers (Employers) using ERPNext Customer doctype
        employers = frappe.get_all(
            "Customer",
            filters={"customer_type": "Company", "disabled": 0},
            fields=["name", "customer_name"]
        )

        risk_assessments = []
        high_risk_count = 0

        for employer in employers:
            try:
                assessment = ai_service.assess_compliance_risk(employer["name"])
                if assessment.get("success"):
                    risk_data = assessment["risk_assessment"]
                    risk_assessments.append({
                        "employer_code": employer["name"],
                        "employer_name": employer["customer_name"],
                        "risk_level": risk_data["risk_level"],
                        "risk_probability": risk_data["risk_probability"]
                    })

                    if risk_data["risk_level"] == "High":
                        high_risk_count += 1

            except Exception as e:
                frappe.log_error(f"Error assessing risk for {employer['name']}: {str(e)}")
                continue

        return {
            "success": True,
            "data": {
                "assessments": risk_assessments,
                "total_assessed": len(risk_assessments),
                "high_risk_employers": high_risk_count,
                "risk_rate": (high_risk_count / len(risk_assessments) * 100) if risk_assessments else 0
            }
        }

    except Exception as e:
        frappe.log_error(f"Error in bulk compliance assessment: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def bulk_benefit_eligibility_prediction() -> Dict[str, Any]:
    """Perform bulk benefit eligibility prediction for all employees

    NOTE: Employee Profile has been removed. Using ERPNext Employee instead.
    """
    try:
        from assistant_crm.services.advanced_ai_service import AdvancedAIService
        ai_service = AdvancedAIService()

        # Get all active employees using ERPNext Employee doctype
        employees = frappe.get_all(
            "Employee",
            filters={"status": "Active"},
            fields=["name", "employee_name"]
        )

        eligibility_predictions = []
        eligible_count = 0

        for employee in employees:
            try:
                prediction = ai_service.predict_benefit_eligibility(employee["name"])
                if prediction.get("success"):
                    eligibility_data = prediction["eligibility_prediction"]
                    eligibility_predictions.append({
                        "employee_number": employee["name"],
                        "employee_name": employee["employee_name"],
                        "eligibility_status": eligibility_data["status"],
                        "confidence": eligibility_data["confidence"]
                    })

                    if eligibility_data["status"] == "Eligible":
                        eligible_count += 1

            except Exception as e:
                frappe.log_error(f"Error predicting eligibility for {employee['name']}: {str(e)}")
                continue

        return {
            "success": True,
            "data": {
                "predictions": eligibility_predictions,
                "total_predicted": len(eligibility_predictions),
                "eligible_employees": eligible_count,
                "eligibility_rate": (eligible_count / len(eligibility_predictions) * 100) if eligibility_predictions else 0
            }
        }

    except Exception as e:
        frappe.log_error(f"Error in bulk eligibility prediction: {str(e)}")
        return {"success": False, "message": str(e)}
