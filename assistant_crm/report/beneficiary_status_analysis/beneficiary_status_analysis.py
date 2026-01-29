"""
Beneficiary Status Analysis - Script Report

Native ERPNext Script Report for analyzing beneficiary/pensioner status distributions,
trends, and demographics using the Customer doctype (customer_type='Pensioner').

Includes Antoine AI integration for intelligent insights.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe.utils import getdate, add_months, get_first_day, get_last_day


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple:
    """Main entry point for Script Report."""
    filters = frappe._dict(filters or {})

    # Ensure date filters
    if not filters.get("date_from") or not filters.get("date_to"):
        if filters.get("period_type") == "Monthly":
            filters.date_from = get_first_day(getdate())
            filters.date_to = getdate()
        else:
            filters.date_to = getdate()
            filters.date_from = frappe.utils.add_days(filters.date_to, -29)

    columns = get_columns()
    data, counts = get_data(filters)
    chart = get_chart_data(counts)
    report_summary = get_report_summary(counts)

    return columns, data, None, chart, report_summary, False


def get_columns() -> List[Dict[str, Any]]:
    """Define report columns."""
    return [
        {"fieldname": "name", "label": "ID", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"fieldname": "customer_name", "label": "Full Name", "fieldtype": "Data", "width": 200},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 100},
        {"fieldname": "gender", "label": "Gender", "fieldtype": "Data", "width": 80},
        {"fieldname": "pas_number", "label": "PAS Number", "fieldtype": "Data", "width": 120},
        {"fieldname": "nrc_number", "label": "NRC Number", "fieldtype": "Data", "width": 130},
        {"fieldname": "dependant_code", "label": "Dependant Code", "fieldtype": "Data", "width": 120},
        {"fieldname": "creation", "label": "Created On", "fieldtype": "Date", "width": 110},
        {"fieldname": "modified", "label": "Last Modified", "fieldtype": "Date", "width": 110},
    ]


def get_data(filters: frappe._dict) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Fetch and aggregate beneficiary data from Customer doctype (Pensioners)."""
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    # Build SQL conditions
    conditions = ["customer_type = 'Pensioner'"]
    values = {"df": df, "dt": dt}

    # Date range filter on creation (only if explicitly filtering by date)
    if filters.get("filter_by_date"):
        conditions.append("DATE(creation) BETWEEN %(df)s AND %(dt)s")

    # Status filter (Active = not disabled, Disabled = disabled)
    if filters.get("status"):
        if filters.status == "Active":
            conditions.append("disabled = 0")
        elif filters.status == "Disabled":
            conditions.append("disabled = 1")

    # Gender filter
    if filters.get("gender"):
        conditions.append("gender = %(gender)s")
        values["gender"] = filters.gender

    where_clause = " AND ".join(conditions)

    # Fetch beneficiaries from Customer table
    rows = frappe.db.sql(f"""
        SELECT
            name, customer_name, gender, disabled,
            custom_pas_number, custom_nrc_number, custom_dependant_code,
            creation, modified
        FROM `tabCustomer`
        WHERE {where_clause}
        ORDER BY modified DESC
        LIMIT 5000
    """, values, as_dict=True)

    # Build data rows and count statuses
    data = []
    counts = {"total": 0, "active": 0, "disabled": 0, "male": 0, "female": 0}

    for r in rows:
        counts["total"] += 1
        is_disabled = r.get("disabled") == 1
        gender = (r.get("gender") or "").strip()

        if is_disabled:
            counts["disabled"] += 1
        else:
            counts["active"] += 1

        if gender == "Male":
            counts["male"] += 1
        elif gender == "Female":
            counts["female"] += 1

        data.append({
            "name": r.get("name"),
            "customer_name": r.get("customer_name"),
            "status": "Disabled" if is_disabled else "Active",
            "gender": gender or "Unknown",
            "pas_number": r.get("custom_pas_number") or "",
            "nrc_number": r.get("custom_nrc_number") or "",
            "dependant_code": r.get("custom_dependant_code") or "",
            "creation": r.get("creation"),
            "modified": r.get("modified"),
        })

    return data, counts


def get_chart_data(counts: Dict[str, int]) -> Dict[str, Any]:
    """Build chart data for status distribution."""
    return {
        "data": {
            "labels": ["Active", "Disabled"],
            "datasets": [{
                "name": "Beneficiaries",
                "values": [
                    counts.get("active", 0),
                    counts.get("disabled", 0),
                ]
            }]
        },
        "type": "pie",
        "colors": ["#28a745", "#dc3545"],
    }


def get_report_summary(counts: Dict[str, int]) -> List[Dict[str, Any]]:
    """Build report summary cards."""
    return [
        {"value": counts.get("total", 0), "label": "Total Pensioners", "datatype": "Int"},
        {"value": counts.get("active", 0), "label": "Active", "datatype": "Int", "indicator": "green"},
        {"value": counts.get("disabled", 0), "label": "Disabled", "datatype": "Int", "indicator": "red"},
        {"value": counts.get("male", 0), "label": "Male", "datatype": "Int", "indicator": "blue"},
        {"value": counts.get("female", 0), "label": "Female", "datatype": "Int", "indicator": "purple"},
    ]


def get_distribution_maps() -> Tuple[Dict[str, int], Dict[str, int]]:
    """Get gender and status distributions via SQL aggregation."""
    gender_map = {}
    for row in frappe.db.sql(
        "SELECT IFNULL(gender, 'Unknown') AS g, COUNT(*) AS cnt FROM `tabCustomer` WHERE customer_type='Pensioner' GROUP BY g",
        as_dict=True
    ):
        gender_map[row.g] = int(row.cnt)

    status_map = {}
    for row in frappe.db.sql(
        "SELECT CASE WHEN disabled=1 THEN 'Disabled' ELSE 'Active' END AS s, COUNT(*) AS cnt FROM `tabCustomer` WHERE customer_type='Pensioner' GROUP BY s",
        as_dict=True
    ):
        status_map[row.s] = int(row.cnt)

    return gender_map, status_map


@frappe.whitelist()
def get_ai_insights(filters: str, query: str) -> Dict[str, Any]:
    """Return Antoine-style insights for the Beneficiary Status Analysis report.

    Builds a JSON context with status counts, distributions and trends,
    and passes it to Antoine via EnhancedAIService.
    """
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})

    # Ensure dates
    if not filters.get("date_from") or not filters.get("date_to"):
        filters.date_to = getdate()
        filters.date_from = frappe.utils.add_days(filters.date_to, -29)

    # Get current data
    _, counts = get_data(filters)
    gender_map, status_map = get_distribution_maps()

    # Get historical reports for trend analysis (if available)
    history = []
    try:
        history = frappe.get_all(
            "Beneficiary Status Report",
            fields=["name", "date_from", "date_to", "total_beneficiaries", "active_count"],
            order_by="date_from desc",
            limit=10,
        )
    except Exception:
        pass  # Table may not exist

    context = {
        "window": {
            "period_type": filters.get("period_type", "Custom"),
            "from": str(filters.date_from),
            "to": str(filters.date_to),
        },
        "current": {
            "total": counts.get("total", 0),
            "active": counts.get("active", 0),
            "disabled": counts.get("disabled", 0),
            "male": counts.get("male", 0),
            "female": counts.get("female", 0),
        },
        "distributions": {
            "gender": gender_map,
            "status": status_map,
        },
        "history": history,
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService
        ai = EnhancedAIService()
        answer = ai.generate_beneficiary_status_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Beneficiary Status Analysis AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure Antoine/OpenAI settings in Enhanced AI Settings."
            )
        }


@frappe.whitelist()
def get_gender_chart() -> Dict[str, Any]:
    """Get gender distribution chart data."""
    gender_map, _ = get_distribution_maps()
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
    _, status_map = get_distribution_maps()
    return {
        "data": {
            "labels": list(status_map.keys()),
            "datasets": [{"name": "Count", "values": list(status_map.values())}]
        },
        "type": "bar",
        "colors": ["#28a745", "#dc3545"],
    }


@frappe.whitelist()
def get_trend_chart(months: int = 6) -> Dict[str, Any]:
    """Get trend chart data for the last N months."""
    labels = []
    values = []
    anchor = getdate()

    # Count pensioners created up to each month
    for i in range(months - 1, -1, -1):
        mend = get_first_day(add_months(anchor, -i + 1)) if i > 0 else anchor
        count = frappe.db.count("Customer", filters={
            "customer_type": "Pensioner",
            "creation": ["<=", mend]
        })
        mstart = add_months(get_first_day(anchor), -i)
        labels.append(mstart.strftime("%b %Y"))
        values.append(int(count))

    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": "Total Pensioners", "values": values}]
        },
        "type": "line",
        "colors": ["#7cd6fd"],
    }
