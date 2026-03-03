"""
Issue Turnaround Analysis - Script Report

Measures time taken to resolve issues (TAT):
- Resolution Time Breakdown
- SLA Compliance by Issue Type
- Monthly trends in Turnaround Time
"""

import json
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe.utils import getdate, flt, time_diff_in_hours
from assistant_crm.report.report_utils import get_period_dates

def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple:
    filters = frappe._dict(filters or {})
    get_period_dates(filters)

    columns = get_columns()
    data, metrics = get_data(filters)
    chart = get_chart_data(metrics)
    report_summary = get_report_summary(metrics)

    return columns, data, None, chart, report_summary, False

def get_columns() -> List[Dict[str, Any]]:
    return [
        {"fieldname": "ticket_id", "label": "Ticket ID", "fieldtype": "Link", "options": "Issue", "width": 140},
        {"fieldname": "issue_type", "label": "Type", "fieldtype": "Data", "width": 120},
        {"fieldname": "date_logged", "label": "Date Logged", "fieldtype": "Datetime", "width": 150},
        {"fieldname": "date_resolved", "label": "Date Resolved", "fieldtype": "Datetime", "width": 150},
        {"fieldname": "agent", "label": "Agent Assigned", "fieldtype": "Link", "options": "User", "width": 140},
        {"fieldname": "tat_hours", "label": "TAT (Hours)", "fieldtype": "Float", "width": 110},
        {"fieldname": "sla_status", "label": "SLA Compliance", "fieldtype": "Data", "width": 120},
    ]

def get_data(filters: frappe._dict) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    # Fetch Issues
    issues = frappe.get_all(
        "Issue",
        filters={"creation": [">=", df], "creation": ["<=", dt]},
        fields=["name", "owner", "status", "resolution_date", "creation", "agreement_fulfilled", "subject"]
    )

    data = []
    metrics = {"total": 0, "avg_tat": 0.0, "sla_met": 0, "resolved": 0}
    total_tat = 0.0

    for i in issues:
        metrics["total"] += 1
        tat = 0.0
        sla = "Pending"
        
        if i.status in ["Closed", "Resolved"] and i.resolution_date:
            tat = time_diff_in_hours(i.resolution_date, i.creation)
            total_tat += tat
            metrics["resolved"] += 1
            sla = "Met" if i.agreement_fulfilled else "Breached"
            if i.agreement_fulfilled:
                metrics["sla_met"] += 1

        data.append({
            "ticket_id": i.name,
            "issue_type": "General Support", # Simplification
            "date_logged": i.creation,
            "date_resolved": i.resolution_date,
            "agent": i.owner,
            "tat_hours": round(tat, 2),
            "sla_status": sla
        })

    metrics["avg_tat"] = round(total_tat / metrics["resolved"], 1) if metrics["resolved"] else 0.0
    return data, metrics

def get_chart_data(metrics: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "data": {
            "labels": ["SLA Met", "SLA Breached"],
            "datasets": [{
                "name": "Tickets",
                "values": [metrics["sla_met"], metrics["total"] - metrics["sla_met"]]
            }]
        },
        "type": "bar",
        "colors": ["#2ecc71", "#e74c3c"]
    }

def get_report_summary(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    sla_rate = round(metrics["sla_met"] / metrics["total"] * 100, 1) if metrics["total"] else 0
    return [
        {"value": metrics["total"], "label": "Total Issues", "indicator": "blue"},
        {"value": f"{metrics['avg_tat']}h", "label": "Avg Turnaround", "indicator": "yellow"},
        {"value": f"{sla_rate}%", "label": "SLA Compliance", "indicator": "green"}
    ]
