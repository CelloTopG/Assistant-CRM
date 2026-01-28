# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# Safe imports
try:
    import frappe
    from frappe.utils import now, add_to_date
    from frappe import _
    FRAPPE_AVAILABLE = True
except ImportError:
    frappe = None
    now = lambda: datetime.now().isoformat()
    add_to_date = lambda date, **kwargs: date + timedelta(**kwargs)
    _ = lambda x: x
    FRAPPE_AVAILABLE = False

def safe_log_error(message: str, title: str = "Intent Lock System"):
    """Safe error logging function"""
    try:
        if frappe:
            frappe.log_error(message, title)
        else:
            print(f"[{title}] {message}")
    except:
        print(f"[{title}] {message}")

class IntentLockSystem:
    """
    Intent Lock-In System for WCFCB Assistant CRM
    
    Implements session-based intent locking to maintain context and avoid 
    re-authentication for follow-up questions within the same intent scope.
    
    Key Features:
    - Lock onto specific user profile and intent after authentication
    - Maintain session context for subsequent questions
    - Prevent intent detection drift during conversations
    - Handle intent change requests explicitly
    - Session timeout and security management
    """
    
    def __init__(self):
        self.session_timeout_minutes = 30  # Session expires after 30 minutes
        self.max_questions_per_intent = 20  # Maximum questions before requiring re-authentication
        
        # Intent categories and their allowed follow-up patterns
        self.intent_categories = {
            'payment_related': {
                'primary_intents': ['payment_status', 'pension_inquiry', 'payment_history'],
                'follow_up_patterns': [
                    'when', 'how much', 'why', 'where', 'what about', 'can you',
                    'show me', 'tell me more', 'explain', 'details', 'history',
                    'next payment', 'last payment', 'amount', 'date', 'method'
                ],
                'related_queries': [
                    'payment method', 'bank details', 'payment schedule', 'amount changes',
                    'payment delays', 'payment confirmation', 'payment receipt'
                ]
            },
            'claims_related': {
                'primary_intents': ['claim_status', 'claim_submission', 'document_status'],
                'follow_up_patterns': [
                    'what documents', 'when will', 'how long', 'what happens next',
                    'can I submit', 'do I need', 'what about', 'status update',
                    'timeline', 'progress', 'requirements', 'next step'
                ],
                'related_queries': [
                    'required documents', 'claim timeline', 'claim approval', 'claim rejection',
                    'appeal process', 'medical reports', 'witness statements'
                ]
            },
            'account_related': {
                'primary_intents': ['account_info', 'contribution_status', 'employment_info'],
                'follow_up_patterns': [
                    'update', 'change', 'modify', 'correct', 'verify', 'confirm',
                    'how to', 'can I', 'what if', 'contact details', 'address',
                    'employment history', 'contribution history'
                ],
                'related_queries': [
                    'contact information', 'address changes', 'employment updates',
                    'contribution rates', 'benefit calculations', 'account status'
                ]
            },
            'employer_related': {
                'primary_intents': ['employer_services', 'compliance_status', 'employee_management'],
                'follow_up_patterns': [
                    'how to register', 'submit returns', 'add employee', 'remove employee',
                    'compliance requirements', 'penalty information', 'payment methods',
                    'reporting deadlines', 'employee contributions'
                ],
                'related_queries': [
                    'employee registration', 'contribution submissions', 'compliance reports',
                    'penalty calculations', 'return deadlines', 'employee benefits'
                ]
            }
        }
        
        # Session storage (in production, this would be Redis or database)
        self._sessions = {}

    def lock_intent(self, session_id: str, intent: str, user_profile: Dict[str, Any], 
                   authentication_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lock onto a specific intent after successful authentication.
        
        Args:
            session_id: Unique session identifier
            intent: The authenticated intent to lock onto
            user_profile: Complete user profile from authentication
            authentication_data: Authentication metadata
        
        Returns:
            Dict containing lock status and session information
        """
        try:
            # Determine intent category
            intent_category = self._get_intent_category(intent)
            
            # Create locked session
            session_data = {
                'locked_intent': intent,
                'intent_category': intent_category,
                'user_profile': user_profile,
                'authentication_data': authentication_data,
                'lock_timestamp': now(),
                'last_activity': now(),
                'question_count': 0,
                'authenticated': True,
                'session_active': True,
                'allowed_follow_ups': self._get_allowed_follow_ups(intent_category),
                'conversation_history': []
            }
            
            # Store session
            self._sessions[session_id] = session_data
            
            safe_log_error(f"Intent locked: {intent} for session {session_id}", "Intent Lock")
            
            return {
                'success': True,
                'locked_intent': intent,
                'intent_category': intent_category,
                'session_active': True,
                'user_type': user_profile.get('user_type'),
                'full_name': user_profile.get('full_name')
            }
            
        except Exception as e:
            safe_log_error(f"Intent lock error: {str(e)}")
            return {
                'success': False,
                'error': 'lock_failed'
            }

    def process_follow_up_question(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Process follow-up question within locked intent context.
        
        Args:
            session_id: Session identifier
            message: User's follow-up message
        
        Returns:
            Dict containing processing result and context
        """
        try:
            session_data = self._get_session_data(session_id)
            
            if not session_data or not session_data.get('session_active'):
                return {
                    'success': False,
                    'error': 'session_expired',
                    'requires_authentication': True
                }
            
            # Check session validity
            if not self._is_session_valid(session_data):
                self._expire_session(session_id)
                return {
                    'success': False,
                    'error': 'session_expired',
                    'requires_authentication': True
                }
            
            # Check if this is an intent change request
            if self._is_intent_change_request(message):
                return self._handle_intent_change_request(session_id, message)
            
            # Check if follow-up is allowed within current intent
            if not self._is_follow_up_allowed(session_data, message):
                return {
                    'success': False,
                    'error': 'follow_up_not_allowed',
                    'suggestion': self._suggest_alternative_action(session_data, message)
                }
            
            # Update session activity
            self._update_session_activity(session_id, message)
            
            # Process within locked intent context
            return {
                'success': True,
                'locked_intent': session_data['locked_intent'],
                'intent_category': session_data['intent_category'],
                'user_profile': session_data['user_profile'],
                'question_count': session_data['question_count'],
                'context_maintained': True,
                'requires_live_data': True
            }
            
        except Exception as e:
            safe_log_error(f"Follow-up processing error: {str(e)}")
            return {
                'success': False,
                'error': 'processing_failed'
            }

    def _get_intent_category(self, intent: str) -> str:
        """Determine which category an intent belongs to."""
        
        for category, config in self.intent_categories.items():
            if intent in config['primary_intents']:
                return category
        
        return 'general'

    def _get_allowed_follow_ups(self, intent_category: str) -> List[str]:
        """Get allowed follow-up patterns for an intent category."""
        
        category_config = self.intent_categories.get(intent_category, {})
        follow_ups = category_config.get('follow_up_patterns', [])
        related_queries = category_config.get('related_queries', [])
        
        return follow_ups + related_queries

    def _is_session_valid(self, session_data: Dict[str, Any]) -> bool:
        """Check if session is still valid."""
        
        try:
            # Check timeout
            last_activity = session_data.get('last_activity')
            if last_activity:
                last_activity_time = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                timeout_threshold = datetime.now() - timedelta(minutes=self.session_timeout_minutes)
                
                if last_activity_time < timeout_threshold:
                    return False
            
            # Check question count limit
            question_count = session_data.get('question_count', 0)
            if question_count >= self.max_questions_per_intent:
                return False
            
            # Check if session is marked as active
            return session_data.get('session_active', False)
            
        except Exception as e:
            safe_log_error(f"Session validation error: {str(e)}")
            return False

    def _is_intent_change_request(self, message: str) -> bool:
        """Check if user is requesting a different intent."""
        
        change_indicators = [
            'different question', 'something else', 'other topic', 'new request',
            'change topic', 'switch to', 'instead of', 'rather than',
            'actually', 'wait', 'forget that', 'never mind',
            'different service', 'other information', 'another question'
        ]
        
        message_lower = message.lower()
        
        # Check for explicit change indicators
        for indicator in change_indicators:
            if indicator in message_lower:
                return True
        
        # Check for new intent keywords that don't match current category
        new_intent_keywords = {
            'payment': ['payment', 'pay', 'money', 'salary', 'pension'],
            'claims': ['claim', 'compensation', 'injury', 'accident'],
            'account': ['account', 'profile', 'information', 'details'],
            'employment': ['employment', 'job', 'work', 'employer']
        }
        
        # If message contains strong keywords for a different intent category, consider it a change
        for intent_type, keywords in new_intent_keywords.items():
            keyword_count = sum(1 for keyword in keywords if keyword in message_lower)
            if keyword_count >= 2:  # Strong indication of intent change
                return True
        
        return False

    def _is_follow_up_allowed(self, session_data: Dict[str, Any], message: str) -> bool:
        """Check if follow-up question is allowed within current intent."""
        
        allowed_patterns = session_data.get('allowed_follow_ups', [])
        message_lower = message.lower()
        
        # Check against allowed follow-up patterns
        for pattern in allowed_patterns:
            if pattern.lower() in message_lower:
                return True
        
        # Check for general follow-up indicators
        general_follow_ups = [
            'what', 'when', 'where', 'why', 'how', 'can you', 'could you',
            'tell me', 'show me', 'explain', 'more details', 'more information',
            'clarify', 'confirm', 'verify', 'check', 'update'
        ]
        
        for indicator in general_follow_ups:
            if message_lower.startswith(indicator):
                return True
        
        return True  # Default to allowing follow-ups to maintain conversation flow

    def _handle_intent_change_request(self, session_id: str, message: str) -> Dict[str, Any]:
        """Handle explicit intent change requests."""
        
        session_data = self._get_session_data(session_id)
        current_intent = session_data.get('locked_intent')
        
        # Clear current session
        self._expire_session(session_id)
        
        return {
            'success': True,
            'intent_change_detected': True,
            'previous_intent': current_intent,
            'requires_new_authentication': True,
            'message': ("I understand you'd like to ask about something different. "
                       "Let me help you with your new request. What would you like to know?")
        }

    def _suggest_alternative_action(self, session_data: Dict[str, Any], message: str) -> str:
        """Suggest alternative action when follow-up is not allowed."""
        
        intent_category = session_data.get('intent_category')
        
        suggestions = {
            'payment_related': "For payment-related questions, you can ask about amounts, dates, methods, or history.",
            'claims_related': "For claims, you can ask about status, required documents, timelines, or next steps.",
            'account_related': "For account information, you can ask about personal details, contributions, or employment history.",
            'employer_related': "For employer services, you can ask about registration, compliance, or employee management."
        }
        
        return suggestions.get(intent_category, 
                             "Please ask questions related to your current topic, or let me know if you'd like to discuss something else.")

    def _update_session_activity(self, session_id: str, message: str):
        """Update session activity and conversation history."""
        
        if session_id in self._sessions:
            session_data = self._sessions[session_id]
            session_data['last_activity'] = now()
            session_data['question_count'] = session_data.get('question_count', 0) + 1
            
            # Add to conversation history (keep last 10 messages)
            history = session_data.get('conversation_history', [])
            history.append({
                'timestamp': now(),
                'message': message,
                'type': 'user_follow_up'
            })
            
            # Keep only last 10 messages
            if len(history) > 10:
                history = history[-10:]
            
            session_data['conversation_history'] = history

    def _get_session_data(self, session_id: str) -> Dict[str, Any]:
        """Get session data safely."""
        return self._sessions.get(session_id, {})

    def _expire_session(self, session_id: str):
        """Expire a session."""
        if session_id in self._sessions:
            self._sessions[session_id]['session_active'] = False
            safe_log_error(f"Session expired: {session_id}", "Intent Lock")

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current session status."""
        
        session_data = self._get_session_data(session_id)
        
        if not session_data:
            return {
                'session_exists': False,
                'authenticated': False,
                'locked_intent': None
            }
        
        return {
            'session_exists': True,
            'authenticated': session_data.get('authenticated', False),
            'session_active': session_data.get('session_active', False),
            'locked_intent': session_data.get('locked_intent'),
            'intent_category': session_data.get('intent_category'),
            'question_count': session_data.get('question_count', 0),
            'last_activity': session_data.get('last_activity'),
            'user_type': session_data.get('user_profile', {}).get('user_type'),
            'session_valid': self._is_session_valid(session_data) if session_data else False
        }

    def clear_session(self, session_id: str):
        """Clear session data completely."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            safe_log_error(f"Session cleared: {session_id}", "Intent Lock")

    def cleanup_expired_sessions(self):
        """Clean up expired sessions (should be called periodically)."""
        
        expired_sessions = []
        
        for session_id, session_data in self._sessions.items():
            if not self._is_session_valid(session_data):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.clear_session(session_id)
        
        if expired_sessions:
            safe_log_error(f"Cleaned up {len(expired_sessions)} expired sessions", "Intent Lock")
