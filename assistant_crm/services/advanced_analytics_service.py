import frappe
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import warnings
warnings.filterwarnings('ignore')


class AdvancedAnalyticsService:
    """
    Advanced Analytics Service for WCFCB Assistant CRM
    Phase B: Enhanced BI dashboard capabilities with predictive modeling
    Compliance Target: 98/100 score
    """
    
    def __init__(self):
        self.config = self.get_analytics_configuration()
        self.predictive_models = self.initialize_predictive_models()
        
    def get_analytics_configuration(self) -> Dict[str, Any]:
        """Get advanced analytics configuration"""
        try:
            settings = frappe.get_single("Advanced Analytics Settings")
            return {
                "enabled": settings.get("enabled", 1),
                "predictive_modeling_enabled": settings.get("predictive_modeling_enabled", 1),
                "real_time_analytics": settings.get("real_time_analytics", 1),
                "data_retention_days": settings.get("data_retention_days", 365),
                "ml_model_retrain_interval": settings.get("ml_model_retrain_interval", 7),
                "anomaly_detection_enabled": settings.get("anomaly_detection_enabled", 1),
                "automated_insights_enabled": settings.get("automated_insights_enabled", 1),
                "dashboard_refresh_interval": settings.get("dashboard_refresh_interval", 300)
            }
        except Exception:
            return {
                "enabled": 1,
                "predictive_modeling_enabled": 1,
                "real_time_analytics": 1,
                "data_retention_days": 365,
                "ml_model_retrain_interval": 7,
                "anomaly_detection_enabled": 1,
                "automated_insights_enabled": 1,
                "dashboard_refresh_interval": 300
            }
    
    def initialize_predictive_models(self) -> Dict[str, Any]:
        """Initialize machine learning models for predictive analytics"""
        return {
            "customer_satisfaction": None,
            "response_time": None,
            "resolution_rate": None,
            "workload_prediction": None,
            "churn_prediction": None
        }
    
    def generate_comprehensive_dashboard(self, date_range: Dict[str, str] = None, 
                                       agent_filter: str = None) -> Dict[str, Any]:
        """
        Generate comprehensive analytics dashboard with predictive insights
        
        Args:
            date_range: Optional date range filter
            agent_filter: Optional agent filter
            
        Returns:
            Dict containing comprehensive dashboard data
        """
        try:
            if not self.config["enabled"]:
                return {"success": False, "error": "Advanced analytics disabled"}
            
            # Set default date range if not provided
            if not date_range:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                date_range = {
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                }
            
            # Generate all dashboard components
            dashboard_data = {
                "overview_metrics": self.get_overview_metrics(date_range, agent_filter),
                "performance_trends": self.get_performance_trends(date_range, agent_filter),
                "channel_analytics": self.get_channel_analytics(date_range, agent_filter),
                "agent_performance": self.get_agent_performance_analytics(date_range, agent_filter),
                "customer_insights": self.get_customer_insights(date_range, agent_filter),
                "predictive_analytics": self.get_predictive_analytics(date_range, agent_filter),
                "real_time_metrics": self.get_real_time_metrics(),
                "automated_insights": self.get_automated_insights(date_range, agent_filter),
                "compliance_metrics": self.get_compliance_metrics(date_range, agent_filter),
                "operational_efficiency": self.get_operational_efficiency_metrics(date_range, agent_filter)
            }
            
            # Add metadata
            dashboard_data["metadata"] = {
                "generated_at": datetime.now().isoformat(),
                "date_range": date_range,
                "agent_filter": agent_filter,
                "data_freshness": self.get_data_freshness(),
                "dashboard_version": "2.0"
            }
            
            return {
                "success": True,
                "dashboard": dashboard_data
            }
            
        except Exception as e:
            frappe.log_error(f"Error generating comprehensive dashboard: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_overview_metrics(self, date_range: Dict[str, str], agent_filter: str = None) -> Dict[str, Any]:
        """Get high-level overview metrics"""
        try:
            # Build query conditions
            conditions = self.build_query_conditions(date_range, agent_filter)
            
            # Total conversations
            total_conversations = frappe.db.sql(f"""
                SELECT COUNT(*) as count
                FROM `tabOmnichannel Conversation`
                WHERE {conditions}
            """, as_dict=True)[0]["count"]
            
            # Resolution metrics
            resolution_metrics = frappe.db.sql(f"""
                SELECT 
                    COUNT(CASE WHEN conversation_status = 'Closed' THEN 1 END) as resolved,
                    COUNT(CASE WHEN conversation_status = 'Open' THEN 1 END) as open,
                    AVG(CASE WHEN end_time IS NOT NULL THEN 
                        TIMESTAMPDIFF(MINUTE, start_time, end_time) END) as avg_resolution_time
                FROM `tabOmnichannel Conversation`
                WHERE {conditions}
            """, as_dict=True)[0]
            
            # Response time metrics
            response_metrics = frappe.db.sql(f"""
                SELECT 
                    AVG(TIMESTAMPDIFF(MINUTE, oc.start_time, om.timestamp)) as avg_first_response_time,
                    COUNT(om.name) as total_messages
                FROM `tabOmnichannel Conversation` oc
                LEFT JOIN `tabOmnichannel Message` om ON oc.name = om.conversation_id
                WHERE {conditions} AND om.is_inbound = 0
                GROUP BY oc.name
            """, as_dict=True)
            
            avg_first_response = np.mean([r["avg_first_response_time"] for r in response_metrics if r["avg_first_response_time"]])
            
            # Customer satisfaction (if available)
            satisfaction_score = self.calculate_customer_satisfaction(date_range, agent_filter)
            
            return {
                "total_conversations": total_conversations,
                "resolved_conversations": resolution_metrics["resolved"],
                "open_conversations": resolution_metrics["open"],
                "resolution_rate": (resolution_metrics["resolved"] / max(1, total_conversations)) * 100,
                "avg_resolution_time_minutes": resolution_metrics["avg_resolution_time"] or 0,
                "avg_first_response_time_minutes": avg_first_response or 0,
                "customer_satisfaction_score": satisfaction_score,
                "total_messages": sum(r["total_messages"] for r in response_metrics)
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting overview metrics: {str(e)}")
            return {}
    
    def get_performance_trends(self, date_range: Dict[str, str], agent_filter: str = None) -> Dict[str, Any]:
        """Get performance trends over time"""
        try:
            conditions = self.build_query_conditions(date_range, agent_filter)
            
            # Daily conversation trends
            daily_trends = frappe.db.sql(f"""
                SELECT 
                    DATE(start_time) as date,
                    COUNT(*) as conversations,
                    COUNT(CASE WHEN conversation_status = 'Closed' THEN 1 END) as resolved,
                    AVG(CASE WHEN end_time IS NOT NULL THEN 
                        TIMESTAMPDIFF(MINUTE, start_time, end_time) END) as avg_resolution_time
                FROM `tabOmnichannel Conversation`
                WHERE {conditions}
                GROUP BY DATE(start_time)
                ORDER BY date
            """, as_dict=True)
            
            # Channel distribution trends
            channel_trends = frappe.db.sql(f"""
                SELECT 
                    DATE(start_time) as date,
                    channel_type,
                    COUNT(*) as count
                FROM `tabOmnichannel Conversation`
                WHERE {conditions}
                GROUP BY DATE(start_time), channel_type
                ORDER BY date, channel_type
            """, as_dict=True)
            
            # Agent workload trends
            agent_trends = frappe.db.sql(f"""
                SELECT 
                    DATE(oc.start_time) as date,
                    oc.assigned_agent,
                    COUNT(*) as conversations,
                    AVG(oc.message_count) as avg_messages_per_conversation
                FROM `tabOmnichannel Conversation` oc
                WHERE {conditions} AND oc.assigned_agent IS NOT NULL
                GROUP BY DATE(oc.start_time), oc.assigned_agent
                ORDER BY date, oc.assigned_agent
            """, as_dict=True)
            
            return {
                "daily_trends": daily_trends,
                "channel_trends": self.format_channel_trends(channel_trends),
                "agent_workload_trends": agent_trends,
                "trend_analysis": self.analyze_trends(daily_trends)
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting performance trends: {str(e)}")
            return {}
    
    def get_channel_analytics(self, date_range: Dict[str, str], agent_filter: str = None) -> Dict[str, Any]:
        """Get detailed channel performance analytics"""
        try:
            conditions = self.build_query_conditions(date_range, agent_filter)
            
            # Channel performance metrics
            channel_metrics = frappe.db.sql(f"""
                SELECT 
                    channel_type,
                    COUNT(*) as total_conversations,
                    COUNT(CASE WHEN conversation_status = 'Closed' THEN 1 END) as resolved,
                    AVG(message_count) as avg_messages,
                    AVG(CASE WHEN end_time IS NOT NULL THEN 
                        TIMESTAMPDIFF(MINUTE, start_time, end_time) END) as avg_resolution_time,
                    AVG(TIMESTAMPDIFF(MINUTE, start_time, last_message_time)) as avg_conversation_duration
                FROM `tabOmnichannel Conversation`
                WHERE {conditions}
                GROUP BY channel_type
                ORDER BY total_conversations DESC
            """, as_dict=True)
            
            # Channel satisfaction scores
            for channel in channel_metrics:
                channel["satisfaction_score"] = self.calculate_channel_satisfaction(
                    channel["channel_type"], date_range, agent_filter
                )
                channel["resolution_rate"] = (channel["resolved"] / max(1, channel["total_conversations"])) * 100
            
            # Channel growth analysis
            channel_growth = self.analyze_channel_growth(date_range, agent_filter)
            
            return {
                "channel_metrics": channel_metrics,
                "channel_growth": channel_growth,
                "channel_recommendations": self.generate_channel_recommendations(channel_metrics)
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting channel analytics: {str(e)}")
            return {}
    
    def get_agent_performance_analytics(self, date_range: Dict[str, str], agent_filter: str = None) -> Dict[str, Any]:
        """Get detailed agent performance analytics"""
        try:
            conditions = self.build_query_conditions(date_range, agent_filter)
            
            # Agent performance metrics
            agent_metrics = frappe.db.sql(f"""
                SELECT 
                    oc.assigned_agent,
                    ap.full_name as agent_name,
                    COUNT(oc.name) as total_conversations,
                    COUNT(CASE WHEN oc.conversation_status = 'Closed' THEN 1 END) as resolved,
                    AVG(oc.message_count) as avg_messages,
                    AVG(CASE WHEN oc.end_time IS NOT NULL THEN 
                        TIMESTAMPDIFF(MINUTE, oc.start_time, oc.end_time) END) as avg_resolution_time,
                    SUM(oc.message_count) as total_messages_handled
                FROM `tabOmnichannel Conversation` oc
                LEFT JOIN `tabAgent Profile` ap ON oc.assigned_agent = ap.user
                WHERE {conditions} AND oc.assigned_agent IS NOT NULL
                GROUP BY oc.assigned_agent, ap.full_name
                ORDER BY total_conversations DESC
            """, as_dict=True)
            
            # Calculate additional metrics for each agent
            for agent in agent_metrics:
                agent["resolution_rate"] = (agent["resolved"] / max(1, agent["total_conversations"])) * 100
                agent["efficiency_score"] = self.calculate_agent_efficiency(agent)
                agent["satisfaction_score"] = self.calculate_agent_satisfaction(
                    agent["assigned_agent"], date_range
                )
            
            # Agent ranking and performance distribution
            agent_ranking = self.rank_agents(agent_metrics)
            performance_distribution = self.analyze_performance_distribution(agent_metrics)
            
            return {
                "agent_metrics": agent_metrics,
                "agent_ranking": agent_ranking,
                "performance_distribution": performance_distribution,
                "top_performers": agent_metrics[:5],
                "improvement_opportunities": self.identify_improvement_opportunities(agent_metrics)
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting agent performance analytics: {str(e)}")
            return {}
    
    def get_predictive_analytics(self, date_range: Dict[str, str], agent_filter: str = None) -> Dict[str, Any]:
        """Get predictive analytics and forecasts"""
        try:
            if not self.config["predictive_modeling_enabled"]:
                return {"enabled": False, "message": "Predictive modeling disabled"}
            
            # Prepare historical data for modeling
            historical_data = self.prepare_historical_data(date_range, agent_filter)
            
            if len(historical_data) < 30:  # Need sufficient data for predictions
                return {
                    "enabled": True,
                    "insufficient_data": True,
                    "message": "Insufficient historical data for reliable predictions"
                }
            
            # Generate predictions
            predictions = {
                "conversation_volume_forecast": self.predict_conversation_volume(historical_data),
                "resolution_time_forecast": self.predict_resolution_times(historical_data),
                "agent_workload_forecast": self.predict_agent_workload(historical_data),
                "channel_demand_forecast": self.predict_channel_demand(historical_data),
                "customer_satisfaction_forecast": self.predict_customer_satisfaction(historical_data)
            }
            
            # Anomaly detection
            anomalies = self.detect_anomalies(historical_data) if self.config["anomaly_detection_enabled"] else []
            
            return {
                "enabled": True,
                "predictions": predictions,
                "anomalies": anomalies,
                "model_accuracy": self.get_model_accuracy_metrics(),
                "confidence_intervals": self.calculate_confidence_intervals(predictions)
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting predictive analytics: {str(e)}")
            return {"enabled": True, "error": str(e)}
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time operational metrics"""
        try:
            if not self.config["real_time_analytics"]:
                return {"enabled": False}
            
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Current active conversations
            active_conversations = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabOmnichannel Conversation`
                WHERE conversation_status = 'Open'
            """, as_dict=True)[0]["count"]
            
            # Today's metrics
            today_metrics = frappe.db.sql(f"""
                SELECT 
                    COUNT(*) as conversations_today,
                    COUNT(CASE WHEN conversation_status = 'Closed' THEN 1 END) as resolved_today,
                    AVG(CASE WHEN end_time IS NOT NULL THEN 
                        TIMESTAMPDIFF(MINUTE, start_time, end_time) END) as avg_resolution_time_today
                FROM `tabOmnichannel Conversation`
                WHERE start_time >= '{today_start}'
            """, as_dict=True)[0]
            
            # Agent availability
            agent_availability = self.get_agent_availability()
            
            # Queue metrics
            queue_metrics = self.get_queue_metrics()
            
            return {
                "enabled": True,
                "timestamp": now.isoformat(),
                "active_conversations": active_conversations,
                "today_metrics": today_metrics,
                "agent_availability": agent_availability,
                "queue_metrics": queue_metrics,
                "system_health": self.get_system_health_status()
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting real-time metrics: {str(e)}")
            return {"enabled": True, "error": str(e)}
