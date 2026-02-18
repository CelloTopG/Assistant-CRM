# -*- coding: utf-8 -*-
# Copyright (c) 2026, WCFCB and contributors
# For license information, please see license.txt
"""
Payout Summary Analysis - Native ERPNext Script Report

This report provides comprehensive payout summary analytics using
ERPNext Payment Entry, Salary Slip, and CoreBusiness Integration data.
Includes Antoine AI integration for insights.
"""

import json
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe import _
from frappe.utils import getdate, flt, fmt_money
from assistant_crm.report.report_utils import get_period_dates

from assistant_crm.services.corebusiness_integration_service import CoreBusinessIntegrationService


MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple:
    """Main report execution function.

    Returns:
        Tuple of (columns, data, message, chart, report_summary, skip_total_row)
    """
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data, summary_data = get_data(filters)
    chart = get_chart_data(summary_data)
    report_summary = get_report_summary(summary_data)

    return columns, data, None, chart, report_summary, False


def get_columns() -> List[Dict[str, Any]]:
    """Return column definitions for the report."""
    return [
        {
            "fieldname": "beneficiary_id",
            "label": _("Beneficiary ID"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "beneficiary_name",
            "label": _("Beneficiary Name"),
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "fieldname": "nrc_number",
            "label": _("NRC Number"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "employer_code",
            "label": _("Employer Code"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "employer_name",
            "label": _("Employer Name"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "benefit_type",
            "label": _("Benefit Type"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "gross_payout",
            "label": _("Gross Payout"),
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "fieldname": "deductions_total",
            "label": _("Deductions"),
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "fieldname": "net_payout",
            "label": _("Net Payout"),
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "fieldname": "payment_count",
            "label": _("Payments"),
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "fieldname": "exception_codes",
            "label": _("Exceptions"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "source",
            "label": _("Source"),
            "fieldtype": "Data",
            "width": 100,
        },
    ]


def get_data(filters: Dict) -> Tuple[List[Dict], Dict]:
    """Fetch and process data for the report."""
    date_from, date_to = _get_date_range(filters)

    # Initialize aggregation structures
    rows_by_beneficiary: Dict[str, Dict[str, Any]] = {}
    summary_data = _init_summary_data()

    # 1) Fetch from ERPNext Payment Entry (native doctype)
    _aggregate_payment_entries(rows_by_beneficiary, date_from, date_to, filters)

    # 2) Fetch from ERPNext Salary Slip (if applicable for periodic payouts)
    _aggregate_salary_slips(rows_by_beneficiary, date_from, date_to, filters)

    # 3) Fetch from Payment Status doctype (if exists)
    _aggregate_payment_status(rows_by_beneficiary, date_from, date_to)

    # 4) Fetch from CoreBusiness Integration Service (CBS API)
    _aggregate_cbs_payments(rows_by_beneficiary, date_from, date_to)

    # Process and enrich rows
    out_rows = _process_aggregated_rows(rows_by_beneficiary, summary_data, filters)

    # Finalize summary calculations
    _finalize_summary(summary_data)

    return out_rows, summary_data


def _get_date_range(filters: Dict) -> Tuple[date, date]:
    """Get date range from filters."""
    get_period_dates(filters)
    return getdate(filters.date_from), getdate(filters.date_to)


def _init_summary_data() -> Dict:
    """Initialize summary data structure."""
    return {
        "total_beneficiaries": 0,
        "total_gross": 0.0,
        "total_deductions": 0.0,
        "total_net": 0.0,
        "exceptions_count": 0,
        "erp_count": 0,
        "cbs_count": 0,
        "salary_slip_count": 0,
        "dependant_summary": {},
        "employer_breakdown": {},
        "benefit_type_breakdown": {},
        "exception_breakdown": {},
    }


def _finalize_summary(summary_data: Dict) -> None:
    """Calculate final KPIs from accumulated data."""
    total = summary_data["total_beneficiaries"]
    summary_data["avg_payout"] = summary_data["total_net"] / total if total else 0.0
    summary_data["avg_deduction"] = summary_data["total_deductions"] / total if total else 0.0
    summary_data["exception_rate"] = (
        (summary_data["exceptions_count"] / total * 100.0) if total else 0.0
    )


def _aggregate_payment_entries(
    agg: Dict[str, Dict[str, Any]], date_from: date, date_to: date, filters: Dict
) -> None:
    """Aggregate from ERPNext Payment Entry doctype."""
    if not frappe.db.table_exists("tabPayment Entry"):
        return

    pe_filters = {
        "docstatus": 1,
        "posting_date": ["between", [date_from, date_to]],
        "payment_type": "Pay",
    }

    # Apply employer filter if provided
    if filters.get("employer"):
        pe_filters["party"] = filters.get("employer")

    payment_entries = frappe.get_all(
        "Payment Entry",
        filters=pe_filters,
        fields=[
            "name", "posting_date", "party", "party_name", "party_type",
            "paid_amount", "total_taxes_and_charges", "reference_no",
            "mode_of_payment", "company"
        ],
        limit=5000,
    )

    for pe in payment_entries:
        # Use party as beneficiary key for now
        key = pe.get("party") or pe.get("name")
        row = agg.setdefault(key, _create_empty_row(key))

        gross = flt(pe.get("paid_amount", 0)) + flt(pe.get("total_taxes_and_charges", 0))
        ded = flt(pe.get("total_taxes_and_charges", 0))
        net = flt(pe.get("paid_amount", 0))

        row["gross_payout"] += gross
        row["deductions_total"] += ded
        row["net_payout"] += net
        row["payment_count"] += 1
        row["sources"].add("Payment Entry")

        if not row["beneficiary_name"] and pe.get("party_name"):
            row["beneficiary_name"] = pe.get("party_name")
        if not row["employer_code"] and pe.get("company"):
            row["employer_code"] = pe.get("company")
            row["employer_name"] = pe.get("company")


def _aggregate_salary_slips(
    agg: Dict[str, Dict[str, Any]], date_from: date, date_to: date, filters: Dict
) -> None:
    """Aggregate from ERPNext Salary Slip doctype (for payroll-based payouts)."""
    if not frappe.db.table_exists("tabSalary Slip"):
        return

    ss_filters = {
        "docstatus": 1,
        "posting_date": ["between", [date_from, date_to]],
    }

    if filters.get("employer"):
        ss_filters["company"] = filters.get("employer")

    salary_slips = frappe.get_all(
        "Salary Slip",
        filters=ss_filters,
        fields=[
            "name", "employee", "employee_name", "posting_date",
            "gross_pay", "total_deduction", "net_pay", "company"
        ],
        limit=5000,
    )

    for ss in salary_slips:
        key = ss.get("employee") or ss.get("name")
        row = agg.setdefault(key, _create_empty_row(key))

        row["gross_payout"] += flt(ss.get("gross_pay", 0))
        row["deductions_total"] += flt(ss.get("total_deduction", 0))
        row["net_payout"] += flt(ss.get("net_pay", 0))
        row["payment_count"] += 1
        row["sources"].add("Salary Slip")

        if not row["beneficiary_name"] and ss.get("employee_name"):
            row["beneficiary_name"] = ss.get("employee_name")
        if not row["employer_code"] and ss.get("company"):
            row["employer_code"] = ss.get("company")
            row["employer_name"] = ss.get("company")


def _aggregate_payment_status(
    agg: Dict[str, Dict[str, Any]], date_from: date, date_to: date
) -> None:
    """Aggregate from custom Payment Status doctype (if exists)."""
    if not frappe.db.table_exists("tabPayment Status"):
        return

    payment_statuses = frappe.get_all(
        "Payment Status",
        filters={
            "status": "Paid",
            "payment_date": ["between", [date_from, date_to]],
        },
        fields=["name", "payment_id", "payment_date", "amount", "beneficiary", "reference_number", "currency"],
        limit=5000,
    )

    for ps in payment_statuses:
        key = ps.get("beneficiary") or ps.get("name")
        row = agg.setdefault(key, _create_empty_row(key))

        net = flt(ps.get("amount", 0))
        row["gross_payout"] += net  # Payment Status has single amount, treat as gross=net
        row["net_payout"] += net
        row["payment_count"] += 1
        row["sources"].add("Payment Status")


def _aggregate_cbs_payments(
    agg: Dict[str, Dict[str, Any]], date_from: date, date_to: date
) -> None:
    """Aggregate from CoreBusiness Integration Service."""
    try:
        cbs = CoreBusinessIntegrationService()
        cbs_payments = cbs.get_payments(
            date_from=str(date_from), date_to=str(date_to), status="Paid", limit=5000
        ) or []
    except Exception as e:
        frappe.log_error(f"CBS payments aggregation error: {str(e)}", "Payout Summary Analysis")
        return

    for p in cbs_payments:
        key = (
            p.get("beneficiary_number") or p.get("beneficiary_id") or
            p.get("nrc") or p.get("nrc_number") or p.get("beneficiary_name") or
            p.get("id") or "UNKNOWN"
        )
        row = agg.setdefault(key, _create_empty_row(key))

        # Parse deductions
        deductions_total = 0.0
        if isinstance(p.get("deductions"), list):
            for d in p["deductions"]:
                deductions_total += flt(d.get("amount", 0))
        elif isinstance(p.get("deductions"), dict):
            for _, v in p["deductions"].items():
                deductions_total += flt(v)

        gross = flt(p.get("gross_amount", 0))
        net = flt(p.get("net_amount", p.get("amount", 0)))
        ded = deductions_total or flt(p.get("deductions_total", 0))

        if not gross and (net or ded):
            gross = max(0.0, net + ded)

        row["gross_payout"] += gross
        row["deductions_total"] += ded
        row["net_payout"] += net
        row["payment_count"] += 1
        row["sources"].add("CoreBusiness")

        # Carry forward identity hints
        if not row["beneficiary_id"] and p.get("beneficiary_number"):
            row["beneficiary_id"] = p.get("beneficiary_number")
        if not row["nrc_number"] and (p.get("nrc") or p.get("nrc_number")):
            row["nrc_number"] = p.get("nrc") or p.get("nrc_number")
        if not row["beneficiary_name"] and p.get("beneficiary_name"):
            row["beneficiary_name"] = p.get("beneficiary_name")


def _create_empty_row(key: str) -> Dict[str, Any]:
    """Create an empty row for aggregation."""
    return {
        "beneficiary_key": key,
        "beneficiary_id": None,
        "beneficiary_name": None,
        "nrc_number": None,
        "employer_code": None,
        "employer_name": None,
        "benefit_type": None,
        "gross_payout": 0.0,
        "deductions_total": 0.0,
        "net_payout": 0.0,
        "payment_count": 0,
        "exceptions": False,
        "exception_codes": [],
        "sources": set(),
    }


def _process_aggregated_rows(
    agg: Dict[str, Dict[str, Any]], summary_data: Dict, filters: Dict
) -> List[Dict]:
    """Process aggregated rows, compute exceptions, and update summary."""
    out_rows: List[Dict] = []

    employer_filter = (filters.get("employer") or "").strip().lower()

    for _key, row in agg.items():
        # Apply employer filter if provided
        if employer_filter:
            emp_code = (row.get("employer_code") or "").lower()
            emp_name = (row.get("employer_name") or "").lower()
            if employer_filter not in emp_code and employer_filter not in emp_name:
                continue

        # Compute exceptions
        _compute_exceptions(row)

        # Update summary data
        summary_data["total_beneficiaries"] += 1
        summary_data["total_gross"] += flt(row.get("gross_payout", 0))
        summary_data["total_deductions"] += flt(row.get("deductions_total", 0))
        summary_data["total_net"] += flt(row.get("net_payout", 0))

        if row.get("exceptions"):
            summary_data["exceptions_count"] += 1

        # Track by source
        if "Payment Entry" in row.get("sources", set()):
            summary_data["erp_count"] += 1
        if "Salary Slip" in row.get("sources", set()):
            summary_data["salary_slip_count"] += 1
        if "CoreBusiness" in row.get("sources", set()):
            summary_data["cbs_count"] += 1

        # Employer breakdown
        emp_key = row.get("employer_code") or row.get("employer_name") or "Unknown"
        eb = summary_data["employer_breakdown"].setdefault(emp_key, {"count": 0, "net": 0.0})
        eb["count"] += 1
        eb["net"] += flt(row.get("net_payout", 0))

        # Benefit type breakdown
        bt_key = row.get("benefit_type") or "General"
        bt = summary_data["benefit_type_breakdown"].setdefault(bt_key, {"count": 0, "net": 0.0})
        bt["count"] += 1
        bt["net"] += flt(row.get("net_payout", 0))

        # Exception breakdown
        for ex_code in row.get("exception_codes", []):
            summary_data["exception_breakdown"][ex_code] = (
                summary_data["exception_breakdown"].get(ex_code, 0) + 1
            )

        # Build output row
        out_rows.append({
            "beneficiary_id": row.get("beneficiary_id") or row.get("beneficiary_key"),
            "beneficiary_name": row.get("beneficiary_name") or row.get("beneficiary_key"),
            "nrc_number": row.get("nrc_number"),
            "employer_code": row.get("employer_code"),
            "employer_name": row.get("employer_name"),
            "benefit_type": row.get("benefit_type"),
            "gross_payout": flt(row.get("gross_payout", 0)),
            "deductions_total": flt(row.get("deductions_total", 0)),
            "net_payout": flt(row.get("net_payout", 0)),
            "payment_count": int(row.get("payment_count", 0)),
            "exception_codes": ", ".join(row.get("exception_codes", [])),
            "source": ", ".join(sorted(row.get("sources", set()))),
        })

    # Sort by net payout descending
    out_rows.sort(key=lambda x: flt(x.get("net_payout", 0)), reverse=True)
    return out_rows


def _compute_exceptions(row: Dict) -> None:
    """Compute exception codes for a payout row."""
    exception_codes: List[str] = []

    if flt(row.get("deductions_total", 0)) > flt(row.get("gross_payout", 0)):
        exception_codes.append("DEDUCTION_EXCEEDS_GROSS")

    if flt(row.get("net_payout", 0)) < 0:
        exception_codes.append("NEGATIVE_NET")

    if int(row.get("payment_count", 0)) > 1:
        exception_codes.append("MULTIPLE_PAYMENTS")

    if flt(row.get("gross_payout", 0)) == 0 and flt(row.get("net_payout", 0)) == 0:
        exception_codes.append("ZERO_PAYOUT")

    row["exceptions"] = bool(exception_codes)
    row["exception_codes"] = exception_codes


# =====================
# Chart & Summary
# =====================

def get_chart_data(summary_data: Dict) -> Dict:
    """Generate chart data for the report."""
    return {
        "type": "bar",
        "data": {
            "labels": ["Gross Payout", "Deductions", "Net Payout"],
            "datasets": [
                {
                    "name": "Amount (ZMW)",
                    "values": [
                        round(summary_data.get("total_gross", 0), 2),
                        round(summary_data.get("total_deductions", 0), 2),
                        round(summary_data.get("total_net", 0), 2),
                    ],
                },
            ],
        },
        "colors": ["#5e64ff"],
    }


def get_report_summary(summary_data: Dict) -> List[Dict]:
    """Generate report summary cards."""
    exception_rate = round(summary_data.get("exception_rate", 0.0), 1)

    return [
        {
            "value": summary_data.get("total_beneficiaries", 0),
            "label": _("Beneficiaries Paid"),
            "datatype": "Int",
        },
        {
            "value": round(summary_data.get("total_gross", 0), 2),
            "label": _("Total Gross (ZMW)"),
            "datatype": "Currency",
            "indicator": "blue",
        },
        {
            "value": round(summary_data.get("total_deductions", 0), 2),
            "label": _("Total Deductions (ZMW)"),
            "datatype": "Currency",
            "indicator": "orange",
        },
        {
            "value": round(summary_data.get("total_net", 0), 2),
            "label": _("Total Net (ZMW)"),
            "datatype": "Currency",
            "indicator": "green",
        },
        {
            "value": round(summary_data.get("avg_payout", 0), 2),
            "label": _("Avg Payout (ZMW)"),
            "datatype": "Currency",
        },
        {
            "value": summary_data.get("exceptions_count", 0),
            "label": _("Exceptions"),
            "datatype": "Int",
            "indicator": "red" if summary_data.get("exceptions_count", 0) > 0 else "gray",
        },
        {
            "value": exception_rate,
            "label": _("Exception Rate %"),
            "datatype": "Percent",
            "indicator": "red" if exception_rate > 5 else ("yellow" if exception_rate > 2 else "green"),
        },
        {
            "value": summary_data.get("erp_count", 0) + summary_data.get("cbs_count", 0),
            "label": _("Data Sources"),
            "datatype": "Int",
            "indicator": "blue",
        },
    ]


# =====================
# Chart Endpoints
# =====================

@frappe.whitelist()
def get_overview_chart(filters: str) -> Dict:
    """Get overview chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters)
    _, summary_data = get_data(filters)
    return get_chart_data(summary_data)


@frappe.whitelist()
def get_employer_breakdown_chart(filters: str) -> Dict:
    """Get employer breakdown chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters)
    _, summary_data = get_data(filters)

    emp_breakdown = summary_data.get("employer_breakdown", {})
    # Sort by net payout and take top 12
    sorted_employers = sorted(emp_breakdown.items(), key=lambda x: x[1]["net"], reverse=True)[:12]
    labels = [e[0] for e in sorted_employers]
    values = [round(e[1]["net"], 2) for e in sorted_employers]

    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{"name": "Net Payout (ZMW)", "values": values}],
        },
        "colors": ["#28a745"],
    }


@frappe.whitelist()
def get_benefit_type_chart(filters: str) -> Dict:
    """Get benefit type breakdown chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters)
    _, summary_data = get_data(filters)

    bt_breakdown = summary_data.get("benefit_type_breakdown", {})
    labels = list(bt_breakdown.keys())[:10]
    values = [round(bt_breakdown[k]["net"], 2) for k in labels]

    return {
        "type": "pie",
        "data": {
            "labels": labels,
            "datasets": [{"name": "Net Payout (ZMW)", "values": values}],
        },
        "colors": ["#5e64ff", "#ffa00a", "#28a745", "#dc3545", "#17a2b8"],
    }


@frappe.whitelist()
def get_exception_chart(filters: str) -> Dict:
    """Get exception breakdown chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters)
    _, summary_data = get_data(filters)

    ex_breakdown = summary_data.get("exception_breakdown", {})
    labels = list(ex_breakdown.keys())
    values = [ex_breakdown[k] for k in labels]

    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{"name": "Count", "values": values}],
        },
        "colors": ["#dc3545"],
    }


# =====================
# Antoine AI Integration
# =====================

@frappe.whitelist()
def get_ai_insights(filters: str, query: str) -> Dict:
    """Return Antoine-style AI insights for Payout Summary Analysis.

    Builds a JSON context with payout KPIs, breakdowns, and sample rows,
    then passes it to Antoine via EnhancedAIService.
    """
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters)

    # Get current data
    rows, summary_data = get_data(filters)
    date_from, date_to = _get_date_range(filters)

    # Get history from previous Payout Summary Reports (if doctype exists)
    history = []
    if frappe.db.table_exists("tabPayout Summary Report"):
        history = frappe.get_all(
            "Payout Summary Report",
            filters={"period_type": filters.get("period_type", "Monthly")},
            fields=[
                "name", "date_from", "date_to", "total_beneficiaries_paid",
                "total_gross_payout", "total_deductions", "total_net_payout",
                "exceptions_count",
            ],
            order_by="date_from desc",
            limit=12,
        )

    # Build payroll month label
    period_type = filters.get("period_type", "Monthly")
    if period_type == "Monthly":
        month = filters.get("month")
        year = filters.get("year")
        payroll_month = f"{month} {year}" if month and year else f"{date_from} - {date_to}"
    else:
        payroll_month = f"{date_from} to {date_to}"

    context = {
        "window": {
            "period_type": period_type,
            "from": str(date_from),
            "to": str(date_to),
            "payroll_month": payroll_month,
        },
        "current": {
            "total_beneficiaries_paid": summary_data.get("total_beneficiaries", 0),
            "total_gross_payout": round(summary_data.get("total_gross", 0), 2),
            "total_deductions": round(summary_data.get("total_deductions", 0), 2),
            "total_net_payout": round(summary_data.get("total_net", 0), 2),
            "exceptions_count": summary_data.get("exceptions_count", 0),
            "avg_payout": round(summary_data.get("avg_payout", 0), 2),
            "exception_rate": round(summary_data.get("exception_rate", 0), 2),
            "erp_source_count": summary_data.get("erp_count", 0),
            "cbs_source_count": summary_data.get("cbs_count", 0),
        },
        "employer_breakdown": summary_data.get("employer_breakdown", {}),
        "benefit_type_breakdown": summary_data.get("benefit_type_breakdown", {}),
        "exception_breakdown": summary_data.get("exception_breakdown", {}),
        "sample_rows": rows[:100],  # Include sample rows for AI context
        "history": [
            {
                "name": h.name,
                "date_from": str(h.date_from) if h.date_from else "",
                "date_to": str(h.date_to) if h.date_to else "",
                "total_beneficiaries_paid": int(h.total_beneficiaries_paid or 0),
                "total_gross_payout": float(h.total_gross_payout or 0),
                "total_deductions": float(h.total_deductions or 0),
                "total_net_payout": float(h.total_net_payout or 0),
                "exceptions_count": int(h.exceptions_count or 0),
            }
            for h in history
        ],
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService

        ai = EnhancedAIService()
        answer = ai.generate_payout_summary_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Payout Summary Analysis AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure Antoine/OpenAI settings in Enhanced AI Settings."
            )
        }


# =====================
# PDF & Email (Optional)
# =====================

@frappe.whitelist()
def generate_pdf(filters: str) -> Dict:
    """Generate a PDF for the payout summary analysis."""
    from frappe.utils.pdf import get_pdf

    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters)
    rows, summary_data = get_data(filters)
    date_from, date_to = _get_date_range(filters)

    html = _build_pdf_html(rows, summary_data, date_from, date_to, filters)
    pdf_bytes = get_pdf(html)

    # Generate filename
    period_type = filters.get("period_type", "Monthly")
    if period_type == "Monthly":
        fname = f"Payout_Summary_{filters.get('month', '')}_{filters.get('year', '')}.pdf".replace(" ", "_")
    else:
        fname = f"Payout_Summary_{date_from}_{date_to}.pdf"

    # Save as attachment
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "is_private": 1,
        "content": pdf_bytes,
    })
    file_doc.save(ignore_permissions=True)

    return {"file_url": file_doc.file_url, "file_name": file_doc.file_name}


def _build_pdf_html(rows: List, summary_data: Dict, date_from, date_to, filters: Dict) -> str:
    """Build HTML for PDF generation."""
    style = """
    <style>
    body { font-family: Inter, Arial, sans-serif; font-size:12px; color:#1f2937; }
    h1 { font-size: 18px; margin: 0 0 4px 0; }
    h2 { font-size: 14px; margin: 16px 0 8px 0; }
    .meta { color:#6b7280; font-size:11px; }
    .cards { display:flex; gap:8px; margin:12px 0; flex-wrap: wrap; }
    .card { border:1px solid #e5e7eb; border-radius:6px; padding:10px; min-width:150px; }
    .label { font-size:11px; color:#6b7280; }
    .value { font-size:16px; font-weight:600; }
    table { border-collapse: collapse; width: 100%; margin-top: 10px; }
    th, td { border: 1px solid #e5e7eb; padding: 6px; text-align: left; font-size: 11px; }
    th { background: #f3f4f6; }
    </style>
    """

    header = f"""
    <div>
      <h1>WCFCB Payout Summary Analysis</h1>
      <div class="meta">
        Period: {frappe.utils.formatdate(date_from)} to {frappe.utils.formatdate(date_to)}
        &nbsp;|&nbsp; Type: {filters.get('period_type', 'Monthly')}
        &nbsp;|&nbsp; Generated: {frappe.utils.format_datetime(frappe.utils.now_datetime())}
      </div>
    </div>
    """

    cards = f"""
    <div class="cards">
      <div class="card"><div class="label">Beneficiaries Paid</div><div class="value">{summary_data.get('total_beneficiaries', 0)}</div></div>
      <div class="card"><div class="label">Total Gross (ZMW)</div><div class="value">{fmt_money(summary_data.get('total_gross', 0))}</div></div>
      <div class="card"><div class="label">Total Deductions (ZMW)</div><div class="value">{fmt_money(summary_data.get('total_deductions', 0))}</div></div>
      <div class="card"><div class="label">Total Net (ZMW)</div><div class="value">{fmt_money(summary_data.get('total_net', 0))}</div></div>
      <div class="card"><div class="label">Exceptions</div><div class="value">{summary_data.get('exceptions_count', 0)}</div></div>
    </div>
    """

    # Build table
    table_rows = ""
    for r in rows[:500]:
        table_rows += f"""
        <tr>
            <td>{frappe.utils.escape_html(r.get('beneficiary_name') or r.get('beneficiary_id') or '')}</td>
            <td>{frappe.utils.escape_html(r.get('nrc_number') or '')}</td>
            <td>{frappe.utils.escape_html(r.get('employer_name') or r.get('employer_code') or '')}</td>
            <td style="text-align:right">{fmt_money(r.get('gross_payout', 0))}</td>
            <td style="text-align:right">{fmt_money(r.get('deductions_total', 0))}</td>
            <td style="text-align:right">{fmt_money(r.get('net_payout', 0))}</td>
            <td style="text-align:center">{r.get('payment_count', 0)}</td>
            <td>{frappe.utils.escape_html(r.get('exception_codes') or '')}</td>
        </tr>
        """

    table = f"""
    <h2>Beneficiary Payouts</h2>
    <table>
        <thead>
            <tr>
                <th>Beneficiary</th>
                <th>NRC</th>
                <th>Employer</th>
                <th>Gross</th>
                <th>Deductions</th>
                <th>Net</th>
                <th>Payments</th>
                <th>Exceptions</th>
            </tr>
        </thead>
        <tbody>
            {table_rows if table_rows else '<tr><td colspan="8" class="text-muted">No payouts found.</td></tr>'}
        </tbody>
    </table>
    """

    return style + header + cards + table

