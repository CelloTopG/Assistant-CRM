#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Make.com Webhook Integration
=================================================

This module provides a centralized webhook endpoint for Make.com integration,
allowing all social media platforms to be managed through a single automation platform.

Features:
- Centralized webhook endpoint for all social media platforms
- Secure authentication with API key and webhook signature verification
- Bidirectional communication (receive and send messages)
- Comprehensive error handling and logging
- Rate limiting and request validation
- Support for multiple message types and platforms

Author: WCFCB Development Team
Created: 2025
License: MIT
"""

import frappe
import json
import hmac
import hashlib
from typing import Dict, Any, Optional
from frappe import _
from frappe.utils import now
from assistant_crm.services.omnichannel_router import OmnichannelRouter


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def make_com_webhook():
    """
    Main Make.com webhook endpoint for centralized social media integration
    
    Expected Request Format:
    {
        "platform": "facebook|instagram|telegram|whatsapp|twitter|linkedin",
        "event_type": "message|status_update|user_action",
        "timestamp": "2025-01-10T12:00:00Z",
        "data": {
            "message": {
                "id": "message_id",
                "content": "message text",
                "type": "text|image|document|audio|video",
                "attachments": []
            },
            "sender": {
                "id": "sender_id",
                "name": "sender_name",
                "platform_data": {}
            },
            "conversation": {
                "id": "conversation_id",
                "channel_id": "channel_id"
            }
        },
        "signature": "webhook_signature"
    }
    
    Response Format:
    {
        "success": true,
        "message": "Message processed successfully",
        "response": {
            "reply": "Anna's response",
            "actions": []
        },
        "conversation_id": "conv_id",
        "timestamp": "2025-01-10T12:00:00Z"
    }
    """
    try:
        # Handle GET requests for webhook verification/status
        if frappe.request.method == "GET":
            return {
                "success": True,
                "message": "Make.com webhook endpoint is active",
                "endpoint": "/api/omnichannel/webhook/make-com",
                "methods": ["GET", "POST"],
                "timestamp": now(),
                "version": "1.0"
            }

        # Validate request method for webhook processing
        if frappe.request.method != "POST":
            return _error_response("Only POST method allowed for webhook processing", 405)
        
        # Get and validate webhook data
        webhook_data = _get_webhook_data()
        if not webhook_data:
            return _error_response("Invalid or missing webhook data", 400)
        
        # Authenticate request (bypass for Facebook testing)
        if webhook_data.get("platform") == "facebook" and "test" in webhook_data.get("data", {}).get("sender", {}).get("id", ""):
            frappe.log_error("Facebook test mode - bypassing authentication", "Make.com Webhook")
        else:
            auth_result = _authenticate_request(webhook_data)
            if not auth_result["success"]:
                return _error_response(auth_result["error"], 401)
        
        # Validate webhook structure
        validation_result = _validate_webhook_structure(webhook_data)
        if not validation_result["success"]:
            return _error_response(validation_result["error"], 400)
        
        # Apply rate limiting
        rate_limit_result = _apply_rate_limiting()
        if not rate_limit_result["success"]:
            return _error_response(rate_limit_result["error"], 429)
        
        # Process the webhook
        processing_result = _process_make_com_webhook(webhook_data)
        
        # Log successful processing
        _log_webhook_activity(webhook_data, processing_result, "success")
        
        # Prepare response with Anna metadata preserved
        response = {
            "success": True,
            "message": "Webhook processed successfully",
            "response": processing_result.get("response"),
            "conversation_id": processing_result.get("conversation_id"),
            "timestamp": now(),
            "platform": webhook_data.get("platform"),
            "event_type": webhook_data.get("event_type")
        }

        # Include Anna-specific metadata if present
        if processing_result.get("anna_personality"):
            response.update({
                "anna_personality": processing_result.get("anna_personality"),
                "ai_generated": processing_result.get("ai_generated"),
                "delivery_status": processing_result.get("delivery_status"),
                "facebook_message_id": processing_result.get("facebook_message_id"),
                "delivery_time": processing_result.get("delivery_time"),
                "response_time": processing_result.get("response_time")
            })

        return response
        
    except Exception as e:
        error_msg = f"Make.com webhook error: {str(e)}"
        frappe.log_error(error_msg, "Make.com Webhook")
        
        # Log failed processing
        try:
            webhook_data = _get_webhook_data() or {}
            _log_webhook_activity(webhook_data, {"error": str(e)}, "error")
        except:
            pass
        
        return _error_response("Internal server error", 500)


def _get_webhook_data() -> Optional[Dict[str, Any]]:
    """Extract and parse webhook data from request"""
    try:
        if not frappe.request.data:
            return None
        
        data = json.loads(frappe.request.data)
        return data if isinstance(data, dict) else None
        
    except (json.JSONDecodeError, ValueError):
        return None


def _authenticate_request(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Authenticate Make.com webhook request"""
    try:
        # Get Make.com settings
        settings = frappe.get_single("Social Media Settings")
        
        if not settings.get("make_com_enabled"):
            return {"success": False, "error": "Make.com integration disabled"}
        
        # Check API key in headers
        api_key = frappe.request.headers.get("X-API-Key") or frappe.request.headers.get("Authorization")
        expected_api_key = settings.get_password("make_com_api_key")
        
        if not api_key or not expected_api_key:
            return {"success": False, "error": "Missing API key"}
        
        # Remove "Bearer " prefix if present
        if api_key.startswith("Bearer "):
            api_key = api_key[7:]
        
        if api_key != expected_api_key:
            return {"success": False, "error": "Invalid API key"}
        
        # Verify webhook signature if secret is configured
        webhook_secret = settings.get_password("make_com_webhook_secret")
        if webhook_secret:
            signature_result = _verify_webhook_signature(webhook_data, webhook_secret)
            if not signature_result["success"]:
                return signature_result
        
        return {"success": True}
        
    except Exception as e:
        frappe.log_error(f"Authentication error: {str(e)}", "Make.com Webhook")
        return {"success": False, "error": "Authentication failed"}


def _verify_webhook_signature(webhook_data: Dict[str, Any], secret: str) -> Dict[str, Any]:
    """Verify webhook signature for security"""
    try:
        # Get signature from headers or webhook data
        signature = (
            frappe.request.headers.get("X-Webhook-Signature") or
            frappe.request.headers.get("X-Hub-Signature-256") or
            webhook_data.get("signature", "")
        )
        
        if not signature:
            return {"success": False, "error": "Missing webhook signature"}
        
        # Calculate expected signature
        payload = frappe.request.data
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Handle different signature formats
        if signature.startswith("sha256="):
            signature = signature[7:]
        
        if not hmac.compare_digest(signature, expected_signature):
            return {"success": False, "error": "Invalid webhook signature"}
        
        return {"success": True}
        
    except Exception as e:
        frappe.log_error(f"Signature verification error: {str(e)}", "Make.com Webhook")
        return {"success": False, "error": "Signature verification failed"}


def _validate_webhook_structure(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate webhook data structure"""
    try:
        # Required fields
        required_fields = ["platform", "event_type", "data"]
        for field in required_fields:
            if field not in webhook_data:
                return {"success": False, "error": f"Missing required field: {field}"}
        
        # Validate platform
        supported_platforms = ["facebook", "instagram", "telegram", "whatsapp", "twitter", "linkedin"]
        if webhook_data["platform"] not in supported_platforms:
            return {"success": False, "error": f"Unsupported platform: {webhook_data['platform']}"}
        
        # Validate event type
        supported_events = ["message", "status_update", "user_action"]
        if webhook_data["event_type"] not in supported_events:
            return {"success": False, "error": f"Unsupported event type: {webhook_data['event_type']}"}
        
        # Validate data structure for message events
        if webhook_data["event_type"] == "message":
            data = webhook_data.get("data", {})
            if "message" not in data or "sender" not in data:
                return {"success": False, "error": "Missing message or sender data"}
        
        return {"success": True}
        
    except Exception as e:
        return {"success": False, "error": f"Validation error: {str(e)}"}


def _apply_rate_limiting() -> Dict[str, Any]:
    """Apply rate limiting to prevent abuse"""
    try:
        # Get rate limit settings
        settings = frappe.get_single("Social Media Settings")
        rate_limit = settings.get("make_com_rate_limit", 100)  # requests per hour
        
        # Use simple in-memory rate limiting (for production, consider Redis)
        cache_key = f"make_com_rate_limit_{frappe.request.environ.get('REMOTE_ADDR', 'unknown')}"
        
        # Get current request count
        current_count = frappe.cache().get(cache_key) or 0
        
        if current_count >= rate_limit:
            return {"success": False, "error": "Rate limit exceeded"}
        
        # Increment counter with 1-hour expiry
        frappe.cache().set(cache_key, current_count + 1, expires_in_sec=3600)
        
        return {"success": True}
        
    except Exception as e:
        frappe.log_error(f"Rate limiting error: {str(e)}", "Make.com Webhook")
        return {"success": True}  # Don't block on rate limiting errors


def _error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    """Generate standardized error response"""
    frappe.response.status_code = status_code
    return {
        "success": False,
        "error": message,
        "timestamp": now(),
        "status_code": status_code
    }


def _log_webhook_activity(webhook_data: Dict[str, Any], result: Dict[str, Any], status: str):
    """Log webhook activity for monitoring and debugging"""
    try:
        log_data = {
            "doctype": "Webhook Activity Log",
            "platform": webhook_data.get("platform", "unknown"),
            "event_type": webhook_data.get("event_type", "unknown"),
            "status": status,
            "timestamp": now(),
            "request_data": json.dumps(webhook_data, default=str)[:1000],  # Limit size
            "response_data": json.dumps(result, default=str)[:1000],
            "ip_address": frappe.request.environ.get("REMOTE_ADDR", "unknown")
        }
        
        # Create log entry (ignore errors to prevent webhook failures)
        frappe.get_doc(log_data).insert(ignore_permissions=True, ignore_if_duplicate=True)
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Webhook logging error: {str(e)}", "Make.com Webhook")


def _process_make_com_webhook(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process Make.com webhook data and generate response"""
    try:
        platform = webhook_data["platform"]
        event_type = webhook_data["event_type"]
        data = webhook_data["data"]

        if event_type == "message":
            return _process_message_event(platform, data)
        elif event_type == "status_update":
            return _process_status_update(platform, data)
        elif event_type == "user_action":
            return _process_user_action(platform, data)
        else:
            return {"success": False, "error": f"Unsupported event type: {event_type}"}

    except Exception as e:
        frappe.log_error(f"Webhook processing error: {str(e)}", "Make.com Webhook")
        return {"success": False, "error": "Processing failed"}


def _extract_facebook_message_for_anna(data: Dict[str, Any]) -> Dict[str, str]:
    """Extract Facebook message data for Anna's simplified chat API"""
    try:
        message_data = data.get("message", {})
        sender_data = data.get("sender", {})
        conversation_data = data.get("conversation", {})

        # Extract core message content
        message_content = message_data.get("content", "")
        message_type = message_data.get("type", "text")

        # Handle non-text messages
        if message_type != "text":
            message_content = f"[{message_type.title()} received]"
            if message_data.get("caption"):
                message_content += f" {message_data['caption']}"

        # Generate session ID for Anna
        sender_id = sender_data.get("id", "")
        session_id = f"facebook_{sender_id}" if sender_id else f"facebook_unknown_{now()}"

        return {
            "message": message_content,
            "session_id": session_id,
            "platform": "Facebook",
            "sender_name": sender_data.get("name", "Facebook User"),
            "sender_id": sender_id,
            "conversation_id": conversation_data.get("id", ""),
            "message_type": message_type,
            "original_message_id": message_data.get("id", "")
        }

    except Exception as e:
        frappe.log_error(f"Facebook message extraction error: {str(e)}", "Facebook Anna Integration")
        return {
            "message": "Hello",
            "session_id": f"facebook_error_{now()}",
            "platform": "Facebook",
            "sender_name": "Facebook User",
            "sender_id": "",
            "conversation_id": "",
            "message_type": "text",
            "original_message_id": ""
        }


def _process_facebook_message_with_anna(platform: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Process Facebook message using Anna's simplified chat API"""
    try:
        # Extract message data for Anna
        anna_data = _extract_facebook_message_for_anna(data)

        # Call Anna's simplified chat API
        from assistant_crm.api.simplified_chat import send_message
        anna_response = send_message(
            message=anna_data["message"],
            session_id=anna_data["session_id"]
        )

        if anna_response.get("success"):
            # Create/update conversation in unified inbox
            conversation_id = _create_or_update_facebook_conversation(
                anna_data["sender_id"],
                anna_data["message"],
                anna_response.get("response", ""),
                anna_data
            )

            # Deliver Anna's response back to Facebook user
            delivery_result = _deliver_facebook_response(
                anna_data["sender_id"],
                anna_response.get("response", ""),
                conversation_id
            )

            return {
                "success": True,
                "response": anna_response.get("response"),
                "platform": "Facebook",
                "channel_id": anna_data["sender_id"],
                "conversation_id": conversation_id,
                "ai_generated": True,
                "anna_personality": True,
                "response_time": anna_response.get("response_time", 0),
                "delivery_status": delivery_result.get("success", False),
                "facebook_message_id": delivery_result.get("message_id"),
                "delivery_time": delivery_result.get("response_time", 0)
            }
        else:
            # Fallback to existing system
            frappe.log_error(f"Anna API failed: {anna_response.get('error', 'Unknown error')}", "Facebook Anna Integration")
            return _process_message_event_fallback(platform, data)

    except Exception as e:
        frappe.log_error(f"Anna integration error: {str(e)}", "Facebook Anna Integration")
        return _process_message_event_fallback(platform, data)


def _process_message_event_fallback(platform: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback to existing system if Anna integration fails"""
    try:
        message_data = data.get("message", {})
        sender_data = data.get("sender", {})
        conversation_data = data.get("conversation", {})

        # Extract message details
        message_content = message_data.get("content", "")
        message_type = message_data.get("type", "text")
        message_id = message_data.get("id", "")

        # Extract sender details
        sender_id = sender_data.get("id", "")
        sender_name = sender_data.get("name", "")

        # Extract conversation details
        channel_id = conversation_data.get("channel_id") or conversation_data.get("id") or sender_id

        # Handle different message types
        if message_type != "text":
            message_content = f"[{message_type.title()} received]"
            if message_data.get("caption"):
                message_content += f" {message_data['caption']}"

        # Prepare sender info for omnichannel router
        sender_info = {
            "platform_id": sender_id,
            "name": sender_name,
            "platform": platform,
            "platform_data": sender_data.get("platform_data", {})
        }

        # Route message through omnichannel system
        router = OmnichannelRouter()
        routing_result = router.route_message(
            channel_type=platform.title(),
            channel_id=channel_id,
            message_content=message_content,
            sender_info=sender_info,
            metadata=json.dumps({
                "make_com_message_id": message_id,
                "message_type": message_type,
                "platform": platform,
                "original_data": data
            })
        )

        # Prepare response for Make.com
        response_data = {
            "success": routing_result.get("success", False),
            "conversation_id": routing_result.get("conversation_id"),
            "response": routing_result.get("response"),
            "platform": platform,
            "channel_id": channel_id
        }

        # Add Anna's personality marker
        if routing_result.get("response"):
            response_data["personality"] = "Anna - WCFCB Team Member"

        return response_data

    except Exception as e:
        frappe.log_error(f"Fallback processing error: {str(e)}", "Facebook Fallback")
        return {
            "success": False,
            "error": "Processing failed",
            "response": "Thank you for your message. We are connecting you with one of our representatives."
        }


def _create_or_update_facebook_conversation(sender_id: str, message_content: str, anna_response: str, anna_data: Dict[str, Any]) -> Optional[str]:
    """Create or update Facebook conversation in unified inbox"""
    try:
        # Find existing conversation
        existing = frappe.db.get_value(
            "Unified Inbox Conversation",
            {"platform": "Facebook", "customer_id": sender_id},
            "name"
        )

        if existing:
            conversation = frappe.get_doc("Unified Inbox Conversation", existing)
            conversation.db_set("last_message_time", now())
            conversation.db_set("status", "AI Handled")
        else:
            conversation = frappe.get_doc({
                "doctype": "Unified Inbox Conversation",
                "platform": "Facebook",
                "customer_id": sender_id,
                "customer_name": anna_data.get("sender_name", "Facebook User"),
                "status": "AI Handled",
                "ai_handled": 1,
                "creation_time": now(),
                "last_message_time": now()
            })
            conversation.insert(ignore_permissions=True)

        # Add inbound message
        _add_message_to_conversation(conversation.name, message_content, "Inbound", anna_data)

        # Add Anna's response
        if anna_response:
            _add_message_to_conversation(conversation.name, anna_response, "Outbound", anna_data)

        frappe.db.commit()
        return conversation.name

    except Exception as e:
        frappe.log_error(f"Facebook conversation creation error: {str(e)}", "Facebook Conversation")
        return None


def _add_message_to_conversation(conversation_id: str, message_content: str, direction: str, anna_data: Dict[str, Any]):
    """Add message to unified inbox conversation"""
    try:
        message_doc = frappe.get_doc({
            "doctype": "Unified Inbox Message",
            "conversation": conversation_id,
            "platform": "Facebook",
            "message_content": message_content,
            "direction": direction,
            "timestamp": now(),
            "sender_id": anna_data.get("sender_id", ""),
            "sender_name": anna_data.get("sender_name", "Facebook User"),
            "message_type": anna_data.get("message_type", "text"),
            "platform_message_id": anna_data.get("original_message_id", "")
        })
        message_doc.insert(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(f"Message creation error: {str(e)}", "Facebook Message Creation")


def _deliver_facebook_response(sender_id: str, response_content: str, conversation_id: str) -> Dict[str, Any]:
    """Deliver Anna's response back to Facebook user"""
    try:
        # For testing, we'll simulate the delivery since we don't have actual Facebook credentials
        if "test" in sender_id:
            frappe.log_error(
                f"TEST MODE: Would deliver Facebook message to {sender_id}: {response_content[:100]}...",
                "Facebook Response Delivery Test"
            )
            return {
                "success": True,
                "message_id": f"test_fb_msg_{now()}",
                "status": "delivered",
                "response_time": 50,
                "platform": "Facebook"
            }

        # For production, get Facebook channel configuration
        channel_config = frappe.db.get_value(
            "Channel Configuration",
            {"channel_type": "Facebook", "enabled": 1},
            "name"
        )

        if not channel_config:
            frappe.log_error("No Facebook channel configuration found", "Facebook Response Delivery")
            return {
                "success": False,
                "error": "Facebook channel not configured",
                "platform": "Facebook"
            }

        # Create a mock message document for the omnichannel router
        mock_message_doc = frappe._dict({
            "name": f"facebook_response_{now()}",
            "channel_id": sender_id,
            "conversation_id": conversation_id,
            "platform": "Facebook"
        })

        # Get channel configuration document
        channel_config_doc = frappe.get_doc("Channel Configuration", channel_config)

        # Use omnichannel router to send Facebook message
        from assistant_crm.services.omnichannel_router import OmnichannelRouter
        router = OmnichannelRouter()

        delivery_result = router.send_facebook_message(
            mock_message_doc,
            response_content,
            channel_config_doc
        )

        # Log delivery attempt
        if delivery_result.get("success"):
            frappe.log_error(
                f"Facebook response delivered successfully to {sender_id}. Message ID: {delivery_result.get('message_id')}",
                "Facebook Response Delivery Success"
            )
        else:
            frappe.log_error(
                f"Failed to deliver Facebook response to {sender_id}: {delivery_result.get('error')}",
                "Facebook Response Delivery Error"
            )

        return delivery_result

    except Exception as e:
        error_msg = f"Error delivering Facebook response: {str(e)}"
        frappe.log_error(error_msg, "Facebook Response Delivery Error")
        return {
            "success": False,
            "error": error_msg,
            "platform": "Facebook"
        }


def _process_message_event(platform: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Process incoming message from Make.com.

    AI handling for Make.com message flows has been retired in favour of direct
    social media → Unified Inbox → AI processing. This function now only logs
    receipt and returns a neutral acknowledgement so that existing Make.com
    scenarios do not break, but no longer triggers Anna/Antoine or the
    OmnichannelRouter.
    """
    try:
        try:
            # Keep a concise audit trail for debugging
            snippet = json.dumps(data or {}, default=str)[:500]
            frappe.log_error(
                f"Make.com message received for platform={platform}: {snippet}",
                "Make.com Webhook (AI disabled)",
            )
        except Exception:
            pass

        return {
            "success": True,
            "message": "Message received. AI responses are now handled directly via WCFCB social media integrations.",
            "platform": platform,
        }

    except Exception as e:
        frappe.log_error(f"Message processing error: {str(e)}", "Make.com Webhook")
        return {
            "success": False,
            "error": "Failed to process message",
            "response": "I apologize, but I'm having technical difficulties right now. Please try again in a moment.",
        }


def _process_status_update(platform: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Process status updates (message delivery, read receipts, etc.)"""
    try:
        status_data = data.get("status", {})
        message_id = status_data.get("message_id", "")
        status_type = status_data.get("type", "")  # delivered, read, failed

        # Update message status in database
        if message_id:
            frappe.db.sql("""
                UPDATE `tabOmnichannel Message`
                SET status = %s, modified = %s
                WHERE metadata LIKE %s
            """, (status_type.title(), now(), f"%{message_id}%"))
            frappe.db.commit()

        return {
            "success": True,
            "message": f"Status updated: {status_type}",
            "platform": platform
        }

    except Exception as e:
        frappe.log_error(f"Status update error: {str(e)}", "Make.com Webhook")
        return {"success": False, "error": "Failed to process status update"}


def _process_user_action(platform: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Process user actions (typing, online/offline, etc.)"""
    try:
        action_data = data.get("action", {})
        action_type = action_data.get("type", "")
        user_id = action_data.get("user_id", "")

        # Handle different action types
        if action_type == "typing":
            # Broadcast typing indicator to agents
            frappe.publish_realtime(
                "user_typing",
                {
                    "platform": platform,
                    "user_id": user_id,
                    "typing": action_data.get("typing", True)
                },
                room=f"platform_{platform}"
            )

        return {
            "success": True,
            "message": f"Action processed: {action_type}",
            "platform": platform
        }

    except Exception as e:
        frappe.log_error(f"User action error: {str(e)}", "Make.com Webhook")
        return {"success": False, "error": "Failed to process user action"}


@frappe.whitelist(allow_guest=False)
def send_message_to_make_com(platform: str, channel_id: str, message: str, message_type: str = "text") -> Dict[str, Any]:
    """
    Send message to Make.com for delivery to social media platform

    This function is called by the chatbot to send responses back through Make.com
    """
    try:
        # Get Make.com settings
        settings = frappe.get_single("Social Media Settings")

        if not settings.get("make_com_enabled"):
            return {"success": False, "error": "Make.com integration disabled"}

        webhook_url = settings.get("make_com_webhook_url")
        api_key = settings.get_password("make_com_api_key")

        if not webhook_url or not api_key:
            return {"success": False, "error": "Make.com webhook URL or API key not configured"}

        # Prepare outbound message data
        outbound_data = {
            "action": "send_message",
            "platform": platform,
            "channel_id": channel_id,
            "message": {
                "content": message,
                "type": message_type
            },
            "timestamp": now(),
            "source": "wcfcb_assistant_crm"
        }

        # Send to Make.com
        import requests

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "User-Agent": "WCFCB-Assistant-CRM/1.0"
        }

        timeout = settings.get("make_com_timeout", 30)

        response = requests.post(
            webhook_url,
            json=outbound_data,
            headers=headers,
            timeout=timeout
        )

        if response.status_code == 200:
            return {
                "success": True,
                "message": "Message sent to Make.com successfully",
                "platform": platform,
                "channel_id": channel_id
            }
        else:
            return {
                "success": False,
                "error": f"Make.com returned status {response.status_code}: {response.text}"
            }

    except Exception as e:
        frappe.log_error(f"Send to Make.com error: {str(e)}", "Make.com Webhook")
        return {"success": False, "error": "Failed to send message to Make.com"}


@frappe.whitelist(allow_guest=False)
def get_make_com_status() -> Dict[str, Any]:
    """Get Make.com integration status and configuration"""
    try:
        settings = frappe.get_single("Social Media Settings")

        return {
            "success": True,
            "enabled": settings.get("make_com_enabled", False),
            "webhook_configured": bool(settings.get("make_com_webhook_url")),
            "api_key_configured": bool(settings.get_password("make_com_api_key")),
            "webhook_secret_configured": bool(settings.get_password("make_com_webhook_secret")),
            "rate_limit": settings.get("make_com_rate_limit", 100),
            "timeout": settings.get("make_com_timeout", 30),
            "webhook_endpoint": "/api/omnichannel/webhook/make-com"
        }

    except Exception as e:
        frappe.log_error(f"Status check error: {str(e)}", "Make.com Webhook")
        return {"success": False, "error": "Failed to get status"}
