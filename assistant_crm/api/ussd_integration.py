#!/usr/bin/env python3
"""
USSD webhook endpoint for Assistant CRM
- Synchronous flow: returns plain text "CON ..." or "END ..."
- Reuses Unified Inbox pipeline by creating an inbound message and invoking
  unified_inbox_api.process_message_with_ai(message_id) inline, then returns the
  most-recent AI outbound message content as the USSD screen.

Exit behavior confirmed:
- If user sends "0" or "exit" (case-insensitive), terminate the session with END.
- If survey flow completes (conversation status becomes Resolved/Closed), return END.

Primary language: English.
"""
from typing import Optional
import json

import frappe
from frappe.utils import now, add_to_date

# Reuse platform helpers for conversation/message creation
from assistant_crm.api.social_media_ports import USSDIntegration


MAX_SCREEN_LEN = 160  # conservative GSM-7 limit per screen
EXIT_KEY_HINT = "\n0. Exit"



def dev_simulate_ussd_request(sessionId: str, phoneNumber: str, serviceCode: str = "*123#", text: str = ""):
    """Dev-only helper to run USSD webhook without an HTTP server.
    Use via: bench --site <site> execute assistant_crm.api.ussd_integration.dev_simulate_ussd_request --kwargs '{"sessionId":"S1","phoneNumber":"26097...","text":"1*Hi"}'
    """
    frappe.local.request = frappe._dict(method="GET")
    frappe.local.request_ip = "127.0.0.1"
    frappe.local.form_dict = frappe._dict(
        sessionId=sessionId,
        phoneNumber=phoneNumber,
        serviceCode=serviceCode,
        text=text,
    )
    return ussd_webhook()


def _truncate_for_ussd(text: str, add_exit_hint: bool) -> str:
    text = (text or "").strip()
    if not text:
        text = "How can I help you today?"
    # Ensure total length including exit hint stays under limit
    extra = len(EXIT_KEY_HINT) if add_exit_hint else 0
    allowed = max(1, MAX_SCREEN_LEN - extra)
    if len(text) > allowed:
        text = text[: allowed - 1] + "…"
    if add_exit_hint:
        # Add exit option on a new line if not already present
        if "0. Exit" not in text:
            text = f"{text}{EXIT_KEY_HINT}"
    return text


def _get_or_create_session(session_id: str, phone_number: str, provider: Optional[str], service_code: Optional[str]) -> str:
    # DocType is named by session_id (autoname field:session_id)
    name = session_id
    try:
        doc = frappe.get_doc("USSD Session", name)
    except frappe.DoesNotExistError:
        doc = frappe.get_doc({
            "doctype": "USSD Session",
            "session_id": session_id,
            "phone_number": phone_number,
            "provider": provider,
            "service_code": service_code,
            "active": 1,
            "step_count": 0,
        })
        doc.insert(ignore_permissions=True)
    # Update last activity on every hit
    try:
        doc.db_set("last_activity", now(), update_modified=True)
    except Exception:
        pass
    return doc.name


def _update_session_progress(session_name: str, conversation: str, timeout_seconds: int, deactivate: bool = False):
    try:
        step = frappe.db.get_value("USSD Session", session_name, "step_count") or 0
        updates = {
            "conversation": conversation,
            "step_count": int(step) + 1,
            "last_activity": now(),
            "expires_at": add_to_date(now(), seconds=timeout_seconds or 120),
        }
        if deactivate:
            updates["active"] = 0
        frappe.db.set_value("USSD Session", session_name, updates, update_modified=True)
    except Exception:
        pass




def _get_session_state(session_name: str) -> dict:
    try:
        raw = frappe.db.get_value("USSD Session", session_name, "state_json") or "{}"
        state = json.loads(raw)
        return state if isinstance(state, dict) else {}
    except Exception:
        return {}


def _set_session_state(session_name: str, state: dict):
    try:
        frappe.db.set_value("USSD Session", session_name, "state_json", json.dumps(state or {}), update_modified=True)
    except Exception:
        pass


def _initial_menu_text() -> str:
    # Prefer explicit binding in Social Media Settings; fallback to is_default
    try:
        bound_name = None
        try:
            settings = frappe.get_single("Social Media Settings")
            bound_name = (getattr(settings, "ussd_default_menu", "") or "").strip()
        except Exception:
            bound_name = None

        default_menu = None
        if bound_name:
            recs = frappe.get_all(
                "USSD Menu", filters={"name": bound_name, "enabled": 1}, fields=["name", "title"], limit=1
            )
            if recs:
                default_menu = recs[0]
        if not default_menu:
            recs = frappe.get_all(
                "USSD Menu", filters={"is_default": 1, "enabled": 1}, fields=["name", "title"], limit=1
            )
            if recs:
                default_menu = recs[0]
        if default_menu:
            menu_name = default_menu["name"]
            title = default_menu.get("title") or "WCFCB"
            items = frappe.get_all(
                "USSD Menu Item",
                filters={"parent": menu_name, "enabled": 1},
                fields=["option_number", "option_text"],
                order_by="idx asc",
            )
            lines = [title]
            for it in items:
                num = it.get("option_number")
                text = it.get("option_text") or ""
                if num:
                    lines.append(f"{num}. {text}")
            lines.append("0. Exit")
            built = "\n".join([ln for ln in lines if ln])
            return built or "Welcome to WCFCB\n1. Chat with WorkCom\n0. Exit"
    except Exception:
        pass
    return "Welcome to WCFCB\n1. Chat with WorkCom\n0. Exit"


def _render_menu(menu_name: str | None = None) -> str:
    try:
        menu = None
        if menu_name:
            recs = frappe.get_all("USSD Menu", filters={"name": menu_name, "enabled": 1}, fields=["name", "title"], limit=1)
            if recs:
                menu = recs[0]
        if not menu:
            bound_name = None
            try:
                settings = frappe.get_single("Social Media Settings")
                bound_name = (getattr(settings, "ussd_default_menu", "") or "").strip()
            except Exception:
                bound_name = None
            if bound_name:
                recs = frappe.get_all("USSD Menu", filters={"name": bound_name, "enabled": 1}, fields=["name", "title"], limit=1)
                if recs:
                    menu = recs[0]
        if not menu:
            recs = frappe.get_all("USSD Menu", filters={"is_default": 1, "enabled": 1}, fields=["name", "title"], limit=1)
            if recs:
                menu = recs[0]
        if not menu:
            return _initial_menu_text()
        items = frappe.get_all(
            "USSD Menu Item",
            filters={"parent": menu["name"], "enabled": 1},
            fields=["option_number", "option_text"],
            order_by="idx asc",
        )
        lines = [menu.get("title") or "WCFCB"]
        for it in items:
            num = it.get("option_number")
            text = it.get("option_text") or ""
            if num:
                lines.append(f"{num}. {text}")
        lines.append("0. Exit")
        return "\n".join([ln for ln in lines if ln])



    except Exception:
        return _initial_menu_text()


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def ussd_webhook():
    # Many providers POST form-encoded data: sessionId, phoneNumber, serviceCode, text
    form = frappe.local.form_dict or {}
    session_id = (form.get("sessionId") or form.get("session_id") or form.get("session") or "").strip()
    phone_number = (form.get("phoneNumber") or form.get("msisdn") or form.get("from") or "").strip()
    service_code = (form.get("serviceCode") or form.get("shortCode") or form.get("to") or "").strip()
    text = (form.get("text") or form.get("message") or "").strip()

    if not session_id or not phone_number:
        frappe.log_error(json.dumps(form, ensure_ascii=False), "USSD webhook missing sessionId/phoneNumber")
        return "END Invalid request"

    # Extract the current user input (last segment after *)
    user_input = text.split("*")[-1] if text else ""



    lower_input = (user_input or "").strip().lower()

    # Initialize settings and platform helper
    integration = USSDIntegration()


    creds = integration.credentials or {}

    # Enforce channel enablement
    try:
        if not int(creds.get("ussd_enabled") or 0):
            return "END USSD is disabled"
    except Exception:
        pass

    # Optional shared-secret validation (header X-USSD-Secret or ?secret=token)
    webhook_secret = (creds.get("ussd_webhook_secret") or "").strip()
    if webhook_secret:
        provided_secret = (frappe.get_request_header("X-USSD-Secret") or form.get("secret") or form.get("token") or "").strip()
        if provided_secret != webhook_secret:
            frappe.log_error(json.dumps({"form": form, "ip": frappe.local.request_ip}, ensure_ascii=False), "USSD Security: Unauthorized")
            return "END Unauthorized"

    timeout_seconds = int(creds.get("ussd_session_timeout_seconds") or 120)

    # Session doc lifecycle
    session_name = _get_or_create_session(session_id, phone_number, creds.get("ussd_provider"), service_code)

    # Ensure we have a conversation in the unified inbox
    platform_data = {
        "conversation_id": phone_number,  # stable per-caller for USSD
        "customer_name": phone_number,
        "customer_phone": phone_number,
        "customer_platform_id": phone_number,
        "provider": creds.get("ussd_provider"),
        "service_code": service_code,
        "session_id": session_id,
    }
    conversation_name = integration.create_unified_inbox_conversation(platform_data) or None

    # Establish session state and show default menu on first screen
    state = _get_session_state(session_name)
    if not text:
        _set_session_state(session_name, {"mode": "menu"})
        _update_session_progress(session_name, conversation_name, timeout_seconds)
        return f"CON {_truncate_for_ussd(_render_menu(None), add_exit_hint=False)}"


    # If user is navigating menu, process selection without invoking AI
    if (state or {}).get("mode") == "menu":
        # Determine current menu
        menu_name = (state or {}).get("current_menu")
        try:
            if not menu_name:
                try:
                    settings = frappe.get_single("Social Media Settings")
                    bound = (getattr(settings, "ussd_default_menu", "") or "").strip()
                except Exception:
                    bound = None
                if bound:
                    menu_name = bound
                if not menu_name:
                    recs = frappe.get_all("USSD Menu", filters={"is_default": 1, "enabled": 1}, fields=["name"], limit=1)
                    menu_name = recs[0]["name"] if recs else None
        except Exception:
            menu_name = None

        # Parse numeric selection
        try:
            sel = int(user_input)
        except Exception:
            sel = None

        if sel is None:
            _update_session_progress(session_name, conversation_name, timeout_seconds)
            msg = 'Please choose a valid option.\n' + _render_menu(menu_name)
            return "CON " + _truncate_for_ussd(msg, add_exit_hint=False)

        # Fetch item for this selection
        item = None
        try:
            items = frappe.get_all(
                "USSD Menu Item",
                filters={"parent": menu_name, "enabled": 1, "option_number": sel},
                fields=["option_number", "option_text", "action_type", "target_menu"],
                limit=1,
            )
            if items:
                item = items[0]
        except Exception:
            item = None

        if not item:
            _update_session_progress(session_name, conversation_name, timeout_seconds)
            msg = 'Please choose a valid option.\n' + _render_menu(menu_name)
            return "CON " + _truncate_for_ussd(msg, add_exit_hint=False)

        action = (item.get('action_type') or 'Chat AI').strip()
        if action == "Next Menu":
            next_menu = item.get("target_menu")
            new_state = {"mode": "menu", "current_menu": next_menu}
            _set_session_state(session_name, new_state)
            _update_session_progress(session_name, conversation_name, timeout_seconds)
            return f"CON {_truncate_for_ussd(_render_menu(next_menu), add_exit_hint=False)}"
        elif action == "Exit":
            farewell = _truncate_for_ussd("Thank you for using our service.", add_exit_hint=False)
            _update_session_progress(session_name, conversation_name, timeout_seconds, deactivate=True)
            try:
                frappe.db.set_value("Unified Inbox Conversation", conversation_name, {"status": "Resolved"}, update_modified=True)
            except Exception:
                pass
            return f"END {farewell}"
        else:  # Chat AI or Back -> Chat AI by default
            onboarding = "You're now chatting with WorkCom. Ask me anything about WCFCB services."
            try:
                integration.create_unified_inbox_message(conversation_name, {
                    "message_id": f"{session_id}:menu_out:{now()}",
                    "direction": "Outbound",
                    "message_type": "text",
                    "content": onboarding,
                    "sender_name": "USSD Bot",
                    "sender_id": "ussd_bot",
                    "sender_platform_id": "ussd_bot",
                    "timestamp": now(),
                    "metadata": {"menu": menu_name or "default", "note": "entering_chat"}
                })
            except Exception:
                pass
            _set_session_state(session_name, {"mode": "chat"})
            _update_session_progress(session_name, conversation_name, timeout_seconds)
            return f"CON {_truncate_for_ussd(onboarding, add_exit_hint=True)}"

    if not conversation_name:
        return "END Service unavailable. Please try again later."

    # Exit keywords: end immediately
    if lower_input in {"0", "exit"}:
        farewell = _truncate_for_ussd("Thank you for using our service.", add_exit_hint=False)
        # Record inbound
        integration.create_unified_inbox_message(conversation_name, {
            "message_id": f"{session_id}:in:{now()}",
            "direction": "Inbound",
            "message_type": "text",
            "content": user_input or "0",
            "sender_name": phone_number,
            "sender_id": phone_number,
            "sender_platform_id": phone_number,
            "timestamp": now(),
            "metadata": {"session_id": session_id, "service_code": service_code}
        })
        # Record outbound farewell
        integration.create_unified_inbox_message(conversation_name, {
            "message_id": f"{session_id}:out:{now()}",
            "direction": "Outbound",
            "message_type": "text",
            "content": farewell,
            "sender_name": "USSD Bot",
            "sender_id": "ussd_bot",
            "sender_platform_id": "ussd_bot",
            "timestamp": now(),
            "metadata": {"ended_by": "user_exit"}
        })
        try:
            frappe.db.set_value("Unified Inbox Conversation", conversation_name, {"status": "Resolved"}, update_modified=True)
        except Exception:
            pass
        _update_session_progress(session_name, conversation_name, timeout_seconds, deactivate=True)
        return f"END {farewell}"

    # Create inbound message first (dedup handled inside helper)
    inbound_msg_id = integration.create_unified_inbox_message(conversation_name, {
        "message_id": f"{session_id}:{now()}",
        "direction": "Inbound",
        "message_type": "text",
        "content": user_input,
        "sender_name": phone_number,
        "sender_id": phone_number,
        "sender_platform_id": phone_number,
        "timestamp": now(),
        "metadata": {"session_id": session_id, "full_text": text, "service_code": service_code}
    })



    # Fall back safety
    if not inbound_msg_id:
        _update_session_progress(session_name, conversation_name, timeout_seconds)
        return "CON Please try again.\n0. Exit"

    # Run the normal AI pipeline synchronously so survey logic and analytics apply
    try:
        import importlib
        inbox_api = importlib.import_module("assistant_crm.api.unified_inbox_api")
        inbox_api.process_message_with_ai(inbound_msg_id)
    except Exception as e:
        frappe.log_error(f"USSD AI processing error: {str(e)}", "USSD Integration")

    # After processing, fetch the latest outbound AI message in this conversation
    try:
        latest = frappe.get_all(
            "Unified Inbox Message",
            filters={
                "conversation": conversation_name,
                "platform": "USSD",
                "direction": "Outbound",
            },
            fields=["name", "message_content", "timestamp"],
            order_by="timestamp desc",
            limit=1,
        )
        reply_text = (latest[0].get("message_content") if latest else "") or ""
    except Exception:
        reply_text = ""

    # If the conversation was resolved during survey completion, end the USSD session
    try:
        status = frappe.db.get_value("Unified Inbox Conversation", conversation_name, "status") or ""
    except Exception:
        status = ""

    # Format screen with proper truncation, append exit hint only if continuing
    end_session = status.strip() in {"Resolved", "Closed"}
    formatted = _truncate_for_ussd(reply_text or "How can I help you today?", add_exit_hint=not end_session)

    _update_session_progress(session_name, conversation_name, timeout_seconds, deactivate=end_session)

    if end_session:
        return f"END {formatted}"
    return f"CON {formatted}"




def cleanup_expired_ussd_sessions() -> int:
    """Deactivate USSD sessions that have passed their expires_at timestamp."""
    try:
        expired = frappe.get_all(
            "USSD Session",
            filters=[["active", "=", 1], ["expires_at", "<", now()]],
            pluck="name",
        )
        for name in expired:
            try:
                frappe.db.set_value("USSD Session", name, "active", 0, update_modified=False)
            except Exception:
                pass
        if expired:
            frappe.logger().info({"ussd_session_cleanup": len(expired)})
        return len(expired or [])
    except Exception as e:
        frappe.log_error(f"USSD session cleanup error: {str(e)}", "USSD Session Cleanup")
        return 0

