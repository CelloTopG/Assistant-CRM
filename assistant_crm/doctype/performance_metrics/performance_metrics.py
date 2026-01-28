# Copyright (c) 2025, Assistant CRM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
from datetime import datetime, timedelta


class PerformanceMetrics(Document):
    def before_save(self):
        """Calculate variance percentage before saving"""
        self.calculate_variance()
        self.validate_metric_data()
    
    def calculate_variance(self):
        """Calculate variance percentage between actual and target values"""
        if self.target_value and self.target_value != 0:
            variance = ((self.metric_value - self.target_value) / self.target_value) * 100
            self.variance_percentage = round(variance, 2)
        else:
            self.variance_percentage = 0
    
    def validate_metric_data(self):
        """Validate metric data based on category"""
        if self.metric_category == "Agent":
            self.validate_agent_metrics()
        elif self.metric_category == "Channel":
            self.validate_channel_metrics()
        elif self.metric_category == "Response":
            self.validate_response_metrics()
    
    def validate_agent_metrics(self):
        """Validate agent-specific metrics"""
        if self.entity_type != "Agent":
            frappe.throw("Entity Type must be 'Agent' for Agent metrics")
        
        # Validate metric value ranges for agent metrics
        if self.metric_name in ["Response Time", "Resolution Time"] and self.metric_value < 0:
            frappe.throw("Time-based metrics cannot be negative")
        
        if self.metric_name in ["Satisfaction Score", "Success Rate"] and (self.metric_value < 0 or self.metric_value > 100):
            frappe.throw("Percentage-based metrics must be between 0 and 100")
    
    def validate_channel_metrics(self):
        """Validate channel-specific metrics"""
        if self.entity_type != "Channel":
            frappe.throw("Entity Type must be 'Channel' for Channel metrics")
    
    def validate_response_metrics(self):
        """Validate response optimization metrics"""
        if self.entity_type != "System":
            frappe.throw("Entity Type must be 'System' for Response metrics")
    
    def get_trend_analysis(self, days=30):
        """Get trend analysis for this metric over specified days"""
        end_date = self.measurement_date
        start_date = end_date - timedelta(days=days)
        
        # Get historical data for the same metric
        historical_data = frappe.get_all(
            "Performance Metrics",
            filters={
                "metric_name": self.metric_name,
                "entity_id": self.entity_id,
                "measurement_date": ["between", [start_date, end_date]]
            },
            fields=["measurement_date", "metric_value"],
            order_by="measurement_date"
        )
        
        if len(historical_data) < 2:
            return {"trend": "insufficient_data", "change": 0}
        
        # Calculate trend
        first_value = historical_data[0]["metric_value"]
        last_value = historical_data[-1]["metric_value"]
        
        if first_value == 0:
            change_percentage = 0
        else:
            change_percentage = ((last_value - first_value) / first_value) * 100
        
        trend = "improving" if change_percentage > 5 else "declining" if change_percentage < -5 else "stable"
        
        return {
            "trend": trend,
            "change": round(change_percentage, 2),
            "data_points": len(historical_data),
            "period_days": days
        }
    
    def update_trend_data(self):
        """Update trend data field with current analysis"""
        trend_analysis = self.get_trend_analysis()
        
        trend_data = {
            "last_updated": datetime.now().isoformat(),
            "trend_30_days": trend_analysis,
            "trend_7_days": self.get_trend_analysis(7),
            "trend_90_days": self.get_trend_analysis(90)
        }
        
        self.trend_data = json.dumps(trend_data)
    
    @staticmethod
    def create_agent_metric(agent_id, agent_name, metric_name, metric_value, target_value=None, details=None):
        """Helper method to create agent performance metrics"""
        metric = frappe.get_doc({
            "doctype": "Performance Metrics",
            "metric_name": metric_name,
            "metric_category": "Agent",
            "metric_value": metric_value,
            "target_value": target_value,
            "entity_type": "Agent",
            "entity_id": agent_id,
            "entity_name": agent_name,
            "measurement_date": datetime.now(),
            "details": json.dumps(details) if details else None
        })
        metric.insert()
        return metric
    
    @staticmethod
    def create_channel_metric(channel_id, channel_name, metric_name, metric_value, target_value=None, details=None):
        """Helper method to create channel performance metrics"""
        metric = frappe.get_doc({
            "doctype": "Performance Metrics",
            "metric_name": metric_name,
            "metric_category": "Channel",
            "metric_value": metric_value,
            "target_value": target_value,
            "entity_type": "Channel",
            "entity_id": channel_id,
            "entity_name": channel_name,
            "measurement_date": datetime.now(),
            "details": json.dumps(details) if details else None
        })
        metric.insert()
        return metric
    
    @staticmethod
    def create_system_metric(metric_name, metric_value, target_value=None, details=None):
        """Helper method to create system performance metrics"""
        metric = frappe.get_doc({
            "doctype": "Performance Metrics",
            "metric_name": metric_name,
            "metric_category": "System",
            "metric_value": metric_value,
            "target_value": target_value,
            "entity_type": "System",
            "entity_id": "system",
            "entity_name": "System",
            "measurement_date": datetime.now(),
            "details": json.dumps(details) if details else None
        })
        metric.insert()
        return metric
    
    def get_dashboard_data(self):
        """Get data formatted for dashboard display"""
        return {
            "metric_name": self.metric_name,
            "current_value": self.metric_value,
            "target_value": self.target_value,
            "variance": self.variance_percentage,
            "status": "above_target" if self.variance_percentage > 0 else "below_target" if self.variance_percentage < 0 else "on_target",
            "entity": f"{self.entity_type}: {self.entity_name}",
            "last_updated": self.measurement_date,
            "trend": json.loads(self.trend_data) if self.trend_data else None
        }


@frappe.whitelist()
def get_metrics_dashboard(entity_type=None, entity_id=None, metric_category=None):
    """Get metrics data for dashboard display"""
    filters = {"status": "Active"}
    
    if entity_type:
        filters["entity_type"] = entity_type
    if entity_id:
        filters["entity_id"] = entity_id
    if metric_category:
        filters["metric_category"] = metric_category
    
    metrics = frappe.get_all(
        "Performance Metrics",
        filters=filters,
        fields=["name", "metric_name", "metric_value", "target_value", "variance_percentage", 
                "entity_type", "entity_name", "measurement_date", "trend_data"],
        order_by="measurement_date desc",
        limit=50
    )
    
    dashboard_data = []
    for metric in metrics:
        doc = frappe.get_doc("Performance Metrics", metric.name)
        dashboard_data.append(doc.get_dashboard_data())
    
    return dashboard_data


@frappe.whitelist()
def update_all_trend_data():
    """Update trend data for all active metrics"""
    active_metrics = frappe.get_all("Performance Metrics", filters={"status": "Active"})
    
    updated_count = 0
    for metric in active_metrics:
        doc = frappe.get_doc("Performance Metrics", metric.name)
        doc.update_trend_data()
        doc.save()
        updated_count += 1
    
    return {"updated_count": updated_count, "message": f"Updated trend data for {updated_count} metrics"}
