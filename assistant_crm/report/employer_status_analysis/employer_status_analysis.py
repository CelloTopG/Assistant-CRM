"""
Employer Status Analysis - Script Report

Production-ready Script Report for analyzing employer status distributions,
registration trends, and branch associations using the Employer doctype.

Includes Antoine AI integration for intelligent insights.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe.utils import getdate, add_months, get_first_day, get_last_day
from assistant_crm.report.report_utils import get_period_dates


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple:
    """Main entry point for Script Report."""
    filters = frappe._dict(filters or {})

    # Ensure date filters
    get_period_dates(filters)

    columns = get_columns()
    data, counts = get_data(filters)
    chart = get_chart_data(counts)
    report_summary = get_report_summary(counts)

    return columns, data, None, chart, report_summary, False


def get_columns() -> List[Dict[str, Any]]:
    """Define report columns based on Employer doctype fields."""
    return [
        {"fieldname": "name", "label": "Employer ID", "fieldtype": "Link", "options": "Employer", "width": 140},
        {"fieldname": "employer_name", "label": "Employer Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "employer_code", "label": "Employer Code", "fieldtype": "Data", "width": 120},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 130},
        {"fieldname": "branch_name", "label": "Branch", "fieldtype": "Link", "options": "Branch", "width": 150},
        {"fieldname": "branch_code", "label": "Branch Code", "fieldtype": "Data", "width": 100},
        {"fieldname": "creation", "label": "Registration Date", "fieldtype": "Date", "width": 120},
    ]


def get_data(filters: frappe._dict) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Fetch and aggregate employer data from Employer doctype."""
    # Build SQL conditions
    conditions = ["1=1"]
    values = {}

    # Status filter
    if filters.get("status"):
        conditions.append("status = %(status)s")
        values["status"] = filters.status

    # Branch filter
    if filters.get("branch"):
        conditions.append("branch_name = %(branch)s")
        values["branch"] = filters.branch

    # Date range filter on creation
    if filters.get("filter_by_date"):
        df = getdate(filters.date_from)
        dt = getdate(filters.date_to)
        conditions.append("DATE(creation) BETWEEN %(df)s AND %(dt)s")
        values["df"] = df
        values["dt"] = dt

    where_clause = " AND ".join(conditions)

    # Fetch employers from Employer table
    rows = frappe.db.sql(f"""
        SELECT
            name, employer_name, employer_code, status, branch_name, branch_code,
            DATE(creation) as creation
        FROM `tabEmployer`
        WHERE {where_clause}
        ORDER BY creation DESC
        LIMIT 5000
    """, values, as_dict=True)

    # Build data rows and count statuses
    data = []
    counts = {
        "total": 0,
        "active": 0,
        "inactive": 0,
        "suspended": 0,
        "pending": 0,
        "blacklisted": 0,
    }

    for r in rows:
        counts["total"] += 1
        status = (r.get("status") or "").strip()

        # Count by status
        if status == "Active":
            counts["active"] += 1
        elif status == "Inactive":
            counts["inactive"] += 1
        elif status == "Suspended":
            counts["suspended"] += 1
        elif status == "Pending Verification":
            counts["pending"] += 1
        elif status == "Blacklisted":
            counts["blacklisted"] += 1

        data.append({
            "name": r.get("name"),
            "employer_name": r.get("employer_name"),
            "employer_code": r.get("employer_code"),
            "status": status or "Unknown",
            "branch_name": r.get("branch_name"),
            "branch_code": r.get("branch_code"),
            "creation": r.get("creation"),
        })

    return data, counts


def get_chart_data(counts: Dict[str, int]) -> Dict[str, Any]:
    """Build chart data for status distribution."""
    return {
        "data": {
            "labels": ["Active", "Inactive", "Suspended", "Pending", "Blacklisted"],
            "datasets": [{
                "name": "Employers",
                "values": [
                    counts.get("active", 0),
                    counts.get("inactive", 0),
                    counts.get("suspended", 0),
                    counts.get("pending", 0),
                    counts.get("blacklisted", 0),
                ]
            }]
        },
        "type": "pie",
        "colors": ["#28a745", "#6c757d", "#ffc107", "#17a2b8", "#dc3545"],
    }


def get_report_summary(counts: Dict[str, int]) -> List[Dict[str, Any]]:
    """Build report summary cards."""
    return [
        {"value": counts.get("total", 0), "label": "Total Employers", "datatype": "Int"},
        {"value": counts.get("active", 0), "label": "Active", "datatype": "Int", "indicator": "green"},
        {"value": counts.get("inactive", 0), "label": "Inactive", "datatype": "Int", "indicator": "grey"},
        {"value": counts.get("suspended", 0), "label": "Suspended", "datatype": "Int", "indicator": "orange"},
        {"value": counts.get("pending", 0), "label": "Pending", "datatype": "Int", "indicator": "blue"},
        {"value": counts.get("blacklisted", 0), "label": "Blacklisted", "datatype": "Int", "indicator": "red"},
    ]


def get_distribution_maps() -> Tuple[Dict[str, int], Dict[str, int]]:
    """Get status and branch distributions via SQL aggregation."""
    status_map = {}
    for row in frappe.db.sql(
        "SELECT IFNULL(status, 'Unknown') AS s, COUNT(*) AS cnt FROM `tabEmployer` GROUP BY s",
        as_dict=True
    ):
        status_map[row.s] = int(row.cnt)

    branch_map = {}
    for row in frappe.db.sql(
        "SELECT IFNULL(branch_name, 'Unassigned') AS b, COUNT(*) AS cnt FROM `tabEmployer` GROUP BY b ORDER BY cnt DESC LIMIT 10",
        as_dict=True
    ):
        branch_map[row.b] = int(row.cnt)

    return status_map, branch_map


@frappe.whitelist()
def get_ai_insights(filters: str, query: str) -> Dict[str, Any]:
    """Return Antoine-style insights for the Employer Status Analysis report."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})

    # Ensure dates
    if not filters.get("date_from") or not filters.get("date_to"):
        filters.date_to = getdate()
        filters.date_from = frappe.utils.add_days(filters.date_to, -29)

    # Get current data
    _, counts = get_data(filters)
    status_map, branch_map = get_distribution_maps()

    context = {
        "window": {
            "period_type": filters.get("period_type", "Custom"),
            "from": str(filters.date_from),
            "to": str(filters.date_to),
        },
        "current": {
            "total": counts.get("total", 0),
            "active": counts.get("active", 0),
            "inactive": counts.get("inactive", 0),
            "suspended": counts.get("suspended", 0),
            "pending": counts.get("pending", 0),
            "blacklisted": counts.get("blacklisted", 0),
        },
        "distributions": {
            "status": status_map,
            "branch": branch_map,
        },
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService
        ai = EnhancedAIService()
        answer = ai.generate_employer_status_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Employer Status Analysis AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure Antoine/OpenAI settings in Enhanced AI Settings."
            )
        }


@frappe.whitelist()
def get_status_chart() -> Dict[str, Any]:
    """Get status distribution chart data."""
    status_map, _ = get_distribution_maps()
    colors = {
        "Active": "#28a745",
        "Inactive": "#6c757d",
        "Suspended": "#ffc107",
        "Pending Verification": "#17a2b8",
        "Blacklisted": "#dc3545",
        "Unknown": "#adb5bd",
    }
    return {
        "data": {
            "labels": list(status_map.keys()),
            "datasets": [{"name": "Count", "values": list(status_map.values())}]
        },
        "type": "bar",
        "colors": [colors.get(k, "#5e64ff") for k in status_map.keys()],
    }


@frappe.whitelist()
def get_branch_chart() -> Dict[str, Any]:
    """Get branch distribution chart data (top 10)."""
    _, branch_map = get_distribution_maps()
    return {
        "data": {
            "labels": list(branch_map.keys()),
            "datasets": [{"name": "Employers", "values": list(branch_map.values())}]
        },
        "type": "bar",
        "colors": ["#7cd6fd"],
    }


@frappe.whitelist()
def get_trend_chart(months: int = 6) -> Dict[str, Any]:
    """Get trend chart data for employer registrations over the last N months."""
    labels = []
    values = []
    anchor = getdate()

    for i in range(months - 1, -1, -1):
        mend = get_first_day(add_months(anchor, -i + 1)) if i > 0 else anchor
        count = frappe.db.count("Employer", filters={
            "creation": ["<=", mend]
        })
        mstart = add_months(get_first_day(anchor), -i)
        labels.append(mstart.strftime("%b %Y"))
        values.append(int(count))

    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": "Total Employers", "values": values}]
        },
        "type": "line",
        "colors": ["#7cd6fd"],
    }

