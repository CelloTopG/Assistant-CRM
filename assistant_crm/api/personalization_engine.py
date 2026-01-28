#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Phase 4.4: Personalization Engine
Implements user-specific content recommendations and adaptive experiences
"""

import frappe
from frappe import _
import json
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict, Counter

class PersonalizationEngine:
    """Advanced personalization engine for tailored user experiences"""
    
    def __init__(self):
        self.user_profiles = {}
        self.content_preferences = {}
        self.interaction_patterns = {}
        
    def get_personalized_experience(self, user_id, current_query=None, context=None):
        """Get personalized experience for user"""
        try:
            # Get or create user profile
            user_profile = self._get_user_profile(user_id)
            
            # Analyze current context
            current_context = self._analyze_current_context(current_query, context)
            
            # Generate personalized recommendations
            recommendations = self._generate_personalized_recommendations(user_profile, current_context)
            
            # Get adaptive interface settings
            interface_settings = self._get_adaptive_interface_settings(user_profile)
            
            # Get personalized content
            personalized_content = self._get_personalized_content(user_profile, current_context)
            
            return {
                "user_id": user_id,
                "user_profile": user_profile,
                "recommendations": recommendations,
                "interface_settings": interface_settings,
                "personalized_content": personalized_content,
                "personalization_confidence": self._calculate_personalization_confidence(user_profile),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            frappe.log_error(f"Personalization Error: {str(e)}")
            return self._get_default_experience(user_id)
    
    def _get_user_profile(self, user_id):
        """Get comprehensive user profile"""
        try:
            # Check if ML User Profile exists
            ml_profile = None
            if frappe.db.exists("ML User Profile", user_id):
                ml_profile = frappe.get_doc("ML User Profile", user_id)
            
            # Get interaction history
            interactions = frappe.get_all("User Interaction Log",
                filters={"user_id": user_id},
                fields=["*"],
                order_by="timestamp desc",
                limit=50
            )
            
            # Build comprehensive profile
            profile = {
                "user_id": user_id,
                "interaction_count": len(interactions),
                "preferences": self._extract_user_preferences(interactions),
                "behavior_patterns": self._analyze_behavior_patterns(interactions),
                "content_affinity": self._calculate_content_affinity(interactions),
                "communication_style": self._determine_communication_style(interactions),
                "satisfaction_history": self._analyze_satisfaction_history(interactions),
                "ml_insights": self._extract_ml_insights(ml_profile) if ml_profile else {},
                "last_updated": datetime.now().isoformat()
            }
            
            # Cache profile
            self.user_profiles[user_id] = profile
            
            return profile
            
        except Exception as e:
            frappe.log_error(f"User Profile Error: {str(e)}")
            return self._create_default_profile(user_id)
    
    def _extract_user_preferences(self, interactions):
        """Extract user preferences from interaction history"""
        preferences = {
            "preferred_language": "en",
            "preferred_topics": [],
            "response_length": "medium",
            "interaction_time": "business_hours",
            "channel_preference": "web",
            "help_seeking_pattern": "direct"
        }
        
        if not interactions:
            return preferences
        
        # Language preference
        languages = [i.language for i in interactions if hasattr(i, 'language') and i.language]
        if languages:
            preferences["preferred_language"] = Counter(languages).most_common(1)[0][0]
        
        # Topic preferences
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
        
        preferences["preferred_topics"] = [topic for topic, score in 
                                         sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)[:3]]
        
        # Response length preference
        response_lengths = []
        for interaction in interactions:
            if hasattr(interaction, 'response_provided') and interaction.response_provided:
                length = len(interaction.response_provided.split())
                response_lengths.append(length)
        
        if response_lengths:
            avg_length = np.mean(response_lengths)
            if avg_length < 50:
                preferences["response_length"] = "short"
            elif avg_length > 150:
                preferences["response_length"] = "detailed"
            else:
                preferences["response_length"] = "medium"
        
        # Interaction time patterns
        interaction_hours = []
        for interaction in interactions:
            hour = frappe.utils.get_datetime(interaction.timestamp).hour
            interaction_hours.append(hour)
        
        if interaction_hours:
            avg_hour = np.mean(interaction_hours)
            if 9 <= avg_hour <= 17:
                preferences["interaction_time"] = "business_hours"
            elif 18 <= avg_hour <= 22:
                preferences["interaction_time"] = "evening"
            else:
                preferences["interaction_time"] = "off_hours"
        
        return preferences
    
    def _analyze_behavior_patterns(self, interactions):
        """Analyze user behavior patterns"""
        patterns = {
            "query_complexity": "medium",
            "help_seeking_style": "direct",
            "patience_level": "medium",
            "technical_comfort": "medium",
            "escalation_tendency": "low"
        }
        
        if not interactions:
            return patterns
        
        # Query complexity analysis
        query_lengths = [len(i.query_text.split()) for i in interactions]
        avg_query_length = np.mean(query_lengths) if query_lengths else 5
        
        if avg_query_length < 5:
            patterns["query_complexity"] = "simple"
        elif avg_query_length > 15:
            patterns["query_complexity"] = "complex"
        
        # Help seeking style
        direct_indicators = ["how", "what", "where", "when", "can you", "please"]
        exploratory_indicators = ["tell me about", "explain", "understand", "learn"]
        
        direct_count = 0
        exploratory_count = 0
        
        for interaction in interactions:
            query_lower = interaction.query_text.lower()
            if any(indicator in query_lower for indicator in direct_indicators):
                direct_count += 1
            if any(indicator in query_lower for indicator in exploratory_indicators):
                exploratory_count += 1
        
        if direct_count > exploratory_count:
            patterns["help_seeking_style"] = "direct"
        else:
            patterns["help_seeking_style"] = "exploratory"
        
        # Patience level (based on follow-up patterns)
        session_groups = defaultdict(list)
        for interaction in interactions:
            session_id = getattr(interaction, 'session_id', 'default')
            session_groups[session_id].append(interaction)
        
        quick_follow_ups = 0
        total_sessions = len(session_groups)
        
        for session_interactions in session_groups.values():
            if len(session_interactions) > 3:  # Multiple queries in same session
                quick_follow_ups += 1
        
        if total_sessions > 0:
            follow_up_rate = quick_follow_ups / total_sessions
            if follow_up_rate > 0.6:
                patterns["patience_level"] = "low"
            elif follow_up_rate < 0.3:
                patterns["patience_level"] = "high"
        
        # Technical comfort level
        technical_terms = ["api", "system", "database", "configuration", "integration", "technical"]
        technical_queries = sum(1 for i in interactions 
                              if any(term in i.query_text.lower() for term in technical_terms))
        
        if len(interactions) > 0:
            technical_ratio = technical_queries / len(interactions)
            if technical_ratio > 0.3:
                patterns["technical_comfort"] = "high"
            elif technical_ratio < 0.1:
                patterns["technical_comfort"] = "low"
        
        # Escalation tendency
        escalated_interactions = sum(1 for i in interactions 
                                   if getattr(i, 'escalated', False) or 
                                   (hasattr(i, 'confidence_score') and i.confidence_score and i.confidence_score < 0.6))
        
        if len(interactions) > 0:
            escalation_rate = escalated_interactions / len(interactions)
            if escalation_rate > 0.3:
                patterns["escalation_tendency"] = "high"
            elif escalation_rate < 0.1:
                patterns["escalation_tendency"] = "low"
        
        return patterns
    
    def _calculate_content_affinity(self, interactions):
        """Calculate user's affinity for different content types"""
        content_affinity = {
            "step_by_step_guides": 0.5,
            "quick_answers": 0.5,
            "detailed_explanations": 0.5,
            "visual_content": 0.5,
            "examples": 0.5,
            "official_documents": 0.5
        }
        
        if not interactions:
            return content_affinity
        
        # Analyze query patterns to infer content preferences
        for interaction in interactions:
            query_lower = interaction.query_text.lower()
            
            # Step-by-step preference
            if any(phrase in query_lower for phrase in ["how to", "step by step", "guide", "process"]):
                content_affinity["step_by_step_guides"] += 0.1
            
            # Quick answer preference
            if any(phrase in query_lower for phrase in ["quick", "fast", "brief", "summary"]):
                content_affinity["quick_answers"] += 0.1
            
            # Detailed explanation preference
            if any(phrase in query_lower for phrase in ["explain", "detail", "comprehensive", "thorough"]):
                content_affinity["detailed_explanations"] += 0.1
            
            # Example preference
            if any(phrase in query_lower for phrase in ["example", "sample", "instance", "case"]):
                content_affinity["examples"] += 0.1
            
            # Official document preference
            if any(phrase in query_lower for phrase in ["official", "document", "form", "regulation"]):
                content_affinity["official_documents"] += 0.1
        
        # Normalize scores
        for key in content_affinity:
            content_affinity[key] = min(1.0, content_affinity[key])
        
        return content_affinity
    
    def _determine_communication_style(self, interactions):
        """Determine preferred communication style"""
        style = {
            "formality": "professional",
            "tone": "helpful",
            "verbosity": "balanced",
            "empathy_level": "standard"
        }
        
        if not interactions:
            return style
        
        # Analyze user's language patterns
        formal_indicators = ["please", "thank you", "could you", "would you", "appreciate"]
        casual_indicators = ["hey", "hi", "thanks", "can you", "help me"]
        
        formal_count = 0
        casual_count = 0
        
        for interaction in interactions:
            query_lower = interaction.query_text.lower()
            formal_count += sum(1 for indicator in formal_indicators if indicator in query_lower)
            casual_count += sum(1 for indicator in casual_indicators if indicator in query_lower)
        
        if formal_count > casual_count * 1.5:
            style["formality"] = "formal"
        elif casual_count > formal_count * 1.5:
            style["formality"] = "casual"
        
        # Determine empathy needs based on sentiment history
        negative_interactions = sum(1 for i in interactions 
                                  if hasattr(i, 'ml_sentiment_score') and 
                                  i.ml_sentiment_score and i.ml_sentiment_score < -0.3)
        
        if len(interactions) > 0:
            negative_ratio = negative_interactions / len(interactions)
            if negative_ratio > 0.3:
                style["empathy_level"] = "high"
            elif negative_ratio < 0.1:
                style["empathy_level"] = "standard"
        
        return style
    
    def _analyze_satisfaction_history(self, interactions):
        """Analyze user satisfaction history"""
        satisfaction_data = {
            "average_rating": 3.0,
            "trend": "stable",
            "consistency": "medium",
            "improvement_areas": []
        }
        
        ratings = [i.satisfaction_rating for i in interactions if i.satisfaction_rating]
        
        if ratings:
            satisfaction_data["average_rating"] = np.mean(ratings)
            
            # Calculate trend
            if len(ratings) >= 5:
                recent_avg = np.mean(ratings[:3])
                older_avg = np.mean(ratings[-3:])
                
                if recent_avg > older_avg + 0.5:
                    satisfaction_data["trend"] = "improving"
                elif recent_avg < older_avg - 0.5:
                    satisfaction_data["trend"] = "declining"
            
            # Calculate consistency
            if len(ratings) >= 3:
                std_dev = np.std(ratings)
                if std_dev < 0.5:
                    satisfaction_data["consistency"] = "high"
                elif std_dev > 1.0:
                    satisfaction_data["consistency"] = "low"
        
        # Identify improvement areas
        low_satisfaction_interactions = [i for i in interactions 
                                       if i.satisfaction_rating and i.satisfaction_rating < 3]
        
        if low_satisfaction_interactions:
            # Analyze common themes in low satisfaction interactions
            common_issues = []
            for interaction in low_satisfaction_interactions:
                if "slow" in interaction.query_text.lower():
                    common_issues.append("response_speed")
                if "confusing" in interaction.query_text.lower():
                    common_issues.append("clarity")
                if "not helpful" in interaction.query_text.lower():
                    common_issues.append("relevance")
            
            satisfaction_data["improvement_areas"] = list(set(common_issues))
        
        return satisfaction_data
    
    def _extract_ml_insights(self, ml_profile):
        """Extract insights from ML User Profile"""
        if not ml_profile:
            return {}
        
        return {
            "escalation_tendency": ml_profile.escalation_tendency,
            "satisfaction_average": ml_profile.satisfaction_average,
            "query_frequency_pattern": ml_profile.query_frequency_pattern,
            "preferred_topics": json.loads(ml_profile.preferred_topics) if ml_profile.preferred_topics else [],
            "optimal_response_style": ml_profile.optimal_response_style,
            "ml_confidence_score": ml_profile.ml_confidence_score
        }
    
    def _analyze_current_context(self, current_query, context):
        """Analyze current interaction context"""
        current_context = {
            "query_intent": "general",
            "urgency_level": "normal",
            "complexity": "medium",
            "emotional_state": "neutral"
        }
        
        if current_query:
            query_lower = current_query.lower()
            
            # Detect urgency
            urgent_indicators = ["urgent", "emergency", "asap", "immediately", "quickly"]
            if any(indicator in query_lower for indicator in urgent_indicators):
                current_context["urgency_level"] = "high"
            
            # Detect complexity
            complex_indicators = ["complex", "complicated", "multiple", "various", "several"]
            simple_indicators = ["simple", "quick", "basic", "just"]
            
            if any(indicator in query_lower for indicator in complex_indicators):
                current_context["complexity"] = "high"
            elif any(indicator in query_lower for indicator in simple_indicators):
                current_context["complexity"] = "low"
            
            # Detect emotional state
            frustrated_indicators = ["frustrated", "annoyed", "difficult", "problem"]
            if any(indicator in query_lower for indicator in frustrated_indicators):
                current_context["emotional_state"] = "frustrated"
        
        # Add external context
        if context:
            current_context.update(context)
        
        return current_context
    
    def _generate_personalized_recommendations(self, user_profile, current_context):
        """Generate personalized recommendations"""
        recommendations = {
            "content_suggestions": [],
            "interaction_style": {},
            "proactive_offers": [],
            "optimization_tips": []
        }
        
        # Content suggestions based on preferences
        preferred_topics = user_profile.get("preferences", {}).get("preferred_topics", [])
        for topic in preferred_topics[:2]:  # Top 2 preferred topics
            recommendations["content_suggestions"].append({
                "type": "topic_based",
                "topic": topic,
                "reason": f"Based on your interest in {topic} topics",
                "priority": "medium"
            })
        
        # Interaction style recommendations
        communication_style = user_profile.get("communication_style", {})
        recommendations["interaction_style"] = {
            "formality": communication_style.get("formality", "professional"),
            "response_length": user_profile.get("preferences", {}).get("response_length", "medium"),
            "empathy_level": communication_style.get("empathy_level", "standard"),
            "technical_level": user_profile.get("behavior_patterns", {}).get("technical_comfort", "medium")
        }
        
        # Proactive offers based on patterns
        behavior_patterns = user_profile.get("behavior_patterns", {})
        if behavior_patterns.get("escalation_tendency") == "high":
            recommendations["proactive_offers"].append({
                "type": "human_assistance",
                "message": "Would you like to speak with a specialist?",
                "reason": "Based on your preference for detailed assistance"
            })
        
        if current_context.get("urgency_level") == "high":
            recommendations["proactive_offers"].append({
                "type": "priority_handling",
                "message": "I'll prioritize your request for immediate assistance",
                "reason": "Urgent request detected"
            })
        
        # Optimization tips
        satisfaction_history = user_profile.get("satisfaction_history", {})
        improvement_areas = satisfaction_history.get("improvement_areas", [])
        
        for area in improvement_areas:
            if area == "response_speed":
                recommendations["optimization_tips"].append({
                    "tip": "Use quick commands like 'STATUS' for faster responses",
                    "category": "efficiency"
                })
            elif area == "clarity":
                recommendations["optimization_tips"].append({
                    "tip": "Try asking specific questions for clearer answers",
                    "category": "communication"
                })
        
        return recommendations
    
    def _get_adaptive_interface_settings(self, user_profile):
        """Get adaptive interface settings"""
        settings = {
            "language": "en",
            "theme": "standard",
            "layout": "default",
            "quick_actions": [],
            "default_view": "conversation"
        }
        
        # Language setting
        preferred_language = user_profile.get("preferences", {}).get("preferred_language", "en")
        settings["language"] = preferred_language
        
        # Quick actions based on preferred topics
        preferred_topics = user_profile.get("preferences", {}).get("preferred_topics", [])
        topic_actions = {
            "claims": ["Check Claim Status", "File New Claim", "Appeal Decision"],
            "medical": ["Find Provider", "Medical Authorization", "Treatment Info"],
            "employer": ["Calculate Premium", "Register Business", "File Return"],
            "legal": ["Appeal Process", "Legal Resources", "Contact Attorney"]
        }
        
        for topic in preferred_topics[:2]:
            if topic in topic_actions:
                settings["quick_actions"].extend(topic_actions[topic][:2])
        
        # Layout based on technical comfort
        technical_comfort = user_profile.get("behavior_patterns", {}).get("technical_comfort", "medium")
        if technical_comfort == "low":
            settings["layout"] = "simplified"
        elif technical_comfort == "high":
            settings["layout"] = "advanced"
        
        return settings
    
    def _get_personalized_content(self, user_profile, current_context):
        """Get personalized content recommendations"""
        content = {
            "recommended_articles": [],
            "quick_replies": [],
            "related_topics": [],
            "personalized_greeting": ""
        }
        
        # Personalized greeting
        interaction_count = user_profile.get("interaction_count", 0)
        if interaction_count == 0:
            content["personalized_greeting"] = "Welcome to WCFCB! I'm here to help you with workers' compensation questions."
        elif interaction_count < 5:
            content["personalized_greeting"] = "Welcome back! How can I assist you today?"
        else:
            content["personalized_greeting"] = "Hello again! What can I help you with?"
        
        # Recommended articles based on preferences and context
        preferred_topics = user_profile.get("preferences", {}).get("preferred_topics", [])

        # Placeholder for article recommendations
        for topic in preferred_topics[:3]:
            content["recommended_articles"].append({
                "title": f"Information about {topic}",
                "reason": f"Based on your interest in {topic}",
                "relevance_score": 0.8
            })
        
        # Quick replies based on behavior patterns
        help_seeking_style = user_profile.get("behavior_patterns", {}).get("help_seeking_style", "direct")
        
        if help_seeking_style == "direct":
            content["quick_replies"] = [
                "Check claim status",
                "File new claim", 
                "Calculate premium",
                "Find medical provider"
            ]
        else:
            content["quick_replies"] = [
                "Tell me about workers compensation",
                "Explain the claim process",
                "Show me employer services",
                "Browse all topics"
            ]
        
        return content
    
    def _calculate_personalization_confidence(self, user_profile):
        """Calculate confidence in personalization accuracy"""
        interaction_count = user_profile.get("interaction_count", 0)
        
        # Base confidence on interaction count
        if interaction_count == 0:
            return 0.3
        elif interaction_count < 5:
            return 0.5
        elif interaction_count < 15:
            return 0.7
        else:
            return 0.9
    
    def _get_default_experience(self, user_id):
        """Get default experience for new or error cases"""
        return {
            "user_id": user_id,
            "user_profile": self._create_default_profile(user_id),
            "recommendations": {
                "content_suggestions": [],
                "interaction_style": {
                    "formality": "professional",
                    "response_length": "medium",
                    "empathy_level": "standard",
                    "technical_level": "medium"
                },
                "proactive_offers": [],
                "optimization_tips": []
            },
            "interface_settings": {
                "language": "en",
                "theme": "standard",
                "layout": "default",
                "quick_actions": ["Check Status", "Get Help", "Contact Agent"],
                "default_view": "conversation"
            },
            "personalized_content": {
                "recommended_articles": [],
                "quick_replies": ["How can I help?", "Check claim status", "File new claim"],
                "related_topics": [],
                "personalized_greeting": "Welcome to WCFCB! How can I assist you today?"
            },
            "personalization_confidence": 0.3,
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_default_profile(self, user_id):
        """Create default user profile"""
        return {
            "user_id": user_id,
            "interaction_count": 0,
            "preferences": {
                "preferred_language": "en",
                "preferred_topics": ["general"],
                "response_length": "medium",
                "interaction_time": "business_hours",
                "channel_preference": "web"
            },
            "behavior_patterns": {
                "query_complexity": "medium",
                "help_seeking_style": "direct",
                "patience_level": "medium",
                "technical_comfort": "medium",
                "escalation_tendency": "low"
            },
            "content_affinity": {
                "step_by_step_guides": 0.5,
                "quick_answers": 0.5,
                "detailed_explanations": 0.5,
                "examples": 0.5
            },
            "communication_style": {
                "formality": "professional",
                "tone": "helpful",
                "verbosity": "balanced",
                "empathy_level": "standard"
            },
            "satisfaction_history": {
                "average_rating": 3.0,
                "trend": "stable",
                "consistency": "medium",
                "improvement_areas": []
            },
            "last_updated": datetime.now().isoformat()
        }

# API Endpoints for Personalization

@frappe.whitelist()
def get_personalized_experience(user_id, current_query=None, context=None):
    """Get personalized experience for user"""
    try:
        engine = PersonalizationEngine()
        
        # Parse context if it's a string
        if isinstance(context, str):
            context = json.loads(context) if context else None
        
        experience = engine.get_personalized_experience(user_id, current_query, context)
        
        return {
            "status": "success",
            "personalized_experience": experience,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to get personalized experience",
            "details": str(e)
        }

@frappe.whitelist()
def update_user_preferences(user_id, preferences):
    """Update user preferences"""
    try:
        # Parse preferences if it's a string
        if isinstance(preferences, str):
            preferences = json.loads(preferences)
        
        # Get or create ML User Profile
        if frappe.db.exists("ML User Profile", user_id):
            profile = frappe.get_doc("ML User Profile", user_id)
        else:
            profile = frappe.new_doc("ML User Profile")
            profile.user_id = user_id
        
        # Update preferences
        if "language_preference" in preferences:
            profile.language_preference = preferences["language_preference"]
        
        if "preferred_topics" in preferences:
            profile.preferred_topics = json.dumps(preferences["preferred_topics"])
        
        if "optimal_response_style" in preferences:
            profile.optimal_response_style = preferences["optimal_response_style"]
        
        profile.profile_last_updated = frappe.utils.now()
        profile.save()
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": "User preferences updated successfully",
            "updated_preferences": preferences
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to update user preferences",
            "details": str(e)
        }

@frappe.whitelist()
def get_content_recommendations(user_id, topic=None, limit=5):
    """Get personalized content recommendations"""
    try:
        engine = PersonalizationEngine()
        user_profile = engine._get_user_profile(user_id)
        
        # Get recommended articles
        recommendations = []
        
        # Base recommendations on user preferences
        preferred_topics = user_profile.get("preferences", {}).get("preferred_topics", [])
        
        if topic:
            # Specific topic requested
            search_topics = [topic]
        else:
            # Use user's preferred topics
            search_topics = preferred_topics[:3] if preferred_topics else ["general"]
        
        # Placeholder for content recommendations
        for search_topic in search_topics:
            recommendations.append({
                "title": f"Information about {search_topic}",
                "category": search_topic,
                "relevance_score": 0.8,
                "reason": f"Matches your interest in {search_topic}"
            })
        
        return {
            "status": "success",
            "user_id": user_id,
            "recommendations": recommendations[:limit],
            "personalization_confidence": engine._calculate_personalization_confidence(user_profile)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to get content recommendations",
            "details": str(e)
        }
