import frappe
from frappe import _

def get_context(context):
    """
    Set context for the unified inbox web page.
    """
    context.title = "Unified Inbox - WCFCB Assistant CRM (PILOT DEMO)"
    context.show_sidebar = False
    context.no_cache = True

    # For demo purposes, allow access without strict permission checks
    if frappe.session.user == "Guest":
        # Allow guest access for demonstration
        context.user = None
        context.user_roles = ["Guest"]
        context.is_agent = False
    else:
        try:
            # Get user information
            context.user = frappe.get_doc("User", frappe.session.user)

            # Get user roles
            context.user_roles = frappe.get_roles(frappe.session.user)

            # Check if user is an agent
            context.is_agent = "Assistant CRM Agent" in context.user_roles or "Assistant CRM Manager" in context.user_roles or "System Manager" in context.user_roles
        except Exception as e:
            frappe.log_error(f"Error getting user info: {str(e)}", "Unified Inbox Web Page")
            context.user = None
            context.user_roles = ["Guest"]
            context.is_agent = False

    # Get platform status (with error handling)
    try:
        from assistant_crm.api.social_media_ports import get_platform_status
        platform_status = get_platform_status()
        context.platform_status = platform_status.get("platforms", {})
    except Exception as e:
        # Provide demo platform status
        context.platform_status = {
            "WhatsApp": {"status": "connected", "last_sync": "2025-08-27 17:00:00"},
            "Facebook": {"status": "connected", "last_sync": "2025-08-27 17:00:00"},
            "Instagram": {"status": "connected", "last_sync": "2025-08-27 17:00:00"},
            "Telegram": {"status": "connected", "last_sync": "2025-08-27 17:00:00"},
            "Tawk.to": {"status": "connected", "last_sync": "2025-08-27 17:00:00"}
        }

    # Get AI performance metrics (with error handling)
    try:
        from assistant_crm.api.unified_inbox_api import get_ai_performance_metrics
        ai_metrics = get_ai_performance_metrics()
        context.ai_metrics = ai_metrics.get("metrics", {})
    except Exception as e:
        # Provide demo AI metrics
        context.ai_metrics = {
            "total_messages_processed": 1247,
            "ai_success_rate": 0.78,
            "average_confidence": 0.82,
            "escalation_rate": 0.22,
            "response_time_avg": 2.3
        }

    # Demo mode flag
    context.demo_mode = True

    return context
