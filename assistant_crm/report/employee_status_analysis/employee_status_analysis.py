"""
Employee Status Analysis - Script Report

Native ERPNext Script Report for analyzing employee status distributions,
trends, and demographics using the Employee doctype.

Includes WorkCom AI integration for intelligent insights.
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
    """Define report columns based on Employee doctype fields."""
    return [
        {"fieldname": "name", "label": "Employee ID", "fieldtype": "Link", "options": "Employee", "width": 140},
        {"fieldname": "employee_name", "label": "Employee Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 100},
        {"fieldname": "company", "label": "Company", "fieldtype": "Link", "options": "Company", "width": 150},
        {"fieldname": "department", "label": "Department", "fieldtype": "Link", "options": "Department", "width": 150},
        {"fieldname": "branch", "label": "Branch", "fieldtype": "Link", "options": "Branch", "width": 130},
        {"fieldname": "designation", "label": "Designation", "fieldtype": "Link", "options": "Designation", "width": 140},
        {"fieldname": "gender", "label": "Gender", "fieldtype": "Data", "width": 80},
        {"fieldname": "date_of_joining", "label": "Date of Joining", "fieldtype": "Date", "width": 120},
        {"fieldname": "ctc", "label": "CTC", "fieldtype": "Currency", "width": 120},
    ]


def get_data(filters: frappe._dict) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Fetch and aggregate employee data from Employee doctype."""
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    # Build SQL conditions
    conditions = ["1=1"]
    values = {"df": df, "dt": dt}

    # Date range filter on date_of_joining
    if filters.get("filter_by_date"):
        conditions.append("date_of_joining BETWEEN %(df)s AND %(dt)s")

    # Status filter
    if filters.get("status"):
        conditions.append("status = %(status)s")
        values["status"] = filters.status

    # Company filter
    if filters.get("company"):
        conditions.append("company = %(company)s")
        values["company"] = filters.company

    # Department filter
    if filters.get("department"):
        conditions.append("department = %(department)s")
        values["department"] = filters.department

    # Branch filter
    if filters.get("branch"):
        conditions.append("branch = %(branch)s")
        values["branch"] = filters.branch

    # Gender filter
    if filters.get("gender"):
        conditions.append("gender = %(gender)s")
        values["gender"] = filters.gender

    where_clause = " AND ".join(conditions)

    # Fetch employees from Employee table
    rows = frappe.db.sql(f"""
        SELECT
            name, employee_name, status, company, department, branch,
            designation, gender, date_of_joining, ctc
        FROM `tabEmployee`
        WHERE {where_clause}
        ORDER BY date_of_joining DESC
        LIMIT 5000
    """, values, as_dict=True)

    # Build data rows and count statuses
    data = []
    counts = {
        "total": 0, "active": 0, "inactive": 0, "suspended": 0, "left": 0,
        "male": 0, "female": 0, "other": 0
    }

    for r in rows:
        counts["total"] += 1
        status = (r.get("status") or "").strip()
        gender = (r.get("gender") or "").strip()

        # Count by status
        if status == "Active":
            counts["active"] += 1
        elif status == "Inactive":
            counts["inactive"] += 1
        elif status == "Suspended":
            counts["suspended"] += 1
        elif status == "Left":
            counts["left"] += 1

        # Count by gender
        if gender == "Male":
            counts["male"] += 1
        elif gender == "Female":
            counts["female"] += 1
        else:
            counts["other"] += 1

        data.append({
            "name": r.get("name"),
            "employee_name": r.get("employee_name"),
            "status": status or "Unknown",
            "company": r.get("company"),
            "department": r.get("department"),
            "branch": r.get("branch"),
            "designation": r.get("designation"),
            "gender": gender or "Unknown",
            "date_of_joining": r.get("date_of_joining"),
            "ctc": r.get("ctc"),
        })

    return data, counts


def get_chart_data(counts: Dict[str, int]) -> Dict[str, Any]:
    """Build chart data for status distribution."""
    return {
        "data": {
            "labels": ["Active", "Inactive", "Suspended", "Left"],
            "datasets": [{
                "name": "Employees",
                "values": [
                    counts.get("active", 0),
                    counts.get("inactive", 0),
                    counts.get("suspended", 0),
                    counts.get("left", 0),
                ]
            }]
        },
        "type": "pie",
        "colors": ["#28a745", "#ffc107", "#fd7e14", "#dc3545"],
    }


def get_report_summary(counts: Dict[str, int]) -> List[Dict[str, Any]]:
    """Build report summary cards."""
    return [
        {"value": counts.get("total", 0), "label": "Total Employees", "datatype": "Int"},
        {"value": counts.get("active", 0), "label": "Active", "datatype": "Int", "indicator": "green"},
        {"value": counts.get("inactive", 0), "label": "Inactive", "datatype": "Int", "indicator": "orange"},
        {"value": counts.get("left", 0), "label": "Left", "datatype": "Int", "indicator": "red"},
        {"value": counts.get("male", 0), "label": "Male", "datatype": "Int", "indicator": "blue"},
        {"value": counts.get("female", 0), "label": "Female", "datatype": "Int", "indicator": "purple"},
    ]


def get_distribution_maps() -> Tuple[Dict[str, int], Dict[str, int], Dict[str, int]]:
    """Get gender, status, and department distributions via SQL aggregation."""
    gender_map = {}
    for row in frappe.db.sql(
        "SELECT IFNULL(gender, 'Unknown') AS g, COUNT(*) AS cnt FROM `tabEmployee` GROUP BY g",
        as_dict=True
    ):
        gender_map[row.g] = int(row.cnt)

    status_map = {}
    for row in frappe.db.sql(
        "SELECT IFNULL(status, 'Unknown') AS s, COUNT(*) AS cnt FROM `tabEmployee` GROUP BY s",
        as_dict=True
    ):
        status_map[row.s] = int(row.cnt)

    department_map = {}
    for row in frappe.db.sql(
        "SELECT IFNULL(department, 'Unassigned') AS d, COUNT(*) AS cnt FROM `tabEmployee` GROUP BY d ORDER BY cnt DESC LIMIT 10",
        as_dict=True
    ):
        department_map[row.d] = int(row.cnt)

    return gender_map, status_map, department_map


@frappe.whitelist()
def get_ai_insights(filters: str, query: str) -> Dict[str, Any]:
    """Return WorkCom-style insights for the Employee Status Analysis report."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})

    # Ensure dates
    if not filters.get("date_from") or not filters.get("date_to"):
        filters.date_to = getdate()
        filters.date_from = frappe.utils.add_days(filters.date_to, -29)

    # Get current data
    _, counts = get_data(filters)
    gender_map, status_map, department_map = get_distribution_maps()

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
            "left": counts.get("left", 0),
            "male": counts.get("male", 0),
            "female": counts.get("female", 0),
        },
        "distributions": {
            "gender": gender_map,
            "status": status_map,
            "department": department_map,
        },
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService
        ai = EnhancedAIService()
        answer = ai.generate_employee_status_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Employee Status Analysis AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure WorkCom/OpenAI settings in Enhanced AI Settings."
            )
        }


@frappe.whitelist()
def get_gender_chart() -> Dict[str, Any]:
    """Get gender distribution chart data."""
    gender_map, _, _ = get_distribution_maps()
    return {
        "data": {
            "labels": list(gender_map.keys()),
            "datasets": [{"name": "Count", "values": list(gender_map.values())}]
        },
        "type": "bar",
        "colors": ["#5e64ff"],
    }


@frappe.whitelist()
def get_status_chart() -> Dict[str, Any]:
    """Get status distribution chart data."""
    _, status_map, _ = get_distribution_maps()
    return {
        "data": {
            "labels": list(status_map.keys()),
            "datasets": [{"name": "Count", "values": list(status_map.values())}]
        },
        "type": "bar",
        "colors": ["#28a745", "#ffc107", "#fd7e14", "#dc3545"],
    }


@frappe.whitelist()
def get_department_chart() -> Dict[str, Any]:
    """Get department distribution chart data (top 10)."""
    _, _, department_map = get_distribution_maps()
    return {
        "data": {
            "labels": list(department_map.keys()),
            "datasets": [{"name": "Employees", "values": list(department_map.values())}]
        },
        "type": "bar",
        "colors": ["#7cd6fd"],
    }


@frappe.whitelist()
def get_trend_chart(months: int = 6) -> Dict[str, Any]:
    """Get trend chart data for the last N months."""
    labels = []
    values = []
    anchor = getdate()

    for i in range(months - 1, -1, -1):
        mend = get_first_day(add_months(anchor, -i + 1)) if i > 0 else anchor
        count = frappe.db.count("Employee", filters={
            "date_of_joining": ["<=", mend]
        })
        mstart = add_months(get_first_day(anchor), -i)
        labels.append(mstart.strftime("%b %Y"))
        values.append(int(count))

    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": "Total Employees", "values": values}]
        },
        "type": "line",
        "colors": ["#7cd6fd"],
    }


