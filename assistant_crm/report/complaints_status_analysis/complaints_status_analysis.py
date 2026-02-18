"""
Complaints Status Analysis - Native ERPNext Script Report

Comprehensive analysis of complaints from the native Issue doctype and
Unified Inbox Conversation. Provides category classification (Claims,
Compliance, General), escalation tracking, resolution metrics, platform
breakdown, and Antoine AI integration for intelligent insights.

This report mirrors the functionality of the Complaints Status Report
doctype but leverages native ERPNext doctypes for improved integration.
"""

import json
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe.utils import getdate, add_days
from assistant_crm.report.report_utils import get_period_dates

# Category constants
CATEGORY_CLAIMS = "Claims"
CATEGORY_COMPLIANCE = "Compliance"
CATEGORY_GENERAL = "General"


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple:
    """Main entry point for Script Report."""
    filters = frappe._dict(filters or {})
    get_period_dates(filters)

    columns = get_columns()
    data, summary_data = get_data(filters)
    chart = get_chart_data(summary_data)
    report_summary = get_report_summary(summary_data)

    return columns, data, None, chart, report_summary, False




def get_columns() -> List[Dict[str, Any]]:
    """Define report columns for complaint data."""
    return [
        {"fieldname": "source_type", "label": "Source", "fieldtype": "Data", "width": 120},
        {"fieldname": "name", "label": "ID", "fieldtype": "Dynamic Link", "options": "source_doctype", "width": 160},
        {"fieldname": "source_doctype", "label": "Doctype", "fieldtype": "Data", "hidden": 1},
        {"fieldname": "platform", "label": "Platform", "fieldtype": "Data", "width": 110},
        {"fieldname": "subject", "label": "Subject", "fieldtype": "Data", "width": 220},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 100},
        {"fieldname": "auto_category", "label": "Auto Category", "fieldtype": "Data", "width": 110},
        {"fieldname": "override_category", "label": "Override", "fieldtype": "Data", "width": 100},
        {"fieldname": "final_category", "label": "Category", "fieldtype": "Data", "width": 100},
        {"fieldname": "escalated", "label": "Escalated", "fieldtype": "Check", "width": 80},
        {"fieldname": "creation", "label": "Created", "fieldtype": "Datetime", "width": 150},
    ]


def get_data(filters: frappe._dict) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch complaints from Issue and Unified Inbox Conversation."""
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    counts, platform_counts, rows = aggregate_complaints(df, dt, filters)

    # Compute additional metrics
    total = counts.get("total", 0)
    summary = {
        "total": total,
        "claims": counts.get("claims", 0),
        "compliance": counts.get("compliance", 0),
        "general": counts.get("general", 0),
        "escalated": counts.get("escalated", 0),
        "resolved": counts.get("resolved", 0),
        "open": counts.get("open", 0),
        "resolution_rate": round(counts.get("resolved", 0) / total * 100, 1) if total else 0,
        "escalation_rate": round(counts.get("escalated", 0) / total * 100, 1) if total else 0,
        "platform_counts": platform_counts,
    }

    return rows, summary


def aggregate_complaints(
    df: date, dt: date, filters: Optional[frappe._dict] = None
) -> Tuple[Dict[str, int], Dict[str, int], List[Dict[str, Any]]]:
    """Aggregate complaints from Issue and Unified Inbox Conversation."""
    filters = filters or frappe._dict()

    counts = {
        "total": 0, "claims": 0, "compliance": 0, "general": 0,
        "escalated": 0, "resolved": 0, "open": 0,
    }
    platform_counts: Dict[str, int] = {}
    rows: List[Dict[str, Any]] = []

    # Build escalation index
    conv_escalations, ref_escalations = _build_escalation_index(df, dt)

    # Get Issues (primary native ERPNext doctype)
    issues = _get_issues(df, dt, filters)
    for i in issues:
        row = _process_issue(i, ref_escalations, filters)
        if row:
            _update_counts(row, counts, platform_counts)
            rows.append(row)

    # Get Unified Inbox Conversations
    conversations = _get_conversations(df, dt, filters)
    seen_conv_ids = set()
    for c in conversations:
        if c.get("name") in seen_conv_ids:
            continue
        seen_conv_ids.add(c.get("name"))
        row = _process_conversation(c, conv_escalations, filters)
        if row:
            _update_counts(row, counts, platform_counts)
            rows.append(row)

    # Sort by creation descending
    rows.sort(key=lambda x: x.get("creation") or "", reverse=True)

    return counts, platform_counts, rows


def _update_counts(
    row: Dict[str, Any], counts: Dict[str, int], platform_counts: Dict[str, int]
):
    """Update aggregated counts based on a row."""
    counts["total"] += 1
    cat = row.get("final_category", CATEGORY_GENERAL)
    if cat == CATEGORY_CLAIMS:
        counts["claims"] += 1
    elif cat == CATEGORY_COMPLIANCE:
        counts["compliance"] += 1
    else:
        counts["general"] += 1

    if row.get("escalated"):
        counts["escalated"] += 1

    status = (row.get("status") or "").lower()
    if status in {"resolved", "closed"}:
        counts["resolved"] += 1
    else:
        counts["open"] += 1

    platform = row.get("platform") or "Unknown"
    platform_counts[platform] = platform_counts.get(platform, 0) + 1


def _get_issues(df: date, dt: date, filters: frappe._dict) -> List[Dict[str, Any]]:
    """Get Issue records within date range."""
    fields = ["name", "subject", "status", "creation", "description", "priority"]
    meta = frappe.get_meta("Issue")

    # Add optional custom fields if present
    for field in ["custom_conversation_id", "custom_platform_source", "complaint_category_override"]:
        if meta.has_field(field):
            fields.append(field)

    filter_conditions = [["creation", ">=", df], ["creation", "<=", dt]]

    # Apply category filter if specified
    if filters.get("category") and meta.has_field("complaint_category_override"):
        filter_conditions.append(["complaint_category_override", "=", filters.category])

    # Apply status filter
    if filters.get("status"):
        filter_conditions.append(["status", "=", filters.status])

    # Apply platform filter
    if filters.get("platform") and meta.has_field("custom_platform_source"):
        filter_conditions.append(["custom_platform_source", "=", filters.platform])

    return frappe.get_all(
        "Issue",
        filters=filter_conditions,
        fields=fields,
        limit=2000,
        order_by="creation desc",
    ) or []


def _get_conversations(df: date, dt: date, filters: frappe._dict) -> List[Dict[str, Any]]:
    """Get Unified Inbox Conversation records within date range."""
    fields = [
        "name", "conversation_id", "platform", "status", "priority",
        "subject", "last_message_preview", "tags", "creation", "escalated_at"
    ]
    try:
        meta = frappe.get_meta("Unified Inbox Conversation")
        if meta.has_field("complaint_category_override"):
            fields.append("complaint_category_override")
    except Exception:
        return []

    filter_conditions = [["creation", ">=", df], ["creation", "<=", dt]]

    # Apply category filter
    if filters.get("category") and meta.has_field("complaint_category_override"):
        filter_conditions.append(["complaint_category_override", "=", filters.category])

    # Apply status filter
    if filters.get("status"):
        filter_conditions.append(["status", "=", filters.status])

    # Apply platform filter
    if filters.get("platform"):
        filter_conditions.append(["platform", "=", filters.platform])

    try:
        return frappe.get_all(
            "Unified Inbox Conversation",
            filters=filter_conditions,
            fields=fields,
            limit=2000,
            order_by="creation desc",
        ) or []
    except Exception:
        return []


def _process_issue(
    issue: Dict[str, Any], ref_escalations: Dict, filters: frappe._dict
) -> Optional[Dict[str, Any]]:
    """Process an Issue record into a complaint row."""
    override = issue.get("complaint_category_override")
    esc = ref_escalations.get(("Issue", issue.get("name")))
    dept = esc.get("department") if esc else None
    text = " ".join(filter(None, [issue.get("subject"), issue.get("description")]))
    auto_category = classify_complaint(text=text, department=dept)
    final_category = override if override in {CATEGORY_CLAIMS, CATEGORY_COMPLIANCE, CATEGORY_GENERAL} else auto_category

    # Apply post-filters
    if filters.get("category") and final_category != filters.category:
        return None

    platform = issue.get("custom_platform_source") or "Unknown"

    return {
        "source_type": "Issue",
        "source_doctype": "Issue",
        "name": issue.get("name"),
        "platform": platform,
        "subject": (issue.get("subject") or "")[:100],
        "status": issue.get("status"),
        "auto_category": auto_category,
        "override_category": override,
        "final_category": final_category,
        "escalated": 1 if esc else 0,
        "creation": issue.get("creation"),
    }


def _process_conversation(
    conv: Dict[str, Any], conv_escalations: Dict, filters: frappe._dict
) -> Optional[Dict[str, Any]]:
    """Process a Unified Inbox Conversation into a complaint row."""
    override = conv.get("complaint_category_override")
    esc = conv_escalations.get(conv.get("name"))
    dept = esc.get("department") if esc else None
    text = " ".join(filter(None, [conv.get("subject"), conv.get("last_message_preview"), conv.get("tags")]))
    auto_category = classify_complaint(text=text, department=dept)
    final_category = override if override in {CATEGORY_CLAIMS, CATEGORY_COMPLIANCE, CATEGORY_GENERAL} else auto_category

    # Apply post-filters
    if filters.get("category") and final_category != filters.category:
        return None

    return {
        "source_type": "Conversation",
        "source_doctype": "Unified Inbox Conversation",
        "name": conv.get("name"),
        "platform": conv.get("platform") or "Unknown",
        "subject": (conv.get("subject") or "")[:100],
        "status": conv.get("status"),
        "auto_category": auto_category,
        "override_category": override,
        "final_category": final_category,
        "escalated": 1 if (conv.get("escalated_at") or esc) else 0,
        "creation": conv.get("creation"),
    }


def classify_complaint(text: Optional[str], department: Optional[str]) -> str:
    """Classify a complaint into Claims, Compliance, or General."""
    t = (text or "").lower()
    dept = (department or "").lower()

    claims_kw = [
        "claim", "compensation", "benefit", "injury", "accident",
        "pension", "settlement", "medical", "payment", "payout"
    ]
    compliance_kw = [
        "compliance", "regulation", "policy", "audit", "violation",
        "breach", "non-compliance", "inspection", "penalty", "fine"
    ]

    if dept in {"claims", "payments"}:
        return CATEGORY_CLAIMS
    if dept in {"compliance"}:
        return CATEGORY_COMPLIANCE

    if any(k in t for k in claims_kw):
        return CATEGORY_CLAIMS
    if any(k in t for k in compliance_kw):
        return CATEGORY_COMPLIANCE
    return CATEGORY_GENERAL


def _build_escalation_index(
    df: date, dt: date
) -> Tuple[Dict[str, Dict[str, Any]], Dict[Tuple[str, str], Dict[str, Any]]]:
    """Build escalation lookup indices."""
    conv_idx: Dict[str, Dict[str, Any]] = {}
    ref_idx: Dict[Tuple[str, str], Dict[str, Any]] = {}
    try:
        if not frappe.db.table_exists("Escalation Workflow"):
            return conv_idx, ref_idx
        meta = frappe.get_meta("Escalation Workflow")
        fields = ["name", "creation"]
        for f in ["conversation", "reference_doctype", "reference_name", "department", "status"]:
            if meta.has_field(f):
                fields.append(f)

        rows = frappe.get_all(
            "Escalation Workflow",
            filters=[["creation", ">=", df], ["creation", "<=", dt]],
            fields=fields,
            limit=2000,
        )
        for r in rows:
            esc = {k: r.get(k) for k in ["department", "status"] if k in r}
            if r.get("conversation"):
                conv_idx[r.get("conversation")] = esc
            rd, rn = r.get("reference_doctype"), r.get("reference_name")
            if rd and rn:
                ref_idx[(rd, rn)] = esc
    except Exception:
        pass
    return conv_idx, ref_idx


def get_chart_data(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Build primary category chart."""
    return {
        "data": {
            "labels": [CATEGORY_CLAIMS, CATEGORY_COMPLIANCE, CATEGORY_GENERAL],
            "datasets": [{
                "name": "Complaints",
                "values": [
                    summary.get("claims", 0),
                    summary.get("compliance", 0),
                    summary.get("general", 0),
                ]
            }]
        },
        "type": "bar",
        "colors": ["#5e64ff", "#ffa00a", "#28a745"],
    }


def get_report_summary(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build report summary cards."""
    esc_rate = summary.get("escalation_rate", 0)
    esc_indicator = "red" if esc_rate > 20 else "orange" if esc_rate > 10 else "green"

    return [
        {"value": summary.get("total", 0), "label": "Total Complaints", "datatype": "Int"},
        {"value": summary.get("claims", 0), "label": "Claims", "datatype": "Int", "indicator": "blue"},
        {"value": summary.get("compliance", 0), "label": "Compliance", "datatype": "Int", "indicator": "orange"},
        {"value": summary.get("general", 0), "label": "General", "datatype": "Int", "indicator": "green"},
        {"value": summary.get("escalated", 0), "label": "Escalated", "datatype": "Int", "indicator": esc_indicator},
        {"value": summary.get("resolved", 0), "label": "Resolved", "datatype": "Int", "indicator": "green"},
        {"value": summary.get("open", 0), "label": "Open", "datatype": "Int", "indicator": "gray"},
        {"value": f"{summary.get('resolution_rate', 0):.1f}%", "label": "Resolution Rate", "datatype": "Data"},
    ]


# ----- Whitelisted API Methods -----

@frappe.whitelist()
def get_ai_insights(filters: str, query: str) -> Dict[str, Any]:
    """Return Antoine-style insights for the Complaints Status Analysis report."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)

    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    # Get current data
    _, summary = get_data(filters)

    # Get historical data for trend analysis
    history = []
    try:
        history = frappe.get_all(
            "Complaints Status Report",
            filters={"period_type": filters.get("period_type", "Weekly")},
            fields=[
                "name", "date_from", "date_to", "total_count", "claims_count",
                "compliance_count", "general_count", "escalated_count",
                "resolved_count", "open_count",
            ],
            order_by="date_from desc",
            limit=12,
        )
    except Exception:
        pass

    context = {
        "window": {
            "period_type": filters.get("period_type", "Weekly"),
            "from": str(df),
            "to": str(dt),
        },
        "current": {
            "total": summary.get("total", 0),
            "claims": summary.get("claims", 0),
            "compliance": summary.get("compliance", 0),
            "general": summary.get("general", 0),
            "escalated": summary.get("escalated", 0),
            "resolved": summary.get("resolved", 0),
            "open": summary.get("open", 0),
            "resolution_rate": summary.get("resolution_rate", 0),
            "escalation_rate": summary.get("escalation_rate", 0),
        },
        "platforms": summary.get("platform_counts", {}),
        "history": history,
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService
        ai = EnhancedAIService()
        answer = ai.generate_complaints_status_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Complaints Status Analysis AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure Antoine/OpenAI settings in Enhanced AI Settings."
            )
        }


@frappe.whitelist()
def get_category_chart(filters: str) -> Dict[str, Any]:
    """Get complaints by category chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    _, summary = get_data(filters)

    return {
        "data": {
            "labels": [CATEGORY_CLAIMS, CATEGORY_COMPLIANCE, CATEGORY_GENERAL],
            "datasets": [{"name": "Complaints", "values": [
                summary.get("claims", 0),
                summary.get("compliance", 0),
                summary.get("general", 0),
            ]}]
        },
        "type": "bar",
        "colors": ["#5e64ff", "#ffa00a", "#28a745"],
    }


@frappe.whitelist()
def get_status_chart(filters: str) -> Dict[str, Any]:
    """Get complaints by status (open/resolved/escalated) chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    _, summary = get_data(filters)

    open_count = summary.get("open", 0)
    resolved_count = summary.get("resolved", 0)
    escalated_count = summary.get("escalated", 0)

    # Handle case where all values are zero - Frappe Charts pie chart fails with all zeros
    if open_count == 0 and resolved_count == 0 and escalated_count == 0:
        return {
            "data": {
                "labels": ["No Data"],
                "datasets": [{"name": "Status", "values": [1]}]
            },
            "type": "pie",
            "colors": ["#e9ecef"],
            "no_data": True,
        }

    return {
        "data": {
            "labels": ["Open", "Resolved", "Escalated"],
            "datasets": [{"name": "Status", "values": [
                open_count,
                resolved_count,
                escalated_count,
            ]}]
        },
        "type": "pie",
        "colors": ["#6c757d", "#28a745", "#dc3545"],
    }


@frappe.whitelist()
def get_platform_chart(filters: str) -> Dict[str, Any]:
    """Get complaints by platform chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    _, summary = get_data(filters)

    platform_counts = summary.get("platform_counts", {})
    platforms = list(platform_counts.keys()) or ["No Data"]
    values = list(platform_counts.values()) or [0]

    return {
        "data": {
            "labels": platforms,
            "datasets": [{"name": "Complaints", "values": values}]
        },
        "type": "bar",
        "colors": ["#5e64ff"],
    }


@frappe.whitelist()
def get_trend_chart(filters: str = None, windows: int = 8) -> Dict[str, Any]:
    """Get complaints trend chart over multiple periods."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    period_type = filters.get("period_type", "Weekly")

    def _first_of_month(d: date) -> date:
        return getdate(f"{d.year}-{d.month:02d}-01")

    wins: List[Tuple[date, date, str]] = []
    end = getdate()
    for _ in range(max(1, int(windows))):
        if period_type.lower().startswith("month"):
            start = _first_of_month(end)
            label = start.strftime("%b %Y")
            wins.append((start, end, label))
            end = add_days(start, -1)
        else:
            start = add_days(end, -6)
            label = f"{start.strftime('%d %b')}–{end.strftime('%d %b')}"
            wins.append((start, end, label))
            end = add_days(start, -1)
    wins.reverse()

    labels, s_total, s_claims, s_compliance, s_general, s_escalated = [], [], [], [], [], []

    for (s, e, lbl) in wins:
        counts, _, _ = aggregate_complaints(s, e, frappe._dict())
        labels.append(lbl)
        s_total.append(counts.get("total", 0))
        s_claims.append(counts.get("claims", 0))
        s_compliance.append(counts.get("compliance", 0))
        s_general.append(counts.get("general", 0))
        s_escalated.append(counts.get("escalated", 0))

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Total", "values": s_total},
                {"name": "Claims", "values": s_claims},
                {"name": "Compliance", "values": s_compliance},
                {"name": "General", "values": s_general},
                {"name": "Escalated", "values": s_escalated},
            ],
        },
        "type": "line",
        "colors": ["#343a40", "#5e64ff", "#ffa00a", "#28a745", "#dc3545"],
    }


@frappe.whitelist()
def get_stacked_platform_chart(filters: str) -> Dict[str, Any]:
    """Get stacked platform x category chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)

    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)
    _, _, rows = aggregate_complaints(df, dt, filters)

    platforms = sorted({(r.get("platform") or "Unknown") for r in rows}) or ["No Data"]

    def series_for(cat: str):
        return [sum(1 for r in rows if (r.get("platform") or "Unknown") == p and r.get("final_category") == cat)
                for p in platforms]

    return {
        "data": {
            "labels": platforms,
            "datasets": [
                {"name": CATEGORY_CLAIMS, "chartType": "bar", "values": series_for(CATEGORY_CLAIMS)},
                {"name": CATEGORY_COMPLIANCE, "chartType": "bar", "values": series_for(CATEGORY_COMPLIANCE)},
                {"name": CATEGORY_GENERAL, "chartType": "bar", "values": series_for(CATEGORY_GENERAL)},
            ]
        },
        "type": "bar",
        "barOptions": {"stacked": 1},
        "colors": ["#5e64ff", "#ffa00a", "#28a745"],
    }


@frappe.whitelist()
def set_category_override(source_doctype: str, source_name: str, category: Optional[str] = None) -> Dict[str, Any]:
    """Set manual category override on the source object (Conversation or Issue)."""
    allowed = {"Unified Inbox Conversation", "Issue"}
    if source_doctype not in allowed:
        frappe.throw("Unsupported source doctype")
    valid = {CATEGORY_CLAIMS, CATEGORY_COMPLIANCE, CATEGORY_GENERAL}
    if category and category not in valid:
        frappe.throw("Invalid category")
    _ensure_override_field(source_doctype)
    doc = frappe.get_doc(source_doctype, source_name)
    doc.db_set("complaint_category_override", category or None, update_modified=True)
    return {"ok": True}


def _ensure_override_field(doctype: str):
    """Ensure the complaint_category_override custom field exists."""
    try:
        meta = frappe.get_meta(doctype)
        if meta.has_field("complaint_category_override"):
            return
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
        create_custom_field(doctype, {
            "fieldname": "complaint_category_override",
            "label": "Complaint Category Override",
            "fieldtype": "Select",
            "options": f"{CATEGORY_CLAIMS}\n{CATEGORY_COMPLIANCE}\n{CATEGORY_GENERAL}",
            "insert_after": "status",
            "permlevel": 0,
        })
    except Exception:
        pass
