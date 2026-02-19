#!/usr/bin/env python3
"""
Script to create concise response templates for basic interactions.
This script adds new Message Template records to support brief, efficient responses
while maintaining WorkCom's warm, professional personality.
"""

import frappe

def create_concise_templates():
    """Create concise response templates for basic interactions"""
    
    # Define concise templates for basic interactions
    concise_templates = [
        {
            "template_name": "Simple Greeting Concise",
            "template_type": "Greeting",
            "language": "en",
            "subject": "Simple Greeting",
            "content": "Hi! I'm WorkCom from WCFCB. How can I help you today?",
            "is_active": 1
        },
        {
            "template_name": "Quick Confirmation",
            "template_type": "General",
            "language": "en", 
            "subject": "Quick Confirmation",
            "content": "Got it! I'll help you with that right away.",
            "is_active": 1
        },
        {
            "template_name": "Brief Thank You",
            "template_type": "General",
            "language": "en",
            "subject": "Brief Thank You", 
            "content": "You're welcome! Is there anything else I can help you with?",
            "is_active": 1
        },
        {
            "template_name": "Quick Status Check",
            "template_type": "General",
            "language": "en",
            "subject": "Quick Status Check",
            "content": "I'll check that for you right now. One moment please.",
            "is_active": 1
        },
        {
            "template_name": "Brief Clarification",
            "template_type": "General", 
            "language": "en",
            "subject": "Brief Clarification",
            "content": "Could you provide a bit more detail so I can help you better?",
            "is_active": 1
        },
        {
            "template_name": "Concise Goodbye",
            "template_type": "Goodbye",
            "language": "en",
            "subject": "Concise Goodbye",
            "content": "Take care! Feel free to reach out anytime you need help.",
            "is_active": 1
        },
        {
            "template_name": "Quick Error Acknowledgment",
            "template_type": "Error Handling",
            "language": "en", 
            "subject": "Quick Error Acknowledgment",
            "content": "I apologize for the confusion. Let me help you resolve this.",
            "is_active": 1
        },
        {
            "template_name": "Brief Wait Request",
            "template_type": "General",
            "language": "en",
            "subject": "Brief Wait Request", 
            "content": "Please hold on while I look that up for you.",
            "is_active": 1
        }
    ]
    
    created_count = 0
    updated_count = 0
    
    for template_data in concise_templates:
        try:
            # Check if template already exists
            existing = frappe.db.exists("Message Template", template_data["template_name"])
            
            if existing:
                # Update existing template
                doc = frappe.get_doc("Message Template", template_data["template_name"])
                for key, value in template_data.items():
                    if key != "template_name":  # Don't update the name field
                        setattr(doc, key, value)
                doc.save()
                updated_count += 1
                print(f"Updated template: {template_data['template_name']}")
            else:
                # Create new template
                doc = frappe.get_doc({
                    "doctype": "Message Template",
                    **template_data
                })
                doc.insert()
                created_count += 1
                print(f"Created template: {template_data['template_name']}")
                
        except Exception as e:
            print(f"Error processing template {template_data['template_name']}: {str(e)}")
    
    frappe.db.commit()
    print(f"\nSummary: Created {created_count} new templates, updated {updated_count} existing templates")
    return created_count, updated_count

if __name__ == "__main__":
    # This script should be run from within Frappe context
    create_concise_templates()

