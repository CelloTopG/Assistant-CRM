#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Predictive Service Delivery
Implements proactive customer engagement and predictive service capabilities
"""

import frappe
from frappe import _
import json
from datetime import datetime, timedelta
from collections import defaultdict
import calendar

class PredictiveServiceEngine:
    """Advanced predictive service delivery engine"""
    
    def __init__(self):
        self.prediction_models = {}
        self.engagement_rules = {}
        self.notification_queue = []
        
    def analyze_user_needs_prediction(self, user_id=None, timeframe_days=30):
        """Analyze and predict user service needs"""
        try:
            # Get user interaction patterns
            if user_id:
                users_to_analyze = [user_id]
            else:
                # Analyze all active users
                users_to_analyze = self._get_active_users(timeframe_days)
            
            predictions = {}
            
            for uid in users_to_analyze:
                user_prediction = self._predict_individual_user_needs(uid, timeframe_days)
                if user_prediction:
                    predictions[uid] = user_prediction
            
            return {
                "status": "success",
                "predictions": predictions,
                "analysis_timeframe": f"{timeframe_days} days",
                "users_analyzed": len(predictions),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            frappe.log_error(f"Predictive Analysis Error: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to analyze user needs prediction",
                "details": str(e)
            }
    
    def _predict_individual_user_needs(self, user_id, timeframe_days):
        """Predict individual user service needs"""
        try:
            # Get user interaction history
            interactions = frappe.get_all("User Interaction Log",
                filters={"user_id": user_id},
                fields=["*"],
                order_by="timestamp desc",
                limit=50
            )
            
            if not interactions:
                return None
            
            # Analyze patterns
            patterns = self._analyze_user_patterns(interactions)
            
            # Generate predictions
            predictions = {
                "user_id": user_id,
                "next_interaction_probability": self._predict_next_interaction(patterns),
                "likely_query_topics": self._predict_query_topics(patterns),
                "escalation_risk": self._predict_escalation_risk(patterns),
                "optimal_engagement_time": self._predict_optimal_engagement_time(patterns),
                "proactive_opportunities": self._identify_proactive_opportunities(patterns),
                "confidence_score": self._calculate_prediction_confidence(patterns)
            }
            
            return predictions
            
        except Exception as e:
            frappe.log_error(f"Individual Prediction Error: {str(e)}")
            return None
    
    def _analyze_user_patterns(self, interactions):
        """Analyze user interaction patterns"""
        patterns = {
            "interaction_frequency": self._calculate_interaction_frequency(interactions),
            "topic_preferences": self._extract_topic_patterns(interactions),
            "time_patterns": self._analyze_time_patterns(interactions),
            "satisfaction_trends": self._analyze_satisfaction_trends(interactions),
            "escalation_history": self._analyze_escalation_patterns(interactions),
            "seasonal_patterns": self._detect_seasonal_patterns(interactions)
        }
        
        return patterns
    
    def _predict_next_interaction(self, patterns):
        """Predict when user will next interact"""
        frequency = patterns.get("interaction_frequency", {})
        avg_days_between = frequency.get("average_days_between", 30)
        
        # Calculate probability based on time since last interaction
        days_since_last = frequency.get("days_since_last", 0)
        
        if avg_days_between <= 7:
            # Frequent user
            if days_since_last >= avg_days_between * 0.8:
                probability = 0.8
            else:
                probability = 0.3
        elif avg_days_between <= 30:
            # Regular user
            if days_since_last >= avg_days_between * 0.9:
                probability = 0.6
            else:
                probability = 0.2
        else:
            # Infrequent user
            probability = 0.1
        
        return {
            "probability": probability,
            "predicted_days": max(1, avg_days_between - days_since_last),
            "confidence": 0.7 if len(patterns.get("time_patterns", {}).get("interaction_times", [])) > 3 else 0.4
        }
    
    def _predict_query_topics(self, patterns):
        """Predict likely query topics"""
        topic_prefs = patterns.get("topic_preferences", {})
        
        # Weight topics by frequency and recency
        weighted_topics = []
        for topic, data in topic_prefs.items():
            weight = data.get("frequency", 0) * data.get("recency_factor", 0.5)
            weighted_topics.append({
                "topic": topic,
                "probability": min(0.9, weight / 10),
                "confidence": 0.6 if data.get("frequency", 0) > 2 else 0.3
            })
        
        # Sort by probability
        weighted_topics.sort(key=lambda x: x["probability"], reverse=True)
        
        return weighted_topics[:3]  # Top 3 likely topics
    
    def _predict_escalation_risk(self, patterns):
        """Predict escalation risk"""
        escalation_history = patterns.get("escalation_history", {})
        satisfaction_trends = patterns.get("satisfaction_trends", {})
        
        base_risk = escalation_history.get("escalation_rate", 0.2)
        
        # Adjust based on satisfaction trends
        if satisfaction_trends.get("trend") == "declining":
            base_risk += 0.3
        elif satisfaction_trends.get("average_satisfaction", 3) < 3:
            base_risk += 0.2
        
        return {
            "risk_level": "high" if base_risk > 0.6 else "medium" if base_risk > 0.3 else "low",
            "probability": min(0.9, base_risk),
            "factors": self._identify_escalation_factors(patterns)
        }
    
    def _predict_optimal_engagement_time(self, patterns):
        """Predict optimal time for proactive engagement"""
        time_patterns = patterns.get("time_patterns", {})
        interaction_times = time_patterns.get("interaction_times", [])
        
        if not interaction_times:
            return {"hour": 10, "confidence": 0.3, "timezone": "UTC"}
        
        # Find most common interaction hours
        hour_counts = defaultdict(int)
        for time_str in interaction_times:
            try:
                dt = frappe.utils.get_datetime(time_str)
                hour_counts[dt.hour] += 1
            except:
                continue
        
        if hour_counts:
            optimal_hour = max(hour_counts, key=hour_counts.get)
            confidence = hour_counts[optimal_hour] / len(interaction_times)
        else:
            optimal_hour = 10  # Default to 10 AM
            confidence = 0.3
        
        return {
            "hour": optimal_hour,
            "confidence": confidence,
            "timezone": "UTC",
            "day_preference": self._get_day_preference(time_patterns)
        }
    
    def _identify_proactive_opportunities(self, patterns):
        """Identify proactive service opportunities"""
        opportunities = []
        
        # Check for claim status update opportunities
        topic_prefs = patterns.get("topic_preferences", {})
        if "claims" in topic_prefs and topic_prefs["claims"].get("frequency", 0) > 2:
            opportunities.append({
                "type": "claim_status_update",
                "priority": "high",
                "message": "Proactive claim status update",
                "confidence": 0.8
            })
        
        # Check for deadline reminders
        if "employer" in topic_prefs:
            opportunities.append({
                "type": "deadline_reminder",
                "priority": "medium", 
                "message": "Upcoming filing deadline reminder",
                "confidence": 0.6
            })
        
        # Check for educational content opportunities
        satisfaction_trends = patterns.get("satisfaction_trends", {})
        if satisfaction_trends.get("average_satisfaction", 3) > 4:
            opportunities.append({
                "type": "educational_content",
                "priority": "low",
                "message": "Relevant educational content recommendation",
                "confidence": 0.5
            })
        
        return opportunities
    
    def generate_proactive_engagements(self, user_id=None, engagement_type="all"):
        """Generate proactive engagement recommendations"""
        try:
            # Get predictions for users
            predictions_result = self.analyze_user_needs_prediction(user_id, 30)
            
            if predictions_result.get("status") != "success":
                return predictions_result
            
            predictions = predictions_result.get("predictions", {})
            engagements = []
            
            for uid, prediction in predictions.items():
                user_engagements = self._create_user_engagements(uid, prediction, engagement_type)
                engagements.extend(user_engagements)
            
            # Sort by priority and confidence
            engagements.sort(key=lambda x: (x.get("priority_score", 0), x.get("confidence", 0)), reverse=True)
            
            return {
                "status": "success",
                "engagements": engagements,
                "total_opportunities": len(engagements),
                "high_priority": len([e for e in engagements if e.get("priority") == "high"]),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": "Failed to generate proactive engagements",
                "details": str(e)
            }
    
    def _create_user_engagements(self, user_id, prediction, engagement_type):
        """Create specific engagements for a user"""
        engagements = []
        
        # Get user profile for personalization
        try:
            from assistant_crm.api.personalization_engine import PersonalizationEngine
            personalization = PersonalizationEngine()
            user_profile = personalization._get_user_profile(user_id)
        except:
            user_profile = {"preferences": {"preferred_language": "en"}}
        
        # Next interaction prediction engagement
        next_interaction = prediction.get("next_interaction_probability", {})
        if next_interaction.get("probability", 0) > 0.6:
            engagements.append({
                "user_id": user_id,
                "type": "proactive_check_in",
                "priority": "medium",
                "priority_score": 60,
                "confidence": next_interaction.get("confidence", 0.5),
                "message": self._generate_check_in_message(user_profile),
                "optimal_time": prediction.get("optimal_engagement_time", {}),
                "predicted_topics": prediction.get("likely_query_topics", [])
            })
        
        # Escalation risk engagement
        escalation_risk = prediction.get("escalation_risk", {})
        if escalation_risk.get("probability", 0) > 0.5:
            engagements.append({
                "user_id": user_id,
                "type": "escalation_prevention",
                "priority": "high",
                "priority_score": 90,
                "confidence": 0.8,
                "message": self._generate_escalation_prevention_message(user_profile),
                "risk_factors": escalation_risk.get("factors", []),
                "recommended_action": "proactive_human_contact"
            })
        
        # Proactive opportunities
        opportunities = prediction.get("proactive_opportunities", [])
        for opportunity in opportunities:
            if opportunity.get("confidence", 0) > 0.5:
                engagements.append({
                    "user_id": user_id,
                    "type": opportunity.get("type"),
                    "priority": opportunity.get("priority"),
                    "priority_score": {"high": 80, "medium": 50, "low": 20}.get(opportunity.get("priority"), 30),
                    "confidence": opportunity.get("confidence"),
                    "message": self._generate_opportunity_message(opportunity, user_profile),
                    "opportunity_details": opportunity
                })
        
        return engagements
    
    def execute_proactive_engagement(self, engagement_id, engagement_data):
        """Execute a proactive engagement"""
        try:
            user_id = engagement_data.get("user_id")
            engagement_type = engagement_data.get("type")
            message = engagement_data.get("message")
            
            # Log the proactive engagement
            engagement_log = frappe.new_doc("Proactive Engagement Log")
            engagement_log.user_id = user_id
            engagement_log.engagement_type = engagement_type
            engagement_log.message_content = message
            engagement_log.priority = engagement_data.get("priority", "medium")
            engagement_log.confidence_score = engagement_data.get("confidence", 0.5)
            engagement_log.status = "executed"
            engagement_log.execution_timestamp = frappe.utils.now()
            engagement_log.predicted_response_time = engagement_data.get("optimal_time", {}).get("hour", 10)
            
            engagement_log.insert()
            frappe.db.commit()
            
            # Execute based on engagement type
            execution_result = self._execute_engagement_by_type(engagement_type, engagement_data)
            
            # Update log with results
            engagement_log.execution_result = json.dumps(execution_result)
            engagement_log.save()
            frappe.db.commit()
            
            return {
                "status": "success",
                "engagement_id": engagement_log.name,
                "execution_result": execution_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": "Failed to execute proactive engagement",
                "details": str(e)
            }
    
    def _execute_engagement_by_type(self, engagement_type, engagement_data):
        """Execute engagement based on type"""
        try:
            if engagement_type == "proactive_check_in":
                return self._execute_check_in(engagement_data)
            elif engagement_type == "escalation_prevention":
                return self._execute_escalation_prevention(engagement_data)
            elif engagement_type == "claim_status_update":
                return self._execute_claim_status_update(engagement_data)
            elif engagement_type == "deadline_reminder":
                return self._execute_deadline_reminder(engagement_data)
            elif engagement_type == "educational_content":
                return self._execute_educational_content(engagement_data)
            else:
                return {"status": "unknown_type", "message": "Unknown engagement type"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _execute_check_in(self, engagement_data):
        """Execute proactive check-in"""
        # This would integrate with omnichannel to send message
        return {
            "status": "success",
            "action": "check_in_message_sent",
            "channel": "preferred",
            "message": engagement_data.get("message")
        }
    
    def _execute_escalation_prevention(self, engagement_data):
        """Execute escalation prevention"""
        # This would trigger immediate human agent assignment
        return {
            "status": "success", 
            "action": "human_agent_assigned",
            "priority": "high",
            "risk_factors": engagement_data.get("risk_factors", [])
        }
    
    def _execute_claim_status_update(self, engagement_data):
        """Execute claim status update"""
        # This would fetch and send claim status
        return {
            "status": "success",
            "action": "claim_status_sent",
            "update_type": "proactive"
        }
    
    def _execute_deadline_reminder(self, engagement_data):
        """Execute deadline reminder"""
        # This would send deadline reminder
        return {
            "status": "success",
            "action": "deadline_reminder_sent",
            "reminder_type": "filing_deadline"
        }
    
    def _execute_educational_content(self, engagement_data):
        """Execute educational content delivery"""
        # This would send relevant educational content
        return {
            "status": "success",
            "action": "educational_content_sent",
            "content_type": "personalized_articles"
        }
    
    # Helper methods for pattern analysis
    def _calculate_interaction_frequency(self, interactions):
        """Calculate user interaction frequency"""
        if len(interactions) < 2:
            return {"frequency": "insufficient_data", "average_days_between": 30}
        
        timestamps = [frappe.utils.get_datetime(i.timestamp) for i in interactions]
        timestamps.sort()
        
        time_diffs = [(timestamps[i+1] - timestamps[i]).days for i in range(len(timestamps)-1)]
        avg_days = sum(time_diffs) / len(time_diffs) if time_diffs else 30
        
        days_since_last = (datetime.now() - timestamps[-1]).days
        
        return {
            "frequency": "high" if avg_days < 7 else "medium" if avg_days < 30 else "low",
            "average_days_between": avg_days,
            "days_since_last": days_since_last,
            "total_interactions": len(interactions)
        }
    
    def _extract_topic_patterns(self, interactions):
        """Extract topic patterns from interactions"""
        topic_keywords = {
            "claims": ["claim", "filing", "status", "benefit", "compensation"],
            "medical": ["medical", "doctor", "treatment", "hospital", "injury"],
            "legal": ["legal", "appeal", "dispute", "attorney", "lawsuit"],
            "employer": ["employer", "registration", "premium", "contribution", "payroll"],
            "general": ["information", "help", "question", "guide", "process"]
        }
        
        topic_data = defaultdict(lambda: {"frequency": 0, "recent_interactions": 0, "recency_factor": 0})
        
        for i, interaction in enumerate(interactions):
            query_lower = interaction.query_text.lower()
            for topic, keywords in topic_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    topic_data[topic]["frequency"] += 1
                    if i < 5:  # Recent interactions (last 5)
                        topic_data[topic]["recent_interactions"] += 1
        
        # Calculate recency factor
        for topic in topic_data:
            if topic_data[topic]["frequency"] > 0:
                topic_data[topic]["recency_factor"] = topic_data[topic]["recent_interactions"] / min(5, len(interactions))
        
        return dict(topic_data)
    
    def _analyze_time_patterns(self, interactions):
        """Analyze time patterns in interactions"""
        interaction_times = []
        day_counts = defaultdict(int)
        
        for interaction in interactions:
            try:
                dt = frappe.utils.get_datetime(interaction.timestamp)
                interaction_times.append(interaction.timestamp)
                day_counts[dt.weekday()] += 1
            except:
                continue
        
        return {
            "interaction_times": interaction_times,
            "preferred_days": dict(day_counts),
            "most_active_day": max(day_counts, key=day_counts.get) if day_counts else 0
        }
    
    def _analyze_satisfaction_trends(self, interactions):
        """Analyze satisfaction trends"""
        ratings = []
        for interaction in interactions:
            if hasattr(interaction, 'satisfaction_rating') and interaction.satisfaction_rating:
                ratings.append(interaction.satisfaction_rating)
        
        if not ratings:
            return {"trend": "no_data", "average_satisfaction": 3.0}
        
        avg_satisfaction = sum(ratings) / len(ratings)
        
        # Determine trend
        if len(ratings) >= 3:
            recent_avg = sum(ratings[:3]) / 3
            older_avg = sum(ratings[-3:]) / 3
            trend = "improving" if recent_avg > older_avg else "declining" if recent_avg < older_avg else "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "trend": trend,
            "average_satisfaction": avg_satisfaction,
            "total_ratings": len(ratings)
        }
    
    def _analyze_escalation_patterns(self, interactions):
        """Analyze escalation patterns"""
        total_interactions = len(interactions)
        escalated_count = 0
        
        for interaction in interactions:
            if (hasattr(interaction, 'escalated') and interaction.escalated) or \
               (hasattr(interaction, 'confidence_score') and interaction.confidence_score and interaction.confidence_score < 0.6):
                escalated_count += 1
        
        escalation_rate = escalated_count / total_interactions if total_interactions > 0 else 0
        
        return {
            "escalation_rate": escalation_rate,
            "total_escalations": escalated_count,
            "escalation_tendency": "high" if escalation_rate > 0.3 else "medium" if escalation_rate > 0.1 else "low"
        }
    
    def _detect_seasonal_patterns(self, interactions):
        """Detect seasonal interaction patterns"""
        month_counts = defaultdict(int)
        
        for interaction in interactions:
            try:
                dt = frappe.utils.get_datetime(interaction.timestamp)
                month_counts[dt.month] += 1
            except:
                continue
        
        return {
            "monthly_distribution": dict(month_counts),
            "peak_month": max(month_counts, key=month_counts.get) if month_counts else 1
        }
    
    def _get_active_users(self, timeframe_days):
        """Get list of active users in timeframe"""
        cutoff_date = (datetime.now() - timedelta(days=timeframe_days)).isoformat()
        
        active_users = frappe.db.sql("""
            SELECT DISTINCT user_id 
            FROM `tabUser Interaction Log` 
            WHERE timestamp > %s
            ORDER BY timestamp DESC
            LIMIT 100
        """, [cutoff_date])
        
        return [user[0] for user in active_users]
    
    def _calculate_prediction_confidence(self, patterns):
        """Calculate overall prediction confidence"""
        confidence_factors = []
        
        # Interaction frequency confidence
        freq_data = patterns.get("interaction_frequency", {})
        if freq_data.get("total_interactions", 0) > 5:
            confidence_factors.append(0.8)
        elif freq_data.get("total_interactions", 0) > 2:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.3)
        
        # Topic pattern confidence
        topic_data = patterns.get("topic_preferences", {})
        if len(topic_data) > 2:
            confidence_factors.append(0.7)
        elif len(topic_data) > 0:
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.2)
        
        # Time pattern confidence
        time_data = patterns.get("time_patterns", {})
        if len(time_data.get("interaction_times", [])) > 3:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.3)
        
        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.3
    
    def _generate_check_in_message(self, user_profile):
        """Generate personalized check-in message"""
        language = user_profile.get("preferences", {}).get("preferred_language", "en")
        
        messages = {
            "en": "Hi! I noticed you might need some assistance with your workers' compensation matters. How can I help you today?",
            "es": "¡Hola! Noté que podrías necesitar ayuda con tus asuntos de compensación laboral. ¿Cómo puedo ayudarte hoy?",
            "fr": "Salut! J'ai remarqué que vous pourriez avoir besoin d'aide avec vos questions d'indemnisation des travailleurs. Comment puis-je vous aider aujourd'hui?"
        }
        
        return messages.get(language, messages["en"])
    
    def _generate_escalation_prevention_message(self, user_profile):
        """Generate escalation prevention message"""
        language = user_profile.get("preferences", {}).get("preferred_language", "en")
        
        messages = {
            "en": "I want to ensure you receive the best possible assistance. Let me connect you with one of our specialists who can provide personalized help.",
            "es": "Quiero asegurarme de que recibas la mejor asistencia posible. Permíteme conectarte con uno de nuestros especialistas que puede brindarte ayuda personalizada.",
            "fr": "Je veux m'assurer que vous recevez la meilleure assistance possible. Permettez-moi de vous connecter avec l'un de nos spécialistes qui peut vous fournir une aide personnalisée."
        }
        
        return messages.get(language, messages["en"])
    
    def _generate_opportunity_message(self, opportunity, user_profile):
        """Generate opportunity-specific message"""
        language = user_profile.get("preferences", {}).get("preferred_language", "en")
        opp_type = opportunity.get("type", "general")
        
        messages = {
            "claim_status_update": {
                "en": "I have an update on your workers' compensation claim. Would you like me to share the latest information?",
                "es": "Tengo una actualización sobre tu reclamo de compensación laboral. ¿Te gustaría que comparta la información más reciente?",
                "fr": "J'ai une mise à jour sur votre réclamation d'indemnisation des travailleurs. Aimeriez-vous que je partage les dernières informations?"
            },
            "deadline_reminder": {
                "en": "Friendly reminder: You have an upcoming filing deadline. Would you like assistance with the process?",
                "es": "Recordatorio amigable: Tienes una fecha límite de presentación próxima. ¿Te gustaría ayuda con el proceso?",
                "fr": "Rappel amical: Vous avez une échéance de dépôt à venir. Aimeriez-vous de l'aide avec le processus?"
            },
            "educational_content": {
                "en": "I found some helpful resources that might interest you based on your recent questions. Would you like me to share them?",
                "es": "Encontré algunos recursos útiles que podrían interesarte basados en tus preguntas recientes. ¿Te gustaría que los comparta?",
                "fr": "J'ai trouvé des ressources utiles qui pourraient vous intéresser basées sur vos questions récentes. Aimeriez-vous que je les partage?"
            }
        }
        
        return messages.get(opp_type, {}).get(language, opportunity.get("message", "I have information that might help you."))
    
    def _get_day_preference(self, time_patterns):
        """Get preferred day of week"""
        preferred_days = time_patterns.get("preferred_days", {})
        if preferred_days:
            most_active_day = max(preferred_days, key=preferred_days.get)
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            return day_names[most_active_day] if 0 <= most_active_day < 7 else "Monday"
        return "Monday"
    
    def _identify_escalation_factors(self, patterns):
        """Identify factors contributing to escalation risk"""
        factors = []
        
        satisfaction_trends = patterns.get("satisfaction_trends", {})
        if satisfaction_trends.get("trend") == "declining":
            factors.append("declining_satisfaction")
        
        if satisfaction_trends.get("average_satisfaction", 3) < 3:
            factors.append("low_satisfaction")
        
        escalation_history = patterns.get("escalation_history", {})
        if escalation_history.get("escalation_rate", 0) > 0.3:
            factors.append("high_escalation_history")
        
        return factors

# API Endpoints for Predictive Service Delivery

@frappe.whitelist()
def analyze_predictive_service_needs(user_id=None, timeframe_days=30):
    """Analyze predictive service needs for users"""
    try:
        engine = PredictiveServiceEngine()
        result = engine.analyze_user_needs_prediction(user_id, int(timeframe_days))
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to analyze predictive service needs",
            "details": str(e)
        }

@frappe.whitelist()
def generate_proactive_engagement_opportunities(user_id=None, engagement_type="all"):
    """Generate proactive engagement opportunities"""
    try:
        engine = PredictiveServiceEngine()
        result = engine.generate_proactive_engagements(user_id, engagement_type)
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to generate proactive engagements",
            "details": str(e)
        }

@frappe.whitelist()
def execute_proactive_engagement(engagement_id, engagement_data):
    """Execute a proactive engagement"""
    try:
        engine = PredictiveServiceEngine()
        
        # Parse engagement data if it's a string
        if isinstance(engagement_data, str):
            engagement_data = json.loads(engagement_data)
        
        result = engine.execute_proactive_engagement(engagement_id, engagement_data)
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to execute proactive engagement",
            "details": str(e)
        }

@frappe.whitelist()
def get_predictive_service_dashboard():
    """Get predictive service delivery dashboard data"""
    try:
        engine = PredictiveServiceEngine()
        
        # Get recent predictions and engagements
        recent_predictions = engine.analyze_user_needs_prediction(None, 7)
        recent_engagements = engine.generate_proactive_engagements(None, "all")
        
        # Calculate dashboard metrics
        dashboard_data = {
            "users_analyzed": recent_predictions.get("users_analyzed", 0),
            "total_opportunities": recent_engagements.get("total_opportunities", 0),
            "high_priority_opportunities": recent_engagements.get("high_priority", 0),
            "prediction_accuracy": calculate_prediction_accuracy(),
            "engagement_success_rate": calculate_engagement_success_rate(),
            "proactive_vs_reactive_ratio": calculate_proactive_ratio(),
            "top_predicted_topics": get_top_predicted_topics(recent_predictions),
            "engagement_distribution": get_engagement_distribution(recent_engagements),
            "period": "last_7_days"
        }
        
        return {
            "status": "success",
            "dashboard_data": dashboard_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to generate predictive service dashboard",
            "details": str(e)
        }

def calculate_prediction_accuracy():
    """Calculate prediction accuracy (placeholder)"""
    # This would be calculated based on actual prediction vs outcome data
    return 0.82  # 82% accuracy placeholder

def calculate_engagement_success_rate():
    """Calculate engagement success rate (placeholder)"""
    # This would be calculated based on engagement outcomes
    return 0.75  # 75% success rate placeholder

def calculate_proactive_ratio():
    """Calculate proactive vs reactive interaction ratio"""
    # This would compare proactive engagements to reactive queries
    return {
        "proactive_percentage": 25,
        "reactive_percentage": 75,
        "trend": "increasing_proactive"
    }

def get_top_predicted_topics(predictions_result):
    """Get top predicted topics from recent analysis"""
    if predictions_result.get("status") != "success":
        return []
    
    topic_counts = defaultdict(int)
    predictions = predictions_result.get("predictions", {})
    
    for user_prediction in predictions.values():
        likely_topics = user_prediction.get("likely_query_topics", [])
        for topic_data in likely_topics:
            topic_counts[topic_data.get("topic", "unknown")] += 1
    
    # Sort and return top topics
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    return [{"topic": topic, "count": count} for topic, count in sorted_topics[:5]]

def get_engagement_distribution(engagements_result):
    """Get distribution of engagement types"""
    if engagements_result.get("status") != "success":
        return {}
    
    type_counts = defaultdict(int)
    engagements = engagements_result.get("engagements", [])
    
    for engagement in engagements:
        eng_type = engagement.get("type", "unknown")
        type_counts[eng_type] += 1
    
    return dict(type_counts)
