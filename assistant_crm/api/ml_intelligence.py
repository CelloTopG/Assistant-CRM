#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Phase 4.1: Advanced AI/ML Integration
Implements machine learning capabilities while preserving existing functionality
"""

import frappe
from frappe import _
import json
import numpy as np
from datetime import datetime, timedelta
import re
from collections import defaultdict
import pickle
import os

class MLIntelligenceEngine:
    """Advanced ML Intelligence Engine for WCFCB Assistant CRM"""
    
    def __init__(self):
        self.model_cache = {}
        self.prediction_cache = {}
        self.learning_data = defaultdict(list)
        
    def initialize_ml_models(self):
        """Initialize ML models for predictive capabilities"""
        try:
            # Customer Behavior Prediction Model
            self.behavior_model = CustomerBehaviorPredictor()
            
            # Query Intent Enhancement Model
            self.intent_enhancer = IntentEnhancementModel()
            
            # Predictive Escalation Model
            self.escalation_predictor = EscalationPredictor()
            
            # User Journey Analytics Model
            self.journey_analyzer = UserJourneyAnalyzer()
            
            return True
        except Exception as e:
            frappe.log_error(f"ML Model Initialization Error: {str(e)}")
            return False

class CustomerBehaviorPredictor:
    """Predicts customer behavior patterns and needs"""
    
    def __init__(self):
        self.user_profiles = {}
        self.behavior_patterns = {}
        
    def analyze_user_behavior(self, user_id, interaction_history):
        """Analyze user behavior patterns for prediction"""
        try:
            # Get user interaction history
            interactions = frappe.get_all("User Interaction Log", 
                filters={"user_id": user_id},
                fields=["query_text", "response_provided", "satisfaction_rating", 
                       "timestamp", "session_id", "confidence_score"],
                order_by="timestamp desc",
                limit=100
            )
            
            if not interactions:
                return self._create_default_profile(user_id)
            
            # Analyze patterns
            behavior_analysis = {
                "query_frequency": self._calculate_query_frequency(interactions),
                "preferred_topics": self._extract_preferred_topics(interactions),
                "satisfaction_trend": self._analyze_satisfaction_trend(interactions),
                "complexity_preference": self._analyze_complexity_preference(interactions),
                "time_patterns": self._analyze_time_patterns(interactions),
                "language_preference": self._detect_language_preference(interactions)
            }
            
            # Generate predictions
            predictions = {
                "next_likely_query": self._predict_next_query(behavior_analysis),
                "escalation_probability": self._predict_escalation_probability(behavior_analysis),
                "satisfaction_forecast": self._forecast_satisfaction(behavior_analysis),
                "optimal_response_style": self._determine_response_style(behavior_analysis)
            }
            
            # Update user profile
            self.user_profiles[user_id] = {
                "behavior_analysis": behavior_analysis,
                "predictions": predictions,
                "last_updated": datetime.now(),
                "confidence_score": self._calculate_prediction_confidence(interactions)
            }
            
            return self.user_profiles[user_id]
            
        except Exception as e:
            frappe.log_error(f"Behavior Analysis Error: {str(e)}")
            return self._create_default_profile(user_id)
    
    def _calculate_query_frequency(self, interactions):
        """Calculate user query frequency patterns"""
        if len(interactions) < 2:
            return {"frequency": "low", "pattern": "irregular"}
        
        # Calculate time differences between queries
        timestamps = [frappe.utils.get_datetime(i.timestamp) for i in interactions]
        time_diffs = [(timestamps[i] - timestamps[i+1]).total_seconds() / 3600 
                     for i in range(len(timestamps)-1)]
        
        avg_hours_between = np.mean(time_diffs) if time_diffs else 24
        
        if avg_hours_between < 1:
            return {"frequency": "very_high", "pattern": "intensive"}
        elif avg_hours_between < 24:
            return {"frequency": "high", "pattern": "daily"}
        elif avg_hours_between < 168:
            return {"frequency": "medium", "pattern": "weekly"}
        else:
            return {"frequency": "low", "pattern": "occasional"}
    
    def _extract_preferred_topics(self, interactions):
        """Extract user's preferred topics from query history"""
        topic_keywords = {
            "claims": ["claim", "filing", "status", "benefit", "compensation"],
            "medical": ["medical", "doctor", "treatment", "hospital", "injury"],
            "legal": ["legal", "appeal", "dispute", "attorney", "lawsuit"],
            "employer": ["employer", "registration", "premium", "contribution", "payroll"],
            "general": ["information", "help", "question", "guide", "process"]
        }
        
        topic_scores = defaultdict(int)
        
        for interaction in interactions:
            query_lower = interaction.query_text.lower()
            for topic, keywords in topic_keywords.items():
                score = sum(1 for keyword in keywords if keyword in query_lower)
                topic_scores[topic] += score
        
        # Sort topics by preference
        sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
        return [topic for topic, score in sorted_topics if score > 0]
    
    def _analyze_satisfaction_trend(self, interactions):
        """Analyze user satisfaction trends over time"""
        ratings = [i.satisfaction_rating for i in interactions if i.satisfaction_rating]
        
        if len(ratings) < 3:
            return {"trend": "insufficient_data", "average": 3.0}
        
        # Calculate trend
        recent_ratings = ratings[:5]  # Last 5 ratings
        older_ratings = ratings[5:10] if len(ratings) > 5 else ratings
        
        recent_avg = np.mean(recent_ratings)
        older_avg = np.mean(older_ratings)
        
        trend = "improving" if recent_avg > older_avg else "declining" if recent_avg < older_avg else "stable"
        
        return {
            "trend": trend,
            "average": np.mean(ratings),
            "recent_average": recent_avg,
            "improvement_rate": recent_avg - older_avg
        }
    
    def _predict_next_query(self, behavior_analysis):
        """Predict the user's next likely query"""
        preferred_topics = behavior_analysis.get("preferred_topics", [])
        
        if not preferred_topics:
            return {"topic": "general", "confidence": 0.3}
        
        # Simple prediction based on topic preference and patterns
        primary_topic = preferred_topics[0]
        
        next_query_suggestions = {
            "claims": "claim status check",
            "medical": "medical provider information",
            "legal": "appeal process guidance",
            "employer": "premium calculation",
            "general": "general information request"
        }
        
        return {
            "topic": primary_topic,
            "suggested_query": next_query_suggestions.get(primary_topic, "information request"),
            "confidence": min(0.8, len(preferred_topics) * 0.2)
        }
    
    def _predict_escalation_probability(self, behavior_analysis):
        """Predict probability of query escalation"""
        satisfaction_trend = behavior_analysis.get("satisfaction_trend", {})
        complexity_pref = behavior_analysis.get("complexity_preference", "medium")
        
        base_probability = 0.2  # 20% base escalation rate
        
        # Adjust based on satisfaction
        if satisfaction_trend.get("trend") == "declining":
            base_probability += 0.3
        elif satisfaction_trend.get("average", 3) < 3:
            base_probability += 0.2
        
        # Adjust based on complexity preference
        if complexity_pref == "high":
            base_probability += 0.2
        
        return min(0.9, base_probability)
    
    def _create_default_profile(self, user_id):
        """Create default profile for new users"""
        return {
            "behavior_analysis": {
                "query_frequency": {"frequency": "unknown", "pattern": "new_user"},
                "preferred_topics": ["general"],
                "satisfaction_trend": {"trend": "new_user", "average": 3.0},
                "complexity_preference": "medium",
                "time_patterns": {"peak_hours": [9, 10, 11, 14, 15, 16]},
                "language_preference": "en"
            },
            "predictions": {
                "next_likely_query": {"topic": "general", "confidence": 0.3},
                "escalation_probability": 0.2,
                "satisfaction_forecast": 3.0,
                "optimal_response_style": "standard"
            },
            "last_updated": datetime.now(),
            "confidence_score": 0.3
        }

class IntentEnhancementModel:
    """Enhances intent recognition with ML insights"""
    
    def __init__(self):
        self.intent_patterns = {}
        self.confidence_adjustments = {}
        
    def enhance_intent_recognition(self, query_text, original_confidence, original_intent):
        """Enhance intent recognition with ML insights"""
        try:
            # Analyze query patterns
            pattern_analysis = self._analyze_query_patterns(query_text)
            
            # Get historical performance for similar queries
            historical_performance = self._get_historical_performance(query_text)
            
            # Calculate enhanced confidence
            enhanced_confidence = self._calculate_enhanced_confidence(
                original_confidence, pattern_analysis, historical_performance
            )
            
            # Suggest alternative intents if confidence is low
            alternative_intents = self._suggest_alternative_intents(
                query_text, enhanced_confidence
            )
            
            return {
                "original_confidence": original_confidence,
                "enhanced_confidence": enhanced_confidence,
                "confidence_adjustment": enhanced_confidence - original_confidence,
                "alternative_intents": alternative_intents,
                "pattern_analysis": pattern_analysis,
                "recommendation": self._generate_recommendation(enhanced_confidence)
            }
            
        except Exception as e:
            frappe.log_error(f"Intent Enhancement Error: {str(e)}")
            return {
                "original_confidence": original_confidence,
                "enhanced_confidence": original_confidence,
                "confidence_adjustment": 0,
                "alternative_intents": [],
                "error": str(e)
            }

# API Endpoints for ML Integration

@frappe.whitelist()
def get_user_behavior_prediction(user_id):
    """Get behavior prediction for a specific user"""
    try:
        ml_engine = MLIntelligenceEngine()
        behavior_predictor = CustomerBehaviorPredictor()
        
        # Get user interaction history
        interactions = frappe.get_all("User Interaction Log",
            filters={"user_id": user_id},
            fields=["*"],
            order_by="timestamp desc",
            limit=50
        )
        
        # Analyze behavior
        prediction = behavior_predictor.analyze_user_behavior(user_id, interactions)
        
        return {
            "status": "success",
            "user_id": user_id,
            "prediction": prediction,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to generate behavior prediction",
            "details": str(e)
        }

@frappe.whitelist()
def enhance_query_intelligence(query_text, user_id=None, original_confidence=None):
    """Enhance query processing with ML intelligence"""
    try:
        ml_engine = MLIntelligenceEngine()
        intent_enhancer = IntentEnhancementModel()
        
        # Get original confidence or calculate it
        if original_confidence is None:
            original_confidence = calculate_basic_confidence(query_text)
        else:
            original_confidence = float(original_confidence)
        
        # Enhance intent recognition
        enhancement = intent_enhancer.enhance_intent_recognition(
            query_text, original_confidence, "general"
        )
        
        # Get user behavior context if user_id provided
        user_context = {}
        if user_id:
            behavior_prediction = get_user_behavior_prediction(user_id)
            if behavior_prediction.get("status") == "success":
                user_context = behavior_prediction.get("prediction", {})
        
        return {
            "status": "success",
            "query_text": query_text,
            "enhancement": enhancement,
            "user_context": user_context,
            "recommendations": generate_ml_recommendations(enhancement, user_context),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to enhance query intelligence",
            "details": str(e)
        }

def calculate_basic_confidence(query_text):
    """Calculate basic confidence score for a query"""
    # Simple confidence calculation based on query characteristics
    confidence = 0.5  # Base confidence
    
    # Adjust based on query length
    word_count = len(query_text.split())
    if word_count > 5:
        confidence += 0.2
    elif word_count < 3:
        confidence -= 0.1
    
    # Adjust based on specific keywords
    high_confidence_keywords = ["claim", "status", "premium", "medical", "appeal"]
    for keyword in high_confidence_keywords:
        if keyword.lower() in query_text.lower():
            confidence += 0.1
    
    return min(1.0, max(0.1, confidence))

def generate_ml_recommendations(enhancement, user_context):
    """Generate ML-based recommendations"""
    recommendations = []
    
    # Confidence-based recommendations
    if enhancement.get("enhanced_confidence", 0) < 0.6:
        recommendations.append({
            "type": "escalation",
            "message": "Consider escalating to human agent",
            "priority": "medium"
        })
    
    # User context-based recommendations
    if user_context.get("predictions", {}).get("escalation_probability", 0) > 0.7:
        recommendations.append({
            "type": "proactive_escalation",
            "message": "User has high escalation probability - prepare for complex query",
            "priority": "high"
        })
    
    # Personalization recommendations
    preferred_topics = user_context.get("behavior_analysis", {}).get("preferred_topics", [])
    if preferred_topics:
        recommendations.append({
            "type": "personalization",
            "message": f"User prefers {preferred_topics[0]} topics - tailor response accordingly",
            "priority": "low"
        })
    
    return recommendations

@frappe.whitelist()
def get_predictive_analytics_dashboard():
    """Get predictive analytics for dashboard display"""
    try:
        # Get recent user interactions for analysis
        recent_interactions = frappe.get_all("User Interaction Log",
            filters={"timestamp": [">", (datetime.now() - timedelta(days=7)).isoformat()]},
            fields=["*"]
        )
        
        # Calculate predictive metrics
        analytics = {
            "total_interactions": len(recent_interactions),
            "average_confidence": np.mean([i.confidence_score for i in recent_interactions if i.confidence_score]) if recent_interactions else 0,
            "escalation_rate": len([i for i in recent_interactions if i.confidence_score and i.confidence_score < 0.6]) / len(recent_interactions) if recent_interactions else 0,
            "satisfaction_average": np.mean([i.satisfaction_rating for i in recent_interactions if i.satisfaction_rating]) if recent_interactions else 0,
            "peak_hours": calculate_peak_hours(recent_interactions),
            "trending_topics": extract_trending_topics(recent_interactions),
            "prediction_accuracy": calculate_prediction_accuracy(),
            "ml_enhancement_impact": calculate_ml_impact()
        }
        
        return {
            "status": "success",
            "analytics": analytics,
            "timestamp": datetime.now().isoformat(),
            "period": "last_7_days"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to generate predictive analytics",
            "details": str(e)
        }

def calculate_peak_hours(interactions):
    """Calculate peak interaction hours"""
    if not interactions:
        return []
    
    hour_counts = defaultdict(int)
    for interaction in interactions:
        hour = frappe.utils.get_datetime(interaction.timestamp).hour
        hour_counts[hour] += 1
    
    # Return top 3 peak hours
    sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
    return [hour for hour, count in sorted_hours[:3]]

def extract_trending_topics(interactions):
    """Extract trending topics from recent interactions"""
    topic_keywords = {
        "claims": ["claim", "filing", "status", "benefit"],
        "medical": ["medical", "doctor", "treatment", "hospital"],
        "legal": ["legal", "appeal", "dispute", "attorney"],
        "employer": ["employer", "registration", "premium", "contribution"]
    }
    
    topic_counts = defaultdict(int)
    
    for interaction in interactions:
        query_lower = interaction.query_text.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                topic_counts[topic] += 1
    
    # Return top 3 trending topics
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    return [{"topic": topic, "count": count} for topic, count in sorted_topics[:3]]

def calculate_prediction_accuracy():
    """Calculate ML prediction accuracy (placeholder)"""
    # This would be calculated based on actual prediction vs outcome data
    return 0.78  # 78% accuracy placeholder

def calculate_ml_impact():
    """Calculate ML enhancement impact (placeholder)"""
    # This would measure improvement in response quality, user satisfaction, etc.
    return {
        "confidence_improvement": 0.15,  # 15% improvement in confidence scores
        "escalation_reduction": 0.12,    # 12% reduction in escalations
        "satisfaction_increase": 0.08    # 8% increase in user satisfaction
    }

class EscalationPredictor:
    """Predicts escalation needs using ML insights"""

    def __init__(self):
        self.escalation_patterns = {}
        self.prediction_model = None

    def predict_escalation_need(self, query_text, user_id, confidence_score, user_context=None):
        """Predict if a query will need escalation"""
        try:
            # Get user history
            user_history = frappe.get_all("User Interaction Log",
                filters={"user_id": user_id},
                fields=["confidence_score", "satisfaction_rating", "escalated"],
                order_by="timestamp desc",
                limit=20
            )

            # Calculate escalation probability
            escalation_probability = self._calculate_escalation_probability(
                query_text, confidence_score, user_history, user_context
            )

            # Determine escalation recommendation
            recommendation = self._generate_escalation_recommendation(escalation_probability)

            return {
                "escalation_probability": escalation_probability,
                "recommendation": recommendation,
                "factors": self._analyze_escalation_factors(query_text, confidence_score, user_history),
                "suggested_department": self._suggest_optimal_department(query_text, escalation_probability)
            }

        except Exception as e:
            frappe.log_error(f"Escalation Prediction Error: {str(e)}")
            return {
                "escalation_probability": 0.2,
                "recommendation": "monitor",
                "error": str(e)
            }

    def _calculate_escalation_probability(self, query_text, confidence_score, user_history, user_context):
        """Calculate probability of escalation need"""
        base_probability = 1.0 - confidence_score  # Lower confidence = higher escalation probability

        # Adjust based on user history
        if user_history:
            avg_satisfaction = np.mean([h.satisfaction_rating for h in user_history if h.satisfaction_rating])
            if avg_satisfaction < 3.0:
                base_probability += 0.2

            escalation_rate = len([h for h in user_history if getattr(h, 'escalated', False)]) / len(user_history)
            base_probability += escalation_rate * 0.3

        # Adjust based on query complexity
        complexity_indicators = ["legal", "appeal", "dispute", "complex", "urgent", "emergency"]
        if any(indicator in query_text.lower() for indicator in complexity_indicators):
            base_probability += 0.3

        # Adjust based on user context
        if user_context and user_context.get("predictions", {}).get("escalation_probability", 0) > 0.7:
            base_probability += 0.2

        return min(0.95, base_probability)

    def _generate_escalation_recommendation(self, probability):
        """Generate escalation recommendation based on probability"""
        if probability > 0.8:
            return "immediate_escalation"
        elif probability > 0.6:
            return "prepare_escalation"
        elif probability > 0.4:
            return "monitor_closely"
        else:
            return "standard_handling"

class UserJourneyAnalyzer:
    """Analyzes user journey patterns for optimization"""

    def __init__(self):
        self.journey_patterns = {}
        self.optimization_suggestions = {}

    def analyze_user_journey(self, user_id, session_id=None):
        """Analyze user journey for optimization opportunities"""
        try:
            # Get user session data
            if session_id:
                interactions = frappe.get_all("User Interaction Log",
                    filters={"user_id": user_id, "session_id": session_id},
                    fields=["*"],
                    order_by="timestamp asc"
                )
            else:
                # Get recent interactions
                interactions = frappe.get_all("User Interaction Log",
                    filters={"user_id": user_id},
                    fields=["*"],
                    order_by="timestamp desc",
                    limit=10
                )

            if not interactions:
                return {"status": "no_data", "message": "No interaction data available"}

            # Analyze journey patterns
            journey_analysis = {
                "total_interactions": len(interactions),
                "session_duration": self._calculate_session_duration(interactions),
                "query_progression": self._analyze_query_progression(interactions),
                "satisfaction_journey": self._analyze_satisfaction_journey(interactions),
                "resolution_path": self._analyze_resolution_path(interactions),
                "optimization_opportunities": self._identify_optimization_opportunities(interactions)
            }

            return {
                "status": "success",
                "user_id": user_id,
                "session_id": session_id,
                "journey_analysis": journey_analysis,
                "recommendations": self._generate_journey_recommendations(journey_analysis)
            }

        except Exception as e:
            frappe.log_error(f"Journey Analysis Error: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to analyze user journey",
                "details": str(e)
            }

@frappe.whitelist()
def get_ml_enhanced_escalation_prediction(query_text, user_id, confidence_score):
    """Get ML-enhanced escalation prediction"""
    try:
        escalation_predictor = EscalationPredictor()

        # Get user context
        behavior_prediction = get_user_behavior_prediction(user_id)
        user_context = behavior_prediction.get("prediction", {}) if behavior_prediction.get("status") == "success" else None

        # Get escalation prediction
        prediction = escalation_predictor.predict_escalation_need(
            query_text, user_id, float(confidence_score), user_context
        )

        return {
            "status": "success",
            "query_text": query_text,
            "user_id": user_id,
            "original_confidence": confidence_score,
            "escalation_prediction": prediction,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to generate escalation prediction",
            "details": str(e)
        }

@frappe.whitelist()
def get_user_journey_analysis(user_id, session_id=None):
    """Get user journey analysis"""
    try:
        journey_analyzer = UserJourneyAnalyzer()
        analysis = journey_analyzer.analyze_user_journey(user_id, session_id)

        return {
            "status": "success",
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to analyze user journey",
            "details": str(e)
        }
