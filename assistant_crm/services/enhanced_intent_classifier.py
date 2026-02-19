#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Enhanced Intent Classification Service
Core Integration Phase: Advanced intent recognition with live data detection
Preserves existing sentiment analysis while adding live data capabilities
"""

import frappe
import re
import json
import uuid
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

@dataclass
class IntentClassificationResult:
    """Structured result for intent classification"""
    intent_type: str  # 'static_info', 'live_data', 'authentication', 'general'
    confidence: float
    data_category: Optional[str] = None  # 'claim_status', 'payment_info', etc.
    requires_auth: bool = False
    user_persona: Optional[str] = None  # 'beneficiary', 'employer', 'staff'
    extracted_entities: Dict = None
    sentiment: str = 'neutral'  # 'positive', 'negative', 'neutral', 'urgent'
    context_awareness: Dict = None

class EnhancedIntentClassifierLogger:
    """Comprehensive logging utility for enhanced intent classification"""

    def __init__(self):
        self.logger = logging.getLogger('enhanced_intent_classifier')
        self.logger.setLevel(logging.DEBUG)

        # Create formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s'
        )

        # Ensure we have a handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def generate_request_id(self):
        """Generate unique request ID for traceability"""
        return str(uuid.uuid4())[:8]

    def log_classification_start(self, request_id, message, context, user_session):
        """Log the start of intent classification process"""
        extra_data = {
            'request_id': request_id,
            'message_length': len(message),
            'has_context': bool(context),
            'has_user_session': bool(user_session)
        }

        self.logger.info(
            f"Starting enhanced intent classification | Message: '{message}' | Context: {bool(context)} | Session: {bool(user_session)}",
            extra=extra_data
        )

        # Log to Frappe for persistence
        try:
            frappe.log_error(
                f"Enhanced Intent Classification - Start [{request_id}]: {message}",
                "Enhanced Intent Classification - Start"
            )
        except:
            pass

    def log_entity_extraction(self, request_id, message, extracted_entities):
        """Log entity extraction results"""
        extra_data = {
            'request_id': request_id,
            'entities_found': len(extracted_entities),
            'entity_types': list(extracted_entities.keys())
        }

        self.logger.debug(
            f"Entity extraction | Found {len(extracted_entities)} entities: {extracted_entities}",
            extra=extra_data
        )

    def log_sentiment_analysis(self, request_id, message, sentiment, confidence=None):
        """Log sentiment analysis results"""
        extra_data = {
            'request_id': request_id,
            'sentiment': sentiment,
            'confidence': confidence
        }

        self.logger.debug(
            f"Sentiment analysis | Sentiment: {sentiment} | Confidence: {confidence}",
            extra=extra_data
        )

    def log_user_persona_detection(self, request_id, detected_persona, source):
        """Log user persona detection"""
        extra_data = {
            'request_id': request_id,
            'persona': detected_persona,
            'source': source
        }

        self.logger.debug(
            f"User persona detection | Persona: {detected_persona} | Source: {source}",
            extra=extra_data
        )

    def log_intent_classification_result(self, request_id, result):
        """Log final intent classification result"""
        extra_data = {
            'request_id': request_id,
            'intent_type': result.intent_type,
            'confidence': result.confidence,
            'data_category': result.data_category,
            'requires_auth': result.requires_auth,
            'sentiment': result.sentiment
        }

        self.logger.info(
            f"Intent classification result | Type: {result.intent_type} | Confidence: {result.confidence:.4f} | Category: {result.data_category} | Auth: {result.requires_auth}",
            extra=extra_data
        )

        # Log to Frappe for persistence
        try:
            frappe.log_error(
                f"Enhanced Intent Classification - Result [{request_id}]: {result.intent_type} (Confidence: {result.confidence:.4f})",
                "Enhanced Intent Classification - Result"
            )
        except:
            pass


class EnhancedIntentClassifier:
    """
    Enhanced intent classification that integrates live data detection
    with existing conversation logic while preserving WorkCom's personality
    """

    def __init__(self):
        self.confidence_threshold = 0.7
        self.sentiment_keywords = self.load_sentiment_keywords()
        self.intent_patterns = self.load_intent_patterns()
        self.entity_extractors = self.load_entity_extractors()
        self.context_memory = {}
        self.logger = EnhancedIntentClassifierLogger()
        
    def classify_intent(self, message: str, conversation_context: Dict = None,
                       user_session: Dict = None) -> IntentClassificationResult:
        """
        Main intent classification method that preserves existing logic
        while adding live data detection capabilities with comprehensive logging
        """
        # Generate unique request ID for traceability
        request_id = self.logger.generate_request_id()
        start_time = time.time()

        try:
            conversation_context = conversation_context or {}
            user_session = user_session or {}

            # Log classification start
            self.logger.log_classification_start(request_id, message, conversation_context, user_session)

            # Normalize message for analysis
            normalization_start = time.time()
            normalized_message = self.normalize_message(message)
            normalization_time = (time.time() - normalization_start) * 1000

            # Extract entities first (claim numbers, dates, etc.)
            entity_start = time.time()
            extracted_entities = self.extract_entities(normalized_message)
            entity_time = (time.time() - entity_start) * 1000

            # Log entity extraction
            self.logger.log_entity_extraction(request_id, normalized_message, extracted_entities)

            # Analyze sentiment (preserve existing sentiment analysis)
            sentiment_start = time.time()
            sentiment = self.analyze_sentiment(normalized_message, conversation_context)
            sentiment_time = (time.time() - sentiment_start) * 1000

            # Log sentiment analysis
            self.logger.log_sentiment_analysis(request_id, normalized_message, sentiment)

            # Determine user persona from context or session
            persona_start = time.time()
            user_persona = self.determine_user_persona(user_session, conversation_context)
            persona_time = (time.time() - persona_start) * 1000

            # Log user persona detection
            persona_source = "session" if user_session.get("user_type") else "context" if conversation_context.get("user_persona") else "default"
            self.logger.log_user_persona_detection(request_id, user_persona, persona_source)

            # Classify intent with enhanced logic
            classification_start = time.time()
            intent_result = self.classify_intent_enhanced(
                normalized_message,
                extracted_entities,
                sentiment,
                user_persona,
                conversation_context
            )
            classification_time = (time.time() - classification_start) * 1000

            # Build comprehensive result
            result = IntentClassificationResult(
                intent_type=intent_result["intent_type"],
                confidence=intent_result["confidence"],
                data_category=intent_result.get("data_category"),
                requires_auth=intent_result.get("requires_auth", False),
                user_persona=user_persona,
                extracted_entities=extracted_entities,
                sentiment=sentiment,
                context_awareness=self.build_context_awareness(
                    normalized_message, conversation_context, user_session
                )
            )

            # Log final result
            self.logger.log_intent_classification_result(request_id, result)

            # Log performance metrics
            total_time = (time.time() - start_time) * 1000
            step_times = {
                'normalization': normalization_time,
                'entity_extraction': entity_time,
                'sentiment_analysis': sentiment_time,
                'persona_detection': persona_time,
                'classification': classification_time
            }

            try:
                frappe.log_error(
                    f"Enhanced Intent Classification - Performance [{request_id}]: Total: {total_time:.2f}ms | Steps: {step_times}",
                    "Enhanced Intent Classification - Performance"
                )
            except:
                pass

            # Update context memory for future classifications
            self.update_context_memory(message, result, conversation_context)

            return result

        except Exception as e:
            # Log error with request ID
            error_msg = f"Intent classification error [{request_id}]: {str(e)}"
            frappe.log_error(error_msg, "Enhanced Intent Classification - Error")

            # Return safe fallback result
            fallback_result = IntentClassificationResult(
                intent_type="general",
                confidence=0.5,
                sentiment="neutral",
                extracted_entities={},
                context_awareness={}
            )

            # Log fallback
            self.logger.log_intent_classification_result(request_id, fallback_result)

            return fallback_result
    
    def classify_intent_enhanced(self, message: str, entities: Dict, sentiment: str,
                               user_persona: str, context: Dict) -> Dict:
        """
        Enhanced intent classification with live data detection
        """
        
        # Check for authentication-related intents first
        auth_intent = self.check_authentication_intent(message, entities, context)
        if auth_intent["is_auth_intent"]:
            return {
                "intent_type": "authentication",
                "confidence": auth_intent["confidence"],
                "requires_auth": True,
                "auth_step": auth_intent["auth_step"]
            }
        
        # Check for live data requests
        live_data_intent = self.check_live_data_intent(message, entities, user_persona)
        if live_data_intent["is_live_data"]:
            return {
                "intent_type": "live_data",
                "confidence": live_data_intent["confidence"],
                "data_category": live_data_intent["data_category"],
                "requires_auth": live_data_intent["requires_auth"],
                "data_specificity": live_data_intent["specificity"]
            }
        
        # Check for static information requests
        static_intent = self.check_static_information_intent(message, entities)
        if static_intent["is_static_info"]:
            return {
                "intent_type": "static_info",
                "confidence": static_intent["confidence"],
                "info_category": static_intent["category"],
                "requires_auth": False
            }
        
        # Default to general conversation
        return {
            "intent_type": "general",
            "confidence": 0.6,
            "requires_auth": False
        }
    
    def check_live_data_intent(self, message: str, entities: Dict, user_persona: str) -> Dict:
        """
        Check if message is requesting live data based on user persona
        """
        message_lower = message.lower()
        
        # Persona-specific live data patterns
        live_data_patterns = {
            "beneficiary": {
                "claim_status": {
                    "keywords": ["my claim", "claim status", "claim progress", "case status", "claim update"],
                    "entities": ["claim_number"],
                    "confidence_boost": 0.2
                },
                "payment_info": {
                    "keywords": ["payment", "compensation", "benefits", "money", "paid", "when will i get"],
                    "entities": ["amount", "date"],
                    "confidence_boost": 0.15
                },
                "medical_info": {
                    "keywords": ["doctor", "medical", "treatment", "appointment", "provider"],
                    "entities": ["provider_name", "date"],
                    "confidence_boost": 0.1
                },
                "profile_info": {
                    "keywords": ["my information", "my details", "contact", "address", "update my"],
                    "entities": ["phone", "email", "address"],
                    "confidence_boost": 0.1
                }
            },
            "employer": {
                "employee_claims": {
                    "keywords": ["employee claims", "worker claims", "staff claims", "company claims"],
                    "entities": ["employee_name", "claim_number"],
                    "confidence_boost": 0.2
                },
                "compliance_status": {
                    "keywords": ["compliance", "premium", "safety", "training", "audit"],
                    "entities": ["date", "percentage"],
                    "confidence_boost": 0.15
                },
                "company_analytics": {
                    "keywords": ["report", "analytics", "statistics", "summary", "dashboard"],
                    "entities": ["date_range", "metric"],
                    "confidence_boost": 0.1
                }
            },
            "staff": {
                "case_management": {
                    "keywords": ["case", "claim", "file", "review", "assign", "update"],
                    "entities": ["claim_number", "user_id"],
                    "confidence_boost": 0.2
                },
                "user_lookup": {
                    "keywords": ["user", "claimant", "employee", "lookup", "search"],
                    "entities": ["user_id", "name"],
                    "confidence_boost": 0.15
                },
                "system_analytics": {
                    "keywords": ["system", "performance", "analytics", "metrics", "health"],
                    "entities": ["metric", "date_range"],
                    "confidence_boost": 0.1
                }
            }
        }
        
        # Get patterns for user persona
        persona_patterns = live_data_patterns.get(user_persona, live_data_patterns["beneficiary"])
        
        best_match = {"category": None, "confidence": 0.0, "specificity": "general"}
        
        for category, pattern in persona_patterns.items():
            confidence = 0.0
            
            # Check keyword matches
            keyword_matches = sum(1 for keyword in pattern["keywords"] if keyword in message_lower)
            if keyword_matches > 0:
                confidence += (keyword_matches / len(pattern["keywords"])) * 0.6
            
            # Check entity matches
            entity_matches = sum(1 for entity in pattern["entities"] if entity in entities)
            if entity_matches > 0:
                confidence += (entity_matches / len(pattern["entities"])) * 0.3
                best_match["specificity"] = "specific"
            
            # Apply confidence boost
            confidence += pattern["confidence_boost"]
            
            # Update best match
            if confidence > best_match["confidence"]:
                best_match = {
                    "category": category,
                    "confidence": min(confidence, 1.0),
                    "specificity": "specific" if entity_matches > 0 else "general"
                }
        
        # Determine if this is a live data request
        is_live_data = best_match["confidence"] >= self.confidence_threshold
        
        return {
            "is_live_data": is_live_data,
            "data_category": best_match["category"],
            "confidence": best_match["confidence"],
            "requires_auth": is_live_data,  # Live data always requires auth
            "specificity": best_match["specificity"]
        }
    
    def check_static_information_intent(self, message: str, entities: Dict) -> Dict:
        """
        Check if message is requesting static information (existing functionality)
        """
        message_lower = message.lower()
        
        static_patterns = {
            "general_help": {
                "keywords": ["help", "how", "what", "explain", "tell me about"],
                "confidence_base": 0.7
            },
            "process_info": {
                "keywords": ["process", "procedure", "steps", "how to", "guide"],
                "confidence_base": 0.8
            },
            "contact_info": {
                "keywords": ["contact", "phone", "email", "office", "address", "location"],
                "confidence_base": 0.9
            },
            "policy_info": {
                "keywords": ["policy", "coverage", "benefits", "eligibility", "rules"],
                "confidence_base": 0.8
            },
            "forms_documents": {
                "keywords": ["form", "document", "download", "application", "paperwork"],
                "confidence_base": 0.8
            }
        }
        
        best_match = {"category": None, "confidence": 0.0}
        
        for category, pattern in static_patterns.items():
            keyword_matches = sum(1 for keyword in pattern["keywords"] if keyword in message_lower)
            
            if keyword_matches > 0:
                confidence = (keyword_matches / len(pattern["keywords"])) * pattern["confidence_base"]
                
                if confidence > best_match["confidence"]:
                    best_match = {"category": category, "confidence": confidence}
        
        return {
            "is_static_info": best_match["confidence"] >= 0.6,
            "category": best_match["category"],
            "confidence": best_match["confidence"]
        }
    
    def check_authentication_intent(self, message: str, entities: Dict, context: Dict) -> Dict:
        """
        Check if message is part of authentication flow
        """
        message_lower = message.lower()
        
        # Check if we're in an authentication flow
        auth_in_progress = context.get("authentication_in_progress", False)
        
        if auth_in_progress:
            # Determine authentication step
            if "claim_number" in entities or re.search(r'wc-\d{4}-\d{6}', message_lower):
                return {
                    "is_auth_intent": True,
                    "confidence": 0.9,
                    "auth_step": "claim_verification"
                }
            elif any(word in message_lower for word in ["name", "birth", "date"]):
                return {
                    "is_auth_intent": True,
                    "confidence": 0.8,
                    "auth_step": "personal_details"
                }
            elif re.search(r'\d{6}', message):  # OTP pattern
                return {
                    "is_auth_intent": True,
                    "confidence": 0.95,
                    "auth_step": "otp_verification"
                }
        
        return {"is_auth_intent": False, "confidence": 0.0}
    
    def extract_entities(self, message: str) -> Dict:
        """
        Extract entities from message using enhanced patterns
        """
        entities = {}
        
        # Claim number extraction
        claim_pattern = r'WC-\d{4}-\d{6}'
        claim_match = re.search(claim_pattern, message.upper())
        if claim_match:
            entities["claim_number"] = claim_match.group()
        
        # Phone number extraction
        phone_pattern = r'(\+260|0)\d{9}'
        phone_match = re.search(phone_pattern, message)
        if phone_match:
            entities["phone"] = phone_match.group()
        
        # Email extraction
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, message)
        if email_match:
            entities["email"] = email_match.group()
        
        # Date extraction (various formats)
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',  # DD/MM/YYYY
            r'\d{4}-\d{2}-\d{2}',      # YYYY-MM-DD
            r'\d{1,2}-\d{1,2}-\d{4}'   # DD-MM-YYYY
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, message)
            if date_match:
                entities["date"] = date_match.group()
                break
        
        # Amount/money extraction
        amount_pattern = r'\$?\d+(?:,\d{3})*(?:\.\d{2})?'
        amount_match = re.search(amount_pattern, message)
        if amount_match:
            entities["amount"] = amount_match.group()
        
        # OTP extraction
        otp_pattern = r'\b\d{6}\b'
        otp_match = re.search(otp_pattern, message)
        if otp_match:
            entities["otp"] = otp_match.group()
        
        return entities
    
    def analyze_sentiment(self, message: str, context: Dict) -> str:
        """
        Analyze sentiment while preserving existing sentiment analysis logic
        """
        message_lower = message.lower()
        
        # Urgent/emergency indicators
        urgent_keywords = ["urgent", "emergency", "asap", "immediately", "help", "problem", "issue", "wrong"]
        if any(keyword in message_lower for keyword in urgent_keywords):
            return "urgent"
        
        # Negative sentiment indicators
        negative_keywords = ["frustrated", "angry", "upset", "disappointed", "confused", "worried"]
        if any(keyword in message_lower for keyword in negative_keywords):
            return "negative"
        
        # Positive sentiment indicators
        positive_keywords = ["thank", "great", "excellent", "perfect", "good", "happy", "satisfied"]
        if any(keyword in message_lower for keyword in positive_keywords):
            return "positive"
        
        return "neutral"
    
    def determine_user_persona(self, user_session: Dict, context: Dict) -> str:
        """
        Determine user persona from session or context
        """
        # Check session data first
        if user_session and user_session.get("user_type"):
            return user_session["user_type"]
        
        # Check context
        if context.get("user_persona"):
            return context["user_persona"]
        
        # Default to beneficiary
        return "beneficiary"
    
    def build_context_awareness(self, message: str, conversation_context: Dict, 
                              user_session: Dict) -> Dict:
        """
        Build context awareness for better intent classification
        """
        return {
            "conversation_turn": conversation_context.get("turn_count", 1),
            "previous_intent": conversation_context.get("last_intent"),
            "session_duration": conversation_context.get("session_duration", 0),
            "authentication_status": user_session.get("identity_verified", False),
            "user_permissions": user_session.get("permissions", []),
            "conversation_topic": self.extract_conversation_topic(message, conversation_context)
        }
    
    def extract_conversation_topic(self, message: str, context: Dict) -> str:
        """
        Extract the main topic of conversation
        """
        message_lower = message.lower()
        
        topics = {
            "claims": ["claim", "case", "injury", "accident", "compensation"],
            "payments": ["payment", "money", "benefits", "compensation", "paid"],
            "medical": ["doctor", "medical", "treatment", "hospital", "provider"],
            "employment": ["work", "job", "employer", "employee", "workplace"],
            "compliance": ["compliance", "safety", "training", "audit", "premium"]
        }
        
        for topic, keywords in topics.items():
            if any(keyword in message_lower for keyword in keywords):
                return topic
        
        return "general"
    
    def update_context_memory(self, message: str, result: IntentClassificationResult, 
                            context: Dict) -> None:
        """
        Update context memory for improved future classifications
        """
        session_id = context.get("session_id", "default")
        
        if session_id not in self.context_memory:
            self.context_memory[session_id] = []
        
        self.context_memory[session_id].append({
            "message": message,
            "intent": result.intent_type,
            "confidence": result.confidence,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 10 interactions per session
        if len(self.context_memory[session_id]) > 10:
            self.context_memory[session_id] = self.context_memory[session_id][-10:]
    
    def normalize_message(self, message: str) -> str:
        """
        Normalize message for consistent processing
        """
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', message.strip())
        
        # Handle common abbreviations
        abbreviations = {
            "w/c": "workers compensation",
            "wc": "workers compensation",
            "comp": "compensation",
            "info": "information",
            "asap": "as soon as possible"
        }
        
        for abbrev, full_form in abbreviations.items():
            normalized = re.sub(r'\b' + abbrev + r'\b', full_form, normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def load_sentiment_keywords(self) -> Dict:
        """Load sentiment analysis keywords"""
        return {
            "positive": ["thank", "great", "excellent", "perfect", "good", "happy", "satisfied"],
            "negative": ["frustrated", "angry", "upset", "disappointed", "confused", "worried"],
            "urgent": ["urgent", "emergency", "asap", "immediately", "help", "problem", "issue"]
        }
    
    def load_intent_patterns(self) -> Dict:
        """Load intent classification patterns"""
        return {
            "greeting": ["hello", "hi", "hey", "good morning", "good afternoon"],
            "goodbye": ["bye", "goodbye", "see you", "thank you", "thanks"],
            "help": ["help", "assist", "support", "guide", "explain"]
        }
    
    def load_entity_extractors(self) -> Dict:
        """Load entity extraction patterns"""
        return {
            "claim_number": r'WC-\d{4}-\d{6}',
            "phone": r'(\+260|0)\d{9}',
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "date": r'\d{1,2}/\d{1,2}/\d{4}',
            "amount": r'\$?\d+(?:,\d{3})*(?:\.\d{2})?'
        }

# API Endpoints for Enhanced Intent Classification

@frappe.whitelist()
def classify_message_intent():
    """
    API endpoint for enhanced intent classification
    """
    try:
        data = frappe.local.form_dict
        message = data.get("message", "")
        conversation_context = data.get("conversation_context", {})
        user_session = data.get("user_session", {})
        
        classifier = EnhancedIntentClassifier()
        result = classifier.classify_intent(message, conversation_context, user_session)
        
        return {
            "success": True,
            "data": {
                "intent_type": result.intent_type,
                "confidence": result.confidence,
                "data_category": result.data_category,
                "requires_auth": result.requires_auth,
                "user_persona": result.user_persona,
                "extracted_entities": result.extracted_entities,
                "sentiment": result.sentiment,
                "context_awareness": result.context_awareness
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Intent classification API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def test_intent_classification():
    """
    Test endpoint for intent classification with sample messages
    """
    try:
        test_messages = [
            {
                "message": "Hi WorkCom, can you check my claim status?",
                "expected_intent": "live_data",
                "user_persona": "beneficiary"
            },
            {
                "message": "What is workers compensation?",
                "expected_intent": "static_info",
                "user_persona": "beneficiary"
            },
            {
                "message": "My claim number is WC-2024-001234",
                "expected_intent": "authentication",
                "user_persona": "beneficiary"
            },
            {
                "message": "Hello WorkCom, how are you today?",
                "expected_intent": "general",
                "user_persona": "beneficiary"
            }
        ]
        
        classifier = EnhancedIntentClassifier()
        results = []
        
        for test in test_messages:
            result = classifier.classify_intent(
                test["message"],
                {},
                {"user_type": test["user_persona"]}
            )
            
            results.append({
                "message": test["message"],
                "expected": test["expected_intent"],
                "actual": result.intent_type,
                "confidence": result.confidence,
                "match": result.intent_type == test["expected_intent"]
            })
        
        accuracy = sum(1 for r in results if r["match"]) / len(results) * 100
        
        return {
            "success": True,
            "data": {
                "test_results": results,
                "accuracy": accuracy,
                "total_tests": len(results),
                "passed_tests": sum(1 for r in results if r["match"])
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Intent classification test error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

