# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from typing import Dict, Optional
from frappe import _
import time
import json
import re

def validate_message(message: str) -> bool:
    """
    Validate input message for basic requirements.
    
    Args:
        message (str): User input message
        
    Returns:
        bool: True if message is valid
    """
    if not message or not isinstance(message, str):
        return False
    
    # Remove whitespace and check if empty
    cleaned_message = message.strip()
    if not cleaned_message:
        return False
        
    # Basic length validation
    if len(cleaned_message) > 1000:  # Reasonable limit
        return False
        
    return True


def get_concise_intent_classification(message: str, context: Dict = None) -> tuple:
    """
    Classify user intent using existing intent recognition service.

    Args:
        message (str): User message
        context (Dict): User context

    Returns:
        tuple: (intent, confidence)
    """
    try:
        # Use existing intent recognition service
        from assistant_crm.assistant_crm.services.intent_recognition_service import classify_intent
        return classify_intent(message, context)
    except ImportError:
        # Enhanced fallback intent detection
        message_lower = message.lower()

        # Enhanced intent mapping for concise responses with better keyword coverage
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'greetings']):
            return 'greeting', 0.9
        elif any(word in message_lower for word in ['claim', 'submit', 'injury', 'accident', 'injured', 'hurt', 'file', 'workplace injury']):
            return 'claim_submission', 0.8
        elif any(word in message_lower for word in ['register', 'registration', 'employer', 'business']):
            return 'employer_registration', 0.8
        elif any(word in message_lower for word in ['payment', 'premium', 'pay', 'billing']):
            return 'payment_inquiry', 0.8
        elif any(word in message_lower for word in ['status', 'check', 'update', 'progress', 'application status', 'claim status']):
            return 'status_inquiry', 0.7
        elif any(word in message_lower for word in ['information', 'info', 'details', 'explain', 'what is', 'how does']):
            return 'information_request', 0.7
        elif any(word in message_lower for word in ['service', 'services', 'access', 'use', 'need']):
            return 'service_request', 0.7
        elif any(word in message_lower for word in ['help', 'assistance', 'support', 'assist']):
            return 'general_inquiry', 0.7
        else:
            return 'general_inquiry', 0.5


def get_concise_response_template(intent: str, user_role: str, context: Dict = None) -> str:
    """
    Get concise response template (20-35 words) from database or fallback to hardcoded.

    Args:
        intent (str): Detected intent
        user_role (str): User role (employer, beneficiary, etc.)
        context (Dict): Additional context

    Returns:
        str: Concise response template
    """
    context = context or {}
    user_name = context.get('user_name', '')

    # Try to get template from database first
    try:
        # Dynamic import to avoid circular dependencies
        import sys
        import os
        module_path = os.path.join(os.path.dirname(os.path.dirname(__file__)))
        if module_path not in sys.path:
            sys.path.insert(0, module_path)

        from assistant_crm.assistant_crm.doctype.concise_response_template.concise_response_template import ConciseResponseTemplate

        # Get template from database
        db_template = ConciseResponseTemplate.get_template(intent, user_role, 'en')

        if db_template and db_template.get('template_content'):
            template_content = db_template['template_content']

            # Personalize with user name if template supports it and user name is available
            if db_template.get('use_user_name', True) and user_name and 'Hi!' in template_content:
                template_content = template_content.replace('Hi!', f'Hi {user_name}!')

            # Update usage statistics
            try:
                ConciseResponseTemplate.update_usage_stats(db_template['name'])
            except:
                pass  # Don't fail if stats update fails

            return template_content

    except Exception as e:
        # Log error but continue with fallback
        try:
            frappe.log_error(f"Failed to get template from database: {str(e)}", "Optimized Template Retrieval Error")
        except:
            pass

    # Fallback to hardcoded templates if database lookup fails
    greeting_prefix = f"Hi {user_name}! " if user_name else "Hi! "

    # Fallback templates (20-35 words each)
    fallback_templates = {
        'greeting': {
            'employer': f"{greeting_prefix}I'm Anna from WCFCB. I can help with premium payments, employee registrations, claims, and compliance. What do you need assistance with today?",
            'beneficiary': f"{greeting_prefix}I'm Anna from WCFCB. I can help with your claims, payments, certificates, and benefits. How can I assist you today?",
            'employee': f"{greeting_prefix}I'm Anna from WCFCB. I can help with workplace injuries, claims, and your coverage. What can I help you with?",
            'default': f"{greeting_prefix}I'm Anna from WCFCB. I'm here to help with claims, registrations, payments, and compliance. How can I assist you?"
        },
        'claim_submission': {
            'employer': "I'll help you submit this workplace injury claim. Please provide the incident date, employee details, and injury description to get started.",
            'beneficiary': "I'll help you submit your claim. Please provide your injury date, workplace details, and medical information to begin the process.",
            'employee': "I'll help you submit your workplace injury claim promptly. Please provide the incident date, injury details, and your employer information to get started.",
            'default': "I'll help you submit your claim efficiently. Please provide the incident date, injury details, and relevant workplace information to start the process."
        },
        'employer_registration': {
            'employer': "I'll help you register as an employer with WCFCB. You'll need your business registration, employee details, and industry classification. Shall we start?",
            'default': "I'll help you with employer registration process. You'll need business registration documents, employee information, and industry classification details. Ready to begin the application?"
        },
        'payment_inquiry': {
            'employer': "I can help with premium payments. Please provide your employer number or business name to check your payment status and options.",
            'beneficiary': "I can help check your payment status. Please provide your claim number or personal details to review your benefits and payments.",
            'default': "I can help with payment inquiries and status checks. Please provide your account details or reference number to check your current payment status."
        },
        'status_inquiry': {
            'employer': "I can check your account status. Please provide your employer number or business name to review your compliance and payment status.",
            'beneficiary': "I can check your claim status immediately. Please provide your claim number or personal details to get the latest update on your case.",
            'default': "I can check your status right away. Please provide your reference number or account details to get the latest information available."
        },
        'general_inquiry': {
            'default': "I'm here to help with all WCFCB services. Could you please tell me specifically what you need assistance with today?"
        }
    }

    # Get fallback template for intent and role
    intent_templates = fallback_templates.get(intent, fallback_templates['general_inquiry'])
    template = intent_templates.get(user_role, intent_templates.get('default', intent_templates[list(intent_templates.keys())[0]]))

    return template


def detect_user_role_concise(context: Dict, message: str) -> str:
    """
    Detect user role for concise response personalization.
    
    Args:
        context (Dict): User context
        message (str): User message
        
    Returns:
        str: Detected user role
    """
    # Check context for role information
    if context.get('user_role'):
        return context['user_role']
    
    # Simple role detection based on message content
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['business', 'company', 'employer', 'employee registration', 'premium']):
        return 'employer'
    elif any(word in message_lower for word in ['injury', 'injured', 'claim', 'benefits', 'compensation']):
        return 'beneficiary'
    elif any(word in message_lower for word in ['workplace', 'work accident', 'on the job']):
        return 'employee'
    else:
        return 'default'


def optimize_response_length(response: str, target_words: int = 30) -> str:
    """
    Optimize response to target word count while maintaining meaning.
    
    Args:
        response (str): Original response
        target_words (int): Target word count (default 30)
        
    Returns:
        str: Optimized response
    """
    words = response.split()
    current_count = len(words)
    
    # If already within target range (20-35 words), return as is
    if 20 <= current_count <= 35:
        return response
    
    # If too long, truncate intelligently
    if current_count > 35:
        # Keep first part up to target words, ensure it ends properly
        truncated = ' '.join(words[:target_words])
        
        # Ensure proper ending
        if not truncated.endswith(('.', '?', '!')):
            # Find last complete sentence
            sentences = truncated.split('.')
            if len(sentences) > 1:
                truncated = '.'.join(sentences[:-1]) + '.'
            else:
                truncated += '.'
        
        return truncated
    
    # If too short, it's probably fine for concise responses
    return response


def get_concise_reply(message: str, user_context: Dict = None, session_id: str = None) -> str:
    """
    Generate concise bot reply (20-35 words) for user message.

    Phase 2: Updated to use new intent-based response system
    Maintains Anna's personality while providing actionable responses in 20-35 words.

    Args:
        message (str): User's input message
        user_context (Dict): Additional user context and preferences
        session_id (str): Session identifier for conversation tracking

    Returns:
        str: Generated concise bot response (20-35 words)
    """
    # Performance monitoring
    start_time = time.time()

    try:
        # Initialize context
        user_context = user_context or {}

        # Validate input message
        if not validate_message(message):
            return "I want to help you, but your message didn't come through clearly. Could you please try again? I'm here to assist."

        # Phase 2: Use new simplified chat system
        from assistant_crm.api.simplified_chat import send_message
        response = send_message(message, session_id, user_context)

        # Log performance
        end_time = time.time()
        frappe.log_error(f"Phase 2 Optimized Reply: {end_time - start_time:.3f}s for '{message[:50]}...' -> '{response[:50]}...'", "Phase 2 Performance")

        return response

    except Exception as e:
        # Fallback response if Phase 2 system fails
        frappe.log_error(f"Phase 2 optimized reply error: {str(e)}", "Phase 2 Reply Error")
        return "Hi! I'm Anna from WCFCB. I'm here to help you. Could you please tell me what you need assistance with?"


def test_concise_responses():
    """
    Test function to validate concise response generation.
    
    Returns:
        dict: Test results with response lengths
    """
    test_cases = [
        {"message": "Hello", "context": {"user_name": "John"}},
        {"message": "I need to submit a claim", "context": {"user_role": "beneficiary"}},
        {"message": "How do I register as an employer?", "context": {"user_role": "employer"}},
        {"message": "What's my payment status?", "context": {"user_name": "Sarah"}},
        {"message": "I need help", "context": {}}
    ]
    
    results = []
    
    for test_case in test_cases:
        try:
            response = get_concise_reply(
                test_case["message"], 
                test_case["context"], 
                f"test_session_{len(results)}"
            )
            
            word_count = len(response.split())
            
            results.append({
                "message": test_case["message"],
                "response": response,
                "word_count": word_count,
                "within_target": 20 <= word_count <= 35,
                "status": "success"
            })
            
        except Exception as e:
            results.append({
                "message": test_case["message"],
                "error": str(e),
                "status": "error"
            })
    
    return {
        "test_results": results,
        "total_tests": len(test_cases),
        "successful_tests": len([r for r in results if r.get("status") == "success"]),
        "within_target_count": len([r for r in results if r.get("within_target", False)])
    }


def get_realtime_data_for_intent(message: str, intent: str, user_context: Dict = None) -> Dict:
    """
    Get real-time data based on detected intent and message content.

    Args:
        message (str): User message
        intent (str): Detected intent
        user_context (Dict): User context information

    Returns:
        Dict: Real-time data response
    """
    try:
        # Extract relevant identifiers from message
        if intent == "claim_status":
            claim_number = extract_claim_number(message)
            if claim_number:
                from assistant_crm.api.realtime_data_integration import get_realtime_claim_status
                return get_realtime_claim_status(claim_number, user_context)

        elif intent == "payment_inquiry":
            account_number = extract_account_number(message)
            if account_number:
                from assistant_crm.api.realtime_data_integration import get_realtime_payment_status
                return get_realtime_payment_status(account_number, user_context)

        elif intent == "employer_status":
            employer_number = extract_employer_number(message)
            if employer_number:
                from assistant_crm.api.realtime_data_integration import get_realtime_employer_status
                return get_realtime_employer_status(employer_number, user_context)

        return {"success": False, "reason": "No identifiers found"}

    except Exception as e:
        frappe.log_error(f"Real-time data integration error: {str(e)}", "Real-time Data Integration")
        return {"success": False, "error": str(e)}


def extract_claim_number(message: str) -> str:
    """Extract claim number from user message."""
    # Look for patterns like "claim 12345", "CLM-12345", etc.
    patterns = [
        r'claim\s+(\w+[-]?\w+)',
        r'CLM[-]?(\w+)',
        r'claim\s*#\s*(\w+)',
        r'reference\s+(\w+[-]?\w+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def extract_account_number(message: str) -> str:
    """Extract account number from user message."""
    # Look for patterns like "account 12345", "ACC-12345", etc.
    patterns = [
        r'account\s+(\w+[-]?\w+)',
        r'ACC[-]?(\w+)',
        r'account\s*#\s*(\w+)',
        r'employer\s+(\w+[-]?\w+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def extract_employer_number(message: str) -> str:
    """Extract employer number from user message."""
    # Look for patterns like "employer 12345", "EMP-12345", etc.
    patterns = [
        r'employer\s+(\w+[-]?\w+)',
        r'EMP[-]?(\w+)',
        r'employer\s*#\s*(\w+)',
        r'company\s+(\w+[-]?\w+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def enhance_reply_with_realtime_data(base_reply: str, realtime_data: Dict) -> str:
    """
    Enhance base reply with real-time data while maintaining conciseness.

    Args:
        base_reply (str): Base optimized reply
        realtime_data (Dict): Real-time data from API

    Returns:
        str: Enhanced reply with real-time information
    """
    try:
        if not realtime_data.get("success") or not realtime_data.get("data"):
            return base_reply

        data = realtime_data["data"]

        # Use personalized message if available
        if data.get("user_message"):
            enhanced_reply = data["user_message"]
        else:
            # Fallback to base reply
            enhanced_reply = base_reply

        # Ensure enhanced reply stays within word count limits
        words = enhanced_reply.split()
        if len(words) > 35:
            # Truncate while maintaining meaning
            enhanced_reply = " ".join(words[:32]) + "..."

        return enhanced_reply

    except Exception as e:
        frappe.log_error(f"Reply enhancement error: {str(e)}", "Reply Enhancement")
        return base_reply
