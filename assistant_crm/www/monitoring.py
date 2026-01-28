# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _


def get_context(context):
    """Get context for monitoring dashboard"""
    context.title = _("Assistant CRM - System Monitoring")
    context.show_sidebar = False
    
    # Check permissions
    if not frappe.has_permission("Assistant CRM Settings", "read"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    
    try:
        from assistant_crm.services.monitoring_service import get_monitoring_service
        from assistant_crm.services.cache_service import get_cache_service
        from assistant_crm.services.error_handler import get_error_handler
        
        monitoring_service = get_monitoring_service()
        
        # Get system health
        context.system_health = monitoring_service.get_system_health()
        
        # Get performance metrics
        context.performance_metrics = monitoring_service.get_performance_metrics()
        
        # Get cache statistics
        cache_service = get_cache_service()
        context.cache_stats = cache_service.get_cache_stats()
        
        # Get error handler statistics
        error_handler = get_error_handler("gemini_api")
        context.error_stats = error_handler.get_error_stats()
        
        # Get active alerts
        context.active_alerts = monitoring_service.get_active_alerts()
        
        # Convert to JSON for JavaScript
        context.system_health_json = json.dumps(context.system_health)
        context.performance_metrics_json = json.dumps(context.performance_metrics)
        context.cache_stats_json = json.dumps(context.cache_stats)
        context.error_stats_json = json.dumps(context.error_stats)
        
    except Exception as e:
        frappe.log_error(f"Error loading monitoring dashboard: {str(e)}", "Monitoring Dashboard")
        context.error_message = str(e)


@frappe.whitelist()
def get_real_time_metrics():
    """API endpoint for real-time metrics"""
    try:
        from assistant_crm.services.monitoring_service import get_monitoring_service
        
        monitoring_service = get_monitoring_service()
        
        return {
            "success": True,
            "data": {
                "system_health": monitoring_service.get_system_health(),
                "performance_metrics": monitoring_service.get_performance_metrics(),
                "timestamp": frappe.utils.now()
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting real-time metrics: {str(e)}", "Monitoring API")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def acknowledge_alert(alert_id):
    """API endpoint to acknowledge an alert"""
    try:
        from assistant_crm.services.monitoring_service import get_monitoring_service
        
        monitoring_service = get_monitoring_service()
        success = monitoring_service.acknowledge_alert(alert_id)
        
        return {
            "success": success,
            "message": "Alert acknowledged successfully" if success else "Failed to acknowledge alert"
        }
        
    except Exception as e:
        frappe.log_error(f"Error acknowledging alert: {str(e)}", "Monitoring API")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def reset_circuit_breaker(service_name="gemini_api"):
    """API endpoint to reset circuit breaker"""
    try:
        from assistant_crm.services.error_handler import get_error_handler
        
        error_handler = get_error_handler(service_name)
        error_handler.reset_circuit()
        
        return {
            "success": True,
            "message": f"Circuit breaker reset for {service_name}"
        }
        
    except Exception as e:
        frappe.log_error(f"Error resetting circuit breaker: {str(e)}", "Monitoring API")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def clear_cache(pattern=None):
    """API endpoint to clear cache"""
    try:
        from assistant_crm.services.cache_service import get_cache_service
        
        cache_service = get_cache_service()
        cleared_count = cache_service.clear_cache(pattern)
        
        return {
            "success": True,
            "message": f"Cleared {cleared_count} cache entries",
            "cleared_count": cleared_count
        }
        
    except Exception as e:
        frappe.log_error(f"Error clearing cache: {str(e)}", "Monitoring API")
        return {
            "success": False,
            "error": str(e)
        }
