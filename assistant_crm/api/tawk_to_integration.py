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
from frappe.utils import now
from typing import Dict, Any, Optional, List
import hashlib
import hmac


# Tawk.to API base URL (not a secret — safe as a constant)
TAWK_TO_BASE_URL = "https://api.tawk.to/v3"


class TawkToIntegration:
    """
    Main class for Tawk.to integration with unified inbox system.
    """
    
    def __init__(self):
        settings = frappe.get_single("Social Media Settings")
        self.api_key = settings.get_password("tawk_to_api_key")
        self.property_id = settings.tawk_to_property_id
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

    Official Tawk.to events (https://developer.tawk.to/webhooks/):
      chat:start              — first message sent in a chat session
      chat:end                — chat session ended by visitor or agent
      chat:transcript_created — full transcript delivered after chat ends
      ticket:create           — new support ticket submitted

    Signature: HMAC-SHA1 of raw request body, delivered in X-Tawk-Signature header.
    """
    try:
        raw_body = frappe.request.get_data()
        if not raw_body:
            return {"status": "error", "message": "No webhook data received"}

        # Verify HMAC-SHA1 signature when Tawk.to sends it.
        # Tawk.to only includes X-Tawk-Signature when a secret is configured on their dashboard.
        signature = frappe.request.headers.get("X-Tawk-Signature")
        if signature:
            settings = frappe.get_single("Social Media Settings")
            secret = settings.get_password("tawk_to_webhook_secret") if settings.get("tawk_to_webhook_secret") else None
            if secret:
                expected = hmac.new(
                    secret.encode("utf-8"), raw_body, hashlib.sha1
                ).hexdigest()
                if not hmac.compare_digest(signature, expected):
                    frappe.log_error("Tawk.to webhook signature mismatch", "Tawk.to Webhook")
                    frappe.response["http_status_code"] = 401
                    return {"status": "error", "message": "Invalid signature"}

        data = json.loads(raw_body.decode("utf-8"))
        event_type = data.get("event")

        if event_type == "chat:start":
            return _handle_chat_start(data)
        elif event_type == "chat:end":
            return _handle_chat_end(data)
        elif event_type == "chat:transcript_created":
            return _handle_transcript_created(data)
        elif event_type == "ticket:create":
            return _handle_ticket_create(data)
        else:
            return {"status": "info", "message": f"Event type '{event_type}' not handled"}

    except Exception as e:
        frappe.log_error(f"Tawk.to webhook error: {str(e)}", "Tawk.to Webhook Error")
        return {"status": "error", "message": "Webhook processing failed"}


def _build_customer_name(visitor: Dict[str, Any]) -> str:
    """Derive a readable name from a Tawk.to visitor object.

    Auto-generated visitor IDs (e.g. 'V1561719148780935') are discarded and the
    email address is used as a fallback so agents always see something meaningful.
    """
    name = visitor.get("name", "")
    email = visitor.get("email", "")
    if name.startswith("V") and name[1:].isdigit():
        name = ""
    if name and email:
        return f"{name} ({email})"
    if email:
        return f"{email.split('@')[0].replace('.', ' ').title()} ({email})"
    return name or "Tawk.to Visitor"


def _normalize_iso_timestamp(ts: str) -> str:
    """Convert an ISO 8601 timestamp ('2019-06-28T14:03:04.646Z') to
    Frappe's expected datetime string ('2019-06-28 14:03:04')."""
    try:
        if not ts:
            return now()
        return str(ts).replace("Z", "").split(".")[0].replace("T", " ")
    except Exception:
        return now()


def _handle_chat_start(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    chat:start payload fields (all at root level):
      chatId, time, message: {text, type, sender: {type}},
      visitor: {name, email, city, country}, property: {id, name}
    """
    chat_id = data.get("chatId")
    if not chat_id:
        return {"status": "error", "message": "Missing chatId in chat:start event"}

    visitor = data.get("visitor") or {}
    message = data.get("message") or {}
    property_data = data.get("property") or {}
    customer_name = _build_customer_name(visitor)
    message_content = message.get("text") or "[Media message]"
    timestamp = _normalize_iso_timestamp(data.get("time"))

    # Idempotency: skip if a conversation for this chat already exists
    existing = frappe.db.get_value(
        "Unified Inbox Conversation",
        {"platform_specific_id": chat_id, "platform": "Tawk.to"},
        "name"
    )
    if existing:
        return {"status": "success", "message": "Conversation already exists", "conversation": existing}

    conversation_doc = frappe.get_doc({
        "doctype": "Unified Inbox Conversation",
        "platform": "Tawk.to",
        "platform_specific_id": chat_id,
        "customer_name": customer_name,
        "customer_email": visitor.get("email"),
        "customer_platform_id": chat_id,
        "status": "Agent Assigned",
        "priority": "Medium",
        "creation_time": timestamp,
        "platform_metadata": json.dumps({
            "visitor": visitor,
            "property": property_data,
        }),
    })
    conversation_doc.insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "Unified Inbox Message",
        "conversation": conversation_doc.name,
        "platform": "Tawk.to",
        "direction": "Inbound",
        "message_type": message.get("type", "text"),
        "message_content": message_content,
        "sender_name": customer_name,
        "sender_id": chat_id,
        "timestamp": timestamp,
        "platform_message_id": f"tawk:start:{chat_id}",
        "handled_by_agent": 0,
    }).insert(ignore_permissions=True)

    return {
        "status": "success",
        "message": "Chat synced to unified inbox",
        "conversation": conversation_doc.name,
    }


def _handle_chat_end(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    chat:end payload fields (all at root level):
      chatId, time, visitor: {name, email, city, country}, property: {id, name}
    """
    chat_id = data.get("chatId")
    if not chat_id:
        return {"status": "error", "message": "Missing chatId in chat:end event"}

    conversation_name = frappe.db.get_value(
        "Unified Inbox Conversation",
        {"platform_specific_id": chat_id, "platform": "Tawk.to"},
        "name"
    )
    if conversation_name:
        frappe.db.set_value("Unified Inbox Conversation", conversation_name, "status", "Resolved")
        return {"status": "success", "message": "Chat marked as Resolved", "conversation": conversation_name}

    return {"status": "info", "message": "No conversation found for this chat"}


def _handle_transcript_created(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    chat:transcript_created payload:
      event, time, property: {id, name},
      chat: {
        id, visitor: {name, email, city, country},
        messages: [{sender: {t, n, id}, type, msg, time, attchs}, ...]
      }

    Ingests the full transcript. If the conversation was already created by
    chat:start/chat:end, messages are appended; otherwise the conversation is
    created here. Duplicate messages are skipped via platform_message_id.
    """
    chat_obj = data.get("chat") or {}
    chat_id = chat_obj.get("id")
    if not chat_id:
        return {"status": "error", "message": "Missing chat.id in transcript event"}

    visitor = chat_obj.get("visitor") or {}
    messages = chat_obj.get("messages") or []
    property_data = data.get("property") or {}
    customer_name = _build_customer_name(visitor)

    # Find or create conversation
    conversation_name = frappe.db.get_value(
        "Unified Inbox Conversation",
        {"platform_specific_id": chat_id, "platform": "Tawk.to"},
        "name"
    )
    if not conversation_name:
        conversation_doc = frappe.get_doc({
            "doctype": "Unified Inbox Conversation",
            "platform": "Tawk.to",
            "platform_specific_id": chat_id,
            "customer_name": customer_name,
            "customer_email": visitor.get("email"),
            "customer_platform_id": chat_id,
            "status": "Resolved",
            "priority": "Medium",
            "creation_time": _normalize_iso_timestamp(data.get("time")),
            "platform_metadata": json.dumps({
                "visitor": visitor,
                "property": property_data,
            }),
        })
        conversation_doc.insert(ignore_permissions=True)
        conversation_name = conversation_doc.name

    ingested = 0
    for idx, msg in enumerate(messages):
        sender = msg.get("sender") or {}
        sender_type = (sender.get("t") or "").lower()  # v=visitor, a=agent, s=system
        direction = "Inbound" if sender_type == "v" else "Outbound"
        sender_name = sender.get("n") or (customer_name if sender_type == "v" else "Agent")
        content = msg.get("msg") or ("[Attachment]" if msg.get("attchs") else "")
        timestamp = _normalize_iso_timestamp(msg.get("time"))
        message_id = f"tawk:transcript:{chat_id}:{idx}"

        if frappe.db.exists("Unified Inbox Message", {"platform_message_id": message_id}):
            continue

        frappe.get_doc({
            "doctype": "Unified Inbox Message",
            "conversation": conversation_name,
            "platform": "Tawk.to",
            "direction": direction,
            "message_type": "text" if (msg.get("type") or "").lower() in ["msg", "text"] else (msg.get("type") or "text"),
            "message_content": content,
            "sender_name": sender_name,
            "sender_id": sender.get("id") or chat_id,
            "timestamp": timestamp,
            "platform_message_id": message_id,
            "platform_metadata": json.dumps(msg),
            "handled_by_agent": 0 if sender_type == "v" else 1,
        }).insert(ignore_permissions=True)
        ingested += 1

    return {
        "status": "success",
        "message": f"Transcript ingested ({ingested} new messages)",
        "conversation": conversation_name,
    }


def _handle_ticket_create(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ticket:create payload:
      event, time, property: {id, name},
      requester: {name, email},
      ticket: {id, humanId, subject, message}

    Note: tickets do NOT have a chatId — they use ticket.id as the identifier.
    """
    ticket = data.get("ticket") or {}
    requester = data.get("requester") or {}
    property_data = data.get("property") or {}

    ticket_id = ticket.get("id")
    if not ticket_id:
        return {"status": "error", "message": "Missing ticket.id in ticket:create event"}

    platform_specific_id = f"ticket:{ticket_id}"

    existing = frappe.db.get_value(
        "Unified Inbox Conversation",
        {"platform_specific_id": platform_specific_id, "platform": "Tawk.to"},
        "name"
    )
    if existing:
        return {"status": "success", "message": "Ticket conversation already exists", "conversation": existing}

    requester_name = requester.get("name") or "Tawk.to Visitor"
    requester_email = requester.get("email")
    human_id = ticket.get("humanId")
    subject = ticket.get("subject") or "New Ticket"
    body = ticket.get("message") or ""
    ticket_label = f"[Ticket #{human_id}]" if human_id else "[Ticket]"
    content = f"{ticket_label} {subject}"
    if body:
        content += f"\n{body}"
    timestamp = _normalize_iso_timestamp(data.get("time"))

    conversation_doc = frappe.get_doc({
        "doctype": "Unified Inbox Conversation",
        "platform": "Tawk.to",
        "platform_specific_id": platform_specific_id,
        "customer_name": requester_name,
        "customer_email": requester_email,
        "customer_platform_id": ticket_id,
        "status": "Open",
        "priority": "Medium",
        "creation_time": timestamp,
        "platform_metadata": json.dumps({
            "ticket": ticket,
            "requester": requester,
            "property": property_data,
        }),
    })
    conversation_doc.insert(ignore_permissions=True)

    frappe.get_doc({
        "doctype": "Unified Inbox Message",
        "conversation": conversation_doc.name,
        "platform": "Tawk.to",
        "direction": "Inbound",
        "message_type": "text",
        "message_content": content,
        "sender_name": requester_name,
        "sender_id": ticket_id,
        "timestamp": timestamp,
        "platform_message_id": f"ticket:{ticket_id}",
        "handled_by_agent": 0,
    }).insert(ignore_permissions=True)

    return {
        "status": "success",
        "message": "Ticket created in unified inbox",
        "conversation": conversation_doc.name,
    }


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
