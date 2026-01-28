#!/usr/bin/env python3
"""
Adapter layer for Unified Inbox AI processing
--------------------------------------------
Provides process_unified_chat(message, user_id, session_id, platform, context)
expected by unified_inbox_api.process_message_with_ai, delegating to the
existing simplified chat API and mapping the return format.

This is a minimal, surgical compatibility shim. No inbound path changes.
"""
from typing import Any, Dict, Optional

try:
    # Use the simplified single-dataflow chat API already present
    from assistant_crm.api.simplified_chat import get_simplified_chat_api
except Exception as e:  # pragma: no cover
    get_simplified_chat_api = None
    _import_error = e  # for diagnostics


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except Exception:
        return default


def process_unified_chat(
    message: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    platform: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compatibility function used by unified_inbox_api.process_message_with_ai.

    Delegates to SimplifiedChatAPI and adapts the response to:
      {"response": str, "confidence": float, ...}
    """
    # Guard against missing adapter dependency
    if get_simplified_chat_api is None:
        # Return low confidence so the pipeline can escalate cleanly
        return {
            "response": "I'm sorry, I'm having trouble processing your request right now.",
            "confidence": 0.0,
            "error": f"Simplified chat API import failed: {_import_error}",
        }

    api = get_simplified_chat_api()
    # CRITICAL: pass through the stable session_id so SimplifiedChat can maintain
    # conversation memory and intent lock across turns (especially for webhooks)
    result = api.process_message(message or "", session_id=session_id) or {}

    # Extract best-effort response text
    response_text = (
        result.get("response")
        or result.get("message")
        or result.get("reply")
        or ""
    )

    # Confidence: prefer metadata.confidence; otherwise derive a sensible default
    meta: Dict[str, Any] = result.get("metadata") or {}
    confidence = meta.get("confidence")
    if confidence is None:
        # If the adapter reports success, provide a conservative default;
        # nudge higher when live data is used
        if result.get("success"):
            base = 0.75
            if meta.get("live_data_used"):
                base = 0.85
            confidence = _safe_float(meta.get("confidence", base), default=base)
        else:
            confidence = 0.0
    else:
        confidence = _safe_float(confidence, default=0.0)

    # Return in the shape expected by unified_inbox_api
    return {
        "response": response_text.strip(),
        "confidence": confidence,
        "metadata": meta,
        # Pass-through for potential future use/telemetry (non-breaking)
        "session_id": session_id,
        "user_id": user_id,
        "platform": platform,
        "context_used": bool(context),
    }

