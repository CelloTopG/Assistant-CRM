# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from typing import Dict, List, Optional
import json


class EnhancedChatService:
    """
    Enhanced chat service that integrates persona detection, context analysis,
    and persona-specific response generation.
    
    This service provides the main interface for the enhanced chatbot functionality
    with persona-aware responses and intelligent conversation management.
    """
    
    def __init__(self):
        """Initialize the enhanced chat service"""
        self.persona_detection_service = None
        self.persona_response_service = None
        self.context_service = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize required services"""
        try:
            # Import services dynamically to avoid circular imports
            from assistant_crm.assistant_crm.services.persona_detection_service import PersonaDetectionService
            from assistant_crm.assistant_crm.services.persona_response_service import PersonaResponseService
            from assistant_crm.assistant_crm.services.context_service import ContextService
            
            self.persona_detection_service = PersonaDetectionService()
            self.persona_response_service = PersonaResponseService()
            self.context_service = ContextService()
            
        except Exception as e:
            frappe.log_error(f"Error initializing enhanced chat services: {str(e)}", 
                           "Enhanced Chat Service")
            # Set fallback None values - will use basic functionality
            pass
    
    def process_message(self, message: str, session_id: str = None, 
                       user_context: Dict = None, language: str = "en") -> Dict:
        """
        Process a chat message with persona-aware intelligence
        
        Args:
            message (str): User's message
            session_id (str): Session identifier
            user_context (Dict): User context data
            language (str): Response language
            
        Returns:
            Dict: Enhanced response with persona information
        """
        try:
            # Get enhanced user context
            if not user_context:
                user_context = self._get_enhanced_context()
            
            # Get conversation history
            conversation_history = self._get_conversation_history(session_id)
            
            # Detect user persona
            persona_result = self._detect_user_persona(
                user_context, conversation_history, message
            )
            
            # Determine intent category
            intent_category = self._determine_intent_category(message, persona_result)
            
            # Generate persona-appropriate response
            response_result = self._generate_persona_response(
                persona_result["persona"], intent_category, user_context, 
                {"message": message, "session_id": session_id}, language
            )
            
            # Log the interaction
            self._log_enhanced_interaction(
                message, response_result, persona_result, session_id, user_context
            )
            
            # Prepare final response
            final_response = {
                "success": True,
                "reply": response_result.get("response", "I'm here to help!"),
                "session_id": session_id,
                "timestamp": frappe.utils.now(),
                "persona_data": {
                    "detected_persona": persona_result["persona"],
                    "confidence": persona_result["confidence"],
                    "persona_characteristics": self._get_persona_characteristics(persona_result["persona"])
                },
                "quick_replies": response_result.get("quick_replies", []),
                "communication_style": response_result.get("communication_style", {}),
                "enhanced_features": {
                    "persona_detection": True,
                    "context_awareness": True,
                    "personalized_responses": True
                }
            }
            
            return final_response
            
        except Exception as e:
            frappe.log_error(f"Error in enhanced chat processing: {str(e)}", 
                           "Enhanced Chat Service")
            return self._generate_fallback_response(message, session_id)
    
    def _get_enhanced_context(self) -> Dict:
        """Get enhanced user context"""
        try:
            if self.context_service:
                return self.context_service.get_enhanced_user_context()
            else:
                # Fallback to basic context
                return {
                    "user": frappe.session.user,
                    "roles": frappe.get_roles(),
                    "timestamp": frappe.utils.now()
                }
        except Exception as e:
            frappe.log_error(f"Error getting enhanced context: {str(e)}", 
                           "Enhanced Chat Service")
            return {"user": frappe.session.user}
    
    def _get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for session"""
        try:
            if not session_id:
                return []
            
            history = frappe.get_all(
                "Chat History",
                fields=["message", "response", "timestamp"],
                filters={"session_id": session_id},
                order_by="timestamp desc",
                limit=10
            )
            
            return history
            
        except Exception as e:
            frappe.log_error(f"Error getting conversation history: {str(e)}", 
                           "Enhanced Chat Service")
            return []
    
    def _detect_user_persona(self, user_context: Dict, conversation_history: List, 
                           current_message: str) -> Dict:
        """Detect user persona"""
        try:
            if self.persona_detection_service:
                return self.persona_detection_service.detect_persona(
                    user_context, conversation_history, current_message
                )
            else:
                # Fallback persona detection
                return self._fallback_persona_detection(user_context, current_message)
                
        except Exception as e:
            frappe.log_error(f"Error detecting persona: {str(e)}", "Enhanced Chat Service")
            return {"success": False, "persona": "general", "confidence": 0.0}
    
    def _fallback_persona_detection(self, user_context: Dict, message: str) -> Dict:
        """Fallback persona detection when service is unavailable"""
        # Simple rule-based detection
        roles = user_context.get("roles", [])
        message_lower = message.lower() if message else ""
        
        # Check for staff roles
        if any("admin" in role.lower() or "manager" in role.lower() for role in roles):
            return {"success": True, "persona": "wcfcb_staff", "confidence": 0.7}
        
        # Check message content for persona indicators
        if any(word in message_lower for word in ["business", "employee", "payroll"]):
            return {"success": True, "persona": "employer", "confidence": 0.6}
        elif any(word in message_lower for word in ["pension", "benefit", "payment"]):
            return {"success": True, "persona": "beneficiary", "confidence": 0.6}
        elif any(word in message_lower for word in ["invoice", "vendor", "supplier"]):
            return {"success": True, "persona": "supplier", "confidence": 0.6}
        else:
            return {"success": True, "persona": "general", "confidence": 0.5}
    
    def _determine_intent_category(self, message: str, persona_result: Dict) -> str:
        """Determine intent category from message"""
        try:
            message_lower = message.lower() if message else ""
            
            # Simple intent classification
            if any(word in message_lower for word in ["hello", "hi", "hey", "good morning"]):
                return "greeting"
            elif any(word in message_lower for word in ["status", "check", "update"]):
                return "status_inquiry"
            elif any(word in message_lower for word in ["help", "how", "what", "guide"]):
                return "information_request"
            elif any(word in message_lower for word in ["problem", "issue", "error", "complaint"]):
                return "complaint"
            elif any(word in message_lower for word in ["thank", "thanks", "appreciate"]):
                return "compliment"
            else:
                return "general_inquiry"
                
        except Exception:
            return "general_inquiry"
    
    def _generate_persona_response(self, persona: str, intent_category: str, 
                                 user_context: Dict, message_context: Dict, 
                                 language: str) -> Dict:
        """Generate persona-appropriate response"""
        try:
            if self.persona_response_service:
                return self.persona_response_service.generate_response(
                    persona, intent_category, user_context, message_context, language
                )
            else:
                # Fallback response generation
                return self._generate_fallback_persona_response(persona, intent_category)
                
        except Exception as e:
            frappe.log_error(f"Error generating persona response: {str(e)}", 
                           "Enhanced Chat Service")
            return self._generate_fallback_persona_response(persona, intent_category)
    
    def _generate_fallback_persona_response(self, persona: str, intent_category: str) -> Dict:
        """Generate fallback response when service is unavailable"""
        responses = {
            "employer": "Hello! I'm Anna, your WCFCB business assistant. How can I help you with your business needs today?",
            "beneficiary": "Hello! I'm Anna, and I'm here to help you with your benefits. What can I assist you with?",
            "supplier": "Good day! I'm Anna, your WCFCB procurement assistant. How can I help you today?",
            "wcfcb_staff": "Hi! I'm Anna, your internal assistant. What can I help you with?",
            "general": "Hello! I'm Anna, your WCFCB assistant. How can I help you today?"
        }
        
        return {
            "success": True,
            "response": responses.get(persona, responses["general"]),
            "quick_replies": [],
            "template_used": "fallback",
            "persona": persona,
            "intent_category": intent_category
        }
    
    def _get_persona_characteristics(self, persona: str) -> Dict:
        """Get characteristics for a persona"""
        try:
            if self.persona_detection_service:
                return self.persona_detection_service.get_persona_characteristics(persona)
            else:
                # Fallback characteristics
                return {
                    "primary_concerns": ["general assistance"],
                    "preferred_communication": "friendly",
                    "typical_queries": ["general inquiries"],
                    "urgency_level": "medium"
                }
        except Exception:
            return {"primary_concerns": ["general assistance"]}
    
    def _log_enhanced_interaction(self, message: str, response_result: Dict, 
                                persona_result: Dict, session_id: str, user_context: Dict):
        """Log the enhanced interaction for analytics"""
        try:
            # Create enhanced chat history entry
            chat_doc = frappe.get_doc({
                "doctype": "Chat History",
                "user": frappe.session.user,
                "session_id": session_id,
                "message": message,
                "response": response_result.get("response", ""),
                "timestamp": frappe.utils.now(),
                "status": "Completed",
                "persona_detected": persona_result.get("persona"),
                "persona_confidence": persona_result.get("confidence", 0.0),
                "template_used": response_result.get("template_used"),
                "enhanced_features_used": True
            })
            chat_doc.insert(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(f"Error logging enhanced interaction: {str(e)}", 
                           "Enhanced Chat Service")
    
    def _generate_fallback_response(self, message: str, session_id: str) -> Dict:
        """Generate fallback response when enhanced processing fails"""
        return {
            "success": True,
            "reply": "I'm here to help! However, I'm experiencing some technical difficulties with my advanced features. How can I assist you today?",
            "session_id": session_id,
            "timestamp": frappe.utils.now(),
            "persona_data": {
                "detected_persona": "general",
                "confidence": 0.0,
                "persona_characteristics": {}
            },
            "quick_replies": [
                {"text": "Get Help", "action": "send_message", "action_config": {"message": "I need help"}},
                {"text": "Contact Support", "action": "escalate", "action_config": {"escalation_type": "technical"}}
            ],
            "enhanced_features": {
                "persona_detection": False,
                "context_awareness": False,
                "personalized_responses": False
            },
            "fallback_mode": True
        }
