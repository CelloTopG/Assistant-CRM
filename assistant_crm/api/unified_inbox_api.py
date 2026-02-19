#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Unified Inbox API
=======================================

Main API for the unified inbox system that orchestrates all platform integrations,
AI processing, and human agent workflows.

Features:
- Unified message processing
- AI-first response system with live data access
- Intelligent escalation to human agents
- Real-time conversation management
- Platform-agnostic message handling
- Agent dashboard integration

Author: WCFCB Development Team
Created: 2025-08-27
License: MIT
"""

import frappe
import json
import requests
from frappe import _
from frappe.utils import now, get_datetime, time_diff_in_seconds
from typing import Dict, Any, Optional, List
import time
from assistant_crm.utils import get_public_url
# NOTE: Do NOT import from social_media_ports or tawk_to_integration at the top level.
# These modules import from unified_inbox_api, creating a circular dependency.
# Instead, import them locally inside the functions that need them.

import re

# --- Helper utilities for NRC extraction and beneficiary lookup ---
NRC_REGEX = re.compile(r"(?<!\d)(\d{6})[\/-](\d{2})[\/-](\d{1,3})(?!\d)")


def _normalize_nrc(raw: str) -> str:
    """Normalize NRC to standard slash-separated format: XXXXXX/XX/X"""
    if not raw:
        return ""
    m = NRC_REGEX.search(str(raw))
    if not m:
        # As fallback, strip non-digits and try to split 6-2-rest
        digits = re.sub(r"\D", "", str(raw))
        if len(digits) >= 9:
            return f"{digits[:6]}/{digits[6:8]}/{digits[8:]}"
        return raw
    g1, g2, g3 = m.group(1), m.group(2), m.group(3)
    return f"{g1}/{g2}/{g3}"


def _extract_first_nrc_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    m = NRC_REGEX.search(text)
    return _normalize_nrc(m.group(0)) if m else None


def _find_beneficiary_or_employee_by_nrc(nrc: str) -> Optional[Dict[str, Any]]:
    """Return dict with keys: kind ('Employee'), full_name, link_doctype, link_name. None if not found.

    NOTE: Beneficiary Profile and Employee Profile doctypes have been removed.
    Now uses ERPNext Employee doctype instead.
    """
    try:
        normalized = _normalize_nrc(nrc)

        # Try ERPNext Employee doctype (replaced Employee Profile)
        emp = frappe.get_all(
            "Employee",
            filters={"custom_nrc_number": normalized},
            fields=["name", "employee_name"],
            limit=1,
        )
        if not emp:
            # Try hyphen variant
            hyphen = normalized.replace("/", "-")
            emp = frappe.get_all(
                "Employee",
                filters={"custom_nrc_number": hyphen},
                fields=["name", "employee_name"],
                limit=1,
            )
        if emp:
            e = emp[0]
            return {
                "kind": "Employee",
                "full_name": e.get("employee_name") or e.get("name"),
                "link_doctype": "Employee",
                "link_name": e.get("name"),
            }
    except Exception as lookup_err:
        try:
            frappe.log_error(f"NRC lookup error: {lookup_err}", "Assistant CRM NRC Lookup")
        except Exception:
            pass
    return None


def _set_issue_customer_fields(issue_name: str, nrc: Optional[str], phone: Optional[str], customer_info: Optional[Dict[str, Any]] = None):
    """Best-effort setter for Issue custom fields. Only sets fields that exist on the Issue DocType.

    NOTE: Beneficiary Profile has been removed. Now uses Employee info instead.
    """
    try:
        meta = frappe.get_meta("Issue")

        updates = {}
        if nrc and getattr(meta, "has_field", None) and meta.has_field("custom_customer_nrc"):
            updates["custom_customer_nrc"] = _normalize_nrc(nrc)
        if phone and getattr(meta, "has_field", None) and meta.has_field("custom_customer_phone"):
            updates["custom_customer_phone"] = phone

        # Employee population (Beneficiary Profile has been removed)
        if customer_info:
            name_to_set = customer_info.get("full_name")
            # Use employee field if present
            if meta.has_field("employee"):
                updates["employee"] = customer_info.get("link_name")
            elif meta.has_field("custom_employee"):
                updates["custom_employee"] = customer_info.get("link_name")
            elif meta.has_field("custom_employee_name"):
                updates["custom_employee_name"] = name_to_set

        if updates:
            frappe.db.set_value("Issue", issue_name, updates)
    except Exception as set_err:
        try:
            frappe.log_error(f"Failed to set Issue customer fields: {set_err}", "Assistant CRM NRC Populate")
        except Exception:
            pass


def _set_issue_employer_link(issue_name: str, customer_info: Optional[Dict[str, Any]] = None):
    """Populate Issue.employer (Link to Customer) when we can infer it.

    NOTE: Employee Profile and Employer Profile have been removed.
    Now uses ERPNext Employee and Customer doctypes.
    """
    try:
        meta = frappe.get_meta("Issue")
        if not (getattr(meta, "has_field", None) and meta.has_field("customer")):
            return
        if not customer_info:
            return
        if customer_info.get("kind") == "Employee" and customer_info.get("link_name"):
            emp = frappe.get_value(
                "Employee",
                customer_info.get("link_name"),
                ["company"],
                as_dict=True,
            )
            company = (emp or {}).get("company")
            # Try to find Customer by company name
            if company:
                customer = frappe.db.get_value("Customer", {"customer_name": company}, "name")
                if customer:
                    frappe.db.set_value("Issue", issue_name, {"customer": customer})
    except Exception as e:
        try:
            frappe.log_error(f"Failed to set Issue.customer: {e}", "Assistant CRM Customer Link")
        except Exception:
            pass


def _clear_invalid_issue_links(issue_doc):
    """Clear invalid link field values on Issue to prevent LinkValidationError.

    The Issue doctype has a 'company' field that links to 'Employer' doctype.
    If the company value doesn't exist in Employer, saving will fail with
    'Could not find Employer: <value>'. This function validates link fields
    and clears any invalid references before saving.

    This function is idempotent - safe to call multiple times. It only modifies
    the in-memory document object and does not persist changes or log unless
    an actual invalid value is found and cleared.
    """
    try:
        # Check and clear invalid 'company' field (links to Employer)
        company_val = getattr(issue_doc, "company", None)
        if company_val and not frappe.db.exists("Employer", company_val):
            issue_doc.company = None

        # Also check 'employer' custom field (links to Customer)
        employer_val = getattr(issue_doc, "employer", None)
        if employer_val and not frappe.db.exists("Customer", employer_val):
            issue_doc.employer = None
    except Exception:
        # Non-fatal: silently ignore errors to avoid blocking save
        pass


@frappe.whitelist()
def get_unified_inbox_conversations(filters: Dict[str, Any] = None, limit: int = 20, offset: int = 0):
    """
    Get unified inbox conversations with filtering and pagination.
    """
    try:
        # Default filters
        default_filters = {"docstatus": ["!=", 2]}  # Exclude deleted documents

        if filters:
            default_filters.update(filters)

        # Get conversations
        # Build fields list, include optional fields only if they exist
        base_fields = [
            "name", "conversation_id", "platform", "customer_name", "customer_phone",
            "customer_email", "status", "priority", "assigned_agent", "creation_time",
            "last_message_time", "last_message_preview", "ai_handled", "ai_mode", "ai_confidence_score",
            "has_active_call", "call_status", "custom_issue_id"
        ]
        try:
            meta = frappe.get_meta("Unified Inbox Conversation")
            if getattr(meta, "has_field", None) and meta.has_field("tags"):
                base_fields.append("tags")
            if getattr(meta, "has_field", None) and meta.has_field("subject"):
                base_fields.append("subject")
            if getattr(meta, "has_field", None) and meta.has_field("customer_nrc"):
                base_fields.append("customer_nrc")
        except Exception:
            pass

        conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters=default_filters,
            fields=base_fields,
            order_by="last_message_time desc",
            limit=limit,
            start=offset
        )

        # Get message counts for each conversation
        for conversation in conversations:
            message_count = frappe.db.count(
                "Unified Inbox Message",
                filters={"conversation": conversation.name}
            )
            conversation["message_count"] = message_count

            # Get unread message count
            unread_count = frappe.db.count(
                "Unified Inbox Message",
                filters={
                    "conversation": conversation.name,
                    "direction": "Inbound",
                    "read_status": "Unread"
                }
            )
            conversation["unread_count"] = unread_count

        return {
            "status": "success",
            "conversations": conversations,
            "total_count": len(conversations)
        }

    except Exception as e:
        frappe.log_error(f"Error getting conversations: {str(e)}", "Unified Inbox API Error")
        return {"status": "error", "message": "Failed to get conversations"}


@frappe.whitelist()
def get_conversations():
    """Simple wrapper for get_unified_inbox_conversations for JavaScript compatibility."""
    try:
        result = get_unified_inbox_conversations()
        if result.get("status") == "success":
            return {
                "status": "success",
                "data": result.get("conversations", [])
            }
        else:
            return {
                "status": "error",
                "message": result.get("message", "Failed to get conversations"),
                "data": []
            }
    except Exception as e:
        frappe.log_error(f"Error in get_conversations: {str(e)}", "Unified Inbox API Error")
        return {
            "status": "error",
            "message": str(e),
            "data": []
        }


@frappe.whitelist()
def search_conversations(q: str = None, limit: int = 50, offset: int = 0):
    """
    Search unified inbox conversations by keyword.
    Matches on customer name, phone, email, NRC (if present), tags/subject (if present),
    platform, last message preview, and also within message content/sender name.
    """
    try:
        kw = (q or "").strip()
        limit_i = int(limit) if str(limit).isdigit() else 50
        offset_i = int(offset) if str(offset).isdigit() else 0

        # If no query provided, behave like get_conversations for convenience
        if not kw:
            base = get_unified_inbox_conversations(limit=limit_i, offset=offset_i)
            if base.get("status") == "success":
                return {"status": "success", "data": base.get("conversations", [])}
            return {"status": "error", "message": base.get("message", "Failed to get conversations"), "data": []}

        like = f"%{kw}%"

        # Build select fields with optional columns guarded by metadata
        select_fields = [
            "c.name as name",
            "c.conversation_id as conversation_id",
            "c.platform as platform",
            "c.customer_name as customer_name",
            "c.customer_phone as customer_phone",
            "c.customer_email as customer_email",
            "c.status as status",
            "c.priority as priority",
            "c.assigned_agent as assigned_agent",
            "c.creation_time as creation_time",
            "c.last_message_time as last_message_time",
            "c.last_message_preview as last_message_preview",
            "c.ai_handled as ai_handled",
            "c.ai_mode as ai_mode",
            "c.ai_confidence_score as ai_confidence_score",
            "c.has_active_call as has_active_call",
            "c.call_status as call_status",
            "c.custom_issue_id as custom_issue_id",
            "c.custom_issue_id as issue_id",
            # inline counts for performance
            "(SELECT COUNT(*) FROM `tabUnified Inbox Message` mm WHERE mm.conversation = c.name) AS message_count",
            "(SELECT COUNT(*) FROM `tabUnified Inbox Message` mu WHERE mu.conversation = c.name AND mu.direction = 'Inbound' AND mu.read_status = 'Unread') AS unread_count",
        ]
        optional_like_columns = []
        try:
            meta = frappe.get_meta("Unified Inbox Conversation")
            if getattr(meta, "has_field", None) and meta.has_field("tags"):
                select_fields.append("c.tags as tags")
                optional_like_columns.append("c.tags")
            if getattr(meta, "has_field", None) and meta.has_field("subject"):
                select_fields.append("c.subject as subject")
                optional_like_columns.append("c.subject")
            if getattr(meta, "has_field", None) and meta.has_field("customer_nrc"):
                select_fields.append("c.customer_nrc as customer_nrc")
                optional_like_columns.append("c.customer_nrc")
        except Exception:
            pass

        # Build WHERE with OR across multiple columns
        or_clauses = [
            "c.customer_name LIKE %(like)s",
            "c.customer_phone LIKE %(like)s",
            "c.customer_email LIKE %(like)s",
            "c.assigned_agent LIKE %(like)s",
            "c.platform LIKE %(like)s",
            "c.last_message_preview LIKE %(like)s",
            "m.message_content LIKE %(like)s",
            "m.sender_name LIKE %(like)s",
        ]
        for col in optional_like_columns:
            or_clauses.append(f"{col} LIKE %(like)s")

        sql = f"""
            SELECT {', '.join(select_fields)}
            FROM `tabUnified Inbox Conversation` c
            LEFT JOIN `tabUnified Inbox Message` m ON m.conversation = c.name
            WHERE c.docstatus != 2 AND (
                {' OR '.join(or_clauses)}
            )
            GROUP BY c.name
            ORDER BY c.last_message_time DESC
            LIMIT %(limit)s OFFSET %(offset)s
        """

        rows = frappe.db.sql(
            sql,
            {"like": like, "limit": limit_i, "offset": offset_i},
            as_dict=True,
        )

        return {"status": "success", "data": rows}
    except Exception as e:
        frappe.log_error(f"Error searching conversations: {str(e)}", "Unified Inbox API Error")
        return {"status": "error", "message": str(e), "data": []}


@frappe.whitelist()
def set_conversation_ai_mode(conversation_name: str, mode: str):
    """Set conversation-level AI mode to Auto/On/Off."""
    try:
        valid_modes = {"Auto", "On", "Off"}
        mode = (mode or "").strip().title()
        if mode not in valid_modes:
            return {"status": "error", "message": f"Invalid mode: {mode}"}

        # Permission check: user must have write access on the conversation
        if not frappe.has_permission("Unified Inbox Conversation", "write", conversation_name):
            return {"status": "error", "message": "Permission denied"}

        doc = frappe.get_doc("Unified Inbox Conversation", conversation_name)
        doc.db_set("ai_mode", mode, update_modified=True)

        # Log for diagnostics
        try:
            frappe.logger("assistant_crm.unified_inbox_ai").info(
                f"[AI] mode_change conversation={conversation_name} mode={mode} by={frappe.session.user}"
            )
        except Exception:
            pass

        return {"status": "success", "mode": mode}
    except Exception as e:
        frappe.log_error(f"Error setting AI mode: {str(e)}", "Unified Inbox API Error")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_messages(conversation_name: str, limit: int = 200, offset: int = 0):
    """Simple wrapper for get_conversation_messages for JavaScript compatibility.
    - limit: number of messages to return (defaults to 200)
    - offset: optional offset for pagination
    """
    try:
        if not conversation_name:
            return {"status": "error", "message": "Conversation name is required", "data": []}

        result = get_conversation_messages(conversation_name, limit=int(limit), offset=int(offset))
        if result.get("status") == "success":
            return {
                "status": "success",
                "data": result.get("messages", [])
            }
        else:
            return {
                "status": "error",
                "message": result.get("message", "Failed to get messages"),
                "data": []
            }
    except Exception as e:
        frappe.log_error(f"Error in get_messages: {str(e)}", "Unified Inbox API Error")
        return {"status": "error", "message": str(e), "data": []}


@frappe.whitelist()
def get_conversation_messages(conversation_name: str, limit: int = 50, offset: int = 0):
    """
    Get messages for a specific conversation.
    """
    try:
        # Resolve conversation identifier: accept docname, platform_specific_id, or conversation_id
        resolved_name = conversation_name
        if not frappe.db.exists("Unified Inbox Conversation", resolved_name):
            alt = frappe.db.get_value("Unified Inbox Conversation", {"platform_specific_id": resolved_name}, "name")
            if not alt:
                alt = frappe.db.get_value("Unified Inbox Conversation", {"conversation_id": resolved_name}, "name")
            if alt:
                resolved_name = alt

        # Get conversation details (allow if user can see it; otherwise still try to fetch minimal info)
        conversation = frappe.get_doc("Unified Inbox Conversation", resolved_name)

        # Get messages (ignore permissions so agents with UI access can see full thread)
        # Return the LAST `limit` messages by default (so newest messages appear), preserving asc order for display
        total_count = frappe.db.count("Unified Inbox Message", {"conversation": resolved_name})
        start_index = offset or 0
        if (start_index == 0) and total_count and (total_count > limit):
            start_index = total_count - limit

        messages = frappe.get_all(
            "Unified Inbox Message",
            filters={"conversation": resolved_name},
            fields=[
                "name", "message_id", "direction", "message_type", "message_content",
                "sender_name", "timestamp", "processed_by_ai", "ai_response", "ai_confidence",
                "handled_by_agent", "agent_response", "has_attachments", "attachments_data",
                "delivery_status", "read_status"
            ],
            order_by="timestamp asc",
            limit=limit,
            start=start_index,
            ignore_permissions=True
        )

        # Mark inbound messages as read (best effort)
        try:
            unread_messages = [msg.name for msg in messages if msg.direction == "Inbound" and msg.read_status == "Unread"]
            if unread_messages:
                frappe.db.set_value("Unified Inbox Message", {"name": ["in", unread_messages]}, "read_status", "Read")
                frappe.db.set_value("Unified Inbox Message", {"name": ["in", unread_messages]}, "read_timestamp", now())
        except Exception:
            pass

        return {
            "status": "success",
            "conversation": conversation.as_dict(),
            "messages": messages
        }

    except Exception as e:
        frappe.log_error(f"Error getting messages: {str(e)}", "Unified Inbox API Error")
        return {"status": "error", "message": "Failed to get messages"}


@frappe.whitelist()
def send_message():
    """
    Enhanced send message function for unified inbox.
    - Preserves existing inbox behavior
    - Adds resilience against rare DocVersion conflicts on Conversation by retrying atomic updates
    - Switches diagnostics to frappe.logger so logs land in bench logs across environments
    """
    try:
        import time as _time
        log = frappe.logger("assistant_crm.unified_send")

        # Get data from request
        data = frappe.local.form_dict
        conversation_name = data.get("conversation_name")
        message_content = data.get("message")
        send_via_platform = data.get("send_via_platform", True)

        if not conversation_name:
            return {"status": "error", "message": "Conversation name is required"}

        if not message_content or not message_content.strip():
            return {"status": "error", "message": "Message content is required"}

        # Get conversation details using direct DB fetch (avoid Document save side-effects)
        conv = frappe.db.get_value(
            "Unified Inbox Conversation",
            conversation_name,
            ["name", "platform", "customer_name", "status", "last_message_time", "last_message_preview"],
            as_dict=True,
        )
        if not conv:
            return {"status": "error", "message": "Conversation not found"}

        # Get current user info (read-only)
        try:
            sender_name = frappe.get_value("User", frappe.session.user, "full_name") or frappe.session.user
        except Exception:
            sender_name = frappe.session.user

        # Diagnostics
        try:
            log.info(f"[SEND] start conv={conversation_name} platform={conv.get('platform')} user={frappe.session.user}")
        except Exception:
            pass

        # Create outbound message record
        message_doc = frappe.get_doc({
            "doctype": "Unified Inbox Message",
            "conversation": conversation_name,
            "platform": conv.get("platform"),
            "direction": "Outbound",
            "message_type": "text",
            "message_content": message_content.strip(),
            "sender_name": sender_name,
            "sender_id": frappe.session.user,
            "timestamp": now(),
            "handled_by_agent": 1,
            "agent_response": message_content.strip()
        })
        message_doc.insert(ignore_permissions=True)

        try:
            log.info(f"[SEND] after_insert msg={message_doc.name}")
        except Exception:
            pass

        # Update conversation with latest message info using atomic field updates to avoid modified conflicts
        _preview_full = message_content.strip()
        _preview = _preview_full[:100] + ("..." if len(_preview_full) > 100 else "")

        # Retry loop for rare concurrent writers touching the same conversation
        for attempt in range(1, 4):
            try:
                frappe.db.set_value(
                    "Unified Inbox Conversation",
                    conversation_name,
                    {
                        "last_message_time": now(),
                        "last_message_preview": _preview,
                        "status": "In Progress",
                    },
                    update_modified=True,
                )
                break
            except Exception as conv_err:
                text = str(conv_err) or ""
                if "has been modified after you have opened it" in text and attempt < 3:
                    try:
                        log.warning(f"[SEND] conv_update_conflict attempt={attempt} conv={conversation_name}; retrying")
                    except Exception:
                        pass
                    frappe.db.rollback()
                    _time.sleep(0.06 * attempt)
                    continue
                # Not a version conflict or max retries reached: re-raise
                raise

        try:
            log.info(f"[SEND] after_conv_update conv={conversation_name}")
        except Exception:
            pass

        # Determine if we should actually send via platform (always allow for live integrations)
        allow_platform_send = bool(send_via_platform)

        try:
            log.info(
                f"[SEND] allow_platform_send={allow_platform_send} platform={conv.get('platform')}"
            )
        except Exception:
            pass

        platform_send_result = {"status": "pending", "message": "Attempting platform send"}
        if allow_platform_send:
            try:
                if conv.get("platform") == "Tawk.to":
                    from assistant_crm.api.tawk_to_integration import send_tawk_to_message
                    platform_send_result = send_tawk_to_message(conversation_name, message_content, frappe.session.user)
                else:
                    from assistant_crm.api.social_media_ports import send_social_media_message
                    twitter_reply_mode = (data.get("twitter_reply_mode") or data.get("reply_mode")) if conv.get("platform") == "Twitter" else None
                    platform_send_result = send_social_media_message(
                        conv.get("platform"), conversation_name, message_content,
                        reply_mode=twitter_reply_mode
                    )
            except Exception as platform_error:
                frappe.log_error(f"Platform send error: {str(platform_error)}", "Platform Send Error")
                platform_send_result = {"status": "warning", "message": "Message saved but platform send failed"}

        frappe.db.commit()

        # Fetch updated conversation fields for response
        conv_updated = frappe.db.get_value(
            "Unified Inbox Conversation",
            conversation_name,
            ["name", "last_message_time", "last_message_preview", "status"],
            as_dict=True,
        ) or {}

        try:
            log.info(f"[SEND] end conv={conversation_name} msg={message_doc.name} platform_result={platform_send_result.get('status')}")
        except Exception:
            pass

        overall_status = "success"
        overall_message = "Message sent successfully"
        try:
            if allow_platform_send and platform_send_result and platform_send_result.get("status") != "success":
                overall_status = "error"
                overall_message = f"Failed to send message: {platform_send_result.get('message')}"
        except Exception:
            pass

        return {
            "status": overall_status,
            "message": overall_message,
            "data": {
                "message_id": message_doc.name,
                "message": {
                    "name": message_doc.name,
                    "direction": "Outbound",
                    "message_content": message_content.strip(),
                    "sender_name": sender_name,
                    "timestamp": message_doc.timestamp,
                    "agent_response": True
                },
                "conversation": {
                    "name": conv_updated.get("name"),
                    "last_message_time": conv_updated.get("last_message_time"),
                    "last_message_preview": conv_updated.get("last_message_preview"),
                    "status": conv_updated.get("status"),
                },
                "platform_send": platform_send_result
            }
        }

    except Exception as e:
        # Ensure meaningful error surfaces to the UI while capturing logs
        frappe.log_error(f"Error sending message: {str(e)}", "Unified Inbox API Error")
        return {"status": "error", "message": f"Failed to send message: {str(e)}"}


@frappe.whitelist()
def assign_conversation_to_agent(conversation_name: str, agent: str, notes: str = None):
	"""Assign conversation to a specific agent."""
	try:
		conversation_doc = frappe.get_doc("Unified Inbox Conversation", conversation_name)

		# Track previous assignee (if any) so we can refresh capacity for
		# both agents after manual reassignment.
		previous_agent = getattr(conversation_doc, "assigned_agent", None)

		# Update assignment
		conversation_doc.db_set("assigned_agent", agent)
		conversation_doc.db_set("agent_assigned_at", now())
		conversation_doc.db_set("status", "Agent Assigned")

		# Save notes if the field exists (guarded)
		if notes:
			try:
				if frappe.get_meta("Unified Inbox Conversation").has_field("agent_notes"):
					conversation_doc.db_set("agent_notes", notes)
			except Exception as notes_err:
				frappe.log_error(f"Failed to save assignment notes: {notes_err}", "Unified Inbox Assignment Notes")

		# Create notification for agent (best-effort, non-blocking)
		try:
			notification = frappe.get_doc({
				"doctype": "Notification Log",
				"subject": f"Conversation assigned: {conversation_doc.customer_name or 'Unknown Customer'}",
				"email_content": f"""
				<p>You have been assigned a conversation:</p>
				<ul>
					<li><strong>Platform:</strong> {conversation_doc.platform}</li>
					<li><strong>Customer:</strong> {conversation_doc.customer_name or 'Unknown'}</li>
					<li><strong>Priority:</strong> {conversation_doc.priority}</li>
					<li><strong>Last Message:</strong> {conversation_doc.last_message_preview or 'No preview available'}</li>
				</ul>
				{f'<p><strong>Notes:</strong> {notes}</p>' if notes else ''}
				""",
				"for_user": agent,
				"type": "Assignment",
			})
			notification.insert(ignore_permissions=True)
		except Exception as notif_err:
			frappe.log_error(f"Assignment notification failed: {notif_err}", "Unified Inbox Assignment Notification")

		# Refresh Agent Dashboard workload snapshot for the agents
		try:
			from assistant_crm.assistant_crm.assistant_crm_module.doctype.agent_dashboard.agent_dashboard import (  # type: ignore
				AgentDashboard,
			)
			# New assignee
			AgentDashboard.sync_unified_inbox_load_for_agent(agent)
			# Old assignee (if different)
			if previous_agent and previous_agent != agent:
				AgentDashboard.sync_unified_inbox_load_for_agent(previous_agent)
		except Exception as sync_err:
			frappe.log_error(f"Failed to sync agent load after manual assignment: {sync_err}", "Unified Inbox Agent Load Sync")

		return {
			"status": "success",
			"message": "Conversation assigned successfully",
		}
	except Exception as e:
		frappe.log_error(f"Error assigning conversation: {str(e)}", "Unified Inbox API Error")
		return {"status": "error", "message": "Failed to assign conversation"}


@frappe.whitelist()
def escalate_conversation(conversation_name: str, reason: str, priority: str = None):
	"""Escalate conversation to higher priority or different department."""
	try:
		conversation_doc = frappe.get_doc("Unified Inbox Conversation", conversation_name)

		# Update escalation details
		conversation_doc.db_set("escalated_at", now())
		conversation_doc.db_set("escalation_reason", reason)
		conversation_doc.db_set("escalated_by", frappe.session.user)
		# Once escalated, mark conversation as requiring explicit human
		# intervention so that subsequent inbound messages bypass AI.
		conversation_doc.db_set("requires_human_intervention", 1)

		if priority:
			conversation_doc.db_set("priority", priority)

		# Prefer currently assigned agent (supervisor) if present,
		# otherwise fall back to routing logic.
		target_agent = conversation_doc.find_available_agent()

		if target_agent:
			conversation_doc.db_set("escalated_agent", target_agent)
			conversation_doc.db_set("agent_assigned_at", now())
			conversation_doc.notify_agent_assignment(target_agent)

			# If there's a linked issue, sync the escalated agent there too
			issue_id = getattr(conversation_doc, "custom_issue_id", None)
			if issue_id:
				try:
					user_name = frappe.get_value("User", target_agent, "full_name") or target_agent
					display_name = f"{user_name} ({target_agent})"
					frappe.db.set_value("Issue", issue_id, {
						"custom_escalated_agent": target_agent,
						"custom_escalated_agent_name": display_name
					})
				except Exception as e:
					frappe.log_error(f"Failed to sync escalation to Issue: {str(e)}", "Unified Inbox Escalation Sync")

		# Create escalation record
		conversation_doc.create_escalation_record(target_agent or conversation_doc.assigned_agent, reason)

		# Refresh Agent Dashboard workload snapshot
		try:
			from assistant_crm.assistant_crm.assistant_crm_module.doctype.agent_dashboard.agent_dashboard import (  # type: ignore
				AgentDashboard,
			)
			if target_agent:
				AgentDashboard.sync_unified_inbox_load_for_agent(target_agent)
			elif conversation_doc.assigned_agent:
				AgentDashboard.sync_unified_inbox_load_for_agent(conversation_doc.assigned_agent)
		except Exception as sync_err:
			frappe.log_error(f"Failed to sync agent load after escalation: {sync_err}", "Unified Inbox Agent Load Sync")

		return {
			"status": "success",
			"message": "Conversation escalated successfully",
		}
	except Exception as e:
		frappe.log_error(f"Error escalating conversation: {str(e)}", "Unified Inbox API Error")
		return {"status": "error", "message": "Failed to escalate conversation"}


@frappe.whitelist()
def close_conversation(conversation_name: str, resolution_notes: str = None):
	"""Close a conversation."""
	try:
		conversation_doc = frappe.get_doc("Unified Inbox Conversation", conversation_name)

		# Remember which agent owned this conversation so we can refresh
		# their workload snapshot after it is closed.
		assigned_agent = getattr(conversation_doc, "assigned_agent", None)

		# Mark as resolved
		conversation_doc.mark_resolved(resolution_notes)

		# Clear explicit human-intervention flag once conversation is
		# closed; any future messages will start a new flow.
		try:
			conversation_doc.db_set("requires_human_intervention", 0)
		except Exception:
			# Field may not exist in some schemas; ignore quietly.
			pass

		# Refresh Agent Dashboard workload snapshot so that capacity-based
		# routing reflects the closed conversation.
		if assigned_agent:
			try:
				from assistant_crm.assistant_crm.assistant_crm_module.doctype.agent_dashboard.agent_dashboard import (  # type: ignore
					AgentDashboard,
				)
				AgentDashboard.sync_unified_inbox_load_for_agent(assigned_agent)
			except Exception as sync_err:
				frappe.log_error(f"Failed to sync agent load after close: {sync_err}", "Unified Inbox Agent Load Sync")

		return {
			"status": "success",
			"message": "Conversation closed successfully",
		}
	except Exception as e:
		frappe.log_error(f"Error closing conversation: {str(e)}", "Unified Inbox API Error")
		return {"status": "error", "message": "Failed to close conversation"}


@frappe.whitelist()
def get_agent_dashboard_data(agent: str = None):
    """
    Get dashboard data for agents.
    """
    try:
        if not agent:
            agent = frappe.session.user

        # Get assigned conversations
        assigned_conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters={"assigned_agent": agent, "status": ["not in", ["Resolved", "Closed"]]},
            fields=["name", "platform", "customer_name", "priority", "status", "last_message_time"],
            order_by="last_message_time desc"
        )

        # Get conversation statistics
        stats = {
            "total_assigned": len(assigned_conversations),
            "high_priority": len([c for c in assigned_conversations if c.priority == "High"]),
            "urgent": len([c for c in assigned_conversations if c.priority == "Urgent"]),
            "pending_response": len([c for c in assigned_conversations if c.status == "Pending Customer"])
        }

        # Get platform distribution
        platform_stats = {}
        for conversation in assigned_conversations:
            platform = conversation.platform
            platform_stats[platform] = platform_stats.get(platform, 0) + 1

        return {
            "status": "success",
            "assigned_conversations": assigned_conversations,
            "statistics": stats,
            "platform_distribution": platform_stats
        }

    except Exception as e:
        frappe.log_error(f"Error getting dashboard data: {str(e)}", "Unified Inbox API Error")
        return {"status": "error", "message": "Failed to get dashboard data"}


def process_conversation_with_ai(conversation_id: str):
    """
    Background job to process conversation with AI.
    """
    try:
        conversation_doc = frappe.get_doc("Unified Inbox Conversation", conversation_id)

        # Get latest unprocessed message
        latest_message = frappe.get_all(
            "Unified Inbox Message",
            filters={
                "conversation": conversation_id,
                "direction": "Inbound",
                "processed_by_ai": 0
            },
            fields=["name", "message_content"],
            order_by="timestamp desc",
            limit=1
        )

        if not latest_message:
            return

        message_doc = frappe.get_doc("Unified Inbox Message", latest_message[0].name)

        # Process with AI
        process_message_with_ai(message_doc.name)

    except Exception as e:
        try:
            frappe.log_error(
                f"Error in AI conversation processing: {str(e)}"[:2000],
                "Unified Inbox AI Error"[:140],
            )
        except Exception:
            pass


def process_message_with_ai(message_id: str):
    """
    Background job to process individual message with AI.
    """
    try:
        message_doc = frappe.get_doc("Unified Inbox Message", message_id)
        conversation_doc = frappe.get_doc("Unified Inbox Conversation", message_doc.conversation)

        # Diagnostic log for job start
        try:
            frappe.logger("assistant_crm.unified_inbox_ai").info(
                f"[AI] start message_id={message_id} conv={message_doc.conversation} platform={message_doc.platform}"
            )
        except Exception:
            pass

        # Get conversation context
        context = message_doc.get_conversation_context()

        # Survey flow interception: if conversation is in a locked survey session, handle here and bypass general AI
        try:
            import json as _json
            conv_ctx_raw = (context or {}).get("conversation_context")
            conv_ctx = _json.loads(conv_ctx_raw) if isinstance(conv_ctx_raw, str) else (conv_ctx_raw or {})
            survey_ctx = (conv_ctx or {}).get("survey") or {}
        except Exception:
            survey_ctx = {}

        if survey_ctx and survey_ctx.get("active"):
            user_text = (message_doc.message_content or "").strip()

            # STOP command to abort survey
            if user_text.upper() == "STOP":
                try:
                    survey_ctx["active"] = False
                    conv_ctx["survey"] = survey_ctx
                    try:
                        conversation_doc.db_set("ai_mode", "Auto")
                    except Exception:
                        pass
                    conversation_doc.db_set("conversation_context", _json.dumps(conv_ctx), update_modified=True)
                except Exception:
                    pass

                stop_msg = "Understood. We’ve stopped the survey for now. Thank you."
                # Record outbound message
                try:
                    out_doc = frappe.get_doc({
                        "doctype": "Unified Inbox Message",
                        "conversation": message_doc.conversation,
                        "platform": message_doc.platform,
                        "direction": "Outbound",
                        "message_type": "text",
                        "message_content": stop_msg,
                        "sender_name": "Survey Bot",
                        "sender_id": "survey_bot",
                        "timestamp": now(),
                        "processed_by_ai": 1
                    })
                    out_doc.insert(ignore_permissions=True)
                except Exception:
                    pass
                try:
                    from assistant_crm.api.social_media_ports import send_social_media_message
                    send_social_media_message(message_doc.platform, message_doc.conversation, stop_msg)
                except Exception:
                    pass
                try:
                    message_doc.db_set("processed_by_ai", 1)
                except Exception:
                    pass
                return

            # Main survey answer handling
            try:
                campaign_name = survey_ctx.get("campaign_name")
                response_id = survey_ctx.get("response_id")
                idx = int(survey_ctx.get("index") or 0)

                camp = frappe.get_doc("Survey Campaign", campaign_name)
                qs = sorted(list(camp.survey_questions or []), key=lambda q: ((q.order or 0), getattr(q, 'idx', 0)))
                total = len(qs)
                if idx < 0 or idx >= total:
                    idx = 0
                current = qs[idx] if qs else None
            except Exception:
                current = None
                qs, total = [], 0

            # Persist the answer
            try:
                sr = frappe.get_doc("Survey Response", response_id)
                answers = []
                if sr.answers:
                    answers = _json.loads(sr.answers) if isinstance(sr.answers, str) else (sr.answers or [])
                if not isinstance(answers, list):
                    answers = []

                val = user_text
                qtype = (current.question_type if current else "Text") or "Text"
                if current and qtype == "Multiple Choice":
                    opts = [o.strip() for o in (current.options or "").splitlines() if o.strip()]
                    if user_text.isdigit():
                        try:
                            n = int(user_text)
                            if 1 <= n <= len(opts):
                                val = opts[n-1]
                        except Exception:
                            pass
                    elif user_text in opts:
                        val = user_text
                elif current and qtype == "Rating":
                    try:
                        val_num = float(user_text)
                        if val_num < 0:
                            val_num = 0
                        if val_num > 10:
                            val_num = min(val_num, 10)
                        val = str(val_num)
                    except Exception:
                        pass
                elif current and qtype in ("Yes/No", "Yes-No", "Boolean"):
                    low = user_text.lower()
                    if low in ("yes", "y", "1", "true"):
                        val = "Yes"
                    elif low in ("no", "n", "0", "false"):
                        val = "No"

                answers.append({
                    "question_text": getattr(current, "question_text", "(free response)"),
                    "type": (qtype or "text").lower(),
                    "value": val,
                })

                sr.db_set("answers", _json.dumps(answers), update_modified=True)
                if idx == 0 and (sr.status or "") == "Sent":
                    sr.db_set("status", "In Progress", update_modified=True)
            except Exception:
                pass

            # Next step: advance index
            idx += 1
            if idx >= total:
                # Complete survey
                try:
                    sr = frappe.get_doc("Survey Response", response_id)
                    sr.db_set("status", "Completed", update_modified=True)
                    sr.db_set("response_time", now(), update_modified=True)
                except Exception:
                    pass
                try:
                    from assistant_crm.services.survey_service import SurveyService
                    SurveyService().update_campaign_statistics(campaign_name)
                except Exception:
                    pass
                try:
                    survey_ctx["active"] = False
                    conv_ctx["survey"] = survey_ctx
                    conversation_doc.db_set("conversation_context", _json.dumps(conv_ctx), update_modified=True)
                    conversation_doc.db_set("ai_mode", "Auto")
                    conversation_doc.db_set("status", "Resolved")
                except Exception:
                    pass

                final_msg = "Thanks for completing the survey. Your feedback helps us improve."
                try:
                    out_doc = frappe.get_doc({
                        "doctype": "Unified Inbox Message",
                        "conversation": message_doc.conversation,
                        "platform": message_doc.platform,
                        "direction": "Outbound",
                        "message_type": "text",
                        "message_content": final_msg,
                        "sender_name": "Survey Bot",
                        "sender_id": "survey_bot",
                        "timestamp": now(),
                        "processed_by_ai": 1
                    })
                    out_doc.insert(ignore_permissions=True)
                except Exception:
                    pass
                try:
                    from assistant_crm.api.social_media_ports import send_social_media_message
                    send_social_media_message(message_doc.platform, message_doc.conversation, final_msg)
                except Exception:
                    pass
                try:
                    message_doc.db_set("processed_by_ai", 1)
                except Exception:
                    pass
                return
            else:
                # Ask next question
                try:
                    next_q = qs[idx]
                    prompt = f"Q{idx+1}/{total}: {next_q.question_text}"
                    if (next_q.question_type or "") == "Multiple Choice" and (next_q.options or "").strip():
                        _opts = [o.strip() for o in next_q.options.splitlines() if o.strip()]
                        _num = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(_opts)])
                        prompt += f"\nPlease reply with the option number or text:\n{_num}"
                    elif (next_q.question_type or "") == "Rating":
                        prompt += "\nPlease reply with a number (e.g., 1-5)."
                    elif (next_q.question_type or "") in ("Yes/No", "Yes-No", "Boolean"):
                        prompt += "\nPlease reply Yes or No."
                except Exception:
                    prompt = "Please provide your response."

                try:
                    survey_ctx["index"] = idx
                    conv_ctx["survey"] = survey_ctx
                    conversation_doc.db_set("conversation_context", _json.dumps(conv_ctx), update_modified=True)
                except Exception:
                    pass

                try:
                    out_doc = frappe.get_doc({
                        "doctype": "Unified Inbox Message",
                        "conversation": message_doc.conversation,
                        "platform": message_doc.platform,
                        "direction": "Outbound",
                        "message_type": "text",
                        "message_content": prompt,
                        "sender_name": "Survey Bot",
                        "sender_id": "survey_bot",
                        "timestamp": now(),
                        "processed_by_ai": 1
                    })
                    out_doc.insert(ignore_permissions=True)
                except Exception:
                    pass
                try:
                    from assistant_crm.api.social_media_ports import send_social_media_message
                    send_social_media_message(message_doc.platform, message_doc.conversation, prompt)
                except Exception:
                    pass
                try:
                    message_doc.db_set("processed_by_ai", 1)
                except Exception:
                    pass
                return

        # Call AI service using a direct WorkCom path (no SimplifiedChat layer)
        start_time = time.time()

        # Get customer context from CoreBusiness if available
        customer_context = None
        if conversation_doc.customer_phone:
            try:
                from assistant_crm.api.corebusiness_integration import get_customer_context
                customer_context = get_customer_context(conversation_doc.customer_phone)
            except Exception as e:
                frappe.log_error(f"Error getting customer context: {str(e)}", "CoreBusiness Integration")

        # Base context from conversation + message
        enhanced_context = context.copy() if context else {}
        if customer_context:
            enhanced_context.update({
                "customer_data": customer_context,
                "has_live_data": True,
                "data_source": "CoreBusiness",
            })

        # Lightweight intent routing to keep the same parsing semantics as SimplifiedChatAPI
        routing_result = {}
        try:
            from assistant_crm.services.intent_router import IntentRouter
            router = IntentRouter()
            user_context = {
                "user_id": conversation_doc.customer_platform_id or conversation_doc.customer_phone or "guest",
                "user_role": "guest",
                "authenticated": False,
            }
            routing_result = router.route_request(
                message=(message_doc.message_content or ""),
                user_context=user_context,
            ) or {}
        except Exception:
            routing_result = {}

        # Build WorkCom context, mirroring SimplifiedChatAPI._generate_ai_response
        ai_context = enhanced_context.copy()
        try:
            ai_context.update({
                "user_message": message_doc.message_content,
                "intent": routing_result.get("intent", "unknown"),
                "confidence": routing_result.get("confidence", 0),
                "data_source": routing_result.get("source", ai_context.get("data_source", "unknown")),
            })

            # Live data from router if available
            if routing_result.get("source") == "live_data" and routing_result.get("data"):
                live_data = routing_result.get("data")
                # Unwrap nested 'data' if present so WorkCom sees the raw structure
                if isinstance(live_data, dict) and "type" not in live_data and isinstance(live_data.get("data"), dict):
                    live_data = live_data.get("data")
                ai_context["live_data"] = live_data
                ai_context["has_live_data"] = True
            else:
                # Preserve existing has_live_data flag from CoreBusiness if set
                ai_context["has_live_data"] = bool(ai_context.get("has_live_data"))

            # Conversation history derived from recent messages
            history = []
            recent_messages = (context or {}).get("recent_messages") or []
            if isinstance(recent_messages, list):
                # Convert to the same structure SimplifiedChatAPI uses (role/text/ts)
                for m in reversed(recent_messages):  # oldest first
                    text = (m.get("message_content") or m.get("ai_response") or m.get("agent_response") or "").strip()
                    if not text:
                        continue
                    direction = (m.get("direction") or "").lower()
                    role = "user" if direction == "inbound" else "assistant"
                    history.append({
                        "role": role,
                        "text": text[:2000],
                        "ts": str(m.get("timestamp") or ""),
                    })
            if history:
                ai_context["conversation_history"] = history[-12:]
        except Exception:
            pass

        # High-signal pre-call diagnostics (mirrors previous logging, but using ai_context)
        try:
            intent_guess = ai_context.get("intent", "unknown")
            live = bool(ai_context.get("has_live_data"))
            source = ai_context.get("data_source") or "none"
            frappe.logger("assistant_crm.unified_inbox_ai").info(
                f"[AI] pre-call msg={message_id} conv={conversation_doc.name} sess={conversation_doc.conversation_id} platform={message_doc.platform} intent={intent_guess} live_data={live} source={source}"
            )
        except Exception:
            pass
        try:
            with open("/workspace/development/frappe-bench/logs/webhook_debug.log", "a") as f:
                f.write(
                    f"[AI-DIAG] pre_call message_id={message_id} conv={conversation_doc.name} sess={conversation_doc.conversation_id} platform={message_doc.platform} intent={ai_context.get('intent', 'unknown')} live_data={ai_context.get('has_live_data', False)} source={ai_context.get('data_source', 'unknown')}\n"
                )
        except Exception:
            pass

        # Direct WorkCom call, mirroring report doctypes and SimplifiedChatAPI's preferred path
        ai_response = ""
        try:
            from assistant_crm.services.enhanced_ai_service import EnhancedAIService
            ai_service = EnhancedAIService()
            ai_response = ai_service.generate_unified_inbox_reply(
                message=message_doc.message_content or "",
                context=ai_context,
            ) or ""
        except Exception as e:
            frappe.log_error(f"Error generating AI response: {str(e)}", "Unified Inbox AI Error")
            ai_response = (
                "I'm sorry, I'm having trouble processing your request right now. "
                "Please try again later or ask to speak with a human agent."
            )

        processing_time = time.time() - start_time

        # Confidence derived from intent router (mirrors metadata.confidence in SimplifiedChatAPI)
        try:
            confidence = float(routing_result.get("confidence", 0.0)) if isinstance(routing_result, dict) else 0.0
        except Exception:
            confidence = 0.0

        # Diagnostic log for AI result
        try:
            frappe.logger("assistant_crm.unified_inbox_ai").info(
                f"[AI] result msg={message_id} conv={conversation_doc.name} sess={conversation_doc.conversation_id} platform={message_doc.platform} intent={ai_context.get('intent', 'unknown')} live_data={ai_context.get('has_live_data', False)} source={ai_context.get('data_source', 'unknown')} conf={confidence:.3f} ai_len={len(ai_response or '')} duration={processing_time:.3f}s"
            )
        except Exception:
            pass
        try:
            with open("/workspace/development/frappe-bench/logs/webhook_debug.log", "a") as f:
                f.write(
                    f"[AI-DIAG] post_call message_id={message_id} conv={conversation_doc.name} sess={conversation_doc.conversation_id} platform={message_doc.platform} intent={ai_context.get('intent', 'unknown')} live_data={ai_context.get('has_live_data', False)} source={ai_context.get('data_source', 'unknown')} conf={confidence:.3f} ai_len={len(ai_response or '')} duration={processing_time:.3f}s\n"
                )
        except Exception:
            pass

        # Update message with AI response
        message_doc.set_ai_response(
            response=ai_response,
            confidence=confidence,
            model_used="WorkCom",
            processing_time=processing_time
        )

        # Update conversation
        conversation_doc.db_set("ai_confidence_score", confidence)
        conversation_doc.db_set("ai_last_response", ai_response)

        # Send AI response if confidence is high enough
        if confidence >= 0.0 and ai_response:  # TEMPORARY: lowered threshold to 0.0 for visibility
            # Create outbound message with AI response
            ai_message_doc = frappe.get_doc({
                "doctype": "Unified Inbox Message",
                "conversation": message_doc.conversation,
                "platform": message_doc.platform,
                "direction": "Outbound",
                "message_type": "text",
                "message_content": ai_response,
                "sender_name": "WorkCom",
                "sender_id": "ai_assistant",
                "timestamp": now(),
                "processed_by_ai": 1,
                "ai_response": ai_response,
                "ai_confidence": confidence
            })

            ai_message_doc.insert(ignore_permissions=True)

            # Send via platform
            send_result = None
            if conversation_doc.platform == "Tawk.to":
                from assistant_crm.api.tawk_to_integration import send_tawk_to_message
                send_result = send_tawk_to_message(message_doc.conversation, ai_response)
            else:
                from assistant_crm.api.social_media_ports import send_social_media_message
                send_result = send_social_media_message(message_doc.platform, message_doc.conversation, ai_response)

            # Diagnostic log for send result
            try:
                frappe.logger("assistant_crm.unified_inbox_ai").info(
                    f"[AI] sent message_id={message_id} platform={message_doc.platform} result={send_result}"
                )
            except Exception:
                pass

            # Update conversation status
            conversation_doc.db_set("status", "AI Responded")

        else:
            # Low confidence - escalate to human agent
            conversation_doc.escalate_to_human_agent(f"Low AI confidence: {confidence}")

        # Mark inbound message as processed by AI (after completion)
        try:
            message_doc.db_set("processed_by_ai", 1)
        except Exception as e:
            frappe.log_error(f"Failed to set processed_by_ai for {message_id}: {str(e)}", "Unified Inbox AI")

        # Final diagnostic log
        try:
            frappe.logger("assistant_crm.unified_inbox_ai").info(
                f"[AI] done message_id={message_id} conv={message_doc.conversation} conf={confidence:.3f} sent={'yes' if (confidence >= 0.0 and ai_response) else 'no'}  # TEMPORARY threshold=0.0"
            )
        except Exception:
            pass


    except Exception as e:
        try:
            frappe.log_error(
                f"Error in AI message processing: {str(e)}"[:2000],
                "Unified Inbox AI Error"[:140],
            )
        except Exception:
            pass


@frappe.whitelist()
def get_ai_performance_metrics():
    """Get AI performance metrics for the last 24 hours."""
    try:
        from frappe.utils import add_days
        yesterday = add_days(now(), -1)

        ai_messages = frappe.get_all(
            "Unified Inbox Message",
            filters={
                "processed_by_ai": 1,
                "timestamp": [">=", yesterday],
            },
            fields=["ai_confidence", "requires_escalation", "platform"],
        )

        if not ai_messages:
            return {
                "status": "success",
                "metrics": {
                    "total_processed": 0,
                    "average_confidence": 0,
                    "escalation_rate": 0,
                    "platform_breakdown": {},
                },
            }

        total_processed = len(ai_messages)
        total_confidence = sum((msg.ai_confidence or 0) for msg in ai_messages)
        average_confidence = (total_confidence / total_processed) if total_processed else 0
        escalated_count = len([msg for msg in ai_messages if msg.requires_escalation])
        escalation_rate = (escalated_count / total_processed) * 100 if total_processed else 0

        platform_breakdown = {}
        for msg in ai_messages:
            plat = msg.platform or "Unknown"
            if plat not in platform_breakdown:
                platform_breakdown[plat] = {"count": 0, "total_confidence": 0}
            platform_breakdown[plat]["count"] += 1
            platform_breakdown[plat]["total_confidence"] += (msg.ai_confidence or 0)

        for plat, data in platform_breakdown.items():
            count = data["count"]
            data["average_confidence"] = (data["total_confidence"] / count) if count else 0
            # Remove helper field to keep output clean
            del data["total_confidence"]

        return {
            "status": "success",
            "metrics": {
                "total_processed": total_processed,
                "average_confidence": round(average_confidence, 3),
                "escalation_rate": round(escalation_rate, 2),
                "platform_breakdown": platform_breakdown,
            },
        }

    except Exception as e:
        frappe.log_error(f"Error getting AI metrics: {str(e)}", "Unified Inbox API Error")
        return {"status": "error", "message": "Failed to get AI metrics"}

# Utility to manually import recent webhook messages from log
# This is a diagnostic/repair helper to backfill Unified Inbox when webhook processing was interrupted
import os
import json as _json
import datetime as _dt


def _iter_recent_facebook_raw_webhooks_from_log(log_path: str, limit: int = 4):
    """Yield up to `limit` most recent Facebook webhook payloads from webhook_debug.log.
    It scans for lines starting with 'DEBUG: Raw webhook data: ' and parses the JSON that follows.
    """
    try:
        if not os.path.exists(log_path):
            return []
        # Read last ~5000 lines to find recent payloads
        with open(log_path, 'r') as f:
            lines = f.readlines()[-5000:]
        payloads = []
        prefix = 'DEBUG: Raw webhook data: '
        for line in reversed(lines):
            if line.startswith(prefix):
                raw = line[len(prefix):].strip()
                try:
                    data = _json.loads(raw)
                    # Only accept Facebook page webhooks
                    if isinstance(data, dict) and data.get('object') == 'page':
                        payloads.append(data)
                        if len(payloads) >= limit:
                            break
                except Exception:
                    continue
        return list(reversed(payloads))  # return in chronological order
    except Exception:
        return []


def _create_fb_message_from_payload(payload) -> list:
    """Create Unified Inbox Conversation/Message docs for a single Facebook webhook payload.
    Returns a list of results per messaging event.
    """
    results = []
    try:
        from assistant_crm.api.social_media_ports import FacebookIntegration
        fb = FacebookIntegration()
        entries = payload.get('entry') or []
        for entry in entries:
            messaging = entry.get('messaging') or []
            for evt in messaging:
                sender = (evt.get('sender') or {}).get('id')
                message = evt.get('message') or {}
                mid = message.get('mid')
                text = message.get('text') or '[Media message]'
                ts_ms = evt.get('timestamp') or 0
                # Build platform_data
                customer_name = f"Facebook User {sender[-6:]}" if sender else 'Facebook User'
                platform_data = {
                    'conversation_id': sender,
                    'customer_name': customer_name,
                    'customer_platform_id': sender,
                    'customer_phone': None,
                    'customer_email': None,
                    'initial_message': text,
                }
                conv = fb.create_unified_inbox_conversation(platform_data)
                if not conv:
                    results.append({'status': 'error', 'message': 'failed to create/find conversation', 'mid': mid})
                    continue
                # Timestamp conversion
                if ts_ms:
                    dt = _dt.datetime.fromtimestamp(ts_ms / 1000)
                    ts_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    from frappe.utils import now as _now
                    ts_str = _now()
                message_data = {
                    'message_id': mid,
                    'content': text,
                    'sender_name': customer_name,
                    'sender_platform_id': sender,
                    'timestamp': ts_str,
                    'direction': 'Inbound',
                    'message_type': 'text',
                    'metadata': evt,
                }
                msg = fb.create_unified_inbox_message(conv, message_data)
                fb.update_conversation_timestamp(conv, ts_str)
                results.append({'status': 'success', 'conversation': conv, 'message': msg, 'mid': mid})
    except Exception as e:
        results.append({'status': 'error', 'message': str(e)})
    return results


@frappe.whitelist()
def manual_import_last_webhook_messages(limit: int = 4, platform: str = 'Facebook'):
    """Manually backfill the last `limit` webhook messages from webhook_debug.log into Unified Inbox.
    - platform: currently supports 'Facebook'
    Returns a summary of created/exists/error per message.
    """
    try:
        log_path = '/workspace/development/frappe-bench/logs/webhook_debug.log'
        summary = {'platform': platform, 'limit': int(limit), 'results': []}
        if platform != 'Facebook':
            return {'status': 'error', 'message': f'Platform {platform} not supported by manual import yet'}
        payloads = _iter_recent_facebook_raw_webhooks_from_log(log_path, int(limit))
        if not payloads:
            return {'status': 'error', 'message': 'No recent webhook payloads found in log'}
        for payload in payloads:
            res = _create_fb_message_from_payload(payload)
            summary['results'].extend(res)
        return {'status': 'success', 'data': summary}
    except Exception as e:
        frappe.log_error(f'Manual import error: {str(e)}', 'Unified Inbox Manual Import')
        return {'status': 'error', 'message': str(e)}



@frappe.whitelist()
def sync_all_platforms():
    """
    Sync all platform integrations manually.
    """
    try:
        results = {}

        # Sync Tawk.to
        from assistant_crm.api.tawk_to_integration import sync_all_tawk_to_chats
        tawk_result = sync_all_tawk_to_chats()
        results["Tawk.to"] = tawk_result

        # Get platform status for social media
        from assistant_crm.api.social_media_ports import get_platform_status
        platform_status = get_platform_status()
        results["social_media_status"] = platform_status

        return {
            "status": "success",
            "message": "Platform sync completed",
            "results": results
        }

    except Exception as e:
        frappe.log_error(f"Error syncing platforms: {str(e)}", "Unified Inbox API Error")
        return {"status": "error", "message": "Failed to sync platforms"}


@frappe.whitelist()
def enhanced_escalate_conversation():
    """
    DEPRECATED: Use escalate_to_erpnext_issue() instead.
    This method is kept for backward compatibility.
    """
    try:
        data = frappe.local.form_dict
        conversation_name = data.get("conversation_name")

        return {
            "status": "deprecated",
            "message": "This escalation method is deprecated. Please use ERPNext Issue escalation instead.",
            "redirect_to": "escalate_to_erpnext_issue"
        }

    except Exception as e:
        frappe.log_error(f"Error in deprecated escalation method: {str(e)}", "Deprecated Escalation")
        return {"status": "error", "message": "Deprecated escalation method failed"}


@frappe.whitelist()
def enhanced_assign_conversation():
    """Enhanced assign conversation with full functionality."""
    try:
        data = frappe.local.form_dict
        conversation_name = data.get("conversation_name")
        target_agent = data.get("target_agent")
        assignment_notes = data.get("assignment_notes", "")

        if not conversation_name:
            return {"status": "error", "message": "Conversation name is required"}

        if not target_agent:
            return {"status": "error", "message": "Target agent is required"}

        # Check if agent exists and is active
        if not frappe.db.exists("User", target_agent):
            return {"status": "error", "message": "Selected agent does not exist"}

        agent_doc = frappe.get_doc("User", target_agent)
        if not agent_doc.enabled:
            return {"status": "error", "message": "Selected agent is not active"}

        # Get conversation
        conversation = frappe.get_doc("Unified Inbox Conversation", conversation_name)

        # Update conversation
        conversation.assigned_agent = target_agent
        conversation.status = "Agent Assigned"
        conversation.assigned_at = frappe.utils.now()
        conversation.assigned_by = frappe.session.user
        conversation.save(ignore_permissions=True)

        # Create assignment log message
        assignment_message = frappe.get_doc({
            "doctype": "Unified Inbox Message",
            "conversation": conversation_name,
            "platform": conversation.platform,
            "direction": "System",
            "message_type": "system",
            "message_content": f"👤 Conversation assigned to {agent_doc.full_name or target_agent}. {assignment_notes}",
            "sender_name": "System",
            "timestamp": frappe.utils.now(),
            "is_system_message": 1
        })
        assignment_message.insert(ignore_permissions=True)

        # Send notification to assigned agent
        send_assignment_notification(target_agent, conversation)

        frappe.db.commit()

        return {
            "status": "success",
            "message": "Conversation assigned successfully",
            "conversation": {
                "name": conversation.name,
                "status": conversation.status,
                "assigned_agent": conversation.assigned_agent,
                "assigned_agent_name": agent_doc.full_name or target_agent
            }
        }

    except Exception as e:
        frappe.log_error(f"Error assigning conversation: {str(e)}", "Conversation Assignment")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def assign_conversation_to_user(doctype, docname, assign_to, description=None):
    """
    Assign conversation using ERPNext's native assignment system.
    This integrates with ERPNext's built-in assignment functionality.
    """
    try:
        # Validate that the user exists and is enabled
        if not frappe.db.exists("User", assign_to):
            return {
                "status": "error",
                "message": f"User {assign_to} does not exist"
            }

        user = frappe.get_doc("User", assign_to)
        if not user.enabled:
            return {
                "status": "error",
                "message": f"User {assign_to} is disabled"
            }

        # Use ERPNext's assignment system
        try:
            from frappe.desk.form.assign_to import add as add_assignment

            # Check if user has permission to assign
            if not frappe.has_permission(doctype, "write", docname):
                return {
                    "status": "error",
                    "error": f"No permission to assign {doctype} {docname}"
                }

            # Add assignment using ERPNext's native system
            assignment = add_assignment({
                "assign_to": [assign_to],
                "doctype": doctype,
                "name": docname,
                "description": description or f"Assigned conversation {docname}"
            })

        except ImportError as import_error:
            frappe.log_error(f"ERPNext assignment import error: {str(import_error)}", "Assignment Import Error")
            return {
                "status": "error",
                "error": f"ERPNext assignment system not available: {str(import_error)}"
            }
        except Exception as assignment_error:
            frappe.log_error(f"Assignment error: {str(assignment_error)}", "Assignment Error")
            return {
                "status": "error",
                "error": f"Assignment failed: {str(assignment_error)}"
            }

        # Update conversation status
        conversation = frappe.get_doc("Unified Inbox Conversation", docname)
        conversation.assigned_agent = assign_to
        conversation.status = "Agent Assigned"
        conversation.assigned_at = frappe.utils.now()
        conversation.assigned_by = frappe.session.user
        conversation.save(ignore_permissions=True)

        # Create assignment log (if the DocType exists)
        try:
            if frappe.db.exists("DocType", "Unified Inbox Assignment Log"):
                frappe.get_doc({
                    "doctype": "Unified Inbox Assignment Log",
                    "conversation": docname,
                    "assigned_to": assign_to,
                    "assigned_by": frappe.session.user,
                    "assignment_type": "Manual",
                    "assignment_reason": "Manual assignment via Inbox",
                    "assignment_notes": description
                }).insert(ignore_permissions=True)
            else:
                # Log assignment in standard way
                frappe.log_error(
                    f"Assignment completed: {docname} assigned to {assign_to} by {frappe.session.user}",
                    "Unified Inbox Assignment"
                )
        except Exception as log_error:
            # Log the error but don't fail the assignment
            frappe.log_error(f"Failed to create assignment log: {str(log_error)}", "Assignment Log Error")
            pass

        # Return response in ERPNext AssignToDialog expected format
        # ERPNext AssignToDialog expects the response directly under 'message'
        return {
            "assigned_to": assign_to,
            "assigned_to_name": user.full_name or user.first_name or user.email,
            "status": "success",
            "conversation_name": docname,
            "assignment_details": assignment
        }

    except Exception as e:
        frappe.log_error(f"Error in assign_conversation_to_user: {str(e)}", "Unified Inbox Assignment Error")
        # Return error in ERPNext expected format
        return {
            "status": "error",
            "error": f"Failed to assign conversation: {str(e)}"
        }


@frappe.whitelist()
def get_available_agents():
    """
    Get list of available agents/users who can be assigned conversations.
    Returns users with appropriate roles for customer service.
    """
    try:
        print("DEBUG: Starting get_available_agents API call")

        # Get all enabled system users (simplified approach)
        users = frappe.get_all(
            "User",
            filters={
                "enabled": 1,
                "user_type": "System User",
                "name": ["!=", "Administrator"]
            },
            fields=["name", "email", "full_name", "first_name"]
        )

        print(f"DEBUG: Found {len(users)} total system users")

        # Simple role filtering
        available_users = []
        customer_service_roles = ["System Manager", "Assistant CRM Agent", "Assistant CRM Manager"]

        for user in users:
            try:
                user_roles = frappe.get_roles(user.name)
                print(f"DEBUG: User {user.email} has roles: {user_roles}")

                # Check for any customer service role
                if any(role in customer_service_roles for role in user_roles):
                    available_users.append({
                        "name": user.name,
                        "email": user.email,
                        "full_name": user.full_name or user.first_name or user.email,
                        "first_name": user.first_name,
                        "roles": user_roles
                    })
                    print(f"DEBUG: Added user {user.email} to available agents")
            except Exception as user_error:
                print(f"DEBUG: Error processing user {user.get('email', 'unknown')}: {str(user_error)}")
                continue

        print(f"DEBUG: Final available users count: {len(available_users)}")

        # Always include current user as fallback
        if not available_users:
            current_user = frappe.get_doc("User", frappe.session.user)
            available_users = [{
                "name": current_user.name,
                "email": current_user.email,
                "full_name": current_user.full_name or current_user.first_name or current_user.email,
                "first_name": current_user.first_name,
                "roles": ["Current User"]
            }]
            print("DEBUG: No users found, using current user as fallback")

        return {
            "status": "success",
            "data": available_users,
            "count": len(available_users)
        }

    except Exception as e:
        error_msg = f"Error getting available agents: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Get Available Agents Error")

        # Return error instead of demo agents
        return {
            "status": "error",
            "message": error_msg,
            "data": [],
            "count": 0
        }


@frappe.whitelist()
def get_supervisors():
    """
    Get list of supervisors (Assistant CRM Manager or System Manager).
    Used for filtering the escalation target user list.
    """
    try:
        # Get all enabled system users
        users = frappe.get_all(
            "User",
            filters={
                "enabled": 1,
                "user_type": "System User",
                "name": ["!=", "Administrator"]
            },
            fields=["name", "email", "full_name", "first_name"]
        )

        supervisors = []
        # Define supervisor roles
        supervisor_roles = ["System Manager", "Assistant CRM Manager"]

        for user in users:
            try:
                user_roles = frappe.get_roles(user.name)
                # Check for any supervisor role
                if any(role in supervisor_roles for role in user_roles):
                    supervisors.append({
                        "name": user.name,
                        "email": user.email,
                        "full_name": user.full_name or user.first_name or user.email,
                        "first_name": user.first_name
                    })
            except Exception:
                continue

        # If no specific supervisors found, return all available agents as fallback
        if not supervisors:
            agents_result = get_available_agents()
            if agents_result.get("status") == "success":
                supervisors = agents_result.get("data", [])

        return {
            "status": "success",
            "data": supervisors,
            "count": len(supervisors)
        }
    except Exception as e:
        frappe.log_error(f"Error getting supervisors: {str(e)}", "Unified Inbox API Error")
        return {"status": "error", "message": str(e), "data": []}


@frappe.whitelist()
def create_issue_for_conversation(conversation_name, customer_name, platform, initial_message, customer_phone=None, customer_nrc=None, priority="Medium"):
    """
    Create an ERPNext Issue for a new conversation.
    This provides automatic ticket generation for customer service tracking.
    """
    try:
        # Defensive: ensure Issue.custom_platform_source options include all omnichannel platforms (e.g. USSD)
        try:
            from assistant_crm.install import ensure_issue_platform_source_field_options
            ensure_issue_platform_source_field_options()
        except Exception:
            # Do not block ticket creation if this repair fails for any reason
            pass

        print(f"DEBUG: Creating Issue for conversation {conversation_name}, customer {customer_name}, platform {platform}")

        # Create real ERPNext Issues for ALL conversations (including demo conversations)

        # Check if Issue already exists for this conversation
        existing_issue = frappe.db.get_value(
            "Issue",
            {"custom_conversation_id": conversation_name},
            "name"
        )

        if existing_issue:
            print(f"DEBUG: Found existing Issue {existing_issue} for conversation {conversation_name}")
            print(f"DEBUG: Updating existing Issue with new message and complete conversation history")

            # Update existing Issue with complete conversation history
            update_result = update_issue_with_conversation_history(conversation_name)

            if update_result.get("status") == "success":
                print(f"DEBUG: Successfully updated existing Issue {existing_issue}")
                return {
                    "status": "success",
                    "message": f"Updated existing Issue {existing_issue} with new message",
                    "issue_id": existing_issue,
                    "existing": True,
                    "updated": True
                }
            else:
                print(f"DEBUG: Failed to update existing Issue: {update_result.get('message')}")
                return {
                    "status": "success",
                    "message": f"Using existing Issue {existing_issue} (update failed)",
                    "issue_id": existing_issue,
                    "existing": True,
                    "updated": False
                }

        # Get the actual detected platform from the conversation
        detected_platform = None
        try:
            conversation_doc = frappe.get_doc("Unified Inbox Conversation", conversation_name)
            detected_platform = conversation_doc.platform
            print(f"DEBUG: Detected platform from conversation: {detected_platform}")
        except Exception as e:
            print(f"DEBUG: Could not get platform from conversation, using provided platform: {platform}")
            detected_platform = platform

        # Create new Issue with minimal required fields only
        issue_doc = frappe.get_doc({
            "doctype": "Issue",
            "subject": f"Customer Inquiry - {customer_name} - {detected_platform}",
            "custom_conversation_id": conversation_name,  # CRITICAL: Set conversation ID for duplicate prevention
            "custom_platform_source": detected_platform  # CRITICAL: Set correct platform source from detected platform
        })

        # Add description if possible
        try:
            issue_doc.description = f"Customer: {customer_name}\nPlatform: {detected_platform}\nMessage: {initial_message}"
        except Exception:
            pass

        # Add priority if possible
        try:
            issue_doc.priority = priority
        except Exception:
            pass

        # Insert first to obtain a name, then set optional custom fields safely
        issue_doc.insert(ignore_permissions=True)

        # Determine NRC to use: param > conversation field > extract from initial message
        conv_nrc = None
        try:
            if 'conversation_doc' in locals() and conversation_doc:
                conv_nrc = getattr(conversation_doc, 'customer_nrc', None)
        except Exception:
            conv_nrc = None
        nrc_to_use = customer_nrc or conv_nrc or _extract_first_nrc_from_text(initial_message)

        # Lookup beneficiary/employee by NRC
        customer_info = _find_beneficiary_or_employee_by_nrc(nrc_to_use) if nrc_to_use else None

        # Persist NRC/phone/beneficiary on the Issue if fields exist
        _set_issue_customer_fields(issue_doc.name, nrc_to_use, customer_phone, customer_info)
        # Also try to set employer link on Issue when possible (via Employee -> employer_code)
        _set_issue_employer_link(issue_doc.name, customer_info)

        # Also persist NRC on conversation if field exists
        try:
            conv_meta = frappe.get_meta("Unified Inbox Conversation")
            if nrc_to_use and getattr(conv_meta, 'has_field', None) and conv_meta.has_field('customer_nrc'):
                frappe.db.set_value("Unified Inbox Conversation", conversation_name, {"customer_nrc": _normalize_nrc(nrc_to_use)})
        except Exception:
            pass
        print(f"DEBUG: Issue created successfully with ID: {issue_doc.name}")

        # Update conversation with Issue reference
        if frappe.db.exists("Unified Inbox Conversation", conversation_name):
            frappe.db.set_value(
                "Unified Inbox Conversation",
                conversation_name,
                "custom_issue_id",
                issue_doc.name
            )

        # Initialize Issue with current conversation history
        print(f"DEBUG: Initializing new Issue {issue_doc.name} with conversation history")
        initial_update_result = update_issue_with_conversation_history(conversation_name)

        if initial_update_result.get("status") == "success":
            print(f"DEBUG: Successfully initialized Issue {issue_doc.name} with conversation history")
        else:
            print(f"DEBUG: Failed to initialize Issue with conversation history: {initial_update_result.get('message')}")

        return {
            "status": "success",
            "message": f"New Issue {issue_doc.name} created successfully",
            "issue_id": issue_doc.name,
            "issue_url": f"/app/issue/{issue_doc.name}",
            "existing": False
        }

    except Exception as e:
        error_msg = f"Error creating issue for conversation {conversation_name}: {str(e)}"
        frappe.log_error(error_msg, "Issue Creation Error")
        print(f"DEBUG: {error_msg}")  # Debug logging
        return {
            "status": "error",
            "message": f"Failed to create issue: {str(e)}",
            "debug_info": error_msg
        }


@frappe.whitelist()
def sync_conversation_issue_status(conversation_name, conversation_status, assigned_agent=None):
    """
    Synchronize conversation status with corresponding ERPNext Issue and persist the
    conversation's status. Robust to legacy records where only one side of the link exists.
    """
    try:
        # 1) Resolve the Issue linked to this conversation
        issue_name = frappe.db.get_value(
            "Issue",
            {"custom_conversation_id": conversation_name},
            "name"
        )
        if not issue_name:
            # Fallback: use the conversation's stored custom_issue_id if reverse link is missing
            issue_name = frappe.db.get_value(
                "Unified Inbox Conversation",
                conversation_name,
                "custom_issue_id"
            )

        if not issue_name:
            return {
                "status": "error",
                "message": "No corresponding Issue found for this conversation"
            }

        # 2) Map conversation status to Issue status
        status_mapping = {
            "New": "Open",
            "AI Responded": "Open",
            "Agent Assigned": "Open",
            "In Progress": "Open",
            "Escalated": "Open",
            "Closed": "Closed",
            "Resolved": "Resolved"
        }
        issue_status = status_mapping.get(conversation_status, "Open")

        # 3) Update Issue (and backfill missing reverse link if needed)
        issue_doc = frappe.get_doc("Issue", issue_name)
        issue_doc.status = issue_status
        if not getattr(issue_doc, "custom_conversation_id", None):
            issue_doc.custom_conversation_id = conversation_name

        # Update assignment if provided
        if assigned_agent and frappe.db.exists("User", assigned_agent):
            issue_doc.custom_assigned_agent = assigned_agent
            try:
                from frappe.desk.form.assign_to import add as add_assignment
                add_assignment({
                    "assign_to": [assigned_agent],
                    "doctype": "Issue",
                    "name": issue_name,
                    "description": f"Assigned from Unified Inbox conversation {conversation_name}"
                })
            except Exception:
                # Assignment might already exist
                pass

        # Clear invalid link field values to prevent LinkValidationError
        # The Issue.company field links to "Employer" doctype, which may have invalid/orphaned references
        _clear_invalid_issue_links(issue_doc)

        issue_doc.save(ignore_permissions=True)

        # Add comment about status change
        try:
            issue_doc.add_comment(
                "Comment",
                f"Status updated from Unified Inbox: {conversation_status}"
            )
        except Exception:
            pass

        # 4) Persist conversation status server-side so new inbound routing uses it
        try:
            frappe.db.set_value(
                "Unified Inbox Conversation",
                conversation_name,
                "status",
                conversation_status,
                update_modified=True,
            )
            if assigned_agent:
                frappe.db.set_value(
                    "Unified Inbox Conversation",
                    conversation_name,
                    "assigned_agent",
                    assigned_agent,
                    update_modified=True,
                )
        except Exception:
            # Do not fail sync if conversation update has issues
            pass

        return {
            "status": "success",
            "message": "Issue and Conversation status synchronized successfully",
            "issue_id": issue_name,
            "issue_status": issue_status,
            "conversation_name": conversation_name,
            "conversation_status": conversation_status,
        }

    except Exception as e:
        frappe.log_error(f"Error syncing status for conversation {conversation_name}: {str(e)}", "Status Sync Error")
        return {
            "status": "error",
            "message": f"Failed to sync status: {str(e)}"
        }


@frappe.whitelist()
def add_conversation_comment_to_issue(conversation_name, message_content, sender_name, message_type="Customer"):
    """
    Add conversation messages as comments to the corresponding ERPNext Issue.
    Provides complete conversation history in the ticket timeline.
    """
    try:
        # Add comments for ALL conversations (including demo conversations)

        # Find corresponding Issue
        issue_name = frappe.db.get_value(
            "Issue",
            {"custom_conversation_id": conversation_name},
            "name"
        )

        if not issue_name:
            return {
                "status": "error",
                "message": "No corresponding Issue found for this conversation"
            }

        # Add comment to Issue
        issue_doc = frappe.get_doc("Issue", issue_name)

        # Readable comment without altering timestamps
        comment_text = f"""
**{message_type} Message from {sender_name}:**

{message_content}

---
*Added from Unified Inbox conversation*
        """.strip()

        issue_doc.add_comment("Comment", comment_text)

        return {
            "status": "success",
            "message": "Comment added to Issue successfully",
            "issue_id": issue_name
        }

    except Exception as e:
        frappe.log_error(f"Error adding comment to issue for conversation {conversation_name}: {str(e)}", "Comment Addition Error")
        return {
            "status": "error",
            "message": f"Failed to add comment: {str(e)}"
        }


@frappe.whitelist()
def escalate_to_erpnext_issue(conversation_name, issue_id, new_priority, assign_to=None, escalation_reason=None):
    """
    Escalate conversation using ERPNext's native Issue escalation system.
    Updates Issue priority, assignment, and adds escalation comments.
    """
    try:
        print(f"DEBUG: Escalating Issue {issue_id} for conversation {conversation_name}")

        # Get the ERPNext Issue
        if not frappe.db.exists("Issue", issue_id):
            return {
                "status": "error",
                "message": f"Issue {issue_id} not found"
            }

        issue_doc = frappe.get_doc("Issue", issue_id)

        # Update Issue priority (ERPNext native escalation)
        old_priority = issue_doc.priority
        issue_doc.priority = new_priority

        # Add escalation comment to Issue
        escalation_comment = f"""
🚨 **ESCALATED FROM UNIFIED INBOX**

**Escalation Reason:** {escalation_reason or 'Not specified'}
**Previous Priority:** {old_priority}
**New Priority:** {new_priority}
**Escalated By:** {frappe.session.user}
**Escalated At:** {frappe.utils.now()}

This Issue was escalated from the Unified Inbox conversation: {conversation_name}
        """.strip()

        issue_doc.add_comment("Comment", escalation_comment)

        # Update custom escalation fields for separation
        if assign_to:
            try:
                user_name = frappe.get_value("User", assign_to, "full_name") or assign_to
                display_name = f"{user_name} ({assign_to})"
                issue_doc.custom_escalated_agent = assign_to
                issue_doc.custom_escalated_agent_name = display_name
                print(f"DEBUG: Set custom_escalated_agent to {display_name}")
            except Exception as e:
                print(f"DEBUG: Error setting custom escalation fields: {str(e)}")

        # Assign to user if specified (ERPNext native assignment)
        if assign_to:
            try:
                from frappe.desk.form.assign_to import add as add_assignment
                add_assignment({
                    "assign_to": [assign_to],
                    "doctype": "Issue",
                    "name": issue_id,
                    "description": f"Escalated from Unified Inbox: {escalation_reason}"
                })
                print(f"DEBUG: Assigned Issue {issue_id} to {assign_to}")
            except Exception as assign_error:
                print(f"DEBUG: Assignment error (may already be assigned): {str(assign_error)}")

        # Clear invalid link field values to prevent LinkValidationError
        _clear_invalid_issue_links(issue_doc)

        # Save the Issue
        issue_doc.save(ignore_permissions=True)
        
        # Update the conversation as well
        if conversation_name and frappe.db.exists("Unified Inbox Conversation", conversation_name):
            try:
                frappe.db.set_value("Unified Inbox Conversation", conversation_name, {
                    "escalated_agent": assign_to,
                    "escalated_at": frappe.utils.now(),
                    "escalated_by": frappe.session.user,
                    "escalation_reason": escalation_reason,
                    "status": "Escalated",
                    "priority": new_priority
                }, update_modified=True)
            except Exception as e:
                frappe.log_error(f"Failed to update conversation escalation status: {str(e)}", "Unified Inbox Escalation Sync")

        print(f"DEBUG: Issue {issue_id} escalated successfully")

        return {
            "status": "success",
            "message": f"Issue {issue_id} escalated successfully",
            "issue_id": issue_id,
            "old_priority": old_priority,
            "new_priority": new_priority,
            "assigned_to": assign_to,
            "issue_url": f"/app/issue/{issue_id}"
        }

    except Exception as e:
        error_msg = f"Error escalating Issue {issue_id}: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "ERPNext Issue Escalation Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def sync_issue_escalation_to_conversation(issue_id):
    """
    Sync ERPNext Issue escalation changes back to Unified Inbox conversation.
    This enables bidirectional sync when Issues are escalated directly in ERPNext.
    """
    try:
        print(f"DEBUG: Syncing Issue {issue_id} escalation to conversation")

        # Find conversation linked to this Issue
        conversation_name = frappe.db.get_value(
            "Unified Inbox Conversation",
            {"custom_issue_id": issue_id},
            "name"
        )

        if not conversation_name:
            return {
                "status": "info",
                "message": f"No conversation found for Issue {issue_id}"
            }

        # Get Issue details
        issue = frappe.get_doc("Issue", issue_id)

        # Update conversation with Issue status
        conversation = frappe.get_doc("Unified Inbox Conversation", conversation_name)

        # Map Issue priority to conversation priority
        conversation.priority = issue.priority

        # Update status based on Issue priority (escalation indicator)
        if issue.priority in ["High", "Urgent"]:
            conversation.status = "Escalated"

        # Update assignment if Issue is assigned
        if hasattr(issue, 'assigned_to') and issue.assigned_to:
            conversation.assigned_agent = issue.assigned_to
            
        # Update escalation fields if present
        if hasattr(issue, 'custom_escalated_agent') and issue.custom_escalated_agent:
            conversation.escalated_agent = issue.custom_escalated_agent
            if not conversation.escalated_at:
                conversation.escalated_at = frappe.utils.now()

        conversation.save(ignore_permissions=True)

        return {
            "status": "success",
            "message": f"Conversation {conversation_name} synced with Issue {issue_id}",
            "conversation_name": conversation_name,
            "issue_priority": issue.priority,
            "conversation_status": conversation.status
        }

    except Exception as e:
        error_msg = f"Error syncing Issue {issue_id} to conversation: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Issue to Conversation Sync Error")
        return {
            "status": "error",
            "message": error_msg
        }


def get_telegram_last_update_id():
    """Get the last processed Telegram update ID."""
    try:
        # Try to get from a simple cache file first
        cache_file = frappe.get_site_path("telegram_last_update_id.txt")
        try:
            with open(cache_file, 'r') as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError):
            return 0
    except Exception:
        return 0


def set_telegram_last_update_id(update_id):
    """Set the last processed Telegram update ID."""
    try:
        # Store in a simple cache file
        cache_file = frappe.get_site_path("telegram_last_update_id.txt")
        with open(cache_file, 'w') as f:
            f.write(str(update_id))
        print(f"DEBUG: Saved Telegram update ID: {update_id}")
    except Exception as e:
        print(f"DEBUG: Error saving Telegram update ID: {str(e)}")


def get_instagram_last_update_id():
    """Get the last processed Instagram update timestamp."""
    try:
        # Try to get from a simple cache file first
        cache_file = frappe.get_site_path("instagram_last_update_id.txt")
        try:
            with open(cache_file, 'r') as f:
                return f.read().strip()
        except (FileNotFoundError, ValueError):
            return None
    except Exception:
        return None


def set_instagram_last_update_id(update_timestamp):
    """Set the last processed Instagram update timestamp."""
    try:
        # Store in a simple cache file
        cache_file = frappe.get_site_path("instagram_last_update_id.txt")
        with open(cache_file, 'w') as f:
            f.write(str(update_timestamp))
        print(f"DEBUG: Saved Instagram update timestamp: {update_timestamp}")
    except Exception as e:
        print(f"DEBUG: Error saving Instagram update timestamp: {str(e)}")


@frappe.whitelist()
def fetch_telegram_messages():
    """
    Fetch live messages from Telegram Bot API using long polling.
    This replaces demo message generation with real Telegram messages.
    """
    try:
        from assistant_crm.api.social_media_ports import TelegramIntegration

        print("DEBUG: Starting Telegram message fetch")

        # Initialize Telegram integration
        telegram = TelegramIntegration()

        if not telegram.is_configured:
            print("DEBUG: Telegram bot not configured")
            return {
                "status": "error",
                "message": "Telegram bot not configured",
                "debug": "Bot token missing or invalid"
            }

        bot_token = telegram.credentials["bot_token"]

        # Get last update ID to avoid processing old messages
        # Use a custom DocType to store Telegram state instead of System Settings
        last_update_id = get_telegram_last_update_id()

        # Fetch updates from Telegram
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        params = {
            "offset": last_update_id + 1,
            "limit": 100,
            "timeout": 10
        }

        print(f"DEBUG: Fetching Telegram updates with offset {last_update_id + 1}")

        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"Telegram API error: {response.status_code}"
            }

        data = response.json()

        if not data.get("ok"):
            return {
                "status": "error",
                "message": f"Telegram API error: {data.get('description', 'Unknown error')}"
            }

        updates = data.get("result", [])
        processed_messages = 0
        new_conversations = 0

        print(f"DEBUG: Received {len(updates)} Telegram updates")

        for update in updates:
            try:
                # Update last processed update ID
                update_id = update.get("update_id")
                if update_id:
                    set_telegram_last_update_id(update_id)

                # Process message if present
                if "message" in update:
                    result = telegram.process_webhook(update)
                    if result.get("status") == "success":
                        processed_messages += 1

                        # Check if this created a new conversation
                        message = update.get("message", {})
                        chat_id = str(message.get("chat", {}).get("id", ""))

                        # Check if this is a new conversation
                        existing_conv = frappe.get_all(
                            "Unified Inbox Conversation",
                            filters={
                                "platform": "Telegram",
                                "customer_platform_id": chat_id
                            },
                            limit=1
                        )

                        if not existing_conv:
                            new_conversations += 1
                            print(f"DEBUG: New Telegram conversation detected for chat_id: {chat_id}")
                        else:
                            print(f"DEBUG: Existing Telegram conversation found for chat_id: {chat_id}")

            except Exception as update_error:
                print(f"DEBUG: Error processing update {update.get('update_id')}: {str(update_error)}")
                continue

        # Commit changes
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"Processed {processed_messages} Telegram messages",
            "processed_messages": processed_messages,
            "new_conversations": new_conversations,
            "total_updates": len(updates)
        }

    except Exception as e:
        error_msg = f"Error fetching Telegram messages: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Telegram Message Fetch Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def fetch_tawkto_messages():
    """
    Fetch live messages from Tawk.to API.
    This replaces demo message generation with real Tawk.to messages.
    Note: This requires API key for full functionality. Currently configured for webhook-based integration.
    """
    try:
        from assistant_crm.api.social_media_ports import TawkToIntegration

        print("DEBUG: Starting Tawk.to message fetch")

        # Initialize Tawk.to integration
        tawkto = TawkToIntegration()

        if not tawkto.is_configured:
            print("DEBUG: Tawk.to not configured")
            return {
                "status": "error",
                "message": "Tawk.to not configured",
                "debug": "Property ID missing or invalid"
            }

        # Note: Tawk.to API requires API key for message polling
        # For now, we'll return a status message indicating webhook-based integration
        if not tawkto.credentials.get("api_key"):
            return {
                "status": "info",
                "message": "Tawk.to configured for webhook-based integration",
                "property_id": tawkto.credentials.get("property_id"),
                "property_url": tawkto.credentials.get("property_url"),
                "webhook_ready": True,
                "api_polling": False,
                "note": "API key required for active message polling"
            }

        # If API key is available, implement active polling here
        api_key = tawkto.credentials["api_key"]
        property_id = tawkto.credentials["property_id"]

        # Tawk.to API endpoint for getting chats
        url = f"https://api.tawk.to/v3/chats"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        params = {
            "property": property_id,
            "status": "active",
            "limit": 50
        }

        print(f"DEBUG: Fetching Tawk.to chats for property {property_id}")

        response = requests.get(url, headers=headers, params=params, timeout=15)

        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"Tawk.to API error: {response.status_code}",
                "response_text": response.text
            }

        data = response.json()
        chats = data.get("data", [])

        processed_messages = 0
        new_conversations = 0

        print(f"DEBUG: Received {len(chats)} Tawk.to chats")

        for chat in chats:
            try:
                # Process each chat and its messages
                chat_id = chat.get("id")
                visitor = chat.get("visitor", {})

                # Get messages for this chat
                messages_url = f"https://api.tawk.to/v3/chats/{chat_id}/messages"
                messages_response = requests.get(messages_url, headers=headers, timeout=10)

                if messages_response.status_code == 200:
                    messages_data = messages_response.json()
                    messages = messages_data.get("data", [])

                    for message in messages:
                        # Process each message through webhook format
                        webhook_data = {
                            "event": "chat:message",
                            "data": {
                                "chat": chat,
                                "message": message
                            }
                        }

                        result = tawkto.process_webhook(webhook_data)
                        if result.get("status") == "success":
                            processed_messages += 1

            except Exception as chat_error:
                print(f"DEBUG: Error processing chat {chat.get('id')}: {str(chat_error)}")
                continue

        return {
            "status": "success",
            "message": f"Processed {processed_messages} Tawk.to messages",
            "processed_messages": processed_messages,
            "new_conversations": new_conversations,
            "total_chats": len(chats)
        }

    except Exception as e:
        error_msg = f"Error fetching Tawk.to messages: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Tawk.to Message Fetch Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def get_telegram_bot_info():
    """
    Get Telegram bot information and status.
    """
    try:
        from assistant_crm.api.social_media_ports import TelegramIntegration

        telegram = TelegramIntegration()

        if not telegram.is_configured:
            return {
                "status": "error",
                "message": "Telegram bot not configured"
            }

        bot_token = telegram.credentials["bot_token"]

        # Get bot information
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"Telegram API error: {response.status_code}"
            }

        data = response.json()

        if not data.get("ok"):
            return {
                "status": "error",
                "message": f"Telegram API error: {data.get('description', 'Unknown error')}"
            }

        bot_info = data.get("result", {})

        return {
            "status": "success",
            "bot_info": {
                "id": bot_info.get("id"),
                "is_bot": bot_info.get("is_bot"),
                "first_name": bot_info.get("first_name"),
                "username": bot_info.get("username"),
                "can_join_groups": bot_info.get("can_join_groups"),
                "can_read_all_group_messages": bot_info.get("can_read_all_group_messages"),
                "supports_inline_queries": bot_info.get("supports_inline_queries")
            },
            "bot_link": f"https://t.me/{bot_info.get('username', '')}"
        }

    except Exception as e:
        error_msg = f"Error getting Telegram bot info: {str(e)}"
        frappe.log_error(error_msg, "Telegram Bot Info Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def fetch_instagram_messages():
    """
    Fetch live messages from Instagram Graph API using polling.

    IMPORTANT: Instagram Graph API has severe limitations for direct messages.
    Direct message access requires Instagram Advanced Access and special permissions.
    This function explains the limitations and provides webhook-based alternatives.
    """
    try:
        from assistant_crm.api.social_media_ports import InstagramIntegration

        print("DEBUG: Starting Instagram message fetch (with API limitations)")

        # Initialize Instagram integration
        instagram = InstagramIntegration()

        if not instagram.is_configured:
            print("DEBUG: Instagram not configured")
            return {
                "status": "error",
                "message": "Instagram not configured",
                "debug": "Access token missing or invalid"
            }

        access_token = instagram.credentials["access_token"]
        api_version = instagram.credentials.get("api_version", "v18.0")

        # Get last update ID to avoid processing old messages
        last_update_id = get_instagram_last_update_id()

        # Instagram Graph API endpoint for getting media and comments
        # Note: Instagram Graph API doesn't have a direct conversations endpoint
        # We need to use a different approach for Instagram Business accounts

        # First, get the Instagram Business Account ID
        me_url = f"https://graph.facebook.com/{api_version}/me"
        me_params = {
            "access_token": access_token,
            "fields": "id,accounts{instagram_business_account}"
        }

        print(f"DEBUG: Getting Instagram Business Account info")

        me_response = requests.get(me_url, params=me_params, timeout=15)

        if me_response.status_code != 200:
            return {
                "status": "error",
                "message": f"Instagram API error getting account info: {me_response.status_code}",
                "response_text": me_response.text
            }

        me_data = me_response.json()
        print(f"DEBUG: Account info response: {me_data}")

        # Extract Instagram Business Account ID
        instagram_account_id = None
        accounts = me_data.get("accounts", {}).get("data", [])
        for account in accounts:
            if account.get("instagram_business_account"):
                instagram_account_id = account["instagram_business_account"]["id"]
                break

        if not instagram_account_id:
            return {
                "status": "error",
                "message": "No Instagram Business Account found. Please ensure you have a connected Instagram Business Account.",
                "debug": me_data
            }

        print(f"DEBUG: Found Instagram Business Account ID: {instagram_account_id}")

        # Get Instagram media (posts) to check for comments/messages
        url = f"https://graph.facebook.com/{api_version}/{instagram_account_id}/media"

        params = {
            "access_token": access_token,
            "fields": "id,media_type,timestamp,comments_count",
            "limit": 20
        }

        print(f"DEBUG: Fetching Instagram conversations with last update: {last_update_id}")

        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"Instagram API error: {response.status_code}",
                "response_text": response.text
            }

        data = response.json()
        media_items = data.get("data", [])

        processed_messages = 0
        new_conversations = 0

        print(f"DEBUG: Received {len(media_items)} Instagram media items")

        # Now that webhooks are enabled, let's check for webhook-received messages
        # Instead of polling, we'll check our database for recent Instagram conversations

        print(f"DEBUG: Checking for recent Instagram conversations (webhook-based)")

        # Get recent Instagram conversations from our database
        recent_conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters={
                "platform": "Instagram",
                "creation": [">=", frappe.utils.add_hours(now(), -1)]  # Last hour
            },
            fields=["name", "customer_name", "custom_issue_id", "creation"],
            order_by="creation desc",
            limit=10
        )

        print(f"DEBUG: Found {len(recent_conversations)} recent Instagram conversations")

        # Get recent Instagram messages
        recent_messages = frappe.get_all(
            "Unified Inbox Message",
            filters={
                "platform": "Instagram",
                "timestamp": [">=", frappe.utils.add_hours(now(), -1)]  # Last hour
            },
            fields=["name", "conversation", "message_content", "timestamp"],
            order_by="timestamp desc",
            limit=20
        )

        print(f"DEBUG: Found {len(recent_messages)} recent Instagram messages")

        return {
            "status": "success",
            "message": f"Instagram webhook-based integration active",
            "webhook_enabled": True,
            "instagram_account_id": instagram_account_id,
            "recent_conversations": len(recent_conversations),
            "recent_messages": len(recent_messages),
            "conversations": recent_conversations,
            "messages": recent_messages,
            "webhook_url": f"{get_public_url()}/api/method/assistant_crm.api.social_media_ports.social_media_webhook",
            "note": "Messages will appear via webhook when sent to Instagram account"
        }

    except Exception as e:
        error_msg = f"Error fetching Instagram messages: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Instagram Message Fetch Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def test_instagram_access_token():
    """
    Test Instagram access token validity and permissions.
    """
    try:
        from assistant_crm.api.social_media_ports import InstagramIntegration

        instagram = InstagramIntegration()

        if not instagram.is_configured:
            return {
                "status": "error",
                "message": "Instagram not configured"
            }

        access_token = instagram.credentials["access_token"]
        api_version = instagram.credentials.get("api_version", "v18.0")

        # Test 1: Basic token validation
        print("DEBUG: Testing Instagram access token...")

        url = f"https://graph.facebook.com/{api_version}/me"
        params = {
            "access_token": access_token
        }

        response = requests.get(url, params=params, timeout=10)

        print(f"DEBUG: Token test response: {response.status_code}")
        print(f"DEBUG: Token test data: {response.text}")

        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"Access token invalid: {response.status_code}",
                "response": response.text
            }

        me_data = response.json()

        # Test 2: Check for Instagram accounts
        accounts_url = f"https://graph.facebook.com/{api_version}/me/accounts"
        accounts_params = {
            "access_token": access_token,
            "fields": "id,name,instagram_business_account"
        }

        accounts_response = requests.get(accounts_url, params=accounts_params, timeout=10)

        print(f"DEBUG: Accounts response: {accounts_response.status_code}")
        print(f"DEBUG: Accounts data: {accounts_response.text}")

        accounts_data = accounts_response.json() if accounts_response.status_code == 200 else {}

        # Test 3: Check token permissions
        permissions_url = f"https://graph.facebook.com/{api_version}/me/permissions"
        permissions_params = {
            "access_token": access_token
        }

        permissions_response = requests.get(permissions_url, params=permissions_params, timeout=10)
        permissions_data = permissions_response.json() if permissions_response.status_code == 200 else {}

        print(f"DEBUG: Permissions response: {permissions_response.status_code}")
        print(f"DEBUG: Permissions data: {permissions_response.text}")

        return {
            "status": "success",
            "message": "Instagram access token test completed",
            "token_valid": True,
            "user_info": me_data,
            "accounts": accounts_data.get("data", []),
            "permissions": permissions_data.get("data", []),
            "api_limitations": {
                "direct_messages": "Requires Instagram Advanced Access",
                "webhook_required": "Use webhook for real-time messages",
                "current_access": "Basic access token provided"
            }
        }

    except Exception as e:
        error_msg = f"Error testing Instagram access token: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Instagram Token Test Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def test_instagram_webhook():
    """
    Test Instagram webhook processing with sample data.
    This simulates receiving an Instagram direct message.
    """
    try:
        from assistant_crm.api.social_media_ports import InstagramIntegration

        print("DEBUG: Testing Instagram webhook processing")

        # Initialize Instagram integration
        instagram = InstagramIntegration()

        # Create sample Instagram webhook data
        import datetime

        sample_webhook_data = {
            "entry": [{
                "messaging": [{
                    "sender": {"id": "test_instagram_user_123"},
                    "recipient": {"id": "wcfcb_instagram_account"},
                    "timestamp": int(datetime.datetime.now().timestamp() * 1000),
                    "message": {
                        "mid": "test_message_id_456",
                        "text": "Hello, I need help with my pension inquiry. This is a test message from Instagram."
                    }
                }]
            }]
        }

        print(f"DEBUG: Processing sample Instagram webhook data")

        # Process the webhook
        result = instagram.process_webhook(sample_webhook_data)

        print(f"DEBUG: Webhook processing result: {result}")

        if result.get("status") == "success":
            # Check if conversation was created
            conversations = frappe.get_all(
                "Unified Inbox Conversation",
                filters={
                    "platform": "Instagram",
                    "customer_platform_id": "test_instagram_user_123"
                },
                fields=["name", "customer_name", "custom_issue_id"],
                limit=1
            )

            conversation_info = conversations[0] if conversations else None

            return {
                "status": "success",
                "message": "Instagram webhook test completed successfully",
                "webhook_result": result,
                "conversation_created": bool(conversation_info),
                "conversation_info": conversation_info,
                "test_data": sample_webhook_data
            }
        else:
            return {
                "status": "error",
                "message": "Instagram webhook test failed",
                "webhook_result": result,
                "test_data": sample_webhook_data
            }

    except Exception as e:
        error_msg = f"Error testing Instagram webhook: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Instagram Webhook Test Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def test_instagram_webhook_endpoint():
    """
    Test Instagram webhook endpoint configuration.
    This simulates a real Instagram webhook call to verify the endpoint is working.
    """
    try:
        print("DEBUG: Testing Instagram webhook endpoint")

        # Test the social media webhook endpoint directly
        webhook_url = f"{get_public_url()}/api/method/assistant_crm.api.social_media_ports.social_media_webhook"

        # Create sample Instagram webhook payload
        import datetime

        sample_payload = {
            "object": "instagram",
            "entry": [{
                "id": "instagram_page_id",
                "time": int(datetime.datetime.now().timestamp()),
                "messaging": [{
                    "sender": {"id": "test_instagram_user_456"},
                    "recipient": {"id": "wcfcb_instagram_page"},
                    "timestamp": int(datetime.datetime.now().timestamp() * 1000),
                    "message": {
                        "mid": "test_instagram_message_789",
                        "text": "Hello WCFCB! I need help with my pension inquiry. This is a test from Instagram DM."
                    }
                }]
            }]
        }

        print(f"DEBUG: Testing webhook URL: {webhook_url}")
        print(f"DEBUG: Sample payload: {sample_payload}")

        # Make a POST request to our webhook endpoint
        response = requests.post(
            webhook_url,
            json=sample_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print(f"DEBUG: Webhook response status: {response.status_code}")
        print(f"DEBUG: Webhook response text: {response.text}")

        # Check if conversation was created
        conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters={
                "platform": "Instagram",
                "customer_platform_id": "test_instagram_user_456"
            },
            fields=["name", "customer_name", "custom_issue_id", "creation"],
            limit=1
        )

        # Check if messages were created
        messages = frappe.get_all(
            "Unified Inbox Message",
            filters={
                "platform": "Instagram",
                "sender_platform_id": "test_instagram_user_456"
            },
            fields=["name", "message_content", "timestamp"],
            limit=5
        )

        return {
            "status": "success",
            "message": "Instagram webhook endpoint test completed",
            "webhook_url": webhook_url,
            "webhook_response": {
                "status_code": response.status_code,
                "response_text": response.text[:500]  # Truncate for readability
            },
            "conversations_created": len(conversations),
            "messages_created": len(messages),
            "conversation_info": conversations[0] if conversations else None,
            "sample_payload": sample_payload,
            "webhook_working": response.status_code == 200
        }

    except Exception as e:
        error_msg = f"Error testing Instagram webhook endpoint: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Instagram Webhook Endpoint Test Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def get_instagram_webhook_config():
    """
    Get Instagram webhook configuration details for Facebook Developers setup.
    """
    try:
        webhook_url = f"{get_public_url()}/api/method/assistant_crm.api.social_media_ports.social_media_webhook"
        verify_token = "wcfcb_instagram_webhook_verify_token_2025"

        return {
            "status": "success",
            "webhook_configuration": {
                "callback_url": webhook_url,
                "verify_token": verify_token,
                "subscription_fields": [
                    "messages",
                    "messaging_postbacks",
                    "messaging_optins",
                    "message_deliveries",
                    "message_reads"
                ]
            },
            "facebook_developers_setup": {
                "step_1": "Go to Facebook Developers Console",
                "step_2": "Select your app",
                "step_3": "Go to Instagram > Configuration",
                "step_4": f"Set Callback URL: {webhook_url}",
                "step_5": f"Set Verify Token: {verify_token}",
                "step_6": "Subscribe to: messages, messaging_postbacks",
                "step_7": "Save configuration",
                "step_8": "Test webhook by sending Instagram DM"
            },
            "webhook_verification": {
                "method": "GET",
                "parameters": {
                    "hub.mode": "subscribe",
                    "hub.challenge": "random_string",
                    "hub.verify_token": verify_token
                },
                "expected_response": "hub.challenge value"
            },
            "webhook_events": {
                "method": "POST",
                "content_type": "application/json",
                "events": ["messages", "messaging_postbacks"]
            },
            "testing_instructions": [
                "1. Configure webhook in Facebook Developers",
                "2. Send a direct message to your Instagram account",
                "3. Check WCFCB Inbox for new conversation",
                "4. Verify ERPNext Issue is created automatically"
            ]
        }

    except Exception as e:
        error_msg = f"Error getting Instagram webhook config: {str(e)}"
        frappe.log_error(error_msg, "Instagram Webhook Config Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def get_tawkto_info():
    """
    Get Tawk.to integration information and status.
    """
    try:
        from assistant_crm.api.social_media_ports import TawkToIntegration

        tawkto = TawkToIntegration()

        if not tawkto.is_configured:
            return {
                "status": "error",
                "message": "Tawk.to not configured"
            }

        property_id = tawkto.credentials.get("property_id")
        property_url = tawkto.credentials.get("property_url")
        api_key = tawkto.credentials.get("api_key")

        return {
            "status": "success",
            "integration_info": {
                "property_id": property_id,
                "property_url": property_url,
                "api_key_configured": bool(api_key),
                "webhook_ready": True,
                "polling_available": bool(api_key)
            },
            "setup_info": {
                "webhook_url": "https://crm.exn1.uk/api/method/assistant_crm.api.social_media_ports.social_media_webhook",
                "webhook_events": ["chat:message"],
                "property_link": f"https://dashboard.tawk.to/#/property/{property_id}" if property_id else None
            }
        }

    except Exception as e:
        error_msg = f"Error getting Tawk.to info: {str(e)}"
        frappe.log_error(error_msg, "Tawk.to Info Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def get_instagram_info():
    """
    Get Instagram integration information and status.
    """
    try:
        from assistant_crm.api.social_media_ports import InstagramIntegration

        instagram = InstagramIntegration()

        if not instagram.is_configured:
            return {
                "status": "error",
                "message": "Instagram not configured"
            }

        access_token = instagram.credentials.get("access_token")
        api_version = instagram.credentials.get("api_version", "v18.0")

        # Test API connection
        url = f"https://graph.facebook.com/{api_version}/me"
        params = {
            "fields": "id,name,username",
            "access_token": access_token
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"Instagram API error: {response.status_code}",
                "response_text": response.text
            }

        data = response.json()

        return {
            "status": "success",
            "integration_info": {
                "api_version": api_version,
                "access_token_configured": bool(access_token),
                "account_id": data.get("id"),
                "account_name": data.get("name"),
                "username": data.get("username"),
                "polling_available": True
            },
            "setup_info": {
                "webhook_url": f"{get_public_url()}/api/method/assistant_crm.api.social_media_ports.social_media_webhook",
                "webhook_events": ["messages"],
                "api_documentation": "https://developers.facebook.com/docs/messenger-platform/"
            }
        }

    except Exception as e:
        error_msg = f"Error getting Instagram info: {str(e)}"
        frappe.log_error(error_msg, "Instagram Info Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def test_telegram_connection():
    """
    Test Telegram bot connection and configuration.
    """
    try:
        from assistant_crm.api.social_media_ports import TelegramIntegration

        telegram = TelegramIntegration()

        print(f"DEBUG: Bot configured: {telegram.is_configured}")
        print(f"DEBUG: Bot credentials: {telegram.credentials}")

        if not telegram.is_configured:
            return {
                "status": "error",
                "message": "Telegram bot not configured",
                "credentials": telegram.credentials
            }

        bot_token = telegram.credentials["bot_token"]

        # Test basic API connection
        url = f"https://api.telegram.org/bot{bot_token}/getMe"

        print(f"DEBUG: Testing Telegram API: {url}")

        response = requests.get(url, timeout=10)

        print(f"DEBUG: Response status: {response.status_code}")
        print(f"DEBUG: Response text: {response.text}")

        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"Telegram API HTTP error: {response.status_code}",
                "response_text": response.text
            }

        data = response.json()

        if not data.get("ok"):
            return {
                "status": "error",
                "message": f"Telegram API error: {data.get('description', 'Unknown error')}",
                "api_response": data
            }

        bot_info = data.get("result", {})

        # Test getUpdates endpoint
        updates_url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        updates_response = requests.get(updates_url, params={"limit": 1}, timeout=10)

        updates_data = updates_response.json() if updates_response.status_code == 200 else {}

        return {
            "status": "success",
            "message": "Telegram bot connection successful",
            "bot_info": bot_info,
            "bot_username": bot_info.get("username"),
            "bot_link": f"https://t.me/{bot_info.get('username', '')}" if bot_info.get('username') else None,
            "updates_test": {
                "status_code": updates_response.status_code,
                "ok": updates_data.get("ok", False),
                "updates_count": len(updates_data.get("result", []))
            }
        }

    except Exception as e:
        error_msg = f"Error testing Telegram connection: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Telegram Connection Test Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def get_telegram_setup_instructions():
    """
    Get setup instructions for the Telegram bot.
    """
    try:
        from assistant_crm.api.social_media_ports import TelegramIntegration

        telegram = TelegramIntegration()
        bot_token = telegram.credentials.get("bot_token", "")

        if not bot_token:
            return {
                "status": "error",
                "message": "No bot token configured"
            }

        # Extract bot username from token (first part before colon)
        bot_id = bot_token.split(":")[0] if ":" in bot_token else "unknown"

        instructions = {
            "status": "success",
            "bot_token": bot_token,
            "bot_id": bot_id,
            "setup_steps": [
                "1. Open Telegram and search for your bot",
                "2. Start a conversation with the bot by sending /start",
                "3. Send any message to the bot",
                "4. Refresh the WCFCB Inbox to see new messages",
                "5. The bot will automatically create ERPNext Issues for new conversations"
            ],
            "bot_commands": [
                "/start - Start conversation with the bot",
                "/help - Get help information",
                "Any text message - Will appear in the Unified Inbox"
            ],
            "troubleshooting": [
                "If messages don't appear, check the browser console for errors",
                "Ensure the bot token is valid and active",
                "Check that the bot has permission to receive messages",
                "Try refreshing the inbox manually"
            ]
        }

        return instructions

    except Exception as e:
        error_msg = f"Error getting setup instructions: {str(e)}"
        frappe.log_error(error_msg, "Telegram Setup Instructions Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def generate_missing_tickets():
    """
    Generate ERPNext Issues for conversations that don't have tickets yet.
    """
    try:
        # Find conversations without Issues
        conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters={
                "custom_issue_id": ["is", "not set"]
            },
            fields=["name", "customer_name", "platform", "creation_time"]
        )

        print(f"DEBUG: Found {len(conversations)} conversations without tickets")

        generated_tickets = 0

        for conv in conversations:
            try:
                # Get first message for initial message content
                first_message = frappe.get_all(
                    "Unified Inbox Message",
                    filters={
                        "conversation": conv.name,
                        "direction": "Inbound"
                    },
                    fields=["message_content"],
                    order_by="timestamp asc",
                    limit=1
                )

                initial_message = "Customer inquiry"
                if first_message:
                    initial_message = first_message[0].message_content

                print(f"DEBUG: Generating ticket for conversation {conv.name}")

                # Generate ticket
                result = create_issue_for_conversation(
                    conversation_name=conv.name,
                    customer_name=conv.customer_name,
                    platform=conv.platform,
                    initial_message=initial_message,
                    priority="Medium"
                )

                if result.get("status") == "success":
                    generated_tickets += 1
                    print(f"DEBUG: Generated ticket {result.get('issue_id')} for conversation {conv.name}")
                else:
                    print(f"DEBUG: Failed to generate ticket for {conv.name}: {result.get('message')}")

            except Exception as conv_error:
                print(f"DEBUG: Error processing conversation {conv.name}: {str(conv_error)}")
                continue

        return {
            "status": "success",
            "message": f"Generated {generated_tickets} tickets for {len(conversations)} conversations",
            "generated_tickets": generated_tickets,
            "total_conversations": len(conversations)
        }

    except Exception as e:
        error_msg = f"Error generating missing tickets: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Generate Missing Tickets Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def get_tawkto_setup_instructions():
    """
    Get setup instructions for Tawk.to integration.
    """
    try:
        from assistant_crm.api.social_media_ports import TawkToIntegration

        tawkto = TawkToIntegration()
        property_id = tawkto.credentials.get("property_id", "")
        property_url = tawkto.credentials.get("property_url", "")

        webhook_url = "https://crm.exn1.uk/api/method/assistant_crm.api.social_media_ports.social_media_webhook"

        instructions = {
            "status": "success",
            "property_id": property_id,
            "property_url": property_url,
            "webhook_url": webhook_url,
            "setup_steps": [
                "1. Log in to your Tawk.to dashboard",
                "2. Go to Administration > Property Settings",
                f"3. Navigate to Webhooks section",
                f"4. Add webhook URL: {webhook_url}",
                "5. Select 'chat:message' event",
                "6. Set webhook to active",
                "7. Test by starting a chat on your website",
                "8. Messages will appear in the WCFCB Inbox automatically"
            ],
            "webhook_configuration": {
                "url": webhook_url,
                "events": ["chat:message"],
                "method": "POST",
                "content_type": "application/json"
            },
            "integration_features": [
                "✅ Automatic ERPNext Issue generation",
                "✅ Real-time message timestamps",
                "✅ Customer identification",
                "✅ Message threading",
                "✅ Agent assignment",
                "✅ Issue escalation"
            ],
            "api_features": [
                "🔑 API Key required for:",
                "- Active message polling",
                "- Sending replies from inbox",
                "- Advanced chat management"
            ],
            "troubleshooting": [
                "If messages don't appear, check webhook configuration",
                "Ensure webhook URL is accessible from internet",
                "Check browser console for debug messages",
                "Verify property ID matches your Tawk.to property"
            ]
        }

        return instructions

    except Exception as e:
        error_msg = f"Error getting Tawk.to setup instructions: {str(e)}"
        frappe.log_error(error_msg, "Tawk.to Setup Instructions Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def get_tawkto_setup_instructions():
    """
    Get setup instructions for Tawk.to integration.
    """
    try:
        from assistant_crm.api.social_media_ports import TawkToIntegration

        tawkto = TawkToIntegration()
        property_id = tawkto.credentials.get("property_id", "")
        property_url = tawkto.credentials.get("property_url", "")

        webhook_url = "https://crm.exn1.uk/api/method/assistant_crm.api.social_media_ports.social_media_webhook"

        instructions = {
            "status": "success",
            "property_id": property_id,
            "property_url": property_url,
            "webhook_url": webhook_url,
            "setup_steps": [
                "1. Log in to your Tawk.to dashboard",
                "2. Go to Administration > Property Settings",
                f"3. Navigate to Webhooks section",
                f"4. Add webhook URL: {webhook_url}",
                "5. Select 'chat:message' event",
                "6. Set webhook to active",
                "7. Test by starting a chat on your website",
                "8. Messages will appear in the WCFCB Inbox automatically"
            ],
            "webhook_configuration": {
                "url": webhook_url,
                "events": ["chat:message"],
                "method": "POST",
                "content_type": "application/json"
            },
            "integration_features": [
                "✅ Automatic ERPNext Issue generation",
                "✅ Real-time message timestamps",
                "✅ Customer identification",
                "✅ Message threading",
                "✅ Agent assignment",
                "✅ Issue escalation"
            ],
            "troubleshooting": [
                "If messages don't appear, check webhook configuration",
                "Ensure webhook URL is accessible from internet",
                "Check browser console for debug messages",
                "Verify property ID matches your Tawk.to property"
            ]
        }

        return instructions

    except Exception as e:
        error_msg = f"Error getting Tawk.to setup instructions: {str(e)}"
        frappe.log_error(error_msg, "Tawk.to Setup Instructions Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def get_instagram_setup_instructions():
    """
    Get setup instructions for Instagram integration.
    """
    try:
        from assistant_crm.api.social_media_ports import InstagramIntegration

        instagram = InstagramIntegration()
        access_token = instagram.credentials.get("access_token", "")
        api_version = instagram.credentials.get("api_version", "v18.0")

        webhook_url = f"{get_public_url()}/api/method/assistant_crm.api.social_media_ports.social_media_webhook"

        instructions = {
            "status": "success",
            "access_token": access_token[:20] + "..." if access_token else "Not configured",
            "api_version": api_version,
            "webhook_url": webhook_url,
            "setup_steps": [
                "1. Create Facebook App at https://developers.facebook.com/",
                "2. Add Instagram Basic Display or Instagram Graph API product",
                "3. Configure Instagram Business Account",
                "4. Generate Access Token with required permissions",
                "5. Set up webhook for real-time message delivery",
                f"6. Configure webhook URL: {webhook_url}",
                "7. Subscribe to 'messages' webhook events",
                "8. Test by sending direct message to Instagram account",
                "9. Messages will appear in WCFCB Inbox automatically"
            ],
            "required_permissions": [
                "instagram_basic",
                "instagram_manage_messages",
                "pages_messaging",
                "pages_show_list"
            ],
            "webhook_configuration": {
                "url": webhook_url,
                "events": ["messages"],
                "method": "POST",
                "content_type": "application/json"
            },
            "integration_features": [
                "✅ Automatic ERPNext Issue generation",
                "✅ Real-time message timestamps",
                "✅ Customer identification (username/profile)",
                "✅ Message threading",
                "✅ Agent assignment",
                "✅ Issue escalation",
                "✅ Direct message support",
                "✅ Media message handling"
            ],
            "api_features": [
                "📊 Active message polling",
                "💬 Sending replies from inbox",
                "👤 User profile information",
                "📷 Media message support"
            ],
            "troubleshooting": [
                "If messages don't appear, check access token validity",
                "Ensure Instagram account is Business/Creator account",
                "Verify webhook configuration in Facebook App",
                "Check browser console for debug messages",
                "Confirm required permissions are granted"
            ]
        }

        return instructions

    except Exception as e:
        error_msg = f"Error getting Instagram setup instructions: {str(e)}"
        frappe.log_error(error_msg, "Instagram Setup Instructions Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def test_live_assignment():
    """Test live conversation assignment functionality."""
    try:
        # Find a live conversation
        live_convs = frappe.get_all(
            "Unified Inbox Conversation",
            filters={"name": ["not like", "conv-%"]},
            fields=["name", "customer_name", "platform"],
            limit=1
        )

        if not live_convs:
            return {"status": "error", "message": "No live conversations found"}

        # Get an agent
        agents = get_available_agents()
        if not agents.get("data"):
            return {"status": "error", "message": "No agents available"}

        test_agent = agents["data"][0]["email"]
        conv_name = live_convs[0]["name"]

        # Test assignment
        frappe.local.form_dict = {
            "conversation_name": conv_name,
            "target_agent": test_agent,
            "assignment_notes": "Test assignment"
        }

        result = enhanced_assign_conversation()

        return {
            "status": "success",
            "message": "Assignment test completed",
            "conversation": conv_name,
            "agent": test_agent,
            "result": result
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def test_agents_api():
    """Test endpoint to verify agent API is working."""
    try:
        result = get_available_agents()
        return {
            "test_status": "success",
            "api_result": result,
            "current_user": frappe.session.user,
            "user_roles": frappe.get_roles(frappe.session.user)
        }
    except Exception as e:
        return {
            "test_status": "error",
            "error": str(e)
        }


@frappe.whitelist()
def debug_assignment_issue():
    """Debug assignment functionality step by step."""
    try:
        debug_results = {
            "timestamp": frappe.utils.now(),
            "tests": {}
        }

        # Test 1: Check DocType exists
        debug_results["tests"]["doctype_exists"] = frappe.db.exists("DocType", "Unified Inbox Conversation")

        # Test 2: Find conversations
        conversations = frappe.get_all("Unified Inbox Conversation", limit=1, fields=["name", "status"])
        debug_results["tests"]["conversations_found"] = len(conversations)
        debug_results["tests"]["sample_conversation"] = conversations[0] if conversations else None

        # Test 3: Find users
        users = frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"}, limit=3, fields=["email", "full_name"])
        debug_results["tests"]["users_found"] = len(users)
        debug_results["tests"]["sample_users"] = users

        # Test 4: Check ERPNext assignment import
        try:
            from frappe.desk.form.assign_to import add as add_assignment
            debug_results["tests"]["erpnext_import"] = "success"
        except Exception as e:
            debug_results["tests"]["erpnext_import"] = f"failed: {str(e)}"

        # Test 5: Test native ERPNext assignment if we have data
        if conversations and users:
            try:
                from frappe.desk.form.assign_to import add as add_assignment
                native_result = add_assignment({
                    "assign_to": [users[0].email],
                    "doctype": "Unified Inbox Conversation",
                    "name": conversations[0].name,
                    "description": "Native ERPNext assignment test"
                })
                debug_results["tests"]["native_assignment"] = native_result
            except Exception as e:
                debug_results["tests"]["native_assignment"] = f"error: {str(e)}"

        # Test 6: Test custom assignment function if we have data
        if conversations and users:
            try:
                test_result = assign_conversation_to_user(
                    doctype="Unified Inbox Conversation",
                    docname=conversations[0].name,
                    assign_to=users[0].email,
                    description="Debug test assignment"
                )
                debug_results["tests"]["custom_assignment_function"] = test_result
            except Exception as e:
                debug_results["tests"]["custom_assignment_function"] = f"error: {str(e)}"

        return {
            "status": "success",
            "debug_results": debug_results
        }

    except Exception as e:
        frappe.log_error(f"Debug assignment error: {str(e)}", "Assignment Debug Error")
        return {
            "status": "error",
            "message": str(e)
        }


# Helper Functions
def get_agent_status(agent_name):
    """Get current status of an agent based on their active conversation count."""
    try:
        # Check agent's active conversation count to determine status
        active_count = frappe.db.count("Unified Inbox Conversation", {
            "assigned_agent": agent_name,
            "status": ["in", ["Agent Assigned", "In Progress", "Escalated"]]
        })
        if active_count >= 5:
            return "Busy"
        return "Available"
    except Exception:
        return "Available"


def get_agent_active_conversations(agent_name):
    """Get number of active conversations for an agent."""
    try:
        count = frappe.db.count("Unified Inbox Conversation", {
            "assigned_agent": agent_name,
            "status": ["in", ["Agent Assigned", "In Progress", "Escalated"]]
        })
        return count
    except:
        return 0


def get_agent_workload_status(agent_name):
    """Get workload status for an agent."""
    try:
        active_count = get_agent_active_conversations(agent_name)
        if active_count == 0:
            return "Light"
        elif active_count <= 3:
            return "Moderate"
        elif active_count <= 6:
            return "Heavy"
        else:
            return "Overloaded"
    except:
        return "Light"


def get_agent_performance_data(agent_name):
    """Get performance data for an agent from the database."""
    try:
        # Get agent's assigned conversations with escalations
        escalations_handled = frappe.db.count(
            "Unified Inbox Conversation",
            {"assigned_agent": agent_name, "status": "Escalated"}
        )

        # Calculate average response time from agent's messages
        agent_messages = frappe.get_all(
            "Unified Inbox Message",
            filters={"sender_name": agent_name, "direction": "Outbound"},
            fields=["timestamp", "conversation"],
            limit=100
        )

        avg_response_time = 60  # Default value in seconds
        if agent_messages:
            # In a real implementation, you'd calculate actual response times
            avg_response_time = 60

        return {
            "avg_response_time": avg_response_time,
            "satisfaction_score": 4.0,  # Would need a feedback system to calculate
            "escalations_handled": escalations_handled or 0
        }
    except Exception:
        return {
            "avg_response_time": 60,
            "satisfaction_score": 4.0,
            "escalations_handled": 0
        }


def send_escalation_notification(agent_name, conversation, escalation_reason):
    """Send notification to agent about escalation."""
    try:
        notification = frappe.get_doc({
            "doctype": "Notification Log",
            "subject": f"🚨 Escalated Conversation: {conversation.customer_name or 'Unknown Customer'}",
            "email_content": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px;">
                <h3 style="color: #d63384;">🚨 Conversation Escalated</h3>
                <p>A conversation has been escalated to you:</p>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <p><strong>Customer:</strong> {conversation.customer_name or 'Unknown'}</p>
                    <p><strong>Platform:</strong> {conversation.platform}</p>
                    <p><strong>Priority:</strong> <span style="color: #dc3545;">{conversation.priority}</span></p>
                    <p><strong>Escalation Reason:</strong> {escalation_reason}</p>
                    <p><strong>Subject:</strong> {conversation.subject or 'No subject'}</p>
                </div>
                <p><strong>Last Message:</strong> {conversation.last_message_preview or 'No preview available'}</p>
                <p style="color: #6c757d; font-size: 12px;">Please respond promptly to this escalated conversation.</p>
            </div>
            """,
            "for_user": agent_name,
            "type": "Alert"
        })
        notification.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Error sending escalation notification: {str(e)}", "Notification Error")


def send_assignment_notification(agent_name, conversation):
    """Send notification to agent about assignment."""
    try:
        notification = frappe.get_doc({
            "doctype": "Notification Log",
            "subject": f"👤 New Assignment: {conversation.customer_name or 'Unknown Customer'}",
            "email_content": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px;">
                <h3 style="color: #0d6efd;">👤 New Conversation Assignment</h3>
                <p>You have been assigned a new conversation:</p>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <p><strong>Customer:</strong> {conversation.customer_name or 'Unknown'}</p>
                    <p><strong>Platform:</strong> {conversation.platform}</p>
                    <p><strong>Priority:</strong> {conversation.priority}</p>
                    <p><strong>Subject:</strong> {conversation.subject or 'No subject'}</p>
                </div>
                <p><strong>Last Message:</strong> {conversation.last_message_preview or 'No preview available'}</p>
                <p style="color: #6c757d; font-size: 12px;">Please review and respond to this conversation.</p>
            </div>
            """,
            "for_user": agent_name,
            "type": "Assignment"
        })
        notification.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Error sending assignment notification: {str(e)}", "Notification Error")



def sweep_escalate_inactive_conversations():
    """
    Scheduled job: escalate open conversations after 24h of inactivity.
    - Assigns to Assistant Manager Corporate Affairs and Customer Services if unassigned
    - Notifies both Assistant Manager Corporate Affairs and Customer Services and Communications Officer
    """
    try:
        # Gather candidate recipients by roles
        target_roles = [
            "Assistant Manager Corporate Affairs and Customer Services",
            "Communications Officer"
        ]
        has_roles = frappe.get_all(
            "Has Role",
            filters={"role": ["in", target_roles]},
            fields=["parent"]
        )
        recipients = list({r["parent"] for r in has_roles}) if has_roles else []

        if not recipients:
            frappe.log_error("No recipients found for escalation (roles missing users).", "Unified Inbox Escalation")
            return {"status": "noop", "processed": 0}

        # Prefer Assistant Manager Corporate Affairs and Customer Services as primary assignee
        am_has_roles = frappe.get_all(
            "Has Role",
            filters={"role": "Assistant Manager Corporate Affairs and Customer Services"},
            fields=["parent"]
        )
        am_users = [r["parent"] for r in am_has_roles] if am_has_roles else []
        # Filter to enabled users only
        enabled_users = set(u["name"] for u in frappe.get_all("User", filters={"name": ["in", recipients], "enabled": 1}, fields=["name"]))
        recipients = [u for u in recipients if u in enabled_users]
        am_users = [u for u in am_users if u in enabled_users]

        if not recipients:
            frappe.log_error("No enabled recipients found for escalation.", "Unified Inbox Escalation")
            return {"status": "noop", "processed": 0}

        primary_assignee = am_users[0] if am_users else recipients[0]

        # Find candidate conversations
        conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters={
                "docstatus": ["!=", 2],
                "status": ["not in", ["Resolved", "Closed"]]
            },
            fields=[
                "name", "assigned_agent", "last_message_time", "creation_time",
                "escalated_at", "platform", "customer_name", "priority", "subject",
                "last_message_preview"
            ],
            order_by="last_message_time asc",
            limit=500
        )

        processed = 0
        now_dt = get_datetime(now())
        for c in conversations:
            last_activity = c.get("last_message_time") or c.get("creation_time")
            if not last_activity:
                continue
            try:
                last_dt = get_datetime(last_activity)
            except Exception:
                continue

            # Skip if already escalated after last activity
            esc_at = c.get("escalated_at")
            if esc_at:
                try:
                    esc_dt = get_datetime(esc_at)
                    if esc_dt >= last_dt:
                        continue
                except Exception:
                    pass

            seconds_inactive = time_diff_in_seconds(now_dt, last_dt)
            if seconds_inactive is None:
                continue
            if seconds_inactive < 24 * 3600:
                continue

            # Load and update conversation
            try:
                doc = frappe.get_doc("Unified Inbox Conversation", c.get("name"))
                doc.db_set("escalated_at", now())
                doc.db_set("escalation_reason", "Auto escalation: 24h inactivity")
                try:
                    doc.db_set("escalated_by", "Administrator")
                except Exception:
                    pass
                try:
                    # Some instances may not have "Escalated" in options; keep current status if db_set fails
                    doc.db_set("status", "Escalated")
                except Exception:
                    pass

                # Assign primary if none
                if not c.get("assigned_agent") and primary_assignee:
                    doc.db_set("assigned_agent", primary_assignee)
                    try:
                        doc.db_set("agent_assigned_at", now())
                    except Exception:
                        pass
                    try:
                        send_assignment_notification(primary_assignee, doc)
                    except Exception:
                        pass

                # Notify all recipients
                for r in recipients:
                    try:
                        send_escalation_notification(r, doc, "24h inactivity")
                    except Exception:
                        pass

                try:
                    doc.add_comment("Comment", "Auto escalated after 24h inactivity; management notified.")
                except Exception:
                    pass

                processed += 1
            except Exception as e:
                frappe.log_error(f"Escalation update failed for {c.get('name')}: {str(e)}", "Unified Inbox Escalation")

        return {"status": "success", "processed": processed}
    except Exception as e:
        frappe.log_error(f"Auto escalation sweep failed: {str(e)}", "Unified Inbox Escalation Sweep")
        return {"status": "error", "message": str(e)}


def sweep_agent_reassignments():
    """
    Scheduled job: detect conversations assigned to unavailable agents and reassign them.
    Agents are considered 'unavailable' if:
    1. Agent Dashboard status is not 'Available' (Sick, On Leave, Busy, Offline, etc.)
    2. Agent is outside their working hours
    3. User account is disabled
    """
    try:
        from assistant_crm.assistant_crm.assistant_crm_module.doctype.agent_dashboard.agent_dashboard import (
            AgentDashboard,
        )
        from frappe.utils import now

        # Find all open conversations that have an assigned agent
        conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters={
                "status": ["not in", ["Resolved", "Closed"]],
                "assigned_agent": ["is", "set"],
            },
            fields=["name", "assigned_agent", "platform", "customer_name"],
        )

        reassigned_count = 0
        for conv in conversations:
            agent_user = conv.assigned_agent

            # Check agent availability
            dashboard_name = frappe.db.get_value(
                "Agent Dashboard", {"agent_user": agent_user}, "name"
            )
            reassign = False
            reason = ""

            if not dashboard_name:
                # No dashboard means they haven't set up availability,
                # we treat them as unavailable to be safe if they're assigned.
                reassign = True
                reason = "No Agent Dashboard configured"
            else:
                agent_dashboard = frappe.get_doc("Agent Dashboard", dashboard_name)
                # Sync load before checking
                AgentDashboard.sync_unified_inbox_load_for_agent(agent_user)
                agent_dashboard.reload()

                if not agent_dashboard.is_available():
                    reassign = True
                    reason = f"Status: {agent_dashboard.status}"
                    if not agent_dashboard.is_within_working_hours():
                        reason = "Outside working hours"
                elif not frappe.db.get_value("User", agent_user, "enabled"):
                    reassign = True
                    reason = "User account disabled"

            if reassign:
                # Find a new available agent
                conv_doc = frappe.get_doc("Unified Inbox Conversation", conv.name)
                new_agent = conv_doc.find_available_agent()

                if new_agent and new_agent != agent_user:
                    # Reassign
                    conv_doc.db_set("assigned_agent", new_agent)
                    conv_doc.db_set("agent_assigned_at", now())

                    # Log the reassignment as a comment
                    comment = (
                        f"🔄 **AUTO-REASSIGNED**\n\n"
                        f"Original agent **{agent_user}** became unavailable ({reason}).\n"
                        f"Reassigned to **{new_agent}** for immediate handling."
                    )
                    conv_doc.add_comment("Comment", comment)

                    # Notify new agent
                    conv_doc.notify_agent_assignment(new_agent)

                    # Sync with linked issue if it exists
                    issue_id = getattr(conv_doc, "custom_issue_id", None)
                    if issue_id:
                        try:
                            frappe.db.set_value(
                                "Issue", issue_id, "custom_assigned_agent", new_agent
                            )
                        except Exception:
                            pass

                    reassigned_count += 1

        if reassigned_count > 0:
            frappe.log_error(
                f"Auto-reassigned {reassigned_count} conversations due to agent unavailability.",
                "Unified Inbox Sweep",
            )

        return {"status": "success", "reassigned": reassigned_count}

    except Exception as e:
        frappe.log_error(
            f"Error in sweep_agent_reassignments: {str(e)}",
            "Unified Inbox Reassignment Error",
        )
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def lookup_customer_data():
    """Lookup customer data from CoreBusiness for unified inbox."""
    try:
        data = frappe.local.form_dict
        nrc_number = data.get("nrc_number")
        phone_number = data.get("phone_number")
        beneficiary_id = data.get("beneficiary_id")

        if not any([nrc_number, phone_number, beneficiary_id]):
            return {
                "status": "error",
                "message": "Please provide NRC number, phone number, or beneficiary ID"
            }

        from assistant_crm.api.corebusiness_integration import get_beneficiary_info, get_customer_data_by_phone

        customer_data = None

        # Try different lookup methods
        if nrc_number:
            result = get_beneficiary_info(nrc_number=nrc_number)
            if result.get("status") == "success":
                customer_data = result.get("data")

        elif beneficiary_id:
            result = get_beneficiary_info(beneficiary_id=beneficiary_id)
            if result.get("status") == "success":
                customer_data = result.get("data")

        elif phone_number:
            customers = get_customer_data_by_phone(phone_number)
            if customers:
                # Convert first customer to expected format
                customer = customers[0]
                customer_data = {
                    "beneficiary_id": customer.get("BENEFICIARY_ID"),
                    "nrc_number": customer.get("NRC_NUMBER"),
                    "full_name": f"{customer.get('FIRST_NAME', '')} {customer.get('LAST_NAME', '')}".strip(),
                    "phone_number": customer.get("PHONE_NUMBER"),
                    "email_address": customer.get("EMAIL_ADDRESS"),
                    "employer_name": customer.get("EMPLOYER_NAME"),
                    "status": customer.get("STATUS")
                }

        if not customer_data:
            return {
                "status": "error",
                "message": "No customer found with the provided information"
            }

        # Get additional data if beneficiary ID is available
        additional_data = {}
        beneficiary_id = customer_data.get("beneficiary_id")

        if beneficiary_id:
            # Get recent payments
            from assistant_crm.api.corebusiness_integration import get_pension_payments, get_claims_status

            payments_result = get_pension_payments(beneficiary_id, 5)
            if payments_result.get("status") == "success":
                additional_data["recent_payments"] = payments_result.get("data", {}).get("payments", [])

            # Get recent claims
            claims_result = get_claims_status(beneficiary_id)
            if claims_result.get("status") == "success":
                additional_data["recent_claims"] = claims_result.get("data", {}).get("claims", [])

        return {
            "status": "success",
            "data": {
                "customer_info": customer_data,
                "additional_data": additional_data,
                "data_source": "CoreBusiness Live Data"
            }
        }

    except Exception as e:
        frappe.log_error(f"Error looking up customer data: {str(e)}", "Customer Lookup Error")
        return {"status": "error", "message": f"Lookup failed: {str(e)}"}


@frappe.whitelist()
def get_customer_summary():
    """Get comprehensive customer summary for agent dashboard."""
    try:
        data = frappe.local.form_dict
        conversation_name = data.get("conversation_name")

        if not conversation_name:
            return {"status": "error", "message": "Conversation name is required"}

        # Get conversation details
        conversation = frappe.get_doc("Unified Inbox Conversation", conversation_name)

        summary = {
            "conversation_info": {
                "customer_name": conversation.customer_name,
                "platform": conversation.platform,
                "status": conversation.status,
                "priority": conversation.priority,
                "created_at": conversation.creation,
                "last_message_time": conversation.last_message_time
            },
            "corebusiness_data": None,
            "interaction_history": {
                "total_messages": 0,
                "ai_responses": 0,
                "agent_responses": 0,
                "escalations": 0
            }
        }

        # Get CoreBusiness data if phone number is available
        if conversation.customer_phone:
            try:
                from assistant_crm.api.corebusiness_integration import get_customer_context
                customer_context = get_customer_context(conversation.customer_phone)
                if customer_context:
                    summary["corebusiness_data"] = customer_context
            except Exception as e:
                frappe.log_error(f"Error getting customer context: {str(e)}", "Customer Summary Error")

        # Get interaction statistics
        messages = frappe.get_all(
            "Unified Inbox Message",
            filters={"conversation": conversation_name},
            fields=["direction", "processed_by_ai", "agent_response"]
        )

        summary["interaction_history"]["total_messages"] = len(messages)
        summary["interaction_history"]["ai_responses"] = len([m for m in messages if m.processed_by_ai])
        summary["interaction_history"]["agent_responses"] = len([m for m in messages if m.agent_response])

        return {
            "status": "success",
            "data": summary
        }

    except Exception as e:
        frappe.log_error(f"Error getting customer summary: {str(e)}", "Customer Summary Error")
        return {"status": "error", "message": f"Failed to get customer summary: {str(e)}"}


@frappe.whitelist()
def create_test_live_conversation():
    """Create a test live conversation for assignment testing."""
    try:
        from assistant_crm.api.social_media_ports import TelegramIntegration

        telegram = TelegramIntegration()

        # Create test webhook data
        import time
        test_webhook = {
            "update_id": 999999,
            "message": {
                "message_id": 12345,
                "from": {
                    "id": 123456789,
                    "first_name": "Test",
                    "last_name": "User",
                    "username": "testuser"
                },
                "chat": {
                    "id": 123456789,
                    "first_name": "Test",
                    "last_name": "User",
                    "type": "private"
                },
                "date": int(time.time()),
                "text": "Hello! I need help with my pension inquiry. This is a test message for assignment testing."
            }
        }

        # Process webhook to create conversation
        result = telegram.process_webhook(test_webhook)

        if result.get("status") == "success":
            # Find the created conversation
            conversations = frappe.get_all(
                "Unified Inbox Conversation",
                filters={
                    "platform": "Telegram",
                    "customer_platform_id": "123456789"
                },
                fields=["name", "customer_name", "custom_issue_id"],
                limit=1
            )

            if conversations:
                conv = conversations[0]
                return {
                    "status": "success",
                    "message": "Test live conversation created",
                    "conversation": {
                        "name": conv.name,
                        "customer_name": conv.customer_name,
                        "issue_id": conv.custom_issue_id
                    }
                }

        return {"status": "error", "message": "Failed to create test conversation"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def diagnostic_assignment_test():
    """
    Comprehensive diagnostic test for ERPNext native assignment functionality.
    Tests all components of the assignment system.
    """
    try:
        print("DEBUG: Starting comprehensive assignment diagnostic test")

        # Test 1: Check if we have live conversations
        live_conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters={"name": ["not like", "conv-%"]},
            fields=["name", "customer_name", "platform", "assigned_agent"],
            limit=5
        )

        print(f"DEBUG: Found {len(live_conversations)} live conversations")

        # Test 2: Check available agents
        agents_result = get_available_agents()
        print(f"DEBUG: Agents API result: {agents_result}")

        # Test 3: Test ERPNext's assignment system directly
        if live_conversations and agents_result.get("status") == "success" and agents_result.get("data"):
            test_conversation = live_conversations[0]
            test_agent = agents_result["data"][0]["email"]

            print(f"DEBUG: Testing assignment of {test_conversation.name} to {test_agent}")

            # Test the assign_conversation_to_user function
            assignment_result = assign_conversation_to_user(
                doctype="Unified Inbox Conversation",
                docname=test_conversation.name,
                assign_to=test_agent,
                description="Diagnostic test assignment"
            )

            print(f"DEBUG: Assignment result: {assignment_result}")

            # Test 4: Check if ERPNext assignment was created
            try:
                from frappe.desk.form.assign_to import get as get_assignments
                assignments = get_assignments("Unified Inbox Conversation", test_conversation.name)
                print(f"DEBUG: ERPNext assignments: {assignments}")
            except Exception as assign_check_error:
                print(f"DEBUG: Error checking assignments: {str(assign_check_error)}")

            # Test 5: Check conversation status after assignment
            updated_conversation = frappe.get_doc("Unified Inbox Conversation", test_conversation.name)
            print(f"DEBUG: Updated conversation status: {updated_conversation.status}")
            print(f"DEBUG: Updated assigned agent: {updated_conversation.assigned_agent}")

            return {
                "status": "success",
                "message": "Diagnostic test completed",
                "test_results": {
                    "live_conversations_found": len(live_conversations),
                    "agents_available": len(agents_result.get("data", [])),
                    "test_conversation": test_conversation.name,
                    "test_agent": test_agent,
                    "assignment_result": assignment_result,
                    "conversation_status": updated_conversation.status,
                    "assigned_agent": updated_conversation.assigned_agent
                }
            }
        else:
            return {
                "status": "error",
                "message": "Cannot run diagnostic test",
                "issues": {
                    "live_conversations": len(live_conversations),
                    "agents_available": len(agents_result.get("data", [])),
                    "agents_api_status": agents_result.get("status")
                }
            }

    except Exception as e:
        error_msg = f"Error in diagnostic test: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Assignment Diagnostic Test Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def test_erpnext_assignment_dialog():
    """Test ERPNext's native assignment dialog compatibility."""
    try:
        # Get a live conversation for testing
        live_conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters={"name": ["not like", "conv-%"]},
            fields=["name", "customer_name", "platform"],
            limit=1
        )

        if not live_conversations:
            return {"status": "error", "message": "No live conversations found"}

        test_conversation = live_conversations[0]
        doctype = "Unified Inbox Conversation"
        docname = test_conversation.name

        # Test document access
        try:
            doc = frappe.get_doc(doctype, docname)
            print(f"DEBUG: Successfully retrieved document: {doc.name}")
        except Exception as doc_error:
            return {"status": "error", "message": f"Cannot access document: {str(doc_error)}"}

        # Test ERPNext assignment imports
        try:
            from frappe.desk.form.assign_to import add as add_assignment
            print("DEBUG: Successfully imported ERPNext assignment functions")
        except Exception as import_error:
            return {"status": "error", "message": f"ERPNext assignment import failed: {str(import_error)}"}

        # Check available users
        users = frappe.get_all(
            "User",
            filters={"enabled": 1, "user_type": "System User"},
            fields=["name", "email", "full_name"],
            limit=5
        )

        return {
            "status": "success",
            "message": "ERPNext assignment dialog compatibility test completed",
            "test_results": {
                "doctype": doctype,
                "docname": docname,
                "document_accessible": True,
                "assignment_functions_available": True,
                "available_users": len(users),
                "sample_users": [{"email": u.email, "name": u.full_name} for u in users[:3]]
            }
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def test_complete_assignment_flow():
    """
    Test the complete assignment flow with the new ERPNext native integration.
    """
    try:
        print("DEBUG: Testing complete assignment flow")

        # Step 1: Get or create a live conversation
        live_conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters={"name": ["not like", "conv-%"]},
            fields=["name", "customer_name", "platform", "assigned_agent"],
            limit=1
        )

        if not live_conversations:
            # Create a test conversation
            create_result = create_test_live_conversation()
            if create_result.get("status") != "success":
                return {"status": "error", "message": "Failed to create test conversation"}

            # Get the created conversation
            live_conversations = frappe.get_all(
                "Unified Inbox Conversation",
                filters={"name": ["not like", "conv-%"]},
                fields=["name", "customer_name", "platform", "assigned_agent"],
                limit=1
            )

        if not live_conversations:
            return {"status": "error", "message": "No live conversations available for testing"}

        test_conversation = live_conversations[0]

        # Step 2: Get available agents
        agents_result = get_available_agents()
        if agents_result.get("status") != "success" or not agents_result.get("data"):
            return {"status": "error", "message": "No agents available for testing"}

        test_agent = agents_result["data"][0]["email"]

        # Step 3: Test the assignment API with new response format
        assignment_result = assign_conversation_to_user(
            doctype="Unified Inbox Conversation",
            docname=test_conversation.name,
            assign_to=test_agent,
            description="Complete flow test assignment"
        )

        print(f"DEBUG: Assignment API result: {assignment_result}")

        # Step 4: Verify the response format matches ERPNext expectations
        expected_format_valid = (
            assignment_result and
            "message" in assignment_result and
            "assigned_to" in assignment_result["message"] and
            "status" in assignment_result["message"]
        )

        # Step 5: Check conversation status after assignment
        updated_conversation = frappe.get_doc("Unified Inbox Conversation", test_conversation.name)

        return {
            "status": "success",
            "message": "Complete assignment flow test completed",
            "test_results": {
                "conversation_name": test_conversation.name,
                "test_agent": test_agent,
                "assignment_api_response": assignment_result,
                "response_format_valid": expected_format_valid,
                "conversation_status_after": updated_conversation.status,
                "assigned_agent_after": updated_conversation.assigned_agent,
                "expected_frontend_data": {
                    "assigned_to": assignment_result.get("message", {}).get("assigned_to"),
                    "assigned_to_name": assignment_result.get("message", {}).get("assigned_to_name"),
                    "status": assignment_result.get("message", {}).get("status")
                }
            }
        }

    except Exception as e:
        error_msg = f"Error in complete assignment flow test: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Complete Assignment Flow Test Error")
        return {"status": "error", "message": error_msg}


@frappe.whitelist()
def test_button_functionality():
    """
    Test individual button functionality to identify specific issues.
    """
    try:
        print("DEBUG: Testing individual button functionality")

        results = {
            "status": "success",
            "button_tests": {}
        }

        # Test Assignment API
        print("DEBUG: Testing assignment functionality")
        try:
            # Get a test conversation and agent
            conversations = frappe.get_all(
                "Unified Inbox Conversation",
                fields=["name", "customer_name", "platform"],
                limit=1
            )

            agents_result = get_available_agents()

            if conversations and agents_result.get("status") == "success" and agents_result.get("data"):
                test_conversation = conversations[0].name
                test_agent = agents_result["data"][0]["email"]

                # Test assignment API call
                assignment_result = assign_conversation_to_user(
                    doctype="Unified Inbox Conversation",
                    docname=test_conversation,
                    assign_to=test_agent,
                    description="Button functionality test"
                )

                results["button_tests"]["assignment"] = {
                    "status": "tested",
                    "api_response": assignment_result,
                    "test_conversation": test_conversation,
                    "test_agent": test_agent
                }
            else:
                results["button_tests"]["assignment"] = {
                    "status": "cannot_test",
                    "reason": "No conversations or agents available"
                }

        except Exception as assign_error:
            results["button_tests"]["assignment"] = {
                "status": "error",
                "error": str(assign_error)
            }

        # Test Issue Creation
        print("DEBUG: Testing issue creation functionality")
        try:
            if conversations:
                test_conversation = conversations[0]
                issue_result = create_issue_for_conversation(
                    conversation_name=test_conversation.name,
                    customer_name=test_conversation.customer_name,
                    platform=test_conversation.platform,
                    initial_message="Test message for button functionality test"
                )

                results["button_tests"]["issue_creation"] = {
                    "status": "tested",
                    "api_response": issue_result,
                    "test_conversation": test_conversation.name
                }
            else:
                results["button_tests"]["issue_creation"] = {
                    "status": "cannot_test",
                    "reason": "No conversations available"
                }

        except Exception as issue_error:
            results["button_tests"]["issue_creation"] = {
                "status": "error",
                "error": str(issue_error)
            }

        return results

    except Exception as e:
        error_msg = f"Error testing button functionality: {str(e)}"
        print(f"DEBUG: {error_msg}")
        return {"status": "error", "message": error_msg}


@frappe.whitelist()
def update_issue_with_conversation_history(conversation_name, new_message_content=None, sender_name=None, timestamp=None, direction="Inbound"):
    """
    Update the ERPNext Issue with complete conversation history after each message.
    This ensures the Issue document contains the full conversation from start to finish.
    """
    try:
        print(f"DEBUG: Updating Issue for conversation {conversation_name} with new message")

        # Find the Issue linked to this conversation
        issue_name = frappe.db.get_value(
            "Issue",
            {"custom_conversation_id": conversation_name},
            "name"
        )

        if not issue_name:
            print(f"DEBUG: No Issue found for conversation {conversation_name}")
            return {"status": "error", "message": "No Issue found for this conversation"}

        # Get the Issue document
        issue_doc = frappe.get_doc("Issue", issue_name)

        # If NRC already exists on Issue, skip re-scanning to avoid overwriting/extra work
        existing_nrc = None
        try:
            issue_meta = frappe.get_meta("Issue")
            if getattr(issue_meta, 'has_field', None) and issue_meta.has_field('custom_customer_nrc'):
                existing_nrc = issue_doc.get('custom_customer_nrc')
        except Exception:
            existing_nrc = None

        # Get all messages for this conversation
        messages = frappe.get_all(
            "Unified Inbox Message",
            filters={"conversation": conversation_name},
            fields=["message_content", "sender_name", "timestamp", "direction", "message_type"],
            order_by="timestamp asc"
        )

        if not existing_nrc:
            # Attempt NRC extraction from messages and persist to Issue/Conversation
            nrc_to_use = None
            try:
                for msg in messages:
                    candidate = _extract_first_nrc_from_text(msg.message_content or "")
                    if candidate:
                        nrc_to_use = candidate
                        break
                if not nrc_to_use and new_message_content:
                    nrc_to_use = _extract_first_nrc_from_text(new_message_content)

                if nrc_to_use:
                    # Store on conversation if field exists
                    try:
                        conv_meta = frappe.get_meta("Unified Inbox Conversation")
                        if getattr(conv_meta, 'has_field', None) and conv_meta.has_field('customer_nrc'):
                            frappe.db.set_value("Unified Inbox Conversation", conversation_name, {"customer_nrc": _normalize_nrc(nrc_to_use)})
                    except Exception:
                        pass

                    # Lookup and update Issue with NRC and beneficiary
                    customer_info = _find_beneficiary_or_employee_by_nrc(nrc_to_use)
                    conv_phone = None
                    try:
                        conv_meta = frappe.get_meta("Unified Inbox Conversation")
                        if getattr(conv_meta, 'has_field', None) and conv_meta.has_field('customer_phone'):
                            conv_phone = frappe.db.get_value("Unified Inbox Conversation", conversation_name, 'customer_phone')
                    except Exception:
                        conv_phone = None
                    _set_issue_customer_fields(issue_name, nrc_to_use, conv_phone, customer_info)
            except Exception as nrc_err:
                try:
                    frappe.log_error(f"NRC extraction/update failed: {nrc_err}", "Assistant CRM NRC Extract")
                except Exception:
                    pass

        # Build conversation history as bullet points, preserving original timestamps (no timezone conversion)
        lines = []
        lines.append("Conversation Timeline")
        lines.append("")

        for msg in messages:
            timestamp_str = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S') if msg.timestamp else "Unknown time"
            direction_label = "Outbound" if (msg.direction or "").lower() == "outbound" else "Inbound"
            sender = msg.sender_name or ("Agent" if direction_label == "Outbound" else "Customer")
            content = (msg.message_content or "[No content]").strip()

            # Bullet line: timestamp, direction, sender, content
            lines.append(f"- {timestamp_str} {direction_label} — {sender}: {content}")

        # Update Issue description with complete conversation, using HTML line breaks so it renders on separate lines
        try:
            escaped_lines = [frappe.utils.escape_html(l) for l in lines]
        except Exception:
            escaped_lines = lines
        full_description = "<br>".join(escaped_lines)

        # Update Issue subject to include message count
        message_count = len(messages)
        original_subject = issue_doc.subject.split(" (")[0]  # Remove existing message count
        new_subject = f"{original_subject} ({message_count} messages)"

        # Use frappe.db.set_value to update only specific fields without validation issues
        # This preserves all other fields and avoids required field validation problems
        print(f"DEBUG: Updating Issue {issue_name} with frappe.db.set_value to avoid validation issues")

        try:
            frappe.db.set_value("Issue", issue_name, {
                "description": full_description,
                "subject": new_subject
            })

            # Commit the changes
            frappe.db.commit()
            print(f"DEBUG: Successfully committed Issue update using frappe.db.set_value")

        except Exception as db_error:
            print(f"DEBUG: frappe.db.set_value failed, trying individual field updates: {str(db_error)}")

            # Fallback: Update fields individually
            try:
                frappe.db.set_value("Issue", issue_name, "description", full_description)
                frappe.db.set_value("Issue", issue_name, "subject", new_subject)
                frappe.db.commit()
                print(f"DEBUG: Successfully updated Issue using individual field updates")

            except Exception as individual_error:
                print(f"DEBUG: Individual field updates also failed: {str(individual_error)}")
                raise individual_error

        print(f"DEBUG: Successfully updated Issue {issue_name} with {message_count} messages")

        return {
            "status": "success",
            "message": f"Issue {issue_name} updated with complete conversation history",
            "issue_id": issue_name,
            "message_count": message_count
        }

    except Exception as e:
        error_msg = f"Error updating Issue for conversation {conversation_name}: {str(e)}"
        frappe.log_error(error_msg, "Issue Update Error")
        print(f"DEBUG: {error_msg}")

        # Enhanced error logging for debugging
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")

        # Log to webhook debug file for easier monitoring
        try:
            with open("/workspace/development/frappe-bench/logs/webhook_debug.log", "a") as f:
                f.write(f"ERROR: Issue update failed for {conversation_name}: {error_msg}\n")
                f.write(f"Traceback: {traceback.format_exc()}\n")
        except:
            pass

        return {
            "status": "error",
            "message": f"Failed to update Issue: {str(e)}"
        }


@frappe.whitelist()
def comprehensive_system_diagnostic():
    """
    Comprehensive diagnostic analysis of the unified inbox system.
    Tests all major components and identifies issues.
    """
    try:
        print("DEBUG: Starting comprehensive system diagnostic")

        diagnostic_results = {
            "status": "success",
            "timestamp": frappe.utils.now(),
            "tests": {}
        }

        # Test 1: Database Connectivity and Conversations
        print("DEBUG: Testing database connectivity and conversations")
        try:
            conversations = frappe.get_all(
                "Unified Inbox Conversation",
                fields=["name", "customer_name", "platform", "status", "assigned_agent", "custom_issue_id"],
                limit=10
            )

            diagnostic_results["tests"]["database_connectivity"] = {
                "status": "success",
                "total_conversations": len(conversations),
                "sample_conversations": conversations[:3] if conversations else [],
                "conversations_with_issues": len([c for c in conversations if c.custom_issue_id])
            }
            print(f"DEBUG: Found {len(conversations)} conversations")

        except Exception as db_error:
            diagnostic_results["tests"]["database_connectivity"] = {
                "status": "error",
                "error": str(db_error)
            }
            print(f"DEBUG: Database connectivity error: {str(db_error)}")

        # Test 2: Available Agents API
        print("DEBUG: Testing available agents API")
        try:
            agents_result = get_available_agents()
            diagnostic_results["tests"]["available_agents_api"] = {
                "status": agents_result.get("status"),
                "agent_count": len(agents_result.get("data", [])),
                "sample_agents": agents_result.get("data", [])[:2]
            }
            print(f"DEBUG: Agents API returned {len(agents_result.get('data', []))} agents")

        except Exception as agents_error:
            diagnostic_results["tests"]["available_agents_api"] = {
                "status": "error",
                "error": str(agents_error)
            }
            print(f"DEBUG: Agents API error: {str(agents_error)}")

        # Test 3: ERPNext Assignment System
        print("DEBUG: Testing ERPNext assignment system")
        try:
            from frappe.desk.form.assign_to import add as add_assignment
            diagnostic_results["tests"]["erpnext_assignment"] = {
                "status": "success",
                "assignment_function_available": True
            }
            print("DEBUG: ERPNext assignment system available")

        except Exception as assignment_error:
            diagnostic_results["tests"]["erpnext_assignment"] = {
                "status": "error",
                "assignment_function_available": False,
                "error": str(assignment_error)
            }
            print(f"DEBUG: ERPNext assignment error: {str(assignment_error)}")

        # Test 4: Issue Creation and Linking
        print("DEBUG: Testing Issue creation and linking")
        try:
            # Check if we have conversations without Issues
            conversations_without_issues = frappe.get_all(
                "Unified Inbox Conversation",
                filters={"custom_issue_id": ["is", "not set"]},
                fields=["name", "customer_name", "platform"],
                limit=5
            )

            # Check existing Issues
            existing_issues = frappe.get_all(
                "Issue",
                filters={"custom_conversation_id": ["is", "set"]},
                fields=["name", "subject", "custom_conversation_id"],
                limit=5
            )

            diagnostic_results["tests"]["issue_integration"] = {
                "status": "success",
                "conversations_without_issues": len(conversations_without_issues),
                "existing_linked_issues": len(existing_issues),
                "sample_unlinked_conversations": conversations_without_issues[:2],
                "sample_linked_issues": existing_issues[:2]
            }
            print(f"DEBUG: {len(conversations_without_issues)} conversations without Issues")

        except Exception as issue_error:
            diagnostic_results["tests"]["issue_integration"] = {
                "status": "error",
                "error": str(issue_error)
            }
            print(f"DEBUG: Issue integration error: {str(issue_error)}")

        return diagnostic_results

    except Exception as e:
        error_msg = f"Error in comprehensive system diagnostic: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Comprehensive System Diagnostic Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def test_telegram_assignment():
    """Test assignment functionality specifically for Telegram conversations."""
    try:
        print("DEBUG: Testing Telegram assignment functionality")

        # Find Telegram conversations
        telegram_conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters={"platform": "Telegram"},
            fields=["name", "customer_name", "status", "assigned_agent"],
            limit=5
        )

        print(f"DEBUG: Found {len(telegram_conversations)} Telegram conversations")

        if not telegram_conversations:
            return {
                "status": "error",
                "message": "No Telegram conversations found for testing"
            }

        # Get available agents
        agents_result = get_available_agents()
        if agents_result.get("status") != "success" or not agents_result.get("data"):
            return {
                "status": "error",
                "message": "No agents available for testing"
            }

        test_conversation = telegram_conversations[0]
        test_agent = agents_result["data"][0]["email"]

        print(f"DEBUG: Testing assignment of Telegram conversation {test_conversation.name} to {test_agent}")

        # Test the assignment
        assignment_result = assign_conversation_to_user(
            doctype="Unified Inbox Conversation",
            docname=test_conversation.name,
            assign_to=test_agent,
            description="Telegram assignment test"
        )

        print(f"DEBUG: Telegram assignment result: {assignment_result}")

        # Check conversation status after assignment
        updated_conversation = frappe.get_doc("Unified Inbox Conversation", test_conversation.name)

        return {
            "status": "success",
            "message": "Telegram assignment test completed",
            "test_results": {
                "telegram_conversation": test_conversation.name,
                "customer_name": test_conversation.customer_name,
                "test_agent": test_agent,
                "assignment_api_response": assignment_result,
                "conversation_status_before": test_conversation.status,
                "conversation_status_after": updated_conversation.status,
                "assigned_agent_before": test_conversation.assigned_agent,
                "assigned_agent_after": updated_conversation.assigned_agent,
                "response_format_analysis": {
                    "has_assigned_to": "assigned_to" in assignment_result,
                    "has_status": "status" in assignment_result,
                    "has_message_wrapper": "message" in assignment_result,
                    "response_structure": list(assignment_result.keys()) if assignment_result else []
                }
            }
        }

    except Exception as e:
        error_msg = f"Error testing Telegram assignment: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Telegram Assignment Test Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def test_frontend_assignment_integration():
    """Test the frontend assignment integration with backend APIs."""
    try:
        print("DEBUG: Testing frontend assignment integration")

        # Find a Telegram conversation
        telegram_conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters={"platform": "Telegram"},
            fields=["name", "customer_name", "status", "assigned_agent"],
            limit=1
        )

        if not telegram_conversations:
            return {
                "status": "error",
                "message": "No Telegram conversations found for testing"
            }

        # Get available agents
        agents_result = get_available_agents()
        if agents_result.get("status") != "success" or not agents_result.get("data"):
            return {
                "status": "error",
                "message": "No agents available for testing"
            }

        test_conversation = telegram_conversations[0]
        test_agent = agents_result["data"][0]["email"]

        print(f"DEBUG: Testing frontend integration with conversation {test_conversation.name} and agent {test_agent}")

        # Test the assignment API that the frontend will call
        assignment_result = assign_conversation_to_user(
            doctype="Unified Inbox Conversation",
            docname=test_conversation.name,
            assign_to=test_agent,
            description="Frontend integration test"
        )

        print(f"DEBUG: Assignment result: {assignment_result}")

        # Verify the conversation was updated
        updated_conversation = frappe.get_doc("Unified Inbox Conversation", test_conversation.name)

        return {
            "status": "success",
            "message": "Frontend assignment integration test completed",
            "test_results": {
                "conversation_name": test_conversation.name,
                "customer_name": test_conversation.customer_name,
                "platform": "Telegram",
                "test_agent": test_agent,
                "assignment_api_response": assignment_result,
                "conversation_status_before": test_conversation.status,
                "conversation_status_after": updated_conversation.status,
                "assigned_agent_before": test_conversation.assigned_agent,
                "assigned_agent_after": updated_conversation.assigned_agent,
                "frontend_expectations": {
                    "should_show_success": assignment_result.get("status") == "success",
                    "should_update_ui": True,
                    "expected_status": "Agent Assigned",
                    "expected_agent": test_agent
                }
            }
        }

    except Exception as e:
        error_msg = f"Error testing frontend assignment integration: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Frontend Assignment Integration Test Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def test_telegram_utc_timestamp_fix():
    """Test the UTC timestamp fix for Telegram conversations."""
    try:
        print("DEBUG: Testing Telegram UTC timestamp fix")

        # Import required modules
        import time
        import random
        from assistant_crm.api.social_media_ports import TelegramIntegration

        # Create unique chat ID for new conversation
        unique_chat_id = random.randint(100000000, 999999999)
        current_unix_time = int(time.time())

        # Create test webhook data with current timestamp
        test_webhook = {
            "update_id": random.randint(100000, 999999),
            "message": {
                "message_id": random.randint(10000, 99999),
                "from": {
                    "id": unique_chat_id,
                    "first_name": "UTC",
                    "last_name": "TestUser",
                    "username": "utctestuser"
                },
                "chat": {
                    "id": unique_chat_id,
                    "first_name": "UTC",
                    "last_name": "TestUser",
                    "type": "private"
                },
                "date": current_unix_time,
                "text": "Testing UTC timestamp fix - this message should show accurate relative time!"
            }
        }

        print(f"DEBUG: Creating test message with Unix timestamp: {current_unix_time}")

        # Process webhook to create conversation
        telegram = TelegramIntegration()
        result = telegram.process_webhook(test_webhook)

        print(f"DEBUG: Webhook processing result: {result}")

        # Get the created conversation
        conversations = frappe.get_all(
            "Unified Inbox Conversation",
            filters={"platform": "Telegram", "customer_name": "UTC TestUser (@utctestuser)"},
            fields=["name", "last_message_time", "creation_time"],
            order_by="creation desc",
            limit=1
        )

        if conversations:
            conv = conversations[0]

            # Get the message
            messages = frappe.get_all(
                "Unified Inbox Message",
                filters={"conversation": conv.name},
                fields=["name", "timestamp", "creation"],
                order_by="creation desc",
                limit=1
            )

            # Calculate time differences
            from datetime import datetime
            now = datetime.now()

            if messages:
                msg = messages[0]
                msg_time = datetime.strptime(str(msg.timestamp)[:19], '%Y-%m-%d %H:%M:%S')
                time_diff = now - msg_time
                minutes_ago = int(time_diff.total_seconds() / 60)

                return {
                    "status": "success",
                    "message": "UTC timestamp fix test completed",
                    "test_results": {
                        "conversation_name": conv.name,
                        "unix_timestamp_sent": current_unix_time,
                        "stored_timestamp": str(msg.timestamp),
                        "current_time": str(now),
                        "time_difference_minutes": minutes_ago,
                        "expected_display": "Just now" if minutes_ago < 1 else f"{minutes_ago}m ago",
                        "timestamp_accuracy": "ACCURATE" if minutes_ago < 5 else "INACCURATE",
                        "utc_fix_working": minutes_ago < 5
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": "No messages found for test conversation"
                }
        else:
            return {
                "status": "error",
                "message": "Test conversation not created"
            }

    except Exception as e:
        error_msg = f"Error testing UTC timestamp fix: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "UTC Timestamp Fix Test Error")
        return {
            "status": "error",
            "message": error_msg
        }


@frappe.whitelist()
def test_real_telegram_webhook_timestamp():
    """Test the real Telegram webhook path (realtime_webhooks.py) for timestamp accuracy."""
    try:
        print("DEBUG: Testing real Telegram webhook timestamp fix")

        # Import required modules
        import time
        import random
        from assistant_crm.api.realtime_webhooks import process_telegram_message_realtime

        # Create unique chat ID for new conversation
        unique_chat_id = random.randint(100000000, 999999999)
        current_unix_time = int(time.time())

        # Create test webhook data with current timestamp
        test_message = {
            "message_id": random.randint(10000, 99999),
            "from": {
                "id": unique_chat_id,
                "first_name": "RealWebhook",
                "last_name": "TestUser",
                "username": "realwebhooktest"
            },
            "chat": {
                "id": unique_chat_id,
                "first_name": "RealWebhook",
                "last_name": "TestUser",
                "type": "private"
            },
            "date": current_unix_time,
            "text": "Testing real webhook timestamp fix - this should show accurate time!"
        }

        print(f"DEBUG: Processing real webhook with Unix timestamp: {current_unix_time}")

        # Process through real webhook path
        process_telegram_message_realtime(test_message)

        # Check if Omnichannel Message was created with correct timestamp
        omnichannel_messages = frappe.get_all(
            "Omnichannel Message",
            filters={"channel_type": "Telegram", "channel_id": str(unique_chat_id)},
            fields=["name", "received_at", "creation"],
            order_by="creation desc",
            limit=1
        )

        # Calculate time differences
        from datetime import datetime
        now = datetime.now()

        if omnichannel_messages:
            msg = omnichannel_messages[0]
            msg_time = datetime.strptime(str(msg.received_at)[:19], '%Y-%m-%d %H:%M:%S')
            time_diff = now - msg_time
            minutes_ago = int(time_diff.total_seconds() / 60)

            return {
                "status": "success",
                "message": "Real webhook timestamp fix test completed",
                "test_results": {
                    "omnichannel_message_name": msg.name,
                    "unix_timestamp_sent": current_unix_time,
                    "stored_received_at": str(msg.received_at),
                    "current_time": str(now),
                    "time_difference_minutes": minutes_ago,
                    "expected_display": "Just now" if minutes_ago < 1 else f"{minutes_ago}m ago",
                    "timestamp_accuracy": "ACCURATE" if minutes_ago < 5 else "INACCURATE",
                    "real_webhook_fix_working": minutes_ago < 5,
                    "webhook_path": "realtime_webhooks.py → omnichannel_router.py"
                }
            }
        else:
            return {
                "status": "error",
                "message": "No Omnichannel Message created by real webhook"
            }

    except Exception as e:
        error_msg = f"Error testing real webhook timestamp fix: {str(e)}"
        print(f"DEBUG: {error_msg}")
        frappe.log_error(error_msg, "Real Webhook Timestamp Fix Test Error")
        return {
            "status": "error",
            "message": error_msg
        }

