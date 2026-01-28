"""
Enhanced Greeting Logic Service for WCFCB Assistant CRM Phase 2
Provides intelligent greeting management and conversation flow optimization
"""

import frappe
from frappe.utils import now, get_time, get_datetime
from typing import Dict, List, Any, Optional
import re
from datetime import datetime, time


class EnhancedGreetingService:
    """
    Enhanced greeting service that provides intelligent, context-aware greetings
    based on user persona, time of day, conversation history, and user preferences
    """
    
    def __init__(self):
        # Time-based greeting patterns
        self.time_greetings = {
            'morning': {'start': time(5, 0), 'end': time(12, 0), 'greeting': 'Good morning'},
            'afternoon': {'start': time(12, 0), 'end': time(17, 0), 'greeting': 'Good afternoon'},
            'evening': {'start': time(17, 0), 'end': time(21, 0), 'greeting': 'Good evening'},
            'night': {'start': time(21, 0), 'end': time(5, 0), 'greeting': 'Good evening'}
        }
        
        # Persona-specific greeting styles
        self.persona_greetings = {
            'employer': {
                'formal': "Good {time_period}! I'm Anna, your WCFCB business assistant.",
                'professional': "Hello! I'm Anna from WCFCB, ready to assist with your business needs.",
                'returning': "Welcome back! I'm here to help with your business requirements."
            },
            'beneficiary': {
                'supportive': "Hello! I'm Anna, and I'm here to help you with your benefits and services.",
                'warm': "Hi there! I'm Anna, your friendly WCFCB assistant.",
                'returning': "Good to see you again! How can I help you today?"
            },
            'supplier': {
                'professional': "Good {time_period}! I'm Anna, your WCFCB procurement assistant.",
                'business': "Hello! I'm Anna, ready to assist with your supplier needs.",
                'returning': "Welcome back! I'm here to help with your supplier requirements."
            },
            'wcfcb_staff': {
                'colleague': "Hi! I'm Anna, your internal assistant.",
                'professional': "Good {time_period}! Ready to assist with internal processes.",
                'returning': "Hello again! What can I help you with today?"
            },
            'general': {
                'friendly': "Hello! I'm Anna, your WCFCB assistant.",
                'professional': "Good {time_period}! I'm Anna, how can I help you today?",
                'returning': "Welcome back! I'm Anna, ready to assist you."
            }
        }
        
        # Conversation flow patterns
        self.flow_patterns = {
            'first_time': ['greeting', 'introduction', 'capability_overview', 'assistance_offer'],
            'returning': ['greeting', 'acknowledgment', 'assistance_offer'],
            'urgent': ['greeting', 'immediate_assistance'],
            'follow_up': ['greeting', 'status_check', 'assistance_offer']
        }
        
        # Anna's personality traits for greetings
        self.anna_personality = {
            'core_traits': ['helpful', 'professional', 'empathetic', 'efficient'],
            'communication_style': 'warm_professional',
            'brand_values': ['customer_focused', 'reliable', 'accessible', 'supportive']
        }
    
    def generate_intelligent_greeting(self, user_context: Dict, conversation_history: List[Dict] = None,
                                    user_preferences: Dict = None) -> Dict[str, Any]:
        """
        Generate an intelligent, context-aware greeting
        
        Args:
            user_context: User context including persona, session info
            conversation_history: Previous conversation history
            user_preferences: User's greeting preferences
            
        Returns:
            Dict containing greeting and conversation flow recommendations
        """
        try:
            # Analyze user context
            persona = user_context.get('persona', 'general')
            is_returning_user = self._is_returning_user(user_context, conversation_history)
            urgency_level = self._detect_urgency(user_context)
            
            # Determine greeting style
            greeting_style = self._determine_greeting_style(persona, is_returning_user, urgency_level, user_preferences)
            
            # Generate time-appropriate greeting
            time_period = self._get_time_period()
            base_greeting = self._get_base_greeting(persona, greeting_style, time_period)
            
            # Add personalization
            personalized_greeting = self._add_personalization(base_greeting, user_context, is_returning_user)
            
            # Generate conversation flow
            flow_type = self._determine_flow_type(is_returning_user, urgency_level, conversation_history)
            conversation_flow = self._generate_conversation_flow(flow_type, persona)
            
            # Add Anna's personality touches
            enhanced_greeting = self._add_anna_personality(personalized_greeting, persona)
            
            # Generate quick action suggestions
            quick_actions = self._generate_quick_actions(persona, user_context)
            
            return {
                'success': True,
                'greeting': enhanced_greeting,
                'greeting_style': greeting_style,
                'conversation_flow': conversation_flow,
                'quick_actions': quick_actions,
                'personalization_applied': True,
                'flow_type': flow_type,
                'anna_personality_traits': self.anna_personality['core_traits'],
                'timestamp': now()
            }
            
        except Exception as e:
            frappe.log_error(f"Enhanced greeting generation error: {str(e)}", "EnhancedGreetingService")
            return self._get_fallback_greeting(user_context.get('persona', 'general'))
    
    def _is_returning_user(self, user_context: Dict, conversation_history: List[Dict]) -> bool:
        """Determine if user is returning based on context and history"""
        
        # Check if user has previous conversations
        if conversation_history and len(conversation_history) > 0:
            return True
        
        # Check session information
        if user_context.get('session_count', 0) > 1:
            return True
        
        # Check user registration status
        if user_context.get('user') != 'Guest':
            return True
        
        return False
    
    def _detect_urgency(self, user_context: Dict) -> str:
        """Detect urgency level from user context"""
        
        # Check for urgent keywords in initial message
        initial_message = user_context.get('initial_message', '').lower()
        urgent_keywords = ['urgent', 'emergency', 'asap', 'immediately', 'help', 'problem', 'issue']
        
        if any(keyword in initial_message for keyword in urgent_keywords):
            return 'high'
        
        # Check user context flags
        if user_context.get('priority') == 'high':
            return 'high'
        
        return 'normal'
    
    def _determine_greeting_style(self, persona: str, is_returning: bool, urgency: str, preferences: Dict) -> str:
        """Determine appropriate greeting style"""
        
        # User preferences override
        if preferences and preferences.get('greeting_style'):
            return preferences['greeting_style']
        
        # Urgency-based style
        if urgency == 'high':
            return 'professional'  # Direct and efficient for urgent matters
        
        # Persona and returning user based style
        if is_returning:
            return 'returning'
        
        # Default persona styles
        persona_defaults = {
            'employer': 'professional',
            'beneficiary': 'supportive',
            'supplier': 'business',
            'wcfcb_staff': 'colleague',
            'general': 'friendly'
        }
        
        return persona_defaults.get(persona, 'friendly')
    
    def _get_time_period(self) -> str:
        """Get current time period for time-appropriate greetings"""
        current_time = get_time()
        
        for period, time_range in self.time_greetings.items():
            if period == 'night':
                # Handle night time (crosses midnight)
                if current_time >= time_range['start'] or current_time < time_range['end']:
                    return period
            else:
                if time_range['start'] <= current_time < time_range['end']:
                    return period
        
        return 'day'  # Fallback
    
    def _get_base_greeting(self, persona: str, style: str, time_period: str) -> str:
        """Get base greeting based on persona and style"""
        
        persona_greetings = self.persona_greetings.get(persona, self.persona_greetings['general'])
        greeting_template = persona_greetings.get(style, persona_greetings.get('professional', 'Hello!'))
        
        # Replace time period placeholder
        if '{time_period}' in greeting_template:
            time_greeting = self.time_greetings.get(time_period, {}).get('greeting', 'Hello')
            greeting_template = greeting_template.replace('{time_period}', time_greeting.lower())
        
        return greeting_template
    
    def _add_personalization(self, base_greeting: str, user_context: Dict, is_returning: bool) -> str:
        """Add personalization to the greeting"""
        
        personalized = base_greeting
        
        # Add user name if available
        user_name = user_context.get('user_name') or user_context.get('full_name')
        if user_name and user_name != 'Guest':
            personalized = f"{personalized.rstrip('!')} {user_name}!"
        
        # Add returning user acknowledgment
        if is_returning:
            personalized += " Welcome back!"
        
        return personalized
    
    def _determine_flow_type(self, is_returning: bool, urgency: str, conversation_history: List[Dict]) -> str:
        """Determine conversation flow type"""
        
        if urgency == 'high':
            return 'urgent'
        
        if is_returning:
            # Check if this is a follow-up to previous conversation
            if conversation_history and len(conversation_history) > 0:
                last_conversation = conversation_history[-1]
                if last_conversation.get('status') == 'pending':
                    return 'follow_up'
            return 'returning'
        
        return 'first_time'
    
    def _generate_conversation_flow(self, flow_type: str, persona: str) -> List[Dict[str, str]]:
        """Generate conversation flow steps"""
        
        flow_steps = []
        pattern = self.flow_patterns.get(flow_type, self.flow_patterns['first_time'])
        
        for step in pattern:
            if step == 'greeting':
                flow_steps.append({'step': 'greeting', 'completed': True})
            elif step == 'introduction':
                flow_steps.append({
                    'step': 'introduction',
                    'message': "I'm here to help you with all your WCFCB needs.",
                    'completed': False
                })
            elif step == 'capability_overview':
                capabilities = self._get_persona_capabilities(persona)
                flow_steps.append({
                    'step': 'capability_overview',
                    'message': f"I can help you with: {', '.join(capabilities)}",
                    'completed': False
                })
            elif step == 'assistance_offer':
                flow_steps.append({
                    'step': 'assistance_offer',
                    'message': "What can I help you with today?",
                    'completed': False
                })
            elif step == 'acknowledgment':
                flow_steps.append({
                    'step': 'acknowledgment',
                    'message': "I'm ready to continue assisting you.",
                    'completed': False
                })
            elif step == 'immediate_assistance':
                flow_steps.append({
                    'step': 'immediate_assistance',
                    'message': "I'm here to help you right away. What do you need?",
                    'completed': False
                })
            elif step == 'status_check':
                flow_steps.append({
                    'step': 'status_check',
                    'message': "Let me check on your previous request.",
                    'completed': False
                })
        
        return flow_steps
    
    def _get_persona_capabilities(self, persona: str) -> List[str]:
        """Get capabilities relevant to user persona"""
        
        capabilities = {
            'employer': ['business registration', 'employee contributions', 'compliance reporting'],
            'beneficiary': ['payment status', 'benefit claims', 'document submission'],
            'supplier': ['procurement processes', 'vendor registration', 'payment tracking'],
            'wcfcb_staff': ['internal processes', 'system administration', 'policy guidance'],
            'general': ['information', 'guidance', 'support']
        }
        
        return capabilities.get(persona, capabilities['general'])
    
    def _add_anna_personality(self, greeting: str, persona: str) -> str:
        """Add Anna's personality touches to the greeting"""
        
        # Add empathy and warmth while maintaining professionalism
        if persona == 'beneficiary':
            # More supportive tone for beneficiaries
            if not any(word in greeting.lower() for word in ['here to help', 'assist']):
                greeting += " I'm here to support you every step of the way."
        
        # Add efficiency indicator for urgent matters
        if 'immediately' in greeting.lower() or 'right away' in greeting.lower():
            greeting += " 😊"
        
        return greeting
    
    def _generate_quick_actions(self, persona: str, user_context: Dict) -> List[Dict[str, str]]:
        """Generate quick action suggestions based on persona"""
        
        quick_actions = {
            'employer': [
                {'action': 'Check Business Status', 'type': 'query'},
                {'action': 'Submit Monthly Return', 'type': 'process'},
                {'action': 'Employee Registration', 'type': 'registration'}
            ],
            'beneficiary': [
                {'action': 'Check Payment Status', 'type': 'query'},
                {'action': 'Submit Claim', 'type': 'claim'},
                {'action': 'Download Certificate', 'type': 'document'}
            ],
            'supplier': [
                {'action': 'Check Payment Status', 'type': 'query'},
                {'action': 'Submit Invoice', 'type': 'process'},
                {'action': 'Update Details', 'type': 'update'}
            ],
            'wcfcb_staff': [
                {'action': 'System Status', 'type': 'admin'},
                {'action': 'User Management', 'type': 'admin'},
                {'action': 'Reports', 'type': 'reporting'}
            ],
            'general': [
                {'action': 'Get Information', 'type': 'query'},
                {'action': 'Contact Support', 'type': 'support'},
                {'action': 'Browse Services', 'type': 'navigation'}
            ]
        }
        
        return quick_actions.get(persona, quick_actions['general'])
    
    def _get_fallback_greeting(self, persona: str) -> Dict[str, Any]:
        """Get fallback greeting in case of errors"""
        
        fallback_greetings = {
            'employer': "Hello! I'm Anna, your WCFCB business assistant. How can I help you today?",
            'beneficiary': "Hello! I'm Anna, and I'm here to help you with your benefits and services.",
            'supplier': "Hello! I'm Anna, your WCFCB procurement assistant. How can I assist you?",
            'wcfcb_staff': "Hi! I'm Anna, your internal assistant. What can I help you with?",
            'general': "Hello! I'm Anna, your WCFCB assistant. How can I help you today?"
        }
        
        return {
            'success': True,
            'greeting': fallback_greetings.get(persona, fallback_greetings['general']),
            'greeting_style': 'professional',
            'conversation_flow': [{'step': 'greeting', 'completed': True}],
            'quick_actions': [],
            'personalization_applied': False,
            'flow_type': 'first_time',
            'fallback_used': True
        }
