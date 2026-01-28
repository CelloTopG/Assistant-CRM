#!/usr/bin/env python3
"""
WCFCB Assistant CRM - ML DocType Enhancements
Adds ML-related fields to existing DocTypes without breaking functionality
"""

import frappe
from frappe import _

def enhance_escalation_workflow_with_ml():
    """Add ML fields to Escalation Workflow DocType"""
    try:
        # Get the existing DocType
        doctype = frappe.get_doc("DocType", "Escalation Workflow")
        
        # Check if ML fields already exist
        existing_fields = [field.fieldname for field in doctype.fields]
        
        ml_fields = [
            {
                "fieldname": "ml_section",
                "fieldtype": "Section Break",
                "label": "ML Intelligence Data",
                "collapsible": 1
            },
            {
                "fieldname": "ml_escalation_probability",
                "fieldtype": "Float",
                "label": "ML Escalation Probability",
                "precision": 3,
                "description": "Machine learning predicted escalation probability (0.0-1.0)"
            },
            {
                "fieldname": "ml_recommendation",
                "fieldtype": "Select",
                "label": "ML Recommendation",
                "options": "immediate_escalation\nprepare_escalation\nmonitor_closely\nstandard_handling",
                "description": "ML-generated escalation recommendation"
            },
            {
                "fieldname": "ml_confidence_adjustment",
                "fieldtype": "Float",
                "label": "ML Confidence Adjustment",
                "precision": 3,
                "description": "ML adjustment to original confidence score"
            },
            {
                "fieldname": "ml_suggested_department",
                "fieldtype": "Data",
                "label": "ML Suggested Department",
                "description": "ML-suggested optimal department for handling"
            },
            {
                "fieldname": "ml_user_behavior_score",
                "fieldtype": "Float",
                "label": "User Behavior Score",
                "precision": 3,
                "description": "ML-calculated user behavior risk score"
            },
            {
                "fieldname": "ml_prediction_accuracy",
                "fieldtype": "Float",
                "label": "Prediction Accuracy",
                "precision": 3,
                "description": "Accuracy of ML prediction (for learning)"
            }
        ]
        
        # Add new fields that don't exist
        fields_added = 0
        for field_data in ml_fields:
            if field_data["fieldname"] not in existing_fields:
                doctype.append("fields", field_data)
                fields_added += 1
        
        if fields_added > 0:
            doctype.save()
            frappe.db.commit()
            print(f"✅ Added {fields_added} ML fields to Escalation Workflow")
        else:
            print("✅ ML fields already exist in Escalation Workflow")
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Escalation Workflow ML Enhancement Error: {str(e)}")
        print(f"❌ Failed to enhance Escalation Workflow: {str(e)}")
        return False

def enhance_user_interaction_log_with_ml():
    """Add ML fields to User Interaction Log DocType"""
    try:
        # Get the existing DocType
        doctype = frappe.get_doc("DocType", "User Interaction Log")
        
        # Check if ML fields already exist
        existing_fields = [field.fieldname for field in doctype.fields]
        
        ml_fields = [
            {
                "fieldname": "ml_analytics_section",
                "fieldtype": "Section Break",
                "label": "ML Analytics",
                "collapsible": 1
            },
            {
                "fieldname": "ml_enhanced_confidence",
                "fieldtype": "Float",
                "label": "ML Enhanced Confidence",
                "precision": 3,
                "description": "ML-enhanced confidence score"
            },
            {
                "fieldname": "ml_sentiment_score",
                "fieldtype": "Float",
                "label": "Sentiment Score",
                "precision": 3,
                "description": "ML-detected sentiment score (-1.0 to 1.0)"
            },
            {
                "fieldname": "ml_emotion_detected",
                "fieldtype": "Select",
                "label": "Detected Emotion",
                "options": "neutral\npositive\nnegative\nfrustrated\nsatisfied\nconfused\nurgent",
                "description": "ML-detected user emotion"
            },
            {
                "fieldname": "ml_user_intent_prediction",
                "fieldtype": "Data",
                "label": "Predicted User Intent",
                "description": "ML-predicted user intent"
            },
            {
                "fieldname": "ml_personalization_data",
                "fieldtype": "Long Text",
                "label": "Personalization Data",
                "description": "JSON data for personalization (user preferences, behavior patterns)"
            },
            {
                "fieldname": "ml_journey_stage",
                "fieldtype": "Select",
                "label": "Journey Stage",
                "options": "discovery\ninformation_gathering\nproblem_solving\nescalation\nresolution\nfollow_up",
                "description": "ML-identified stage in user journey"
            }
        ]
        
        # Add new fields that don't exist
        fields_added = 0
        for field_data in ml_fields:
            if field_data["fieldname"] not in existing_fields:
                doctype.append("fields", field_data)
                fields_added += 1
        
        if fields_added > 0:
            doctype.save()
            frappe.db.commit()
            print(f"✅ Added {fields_added} ML fields to User Interaction Log")
        else:
            print("✅ ML fields already exist in User Interaction Log")
        
        return True
        
    except Exception as e:
        frappe.log_error(f"User Interaction Log ML Enhancement Error: {str(e)}")
        print(f"❌ Failed to enhance User Interaction Log: {str(e)}")
        return False

def create_ml_user_profile_doctype():
    """Create ML User Profile DocType for storing user behavior data"""
    try:
        # Check if DocType already exists
        if frappe.db.exists("DocType", "ML User Profile"):
            print("✅ ML User Profile DocType already exists")
            return True
        
        # Create new DocType
        doctype = frappe.new_doc("DocType")
        doctype.name = "ML User Profile"
        doctype.module = "Assistant CRM"
        doctype.custom = 1
        doctype.is_submittable = 0
        doctype.track_changes = 1
        doctype.autoname = "field:user_id"
        
        # Add fields
        fields = [
            {
                "fieldname": "user_id",
                "fieldtype": "Data",
                "label": "User ID",
                "reqd": 1,
                "unique": 1
            },
            {
                "fieldname": "profile_section",
                "fieldtype": "Section Break",
                "label": "User Profile"
            },
            {
                "fieldname": "first_interaction",
                "fieldtype": "Datetime",
                "label": "First Interaction"
            },
            {
                "fieldname": "last_interaction",
                "fieldtype": "Datetime",
                "label": "Last Interaction"
            },
            {
                "fieldname": "total_interactions",
                "fieldtype": "Int",
                "label": "Total Interactions",
                "default": 0
            },
            {
                "fieldname": "language_preference",
                "fieldtype": "Select",
                "label": "Language Preference",
                "options": "en\nes\nfr\nbem\nny\nto"
            },
            {
                "fieldname": "behavior_section",
                "fieldtype": "Section Break",
                "label": "Behavior Analysis"
            },
            {
                "fieldname": "query_frequency_pattern",
                "fieldtype": "Select",
                "label": "Query Frequency Pattern",
                "options": "very_high\nhigh\nmedium\nlow\nirregular"
            },
            {
                "fieldname": "preferred_topics",
                "fieldtype": "Long Text",
                "label": "Preferred Topics (JSON)",
                "description": "JSON array of preferred topics"
            },
            {
                "fieldname": "satisfaction_average",
                "fieldtype": "Float",
                "label": "Average Satisfaction",
                "precision": 2
            },
            {
                "fieldname": "escalation_tendency",
                "fieldtype": "Float",
                "label": "Escalation Tendency",
                "precision": 3,
                "description": "Probability of requiring escalation (0.0-1.0)"
            },
            {
                "fieldname": "predictions_section",
                "fieldtype": "Section Break",
                "label": "ML Predictions"
            },
            {
                "fieldname": "next_likely_query",
                "fieldtype": "Data",
                "label": "Next Likely Query"
            },
            {
                "fieldname": "optimal_response_style",
                "fieldtype": "Select",
                "label": "Optimal Response Style",
                "options": "concise\ndetailed\nstep_by_step\nvisual\ntechnical\nsimple"
            },
            {
                "fieldname": "peak_interaction_hours",
                "fieldtype": "Data",
                "label": "Peak Interaction Hours",
                "description": "Comma-separated hours (0-23)"
            },
            {
                "fieldname": "ml_confidence_score",
                "fieldtype": "Float",
                "label": "ML Confidence Score",
                "precision": 3,
                "description": "Confidence in ML predictions for this user"
            },
            {
                "fieldname": "metadata_section",
                "fieldtype": "Section Break",
                "label": "Metadata"
            },
            {
                "fieldname": "profile_last_updated",
                "fieldtype": "Datetime",
                "label": "Profile Last Updated"
            },
            {
                "fieldname": "ml_model_version",
                "fieldtype": "Data",
                "label": "ML Model Version",
                "description": "Version of ML model used for predictions"
            }
        ]
        
        for field in fields:
            doctype.append("fields", field)
        
        # Add permissions
        doctype.append("permissions", {
            "role": "System Manager",
            "read": 1,
            "write": 1,
            "create": 1,
            "delete": 1
        })
        
        doctype.append("permissions", {
            "role": "Assistant CRM User",
            "read": 1,
            "write": 0,
            "create": 0,
            "delete": 0
        })
        
        doctype.insert()
        frappe.db.commit()
        print("✅ Created ML User Profile DocType")
        return True
        
    except Exception as e:
        frappe.log_error(f"ML User Profile Creation Error: {str(e)}")
        print(f"❌ Failed to create ML User Profile DocType: {str(e)}")
        return False

def execute_all_ml_enhancements():
    """Execute all ML DocType enhancements"""
    print("🤖 EXECUTING ML DOCTYPE ENHANCEMENTS")
    print("=" * 50)
    
    results = {
        "escalation_workflow": enhance_escalation_workflow_with_ml(),
        "user_interaction_log": enhance_user_interaction_log_with_ml(),
        "ml_user_profile": create_ml_user_profile_doctype()
    }
    
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    print(f"\n📊 ML Enhancement Results: {success_count}/{total_count} successful")
    
    if success_count == total_count:
        print("🎉 All ML DocType enhancements completed successfully!")
        return True
    else:
        print("⚠️ Some ML enhancements failed. Check logs for details.")
        return False

if __name__ == "__main__":
    frappe.init(site="dev")
    frappe.connect()
    execute_all_ml_enhancements()
