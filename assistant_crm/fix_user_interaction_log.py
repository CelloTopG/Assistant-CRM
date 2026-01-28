#!/usr/bin/env python3
"""
Fix User Interaction Log DocType - Create if missing
"""

import frappe
from frappe import _

def fix_user_interaction_log():
    """Fix or create User Interaction Log DocType"""
    
    print("🔧 FIXING USER INTERACTION LOG DOCTYPE")
    print("=" * 50)
    
    try:
        # Check if DocType exists
        if frappe.db.exists("DocType", "User Interaction Log"):
            print("✅ User Interaction Log DocType exists")
            
            # Check if it has the required fields
            meta = frappe.get_meta("User Interaction Log")
            existing_fields = [field.fieldname for field in meta.fields]
            
            required_fields = [
                "user_id", "query_text", "response_provided", "timestamp", 
                "session_id", "confidence_score", "satisfaction_rating",
                "ml_sentiment_score", "ml_emotion_detected"
            ]
            
            missing_fields = [field for field in required_fields if field not in existing_fields]
            
            if missing_fields:
                print(f"⚠️ Missing fields: {missing_fields}")
                add_missing_fields(missing_fields)
            else:
                print("✅ All required fields present")
            
        else:
            print("❌ User Interaction Log DocType does not exist - creating it")
            create_user_interaction_log_doctype()
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing User Interaction Log: {str(e)}")
        return False

def create_user_interaction_log_doctype():
    """Create User Interaction Log DocType"""
    
    try:
        doctype = frappe.new_doc("DocType")
        doctype.name = "User Interaction Log"
        doctype.module = "Assistant CRM"
        doctype.custom = 1
        doctype.is_submittable = 0
        doctype.track_changes = 1
        doctype.autoname = "naming_series:"
        
        # Add fields
        fields = [
            {
                "fieldname": "naming_series",
                "fieldtype": "Select",
                "label": "Naming Series",
                "options": "UIL-.YYYY.-.#####",
                "reqd": 1
            },
            {
                "fieldname": "user_id",
                "fieldtype": "Data",
                "label": "User ID",
                "reqd": 1
            },
            {
                "fieldname": "session_id",
                "fieldtype": "Data",
                "label": "Session ID"
            },
            {
                "fieldname": "query_text",
                "fieldtype": "Long Text",
                "label": "Query Text"
            },
            {
                "fieldname": "response_provided",
                "fieldtype": "Long Text",
                "label": "Response Provided"
            },
            {
                "fieldname": "confidence_score",
                "fieldtype": "Float",
                "label": "Confidence Score",
                "precision": 3
            },
            {
                "fieldname": "satisfaction_rating",
                "fieldtype": "Int",
                "label": "Satisfaction Rating",
                "description": "User satisfaction rating (1-5 scale)"
            },
            {
                "fieldname": "timestamp",
                "fieldtype": "Datetime",
                "label": "Timestamp",
                "reqd": 1
            },
            {
                "fieldname": "language",
                "fieldtype": "Select",
                "label": "Language",
                "options": "en\nes\nfr\nbem\nny\nto"
            },
            {
                "fieldname": "escalated",
                "fieldtype": "Check",
                "label": "Escalated"
            },
            # ML and Sentiment Analysis Fields
            {
                "fieldname": "ml_section",
                "fieldtype": "Section Break",
                "label": "ML Analytics",
                "collapsible": 1
            },
            {
                "fieldname": "ml_sentiment_score",
                "fieldtype": "Float",
                "label": "ML Sentiment Score",
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
                "fieldname": "ml_enhanced_confidence",
                "fieldtype": "Float",
                "label": "ML Enhanced Confidence",
                "precision": 3,
                "description": "ML-enhanced confidence score"
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
                "description": "JSON data for personalization"
            },
            {
                "fieldname": "ml_journey_stage",
                "fieldtype": "Select",
                "label": "Journey Stage",
                "options": "discovery\ninformation_gathering\nproblem_solving\nescalation\nresolution\nfollow_up",
                "description": "ML-identified stage in user journey"
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
            "write": 1,
            "create": 1,
            "delete": 0
        })
        
        doctype.insert()
        frappe.db.commit()
        print("✅ User Interaction Log DocType created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create User Interaction Log DocType: {str(e)}")
        return False

def add_missing_fields(missing_fields):
    """Add missing fields to existing DocType"""
    
    try:
        doctype = frappe.get_doc("DocType", "User Interaction Log")
        
        field_definitions = {
            "satisfaction_rating": {
                "fieldname": "satisfaction_rating",
                "fieldtype": "Int",
                "label": "Satisfaction Rating",
                "description": "User satisfaction rating (1-5 scale)"
            },
            "ml_sentiment_score": {
                "fieldname": "ml_sentiment_score",
                "fieldtype": "Float",
                "label": "ML Sentiment Score",
                "precision": 3,
                "description": "ML-detected sentiment score (-1.0 to 1.0)"
            },
            "ml_emotion_detected": {
                "fieldname": "ml_emotion_detected",
                "fieldtype": "Select",
                "label": "Detected Emotion",
                "options": "neutral\npositive\nnegative\nfrustrated\nsatisfied\nconfused\nurgent",
                "description": "ML-detected user emotion"
            }
        }
        
        fields_added = 0
        for field_name in missing_fields:
            if field_name in field_definitions:
                doctype.append("fields", field_definitions[field_name])
                fields_added += 1
                print(f"✅ Added field: {field_name}")
        
        if fields_added > 0:
            doctype.save()
            frappe.db.commit()
            print(f"✅ Added {fields_added} missing fields")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to add missing fields: {str(e)}")
        return False

def create_sample_interaction_data():
    """Create sample interaction data for testing"""
    
    try:
        print("\n📝 Creating sample interaction data...")
        
        sample_interactions = [
            {
                "user_id": "test_user_001",
                "query_text": "I'm very satisfied with the excellent service provided",
                "response_provided": "Thank you for your positive feedback! We're glad we could help.",
                "satisfaction_rating": 5,
                "ml_sentiment_score": 0.8,
                "ml_emotion_detected": "satisfied"
            },
            {
                "user_id": "test_user_002",
                "query_text": "I'm frustrated with this slow response time",
                "response_provided": "I apologize for the delay. Let me help you immediately.",
                "satisfaction_rating": 2,
                "ml_sentiment_score": -0.6,
                "ml_emotion_detected": "frustrated"
            },
            {
                "user_id": "test_user_003",
                "query_text": "Can you help me check my workers compensation claim status?",
                "response_provided": "I'll check your claim status right away. Please provide your claim number.",
                "satisfaction_rating": 4,
                "ml_sentiment_score": 0.2,
                "ml_emotion_detected": "neutral"
            },
            {
                "user_id": "test_user_004",
                "query_text": "This is urgent! I need immediate help with my denied claim",
                "response_provided": "I understand this is urgent. Let me escalate this to our claims specialist immediately.",
                "satisfaction_rating": 3,
                "ml_sentiment_score": -0.3,
                "ml_emotion_detected": "urgent"
            },
            {
                "user_id": "test_user_005",
                "query_text": "Thank you for the quick and helpful response",
                "response_provided": "You're welcome! I'm here to help whenever you need assistance.",
                "satisfaction_rating": 5,
                "ml_sentiment_score": 0.7,
                "ml_emotion_detected": "satisfied"
            }
        ]
        
        created_count = 0
        for data in sample_interactions:
            try:
                interaction = frappe.new_doc("User Interaction Log")
                interaction.user_id = data["user_id"]
                interaction.query_text = data["query_text"]
                interaction.response_provided = data["response_provided"]
                interaction.satisfaction_rating = data["satisfaction_rating"]
                interaction.ml_sentiment_score = data["ml_sentiment_score"]
                interaction.ml_emotion_detected = data["ml_emotion_detected"]
                interaction.timestamp = frappe.utils.now()
                interaction.session_id = f"test_session_{created_count + 1}"
                interaction.confidence_score = 0.8
                interaction.language = "en"
                
                interaction.insert()
                created_count += 1
                
            except Exception as e:
                print(f"❌ Failed to create interaction {created_count + 1}: {str(e)}")
        
        if created_count > 0:
            frappe.db.commit()
            print(f"✅ Created {created_count} sample interactions")
        
        return created_count
        
    except Exception as e:
        print(f"❌ Error creating sample data: {str(e)}")
        return 0

def test_satisfaction_dashboard_after_fix():
    """Test satisfaction dashboard after fix"""
    
    print("\n🧪 Testing satisfaction dashboard after fix...")
    
    try:
        from assistant_crm.api.sentiment_analysis import get_satisfaction_dashboard
        
        result = get_satisfaction_dashboard()
        
        if result.get("status") == "success":
            print("✅ Satisfaction dashboard test: PASSED")
            dashboard_data = result.get("dashboard_data", {})
            print(f"   📊 Total Interactions: {dashboard_data.get('total_interactions', 0)}")
            print(f"   🎭 Average Sentiment: {dashboard_data.get('average_sentiment', 0)}")
            print(f"   📈 Data Quality: {dashboard_data.get('data_quality', {})}")
            return True
        else:
            print(f"❌ Satisfaction dashboard test: FAILED")
            print(f"   Error: {result.get('message', 'Unknown error')}")
            print(f"   Details: {result.get('details', 'No details')}")
            return False
            
    except Exception as e:
        print(f"❌ Satisfaction dashboard test: ERROR - {str(e)}")
        return False

def create_proactive_engagement_log_doctype():
    """Create Proactive Engagement Log DocType for predictive service delivery"""

    try:
        if frappe.db.exists("DocType", "Proactive Engagement Log"):
            print("✅ Proactive Engagement Log DocType already exists")
            return True

        doctype = frappe.new_doc("DocType")
        doctype.name = "Proactive Engagement Log"
        doctype.module = "Assistant CRM"
        doctype.custom = 1
        doctype.is_submittable = 0
        doctype.track_changes = 1
        doctype.autoname = "naming_series:"

        # Add fields
        fields = [
            {
                "fieldname": "naming_series",
                "fieldtype": "Select",
                "label": "Naming Series",
                "options": "PEL-.YYYY.-.#####",
                "reqd": 1
            },
            {
                "fieldname": "user_id",
                "fieldtype": "Data",
                "label": "User ID",
                "reqd": 1
            },
            {
                "fieldname": "engagement_type",
                "fieldtype": "Select",
                "label": "Engagement Type",
                "options": "proactive_check_in\nescalation_prevention\nclaim_status_update\ndeadline_reminder\neducational_content\nother",
                "reqd": 1
            },
            {
                "fieldname": "message_content",
                "fieldtype": "Long Text",
                "label": "Message Content"
            },
            {
                "fieldname": "priority",
                "fieldtype": "Select",
                "label": "Priority",
                "options": "low\nmedium\nhigh\ncritical",
                "default": "medium"
            },
            {
                "fieldname": "confidence_score",
                "fieldtype": "Float",
                "label": "Confidence Score",
                "precision": 3
            },
            {
                "fieldname": "status",
                "fieldtype": "Select",
                "label": "Status",
                "options": "pending\nexecuted\nsuccessful\nfailed\ncancelled",
                "default": "pending"
            },
            {
                "fieldname": "execution_timestamp",
                "fieldtype": "Datetime",
                "label": "Execution Timestamp"
            },
            {
                "fieldname": "predicted_response_time",
                "fieldtype": "Int",
                "label": "Predicted Response Time (hours)"
            },
            {
                "fieldname": "execution_result",
                "fieldtype": "Long Text",
                "label": "Execution Result"
            },
            {
                "fieldname": "user_response",
                "fieldtype": "Long Text",
                "label": "User Response"
            },
            {
                "fieldname": "effectiveness_score",
                "fieldtype": "Float",
                "label": "Effectiveness Score",
                "precision": 3
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
            "write": 1,
            "create": 1,
            "delete": 0
        })

        doctype.insert()
        frappe.db.commit()
        print("✅ Proactive Engagement Log DocType created successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to create Proactive Engagement Log DocType: {str(e)}")
        return False

def create_voice_interaction_log_doctype():
    """Create Voice Interaction Log DocType for voice interface"""

    try:
        if frappe.db.exists("DocType", "Voice Interaction Log"):
            print("✅ Voice Interaction Log DocType already exists")
            return True

        doctype = frappe.new_doc("DocType")
        doctype.name = "Voice Interaction Log"
        doctype.module = "Assistant CRM"
        doctype.custom = 1
        doctype.is_submittable = 0
        doctype.track_changes = 1
        doctype.autoname = "naming_series:"

        # Add fields
        fields = [
            {
                "fieldname": "naming_series",
                "fieldtype": "Select",
                "label": "Naming Series",
                "options": "VIL-.YYYY.-.#####",
                "reqd": 1
            },
            {
                "fieldname": "user_id",
                "fieldtype": "Data",
                "label": "User ID",
                "reqd": 1
            },
            {
                "fieldname": "session_id",
                "fieldtype": "Data",
                "label": "Session ID"
            },
            {
                "fieldname": "transcribed_text",
                "fieldtype": "Long Text",
                "label": "Transcribed Text"
            },
            {
                "fieldname": "transcription_confidence",
                "fieldtype": "Float",
                "label": "Transcription Confidence",
                "precision": 3
            },
            {
                "fieldname": "language",
                "fieldtype": "Select",
                "label": "Language",
                "options": "en\nes\nfr\nbem\nny\nto"
            },
            {
                "fieldname": "audio_duration",
                "fieldtype": "Float",
                "label": "Audio Duration (seconds)",
                "precision": 1
            },
            {
                "fieldname": "audio_quality",
                "fieldtype": "Select",
                "label": "Audio Quality",
                "options": "poor\nfair\ngood\nexcellent\nunknown"
            },
            {
                "fieldname": "processing_status",
                "fieldtype": "Select",
                "label": "Processing Status",
                "options": "pending\nprocessing\ncompleted\nfailed",
                "default": "pending"
            },
            {
                "fieldname": "timestamp",
                "fieldtype": "Datetime",
                "label": "Timestamp",
                "reqd": 1
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
            "write": 1,
            "create": 1,
            "delete": 0
        })

        doctype.insert()
        frappe.db.commit()
        print("✅ Voice Interaction Log DocType created successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to create Voice Interaction Log DocType: {str(e)}")
        return False

def create_voice_interaction_log_doctype():
    """Create Voice Interaction Log DocType for voice interface"""

    try:
        if frappe.db.exists("DocType", "Voice Interaction Log"):
            print("✅ Voice Interaction Log DocType already exists")
            return True

        doctype = frappe.new_doc("DocType")
        doctype.name = "Voice Interaction Log"
        doctype.module = "Assistant CRM"
        doctype.custom = 1
        doctype.is_submittable = 0
        doctype.track_changes = 1
        doctype.autoname = "naming_series:"

        # Add fields
        fields = [
            {
                "fieldname": "naming_series",
                "fieldtype": "Select",
                "label": "Naming Series",
                "options": "VIL-.YYYY.-.#####",
                "reqd": 1
            },
            {
                "fieldname": "user_id",
                "fieldtype": "Data",
                "label": "User ID",
                "reqd": 1
            },
            {
                "fieldname": "session_id",
                "fieldtype": "Data",
                "label": "Session ID"
            },
            {
                "fieldname": "transcribed_text",
                "fieldtype": "Long Text",
                "label": "Transcribed Text"
            },
            {
                "fieldname": "transcription_confidence",
                "fieldtype": "Float",
                "label": "Transcription Confidence",
                "precision": 3
            },
            {
                "fieldname": "language",
                "fieldtype": "Select",
                "label": "Language",
                "options": "en\nes\nfr\nbem\nny\nto"
            },
            {
                "fieldname": "audio_duration",
                "fieldtype": "Float",
                "label": "Audio Duration (seconds)",
                "precision": 1
            },
            {
                "fieldname": "audio_quality",
                "fieldtype": "Select",
                "label": "Audio Quality",
                "options": "poor\nfair\ngood\nexcellent\nunknown"
            },
            {
                "fieldname": "processing_status",
                "fieldtype": "Select",
                "label": "Processing Status",
                "options": "pending\nprocessing\ncompleted\nfailed",
                "default": "pending"
            },
            {
                "fieldname": "timestamp",
                "fieldtype": "Datetime",
                "label": "Timestamp",
                "reqd": 1
            },
            {
                "fieldname": "response_generated",
                "fieldtype": "Long Text",
                "label": "Response Generated"
            },
            {
                "fieldname": "voice_response_url",
                "fieldtype": "Data",
                "label": "Voice Response URL"
            },
            {
                "fieldname": "accessibility_features_used",
                "fieldtype": "Long Text",
                "label": "Accessibility Features Used"
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
            "write": 1,
            "create": 1,
            "delete": 0
        })

        doctype.insert()
        frappe.db.commit()
        print("✅ Voice Interaction Log DocType created successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to create Voice Interaction Log DocType: {str(e)}")
        return False

if __name__ == "__main__":
    frappe.init(site="dev")
    frappe.connect()

    print("🔧 FIXING USER INTERACTION LOG FOR SATISFACTION DASHBOARD")
    print("=" * 70)

    # Step 1: Fix or create User Interaction Log DocType
    doctype_fixed = fix_user_interaction_log()

    # Step 2: Create Proactive Engagement Log DocType
    proactive_doctype_created = create_proactive_engagement_log_doctype()

    if doctype_fixed:
        print("\n✅ DocType fix completed")

        # Step 3: Create sample data
        sample_count = create_sample_interaction_data()

        # Step 4: Test dashboard
        dashboard_works = test_satisfaction_dashboard_after_fix()

        if dashboard_works:
            print("\n🎉 SATISFACTION DASHBOARD FIX: SUCCESS!")
            print("✅ Dashboard now working correctly")
            print("🚀 Ready for Phase 4 re-testing")
        else:
            print("\n❌ SATISFACTION DASHBOARD FIX: STILL FAILING")
            print("🔧 Additional investigation needed")
    else:
        print("\n❌ DOCTYPE FIX FAILED")
        print("🔧 Cannot proceed with dashboard testing")

    print("=" * 70)
