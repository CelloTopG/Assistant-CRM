#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Conversation Flow Optimizer
Core Integration Phase: Seamless authentication-to-data workflows
Maintains conversation context across authentication and data retrieval processes
"""

import frappe
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

class ConversationState(Enum):
    """Conversation flow states"""
    INITIAL = "initial"
    AUTHENTICATION_REQUIRED = "authentication_required"
    AUTHENTICATION_IN_PROGRESS = "authentication_in_progress"
    AUTHENTICATED = "authenticated"
    DATA_RETRIEVAL = "data_retrieval"
    DATA_PRESENTATION = "data_presentation"
    FOLLOW_UP = "follow_up"
    ERROR_RECOVERY = "error_recovery"

@dataclass
class FlowTransition:
    """Represents a conversation flow transition"""
    from_state: ConversationState
    to_state: ConversationState
    trigger: str
    condition: Optional[str] = None
    action: Optional[str] = None

class ConversationFlowOptimizer:
    """
    Optimizes conversation flow for seamless authentication-to-data workflows
    Maintains natural conversation feel while handling complex state transitions
    """
    
    def __init__(self):
        self.flow_transitions = self.define_flow_transitions()
        self.state_handlers = self.define_state_handlers()
        self.context_preservers = self.define_context_preservers()
        self.progressive_disclosure_rules = self.define_progressive_disclosure_rules()
        
    def optimize_conversation_flow(self, message: str, current_state: str, 
                                 conversation_context: Dict, user_session: Dict,
                                 intent_result: Dict) -> Dict:
        """
        Main method to optimize conversation flow
        """
        try:
            # Convert string state to enum
            current_state_enum = ConversationState(current_state)
            
            # Determine next state based on intent and current state
            next_state = self.determine_next_state(
                current_state_enum, intent_result, conversation_context, user_session
            )
            
            # Handle state transition
            transition_result = self.handle_state_transition(
                current_state_enum, next_state, message, conversation_context, 
                user_session, intent_result
            )
            
            # Preserve conversation context
            updated_context = self.preserve_conversation_context(
                conversation_context, transition_result, intent_result
            )
            
            # Apply progressive disclosure
            disclosure_result = self.apply_progressive_disclosure(
                transition_result, user_session, updated_context
            )
            
            return {
                "success": True,
                "current_state": current_state_enum.value,
                "next_state": next_state.value,
                "transition_result": disclosure_result,
                "updated_context": updated_context,
                "flow_guidance": self.generate_flow_guidance(next_state, intent_result)
            }
            
        except Exception as e:
            frappe.log_error(f"Conversation flow optimization error: {str(e)}")
            return self.handle_flow_error(current_state, message, conversation_context)
    
    def determine_next_state(self, current_state: ConversationState, intent_result: Dict,
                           conversation_context: Dict, user_session: Dict) -> ConversationState:
        """
        Determine next conversation state based on current state and intent
        """
        intent_type = intent_result.get("intent_type", "general")
        requires_auth = intent_result.get("requires_auth", False)
        is_authenticated = user_session.get("identity_verified", False)
        
        # State transition logic
        if current_state == ConversationState.INITIAL:
            if requires_auth and not is_authenticated:
                return ConversationState.AUTHENTICATION_REQUIRED
            elif intent_type == "live_data" and is_authenticated:
                return ConversationState.DATA_RETRIEVAL
            else:
                return ConversationState.INITIAL
        
        elif current_state == ConversationState.AUTHENTICATION_REQUIRED:
            if intent_type == "authentication":
                return ConversationState.AUTHENTICATION_IN_PROGRESS
            else:
                return ConversationState.AUTHENTICATION_REQUIRED
        
        elif current_state == ConversationState.AUTHENTICATION_IN_PROGRESS:
            if is_authenticated:
                # Check if original intent was for live data
                original_intent = conversation_context.get("original_intent")
                if original_intent and original_intent.get("intent_type") == "live_data":
                    return ConversationState.DATA_RETRIEVAL
                else:
                    return ConversationState.AUTHENTICATED
            else:
                return ConversationState.AUTHENTICATION_IN_PROGRESS
        
        elif current_state == ConversationState.AUTHENTICATED:
            if intent_type == "live_data":
                return ConversationState.DATA_RETRIEVAL
            else:
                return ConversationState.AUTHENTICATED
        
        elif current_state == ConversationState.DATA_RETRIEVAL:
            return ConversationState.DATA_PRESENTATION
        
        elif current_state == ConversationState.DATA_PRESENTATION:
            if intent_type == "live_data":
                return ConversationState.DATA_RETRIEVAL
            else:
                return ConversationState.FOLLOW_UP
        
        elif current_state == ConversationState.FOLLOW_UP:
            if intent_type == "live_data":
                return ConversationState.DATA_RETRIEVAL
            elif requires_auth and not is_authenticated:
                return ConversationState.AUTHENTICATION_REQUIRED
            else:
                return ConversationState.FOLLOW_UP
        
        return current_state
    
    def handle_state_transition(self, from_state: ConversationState, to_state: ConversationState,
                              message: str, context: Dict, session: Dict, 
                              intent_result: Dict) -> Dict:
        """
        Handle specific state transitions with appropriate actions
        """
        transition_key = f"{from_state.value}_to_{to_state.value}"
        handler = self.state_handlers.get(transition_key, self.default_state_handler)
        
        return handler(message, context, session, intent_result)
    
    def preserve_conversation_context(self, context: Dict, transition_result: Dict,
                                    intent_result: Dict) -> Dict:
        """
        Preserve conversation context across state transitions
        """
        updated_context = context.copy()
        
        # Preserve original intent during authentication flow
        if intent_result.get("intent_type") == "live_data" and not context.get("original_intent"):
            updated_context["original_intent"] = intent_result
        
        # Update conversation flow tracking
        updated_context["flow_history"] = context.get("flow_history", [])
        updated_context["flow_history"].append({
            "timestamp": datetime.now().isoformat(),
            "intent": intent_result.get("intent_type"),
            "transition": transition_result.get("transition_type"),
            "success": transition_result.get("success", True)
        })
        
        # Keep only last 10 flow events
        if len(updated_context["flow_history"]) > 10:
            updated_context["flow_history"] = updated_context["flow_history"][-10:]
        
        # Preserve user preferences and context
        if "user_preferences" not in updated_context:
            updated_context["user_preferences"] = {}
        
        # Track conversation topics
        topic = intent_result.get("context_awareness", {}).get("conversation_topic", "general")
        updated_context["current_topic"] = topic
        
        return updated_context
    
    def apply_progressive_disclosure(self, transition_result: Dict, user_session: Dict,
                                   context: Dict) -> Dict:
        """
        Apply progressive disclosure based on user verification level
        """
        auth_level = user_session.get("authentication_level", "none")
        user_permissions = user_session.get("permissions", [])
        
        # Get disclosure rules for current authentication level
        disclosure_rules = self.progressive_disclosure_rules.get(auth_level, {})
        
        # Apply disclosure filtering to response
        if "response" in transition_result:
            filtered_response = self.filter_response_by_disclosure(
                transition_result["response"], disclosure_rules, user_permissions
            )
            transition_result["response"] = filtered_response
        
        # Apply disclosure to data
        if "data" in transition_result:
            filtered_data = self.filter_data_by_disclosure(
                transition_result["data"], disclosure_rules, user_permissions
            )
            transition_result["data"] = filtered_data
        
        # Add disclosure guidance
        transition_result["disclosure_level"] = auth_level
        transition_result["available_actions"] = self.get_available_actions(
            auth_level, user_permissions
        )
        
        return transition_result
    
    def filter_response_by_disclosure(self, response: str, rules: Dict, 
                                    permissions: List[str]) -> str:
        """
        Filter response content based on disclosure rules
        """
        if not rules:
            return response
        
        # Apply content filtering based on permissions
        if "read_payment_info" not in permissions:
            # Remove payment-related information
            response = self.remove_payment_references(response)
        
        if "read_medical_info" not in permissions:
            # Remove medical information
            response = self.remove_medical_references(response)
        
        return response
    
    def filter_data_by_disclosure(self, data: Dict, rules: Dict, 
                                permissions: List[str]) -> Dict:
        """
        Filter data based on disclosure rules and permissions
        """
        if not rules or not data:
            return data
        
        filtered_data = data.copy()
        
        # Remove sensitive fields based on permissions
        if "read_payment_info" not in permissions:
            filtered_data.pop("payment_info", None)
            filtered_data.pop("compensation", None)
        
        if "read_medical_info" not in permissions:
            filtered_data.pop("medical_info", None)
            filtered_data.pop("treatment_details", None)
        
        return filtered_data
    
    def generate_flow_guidance(self, next_state: ConversationState, 
                             intent_result: Dict) -> Dict:
        """
        Generate guidance for the next step in conversation flow
        """
        guidance = {
            "next_state": next_state.value,
            "suggested_actions": [],
            "user_guidance": "",
            "system_guidance": ""
        }
        
        if next_state == ConversationState.AUTHENTICATION_REQUIRED:
            guidance.update({
                "suggested_actions": ["request_claim_number", "explain_verification"],
                "user_guidance": "I'll need to verify your identity to access your personal information.",
                "system_guidance": "Initiate authentication flow with warm, reassuring tone."
            })
        
        elif next_state == ConversationState.AUTHENTICATION_IN_PROGRESS:
            guidance.update({
                "suggested_actions": ["process_credentials", "provide_feedback"],
                "user_guidance": "Please provide the requested verification information.",
                "system_guidance": "Process authentication step and provide clear feedback."
            })
        
        elif next_state == ConversationState.DATA_RETRIEVAL:
            guidance.update({
                "suggested_actions": ["fetch_live_data", "prepare_response"],
                "user_guidance": "Let me get your current information.",
                "system_guidance": "Retrieve live data and prepare personalized response."
            })
        
        elif next_state == ConversationState.DATA_PRESENTATION:
            guidance.update({
                "suggested_actions": ["present_data", "offer_follow_up"],
                "user_guidance": "Here's your information!",
                "system_guidance": "Present data with WorkCom's personality and offer next steps."
            })
        
        elif next_state == ConversationState.FOLLOW_UP:
            guidance.update({
                "suggested_actions": ["ask_follow_up", "offer_assistance"],
                "user_guidance": "Is there anything else you'd like to know?",
                "system_guidance": "Engage in follow-up conversation and offer additional help."
            })
        
        return guidance
    
    # State Handlers
    
    def handle_initial_to_auth_required(self, message: str, context: Dict, 
                                      session: Dict, intent: Dict) -> Dict:
        """Handle transition from initial to authentication required"""
        return {
            "success": True,
            "transition_type": "auth_initiation",
            "response": "I'd be happy to help you with your personal information! 😊\n\nTo make sure I'm providing your details to the right person, I'll need to verify your identity first. This keeps your information safe and secure.\n\nCould you please provide your claim number?",
            "next_action": "collect_claim_number",
            "preserve_intent": True
        }
    
    def handle_auth_required_to_in_progress(self, message: str, context: Dict,
                                          session: Dict, intent: Dict) -> Dict:
        """Handle transition from auth required to in progress"""
        return {
            "success": True,
            "transition_type": "auth_processing",
            "response": "Thank you! Let me verify that information for you. 😊",
            "next_action": "process_authentication",
            "show_progress": True
        }
    
    def handle_auth_in_progress_to_authenticated(self, message: str, context: Dict,
                                               session: Dict, intent: Dict) -> Dict:
        """Handle transition from auth in progress to authenticated"""
        original_intent = context.get("original_intent")
        
        if original_intent and original_intent.get("intent_type") == "live_data":
            return {
                "success": True,
                "transition_type": "auth_complete_with_data",
                "response": "Excellent! I've verified your identity successfully. 😊\n\nNow let me get your information.",
                "next_action": "proceed_to_data_retrieval",
                "continue_flow": True
            }
        else:
            return {
                "success": True,
                "transition_type": "auth_complete",
                "response": "Excellent! I've verified your identity successfully. 😊\n\nYou now have secure access to your personal information. How can I help you today?",
                "next_action": "await_authenticated_request",
                "show_capabilities": True
            }
    
    def handle_authenticated_to_data_retrieval(self, message: str, context: Dict,
                                             session: Dict, intent: Dict) -> Dict:
        """Handle transition from authenticated to data retrieval"""
        return {
            "success": True,
            "transition_type": "data_fetch_initiation",
            "response": "Perfect! Let me get that information for you right away. 😊",
            "next_action": "fetch_live_data",
            "show_loading": True
        }
    
    def handle_data_retrieval_to_presentation(self, message: str, context: Dict,
                                            session: Dict, intent: Dict) -> Dict:
        """Handle transition from data retrieval to presentation"""
        return {
            "success": True,
            "transition_type": "data_presentation",
            "response": "",  # Will be filled by response assembler
            "next_action": "present_formatted_data",
            "offer_follow_up": True
        }
    
    def default_state_handler(self, message: str, context: Dict, session: Dict,
                            intent: Dict) -> Dict:
        """Default handler for unspecified transitions"""
        return {
            "success": True,
            "transition_type": "default",
            "response": "I'm here to help! 😊",
            "next_action": "continue_conversation"
        }
    
    # Utility Methods
    
    def remove_payment_references(self, response: str) -> str:
        """Remove payment-related information from response"""
        import re
        
        # Remove payment amounts
        response = re.sub(r'\$[\d,]+\.?\d*', '[Payment Amount]', response)
        
        # Remove payment dates
        response = re.sub(r'(Last Payment|Next Payment): [^\n]+', r'\1: [Contact support for details]', response)
        
        return response
    
    def remove_medical_references(self, response: str) -> str:
        """Remove medical information from response"""
        import re
        
        # Remove doctor names
        response = re.sub(r'Dr\. [A-Za-z\s]+', '[Medical Provider]', response)
        
        # Remove medical facility names
        response = re.sub(r'(Medical Center|Hospital|Clinic): [^\n]+', r'\1: [Contact support for details]', response)
        
        return response
    
    def get_available_actions(self, auth_level: str, permissions: List[str]) -> List[str]:
        """Get available actions based on authentication level"""
        actions = ["general_help", "contact_info", "process_guidance"]
        
        if auth_level in ["basic", "enhanced"]:
            actions.extend(["view_claim_status", "view_profile"])
        
        if auth_level == "enhanced":
            actions.extend(["view_payments", "update_contact", "upload_documents"])
        
        if "admin" in permissions:
            actions.extend(["system_admin", "bulk_operations"])
        
        return actions
    
    def handle_flow_error(self, current_state: str, message: str, context: Dict) -> Dict:
        """Handle conversation flow errors gracefully"""
        return {
            "success": False,
            "current_state": current_state,
            "next_state": ConversationState.ERROR_RECOVERY.value,
            "transition_result": {
                "success": False,
                "transition_type": "error_recovery",
                "response": "I'm sorry, but I'm having a small technical difficulty. 😔\n\nLet me try to help you in a different way. What would you like to know about?",
                "next_action": "restart_conversation"
            },
            "updated_context": context,
            "flow_guidance": {
                "next_state": ConversationState.ERROR_RECOVERY.value,
                "suggested_actions": ["restart", "contact_support"],
                "user_guidance": "Please try rephrasing your request.",
                "system_guidance": "Attempt graceful recovery or escalate to support."
            }
        }
    
    def define_flow_transitions(self) -> List[FlowTransition]:
        """Define valid conversation flow transitions"""
        return [
            FlowTransition(ConversationState.INITIAL, ConversationState.AUTHENTICATION_REQUIRED, "live_data_request"),
            FlowTransition(ConversationState.AUTHENTICATION_REQUIRED, ConversationState.AUTHENTICATION_IN_PROGRESS, "auth_credentials"),
            FlowTransition(ConversationState.AUTHENTICATION_IN_PROGRESS, ConversationState.AUTHENTICATED, "auth_success"),
            FlowTransition(ConversationState.AUTHENTICATED, ConversationState.DATA_RETRIEVAL, "live_data_request"),
            FlowTransition(ConversationState.DATA_RETRIEVAL, ConversationState.DATA_PRESENTATION, "data_retrieved"),
            FlowTransition(ConversationState.DATA_PRESENTATION, ConversationState.FOLLOW_UP, "data_presented"),
            FlowTransition(ConversationState.FOLLOW_UP, ConversationState.DATA_RETRIEVAL, "new_data_request")
        ]
    
    def define_state_handlers(self) -> Dict:
        """Define handlers for state transitions"""
        return {
            "initial_to_authentication_required": self.handle_initial_to_auth_required,
            "authentication_required_to_authentication_in_progress": self.handle_auth_required_to_in_progress,
            "authentication_in_progress_to_authenticated": self.handle_auth_in_progress_to_authenticated,
            "authenticated_to_data_retrieval": self.handle_authenticated_to_data_retrieval,
            "data_retrieval_to_data_presentation": self.handle_data_retrieval_to_presentation
        }
    
    def define_context_preservers(self) -> Dict:
        """Define context preservation rules"""
        return {
            "authentication_flow": ["original_intent", "user_preferences", "conversation_topic"],
            "data_flow": ["authentication_context", "user_permissions", "session_data"],
            "error_recovery": ["last_successful_state", "user_context", "conversation_history"]
        }
    
    def define_progressive_disclosure_rules(self) -> Dict:
        """Define progressive disclosure rules by authentication level"""
        return {
            "none": {
                "allowed_data": ["general_info", "contact_info", "process_guidance"],
                "restricted_data": ["personal_info", "payment_info", "medical_info"],
                "max_detail_level": "basic"
            },
            "basic": {
                "allowed_data": ["general_info", "contact_info", "claim_status", "profile_info"],
                "restricted_data": ["payment_info", "medical_details", "sensitive_documents"],
                "max_detail_level": "standard"
            },
            "enhanced": {
                "allowed_data": ["all_personal_data", "payment_info", "medical_info", "documents"],
                "restricted_data": ["admin_functions", "other_users_data"],
                "max_detail_level": "detailed"
            }
        }

# API Endpoints

@frappe.whitelist()
def optimize_conversation_flow():
    """
    API endpoint for conversation flow optimization
    """
    try:
        data = frappe.local.form_dict
        message = data.get("message", "")
        current_state = data.get("current_state", "initial")
        conversation_context = data.get("conversation_context", {})
        user_session = data.get("user_session", {})
        intent_result = data.get("intent_result", {})
        
        optimizer = ConversationFlowOptimizer()
        result = optimizer.optimize_conversation_flow(
            message, current_state, conversation_context, user_session, intent_result
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        frappe.log_error(f"Conversation flow optimization API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def test_conversation_flows():
    """
    Test endpoint for conversation flow scenarios
    """
    try:
        test_scenarios = [
            {
                "name": "Authentication Flow",
                "steps": [
                    {"state": "initial", "message": "I need my claim status", "intent": {"intent_type": "live_data", "requires_auth": True}},
                    {"state": "authentication_required", "message": "WC-2024-001234", "intent": {"intent_type": "authentication"}},
                    {"state": "authentication_in_progress", "message": "John Doe", "intent": {"intent_type": "authentication"}},
                    {"state": "authenticated", "message": "", "intent": {"intent_type": "live_data"}}
                ]
            },
            {
                "name": "Direct Data Request",
                "steps": [
                    {"state": "authenticated", "message": "Show me my payments", "intent": {"intent_type": "live_data", "data_category": "payment_info"}}
                ]
            }
        ]
        
        optimizer = ConversationFlowOptimizer()
        results = []
        
        for scenario in test_scenarios:
            scenario_result = {"name": scenario["name"], "steps": []}
            
            for step in scenario["steps"]:
                result = optimizer.optimize_conversation_flow(
                    step["message"],
                    step["state"],
                    {},
                    {"identity_verified": step["state"] in ["authenticated", "data_retrieval"]},
                    step["intent"]
                )
                
                scenario_result["steps"].append({
                    "input_state": step["state"],
                    "output_state": result.get("next_state"),
                    "success": result.get("success", False),
                    "has_response": bool(result.get("transition_result", {}).get("response"))
                })
            
            results.append(scenario_result)
        
        return {
            "success": True,
            "data": {
                "test_scenarios": results,
                "total_scenarios": len(results),
                "total_steps": sum(len(s["steps"]) for s in results)
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Conversation flow test error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

