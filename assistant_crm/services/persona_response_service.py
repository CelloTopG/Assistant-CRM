# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from typing import Dict, List, Optional
import json


class PersonaResponseService:
    """
    Service for managing persona-based response generation.
    
    This service handles the selection and rendering of appropriate response
    templates based on detected user persona and conversation context.
    """
    
    def __init__(self):
        """Initialize the persona response service"""
        self.templates_cache = {}
        self.load_templates()

    def load_templates(self):
        """Load all active response templates - deprecated"""
        # Persona Response Template doctype has been deprecated
        # Use default responses instead
        self.templates_cache = {}
    
    def generate_response(self, persona: str, intent_category: str = "general",
                         user_context: Dict = None, message_context: Dict = None,
                         language: str = "en") -> Dict:
        """
        Generate a persona-appropriate response

        Args:
            persona (str): Detected user persona
            intent_category (str): Intent category of the conversation
            user_context (Dict): User context data
            message_context (Dict): Current message context
            language (str): Response language

        Returns:
            Dict: Generated response with template and quick replies
        """
        # Persona Response Template doctype has been deprecated
        # Use default responses instead
        return self._generate_default_response(persona, user_context)
    
    def _find_best_template(self, persona: str, intent_category: str, 
                           language: str) -> Optional[Dict]:
        """Find the best matching template"""
        # Try exact match first
        key = f"{persona}_{intent_category}_{language}"
        if key in self.templates_cache and self.templates_cache[key]:
            return self.templates_cache[key][0]  # Return highest priority template
        
        # Try with general intent
        key = f"{persona}_general_{language}"
        if key in self.templates_cache and self.templates_cache[key]:
            return self.templates_cache[key][0]
        
        # Try with English fallback
        if language != "en":
            key = f"{persona}_{intent_category}_en"
            if key in self.templates_cache and self.templates_cache[key]:
                return self.templates_cache[key][0]
            
            key = f"{persona}_general_en"
            if key in self.templates_cache and self.templates_cache[key]:
                return self.templates_cache[key][0]
        
        return None
    
    def _find_fallback_template(self, persona: str, language: str) -> Optional[Dict]:
        """Find fallback template for persona"""
        # Try general persona with same language
        key = f"general_general_{language}"
        if key in self.templates_cache and self.templates_cache[key]:
            return self.templates_cache[key][0]
        
        # Try general persona with English
        if language != "en":
            key = "general_general_en"
            if key in self.templates_cache and self.templates_cache[key]:
                return self.templates_cache[key][0]
        
        return None
    
    def _prepare_additional_data(self, persona: str, intent_category: str, 
                               message_context: Dict = None) -> Dict:
        """Prepare additional data for template rendering"""
        additional_data = {
            "intent_category": intent_category,
            "persona_type": persona
        }
        
        if message_context:
            additional_data.update({
                "original_message": message_context.get("message", ""),
                "session_id": message_context.get("session_id", ""),
                "conversation_turn": message_context.get("turn", 1)
            })
        
        # Add persona-specific data
        persona_characteristics = self._get_persona_characteristics(persona)
        additional_data.update(persona_characteristics)
        
        return additional_data
    
    def _get_persona_characteristics(self, persona: str) -> Dict:
        """Get characteristics for a specific persona"""
        characteristics = {
            "employer": {
                "primary_focus": "business efficiency and compliance",
                "key_concerns": "cost management, regulatory compliance, process optimization",
                "preferred_actions": "registration, reporting, contribution management"
            },
            "beneficiary": {
                "primary_focus": "benefit access and support",
                "key_concerns": "payment status, claim processing, documentation",
                "preferred_actions": "status checking, claim submission, certificate updates"
            },
            "supplier": {
                "primary_focus": "payment and contract management",
                "key_concerns": "payment timing, contract status, procurement processes",
                "preferred_actions": "payment tracking, contract inquiries, vendor registration"
            },
            "wcfcb_staff": {
                "primary_focus": "operational efficiency and accuracy",
                "key_concerns": "policy compliance, system functionality, process optimization",
                "preferred_actions": "system administration, policy lookup, process guidance"
            },
            "general": {
                "primary_focus": "general assistance and information",
                "key_concerns": "basic information, general guidance",
                "preferred_actions": "information requests, general inquiries"
            }
        }
        
        return characteristics.get(persona, characteristics["general"])
    
    def _enhance_response_for_persona(self, response: str, persona: str, 
                                    user_context: Dict = None) -> str:
        """Apply persona-specific enhancements to response"""
        # Add persona-specific context cues
        if persona == "employer":
            if "registration" in response.lower():
                response += "\n\n💼 **Business Tip:** Keep your employee records updated for accurate contributions."
        elif persona == "beneficiary":
            if "payment" in response.lower():
                response += "\n\n💡 **Helpful Note:** Payments are typically processed on the 15th of each month."
        elif persona == "supplier":
            if "payment" in response.lower():
                response += "\n\n📋 **Vendor Info:** Payment processing takes 5-7 business days after approval."
        elif persona == "wcfcb_staff":
            response += "\n\n🔧 **Staff Note:** Check the internal knowledge base for detailed procedures."
        
        return response
    
    def _generate_default_response(self, persona: str, user_context: Dict = None) -> Dict:
        """Generate a default response when no template is found"""
        default_responses = {
            "employer": "Hello! I'm Anna, your WCFCB business assistant. How can I help you with your business needs today?",
            "beneficiary": "Hello! I'm Anna, and I'm here to help you with your benefits and services. What can I assist you with?",
            "supplier": "Good day! I'm Anna, your WCFCB procurement assistant. How can I help you with your vendor needs?",
            "wcfcb_staff": "Hi! I'm Anna, your internal assistant. What can I help you with today?",
            "general": "Hello! I'm Anna, your WCFCB assistant. How can I help you today?"
        }
        
        response = default_responses.get(persona, default_responses["general"])
        
        return {
            "success": True,
            "response": response,
            "quick_replies": self._get_default_quick_replies(persona),
            "template_used": "default",
            "persona": persona,
            "intent_category": "greeting",
            "language": "en"
        }
    
    def _get_default_quick_replies(self, persona: str) -> List[Dict]:
        """Get default quick replies for a persona"""
        default_replies = {
            "employer": [
                {"text": "Register Business", "action": "start_process", "action_config": {"process_id": "business_registration"}},
                {"text": "Check Contributions", "action": "show_info", "action_config": {"info_type": "contribution_status"}},
                {"text": "Contact Support", "action": "escalate", "action_config": {"escalation_type": "business_support"}}
            ],
            "beneficiary": [
                {"text": "Check Payment Status", "action": "show_info", "action_config": {"info_type": "payment_status"}},
                {"text": "Submit Life Certificate", "action": "start_process", "action_config": {"process_id": "life_certificate"}},
                {"text": "File a Claim", "action": "start_process", "action_config": {"process_id": "claim_submission"}}
            ],
            "supplier": [
                {"text": "Check Payment Status", "action": "show_info", "action_config": {"info_type": "vendor_payment"}},
                {"text": "View Contracts", "action": "show_info", "action_config": {"info_type": "contract_status"}},
                {"text": "Procurement Inquiry", "action": "start_process", "action_config": {"process_id": "procurement_inquiry"}}
            ],
            "wcfcb_staff": [
                {"text": "Policy Lookup", "action": "show_info", "action_config": {"info_type": "policy_search"}},
                {"text": "System Status", "action": "show_info", "action_config": {"info_type": "system_status"}},
                {"text": "User Management", "action": "open_form", "action_config": {"form_name": "User"}}
            ],
            "general": [
                {"text": "Services", "action": "show_info", "action_config": {"info_type": "services"}},
                {"text": "Contact Info", "action": "show_info", "action_config": {"info_type": "contact"}},
                {"text": "Speak to Agent", "action": "escalate", "action_config": {"escalation_type": "general"}}
            ]
        }
        
        return default_replies.get(persona, default_replies["general"])
    
    def _generate_error_response(self, persona: str, user_context: Dict = None) -> Dict:
        """Generate error response"""
        return {
            "success": False,
            "response": "I apologize, but I'm experiencing technical difficulties. Please try again or contact our support team.",
            "quick_replies": [
                {"text": "Try Again", "action": "send_message", "action_config": {"message": "Hello"}},
                {"text": "Contact Support", "action": "escalate", "action_config": {"escalation_type": "technical"}}
            ],
            "template_used": "error",
            "persona": persona,
            "error": True
        }
