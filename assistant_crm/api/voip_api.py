import frappe
from frappe import _
import json
from datetime import datetime
from assistant_crm.services.voip_service import VoIPService


@frappe.whitelist(allow_guest=False)
def initiate_call(customer_phone, customer_id=None):
    """
    Initiate an outbound call to a customer
    
    Args:
        customer_phone: Customer's phone number
        customer_id: Optional customer ID for context
        
    Returns:
        Dict containing call session information and SIP configuration
    """
    try:
        agent_id = frappe.session.user
        voip_service = VoIPService()
        
        result = voip_service.initiate_call(
            agent_id=agent_id,
            customer_phone=customer_phone,
            customer_id=customer_id
        )
        
        if result.get("success"):
            return {
                "success": True,
                "call_session_id": result["call_session_id"],
                "sip_config": result["sip_config"],
                "agent_credentials": result["agent_credentials"],
                "customer_uri": result["customer_uri"],
                "websocket_url": result["websocket_url"],
                "message": "Call initiated successfully"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to initiate call"),
                "message": "Call initiation failed"
            }
            
    except Exception as e:
        frappe.log_error(f"Error in initiate_call API: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Call initiation failed"
        }


@frappe.whitelist(allow_guest=False)
def handle_incoming_call(caller_phone, sip_call_id=None):
    """
    Handle incoming call and route to agent
    
    Args:
        caller_phone: Phone number of the caller
        sip_call_id: Optional SIP call ID
        
    Returns:
        Dict containing call routing information
    """
    try:
        voip_service = VoIPService()
        
        result = voip_service.handle_incoming_call(
            caller_phone=caller_phone,
            agent_id=None  # Let the system auto-route
        )
        
        if result.get("success"):
            return {
                "success": True,
                "call_session_id": result["call_session_id"],
                "agent_id": result["agent_id"],
                "customer_context": result.get("customer_context"),
                "routing_reason": result.get("routing_reason"),
                "message": "Call routed successfully"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to route call"),
                "action": result.get("action", "reject"),
                "message": "Call routing failed"
            }
            
    except Exception as e:
        frappe.log_error(f"Error in handle_incoming_call API: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Call handling failed"
        }


@frappe.whitelist(allow_guest=False)
def update_call_status(call_session_id, status, metadata=None):
    """
    Update call session status
    
    Args:
        call_session_id: Unique call session identifier
        status: New call status (ringing, connected, on_hold, ended, failed)
        metadata: Optional additional metadata
        
    Returns:
        Dict containing update result
    """
    try:
        voip_service = VoIPService()
        
        # Parse metadata if it's a string
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        result = voip_service.update_call_status(
            call_session_id=call_session_id,
            status=status,
            metadata=metadata or {}
        )
        
        if result.get("success"):
            return {
                "success": True,
                "call_session_id": call_session_id,
                "status": status,
                "message": f"Call status updated to {status}"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to update call status"),
                "message": "Status update failed"
            }
            
    except Exception as e:
        frappe.log_error(f"Error in update_call_status API: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Status update failed"
        }


@frappe.whitelist(allow_guest=False)
def get_call_session(call_session_id):
    """
    Get call session information
    
    Args:
        call_session_id: Unique call session identifier
        
    Returns:
        Dict containing call session data
    """
    try:
        voip_service = VoIPService()
        session = voip_service.get_call_session(call_session_id)
        
        if session:
            return {
                "success": True,
                "session": session,
                "message": "Call session retrieved"
            }
        else:
            return {
                "success": False,
                "error": "Call session not found",
                "message": "Session not found"
            }
            
    except Exception as e:
        frappe.log_error(f"Error in get_call_session API: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve session"
        }


@frappe.whitelist(allow_guest=False)
def get_active_calls():
    """
    Get active calls for current agent
    
    Returns:
        Dict containing list of active calls
    """
    try:
        agent_id = frappe.session.user
        voip_service = VoIPService()
        
        active_calls = voip_service.get_active_calls_for_agent(agent_id)
        
        return {
            "success": True,
            "active_calls": active_calls,
            "count": len(active_calls),
            "message": f"Found {len(active_calls)} active calls"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_active_calls API: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "active_calls": [],
            "count": 0,
            "message": "Failed to retrieve active calls"
        }


@frappe.whitelist(allow_guest=False)
def get_call_statistics(date_range=None):
    """
    Get call statistics for current agent
    
    Args:
        date_range: Optional date range filter (JSON string)
        
    Returns:
        Dict containing call statistics
    """
    try:
        agent_id = frappe.session.user
        voip_service = VoIPService()
        
        # Parse date range if provided
        if isinstance(date_range, str):
            try:
                date_range = json.loads(date_range)
            except:
                date_range = None
        
        stats = voip_service.get_call_statistics(
            agent_id=agent_id,
            date_range=date_range
        )
        
        return {
            "success": True,
            "statistics": stats,
            "agent_id": agent_id,
            "message": "Call statistics retrieved"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_call_statistics API: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "statistics": {},
            "message": "Failed to retrieve statistics"
        }


@frappe.whitelist(allow_guest=False)
def get_sip_configuration():
    """
    Get SIP configuration for agent softphone
    
    Returns:
        Dict containing SIP configuration
    """
    try:
        agent_id = frappe.session.user
        voip_service = VoIPService()
        
        # Get agent SIP credentials
        agent_credentials = voip_service.get_agent_sip_credentials(agent_id)
        if not agent_credentials:
            return {
                "success": False,
                "error": "Agent SIP credentials not found",
                "message": "SIP configuration unavailable"
            }
        
        # Get SIP configuration
        sip_config = voip_service.get_sip_configuration()
        
        return {
            "success": True,
            "sip_config": sip_config,
            "agent_credentials": agent_credentials,
            "agent_id": agent_id,
            "message": "SIP configuration retrieved"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_sip_configuration API: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve SIP configuration"
        }


@frappe.whitelist(allow_guest=False)
def search_customers_by_phone(phone_query):
    """
    Search customers by phone number for call initiation
    
    Args:
        phone_query: Partial phone number to search
        
    Returns:
        Dict containing matching customers
    """
    try:
        # Search customers with matching phone numbers
        customers = frappe.db.sql("""
            SELECT 
                name as customer_id,
                customer_name,
                mobile_no,
                phone,
                email_id,
                customer_group
            FROM `tabCustomer`
            WHERE mobile_no LIKE %s OR phone LIKE %s
            ORDER BY customer_name
            LIMIT 20
        """, (f"%{phone_query}%", f"%{phone_query}%"), as_dict=True)
        
        # Enhance with recent interaction data
        for customer in customers:
            recent_calls = frappe.db.sql("""
                SELECT call_direction, call_status, start_time, duration
                FROM `tabCall Log`
                WHERE customer_id = %s
                ORDER BY start_time DESC
                LIMIT 3
            """, (customer["customer_id"],), as_dict=True)
            
            customer["recent_calls"] = recent_calls
            customer["primary_phone"] = customer["mobile_no"] or customer["phone"]
        
        return {
            "success": True,
            "customers": customers,
            "count": len(customers),
            "message": f"Found {len(customers)} matching customers"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in search_customers_by_phone API: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "customers": [],
            "count": 0,
            "message": "Customer search failed"
        }


@frappe.whitelist(allow_guest=False)
def get_call_analytics_dashboard(period="today"):
    """
    Get call analytics for dashboard display
    
    Args:
        period: Time period (today, week, month)
        
    Returns:
        Dict containing dashboard analytics
    """
    try:
        from assistant_crm.doctype.call_log.call_log import get_call_analytics
        
        # Determine date range based on period
        date_range = None
        if period == "today":
            date_range = {
                "start_date": frappe.utils.today(),
                "end_date": frappe.utils.today()
            }
        elif period == "week":
            date_range = {
                "start_date": frappe.utils.add_days(frappe.utils.today(), -7),
                "end_date": frappe.utils.today()
            }
        elif period == "month":
            date_range = {
                "start_date": frappe.utils.add_days(frappe.utils.today(), -30),
                "end_date": frappe.utils.today()
            }
        
        # Get analytics for current agent
        agent_id = frappe.session.user
        analytics = get_call_analytics(agent_id=agent_id, date_range=date_range)
        
        return {
            "success": True,
            "analytics": analytics,
            "period": period,
            "agent_id": agent_id,
            "message": "Call analytics retrieved"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_call_analytics_dashboard API: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "analytics": {},
            "message": "Failed to retrieve analytics"
        }
