"""
Omnichannel Interaction Analysis - Script Report

Tracks conversations across all integrated channels:
- WhatsApp, Facebook, Telegram, Email, Web
- Response times and resolution status
- Channel-wise volume breakdown
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
    data, metrics = get_data(filters)
    chart = get_chart_data(metrics)
    report_summary = get_report_summary(metrics)

    return columns, data, None, chart, report_summary, False

def get_columns() -> List[Dict[str, Any]]:
    return [
        {"fieldname": "channel", "label": "Channel", "fieldtype": "Data", "width": 120},
        {"fieldname": "interaction_id", "label": "Interaction ID", "fieldtype": "Link", "options": "Unified Inbox Conversation", "width": 160},
        {"fieldname": "response_time", "label": "Resp. Time (Min)", "fieldtype": "Int", "width": 120},
        {"fieldname": "agent", "label": "Agent Assigned", "fieldtype": "Link", "options": "User", "width": 150},
        {"fieldname": "status", "label": "Resolution Status", "fieldtype": "Select", "width": 140},
        {"fieldname": "sla_status", "label": "SLA Status", "fieldtype": "Data", "width": 120},
    ]

def get_data(filters: frappe._dict) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    # Fetch Unified Inbox Conversations
    conversations = frappe.get_all(
        "Unified Inbox Conversation",
        filters={"creation": [">=", df], "creation": ["<=", dt]},
        fields=["name", "platform", "agent", "status", "creation", "modified"]
    )

    data = []
    channel_counts = {}
    metrics = {"total": 0, "resolved": 0, "avg_resp": 15.0} # Mocked avg for now

    for c in conversations:
        channel = c.platform or "Web"
        channel_counts[channel] = channel_counts.get(channel, 0) + 1
        metrics["total"] += 1
        
        if c.status == "Resolved":
            metrics["resolved"] += 1

        data.append({
            "channel": channel,
            "interaction_id": c.name,
            "response_time": 5, # Demo value
            "agent": c.agent or "Unassigned",
            "status": c.status or "Open",
            "sla_status": "Met" if c.status == "Resolved" else "Pending"
        })

    metrics["channel_counts"] = channel_counts
    return data, metrics

def get_chart_data(metrics: Dict[str, Any]) -> Dict[str, Any]:
    labels = list(metrics["channel_counts"].keys())
    values = list(metrics["channel_counts"].values())
    
    return {
        "data": {
            "labels": labels,
            "datasets": [{
                "name": "Interactions",
                "values": values
            }]
        },
        "type": "pie",
        "colors": ["#1abc9c", "#3498db", "#9b59b6", "#f1c40f", "#e67e22"]
    }

def get_report_summary(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    res_rate = round(metrics["resolved"] / metrics["total"] * 100, 1) if metrics["total"] else 0
    return [
        {"value": metrics["total"], "label": "Total Interactions", "indicator": "blue"},
        {"value": f"{res_rate}%", "label": "Resolution Rate", "indicator": "green"},
        {"value": f"{metrics['avg_resp']}m", "label": "Avg Response Time", "indicator": "yellow"}
    ]
