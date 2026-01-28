#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Real-Time Communication Service
Enhanced WebSocket and real-time event management for omnichannel communication
"""

import frappe
import json
from frappe import _
from frappe.utils import now, get_datetime
from typing import Dict, List, Optional, Any


class RealtimeService:
    """Enhanced real-time communication service for omnichannel integration"""
    
    def __init__(self):
        self.active_sessions = {}
        self.agent_status = {}
        self.typing_indicators = {}
        
    def broadcast_message(self, channel_type: str, channel_id: str, message_data: Dict[str, Any], 
                         target_users: Optional[List[str]] = None):
        """Broadcast message to all relevant users with enhanced targeting"""
        try:
            event_data = {
                "channel_type": channel_type,
                "channel_id": channel_id,
                "message": message_data.get("content", ""),
                "sender": message_data.get("sender", "System"),
                "timestamp": now(),
                "message_id": message_data.get("message_id"),
                "metadata": message_data.get("metadata", {}),
                "priority": message_data.get("priority", "medium")
            }
            
            if target_users:
                # Targeted broadcast to specific users
                for user in target_users:
                    frappe.publish_realtime(
                        "omnichannel_message",
                        event_data,
                        user=user
                    )
            else:
                # Broadcast to all agents and relevant users
                frappe.publish_realtime(
                    "omnichannel_message",
                    event_data,
                    room=f"channel_{channel_type}_{channel_id}"
                )
                
            # Also broadcast to general omnichannel room for dashboards
            frappe.publish_realtime(
                "omnichannel_update",
                {
                    "type": "new_message",
                    "channel_type": channel_type,
                    "data": event_data
                },
                room="omnichannel_dashboard"
            )
            
            return {"success": True, "event_data": event_data}
            
        except Exception as e:
            frappe.log_error(f"Error broadcasting message: {str(e)}", "Realtime Service")
            return {"success": False, "error": str(e)}
    
    def notify_agent_assignment(self, agent_id: str, conversation_id: str, message_data: Dict[str, Any]):
        """Real-time notification for agent assignment"""
        try:
            # Validate agent_id exists before proceeding
            if not agent_id or not frappe.db.exists("User", agent_id):
                frappe.log_error(f"Invalid agent assignment - agent_id '{agent_id}' not found", "User Validation")
                return {"success": False, "error": f"Agent '{agent_id}' not found"}

            notification_data = {
                "type": "agent_assignment",
                "conversation_id": conversation_id,
                "agent_id": agent_id,
                "customer_name": message_data.get("customer_name", "Unknown"),
                "channel_type": message_data.get("channel_type"),
                "priority": message_data.get("priority", "medium"),
                "message_preview": message_data.get("content", "")[:100],
                "timestamp": now(),
                "estimated_response_time": self.calculate_response_time(agent_id)
            }
            
            # Notify the assigned agent
            frappe.publish_realtime(
                "agent_assignment",
                notification_data,
                user=agent_id
            )
            
            # Update agent dashboard
            frappe.publish_realtime(
                "agent_status_update",
                {
                    "agent_id": agent_id,
                    "new_conversation": conversation_id,
                    "workload_change": "+1"
                },
                room="agent_dashboard"
            )
            
            # Notify customer about agent assignment (if applicable)
            if message_data.get("notify_customer", True):
                self.notify_customer_agent_assigned(conversation_id, agent_id, message_data)
            
            return {"success": True, "notification_sent": True}
            
        except Exception as e:
            frappe.log_error(f"Error notifying agent assignment: {str(e)}", "Realtime Service")
            return {"success": False, "error": str(e)}
    
    def update_typing_indicator(self, conversation_id: str, user_id: str, is_typing: bool, 
                               channel_type: str = None):
        """Manage real-time typing indicators"""
        try:
            typing_key = f"{conversation_id}_{user_id}"
            
            if is_typing:
                self.typing_indicators[typing_key] = {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "channel_type": channel_type,
                    "started_at": now()
                }
            else:
                self.typing_indicators.pop(typing_key, None)
            
            # Broadcast typing status
            frappe.publish_realtime(
                "typing_indicator",
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "is_typing": is_typing,
                    "channel_type": channel_type,
                    "timestamp": now()
                },
                room=f"conversation_{conversation_id}"
            )
            
            return {"success": True, "typing_updated": True}
            
        except Exception as e:
            frappe.log_error(f"Error updating typing indicator: {str(e)}", "Realtime Service")
            return {"success": False, "error": str(e)}
    
    def update_agent_status(self, agent_id: str, status: str, additional_data: Dict[str, Any] = None):
        """Real-time agent status updates"""
        try:
            # Build status_data step by step to isolate dictionary update error
            status_data = {
                "agent_id": agent_id,
                "status": status,  # online, busy, away, offline
                "timestamp": now()
            }

            # Add active conversations with error handling
            try:
                status_data["active_conversations"] = self.get_agent_active_conversations(agent_id)
            except Exception as conv_error:
                frappe.log_error(f"Error getting active conversations: {str(conv_error)}", "Realtime Service Conversations Error")
                status_data["active_conversations"] = 0

            # Add response time with error handling
            try:
                status_data["response_time_avg"] = self.get_agent_avg_response_time(agent_id)
            except Exception as time_error:
                frappe.log_error(f"Error getting response time: {str(time_error)}", "Realtime Service Response Time Error")
                status_data["response_time_avg"] = 0.0
            
            if additional_data:
                # Enhanced surgical fix for dictionary update error
                try:
                    if isinstance(additional_data, dict):
                        status_data.update(additional_data)
                    else:
                        frappe.log_error(f"Invalid additional_data format: {type(additional_data)} - {additional_data}", "Realtime Service Data Format")
                except Exception as update_error:
                    frappe.log_error(f"Dictionary update error in additional_data: {str(update_error)} - Data: {additional_data}", "Realtime Service Update Error")

            # Assign status data with error handling
            try:
                self.agent_status[agent_id] = status_data
            except Exception as assign_error:
                frappe.log_error(f"Error assigning agent status: {str(assign_error)} - Agent: {agent_id}, Data: {status_data}", "Realtime Service Assignment Error")
            
            # Broadcast to agent dashboard with error handling
            try:
                frappe.publish_realtime(
                    "agent_status_update",
                    status_data,
                    room="agent_dashboard"
                )
            except Exception as broadcast_error:
                frappe.log_error(f"Agent dashboard broadcast error: {str(broadcast_error)} - Data: {status_data}", "Realtime Service Broadcast Error")

            # Notify the agent with error handling
            try:
                frappe.publish_realtime(
                    "status_confirmed",
                    {"status": status, "timestamp": now()},
                    user=agent_id
                )
            except Exception as notify_error:
                frappe.log_error(f"Agent notification error: {str(notify_error)} - Agent: {agent_id}", "Realtime Service Notify Error")
            
            return {"success": True, "status_updated": True}
            
        except Exception as e:
            frappe.log_error(f"Error updating agent status: {str(e)}", "Realtime Service")
            return {"success": False, "error": str(e)}
    
    def broadcast_conversation_update(self, conversation_id: str, update_type: str, 
                                    update_data: Dict[str, Any]):
        """Broadcast conversation state changes"""
        try:
            event_data = {
                "conversation_id": conversation_id,
                "update_type": update_type,  # status_change, escalation, resolution, etc.
                "data": update_data,
                "timestamp": now()
            }
            
            # Broadcast to conversation participants
            frappe.publish_realtime(
                "conversation_update",
                event_data,
                room=f"conversation_{conversation_id}"
            )
            
            # Update dashboards
            frappe.publish_realtime(
                "dashboard_update",
                {
                    "type": "conversation_update",
                    "conversation_id": conversation_id,
                    "update_type": update_type,
                    "data": update_data
                },
                room="omnichannel_dashboard"
            )
            
            return {"success": True, "update_broadcasted": True}
            
        except Exception as e:
            frappe.log_error(f"Error broadcasting conversation update: {str(e)}", "Realtime Service")
            return {"success": False, "error": str(e)}
    
    def notify_customer_agent_assigned(self, conversation_id: str, agent_id: str,
                                     message_data: Dict[str, Any]):
        """Notify customer that an agent has been assigned"""
        try:
            # Validate and get agent details with graceful error handling
            agent_name = "Support Agent"  # Default fallback

            if agent_id and frappe.db.exists("User", agent_id):
                try:
                    agent_doc = frappe.get_doc("User", agent_id)
                    agent_name = agent_doc.full_name or agent_doc.first_name or "Support Agent"
                except Exception:
                    # If user document can't be fetched, use default
                    agent_name = "Support Agent"
            else:
                # Log invalid agent_id for debugging but continue operation
                frappe.log_error(f"Invalid or non-existent agent_id: {agent_id}", "User Validation")
                agent_name = "Support Agent"
            
            notification_message = f"Hello! I'm {agent_name}, and I'll be assisting you today. How can I help?"
            
            # Send notification through the original channel
            channel_type = message_data.get("channel_type")
            channel_id = message_data.get("channel_id")
            
            if channel_type == "Website Chat":
                frappe.publish_realtime(
                    "agent_assigned_notification",
                    {
                        "message": notification_message,
                        "agent_name": agent_name,
                        "agent_id": agent_id,
                        "conversation_id": conversation_id
                    },
                    room=f"chat_{channel_id}"
                )
            
            return {"success": True, "customer_notified": True}
            
        except Exception as e:
            frappe.log_error(f"Error notifying customer: {str(e)}", "Realtime Service")
            return {"success": False, "error": str(e)}
    
    def calculate_response_time(self, agent_id: str) -> int:
        """Calculate estimated response time for agent"""
        try:
            # Get agent's recent response times
            recent_responses = frappe.db.sql("""
                SELECT AVG(response_time) as avg_time
                FROM `tabOmnichannel Message`
                WHERE agent_assigned = %s
                AND response_time IS NOT NULL
                AND DATE(processed_at) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            """, (agent_id,), as_dict=True)
            
            if recent_responses and recent_responses[0].avg_time:
                return int(recent_responses[0].avg_time)
            
            return 300  # Default 5 minutes
            
        except Exception:
            return 300
    
    def get_agent_active_conversations(self, agent_id: str) -> int:
        """Get count of active conversations for agent"""
        try:
            count = frappe.db.count("Omnichannel Conversation", {
                "assigned_agent": agent_id,
                "status": ["in", ["Open", "Assigned", "Pending"]]
            })
            return count
        except Exception:
            return 0
    
    def get_agent_avg_response_time(self, agent_id: str) -> float:
        """Get agent's average response time"""
        try:
            result = frappe.db.sql("""
                SELECT AVG(response_time) as avg_time
                FROM `tabOmnichannel Message`
                WHERE agent_assigned = %s
                AND response_time IS NOT NULL
                AND DATE(processed_at) = CURDATE()
            """, (agent_id,), as_dict=True)
            
            if result and result[0].avg_time:
                return float(result[0].avg_time)
            
            return 0.0
        except Exception:
            return 0.0


# ==================== MODULE-LEVEL FUNCTION WRAPPERS ====================
# These functions provide module-level access to class methods for API calls

@frappe.whitelist(allow_guest=True)
def get_agent_avg_response_time(agent_id: str = None) -> float:
    """Module-level wrapper for getting agent average response time"""
    try:
        if not agent_id:
            agent_id = frappe.form_dict.get('agent_id') or frappe.session.user

        service = RealtimeService()
        return service.get_agent_avg_response_time(agent_id)
    except Exception as e:
        frappe.log_error(f"Error getting agent avg response time: {str(e)}")
        return 0.0

@frappe.whitelist(allow_guest=True)
def get_agent_active_conversations(agent_id: str = None) -> int:
    """Module-level wrapper for getting agent active conversations"""
    try:
        if not agent_id:
            agent_id = frappe.form_dict.get('agent_id') or frappe.session.user

        service = RealtimeService()
        return service.get_agent_active_conversations(agent_id)
    except Exception as e:
        frappe.log_error(f"Error getting agent active conversations: {str(e)}")
        return 0

@frappe.whitelist(allow_guest=True)
def update_agent_status(agent_id: str = None, status: str = "online", additional_data: dict = None):
    """Module-level wrapper for updating agent status"""
    try:
        if not agent_id:
            agent_id = frappe.form_dict.get('agent_id') or frappe.session.user
        if not status:
            status = frappe.form_dict.get('status', 'online')



        service = RealtimeService()
        return service.update_agent_status(agent_id, status, additional_data)
    except Exception as e:
        frappe.log_error(f"Error updating agent status: {str(e)}")
        return {"success": False, "error": str(e)}

@frappe.whitelist(allow_guest=True)
def broadcast_message(channel_type: str, channel_id: str, message_data: dict, target_users: list = None):
    """Module-level wrapper for broadcasting messages"""
    try:
        service = RealtimeService()
        return service.broadcast_message(channel_type, channel_id, message_data, target_users)
    except Exception as e:
        frappe.log_error(f"Error broadcasting message: {str(e)}")
        return {"success": False, "error": str(e)}


# API Endpoints for Real-time Operations

@frappe.whitelist()
def join_conversation_room(conversation_id):
    """Join a conversation room for real-time updates"""
    try:
        # Verify user has access to conversation
        conversation = frappe.get_doc("Omnichannel Conversation", conversation_id)
        
        # Join the room
        frappe.publish_realtime(
            "room_joined",
            {"conversation_id": conversation_id, "user": frappe.session.user},
            room=f"conversation_{conversation_id}"
        )
        
        return {"success": True, "room": f"conversation_{conversation_id}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def update_typing_status(conversation_id, is_typing):
    """Update typing status for real-time indicators"""
    try:
        service = RealtimeService()
        result = service.update_typing_indicator(
            conversation_id, 
            frappe.session.user, 
            bool(is_typing)
        )
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


# ROLLBACK VERSION - Uncomment if needed
# @frappe.whitelist()
# def set_agent_status(status, additional_data=None):
#     """Set agent online status"""
#     try:
#         service = RealtimeService()
#         result = service.update_agent_status(
#             frappe.session.user,
#             status,
#             additional_data or {}
#         )
#         return result
#
#     except Exception as e:
#         return {"success": False, "error": str(e)}

@frappe.whitelist(allow_guest=True)
def set_agent_status(status, additional_data=None):
    """Set agent online status"""
    try:
        # For guest users, require agent_id parameter
        agent_id = frappe.form_dict.get('agent_id') or frappe.session.user
        if frappe.session.user == 'Guest' and not frappe.form_dict.get('agent_id'):
            return {"success": False, "error": "agent_id required for guest access"}

        service = RealtimeService()
        result = service.update_agent_status(
            agent_id,
            status,
            additional_data or {}
        )
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def test_ngrok_connection():
    """
    Whitelisted method to test ngrok tunnel connection
    Accessible via: https://your-ngrok-url.ngrok.io/api/method/assistant_crm.services.realtime_service.test_ngrok_connection
    """
    try:
        return {
            "success": True,
            "message": "ngrok tunnel connection successful",
            "timestamp": now(),
            "service": "WCFCB Assistant CRM",
            "version": "1.0",
            "tunnel_status": "active",
            "endpoints": {
                "webhook": "/api/omnichannel/webhook/make-com",
                "chatbot": "/app/assistant-crm",
                "api_test": "/api/method/assistant_crm.services.realtime_service.test_ngrok_connection"
            }
        }
    except Exception as e:
        frappe.log_error(f"ngrok test error: {str(e)}", "ngrok Test")
        return {
            "success": False,
            "error": "ngrok test failed",
            "timestamp": now()
        }


@frappe.whitelist(allow_guest=True)
def get_tunnel_status():
    """
    Get tunnel and system status information
    Accessible via: https://your-ngrok-url.ngrok.io/api/method/assistant_crm.services.realtime_service.get_tunnel_status
    """
    try:
        # Get system information
        system_info = {
            "frappe_version": frappe.__version__,
            "site": frappe.local.site,
            "timestamp": now(),
            "user": frappe.session.user
        }

        # Get Make.com integration status
        try:
            settings = frappe.get_single("Social Media Settings")
            make_com_status = {
                "enabled": settings.get("make_com_enabled", False),
                "api_key_configured": bool(settings.get("make_com_api_key")),
                "webhook_secret_configured": bool(settings.get("make_com_webhook_secret")),
                "rate_limit": settings.get("make_com_rate_limit", 1000),
                "timeout": settings.get("make_com_timeout", 30)
            }
        except:
            make_com_status = {"error": "Settings not accessible"}

        return {
            "success": True,
            "message": "Tunnel status retrieved successfully",
            "system": system_info,
            "make_com_integration": make_com_status,
            "available_endpoints": {
                "webhook": "/api/omnichannel/webhook/make-com",
                "chatbot_app": "/app/assistant-crm",
                "api_ping": "/api/method/ping",
                "tunnel_test": "/api/method/assistant_crm.services.realtime_service.test_ngrok_connection"
            }
        }

    except Exception as e:
        frappe.log_error(f"Tunnel status error: {str(e)}", "Tunnel Status")
        return {
            "success": False,
            "error": "Failed to get tunnel status",
            "timestamp": now()
        }


# ==================== SOCKET.IO EVENT HANDLERS ====================
# These handlers are referenced in hooks.py socketio_events and realtime_events

@frappe.whitelist(allow_guest=True)
def handle_omnichannel_message(data=None):
    """Handle incoming omnichannel messages via Socket.IO"""
    try:
        if not data:
            data = frappe.local.form_dict

        service = RealtimeService()
        return service.broadcast_message(
            data.get("channel_type", "Website Chat"),
            data.get("channel_id", ""),
            data,
            data.get("target_users")
        )
    except Exception as e:
        frappe.log_error(f"Error handling omnichannel message: {str(e)}", "Socket.IO Handler")
        return {"success": False, "error": str(e)}

@frappe.whitelist(allow_guest=True)
def handle_agent_assignment(data=None):
    """Handle agent assignment notifications via Socket.IO"""
    try:
        if not data:
            data = frappe.local.form_dict

        service = RealtimeService()
        return service.notify_agent_assignment(
            data.get("agent_id"),
            data.get("conversation_id"),
            data
        )
    except Exception as e:
        frappe.log_error(f"Error handling agent assignment: {str(e)}", "Socket.IO Handler")
        return {"success": False, "error": str(e)}

@frappe.whitelist(allow_guest=True)
def handle_typing_start(data=None):
    """Handle typing start events via Socket.IO"""
    try:
        if not data:
            data = frappe.local.form_dict

        service = RealtimeService()
        return service.update_typing_indicator(
            data.get("conversation_id"),
            data.get("user_id", frappe.session.user),
            True,
            data.get("channel_type")
        )
    except Exception as e:
        frappe.log_error(f"Error handling typing start: {str(e)}", "Socket.IO Handler")
        return {"success": False, "error": str(e)}

@frappe.whitelist(allow_guest=True)
def handle_typing_stop(data=None):
    """Handle typing stop events via Socket.IO"""
    try:
        if not data:
            data = frappe.local.form_dict

        service = RealtimeService()
        return service.update_typing_indicator(
            data.get("conversation_id"),
            data.get("user_id", frappe.session.user),
            False,
            data.get("channel_type")
        )
    except Exception as e:
        frappe.log_error(f"Error handling typing stop: {str(e)}", "Socket.IO Handler")
        return {"success": False, "error": str(e)}

@frappe.whitelist(allow_guest=True)
def leave_conversation_room(conversation_id=None):
    """Leave a conversation room for real-time updates"""
    try:
        if not conversation_id:
            conversation_id = frappe.local.form_dict.get("conversation_id")

        # Broadcast leave event
        frappe.publish_realtime(
            "room_left",
            {"conversation_id": conversation_id, "user": frappe.session.user},
            room=f"conversation_{conversation_id}"
        )

        return {"success": True, "room": f"conversation_{conversation_id}"}

    except Exception as e:
        return {"success": False, "error": str(e)}
