"""
Advanced Conversation Logic Service for WCFCB Assistant CRM
Handles conversation flow, context tracking, and intelligent routing
"""

import frappe
from frappe.utils import now, get_datetime
from typing import Dict, List, Any, Optional
import json
import re
from datetime import datetime, timedelta


class ConversationLogicService:
    """
    Advanced conversation logic service that manages conversation flow,
    context tracking, and intelligent routing based on conversation state
    """
    
    def __init__(self):
        self.conversation_states = {
            'greeting': 'initial_contact',
            'information_gathering': 'collecting_details',
            'problem_solving': 'addressing_issue',
            'escalation': 'transferring_to_human',
            'resolution': 'issue_resolved',
            'follow_up': 'checking_satisfaction'
        }
        
        self.conversation_patterns = {
            'greeting_patterns': [
                r'\b(hello|hi|hey|good\s+(morning|afternoon|evening)|greetings)\b',
                r'\b(how\s+are\s+you|what\'s\s+up|howdy)\b'
            ],
            'question_patterns': [
                r'\b(what|how|when|where|why|who|which)\b',
                r'\?',
                r'\b(can\s+you|could\s+you|would\s+you)\b'
            ],
            'urgency_patterns': [
                r'\b(urgent|emergency|asap|immediately|right\s+now)\b',
                r'\b(help\s+me|need\s+help|problem|issue|trouble)\b'
            ],
            'frustration_patterns': [
                r'\b(frustrated|angry|upset|annoyed|disappointed)\b',
                r'\b(not\s+working|broken|failed|error)\b'
            ]
        }
    
    def analyze_conversation_flow(self, conversation_history: List[Dict], current_message: str, 
                                user_context: Dict) -> Dict[str, Any]:
        """
        Analyze the conversation flow and determine the next best action
        
        Args:
            conversation_history: List of previous messages in conversation
            current_message: Current user message
            user_context: User context information
            
        Returns:
            Dict containing conversation analysis and recommendations
        """
        try:
            # Analyze conversation state
            current_state = self._determine_conversation_state(conversation_history, current_message)
            
            # Detect conversation patterns
            patterns = self._detect_conversation_patterns(current_message)
            
            # Analyze conversation context
            context_analysis = self._analyze_conversation_context(conversation_history, user_context)
            
            # Determine next action
            next_action = self._determine_next_action(current_state, patterns, context_analysis)
            
            # Generate conversation insights
            insights = self._generate_conversation_insights(conversation_history, current_message)
            
            return {
                'success': True,
                'conversation_state': current_state,
                'detected_patterns': patterns,
                'context_analysis': context_analysis,
                'next_action': next_action,
                'insights': insights,
                'recommendations': self._generate_recommendations(current_state, patterns),
                'timestamp': now()
            }
            
        except Exception as e:
            frappe.log_error(f"Conversation Logic Analysis Error: {str(e)}", "ConversationLogicService")
            return {
                'success': False,
                'error': str(e),
                'conversation_state': 'unknown',
                'next_action': 'fallback_response'
            }
    
    def _determine_conversation_state(self, conversation_history: List[Dict], current_message: str) -> str:
        """Determine the current state of the conversation"""
        
        # If no history, this is likely a greeting
        if not conversation_history:
            if self._matches_pattern(current_message, self.conversation_patterns['greeting_patterns']):
                return 'greeting'
            return 'information_gathering'
        
        # Analyze recent conversation flow
        recent_messages = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
        
        # Check for escalation indicators
        if self._matches_pattern(current_message, self.conversation_patterns['frustration_patterns']):
            return 'escalation'
        
        # Check for questions (information gathering)
        if self._matches_pattern(current_message, self.conversation_patterns['question_patterns']):
            return 'information_gathering'
        
        # Check for problem-solving context
        problem_keywords = ['issue', 'problem', 'help', 'support', 'fix', 'resolve']
        if any(keyword in current_message.lower() for keyword in problem_keywords):
            return 'problem_solving'
        
        # Default to information gathering
        return 'information_gathering'
    
    def _detect_conversation_patterns(self, message: str) -> Dict[str, bool]:
        """Detect various conversation patterns in the message"""
        
        patterns = {}
        
        for pattern_type, pattern_list in self.conversation_patterns.items():
            patterns[pattern_type] = self._matches_pattern(message, pattern_list)
        
        # Additional pattern detection
        patterns['contains_numbers'] = bool(re.search(r'\d+', message))
        patterns['contains_email'] = bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message))
        patterns['contains_phone'] = bool(re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', message))
        patterns['is_short_response'] = len(message.split()) <= 3
        patterns['is_long_message'] = len(message.split()) > 50
        
        return patterns
    
    def _matches_pattern(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the given regex patterns"""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _analyze_conversation_context(self, conversation_history: List[Dict], user_context: Dict) -> Dict[str, Any]:
        """Analyze the broader context of the conversation"""
        
        context = {
            'conversation_length': len(conversation_history),
            'user_engagement_level': 'medium',
            'topic_consistency': True,
            'response_time_pattern': 'normal',
            'user_satisfaction_indicators': []
        }
        
        if conversation_history:
            # Analyze engagement level
            avg_message_length = sum(len(msg.get('content', '').split()) for msg in conversation_history) / len(conversation_history)
            if avg_message_length > 20:
                context['user_engagement_level'] = 'high'
            elif avg_message_length < 5:
                context['user_engagement_level'] = 'low'
            
            # Check for satisfaction indicators
            satisfaction_positive = ['thank', 'thanks', 'helpful', 'great', 'perfect', 'solved']
            satisfaction_negative = ['not helpful', 'frustrated', 'still not working', 'confused']
            
            recent_messages = ' '.join([msg.get('content', '') for msg in conversation_history[-3:]])
            
            for indicator in satisfaction_positive:
                if indicator in recent_messages.lower():
                    context['user_satisfaction_indicators'].append(f'positive: {indicator}')
            
            for indicator in satisfaction_negative:
                if indicator in recent_messages.lower():
                    context['user_satisfaction_indicators'].append(f'negative: {indicator}')
        
        return context
    
    def _determine_next_action(self, state: str, patterns: Dict, context: Dict) -> Dict[str, Any]:
        """Determine the next best action based on conversation analysis"""
        
        action = {
            'type': 'respond',
            'priority': 'medium',
            'suggested_response_type': 'informational',
            'escalation_needed': False,
            'follow_up_required': False
        }
        
        # State-based action determination
        if state == 'greeting':
            action.update({
                'type': 'greet',
                'suggested_response_type': 'greeting',
                'priority': 'high'
            })
        
        elif state == 'escalation':
            action.update({
                'type': 'escalate',
                'escalation_needed': True,
                'priority': 'high',
                'suggested_response_type': 'escalation'
            })
        
        elif state == 'problem_solving':
            action.update({
                'type': 'solve',
                'suggested_response_type': 'solution',
                'follow_up_required': True
            })
        
        # Pattern-based adjustments
        if patterns.get('urgency_patterns'):
            action['priority'] = 'high'
        
        if patterns.get('frustration_patterns'):
            action['suggested_response_type'] = 'empathetic'
            action['escalation_needed'] = True
        
        # Context-based adjustments
        if context.get('user_engagement_level') == 'low':
            action['suggested_response_type'] = 'engaging'
        
        return action
    
    def _generate_conversation_insights(self, conversation_history: List[Dict], current_message: str) -> Dict[str, Any]:
        """Generate insights about the conversation"""
        
        insights = {
            'conversation_quality': 'good',
            'user_journey_stage': 'information_seeking',
            'potential_resolution_path': 'standard_support',
            'estimated_resolution_time': '5-10 minutes',
            'confidence_level': 0.8
        }
        
        # Analyze conversation quality
        if conversation_history:
            if len(conversation_history) > 10:
                insights['conversation_quality'] = 'extended'
            elif any('thank' in msg.get('content', '').lower() for msg in conversation_history):
                insights['conversation_quality'] = 'positive'
        
        # Determine user journey stage
        if not conversation_history:
            insights['user_journey_stage'] = 'initial_contact'
        elif len(conversation_history) < 3:
            insights['user_journey_stage'] = 'information_gathering'
        else:
            insights['user_journey_stage'] = 'problem_resolution'
        
        return insights
    
    def _generate_recommendations(self, state: str, patterns: Dict) -> List[str]:
        """Generate recommendations for handling the conversation"""
        
        recommendations = []
        
        # State-based recommendations
        if state == 'greeting':
            recommendations.append("Use warm, persona-appropriate greeting")
            recommendations.append("Offer specific help options")
        
        elif state == 'escalation':
            recommendations.append("Acknowledge user frustration")
            recommendations.append("Offer human agent transfer")
            recommendations.append("Provide escalation timeline")
        
        elif state == 'problem_solving':
            recommendations.append("Provide step-by-step guidance")
            recommendations.append("Offer multiple solution options")
            recommendations.append("Schedule follow-up check")
        
        # Pattern-based recommendations
        if patterns.get('urgency_patterns'):
            recommendations.append("Prioritize immediate assistance")
            recommendations.append("Provide direct contact options")
        
        if patterns.get('question_patterns'):
            recommendations.append("Provide comprehensive answers")
            recommendations.append("Anticipate follow-up questions")
        
        return recommendations
    
    def track_conversation_metrics(self, conversation_id: str, metrics: Dict) -> bool:
        """Track conversation metrics for analytics"""
        try:
            # This would typically save to a conversation metrics table
            # For now, we'll log the metrics
            frappe.logger().info(f"Conversation Metrics - ID: {conversation_id}, Metrics: {json.dumps(metrics)}")
            return True
        except Exception as e:
            frappe.log_error(f"Error tracking conversation metrics: {str(e)}", "ConversationLogicService")
            return False
