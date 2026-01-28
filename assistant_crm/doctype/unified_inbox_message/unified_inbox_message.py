"""Unified Inbox Message DocType for managing individual messages.

This module handles message lifecycle inside the Unified Inbox system,
including AI processing, escalation, and agent notifications.
"""

import hashlib
import json
from typing import Any, Dict, Optional

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, now


class UnifiedInboxMessage(Document):
    """Unified Inbox Message DocType for managing individual messages
    within conversations across multiple platforms.
    """

    def before_insert(self):
        """Set default values before inserting the document."""
        if not self.message_id:
            self.message_id = self.generate_message_id()

        if not self.timestamp:
            self.timestamp = now()

        if not self.direction:
            self.direction = "Inbound"

        if not self.message_type:
            self.message_type = "text"

    def after_insert(self):
        """Actions to perform after inserting the document."""
        # Lightweight diagnostic to confirm after_insert firing
        try:
            frappe.logger("assistant_crm.unified_inbox_ai").info(
                f"[AI] after_insert doc={self.name} dir={self.direction} platform={self.platform}"
            )
        except Exception:
            pass

        # Fallback file log to ensure visibility even if logger not configured
        try:
            with open(
                "/workspace/development/frappe-bench/logs/webhook_debug.log", "a"
            ) as f:
                f.write(
                    f"[AI-DIAG] after_insert doc={self.name} dir={self.direction} platform={self.platform}\n"
                )
        except Exception:
            pass

        # Update conversation with latest message info
        self.update_conversation_last_message()

        # Process inbound messages
        if self.direction == "Inbound":
            self.process_inbound_message()

    def generate_message_id(self) -> str:
        """Generate a unique message ID."""
        unique_string = (
            f"{self.platform}_{self.conversation}_{now()}_"
            f"{frappe.generate_hash(length=6)}"
        )
        return hashlib.md5(unique_string.encode()).hexdigest()[:12].upper()

    def update_conversation_last_message(self) -> None:
        """Update the parent conversation with latest message information."""
        try:
            if not self.conversation:
                return

            conversation_doc = frappe.get_doc(
                "Unified Inbox Conversation", self.conversation
            )

            # Update last message time and preview
            conversation_doc.db_set("last_message_time", self.timestamp)
            try:
                frappe.logger("assistant_crm.unified_send").info(
                    f"[CONV_UPDATE] time conv={self.conversation} msg={self.name} ts={self.timestamp}"
                )
            except Exception:
                pass

            # Create message preview (first 100 characters)
            preview = (
                self.message_content[:100] + "..."
                if len(self.message_content) > 100
                else self.message_content
            )
            conversation_doc.db_set("last_message_preview", preview)
            try:
                frappe.logger("assistant_crm.unified_send").info(
                    f"[CONV_UPDATE] preview conv={self.conversation} msg={self.name} len={len(preview or '')}"
                )
            except Exception:
                pass

            # If this is the first message, set first response time for outbound
            # messages
            if (
                self.direction == "Outbound"
                and not conversation_doc.first_response_time
            ):
                conversation_doc.db_set("first_response_time", self.timestamp)
                try:
                    frappe.logger("assistant_crm.unified_send").info(
                        f"[CONV_UPDATE] first_response_time conv={self.conversation} msg={self.name}"
                    )
                except Exception:
                    pass

        except Exception as e:
            try:
                frappe.logger("assistant_crm.unified_send").exception(
                    f"[CONV_UPDATE] exception conv={self.conversation} msg={self.name}: {str(e)}"
                )
            except Exception:
                pass
            frappe.log_error(
                f"Failed to update conversation: {str(e)}",
                "Unified Inbox - Conversation Update Error",
            )

    def process_inbound_message(self) -> None:
        """Process inbound message for AI or agent handling."""
        try:
            conversation_doc = frappe.get_doc(
                "Unified Inbox Conversation", self.conversation
            )

            # Ensure there is always a supervising agent attached to the
            # conversation so that humans can monitor and take over when
            # required. This does not, by itself, disable AI.
            conversation_doc.auto_assign_supervising_agent_if_needed()

            # Check if conversation should be processed by AI (respects
            # conversation mode, global settings, and explicit
            # requires_human_intervention flag)
            if conversation_doc.should_process_with_ai_supervising():
                try:
                    frappe.logger("assistant_crm.unified_inbox_ai").info(
                        f"[AI] gate=allow message_id={self.name} conv={self.conversation} platform={self.platform}"
                    )
                except Exception:
                    pass

                # Fallback file log
                try:
                    with open(
                        "/workspace/development/frappe-bench/logs/webhook_debug.log",
                        "a",
                    ) as f:
                        f.write(
                            f"[AI-DIAG] gate=allow message_id={self.name} conv={self.conversation} platform={self.platform}\n"
                        )
                except Exception:
                    pass

                self.trigger_ai_processing()

            elif conversation_doc.assigned_agent:
                try:
                    frappe.logger("assistant_crm.unified_inbox_ai").info(
                        f"[AI] gate=blocked reason=agent_or_settings message_id={self.name} conv={self.conversation}"
                    )
                except Exception:
                    pass

                try:
                    with open(
                        "/workspace/development/frappe-bench/logs/webhook_debug.log",
                        "a",
                    ) as f:
                        f.write(
                            f"[AI-DIAG] gate=blocked reason=agent_or_settings message_id={self.name} conv={self.conversation}\n"
                        )
                except Exception:
                    pass

                # Notify assigned agent of new message when AI is disabled but an
                # owner is already attached to the conversation (e.g. manual
                # escalation or ai_mode = "Off").
                self.notify_assigned_agent()

            else:
                try:
                    frappe.logger("assistant_crm.unified_inbox_ai").info(
                        "[AI] gate=blocked reason=ai_disabled_or_platform "
                        f"message_id={self.name} conv={self.conversation} platform={self.platform}"
                    )
                except Exception:
                    pass

                try:
                    with open(
                        "/workspace/development/frappe-bench/logs/webhook_debug.log",
                        "a",
                    ) as f:
                        f.write(
                            "[AI-DIAG] gate-blocked "
                            "reason=ai_disabled_or_platform "
                            f"message_id={self.name} conv={self.conversation} platform={self.platform}\n"
                        )
                except Exception:
                    pass

                # Direct to human agent (e.g., Tawk.to)
                conversation_doc.escalate_to_human_agent(
                    "Platform requires human agent"
                )

        except Exception as e:
            frappe.log_error(
                f"Failed to process inbound message: {str(e)}",
                "Unified Inbox - Message Processing Error",
            )

    def trigger_ai_processing(self) -> None:
        """Trigger AI processing for this message.

        Default: enqueue async job. Optional dev guardrails:

        - ai_force_sync_processing: always process synchronously
          (single-process, deterministic)
        - ai_sync_fallback_when_no_workers: if no workers online (or
          developer_mode), process synchronously
        - ai_queue_per_conversation: shard queues by conversation to keep
          ordering/affinity
        """

        try:
            # Fallback file log prior to enqueue attempt
            try:
                with open(
                    "/workspace/development/frappe-bench/logs/webhook_debug.log",
                    "a",
                ) as f:
                    f.write(
                        f"[AI-DIAG] enqueue_attempt message_id={self.name} conv={self.conversation} platform={self.platform}\n"
                    )
            except Exception:
                pass

            conf = getattr(frappe, "conf", {}) or {}

            # 1) Hard override: force sync processing if configured
            if conf.get("ai_force_sync_processing"):
                try:
                    with open(
                        "/workspace/development/frappe-bench/logs/webhook_debug.log",
                        "a",
                    ) as f:
                        f.write(
                            f"[AI-DIAG] force_sync_processing message_id={self.name} conv={self.conversation}\n"
                        )
                except Exception:
                    pass

                try:
                    from assistant_crm.api.unified_inbox_api import (
                        process_message_with_ai,
                    )

                    process_message_with_ai(self.name)
                    try:
                        frappe.logger("assistant_crm.unified_inbox_ai").info(
                            f"[AI] sync_processed (forced) message_id={self.name} conv={self.conversation}"
                        )
                    except Exception:
                        pass
                except Exception as proc_err:
                    frappe.log_error(
                        f"Forced sync AI processing failed for {self.name}: {str(proc_err)}",
                        "Unified Inbox - AI Forced Sync Error",
                    )
                return

            # 2) Determine if sync fallback is desired due to no workers online
            want_sync_fallback = False
            try:
                if conf.get("ai_sync_fallback_when_no_workers") or conf.get(
                    "developer_mode"
                ):
                    # Check if any RQ workers are online
                    try:
                        from frappe.utils.background_jobs import get_redis_conn
                        from rq import Worker

                        conn = get_redis_conn()
                        workers = []
                        try:
                            workers = Worker.all(connection=conn)
                        except TypeError:
                            # Older rq versions use positional arg
                            workers = Worker.all(conn)
                        want_sync_fallback = not bool(workers)
                    except Exception:
                        # If we can't determine, stay async-only
                        want_sync_fallback = False
            except Exception:
                want_sync_fallback = False

            if want_sync_fallback:
                # DEV GUARDRAIL: No workers online and fallback enabled 
                # process synchronously
                try:
                    with open(
                        "/workspace/development/frappe-bench/logs/webhook_debug.log",
                        "a",
                    ) as f:
                        f.write(
                            f"[AI-DIAG] no_workers_online fallback_sync message_id={self.name} conv={self.conversation}\n"
                        )
                except Exception:
                    pass

                try:
                    from assistant_crm.api.unified_inbox_api import (
                        process_message_with_ai,
                    )

                    process_message_with_ai(self.name)
                    try:
                        frappe.logger("assistant_crm.unified_inbox_ai").info(
                            f"[AI] sync_processed message_id={self.name} conv={self.conversation}"
                        )
                    except Exception:
                        pass
                except Exception as proc_err:
                    frappe.log_error(
                        f"Sync AI processing failed for {self.name}: {str(proc_err)}",
                        "Unified Inbox - AI Sync Fallback Error",
                    )
                return

            # 3) Async path with optional per-conversation queue sharding
            queue_name = "default"
            try:
                if conf.get("ai_queue_per_conversation"):
                    shards = int(conf.get("ai_conversation_queue_shards") or 4)
                    if shards < 1:
                        shards = 1
                    # Stable shard by conversation name
                    shard_idx = abs(hash(self.conversation)) % shards
                    queue_name = f"ai_conv_{shard_idx}"
            except Exception:
                queue_name = "default"

            frappe.enqueue(
                "assistant_crm.api.unified_inbox_api.process_message_with_ai",
                message_id=self.name,
                queue=queue_name,
                timeout=300,
            )
            try:
                frappe.logger("assistant_crm.unified_inbox_ai").info(
                    f"[AI] enqueued message_id={self.name} conv={self.conversation} queue={queue_name} platform={self.platform}"
                )
            except Exception:
                pass

            # Fallback file log after enqueue
            try:
                with open(
                    "/workspace/development/frappe-bench/logs/webhook_debug.log",
                    "a",
                ) as f:
                    f.write(
                        f"[AI-DIAG] enqueued message_id={self.name} conv={self.conversation} queue={queue_name} platform={self.platform}\n"
                    )
            except Exception:
                pass

        except Exception as e:
            frappe.log_error(
                f"Failed to trigger AI processing: {str(e)}",
                "Unified Inbox - AI Processing Error",
            )

    def notify_assigned_agent(self) -> None:
        """Notify assigned agent of new message."""
        try:
            conversation_doc = frappe.get_doc(
                "Unified Inbox Conversation", self.conversation
            )

            if conversation_doc.assigned_agent:
                # Create notification
                notification = frappe.get_doc(
                    {
                        "doctype": "Notification Log",
                        "subject": (
                            "New message from "
                            f"{conversation_doc.customer_name or 'Unknown Customer'}"
                        ),
                        "email_content": f"""
                        <p>New message received:</p>
                        <ul>
                            <li><strong>Platform:</strong> {self.platform}</li>
                            <li><strong>Customer:</strong> {conversation_doc.customer_name or 'Unknown'}</li>
                            <li><strong>Message:</strong> {self.message_content[:200]}{'...' if len(self.message_content) > 200 else ''}</li>
                        </ul>
                        <p>Please respond as soon as possible.</p>
                        """,
                        "for_user": conversation_doc.assigned_agent,
                        "type": "Alert",
                    }
                )
                notification.insert(ignore_permissions=True)

        except Exception as e:
            frappe.log_error(
                f"Failed to notify agent: {str(e)}",
                "Unified Inbox - Agent Notification Error",
            )

    def set_ai_response(
        self,
        response: str,
        confidence: float,
        model_used: Optional[str] = None,
        processing_time: Optional[float] = None,
    ) -> None:
        """Set AI response for this message."""

        self.db_set("ai_response", response)
        self.db_set("ai_confidence", confidence)

        if model_used:
            self.db_set("ai_model_used", model_used)

        if processing_time is not None:
            self.db_set("ai_processing_time", processing_time)

        # Check if escalation is needed based on confidence
        if confidence < 0.7:
            self.db_set("requires_escalation", 1)

            # Update conversation
            conversation_doc = frappe.get_doc(
                "Unified Inbox Conversation", self.conversation
            )
            conversation_doc.escalate_to_human_agent(
                f"Low AI confidence: {confidence}"
            )

    def set_agent_response(
        self,
        response: str,
        agent: str,
        response_time: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Set agent response for this message."""

        self.db_set("handled_by_agent", 1)
        self.db_set("agent_response", response)

        if response_time is not None:
            self.db_set("agent_response_time", response_time)

        if notes:
            self.db_set("agent_notes", notes)

    def add_attachment(self, attachment_data: Dict[str, Any]) -> None:
        """Add attachment data to the message."""

        self.db_set("has_attachments", 1)

        current_attachments = []
        if self.attachments_data:
            current_attachments = (
                json.loads(self.attachments_data)
                if isinstance(self.attachments_data, str)
                else self.attachments_data
            )

        current_attachments.append(attachment_data)
        self.db_set("attachments_data", json.dumps(current_attachments))

    def add_media_url(self, media_url: str, media_type: Optional[str] = None) -> None:
        """Add media URL to the message."""

        current_media = []
        if self.media_urls:
            current_media = (
                json.loads(self.media_urls)
                if isinstance(self.media_urls, str)
                else self.media_urls
            )

        media_data = {
            "url": media_url,
            "type": media_type or "unknown",
            "timestamp": now(),
        }
        current_media.append(media_data)
        self.db_set("media_urls", json.dumps(current_media))

    def update_delivery_status(self, status: str, timestamp: Optional[str] = None) -> None:
        """Update message delivery status."""

        self.db_set("delivery_status", status)

        if timestamp:
            self.db_set("delivery_timestamp", timestamp)
        elif status in ["Delivered", "Read"]:
            self.db_set("delivery_timestamp", now())

    def mark_as_read(self, timestamp: Optional[str] = None) -> None:
        """Mark message as read."""

        self.db_set("read_status", "Read")
        self.db_set("read_timestamp", timestamp or now())

    def add_platform_metadata(self, metadata: Dict[str, Any]) -> None:
        """Add platform-specific metadata."""

        current_metadata: Dict[str, Any] = {}
        if self.platform_metadata:
            current_metadata = (
                json.loads(self.platform_metadata)
                if isinstance(self.platform_metadata, str)
                else self.platform_metadata
            )

        current_metadata.update(metadata)
        self.db_set("platform_metadata", json.dumps(current_metadata))

    def get_conversation_context(self) -> Dict[str, Any]:
        """Get conversation context for AI processing."""

        try:
            conversation_doc = frappe.get_doc(
                "Unified Inbox Conversation", self.conversation
            )

            # Get recent messages for context
            recent_messages = frappe.get_all(
                "Unified Inbox Message",
                filters={
                    "conversation": self.conversation,
                    "timestamp": ["<", self.timestamp],
                },
                fields=[
                    "message_content",
                    "direction",
                    "timestamp",
                    "ai_response",
                    "agent_response",
                ],
                order_by="timestamp desc",
                limit=10,
            )

            context = {
                "conversation_id": conversation_doc.conversation_id,
                "customer_name": conversation_doc.customer_name,
                "platform": self.platform,
                "recent_messages": recent_messages,
                "conversation_context": conversation_doc.conversation_context,
                "platform_metadata": conversation_doc.platform_metadata,
            }

            return context

        except Exception as e:
            frappe.log_error(
                f"Failed to get conversation context: {str(e)}",
                "Unified Inbox - Context Error",
            )
            return {}

    def should_escalate_to_agent(self) -> bool:
        """Determine if message should be escalated to human agent."""

        # Already handled by agent
        if getattr(self, "handled_by_agent", None):
            return False

        # AI confidence too low
        if getattr(self, "ai_confidence", None) and self.ai_confidence < 0.7:
            return True

        # Requires escalation flag set
        if getattr(self, "requires_escalation", None):
            return True

        # Platform-specific rules (e.g., Tawk.to always goes to agent)
        if getattr(self, "platform", None) == "Tawk.to":
            return True

        return False
