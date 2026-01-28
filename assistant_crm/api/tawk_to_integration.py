#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Tawk.to Integration API
============================================

Complete integration with Tawk.to for call logging and chat management.
Provides real-time synchronization with Tawk.to platform and direct routing
to human agents bypassing AI chatbot.

Features:
- Real-time chat synchronization
- Call logging integration
- Visitor tracking
- Agent assignment
- Direct human agent routing
- Webhook handling for Tawk.to events

Author: WCFCB Development Team
Created: 2025-08-27
License: MIT
"""

import frappe
import requests
import json
from frappe import _
from frappe.utils import now, get_datetime
from typing import Dict, Any, Optional, List
import hashlib
import hmac


# Tawk.to API Configuration
TAWK_TO_API_KEY = "47585bce62f84437dace4a6ed63ee14b1ce2a6dd"
TAWK_TO_PROPERTY_ID = "68ac3c63fda87419226520f9"
TAWK_TO_BASE_URL = "https://api.tawk.to/v3"


class TawkToIntegration:
    """
    Main class for Tawk.to integration with unified inbox system.
    """
    
    def __init__(self):
        self.api_key = TAWK_TO_API_KEY
        self.property_id = TAWK_TO_PROPERTY_ID
        self.base_url = TAWK_TO_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def get_active_chats(self) -> List[Dict[str, Any]]:
        """Get all active chats from Tawk.to."""
        try:
            url = f"{self.base_url}/property/{self.property_id}/chats"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json().get("chats", [])
            else:
                frappe.log_error(f"Failed to get active chats: {response.text}", "Tawk.to Integration Error")
                return []
                
        except Exception as e:
            frappe.log_error(f"Error getting active chats: {str(e)}", "Tawk.to Integration Error")
            return []
    
    def get_chat_messages(self, chat_id: str) -> List[Dict[str, Any]]:
        """Get messages for a specific chat."""
        try:
            url = f"{self.base_url}/property/{self.property_id}/chats/{chat_id}/messages"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json().get("messages", [])
            else:
                frappe.log_error(f"Failed to get chat messages: {response.text}", "Tawk.to Integration Error")
                return []
                
        except Exception as e:
            frappe.log_error(f"Error getting chat messages: {str(e)}", "Tawk.to Integration Error")
            return []
    
    def send_message(self, chat_id: str, message: str, agent_id: str = None) -> bool:
        """Send a message to a Tawk.to chat."""
        try:
            url = f"{self.base_url}/property/{self.property_id}/chats/{chat_id}/messages"
            
            payload = {
                "message": message,
                "type": "text"
            }
            
            if agent_id:
                payload["agentId"] = agent_id
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 201:
                return True
            else:
                frappe.log_error(f"Failed to send message: {response.text}", "Tawk.to Integration Error")
                return False
                
        except Exception as e:
            frappe.log_error(f"Error sending message: {str(e)}", "Tawk.to Integration Error")
            return False
    
    def get_visitor_info(self, visitor_id: str) -> Dict[str, Any]:
        """Get visitor information from Tawk.to."""
        try:
            url = f"{self.base_url}/property/{self.property_id}/visitors/{visitor_id}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                frappe.log_error(f"Failed to get visitor info: {response.text}", "Tawk.to Integration Error")
                return {}
                
        except Exception as e:
            frappe.log_error(f"Error getting visitor info: {str(e)}", "Tawk.to Integration Error")
            return {}
    
    def sync_chat_to_unified_inbox(self, chat_data: Dict[str, Any]) -> Optional[str]:
        """Sync a Tawk.to chat to unified inbox."""
        try:
            # Check if conversation already exists
            existing_conversation = frappe.get_all(
                "Unified Inbox Conversation",
                filters={
                    "platform": "Tawk.to",
                    "tawk_to_session_id": chat_data.get("id")
                },
                limit=1
            )
            
            if existing_conversation:
                return existing_conversation[0].name
            
            # Get visitor information
            visitor_info = self.get_visitor_info(chat_data.get("visitorId", ""))
            
            # Create new unified inbox conversation
            conversation_doc = frappe.get_doc({
                "doctype": "Unified Inbox Conversation",
                "platform": "Tawk.to",
                "platform_specific_id": chat_data.get("id"),
                "customer_name": visitor_info.get("name") or chat_data.get("visitorName") or "Unknown Visitor",
                "customer_email": visitor_info.get("email"),
                "customer_phone": visitor_info.get("phone"),
                "customer_platform_id": chat_data.get("visitorId"),
                "status": "Agent Assigned",  # Tawk.to chats go directly to agents
                "priority": "Medium",
                "tawk_to_session_id": chat_data.get("id"),
                "tawk_to_visitor_id": chat_data.get("visitorId"),
                "tawk_to_chat_id": chat_data.get("id"),
                "creation_time": chat_data.get("createdTime") or now(),
                "platform_metadata": json.dumps({
                    "tawk_to_data": chat_data,
                    "visitor_info": visitor_info
                })
            })
            
            conversation_doc.insert(ignore_permissions=True)
            
            # Assign to available agent immediately
            conversation_doc.escalate_to_human_agent("Tawk.to chat - direct to agent")
            
            return conversation_doc.name
            
        except Exception as e:
            frappe.log_error(f"Error syncing chat to unified inbox: {str(e)}", "Tawk.to Integration Error")
            return None
    
    def sync_messages_to_unified_inbox(self, conversation_name: str, chat_id: str):
        """Sync Tawk.to messages to unified inbox."""
        try:
            # Get messages from Tawk.to
            messages = self.get_chat_messages(chat_id)
            
            for message_data in messages:
                # Check if message already exists
                existing_message = frappe.get_all(
                    "Unified Inbox Message",
                    filters={
                        "conversation": conversation_name,
                        "platform_message_id": message_data.get("id")
                    },
                    limit=1
                )
                
                if existing_message:
                    continue
                
                # Create unified inbox message
                message_doc = frappe.get_doc({
                    "doctype": "Unified Inbox Message",
                    "conversation": conversation_name,
                    "platform": "Tawk.to",
                    "direction": "Outbound" if message_data.get("type") == "agent" else "Inbound",
                    "message_type": message_data.get("messageType", "text"),
                    "message_content": message_data.get("text", ""),
                    "sender_name": message_data.get("senderName"),
                    "sender_id": message_data.get("senderId"),
                    "timestamp": message_data.get("time") or now(),
                    "platform_message_id": message_data.get("id"),
                    "platform_metadata": json.dumps(message_data),
                    "handled_by_agent": 1 if message_data.get("type") == "agent" else 0
                })
                
                message_doc.insert(ignore_permissions=True)
                
        except Exception as e:
            frappe.log_error(f"Error syncing messages: {str(e)}", "Tawk.to Integration Error")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def tawk_to_webhook():
    """
    Webhook endpoint for Tawk.to events.
    
    Handles real-time events from Tawk.to including:
    - New chat started
    - Message received
    - Chat ended
    - Agent assigned
    """
    try:
        # Get webhook data
        webhook_data = frappe.request.get_data(as_text=True)
        
        if not webhook_data:
            return {"status": "error", "message": "No webhook data received"}
        
        data = json.loads(webhook_data)
        event_type = data.get("event")
        
        tawk_integration = TawkToIntegration()
        
        if event_type == "chat:start":
            # New chat started
            chat_data = data.get("chatData", {})
            conversation_name = tawk_integration.sync_chat_to_unified_inbox(chat_data)
            
            if conversation_name:
                # Sync initial messages
                tawk_integration.sync_messages_to_unified_inbox(conversation_name, chat_data.get("id"))
            
            return {"status": "success", "message": "Chat synced to unified inbox"}
        
        elif event_type == "message:received":
            # New message received
            message_data = data.get("messageData", {})
            chat_id = message_data.get("chatId")
            
            # Find existing conversation
            conversation = frappe.get_all(
                "Unified Inbox Conversation",
                filters={
                    "platform": "Tawk.to",
                    "tawk_to_session_id": chat_id
                },
                limit=1
            )
            
            if conversation:
                tawk_integration.sync_messages_to_unified_inbox(conversation[0].name, chat_id)
            
            return {"status": "success", "message": "Message synced to unified inbox"}
        
        elif event_type == "chat:end":
            # Chat ended
            chat_data = data.get("chatData", {})
            chat_id = chat_data.get("id")
            
            # Update conversation status
            conversation = frappe.get_all(
                "Unified Inbox Conversation",
                filters={
                    "platform": "Tawk.to",
                    "tawk_to_session_id": chat_id
                },
                limit=1
            )
            
            if conversation:
                frappe.db.set_value("Unified Inbox Conversation", conversation[0].name, "status", "Closed")
            
            return {"status": "success", "message": "Chat closed in unified inbox"}
        
        else:
            return {"status": "info", "message": f"Event type {event_type} not handled"}
        
    except Exception as e:
        frappe.log_error(f"Tawk.to webhook error: {str(e)}", "Tawk.to Webhook Error")
        return {"status": "error", "message": "Webhook processing failed"}


@frappe.whitelist()
def sync_all_tawk_to_chats():
    """
    Manual sync of all active Tawk.to chats.
    Can be called from the UI or scheduled as a background job.
    """
    try:
        tawk_integration = TawkToIntegration()
        active_chats = tawk_integration.get_active_chats()
        
        synced_count = 0
        
        for chat_data in active_chats:
            conversation_name = tawk_integration.sync_chat_to_unified_inbox(chat_data)
            
            if conversation_name:
                tawk_integration.sync_messages_to_unified_inbox(conversation_name, chat_data.get("id"))
                synced_count += 1
        
        return {
            "status": "success",
            "message": f"Synced {synced_count} Tawk.to chats to unified inbox",
            "synced_count": synced_count
        }
        
    except Exception as e:
        frappe.log_error(f"Error syncing Tawk.to chats: {str(e)}", "Tawk.to Sync Error")
        return {"status": "error", "message": "Failed to sync Tawk.to chats"}


@frappe.whitelist()
def send_tawk_to_message(conversation_name: str, message: str, agent: str = None):
    """
    Send a message to Tawk.to from the unified inbox.
    """
    try:
        # Get conversation details
        conversation_doc = frappe.get_doc("Unified Inbox Conversation", conversation_name)
        
        if conversation_doc.platform != "Tawk.to":
            return {"status": "error", "message": "Not a Tawk.to conversation"}
        
        tawk_integration = TawkToIntegration()
        
        # Send message to Tawk.to
        success = tawk_integration.send_message(
            conversation_doc.tawk_to_session_id,
            message,
            agent
        )
        
        if success:
            # Create outbound message record
            message_doc = frappe.get_doc({
                "doctype": "Unified Inbox Message",
                "conversation": conversation_name,
                "platform": "Tawk.to",
                "direction": "Outbound",
                "message_type": "text",
                "message_content": message,
                "sender_name": agent or frappe.session.user,
                "sender_id": agent or frappe.session.user,
                "timestamp": now(),
                "handled_by_agent": 1,
                "agent_response": message
            })
            
            message_doc.insert(ignore_permissions=True)
            
            return {"status": "success", "message": "Message sent to Tawk.to"}
        else:
            return {"status": "error", "message": "Failed to send message to Tawk.to"}
        
    except Exception as e:
        frappe.log_error(f"Error sending Tawk.to message: {str(e)}", "Tawk.to Send Error")
        return {"status": "error", "message": "Failed to send message"}
