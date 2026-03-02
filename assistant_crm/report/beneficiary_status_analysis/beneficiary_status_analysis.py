"""
Beneficiary Status Analysis - Script Report

Native ERPNext Script Report for analyzing beneficiary/pensioner status distributions,
trends, and demographics using the Customer doctype (customer_type='Pensioner').

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
    """Define report columns for beneficiary financial summary."""
    return [
        {"fieldname": "period", "label": "Period", "fieldtype": "Data", "width": 100},
        {"fieldname": "beneficiary_id", "label": "Beneficiary ID", "fieldtype": "Link", "options": "Customer", "width": 120},
        {"fieldname": "beneficiary_name", "label": "Beneficiary Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "nrc_number", "label": "NRC Number", "fieldtype": "Data", "width": 130},
        {"fieldname": "pas_number", "label": "Pension No.", "fieldtype": "Data", "width": 120},
        {"fieldname": "amount_paid", "label": "Amount Paid", "fieldtype": "Currency", "width": 120},
        {"fieldname": "unpaid_compensation", "label": "Unpaid Compensation", "fieldtype": "Currency", "width": 150},
        {"fieldname": "conditions_met", "label": "Conditions Met", "fieldtype": "Check", "width": 110},
        {"fieldname": "paid_period", "label": "Paid Period", "fieldtype": "Data", "width": 120},
        {"fieldname": "unpaid_period", "label": "Unpaid Period", "fieldtype": "Data", "width": 120},
        {"fieldname": "remaining_balance", "label": "Remaining Balance", "fieldtype": "Currency", "width": 140},
    ]


def get_data(filters: frappe._dict) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Fetch financial beneficiary data joined with Payment Status."""
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    # Fetch Pensioners from Customer
    pensioners = frappe.get_all(
        "Customer",
        filters={"customer_type": "Pensioner"},
        fields=["name", "customer_name", "custom_nrc_number", "custom_pas_number", "disabled"]
    )

    # Fetch all Payment Status records for the period
    payments = frappe.get_all(
        "Payment Status",
        filters={"payment_date": [">=", df], "payment_date": ["<=", dt]},
        fields=["beneficiary", "amount", "status", "payment_date", "payment_type"]
    )

    # Aggregate financial data by (Period, Beneficiary)
    financial_data = {}
    
    for p in payments:
        if not p.payment_date:
            continue
            
        period_key = p.payment_date.strftime("%b %Y")
        beneficiary_key = p.beneficiary # Usually NRC or Name
        key = (period_key, beneficiary_key)
        
        if key not in financial_data:
            financial_data[key] = {
                "period": period_key,
                "amount_paid": 0.0,
                "unpaid_compensation": 0.0,
                "paid_periods": set(),
                "unpaid_periods": set(),
            }
            
        if p.status == "Paid":
            financial_data[key]["amount_paid"] += float(p.amount or 0)
            financial_data[key]["paid_periods"].add(period_key)
        else:
            financial_data[key]["unpaid_compensation"] += float(p.amount or 0)
            financial_data[key]["unpaid_periods"].add(period_key)

    data = []
    counts = {"total": 0, "active": 0, "disabled": 0, "male": 0, "female": 0}

    # Match pensioners with financial data
    for p in pensioners:
        # For each period in financial data
        for (p_period, b_key), fin in financial_data.items():
            # Check if b_key matches either ID or NRC or PAS
            if b_key in {p.name, p.custom_nrc_number, p.custom_pas_number}:
                # Create row for this pensioner in this period
                row = {
                    "period": p_period,
                    "beneficiary_id": p.name,
                    "beneficiary_name": p.customer_name,
                    "nrc_number": p.custom_nrc_number,
                    "pas_number": p.custom_pas_number,
                    "amount_paid": fin["amount_paid"],
                    "unpaid_compensation": fin["unpaid_compensation"],
                    "conditions_met": 1 if not p.disabled else 0, # Placeholder logic
                    "paid_period": ", ".join(fin["paid_periods"]),
                    "unpaid_period": ", ".join(fin["unpaid_periods"]),
                    "remaining_balance": fin["unpaid_compensation"] # Placeholder
                }
                data.append(row)

    # Fallback to pensioners without financial data if data is empty
    if not data:
        for p in pensioners:
            data.append({
                "period": df.strftime("%b %Y"),
                "beneficiary_id": p.name,
                "beneficiary_name": p.customer_name,
                "nrc_number": p.custom_nrc_number,
                "pas_number": p.custom_pas_number,
                "amount_paid": 0.0,
                "unpaid_compensation": 0.0,
                "conditions_met": 1 if not p.disabled else 0,
                "paid_period": "-",
                "unpaid_period": "-",
                "remaining_balance": 0.0
            })

    # Update counts based on pensioners (not periods)
    for p in pensioners:
        counts["total"] += 1
        if p.disabled: counts["disabled"] += 1
        else: counts["active"] += 1

    # Sort data by Period then Beneficiary Name
    data.sort(key=lambda x: (x["period"], x["beneficiary_name"]))

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
    """Return WorkCom-style insights for the Beneficiary Status Analysis report.

    Builds a JSON context with status counts, distributions and trends,
    and passes it to WorkCom via EnhancedAIService.
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
                "administrator to configure WorkCom/OpenAI settings in Enhanced AI Settings."
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

