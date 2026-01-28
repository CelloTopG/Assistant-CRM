# Simplified API usage endpoint - verbose logging removed
import frappe
import json
from frappe.utils import now

@frappe.whitelist(allow_guest=True)
def log_api_usage(log_data):
    """
    Simplified API usage endpoint - accepts logging data but performs minimal processing
    Verbose logging has been removed for performance optimization.

    Args:
        log_data (dict): Usage data from frontend

    Returns:
        dict: Simple success response
    """
    try:
        # Basic validation only
        if isinstance(log_data, str):
            try:
                log_data = json.loads(log_data)
            except json.JSONDecodeError:
                return {"success": False, "error": "Invalid JSON format"}

        if not log_data or not isinstance(log_data, dict):
            return {"success": False, "error": "Invalid log data"}

        # Calculate basic performance metrics for response
        response_time = log_data.get('responseTime', 0)
        performance_category = 'fast' if response_time < 1000 else 'moderate' if response_time < 3000 else 'slow'

        # Return success without verbose logging
        return {
            "success": True,
            "logged": True,
            "performance_metrics": {
                "response_time_ms": response_time,
                "performance_category": performance_category,
                "api_type": log_data.get('apiType', 'unknown'),
                "status": log_data.get('status', 'unknown')
            },
            "timestamp": now()
        }

    except Exception as e:
        # Only log critical errors
        frappe.log_error(f"API usage endpoint error: {str(e)}", "API Usage Error")
        return {
            "success": False,
            "error": "Processing failed"
        }
