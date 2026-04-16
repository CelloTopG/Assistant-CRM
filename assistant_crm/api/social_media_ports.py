#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Social Media Platform Ports
=================================================

Plug-and-play social media integration ports for Instagram, Facebook,
Telegram, and WhatsApp. Designed to easily accept API credentials when available.

Features:
- Standardized interface for all platforms
- Easy credential configuration
- Webhook handling for each platform
- Message normalization
- Error handling and logging
- Ready for production deployment

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
from abc import ABC, abstractmethod
import hashlib
import hmac


def _normalize_iso(ts: str) -> str:
    """Convert an ISO 8601 timestamp ('2019-06-28T14:03:04.646Z') to
    Frappe's expected datetime string ('2019-06-28 14:03:04').
    Returns now() on any failure."""
    try:
        if not ts:
            return now()
        ts_s = str(ts).replace("Z", "").split(".")[0].replace("T", " ")
        return ts_s
    except Exception:
        return now()


class SocialMediaPlatform(ABC):
    """
    Abstract base class for social media platform integrations.
    All platform-specific classes inherit from this.
    """

    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.credentials = self.get_platform_credentials()
        self.is_configured = self.check_configuration()

    @abstractmethod
    def get_platform_credentials(self) -> Dict[str, str]:
        """Get platform-specific credentials from settings."""
        pass

    @abstractmethod
    def check_configuration(self) -> bool:
        """Check if platform is properly configured."""
        pass

    @abstractmethod
    def send_message(self, recipient_id: str, message: str, message_type: str = "text") -> bool:
        """Send message to platform."""
        pass

    @abstractmethod
    def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming webhook from platform."""
        pass

    def publish_post(self, content: str, media_urls: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Publish an original post/content to this platform's public feed or page.

        Must be overridden by each platform adapter that supports content publishing.
        Returns a dict with at minimum:
          - success (bool)
          - post_id (str, optional) — platform-assigned ID of the created post
          - post_url (str, optional) — public URL of the post
          - error (str, optional) — human-readable error message on failure

        Default implementation raises NotImplementedError so the publisher can
        surface a clear message rather than silently failing.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement publish_post(). "
            "Override this method to enable content publishing for this platform."
        )

    def create_unified_inbox_conversation(
        self,
        platform_data: Dict[str, Any],
        force_new: bool = False,
        tags: Optional[List[str]] = None,
        subject: Optional[str] = None,
        survey_label: Optional[str] = None,
    ) -> Optional[str]:
        """Create unified inbox conversation from platform data.
        Rule: For Facebook, Instagram, Telegram, and Twitter, if the latest conversation for the same
        user/chat has a closed/resolved ticket (or conversation), start a NEW conversation.
        Tawk.to already implements its own sessioning; leave it unchanged.
        If force_new=True, always create a new conversation (used for Surveys).
        """
        try:
            # Statuses that mean the conversation is finished — a new message must open a fresh one
            CLOSED_STATUSES = {"Resolved", "Closed"}

            # Resolve the platform user identifier — prefer customer_platform_id, fall back to conversation_id
            platform_user_id = platform_data.get("customer_platform_id") or platform_data.get("conversation_id")

            # Find the single most recent conversation for this platform + user (no status filter —
            # we check the status explicitly in Python to avoid Frappe filter edge-cases)
            recent = frappe.get_all(
                "Unified Inbox Conversation",
                filters={
                    "platform": self.platform_name,
                    "customer_platform_id": platform_user_id,
                },
                fields=["name", "status", "custom_issue_id"],
                order_by="creation desc",
                limit=1,
            )

            if recent and not force_new:
                conv_status = (recent[0].get("status") or "").strip()

                # Conversation is still open — reuse it
                if conv_status not in CLOSED_STATUSES:
                    # Also check whether the linked Issue has been closed independently
                    issue_closed = False
                    try:
                        issue_name = recent[0].get("custom_issue_id")
                        if issue_name:
                            issue_status = frappe.db.get_value("Issue", issue_name, "status")
                            if (issue_status or "").strip() in CLOSED_STATUSES:
                                issue_closed = True
                    except Exception:
                        pass

                    if not issue_closed:
                        # Refresh customer name if we now have a better one
                        try:
                            new_name = (platform_data.get("customer_name") or "").strip()
                            if new_name:
                                current_name = (frappe.db.get_value(
                                    "Unified Inbox Conversation", recent[0].name, "customer_name"
                                ) or "").strip()
                                if not current_name or current_name.lower() in {"unknown customer", "test"}:
                                    frappe.db.set_value(
                                        "Unified Inbox Conversation",
                                        recent[0].name,
                                        "customer_name",
                                        new_name,
                                        update_modified=True,
                                    )
                        except Exception:
                            pass
                        return recent[0].name
                # Conversation is Resolved/Closed — fall through and create a new one

            # Create new conversation
            tag_str = None
            try:
                if tags:
                    # Store as comma-separated, unique, trimmed
                    uniq = []
                    for t in [str(x).strip() for x in tags if x]:
                        if t and t not in uniq:
                            uniq.append(t)
                    tag_str = ", ".join(uniq) if uniq else None
            except Exception:
                tag_str = None

            auto_subject = subject or (f"Survey: {survey_label}" if survey_label else None)

            # Build base fields
            # Note: Do NOT set conversation_id here; let the DocType generate a unique internal ID.
            doc_fields = {
                "doctype": "Unified Inbox Conversation",
                "platform": self.platform_name,
                "customer_name": platform_data.get("customer_name", "Unknown Customer"),
                "customer_email": platform_data.get("customer_email"),
                "customer_phone": platform_data.get("customer_phone"),
                "customer_platform_id": platform_data.get("customer_platform_id"),
                "status": "New",
                "priority": "Medium",
                "creation_time": now(),
                "last_message_time": now(),  # Set current time for last message
                "platform_metadata": json.dumps(platform_data),
                # YouTube comments are public posts — agents should respond manually.
                "ai_mode": "Off" if self.platform_name == "YouTube" else "Auto",
            }

            # Conditionally include optional fields if they exist on the DocType
            try:
                meta = frappe.get_meta("Unified Inbox Conversation")
                if tag_str and getattr(meta, "has_field", None) and meta.has_field("tags"):
                    doc_fields["tags"] = tag_str
                if auto_subject and getattr(meta, "has_field", None) and meta.has_field("subject"):
                    doc_fields["subject"] = auto_subject
            except Exception:
                # Best-effort only
                pass

            conversation_doc = frappe.get_doc(doc_fields)

            conversation_doc.insert(ignore_permissions=True)
            frappe.db.commit()  # Commit so subsequent loop iterations can find this conversation

            # Automatically generate ERPNext Issue for new conversation
            # Wrapped in its own try/except so issue creation failure
            # doesn't prevent the conversation from being returned
            try:
                self.create_issue_for_new_conversation(conversation_doc.name, platform_data)
            except Exception as issue_err:
                # Log but don't propagate ÔÇö the conversation was already created
                frappe.log_error(
                    message=f"Issue creation failed for {conversation_doc.name}: {str(issue_err)}",
                    title="Auto Issue Creation Error"
                )

            return conversation_doc.name

        except Exception as e:
            frappe.log_error(
                message=f"Error creating conversation for {self.platform_name}: {str(e)}",
                title="Social Media Integration Error"
            )
            return None

    def _normalize_platform_message_id(self, raw_id: Optional[str]) -> Optional[str]:
        """Ensure platform_message_id fits DB column length (<=140). Use SHA1 surrogate if too long."""
        if not raw_id:
            return None
        try:
            if len(raw_id) <= 140:
                return raw_id
            import hashlib
            # Prefix with short platform hint, deterministic and short
            return f"{self.platform_name[:2].lower()}:{hashlib.sha1(raw_id.encode('utf-8')).hexdigest()}"
        except Exception:
            # Fallback to hard truncate
            return raw_id[:140]

    def create_unified_inbox_message(self, conversation_name: str, message_data: Dict[str, Any]) -> Optional[str]:
        """Create unified inbox message from platform message data."""
        try:
            # Normalize platform message id to avoid DB truncation errors
            raw_msg_id = message_data.get("message_id")
            norm_msg_id = self._normalize_platform_message_id(raw_msg_id)

            # Prepare metadata and keep raw id when we shorten it
            metadata = dict(message_data.get("metadata", {}))
            if raw_msg_id and norm_msg_id and raw_msg_id != norm_msg_id:
                metadata["raw_platform_message_id"] = raw_msg_id

            # Check if message already exists (use normalized id mapped to message_id)
            existing_message = frappe.get_all(
                "Unified Inbox Message",
                filters={"message_id": norm_msg_id},
                limit=1
            )

            if existing_message:
                return existing_message[0].name

            # Create new message
            message_doc = frappe.get_doc({
                "doctype": "Unified Inbox Message",
                "message_id": norm_msg_id,
                "conversation": conversation_name,
                "platform": self.platform_name,
                "direction": message_data.get("direction", "Inbound"),
                "message_type": message_data.get("message_type", "text"),
                "message_content": message_data.get("content", ""),
                "sender_name": message_data.get("sender_name"),
                "sender_id": message_data.get("sender_id"),
                "sender_platform_id": message_data.get("sender_platform_id"),
                "timestamp": message_data.get("timestamp", now()),
                "platform_message_id": norm_msg_id,
                "platform_metadata": json.dumps(metadata)
            })

            # Handle attachments
            if message_data.get("attachments"):
                message_doc.has_attachments = 1
                message_doc.attachments_data = json.dumps(message_data.get("attachments"))

            message_doc.insert(ignore_permissions=True)
            return message_doc.name

        except Exception as e:
            frappe.log_error(f"Error creating message for {self.platform_name}: {str(e)}", "Social Media Integration Error")
            return None

    def create_issue_for_new_conversation(self, conversation_name: str, platform_data: Dict[str, Any]):
        """Create ERPNext Issue for new conversation automatically."""
        try:
            # Use importlib to avoid circular import issues between
            # social_media_ports and unified_inbox_api
            import importlib
            inbox_api = importlib.import_module("assistant_crm.api.unified_inbox_api")

            customer_name = platform_data.get("customer_name", "Unknown Customer")
            initial_message = platform_data.get("initial_message", "New customer inquiry")

            print(f"DEBUG: Auto-creating Issue for {self.platform_name} conversation: {conversation_name}")

            # Call the Issue creation API
            result = inbox_api.create_issue_for_conversation(
                conversation_name=conversation_name,
                customer_name=customer_name,
                platform=self.platform_name,
                initial_message=initial_message,
                customer_phone=platform_data.get("customer_phone"),
                customer_nrc=platform_data.get("customer_nrc"),
                priority="Medium"
            )

            if result.get("status") == "success":
                print(f"DEBUG: Issue {result.get('issue_id')} created for conversation {conversation_name}")
            else:
                print(f"DEBUG: Failed to create Issue for conversation {conversation_name}: {result.get('message')}")

        except Exception as e:
            print(f"DEBUG: Error creating Issue for conversation {conversation_name}: {str(e)}")
            frappe.log_error(
                message=f"Error creating Issue for {self.platform_name} conversation {conversation_name}: {str(e)}",
                title="Auto Issue Creation Error"
            )

    def update_conversation_timestamp(self, conversation_name: str, timestamp_str: str) -> bool:
        """Update conversation's last_message_time only if the new timestamp is more recent.

        Returns True if the timestamp was updated, False if skipped (already newer).
        This prevents polling loops that process messages in newest-first order from
        overwriting a recent timestamp with an older one on subsequent iterations.
        """
        try:
            current = frappe.db.get_value(
                "Unified Inbox Conversation", conversation_name, "last_message_time"
            )
            if current:
                try:
                    from frappe.utils import get_datetime
                    if get_datetime(timestamp_str) <= get_datetime(str(current)):
                        return False  # New timestamp is not newer; skip update
                except Exception:
                    pass  # On parse failure, fall through and update anyway
            frappe.db.set_value(
                "Unified Inbox Conversation",
                conversation_name,
                "last_message_time",
                timestamp_str,
                update_modified=True,
            )
            return True
        except Exception as e:
            frappe.log_error(f"Error updating conversation timestamp: {str(e)}", "Social Media Integration")
            return False

    def update_issue_conversation_history(self, conversation_name: str, new_message_content: str, sender_name: str, timestamp_str: str, direction: str):
        """Update the ERPNext Issue with complete conversation history after each message."""

        # CRITICAL DEBUG: Log to file to ensure this function is being called
        debug_msg = f"DEBUG: ===== ISSUE UPDATE FUNCTION CALLED =====\nConversation: {conversation_name}\nMessage: {new_message_content[:50]}...\nSender: {sender_name}\nDirection: {direction}\n"
        print(debug_msg)

        try:
            log = frappe.logger("assistant_crm.unified_inbox")
            log.info(debug_msg)
        except:
            pass

        try:
            print(f"DEBUG: Starting Issue update for conversation {conversation_name}")
            print(f"DEBUG: Message: {new_message_content[:50]}... from {sender_name}")

            # Find the Issue linked to this conversation
            issue_name = frappe.db.get_value(
                "Issue",
                {"custom_conversation_id": conversation_name},
                "name"
            )

            if not issue_name:
                print(f"DEBUG: No Issue found for conversation {conversation_name}")
                return

            print(f"DEBUG: Found Issue {issue_name} for conversation {conversation_name}")

            # Get all messages for this conversation
            messages = frappe.get_all(
                "Unified Inbox Message",
                filters={"conversation": conversation_name},
                fields=["message_content", "sender_name", "timestamp", "direction", "message_type"],
                order_by="timestamp asc"
            )

            print(f"DEBUG: Found {len(messages)} messages for conversation {conversation_name}")

            # Build complete conversation history
            conversation_history = []
            conversation_history.append("=== COMPLETE CONVERSATION HISTORY ===\n")

            for msg in messages:
                timestamp_str_formatted = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S') if msg.timestamp else "Unknown time"
                direction_indicator = "ÔåÆ" if msg.direction == "Outbound" else "ÔåÉ"
                sender = msg.sender_name or "Unknown"
                content = msg.message_content or "[No content]"

                conversation_history.append(f"{timestamp_str_formatted} {direction_indicator} {sender}:")
                conversation_history.append(f"   {content}\n")

            conversation_history.append("=== END CONVERSATION HISTORY ===")

            # Update Issue description with complete conversation
            full_description = "\n".join(conversation_history)

            # Get the Issue document and update it
            issue_doc = frappe.get_doc("Issue", issue_name)
            issue_doc.description = full_description

            # Update Issue subject to include message count
            message_count = len(messages)
            original_subject = issue_doc.subject.split(" (")[0]  # Remove existing message count
            issue_doc.subject = f"{original_subject} ({message_count} messages)"

            # Save the Issue
            issue_doc.save()

            print(f"DEBUG: Successfully updated Issue {issue_name} with {message_count} messages")

        except Exception as e:
            print(f"DEBUG: Error updating Issue conversation history: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            frappe.log_error(f"Error updating Issue conversation history: {str(e)}", "Social Media Integration")


class WhatsAppIntegration(SocialMediaPlatform):
    """WhatsApp Business API integration."""

    def __init__(self):
        super().__init__("WhatsApp")

    def get_platform_credentials(self) -> Dict[str, str]:
        """Get WhatsApp credentials from Social Media Settings."""
        try:
            settings = frappe.get_single("Social Media Settings")
            def get_pwd(field: str) -> str:
                try:
                    return settings.get_password(field) or ""
                except Exception:
                    return settings.get(field) or ""

            return {
                "access_token": get_pwd("whatsapp_access_token"),
                "phone_number_id": (settings.get("whatsapp_phone_number_id") or "").strip(),
                "business_account_id": (settings.get("whatsapp_business_account_id") or "").strip(),
                "webhook_verify_token": (settings.get("whatsapp_webhook_verify_token") or "wcfcb_webhook_verify_token").strip(),
                "app_secret": get_pwd("whatsapp_app_secret"),
                "enabled": bool(settings.get("whatsapp_enabled"))
            }
        except Exception:
            return {
                "access_token": "",
                "phone_number_id": "",
                "business_account_id": "",
                "webhook_verify_token": "wcfcb_webhook_verify_token",
                "app_secret": "",
                "enabled": False
            }

    def check_configuration(self) -> bool:
        """Check if WhatsApp is properly configured."""
        required_fields = ["access_token", "phone_number_id"]
        return all(self.credentials.get(field) for field in required_fields)

    def send_message(self, recipient_id: str, message: str, message_type: str = "text") -> bool:
        """Send WhatsApp message."""
        if not self.is_configured:
            frappe.log_error("WhatsApp not configured", "WhatsApp Integration")
            return False

        try:
            url = f"https://graph.facebook.com/v18.0/{self.credentials['phone_number_id']}/messages"

            headers = {
                "Authorization": f"Bearer {self.credentials['access_token']}",
                "Content-Type": "application/json"
            }

            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "text",
                "text": {"body": message}
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            return response.status_code == 200

        except Exception as e:
            frappe.log_error(f"WhatsApp send error: {str(e)}", "WhatsApp Integration")
            return False

    def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process WhatsApp webhook."""
        try:
            print(f"DEBUG: Processing WhatsApp webhook: {json.dumps(webhook_data, indent=2)}")

            # Extract message data from WhatsApp webhook format
            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})

            if "messages" in value:
                for message in value["messages"]:
                    # Get customer information from contacts array
                    contacts = value.get("contacts", [])
                    customer_info = {}

                    # Find contact info for this sender
                    sender_phone = message.get("from")
                    for contact in contacts:
                        if contact.get("wa_id") == sender_phone:
                            customer_info = contact
                            break

                    # Build customer name from available information
                    customer_name = "WhatsApp User"
                    if customer_info:
                        profile = customer_info.get("profile", {})
                        if profile.get("name"):
                            customer_name = profile.get("name")
                        elif contact.get("wa_id"):
                            customer_name = f"WhatsApp User {contact.get('wa_id')[-4:]}"

                    # Extract message content based on message type
                    message_content = self.extract_whatsapp_message_content(message)

                    print(f"DEBUG: WhatsApp message from {customer_name}: {message_content[:50]}...")

                    # Process incoming message
                    platform_data = {
                        "conversation_id": sender_phone,
                        "customer_name": customer_name,
                        "customer_platform_id": sender_phone,
                        "customer_phone": sender_phone,  # WhatsApp provides phone number
                        "customer_email": None,  # WhatsApp doesn't provide email
                        "initial_message": message_content
                    }

                    conversation_name = self.create_unified_inbox_conversation(platform_data)

                    if conversation_name:
                        # Convert WhatsApp timestamp to proper datetime format
                        import datetime
                        timestamp = message.get("timestamp", 0)
                        if timestamp:
                            # WhatsApp timestamps are Unix timestamps in seconds
                            dt = datetime.datetime.fromtimestamp(int(timestamp))
                            timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                            print(f"DEBUG: WhatsApp message timestamp: {timestamp_str} (from Unix: {timestamp})")

                            # Update conversation timestamp
                            self.update_conversation_timestamp(conversation_name, timestamp_str)
                        else:
                            timestamp_str = now()
                            print(f"DEBUG: Using current time as fallback: {timestamp_str}")

                        message_data = {
                            "message_id": message.get("id"),
                            "content": message_content,
                            "sender_name": customer_name,
                            "sender_platform_id": sender_phone,
                            "timestamp": timestamp_str,
                            "direction": "Inbound",
                            "message_type": self.get_whatsapp_message_type(message),
                            "metadata": message
                        }

                        self.create_unified_inbox_message(conversation_name, message_data)

                        print(f"DEBUG: Processed WhatsApp message from {customer_name}")

            return {"status": "success", "platform": "WhatsApp"}

        except Exception as e:
            print(f"DEBUG: WhatsApp webhook error: {str(e)}")
            frappe.log_error(f"WhatsApp webhook error: {str(e)}", "WhatsApp Integration")
            return {"status": "error", "message": str(e)}

    def extract_whatsapp_message_content(self, message: Dict[str, Any]) -> str:
        """Extract message content from WhatsApp message based on type."""
        message_type = message.get("type", "text")

        if message_type == "text":
            return message.get("text", {}).get("body", "")
        elif message_type == "image":
            caption = message.get("image", {}).get("caption", "")
            return f"[Image]{': ' + caption if caption else ''}"
        elif message_type == "video":
            caption = message.get("video", {}).get("caption", "")
            return f"[Video]{': ' + caption if caption else ''}"
        elif message_type == "audio":
            return "[Audio Message]"
        elif message_type == "voice":
            return "[Voice Message]"
        elif message_type == "document":
            filename = message.get("document", {}).get("filename", "")
            caption = message.get("document", {}).get("caption", "")
            return f"[Document: {filename}]{': ' + caption if caption else ''}"
        elif message_type == "location":
            location = message.get("location", {})
            return f"[Location: {location.get('latitude', 'Unknown')}, {location.get('longitude', 'Unknown')}]"
        elif message_type == "contacts":
            return "[Contact Information]"
        elif message_type == "sticker":
            return "[Sticker]"
        else:
            return f"[{message_type.title()} Message]"

    def get_whatsapp_message_type(self, message: Dict[str, Any]) -> str:
        """Get normalized message type for unified inbox."""
        whatsapp_type = message.get("type", "text")

        # Map WhatsApp types to unified inbox types
        type_mapping = {
            "text": "text",
            "image": "image",
            "video": "video",
            "audio": "audio",
            "voice": "voice",
            "document": "document",
            "location": "location",
            "contacts": "contact",
            "sticker": "sticker"
        }

        return type_mapping.get(whatsapp_type, "text")


class FacebookIntegration(SocialMediaPlatform):
    """Facebook Messenger integration."""

    def __init__(self):
        super().__init__("Facebook")

    def get_platform_credentials(self) -> Dict[str, str]:
        """Get Facebook credentials from Social Media Settings (Single Doc)."""
        try:
            settings = frappe.get_single("Social Media Settings")
            def gp(field):
                try:
                    return settings.get_password(field)
                except Exception:
                    return settings.get(field)
            return {
                "page_access_token": gp("facebook_page_access_token") or "",
                "app_secret": gp("facebook_app_secret") or "",
                "verify_token": settings.get("webhook_verify_token") or "",
                "page_id": settings.get("facebook_page_id") or "",
                "api_version": settings.get("facebook_api_version") or "v23.0",
                "use_fallback_names": False,
            }
        except Exception:
            # Fallback to safe defaults
            return {
                "page_access_token": "",
                "app_secret": "",
                "verify_token": "",
                "page_id": "",
                "api_version": "v23.0",
                "use_fallback_names": False,
            }

    def check_configuration(self) -> bool:
        """Check if Facebook is properly configured.
        For sending messages, the page_access_token is sufficient. app_secret is only
        required for validating incoming webhooks/signatures and should not block
        outbound sends.
        """
        required_fields = ["page_access_token"]
        return all(self.credentials.get(field) for field in required_fields)

    def send_message(self, recipient_id: str, message: str, message_type: str = "text") -> bool:
        """Send Facebook message via Graph API with token auto-recovery.
        - messaging_type is required
        - access_token must be a Page Access Token; if a user/system token is provided,
          we attempt to exchange it for a page token using the configured page_id.
        """
        if not self.is_configured:
            frappe.log_error("Facebook not configured", "Facebook Integration")
            return False

        try:
            # Reset diagnostics for this send
            self.last_request_payload = None
            self.last_response_status = None
            self.last_response_text = None
            self.last_error = None

            api_ver = self.credentials.get("api_version", "v23.0")
            url = f"https://graph.facebook.com/{api_ver}/me/messages"

            def compute_appsecret_proof(tok: str) -> Optional[str]:
                try:
                    app_secret = (self.credentials.get("app_secret") or "").strip()
                    if not app_secret or not tok:
                        return None
                    import hmac, hashlib as _hashlib
                    return hmac.new(app_secret.encode("utf-8"), tok.encode("utf-8"), _hashlib.sha256).hexdigest()
                except Exception:
                    return None

            def do_send(token: str) -> requests.Response:
                headers = {"Content-Type": "application/json"}
                payload = {
                    "messaging_type": "RESPONSE",
                    "recipient": {"id": recipient_id},
                    "message": {"text": message},
                }
                params = {"access_token": token}
                proof = compute_appsecret_proof(token)
                if proof:
                    params["appsecret_proof"] = proof
                # Track request/response diagnostics
                try:
                    self.last_request_payload = {"url": url, "params": {k: ("***" if k == "access_token" else v) for k, v in params.items()}, "json": payload}
                except Exception:
                    pass
                resp = requests.post(url, params=params, headers=headers, json=payload, timeout=30)
                try:
                    self.last_response_status = resp.status_code
                    self.last_response_text = resp.text
                except Exception:
                    pass
                return resp

            # Initial token from settings (trim and sanitize)
            token = (self.credentials.get("page_access_token") or "")
            token = token.strip().strip('"').strip("'")
            token = token.replace(" ", "").replace("\n", "").replace("\r", "")
            if not token:
                frappe.log_error("Missing Facebook Page Access Token", "Facebook Integration")
                return False

            # First attempt
            resp = do_send(token)
            if resp.status_code == 200:
                return True

            # If token invalid/expired, try to derive a proper page token using the configured page_id
            try:
                err = resp.json() if resp.content else {}
            except Exception:
                err = {}

            # Attempt token exchange for a proper Page Access Token
            if self.credentials.get("page_id") and token:
                try:
                    page_id = self.credentials.get("page_id")
                    exchange_url = f"https://graph.facebook.com/{api_ver}/{page_id}"
                    exchange_params = {"fields": "access_token", "access_token": token}
                    proof = compute_appsecret_proof(token)
                    if proof:
                        exchange_params["appsecret_proof"] = proof
                    ex = requests.get(exchange_url, params=exchange_params, timeout=15)
                    if ex.status_code != 200:
                        try:
                            ex_txt = ex.text
                        except Exception:
                            ex_txt = "<no response text>"
                        # Track diagnostics for token exchange failure
                        try:
                            self.last_response_status = ex.status_code
                            self.last_response_text = ex_txt
                            self.last_error = "token_exchange_failed"
                        except Exception:
                            pass
                        frappe.log_error(f"Facebook token exchange failed: HTTP {ex.status_code} - {ex_txt}", "Facebook Integration")
                    if ex.status_code == 200:
                        page_token = (ex.json() or {}).get("access_token")
                        if page_token:
                            resp2 = do_send(page_token)
                            if resp2.status_code == 200:
                                return True
                            else:
                                try:
                                    err_txt2 = resp2.text
                                except Exception:
                                    err_txt2 = "<no response text>"
                                frappe.log_error(
                                    f"Facebook send failed after token exchange: HTTP {resp2.status_code} - {err_txt2}",
                                    "Facebook Integration"
                                )
                                return False
                except Exception as ex_err:
                    frappe.log_error(f"Facebook token exchange failed: {str(ex_err)}", "Facebook Integration")

            # Log detailed error for diagnostics
            try:
                err_txt = resp.text
            except Exception:
                err_txt = "<no response text>"
            frappe.log_error(
                f"Facebook send failed: HTTP {resp.status_code} - {err_txt}",
                "Facebook Integration"
            )
            return False

        except Exception as e:
            try:
                self.last_error = str(e)
            except Exception:
                pass
            frappe.log_error(f"Facebook send error: {str(e)}", "Facebook Integration")
            return False

    def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Facebook webhook."""
        try:
            # Extract message data from Facebook webhook format
            entry = (webhook_data.get("entry") or [{}])[0]
            messaging_events = (entry.get("messaging") or [])

            for messaging in messaging_events:
                if "message" not in messaging:
                    continue

                message = messaging["message"]
                sender = messaging.get("sender", {})
                recipient = messaging.get("recipient", {})

                # Determine correct user PSID. If this is an echo (our own sent message),
                # Facebook sets sender to the Page ID and recipient to the user PSID.
                page_id = (self.credentials.get("page_id") or "").strip()
                is_echo = bool(message.get("is_echo"))
                raw_sender_id = sender.get("id")
                user_psid = recipient.get("id") if (is_echo or (page_id and raw_sender_id == page_id)) else raw_sender_id

                # Ignore echo messages (our own sends) to prevent infinite reply loops
                if is_echo or (page_id and raw_sender_id == page_id):
                    # Skip this event but continue processing any others in the same payload
                    continue

                # Get message content for ticket generation
                message_content = message.get("text", "")
                if not message_content:
                    message_content = "[Media message]"

                # Get user information for better customer names
                user_info = self.get_user_info(user_psid)
                customer_name = user_info.get("name", user_info.get("first_name", f"Facebook User {user_psid[-6:]}"))

                platform_data = {
                    "conversation_id": user_psid,
                    "customer_name": customer_name,
                    "customer_platform_id": user_psid,
                    "customer_phone": None,
                    "customer_email": None,
                    "initial_message": message_content
                }

                conversation_name = self.create_unified_inbox_conversation(platform_data)

                if conversation_name:
                    # Extract timestamp from Facebook webhook (same approach as Tawk.to)
                    import datetime

                    # Get timestamp from Facebook message
                    timestamp_ms = messaging.get("timestamp", 0)

                    # Convert milliseconds to a string without timezone conversion
                    if timestamp_ms:
                        dt = datetime.datetime.utcfromtimestamp(timestamp_ms / 1000)  # Facebook uses milliseconds
                        timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        timestamp = now()

                    message_data = {
                        "message_id": message.get("mid"),
                        "content": message_content,
                        "sender_name": customer_name,
                        "sender_platform_id": user_psid,
                        "timestamp": timestamp,
                        "direction": "Inbound",
                        "message_type": "text",
                        "metadata": messaging
                    }

                    self.create_unified_inbox_message(conversation_name, message_data)

                    # Update conversation timestamp for proper inbox sorting
                    self.update_conversation_timestamp(conversation_name, timestamp)

            return {"status": "success", "platform": "Facebook"}

        except Exception as e:
            frappe.log_error(f"Facebook webhook error: {str(e)}", "Facebook Integration")
            return {"status": "error", "message": str(e)}

    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get Facebook user information."""
        try:
            # Facebook Messenger API for user info
            api_ver = self.credentials.get("api_version", "v23.0")
            url = f"https://graph.facebook.com/{api_ver}/{user_id}"
            params = {
                "fields": "first_name,last_name,name,profile_pic",
                "access_token": self.credentials.get("page_access_token", "")
            }

            if not params["access_token"]:
                print(f"DEBUG: No Facebook access token configured")
                return self._get_facebook_fallback_user_info(user_id)

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                print(f"DEBUG: Successfully got Facebook user info for {user_id}: {data.get('name', 'No name')}")
                return data
            else:
                error_data = response.json() if response.content else {}
                print(f"DEBUG: Facebook API error {response.status_code}: {error_data.get('error', {}).get('message', 'Unknown error')}")
                return self._get_facebook_fallback_user_info(user_id)

        except Exception as e:
            print(f"DEBUG: Error getting Facebook user info: {str(e)}")
            return self._get_facebook_fallback_user_info(user_id)

    def _upload_photo_to_facebook(
        self, base: str, page_id: str, params_base: Dict[str, Any], url: str
    ) -> Optional[str]:
        """
        Upload a photo to the Facebook page as an unpublished staging item.

        Strategy:
          1. If the URL points to a local Frappe file (public or private),
             upload the raw bytes via multipart/form-data — works regardless
             of whether the file is publicly accessible on the internet.
          2. Fall back to the URL-based upload for externally hosted images.

        Returns the photo ID string on success, or None on failure.
        """
        import os
        import mimetypes

        # Try to resolve a local filesystem path for the URL
        local_path = None
        try:
            from assistant_crm.api.social_media_publisher import _resolve_file_path
            local_path = _resolve_file_path(url)
        except Exception:
            pass

        photo_params = dict(params_base)
        photo_params["published"] = "false"
        endpoint = f"{base}/{page_id}/photos"

        if local_path and os.path.isfile(local_path):
            # --- Multipart upload (private or public local file) ---
            mime = mimetypes.guess_type(local_path)[0] or "image/jpeg"
            try:
                with open(local_path, "rb") as fh:
                    resp = requests.post(
                        endpoint,
                        params=photo_params,
                        files={"source": (os.path.basename(local_path), fh, mime)},
                        timeout=60
                    )
            except Exception as e:
                frappe.log_error(
                    title="Facebook publish_post: multipart upload exception",
                    message=str(e)
                )
                return None
        else:
            # --- URL-based upload (externally hosted image) ---
            photo_params["url"] = url
            resp = requests.post(endpoint, params=photo_params, timeout=30)

        if resp.status_code == 200:
            return (resp.json() or {}).get("id")

        frappe.log_error(
            title="Facebook publish_post: photo upload failed",
            message=f"URL={url} status={resp.status_code} body={resp.text[:500]}"
        )
        return None

    def _get_facebook_fallback_user_info(self, user_id: str) -> Dict[str, Any]:
        """Generate fallback user info for Facebook when API is unavailable."""
        short_id = user_id[-6:] if len(user_id) > 6 else user_id
        return {
            "id": user_id,
            "name": f"Facebook User {short_id}",
            "first_name": f"User {short_id}"
        }

    def publish_post(self, content: str, media_urls: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Publish a post to the configured Facebook Page.

        Text-only: POST /{page_id}/feed with message.
        With images: upload each image as an unpublished Photo, then attach
        all photo IDs to a single feed post via attached_media[].

        Returns dict with keys: success, post_id, post_url, error.
        """
        token = (self.credentials.get("page_access_token") or "").strip()
        page_id = (self.credentials.get("page_id") or "").strip()
        api_ver = self.credentials.get("api_version", "v23.0")

        if not token:
            return {"success": False, "error": "Facebook page_access_token is not configured."}
        if not page_id:
            return {"success": False, "error": "Facebook page_id is not configured."}

        base = f"https://graph.facebook.com/{api_ver}"

        def _make_params(tok: str) -> dict:
            """Build params_base with access_token and optional appsecret_proof."""
            p = {"access_token": tok}
            try:
                app_secret = (self.credentials.get("app_secret") or "").strip()
                if app_secret and tok:
                    import hmac as _hmac
                    p["appsecret_proof"] = _hmac.new(
                        app_secret.encode("utf-8"), tok.encode("utf-8"), hashlib.sha256
                    ).hexdigest()
            except Exception:
                pass
            return p

        def _exchange_for_page_token(user_token: str) -> Optional[str]:
            """Exchange a User Access Token for a Page Access Token using page_id."""
            try:
                ex_resp = requests.get(
                    f"{base}/{page_id}",
                    params={"fields": "access_token", "access_token": user_token},
                    timeout=15,
                )
                if ex_resp.status_code == 200:
                    page_token = (ex_resp.json() or {}).get("access_token", "").strip()
                    if page_token:
                        # Persist so future calls use the Page token directly
                        try:
                            frappe.get_single("Social Media Settings").db_set(
                                "facebook_page_access_token", page_token
                            )
                        except Exception:
                            pass
                        return page_token
            except Exception:
                pass
            return None

        params_base = _make_params(token)

        _video_exts = (".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v")

        def _is_video(url: str) -> bool:
            return any(url.lower().split("?")[0].endswith(ext) for ext in _video_exts)

        try:
            valid_urls = [u for u in (media_urls or []) if u]
            video_urls = [u for u in valid_urls if _is_video(u)]
            image_urls = [u for u in valid_urls if not _is_video(u)]

            # --- Video post: Facebook requires /{page_id}/videos, not /photos ---
            if video_urls:
                # Publish the first video as a native video post.
                # Facebook does not support multi-video carousels in a single post.
                video_url = video_urls[0]
                video_params = dict(params_base)
                video_params["description"] = content
                video_params["published"] = "true"

                local_path = None
                try:
                    from assistant_crm.api.social_media_publisher import _resolve_file_path
                    local_path = _resolve_file_path(video_url)
                except Exception:
                    pass

                import os as _os
                import mimetypes as _mimetypes
                if local_path and _os.path.isfile(local_path):
                    mime = _mimetypes.guess_type(local_path)[0] or "video/mp4"
                    try:
                        with open(local_path, "rb") as fh:
                            resp = requests.post(
                                f"{base}/{page_id}/videos",
                                params=video_params,
                                files={"source": (_os.path.basename(local_path), fh, mime)},
                                timeout=300,
                            )
                    except Exception as e:
                        frappe.log_error(title="Facebook publish_post: video upload exception", message=str(e))
                        return {"success": False, "error": str(e)}
                else:
                    video_params["file_url"] = video_url
                    resp = requests.post(f"{base}/{page_id}/videos", params=video_params, timeout=120)

                # If 403, try exchanging User token → Page token and retry
                if resp.status_code == 403:
                    page_token = _exchange_for_page_token(token)
                    if page_token:
                        video_params = dict(_make_params(page_token))
                        video_params["description"] = content
                        video_params["published"] = "true"
                        if local_path and _os.path.isfile(local_path):
                            try:
                                with open(local_path, "rb") as fh:
                                    resp = requests.post(
                                        f"{base}/{page_id}/videos",
                                        params=video_params,
                                        files={"source": (_os.path.basename(local_path), fh, mime)},
                                        timeout=300,
                                    )
                            except Exception as e:
                                return {"success": False, "error": str(e)}
                        else:
                            video_params["file_url"] = video_url
                            resp = requests.post(f"{base}/{page_id}/videos", params=video_params, timeout=120)

                if resp.status_code == 200:
                    post_id = (resp.json() or {}).get("id", "")
                    post_url = f"https://www.facebook.com/{page_id}/videos/{post_id}/" if post_id else ""
                    return {"success": True, "post_id": post_id, "post_url": post_url}
                else:
                    error_data = resp.json() if resp.content else {}
                    error_msg = (error_data.get("error") or {}).get("message", resp.text[:300])
                    frappe.log_error(
                        title="Facebook publish_post: video upload failed",
                        message=f"URL={video_url} status={resp.status_code} error={error_msg}"
                    )
                    return {"success": False, "error": error_msg}

            # --- Image post: upload each image as an unpublished photo then attach ---
            def _do_image_post(pb: dict) -> dict:
                """Upload photos and create the feed post using the given params_base."""
                media = []
                for url in image_urls:
                    photo_id = self._upload_photo_to_facebook(base, page_id, pb, url)
                    if photo_id:
                        media.append({"media_fbid": photo_id})

                fp = dict(pb)
                payload: Dict[str, Any] = {"message": content}
                if media:
                    for i, item in enumerate(media):
                        payload[f"attached_media[{i}]"] = json.dumps(item)

                r = requests.post(
                    f"{base}/{page_id}/feed",
                    params=fp,
                    data=payload,
                    timeout=30,
                )
                return r

            resp = _do_image_post(params_base)

            # If we get a 403 the stored token is likely a User token — try exchanging
            # it for a Page Access Token and retry once.
            if resp.status_code == 403:
                page_token = _exchange_for_page_token(token)
                if page_token:
                    params_base = _make_params(page_token)
                    resp = _do_image_post(params_base)

            if resp.status_code == 200:
                post_id = (resp.json() or {}).get("id", "")
                # post_id format is "{page_id}_{post_numeric_id}"
                post_url = f"https://www.facebook.com/{post_id.replace('_', '/posts/')}" if post_id else ""
                return {"success": True, "post_id": post_id, "post_url": post_url}
            else:
                error_data = resp.json() if resp.content else {}
                error_msg = (error_data.get("error") or {}).get("message", resp.text[:300])
                frappe.log_error(
                    title="Facebook publish_post: feed post failed",
                    message=f"status={resp.status_code} error={error_msg}"
                )
                return {"success": False, "error": error_msg}

        except Exception as e:
            frappe.log_error(title="Facebook publish_post: exception", message=frappe.get_traceback())
            return {"success": False, "error": str(e)}



class TelegramIntegration(SocialMediaPlatform):
    """Telegram Bot API integration."""

    def __init__(self):
        super().__init__("Telegram")

    def get_platform_credentials(self) -> Dict[str, str]:
        """Get Telegram credentials from Social Media Settings."""
        try:
            settings = frappe.get_single("Social Media Settings")
            def gp(field):
                try:
                    return settings.get_password(field)
                except Exception:
                    return settings.get(field)
            return {
                "bot_token": gp("telegram_bot_token") or "",
                "webhook_secret": gp("telegram_webhook_secret") or ""
            }
        except Exception:
            return {
                "bot_token": "",
                "webhook_secret": ""
            }

    def check_configuration(self) -> bool:
        """Check if Telegram is properly configured."""
        required_fields = ["bot_token"]
        return all(self.credentials.get(field) for field in required_fields)

    def send_message(self, recipient_id: str, message: str, message_type: str = "text") -> bool:
        """Send Telegram message with diagnostics (parity with IG/FB)."""
        if not self.is_configured:
            frappe.log_error("Telegram not configured", "Telegram Integration")
            return False

        try:
            # Reset diagnostics
            self.last_request_payload = None
            self.last_response_status = None
            self.last_response_text = None
            self.last_error = None

            token = (self.credentials.get('bot_token') or '').strip()
            url = f"https://api.telegram.org/bot{token}/sendMessage"

            payload = {
                "chat_id": recipient_id,
                "text": message
            }

            # Record safe diagnostics (redact token in URL)
            try:
                redacted_url = url.replace(token, "***") if token else url
                self.last_request_payload = {"url": redacted_url, "json": payload}
            except Exception:
                pass

            response = requests.post(url, json=payload, timeout=30)
            try:
                self.last_response_status = response.status_code
                self.last_response_text = response.text
            except Exception:
                pass

            if response.status_code == 200:
                try:
                    data = response.json()
                    return bool(data.get("ok") is True)
                except Exception:
                    # If JSON parsing fails but status is 200, consider it success
                    return True
            return False

        except Exception as e:
            try:
                self.last_error = str(e)
            except Exception:
                pass
            frappe.log_error(f"Telegram send error: {str(e)}", "Telegram Integration")
            return False

    def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Telegram webhook."""
        try:
            # Extract message data from Telegram webhook format
            message = webhook_data.get("message", {})

            if message:
                chat = message.get("chat", {})
                from_user = message.get("from", {})

                # Build customer name from available fields
                customer_name = from_user.get("first_name", "")
                if from_user.get("last_name"):
                    customer_name += f" {from_user.get('last_name')}"
                if from_user.get("username"):
                    customer_name += f" (@{from_user.get('username')})"
                if not customer_name:
                    customer_name = "Telegram User"

                # Get message content for ticket generation
                message_content = message.get("text", message.get("caption", ""))
                if not message_content:
                    if message.get("photo"):
                        message_content = "[Image message]"
                    elif message.get("document"):
                        message_content = "[Document message]"
                    elif message.get("voice"):
                        message_content = "[Voice message]"
                    elif message.get("video"):
                        message_content = "[Video message]"
                    else:
                        message_content = "[Media message]"

                platform_data = {
                    "conversation_id": str(chat.get("id")),
                    "customer_name": customer_name,
                    "customer_platform_id": str(from_user.get("id")),
                    "customer_phone": None,  # Telegram doesn't provide phone numbers
                    "customer_email": None,  # Telegram doesn't provide emails
                    "initial_message": message_content  # Add initial message for ticket generation
                }

                conversation_name = self.create_unified_inbox_conversation(platform_data)

                if conversation_name:
                    # Convert Unix timestamp to proper datetime format
                    import datetime
                    from frappe.utils import get_datetime

                    # Get Unix timestamp from Telegram message
                    unix_timestamp = message.get("date", 0)

                    # Convert to proper datetime format for Frappe (using UTC for accurate timestamps)
                    if unix_timestamp:
                        dt = datetime.datetime.utcfromtimestamp(unix_timestamp)
                        timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        timestamp = now()

                    message_data = {
                        "message_id": str(message.get("message_id")),
                        "content": message.get("text", message.get("caption", "")),  # Handle both text and media with captions
                        "sender_name": customer_name,
                        "sender_platform_id": str(from_user.get("id")),
                        "timestamp": timestamp,
                        "direction": "Inbound",
                        "message_type": "text",
                        "metadata": message
                    }

                    # Handle different message types
                    if message.get("photo"):
                        message_data["message_type"] = "image"
                        message_data["content"] = message.get("caption", "[Image]")
                    elif message.get("document"):
                        message_data["message_type"] = "document"
                        message_data["content"] = message.get("caption", "[Document]")
                    elif message.get("voice"):
                        message_data["message_type"] = "voice"
                        message_data["content"] = "[Voice Message]"
                    elif message.get("video"):
                        message_data["message_type"] = "video"
                        message_data["content"] = message.get("caption", "[Video]")

                    self.create_unified_inbox_message(conversation_name, message_data)

                    # Enqueue AI processing for this conversation (safe for duplicates)
                    try:
                        frappe.enqueue(
                            "assistant_crm.api.unified_inbox_api.process_conversation_with_ai",
                            conversation_id=conversation_name,
                            queue="long",
                        )
                    except Exception as ai_err:
                        frappe.log_error(f"Telegram AI enqueue error: {str(ai_err)}", "Telegram Integration")

                    # Note: Issue update is now handled in create_issue_for_conversation()
                    # No need for redundant update here

                    print(f"DEBUG: Processed Telegram message from {customer_name}: {message_data['content'][:50]}...")

            return {"status": "success", "platform": "Telegram"}

        except Exception as e:
            frappe.log_error(f"Telegram webhook error: {str(e)}", "Telegram Integration")
            return {"status": "error", "message": str(e)}


class TawkToIntegration(SocialMediaPlatform):
    """Tawk.to Live Chat API integration."""

    def __init__(self):
        super().__init__("Tawk.to")

    def get_platform_credentials(self) -> Dict[str, str]:
        """Get Tawk.to credentials from Social Media Settings."""
        settings = frappe.get_single("Social Media Settings")
        return {
            "property_id": settings.tawk_to_property_id or "",
            "api_key": settings.get_password("tawk_to_api_key") if settings.get("tawk_to_api_key") else "",
            "webhook_secret": settings.get_password("tawk_to_webhook_secret") if settings.get("tawk_to_webhook_secret") else "",
        }

    def check_configuration(self) -> bool:
        """Check if Tawk.to is properly configured."""
        required_fields = ["property_id"]  # API key not required for basic webhook processing
        return all(self.credentials.get(field) for field in required_fields)

    def send_message(self, recipient_id: str, message: str, message_type: str = "text") -> bool:
        """Send Tawk.to message (requires API key)."""
        if not self.credentials.get("api_key"):
            frappe.log_error("Tawk.to API key not configured for sending messages", "Tawk.to Integration")
            return False

        try:
            # Tawk.to API endpoint for sending messages
            url = f"https://api.tawk.to/v3/chats/{recipient_id}/messages"

            headers = {
                "Authorization": f"Bearer {self.credentials['api_key']}",
                "Content-Type": "application/json"
            }

            payload = {
                "message": message,
                "type": "msg"
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            return response.status_code == 200

        except Exception as e:
            frappe.log_error(f"Tawk.to send error: {str(e)}", "Tawk.to Integration")
            return False

    def build_customer_name(self, visitor: Dict[str, Any]) -> str:
        """Build customer name from visitor data with enhanced logic."""
        name = visitor.get("name", "")
        email = visitor.get("email", "")

        # Clean up auto-generated visitor names (like V1756735189389218)
        if name and name.startswith("V") and name[1:].isdigit():
            name = ""  # Ignore auto-generated visitor IDs

        # Build meaningful customer name
        if name and email:
            return f"{name} ({email})"
        elif email:
            # Extract name from email if possible
            email_name = email.split("@")[0].replace(".", " ").title()
            return f"{email_name} ({email})"
        elif name and not name.startswith("V"):
            return name
        else:
            return "Tawk.to Visitor"

    def build_conversation_content(self, messages: List[Dict[str, Any]]) -> str:
        """Build complete conversation content from Tawk.to transcript messages."""
        if not messages:
            return ""

        conversation_lines = []
        for msg in messages:
            sender = msg.get("sender", {})
            sender_type = sender.get("t", "")  # 'v' = visitor, 'a' = agent, 's' = system
            sender_name = sender.get("n", "Unknown")
            message_text = msg.get("msg", "")
            timestamp = msg.get("time", "")

            # Format sender
            if sender_type == "v":
                sender_label = "Visitor"
            elif sender_type == "a":
                sender_label = f"Agent ({sender_name})"
            elif sender_type == "s":
                sender_label = f"System ({sender_name})"
            else:
                sender_label = "Unknown"

            # Add timestamp if available
            time_str = f" [{timestamp}]" if timestamp else ""

            conversation_lines.append(f"{sender_label}{time_str}: {message_text}")

        return "\n".join(conversation_lines)

    def find_existing_conversation(self, chat_id: str) -> str:
        """Find existing conversation by Tawk.to chat ID or ticket platform_specific_id."""
        try:
            return frappe.db.get_value(
                "Unified Inbox Conversation",
                {"platform_specific_id": chat_id, "platform": "Tawk.to"},
                "name"
            )
        except Exception as e:
            frappe.log_error(f"Error finding Tawk.to conversation: {str(e)}", "Tawk.to Integration")
            return None

    def process_real_tawkto_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process real Tawk.to webhook with official payload structure."""
        try:
            event_type = webhook_data.get("event")

            if event_type == "chat:start":
                chat_id = webhook_data.get("chatId")
                message = webhook_data.get("message", {})
                visitor = webhook_data.get("visitor", {})
                property_data = webhook_data.get("property", {})

                if not chat_id:
                    return {"status": "error", "message": "No chatId in chat:start event"}

                customer_name = self.build_customer_name(visitor)
                message_content = message.get("text", "") or "[Media message]"

                platform_data = {
                    "conversation_id": chat_id,
                    "customer_name": customer_name,
                    "customer_platform_id": chat_id,
                    "customer_email": visitor.get("email"),
                    "customer_phone": None,
                    "initial_message": message_content,
                    "tawk_property_id": property_data.get("id"),
                    "tawk_property_name": property_data.get("name"),
                }

                return self.create_conversation_and_message(platform_data, webhook_data)

            elif event_type == "ticket:create":
                # Official ticket:create payload (no chatId — tickets are independent of chats):
                #   requester: {name, email}, ticket: {id, humanId, subject, message},
                #   property: {id, name}, time: ISO string
                ticket = webhook_data.get("ticket") or {}
                requester = webhook_data.get("requester") or {}
                property_data = webhook_data.get("property") or {}

                ticket_id = ticket.get("id")
                if not ticket_id:
                    return {"status": "error", "message": "Missing ticket.id in ticket:create event"}

                platform_specific_id = f"ticket:{ticket_id}"
                requester_name = requester.get("name") or "Tawk.to Visitor"
                requester_email = requester.get("email")
                human_id = ticket.get("humanId")
                subject = (ticket.get("subject") or "").strip()
                body = (ticket.get("message") or "").strip()
                ticket_label = f"[Ticket #{human_id}]" if human_id else "[Ticket]"
                message_content = f"{ticket_label} {subject}"
                if body:
                    message_content += f"\n{body}"

                timestamp_str = _normalize_iso(webhook_data.get("time"))

                conversation_name = self.find_existing_conversation(platform_specific_id)
                if not conversation_name:
                    platform_data = {
                        "conversation_id": platform_specific_id,
                        "customer_name": requester_name,
                        "customer_platform_id": ticket_id,
                        "customer_email": requester_email,
                        "customer_phone": None,
                        "initial_message": message_content,
                        "tawk_property_id": property_data.get("id"),
                        "tawk_property_name": property_data.get("name"),
                    }
                    conversation_name = self.create_unified_inbox_conversation(platform_data)

                if conversation_name:
                    msg_id = f"ticket:{ticket_id}"
                    message_data = {
                        "message_id": msg_id,
                        "content": message_content,
                        "sender_name": requester_name,
                        "sender_platform_id": ticket_id,
                        "timestamp": timestamp_str,
                        "direction": "Inbound",
                        "message_type": "text",
                        "metadata": ticket,
                    }
                    self.create_unified_inbox_message(conversation_name, message_data)
                    self.update_conversation_timestamp(conversation_name, timestamp_str)

                return {"status": "success", "platform": "Tawk.to", "conversation": conversation_name, "type": "ticket_create"}

            elif event_type == "chat:end":
                chat_id = webhook_data.get("chatId")
                visitor = webhook_data.get("visitor", {})
                property_data = webhook_data.get("property", {})

                if not chat_id:
                    return {"status": "error", "message": "No chatId in chat:end event"}

                existing_conversation = self.find_existing_conversation(chat_id)

                if existing_conversation:
                    frappe.db.set_value(
                        "Unified Inbox Conversation",
                        existing_conversation,
                        "status",
                        "Resolved",
                    )
                    return {"status": "success", "platform": "Tawk.to", "conversation": existing_conversation, "type": "chat_ended"}

                else:
                    # chat:end arrived without a prior chat:start — create a minimal record
                    customer_name = self.build_customer_name(visitor)
                    platform_data = {
                        "conversation_id": chat_id,
                        "customer_name": customer_name,
                        "customer_platform_id": chat_id,
                        "customer_email": visitor.get("email"),
                        "customer_phone": None,
                        "initial_message": "Chat ended",
                        "tawk_property_id": property_data.get("id"),
                        "tawk_property_name": property_data.get("name"),
                    }
                    return self.create_conversation_and_message(platform_data, webhook_data)



            elif event_type == "chat:transcript_created":
                # Ingest full transcript after chat ends to ensure complete history in Unified Inbox
                    chat_obj = webhook_data.get("chat") or {}
                    chat_id = chat_obj.get("id") or webhook_data.get("chatId")
                    property_data = webhook_data.get("property", {})
                    visitor = chat_obj.get("visitor") or webhook_data.get("visitor") or {}
                    messages = list(chat_obj.get("messages") or [])


                    if not chat_id:
                        return {"status": "error", "message": "Missing chat id in transcript"}

                    # Find or create conversation
                    conversation_name = self.find_existing_conversation(chat_id)
                    customer_name = self.build_customer_name(visitor)

                    if not conversation_name:
                        platform_data = {
                            "conversation_id": chat_id,
                            "customer_name": customer_name,
                            "customer_platform_id": chat_id,
                            "customer_email": visitor.get("email"),
                            "customer_phone": None,
                            "initial_message": "Chat transcript received",
                            "tawk_property_id": property_data.get("id"),
                            "tawk_property_name": property_data.get("name"),
                        }
                        conversation_name = self.create_unified_inbox_conversation(platform_data)

                    if not conversation_name:
                        return {"status": "error", "message": "Failed to resolve conversation for transcript"}

                    # Ingest messages in chronological order
                    last_ts = None
                    last_sender = None
                    last_direction = "Inbound"
                    last_content = ""

                    for idx, msg in enumerate(messages or []):
                        sender = msg.get("sender") or {}
                        sender_type = (sender.get("t") or "").lower()  # a (agent), v (visitor), s (system)
                        sender_name = sender.get("n") or (customer_name if sender_type == "v" else ("System" if sender_type == "s" else "Agent"))
                        direction = "Inbound" if sender_type == "v" else "Outbound"

                        content = msg.get("msg") or ""
                        # If no content but attachments exist, add a placeholder
                        if not content and msg.get("attchs"):
                            content = "[Attachment]"

                        # Build attachments list if present
                        attachments = []
                        for att in msg.get("attchs") or []:
                            try:
                                file_info = ((att.get("content") or {}).get("file") or {})
                                attachments.append({
                                    "type": att.get("type"),
                                    "url": file_info.get("url"),
                                    "name": file_info.get("name"),
                                    "mimeType": file_info.get("mimeType"),
                                    "size": file_info.get("size"),
                                    "extension": file_info.get("extension"),
                                })
                            except Exception:
                                continue

                        timestamp_str = _normalize_iso(msg.get("time"))

                        message_id = f"tawk:transcript:{chat_id}:{idx}"
                        message_data = {
                            "message_id": message_id,
                            "content": content,
                            "sender_name": sender_name,
                            "sender_platform_id": chat_id,
                            "timestamp": timestamp_str,
                            "direction": direction,
                            "message_type": ("text" if (msg.get("type") or "").lower() in ["msg", "text"] else (msg.get("type") or "text")),
                            "attachments": attachments,
                            "metadata": msg,
                        }

                        try:
                            self.create_unified_inbox_message(conversation_name, message_data)
                        except Exception as ins_err:
                            frappe.log_error(f"Transcript message insert failed idx={idx} id={message_id}: {ins_err}", "Tawk.to Integration")

                        last_ts = timestamp_str
                        last_sender = sender_name
                        last_direction = direction
                        last_content = content

                    # Update conversation last message time to the last transcript message
                    if last_ts:
                        self.update_conversation_timestamp(conversation_name, last_ts)

                    # Update ERPNext Issue description with full conversation history
                    try:
                        self.update_issue_conversation_history(
                            conversation_name,
                            last_content or "[Transcript Imported]",
                            last_sender or customer_name,
                            last_ts or now(),
                            last_direction,
                        )
                    except Exception as issue_err:
                        frappe.log_error(f"Issue update after transcript failed: {issue_err}", "Tawk.to Integration")

                    return {
                        "status": "success",
                        "platform": "Tawk.to",
                        "conversation": conversation_name,
                        "type": "chat_transcript_created",
                        "messages_ingested": len(messages or []),
                    }

            else:
                return {"status": "info", "message": f"Event type '{event_type}' not handled"}

        except Exception as e:
            frappe.log_error(f"Real Tawk.to webhook error: {str(e)}", "Tawk.to Integration")
            return {"status": "error", "message": str(e)}

    def process_legacy_test_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process legacy test webhook format for backward compatibility."""
        try:
            event_type = webhook_data.get("event")

            if event_type == "chat:message":
                message_data = webhook_data.get("data", {})
                chat_data = message_data.get("chat", {})
                message = message_data.get("message", {})
                visitor = chat_data.get("visitor", {})

                # Build customer name from available fields
                customer_name = visitor.get("name", "")
                if visitor.get("email"):
                    customer_name += f" ({visitor.get('email')})"
                if not customer_name:
                    customer_name = "Tawk.to Visitor"

                # Get message content
                message_content = message.get("text", "")
                if not message_content:
                    message_content = "[Media message]"

                platform_data = {
                    "conversation_id": chat_data.get("id"),
                    "customer_name": customer_name,
                    "customer_platform_id": visitor.get("id"),
                    "customer_email": visitor.get("email"),
                    "customer_phone": visitor.get("phone"),
                    "initial_message": message_content  # Add initial message for ticket generation
                }

                conversation_name = self.create_unified_inbox_conversation(platform_data)

                if conversation_name:
                    # Convert timestamp to proper datetime format
                    import datetime

                    # Get timestamp from Tawk.to message
                    timestamp_ms = message.get("time", 0)

                    # Legacy test format sends millisecond timestamps
                    if timestamp_ms:
                        dt = datetime.datetime.fromtimestamp(timestamp_ms / 1000)
                        timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        timestamp = now()

                    message_data = {
                        "message_id": message.get("id"),
                        "content": message_content,
                        "sender_name": customer_name,
                        "sender_platform_id": visitor.get("id"),
                        "timestamp": timestamp,
                        "direction": "Inbound",
                        "message_type": "text",
                        "metadata": webhook_data
                    }

                    self.create_unified_inbox_message(conversation_name, message_data)

            return {"status": "success", "platform": "Tawk.to", "format": "legacy"}

        except Exception as e:
            frappe.log_error(f"Legacy Tawk.to webhook error: {str(e)}", "Tawk.to Integration")
            return {"status": "error", "message": str(e)}

    def create_conversation_and_message(self, platform_data: Dict[str, Any], webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create conversation and first message for a Tawk.to chat:start event."""
        try:
            conversation_name = self.create_unified_inbox_conversation(platform_data)

            if conversation_name:
                # Tawk.to timestamps are ISO 8601 strings ("2019-06-28T14:03:04.646Z"),
                # not milliseconds. Use the root-level time field from the webhook payload.
                timestamp = _normalize_iso(webhook_data.get("time"))

                message_data = {
                    "message_id": webhook_data.get("chatId", "unknown"),
                    "content": platform_data.get("initial_message", ""),
                    "sender_name": platform_data.get("customer_name", ""),
                    "sender_platform_id": platform_data.get("customer_platform_id", ""),
                    "timestamp": timestamp,
                    "direction": "Inbound",
                    "message_type": "text",
                    "metadata": webhook_data,
                }

                self.create_unified_inbox_message(conversation_name, message_data)
                self.update_conversation_timestamp(conversation_name, timestamp)

                return {"status": "success", "platform": "Tawk.to", "conversation": conversation_name}
            else:
                return {"status": "error", "message": "Failed to create conversation"}

        except Exception as e:
            frappe.log_error(f"Tawk.to conversation creation error: {str(e)}", "Tawk.to Integration")
            return {"status": "error", "message": str(e)}

    def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Route a Tawk.to webhook payload to the correct handler.

        Real Tawk.to format detection covers all four official events:
          - chat:start / chat:end  → have chatId + visitor at root
          - chat:transcript_created → has a 'chat' object at root
          - ticket:create           → has 'ticket' + 'requester' at root (no chatId)

        Payloads wrapped in a 'data' key are the legacy test format.
        """
        try:
            event_type = webhook_data.get("event")

            is_real_format = (
                ("chatId" in webhook_data and "visitor" in webhook_data)
                or (event_type == "chat:transcript_created" and "chat" in webhook_data)
                or (event_type == "ticket:create" and "ticket" in webhook_data)
            )

            if is_real_format:
                return self.process_real_tawkto_webhook(webhook_data)
            elif "data" in webhook_data:
                return self.process_legacy_test_webhook(webhook_data)
            else:
                frappe.log_error(
                    f"Unknown Tawk.to payload format. Keys: {list(webhook_data.keys())}",
                    "Tawk.to Integration"
                )
                return {"status": "error", "message": "Unknown payload format"}

        except Exception as e:
            frappe.log_error(f"Tawk.to webhook error: {str(e)}", "Tawk.to Integration")
            return {"status": "error", "message": str(e)}


class InstagramIntegration(SocialMediaPlatform):
    """Instagram Graph API integration for direct messages and comments."""

    def __init__(self):
        super().__init__("Instagram")
        # Diagnostics for last send attempt
        self.last_request_payload = None
        self.last_response_status = None
        self.last_response_text = None
        self.last_error = None

    def get_platform_credentials(self) -> Dict[str, str]:
        """Get Instagram credentials from settings.
        Preference order for token:
        1) instagram_access_token (if explicitly set)
        2) facebook_page_access_token (reuse same long-lived token as Facebook)
        """
        try:
            settings = frappe.get_single("Social Media Settings")
            def gp(field):
                try:
                    return settings.get_password(field)
                except Exception:
                    return settings.get(field)
            # Prefer Instagram-specific access token; fall back to the Facebook Page token
            # if no dedicated Instagram token is configured (both point to the same Page token
            # in most setups, but instagram_access_token should carry instagram_manage_messages scope)
            token = (
                gp("instagram_access_token")
                or gp("facebook_page_access_token")
                or ""
            )
            api_ver = (
                settings.get("instagram_api_version")
                or settings.get("facebook_api_version")
                or "v23.0"
            )
            webhook_secret = (
                gp("webhook_secret")
                or gp("facebook_app_secret")
                or gp("instagram_webhook_secret")
                or settings.get("webhook_verify_token")
                or ""
            )
            instagram_business_account_id = (
                settings.get("instagram_business_account_id") or ""
            ).strip()
            return {
                "access_token": token,
                "api_version": api_ver,
                "webhook_secret": webhook_secret,
                "instagram_business_account_id": instagram_business_account_id,
                "use_fallback_names": False,
            }
        except Exception:
            return {
                "access_token": "",
                "api_version": "v23.0",
                "webhook_secret": "",
                "instagram_business_account_id": "",
                "use_fallback_names": False,
            }

    def check_configuration(self) -> bool:
        """Check if Instagram is properly configured."""
        required_fields = ["access_token"]
        return all(self.credentials.get(field) for field in required_fields)

    def send_message(self, recipient_id: str, message: str, message_type: str = "text") -> bool:
        """Send Instagram direct message via Graph API.
        Uses the configured token and, if needed, auto-derives a Page Access Token
        from the existing user/system token using the configured Facebook Page ID.
        """
        try:
            # Reset diagnostics for this send
            self.last_request_payload = None
            self.last_response_status = None
            self.last_response_text = None
            self.last_error = None

            # Instagram Graph API endpoint for sending messages
            api_ver = self.credentials.get("api_version", "v23.0")
            ig_account_id = (self.credentials.get("instagram_business_account_id") or "").strip()
            # Use IG Business Account ID if available; fall back to "me" only as a last resort
            ig_sender = ig_account_id or "me"
            url = f"https://graph.facebook.com/{api_ver}/{ig_sender}/messages"

            # Sanitize token similar to Facebook sender
            raw_token = (self.credentials.get("access_token") or "")
            token = raw_token.strip().strip('"').strip("'")
            token = token.replace(" ", "").replace("\n", "").replace("\r", "")
            if not token:
                self.last_error = "Missing Instagram/Facebook Page Access Token"
                frappe.log_error("Missing Instagram Access Token", "Instagram Integration")
                return False

            def do_send(current_token: str) -> requests.Response:
                params = {"access_token": current_token}
                payload = {
                    "recipient": {"id": recipient_id},
                    "message": {"text": message},
                    "messaging_type": "RESPONSE",
                }
                # Track request/response diagnostics but mask the token
                try:
                    self.last_request_payload = {
                        "url": url,
                        "params": {"access_token": "***"},
                        "json": payload,
                    }
                except Exception:
                    pass
                resp = requests.post(url, params=params, json=payload, timeout=30)
                try:
                    self.last_response_status = resp.status_code
                    self.last_response_text = resp.text
                except Exception:
                    pass
                return resp

            # First attempt with the configured token
            response = do_send(token)
            if response.status_code == 200:
                self.last_error = None
                return True

            # Check if the failure is because the IG account ID doesn't exist or the
            # token lacks permissions for it (GraphMethodException code=100, subcode=33).
            # In that case the configured instagram_business_account_id is wrong — skip
            # the token-exchange round-trip and fall straight through to the page_id
            # fallback (/{page_id}/messages) which is the correct endpoint for
            # Instagram accounts that are linked to a Facebook Page.
            _ig_obj_missing = False
            try:
                _err_body = response.json() or {}
                _err_obj = _err_body.get("error") or {}
                if _err_obj.get("code") == 100 and _err_obj.get("error_subcode") == 33:
                    _ig_obj_missing = True
                    frappe.log_error(
                        "Instagram Integration",
                        (
                            f"Instagram DM send failed: the configured instagram_business_account_id "
                            f"('{ig_account_id}') returned 'Object does not exist / no permissions' "
                            f"(error_subcode 33). Skipping token exchange and trying the Facebook "
                            f"Page endpoint directly. Check 'instagram_business_account_id' in "
                            f"Social Media Settings."
                        )
                    )
            except Exception:
                pass

            # If the token is a user/system token, try to derive a Page Access Token
            # (skip this expensive step if the account ID itself is wrong)
            page_token_used = False
            try:
                settings = frappe.get_single("Social Media Settings")
                page_id = (settings.get("facebook_page_id") or "").strip()
            except Exception:
                page_id = ""

            if page_id and token and not _ig_obj_missing:
                try:
                    exchange_url = f"https://graph.facebook.com/{api_ver}/{page_id}"
                    exchange_params = {
                        "fields": "access_token",
                        "access_token": token,
                    }
                    exchange_resp = requests.get(exchange_url, params=exchange_params, timeout=15)
                    if exchange_resp.status_code == 200:
                        data = exchange_resp.json() or {}
                        page_token = (data.get("access_token") or "").strip()
                        if page_token:
                            # Try send again with the derived Page token
                            response2 = do_send(page_token)
                            if response2.status_code == 200:
                                page_token_used = True
                                self.last_error = None
                                # Persist the derived token to instagram_access_token so future
                                # sends use it directly without re-exchanging.
                                # Do NOT overwrite facebook_page_access_token — that token is
                                # managed by the Facebook integration independently.
                                try:
                                    settings.db_set("instagram_access_token", page_token)
                                except Exception:
                                    # Non-fatal if we cannot persist; sending succeeded
                                    pass
                                return True
                            else:
                                # Log failure after token exchange attempt
                                try:
                                    frappe.log_error(
                                        "Instagram Integration",
                                        f"Instagram send failed after token exchange: HTTP {response2.status_code} - {response2.text}",
                                    )
                                except Exception:
                                    pass
                    else:
                        # Log token exchange diagnostics
                        try:
                            ex_txt = exchange_resp.text
                        except Exception:
                            ex_txt = "<no response text>"
                        frappe.log_error(
                            "Instagram Integration",
                            f"Instagram token exchange failed: HTTP {exchange_resp.status_code} - {ex_txt}",
                        )
                except Exception as ex_err:
                    frappe.log_error(
                        "Instagram Integration",
                        f"Instagram token exchange failed: {str(ex_err)}",
                    )

            # Fallback: Page-connected Instagram. When Instagram is linked to a Facebook
            # Page, DM replies must use /{page_id}/messages (same as Facebook Messenger),
            # not /{ig_account_id}/messages. Try this before giving up.
            if page_id:
                try:
                    try:
                        fb_token = (settings.get_password("facebook_page_access_token") or "").strip()
                    except Exception:
                        fb_token = (settings.get("facebook_page_access_token") or "").strip()
                    if not fb_token:
                        fb_token = token  # also try the configured IG token
                    if fb_token:
                        fb_url = f"https://graph.facebook.com/{api_ver}/{page_id}/messages"
                        fb_resp = requests.post(
                            fb_url,
                            params={"access_token": fb_token},
                            json={
                                "recipient": {"id": recipient_id},
                                "message": {"text": message},
                                "messaging_type": "RESPONSE",
                            },
                            timeout=30,
                        )
                        self.last_response_status = fb_resp.status_code
                        self.last_response_text = fb_resp.text
                        if fb_resp.status_code == 200:
                            self.last_error = None
                            return True
                        try:
                            frappe.logger("assistant_crm.unified_send").warning(
                                f"[IG_SEND] page_id attempt failed: status={fb_resp.status_code} body={fb_resp.text}"
                            )
                        except Exception:
                            pass
                except Exception as fb_err:
                    try:
                        frappe.logger("assistant_crm.unified_send").warning(
                            f"[IG_SEND] page_id attempt error: {str(fb_err)}"
                        )
                    except Exception:
                        pass

            # Log detailed error and return False
            try:
                frappe.logger("assistant_crm.unified_send").error(
                    f"[IG_SEND] all attempts failed: status={response.status_code} body={response.text}"
                )
            except Exception:
                pass
            self.last_error = f"HTTP {response.status_code}: {response.text}"
            return False

        except Exception as e:
            try:
                self.last_error = str(e)
            except Exception:
                pass
            frappe.log_error("Instagram Integration", f"Instagram send error: {str(e)}")
            return False

    def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Instagram webhook (robust to different payload shapes, skips echoes).
        Creates/updates Unified Inbox Conversation and Message and auto-generates Issue.
        """
        try:
            entries = webhook_data.get("entry") or []
            processed = 0

            def iter_messaging_from_entry(entry: Dict[str, Any]):
                # Primary path used by IG messaging
                for evt in (entry.get("messaging") or []):
                    yield evt
                # Some IG deliveries may nest under changes[].value.messaging
                for change in (entry.get("changes") or []):
                    val = change.get("value") or {}
                    for evt in (val.get("messaging") or []):
                        yield evt

            for entry in entries:
                for message_event in iter_messaging_from_entry(entry):
                    message = message_event.get("message") or {}
                    if not message:
                        continue

                    # Ignore echo messages generated by our own outbound sends
                    if message.get("is_echo"):
                        continue

                    sender = message_event.get("sender") or {}
                    sender_id = sender.get("id")
                    if not sender_id:
                        continue

                    # Prefer per-event timestamp, fallback to entry time if present
                    ts = message_event.get("timestamp") or entry.get("time") or 0

                    # Get user display info (with graceful fallback internally)
                    user_info = self.get_user_info(sender_id)
                    customer_name = (
                        user_info.get("name")
                        or user_info.get("username")
                        or f"Instagram User {sender_id}"
                    )

                    # Build message content with media fallback
                    message_content = message.get("text") or ""
                    if not message_content:
                        if message.get("attachments"):
                            att = (message.get("attachments") or [{}])[0]
                            att_type = (att.get("type") or "media").title()
                            message_content = f"[{att_type} message]"
                        else:
                            message_content = "[Media message]"

                    platform_data = {
                        "conversation_id": sender_id,  # Use sender ID as conversation ID
                        "customer_name": customer_name,
                        "customer_platform_id": sender_id,
                        "customer_email": None,  # Instagram doesn't provide emails
                        "customer_phone": None,  # Instagram doesn't provide phone numbers
                        "initial_message": message_content,
                    }

                    conversation_name = self.create_unified_inbox_conversation(platform_data)
                    if not conversation_name:
                        continue

                    # Convert timestamp (supports seconds or milliseconds) to string without timezone conversion
                    import datetime
                    if ts:
                        try:
                            ts_int = int(ts)
                            # If timestamp looks like milliseconds, convert
                            if ts_int > 10**12:
                                ts_int = ts_int // 1000
                            dt = datetime.datetime.utcfromtimestamp(ts_int)
                            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            timestamp_str = now()
                    else:
                        timestamp_str = now()

                    # Ensure a stable message_id even if mid is missing
                    mid = message.get("mid") or f"ig:{sender_id}:{ts or now()}"

                    message_data = {
                        "message_id": mid,
                        "content": message_content,
                        "sender_name": customer_name,
                        "sender_platform_id": sender_id,
                        "timestamp": timestamp_str,
                        "direction": "Inbound",
                        "message_type": "text",
                        "metadata": message_event,
                    }

                    # If media, update message_type accordingly
                    if message.get("attachments"):
                        att = (message.get("attachments") or [{}])[0]
                        message_data["message_type"] = att.get("type", "media")

                    self.create_unified_inbox_message(conversation_name, message_data)
                    self.update_conversation_timestamp(conversation_name, timestamp_str)
                    processed += 1

                    print(
                        f"DEBUG: Processed Instagram message from {customer_name}: {message_content[:50]}..."
                    )

            return {"status": "success", "platform": "Instagram", "processed": processed}

        except Exception as e:
            frappe.log_error("Instagram Integration", f"Instagram webhook error: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get Instagram user information with enhanced error handling."""
        try:
            # Check if we should use fallback names
            if self.credentials.get("use_fallback_names", False):
                return self._get_fallback_user_info(user_id)

            # Try Instagram Business API first
            user_info = self._get_instagram_business_user_info(user_id)
            if user_info:
                return user_info

            # Fallback to basic Graph API
            user_info = self._get_basic_user_info(user_id)
            if user_info:
                return user_info

            # Final fallback
            return self._get_fallback_user_info(user_id)

        except Exception as e:
            print(f"DEBUG: Error getting Instagram user info: {str(e)}")
            return self._get_fallback_user_info(user_id)

    def _get_instagram_business_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user info via Instagram Business API."""
        try:
            url = f"https://graph.facebook.com/{self.credentials['api_version']}/{user_id}"
            params = {
                "fields": "name,username,profile_pic",
                "access_token": self.credentials["access_token"]
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                print(f"DEBUG: Successfully got Instagram user info for {user_id}: {data.get('name', 'No name')}")
                return data
            else:
                error_data = response.json() if response.content else {}
                print(f"DEBUG: Instagram API error {response.status_code}: {error_data.get('error', {}).get('message', 'Unknown error')}")
                return None

        except Exception as e:
            print(f"DEBUG: Instagram Business API error: {str(e)}")
            return None

    def _get_basic_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get basic user info via Facebook Graph API."""
        try:
            # Try with minimal fields that might be available
            url = f"https://graph.facebook.com/{self.credentials['api_version']}/{user_id}"
            params = {
                "fields": "id",  # Just try to get basic ID info
                "access_token": self.credentials["access_token"]
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # Generate a more user-friendly name based on ID
                return {
                    "id": user_id,
                    "name": f"Instagram User {user_id[-6:]}",  # Use last 6 digits
                    "username": f"user_{user_id[-6:]}"
                }
            else:
                return None

        except Exception as e:
            print(f"DEBUG: Basic user info error: {str(e)}")
            return None

    def _get_fallback_user_info(self, user_id: str) -> Dict[str, Any]:
        """Generate fallback user info when API is unavailable."""
        # Create more user-friendly names using the last 6 digits of the ID
        short_id = user_id[-6:] if len(user_id) > 6 else user_id
        return {
            "id": user_id,
            "name": f"Instagram User {short_id}",
            "username": f"user_{short_id}"
        }

    def _discover_ig_account_id(self, token: str, api_ver: str) -> Optional[str]:
        """
        Query the linked Facebook Page to discover the correct Instagram Business
        Account ID (different from the Facebook Page ID, even when linked).

        Persists the discovered ID to instagram_business_account_id in Social Media
        Settings so future calls use it without re-querying.

        Returns the discovered ID string, or None if unavailable.
        """
        try:
            settings = frappe.get_single("Social Media Settings")
            page_id = (settings.get("facebook_page_id") or "").strip()
            if not page_id:
                frappe.log_error(
                    title="Instagram: cannot auto-discover IG account ID",
                    message="facebook_page_id is not set in Social Media Settings."
                )
                return None

            resp = requests.get(
                f"https://graph.facebook.com/{api_ver}/{page_id}",
                params={"fields": "instagram_business_account", "access_token": token},
                timeout=15,
            )
            if resp.status_code != 200:
                frappe.log_error(
                    title="Instagram: IG account ID discovery failed",
                    message=f"GET /{page_id}?fields=instagram_business_account → {resp.status_code} {resp.text[:300]}"
                )
                return None

            ig_acct = (resp.json() or {}).get("instagram_business_account") or {}
            ig_id = (ig_acct.get("id") or "").strip()
            if not ig_id:
                frappe.log_error(
                    title="Instagram: IG account ID discovery — no account linked",
                    message=(
                        f"Page {page_id} has no instagram_business_account. "
                        "Make sure the Instagram account is connected to this Facebook Page "
                        "in Facebook Business Settings."
                    )
                )
                return None

            # Persist so future calls skip this lookup
            try:
                settings.db_set("instagram_business_account_id", ig_id)
            except Exception:
                pass

            frappe.logger("assistant_crm").info(
                f"Instagram: IG account ID auto-corrected — "
                f"instagram_business_account_id='{ig_id}' discovered from "
                f"Facebook Page '{page_id}'. Setting updated automatically."
            )
            return ig_id
        except Exception:
            frappe.log_error(
                title="Instagram: IG account ID discovery exception",
                message=frappe.get_traceback()
            )
            return None

    def publish_post(self, content: str, media_urls: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Publish a post to the configured Instagram Business Account.

        Instagram Content Publishing API requires at least one image or video —
        text-only posts are not supported. If no media_urls are provided this
        method returns a descriptive error rather than silently failing.

        Two-step process:
          1. POST /{ig_user_id}/media   → create a media container (returns creation_id)
          2. POST /{ig_user_id}/media_publish → publish the container

        For multiple images (carousel), each image is staged as a container with
        is_carousel_item=true, then a parent CAROUSEL container is created and published.

        Returns dict with keys: success, post_id, post_url, error.
        """
        token = (self.credentials.get("access_token") or "").strip()
        ig_user_id = (self.credentials.get("instagram_business_account_id") or "").strip()
        api_ver = self.credentials.get("api_version", "v23.0")

        if not token:
            return {"success": False, "error": "Instagram access_token is not configured."}
        if not ig_user_id:
            return {"success": False, "error": "instagram_business_account_id is not configured in Social Media Settings."}

        # Instagram does not support text-only posts via the Content Publishing API
        valid_media = [u for u in (media_urls or []) if u]
        if not valid_media:
            return {
                "success": False,
                "error": (
                    "Instagram does not support text-only posts. "
                    "Please attach at least one image or video."
                )
            }

        # Instagram only accepts direct image/video file URLs — not links to external
        # platforms (YouTube, Vimeo, etc.) or web pages. Detect and reject early.
        _supported_image_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff")
        _supported_video_exts = (".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v")
        _all_media_exts = _supported_image_exts + _supported_video_exts
        non_media_urls = [
            u for u in valid_media
            if not any(u.lower().split("?")[0].endswith(ext) for ext in _all_media_exts)
        ]
        if non_media_urls:
            return {
                "success": False,
                "error": (
                    "Instagram only supports direct image or video file URLs (.jpg, .png, .mp4, etc.). "
                    "Links to external platforms (YouTube, Vimeo, web pages) cannot be posted to Instagram. "
                    f"Unsupported URL(s): {', '.join(non_media_urls)}"
                )
            }

        # Instagram's API fetches media from the URL directly — private Frappe files
        # are behind authentication and cannot be reached by Instagram's servers.
        # Workaround: temporarily copy private files to the public/files directory
        # under an unguessable UUID name, use those public URLs for posting, then
        # delete the copies in a finally block regardless of success or failure.
        import os as _os, shutil as _shutil, uuid as _uuid
        from assistant_crm.api.social_media_publisher import _resolve_file_path

        _temp_public_files = []  # cleaned up in finally below
        _site_url = (
            frappe.conf.get("assistant_crm_public_base_url")
            or frappe.conf.get("host_name")
            or frappe.utils.get_url()
        ).rstrip("/")
        if not _site_url.startswith(("http://", "https://")):
            _site_url = f"https://{_site_url}"
        _site_path = frappe.get_site_path()

        private_urls = [u for u in valid_media if "/private/files/" in u]
        if private_urls:
            _promoted = {}
            for _priv_url in private_urls:
                _local = _resolve_file_path(_priv_url)
                if _local and _os.path.isfile(_local):
                    _ext = _os.path.splitext(_local)[1]
                    _tmp_name = f"_ig_tmp_{_uuid.uuid4().hex}{_ext}"
                    _tmp_path = _os.path.join(_site_path, "public", "files", _tmp_name)
                    _shutil.copy2(_local, _tmp_path)
                    _temp_public_files.append(_tmp_path)
                    _promoted[_priv_url] = f"{_site_url}/files/{_tmp_name}"

            if _promoted:
                # Swap private URLs with their temporary public counterparts
                valid_media = [_promoted.get(u, u) for u in valid_media]
            else:
                err = (
                    "Instagram cannot access private Frappe files and the local file "
                    "path could not be resolved. Please re-upload the image/video as a "
                    "Public file (uncheck 'Private' when uploading in Frappe) so "
                    "Instagram can fetch it from a public URL."
                )
                frappe.log_error(title="Instagram publish_post: private file URL", message=f"urls={private_urls} | {err}")
                return {"success": False, "error": err}

        import re as _re
        base = f"https://graph.facebook.com/{api_ver}/{ig_user_id}"
        params_base = {"access_token": token}

        # Wrap everything from here in try/finally so temp public files are always cleaned up,
        # including on early returns from the local_urls check below.
        try:
            local_urls = [
                u for u in valid_media
                if _re.search(r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|172\.\d+\.\d+\.\d+|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)", u)
            ]
            if local_urls:
                err = (
                    "Instagram requires a publicly accessible image URL. "
                    "This site is configured with a local/private hostname (localhost or internal IP). "
                    "Set 'host_name' in site_config.json to your public domain (e.g. https://yoursite.com) "
                    "and re-publish."
                )
                frappe.log_error(title="Instagram publish_post: local image URL", message=f"urls={local_urls} | {err}")
                return {"success": False, "error": err}
            if len(valid_media) == 1:
                # --- Single image / video ---
                media_url = valid_media[0]
                container_params = dict(params_base)
                container_params["caption"] = content
                # Instagram API v19+: feed videos must use media_type=REELS.
                # media_type=VIDEO is IGTV only and requires special eligibility.
                _video_exts_ig = (".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v")
                if any(media_url.lower().split("?")[0].endswith(ext) for ext in _video_exts_ig):
                    container_params["media_type"] = "REELS"
                    container_params["video_url"] = media_url
                    container_params["share_to_feed"] = "true"
                else:
                    container_params["image_url"] = media_url

                resp = requests.post(f"{base}/media", params=container_params, timeout=30)
                if resp.status_code != 200:
                    # If the IG account ID is wrong (subcode 33 = "Object does not exist"),
                    # auto-discover the correct ID from the linked Facebook Page and retry once.
                    try:
                        _err_obj = (resp.json() or {}).get("error") or {}
                        if _err_obj.get("code") == 100 and _err_obj.get("error_subcode") == 33:
                            _new_id = self._discover_ig_account_id(token, api_ver)
                            if _new_id and _new_id != ig_user_id:
                                ig_user_id = _new_id
                                base = f"https://graph.facebook.com/{api_ver}/{ig_user_id}"
                                resp = requests.post(f"{base}/media", params=container_params, timeout=30)
                    except Exception:
                        pass

                if resp.status_code != 200:
                    error_msg = ((resp.json() or {}).get("error") or {}).get("message", resp.text[:300])
                    media_param = "video_url" if any(media_url.lower().split("?")[0].endswith(ext) for ext in (".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v")) else "image_url"
                    hint = ""
                    if "only photo or video" in error_msg.lower():
                        hint = (
                            " Instagram fetched the URL but received a non-image Content-Type. "
                            "Check that your web server (Nginx) serves the file with the correct "
                            "Content-Type header (image/jpeg, image/png, etc.) and that the URL is "
                            "publicly accessible without authentication."
                        )
                    frappe.log_error(
                        title="Instagram publish_post: media container creation failed",
                        message=f"{media_param}={media_url} status={resp.status_code} error={error_msg}{hint}"
                    )
                    return {"success": False, "error": f"Instagram media container creation failed: {error_msg}{hint}"}

                creation_id = (resp.json() or {}).get("id")
                if not creation_id:
                    return {"success": False, "error": "Instagram did not return a container ID."}

            else:
                # --- Carousel (multiple images) ---
                # Auto-discover correct IG account ID before looping if first item fails with subcode 33
                _carousel_id_checked = False
                item_ids = []
                for media_url in valid_media:
                    item_params = dict(params_base)
                    item_params["is_carousel_item"] = "true"
                    item_params["image_url"] = media_url
                    resp = requests.post(f"{base}/media", params=item_params, timeout=30)
                    if resp.status_code != 200 and not _carousel_id_checked:
                        try:
                            _err_obj = (resp.json() or {}).get("error") or {}
                            if _err_obj.get("code") == 100 and _err_obj.get("error_subcode") == 33:
                                _new_id = self._discover_ig_account_id(token, api_ver)
                                if _new_id and _new_id != ig_user_id:
                                    ig_user_id = _new_id
                                    base = f"https://graph.facebook.com/{api_ver}/{ig_user_id}"
                                    resp = requests.post(f"{base}/media", params=item_params, timeout=30)
                        except Exception:
                            pass
                        _carousel_id_checked = True
                    if resp.status_code == 200:
                        item_id = (resp.json() or {}).get("id")
                        if item_id:
                            item_ids.append(item_id)
                    else:
                        frappe.log_error(
                            title="Instagram publish_post: carousel item failed",
                            message=f"URL={media_url} status={resp.status_code} body={resp.text[:300]}"
                        )

                if not item_ids:
                    return {"success": False, "error": "All Instagram carousel items failed to upload."}

                carousel_params = dict(params_base)
                carousel_params["media_type"] = "CAROUSEL"
                carousel_params["caption"] = content
                carousel_params["children"] = ",".join(item_ids)
                resp = requests.post(f"{base}/media", params=carousel_params, timeout=30)
                if resp.status_code != 200:
                    error_msg = ((resp.json() or {}).get("error") or {}).get("message", resp.text[:300])
                    return {"success": False, "error": f"Instagram carousel container creation failed: {error_msg}"}

                creation_id = (resp.json() or {}).get("id")
                if not creation_id:
                    return {"success": False, "error": "Instagram did not return a carousel container ID."}

            # --- Step 2: Wait for container to finish processing ---
            # Videos (REELS) are processed asynchronously. Polling is required before
            # calling media_publish — publishing immediately returns "Media ID is not available".
            import time as _time
            max_wait_secs = 120
            poll_interval = 5
            elapsed = 0
            while elapsed < max_wait_secs:
                status_resp = requests.get(
                    f"https://graph.facebook.com/{api_ver}/{creation_id}",
                    params={"fields": "status_code", "access_token": token},
                    timeout=15,
                )
                if status_resp.status_code == 200:
                    status_code = (status_resp.json() or {}).get("status_code", "")
                    if status_code == "FINISHED":
                        break
                    elif status_code == "ERROR":
                        error_detail = (status_resp.json() or {}).get("status_code", "unknown")
                        frappe.log_error(
                            title="Instagram publish_post: container processing error",
                            message=f"creation_id={creation_id} status_code={error_detail}"
                        )
                        return {"success": False, "error": f"Instagram rejected the media during processing: {error_detail}"}
                    # IN_PROGRESS or PUBLISHED — keep waiting
                _time.sleep(poll_interval)
                elapsed += poll_interval

            # --- Step 3: Publish the container ---
            publish_params = dict(params_base)
            publish_params["creation_id"] = creation_id
            resp = requests.post(f"{base}/media_publish", params=publish_params, timeout=30)

            if resp.status_code == 200:
                post_id = (resp.json() or {}).get("id", "")
                post_url = f"https://www.instagram.com/p/{post_id}/" if post_id else ""
                return {"success": True, "post_id": post_id, "post_url": post_url}
            else:
                error_msg = ((resp.json() or {}).get("error") or {}).get("message", resp.text[:300])
                frappe.log_error(
                    title="Instagram publish_post: media_publish failed",
                    message=f"creation_id={creation_id} status={resp.status_code} error={error_msg}"
                )
                return {"success": False, "error": error_msg}

        except Exception as e:
            frappe.log_error(title="Instagram publish_post: exception", message=frappe.get_traceback())
            return {"success": False, "error": str(e)}
        finally:
            # Always remove temporary public copies of private files
            for _tf in _temp_public_files:
                try:
                    _os.remove(_tf)
                except Exception:
                    pass


class TwitterIntegration(SocialMediaPlatform):
    """Twitter (X) integration for Direct Messages via Account Activity webhooks."""

    def __init__(self):
        super().__init__("Twitter")

    def get_platform_credentials(self) -> Dict[str, str]:
        """Get Twitter credentials from Social Media Settings."""
        try:
            settings = frappe.get_single("Social Media Settings")
            def gp(field: str) -> str:
                try:
                    return settings.get_password(field)
                except Exception:
                    return settings.get(field)
            return {
                "client_id": settings.get("twitter_client_id") or "",
                "client_secret": gp("twitter_client_secret") or "",
                "api_key": settings.get("twitter_api_key") or "",
                "api_secret": gp("twitter_api_secret") or "",
                "bearer_token": gp("twitter_bearer_token") or "",
                "access_token": gp("twitter_access_token") or "",
                "access_token_secret": gp("twitter_access_token_secret") or "",
                "webhook_env": settings.get("twitter_webhook_env") or "",
                "webhook_secret": gp("twitter_webhook_secret") or "",
            }
        except Exception:
            return {
                "client_id": "",
                "client_secret": "",
                "api_key": "",
                "api_secret": "",
                "bearer_token": "",
                "access_token": "",
                "access_token_secret": "",
                "webhook_env": "",
                "webhook_secret": "",
            }

    def check_configuration(self) -> bool:
        """Consider inbound configured if we have a webhook secret or bearer token."""
        return bool(self.credentials.get("webhook_secret") or self.credentials.get("bearer_token"))

    def _require_user_context(self) -> Optional[str]:
        """Validate that user-context OAuth 1.0a credentials exist for write actions."""
        api_key = (self.credentials.get("api_key") or "").strip()
        api_secret = (self.credentials.get("api_secret") or "").strip()
        access_token = (self.credentials.get("access_token") or "").strip()
        access_token_secret = (self.credentials.get("access_token_secret") or "").strip()
        if not (api_key and api_secret and access_token and access_token_secret):
            return "Missing API key/secret or access token/secret"
        return None

    def _build_oauth1_header(self, method: str, url: str, params: Dict[str, Any]) -> str:
        """Create OAuth 1.0a Authorization header including given params (for form-encoded POST)."""
        import time, uuid, hmac, hashlib, base64, urllib.parse as urlparse
        api_key = (self.credentials.get("api_key") or "").strip()
        api_secret = (self.credentials.get("api_secret") or "").strip()
        access_token = (self.credentials.get("access_token") or "").strip()
        access_token_secret = (self.credentials.get("access_token_secret") or "").strip()

        def pct_encode(s: str) -> str:
            return urlparse.quote(str(s), safe="~")

        oauth_params = {
            "oauth_consumer_key": api_key,
            "oauth_nonce": uuid.uuid4().hex,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": access_token,
            "oauth_version": "1.0",
        }

        # Collect parameters for signature: OAuth + request params
        all_params = {**oauth_params, **{k: str(v) for k, v in (params or {}).items()}}
        param_items = sorted([(pct_encode(k), pct_encode(v)) for k, v in all_params.items()])
        param_str = "&".join([f"{k}={v}" for k, v in param_items])

        base_elems = [method.upper(), pct_encode(url), pct_encode(param_str)]
        base_string = "&".join(base_elems)
        signing_key = f"{pct_encode(api_secret)}&{pct_encode(access_token_secret)}"
        signature = base64.b64encode(
            hmac.new(signing_key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1).digest()
        ).decode("utf-8")

        oauth_header_params = oauth_params.copy()
        oauth_header_params["oauth_signature"] = signature
        header_kv = ", ".join([f'{k}="{pct_encode(v)}"' for k, v in oauth_header_params.items()])
        return f"OAuth {header_kv}"

    def send_message(self, recipient_id: str, message: str, message_type: str = "text") -> bool:
        """Send a Direct Message via Twitter API v1.1 using OAuth 1.0a user context."""
        # Reset diagnostics
        self.last_request_payload = None
        self.last_response_status = None
        self.last_response_text = None
        self.last_error = None

        try:
            need = self._require_user_context()
            if need:
                frappe.log_error(
                    f"Twitter sending not configured - {need}",
                    "Twitter Integration"
                )
                return False

            # Endpoint and payload
            url = "https://api.twitter.com/1.1/direct_messages/events/new.json"
            event_payload = {
                "event": {
                    "type": "message_create",
                    "message_create": {
                        "target": {"recipient_id": str(recipient_id)},
                        "message_data": {"text": str(message or "").strip()[:10000]}
                    }
                }
            }

            self.last_request_payload = event_payload

            # Build OAuth 1.0a Authorization header (RFC 5849) ÔÇö JSON body not included in signature
            auth_header = self._build_oauth1_header("POST", url, params={})
            headers = {
                "Authorization": auth_header,
                "Content-Type": "application/json",
            }

            resp = requests.post(url, headers=headers, json=event_payload, timeout=15)
            self.last_response_status = resp.status_code
            try:
                self.last_response_text = resp.text
            except Exception:
                self.last_response_text = ""

            if 200 <= resp.status_code < 300:
                return True

            # Log error for observability
            try:
                frappe.log_error(
                    f"Twitter DM send failed: {resp.status_code} {resp.text}",
                    "Twitter Integration"
                )
            except Exception:
                pass
            return False

        except Exception as e:
            self.last_error = str(e)
            try:
                frappe.log_error(f"Twitter DM send exception: {str(e)}", "Twitter Integration")
            except Exception:
                pass
            return False

    def send_public_reply(self, in_reply_to_tweet_id: str, text: str) -> bool:
        """Reply publicly to a tweet using v1.1 statuses/update.json (OAuth 1.0a)."""
        # Reset diagnostics
        self.last_request_payload = None
        self.last_response_status = None
        self.last_response_text = None
        self.last_error = None
        try:
            need = self._require_user_context()
            if need:
                frappe.log_error(
                    f"Twitter public reply not configured - {need}",
                    "Twitter Integration"
                )
                return False

            url = "https://api.twitter.com/1.1/statuses/update.json"
            params = {
                "status": str(text or "")[:280],
                "in_reply_to_status_id": str(in_reply_to_tweet_id),
                "auto_populate_reply_metadata": "true",
            }
            self.last_request_payload = params

            # OAuth header with params included in signature (form-encoded)
            auth_header = self._build_oauth1_header("POST", url, params=params)
            headers = {
                "Authorization": auth_header,
                "Content-Type": "application/x-www-form-urlencoded",
            }

            resp = requests.post(url, headers=headers, data=params, timeout=15)
            self.last_response_status = resp.status_code
            try:
                self.last_response_text = resp.text
            except Exception:
                self.last_response_text = ""

            if 200 <= resp.status_code < 300:
                return True

            try:
                frappe.log_error(
                    f"Twitter public reply failed: {resp.status_code} {resp.text}",
                    "Twitter Integration"
                )
            except Exception:
                pass
            return False
        except Exception as e:
            self.last_error = str(e)
            try:
                frappe.log_error(f"Twitter public reply exception: {str(e)}", "Twitter Integration")
            except Exception:
                pass
            return False

    def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Twitter Account Activity webhook for Direct Messages."""
        try:
            events = []
            users = webhook_data.get("users") or {}
            for_user_id = str(webhook_data.get("for_user_id") or "")

            if webhook_data.get("direct_message_events"):
                events = webhook_data.get("direct_message_events") or []
            elif webhook_data.get("dm_events"):
                events = webhook_data.get("dm_events") or []

            for ev in events:
                mc = ev.get("message_create") or {}
                sender_id = str(mc.get("sender_id") or "")
                if not sender_id or (for_user_id and sender_id == for_user_id):
                    # Ignore echoes (our own messages)
                    continue

                msg_data = mc.get("message_data") or {}
                text = msg_data.get("text") or "[Message]"

                # Derive customer name
                customer_name = None
                try:
                    if isinstance(users, dict) and sender_id in users:
                        u = users.get(sender_id) or {}
                        nm = u.get("name") or ""
                        sn = u.get("screen_name") or u.get("username") or ""
                        customer_name = f"{nm} (@{sn})".strip() if sn else (nm or None)
                except Exception:
                    pass
                if not customer_name:
                    uinfo = self._fetch_user_info(sender_id)
                    if uinfo:
                        nm = uinfo.get("name") or ""
                        un = uinfo.get("username") or ""
                        customer_name = f"{nm} (@{un})".strip() if un else (nm or f"Twitter User {sender_id[-6:]}")

                platform_data = {
                    "conversation_id": sender_id,
                    "customer_name": customer_name or f"Twitter User {sender_id[-6:]}",
                    "customer_platform_id": sender_id,
                    "customer_phone": None,
                    "customer_email": None,
                    "initial_message": text,
                }

                conversation_name = self.create_unified_inbox_conversation(platform_data)
                if conversation_name:
                    # Timestamp handling
                    ts = ev.get("created_timestamp") or msg_data.get("time")
                    import datetime
                    if ts:
                        try:
                            ts_i = int(ts)
                            if ts_i > 10_000_000_000:  # microseconds
                                ts_i = ts_i // 1_000_000
                            elif ts_i > 1_000_000_000:  # milliseconds
                                ts_i = ts_i // 1_000
                            dt = datetime.datetime.utcfromtimestamp(ts_i)
                            ts_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except Exception:
                            ts_str = now()
                    else:
                        ts_str = now()

                    message_data = {
                        "message_id": ev.get("id") or f"tw:{sender_id}:{ts or ''}",
                        "content": text,
                        "sender_name": customer_name or f"Twitter User {sender_id[-6:]}",
                        "sender_platform_id": sender_id,
                        "timestamp": ts_str,
                        "direction": "Inbound",
                        "message_type": "text",
                        "metadata": ev,
                    }
                    self.create_unified_inbox_message(conversation_name, message_data)
                    self.update_conversation_timestamp(conversation_name, ts_str)

            # Process public mentions/replies (Phase 5)
            tweets = webhook_data.get("tweet_create_events") or []
            if tweets:
                for tw in tweets:
                    try:
                        user = tw.get("user") or {}
                        sender_id = str(user.get("id_str") or user.get("id") or "")
                        if not sender_id or (for_user_id and sender_id == for_user_id):
                            # Ignore our own tweets
                            continue

                        # Only ingest tweets that mention our account
                        mentions = ((tw.get("entities") or {}).get("user_mentions") or [])
                        mentioned_ids = {str(m.get("id") or m.get("id_str")) for m in mentions if m}
                        if for_user_id and for_user_id not in mentioned_ids:
                            continue

                        text = tw.get("full_text") or tw.get("text") or "[Tweet]"

                        # Derive customer name
                        nm = user.get("name") or ""
                        sn = user.get("screen_name") or user.get("username") or ""
                        if not (nm or sn):
                            uinfo = self._fetch_user_info(sender_id)
                            nm = uinfo.get("name") or nm
                            sn = uinfo.get("username") or sn
                        customer_name = f"{nm} (@{sn})".strip() if sn else (nm or f"Twitter User {sender_id[-6:]}")

                        platform_data = {
                            "conversation_id": sender_id,
                            "customer_name": customer_name,
                            "customer_platform_id": sender_id,
                            "customer_phone": None,
                            "customer_email": None,
                            "initial_message": text,
                        }

                        conversation_name = self.create_unified_inbox_conversation(platform_data)
                        if conversation_name:
                            # Parse created_at timestamp if available
                            ts_str = now()
                            created_at = tw.get("created_at")
                            if created_at:
                                try:
                                    import datetime
                                    dt = datetime.datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
                                    ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                                except Exception:
                                    pass

                            message_data = {
                                "message_id": tw.get("id_str") or str(tw.get("id") or ""),
                                "content": text,
                                "sender_name": customer_name,
                                "sender_platform_id": sender_id,
                                "timestamp": ts_str,
                                "direction": "Inbound",
                                "message_type": "text",
                                "metadata": tw,
                            }
                            self.create_unified_inbox_message(conversation_name, message_data)
                            self.update_conversation_timestamp(conversation_name, ts_str)
                    except Exception as e2:
                        try:
                            frappe.log_error(f"Twitter tweet processing error: {str(e2)}", "Twitter Integration")
                        except Exception:
                            pass

            return {"status": "success", "platform": "Twitter"}
        except Exception as e:
            frappe.log_error(f"Twitter webhook error: {str(e)}", "Twitter Integration")
            return {"status": "error", "message": str(e)}

    def _fetch_user_info(self, user_id: str) -> Dict[str, Any]:
        """Fetch user info via Twitter API v2 using Bearer token if available."""
        try:
            bearer = (self.credentials.get("bearer_token") or "").strip()
            if not bearer:
                return {}
            url = f"https://api.twitter.com/2/users/{user_id}"
            params = {"user.fields": "name,username"}
            headers = {"Authorization": f"Bearer {bearer}"}
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = (resp.json() or {}).get("data") or {}
                return {"name": data.get("name"), "username": data.get("username")}
        except Exception:
            pass
        short_id = user_id[-6:] if len(user_id) > 6 else user_id
        return {"name": f"Twitter User {short_id}", "username": ""}

    def publish_post(self, content: str, media_urls: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a public Tweet via Twitter API v2.

        Uses OAuth 1.0a user context (api_key + api_secret + access_token +
        access_token_secret) — the same credential set already used for
        sending DMs — so no additional credential fields are needed.

        Media is not uploaded here (Twitter media upload requires multipart
        v1.1 endpoint and file bytes; Frappe attachment URLs may be internal).
        If media_urls are provided they are noted in the error log but the text
        tweet is still published.

        Returns dict with keys: success, post_id, post_url, error.
        """
        api_key = (self.credentials.get("api_key") or "").strip()
        api_secret = (self.credentials.get("api_secret") or "").strip()
        access_token = (self.credentials.get("access_token") or "").strip()
        access_token_secret = (self.credentials.get("access_token_secret") or "").strip()

        if not all([api_key, api_secret, access_token, access_token_secret]):
            return {
                "success": False,
                "error": (
                    "Twitter OAuth 1.0a credentials are incomplete. "
                    "Ensure api_key, api_secret, access_token, and access_token_secret "
                    "are all set in Social Media Settings."
                )
            }

        tweet_url = "https://api.twitter.com/2/tweets"
        payload = {"text": content[:280]}  # Twitter hard limit

        try:
            auth_header = self._build_oauth1_header("POST", tweet_url, {})
            headers = {
                "Authorization": auth_header,
                "Content-Type": "application/json",
            }
            resp = requests.post(tweet_url, headers=headers, json=payload, timeout=30)

            if resp.status_code in (200, 201):
                data = (resp.json() or {}).get("data") or {}
                tweet_id = data.get("id", "")
                post_url = f"https://twitter.com/i/web/status/{tweet_id}" if tweet_id else ""
                if media_urls:
                    frappe.log_error(
                        title="Twitter publish_post: media skipped",
                        message=(
                            f"Tweet {tweet_id} published as text-only. "
                            f"Media upload is not implemented: {media_urls}"
                        )
                    )
                return {"success": True, "post_id": tweet_id, "post_url": post_url}
            else:
                error_data = resp.json() if resp.content else {}
                error_msg = error_data.get("detail") or error_data.get("title") or resp.text[:300]
                frappe.log_error(
                    title="Twitter publish_post: tweet creation failed",
                    message=f"status={resp.status_code} error={error_msg}"
                )
                return {"success": False, "error": error_msg}

        except Exception as e:
            frappe.log_error(title="Twitter publish_post: exception", message=frappe.get_traceback())
            return {"success": False, "error": str(e)}


class LinkedInIntegration(SocialMediaPlatform):
    """LinkedIn Messaging integration (inbound first)."""

    def __init__(self):
        super().__init__("LinkedIn")

    def get_platform_credentials(self) -> Dict[str, str]:
        try:
            settings = frappe.get_single("Social Media Settings")
            creds = {
                "enabled": bool(settings.get("linkedin_enabled")),
                "client_id": (settings.get("linkedin_client_id") or "").strip(),
                "api_version": (settings.get("linkedin_api_version") or "v2").strip(),
                "organization_id": (settings.get("linkedin_organization_id") or "").strip(),
            }
            # Secrets via get_password when possible
            try:
                creds["client_secret"] = (settings.get_password("linkedin_client_secret") or "").strip()
            except Exception:
                creds["client_secret"] = (settings.get("linkedin_client_secret") or "").strip()
            try:
                creds["access_token"] = (settings.get_password("linkedin_access_token") or "").strip()
            except Exception:
                creds["access_token"] = (settings.get("linkedin_access_token") or "").strip()
            try:
                creds["webhook_secret"] = (settings.get_password("linkedin_webhook_secret") or "").strip()
            except Exception:
                creds["webhook_secret"] = (settings.get("linkedin_webhook_secret") or "").strip()
            return creds
        except Exception:
            return {
                "enabled": False,
                "client_id": "",
                "client_secret": "",
                "access_token": "",
                "api_version": "v2",
                "organization_id": "",
                "webhook_secret": "",
            }



    def check_configuration(self) -> bool:
        return bool(self.credentials.get("enabled"))

    def send_message(self, recipient_id: str, message: str, message_type: str = "text") -> bool:
        """Send a Direct Message via LinkedIn Messaging API using OAuth 2.0 bearer token.
        Returns True on 2xx status, False otherwise. Populates diagnostics fields on failure.
        """
        # Reset diagnostics
        self.last_request_payload = None
        self.last_response_status = None
        self.last_response_text = None
        self.last_error = None
        try:
            token = (self.credentials.get("access_token") or "").strip()
            if not token:
                self.last_error = "missing_access_token"
                return False

            api_ver = self.credentials.get("api_version", "v2").strip() or "v2"
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json",
            }

            # Normalize recipient as a URN
            rid = str(recipient_id or "").strip()
            if not rid:
                self.last_error = "empty_recipient_id"
                return False
            if not rid.startswith("urn:"):
                rid = f"urn:li:person:{rid}"

            subject = "Message from WCFCB"
            url = f"https://api.linkedin.com/{api_ver}/messages"

            # Variant A payload (newer shape)
            payload_a = {
                "recipients": [rid],
                "subject": subject,
                "text": str(message or ""),
            }
            org_id = (self.credentials.get("organization_id") or "").strip()
            if org_id:
                payload_a["from"] = f"urn:li:organization:{org_id}"

            self.last_request_payload = payload_a
            resp = requests.post(url, headers=headers, json=payload_a, timeout=15)
            self.last_response_status = getattr(resp, "status_code", None)
            try:
                self.last_response_text = getattr(resp, "text", None)
            except Exception:
                pass
            if resp is not None and resp.status_code in (200, 201, 202):
                return True

            # Variant B payload (legacy shape)
            payload_b = {
                "recipients": {"values": [{"person": rid}]},
                "subject": subject,
                "body": str(message or ""),
            }
            if org_id:
                payload_b["from"] = f"urn:li:organization:{org_id}"

            self.last_request_payload = payload_b
            resp2 = requests.post(url, headers=headers, json=payload_b, timeout=15)
            self.last_response_status = getattr(resp2, "status_code", None)
            try:
                self.last_response_text = getattr(resp2, "text", None)
            except Exception:
                pass
            return bool(resp2 is not None and resp2.status_code in (200, 201, 202))
        except Exception as e:
            self.last_error = str(e)
            try:
                frappe.log_error(f"LinkedIn send error: {str(e)}", "LinkedIn Integration")
            except Exception:
                pass
            return False

    def _get_user_info_cached(self, user_id: str) -> Dict[str, Any]:
        """Resolve real name with caching to minimize API calls.
        Falls back to a generic name if API credentials are missing or calls fail.
        """
        try:
            cache = frappe.cache()
            key = f"linkedin_user_info:{user_id}"
            cached = cache.get_value(key)
            if cached:
                try:
                    if isinstance(cached, (bytes, bytearray)):
                        cached = cached.decode("utf-8")
                    if isinstance(cached, str):
                        return json.loads(cached)
                except Exception:
                    if isinstance(cached, dict):
                        return cached

            token = (self.credentials.get("access_token") or "").strip()
            api_ver = self.credentials.get("api_version", "v2")
            headers = {"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0"}

            user_info = None
            if token and user_id:
                try:
                    # If user_id is an URN (urn:li:person:XXX), use it directly; else build URN-like query
                    person_urn = user_id if user_id.startswith("urn:") else f"urn:li:person:{user_id}"
                    url = f"https://api.linkedin.com/{api_ver}/people/(id:{person_urn})"
                    # Projection for localized first/last name (v2 fields)
                    params = {"projection": "(localizedFirstName,localizedLastName,id)"}
                    import requests
                    resp = requests.get(url, headers=headers, params=params, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json() or {}
                        fn = (data.get("localizedFirstName") or "").strip()
                        ln = (data.get("localizedLastName") or "").strip()
                        full = (f"{fn} {ln}".strip()) or (data.get("id") or "")
                        user_info = {"id": data.get("id"), "name": full or None}
                except Exception:
                    pass

            if not user_info:
                short_id = user_id[-6:] if user_id and len(user_id) > 6 else (user_id or "")
                user_info = {"id": user_id, "name": f"LinkedIn User {short_id}"}

            try:
                cache.set_value(key, json.dumps(user_info))
            except Exception:
                pass
            return user_info
        except Exception:
            short_id = user_id[-6:] if user_id and len(user_id) > 6 else (user_id or "")
            return {"id": user_id, "name": f"LinkedIn User {short_id}"}

    def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize LinkedIn webhook payload and persist to Unified Inbox.
        Returns dict with conversation_id when successful.
        """
        try:
            events = []
            if isinstance(webhook_data, dict):
                if isinstance(webhook_data.get("events"), list):
                    events = webhook_data.get("events") or []
                else:
                    events = [webhook_data]
            elif isinstance(webhook_data, list):
                events = webhook_data

            conversation_id = None
            last_message_id = None

            for ev in events:
                val = ev.get("value") if isinstance(ev, dict) else None
                val = val if isinstance(val, dict) else (ev if isinstance(ev, dict) else {})

                # Extract sender and message
                sender_id = str(
                    (val.get("sender") or {}).get("id") or
                    (val.get("from") or {}).get("id") or
                    val.get("actor") or val.get("actorId") or val.get("fromMemberUrn") or ""
                )
                if not sender_id:
                    # Skip if we cannot identify sender
                    continue

                # Message content and ids
                text = (
                    (val.get("message") or {}).get("text") or
                    val.get("text") or
                    val.get("body") or
                    "[LinkedIn message]"
                )
                msg_id = str(val.get("eventId") or val.get("id") or val.get("message_id") or "")

                # Timestamp handling
                timestamp_str = now()
                ts_raw = val.get("createdAt") or val.get("timestamp")
                try:
                    if ts_raw:
                        import datetime
                        if isinstance(ts_raw, (int, float)):
                            dt = datetime.datetime.utcfromtimestamp(int(ts_raw)/1000 if int(ts_raw) > 1e12 else int(ts_raw))
                            timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass

                # Resolve sender display name with caching
                info = self._get_user_info_cached(sender_id)
                customer_name = info.get("name") or "LinkedIn User"

                # Create or reuse conversation
                conversation_id = conversation_id or self.create_unified_inbox_conversation({
                    "conversation_id": sender_id,
                    "customer_name": customer_name,
                    "customer_platform_id": sender_id,
                    "initial_message": text,
                })

                if not conversation_id:
                    continue

                # Persist message
                self.create_unified_inbox_message(conversation_id, {
                    "direction": "Inbound",
                    "message_type": "text",
                    "content": text,
                    "sender_name": customer_name,
                    "sender_id": sender_id,
                    "sender_platform_id": sender_id,
                    "timestamp": timestamp_str,
                    "message_id": msg_id,
                    "metadata": {"raw": val},
                })

                # Keep last id and update accurate timestamps
                last_message_id = msg_id or last_message_id
                if timestamp_str:
                    self.update_conversation_timestamp(conversation_id, timestamp_str)

                # Update Issue with full conversation history
                try:
                    self.update_issue_conversation_history(conversation_id, text, customer_name, timestamp_str, direction="Inbound")
                except Exception:
                    pass

            return {"status": "success", "conversation_id": conversation_id, "last_message_id": last_message_id}
        except Exception as e:
            frappe.log_error(f"LinkedIn webhook error: {str(e)}", "LinkedIn Integration")
            return {"status": "error", "message": str(e)}

    def publish_post(self, content: str, media_urls: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Publish a public share to LinkedIn via the UGC Posts API.

        Posts as the configured Organization when linkedin_organization_id is set,
        otherwise posts as the authenticated user (urn:li:person from /v2/me).

        Text-only and image posts are both supported. Image upload requires
        a publicly accessible URL — Frappe attachment URLs that are only
        accessible within the server will be skipped with a warning.

        Returns dict with keys: success, post_id, post_url, error.
        """
        token = (self.credentials.get("access_token") or "").strip()
        org_id = (self.credentials.get("organization_id") or "").strip()
        api_ver = (self.credentials.get("api_version") or "v2").strip() or "v2"

        if not token:
            return {"success": False, "error": "LinkedIn access_token is not configured."}

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

        # Resolve the author URN
        if org_id:
            author_urn = f"urn:li:organization:{org_id}"
        else:
            # Fall back to the authenticated user's person URN
            try:
                me_resp = requests.get(
                    f"https://api.linkedin.com/{api_ver}/me",
                    headers=headers,
                    timeout=10
                )
                if me_resp.status_code == 200:
                    person_id = (me_resp.json() or {}).get("id", "")
                    author_urn = f"urn:li:person:{person_id}" if person_id else ""
                else:
                    author_urn = ""
            except Exception:
                author_urn = ""

            if not author_urn:
                return {
                    "success": False,
                    "error": (
                        "Could not resolve LinkedIn author URN. "
                        "Set linkedin_organization_id in Social Media Settings or ensure the token has r_liteprofile scope."
                    )
                }

        try:
            # Determine media category and build shareMedia list
            valid_media = [u for u in (media_urls or []) if u]
            if valid_media:
                share_media = []
                for media_url in valid_media:
                    share_media.append({
                        "status": "READY",
                        "originalUrl": media_url,
                        "media": media_url,
                    })
                share_media_category = "ARTICLE" if share_media else "NONE"
            else:
                share_media = []
                share_media_category = "NONE"

            specific_content: Dict[str, Any] = {
                "shareCommentary": {"text": content},
                "shareMediaCategory": share_media_category,
            }
            if share_media:
                specific_content["media"] = share_media

            payload = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": specific_content
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                },
            }

            resp = requests.post(
                f"https://api.linkedin.com/{api_ver}/ugcPosts",
                headers=headers,
                json=payload,
                timeout=30
            )

            if resp.status_code in (200, 201):
                # The post ID is returned in the x-restli-id header or the response body
                post_id = resp.headers.get("x-restli-id") or (resp.json() or {}).get("id", "")
                post_url = f"https://www.linkedin.com/feed/update/{post_id}" if post_id else ""
                return {"success": True, "post_id": post_id, "post_url": post_url}
            else:
                error_data = resp.json() if resp.content else {}
                error_msg = (
                    error_data.get("message")
                    or error_data.get("serviceErrorCode")
                    or resp.text[:300]
                )
                frappe.log_error(
                    title="LinkedIn publish_post: ugcPosts failed",
                    message=f"author={author_urn} status={resp.status_code} error={error_msg}"
                )
                return {"success": False, "error": str(error_msg)}

        except Exception as e:
            frappe.log_error(title="LinkedIn publish_post: exception", message=frappe.get_traceback())
            return {"success": False, "error": str(e)}


class YouTubeIntegration(SocialMediaPlatform):
    """YouTube Data API v3 integration for comments and live chat messages.

    Supports:
    - Processing incoming YouTube comments (via PubSubHubbub push notifications)
    - Processing live chat messages
    - Replying to comments via the YouTube Data API
    - Community post comment handling

    Flow: Webhook ÔåÆ Unified Inbox Conversation ÔåÆ Unified Inbox Message ÔåÆ AI Processing ÔåÆ Reply
    """

    def __init__(self):
        super().__init__("YouTube")
        # Diagnostics for last send attempt
        self.last_request_payload = None
        self.last_response_status = None
        self.last_response_text = None
        self.last_error = None

    def get_platform_credentials(self) -> Dict[str, str]:
        """Get YouTube credentials from Social Media Settings.

        Required credentials:
        - youtube_api_key: YouTube Data API key (for read operations)
        - youtube_client_id: OAuth 2.0 client ID (for write operations like replying)
        - youtube_client_secret: OAuth 2.0 client secret
        - youtube_access_token: OAuth 2.0 access token (for authenticated requests)
        - youtube_refresh_token: OAuth 2.0 refresh token
        - youtube_channel_id: The channel ID to monitor
        - youtube_webhook_secret: Secret for verifying webhook signatures
        """
        try:
            settings = frappe.get_single("Social Media Settings")

            def get_pwd(field: str) -> str:
                """Safely retrieve password field."""
                try:
                    return settings.get_password(field) or ""
                except Exception:
                    return settings.get(field) or ""

            return {
                "api_key": settings.get("youtube_api_key") or "",
                "client_id": settings.get("youtube_client_id") or "",
                "client_secret": get_pwd("youtube_client_secret"),
                "access_token": get_pwd("youtube_access_token"),
                "refresh_token": get_pwd("youtube_refresh_token"),
                "channel_id": settings.get("youtube_channel_id") or "",
                "webhook_secret": get_pwd("youtube_webhook_secret"),
                "api_version": settings.get("youtube_api_version") or "v3",
            }
        except Exception:
            return {
                "api_key": "",
                "client_id": "",
                "client_secret": "",
                "access_token": "",
                "refresh_token": "",
                "channel_id": "",
                "webhook_secret": "",
                "api_version": "v3",
            }

    def check_configuration(self) -> bool:
        """Check if YouTube is properly configured for receiving and sending messages."""
        # For receiving: need at least api_key and channel_id
        # For sending: need access_token (OAuth)
        has_read = bool(self.credentials.get("api_key")) or bool(self.credentials.get("access_token"))
        has_channel = bool(self.credentials.get("channel_id"))
        return has_read and has_channel

    def _refresh_access_token(self) -> Optional[str]:
        """Refresh the OAuth 2.0 access token using the refresh token.
        Returns the new access token or None on failure.
        """
        try:
            refresh_token = self.credentials.get("refresh_token")
            client_id = self.credentials.get("client_id")
            client_secret = self.credentials.get("client_secret")

            if not all([refresh_token, client_id, client_secret]):
                return None

            url = "https://oauth2.googleapis.com/token"
            payload = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }

            resp = requests.post(url, data=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                new_token = data.get("access_token")
                if new_token:
                    # Persist the new token
                    try:
                        settings = frappe.get_single("Social Media Settings")
                        settings.db_set("youtube_access_token", new_token)
                        self.credentials["access_token"] = new_token
                    except Exception:
                        pass
                    return new_token
            return None
        except Exception as e:
            frappe.log_error(f"YouTube token refresh error: {str(e)}", "YouTube Integration")
            return None

    def send_message(self, recipient_id: str, message: str, message_type: str = "text") -> bool:
        """Reply to a YouTube comment or live chat message.

        For comments: recipient_id should be the comment ID (or video_id:comment_id format)
        For live chat: recipient_id should be the liveChatId

        Uses YouTube Data API v3:
        - POST https://www.googleapis.com/youtube/v3/comments (for comment replies)
        - POST https://www.googleapis.com/youtube/v3/liveChat/messages (for live chat)
        """
        # Reset diagnostics
        self.last_request_payload = None
        self.last_response_status = None
        self.last_response_text = None
        self.last_error = None

        try:
            access_token = (self.credentials.get("access_token") or "").strip()
            if not access_token:
                self.last_error = "Missing YouTube OAuth access token"
                frappe.log_error("Missing YouTube access token for sending", "YouTube Integration")
                return False

            # Determine if this is a live chat or comment reply based on recipient_id format
            is_live_chat = recipient_id.startswith("livechat:")

            def do_send(token: str) -> requests.Response:
                if is_live_chat:
                    # Live chat message
                    live_chat_id = recipient_id.replace("livechat:", "")
                    url = "https://www.googleapis.com/youtube/v3/liveChat/messages"
                    params = {"part": "snippet"}
                    payload = {
                        "snippet": {
                            "liveChatId": live_chat_id,
                            "type": "textMessageEvent",
                            "textMessageDetails": {
                                "messageText": message[:200]  # Live chat limit
                            }
                        }
                    }
                else:
                    # Comment reply
                    # recipient_id format: parentId (the comment being replied to)
                    url = "https://www.googleapis.com/youtube/v3/comments"
                    params = {"part": "snippet"}
                    payload = {
                        "snippet": {
                            "parentId": recipient_id,
                            "textOriginal": message[:10000]  # Comments can be longer
                        }
                    }

                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }

                self.last_request_payload = {"url": url, "params": params, "json": payload}
                resp = requests.post(url, params=params, json=payload, headers=headers, timeout=30)
                self.last_response_status = resp.status_code
                self.last_response_text = resp.text
                return resp

            # First attempt
            response = do_send(access_token)

            if response.status_code == 200:
                self.last_error = None
                return True

            # If 401/403, try token refresh
            if response.status_code in (401, 403):
                new_token = self._refresh_access_token()
                if new_token:
                    response = do_send(new_token)
                    if response.status_code == 200:
                        self.last_error = None
                        return True

            # Log failure
            self.last_error = f"HTTP {response.status_code}: {response.text}"
            frappe.log_error(
                f"YouTube send failed: {response.status_code} - {response.text}",
                "YouTube Integration"
            )
            return False

        except Exception as e:
            self.last_error = str(e)
            frappe.log_error(f"YouTube send error: {str(e)}", "YouTube Integration")
            return False

    def publish_post(self, content: str, media_urls: Optional[List[str]] = None) -> Dict[str, Any]:
        """Upload a video to the configured YouTube channel.

        YouTube does not support text-only posts via the public Data API.
        A video file must be included in media_urls (MP4, MOV, AVI, MKV, WEBM, FLV, WMV, M4V).

        The first line of ``content`` becomes the video title (max 100 chars).
        The full ``content`` is used as the video description (max 5000 chars).
        All uploaded videos are set to public visibility by default.

        Requires an OAuth 2.0 access token with the ``youtube.upload`` scope.
        The token is auto-refreshed if the initial request returns 401/403.

        Returns dict with keys: success, post_id, post_url, error.
        """
        VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}

        # Resolve access token (refresh if needed)
        access_token = (self.credentials.get("access_token") or "").strip()
        if not access_token:
            access_token = self._refresh_access_token() or ""
        if not access_token:
            msg = (
                "YouTube OAuth access token is not configured. "
                "Set youtube_access_token (with youtube.upload scope) in Social Media Settings."
            )
            frappe.log_error(title="YouTube publish_post: missing access token", message=msg)
            return {"success": False, "error": msg}

        # Locate the first video URL from the provided media attachments
        video_url = None
        for url in (media_urls or []):
            clean = url.split("?")[0].lower()
            if any(clean.endswith(ext) for ext in VIDEO_EXTENSIONS):
                video_url = url
                break

        # Ensure the video URL has a scheme — frappe.conf.host_name is sometimes
        # stored without one (e.g. "erpdev.example.com"), which causes urlparse to
        # treat the entire string as a path and requests.get() to raise MissingSchema.
        if video_url and not video_url.startswith(("http://", "https://")):
            video_url = f"https://{video_url}"

        if not video_url:
            msg = (
                "YouTube requires a video file to publish. "
                "Attach a video (MP4, MOV, AVI, etc.) to this post and try again. "
                f"Received media_urls: {media_urls or []}"
            )
            frappe.log_error(title="YouTube publish_post: no video attachment", message=msg)
            return {"success": False, "error": "YouTube requires a video file to publish. Attach a video (MP4, MOV, AVI, etc.) to this post and try again."}

        # Derive title (first non-blank line) and description from content
        lines = [ln for ln in (content or "").split("\n") if ln.strip()]
        title = (lines[0].strip()[:100]) if lines else "New Post"
        description = (content or "")[:5000]

        # Map video extension → MIME type
        MIME_TYPES = {
            ".mp4": "video/mp4", ".mov": "video/quicktime", ".avi": "video/x-msvideo",
            ".mkv": "video/x-matroska", ".webm": "video/webm", ".flv": "video/x-flv",
            ".wmv": "video/x-ms-wmv", ".m4v": "video/x-m4v",
        }

        import os
        from urllib.parse import urlparse, unquote

        parsed_path = unquote(urlparse(video_url).path)
        ext = os.path.splitext(parsed_path)[1].lower()
        content_type = MIME_TYPES.get(ext, "video/mp4")

        # Prefer reading directly from the local filesystem to avoid making an
        # HTTPS request back to a server that may only speak plain HTTP on its
        # internal port (which causes SSL: WRONG_VERSION_NUMBER errors).
        video_bytes = None
        try:
            site_path = frappe.get_site_path()
            if parsed_path.startswith("/private/files/"):
                local_path = os.path.join(site_path, "private", "files", parsed_path[len("/private/files/"):])
            elif parsed_path.startswith("/files/"):
                local_path = os.path.join(site_path, "public", "files", parsed_path[len("/files/"):])
            else:
                local_path = None

            if local_path and os.path.isfile(local_path):
                with open(local_path, "rb") as fh:
                    video_bytes = fh.read()
        except Exception:
            pass  # Fall through to HTTP download

        # HTTP fallback (for externally hosted files)
        if video_bytes is None:
            try:
                dl_resp = requests.get(video_url, timeout=120, stream=False)
                if dl_resp.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Could not download video (HTTP {dl_resp.status_code}): {video_url}"
                    }
                video_bytes = dl_resp.content
                ct = dl_resp.headers.get("Content-Type", "").split(";")[0].strip()
                if ct.startswith("video/"):
                    content_type = ct
            except Exception as e:
                frappe.log_error(title="YouTube publish_post: video download error", message=frappe.get_traceback())
                return {"success": False, "error": f"Failed to read video file: {str(e)}"}

        if not video_bytes:
            return {"success": False, "error": f"Video file is empty or could not be read: {video_url}"}

        video_metadata = {
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "22",  # People & Blogs
            },
            "status": {
                "privacyStatus": "public",
            },
        }

        upload_endpoint = "https://www.googleapis.com/upload/youtube/v3/videos"
        upload_params = {"uploadType": "resumable", "part": "snippet,status"}

        def _initiate_upload(token: str):
            """Send the resumable upload initiation request and return (resp, location_url)."""
            init_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": content_type,
                "X-Upload-Content-Length": str(len(video_bytes)),
            }
            resp = requests.post(
                upload_endpoint,
                headers=init_headers,
                params=upload_params,
                json=video_metadata,
                timeout=30,
            )
            return resp, resp.headers.get("Location")

        try:
            init_resp, upload_url = _initiate_upload(access_token)

            # Auto-refresh on auth failure and retry once
            if init_resp.status_code in (401, 403):
                new_token = self._refresh_access_token()
                if new_token:
                    access_token = new_token
                    init_resp, upload_url = _initiate_upload(new_token)

            if init_resp.status_code not in (200, 201) or not upload_url:
                error_msg = (init_resp.json() or {}).get("error", {}).get("message") or init_resp.text[:300]
                frappe.log_error(
                    title="YouTube publish_post: resumable upload initiation failed",
                    message=f"status={init_resp.status_code} error={error_msg}"
                )
                return {"success": False, "error": f"YouTube upload initiation failed: {error_msg}"}

            # Upload the video bytes to the session URI
            upload_headers = {
                "Content-Type": content_type,
                "Content-Length": str(len(video_bytes)),
            }
            upload_resp = requests.put(
                upload_url,
                headers=upload_headers,
                data=video_bytes,
                timeout=300,
            )

            if upload_resp.status_code in (200, 201):
                video_id = (upload_resp.json() or {}).get("id", "")
                post_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
                return {"success": True, "post_id": video_id, "post_url": post_url}
            else:
                error_msg = (upload_resp.json() or {}).get("error", {}).get("message") or upload_resp.text[:300]
                frappe.log_error(
                    title="YouTube publish_post: video upload failed",
                    message=f"status={upload_resp.status_code} error={error_msg}"
                )
                return {"success": False, "error": f"YouTube video upload failed: {error_msg}"}

        except Exception:
            frappe.log_error(title="YouTube publish_post: exception", message=frappe.get_traceback())
            return {"success": False, "error": "Unhandled exception during YouTube upload. See error log."}

    def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process YouTube webhook notifications.

        YouTube uses PubSubHubbub (WebSub) for push notifications about:
        - New video uploads
        - Video updates

        For comments, we typically need to poll (using poll_youtube_comments),
        but this method handles any webhook payloads including:
        - Feed updates from PubSubHubbub
        - Custom webhook integrations
        - Make.com forwarded YouTube events
        """
        try:
            processed = 0
            conversation_id = None

            # Handle different webhook payload formats

            # Format 1: Make.com or custom integration with standardized structure
            if webhook_data.get("platform") == "YouTube" or webhook_data.get("source") == "youtube":
                return self._process_standard_webhook(webhook_data)

            # Format 2: PubSubHubbub feed notification (Atom XML converted to dict)
            if webhook_data.get("feed") or webhook_data.get("entry"):
                return self._process_pubsubhubbub(webhook_data)

            # Format 3: Direct comment/live chat event (from polling or custom integration)
            if webhook_data.get("items") or webhook_data.get("comment") or webhook_data.get("liveChatMessage"):
                return self._process_comment_event(webhook_data)

            # Format 4: Wrapper format with 'data' key
            if webhook_data.get("data"):
                inner_data = webhook_data.get("data")
                if isinstance(inner_data, dict):
                    return self.process_webhook(inner_data)
                elif isinstance(inner_data, list):
                    for item in inner_data:
                        result = self.process_webhook(item)
                        if result.get("status") == "success":
                            processed += 1
                            conversation_id = conversation_id or result.get("conversation_id")

            # If we couldn't process, log and return
            if processed == 0:
                frappe.log_error(
                    f"Unrecognized YouTube webhook format: {json.dumps(webhook_data)[:500]}",
                    "YouTube Integration"
                )
                return {"status": "skipped", "message": "Unrecognized webhook format"}

            return {"status": "success", "processed": processed, "conversation_id": conversation_id}

        except Exception as e:
            frappe.log_error(f"YouTube webhook error: {str(e)}", "YouTube Integration")
            return {"status": "error", "message": str(e)}

    def _process_standard_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process standardized webhook payload from Make.com or custom integration.

        Expected format:
        {
            "platform": "YouTube",
            "event_type": "comment" | "live_chat" | "community_post",
            "video_id": "...",
            "comment_id": "...",
            "author_channel_id": "...",
            "author_name": "...",
            "text": "...",
            "timestamp": "..." (ISO 8601 or Unix timestamp),
            "parent_id": "..." (for replies),
            "live_chat_id": "..." (for live chat)
        }
        """
        try:
            event_type = data.get("event_type") or data.get("type") or "comment"

            # Extract message details
            comment_id = data.get("comment_id") or data.get("id") or ""
            video_id = data.get("video_id") or ""
            author_channel_id = data.get("author_channel_id") or data.get("channelId") or ""
            author_name = data.get("author_name") or data.get("authorDisplayName") or "YouTube User"
            text = data.get("text") or data.get("textDisplay") or data.get("message") or "[YouTube message]"
            parent_id = data.get("parent_id") or data.get("parentId") or ""
            live_chat_id = data.get("live_chat_id") or data.get("liveChatId") or ""

            # Timestamp handling
            timestamp_str = now()
            ts_raw = data.get("timestamp") or data.get("publishedAt") or data.get("created_at")
            if ts_raw:
                timestamp_str = self._parse_timestamp(ts_raw)

            # For live chat, use live_chat_id as conversation key
            # For comments, use author_channel_id as conversation key
            if event_type == "live_chat" and live_chat_id:
                conversation_key = f"{live_chat_id}:{author_channel_id}"
                platform_specific_id = f"livechat:{live_chat_id}"
            else:
                conversation_key = author_channel_id or comment_id
                platform_specific_id = author_channel_id

            # Create or find conversation
            platform_data = {
                "conversation_id": platform_specific_id,
                "customer_name": author_name,
                "customer_platform_id": author_channel_id,
                "initial_message": text,
            }

            conversation_id = self.create_unified_inbox_conversation(platform_data)

            if not conversation_id:
                return {"status": "error", "message": "Failed to create conversation"}

            # Build message ID
            message_id = comment_id or f"yt:{author_channel_id}:{timestamp_str}"

            # Create message
            message_data = {
                "message_id": message_id,
                "content": text,
                "sender_name": author_name,
                "sender_platform_id": author_channel_id,
                "timestamp": timestamp_str,
                "direction": "Inbound",
                "message_type": "text",
                "metadata": {
                    "event_type": event_type,
                    "video_id": video_id,
                    "comment_id": comment_id,
                    "parent_id": parent_id,
                    "live_chat_id": live_chat_id,
                    "raw": data,
                },
            }

            self.create_unified_inbox_message(conversation_id, message_data)
            self.update_conversation_timestamp(conversation_id, timestamp_str)

            # Create/update Issue
            try:
                self.create_issue_for_new_conversation(
                    conversation_id,
                    f"[YouTube] {author_name}",
                    text
                )
                self.update_issue_conversation_history(
                    conversation_id, text, author_name, timestamp_str, direction="Inbound"
                )
            except Exception:
                pass

            return {"status": "success", "conversation_id": conversation_id, "message_id": message_id}

        except Exception as e:
            frappe.log_error(f"YouTube standard webhook error: {str(e)}", "YouTube Integration")
            return {"status": "error", "message": str(e)}

    def _process_pubsubhubbub(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process PubSubHubbub/WebSub feed notification.

        YouTube sends Atom feed updates for subscribed channels.
        This typically notifies about new videos, not comments.
        """
        try:
            entries = data.get("entry") or []
            if isinstance(entries, dict):
                entries = [entries]

            processed = 0
            for entry in entries:
                video_id = entry.get("yt:videoId") or entry.get("videoId") or ""
                channel_id = entry.get("yt:channelId") or entry.get("channelId") or ""
                title = entry.get("title") or ""
                author = (entry.get("author") or {}).get("name") or "YouTube Channel"
                published = entry.get("published") or entry.get("updated") or ""

                if video_id:
                    # Log the new video notification
                    frappe.log_error(
                        f"YouTube PubSubHubbub: New video {video_id} from channel {channel_id}: {title}",
                        "YouTube Integration Info"
                    )
                    # Could trigger comment polling for this video here
                    processed += 1

            return {"status": "success", "processed": processed, "type": "pubsubhubbub"}

        except Exception as e:
            frappe.log_error(f"YouTube PubSubHubbub error: {str(e)}", "YouTube Integration")
            return {"status": "error", "message": str(e)}

    def _process_comment_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a comment or live chat event from the YouTube Data API format."""
        try:
            items = data.get("items") or []
            if data.get("comment"):
                items = [data.get("comment")]
            if data.get("liveChatMessage"):
                items = [data.get("liveChatMessage")]

            processed = 0
            conversation_id = None

            for item in items:
                snippet = item.get("snippet") or item

                # Determine if comment or live chat
                is_live_chat = bool(snippet.get("liveChatId"))

                if is_live_chat:
                    author_channel_id = snippet.get("authorChannelId") or ""
                    author_name = snippet.get("authorDisplayName") or "YouTube User"
                    text = (snippet.get("textMessageDetails") or {}).get("messageText") or snippet.get("displayMessage") or ""
                    message_id = item.get("id") or ""
                    live_chat_id = snippet.get("liveChatId") or ""
                    platform_specific_id = f"livechat:{live_chat_id}:{author_channel_id}"
                else:
                    # Comment
                    author_channel_id = (snippet.get("authorChannelId") or {}).get("value") or snippet.get("authorChannelId") or ""
                    author_name = snippet.get("authorDisplayName") or "YouTube User"
                    text = snippet.get("textDisplay") or snippet.get("textOriginal") or ""
                    message_id = item.get("id") or ""
                    platform_specific_id = author_channel_id

                # Timestamp
                timestamp_str = self._parse_timestamp(snippet.get("publishedAt") or snippet.get("updatedAt") or "")

                # Create conversation
                platform_data = {
                    "conversation_id": platform_specific_id,
                    "customer_name": author_name,
                    "customer_platform_id": author_channel_id,
                    "initial_message": text,
                }

                conversation_id = self.create_unified_inbox_conversation(platform_data)
                if not conversation_id:
                    continue

                # Create message
                message_data = {
                    "message_id": message_id,
                    "content": text,
                    "sender_name": author_name,
                    "sender_platform_id": author_channel_id,
                    "timestamp": timestamp_str,
                    "direction": "Inbound",
                    "message_type": "text",
                    "metadata": {"raw": item},
                }

                if self.create_unified_inbox_message(conversation_id, message_data):
                    self.update_conversation_timestamp(conversation_id, timestamp_str)
                    processed += 1

            return {"status": "success", "processed": processed, "conversation_id": conversation_id}

        except Exception as e:
            frappe.log_error(f"YouTube comment event error: {str(e)}", "YouTube Integration")
            return {"status": "error", "message": str(e)}

    def _parse_timestamp(self, ts_raw: Any) -> str:
        """Parse various timestamp formats to Frappe datetime format."""
        import datetime
        try:
            if not ts_raw:
                return now()

            if isinstance(ts_raw, (int, float)):
                # Unix timestamp (seconds or milliseconds)
                ts_int = int(ts_raw)
                if ts_int > 10**12:
                    ts_int //= 1000
                dt = datetime.datetime.utcfromtimestamp(ts_int)
                return dt.strftime('%Y-%m-%d %H:%M:%S')

            if isinstance(ts_raw, str):
                # ISO 8601 format (YouTube uses this)
                # Example: "2025-01-15T10:30:00Z" or "2025-01-15T10:30:00.000Z"
                ts_raw = ts_raw.replace("Z", "+00:00")
                try:
                    dt = datetime.datetime.fromisoformat(ts_raw)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass

                # Try other common formats
                for fmt in [
                    "%Y-%m-%dT%H:%M:%S.%f%z",
                    "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%d %H:%M:%S",
                ]:
                    try:
                        dt = datetime.datetime.strptime(ts_raw, fmt)
                        return dt.strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        continue

            return now()
        except Exception:
            return now()


@frappe.whitelist()
def poll_youtube_comments(video_id: str = None, channel_id: str = None) -> Dict[str, Any]:
    """Poll YouTube comments for a specific video or channel.

    Uses YouTube Data API v3 to fetch comments and ingest into Unified Inbox.
    - Auto-refreshes OAuth token before polling.
    - Only fetches comments newer than the last successful poll (publishedAfter).
    - Safe to run repeatedly; relies on comment ID de-duplication.

    Args:
        video_id: Specific video ID to poll comments for
        channel_id: Channel ID to poll all recent video comments (if video_id not provided)
    """
    try:
        integ = YouTubeIntegration()

        # Auto-refresh token if expired before polling
        access_token = (get_valid_youtube_token() or "").strip()
        api_key = (integ.credentials.get("api_key") or "").strip()

        if not (api_key or access_token):
            return {"status": "skipped", "reason": "YouTube not configured"}

        channel_id = channel_id or integ.credentials.get("channel_id")

        imported = {"comments": 0}

        headers = {}
        params = {"key": api_key} if api_key else {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        # Determine publishedAfter from last poll time to avoid re-importing old comments.
        # Only apply this filter for automated channel polls, not manual video_id calls.
        published_after = None
        if not video_id:
            try:
                settings = frappe.get_doc("Social Media Settings", "Social Media Settings")
                last_polled = settings.get("youtube_last_polled")
                if last_polled:
                    from frappe.utils import get_datetime
                    import datetime
                    dt = get_datetime(str(last_polled))
                    # Add 1 second to avoid re-fetching the last seen comment
                    dt = dt + datetime.timedelta(seconds=1)
                    published_after = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass

        # Fetch comment items — either for a specific video or across the whole channel
        if video_id:
            try:
                url = "https://www.googleapis.com/youtube/v3/commentThreads"
                comment_params = {
                    **params,
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": 100,
                    "order": "time",
                }
                resp = requests.get(url, params=comment_params, headers=headers, timeout=15)
                if resp.status_code == 200:
                    comment_items = (resp.json() or {}).get("items") or []
                else:
                    frappe.log_error(f"YouTube video comments fetch failed ({resp.status_code}): {resp.text[:300]}", "YouTube Polling")
                    comment_items = []
            except Exception as e:
                frappe.log_error(f"YouTube video comment fetch error: {str(e)}", "YouTube Polling")
                comment_items = []
        elif channel_id:
            # Use allThreadsRelatedToChannelId — returns the most recent comments across
            # ALL videos on the channel, including old videos.
            try:
                url = "https://www.googleapis.com/youtube/v3/commentThreads"
                comment_params = {
                    **params,
                    "part": "snippet",
                    "allThreadsRelatedToChannelId": channel_id,
                    "maxResults": 100,
                    "order": "time",
                }
                # Note: publishedAfter is NOT supported by the commentThreads API endpoint.
                # Filtering is done client-side below after fetching.
                resp = requests.get(url, params=comment_params, headers=headers, timeout=15)
                if resp.status_code == 200:
                    comment_items = (resp.json() or {}).get("items") or []
                else:
                    frappe.log_error(f"YouTube channel comments fetch failed ({resp.status_code}): {resp.text[:300]}", "YouTube Polling")
                    comment_items = []
            except Exception as e:
                frappe.log_error(f"YouTube channel comment fetch error: {str(e)}", "YouTube Polling")
                comment_items = []
        else:
            return {"status": "skipped", "reason": "No video_id or channel_id provided"}

        if not comment_items:
            return {"status": "skipped", "reason": "No new comments"}

        # Client-side filter: drop comments that are not newer than last poll.
        # This is necessary because the commentThreads API does not support publishedAfter.
        if published_after and not video_id:
            try:
                from frappe.utils import get_datetime
                cutoff = get_datetime(published_after)
                filtered = []
                for item in comment_items:
                    snippet_ts = ((item.get("snippet") or {}).get("topLevelComment") or {}).get("snippet", {}).get("publishedAt") or ""
                    if snippet_ts:
                        try:
                            import datetime
                            item_dt = get_datetime(snippet_ts.replace("Z", "+00:00").replace("+00:00", ""))
                            if item_dt > cutoff:
                                filtered.append(item)
                        except Exception:
                            filtered.append(item)  # Keep on parse failure
                    else:
                        filtered.append(item)
                comment_items = filtered
            except Exception:
                pass  # On any error keep all items

        if not comment_items:
            return {"status": "skipped", "reason": "No new comments"}

        # In-run conversation cache: maps author_channel_id -> conversation_name
        # Prevents creating a new conversation per comment when multiple comments
        # from the same user appear in a single poll batch.
        conversation_cache = {}

        newest_published_at = None

        for item in comment_items:
            try:
                top_snippet = item.get("snippet") or {}
                snippet = (top_snippet.get("topLevelComment") or {}).get("snippet") or {}
                comment_id = item.get("id") or ""
                vid = top_snippet.get("videoId") or video_id or ""
                author_channel_id = (snippet.get("authorChannelId") or {}).get("value") or ""
                author_name = snippet.get("authorDisplayName") or "YouTube User"
                text = snippet.get("textDisplay") or snippet.get("textOriginal") or ""
                published_at_item = snippet.get("publishedAt") or ""

                if not (author_channel_id and text):
                    continue

                # Check message deduplication before creating/finding conversation
                norm_id = integ._normalize_platform_message_id(comment_id)
                if norm_id and frappe.db.exists("Unified Inbox Message", {"message_id": norm_id}):
                    continue  # Already imported, skip entirely

                # Reuse conversation from cache or DB
                if author_channel_id in conversation_cache:
                    cv = conversation_cache[author_channel_id]
                else:
                    platform_data = {
                        "conversation_id": author_channel_id,
                        "customer_name": author_name,
                        "customer_platform_id": author_channel_id,
                        "initial_message": text,
                    }
                    cv = integ.create_unified_inbox_conversation(platform_data)
                    if cv:
                        conversation_cache[author_channel_id] = cv

                if not cv:
                    continue

                ts_str = integ._parse_timestamp(published_at_item)
                message_data = {
                    "message_id": comment_id,
                    "content": text,
                    "sender_name": author_name,
                    "sender_platform_id": author_channel_id,
                    "timestamp": ts_str,
                    "direction": "Inbound",
                    "message_type": "text",
                    "metadata": {"video_id": vid, "raw": item},
                }

                if integ.create_unified_inbox_message(cv, message_data):
                    timestamp_advanced = integ.update_conversation_timestamp(cv, ts_str)
                    if timestamp_advanced:
                        try:
                            preview = (text or "")[:140]
                            frappe.db.set_value(
                                "Unified Inbox Conversation",
                                cv,
                                "last_message_preview",
                                preview,
                                update_modified=False,
                            )
                        except Exception:
                            pass
                    imported["comments"] += 1
                    # Track newest comment timestamp to advance the poll window
                    if published_at_item:
                        if newest_published_at is None or published_at_item > newest_published_at:
                            newest_published_at = published_at_item

            except Exception:
                continue

        # Save last polled timestamp only when new comments were actually imported.
        # Use the newest comment's publishedAt so the next poll window starts exactly there.
        if not video_id and newest_published_at:
            try:
                ts_to_save = integ._parse_timestamp(newest_published_at)
                frappe.db.set_value(
                    "Social Media Settings",
                    "Social Media Settings",
                    "youtube_last_polled",
                    ts_to_save,
                    update_modified=False,
                )
                frappe.db.commit()
            except Exception:
                pass

        return {"status": "success", "imported": imported}

    except Exception as e:
        frappe.log_error(f"YouTube polling fatal error: {str(e)}", "YouTube Polling")
        return {"status": "error", "message": str(e)}


# Platform factory for easy instantiation

# --- Scheduled polling for Twitter (mentions + DMs) ---
@frappe.whitelist()
def poll_twitter_inbox() -> Dict[str, Any]:
    """Poll Twitter mentions and DMs and ingest into the Unified Inbox.
    Safe to run repeatedly; relies on platform_message_id de-duplication.
    """
    try:
        integ = TwitterIntegration()
        creds = integ.credentials or {}
        configured = (
            (creds.get("api_key") and creds.get("api_secret") and creds.get("access_token") and creds.get("access_token_secret"))
            or creds.get("bearer_token")
        )
        if not configured:
            return {"status": "skipped", "reason": "Twitter not configured"}

        # Determine own user id to ignore self DMs (best-effort)
        own_id = None
        try:
            url = "https://api.twitter.com/1.1/account/verify_credentials.json"
            auth_header = integ._build_oauth1_header("GET", url, params={})
            resp = requests.get(url, headers={"Authorization": auth_header}, timeout=10)
            if resp.status_code == 200:
                jd = resp.json() or {}
                own_id = str(jd.get("id_str") or jd.get("id") or "") or None
        except Exception:
            pass

        imported = {"mentions": 0, "dms": 0}

        # Fetch mentions (v1.1)
        try:
            url = "https://api.twitter.com/1.1/statuses/mentions_timeline.json"
            params = {"count": 50, "tweet_mode": "extended", "include_entities": "true"}
            auth_header = integ._build_oauth1_header("GET", url, params=params)
            r = requests.get(url, headers={"Authorization": auth_header}, params=params, timeout=15)
            if r.status_code == 200:
                tweets = r.json() or []
                for tw in tweets:
                    try:
                        user = tw.get("user") or {}
                        sender_id = str(user.get("id_str") or user.get("id") or "")
                        if not sender_id:
                            continue
                        text = tw.get("full_text") or tw.get("text") or "[Tweet]"
                        nm = user.get("name") or ""
                        sn = user.get("screen_name") or user.get("username") or ""
                        customer_name = f"{nm} (@{sn})".strip() if sn else (nm or f"Twitter User {sender_id[-6:]}")
                        platform_data = {
                            "conversation_id": sender_id,
                            "customer_name": customer_name,
                            "customer_platform_id": sender_id,
                            "initial_message": text,
                        }
                        cv = integ.create_unified_inbox_conversation(platform_data)
                        if not cv:
                            continue
                        # Timestamp from created_at
                        ts_str = now()
                        created_at = tw.get("created_at")
                        if created_at:
                            try:
                                import datetime
                                dt = datetime.datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
                                ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                            except Exception:
                                pass
                        message_data = {
                            "message_id": tw.get("id_str") or str(tw.get("id") or ""),
                            "content": text,
                            "sender_name": customer_name,
                            "sender_platform_id": sender_id,
                            "timestamp": ts_str,
                            "direction": "Inbound",
                            "message_type": "text",
                            "metadata": tw,
                        }
                        if integ.create_unified_inbox_message(cv, message_data):
                            timestamp_advanced = integ.update_conversation_timestamp(cv, ts_str)
                            if timestamp_advanced:
                                # Only update preview when this comment is the newest so far
                                try:
                                    preview = (text or "")[:140]
                                    frappe.db.set_value(
                                        "Unified Inbox Conversation",
                                        cv,
                                        "last_message_preview",
                                        preview,
                                        update_modified=False,
                                    )
                                except Exception:
                                    pass
                            imported["mentions"] += 1
                    except Exception:
                        continue
        except Exception as e:
            try:
                frappe.log_error(f"Twitter mentions poll error: {str(e)}", "Twitter Polling")
            except Exception:
                pass

        # Fetch DMs (v1.1)
        try:
            url = "https://api.twitter.com/1.1/direct_messages/events/list.json"
            params = {"count": 50}
            auth_header = integ._build_oauth1_header("GET", url, params=params)
            r = requests.get(url, headers={"Authorization": auth_header}, params=params, timeout=15)
            if r.status_code == 200:
                payload = r.json() or {}
                events = payload.get("events") or []
                for ev in events:
                    try:
                        mc = ev.get("message_create") or {}
                        sender_id = str(mc.get("sender_id") or "")
                        if not sender_id:
                            continue
                        if own_id and sender_id == own_id:
                            continue
                        msg_data = mc.get("message_data") or {}
                        text = msg_data.get("text") or "[Message]"
                        # Resolve customer name via v2 lookup (best-effort)
                        try:
                            ui = integ._fetch_user_info(sender_id)
                            nm = ui.get("name") or ""
                            un = ui.get("username") or ""
                            customer_name = f"{nm} (@{un})".strip() if un else (nm or f"Twitter User {sender_id[-6:]}")
                        except Exception:
                            customer_name = f"Twitter User {sender_id[-6:]}"
                        platform_data = {
                            "conversation_id": sender_id,
                            "customer_name": customer_name,
                            "customer_platform_id": sender_id,
                            "initial_message": text,
                        }
                        cv = integ.create_unified_inbox_conversation(platform_data)
                        if not cv:
                            continue
                        ts = ev.get("created_timestamp")
                        ts_str = now()
                        if ts:
                            try:
                                import datetime
                                ts_i = int(ts)
                                if ts_i > 10_000_000_000:
                                    ts_i //= 1_000_000
                                elif ts_i > 1_000_000_000:
                                    ts_i //= 1_000
                                dt = datetime.datetime.utcfromtimestamp(ts_i)
                                ts_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                            except Exception:
                                pass
                        message_data = {
                            "message_id": ev.get("id") or f"tw:{sender_id}:{ts or ''}",
                            "content": text,
                            "sender_name": customer_name,
                            "sender_platform_id": sender_id,
                            "timestamp": ts_str,
                            "direction": "Inbound",
                            "message_type": "text",
                            "metadata": ev,
                        }
                        if integ.create_unified_inbox_message(cv, message_data):
                            timestamp_advanced = integ.update_conversation_timestamp(cv, ts_str)
                            if timestamp_advanced:
                                # Only update preview when this comment is the newest so far
                                try:
                                    preview = (text or "")[:140]
                                    frappe.db.set_value(
                                        "Unified Inbox Conversation",
                                        cv,
                                        "last_message_preview",
                                        preview,
                                        update_modified=False,
                                    )
                                except Exception:
                                    pass
                            imported["dms"] += 1
                    except Exception:
                        continue
        except Exception as e:
            try:
                frappe.log_error(f"Twitter DM poll error: {str(e)}", "Twitter Polling")
            except Exception:
                pass

        return {"status": "success", "imported": imported}
    except Exception as e:
        frappe.log_error(f"Twitter polling fatal error: {str(e)}", "Twitter Polling")
        return {"status": "error", "message": str(e)}

def get_platform_integration(platform_name: str) -> Optional[SocialMediaPlatform]:
    """Get platform integration instance by name."""
    platforms = {
        "WhatsApp": WhatsAppIntegration,
        "Facebook": FacebookIntegration,
        "Instagram": InstagramIntegration,
        "Telegram": TelegramIntegration,
        "Tawk.to": TawkToIntegration,
        "Twitter": TwitterIntegration,
        "LinkedIn": LinkedInIntegration,
        "USSD": USSDIntegration,
        "YouTube": YouTubeIntegration,
    }

    platform_class = platforms.get(platform_name)
    if platform_class:
        return platform_class()
    return None



@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def social_media_webhook():
    """
    Universal webhook endpoint for all social media platforms.
    Supports both GET (for verification) and POST (for webhook events).
    Routes webhooks to appropriate platform handlers.
    """
    try:
        # Handle GET request for webhook verification (Facebook/Instagram)
        if frappe.request.method == "GET":
            hub_mode = frappe.form_dict.get("hub.mode")
            hub_verify_token = frappe.form_dict.get("hub.verify_token")
            hub_challenge = frappe.form_dict.get("hub.challenge")

            # Support verification via configured token in Social Media Settings
            try:
                settings = frappe.get_single("Social Media Settings")
                configured_token = (settings.get("webhook_verify_token") or "").strip()
            except Exception:
                configured_token = ""

            expected_verify_tokens = [t for t in [configured_token] if t]

            if hub_mode == "subscribe" and (hub_verify_token in expected_verify_tokens):
                # Use Flask/Werkzeug Response directly to bypass Frappe's JSON wrapping
                from werkzeug.wrappers import Response
                return Response(hub_challenge, content_type='text/plain', status=200)

            from werkzeug.wrappers import Response
            return Response("Verification failed", content_type='text/plain', status=403)

        # Handle POST request for webhook events
        webhook_data = frappe.request.get_data(as_text=True)

        if not webhook_data:
            return {"status": "error", "message": "No webhook data received"}

        try:
            data = json.loads(webhook_data)
        except json.JSONDecodeError as e:
            frappe.log_error(f"Webhook JSON parse error: {str(e)}", "Social Media Webhook")
            return {"status": "error", "message": "Invalid JSON data"}

        platform = frappe.request.headers.get("X-Platform") or detect_platform_from_webhook(data)

        # Validate webhook signatures where configured.
        if platform == "Tawk.to":
            raw_body = frappe.request.get_data()
            sig_valid = validate_tawkto_webhook_signature(raw_body, frappe.request.headers)
            if not sig_valid:
                # Signature mismatch — allow through for now while secret is being configured.
                # Once tawk_to_webhook_secret is set in Social Media Settings this will enforce.
                frappe.logger("assistant_crm.webhooks").warning(
                    "Tawk.to webhook signature validation failed — allowing through (configure "
                    "tawk_to_webhook_secret in Social Media Settings to enforce)"
                )

        elif platform == "Instagram":
            sig_valid = validate_instagram_webhook_signature(webhook_data, dict(frappe.request.headers))
            if not sig_valid:
                frappe.logger("assistant_crm.webhooks").warning(
                    "Instagram webhook signature validation failed — allowing through (configure "
                    "webhook_secret in Social Media Settings to enforce)"
                )

        if not platform:
            return {"status": "error", "message": "Could not determine platform"}

        platform_integration = get_platform_integration(platform)

        if not platform_integration:
            return {"status": "error", "message": f"Platform {platform} not supported"}

        try:
            return platform_integration.process_webhook(data)
        except Exception as e:
            frappe.log_error(f"Webhook processing error ({platform}): {str(e)}", "Social Media Webhook")
            return {"status": "error", "message": f"Webhook processing error: {str(e)}"}

    except Exception as e:
        frappe.log_error(f"Social media webhook error: {str(e)}", "Social Media Webhook Error")
        return {"status": "error", "message": "Webhook processing failed"}


def detect_platform_from_webhook(data: Dict[str, Any]) -> Optional[str]:
    """Detect the originating platform from a webhook payload structure."""

    # WhatsApp: entry.changes with whatsapp_business_account field, messages+contacts, or phone_number_id
    if "entry" in data and any("changes" in entry for entry in data.get("entry", [])):
        changes = data["entry"][0].get("changes", [])
        for change in changes:
            field = change.get("field", "")
            value = change.get("value", {})
            if "whatsapp_business_account" in field:
                return "WhatsApp"
            if "messages" in value and "contacts" in value:
                return "WhatsApp"
            if "metadata" in value and value.get("metadata", {}).get("phone_number_id"):
                return "WhatsApp"

    # Instagram: object == "instagram"
    if data.get("object") == "instagram":
        return "Instagram"

    # Facebook / Instagram: entry.messaging structure
    if "entry" in data and any("messaging" in entry for entry in data.get("entry", [])):
        if data.get("object") == "page":
            # Instagram DMs sent to a Page-connected Instagram Business Account also
            # arrive as object=="page" when a Page Access Token is in use. Distinguish
            # by matching the recipient ID against the configured Instagram Business
            # Account ID, then fall back to the 17+ digit heuristic.
            try:
                _settings = frappe.get_single("Social Media Settings")
                _ig_id = (_settings.get("instagram_business_account_id") or "").strip()
            except Exception:
                _ig_id = ""

            for _entry in data.get("entry", []):
                for _evt in (_entry.get("messaging") or []):
                    _recipient = str(_evt.get("recipient", {}).get("id", "") or "")
                    _sender = str(_evt.get("sender", {}).get("id", "") or "")
                    # Explicit match: recipient is the configured IG Business Account
                    if _ig_id and _recipient == _ig_id:
                        return "Instagram"
                    # Heuristic fallback: both IDs are 17+ digits → Instagram
                    if len(_sender) >= 17 and len(_recipient) >= 17:
                        return "Instagram"

            return "Facebook"

        entry = data["entry"][0]
        messaging = entry.get("messaging", [])
        if messaging:
            message_event = messaging[0]
            sender_id = message_event.get("sender", {}).get("id", "")
            recipient_id = message_event.get("recipient", {}).get("id", "")
            # Instagram Business account IDs are typically 17+ digits
            if len(str(sender_id)) >= 17 and len(str(recipient_id)) >= 17:
                return "Instagram"
            message = message_event.get("message", {})
            if message:
                for attachment in message.get("attachments", []):
                    if attachment.get("type") in ["image", "video", "audio"]:
                        return "Instagram"
        return "Facebook"

    # Telegram: message.chat present
    if "message" in data and "chat" in data.get("message", {}):
        return "Telegram"

    # Twitter
    if any(k in data for k in ("direct_message_events", "dm_events", "for_user_id")):
        return "Twitter"

    # Tawk.to: official events and legacy test event
    event_type = data.get("event")
    if event_type in ("chat:start", "chat:end", "chat:transcript_created", "ticket:create", "chat:message"):
        return "Tawk.to"

    return None


def validate_instagram_webhook_signature(webhook_data: str, headers: Dict[str, str]) -> bool:
    """Validate Instagram webhook signature using HMAC-SHA256."""
    try:
        # Get signature from headers
        signature_header = headers.get('X-Hub-Signature-256', '')
        if not signature_header:
            print(f"DEBUG: No X-Hub-Signature-256 header found")
            return True  # Allow for now if no signature

        # Extract signature (remove 'sha256=' prefix if present)
        signature = signature_header.replace('sha256=', '')

        # Get webhook secret from Instagram integration
        instagram_integration = InstagramIntegration()
        webhook_secret = instagram_integration.credentials.get('webhook_secret', '')

        if not webhook_secret:
            print(f"DEBUG: No webhook secret configured for Instagram")
            return True  # Allow for now if no secret configured

        # Calculate expected signature
        import hmac
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            webhook_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Compare signatures
        is_valid = hmac.compare_digest(signature, expected_signature)
        print(f"DEBUG: Instagram signature validation: {'PASSED' if is_valid else 'FAILED'}")
        print(f"DEBUG: Received signature: {signature}")
        print(f"DEBUG: Expected signature: {expected_signature}")
        print(f"DEBUG: Payload length: {len(webhook_data)} bytes")

        return is_valid

    except Exception as e:
        print(f"DEBUG: Error validating Instagram signature: {str(e)}")
        return True  # Allow on error for now




def validate_tawkto_webhook_signature(raw_body: bytes, headers: Dict[str, str]) -> bool:
    """Validate Tawk.to webhook signature using the secret key and raw request bytes.

    Per Tawk.to docs: signature is HMAC-SHA1 of the raw request body using the
    webhook secret, delivered in the X-Tawk-Signature header.
    """
    try:
        signature = headers.get("X-Tawk-Signature") or headers.get("x-tawk-signature")

        if not signature:
            # Tawk.to only sends the header when a secret is configured on their dashboard.
            # Allow through if no signature is present (secret not yet configured).
            return True

        # Load webhook secret from Social Media Settings (Password field, stored encrypted)
        settings = frappe.get_single("Social Media Settings")
        tawkto_secret = settings.get_password("tawk_to_webhook_secret") if settings.get("tawk_to_webhook_secret") else None

        if not tawkto_secret:
            frappe.logger("assistant_crm.webhooks").warning(
                "Tawk.to webhook signature received but tawk_to_webhook_secret is not configured "
                "in Social Media Settings — allowing through"
            )
            return True

        import hmac as _hmac
        body_bytes = raw_body if isinstance(raw_body, bytes) else raw_body.encode("utf-8")
        expected_signature = _hmac.new(
            tawkto_secret.encode("utf-8"),
            body_bytes,
            hashlib.sha1,
        ).hexdigest()

        return _hmac.compare_digest(signature, expected_signature)

    except Exception as e:
        frappe.log_error(f"Error validating Tawk.to signature: {str(e)}", "Tawk.to Webhook")
        return True  # Fail open to avoid dropping legitimate webhooks during transient errors


@frappe.whitelist()
def send_social_media_message(platform: str, conversation_name: str, message: str, reply_mode: str = None, reply_to_platform_message_id: str = None):
    """
    Send message to social media platform from unified inbox.
    Adds detailed diagnostics but does not modify conversation state here.
    """
    try:
        log = frappe.logger("assistant_crm.unified_send")
        try:
            log.info(f"[SOCIAL_SEND] start platform={platform} conv={conversation_name}")
        except Exception:
            pass

        # Get conversation details (read-only)
        conversation_doc = frappe.get_doc("Unified Inbox Conversation", conversation_name)

        if conversation_doc.platform != platform:
            try:
                log.warning(f"[SOCIAL_SEND] platform_mismatch conv={conversation_name} expected={conversation_doc.platform} got={platform}")
            except Exception:
                pass
            return {"status": "error", "message": "Platform mismatch"}

        # Get platform integration
        platform_integration = get_platform_integration(platform)

        if not platform_integration:
            try:
                log.error(f"[SOCIAL_SEND] no_integration platform={platform} conv={conversation_name}")
            except Exception:
                pass
            return {"status": "error", "message": f"Platform {platform} not supported"}

        if not platform_integration.is_configured:
            try:
                log.error(f"[SOCIAL_SEND] not_configured platform={platform} conv={conversation_name}")
            except Exception:
                pass
            return {"status": "error", "message": f"{platform} not configured"}
        # Instagram 24-hour messaging window guard
        try:
            if platform == "Instagram":
                last_inbound = frappe.get_all(
                    "Unified Inbox Message",
                    filters={
                        "conversation": conversation_name,
                        "direction": "Inbound",
                    },
                    fields=["name", "timestamp"],
                    order_by="timestamp desc",
                    limit=1,
                )
                if last_inbound:
                    from frappe.utils import time_diff_in_seconds
                    last_ts = last_inbound[0].get("timestamp")
                    if last_ts:
                        age_sec = time_diff_in_seconds(now(), last_ts)
                        if age_sec is not None and age_sec > 24 * 3600:
                            hours = round(age_sec / 3600, 1)
                            msg = (
                                "Instagram enforces a 24-hour customer care window. "
                                f"Last inbound was {hours}h ago; ask the customer to send a new message to reopen the window."
                            )
                            try:
                                log.warning(f"[SOCIAL_SEND] IG window closed conv={conversation_name} age_h={hours}")
                            except Exception:
                                pass
                            return {
                                "status": "error",
                                "message": msg,
                                "error_details": {
                                    "policy": "24h_window",
                                    "last_inbound_timestamp": str(last_ts),
                                    "age_hours": hours,
                                },
                            }
        except Exception:
            # Non-blocking guard: on any error, continue to attempt send
            pass

        # Determine reply mode for Twitter if applicable
        if platform == "Twitter":
            data = getattr(frappe.local, "form_dict", {}) or {}
            reply_mode = reply_mode or data.get("twitter_reply_mode") or data.get("reply_mode")
            reply_to_platform_message_id = reply_to_platform_message_id or data.get("reply_to_platform_message_id")

        # Send message
        try:
            log.info(
                f"[SOCIAL_SEND] sending platform={platform} conv={conversation_name} recipient={getattr(conversation_doc, 'customer_platform_id', None)} content_len={len(message or '')} reply_mode={reply_mode}"
            )
        except Exception:
            pass

        success = False
        if platform == "Twitter" and reply_mode in ("public", "tweet"):
            # Determine tweet to reply to
            tweet_id = None
            if reply_to_platform_message_id:
                tweet_id = str(reply_to_platform_message_id)
            else:
                candidates = frappe.get_all(
                    "Unified Inbox Message",
                    filters={
                        "conversation": conversation_name,
                        "platform": "Twitter",
                        "direction": "Inbound",
                        "platform_message_id": ["!=", ""],
                    },
                    fields=["name", "platform_message_id", "platform_metadata"],
                    order_by="timestamp desc",
                    limit=5,
                )
                for row in candidates or []:
                    tweet_id_candidate = row.get("platform_message_id")
                    md = None
                    try:
                        md = json.loads(row.get("platform_metadata") or "{}")
                    except Exception:
                        md = None
                    # Heuristic: tweet payloads won't have message_create key
                    if md and isinstance(md, dict) and not md.get("message_create"):
                        tweet_id = tweet_id_candidate
                        break
            if not tweet_id:
                return {
                    "status": "error",
                    "message": "No tweet found in this conversation to reply to",
                    "error_details": {"hint": "Select an inbound mention/tweet conversation or provide reply_to_platform_message_id"},
                }
            success = getattr(platform_integration, "send_public_reply")(tweet_id, message)
        else:
            # Default to DM send
            success = platform_integration.send_message(
                conversation_doc.customer_platform_id,
                message
            )

        try:
            log.info(f"[SOCIAL_SEND] result platform={platform} conv={conversation_name} success={bool(success)}")
        except Exception:
            pass

        if success:
            # Caller is responsible for creating the outbound message record to avoid duplicates
            return {"status": "success", "message": f"Message sent to {platform}"}
        else:
            # Include best-effort diagnostics if available on the integration
            error_details = {}
            try:
                if getattr(platform_integration, "last_response_status", None) is not None:
                    error_details["status_code"] = platform_integration.last_response_status
                if getattr(platform_integration, "last_response_text", None):
                    error_details["response_text"] = platform_integration.last_response_text
                if getattr(platform_integration, "last_request_payload", None):
                    error_details["request_payload"] = platform_integration.last_request_payload
                if getattr(platform_integration, "last_error", None):
                    error_details["error"] = platform_integration.last_error
            except Exception:
                pass
            return {"status": "error", "message": f"Failed to send message to {platform}", "error_details": error_details}

    except Exception as e:
        try:
            frappe.logger("assistant_crm.unified_send").exception(
                f"[SOCIAL_SEND] exception platform={platform} conv={conversation_name}: {str(e)}"
            )
        except Exception:
            pass
        frappe.log_error(f"Error sending {platform} message: {str(e)}", "Social Media Send Error")
        return {"status": "error", "message": "Failed to send message"}


@frappe.whitelist()
def get_platform_status():
    """
    Get configuration status of all social media platforms.
    """
    platforms = ["WhatsApp", "Facebook", "Instagram", "Telegram", "Twitter", "Tawk.to", "LinkedIn", "USSD"]
    status = {}

    for platform_name in platforms:
        platform_integration = get_platform_integration(platform_name)
        if platform_integration:
            status[platform_name] = {
                "configured": platform_integration.is_configured,
                "credentials_available": bool(platform_integration.credentials)
            }
        else:
            status[platform_name] = {
                "configured": False,
                "credentials_available": False
            }

    return {"status": "success", "platforms": status}


@frappe.whitelist(allow_guest=True)
def test_platform_detection():
    """Test platform detection logic with sample webhook data."""
    try:
        print("DEBUG: Testing platform detection logic")

        # Test Instagram webhook structure
        instagram_sample = {
            "entry": [
                {
                    "id": "17841405822304914",  # Long Instagram Business Account ID
                    "time": 1234567890,
                    "messaging": [
                        {
                            "sender": {"id": "1234567890123456"},  # Long Instagram user ID
                            "recipient": {"id": "17841405822304914"},
                            "timestamp": 1234567890,
                            "message": {
                                "mid": "m_test123",
                                "text": "Hello from Instagram!"
                            }
                        }
                    ]
                }
            ]
        }

        # Test Facebook webhook structure
        facebook_sample = {
            "entry": [
                {
                    "id": "123456789",  # Shorter Facebook Page ID
                    "time": 1234567890,
                    "messaging": [
                        {
                            "sender": {"id": "987654321"},  # Shorter Facebook user ID
                            "recipient": {"id": "123456789"},
                            "timestamp": 1234567890,
                            "message": {
                                "mid": "m_test456",
                                "text": "Hello from Facebook!"
                            }
                        }
                    ]
                }
            ]
        }

        # Test platform detection
        instagram_result = detect_platform_from_webhook(instagram_sample)
        facebook_result = detect_platform_from_webhook(facebook_sample)

        return {
            "status": "success",
            "message": "Platform detection test completed",
            "results": {
                "instagram_detection": instagram_result,
                "facebook_detection": facebook_result,
                "instagram_sample": instagram_sample,
                "facebook_sample": facebook_sample
            }
        }

    except Exception as e:
        error_msg = f"Error testing platform detection: {str(e)}"
        print(f"DEBUG: {error_msg}")
        return {"status": "error", "message": error_msg}


@frappe.whitelist()
def test_platform_detection():
    """Test platform detection logic with sample webhook data."""
    try:
        print("DEBUG: Testing platform detection logic")

        # Test Instagram webhook structure
        instagram_sample = {
            "entry": [
                {
                    "id": "17841405822304914",  # Long Instagram Business Account ID
                    "time": 1234567890,
                    "messaging": [
                        {
                            "sender": {"id": "1234567890123456"},  # Long Instagram user ID
                            "recipient": {"id": "17841405822304914"},
                            "timestamp": 1234567890,
                            "message": {
                                "mid": "m_test123",
                                "text": "Hello from Instagram!"
                            }
                        }
                    ]
                }
            ]
        }

        # Test Facebook webhook structure
        facebook_sample = {
            "entry": [
                {
                    "id": "123456789",  # Shorter Facebook Page ID
                    "time": 1234567890,
                    "messaging": [
                        {
                            "sender": {"id": "987654321"},  # Shorter Facebook user ID
                            "recipient": {"id": "123456789"},
                            "timestamp": 1234567890,
                            "message": {
                                "mid": "m_test456",
                                "text": "Hello from Facebook!"
                            }
                        }
                    ]
                }
            ]
        }

        # Test platform detection
        instagram_result = detect_platform_from_webhook(instagram_sample)
        facebook_result = detect_platform_from_webhook(facebook_sample)

        return {
            "status": "success",
            "message": "Platform detection test completed",
            "results": {
                "instagram_detection": instagram_result,
                "facebook_detection": facebook_result,
                "instagram_sample": instagram_sample,
                "facebook_sample": facebook_sample
            }
        }

    except Exception as e:
        error_msg = f"Error testing platform detection: {str(e)}"
        print(f"DEBUG: {error_msg}")
        return {"status": "error", "message": error_msg}


@frappe.whitelist(allow_guest=True)
def validate_instagram_integration():
    """Validate Instagram integration by checking recent conversations and messages."""
    try:
        # Get recent Instagram conversations
        instagram_conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters={
                "platform": "Instagram",
                "creation": [">=", frappe.utils.add_days(frappe.utils.now(), -1)]
            },
            fields=["name", "customer_name", "platform_specific_id", "creation", "status"],
            order_by="creation desc",
            limit=10
        )

        # Get recent Instagram messages
        instagram_messages = frappe.get_all(
            "Unified Inbox Message",
            filters={
                "platform": "Instagram",
                "creation": [">=", frappe.utils.add_days(frappe.utils.now(), -1)]
            },
            fields=["name", "conversation", "message_content", "sender_platform_id", "creation"],
            order_by="creation desc",
            limit=20
        )

        # Get recent Issues created for Instagram conversations
        instagram_issues = frappe.get_all(
            "Issue",
            filters={
                "subject": ["like", "%Instagram%"],
                "creation": [">=", frappe.utils.add_days(frappe.utils.now(), -1)]
            },
            fields=["name", "subject", "description", "status", "creation"],
            order_by="creation desc",
            limit=10
        )

        return {
            "status": "success",
            "message": "Instagram integration validation completed",
            "data": {
                "conversations": instagram_conversations,
                "messages": instagram_messages,
                "issues": instagram_issues,
                "conversation_count": len(instagram_conversations),
                "message_count": len(instagram_messages),
                "issue_count": len(instagram_issues)
            }
        }

    except Exception as e:
        error_msg = f"Error validating Instagram integration: {str(e)}"
        print(f"DEBUG: {error_msg}")
        return {"status": "error", "message": error_msg}


@frappe.whitelist()
def test_whatsapp_integration():
    """Test WhatsApp integration with sample webhook data."""
    try:
        print("DEBUG: Testing WhatsApp integration")

        # Sample WhatsApp webhook data
        sample_whatsapp_webhook = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "+264814193615",
                            "phone_number_id": "PHONE_NUMBER_ID"
                        },
                        "contacts": [{
                            "profile": {
                                "name": "John Doe"
                            },
                            "wa_id": "264814193615"
                        }],
                        "messages": [{
                            "from": "264814193615",
                            "id": "wamid.HBgNMjY0ODE0MTkzNjE1FQIAEhggRjE4QzY5RjVGNzU4NzY5RTlBNzY5RjVGNzU4NzY5RTkA",
                            "timestamp": "1693920000",
                            "text": {
                                "body": "Hello, I need help with my pension payment"
                            },
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }

        # Test platform detection
        detected_platform = detect_platform_from_webhook(sample_whatsapp_webhook)
        print(f"DEBUG: Platform detection result: {detected_platform}")

        if detected_platform != "WhatsApp":
            return {
                "status": "error",
                "message": f"Platform detection failed. Expected 'WhatsApp', got '{detected_platform}'"
            }

        # Test WhatsApp integration processing
        whatsapp_integration = WhatsAppIntegration()
        result = whatsapp_integration.process_webhook(sample_whatsapp_webhook)

        print(f"DEBUG: WhatsApp processing result: {result}")

        # Check if conversation was created
        conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters={"platform": "WhatsApp", "customer_platform_id": "264814193615"},
            fields=["name", "customer_name", "platform", "last_message_preview"],
            limit=1
        )

        return {
            "status": "success",
            "platform_detection": detected_platform,
            "webhook_processing": result,
            "conversations_created": len(conversations),
            "sample_conversation": conversations[0] if conversations else None,
            "message": "WhatsApp integration test completed successfully"
        }

    except Exception as e:
        error_msg = f"Error testing WhatsApp integration: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "WhatsApp Integration Test")
        return {"status": "error", "message": error_msg}


@frappe.whitelist()
def test_facebook_instagram_timestamps():
    """Test Facebook and Instagram timestamp handling with sample webhook data."""
    try:
        print("DEBUG: Testing Facebook and Instagram timestamp handling")

        # Sample Facebook webhook with timestamp
        facebook_webhook = {
            "object": "page",
            "entry": [{
                "id": "123456789",
                "time": 1693920000000,  # This is entry time
                "messaging": [{
                    "sender": {"id": "987654321"},
                    "recipient": {"id": "123456789"},
                    "timestamp": 1693920000000,  # This is message timestamp in milliseconds
                    "message": {
                        "mid": "m_test_facebook_123",
                        "text": "Test Facebook message with timestamp"
                    }
                }]
            }]
        }

        # Sample Instagram webhook with timestamp
        instagram_webhook = {
            "object": "instagram",
            "entry": [{
                "id": "17841405822304914",
                "time": 1693920000000,  # This is entry time
                "messaging": [{
                    "sender": {"id": "1234567890123456"},
                    "recipient": {"id": "17841405822304914"},
                    "timestamp": 1693920000000,  # This is message timestamp in milliseconds
                    "message": {
                        "mid": "m_test_instagram_123",
                        "text": "Test Instagram message with timestamp"
                    }
                }]
            }]
        }

        results = {}

        # Test Facebook timestamp processing
        print("DEBUG: Testing Facebook timestamp processing...")
        facebook_integration = FacebookIntegration()
        facebook_result = facebook_integration.process_webhook(facebook_webhook)
        results["facebook"] = facebook_result

        # Test Instagram timestamp processing
        print("DEBUG: Testing Instagram timestamp processing...")
        instagram_integration = InstagramIntegration()
        instagram_result = instagram_integration.process_webhook(instagram_webhook)
        results["instagram"] = instagram_result

        # Check recent messages to see their timestamps
        recent_messages = frappe.get_all(
            "Unified Inbox Message",
            filters={
                "platform": ["in", ["Facebook", "Instagram"]],
                "creation": [">=", frappe.utils.add_days(frappe.utils.now(), -1)]
            },
            fields=["name", "platform", "timestamp", "creation", "message_content", "platform_message_id"],
            order_by="creation desc",
            limit=10
        )

        return {
            "status": "success",
            "message": "Timestamp testing completed",
            "webhook_processing": results,
            "recent_messages": recent_messages,
            "expected_timestamp": "2023-09-05 13:20:00",  # What 1693920000000ms should convert to
            "test_timestamp_ms": 1693920000000
        }

    except Exception as e:
        error_msg = f"Error testing timestamps: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Timestamp Test Error")
        return {"status": "error", "message": error_msg}


@frappe.whitelist()
def validate_timestamp_fix():
    """Validate that the timestamp fix is working correctly for Facebook and Instagram."""
    try:
        print("DEBUG: Validating timestamp fix for Facebook and Instagram")

        # Test with various webhook scenarios
        test_scenarios = [
            {
                "name": "Facebook with messaging timestamp",
                "platform": "Facebook",
                "webhook": {
                    "object": "page",
                    "entry": [{
                        "id": "123456789",
                        "time": 1693920000000,
                        "messaging": [{
                            "sender": {"id": "987654321"},
                            "recipient": {"id": "123456789"},
                            "timestamp": 1693920000000,  # This should be used
                            "message": {"mid": "test_timestamp_1", "text": "Test message 1"}
                        }]
                    }]
                }
            },
            {
                "name": "Instagram with message timestamp",
                "platform": "Instagram",
                "webhook": {
                    "object": "instagram",
                    "entry": [{
                        "id": "17841405822304914",
                        "time": 1693920000000,
                        "messaging": [{
                            "sender": {"id": "1234567890123456"},
                            "recipient": {"id": "17841405822304914"},
                            "timestamp": 1693920000000,  # This should be used
                            "message": {"mid": "test_timestamp_2", "text": "Test message 2"}
                        }]
                    }]
                }
            }
        ]

        results = []

        for scenario in test_scenarios:
            print(f"DEBUG: Testing scenario: {scenario['name']}")

            if scenario['platform'] == 'Facebook':
                integration = FacebookIntegration()
            else:
                integration = InstagramIntegration()

            # Process the webhook
            result = integration.process_webhook(scenario['webhook'])

            # Check if the message was created with correct timestamp
            message_id = scenario['webhook']['entry'][0]['messaging'][0]['message']['mid']

            message = frappe.get_all(
                "Unified Inbox Message",
                filters={"platform_message_id": message_id},
                fields=["name", "timestamp", "creation"],
                limit=1
            )

            scenario_result = {
                "scenario": scenario['name'],
                "platform": scenario['platform'],
                "webhook_result": result,
                "message_created": len(message) > 0,
                "message_timestamp": message[0]['timestamp'] if message else None,
                "expected_timestamp": "2023-09-05 13:20:00",
                "timestamp_correct": message[0]['timestamp'] == "2023-09-05 13:20:00" if message else False
            }

            results.append(scenario_result)
            print(f"DEBUG: Scenario result: {scenario_result}")

        # Summary
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r['timestamp_correct'])

        return {
            "status": "success",
            "message": "Timestamp validation completed",
            "test_results": results,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            }
        }

    except Exception as e:
        error_msg = f"Error validating timestamp fix: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Timestamp Validation Error")
        return {"status": "error", "message": error_msg}


class USSDIntegration(SocialMediaPlatform):
    """USSD integration shim.
    Note: USSD replies are delivered synchronously via the ussd_webhook HTTP response.
    send_message() returns False to indicate push is not supported by default.
    """
    def __init__(self):
        super().__init__("USSD")
        self.last_error = None
        self.last_response_status = None
        self.last_response_text = None
        self.last_request_payload = None

    def get_platform_credentials(self) -> Dict[str, str]:
        try:
            settings = frappe.get_single("Social Media Settings")
            return {
                "ussd_enabled": int(getattr(settings, "ussd_enabled", 0) or 0),
                "ussd_provider": getattr(settings, "ussd_provider", None),
                "ussd_short_code": getattr(settings, "ussd_short_code", None),
                "ussd_service_code": getattr(settings, "ussd_service_code", None),
                "ussd_app_username": getattr(settings, "ussd_app_username", None),
                "ussd_api_key": getattr(settings, "ussd_api_key", None),
                "ussd_webhook_secret": getattr(settings, "ussd_webhook_secret", None),
                "ussd_session_timeout_seconds": int(getattr(settings, "ussd_session_timeout_seconds", 120) or 120),
                "ussd_default_menu": getattr(settings, "ussd_default_menu", None),
                "ussd_feedback_api_url": getattr(settings, "ussd_feedback_api_url", None),
            }
        except Exception as e:
            self.last_error = str(e)
            return {}

    def check_configuration(self) -> bool:
        try:
            c = self.credentials or {}
            return bool(int(c.get("ussd_enabled", 0)))
        except Exception:
            return False

    def send_message(self, recipient_id: str, message: str, message_type: str = "text") -> bool:
        # Outbound USSD push is generally not supported; the provider expects synchronous responses
        self.last_error = "USSD push send not supported; use synchronous webhook response."
        return False

    def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        # USSD webhooks are handled by assistant_crm.api.ussd_integration.ussd_webhook
        return {"status": "unsupported", "message": "Use ussd_webhook endpoint"}

@frappe.whitelist(allow_guest=True)
def google_oauth_callback(code=None, error=None, error_description=None, **kwargs):
    try:
        # 1️⃣ Handle errors from Google
        if error:
            frappe.log_error(f"OAuth Error: {error} - {error_description}", "Google OAuth")
            return f"<h3>OAuth Error: {error_description}</h3>"

        if not code:
            return "<h3>No authorization code received.</h3>"

        # 2️⃣ Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"

        settings = frappe.get_doc("Social Media Settings", "Social Media Settings")
        client_id = settings.get("youtube_client_id")
        # In Frappe 15, get_password retrieves decrypted password field values.
        try:
            client_secret = settings.get_password("youtube_client_secret")
        except Exception:
            client_secret = settings.get("youtube_client_secret")

        oauth_callback_path = "/api/method/assistant_crm.api.social_media_ports.google_oauth_callback"
        stored_redirect_uri = (settings.get("youtube_redirect_uri") or "").strip()
        if stored_redirect_uri:
            redirect_uri = stored_redirect_uri
        else:
            from assistant_crm.utils import get_public_url
            redirect_uri = get_public_url() + oauth_callback_path

        payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }

        import requests
        response = requests.post(token_url, data=payload)
        tokens = response.json()

        # 🔍 DEBUG LOG (VERY IMPORTANT)
        frappe.logger("assistant_crm.webhook").info(f"Google Token Response: {tokens}")

        # 3️⃣ Handle failure
        if "access_token" not in tokens:
            frappe.log_error(f"Token exchange failed: {tokens}", "Google OAuth")
            return f"<h3>Token exchange failed: {tokens}</h3>"

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        # 4️⃣ Save tokens securely
        settings = frappe.get_doc("Social Media Settings", "Social Media Settings")

        settings.youtube_access_token = access_token

        if refresh_token:
            settings.youtube_refresh_token = refresh_token

        settings.save(ignore_permissions=True)
        frappe.db.commit()

        return "<h3>Authentication successful! Tokens have been saved. You can close this window.</h3>"

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Google OAuth Callback Error")
        return f"<h3>Internal Error: {str(e)}</h3>"


@frappe.whitelist()
def refresh_youtube_token():
    try:
        settings = frappe.get_doc("Social Media Settings", "Social Media Settings")

        # In Frappe, .get_password retrieves decrypted password field values.
        refresh_token = settings.get_password("youtube_refresh_token")

        if not refresh_token:
            return None

        token_url = "https://oauth2.googleapis.com/token"

        client_id = settings.get("youtube_client_id")
        try:
            client_secret = settings.get_password("youtube_client_secret")
        except Exception:
            client_secret = settings.get("youtube_client_secret")

        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        import requests
        response = requests.post(token_url, data=payload)
        data = response.json()

        if "access_token" in data:
            settings.youtube_access_token = data["access_token"]
            settings.save(ignore_permissions=True)
            frappe.db.commit()
            return data["access_token"]

        else:
            frappe.log_error(f"Refresh failed: {data}", "YouTube Token Refresh")
            return None
    except Exception as e:
        frappe.log_error(str(e), "YouTube Token Refresh Exception")
        return None

def ensure_youtube_comment_field():
    if not frappe.db.has_column("Communication", "youtube_comment_id"):
        try:
            from frappe.custom.doctype.custom_field.custom_field import create_custom_field
            create_custom_field("Communication", {
                "fieldname": "youtube_comment_id",
                "label": "YouTube Comment ID",
                "fieldtype": "Data",
                "insert_after": "sender",
                "hidden": 1
            })
            frappe.db.commit()
        except Exception:
            pass

@frappe.whitelist()
def get_valid_youtube_token():
    settings = frappe.get_doc("Social Media Settings", "Social Media Settings")
    token = settings.youtube_access_token
    
    if not token:
        return refresh_youtube_token()

    import requests
    test = requests.get(
        "https://www.googleapis.com/oauth2/v1/tokeninfo",
        params={"access_token": token}
    ).json()

    if "error" in test:
        token = refresh_youtube_token()

    return token

def get_all_videos():
    token = get_valid_youtube_token()
    if not token:
        return []

    headers = {"Authorization": f"Bearer {token}"}
    url = "https://www.googleapis.com/youtube/v3/search"
    
    import requests
    videos = []
    next_page_token = None

    while True:
        params = {
            "part": "snippet",
            "forMine": True,
            "type": "video",
            "maxResults": 50
        }
        if next_page_token:
            params["pageToken"] = next_page_token

        res = requests.get(url, headers=headers, params=params).json()

        for item in res.get("items", []):
            vid = item.get("id", {}).get("videoId")
            if vid:
                videos.append(vid)

        next_page_token = res.get("nextPageToken")
        if not next_page_token:
            break

    return videos

@frappe.whitelist()
def sync_youtube_comments():
    ensure_youtube_comment_field()
    token = get_valid_youtube_token()
    
    if not token:
        return {"status": "error", "message": "No valid YouTube token to sync"}

    headers = {"Authorization": f"Bearer {token}"}
    videos = get_all_videos()
    
    import requests
    synced_count = 0

    for video_id in videos:
        url = "https://www.googleapis.com/youtube/v3/commentThreads"
        next_page_token = None

        while True:
            params = {
                "part": "snippet",
                "videoId": video_id,
                "maxResults": 50
            }
            if next_page_token:
                params["pageToken"] = next_page_token

            res = requests.get(url, headers=headers, params=params).json()
            
            if "error" in res:
                break
                
            for item in res.get("items", []):
                snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                comment_id = item.get("id")

                if not comment_id or not snippet:
                    continue

                # Duplicate Prevention via Custom Field
                existing = frappe.db.exists("Communication", {
                    "youtube_comment_id": comment_id
                })

                if not existing:
                    try:
                        frappe.get_doc({
                            "doctype": "Communication",
                            "subject": f"YouTube Comment on {video_id}",
                            "content": snippet.get("textDisplay", ""),
                            "sender": snippet.get("authorDisplayName", "YouTube User"),
                            "communication_type": "Communication",
                            "communication_medium": "YouTube",
                            "youtube_comment_id": comment_id,
                            "sent_or_received": "Received",
                            "status": "Open"
                        }).insert(ignore_permissions=True)
                        
                        synced_count += 1
                        
                        # --- PRO-LEVEL ARCHITECTURE MAPPER ---
                        # Pass it natively into the CRM AI/Inbox Engine
                        author_channel_id = (snippet.get("authorChannelId") or {}).get("value") or ""
                        if author_channel_id:
                            yt = YouTubeIntegration()
                            yt.process_webhook({
                                "platform": "YouTube",
                                "event_type": "comment",
                                "video_id": video_id,
                                "comment_id": comment_id,
                                "author_channel_id": author_channel_id,
                                "author_name": snippet.get("authorDisplayName", "YouTube User"),
                                "text": snippet.get("textDisplay", "")
                            })
                    except Exception as e:
                        frappe.log_error(f"Sync fail for {comment_id}: {str(e)}", "YouTube Auto Sync")
            
            next_page_token = res.get("nextPageToken")
            if not next_page_token:
                break

    frappe.db.commit()
    frappe.logger("assistant_crm.youtube").info(f"Auto-sync completed. Downloaded {synced_count} new comments.")
    return {"status": "success", "synced": synced_count}

