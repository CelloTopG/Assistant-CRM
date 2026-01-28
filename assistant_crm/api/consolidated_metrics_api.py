"""
Consolidated Metrics API - Updated for New Performance Metrics DocType
Surgical precision updates to work with unified metrics system
"""

import frappe
import json
from frappe.utils import now, add_days, get_datetime
from datetime import datetime, timedelta

# Safe import of translation function
try:
    from frappe import _
except ImportError:
    def _(text):
        return text


class ConsolidatedMetricsService:
    """Service class for handling consolidated metrics operations"""
    
    def create_metric_consolidated(self, metric_data):
        """
        Create a new performance metric with consolidated structure
        
        Args:
            metric_data (dict): Metric data
            
        Returns:
            dict: Created metric document
        """
        try:
            # Use the helper methods from Performance Metrics doctype
            if metric_data.get("metric_category") == "Agent":
                metric_doc = frappe.get_doc("Performance Metrics").create_agent_metric(
                    agent_id=metric_data.get("entity_id"),
                    agent_name=metric_data.get("entity_name"),
                    metric_name=metric_data.get("metric_name"),
                    metric_value=metric_data.get("metric_value"),
                    target_value=metric_data.get("target_value"),
                    details=metric_data.get("details")
                )
            elif metric_data.get("metric_category") == "Channel":
                metric_doc = frappe.get_doc("Performance Metrics").create_channel_metric(
                    channel_id=metric_data.get("entity_id"),
                    channel_name=metric_data.get("entity_name"),
                    metric_name=metric_data.get("metric_name"),
                    metric_value=metric_data.get("metric_value"),
                    target_value=metric_data.get("target_value"),
                    details=metric_data.get("details")
                )
            elif metric_data.get("metric_category") == "System":
                metric_doc = frappe.get_doc("Performance Metrics").create_system_metric(
                    metric_name=metric_data.get("metric_name"),
                    metric_value=metric_data.get("metric_value"),
                    target_value=metric_data.get("target_value"),
                    details=metric_data.get("details")
                )
            else:
                # Generic metric creation
                metric_doc = frappe.get_doc({
                    "doctype": "Performance Metrics",
                    "metric_name": metric_data.get("metric_name"),
                    "metric_category": metric_data.get("metric_category"),
                    "metric_value": metric_data.get("metric_value"),
                    "target_value": metric_data.get("target_value"),
                    "entity_type": metric_data.get("entity_type"),
                    "entity_id": metric_data.get("entity_id"),
                    "entity_name": metric_data.get("entity_name"),
                    "measurement_date": metric_data.get("measurement_date", now()),
                    "period": metric_data.get("period", "Daily"),
                    "frequency": metric_data.get("frequency", "Recurring"),
                    "details": json.dumps(metric_data.get("details", {})) if metric_data.get("details") else None
                })
                metric_doc.insert(ignore_permissions=True)
            
            return {
                "success": True,
                "metric": metric_doc,
                "message": "Metric created successfully"
            }
            
        except Exception as e:
            frappe.log_error(f"Error creating consolidated metric: {str(e)}", "Consolidated Metrics Error")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_metrics_dashboard_consolidated(self, entity_type=None, entity_id=None, metric_category=None):
        """
        Get metrics data for dashboard display using consolidated structure
        
        Args:
            entity_type (str): Filter by entity type
            entity_id (str): Filter by entity ID
            metric_category (str): Filter by metric category
            
        Returns:
            dict: Dashboard metrics data
        """
        try:
            # Use the dashboard method from Performance Metrics doctype
            dashboard_data = frappe.get_doc("Performance Metrics").get_metrics_dashboard(
                entity_type=entity_type,
                entity_id=entity_id,
                metric_category=metric_category
            )
            
            return {
                "success": True,
                "metrics": dashboard_data,
                "count": len(dashboard_data)
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting consolidated metrics dashboard: {str(e)}", "Consolidated Metrics Error")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_metric_trends_consolidated(self, metric_name, entity_id, days=30):
        """
        Get trend analysis for a specific metric
        
        Args:
            metric_name (str): Name of the metric
            entity_id (str): Entity ID
            days (int): Number of days for trend analysis
            
        Returns:
            dict: Trend analysis data
        """
        try:
            # Get recent metric record
            metric_record = frappe.get_all(
                "Performance Metrics",
                filters={
                    "metric_name": metric_name,
                    "entity_id": entity_id,
                    "status": "Active"
                },
                fields=["name"],
                order_by="measurement_date desc",
                limit=1
            )
            
            if not metric_record:
                return {
                    "success": False,
                    "error": "Metric not found"
                }
            
            # Get trend analysis
            metric_doc = frappe.get_doc("Performance Metrics", metric_record[0]["name"])
            trend_analysis = metric_doc.get_trend_analysis(days)
            
            return {
                "success": True,
                "trend": trend_analysis
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting consolidated metric trends: {str(e)}", "Consolidated Metrics Error")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_all_trend_data_consolidated(self):
        """Update trend data for all active metrics"""
        try:
            # Use the update method from Performance Metrics doctype
            result = frappe.get_doc("Performance Metrics").update_all_trend_data()
            
            return {
                "success": True,
                "updated_count": result.get("updated_count", 0),
                "message": result.get("message", "Trend data updated")
            }
            
        except Exception as e:
            frappe.log_error(f"Error updating consolidated trend data: {str(e)}", "Consolidated Metrics Error")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_entity_metrics_consolidated(self, entity_type, entity_id, metric_category=None, limit=50):
        """
        Get all metrics for a specific entity
        
        Args:
            entity_type (str): Type of entity
            entity_id (str): Entity ID
            metric_category (str): Optional metric category filter
            limit (int): Maximum results
            
        Returns:
            dict: Entity metrics data
        """
        try:
            filters = {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "status": "Active"
            }
            
            if metric_category:
                filters["metric_category"] = metric_category
            
            metrics = frappe.get_all(
                "Performance Metrics",
                filters=filters,
                fields=[
                    "name", "metric_name", "metric_category", "metric_value",
                    "target_value", "variance_percentage", "measurement_date",
                    "period", "details", "trend_data"
                ],
                order_by="measurement_date desc",
                limit=limit
            )
            
            # Parse details and trend data
            for metric in metrics:
                if metric.get("details"):
                    try:
                        metric["details"] = json.loads(metric["details"])
                    except:
                        metric["details"] = {}
                
                if metric.get("trend_data"):
                    try:
                        metric["trend_data"] = json.loads(metric["trend_data"])
                    except:
                        metric["trend_data"] = {}
            
            return {
                "success": True,
                "metrics": metrics,
                "count": len(metrics),
                "entity": {
                    "type": entity_type,
                    "id": entity_id
                }
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting consolidated entity metrics: {str(e)}", "Consolidated Metrics Error")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_metrics_summary_consolidated(self, metric_category=None, period="Daily"):
        """
        Get summary of metrics by category and period
        
        Args:
            metric_category (str): Optional category filter
            period (str): Time period filter
            
        Returns:
            dict: Metrics summary
        """
        try:
            filters = {
                "status": "Active",
                "period": period
            }
            
            if metric_category:
                filters["metric_category"] = metric_category
            
            # Get metrics summary
            metrics = frappe.get_all(
                "Performance Metrics",
                filters=filters,
                fields=[
                    "metric_category", "metric_name", "metric_value",
                    "target_value", "variance_percentage", "entity_type"
                ]
            )
            
            # Group by category
            summary = {}
            for metric in metrics:
                category = metric["metric_category"]
                if category not in summary:
                    summary[category] = {
                        "count": 0,
                        "avg_value": 0,
                        "avg_variance": 0,
                        "above_target": 0,
                        "below_target": 0,
                        "on_target": 0
                    }
                
                summary[category]["count"] += 1
                summary[category]["avg_value"] += metric["metric_value"]
                summary[category]["avg_variance"] += metric["variance_percentage"] or 0
                
                # Categorize performance
                variance = metric["variance_percentage"] or 0
                if variance > 5:
                    summary[category]["above_target"] += 1
                elif variance < -5:
                    summary[category]["below_target"] += 1
                else:
                    summary[category]["on_target"] += 1
            
            # Calculate averages
            for category in summary:
                count = summary[category]["count"]
                if count > 0:
                    summary[category]["avg_value"] /= count
                    summary[category]["avg_variance"] /= count
            
            return {
                "success": True,
                "summary": summary,
                "period": period,
                "total_metrics": len(metrics)
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting consolidated metrics summary: {str(e)}", "Consolidated Metrics Error")
            return {
                "success": False,
                "error": str(e)
            }


# Initialize service
consolidated_metrics_service = ConsolidatedMetricsService()


# ============================================================================
# CONSOLIDATED METRICS API ENDPOINTS
# ============================================================================

@frappe.whitelist()
def create_metric_consolidated():
    """Create a new performance metric"""
    try:
        data = frappe.local.form_dict
        result = consolidated_metrics_service.create_metric_consolidated(data)
        return result
        
    except Exception as e:
        frappe.log_error(f"Metrics creation API error: {str(e)}", "Consolidated Metrics API Error")
        return {"success": False, "error": "Failed to create metric"}


@frappe.whitelist()
def get_metrics_dashboard_consolidated(entity_type=None, entity_id=None, metric_category=None):
    """Get metrics data for dashboard display"""
    try:
        result = consolidated_metrics_service.get_metrics_dashboard_consolidated(entity_type, entity_id, metric_category)
        return result
        
    except Exception as e:
        frappe.log_error(f"Metrics dashboard API error: {str(e)}", "Consolidated Metrics API Error")
        return {"success": False, "error": "Failed to get dashboard data"}


@frappe.whitelist()
def get_metric_trends_consolidated(metric_name, entity_id, days=30):
    """Get trend analysis for a specific metric"""
    try:
        result = consolidated_metrics_service.get_metric_trends_consolidated(metric_name, entity_id, int(days))
        return result
        
    except Exception as e:
        frappe.log_error(f"Metrics trends API error: {str(e)}", "Consolidated Metrics API Error")
        return {"success": False, "error": "Failed to get trend data"}


@frappe.whitelist()
def get_entity_metrics_consolidated(entity_type, entity_id, metric_category=None, limit=50):
    """Get all metrics for a specific entity"""
    try:
        result = consolidated_metrics_service.get_entity_metrics_consolidated(entity_type, entity_id, metric_category, int(limit))
        return result
        
    except Exception as e:
        frappe.log_error(f"Entity metrics API error: {str(e)}", "Consolidated Metrics API Error")
        return {"success": False, "error": "Failed to get entity metrics"}


@frappe.whitelist()
def get_metrics_summary_consolidated(metric_category=None, period="Daily"):
    """Get summary of metrics by category and period"""
    try:
        result = consolidated_metrics_service.get_metrics_summary_consolidated(metric_category, period)
        return result
        
    except Exception as e:
        frappe.log_error(f"Metrics summary API error: {str(e)}", "Consolidated Metrics API Error")
        return {"success": False, "error": "Failed to get metrics summary"}


@frappe.whitelist()
def update_all_trend_data_consolidated():
    """Update trend data for all active metrics"""
    try:
        result = consolidated_metrics_service.update_all_trend_data_consolidated()
        return result
        
    except Exception as e:
        frappe.log_error(f"Trend update API error: {str(e)}", "Consolidated Metrics API Error")
        return {"success": False, "error": "Failed to update trend data"}
