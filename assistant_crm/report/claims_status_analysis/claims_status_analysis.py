"""
Claims Status Analysis - Native ERPNext Script Report

Comprehensive analysis of claims from the Claim doctype with full lifecycle
status tracking, claim type breakdown, amount analysis, escalation metrics,
and Antoine AI integration for intelligent insights.

This report replaces the Claims Status Report doctype with a native ERPNext
Script Report for improved integration and real-time data access.
"""

import json
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe.utils import getdate, add_days, flt
from assistant_crm.report.report_utils import get_period_dates

# Claim lifecycle statuses (from Claim doctype)
LIFECYCLE_STATUSES = [
    "Submitted",
    "Under Review",
    "Pending Documentation",
    "Medical Review",
    "Validated",
    "Approved",
    "Rejected",
    "Closed",
    "Appealed",
    "Settled",
    "Reopened",
    "Escalated",
]

# Claim types
CLAIM_TYPES = [
    "Injury",
    "Illness",
    "Medical",
    "Disability",
    "Death",
    "Rehabilitation",
    "Reimbursement",
]


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
    """Define report columns for claim data."""
    return [
        {"fieldname": "claim_number", "label": "Claim Number", "fieldtype": "Link", "options": "Claim", "width": 160},
        {"fieldname": "creation", "label": "Created", "fieldtype": "Datetime", "width": 150},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 120},
        {"fieldname": "claim_type", "label": "Type", "fieldtype": "Data", "width": 110},
        {"fieldname": "claimant", "label": "Claimant", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"fieldname": "employer", "label": "Employer", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"fieldname": "amount", "label": "Amount", "fieldtype": "Currency", "width": 120},
        {"fieldname": "incident_date", "label": "Incident Date", "fieldtype": "Date", "width": 110},
        {"fieldname": "is_escalated", "label": "Escalated", "fieldtype": "Check", "width": 80},
    ]


def get_data(filters: frappe._dict) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch claims and compute summary metrics."""
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    rows, summary = aggregate_claims(df, dt, filters)
    return rows, summary


def aggregate_claims(
    df: date, dt: date, filters: Optional[frappe._dict] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Aggregate Claim records between the given dates."""
    filters = filters or frappe._dict()

    # Build filter conditions
    filter_conditions = [["creation", ">=", df], ["creation", "<=", dt]]

    if filters.get("status"):
        filter_conditions.append(["status", "=", filters.status])

    if filters.get("claim_type"):
        filter_conditions.append(["claim_type", "=", filters.claim_type])

    if filters.get("employer"):
        filter_conditions.append(["employer", "=", filters.employer])

    # Fetch claims
    claims = frappe.get_all(
        "Claim",
        filters=filter_conditions,
        fields=[
            "name", "claim_number", "status", "claim_type",
            "claimant", "employer", "amount", "incident_date", "creation"
        ],
        limit=5000,
        order_by="creation desc",
    )

    # Initialize summary
    summary = {
        "total": 0,
        "logged": 0,
        "validated": 0,
        "approved": 0,
        "rejected": 0,
        "escalated": 0,
        "settled": 0,
        "pending": 0,
        "total_amount": 0.0,
        "approved_amount": 0.0,
        "status_breakdown": {s: 0 for s in LIFECYCLE_STATUSES},
        "type_breakdown": {t: 0 for t in CLAIM_TYPES},
    }

    rows: List[Dict[str, Any]] = []

    for claim in claims:
        summary["total"] += 1
        summary["logged"] += 1

        status = (claim.get("status") or "").strip()
        claim_type = (claim.get("claim_type") or "").strip()
        amount = flt(claim.get("amount") or 0)

        summary["total_amount"] += amount

        # Track status breakdown
        if status in summary["status_breakdown"]:
            summary["status_breakdown"][status] += 1

        # Track type breakdown
        if claim_type in summary["type_breakdown"]:
            summary["type_breakdown"][claim_type] += 1

        # High-level KPIs
        if status == "Validated":
            summary["validated"] += 1
        elif status in {"Approved", "Settled"}:
            summary["approved"] += 1
            summary["approved_amount"] += amount
            if status == "Settled":
                summary["settled"] += 1
        elif status == "Rejected":
            summary["rejected"] += 1
        elif status == "Escalated":
            summary["escalated"] += 1
        elif status in {"Submitted", "Under Review", "Pending Documentation", "Medical Review"}:
            summary["pending"] += 1

        # Determine if escalated
        is_escalated = 1 if status == "Escalated" else 0

        rows.append({
            "claim_number": claim.get("claim_number") or claim.get("name"),
            "creation": claim.get("creation"),
            "status": status,
            "claim_type": claim_type,
            "claimant": claim.get("claimant"),
            "employer": claim.get("employer"),
            "amount": amount,
            "incident_date": claim.get("incident_date"),
            "is_escalated": is_escalated,
        })

    # Compute rates
    total = summary["total"]
    summary["approval_rate"] = round(summary["approved"] / total * 100, 1) if total else 0
    summary["rejection_rate"] = round(summary["rejected"] / total * 100, 1) if total else 0
    summary["escalation_rate"] = round(summary["escalated"] / total * 100, 1) if total else 0
    summary["validation_rate"] = round(summary["validated"] / total * 100, 1) if total else 0

    return rows, summary


def get_chart_data(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Build primary status chart."""
    status_breakdown = summary.get("status_breakdown", {})
    # Filter to non-zero statuses for cleaner chart
    labels = [s for s in LIFECYCLE_STATUSES if status_breakdown.get(s, 0) > 0]
    values = [status_breakdown.get(s, 0) for s in labels]

    if not labels:
        labels = ["No Data"]
        values = [0]

    return {
        "data": {
            "labels": labels,
            "datasets": [{
                "name": "Claims",
                "values": values
            }]
        },
        "type": "bar",
        "colors": ["#5e64ff"],
    }


def get_report_summary(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build report summary cards."""
    esc_rate = summary.get("escalation_rate", 0)
    esc_indicator = "red" if esc_rate > 10 else "orange" if esc_rate > 5 else "green"

    approval_rate = summary.get("approval_rate", 0)
    approval_indicator = "green" if approval_rate >= 70 else "orange" if approval_rate >= 50 else "red"

    return [
        {"value": summary.get("total", 0), "label": "Total Claims", "datatype": "Int"},
        {"value": summary.get("pending", 0), "label": "Pending", "datatype": "Int", "indicator": "orange"},
        {"value": summary.get("validated", 0), "label": "Validated", "datatype": "Int", "indicator": "blue"},
        {"value": summary.get("approved", 0), "label": "Approved", "datatype": "Int", "indicator": "green"},
        {"value": summary.get("rejected", 0), "label": "Rejected", "datatype": "Int", "indicator": "red"},
        {"value": summary.get("escalated", 0), "label": "Escalated", "datatype": "Int", "indicator": esc_indicator},
        {"value": f"{approval_rate:.1f}%", "label": "Approval Rate", "datatype": "Data", "indicator": approval_indicator},
        {"value": frappe.format_value(summary.get("total_amount", 0), {"fieldtype": "Currency"}), "label": "Total Amount", "datatype": "Data"},
    ]


# ----- Whitelisted API Methods -----

@frappe.whitelist()
def get_ai_insights(filters: str, query: str) -> Dict[str, Any]:
    """Return Antoine-style insights for the Claims Status Analysis report."""
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
            "Claims Status Report",
            filters={"period_type": filters.get("period_type", "Weekly")},
            fields=[
                "name", "date_from", "date_to", "logged_count",
                "validated_count", "approved_count", "rejected_count", "escalated_count",
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
            "logged": summary.get("logged", 0),
            "validated": summary.get("validated", 0),
            "approved": summary.get("approved", 0),
            "rejected": summary.get("rejected", 0),
            "escalated": summary.get("escalated", 0),
            "settled": summary.get("settled", 0),
            "pending": summary.get("pending", 0),
            "total_amount": summary.get("total_amount", 0),
            "approved_amount": summary.get("approved_amount", 0),
            "approval_rate": summary.get("approval_rate", 0),
            "rejection_rate": summary.get("rejection_rate", 0),
            "escalation_rate": summary.get("escalation_rate", 0),
        },
        "status_breakdown": summary.get("status_breakdown", {}),
        "type_breakdown": summary.get("type_breakdown", {}),
        "history": history,
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService
        ai = EnhancedAIService()
        # Reuse the existing claims status report insights method
        answer = ai.generate_claims_status_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Claims Status Analysis AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure Antoine/OpenAI settings in Enhanced AI Settings."
            )
        }


@frappe.whitelist()
def get_status_chart(filters: str) -> Dict[str, Any]:
    """Get claims by status chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    _, summary = get_data(filters)

    status_breakdown = summary.get("status_breakdown", {})
    labels = [s for s in LIFECYCLE_STATUSES if status_breakdown.get(s, 0) > 0]
    values = [status_breakdown.get(s, 0) for s in labels]

    if not labels:
        return {
            "data": {"labels": ["No Data"], "datasets": [{"name": "Claims", "values": [0]}]},
            "type": "bar",
            "colors": ["#e9ecef"],
            "no_data": True,
        }

    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": "Claims", "values": values}]
        },
        "type": "bar",
        "colors": ["#5e64ff"],
    }


@frappe.whitelist()
def get_type_chart(filters: str) -> Dict[str, Any]:
    """Get claims by type chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    _, summary = get_data(filters)

    type_breakdown = summary.get("type_breakdown", {})
    labels = [t for t in CLAIM_TYPES if type_breakdown.get(t, 0) > 0]
    values = [type_breakdown.get(t, 0) for t in labels]

    if not labels:
        return {
            "data": {"labels": ["No Data"], "datasets": [{"name": "Claims", "values": [0]}]},
            "type": "pie",
            "colors": ["#e9ecef"],
            "no_data": True,
        }

    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": "Claims", "values": values}]
        },
        "type": "pie",
        "colors": ["#5e64ff", "#28a745", "#ffa00a", "#dc3545", "#6c757d", "#17a2b8", "#6f42c1"],
    }


@frappe.whitelist()
def get_outcome_chart(filters: str) -> Dict[str, Any]:
    """Get claims outcome (approved/rejected/pending) pie chart."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    _, summary = get_data(filters)

    approved = summary.get("approved", 0)
    rejected = summary.get("rejected", 0)
    pending = summary.get("pending", 0)

    if approved == 0 and rejected == 0 and pending == 0:
        return {
            "data": {"labels": ["No Data"], "datasets": [{"name": "Outcome", "values": [1]}]},
            "type": "pie",
            "colors": ["#e9ecef"],
            "no_data": True,
        }

    return {
        "data": {
            "labels": ["Approved", "Rejected", "Pending"],
            "datasets": [{"name": "Outcome", "values": [approved, rejected, pending]}]
        },
        "type": "pie",
        "colors": ["#28a745", "#dc3545", "#ffa00a"],
    }


@frappe.whitelist()
def get_amount_by_type_chart(filters: str) -> Dict[str, Any]:
    """Get total claim amounts by type chart."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)

    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    filter_conditions = [["creation", ">=", df], ["creation", "<=", dt]]
    if filters.get("status"):
        filter_conditions.append(["status", "=", filters.status])

    claims = frappe.get_all(
        "Claim",
        filters=filter_conditions,
        fields=["claim_type", "amount"],
        limit=10000,
    )

    amounts_by_type: Dict[str, float] = {}
    for c in claims:
        ct = c.get("claim_type") or "Unknown"
        amounts_by_type[ct] = amounts_by_type.get(ct, 0) + flt(c.get("amount") or 0)

    labels = list(amounts_by_type.keys())
    values = [amounts_by_type[t] for t in labels]

    if not labels:
        return {
            "data": {"labels": ["No Data"], "datasets": [{"name": "Amount", "values": [0]}]},
            "type": "bar",
            "colors": ["#e9ecef"],
            "no_data": True,
        }

    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": "Amount (ZMW)", "values": values}]
        },
        "type": "bar",
        "colors": ["#17a2b8"],
    }


@frappe.whitelist()
def get_trend_chart(filters: str = None, windows: int = 8) -> Dict[str, Any]:
    """Get claims trend chart over multiple periods."""
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

    labels = []
    s_total, s_approved, s_rejected, s_escalated = [], [], [], []

    for (s, e, lbl) in wins:
        _, summary = aggregate_claims(s, e, frappe._dict())
        labels.append(lbl)
        s_total.append(summary.get("total", 0))
        s_approved.append(summary.get("approved", 0))
        s_rejected.append(summary.get("rejected", 0))
        s_escalated.append(summary.get("escalated", 0))

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Total", "values": s_total},
                {"name": "Approved", "values": s_approved},
                {"name": "Rejected", "values": s_rejected},
                {"name": "Escalated", "values": s_escalated},
            ],
        },
        "type": "line",
        "colors": ["#343a40", "#28a745", "#dc3545", "#ffa00a"],
    }


@frappe.whitelist()
def get_employer_chart(filters: str) -> Dict[str, Any]:
    """Get claims count by employer (top 10)."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)

    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    filter_conditions = [["creation", ">=", df], ["creation", "<=", dt]]
    if filters.get("status"):
        filter_conditions.append(["status", "=", filters.status])
    if filters.get("claim_type"):
        filter_conditions.append(["claim_type", "=", filters.claim_type])

    claims = frappe.get_all(
        "Claim",
        filters=filter_conditions,
        fields=["employer"],
        limit=10000,
    )

    employer_counts: Dict[str, int] = {}
    for c in claims:
        emp = c.get("employer") or "Unknown"
        employer_counts[emp] = employer_counts.get(emp, 0) + 1

    # Sort by count descending and take top 10
    sorted_employers = sorted(employer_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    labels = [e[0] for e in sorted_employers]
    values = [e[1] for e in sorted_employers]

    if not labels:
        return {
            "data": {"labels": ["No Data"], "datasets": [{"name": "Claims", "values": [0]}]},
            "type": "bar",
            "colors": ["#e9ecef"],
            "no_data": True,
        }

    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": "Claims", "values": values}]
        },
        "type": "bar",
        "colors": ["#6f42c1"],
    }

