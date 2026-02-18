"""
Branch Performance Analysis - Script Report

Native ERPNext Script Report for analyzing branch performance using:
- Issue doctype (via custom_branch field)
- Claim doctype (via branch field)
- Unified Inbox Conversation doctype (via branch field)

Includes Antoine AI integration for intelligent insights.
"""

import json
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe.utils import getdate, get_datetime, add_months, get_first_day, get_last_day
from assistant_crm.report.report_utils import get_period_dates

# Import SLA aggregation for within/breached counts
from assistant_crm.assistant_crm.doctype.sla_compliance_report.sla_compliance_report import (
    aggregate_sla_compliance,
)

# Region names for Zambia
_REGION_NAMES = [
    "Lusaka", "Copperbelt", "Northern", "Eastern", "Southern",
    "Western", "Central", "Luapula", "Muchinga", "North-Western",
]


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple:
    """Main entry point for Script Report."""
    filters = frappe._dict(filters or {})

    # Ensure date filters
    get_period_dates(filters)

    columns = get_columns()
    data, summary = get_data(filters)
    chart = get_chart_data(data)
    report_summary = get_report_summary(summary)

    return columns, data, None, chart, report_summary, False


def get_columns() -> List[Dict[str, Any]]:
    """Define report columns based on branch performance metrics."""
    return [
        {"fieldname": "branch", "label": "Branch", "fieldtype": "Link", "options": "Branch", "width": 150},
        {"fieldname": "region", "label": "Region", "fieldtype": "Data", "width": 120},
        {"fieldname": "total_issues", "label": "Issues", "fieldtype": "Int", "width": 80},
        {"fieldname": "issues_resolved", "label": "Issues Resolved", "fieldtype": "Int", "width": 110},
        {"fieldname": "total_claims", "label": "Claims", "fieldtype": "Int", "width": 80},
        {"fieldname": "claims_resolved", "label": "Claims Resolved", "fieldtype": "Int", "width": 110},
        {"fieldname": "total_complaints", "label": "Complaints", "fieldtype": "Int", "width": 100},
        {"fieldname": "complaints_resolved", "label": "Complaints Resolved", "fieldtype": "Int", "width": 130},
        {"fieldname": "complaints_escalated", "label": "Escalated", "fieldtype": "Int", "width": 90},
        {"fieldname": "sla_percent", "label": "SLA %", "fieldtype": "Percent", "width": 80},
        {"fieldname": "avg_issue_days", "label": "Avg Issue Days", "fieldtype": "Float", "precision": 1, "width": 110},
        {"fieldname": "avg_claim_days", "label": "Avg Claim Days", "fieldtype": "Float", "precision": 1, "width": 110},
        {"fieldname": "avg_complaint_days", "label": "Avg Complaint Days", "fieldtype": "Float", "precision": 1, "width": 130},
    ]


def get_data(filters: frappe._dict) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch and aggregate branch performance data from Issue, Claim, and Unified Inbox Conversation."""
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    branch_filter = (filters.get("branch") or "").strip().lower()
    region_filter = (filters.get("region") or "All").strip() or "All"
    channel = filters.get("channel") if filters.get("channel") != "All" else None
    priority = filters.get("priority") if filters.get("priority") != "All" else None

    # Aggregate from each source
    claims_by_branch = _aggregate_claims_by_branch(df, dt, branch_filter, priority)
    complaints_by_branch = _aggregate_complaints_by_branch(df, dt, branch_filter, channel, priority)
    issues_by_branch = _aggregate_issues_by_branch(df, dt, branch_filter, priority)

    # Get SLA data
    sla_counts, sla_charts, _ = aggregate_sla_compliance(df, dt, {
        "branch": filters.get("branch"),
        "role": None,
        "channel": channel,
        "priority": priority,
    })
    sla_by_branch = _extract_sla_branch_stats(sla_charts)

    all_branches = sorted(set(claims_by_branch.keys()) | set(complaints_by_branch.keys()) | 
                          set(sla_by_branch.keys()) | set(issues_by_branch.keys()))

    data = []
    totals = {
        "total_branches": 0, "total_issues": 0, "total_claims": 0, "total_complaints": 0,
        "total_escalations": 0, "sla_within": 0, "sla_breached": 0,
        "issue_days_sum": 0.0, "issue_days_count": 0,
        "claim_days_sum": 0.0, "claim_days_count": 0,
        "complaint_days_sum": 0.0, "complaint_days_count": 0,
    }

    for branch in all_branches:
        region = _map_branch_to_region(branch)
        if region_filter not in ("All", "", None) and region != region_filter:
            continue

        c = claims_by_branch.get(branch, {})
        comp = complaints_by_branch.get(branch, {})
        iss = issues_by_branch.get(branch, {})
        sla = sla_by_branch.get(branch, {"within": 0, "breached": 0})

        within = int(sla.get("within", 0))
        breached = int(sla.get("breached", 0))
        total_sla = within + breached
        sla_percent = (within / total_sla * 100.0) if total_sla else 0.0

        avg_issue_days = _avg_from_sums(iss.get("resolution_days_sum", 0.0), iss.get("resolution_days_count", 0))
        avg_claim_days = _avg_from_sums(c.get("resolution_days_sum", 0.0), c.get("resolution_days_count", 0))
        avg_comp_days = _avg_from_sums(comp.get("resolution_days_sum", 0.0), comp.get("resolution_days_count", 0))

        row = {
            "branch": branch,
            "region": region,
            "total_issues": int(iss.get("total", 0)),
            "issues_resolved": int(iss.get("resolved", 0)),
            "total_claims": int(c.get("total", 0)),
            "claims_resolved": int(c.get("resolved", 0)),
            "total_complaints": int(comp.get("total", 0)),
            "complaints_resolved": int(comp.get("resolved", 0)),
            "complaints_escalated": int(comp.get("escalated", 0)),
            "sla_within": within,
            "sla_breached": breached,
            "sla_percent": round(sla_percent, 1),
            "avg_issue_days": round(avg_issue_days, 1),
            "avg_claim_days": round(avg_claim_days, 1),
            "avg_complaint_days": round(avg_comp_days, 1),
        }
        data.append(row)

        # Accumulate totals
        totals["total_branches"] += 1
        totals["total_issues"] += row["total_issues"]
        totals["total_claims"] += row["total_claims"]
        totals["total_complaints"] += row["total_complaints"]
        totals["total_escalations"] += row["complaints_escalated"]
        totals["sla_within"] += within
        totals["sla_breached"] += breached

    # Calculate overall SLA
    total_sla = totals["sla_within"] + totals["sla_breached"]
    totals["overall_sla"] = (totals["sla_within"] / total_sla * 100.0) if total_sla else 0.0

    data.sort(key=lambda x: ((x.get("region") or ""), (x.get("branch") or "")))
    return data, totals


def get_chart_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build default chart data showing top branches by total activity."""
    if not data:
        return {}
    top = sorted(
        data,
        key=lambda r: (r.get("total_issues", 0) or 0) + (r.get("total_claims", 0) or 0) + (r.get("total_complaints", 0) or 0),
        reverse=True,
    )[:10]
    labels = [r.get("branch") or "" for r in top]
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Issues", "values": [int(r.get("total_issues", 0) or 0) for r in top]},
                {"name": "Claims", "values": [int(r.get("total_claims", 0) or 0) for r in top]},
                {"name": "Complaints", "values": [int(r.get("total_complaints", 0) or 0) for r in top]},
            ],
        },
        "type": "bar",
        "barOptions": {"stacked": True},
        "colors": ["#5e64ff", "#28a745", "#ffc107"],
    }


def get_report_summary(totals: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build report summary cards."""
    sla = totals.get("overall_sla", 0.0)
    sla_indicator = "green" if sla >= 90 else ("orange" if sla >= 75 else "red")
    return [
        {"value": totals.get("total_branches", 0), "label": "Branches", "datatype": "Int"},
        {"value": totals.get("total_issues", 0), "label": "Total Issues", "datatype": "Int", "indicator": "blue"},
        {"value": totals.get("total_claims", 0), "label": "Total Claims", "datatype": "Int", "indicator": "green"},
        {"value": totals.get("total_complaints", 0), "label": "Total Complaints", "datatype": "Int", "indicator": "orange"},
        {"value": totals.get("total_escalations", 0), "label": "Escalations", "datatype": "Int", "indicator": "red"},
        {"value": round(sla, 1), "label": "Overall SLA %", "datatype": "Percent", "indicator": sla_indicator},
    ]


# ----------------------
# Aggregation Helpers
# ----------------------

def _aggregate_issues_by_branch(df: date, dt: date, branch_filter: str, priority: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """Aggregate Issue tickets by custom_branch field."""
    from_date = str(df) if df else None
    to_date = str(dt) if dt else None

    sql = """
        SELECT name, custom_branch, status, priority, creation, modified
        FROM `tabIssue`
        WHERE 1=1
    """
    params = []

    if from_date and to_date:
        sql += " AND creation >= %s AND creation <= %s"
        params.extend([from_date, to_date])

    if priority:
        sql += " AND priority = %s"
        params.append(priority)

    if branch_filter:
        sql += " AND LOWER(COALESCE(custom_branch, '')) LIKE %s"
        params.append(f"%{branch_filter.lower()}%")

    sql += " LIMIT 10000"
    issues = frappe.db.sql(sql, params, as_dict=True)

    result: Dict[str, Dict[str, Any]] = {}
    for i in issues:
        branch = i.get("custom_branch") or "Unassigned"
        bucket = result.setdefault(branch, {"total": 0, "open": 0, "resolved": 0, "resolution_days_sum": 0.0, "resolution_days_count": 0})
        bucket["total"] += 1
        status = (i.get("status") or "").lower()
        if status in {"closed", "resolved"}:
            bucket["resolved"] += 1
        elif status in {"open", "replied"}:
            bucket["open"] += 1

        creation = i.get("creation")
        # Use modified date as resolution date for closed issues
        resolution_date = i.get("modified")
        if creation and resolution_date and status in {"closed", "resolved"}:
            try:
                start = get_datetime(creation)
                end = get_datetime(resolution_date)
                days = (end - start).days
                bucket["resolution_days_sum"] += max(days, 0)
                bucket["resolution_days_count"] += 1
            except Exception:
                pass

    return result


def _aggregate_claims_by_branch(df: date, dt: date, branch_filter: str, priority: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """Aggregate Claim records by branch field."""
    from_date = str(df) if df else None
    to_date = str(dt) if dt else None

    sql = """
        SELECT name, branch, approved_by, status, submitted_date, approved_on, amount, creation
        FROM `tabClaim`
        WHERE docstatus >= 0
    """
    params = []

    if from_date and to_date:
        sql += " AND (submitted_date BETWEEN %s AND %s OR (submitted_date IS NULL AND creation BETWEEN %s AND %s))"
        params.extend([from_date, to_date, from_date, to_date])

    if priority:
        sql += " AND priority = %s"
        params.append(priority)

    if branch_filter:
        sql += " AND LOWER(COALESCE(branch, '')) LIKE %s"
        params.append(f"%{branch_filter.lower()}%")

    sql += " LIMIT 10000"
    rows = frappe.db.sql(sql, params, as_dict=True)

    result: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        branch = r.get("branch") or _derive_branch_for_user(r.get("approved_by"))
        if not branch:
            branch = "Unassigned"

        bucket = result.setdefault(branch, {"total": 0, "resolved": 0, "rejected": 0, "amount_total": 0.0, "resolution_days_sum": 0.0, "resolution_days_count": 0})
        bucket["total"] += 1
        bucket["amount_total"] += float(r.get("amount") or 0.0)

        status = (r.get("status") or "").lower()
        if status in {"approved", "paid", "settled", "closed"}:
            bucket["resolved"] += 1
        if status in {"rejected", "declined"}:
            bucket["rejected"] += 1

        submitted = r.get("submitted_date")
        approved_on = r.get("approved_on")
        if submitted and approved_on:
            try:
                start = get_datetime(submitted)
                end = get_datetime(approved_on)
                days = (end - start).days
                bucket["resolution_days_sum"] += max(days, 0)
                bucket["resolution_days_count"] += 1
            except Exception:
                pass

    return result


def _aggregate_complaints_by_branch(df: date, dt: date, branch_filter: str, channel: Optional[str], priority: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """Aggregate Unified Inbox Conversation (complaints) by branch field."""
    from_date = str(df) if df else None
    to_date = str(dt) if dt else None

    sql = """
        SELECT name, branch, assigned_agent, status, priority, creation_time, last_message_time, escalated_at
        FROM `tabUnified Inbox Conversation`
        WHERE 1=1
    """
    params = []

    if from_date and to_date:
        sql += " AND creation >= %s AND creation <= %s"
        params.extend([from_date, to_date])

    if channel:
        sql += " AND platform = %s"
        params.append(channel)
    if priority:
        sql += " AND priority = %s"
        params.append(priority)

    if branch_filter:
        sql += " AND LOWER(COALESCE(branch, '')) LIKE %s"
        params.append(f"%{branch_filter.lower()}%")

    sql += " LIMIT 10000"
    convs = frappe.db.sql(sql, params, as_dict=True)

    result: Dict[str, Dict[str, Any]] = {}
    for c in convs:
        branch = c.get("branch") or _derive_branch_for_user(c.get("assigned_agent"))
        if not branch:
            branch = "Unassigned"

        bucket = result.setdefault(branch, {"total": 0, "resolved": 0, "escalated": 0, "resolution_days_sum": 0.0, "resolution_days_count": 0})
        bucket["total"] += 1
        status = (c.get("status") or "").lower()
        if status in {"closed", "resolved"}:
            bucket["resolved"] += 1
        if c.get("escalated_at"):
            bucket["escalated"] += 1

        creation_time = c.get("creation_time")
        last_msg_time = c.get("last_message_time")
        if creation_time and last_msg_time and status in {"closed", "resolved"}:
            try:
                start = get_datetime(creation_time)
                end = get_datetime(last_msg_time)
                days = (end - start).total_seconds() / (60.0 * 60.0 * 24.0)
                bucket["resolution_days_sum"] += max(days, 0.0)
                bucket["resolution_days_count"] += 1
            except Exception:
                pass

    return result


def _derive_branch_for_user(user_id: Optional[str]) -> str:
    """Derive branch from user's branch or department field."""
    if not user_id:
        return "Unassigned"
    try:
        user = frappe.get_cached_doc("User", user_id)
        meta = user.meta
        if meta.has_field("branch") and getattr(user, "branch", None):
            return str(user.branch)
        if meta.has_field("department") and getattr(user, "department", None):
            return str(user.department)
    except Exception:
        return "Unassigned"
    return "Unassigned"


def _map_branch_to_region(branch: Optional[str]) -> str:
    """Map branch name to Zambian region."""
    if not branch:
        return "Unassigned"
    b = branch.lower()
    for region in _REGION_NAMES:
        if region.lower() in b:
            return region
    return "Other"


def _avg_from_sums(total: float, count: int) -> float:
    return float(total) / count if count else 0.0


def _extract_sla_branch_stats(charts: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """Pull branch-level within/breached counts from SLA charts structure."""
    result: Dict[str, Dict[str, int]] = {}
    branch_chart = (charts or {}).get("branch") or {}
    data = branch_chart.get("data") or {}
    labels = data.get("labels") or []
    datasets = data.get("datasets") or []
    within_ds = next((d for d in datasets if (d.get("name") or "").lower().startswith("within")), None)
    breached_ds = next((d for d in datasets if (d.get("name") or "").lower().startswith("breach")), None)
    within_vals = within_ds.get("values") if isinstance(within_ds, dict) else []
    breached_vals = breached_ds.get("values") if isinstance(breached_ds, dict) else []
    for idx, label in enumerate(labels):
        result[label] = {
            "within": int((within_vals[idx] if idx < len(within_vals) else 0) or 0),
            "breached": int((breached_vals[idx] if idx < len(breached_vals) else 0) or 0),
        }
    return result


# ----------------------
# AI Integration
# ----------------------

@frappe.whitelist()
def get_ai_insights(filters: str, query: str) -> Dict[str, Any]:
    """Return Antoine-style insights for the Branch Performance Analysis report."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})

    # Ensure dates
    if not filters.get("date_from") or not filters.get("date_to"):
        filters.date_to = getdate()
        filters.date_from = frappe.utils.add_days(filters.date_to, -29)

    # Get current data
    data, totals = get_data(filters)

    # Build context for AI
    context = {
        "window": {
            "period_type": filters.get("period_type", "Custom"),
            "from": str(filters.date_from),
            "to": str(filters.date_to),
        },
        "current": {
            "total_branches": totals.get("total_branches", 0),
            "total_issues": totals.get("total_issues", 0),
            "total_claims": totals.get("total_claims", 0),
            "total_complaints": totals.get("total_complaints", 0),
            "total_escalations": totals.get("total_escalations", 0),
            "overall_sla_percent": round(totals.get("overall_sla", 0.0), 1),
            "rows": data[:50],  # Limit rows for context size
        },
        "history": [],  # Could fetch historical data from Branch Performance Report doctype
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService
        ai = EnhancedAIService()
        answer = ai.generate_branch_performance_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Branch Performance Analysis AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure Antoine/OpenAI settings in Enhanced AI Settings."
            )
        }


# ----------------------
# Additional Chart Functions
# ----------------------

@frappe.whitelist()
def get_sla_chart(filters: str) -> Dict[str, Any]:
    """Get SLA compliance chart by branch."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    if not filters.get("date_from") or not filters.get("date_to"):
        filters.date_to = getdate()
        filters.date_from = frappe.utils.add_days(filters.date_to, -29)

    data, _ = get_data(filters)
    top = sorted(data, key=lambda r: float(r.get("sla_percent", 0.0) or 0.0), reverse=True)[:12]
    labels = [r.get("branch") or "" for r in top]
    values = [round(float(r.get("sla_percent", 0.0) or 0.0), 1) for r in top]

    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": "SLA %", "values": values}],
        },
        "type": "bar",
        "colors": ["#28a745"],
    }


@frappe.whitelist()
def get_regional_chart(filters: str) -> Dict[str, Any]:
    """Get regional comparison chart."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    if not filters.get("date_from") or not filters.get("date_to"):
        filters.date_to = getdate()
        filters.date_from = frappe.utils.add_days(filters.date_to, -29)

    data, _ = get_data(filters)

    # Aggregate by region
    region_acc: Dict[str, Dict[str, Any]] = {}
    for row in data:
        region = row.get("region") or "Other"
        reg = region_acc.setdefault(region, {"region": region, "issues": 0, "claims": 0, "complaints": 0, "sla_within": 0, "sla_breached": 0})
        reg["issues"] += row.get("total_issues", 0)
        reg["claims"] += row.get("total_claims", 0)
        reg["complaints"] += row.get("total_complaints", 0)
        reg["sla_within"] += row.get("sla_within", 0)
        reg["sla_breached"] += row.get("sla_breached", 0)

    region_rows = []
    for reg_key, rdata in sorted(region_acc.items()):
        total_sla = rdata["sla_within"] + rdata["sla_breached"]
        rdata["sla_percent"] = (rdata["sla_within"] / total_sla * 100.0) if total_sla else 0.0
        region_rows.append(rdata)

    labels = [r.get("region") or "" for r in region_rows]
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Issues", "values": [r.get("issues", 0) for r in region_rows]},
                {"name": "Claims", "values": [r.get("claims", 0) for r in region_rows]},
                {"name": "Complaints", "values": [r.get("complaints", 0) for r in region_rows]},
            ],
        },
        "type": "bar",
        "barOptions": {"stacked": True},
        "colors": ["#5e64ff", "#28a745", "#ffc107"],
    }


@frappe.whitelist()
def get_trend_chart(filters: str, months: int = 6) -> Dict[str, Any]:
    """Get trend chart for the last N months."""
    months = int(months)
    labels = []
    issues_vals = []
    claims_vals = []
    complaints_vals = []
    anchor = getdate()

    for i in range(months - 1, -1, -1):
        mstart = get_first_day(add_months(anchor, -i))
        mend = get_last_day(mstart)
        labels.append(mstart.strftime("%b %Y"))

        # Count issues
        issue_count = frappe.db.count("Issue", filters={"creation": ["between", [mstart, mend]]})
        issues_vals.append(int(issue_count or 0))

        # Count claims
        claim_count = frappe.db.sql("""
            SELECT COUNT(*) FROM `tabClaim`
            WHERE docstatus >= 0 AND (
                (submitted_date BETWEEN %s AND %s) OR
                (submitted_date IS NULL AND creation BETWEEN %s AND %s)
            )
        """, [mstart, mend, mstart, mend])[0][0]
        claims_vals.append(int(claim_count or 0))

        # Count complaints
        complaint_count = frappe.db.count("Unified Inbox Conversation", filters={"creation": ["between", [mstart, mend]]})
        complaints_vals.append(int(complaint_count or 0))

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Issues", "values": issues_vals},
                {"name": "Claims", "values": claims_vals},
                {"name": "Complaints", "values": complaints_vals},
            ],
        },
        "type": "line",
        "colors": ["#5e64ff", "#28a745", "#ffc107"],
    }

