"""
AI Automation Analysis - Native ERPNext Script Report

Comprehensive analysis of AI automation events, after-hours ticket handling,
document validation, data quality, and system health using native ERPNext doctypes
where applicable and custom doctypes for AI-specific metrics.

Leverages native Frappe/ERPNext doctypes:
- Scheduled Job Log: Automation execution tracking
- Error Log: System error monitoring
- Activity Log: User activity and audit trail
- Communication: Email/notification tracking

Includes Antoine AI integration for intelligent insights.
"""

import json
from datetime import date, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe import _
from frappe.utils import getdate, get_first_day, get_last_day, now_datetime, get_datetime, cint, flt
from assistant_crm.report.report_utils import get_period_dates

# Business hours definition (configurable via CRM Settings)
BUSINESS_START = time(8, 0)
BUSINESS_END = time(17, 0)
BUSINESS_DAYS = {0, 1, 2, 3, 4}  # Monday to Friday


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple:
    """Main entry point for Script Report.

    Returns:
        Tuple of (columns, data, message, chart, report_summary, skip_total_row)
    """
    filters = frappe._dict(filters or {})
    get_period_dates(filters)

    columns = get_columns()
    data, summary_data = get_data(filters)
    chart = get_chart_data(summary_data)
    report_summary = get_report_summary(summary_data)

    return columns, data, None, chart, report_summary, False




def get_columns() -> List[Dict[str, Any]]:
    """Define report columns for scheduled job log data (native ERPNext)."""
    return [
        {"fieldname": "name", "label": "Log ID", "fieldtype": "Link", "options": "Scheduled Job Log", "width": 180},
        {"fieldname": "creation", "label": "Timestamp", "fieldtype": "Datetime", "width": 160},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 100},
        {"fieldname": "scheduled_job_type", "label": "Job Type", "fieldtype": "Link", "options": "Scheduled Job Type", "width": 200},
        {"fieldname": "is_after_hours", "label": "After Hours", "fieldtype": "Check", "width": 90},
        {"fieldname": "details", "label": "Details", "fieldtype": "Data", "width": 250},
    ]


def _is_business_hours(ts) -> bool:
    """Check if timestamp is within business hours."""
    if not ts:
        return False
    dt_val = get_datetime(ts)
    return dt_val.weekday() in BUSINESS_DAYS and BUSINESS_START <= dt_val.time() <= BUSINESS_END


def get_data(filters: frappe._dict) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch scheduled job logs (native ERPNext) and compute summary metrics."""
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    # Build conditions for Scheduled Job Log (native Frappe doctype)
    conditions = ["sjl.creation BETWEEN %(df)s AND %(dt)s"]
    values = {"df": df, "dt": dt}

    if filters.get("status"):
        conditions.append("sjl.status = %(status)s")
        values["status"] = filters.status

    if filters.get("job_type"):
        conditions.append("sjl.scheduled_job_type LIKE %(job_type)s")
        values["job_type"] = f"%{filters.job_type}%"

    where_clause = " AND ".join(conditions)

    # Fetch scheduled job logs (native ERPNext doctype)
    logs = frappe.db.sql(f"""
        SELECT
            sjl.name, sjl.creation, sjl.status,
            sjl.scheduled_job_type, sjl.details
        FROM `tabScheduled Job Log` sjl
        WHERE {where_clause}
        ORDER BY sjl.creation DESC
        LIMIT 5000
    """, values, as_dict=True)

    # Build data rows and compute summary
    data = []
    summary = {
        "total_automations": 0,
        "success": 0,
        "failed": 0,
        "after_hours_count": 0,
        "by_job_type": {},
    }

    for log in logs:
        summary["total_automations"] += 1
        status = (log.get("status") or "").lower()

        if status == "complete":
            summary["success"] += 1
        elif status == "failed":
            summary["failed"] += 1

        is_after = not _is_business_hours(log.get("creation"))
        if is_after:
            summary["after_hours_count"] += 1

        # Track by job type
        job_type = log.get("scheduled_job_type") or "Unknown"
        summary["by_job_type"][job_type] = summary["by_job_type"].get(job_type, 0) + 1

        data.append({
            "name": log.get("name"),
            "creation": log.get("creation"),
            "status": log.get("status"),
            "scheduled_job_type": job_type,
            "is_after_hours": 1 if is_after else 0,
            "details": (log.get("details") or "")[:100],
        })

    # Compute additional summary metrics
    summary["success_rate"] = (
        round(summary["success"] / summary["total_automations"] * 100, 1)
        if summary["total_automations"] else 0
    )

    # Get after-hours ticket metrics from Unified Inbox Conversation
    after_hours = _get_after_hours_metrics(df, dt)
    summary.update(after_hours)

    # Get document validation metrics
    doc_validation = _get_document_validation_metrics(df, dt)
    summary.update(doc_validation)

    # Get data quality and AI failure metrics
    data_quality = _get_data_quality_metrics(df, dt)
    summary.update(data_quality)

    # Get system health metrics
    system_health = _get_system_health()
    summary.update(system_health)

    return data, summary


def _get_after_hours_metrics(df: date, dt: date) -> Dict[str, Any]:
    """Get after-hours ticket metrics from Unified Inbox Conversation."""
    convs = frappe.get_all(
        "Unified Inbox Conversation",
        filters={"creation_time": ["between", [df, dt]]},
        fields=["creation_time", "ai_handled", "platform"],
        limit=100000,
    )

    after_hours_convs = [c for c in convs if not _is_business_hours(c.creation_time)]
    total_after = len(after_hours_convs)
    ai_handled = sum(1 for c in after_hours_convs if c.ai_handled)

    by_platform: Dict[str, int] = {}
    for c in after_hours_convs:
        p = c.platform or "Unknown"
        by_platform[p] = by_platform.get(p, 0) + 1

    return {
        "after_hours_tickets": total_after,
        "after_hours_ai_handled": ai_handled,
        "after_hours_ai_rate": round(ai_handled / total_after * 100, 1) if total_after else 0,
        "after_hours_by_platform": by_platform,
    }


def _get_document_validation_metrics(df: date, dt: date) -> Dict[str, Any]:
    """Get document validation metrics."""
    docs = frappe.get_all(
        "Document Validation",
        filters={"validation_date": ["between", [df, dt]]},
        fields=["validation_status"],
        limit=100000,
    )

    total = len(docs)
    status_counts: Dict[str, int] = {}
    for d in docs:
        s = (d.validation_status or "Unknown").title()
        status_counts[s] = status_counts.get(s, 0) + 1

    failed = status_counts.get("Failed", 0)
    warnings = status_counts.get("Passed With Warnings", 0)

    return {
        "doc_validations_total": total,
        "doc_validations_failed": failed,
        "doc_validations_warnings": warnings,
        "doc_validation_status_counts": status_counts,
    }


def _get_data_quality_metrics(df: date, dt: date) -> Dict[str, Any]:
    """Get data quality issues and AI failure metrics."""
    try:
        from assistant_crm.assistant_crm.api.integration_monitoring import get_data_quality_metrics
        snapshot = get_data_quality_metrics() or {}
    except Exception:
        snapshot = {}

    issues = snapshot.get("quality_issues") or []
    issues_total = sum(i.get("count", 0) for i in issues)

    # Get AI failures from Failed Query Log
    failures = frappe.get_all(
        "Failed Query Log",
        filters={"creation": ["between", [df, dt]]},
        fields=["failure_reason"],
        limit=100000,
    )
    ai_failures_total = len(failures)
    by_reason: Dict[str, int] = {}
    for f in failures:
        r = f.failure_reason or "Unknown"
        by_reason[r] = by_reason.get(r, 0) + 1

    return {
        "data_quality_issues_total": issues_total,
        "data_quality_issues": issues,
        "ai_failures_total": ai_failures_total,
        "ai_failures_by_reason": by_reason,
    }


def _get_system_health() -> Dict[str, Any]:
    """Get system health metrics."""
    try:
        from assistant_crm.assistant_crm.production.monitoring_analytics_system import get_monitoring_system
        health = get_monitoring_system().calculate_system_health()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AI Automation Analysis system health error")
        health = {"overall_score": 0, "status": "unknown", "factors": {}}

    score = float(health.get("overall_score") or 0)
    status = health.get("status") or "unknown"

    return {
        "system_health_score": score,
        "system_health_status": status,
        "system_health_factors": health.get("factors") or {},
    }


def get_chart_data(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Build primary automation status chart."""
    return {
        "data": {
            "labels": ["Success", "Failed"],
            "datasets": [{
                "name": "Automations",
                "values": [
                    summary.get("success", 0),
                    summary.get("failed", 0),
                ]
            }]
        },
        "type": "bar",
        "colors": ["#28a745", "#dc3545"],
    }


def get_report_summary(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build report summary cards."""
    health_score = summary.get("system_health_score", 0)
    health_indicator = "green" if health_score >= 80 else "orange" if health_score >= 60 else "red"

    return [
        {"value": summary.get("total_automations", 0), "label": "Automations", "datatype": "Int"},
        {"value": f"{summary.get('success_rate', 0):.1f}%", "label": "Success Rate", "datatype": "Data", "indicator": "green"},
        {"value": summary.get("after_hours_tickets", 0), "label": "After-Hours Tickets", "datatype": "Int", "indicator": "blue"},
        {"value": f"{summary.get('after_hours_ai_rate', 0):.1f}%", "label": "After-Hours AI Rate", "datatype": "Data"},
        {"value": summary.get("doc_validations_failed", 0), "label": "Doc Validation Fails", "datatype": "Int", "indicator": "orange"},
        {"value": summary.get("data_quality_issues_total", 0), "label": "Data Quality Issues", "datatype": "Int"},
        {"value": summary.get("ai_failures_total", 0), "label": "AI Failures", "datatype": "Int", "indicator": "red"},
        {"value": f"{health_score:.1f}%", "label": "System Health", "datatype": "Data", "indicator": health_indicator},
    ]


@frappe.whitelist()
def get_ai_insights(filters: str, query: str) -> Dict[str, Any]:
    """Return Antoine-style insights for the AI Automation Analysis report."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)

    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    # Get current data
    _, summary = get_data(filters)

    # Get historical reports for trend analysis
    history = []
    try:
        history = frappe.get_all(
            "AI Automation Report",
            filters={"period_type": filters.get("period_type", "Monthly")},
            fields=[
                "name", "date_from", "date_to", "total_ai_automations",
                "after_hours_tickets", "after_hours_ai_handled",
                "invalid_documents_total", "invalid_documents_failed",
                "data_quality_issues_total", "ai_failures_total",
                "system_health_score", "system_health_status"
            ],
            order_by="date_from desc",
            limit=12,
        )
    except Exception:
        pass

    context = {
        "window": {
            "period_type": filters.get("period_type", "Monthly"),
            "from": str(df),
            "to": str(dt),
        },
        "current": {
            "total_ai_automations": summary.get("total_automations", 0),
            "success_count": summary.get("success", 0),
            "failed_count": summary.get("failed", 0),
            "success_rate": summary.get("success_rate", 0),
            "after_hours_tickets": summary.get("after_hours_tickets", 0),
            "after_hours_ai_handled": summary.get("after_hours_ai_handled", 0),
            "after_hours_ai_rate": summary.get("after_hours_ai_rate", 0),
            "doc_validations_total": summary.get("doc_validations_total", 0),
            "doc_validations_failed": summary.get("doc_validations_failed", 0),
            "data_quality_issues_total": summary.get("data_quality_issues_total", 0),
            "ai_failures_total": summary.get("ai_failures_total", 0),
            "system_health_score": summary.get("system_health_score", 0),
            "system_health_status": summary.get("system_health_status", ""),
        },
        "history": history,
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService
        ai = EnhancedAIService()
        answer = ai.generate_ai_automation_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AI Automation Analysis AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure Antoine/OpenAI settings in Enhanced AI Settings."
            )
        }


@frappe.whitelist()
def get_automation_status_chart(filters: str) -> Dict[str, Any]:
    """Get automation success/failure chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    _, summary = get_data(filters)

    return {
        "data": {
            "labels": ["Success", "Failed"],
            "datasets": [{"name": "Count", "values": [
                summary.get("success", 0),
                summary.get("failed", 0),
            ]}]
        },
        "type": "bar",
        "colors": ["#28a745", "#dc3545"],
    }


@frappe.whitelist()
def get_after_hours_chart(filters: str) -> Dict[str, Any]:
    """Get after-hours tickets by platform chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    _, summary = get_data(filters)

    platform_counts = summary.get("after_hours_by_platform", {})
    plats = list(platform_counts.keys())
    counts = [platform_counts[p] for p in plats]

    return {
        "data": {
            "labels": plats if plats else ["No Data"],
            "datasets": [{"name": "After-Hours Tickets", "values": counts if counts else [0]}]
        },
        "type": "bar",
        "colors": ["#5e64ff"],
    }


@frappe.whitelist()
def get_document_validation_chart(filters: str) -> Dict[str, Any]:
    """Get document validation status chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    _, summary = get_data(filters)

    status_counts = summary.get("doc_validation_status_counts", {})
    labels = list(status_counts.keys())
    values = list(status_counts.values())

    return {
        "data": {
            "labels": labels if labels else ["No Data"],
            "datasets": [{"name": "Validations", "values": values if values else [0]}]
        },
        "type": "pie",
        "colors": ["#28a745", "#ffa00a", "#dc3545", "#5e64ff"],
    }


@frappe.whitelist()
def get_data_quality_chart(filters: str) -> Dict[str, Any]:
    """Get data quality issues chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    _, summary = get_data(filters)

    issues = summary.get("data_quality_issues", [])
    labels = [i.get("type", "Unknown") for i in issues]
    values = [i.get("count", 0) for i in issues]

    return {
        "data": {
            "labels": labels if labels else ["No Data"],
            "datasets": [{"name": "Data Issues", "values": values if values else [0]}]
        },
        "type": "bar",
        "colors": ["#ffa00a"],
    }


@frappe.whitelist()
def get_ai_failures_chart(filters: str) -> Dict[str, Any]:
    """Get AI failures by reason chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    _, summary = get_data(filters)

    by_reason = summary.get("ai_failures_by_reason", {})
    labels = list(by_reason.keys())
    values = list(by_reason.values())

    return {
        "data": {
            "labels": labels if labels else ["No Data"],
            "datasets": [{"name": "AI Failures", "values": values if values else [0]}]
        },
        "type": "bar",
        "colors": ["#dc3545"],
    }


@frappe.whitelist()
def get_system_health_chart(filters: str) -> Dict[str, Any]:
    """Get system health gauge chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    _, summary = get_data(filters)

    score = summary.get("system_health_score", 0)

    return {
        "data": {
            "labels": ["Health", "Remaining"],
            "datasets": [{"name": "System Health", "values": [round(score, 1), max(0, 100 - round(score, 1))]}]
        },
        "type": "pie",
        "colors": ["#28a745", "#e9ecef"],
    }


@frappe.whitelist()
def get_automation_trend_chart(filters: str = None, months: int = 6) -> Dict[str, Any]:
    """Get automation trend chart over months using native Scheduled Job Log."""
    from frappe.utils import add_months

    labels = []
    success_values = []
    failed_values = []
    anchor = getdate()

    for i in range(months - 1, -1, -1):
        month_start = get_first_day(add_months(anchor, -i))
        if i > 0:
            month_end = get_first_day(add_months(anchor, -i + 1)) - timedelta(days=1)
        else:
            month_end = anchor

        # Count scheduled job logs in this month (native Frappe doctype)
        logs = frappe.get_all(
            "Scheduled Job Log",
            filters={"creation": ["between", [month_start, month_end]]},
            fields=["status"],
            limit=100000,
        )

        success = sum(1 for l in logs if (l.status or "").lower() == "complete")
        failed = sum(1 for l in logs if (l.status or "").lower() == "failed")

        labels.append(month_start.strftime("%b %Y"))
        success_values.append(success)
        failed_values.append(failed)

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Complete", "values": success_values},
                {"name": "Failed", "values": failed_values}
            ]
        },
        "type": "line",
        "colors": ["#28a745", "#dc3545"],
    }

