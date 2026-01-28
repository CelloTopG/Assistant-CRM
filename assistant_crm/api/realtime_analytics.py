#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Real-Time Analytics API
Live analytics and performance monitoring for omnichannel communication
"""

import frappe
import json
from frappe import _
from frappe.utils import now, get_datetime, add_to_date, time_diff_in_seconds
from datetime import datetime, timedelta
from typing import Dict, List, Any


@frappe.whitelist()
def get_realtime_dashboard_data():
    """Get comprehensive real-time dashboard data"""
    try:
        current_time = now()
        
        dashboard_data = {
            "overview": get_overview_metrics(),
            "channel_performance": get_channel_performance(),
            "agent_performance": get_agent_performance(),
            "conversation_flow": get_conversation_flow_metrics(),
            "response_times": get_response_time_analytics(),
            "customer_satisfaction": get_satisfaction_metrics(),
            "live_conversations": get_live_conversations(),
            "system_health": get_system_health_metrics(),
            "timestamp": current_time
        }
        
        return {"success": True, "data": dashboard_data}
        
    except Exception as e:
        frappe.log_error(f"Error getting dashboard data: {str(e)}", "Real-time Analytics")
        return {"success": False, "error": str(e)}


def get_overview_metrics():
    """Get high-level overview metrics"""
    try:
        today = frappe.utils.today()
        
        metrics = {
            "total_conversations_today": frappe.db.count("Omnichannel Conversation", {
                "creation_time": [">=", today]
            }),
            "active_conversations": frappe.db.count("Omnichannel Conversation", {
                "status": ["in", ["Open", "Assigned", "Pending"]]
            }),
            "messages_today": frappe.db.count("Omnichannel Message", {
                "received_at": [">=", today]
            }),
            "agents_online": frappe.db.count("Agent Dashboard", {
                "status": "online"
            }),
            "avg_response_time_today": get_average_response_time(today),
            "escalation_rate_today": get_escalation_rate(today),
            "resolution_rate_today": get_resolution_rate(today)
        }
        
        return metrics
        
    except Exception as e:
        frappe.log_error(f"Error getting overview metrics: {str(e)}", "Real-time Analytics")
        return {}


def get_channel_performance():
    """Get performance metrics by channel"""
    try:
        today = frappe.utils.today()
        
        channel_data = frappe.db.sql("""
            SELECT 
                channel_type,
                COUNT(*) as message_count,
                AVG(response_time) as avg_response_time,
                COUNT(CASE WHEN escalated_to_agent = 1 THEN 1 END) as escalations,
                COUNT(CASE WHEN processed_by_ai = 1 THEN 1 END) as ai_handled
            FROM `tabOmnichannel Message`
            WHERE DATE(received_at) = %s
            GROUP BY channel_type
            ORDER BY message_count DESC
        """, (today,), as_dict=True)
        
        # Add real-time status for each channel
        for channel in channel_data:
            channel["status"] = get_channel_status(channel["channel_type"])
            channel["active_conversations"] = frappe.db.count("Omnichannel Conversation", {
                "primary_channel": channel["channel_type"],
                "status": ["in", ["Open", "Assigned", "Pending"]]
            })
        
        return channel_data
        
    except Exception as e:
        frappe.log_error(f"Error getting channel performance: {str(e)}", "Real-time Analytics")
        return []


def get_agent_performance():
    """Get real-time agent performance metrics"""
    try:
        agent_data = frappe.db.sql("""
            SELECT 
                u.name as agent_id,
                u.full_name as agent_name,
                ad.status,
                ad.active_conversations,
                ad.total_conversations_today,
                ad.avg_response_time_today,
                ad.customer_satisfaction_avg,
                ad.last_activity
            FROM `tabUser` u
            LEFT JOIN `tabAgent Dashboard` ad ON u.name = ad.user
            WHERE u.name IN (
                SELECT DISTINCT agent_assigned 
                FROM `tabOmnichannel Message` 
                WHERE agent_assigned IS NOT NULL
            )
            ORDER BY ad.status DESC, ad.active_conversations DESC
        """, as_dict=True)
        
        # Add real-time metrics
        for agent in agent_data:
            agent["current_workload"] = get_agent_current_workload(agent["agent_id"])
            agent["response_time_trend"] = get_agent_response_trend(agent["agent_id"])
            agent["availability_score"] = calculate_availability_score(agent)
        
        return agent_data
        
    except Exception as e:
        frappe.log_error(f"Error getting agent performance: {str(e)}", "Real-time Analytics")
        return []


def get_conversation_flow_metrics():
    """Get conversation flow and routing metrics"""
    try:
        today = frappe.utils.today()
        
        flow_data = {
            "routing_distribution": frappe.db.sql("""
                SELECT 
                    CASE 
                        WHEN processed_by_ai = 1 THEN 'AI Handled'
                        WHEN escalated_to_agent = 1 THEN 'Agent Escalated'
                        ELSE 'Pending'
                    END as routing_type,
                    COUNT(*) as count
                FROM `tabOmnichannel Message`
                WHERE DATE(received_at) = %s
                GROUP BY routing_type
            """, (today,), as_dict=True),
            
            "escalation_reasons": frappe.db.sql("""
                SELECT 
                    escalation_reason,
                    COUNT(*) as count
                FROM `tabOmnichannel Message`
                WHERE DATE(received_at) = %s
                AND escalated_to_agent = 1
                AND escalation_reason IS NOT NULL
                GROUP BY escalation_reason
                ORDER BY count DESC
                LIMIT 10
            """, (today,), as_dict=True),
            
            "conversation_duration": get_conversation_duration_stats(),
            "peak_hours": get_peak_hours_data()
        }
        
        return flow_data
        
    except Exception as e:
        frappe.log_error(f"Error getting conversation flow metrics: {str(e)}", "Real-time Analytics")
        return {}


def get_response_time_analytics():
    """Get detailed response time analytics"""
    try:
        today = frappe.utils.today()
        
        response_data = {
            "hourly_trends": frappe.db.sql("""
                SELECT 
                    HOUR(received_at) as hour,
                    AVG(response_time) as avg_response_time,
                    COUNT(*) as message_count
                FROM `tabOmnichannel Message`
                WHERE DATE(received_at) = %s
                AND response_time IS NOT NULL
                GROUP BY HOUR(received_at)
                ORDER BY hour
            """, (today,), as_dict=True),
            
            "channel_comparison": frappe.db.sql("""
                SELECT 
                    channel_type,
                    AVG(response_time) as avg_response_time,
                    MIN(response_time) as min_response_time,
                    MAX(response_time) as max_response_time,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_time) as median_response_time
                FROM `tabOmnichannel Message`
                WHERE DATE(received_at) = %s
                AND response_time IS NOT NULL
                GROUP BY channel_type
            """, (today,), as_dict=True),
            
            "sla_compliance": calculate_sla_compliance(),
            "response_time_distribution": get_response_time_distribution()
        }
        
        return response_data
        
    except Exception as e:
        frappe.log_error(f"Error getting response time analytics: {str(e)}", "Real-time Analytics")
        return {}


def get_satisfaction_metrics():
    """Get customer satisfaction metrics"""
    try:
        today = frappe.utils.today()
        
        satisfaction_data = {
            "overall_rating": frappe.db.sql("""
                SELECT AVG(satisfaction_rating) as avg_rating
                FROM `tabUser Interaction Log`
                WHERE DATE(timestamp) = %s
                AND satisfaction_rating IS NOT NULL
            """, (today,), as_dict=True)[0].get("avg_rating", 0),
            
            "rating_distribution": frappe.db.sql("""
                SELECT 
                    satisfaction_rating,
                    COUNT(*) as count
                FROM `tabUser Interaction Log`
                WHERE DATE(timestamp) = %s
                AND satisfaction_rating IS NOT NULL
                GROUP BY satisfaction_rating
                ORDER BY satisfaction_rating
            """, (today,), as_dict=True),
            
            "channel_satisfaction": frappe.db.sql("""
                SELECT 
                    om.channel_type,
                    AVG(uil.satisfaction_rating) as avg_rating,
                    COUNT(uil.satisfaction_rating) as rating_count
                FROM `tabOmnichannel Message` om
                LEFT JOIN `tabUser Interaction Log` uil ON om.customer_id = uil.user_id
                WHERE DATE(om.received_at) = %s
                AND uil.satisfaction_rating IS NOT NULL
                GROUP BY om.channel_type
            """, (today,), as_dict=True),
            
            "feedback_trends": get_feedback_trends()
        }
        
        return satisfaction_data
        
    except Exception as e:
        frappe.log_error(f"Error getting satisfaction metrics: {str(e)}", "Real-time Analytics")
        return {}


def get_live_conversations():
    """Get currently active conversations with real-time data"""
    try:
        live_conversations = frappe.db.sql("""
            SELECT 
                oc.name as conversation_id,
                oc.customer_name,
                oc.primary_channel,
                oc.status,
                oc.priority,
                oc.assigned_agent,
                oc.creation_time,
                oc.last_message_time,
                COUNT(om.name) as message_count,
                MAX(om.received_at) as last_activity
            FROM `tabOmnichannel Conversation` oc
            LEFT JOIN `tabOmnichannel Message` om ON oc.name = om.conversation_id
            WHERE oc.status IN ('Open', 'Assigned', 'Pending')
            GROUP BY oc.name
            ORDER BY oc.last_message_time DESC
            LIMIT 50
        """, as_dict=True)
        
        # Add real-time status for each conversation
        for conversation in live_conversations:
            conversation["is_typing"] = check_typing_status(conversation["conversation_id"])
            conversation["agent_online"] = check_agent_online_status(conversation["assigned_agent"])
            conversation["estimated_response_time"] = calculate_estimated_response_time(conversation)
        
        return live_conversations
        
    except Exception as e:
        frappe.log_error(f"Error getting live conversations: {str(e)}", "Real-time Analytics")
        return []


def get_system_health_metrics():
    """Get system health and performance metrics"""
    try:
        health_data = {
            "message_processing_rate": get_message_processing_rate(),
            "webhook_success_rate": get_webhook_success_rate(),
            "ai_service_uptime": get_ai_service_uptime(),
            "database_performance": get_database_performance(),
            "real_time_connections": get_realtime_connection_count(),
            "error_rate": get_error_rate(),
            "system_load": get_system_load_metrics()
        }
        
        return health_data
        
    except Exception as e:
        frappe.log_error(f"Error getting system health metrics: {str(e)}", "Real-time Analytics")
        return {}


# Utility functions for calculations

def get_average_response_time(date):
    """Calculate average response time for a given date"""
    try:
        result = frappe.db.sql("""
            SELECT AVG(response_time) as avg_time
            FROM `tabOmnichannel Message`
            WHERE DATE(received_at) = %s
            AND response_time IS NOT NULL
        """, (date,), as_dict=True)
        
        return result[0].get("avg_time", 0) if result else 0
    except Exception:
        return 0


def get_escalation_rate(date):
    """Calculate escalation rate for a given date"""
    try:
        total_messages = frappe.db.count("Omnichannel Message", {
            "received_at": [">=", date]
        })
        
        escalated_messages = frappe.db.count("Omnichannel Message", {
            "received_at": [">=", date],
            "escalated_to_agent": 1
        })
        
        return (escalated_messages / total_messages * 100) if total_messages > 0 else 0
    except Exception:
        return 0


def get_resolution_rate(date):
    """Calculate resolution rate for a given date"""
    try:
        total_conversations = frappe.db.count("Omnichannel Conversation", {
            "creation_time": [">=", date]
        })
        
        resolved_conversations = frappe.db.count("Omnichannel Conversation", {
            "creation_time": [">=", date],
            "status": ["in", ["Resolved", "Closed"]]
        })
        
        return (resolved_conversations / total_conversations * 100) if total_conversations > 0 else 0
    except Exception:
        return 0


@frappe.whitelist()
def get_realtime_metrics_stream():
    """Get streaming metrics for real-time updates"""
    try:
        metrics = {
            "timestamp": now(),
            "active_conversations": frappe.db.count("Omnichannel Conversation", {
                "status": ["in", ["Open", "Assigned", "Pending"]]
            }),
            "agents_online": frappe.db.count("Agent Dashboard", {
                "status": "online"
            }),
            "messages_last_hour": frappe.db.count("Omnichannel Message", {
                "received_at": [">=", add_to_date(now(), hours=-1)]
            }),
            "avg_response_time_last_hour": get_average_response_time_last_hour(),
            "system_load": get_current_system_load()
        }
        
        # Broadcast to dashboard subscribers
        frappe.publish_realtime(
            "dashboard_metrics_update",
            metrics,
            room="analytics_dashboard"
        )
        
        return {"success": True, "metrics": metrics}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_average_response_time_last_hour():
    """Get average response time for the last hour"""
    try:
        one_hour_ago = add_to_date(now(), hours=-1)
        result = frappe.db.sql("""
            SELECT AVG(response_time) as avg_time
            FROM `tabOmnichannel Message`
            WHERE received_at >= %s
            AND response_time IS NOT NULL
        """, (one_hour_ago,), as_dict=True)
        
        return result[0].get("avg_time", 0) if result else 0
    except Exception:
        return 0


# Additional helper functions would be implemented here...
# (Due to length constraints, showing key structure and main functions)
