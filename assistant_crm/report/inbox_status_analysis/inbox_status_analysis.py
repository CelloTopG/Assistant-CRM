"""
Inbox Status Analysis - Native ERPNext Script Report

Comprehensive inbox performance analysis using native ERPNext doctypes:
- Issue: For service desk tickets
- Unified Inbox Conversation: For omnichannel conversations
- Unified Inbox Message: For message-level metrics

Includes Antoine AI integration for intelligent insights.
"""

import json
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe.utils import getdate, get_datetime, add_days, add_months, get_first_day, get_last_day, now_datetime
from assistant_crm.report.report_utils import get_period_dates

# Supported platforms for channel analysis
PLATFORMS = [
    "WhatsApp", "Facebook", "Instagram", "Telegram", "Twitter", "Tawk.to",
    "Website Chat", "Email", "Phone", "LinkedIn", "USSD", "YouTube"
]


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple:
    """Main entry point for Script Report."""
    filters = frappe._dict(filters or {})

    # Ensure date filters
    get_period_dates(filters)

    columns = get_columns()
    data, summary = get_data(filters)
    chart = get_chart_data(data, filters)
    report_summary = get_report_summary(summary)

    return columns, data, None, chart, report_summary, False


def get_columns() -> List[Dict[str, Any]]:
    """Define report columns for inbox metrics by platform."""
    return [
        {"fieldname": "platform", "label": "Platform", "fieldtype": "Data", "width": 140},
        {"fieldname": "total_conversations", "label": "Conversations", "fieldtype": "Int", "width": 110},
        {"fieldname": "total_messages", "label": "Messages", "fieldtype": "Int", "width": 100},
        {"fieldname": "inbound_count", "label": "Inbound", "fieldtype": "Int", "width": 90},
        {"fieldname": "outbound_count", "label": "Outbound", "fieldtype": "Int", "width": 90},
        {"fieldname": "ai_first_responses", "label": "AI First", "fieldtype": "Int", "width": 80},
        {"fieldname": "ai_handled", "label": "AI Handled", "fieldtype": "Int", "width": 90},
        {"fieldname": "escalated", "label": "Escalated", "fieldtype": "Int", "width": 90},
        {"fieldname": "resolved", "label": "Resolved", "fieldtype": "Int", "width": 90},
        {"fieldname": "open_count", "label": "Open", "fieldtype": "Int", "width": 70},
        {"fieldname": "avg_frt_min", "label": "Avg FRT (min)", "fieldtype": "Float", "precision": 1, "width": 110},
        {"fieldname": "p90_frt_min", "label": "P90 FRT (min)", "fieldtype": "Float", "precision": 1, "width": 110},
        {"fieldname": "avg_resolution_hrs", "label": "Avg Res (hrs)", "fieldtype": "Float", "precision": 1, "width": 110},
        {"fieldname": "linked_issues", "label": "Linked Issues", "fieldtype": "Int", "width": 100},
    ]


def get_data(filters: frappe._dict) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch and aggregate inbox data from Unified Inbox Conversation and Message."""
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    platform_filter = (filters.get("platform") or "").strip() or None
    status_filter = (filters.get("status") or "").strip() or None
    agent_filter = (filters.get("assigned_agent") or "").strip() or None
    ai_mode_filter = (filters.get("ai_mode") or "").strip() or None

    # Get conversations in date range
    conv_filters = {"creation": ["between", [df, dt]]}
    if platform_filter:
        conv_filters["platform"] = platform_filter
    if status_filter:
        conv_filters["status"] = status_filter
    if agent_filter:
        conv_filters["assigned_agent"] = agent_filter
    if ai_mode_filter:
        conv_filters["ai_mode"] = ai_mode_filter

    convs = frappe.get_all(
        "Unified Inbox Conversation",
        filters=conv_filters,
        fields=[
            "name", "platform", "status", "priority", "escalated_at",
            "ai_handled", "ai_mode", "creation_time", "last_message_time",
            "assigned_agent", "custom_issue_id"
        ],
        order_by="creation asc",
        limit=10000,
    ) or []

    # Get messages in date range
    msgs = frappe.get_all(
        "Unified Inbox Message",
        filters={"timestamp": ["between", [df, dt]]},
        fields=["platform", "direction", "conversation", "processed_by_ai", "handled_by_agent", "timestamp"],
        limit=50000,
    ) or []

    # Get linked issues count
    issues = frappe.get_all(
        "Issue",
        filters={"creation": ["between", [df, dt]]},
        fields=["name", "custom_conversation_id"],
        limit=10000,
    ) or []

    # Build platform aggregation
    platform_data = _aggregate_by_platform(convs, msgs, issues, df, dt)

    # Calculate totals for summary
    totals = _calculate_totals(platform_data)

    # Convert to list and sort
    data = sorted(platform_data.values(), key=lambda r: -(r.get("total_conversations", 0) or 0))

    return data, totals


def _aggregate_by_platform(convs, msgs, issues, df, dt) -> Dict[str, Dict[str, Any]]:
    """Aggregate metrics by platform."""
    result: Dict[str, Dict[str, Any]] = {}

    # Initialize all known platforms
    for plat in PLATFORMS:
        result[plat] = _new_platform_bucket(plat)

    # Conversation aggregation
    conv_names = {c.get("name"): c for c in convs}
    for c in convs:
        plat = c.get("platform") or "Unknown"
        if plat not in result:
            result[plat] = _new_platform_bucket(plat)
        bucket = result[plat]

        bucket["total_conversations"] += 1
        status = (c.get("status") or "").lower()
        if status in {"resolved", "closed"}:
            bucket["resolved"] += 1
        else:
            bucket["open_count"] += 1
        if c.get("escalated_at"):
            bucket["escalated"] += 1
        if c.get("ai_handled"):
            bucket["ai_handled"] += 1
        if c.get("custom_issue_id"):
            bucket["linked_issues"] += 1

    # Message aggregation and FRT calculation
    conv_msgs: Dict[str, List[Dict]] = {}
    for m in msgs:
        conv = m.get("conversation")
        if conv not in conv_msgs:
            conv_msgs[conv] = []
        conv_msgs[conv].append(m)

        plat = m.get("platform") or "Unknown"
        if plat not in result:
            result[plat] = _new_platform_bucket(plat)
        bucket = result[plat]

        bucket["total_messages"] += 1
        direction = (m.get("direction") or "").lower()
        if direction == "inbound":
            bucket["inbound_count"] += 1
        elif direction == "outbound":
            bucket["outbound_count"] += 1

    # Calculate FRT for each conversation
    for conv_name, conv_data in conv_names.items():
        plat = conv_data.get("platform") or "Unknown"
        if plat not in result:
            continue
        bucket = result[plat]

        msgs_list = sorted(conv_msgs.get(conv_name, []), key=lambda x: x.get("timestamp") or "")
        first_inbound = next((m for m in msgs_list if (m.get("direction") or "").lower() == "inbound"), None)
        first_outbound = next((m for m in msgs_list if (m.get("direction") or "").lower() == "outbound"), None)

        if first_inbound and first_outbound:
            try:
                fi_ts = get_datetime(first_inbound.get("timestamp"))
                fo_ts = get_datetime(first_outbound.get("timestamp"))
                frt_min = max(0.0, (fo_ts - fi_ts).total_seconds() / 60.0)
                bucket["frt_values"].append(frt_min)

                # Check if first response was AI
                if first_outbound.get("processed_by_ai") and not first_outbound.get("handled_by_agent"):
                    bucket["ai_first_responses"] += 1
            except Exception:
                pass

        # Resolution time for resolved conversations
        status = (conv_data.get("status") or "").lower()
        if status in {"resolved", "closed"} and first_inbound and conv_data.get("last_message_time"):
            try:
                end_ts = get_datetime(conv_data.get("last_message_time"))
                start_ts = get_datetime(first_inbound.get("timestamp"))
                res_hrs = max(0.0, (end_ts - start_ts).total_seconds() / 3600.0)
                bucket["resolution_values"].append(res_hrs)
            except Exception:
                pass

    # Count issues linked to conversations
    for issue in issues:
        conv_link = issue.get("custom_conversation_id")
        if conv_link and conv_link in conv_names:
            plat = conv_names[conv_link].get("platform") or "Unknown"
            if plat in result:
                result[plat]["linked_issues"] += 1

    # Calculate averages and percentiles
    for plat, bucket in result.items():
        bucket["avg_frt_min"] = _avg(bucket["frt_values"])
        bucket["p90_frt_min"] = _percentile(bucket["frt_values"], 90)
        bucket["avg_resolution_hrs"] = _avg(bucket["resolution_values"])
        # Clean up internal arrays
        del bucket["frt_values"]
        del bucket["resolution_values"]

    # Remove platforms with no data
    result = {k: v for k, v in result.items() if v.get("total_conversations", 0) > 0 or v.get("total_messages", 0) > 0}

    return result


def _new_platform_bucket(platform: str) -> Dict[str, Any]:
    """Create empty bucket for platform aggregation."""
    return {
        "platform": platform,
        "total_conversations": 0,
        "total_messages": 0,
        "inbound_count": 0,
        "outbound_count": 0,
        "ai_first_responses": 0,
        "ai_handled": 0,
        "escalated": 0,
        "resolved": 0,
        "open_count": 0,
        "linked_issues": 0,
        "frt_values": [],
        "resolution_values": [],
        "avg_frt_min": 0.0,
        "p90_frt_min": 0.0,
        "avg_resolution_hrs": 0.0,
    }


def _calculate_totals(platform_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate summary totals across all platforms."""
    totals = {
        "total_conversations": 0,
        "total_messages": 0,
        "inbound_count": 0,
        "outbound_count": 0,
        "ai_first_responses": 0,
        "ai_handled": 0,
        "escalated": 0,
        "resolved": 0,
        "open_count": 0,
        "linked_issues": 0,
        "all_frt_values": [],
        "all_resolution_values": [],
    }

    for plat, data in platform_data.items():
        totals["total_conversations"] += data.get("total_conversations", 0)
        totals["total_messages"] += data.get("total_messages", 0)
        totals["inbound_count"] += data.get("inbound_count", 0)
        totals["outbound_count"] += data.get("outbound_count", 0)
        totals["ai_first_responses"] += data.get("ai_first_responses", 0)
        totals["ai_handled"] += data.get("ai_handled", 0)
        totals["escalated"] += data.get("escalated", 0)
        totals["resolved"] += data.get("resolved", 0)
        totals["open_count"] += data.get("open_count", 0)
        totals["linked_issues"] += data.get("linked_issues", 0)

    return totals


def _avg(values: List[float]) -> float:
    """Calculate average of a list."""
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def _percentile(values: List[float], p: float) -> float:
    """Calculate percentile of a list."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = max(0, min(len(sorted_vals) - 1, int(round((p / 100.0) * (len(sorted_vals) - 1)))))
    return round(sorted_vals[k], 1)


def get_chart_data(data: List[Dict[str, Any]], filters: frappe._dict) -> Dict[str, Any]:
    """Build default chart showing message volume by platform."""
    if not data:
        return {}

    labels = [r.get("platform") or "" for r in data[:12]]
    inbound_vals = [int(r.get("inbound_count", 0) or 0) for r in data[:12]]
    outbound_vals = [int(r.get("outbound_count", 0) or 0) for r in data[:12]]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Inbound", "values": inbound_vals},
                {"name": "Outbound", "values": outbound_vals},
            ],
        },
        "type": "bar",
        "barOptions": {"stacked": True},
        "colors": ["#5e64ff", "#28a745"],
    }


def get_report_summary(totals: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build report summary cards."""
    resolution_rate = 0.0
    total_conv = totals.get("total_conversations", 0)
    if total_conv:
        resolution_rate = (totals.get("resolved", 0) / total_conv) * 100.0

    ai_rate = 0.0
    if total_conv:
        ai_rate = (totals.get("ai_handled", 0) / total_conv) * 100.0

    resolution_indicator = "green" if resolution_rate >= 80 else ("orange" if resolution_rate >= 60 else "red")
    ai_indicator = "blue" if ai_rate >= 50 else "grey"

    return [
        {"value": totals.get("total_conversations", 0), "label": "Conversations", "datatype": "Int", "indicator": "blue"},
        {"value": totals.get("total_messages", 0), "label": "Messages", "datatype": "Int"},
        {"value": totals.get("inbound_count", 0), "label": "Inbound", "datatype": "Int", "indicator": "orange"},
        {"value": totals.get("outbound_count", 0), "label": "Outbound", "datatype": "Int", "indicator": "green"},
        {"value": totals.get("ai_first_responses", 0), "label": "AI First Responses", "datatype": "Int", "indicator": "blue"},
        {"value": totals.get("escalated", 0), "label": "Escalated", "datatype": "Int", "indicator": "red"},
        {"value": round(resolution_rate, 1), "label": "Resolution Rate %", "datatype": "Percent", "indicator": resolution_indicator},
        {"value": round(ai_rate, 1), "label": "AI Handling Rate %", "datatype": "Percent", "indicator": ai_indicator},
    ]


# ----------------------
# AI Integration
# ----------------------

@frappe.whitelist()
def get_ai_insights(filters: str, query: str) -> Dict[str, Any]:
    """Return Antoine-style insights for Inbox Status Analysis report."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})

    # Ensure dates
    if not filters.get("date_from") or not filters.get("date_to"):
        filters.date_to = getdate()
        filters.date_from = add_days(filters.date_to, -6)

    # Get current data
    data, totals = get_data(filters)

    # Build context for AI
    context = {
        "window": {
            "period_type": filters.get("period_type", "Weekly"),
            "from": str(filters.date_from),
            "to": str(filters.date_to),
        },
        "current": {
            "total_conversations": totals.get("total_conversations", 0),
            "total_messages": totals.get("total_messages", 0),
            "inbound_messages": totals.get("inbound_count", 0),
            "outbound_messages": totals.get("outbound_count", 0),
            "ai_first_responses": totals.get("ai_first_responses", 0),
            "ai_handled_conversations": totals.get("ai_handled", 0),
            "escalated_conversations": totals.get("escalated", 0),
            "resolved_conversations": totals.get("resolved", 0),
            "open_conversations": totals.get("open_count", 0),
            "linked_issues": totals.get("linked_issues", 0),
            "platform_breakdown": data[:20],  # Limit for context size
        },
        "history": _get_historical_data(filters),
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService
        ai = EnhancedAIService()
        answer = ai.generate_inbox_status_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Inbox Status Analysis AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure Antoine/OpenAI settings in Enhanced AI Settings."
            )
        }


def _get_historical_data(filters: frappe._dict) -> List[Dict[str, Any]]:
    """Get historical inbox status reports for trend comparison."""
    try:
        history = frappe.get_all(
            "Inbox Status Report",
            filters={"period_type": filters.get("period_type", "Weekly")},
            fields=[
                "name", "date_from", "date_to", "total_conversations", "total_messages",
                "inbound_count", "outbound_count", "escalated_count", "resolved_count",
                "ai_first_response_count", "ai_handled_conversations",
                "avg_first_response_minutes", "p90_first_response_minutes",
            ],
            order_by="date_from desc",
            limit=5,
        )
        return history or []
    except Exception:
        return []


# ----------------------
# Additional Chart Functions
# ----------------------

@frappe.whitelist()
def get_platform_distribution_chart(filters: str) -> Dict[str, Any]:
    """Get bar chart showing conversation distribution by platform."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    if not filters.get("date_from") or not filters.get("date_to"):
        filters.date_to = getdate()
        filters.date_from = add_days(filters.date_to, -6)

    data, _ = get_data(filters)
    labels = [r.get("platform") or "" for r in data[:10]]
    values = [int(r.get("total_conversations", 0) or 0) for r in data[:10]]

    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": "Conversations", "values": values}],
        },
        "type": "bar",
        "colors": ["#5e64ff"],
    }


@frappe.whitelist()
def get_ai_vs_human_chart(filters: str) -> Dict[str, Any]:
    """Get chart comparing AI vs human handling."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    if not filters.get("date_from") or not filters.get("date_to"):
        filters.date_to = getdate()
        filters.date_from = add_days(filters.date_to, -6)

    data, totals = get_data(filters)
    ai_handled = totals.get("ai_handled", 0)
    human_handled = totals.get("total_conversations", 0) - ai_handled

    return {
        "data": {
            "labels": ["AI Handled", "Human Handled"],
            "datasets": [{"name": "Conversations", "values": [ai_handled, max(0, human_handled)]}],
        },
        "type": "bar",
        "colors": ["#5e64ff", "#28a745"],
    }


@frappe.whitelist()
def get_status_distribution_chart(filters: str) -> Dict[str, Any]:
    """Get chart showing open/resolved/escalated status."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    if not filters.get("date_from") or not filters.get("date_to"):
        filters.date_to = getdate()
        filters.date_from = add_days(filters.date_to, -6)

    data, totals = get_data(filters)

    return {
        "data": {
            "labels": ["Open", "Resolved", "Escalated"],
            "datasets": [{"name": "Conversations", "values": [
                totals.get("open_count", 0),
                totals.get("resolved", 0),
                totals.get("escalated", 0),
            ]}],
        },
        "type": "bar",
        "colors": ["#ffc107", "#28a745", "#dc3545"],
    }


@frappe.whitelist()
def get_trend_chart(filters: str, weeks: int = 8) -> Dict[str, Any]:
    """Get trend chart for the last N weeks."""
    weeks = int(weeks)
    labels = []
    conv_vals = []
    msg_vals = []
    ai_vals = []
    anchor = getdate()

    for i in range(weeks - 1, -1, -1):
        end = add_days(anchor, -7 * i)
        start = add_days(end, -6)
        labels.append(f"{start.strftime('%d %b')}-{end.strftime('%d %b')}")

        conv_count = frappe.db.count("Unified Inbox Conversation", filters={"creation": ["between", [start, end]]})
        conv_vals.append(int(conv_count or 0))

        msg_count = frappe.db.count("Unified Inbox Message", filters={"timestamp": ["between", [start, end]]})
        msg_vals.append(int(msg_count or 0))

        ai_count = frappe.db.count("Unified Inbox Conversation", filters={
            "creation": ["between", [start, end]],
            "ai_handled": 1
        })
        ai_vals.append(int(ai_count or 0))

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Conversations", "values": conv_vals},
                {"name": "AI Handled", "values": ai_vals},
            ],
        },
        "type": "line",
        "colors": ["#5e64ff", "#28a745"],
    }


@frappe.whitelist()
def get_response_time_chart(filters: str) -> Dict[str, Any]:
    """Get chart showing FRT by platform."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    if not filters.get("date_from") or not filters.get("date_to"):
        filters.date_to = getdate()
        filters.date_from = add_days(filters.date_to, -6)

    data, _ = get_data(filters)
    # Filter platforms with FRT data and sort by FRT
    with_frt = [r for r in data if (r.get("avg_frt_min") or 0) > 0]
    sorted_data = sorted(with_frt, key=lambda r: r.get("avg_frt_min", 0))[:10]

    labels = [r.get("platform") or "" for r in sorted_data]
    avg_vals = [float(r.get("avg_frt_min", 0) or 0) for r in sorted_data]
    p90_vals = [float(r.get("p90_frt_min", 0) or 0) for r in sorted_data]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Avg FRT (min)", "values": avg_vals},
                {"name": "P90 FRT (min)", "values": p90_vals},
            ],
        },
        "type": "bar",
        "colors": ["#17a2b8", "#ffc107"],
    }

