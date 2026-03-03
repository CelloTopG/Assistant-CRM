"""
Agent Performance Analysis - Script Report

KPIs for Support Agents:
- Tickets Handled
- Average Resolution Time (TAT)
- SLA Compliance Percentage
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
        {"fieldname": "agent", "label": "Agent Name", "fieldtype": "Link", "options": "User", "width": 180},
        {"fieldname": "tickets_handled", "label": "Tickets Handled", "fieldtype": "Int", "width": 120},
        {"fieldname": "avg_resolution_time", "label": "Avg Resolution (Hrs)", "fieldtype": "Float", "width": 140},
        {"fieldname": "sla_compliance", "label": "SLA Compliance %", "fieldtype": "Percent", "width": 140},
        {"fieldname": "breached_tickets", "label": "Breached", "fieldtype": "Int", "width": 110},
    ]

def get_data(filters: frappe._dict) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    # Fetch Issues (tickets)
    issues = frappe.get_all(
        "Issue",
        filters={"creation": [">=", df], "creation": ["<=", dt]},
        fields=["name", "owner", "status", "resolution_date", "creation", "agreement_fulfilled"]
    )

    agent_stats = {}
    
    for i in issues:
        agent = i.owner
        if agent not in agent_stats:
            agent_stats[agent] = {
                "agent": agent,
                "tickets_handled": 0,
                "total_res_time": 0.0,
                "resolved_count": 0,
                "sla_met": 0,
                "breached": 0
            }
        
        agent_stats[agent]["tickets_handled"] += 1
        
        if i.status in ["Closed", "Resolved"] and i.resolution_date:
            res_hours = time_diff_in_hours(i.resolution_date, i.creation)
            agent_stats[agent]["total_res_time"] += res_hours
            agent_stats[agent]["resolved_count"] += 1
            
        if i.agreement_fulfilled:
            agent_stats[agent]["sla_met"] += 1
        else:
            agent_stats[agent]["breached"] += 1

    data = []
    total_metrics = {"avg_sla": 0.0, "total_tickets": 0, "active_agents": 0}
    
    for agent, stats in agent_stats.items():
        avg_res = stats["total_res_time"] / stats["resolved_count"] if stats["resolved_count"] else 0
        sla_perc = (stats["sla_met"] / stats["tickets_handled"] * 100) if stats["tickets_handled"] else 0
        
        data.append({
            "agent": agent,
            "tickets_handled": stats["tickets_handled"],
            "avg_resolution_time": round(avg_res, 2),
            "sla_compliance": round(sla_perc, 1),
            "breached_tickets": stats["breached"]
        })
        
        total_metrics["total_tickets"] += stats["tickets_handled"]
        total_metrics["avg_sla"] += sla_perc
    
    if agent_stats:
        total_metrics["active_agents"] = len(agent_stats)
        total_metrics["avg_sla"] /= total_metrics["active_agents"]

    return data, total_metrics

def get_chart_data(metrics: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "data": {
            "labels": ["Summary"],
            "datasets": [{
                "name": "Tickets",
                "values": [metrics["total_tickets"]]
            }]
        },
        "type": "bar",
        "colors": ["#3498db"]
    }

def get_report_summary(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"value": metrics["total_tickets"], "label": "Total Tickets", "indicator": "blue"},
        {"value": metrics["active_agents"], "label": "Active Agents", "indicator": "green"},
        {"value": round(metrics["avg_sla"], 1), "label": "Avg SLA Compliance %", "indicator": "orange"}
    ]
