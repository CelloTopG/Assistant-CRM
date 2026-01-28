#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Conversation State Manager for WCFCB Assistant CRM
=================================================

PHASE 5: Manages conversation state and user journey for natural flow.
Tracks authentication status, topics discussed, and conversation context.

Author: WCFCB Development Team
Created: 2025-08-17
License: MIT
"""

from typing import Dict, Any, List, Optional
from enum import Enum

# Safe imports
try:
    import frappe
    FRAPPE_AVAILABLE = True
except ImportError:
    frappe = None
    FRAPPE_AVAILABLE = False

def safe_log_error(message: str, title: str = "Conversation State Manager"):
    """Safe error logging function"""
    try:
        if frappe and hasattr(frappe, 'log_error'):
            frappe.log_error(message, title)
        else:
            print(f"[{title}] {message}")
    except:
        print(f"[{title}] {message}")

class ConversationState(Enum):
    """Conversation states for tracking user journey"""
    INITIAL = "initial"
    AUTHENTICATED = "authenticated"
    DATA_RETRIEVED = "data_retrieved"
    TOPIC_FOCUSED = "topic_focused"
    HELPING = "helping"
    COMPLETED = "completed"

class ConversationTopic(Enum):
    """Topics the user might be interested in"""
    ACCOUNT_INFO = "account_info"
    PAYMENT_STATUS = "payment_status"
    CLAIM_STATUS = "claim_status"
    BENEFITS = "benefits"
    EMPLOYER_SERVICES = "employer_services"
    GENERAL_INQUIRY = "general_inquiry"

class ConversationStateManager:
    """
    PHASE 5: Manages conversation state for natural flow and context awareness.
    
    Features:
    - Tracks user authentication status
    - Monitors conversation topics
    - Provides context for natural responses
    - Guides conversation flow
    """
    
    def __init__(self):
        self.states = {}  # session_id -> state_data
    
    def get_conversation_state(self, session_id: str, user_context: Dict = None) -> Dict[str, Any]:
        """
        Get current conversation state for a session.
        
        Args:
            session_id: Session identifier
            user_context: Current user context
            
        Returns:
            Dict: Conversation state information
        """
        try:
            if session_id not in self.states:
                self.states[session_id] = self._initialize_conversation_state()
            
            state_data = self.states[session_id]
            
            # Update state based on current context
            if user_context:
                self._update_state_from_context(state_data, user_context)
            
            return state_data
            
        except Exception as e:
            safe_log_error(f"Error getting conversation state: {str(e)}")
            return self._initialize_conversation_state()
    
    def update_conversation_state(self, session_id: str, message: str, intent: str, 
                                live_data_available: bool = False, response: str = "") -> Dict[str, Any]:
        """
        Update conversation state based on new interaction.
        
        Args:
            session_id: Session identifier
            message: User message
            intent: Detected intent
            live_data_available: Whether live data was found
            response: Bot response
            
        Returns:
            Dict: Updated conversation state
        """
        try:
            if session_id not in self.states:
                self.states[session_id] = self._initialize_conversation_state()
            
            state_data = self.states[session_id]
            
            # Update authentication status
            if self._contains_identifier(message):
                state_data['authentication_status'] = 'provided_identifier'
                state_data['state'] = ConversationState.AUTHENTICATED.value
            
            # Update data retrieval status
            if live_data_available:
                state_data['data_retrieved'] = True
                state_data['state'] = ConversationState.DATA_RETRIEVED.value
            
            # Update current topic
            topic = self._detect_conversation_topic(intent, message)
            if topic:
                state_data['current_topic'] = topic.value
                state_data['topics_discussed'].append(topic.value)
                state_data['state'] = ConversationState.TOPIC_FOCUSED.value
            
            # Update interaction count
            state_data['interaction_count'] += 1
            
            # Track message patterns
            state_data['message_history'].append({
                'message': message,
                'intent': intent,
                'response_length': len(response),
                'live_data_used': live_data_available
            })
            
            # Keep only recent history
            if len(state_data['message_history']) > 5:
                state_data['message_history'] = state_data['message_history'][-5:]
            
            # Remove duplicate topics
            state_data['topics_discussed'] = list(set(state_data['topics_discussed']))
            
            return state_data
            
        except Exception as e:
            safe_log_error(f"Error updating conversation state: {str(e)}")
            return self.states.get(session_id, self._initialize_conversation_state())
    
    def get_conversation_guidance(self, session_id: str) -> Dict[str, Any]:
        """
        Get guidance for natural conversation flow.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict: Conversation guidance information
        """
        try:
            state_data = self.states.get(session_id, self._initialize_conversation_state())
            
            guidance = {
                'should_greet': state_data['interaction_count'] == 1,
                'should_acknowledge_auth': (
                    state_data['authentication_status'] == 'provided_identifier' and 
                    state_data['interaction_count'] <= 2
                ),
                'should_reference_data': state_data['data_retrieved'],
                'should_continue_topic': len(state_data['topics_discussed']) > 0,
                'conversation_maturity': self._assess_conversation_maturity(state_data),
                'suggested_tone': self._suggest_tone(state_data),
                'context_hints': self._generate_context_hints(state_data)
            }
            
            return guidance
            
        except Exception as e:
            safe_log_error(f"Error getting conversation guidance: {str(e)}")
            return {
                'should_greet': True,
                'should_acknowledge_auth': False,
                'should_reference_data': False,
                'should_continue_topic': False,
                'conversation_maturity': 'new',
                'suggested_tone': 'friendly',
                'context_hints': []
            }
    
    def _initialize_conversation_state(self) -> Dict[str, Any]:
        """Initialize new conversation state"""
        return {
            'state': ConversationState.INITIAL.value,
            'authentication_status': 'none',
            'data_retrieved': False,
            'current_topic': None,
            'topics_discussed': [],
            'interaction_count': 0,
            'message_history': [],
            'user_satisfaction': 'unknown',
            'needs_escalation': False
        }
    
    def _update_state_from_context(self, state_data: Dict, user_context: Dict):
        """Update state based on user context"""
        try:
            # Check for live data
            if user_context.get('has_live_data') or user_context.get('live_data'):
                state_data['data_retrieved'] = True
            
            # Check for user identifier
            if user_context.get('user_identifier'):
                state_data['authentication_status'] = 'provided_identifier'
            
            # Update conversation history count
            conversation_history = user_context.get('conversation_history', [])
            if conversation_history:
                state_data['interaction_count'] = len(conversation_history)
                
        except Exception as e:
            safe_log_error(f"Error updating state from context: {str(e)}")
    
    def _contains_identifier(self, message: str) -> bool:
        """Check if message contains user identifier"""
        import re
        message_lower = message.lower()
        
        # Check for NRC pattern
        nrc_pattern = r'\d{6}/\d{2}/\d'
        if re.search(nrc_pattern, message):
            return True
        
        # Check for email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, message):
            return True
        
        # Check for customer ID pattern
        if any(keyword in message_lower for keyword in ['customer', 'cust-', 'ben-', 'my id']):
            return True
        
        return False
    
    def _detect_conversation_topic(self, intent: str, message: str) -> Optional[ConversationTopic]:
        """Detect conversation topic from intent and message"""
        intent_topic_map = {
            'account_status': ConversationTopic.ACCOUNT_INFO,
            'payment_status': ConversationTopic.PAYMENT_STATUS,
            'claim_status': ConversationTopic.CLAIM_STATUS,
            'pension_inquiry': ConversationTopic.BENEFITS,
            'employer_services': ConversationTopic.EMPLOYER_SERVICES
        }
        
        return intent_topic_map.get(intent, ConversationTopic.GENERAL_INQUIRY)
    
    def _assess_conversation_maturity(self, state_data: Dict) -> str:
        """Assess how mature/developed the conversation is"""
        interaction_count = state_data['interaction_count']
        
        if interaction_count <= 1:
            return 'new'
        elif interaction_count <= 3:
            return 'developing'
        elif interaction_count <= 6:
            return 'established'
        else:
            return 'extended'
    
    def _suggest_tone(self, state_data: Dict) -> str:
        """Suggest appropriate tone based on conversation state"""
        if state_data['interaction_count'] == 1:
            return 'welcoming'
        elif state_data['data_retrieved']:
            return 'helpful_and_informed'
        elif len(state_data['topics_discussed']) > 2:
            return 'collaborative'
        else:
            return 'friendly'
    
    def _generate_context_hints(self, state_data: Dict) -> List[str]:
        """Generate context hints for natural conversation"""
        hints = []
        
        if state_data['data_retrieved']:
            hints.append("Reference user's specific data")
        
        if len(state_data['topics_discussed']) > 1:
            hints.append("Acknowledge previous topics discussed")
        
        if state_data['interaction_count'] > 3:
            hints.append("Maintain conversation continuity")
        
        return hints

# Global instance
_conversation_state_manager = None

def get_conversation_state_manager() -> ConversationStateManager:
    """Get global conversation state manager instance"""
    global _conversation_state_manager
    if _conversation_state_manager is None:
        _conversation_state_manager = ConversationStateManager()
    return _conversation_state_manager
