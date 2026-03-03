"""
Employer Compliance Analysis - Script Report

Analyzes employer compliance tracking:
- Workers earnings submission
- Assessment status
- Payment status
- ZRA TPIN tracking
"""

import json
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe.utils import getdate, flt
from assistant_crm.report.report_utils import get_period_dates

def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple:
    filters = frappe._dict(filters or {})
    get_period_dates(filters)

    columns = get_columns()
    data, summary_metrics = get_data(filters)
    chart = get_chart_data(summary_metrics)
    report_summary = get_report_summary(summary_metrics)

    return columns, data, None, chart, report_summary, False

def get_columns() -> List[Dict[str, Any]]:
    return [
        {"fieldname": "employer_id", "label": "Employer ID", "fieldtype": "Link", "options": "Employer", "width": 140},
        {"fieldname": "employer_name", "label": "Employer Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "employer_no", "label": "Employer No.", "fieldtype": "Data", "width": 120},
        {"fieldname": "zra_tpin", "label": "ZRA TPIN", "fieldtype": "Data", "width": 130},
        {"fieldname": "compliance_status", "label": "Compliance Status", "fieldtype": "Select", "width": 140},
        {"fieldname": "assessment_status", "label": "Assessment", "fieldtype": "Data", "width": 120},
        {"fieldname": "payment_status", "label": "Payment", "fieldtype": "Data", "width": 120},
        {"fieldname": "outstanding_amount", "label": "Outstanding", "fieldtype": "Currency", "width": 120},
        {"fieldname": "creation", "label": "Reported Date", "fieldtype": "Date", "width": 110},
    ]

def get_data(filters: frappe._dict) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    # Fetch from Employer Contributions as it has compliance data
    contributions = frappe.get_all(
        "Employer Contributions",
        filters={"creation": [">=", df], "creation": ["<=", dt]},
        fields=["employer_id", "employer_name", "status", "compliance_status", "outstanding_amount", "creation"]
    )

    data = []
    metrics = {"compliant": 0, "non_compliant": 0, "under_review": 0, "total_outstanding": 0.0}

    for c in contributions:
        status = c.compliance_status or "Unknown"
        if status == "Compliant":
            metrics["compliant"] += 1
        elif status == "Non-Compliant":
            metrics["non_compliant"] += 1
        elif status == "Under Review":
            metrics["under_review"] += 1
        
        metrics["total_outstanding"] += flt(c.outstanding_amount)

        data.append({
            "employer_id": c.employer_id,
            "employer_name": c.employer_name,
            "employer_no": c.employer_id, # Fallback
            "zra_tpin": "N/A", # Needs field mapping
            "compliance_status": status,
            "assessment_status": "Assessed" if flt(c.outstanding_amount) >= 0 else "Not Assessed",
            "payment_status": c.status or "Pending",
            "outstanding_amount": c.outstanding_amount,
            "creation": c.creation
        })

    return data, metrics

def get_chart_data(metrics: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "data": {
            "labels": ["Compliant", "Non-Compliant", "Under Review"],
            "datasets": [{
                "name": "Employers",
                "values": [metrics["compliant"], metrics["non_compliant"], metrics["under_review"]]
            }]
        },
        "type": "donut",
        "colors": ["#2ecc71", "#e74c3c", "#f1c40f"]
    }

def get_report_summary(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"value": metrics["compliant"], "label": "Compliant", "indicator": "green"},
        {"value": metrics["non_compliant"], "label": "Non-Compliant", "indicator": "red"},
        {"value": metrics["under_review"], "label": "Under Review", "indicator": "yellow"},
        {"value": metrics["total_outstanding"], "label": "Total Debt", "datatype": "Currency", "indicator": "red"}
    ]
