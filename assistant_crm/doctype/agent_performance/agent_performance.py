# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, get_datetime
import json


class AgentPerformance(Document):
    """
    Agent Performance DocType for tracking agent metrics and performance.
    """
    
    def before_save(self):
        """Set agent name and calculate derived metrics."""
        if self.agent:
            user_doc = frappe.get_doc("User", self.agent)
            self.agent_name = user_doc.full_name or user_doc.first_name
        
        # Calculate derived metrics
        self.calculate_derived_metrics()
    
    def calculate_derived_metrics(self):
        """Calculate derived performance metrics."""
        # Calculate most active platform
        if self.platform_distribution:
            try:
                platform_data = json.loads(self.platform_distribution) if isinstance(self.platform_distribution, str) else self.platform_distribution
                if platform_data:
                    self.most_active_platform = max(platform_data, key=platform_data.get)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Calculate platform expertise score (based on platform diversity)
        if self.platform_distribution:
            try:
                platform_data = json.loads(self.platform_distribution) if isinstance(self.platform_distribution, str) else self.platform_distribution
                if platform_data:
                    # Score based on number of platforms handled and distribution
                    num_platforms = len(platform_data)
                    total_conversations = sum(platform_data.values())
                    if total_conversations > 0:
                        # Higher score for handling multiple platforms effectively
                        diversity_score = min(num_platforms / 5.0, 1.0)  # Max 5 platforms
                        volume_score = min(total_conversations / 20.0, 1.0)  # Max 20 conversations
                        self.platform_expertise_score = (diversity_score + volume_score) / 2 * 100
            except (json.JSONDecodeError, TypeError):
                self.platform_expertise_score = 0
    
    def get_performance_summary(self):
        """Get a summary of agent performance."""
        return {
            "agent": self.agent_name,
            "total_conversations": self.total_conversations,
            "active_conversations": self.active_conversations,
            "satisfaction_score": self.customer_satisfaction_score,
            "response_time": self.average_response_time,
            "status": self.current_workload_status,
            "most_active_platform": self.most_active_platform
        }


@frappe.whitelist()
def get_agent_performance_data(agent=None, date=None):
    """Get agent performance data for dashboard."""
    try:
        filters = {}
        if agent:
            filters["agent"] = agent
        if date:
            filters["date"] = date
        else:
            filters["date"] = now().split()[0]  # Today
        
        performance_records = frappe.get_all(
            "Agent Performance",
            filters=filters,
            fields=["*"],
            order_by="date desc"
        )
        
        return {
            "status": "success",
            "performance_data": performance_records
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting agent performance data: {str(e)}", "Agent Performance Error")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_team_performance_summary():
    """Get team-wide performance summary."""
    try:
        today = now().split()[0]
        
        # Get all agent performance records for today
        performance_records = frappe.get_all(
            "Agent Performance",
            filters={"date": today},
            fields=["*"]
        )
        
        if not performance_records:
            return {
                "status": "success",
                "summary": {
                    "total_agents": 0,
                    "total_conversations": 0,
                    "average_satisfaction": 0,
                    "average_response_time": 0,
                    "agents_available": 0,
                    "agents_busy": 0
                }
            }
        
        # Calculate team metrics
        total_agents = len(performance_records)
        total_conversations = sum(record.total_conversations for record in performance_records)
        avg_satisfaction = sum(record.customer_satisfaction_score or 0 for record in performance_records) / total_agents
        avg_response_time = sum(record.average_response_time or 0 for record in performance_records) / total_agents
        
        # Count agent statuses
        agents_available = len([r for r in performance_records if r.current_workload_status == "Available"])
        agents_busy = len([r for r in performance_records if r.current_workload_status == "Busy"])
        
        return {
            "status": "success",
            "summary": {
                "total_agents": total_agents,
                "total_conversations": total_conversations,
                "average_satisfaction": round(avg_satisfaction, 2),
                "average_response_time": round(avg_response_time, 2),
                "agents_available": agents_available,
                "agents_busy": agents_busy,
                "performance_records": performance_records
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting team performance summary: {str(e)}", "Team Performance Error")
        return {"status": "error", "message": str(e)}
