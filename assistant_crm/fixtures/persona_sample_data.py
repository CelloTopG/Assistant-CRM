# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def create_sample_persona_data():
    """Create sample data for persona detection system - deprecated"""
    # Persona Classification Rule, Persona Keyword, and Persona Response Template
    # doctypes have been deprecated - skipping sample data creation
    print("Persona doctypes have been deprecated - skipping sample data creation")


def create_sample_classification_rules():
    """Create sample persona classification rules - deprecated"""
    # Persona Classification Rule doctype has been deprecated
    print("Persona Classification Rule doctype has been deprecated - skipping")


def create_sample_keywords():
    """Create sample persona keywords - deprecated"""
    # Persona Keyword doctype has been removed
    print("Persona Keyword doctype has been deprecated - skipping keyword creation")


def create_sample_response_templates():
    """Create sample persona response templates - deprecated"""
    # Persona Response Template doctype has been deprecated
    print("Persona Response Template doctype has been deprecated - skipping")


def test_persona_detection():
    """Test the persona detection system with sample messages"""
    
    try:
        from assistant_crm.assistant_crm.services.persona_detection_service import PersonaDetectionService
        
        detection_service = PersonaDetectionService()
        
        test_messages = [
            {
                "message": "I need help with business registration and employee contributions",
                "expected_persona": "employer"
            },
            {
                "message": "When will I receive my pension payment this month?",
                "expected_persona": "beneficiary"
            },
            {
                "message": "I need to check the status of my invoice payment",
                "expected_persona": "supplier"
            },
            {
                "message": "How do I manage user permissions in the system?",
                "expected_persona": "wcfcb_staff"
            }
        ]
        
        print("\n=== Testing Persona Detection ===")
        
        for test in test_messages:
            user_context = {"user": "Guest", "roles": []}
            result = detection_service.detect_persona(
                user_context=user_context,
                current_message=test["message"]
            )
            
            print(f"Message: {test['message'][:50]}...")
            print(f"Expected: {test['expected_persona']}")
            print(f"Detected: {result.get('persona', 'unknown')} (confidence: {result.get('confidence', 0):.2f})")
            print("---")
            
    except Exception as e:
        print(f"Error testing persona detection: {str(e)}")


if __name__ == "__main__":
    create_sample_persona_data()
    test_persona_detection()
