# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import re
import json
from difflib import SequenceMatcher
import math
import uuid
import time
from datetime import datetime
import logging


class IntentDetectionLogger:
    """Minimal fallback logger - verbose logging removed"""

    def generate_request_id(self):
        """Generate unique request ID for traceability"""
        return str(uuid.uuid4())[:8]

    def log_raw_input(self, *args, **kwargs):
        """Verbose logging removed"""
        pass

    def log_preprocessing_step(self, *args, **kwargs):
        """Verbose logging removed"""
        pass

    def log_confidence_scores(self, *args, **kwargs):
        """Verbose logging removed"""
        pass

    def log_final_intent_selection(self, *args, **kwargs):
        """Verbose logging removed"""
        pass

    def log_fallback_triggered(self, *args, **kwargs):
        """Verbose logging removed"""
        pass

    def log_context_analysis(self, *args, **kwargs):
        """Verbose logging removed"""
        pass

    def log_performance_metrics(self, *args, **kwargs):
        """Verbose logging removed"""
        pass


class IntentRecognitionService:
    """Advanced intent recognition service for chatbot conversation flow"""

    def __init__(self):
        self.intents = []
        self.logger = IntentDetectionLogger()
        self.load_intents()
    
    def load_intents(self):
        """Load all active intent definitions"""
        try:
            self.intents = frappe.db.sql("""
                SELECT name, intent_name, flow_type, priority, confidence_threshold,
                       escalation_threshold, description
                FROM `tabIntent Definition`
                WHERE is_active = 1
                ORDER BY priority ASC, confidence_threshold DESC
            """, as_dict=True)
            
            # Load training data for each intent
            for intent in self.intents:
                intent['keywords'] = self.get_intent_keywords(intent['name'])
                intent['training_examples'] = self.get_training_examples(intent['name'])
                intent['follow_up_questions'] = self.get_follow_up_questions(intent['name'])
                
        except Exception as e:
            frappe.log_error(f"Error loading intents: {str(e)}", "Intent Recognition Service")
            self.intents = []
    
    def get_intent_keywords(self, intent_name):
        """Get keywords for a specific intent"""
        try:
            return frappe.db.sql("""
                SELECT keyword, language, weight, keyword_type
                FROM `tabIntent Keyword`
                WHERE parent = %s AND is_active = 1
                ORDER BY weight DESC
            """, (intent_name,), as_dict=True)
        except:
            return []
    
    def get_training_examples(self, intent_name):
        """Get training examples for a specific intent"""
        try:
            return frappe.db.sql("""
                SELECT example_text, language, weight
                FROM `tabIntent Training Example`
                WHERE parent = %s AND is_active = 1
                ORDER BY weight DESC
            """, (intent_name,), as_dict=True)
        except:
            return []
    
    def get_follow_up_questions(self, intent_name):
        """Get follow-up questions for a specific intent"""
        try:
            return frappe.db.sql("""
                SELECT question_text, language, question_type, expected_response, next_intent
                FROM `tabFollow Up Question`
                WHERE parent = %s AND is_active = 1
                ORDER BY idx
            """, (intent_name,), as_dict=True)
        except:
            return []
    
    def recognize_intent(self, user_message, language='en', context=None):
        """Recognize intent from user message with comprehensive logging"""
        # Generate unique request ID for traceability
        request_id = self.logger.generate_request_id()
        start_time = time.time()

        # Log raw input
        self.logger.log_raw_input(request_id, user_message, language, context)

        if not self.intents:
            self.load_intents()

        # Log preprocessing step
        preprocessing_start = time.time()
        user_tokens = self.preprocess_message(user_message, request_id)
        preprocessing_time = (time.time() - preprocessing_start) * 1000

        self.logger.log_preprocessing_step(
            request_id,
            "tokenization",
            user_message,
            user_tokens,
            preprocessing_time
        )

        # Log context analysis if available
        if context:
            self.logger.log_context_analysis(request_id, context)

        best_intent = None
        best_score = 0
        intent_scores = {}

        # Calculate scores for all intents
        scoring_start = time.time()
        for intent in self.intents:
            score = self.calculate_intent_score(user_tokens, intent, user_message, language, request_id)
            intent_scores[intent['intent_name']] = score

            if score > best_score and score >= intent.get('confidence_threshold', 0.8):
                best_score = score
                best_intent = intent

        scoring_time = (time.time() - scoring_start) * 1000

        # Log confidence scores
        self.logger.log_confidence_scores(request_id, intent_scores, 0.8)

        if best_intent:
            # Log final intent selection
            escalate = best_score < best_intent.get('escalation_threshold', 0.5)
            self.logger.log_final_intent_selection(
                request_id,
                best_intent['intent_name'],
                best_score,
                best_intent.get('confidence_threshold', 0.8),
                escalate
            )

            # Update intent usage statistics
            self.update_intent_usage(best_intent['name'], best_score >= 0.9)

            # Log performance metrics
            total_time = (time.time() - start_time) * 1000
            self.logger.log_performance_metrics(
                request_id,
                total_time,
                {'preprocessing': preprocessing_time, 'scoring': scoring_time}
            )

            return {
                'success': True,
                'intent_name': best_intent['intent_name'],
                'flow_type': best_intent['flow_type'],
                'confidence': best_score,
                'intent_id': best_intent['name'],
                'description': best_intent['description'],
                'follow_up_questions': best_intent['follow_up_questions'],
                'escalate': escalate,
                'request_id': request_id
            }
        else:
            # Log fallback triggered
            self.logger.log_fallback_triggered(
                request_id,
                "No intent met confidence threshold",
                'unknown',
                0
            )

            # Log performance metrics
            total_time = (time.time() - start_time) * 1000
            self.logger.log_performance_metrics(
                request_id,
                total_time,
                {'preprocessing': preprocessing_time, 'scoring': scoring_time}
            )

            return {
                'success': False,
                'intent_name': 'unknown',
                'flow_type': 'General Inquiry',
                'confidence': 0,
                'escalate': True,
                'message': 'Could not determine specific intent',
                'request_id': request_id
            }
    
    def preprocess_message(self, message, request_id=None):
        """Preprocess user message for intent recognition with detailed logging"""
        if request_id and hasattr(self, 'logger'):
            # Log original message
            self.logger.log_preprocessing_step(
                request_id,
                "original_input",
                message,
                f"Length: {len(message)} chars"
            )

        # Convert to lowercase and remove punctuation
        cleaned_message = re.sub(r'[^\w\s]', '', message.lower())

        if request_id and hasattr(self, 'logger'):
            self.logger.log_preprocessing_step(
                request_id,
                "punctuation_removal",
                message,
                cleaned_message
            )

        # Tokenize and filter short words
        all_tokens = cleaned_message.split()
        filtered_tokens = [word for word in all_tokens if len(word) > 2]

        if request_id and hasattr(self, 'logger'):
            self.logger.log_preprocessing_step(
                request_id,
                "tokenization_filtering",
                f"{len(all_tokens)} tokens",
                f"{len(filtered_tokens)} tokens after filtering"
            )

        # Remove common stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his',
            'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy',
            'did', 'she', 'use', 'way', 'will', 'with', 'what', 'when', 'where',
            'why', 'this', 'that', 'they', 'them', 'there', 'their', 'then'
        }

        final_tokens = [token for token in filtered_tokens if token not in stop_words]

        if request_id and hasattr(self, 'logger'):
            removed_stop_words = [token for token in filtered_tokens if token in stop_words]
            self.logger.log_preprocessing_step(
                request_id,
                "stop_word_removal",
                f"Removed: {removed_stop_words}",
                f"Final tokens: {final_tokens}"
            )

        return final_tokens
    
    def calculate_intent_score(self, user_tokens, intent, original_message, language, request_id=None):
        """Calculate intent matching score with detailed logging"""
        # Keyword matching (50% weight)
        keyword_score = self.calculate_keyword_score(user_tokens, intent['keywords'], language) * 0.5

        # Training example similarity (40% weight)
        example_score = self.calculate_example_score(original_message, intent['training_examples'], language) * 0.4

        # Priority boost (10% weight) - higher priority intents get slight boost
        priority_score = (11 - intent.get('priority', 5)) / 10 * 0.1

        total_score = keyword_score + example_score + priority_score
        final_score = min(total_score, 1.0)  # Cap at 1.0

        # Log detailed scoring breakdown if request_id is available
        if request_id and hasattr(self, 'logger'):
            self.logger.log_preprocessing_step(
                request_id,
                f"score_calculation_{intent['intent_name']}",
                f"Keywords: {keyword_score:.4f}, Examples: {example_score:.4f}, Priority: {priority_score:.4f}",
                f"Total: {final_score:.4f}"
            )

        return final_score
    
    def calculate_keyword_score(self, user_tokens, keywords, language):
        """Calculate keyword matching score"""
        if not keywords:
            return 0
        
        # Filter keywords by language
        lang_keywords = [kw for kw in keywords if kw['language'] == language]
        if not lang_keywords and language != 'en':
            # Fallback to English keywords
            lang_keywords = [kw for kw in keywords if kw['language'] == 'en']
        
        if not lang_keywords:
            return 0
        
        total_weight = sum(kw['weight'] for kw in lang_keywords)
        matched_weight = 0
        
        for keyword_data in lang_keywords:
            keyword = keyword_data['keyword'].lower()
            weight = keyword_data['weight']
            keyword_type = keyword_data.get('keyword_type', 'Primary')
            
            # Check for exact keyword match
            if keyword in user_tokens:
                if keyword_type == 'Primary':
                    matched_weight += weight
                elif keyword_type == 'Secondary':
                    matched_weight += weight * 0.8
                elif keyword_type == 'Context':
                    matched_weight += weight * 0.6
                elif keyword_type == 'Negative':
                    matched_weight -= weight * 0.5  # Negative keywords reduce score
            else:
                # Check for partial matches
                for token in user_tokens:
                    if keyword in token or token in keyword:
                        if keyword_type == 'Primary':
                            matched_weight += weight * 0.5
                        elif keyword_type == 'Secondary':
                            matched_weight += weight * 0.4
                        elif keyword_type == 'Context':
                            matched_weight += weight * 0.3
                        break
        
        return max(matched_weight / total_weight, 0) if total_weight > 0 else 0
    
    def calculate_example_score(self, user_message, training_examples, language):
        """Calculate similarity with training examples"""
        if not training_examples:
            return 0
        
        # Filter examples by language
        lang_examples = [ex for ex in training_examples if ex['language'] == language]
        if not lang_examples and language != 'en':
            # Fallback to English examples
            lang_examples = [ex for ex in training_examples if ex['language'] == 'en']
        
        if not lang_examples:
            return 0
        
        best_similarity = 0
        user_lower = user_message.lower()
        
        for example in lang_examples:
            example_text = example['example_text'].lower()
            weight = example.get('weight', 1.0)
            
            # Calculate similarity using sequence matcher
            similarity = SequenceMatcher(None, user_lower, example_text).ratio()
            weighted_similarity = similarity * weight
            
            if weighted_similarity > best_similarity:
                best_similarity = weighted_similarity
        
        return best_similarity
    
    def update_intent_usage(self, intent_name, success=True):
        """Update intent usage statistics"""
        try:
            intent_doc = frappe.get_doc("Intent Definition", intent_name)
            intent_doc.update_usage_stats(success)
        except Exception as e:
            frappe.log_error(f"Error updating intent usage: {str(e)}", "Intent Recognition Service")
    
    def match_intent(self, user_message, specific_intent=None):
        """Match a specific intent (for testing)"""
        if specific_intent:
            intent_data = frappe.get_doc("Intent Definition", specific_intent)
            user_tokens = self.preprocess_message(user_message)

            intent_dict = {
                'name': intent_data.name,
                'intent_name': intent_data.intent_name,
                'flow_type': intent_data.flow_type,
                'priority': intent_data.priority,
                'confidence_threshold': intent_data.confidence_threshold,
                'keywords': self.get_intent_keywords(intent_data.name),
                'training_examples': self.get_training_examples(intent_data.name)
            }

            score = self.calculate_intent_score(user_tokens, intent_dict, user_message, 'en')

            return {
                'confidence': score,
                'threshold': intent_data.confidence_threshold,
                'intent_name': intent_data.intent_name,
                'flow_type': intent_data.flow_type
            }
        else:
            return self.recognize_intent(user_message)

    def get_conversation_context(self, session_id):
        """Get conversation context for better intent recognition"""
        try:
            # Get recent conversation history
            recent_messages = frappe.db.sql("""
                SELECT message, context_data, timestamp
                FROM `tabChat History`
                WHERE session_id = %s
                ORDER BY timestamp DESC
                LIMIT 5
            """, (session_id,), as_dict=True)

            context = {
                'previous_intents': [msg.get('intent_detected') for msg in recent_messages if msg.get('intent_detected')],
                'conversation_flow': self.analyze_conversation_flow(recent_messages),
                'user_preferences': self.get_user_preferences(session_id)
            }

            return context

        except Exception as e:
            frappe.log_error(f"Error getting conversation context: {str(e)}", "Intent Recognition Service")
            return {}

    def analyze_conversation_flow(self, messages):
        """Analyze conversation flow to predict likely next intents"""
        if not messages:
            return {}

        # Define common conversation flows
        flow_patterns = {
            'claim_submission': ['general_information', 'submit_new_claim', 'check_claim_status'],
            'employer_onboarding': ['general_information', 'employer_registration', 'premium_payment'],
            'information_seeking': ['general_information', 'contact_information', 'specific_service_info']
        }

        # Analyze recent intents to predict flow
        recent_intents = [msg.get('intent_detected') for msg in messages[:3] if msg.get('intent_detected')]

        for flow_name, pattern in flow_patterns.items():
            if any(intent in pattern for intent in recent_intents):
                return {
                    'current_flow': flow_name,
                    'likely_next_intents': pattern,
                    'flow_position': len([i for i in recent_intents if i in pattern])
                }

        return {}

    def get_user_preferences(self, session_id):
        """Get user preferences for personalized intent recognition"""
        try:
            # This could be expanded to include user profile data
            preferences = frappe.db.sql("""
                SELECT context_data
                FROM `tabChat History`
                WHERE session_id = %s AND context_data IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT 1
            """, (session_id,), as_dict=True)

            return preferences[0] if preferences else {}

        except:
            return {}

    def enhance_intent_with_context(self, intent_result, context):
        """Enhance intent recognition result with conversation context"""
        if not context:
            return intent_result

        # Boost confidence if intent fits conversation flow
        flow_info = context.get('conversation_flow', {})
        if flow_info.get('likely_next_intents'):
            if intent_result.get('intent_name') in flow_info['likely_next_intents']:
                intent_result['confidence'] = min(intent_result['confidence'] * 1.2, 1.0)
                intent_result['context_boost'] = True

        # Add conversation context to result
        intent_result['conversation_context'] = context

        return intent_result
