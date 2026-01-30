# -*- coding: utf-8 -*-
# Copyright (c) 2026, WCFCB and contributors
# For license information, please see license.txt
"""
SLA Compliance Analysis - Native ERPNext Script Report

This report provides comprehensive SLA compliance analytics using
Unified Inbox Conversation and Escalation Workflow data.
Includes Antoine AI integration for insights.
"""

import json
from datetime import datetime, timedelta, time
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime


# Business Hours Configuration
BUSINESS_START = time(8, 0)
BUSINESS_END = time(17, 0)
BUSINESS_DAYS = {0, 1, 2, 3, 4}  # Mon-Fri

# Categories
CATEGORY_CLAIMS = "Claims"
CATEGORY_COMPLIANCE = "Compliance"
CATEGORY_GENERAL = "General"


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple:
    """Main report execution function.

    Returns:
        Tuple of (columns, data, message, chart, report_summary, skip_total_row)
    """
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data, summary_data = get_data(filters)
    chart = get_chart_data(summary_data)
    report_summary = get_report_summary(summary_data)

    return columns, data, None, chart, report_summary, False


def get_columns() -> List[Dict[str, Any]]:
    """Return column definitions for the report."""
    return [
        {
            "fieldname": "conversation",
            "label": _("Conversation"),
            "fieldtype": "Link",
            "options": "Unified Inbox Conversation",
            "width": 180,
        },
        {
            "fieldname": "platform",
            "label": _("Platform"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "priority",
            "label": _("Priority"),
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "fieldname": "branch",
            "label": _("Branch"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "role_bucket",
            "label": _("Role"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "category",
            "label": _("Category"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "frt_minutes",
            "label": _("FRT (min)"),
            "fieldtype": "Float",
            "width": 90,
            "precision": 1,
        },
        {
            "fieldname": "frt_label",
            "label": _("Response By"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "frt_status",
            "label": _("FRT Status"),
            "fieldtype": "Data",
            "width": 90,
        },
        {
            "fieldname": "rt_hours",
            "label": _("RT (hrs)"),
            "fieldtype": "Float",
            "width": 90,
            "precision": 2,
        },
        {
            "fieldname": "rt_status",
            "label": _("RT Status"),
            "fieldtype": "Data",
            "width": 90,
        },
        {
            "fieldname": "escalated",
            "label": _("Escalated"),
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "fieldname": "overall_status",
            "label": _("Overall SLA"),
            "fieldtype": "Data",
            "width": 100,
        },
    ]


def get_data(filters: Dict) -> Tuple[List[Dict], Dict]:
    """Fetch and process data for the report."""
    date_from = getdate(filters.get("date_from"))
    date_to = getdate(filters.get("date_to"))

    if not date_from or not date_to:
        today = getdate()
        first_this_month = today.replace(day=1)
        last_prev_month = first_this_month - timedelta(days=1)
        first_prev_month = last_prev_month.replace(day=1)
        date_from = first_prev_month
        date_to = last_prev_month

    # Build conversation filters
    conv_filters = {"creation": ["between", [date_from, date_to]]}

    if filters.get("channel") and filters.get("channel") != "All":
        conv_filters["platform"] = filters.get("channel")
    if filters.get("priority") and filters.get("priority") != "All":
        conv_filters["priority"] = filters.get("priority")

    conversations = frappe.get_all(
        "Unified Inbox Conversation",
        filters=conv_filters,
        fields=["name", "platform", "priority", "status", "assigned_agent",
                "creation", "modified", "last_message_time", "branch"],
        order_by="creation asc",
        limit=5000,
    )

    # Get escalations
    esc_index = _get_escalation_index(date_from, date_to)

    # Get SLA rules
    sla_rules = _get_sla_rules()

    # Process conversations
    rows: List[Dict] = []
    summary_data = _init_summary_data()

    branch_filter = (filters.get("branch_filter") or "").strip().lower()
    role_filter = (filters.get("role_filter") or "").strip().lower()

    for conv in conversations:
        row = _process_conversation(
            conv, esc_index, sla_rules, summary_data, branch_filter, role_filter
        )
        if row:
            rows.append(row)

    # Calculate final metrics
    _finalize_summary(summary_data)

    return rows, summary_data


def _init_summary_data() -> Dict:
    """Initialize summary data structure."""
    return {
        "frt_vals": [],
        "rt_vals": [],
        "frt_within": 0,
        "frt_total": 0,
        "rt_within": 0,
        "rt_total": 0,
        "total_items": 0,
        "within_sla": 0,
        "breached_sla": 0,
        "ai_first": 0,
        "escalations_total": 0,
        "escalations_within": 0,
        "escalations_breached": 0,
        "branch_stats": {},
        "role_stats": {},
        "cat_stats": {
            CATEGORY_CLAIMS: {"within": 0, "breached": 0},
            CATEGORY_COMPLIANCE: {"within": 0, "breached": 0},
            CATEGORY_GENERAL: {"within": 0, "breached": 0},
        },
    }


def _finalize_summary(summary_data: Dict) -> None:
    """Calculate final KPIs from accumulated data."""
    frt_vals = summary_data["frt_vals"]
    rt_vals = summary_data["rt_vals"]

    summary_data["frt_avg"] = sum(frt_vals) / len(frt_vals) if frt_vals else 0.0
    summary_data["rt_avg"] = sum(rt_vals) / len(rt_vals) if rt_vals else 0.0
    summary_data["frt_p90"] = _percentile(frt_vals, 90)
    summary_data["rt_p90"] = _percentile(rt_vals, 90)

    total = summary_data["total_items"]
    within = summary_data["within_sla"]
    frt_total = summary_data["frt_total"]
    rt_total = summary_data["rt_total"]

    summary_data["compliance_percent"] = (within / total * 100.0) if total else 0.0
    summary_data["frt_within_percent"] = (
        summary_data["frt_within"] / frt_total * 100.0
    ) if frt_total else 0.0
    summary_data["rt_within_percent"] = (
        summary_data["rt_within"] / rt_total * 100.0
    ) if rt_total else 0.0


def _percentile(values: List[float], p: float) -> float:
    """Calculate percentile of a list of values."""
    if not values:
        return 0.0
    arr = sorted(values)
    k = max(0, min(len(arr) - 1, int(round((p / 100.0) * (len(arr) - 1)))))
    return float(arr[k])



def _process_conversation(
    conv: Dict,
    esc_index: Dict,
    sla_rules: List[Dict],
    summary_data: Dict,
    branch_filter: str,
    role_filter: str,
) -> Optional[Dict]:
    """Process a single conversation and return row data."""
    branch = conv.get("branch") or _derive_branch(conv.get("assigned_agent"))
    role_bucket = _derive_role_bucket(conv.get("assigned_agent"))

    # Apply filters
    if branch_filter and branch_filter not in branch.lower():
        return None
    if role_filter and role_filter not in role_bucket.lower():
        return None

    sla = _match_sla(sla_rules, conv.get("platform"), conv.get("priority"))
    first_in, first_out, responder_type, inbound_text = _get_first_response(conv.get("name"))

    frt_minutes = None
    frt_ok = None

    if first_in and first_out:
        if sla and sla.get("business_hours_only"):
            frt_minutes = _business_minutes_between(first_in, first_out)
        else:
            frt_minutes = _minutes_between(first_in, first_out)

        summary_data["frt_vals"].append(frt_minutes)
        summary_data["frt_total"] += 1

        if sla and sla.get("first_response_time"):
            frt_ok = frt_minutes <= float(sla.get("first_response_time"))
            if frt_ok:
                summary_data["frt_within"] += 1

        if responder_type == "AI Response":
            summary_data["ai_first"] += 1

    # Resolution time
    rt_hours = None
    rt_ok = None
    if conv.get("status") in ("Resolved", "Closed"):
        end_ts = _get_resolution_time(conv)
        if end_ts and first_in:
            if sla and sla.get("business_hours_only"):
                minutes = _business_minutes_between(first_in, end_ts)
            else:
                minutes = _minutes_between(first_in, end_ts)
            rt_hours = minutes / 60.0
            summary_data["rt_vals"].append(rt_hours)
            summary_data["rt_total"] += 1
            if sla and sla.get("resolution_time"):
                rt_ok = rt_hours <= float(sla.get("resolution_time"))
                if rt_ok:
                    summary_data["rt_within"] += 1

    # Escalation handling
    esc_ok = None
    escs = esc_index.get(conv.get("name")) or []
    if escs:
        summary_data["escalations_total"] += 1
        e = sorted(escs, key=lambda x: x.get("escalation_date"))[0]
        if first_in:
            esc_dt = get_datetime(e.get("escalation_date"))
            if sla and sla.get("business_hours_only"):
                esc_minutes = _business_minutes_between(first_in, esc_dt)
            else:
                esc_minutes = _minutes_between(first_in, esc_dt)
            if sla and sla.get("escalation_time"):
                esc_ok = esc_minutes <= float(sla.get("escalation_time"))
                if esc_ok:
                    summary_data["escalations_within"] += 1
                else:
                    summary_data["escalations_breached"] += 1

    # Overall compliance
    applicable = [v for v in [frt_ok, rt_ok, esc_ok] if v is not None]
    if applicable:
        summary_data["total_items"] += 1
        if all(applicable):
            summary_data["within_sla"] += 1
            overall = "Within"
        else:
            summary_data["breached_sla"] += 1
            overall = "Breached"
    else:
        overall = "N/A"

    # Category classification
    category = _classify(inbound_text or "", branch)
    summary_data["cat_stats"].setdefault(category, {"within": 0, "breached": 0})
    if overall == "Within":
        summary_data["cat_stats"][category]["within"] += 1
    elif overall == "Breached":
        summary_data["cat_stats"][category]["breached"] += 1

    # Update branch/role stats
    for bucket, store_key in [(branch, "branch_stats"), (role_bucket, "role_stats")]:
        store = summary_data[store_key]
        store.setdefault(bucket, {"within": 0, "breached": 0})
        if overall == "Within":
            store[bucket]["within"] += 1
        elif overall == "Breached":
            store[bucket]["breached"] += 1

    return {
        "conversation": conv.get("name"),
        "platform": conv.get("platform"),
        "priority": conv.get("priority"),
        "branch": branch,
        "role_bucket": role_bucket,
        "category": category,
        "frt_minutes": round(frt_minutes, 1) if frt_minutes else None,
        "frt_label": responder_type,
        "frt_status": "Within" if frt_ok else ("Breached" if frt_ok is False else "N/A"),
        "rt_hours": round(rt_hours, 2) if rt_hours else None,
        "rt_status": "Within" if rt_ok else ("Breached" if rt_ok is False else "N/A"),
        "escalated": "Yes" if escs else "No",
        "overall_status": overall,
    }



def _get_escalation_index(date_from, date_to) -> Dict:
    """Build escalation index by conversation."""
    esc_index = {}
    try:
        esc_meta = frappe.get_meta("Escalation Workflow")
        has_conv = esc_meta and esc_meta.has_field("conversation")
    except Exception:
        has_conv = False

    if has_conv:
        escalations = frappe.get_all(
            "Escalation Workflow",
            filters={"escalation_date": ["between", [date_from, date_to]]},
            fields=["name", "conversation", "escalation_date"],
            limit=5000,
        )
        for e in escalations:
            esc_index.setdefault(e.conversation, []).append(e)

    return esc_index


def _get_sla_rules() -> List[Dict]:
    """Get active SLA configuration rules."""
    return frappe.get_all(
        "SLA Configuration",
        filters={"is_active": 1},
        fields=["name", "channel", "priority", "first_response_time",
                "resolution_time", "escalation_time", "business_hours_only"],
        limit=200,
    )


def _match_sla(sla_rules: List[Dict], channel: Optional[str], priority: Optional[str]) -> Optional[Dict]:
    """Match the most specific SLA rule for given channel and priority."""
    candidates = []
    for r in sla_rules:
        if r.get("channel") not in (None, "", "All") and channel and r.get("channel") != channel:
            continue
        if r.get("priority") not in (None, "", "All") and priority and r.get("priority") != priority:
            continue
        candidates.append(r)

    if not candidates:
        candidates = [r for r in sla_rules
                      if r.get("channel") in (None, "", "All")
                      and r.get("priority") in (None, "", "All")]

    return candidates[0] if candidates else None


def _derive_branch(user_id: Optional[str]) -> str:
    """Derive branch from user's branch or department field."""
    if not user_id:
        return "Unassigned"
    try:
        user_meta = frappe.get_meta("User")
        user = frappe.get_cached_doc("User", user_id)
        if user_meta.has_field("branch") and getattr(user, "branch", None):
            return user.branch
        if user_meta.has_field("department") and getattr(user, "department", None):
            return user.department
    except Exception:
        pass
    return "Unassigned"


def _derive_role_bucket(user_id: Optional[str]) -> str:
    """Derive role bucket from user's roles."""
    if not user_id:
        return "Other"
    try:
        roles = [r.role for r in frappe.get_all(
            "Has Role", filters={"parent": user_id}, fields=["role"], limit=100
        )]
        if any("Customer Service" in r for r in roles):
            return "Customer Service"
        if any("Corporate Affairs" in r for r in roles):
            return "Corporate Affairs"
    except Exception:
        pass
    return "Other"


def _classify(text: str, dept: Optional[str]) -> str:
    """Classify conversation into category."""
    try:
        from assistant_crm.assistant_crm.doctype.complaints_status_report.complaints_status_report import classify_complaint
        return classify_complaint(text=text or "", department=dept)
    except Exception:
        return CATEGORY_GENERAL


def _get_first_response(conversation_name: str) -> Tuple[Optional[datetime], Optional[datetime], Optional[str], Optional[str]]:
    """Get first inbound and outbound messages for a conversation."""
    msgs = frappe.get_all(
        "Unified Inbox Message",
        filters={"conversation": conversation_name},
        fields=["timestamp", "direction", "processed_by_ai", "ai_response",
                "handled_by_agent", "agent_response", "sender_name", "message_content"],
        order_by="timestamp asc",
        limit=500,
    )

    first_in_msg = next((m for m in msgs if (m.direction or "").lower() == "inbound"), None)
    first_in = get_datetime(first_in_msg.timestamp) if first_in_msg else None

    first_out_msg = next((m for m in msgs if (m.direction or "").lower() == "outbound"), None)
    first_out = get_datetime(first_out_msg.timestamp) if first_out_msg else None

    resp_type = None
    if first_out_msg:
        if getattr(first_out_msg, "handled_by_agent", 0) or getattr(first_out_msg, "agent_response", 0):
            resp_type = "Human Response"
        elif (getattr(first_out_msg, "processed_by_ai", 0) or
              getattr(first_out_msg, "ai_response", 0) or
              (first_out_msg.sender_name or "").lower().find("ai") >= 0):
            resp_type = "AI Response"
        else:
            resp_type = "Human Response"

    inbound_text = getattr(first_in_msg, "message_content", None) if first_in_msg else None
    return first_in, first_out, resp_type, inbound_text


def _get_resolution_time(conv: Dict) -> Optional[datetime]:
    """Get resolution timestamp for a conversation."""
    fields = ["resolved_at", "closed_at", "last_message_time", "modified"]
    for f in fields:
        val = conv.get(f)
        if val:
            try:
                return get_datetime(val)
            except Exception:
                continue
    return None


def _minutes_between(start: datetime, end: datetime) -> float:
    """Calculate minutes between two timestamps."""
    return max(0.0, (end - start).total_seconds() / 60.0)


def _business_minutes_between(start: datetime, end: datetime) -> float:
    """Calculate business minutes between two timestamps (Mon-Fri 08:00-17:00)."""
    if end <= start:
        return 0.0

    total = 0.0
    cur = start
    while cur.date() <= end.date():
        if cur.weekday() in BUSINESS_DAYS:
            day_start = datetime.combine(cur.date(), BUSINESS_START)
            day_end = datetime.combine(cur.date(), BUSINESS_END)
            s = max(cur, day_start)
            e = min(end, day_end)
            if e > s:
                total += (e - s).total_seconds() / 60.0
        cur = datetime.combine(cur.date() + timedelta(days=1), time(0, 0))

    return total



def get_chart_data(summary_data: Dict) -> Dict:
    """Generate chart data for the report."""
    cat_stats = summary_data.get("cat_stats", {})

    return {
        "type": "bar",
        "data": {
            "labels": [CATEGORY_CLAIMS, CATEGORY_COMPLIANCE, CATEGORY_GENERAL],
            "datasets": [
                {
                    "name": "Within SLA",
                    "values": [
                        cat_stats.get(CATEGORY_CLAIMS, {}).get("within", 0),
                        cat_stats.get(CATEGORY_COMPLIANCE, {}).get("within", 0),
                        cat_stats.get(CATEGORY_GENERAL, {}).get("within", 0),
                    ],
                },
                {
                    "name": "Breached",
                    "values": [
                        cat_stats.get(CATEGORY_CLAIMS, {}).get("breached", 0),
                        cat_stats.get(CATEGORY_COMPLIANCE, {}).get("breached", 0),
                        cat_stats.get(CATEGORY_GENERAL, {}).get("breached", 0),
                    ],
                },
            ],
        },
        "barOptions": {"stacked": 1},
        "colors": ["#28a745", "#dc3545"],
    }


def get_report_summary(summary_data: Dict) -> List[Dict]:
    """Generate report summary cards."""
    compliance = round(summary_data.get("compliance_percent", 0.0), 1)

    return [
        {
            "value": summary_data.get("total_items", 0),
            "label": _("Total Items"),
            "datatype": "Int",
        },
        {
            "value": summary_data.get("within_sla", 0),
            "label": _("Within SLA"),
            "datatype": "Int",
            "indicator": "green",
        },
        {
            "value": summary_data.get("breached_sla", 0),
            "label": _("Breached SLA"),
            "datatype": "Int",
            "indicator": "red",
        },
        {
            "value": compliance,
            "label": _("Compliance %"),
            "datatype": "Percent",
            "indicator": "green" if compliance >= 80 else ("yellow" if compliance >= 60 else "red"),
        },
        {
            "value": round(summary_data.get("frt_avg", 0.0), 1),
            "label": _("Avg FRT (min)"),
            "datatype": "Float",
        },
        {
            "value": round(summary_data.get("rt_avg", 0.0), 2),
            "label": _("Avg RT (hrs)"),
            "datatype": "Float",
        },
        {
            "value": summary_data.get("ai_first", 0),
            "label": _("AI First Responses"),
            "datatype": "Int",
            "indicator": "blue",
        },
        {
            "value": summary_data.get("escalations_total", 0),
            "label": _("Escalations"),
            "datatype": "Int",
            "indicator": "orange",
        },
    ]


# =====================
# Chart Endpoints
# =====================

@frappe.whitelist()
def get_overview_chart(filters: str) -> Dict:
    """Get overview chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters)
    _, summary_data = get_data(filters)
    return get_chart_data(summary_data)


@frappe.whitelist()
def get_branch_breakdown_chart(filters: str) -> Dict:
    """Get branch breakdown chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters)
    _, summary_data = get_data(filters)

    branch_stats = summary_data.get("branch_stats", {})
    labels = list(branch_stats.keys())[:12]

    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Within", "values": [branch_stats[k]["within"] for k in labels]},
                {"name": "Breached", "values": [branch_stats[k]["breached"] for k in labels]},
            ],
        },
        "barOptions": {"stacked": 1},
        "colors": ["#28a745", "#dc3545"],
    }


@frappe.whitelist()
def get_role_breakdown_chart(filters: str) -> Dict:
    """Get role breakdown chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters)
    _, summary_data = get_data(filters)

    role_stats = summary_data.get("role_stats", {})
    labels = list(role_stats.keys())[:12]

    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Within", "values": [role_stats[k]["within"] for k in labels]},
                {"name": "Breached", "values": [role_stats[k]["breached"] for k in labels]},
            ],
        },
        "barOptions": {"stacked": 1},
        "colors": ["#28a745", "#dc3545"],
    }


@frappe.whitelist()
def get_trend_chart(filters: str, months: int = 6) -> Dict:
    """Get compliance trend chart over time."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters)

    date_to = getdate(filters.get("date_to")) or getdate()
    trend = []

    for i in range(months):
        if i == 0:
            end = date_to
        else:
            end = (start.replace(day=1) - timedelta(days=1))
        start = end.replace(day=1)

        temp_filters = frappe._dict({
            "date_from": start,
            "date_to": end,
            "channel": filters.get("channel"),
            "priority": filters.get("priority"),
            "branch_filter": filters.get("branch_filter"),
            "role_filter": filters.get("role_filter"),
        })

        _, summary = get_data(temp_filters)
        trend.append({
            "label": start.strftime("%b %Y"),
            "compliance": round(summary.get("compliance_percent", 0.0), 1),
        })

    trend.reverse()

    return {
        "type": "line",
        "data": {
            "labels": [t["label"] for t in trend],
            "datasets": [{"name": "Compliance %", "values": [t["compliance"] for t in trend]}],
        },
        "colors": ["#5e64ff"],
    }



# =====================
# Antoine AI Integration
# =====================

@frappe.whitelist()
def get_ai_insights(filters: str, query: str) -> Dict:
    """Return Antoine-style AI insights for SLA Compliance Analysis.

    Builds a JSON context with SLA compliance %, FRT/RT metrics, escalation
    behaviour and passes it to Antoine via EnhancedAIService.
    """
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters)

    # Get current data
    _, summary_data = get_data(filters)

    # Get history from previous SLA Compliance Reports
    history = frappe.get_all(
        "SLA Compliance Report",
        filters={"period_type": filters.get("period_type", "Monthly")},
        fields=[
            "name", "date_from", "date_to", "compliance_percent",
            "frt_avg_minutes", "rt_avg_hours", "escalations_total",
        ],
        order_by="date_from desc",
        limit=12,
    )

    context = {
        "window": {
            "period_type": filters.get("period_type", "Monthly"),
            "from": str(filters.get("date_from", "")),
            "to": str(filters.get("date_to", "")),
        },
        "current": {
            "total_items": summary_data.get("total_items", 0),
            "within_sla": summary_data.get("within_sla", 0),
            "breached_sla": summary_data.get("breached_sla", 0),
            "compliance_percent": round(summary_data.get("compliance_percent", 0.0), 2),
            "frt_avg_minutes": round(summary_data.get("frt_avg", 0.0), 2),
            "frt_p90_minutes": round(summary_data.get("frt_p90", 0.0), 2),
            "frt_within_percent": round(summary_data.get("frt_within_percent", 0.0), 2),
            "rt_avg_hours": round(summary_data.get("rt_avg", 0.0), 2),
            "rt_p90_hours": round(summary_data.get("rt_p90", 0.0), 2),
            "rt_within_percent": round(summary_data.get("rt_within_percent", 0.0), 2),
            "escalations_total": summary_data.get("escalations_total", 0),
            "escalations_within": summary_data.get("escalations_within", 0),
            "escalations_breached": summary_data.get("escalations_breached", 0),
            "ai_first_responses": summary_data.get("ai_first", 0),
        },
        "branch_breakdown": summary_data.get("branch_stats", {}),
        "role_breakdown": summary_data.get("role_stats", {}),
        "category_breakdown": summary_data.get("cat_stats", {}),
        "history": [
            {
                "name": h.name,
                "date_from": str(h.date_from) if h.date_from else "",
                "date_to": str(h.date_to) if h.date_to else "",
                "compliance_percent": float(h.compliance_percent or 0),
                "frt_avg_minutes": float(h.frt_avg_minutes or 0),
                "rt_avg_hours": float(h.rt_avg_hours or 0),
                "escalations_total": int(h.escalations_total or 0),
            }
            for h in history
        ],
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService

        ai = EnhancedAIService()
        answer = ai.generate_sla_compliance_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "SLA Compliance Analysis AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure Antoine/OpenAI settings in Enhanced AI Settings."
            )
        }