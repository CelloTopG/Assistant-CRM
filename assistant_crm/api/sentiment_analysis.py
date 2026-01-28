#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Phase 4.3: Sentiment Analysis
Implements real-time customer satisfaction monitoring and emotion detection
"""

import frappe
from frappe import _
import re
import json
from datetime import datetime, timedelta
from collections import defaultdict

class SentimentAnalysisEngine:
    """Advanced sentiment analysis engine for customer interactions"""
    
    def __init__(self):
        self.emotion_patterns = self._load_emotion_patterns()
        self.sentiment_cache = {}
        self.satisfaction_thresholds = {
            "very_positive": 0.8,
            "positive": 0.4,
            "neutral": -0.2,
            "negative": -0.6,
            "very_negative": -1.0
        }
        
    def analyze_sentiment(self, text, user_id=None, context=None):
        """Analyze sentiment of user text"""
        try:
            # Clean and preprocess text
            cleaned_text = self._preprocess_text(text)
            
            # Calculate sentiment score
            sentiment_score = self._calculate_sentiment_score(cleaned_text)
            
            # Detect emotions
            emotions = self._detect_emotions(cleaned_text)
            
            # Determine satisfaction level
            satisfaction_level = self._determine_satisfaction_level(sentiment_score)
            
            # Get contextual insights
            contextual_insights = self._get_contextual_insights(sentiment_score, emotions, user_id, context)
            
            # Generate recommendations
            recommendations = self._generate_sentiment_recommendations(sentiment_score, emotions, contextual_insights)
            
            result = {
                "sentiment_score": sentiment_score,
                "satisfaction_level": satisfaction_level,
                "primary_emotion": emotions.get("primary", "neutral"),
                "emotion_confidence": emotions.get("confidence", 0.5),
                "emotions_detected": emotions.get("all_emotions", []),
                "contextual_insights": contextual_insights,
                "recommendations": recommendations,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            # Cache result for performance
            if user_id:
                self.sentiment_cache[f"{user_id}_{hash(text)}"] = result
            
            return result
            
        except Exception as e:
            frappe.log_error(f"Sentiment Analysis Error: {str(e)}")
            return {
                "sentiment_score": 0.0,
                "satisfaction_level": "neutral",
                "primary_emotion": "neutral",
                "error": str(e)
            }
    
    def _preprocess_text(self, text):
        """Clean and preprocess text for analysis"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Handle common abbreviations and slang
        replacements = {
            "u": "you",
            "ur": "your", 
            "cant": "cannot",
            "wont": "will not",
            "dont": "do not",
            "isnt": "is not",
            "arent": "are not",
            "wasnt": "was not",
            "werent": "were not"
        }
        
        for abbrev, full in replacements.items():
            text = re.sub(r'\b' + abbrev + r'\b', full, text)
        
        return text
    
    def _calculate_sentiment_score(self, text):
        """Calculate sentiment score (-1.0 to 1.0)"""
        # Positive sentiment indicators
        positive_words = {
            "excellent": 0.8, "great": 0.7, "good": 0.6, "helpful": 0.6,
            "satisfied": 0.7, "happy": 0.7, "pleased": 0.6, "thank": 0.5,
            "thanks": 0.5, "appreciate": 0.6, "wonderful": 0.8, "amazing": 0.8,
            "perfect": 0.9, "outstanding": 0.9, "fantastic": 0.8, "love": 0.7,
            "like": 0.4, "enjoy": 0.5, "impressed": 0.7, "recommend": 0.6,
            "efficient": 0.6, "quick": 0.5, "fast": 0.5, "easy": 0.5,
            "clear": 0.4, "helpful": 0.6, "useful": 0.5, "convenient": 0.5
        }
        
        # Negative sentiment indicators
        negative_words = {
            "terrible": -0.8, "awful": -0.8, "bad": -0.6, "poor": -0.6,
            "disappointed": -0.7, "frustrated": -0.7, "angry": -0.8, "upset": -0.7,
            "annoyed": -0.6, "confused": -0.5, "difficult": -0.5, "hard": -0.4,
            "slow": -0.5, "complicated": -0.6, "useless": -0.7, "waste": -0.6,
            "problem": -0.5, "issue": -0.4, "error": -0.5, "wrong": -0.5,
            "fail": -0.6, "failed": -0.6, "broken": -0.6, "not working": -0.7,
            "hate": -0.8, "dislike": -0.6, "horrible": -0.8, "worst": -0.9,
            "never": -0.4, "cannot": -0.4, "unable": -0.5, "impossible": -0.6
        }
        
        # Intensity modifiers
        intensifiers = {
            "very": 1.3, "extremely": 1.5, "really": 1.2, "quite": 1.1,
            "absolutely": 1.4, "completely": 1.3, "totally": 1.3, "highly": 1.2,
            "incredibly": 1.4, "amazingly": 1.3, "exceptionally": 1.4
        }
        
        # Negation words
        negations = ["not", "no", "never", "nothing", "nobody", "nowhere", "neither", "nor"]
        
        words = text.split()
        sentiment_score = 0.0
        word_count = 0
        
        for i, word in enumerate(words):
            # Check for negation in previous 2 words
            negated = False
            for j in range(max(0, i-2), i):
                if words[j] in negations:
                    negated = True
                    break
            
            # Check for intensifier in previous word
            intensifier = 1.0
            if i > 0 and words[i-1] in intensifiers:
                intensifier = intensifiers[words[i-1]]
            
            # Calculate word sentiment
            word_sentiment = 0.0
            if word in positive_words:
                word_sentiment = positive_words[word] * intensifier
            elif word in negative_words:
                word_sentiment = negative_words[word] * intensifier
            
            # Apply negation
            if negated:
                word_sentiment *= -0.8
            
            sentiment_score += word_sentiment
            if word_sentiment != 0:
                word_count += 1
        
        # Normalize score
        if word_count > 0:
            sentiment_score = sentiment_score / word_count
        
        # Ensure score is within bounds
        return max(-1.0, min(1.0, sentiment_score))
    
    def _detect_emotions(self, text):
        """Detect emotions in text"""
        emotion_patterns = {
            "frustrated": [
                r"frustrated", r"annoying", r"irritating", r"fed up",
                r"sick of", r"tired of", r"cannot believe", r"ridiculous"
            ],
            "angry": [
                r"angry", r"furious", r"mad", r"outraged", r"livid",
                r"hate", r"disgusted", r"appalled"
            ],
            "satisfied": [
                r"satisfied", r"content", r"pleased", r"happy",
                r"glad", r"delighted", r"thrilled"
            ],
            "confused": [
                r"confused", r"unclear", r"don't understand", r"not sure",
                r"puzzled", r"bewildered", r"lost"
            ],
            "urgent": [
                r"urgent", r"emergency", r"asap", r"immediately",
                r"right away", r"quickly", r"fast", r"hurry"
            ],
            "disappointed": [
                r"disappointed", r"let down", r"expected better",
                r"not what i expected", r"hoped for more"
            ],
            "grateful": [
                r"thank", r"grateful", r"appreciate", r"thankful",
                r"blessed", r"indebted"
            ]
        }
        
        detected_emotions = []
        emotion_scores = {}
        
        for emotion, patterns in emotion_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
            
            if score > 0:
                emotion_scores[emotion] = score
                detected_emotions.append(emotion)
        
        # Determine primary emotion
        primary_emotion = "neutral"
        confidence = 0.5
        
        if emotion_scores:
            primary_emotion = max(emotion_scores, key=emotion_scores.get)
            max_score = emotion_scores[primary_emotion]
            confidence = min(0.95, 0.5 + (max_score * 0.2))
        
        return {
            "primary": primary_emotion,
            "confidence": confidence,
            "all_emotions": detected_emotions,
            "emotion_scores": emotion_scores
        }
    
    def _determine_satisfaction_level(self, sentiment_score):
        """Determine satisfaction level from sentiment score"""
        if sentiment_score >= self.satisfaction_thresholds["very_positive"]:
            return "very_positive"
        elif sentiment_score >= self.satisfaction_thresholds["positive"]:
            return "positive"
        elif sentiment_score >= self.satisfaction_thresholds["neutral"]:
            return "neutral"
        elif sentiment_score >= self.satisfaction_thresholds["negative"]:
            return "negative"
        else:
            return "very_negative"
    
    def _get_contextual_insights(self, sentiment_score, emotions, user_id, context):
        """Get contextual insights based on user history and current interaction"""
        insights = {
            "sentiment_trend": "stable",
            "emotion_pattern": "normal",
            "escalation_risk": "low",
            "intervention_needed": False
        }
        
        try:
            if user_id:
                # Get user's recent interactions
                recent_interactions = frappe.get_all("User Interaction Log",
                    filters={
                        "user_id": user_id,
                        "timestamp": [">", (datetime.now() - timedelta(days=7)).isoformat()]
                    },
                    fields=["ml_sentiment_score", "satisfaction_rating", "timestamp"],
                    order_by="timestamp desc",
                    limit=10
                )
                
                if recent_interactions:
                    # Analyze sentiment trend
                    recent_scores = [i.ml_sentiment_score for i in recent_interactions if i.ml_sentiment_score]
                    if len(recent_scores) >= 3:
                        if recent_scores[0] < recent_scores[-1] - 0.3:
                            insights["sentiment_trend"] = "declining"
                        elif recent_scores[0] > recent_scores[-1] + 0.3:
                            insights["sentiment_trend"] = "improving"
                    
                    # Check for escalation risk
                    negative_count = len([s for s in recent_scores if s < -0.3])
                    if negative_count >= 2:
                        insights["escalation_risk"] = "high"
                        insights["intervention_needed"] = True
                    elif negative_count >= 1 and sentiment_score < -0.5:
                        insights["escalation_risk"] = "medium"
            
            # Check current emotion patterns
            primary_emotion = emotions.get("primary", "neutral")
            if primary_emotion in ["angry", "frustrated", "disappointed"]:
                insights["emotion_pattern"] = "negative"
                if sentiment_score < -0.6:
                    insights["intervention_needed"] = True
            elif primary_emotion == "urgent":
                insights["escalation_risk"] = "medium"
                insights["intervention_needed"] = True
        
        except Exception as e:
            frappe.log_error(f"Contextual Insights Error: {str(e)}")
        
        return insights
    
    def _generate_sentiment_recommendations(self, sentiment_score, emotions, insights):
        """Generate recommendations based on sentiment analysis"""
        recommendations = []
        
        # Sentiment-based recommendations
        if sentiment_score < -0.6:
            recommendations.append({
                "type": "immediate_attention",
                "priority": "high",
                "action": "Escalate to human agent immediately",
                "reason": "Very negative sentiment detected"
            })
        elif sentiment_score < -0.3:
            recommendations.append({
                "type": "careful_handling",
                "priority": "medium",
                "action": "Use empathetic language and offer additional assistance",
                "reason": "Negative sentiment detected"
            })
        elif sentiment_score > 0.6:
            recommendations.append({
                "type": "positive_reinforcement",
                "priority": "low",
                "action": "Acknowledge positive feedback and offer additional services",
                "reason": "Very positive sentiment detected"
            })
        
        # Emotion-based recommendations
        primary_emotion = emotions.get("primary", "neutral")
        if primary_emotion == "frustrated":
            recommendations.append({
                "type": "frustration_handling",
                "priority": "high",
                "action": "Acknowledge frustration and provide clear, step-by-step guidance",
                "reason": "User frustration detected"
            })
        elif primary_emotion == "confused":
            recommendations.append({
                "type": "clarity_improvement",
                "priority": "medium",
                "action": "Provide clearer explanations and offer multiple communication channels",
                "reason": "User confusion detected"
            })
        elif primary_emotion == "urgent":
            recommendations.append({
                "type": "urgency_response",
                "priority": "high",
                "action": "Prioritize response and provide immediate assistance options",
                "reason": "Urgency detected in user communication"
            })
        
        # Contextual recommendations
        if insights.get("intervention_needed"):
            recommendations.append({
                "type": "intervention",
                "priority": "high",
                "action": "Immediate human intervention required",
                "reason": "Pattern indicates high risk of escalation"
            })
        
        if insights.get("sentiment_trend") == "declining":
            recommendations.append({
                "type": "trend_reversal",
                "priority": "medium",
                "action": "Proactive outreach to address declining satisfaction",
                "reason": "Declining sentiment trend detected"
            })
        
        return recommendations
    
    def _load_emotion_patterns(self):
        """Load emotion detection patterns"""
        # This could be loaded from a configuration file or database
        return {
            "positive": ["happy", "pleased", "satisfied", "great", "excellent"],
            "negative": ["angry", "frustrated", "disappointed", "terrible", "awful"],
            "neutral": ["okay", "fine", "normal", "standard", "regular"]
        }

class SatisfactionMonitor:
    """Real-time satisfaction monitoring system"""
    
    def __init__(self):
        self.sentiment_engine = SentimentAnalysisEngine()
        self.alert_thresholds = {
            "individual_negative": -0.6,
            "trend_decline": -0.3,
            "escalation_risk": 0.7
        }
    
    def monitor_interaction(self, user_id, query_text, response_provided, interaction_id=None):
        """Monitor individual interaction for satisfaction"""
        try:
            # Analyze sentiment
            sentiment_analysis = self.sentiment_engine.analyze_sentiment(query_text, user_id)
            
            # Update interaction log with sentiment data
            if interaction_id:
                self._update_interaction_sentiment(interaction_id, sentiment_analysis)
            
            # Check for alerts
            alerts = self._check_satisfaction_alerts(user_id, sentiment_analysis)
            
            # Generate monitoring report
            monitoring_report = {
                "user_id": user_id,
                "interaction_id": interaction_id,
                "sentiment_analysis": sentiment_analysis,
                "alerts": alerts,
                "monitoring_timestamp": datetime.now().isoformat(),
                "requires_attention": len([a for a in alerts if a.get("priority") == "high"]) > 0
            }
            
            # Log monitoring data
            self._log_satisfaction_monitoring(monitoring_report)
            
            return monitoring_report
            
        except Exception as e:
            frappe.log_error(f"Satisfaction Monitoring Error: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to monitor satisfaction",
                "details": str(e)
            }
    
    def _update_interaction_sentiment(self, interaction_id, sentiment_analysis):
        """Update interaction log with sentiment data"""
        try:
            interaction = frappe.get_doc("User Interaction Log", interaction_id)
            interaction.ml_sentiment_score = sentiment_analysis.get("sentiment_score", 0.0)
            interaction.ml_emotion_detected = sentiment_analysis.get("primary_emotion", "neutral")
            interaction.save()
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Interaction Update Error: {str(e)}")
    
    def _check_satisfaction_alerts(self, user_id, sentiment_analysis):
        """Check for satisfaction alerts"""
        alerts = []
        
        sentiment_score = sentiment_analysis.get("sentiment_score", 0.0)
        primary_emotion = sentiment_analysis.get("primary_emotion", "neutral")
        insights = sentiment_analysis.get("contextual_insights", {})
        
        # Individual negative sentiment alert
        if sentiment_score <= self.alert_thresholds["individual_negative"]:
            alerts.append({
                "type": "negative_sentiment",
                "priority": "high",
                "message": f"Very negative sentiment detected (score: {sentiment_score:.2f})",
                "recommended_action": "Immediate escalation to human agent"
            })
        
        # Emotion-based alerts
        if primary_emotion in ["angry", "frustrated"]:
            alerts.append({
                "type": "negative_emotion",
                "priority": "high",
                "message": f"Negative emotion detected: {primary_emotion}",
                "recommended_action": "Use empathetic communication and offer immediate assistance"
            })
        
        # Trend-based alerts
        if insights.get("sentiment_trend") == "declining":
            alerts.append({
                "type": "declining_trend",
                "priority": "medium",
                "message": "Declining satisfaction trend detected",
                "recommended_action": "Proactive outreach to address concerns"
            })
        
        # Escalation risk alerts
        if insights.get("escalation_risk") == "high":
            alerts.append({
                "type": "escalation_risk",
                "priority": "high",
                "message": "High escalation risk detected",
                "recommended_action": "Prepare for potential escalation and ensure human backup"
            })
        
        return alerts
    
    def _log_satisfaction_monitoring(self, monitoring_report):
        """Log satisfaction monitoring data"""
        try:
            # This could be stored in a dedicated monitoring log
            frappe.log_error(f"Satisfaction Monitor: {json.dumps(monitoring_report)}", "Satisfaction Monitoring")
        except Exception as e:
            frappe.log_error(f"Monitoring Log Error: {str(e)}")

# API Endpoints for Sentiment Analysis

@frappe.whitelist(allow_guest=True)
def analyze_sentiment(text, user_id=None, context=None):
    """Analyze sentiment of text - main API method"""
    try:
        sentiment_engine = SentimentAnalysisEngine()

        # Parse context if it's a string
        if isinstance(context, str):
            context = json.loads(context) if context else None

        result = sentiment_engine.analyze_sentiment(text, user_id, context)

        return {
            "status": "success",
            "text": text,
            "user_id": user_id,
            "sentiment_analysis": result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to analyze sentiment",
            "details": str(e)
        }

@frappe.whitelist(allow_guest=True)
def analyze_text_sentiment(text, user_id=None, context=None):
    """Analyze sentiment of text - wrapper for backward compatibility"""
    return analyze_sentiment(text, user_id, context)

@frappe.whitelist()
def monitor_user_satisfaction(user_id, query_text, response_provided, interaction_id=None):
    """Monitor user satisfaction in real-time"""
    try:
        monitor = SatisfactionMonitor()
        
        monitoring_report = monitor.monitor_interaction(
            user_id, query_text, response_provided, interaction_id
        )
        
        return {
            "status": "success",
            "monitoring_report": monitoring_report,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to monitor satisfaction",
            "details": str(e)
        }

@frappe.whitelist()
def get_satisfaction_dashboard():
    """Get satisfaction monitoring dashboard data"""
    try:
        # Get recent interactions with sentiment data
        recent_interactions = frappe.get_all("User Interaction Log",
            filters={"timestamp": [">", (datetime.now() - timedelta(days=7)).isoformat()]},
            fields=["ml_sentiment_score", "ml_emotion_detected", "satisfaction_rating", "timestamp", "user_id"]
        )
        
        # Calculate dashboard metrics
        total_interactions = len(recent_interactions)
        sentiment_scores = [i.ml_sentiment_score for i in recent_interactions if i.ml_sentiment_score is not None]
        
        # Calculate average sentiment safely without numpy
        average_sentiment = 0.0
        if sentiment_scores:
            try:
                average_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            except:
                average_sentiment = 0.0

        dashboard_data = {
            "total_interactions": total_interactions,
            "average_sentiment": round(average_sentiment, 3),
            "sentiment_distribution": calculate_sentiment_distribution(sentiment_scores),
            "emotion_distribution": calculate_emotion_distribution(recent_interactions),
            "satisfaction_trend": calculate_satisfaction_trend(recent_interactions),
            "alerts_summary": get_recent_alerts(),
            "top_negative_users": get_users_needing_attention(recent_interactions),
            "period": "last_7_days",
            "data_quality": {
                "total_records": total_interactions,
                "records_with_sentiment": len(sentiment_scores),
                "sentiment_coverage": round((len(sentiment_scores) / total_interactions * 100), 1) if total_interactions > 0 else 0
            }
        }
        
        return {
            "status": "success",
            "dashboard_data": dashboard_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to generate satisfaction dashboard",
            "details": str(e)
        }

def calculate_sentiment_distribution(sentiment_scores):
    """Calculate distribution of sentiment scores"""
    if not sentiment_scores:
        return {"very_positive": 0, "positive": 0, "neutral": 0, "negative": 0, "very_negative": 0}
    
    distribution = {"very_positive": 0, "positive": 0, "neutral": 0, "negative": 0, "very_negative": 0}
    
    for score in sentiment_scores:
        if score >= 0.8:
            distribution["very_positive"] += 1
        elif score >= 0.4:
            distribution["positive"] += 1
        elif score >= -0.2:
            distribution["neutral"] += 1
        elif score >= -0.6:
            distribution["negative"] += 1
        else:
            distribution["very_negative"] += 1
    
    return distribution

def calculate_emotion_distribution(interactions):
    """Calculate distribution of detected emotions"""
    emotions = [i.ml_emotion_detected for i in interactions if i.ml_emotion_detected]
    
    emotion_counts = defaultdict(int)
    for emotion in emotions:
        emotion_counts[emotion] += 1
    
    return dict(emotion_counts)

def calculate_satisfaction_trend(interactions):
    """Calculate satisfaction trend over time"""
    # Group by day and calculate average sentiment
    daily_sentiment = defaultdict(list)
    
    for interaction in interactions:
        if interaction.ml_sentiment_score is not None:
            date = frappe.utils.get_datetime(interaction.timestamp).date()
            daily_sentiment[date].append(interaction.ml_sentiment_score)
    
    trend_data = []
    for date, scores in sorted(daily_sentiment.items()):
        # Calculate average without numpy
        avg_score = sum(scores) / len(scores) if scores else 0.0
        trend_data.append({
            "date": date.isoformat(),
            "average_sentiment": round(avg_score, 3),
            "interaction_count": len(scores)
        })
    
    return trend_data

def get_recent_alerts():
    """Get summary of recent satisfaction alerts"""
    # This would query a dedicated alerts log
    # For now, return placeholder data
    return {
        "high_priority": 2,
        "medium_priority": 5,
        "low_priority": 8,
        "total": 15
    }

def get_users_needing_attention(interactions):
    """Get users who need attention based on sentiment"""
    user_sentiment = defaultdict(list)
    
    for interaction in interactions:
        if interaction.ml_sentiment_score is not None:
            user_sentiment[interaction.user_id].append(interaction.ml_sentiment_score)
    
    users_needing_attention = []
    for user_id, scores in user_sentiment.items():
        # Calculate average without numpy
        avg_sentiment = sum(scores) / len(scores) if scores else 0.0
        if avg_sentiment < -0.3 or len([s for s in scores if s < -0.5]) >= 2:
            users_needing_attention.append({
                "user_id": user_id,
                "average_sentiment": round(avg_sentiment, 3),
                "negative_interactions": len([s for s in scores if s < -0.3]),
                "total_interactions": len(scores)
            })
    
    # Sort by severity (lowest sentiment first)
    users_needing_attention.sort(key=lambda x: x["average_sentiment"])
    
    return users_needing_attention[:10]  # Top 10 users needing attention
