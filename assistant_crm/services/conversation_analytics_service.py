# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now, get_datetime, add_to_date, date_diff
from typing import Dict, List, Optional, Any, Tuple
import json
import logging
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger(__name__)

class ConversationAnalyticsManager:
    """
    Manages conversation analytics, insights, and performance tracking for the assistant_crm system.
    Provides comprehensive analytics for user satisfaction, conversation success, and improvement opportunities.
    """
    
    def __init__(self):
        """Initialize conversation analytics manager."""
        self.analytics_cache = {}
        self.insight_generators = {
            'user_satisfaction': self._analyze_user_satisfaction,
            'conversation_success': self._analyze_conversation_success,
            'response_quality': self._analyze_response_quality,
            'escalation_patterns': self._analyze_escalation_patterns,
            'user_journey': self._analyze_user_journey,
            'performance_trends': self._analyze_performance_trends
        }
    
    def generate_comprehensive_analytics(self, date_range: Dict = None, 
                                       filters: Dict = None) -> Dict:
        """
        Generate comprehensive conversation analytics.
        
        Args:
            date_range (Dict): Date range for analysis {'start': date, 'end': date}
            filters (Dict): Additional filters (user_role, department, etc.)
            
        Returns:
            Dict: Comprehensive analytics report
        """
        try:
            # Set default date range if not provided
            if not date_range:
                end_date = get_datetime(now())
                start_date = end_date - timedelta(days=30)
                date_range = {'start': start_date, 'end': end_date}
            
            # Get conversation data
            conversation_data = self._get_conversation_data(date_range, filters)
            
            if not conversation_data:
                return {
                    "status": "no_data",
                    "message": "No conversation data found for the specified period",
                    "date_range": date_range
                }
            
            # Generate analytics sections
            analytics_report = {
                "report_metadata": {
                    "generated_at": now(),
                    "date_range": date_range,
                    "filters": filters or {},
                    "total_conversations": len(conversation_data['sessions']),
                    "total_turns": len(conversation_data['turns'])
                },
                "executive_summary": self._generate_executive_summary(conversation_data),
                "user_satisfaction_analysis": self._analyze_user_satisfaction(conversation_data),
                "conversation_success_analysis": self._analyze_conversation_success(conversation_data),
                "response_quality_analysis": self._analyze_response_quality(conversation_data),
                "escalation_analysis": self._analyze_escalation_patterns(conversation_data),
                "user_journey_analysis": self._analyze_user_journey(conversation_data),
                "performance_trends": self._analyze_performance_trends(conversation_data),
                "improvement_opportunities": self._identify_improvement_opportunities(conversation_data),
                "recommendations": self._generate_recommendations(conversation_data)
            }
            
            return analytics_report
            
        except Exception as e:
            logger.error(f"Error generating comprehensive analytics: {str(e)}")
            return {
                "status": "error",
                "message": "Failed to generate analytics",
                "details": str(e)
            }
    
    def _get_conversation_data(self, date_range: Dict, filters: Dict = None) -> Dict:
        """Get conversation data for analysis."""
        try:
            # Build filters
            session_filters = {
                "start_time": ["between", [date_range['start'], date_range['end']]]
            }
            
            turn_filters = {
                "timestamp": ["between", [date_range['start'], date_range['end']]]
            }
            
            if filters:
                if filters.get('user_role'):
                    session_filters['user_role'] = filters['user_role']
                if filters.get('department'):
                    # Add department filter logic if needed
                    pass
            
            # Get conversation sessions
            sessions = frappe.get_all("Conversation Session",
                filters=session_filters,
                fields=["*"],
                order_by="start_time desc"
            )
            
            # Get conversation turns
            turns = frappe.get_all("Conversation Turn",
                filters=turn_filters,
                fields=["*"],
                order_by="timestamp desc"
            )
            
            # Get escalations
            escalation_filters = {
                "escalation_date": ["between", [date_range['start'], date_range['end']]]
            }
            escalations = frappe.get_all("Escalation Workflow",
                filters=escalation_filters,
                fields=["*"],
                order_by="escalation_date desc"
            )
            
            return {
                "sessions": sessions,
                "turns": turns,
                "escalations": escalations,
                "date_range": date_range
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation data: {str(e)}")
            return {"sessions": [], "turns": [], "escalations": []}
    
    def _generate_executive_summary(self, data: Dict) -> Dict:
        """Generate executive summary of key metrics."""
        sessions = data['sessions']
        turns = data['turns']
        escalations = data['escalations']
        
        # Calculate key metrics
        total_conversations = len(sessions)
        total_turns = len(turns)
        total_escalations = len(escalations)
        
        # Average turns per conversation
        avg_turns_per_conversation = total_turns / total_conversations if total_conversations > 0 else 0
        
        # Escalation rate
        escalation_rate = (total_escalations / total_conversations) * 100 if total_conversations > 0 else 0
        
        # Completed conversations
        completed_sessions = [s for s in sessions if s.status == 'completed']
        completion_rate = (len(completed_sessions) / total_conversations) * 100 if total_conversations > 0 else 0
        
        # Average satisfaction (if available)
        satisfaction_scores = [s.satisfaction_score for s in sessions if s.satisfaction_score]
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0
        
        # Response quality scores
        quality_scores = [t.response_quality_score for t in turns if t.response_quality_score]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return {
            "total_conversations": total_conversations,
            "total_turns": total_turns,
            "avg_turns_per_conversation": round(avg_turns_per_conversation, 2),
            "escalation_rate": round(escalation_rate, 2),
            "completion_rate": round(completion_rate, 2),
            "avg_satisfaction_score": round(avg_satisfaction, 2),
            "avg_response_quality": round(avg_quality, 2),
            "total_escalations": total_escalations
        }
    
    def _analyze_user_satisfaction(self, data: Dict) -> Dict:
        """Analyze user satisfaction patterns."""
        sessions = data['sessions']
        turns = data['turns']
        
        # Satisfaction by user role
        satisfaction_by_role = {}
        for session in sessions:
            if session.satisfaction_score and session.user_role:
                role = session.user_role
                if role not in satisfaction_by_role:
                    satisfaction_by_role[role] = []
                satisfaction_by_role[role].append(session.satisfaction_score)
        
        # Calculate averages
        role_satisfaction_avg = {}
        for role, scores in satisfaction_by_role.items():
            role_satisfaction_avg[role] = sum(scores) / len(scores)
        
        # Satisfaction trends over time
        satisfaction_trends = self._calculate_satisfaction_trends(sessions)
        
        # Turn-level satisfaction analysis
        turn_satisfaction = {}
        for turn in turns:
            if turn.user_satisfaction:
                satisfaction = turn.user_satisfaction
                if satisfaction not in turn_satisfaction:
                    turn_satisfaction[satisfaction] = 0
                turn_satisfaction[satisfaction] += 1
        
        return {
            "satisfaction_by_role": role_satisfaction_avg,
            "satisfaction_trends": satisfaction_trends,
            "turn_satisfaction_distribution": turn_satisfaction,
            "overall_satisfaction_score": sum(role_satisfaction_avg.values()) / len(role_satisfaction_avg) if role_satisfaction_avg else 0
        }
    
    def _analyze_conversation_success(self, data: Dict) -> Dict:
        """Analyze conversation success patterns."""
        sessions = data['sessions']
        turns = data['turns']
        
        # Success rate by completion status
        status_counts = {}
        for session in sessions:
            status = session.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Success rate by user role
        success_by_role = {}
        for session in sessions:
            if session.user_role:
                role = session.user_role
                if role not in success_by_role:
                    success_by_role[role] = {"total": 0, "successful": 0}
                success_by_role[role]["total"] += 1
                if session.status == "completed":
                    success_by_role[role]["successful"] += 1
        
        # Calculate success rates
        role_success_rates = {}
        for role, data in success_by_role.items():
            role_success_rates[role] = (data["successful"] / data["total"]) * 100 if data["total"] > 0 else 0
        
        # Conversation length vs success correlation
        length_success_correlation = self._analyze_length_success_correlation(sessions)
        
        return {
            "status_distribution": status_counts,
            "success_rate_by_role": role_success_rates,
            "length_success_correlation": length_success_correlation,
            "overall_success_rate": (status_counts.get("completed", 0) / len(sessions)) * 100 if sessions else 0
        }
    
    def _analyze_response_quality(self, data: Dict) -> Dict:
        """Analyze response quality patterns."""
        turns = data['turns']
        
        # Quality score distribution
        quality_distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        quality_scores = []
        
        for turn in turns:
            if turn.response_quality_score:
                score = turn.response_quality_score
                quality_scores.append(score)
                
                # Convert to grade
                if score >= 0.9:
                    grade = "A"
                elif score >= 0.8:
                    grade = "A"
                elif score >= 0.7:
                    grade = "B"
                elif score >= 0.6:
                    grade = "C"
                elif score >= 0.5:
                    grade = "D"
                else:
                    grade = "F"
                
                quality_distribution[grade] += 1
        
        # Quality by intent
        quality_by_intent = {}
        for turn in turns:
            if turn.intent and turn.response_quality_score:
                intent = turn.intent
                if intent not in quality_by_intent:
                    quality_by_intent[intent] = []
                quality_by_intent[intent].append(turn.response_quality_score)
        
        # Calculate averages
        intent_quality_avg = {}
        for intent, scores in quality_by_intent.items():
            intent_quality_avg[intent] = sum(scores) / len(scores)
        
        return {
            "quality_distribution": quality_distribution,
            "quality_by_intent": intent_quality_avg,
            "average_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            "quality_trends": self._calculate_quality_trends(turns)
        }
    
    def _analyze_escalation_patterns(self, data: Dict) -> Dict:
        """Analyze escalation patterns and triggers."""
        escalations = data['escalations']
        sessions = data['sessions']
        
        # Escalation reasons
        escalation_reasons = {}
        for escalation in escalations:
            reason = escalation.escalation_reason
            escalation_reasons[reason] = escalation_reasons.get(reason, 0) + 1
        
        # Escalation by user role
        escalation_by_role = {}
        for escalation in escalations:
            # Find corresponding session
            session = next((s for s in sessions if s.session_id == escalation.session_id), None)
            if session and session.user_role:
                role = session.user_role
                escalation_by_role[role] = escalation_by_role.get(role, 0) + 1
        
        # Escalation resolution analysis
        resolution_analysis = self._analyze_escalation_resolution(escalations)
        
        return {
            "escalation_reasons": escalation_reasons,
            "escalation_by_role": escalation_by_role,
            "resolution_analysis": resolution_analysis,
            "escalation_rate": (len(escalations) / len(sessions)) * 100 if sessions else 0
        }

    def _analyze_user_journey(self, data: Dict) -> Dict:
        """Analyze user journey patterns and flow."""
        sessions = data['sessions']
        turns = data['turns']

        # Journey by user role
        journey_by_role = {}
        for session in sessions:
            if session.user_role:
                role = session.user_role
                if role not in journey_by_role:
                    journey_by_role[role] = {
                        "avg_turns": 0,
                        "avg_duration": 0,
                        "common_intents": {},
                        "success_rate": 0
                    }

        # Calculate journey metrics for each role
        for role in journey_by_role.keys():
            role_sessions = [s for s in sessions if s.user_role == role]
            role_turns = [t for t in turns if any(s.session_id == t.session_id for s in role_sessions)]

            # Average turns
            total_turns = sum(s.total_turns for s in role_sessions if s.total_turns)
            journey_by_role[role]["avg_turns"] = total_turns / len(role_sessions) if role_sessions else 0

            # Average duration (if available)
            durations = []
            for session in role_sessions:
                if session.end_time and session.start_time:
                    start = get_datetime(session.start_time)
                    end = get_datetime(session.end_time)
                    duration = (end - start).total_seconds() / 60  # minutes
                    durations.append(duration)
            journey_by_role[role]["avg_duration"] = sum(durations) / len(durations) if durations else 0

            # Common intents
            intent_counts = {}
            for turn in role_turns:
                if turn.intent:
                    intent_counts[turn.intent] = intent_counts.get(turn.intent, 0) + 1
            journey_by_role[role]["common_intents"] = intent_counts

            # Success rate
            successful = len([s for s in role_sessions if s.status == "completed"])
            journey_by_role[role]["success_rate"] = (successful / len(role_sessions)) * 100 if role_sessions else 0

        # Flow analysis
        flow_analysis = self._analyze_conversation_flow(turns)

        return {
            "journey_by_role": journey_by_role,
            "flow_analysis": flow_analysis,
            "common_user_paths": self._identify_common_paths(turns)
        }

    def _analyze_performance_trends(self, data: Dict) -> Dict:
        """Analyze performance trends over time."""
        sessions = data['sessions']
        turns = data['turns']

        # Group data by time periods
        daily_metrics = {}

        for session in sessions:
            date_key = get_datetime(session.start_time).strftime('%Y-%m-%d')
            if date_key not in daily_metrics:
                daily_metrics[date_key] = {
                    "conversations": 0,
                    "turns": 0,
                    "escalations": 0,
                    "satisfaction_scores": [],
                    "quality_scores": []
                }
            daily_metrics[date_key]["conversations"] += 1
            if session.satisfaction_score:
                daily_metrics[date_key]["satisfaction_scores"].append(session.satisfaction_score)

        for turn in turns:
            date_key = get_datetime(turn.timestamp).strftime('%Y-%m-%d')
            if date_key in daily_metrics:
                daily_metrics[date_key]["turns"] += 1
                if turn.response_quality_score:
                    daily_metrics[date_key]["quality_scores"].append(turn.response_quality_score)

        # Calculate daily averages
        trend_data = {}
        for date, metrics in daily_metrics.items():
            trend_data[date] = {
                "conversations": metrics["conversations"],
                "avg_satisfaction": sum(metrics["satisfaction_scores"]) / len(metrics["satisfaction_scores"]) if metrics["satisfaction_scores"] else 0,
                "avg_quality": sum(metrics["quality_scores"]) / len(metrics["quality_scores"]) if metrics["quality_scores"] else 0,
                "turns_per_conversation": metrics["turns"] / metrics["conversations"] if metrics["conversations"] > 0 else 0
            }

        return {
            "daily_trends": trend_data,
            "trend_analysis": self._calculate_trend_direction(trend_data)
        }

    def _identify_improvement_opportunities(self, data: Dict) -> Dict:
        """Identify specific improvement opportunities."""
        sessions = data['sessions']
        turns = data['turns']
        escalations = data['escalations']

        opportunities = []

        # Low satisfaction areas
        low_satisfaction_sessions = [s for s in sessions if s.satisfaction_score and s.satisfaction_score < 3]
        if len(low_satisfaction_sessions) > len(sessions) * 0.2:  # More than 20%
            opportunities.append({
                "area": "User Satisfaction",
                "issue": "High percentage of low satisfaction scores",
                "impact": "high",
                "recommendation": "Review response templates and empathy training"
            })

        # High escalation rate
        escalation_rate = (len(escalations) / len(sessions)) * 100 if sessions else 0
        if escalation_rate > 15:  # More than 15%
            opportunities.append({
                "area": "Escalation Management",
                "issue": f"High escalation rate ({escalation_rate:.1f}%)",
                "impact": "high",
                "recommendation": "Improve intent detection and response quality"
            })

        # Low quality responses
        low_quality_turns = [t for t in turns if t.response_quality_score and t.response_quality_score < 0.6]
        if len(low_quality_turns) > len(turns) * 0.3:  # More than 30%
            opportunities.append({
                "area": "Response Quality",
                "issue": "High percentage of low quality responses",
                "impact": "medium",
                "recommendation": "Optimize response templates and training data"
            })

        # Long conversation duration
        long_sessions = []
        for session in sessions:
            if session.total_turns and session.total_turns > 10:
                long_sessions.append(session)

        if len(long_sessions) > len(sessions) * 0.25:  # More than 25%
            opportunities.append({
                "area": "Conversation Efficiency",
                "issue": "Many conversations require excessive turns",
                "impact": "medium",
                "recommendation": "Improve first-response resolution rate"
            })

        return {
            "opportunities": opportunities,
            "priority_areas": self._prioritize_improvement_areas(opportunities)
        }

    def _generate_recommendations(self, data: Dict) -> Dict:
        """Generate actionable recommendations based on analytics."""
        sessions = data['sessions']
        turns = data['turns']
        escalations = data['escalations']

        recommendations = {
            "immediate_actions": [],
            "short_term_improvements": [],
            "long_term_strategies": []
        }

        # Calculate key metrics for recommendations
        avg_satisfaction = sum(s.satisfaction_score for s in sessions if s.satisfaction_score) / len([s for s in sessions if s.satisfaction_score]) if sessions else 0
        avg_quality = sum(t.response_quality_score for t in turns if t.response_quality_score) / len([t for t in turns if t.response_quality_score]) if turns else 0
        escalation_rate = (len(escalations) / len(sessions)) * 100 if sessions else 0

        # Immediate actions
        if avg_satisfaction < 3.5:
            recommendations["immediate_actions"].append("Review and update response templates for better user satisfaction")

        if escalation_rate > 20:
            recommendations["immediate_actions"].append("Implement emergency escalation review and process optimization")

        if avg_quality < 0.7:
            recommendations["immediate_actions"].append("Conduct response quality audit and template optimization")

        # Short-term improvements
        recommendations["short_term_improvements"].extend([
            "Implement A/B testing for response optimization",
            "Enhance intent detection accuracy through additional training",
            "Develop role-specific response personalization",
            "Create automated quality monitoring alerts"
        ])

        # Long-term strategies
        recommendations["long_term_strategies"].extend([
            "Implement machine learning for predictive escalation prevention",
            "Develop advanced sentiment analysis for emotional intelligence",
            "Create comprehensive user journey optimization",
            "Build predictive analytics for proactive support"
        ])

        return recommendations

    # Helper methods
    def _calculate_satisfaction_trends(self, sessions: List) -> Dict:
        """Calculate satisfaction trends over time."""
        # Group by week
        weekly_satisfaction = {}
        for session in sessions:
            if session.satisfaction_score:
                week_key = get_datetime(session.start_time).strftime('%Y-W%U')
                if week_key not in weekly_satisfaction:
                    weekly_satisfaction[week_key] = []
                weekly_satisfaction[week_key].append(session.satisfaction_score)

        # Calculate weekly averages
        trend_data = {}
        for week, scores in weekly_satisfaction.items():
            trend_data[week] = sum(scores) / len(scores)

        return trend_data

    def _analyze_length_success_correlation(self, sessions: List) -> Dict:
        """Analyze correlation between conversation length and success."""
        length_success = {"short": {"total": 0, "successful": 0},
                         "medium": {"total": 0, "successful": 0},
                         "long": {"total": 0, "successful": 0}}

        for session in sessions:
            if session.total_turns:
                if session.total_turns <= 3:
                    category = "short"
                elif session.total_turns <= 7:
                    category = "medium"
                else:
                    category = "long"

                length_success[category]["total"] += 1
                if session.status == "completed":
                    length_success[category]["successful"] += 1

        # Calculate success rates
        for category in length_success:
            total = length_success[category]["total"]
            successful = length_success[category]["successful"]
            length_success[category]["success_rate"] = (successful / total) * 100 if total > 0 else 0

        return length_success

    def _calculate_quality_trends(self, turns: List) -> Dict:
        """Calculate quality trends over time."""
        daily_quality = {}
        for turn in turns:
            if turn.response_quality_score:
                date_key = get_datetime(turn.timestamp).strftime('%Y-%m-%d')
                if date_key not in daily_quality:
                    daily_quality[date_key] = []
                daily_quality[date_key].append(turn.response_quality_score)

        # Calculate daily averages
        trend_data = {}
        for date, scores in daily_quality.items():
            trend_data[date] = sum(scores) / len(scores)

        return trend_data

    def _analyze_escalation_resolution(self, escalations: List) -> Dict:
        """Analyze escalation resolution patterns."""
        resolution_times = []
        resolution_satisfaction = []

        for escalation in escalations:
            if escalation.resolution_date and escalation.escalation_date:
                start = get_datetime(escalation.escalation_date)
                end = get_datetime(escalation.resolution_date)
                resolution_time = (end - start).total_seconds() / 3600  # hours
                resolution_times.append(resolution_time)

            if escalation.customer_satisfaction:
                satisfaction_map = {
                    "very_satisfied": 5,
                    "satisfied": 4,
                    "neutral": 3,
                    "dissatisfied": 2,
                    "very_dissatisfied": 1
                }
                score = satisfaction_map.get(escalation.customer_satisfaction, 3)
                resolution_satisfaction.append(score)

        return {
            "avg_resolution_time_hours": sum(resolution_times) / len(resolution_times) if resolution_times else 0,
            "avg_resolution_satisfaction": sum(resolution_satisfaction) / len(resolution_satisfaction) if resolution_satisfaction else 0,
            "total_resolved": len([e for e in escalations if e.status == "resolved"]),
            "resolution_rate": (len([e for e in escalations if e.status == "resolved"]) / len(escalations)) * 100 if escalations else 0
        }

    def _analyze_conversation_flow(self, turns: List) -> Dict:
        """Analyze conversation flow patterns."""
        flow_patterns = {}
        intent_sequences = []

        # Group turns by session
        session_turns = {}
        for turn in turns:
            session_id = turn.session_id
            if session_id not in session_turns:
                session_turns[session_id] = []
            session_turns[session_id].append(turn)

        # Analyze intent sequences
        for session_id, session_turns_list in session_turns.items():
            sorted_turns = sorted(session_turns_list, key=lambda x: x.turn_number)
            intents = [turn.intent for turn in sorted_turns if turn.intent]
            if len(intents) >= 2:
                intent_sequences.append(intents)

        # Find common patterns
        common_patterns = {}
        for sequence in intent_sequences:
            for i in range(len(sequence) - 1):
                pattern = f"{sequence[i]} -> {sequence[i+1]}"
                common_patterns[pattern] = common_patterns.get(pattern, 0) + 1

        return {
            "common_intent_transitions": common_patterns,
            "avg_intents_per_conversation": sum(len(seq) for seq in intent_sequences) / len(intent_sequences) if intent_sequences else 0
        }

    def _identify_common_paths(self, turns: List) -> List:
        """Identify common user conversation paths."""
        # This is a simplified implementation
        # In production, would use more sophisticated path analysis

        session_paths = {}
        for turn in turns:
            session_id = turn.session_id
            if session_id not in session_paths:
                session_paths[session_id] = []
            if turn.intent:
                session_paths[session_id].append(turn.intent)

        # Find most common paths
        path_counts = {}
        for path in session_paths.values():
            if len(path) >= 2:
                path_str = " -> ".join(path[:3])  # First 3 intents
                path_counts[path_str] = path_counts.get(path_str, 0) + 1

        # Return top 5 most common paths
        sorted_paths = sorted(path_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"path": path, "frequency": count} for path, count in sorted_paths[:5]]

    def _calculate_trend_direction(self, trend_data: Dict) -> Dict:
        """Calculate trend direction for key metrics."""
        if len(trend_data) < 2:
            return {"insufficient_data": True}

        dates = sorted(trend_data.keys())

        # Calculate trends for each metric
        trends = {}
        metrics = ["avg_satisfaction", "avg_quality", "turns_per_conversation"]

        for metric in metrics:
            values = [trend_data[date][metric] for date in dates if trend_data[date][metric] > 0]
            if len(values) >= 2:
                # Simple trend calculation
                early_avg = sum(values[:len(values)//2]) / (len(values)//2)
                late_avg = sum(values[len(values)//2:]) / (len(values) - len(values)//2)

                if late_avg > early_avg * 1.05:
                    trends[metric] = "improving"
                elif late_avg < early_avg * 0.95:
                    trends[metric] = "declining"
                else:
                    trends[metric] = "stable"
            else:
                trends[metric] = "insufficient_data"

        return trends

    def _prioritize_improvement_areas(self, opportunities: List) -> List:
        """Prioritize improvement areas by impact and effort."""
        # Sort by impact (high impact first)
        high_impact = [opp for opp in opportunities if opp["impact"] == "high"]
        medium_impact = [opp for opp in opportunities if opp["impact"] == "medium"]
        low_impact = [opp for opp in opportunities if opp["impact"] == "low"]

        return high_impact + medium_impact + low_impact


# Utility functions for integration

def get_conversation_analytics_manager() -> ConversationAnalyticsManager:
    """Get conversation analytics manager instance."""
    return ConversationAnalyticsManager()


def generate_analytics_report(date_range: Dict = None, filters: Dict = None) -> Dict:
    """
    Generate comprehensive analytics report.

    Args:
        date_range (Dict): Date range for analysis
        filters (Dict): Additional filters

    Returns:
        Dict: Analytics report
    """
    analytics_manager = get_conversation_analytics_manager()
    return analytics_manager.generate_comprehensive_analytics(date_range, filters)


def get_real_time_metrics() -> Dict:
    """Get real-time conversation metrics."""
    try:
        # Get today's data
        today = get_datetime(now()).date()
        date_range = {
            'start': datetime.combine(today, datetime.min.time()),
            'end': get_datetime(now())
        }

        analytics_manager = get_conversation_analytics_manager()
        data = analytics_manager._get_conversation_data(date_range)

        return {
            "active_conversations": len([s for s in data['sessions'] if s.status == 'active']),
            "completed_today": len([s for s in data['sessions'] if s.status == 'completed']),
            "escalations_today": len(data['escalations']),
            "avg_response_quality_today": sum(t.response_quality_score for t in data['turns'] if t.response_quality_score) / len([t for t in data['turns'] if t.response_quality_score]) if data['turns'] else 0
        }

    except Exception as e:
        logger.error(f"Error getting real-time metrics: {str(e)}")
        return {"error": "Failed to get real-time metrics"}
