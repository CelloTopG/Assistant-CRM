# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now
import json

class ConversationTurn(Document):
    """
    DocType for managing individual conversation turns in the assistant_crm system.
    Tracks user messages, bot responses, and conversation analytics.
    """
    
    def before_insert(self):
        """Set default values before inserting the document."""
        if not self.timestamp:
            self.timestamp = now()
    
    def before_save(self):
        """Validate and process data before saving."""
        # Validate JSON fields
        if self.context_data:
            try:
                json.loads(self.context_data)
            except json.JSONDecodeError:
                frappe.throw("Invalid JSON in context_data field")
        
        # Calculate response quality score if not set
        if not self.response_quality_score:
            self.response_quality_score = self._calculate_response_quality()
    
    def _calculate_response_quality(self):
        """Calculate response quality score based on various factors."""
        score = 0.5  # Base score
        
        # Confidence score factor (0.3 weight)
        if self.confidence:
            score += (self.confidence * 0.3)
        
        # Response length factor (0.2 weight)
        if self.bot_response:
            response_length = len(self.bot_response)
            if 50 <= response_length <= 500:  # Optimal length range
                score += 0.2
            elif response_length < 50:
                score += 0.1  # Too short
            else:
                score += 0.05  # Too long
        
        # Escalation risk factor (0.3 weight)
        escalation_weights = {
            "low": 0.3,
            "medium": 0.2,
            "high": 0.1,
            "critical": 0.0
        }
        if self.escalation_risk:
            score += escalation_weights.get(self.escalation_risk, 0.1)
        
        # Flow stage factor (0.2 weight)
        flow_weights = {
            "greeting": 0.2,
            "information_gathering": 0.15,
            "problem_solving": 0.2,
            "closing": 0.2,
            "ongoing": 0.1
        }
        if self.flow_stage:
            score += flow_weights.get(self.flow_stage, 0.1)
        
        return min(1.0, max(0.0, score))  # Ensure score is between 0 and 1
    
    def get_turn_analytics(self):
        """Get analytics for this conversation turn."""
        try:
            context_data = json.loads(self.context_data) if self.context_data else {}
            
            analytics = {
                "turn_number": self.turn_number,
                "timestamp": self.timestamp,
                "intent": self.intent,
                "confidence": self.confidence,
                "flow_stage": self.flow_stage,
                "escalation_risk": self.escalation_risk,
                "response_quality_score": self.response_quality_score,
                "user_satisfaction": self.user_satisfaction,
                "processing_time": self.processing_time,
                "message_length": len(self.user_message) if self.user_message else 0,
                "response_length": len(self.bot_response) if self.bot_response else 0,
                "context_data": context_data
            }
            
            return analytics
            
        except Exception as e:
            frappe.log_error(f"Error getting turn analytics: {str(e)}")
            return {}
    
    def update_satisfaction(self, satisfaction_level):
        """Update user satisfaction for this turn."""
        valid_levels = ["very_satisfied", "satisfied", "neutral", "dissatisfied", "very_dissatisfied"]
        if satisfaction_level in valid_levels:
            self.user_satisfaction = satisfaction_level
            self.save()
            frappe.db.commit()
            return True
        return False
    
    @frappe.whitelist()
    def get_turn_details(self):
        """Get detailed information about this conversation turn."""
        return {
            "turn_info": {
                "session_id": self.session_id,
                "conversation_id": self.conversation_id,
                "turn_number": self.turn_number,
                "timestamp": self.timestamp
            },
            "interaction": {
                "user_message": self.user_message,
                "bot_response": self.bot_response,
                "intent": self.intent,
                "confidence": self.confidence
            },
            "flow_analysis": {
                "flow_stage": self.flow_stage,
                "escalation_risk": self.escalation_risk,
                "response_quality_score": self.response_quality_score,
                "user_satisfaction": self.user_satisfaction
            },
            "performance": {
                "processing_time": self.processing_time,
                "message_length": len(self.user_message) if self.user_message else 0,
                "response_length": len(self.bot_response) if self.bot_response else 0
            },
            "context": json.loads(self.context_data) if self.context_data else {}
        }


@frappe.whitelist()
def get_conversation_turns(conversation_id, limit=50):
    """Get conversation turns for a specific conversation."""
    turns = frappe.get_all("Conversation Turn",
        filters={"conversation_id": conversation_id},
        fields=["*"],
        order_by="turn_number",
        limit=limit
    )
    
    return turns


@frappe.whitelist()
def get_turn_analytics_summary(session_id=None, conversation_id=None):
    """Get analytics summary for conversation turns."""
    try:
        filters = {}
        if session_id:
            filters["session_id"] = session_id
        if conversation_id:
            filters["conversation_id"] = conversation_id
        
        turns = frappe.get_all("Conversation Turn",
            filters=filters,
            fields=["*"],
            order_by="turn_number"
        )
        
        if not turns:
            return {"error": "No turns found"}
        
        # Calculate summary analytics
        total_turns = len(turns)
        avg_confidence = sum(turn.confidence for turn in turns if turn.confidence) / total_turns
        avg_quality = sum(turn.response_quality_score for turn in turns if turn.response_quality_score) / total_turns
        
        # Escalation risk distribution
        escalation_counts = {}
        for turn in turns:
            risk = turn.escalation_risk or "unknown"
            escalation_counts[risk] = escalation_counts.get(risk, 0) + 1
        
        # Intent distribution
        intent_counts = {}
        for turn in turns:
            intent = turn.intent or "unknown"
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        # Satisfaction distribution
        satisfaction_counts = {}
        for turn in turns:
            satisfaction = turn.user_satisfaction or "unknown"
            satisfaction_counts[satisfaction] = satisfaction_counts.get(satisfaction, 0) + 1
        
        return {
            "summary": {
                "total_turns": total_turns,
                "average_confidence": round(avg_confidence, 3),
                "average_quality_score": round(avg_quality, 3),
                "session_id": session_id,
                "conversation_id": conversation_id
            },
            "distributions": {
                "escalation_risk": escalation_counts,
                "intents": intent_counts,
                "satisfaction": satisfaction_counts
            },
            "performance": {
                "avg_processing_time": sum(turn.processing_time for turn in turns if turn.processing_time) / total_turns,
                "avg_message_length": sum(len(turn.user_message) for turn in turns if turn.user_message) / total_turns,
                "avg_response_length": sum(len(turn.bot_response) for turn in turns if turn.bot_response) / total_turns
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting turn analytics summary: {str(e)}")
        return {
            "error": "Failed to generate analytics summary",
            "details": str(e)
        }


@frappe.whitelist()
def update_turn_satisfaction(turn_id, satisfaction_level):
    """Update satisfaction level for a specific turn."""
    try:
        turn = frappe.get_doc("Conversation Turn", turn_id)
        if turn.update_satisfaction(satisfaction_level):
            return {
                "status": "success",
                "message": "Satisfaction updated successfully"
            }
        else:
            return {
                "status": "error",
                "message": "Invalid satisfaction level"
            }
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": "Turn not found"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to update satisfaction",
            "details": str(e)
        }
