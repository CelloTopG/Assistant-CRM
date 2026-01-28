# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now, get_datetime, add_to_date
from typing import Dict, List, Optional, Any
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

class ConversationFlowManager:
    """
    Manages conversation flow, state, and multi-turn interactions for the assistant_crm system.
    Integrates with existing role-based response system and escalation management.
    """
    
    def __init__(self, session_id: str = None, user_id: str = None):
        """
        Initialize conversation flow manager.
        
        Args:
            session_id (str): Unique session identifier
            user_id (str): User identifier
        """
        self.session_id = session_id or frappe.session.sid
        self.user_id = user_id or frappe.session.user
        self.conversation_state = {}
        self.conversation_history = []
        self.context_memory = {}
        
    def start_conversation(self, initial_context: Dict = None) -> Dict:
        """
        Start a new conversation session.
        
        Args:
            initial_context (Dict): Initial conversation context
            
        Returns:
            Dict: Conversation session information
        """
        try:
            # Create conversation session record
            conversation_doc = frappe.new_doc("Conversation Session")
            conversation_doc.session_id = self.session_id
            conversation_doc.user_id = self.user_id
            conversation_doc.start_time = now()
            conversation_doc.status = "active"
            conversation_doc.initial_context = json.dumps(initial_context or {})
            conversation_doc.conversation_state = json.dumps({
                "turn_count": 0,
                "current_intent": None,
                "user_role": None,
                "satisfaction_score": None,
                "escalation_risk": "low"
            })
            conversation_doc.insert()
            frappe.db.commit()
            
            # Initialize conversation state
            self.conversation_state = {
                "conversation_id": conversation_doc.name,
                "turn_count": 0,
                "current_intent": None,
                "user_role": None,
                "satisfaction_score": None,
                "escalation_risk": "low",
                "context_memory": initial_context or {},
                "last_response_quality": None,
                "conversation_flow": "greeting"
            }
            
            return {
                "status": "success",
                "conversation_id": conversation_doc.name,
                "session_id": self.session_id,
                "message": "Conversation session started successfully"
            }
            
        except Exception as e:
            logger.error(f"Error starting conversation: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to start conversation session",
                "details": str(e)
            }
    
    def process_conversation_turn(self, user_message: str, bot_response: str, 
                                 intent: str, confidence: float, 
                                 user_context: Dict = None) -> Dict:
        """
        Process a conversation turn and update conversation state.
        
        Args:
            user_message (str): User's message
            bot_response (str): Bot's response
            intent (str): Detected intent
            confidence (float): Intent confidence score
            user_context (Dict): Current user context
            
        Returns:
            Dict: Updated conversation state and recommendations
        """
        try:
            # Update turn count
            self.conversation_state["turn_count"] = self.conversation_state.get("turn_count", 0) + 1
            
            # Analyze conversation flow
            flow_analysis = self._analyze_conversation_flow(user_message, intent, confidence)
            
            # Update conversation state
            self.conversation_state.update({
                "current_intent": intent,
                "last_confidence": confidence,
                "conversation_flow": flow_analysis["flow_stage"],
                "escalation_risk": flow_analysis["escalation_risk"],
                "user_satisfaction_indicators": flow_analysis["satisfaction_indicators"]
            })
            
            # Store conversation turn
            turn_data = {
                "turn_number": self.conversation_state["turn_count"],
                "timestamp": now(),
                "user_message": user_message,
                "bot_response": bot_response,
                "intent": intent,
                "confidence": confidence,
                "flow_stage": flow_analysis["flow_stage"],
                "escalation_risk": flow_analysis["escalation_risk"],
                "context": user_context or {}
            }
            
            self.conversation_history.append(turn_data)
            
            # Update conversation memory
            self._update_conversation_memory(user_message, intent, user_context)
            
            # Generate flow recommendations
            recommendations = self._generate_flow_recommendations()
            
            # Save conversation turn to database
            self._save_conversation_turn(turn_data)
            
            return {
                "status": "success",
                "conversation_state": self.conversation_state,
                "flow_analysis": flow_analysis,
                "recommendations": recommendations,
                "turn_data": turn_data
            }
            
        except Exception as e:
            logger.error(f"Error processing conversation turn: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to process conversation turn",
                "details": str(e)
            }
    
    def _analyze_conversation_flow(self, user_message: str, intent: str, confidence: float) -> Dict:
        """
        Analyze current conversation flow and determine stage.
        
        Args:
            user_message (str): User's message
            intent (str): Detected intent
            confidence (float): Intent confidence
            
        Returns:
            Dict: Flow analysis results
        """
        message_lower = user_message.lower().strip()
        turn_count = self.conversation_state.get("turn_count", 0)
        
        # Determine conversation flow stage
        flow_stage = "ongoing"
        
        # Greeting detection
        greeting_indicators = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
        if turn_count <= 1 and any(greeting in message_lower for greeting in greeting_indicators):
            flow_stage = "greeting"
        
        # Information gathering stage
        elif intent in ["information_request", "document_request", "status_inquiry"]:
            flow_stage = "information_gathering"
        
        # Problem solving stage
        elif intent in ["claim_submission", "technical_help", "complaint"]:
            flow_stage = "problem_solving"
        
        # Closing stage
        closing_indicators = ["thank you", "thanks", "that's all", "goodbye", "bye", "that helps"]
        if any(closing in message_lower for closing in closing_indicators):
            flow_stage = "closing"
        
        # Escalation risk assessment
        escalation_risk = self._assess_escalation_risk(user_message, intent, confidence)
        
        # Satisfaction indicators
        satisfaction_indicators = self._detect_satisfaction_indicators(user_message)
        
        return {
            "flow_stage": flow_stage,
            "escalation_risk": escalation_risk,
            "satisfaction_indicators": satisfaction_indicators,
            "turn_count": turn_count,
            "confidence_trend": self._calculate_confidence_trend()
        }
    
    def _assess_escalation_risk(self, user_message: str, intent: str, confidence: float) -> str:
        """
        Assess escalation risk based on conversation indicators.
        
        Args:
            user_message (str): User's message
            intent (str): Detected intent
            confidence (float): Intent confidence
            
        Returns:
            str: Escalation risk level (low, medium, high, critical)
        """
        message_lower = user_message.lower()
        risk_score = 0
        
        # Frustration indicators
        frustration_keywords = [
            "frustrated", "angry", "upset", "disappointed", "terrible", "awful",
            "useless", "waste of time", "not helping", "doesn't work", "broken"
        ]
        if any(keyword in message_lower for keyword in frustration_keywords):
            risk_score += 3
        
        # Urgency indicators
        urgency_keywords = ["urgent", "emergency", "immediately", "asap", "deadline", "critical"]
        if any(keyword in message_lower for keyword in urgency_keywords):
            risk_score += 2
        
        # Repetition indicators (same intent multiple times)
        recent_intents = [turn.get("intent") for turn in self.conversation_history[-3:]]
        if recent_intents.count(intent) >= 2:
            risk_score += 2
        
        # Low confidence pattern
        if confidence < 0.6:
            risk_score += 1
        
        # Multiple turns without resolution
        if self.conversation_state.get("turn_count", 0) > 5:
            risk_score += 1
        
        # Escalation request keywords
        escalation_keywords = ["speak to manager", "human agent", "supervisor", "escalate", "transfer"]
        if any(keyword in message_lower for keyword in escalation_keywords):
            risk_score += 4
        
        # Determine risk level
        if risk_score >= 6:
            return "critical"
        elif risk_score >= 4:
            return "high"
        elif risk_score >= 2:
            return "medium"
        else:
            return "low"
    
    def _detect_satisfaction_indicators(self, user_message: str) -> Dict:
        """
        Detect user satisfaction indicators in the message.
        
        Args:
            user_message (str): User's message
            
        Returns:
            Dict: Satisfaction indicators and score
        """
        message_lower = user_message.lower()
        
        # Positive indicators
        positive_keywords = [
            "thank you", "thanks", "helpful", "great", "excellent", "perfect",
            "exactly", "that's right", "appreciate", "wonderful", "amazing"
        ]
        positive_score = sum(1 for keyword in positive_keywords if keyword in message_lower)
        
        # Negative indicators
        negative_keywords = [
            "not helpful", "doesn't help", "wrong", "incorrect", "useless",
            "terrible", "awful", "bad", "poor", "disappointing"
        ]
        negative_score = sum(1 for keyword in negative_keywords if keyword in message_lower)
        
        # Calculate satisfaction score (-5 to +5)
        satisfaction_score = min(5, max(-5, positive_score - negative_score))
        
        return {
            "satisfaction_score": satisfaction_score,
            "positive_indicators": positive_score,
            "negative_indicators": negative_score,
            "overall_sentiment": "positive" if satisfaction_score > 0 else "negative" if satisfaction_score < 0 else "neutral"
        }
    
    def _calculate_confidence_trend(self) -> Dict:
        """
        Calculate confidence trend over recent conversation turns.
        
        Returns:
            Dict: Confidence trend analysis
        """
        if len(self.conversation_history) < 2:
            return {"trend": "insufficient_data", "average": 0}
        
        recent_confidences = [turn.get("confidence", 0) for turn in self.conversation_history[-5:]]
        average_confidence = sum(recent_confidences) / len(recent_confidences)
        
        # Calculate trend
        if len(recent_confidences) >= 3:
            early_avg = sum(recent_confidences[:2]) / 2
            late_avg = sum(recent_confidences[-2:]) / 2
            
            if late_avg > early_avg + 0.1:
                trend = "improving"
            elif late_avg < early_avg - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "average": average_confidence,
            "recent_confidences": recent_confidences
        }

    def _update_conversation_memory(self, user_message: str, intent: str, user_context: Dict = None):
        """
        Update conversation memory with relevant information.

        Args:
            user_message (str): User's message
            intent (str): Detected intent
            user_context (Dict): Current user context
        """
        # Extract and store key information
        if intent == "claim_submission":
            self.context_memory["has_claim_inquiry"] = True
            self.context_memory["last_claim_inquiry"] = now()

        elif intent == "payment_status":
            self.context_memory["has_payment_inquiry"] = True
            self.context_memory["last_payment_inquiry"] = now()

        elif intent == "document_request":
            self.context_memory["has_document_request"] = True
            self.context_memory["last_document_request"] = now()

        # Store user role if detected
        if user_context and user_context.get("user_role"):
            self.context_memory["user_role"] = user_context["user_role"]

        # Store important entities mentioned
        entities = self._extract_entities(user_message)
        if entities:
            self.context_memory["mentioned_entities"] = entities

    def _extract_entities(self, message: str) -> Dict:
        """
        Extract important entities from user message.

        Args:
            message (str): User's message

        Returns:
            Dict: Extracted entities
        """
        entities = {}
        message_lower = message.lower()

        # Extract claim numbers
        import re
        claim_pattern = r'\b(?:claim|case|reference)?\s*(?:number|#|no\.?)?\s*([A-Z]{2}\d{6}|\d{6,8})\b'
        claim_matches = re.findall(claim_pattern, message, re.IGNORECASE)
        if claim_matches:
            entities["claim_numbers"] = claim_matches

        # Extract dates
        date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'
        date_matches = re.findall(date_pattern, message)
        if date_matches:
            entities["dates"] = date_matches

        # Extract amounts
        amount_pattern = r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        amount_matches = re.findall(amount_pattern, message)
        if amount_matches:
            entities["amounts"] = amount_matches

        return entities

    def _generate_flow_recommendations(self) -> Dict:
        """
        Generate recommendations for conversation flow management.

        Returns:
            Dict: Flow recommendations
        """
        recommendations = {
            "next_actions": [],
            "escalation_needed": False,
            "response_adjustments": [],
            "follow_up_required": False
        }

        escalation_risk = self.conversation_state.get("escalation_risk", "low")
        turn_count = self.conversation_state.get("turn_count", 0)
        flow_stage = self.conversation_state.get("conversation_flow", "ongoing")

        # Escalation recommendations
        if escalation_risk == "critical":
            recommendations["escalation_needed"] = True
            recommendations["next_actions"].append("immediate_human_transfer")
        elif escalation_risk == "high":
            recommendations["next_actions"].append("prepare_escalation")
            recommendations["response_adjustments"].append("increase_empathy")

        # Flow stage recommendations
        if flow_stage == "greeting":
            recommendations["next_actions"].append("role_detection")
            recommendations["response_adjustments"].append("warm_welcome")

        elif flow_stage == "information_gathering":
            recommendations["next_actions"].append("provide_comprehensive_info")
            recommendations["response_adjustments"].append("detailed_explanation")

        elif flow_stage == "problem_solving":
            recommendations["next_actions"].append("step_by_step_guidance")
            recommendations["response_adjustments"].append("solution_focused")

        elif flow_stage == "closing":
            recommendations["next_actions"].append("satisfaction_check")
            recommendations["follow_up_required"] = True

        # Turn count recommendations
        if turn_count > 5:
            recommendations["next_actions"].append("conversation_summary")
            recommendations["response_adjustments"].append("concise_responses")

        # Confidence trend recommendations
        confidence_trend = self._calculate_confidence_trend()
        if confidence_trend["trend"] == "declining":
            recommendations["next_actions"].append("clarify_intent")
            recommendations["response_adjustments"].append("ask_clarifying_questions")

        return recommendations

    def _save_conversation_turn(self, turn_data: Dict):
        """
        Save conversation turn to database.

        Args:
            turn_data (Dict): Turn data to save
        """
        try:
            # Ensure conversation session exists
            conversation_session_id = self._ensure_conversation_session()

            # Create conversation turn record
            turn_doc = frappe.new_doc("Conversation Turn")
            turn_doc.session_id = self.session_id
            turn_doc.conversation_id = conversation_session_id
            turn_doc.turn_number = turn_data["turn_number"]
            turn_doc.timestamp = turn_data["timestamp"]
            turn_doc.user_message = turn_data["user_message"]
            turn_doc.bot_response = turn_data["bot_response"]
            turn_doc.intent = turn_data["intent"]
            turn_doc.confidence = turn_data["confidence"]
            turn_doc.flow_stage = turn_data["flow_stage"]
            turn_doc.escalation_risk = turn_data["escalation_risk"]
            turn_doc.context_data = json.dumps(turn_data["context"])
            turn_doc.insert()
            frappe.db.commit()

        except Exception as e:
            logger.error(f"Error saving conversation turn: {str(e)}")

    def _ensure_conversation_session(self) -> str:
        """
        Ensure conversation session exists and return its ID.

        Returns:
            str: Conversation session document name
        """
        try:
            # Check if session already exists
            existing_session = frappe.get_all("Conversation Session",
                filters={"session_id": self.session_id},
                fields=["name"],
                limit=1
            )

            if existing_session:
                return existing_session[0].name

            # Create new conversation session
            session_doc = frappe.new_doc("Conversation Session")
            session_doc.session_id = self.session_id
            session_doc.user_id = self.user_id
            session_doc.start_time = now()
            session_doc.status = "active"
            session_doc.total_turns = 0
            session_doc.insert()
            frappe.db.commit()

            return session_doc.name

        except Exception as e:
            logger.error(f"Error ensuring conversation session: {str(e)}")
            # Return a fallback session ID to prevent complete failure
            return f"fallback_session_{self.session_id}"

    def get_conversation_context(self) -> Dict:
        """
        Get current conversation context for response generation.

        Returns:
            Dict: Conversation context
        """
        return {
            "conversation_state": self.conversation_state,
            "conversation_history": self.conversation_history[-5:],  # Last 5 turns
            "context_memory": self.context_memory,
            "session_id": self.session_id,
            "user_id": self.user_id
        }

    def end_conversation(self, reason: str = "user_ended") -> Dict:
        """
        End the conversation session.

        Args:
            reason (str): Reason for ending conversation

        Returns:
            Dict: Conversation summary
        """
        try:
            # Update conversation session
            conversation_id = self.conversation_state.get("conversation_id")
            if conversation_id:
                conversation_doc = frappe.get_doc("Conversation Session", conversation_id)
                conversation_doc.end_time = now()
                conversation_doc.status = "completed"
                conversation_doc.end_reason = reason
                conversation_doc.total_turns = self.conversation_state.get("turn_count", 0)
                conversation_doc.final_state = json.dumps(self.conversation_state)
                conversation_doc.save()
                frappe.db.commit()

            # Generate conversation summary
            summary = self._generate_conversation_summary()

            return {
                "status": "success",
                "conversation_id": conversation_id,
                "summary": summary,
                "message": "Conversation ended successfully"
            }

        except Exception as e:
            logger.error(f"Error ending conversation: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to end conversation",
                "details": str(e)
            }

    def _generate_conversation_summary(self) -> Dict:
        """
        Generate a summary of the conversation.

        Returns:
            Dict: Conversation summary
        """
        total_turns = self.conversation_state.get("turn_count", 0)
        escalation_risk = self.conversation_state.get("escalation_risk", "low")

        # Calculate satisfaction indicators
        satisfaction_scores = []
        for turn in self.conversation_history:
            if "satisfaction_indicators" in turn:
                satisfaction_scores.append(turn["satisfaction_indicators"].get("satisfaction_score", 0))

        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0

        # Identify main topics
        intents = [turn.get("intent") for turn in self.conversation_history]
        main_intent = max(set(intents), key=intents.count) if intents else "unknown"

        return {
            "total_turns": total_turns,
            "main_intent": main_intent,
            "escalation_risk": escalation_risk,
            "average_satisfaction": avg_satisfaction,
            "conversation_successful": avg_satisfaction > 0 and escalation_risk in ["low", "medium"],
            "topics_covered": list(set(intents)),
            "entities_mentioned": self.context_memory.get("mentioned_entities", {}),
            "user_role": self.context_memory.get("user_role", "unknown")
        }


# Utility functions for integration with existing services

def get_conversation_flow_manager(session_id: str = None, user_id: str = None) -> ConversationFlowManager:
    """
    Get or create a conversation flow manager instance.

    Args:
        session_id (str): Session identifier
        user_id (str): User identifier

    Returns:
        ConversationFlowManager: Flow manager instance
    """
    return ConversationFlowManager(session_id, user_id)


def process_conversation_with_flow(user_message: str, bot_response: str,
                                  intent: str, confidence: float,
                                  session_id: str = None, user_context: Dict = None) -> Dict:
    """
    Process a conversation turn with flow management.

    Args:
        user_message (str): User's message
        bot_response (str): Bot's response
        intent (str): Detected intent
        confidence (float): Intent confidence
        session_id (str): Session identifier
        user_context (Dict): User context

    Returns:
        Dict: Flow processing results
    """
    flow_manager = get_conversation_flow_manager(session_id)
    return flow_manager.process_conversation_turn(
        user_message, bot_response, intent, confidence, user_context
    )
