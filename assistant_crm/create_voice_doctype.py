#!/usr/bin/env python3
"""
Create Voice Interaction Log DocType for Voice Interface Integration
"""

import frappe
from frappe import _

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
    
    print("🎤 CREATING VOICE INTERACTION LOG DOCTYPE")
    print("=" * 50)
    
    success = create_voice_interaction_log_doctype()
    
    if success:
        print("✅ Voice DocType creation completed successfully")
    else:
        print("❌ Voice DocType creation failed")
    
    print("=" * 50)
