import json
from datetime import timedelta
from typing import Any, Dict, List, Optional

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime


class ClaimsStatusReport(Document):
    """Aggregated claims status snapshot for a given window."""

    def before_insert(self):  # type: ignore[override]
        self._ensure_dates()

    def before_save(self):  # type: ignore[override]
        self._ensure_dates()

    def _ensure_dates(self):
        if not getattr(self, "date_from", None) or not getattr(self, "date_to", None):
            today = getdate()
            if (self.period_type or "Daily") == "Weekly":
                self.date_to = today
                self.date_from = today - timedelta(days=6)
            else:  # Daily / Custom default
                self.date_from = today
                self.date_to = today

    @frappe.whitelist()
    def run_generation(self):
        """Populate KPI fields, chart data and HTML summary for this report."""
        self._ensure_dates()
        counts, chart = aggregate_claims(self.date_from, self.date_to)
        self.logged_count = counts.get("logged", 0)
        self.validated_count = counts.get("validated", 0)
        self.approved_count = counts.get("approved", 0)
        self.rejected_count = counts.get("rejected", 0)
        self.escalated_count = counts.get("escalated", 0)
        self.chart_json = json.dumps(chart or {})
        self.report_html = build_report_html(self, counts)
        self.generated_at = now_datetime()
        self.generated_by = frappe.session.user
        if not getattr(self, "title", None):
            self.title = f"Claims Status {self.date_from} \t {self.date_to}"
        self.save()
        return {"message": "ok", "counts": counts}


def aggregate_claims(date_from, date_to) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Aggregate Claim DocType records between the given dates.

    Uses the local Claim DocType and groups by the full lifecycle statuses
    (Submitted, Under Review, Pending Documentation, Medical Review, Validated,
    Approved, Rejected, Closed, Appealed, Settled, Reopened, Escalated).
    """

    lifecycle_statuses = [
        "Submitted",
        "Under Review",
        "Pending Documentation",
        "Medical Review",
        "Validated",
        "Approved",
        "Rejected",
        "Closed",
        "Appealed",
        "Settled",
        "Reopened",
        "Escalated",
    ]

    df, dt = getdate(date_from), getdate(date_to)
    claims = frappe.get_all(
        "Claim",
        filters={"creation": ["between", [df, dt]]},
        fields=["name", "claim_number", "status", "is_escalated"],
        limit=5000,
    )

    # High-level KPIs stored on the DocType
    counts: Dict[str, Any] = {"logged": 0, "validated": 0, "approved": 0, "rejected": 0, "escalated": 0}

    # Fine-grained lifecycle breakdown used for the dashboard + HTML
    status_breakdown: Dict[str, int] = {s: 0 for s in lifecycle_statuses}
    by_status_for_chart: Dict[str, int] = {}

    for row in claims:
        counts["logged"] += 1
        raw_status = (row.get("status") or "").strip()
        if not raw_status:
            continue

        status = raw_status
        if status in status_breakdown:
            status_breakdown[status] += 1

        by_status_for_chart[status] = by_status_for_chart.get(status, 0) + 1

        if status == "Validated":
            counts["validated"] += 1
        if status in {"Approved", "Settled"}:
            counts["approved"] += 1
        if status == "Rejected":
            counts["rejected"] += 1
        if row.get("is_escalated") or status == "Escalated":
            counts["escalated"] += 1

    # Attach full lifecycle breakdown so the HTML renderer can show all statuses
    counts["status_breakdown"] = status_breakdown

    chart = {
        "type": "bar",
        "data": {
            "labels": list(by_status_for_chart.keys()),
            "datasets": [
                {"name": "Claims", "values": [by_status_for_chart[s] for s in by_status_for_chart.keys()]},
            ],
        },
    }
    return counts, chart


def build_report_html(doc: "ClaimsStatusReport", counts: Dict[str, Any]) -> str:
    lifecycle_statuses = [
        "Submitted",
        "Under Review",
        "Pending Documentation",
        "Medical Review",
        "Validated",
        "Approved",
        "Rejected",
        "Closed",
        "Appealed",
        "Settled",
        "Reopened",
        "Escalated",
    ]

    status_breakdown: Dict[str, int] = counts.get("status_breakdown") or {}

    def card(label: str, value: Any, style: str = "") -> str:
        return (
            "<div style='display:inline-block;margin:6px;padding:10px;border:1px solid #ddd;border-radius:6px"
            f"{style}'><div style='font-size:12px;color:#666'>{label}</div>"
            f"<div style='font-size:18px;font-weight:600'>{value}</div></div>"
        )

    # Top-level KPI cards
    cards = "".join(
        [
            card("Total Claims", counts.get("logged", 0)),
            card("Validated", counts.get("validated", 0)),
            card("Approved", counts.get("approved", 0)),
            card("Rejected", counts.get("rejected", 0)),
            card("Escalated", counts.get("escalated", 0), style=";background:#ffe5e5"),
        ]
    )

    # Detailed lifecycle table covering all statuses
    rows = []
    for st in lifecycle_statuses:
        rows.append(
            f"<tr><td>{st}</td><td style='text-align:right'>{status_breakdown.get(st, 0)}</td></tr>"
        )
    table_html = (
        "<table class='table table-bordered' style='margin-top:12px'>"
        "<thead><tr><th>Status</th><th style='text-align:right'>Count</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )

    return f"<div><div style='margin-bottom:10px'>{cards}</div>{table_html}</div>"


def _build_pdf_html(doc: "ClaimsStatusReport") -> str:
    subtitle = f"{doc.period_type} | {doc.date_from} \t {doc.date_to}"
    header = f"<h2 style='margin:0'>WCFCB Claims Status Report</h2><div style='color:#666'>{subtitle}</div>"
    counts = {
        "logged": getattr(doc, "logged_count", 0) or 0,
        "validated": getattr(doc, "validated_count", 0) or 0,
        "approved": getattr(doc, "approved_count", 0) or 0,
        "rejected": getattr(doc, "rejected_count", 0) or 0,
        "escalated": getattr(doc, "escalated_count", 0) or 0,
    }
    fallback = "<div class='text-muted'>No claims found in this period.</div>"
    html_body = getattr(doc, "report_html", None) or build_report_html(doc, counts) or fallback
    return f"<div style='font-family:Inter,Arial,sans-serif'>{header}<hr/>{html_body}</div>"


def _attach_to_doc(doctype: str, name: str, filename: str, content: bytes):
    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": filename,
            "attached_to_doctype": doctype,
            "attached_to_name": name,
            "content": content,
            "is_private": 1,
        }
    )
    file_doc.save(ignore_permissions=True)
    return file_doc


def _get_role_emails(roles: List[str]) -> List[str]:
    if not roles:
        return []
    has_roles = frappe.get_all("Has Role", filters={"role": ["in", roles]}, fields=["parent"], limit=1000)
    user_ids = {r["parent"] for r in has_roles if r.get("parent")}
    if not user_ids:
        return []
    users = frappe.get_all(
        "User",
        filters={"name": ["in", list(user_ids)], "enabled": 1, "user_type": "System User"},
        fields=["email"],
        limit=1000,
    )
    return sorted({u["email"] for u in users if u.get("email")})


@frappe.whitelist()
def generate_report(name: str):
    """Wrapper used by the client script button."""
    doc = frappe.get_doc("Claims Status Report", name)
    return doc.run_generation()


@frappe.whitelist()
def generate_pdf(name: str) -> Dict[str, Any]:
    doc = frappe.get_doc("Claims Status Report", name)
    html = _build_pdf_html(doc)
    try:
        from frappe.utils.pdf import get_pdf

        pdf_bytes = get_pdf(html)
    except Exception:
        pdf_bytes = frappe.get_print(doc.doctype, doc.name, print_format=None, as_pdf=True)
    filename = f"Claims_Status_Report_{doc.name}.pdf"
    file_doc = _attach_to_doc(doc.doctype, doc.name, filename, pdf_bytes)
    return {"file_url": file_doc.file_url, "file_name": filename}


@frappe.whitelist()
def email_report(name: str, recipients: Optional[List[str]] | None = None) -> Dict[str, Any]:
    doc = frappe.get_doc("Claims Status Report", name)
    recipients = recipients or _get_role_emails(["Claims Officer", "WCFCB Manager", "System Manager"]) or []
    if not recipients:
        return {"ok": False, "message": "No recipients configured"}
    html = _build_pdf_html(doc)
    try:
        from frappe.utils.pdf import get_pdf

        pdf_bytes = get_pdf(html)
    except Exception:
        pdf_bytes = frappe.get_print(doc.doctype, doc.name, print_format=None, as_pdf=True)
    filename = f"Claims_Status_Report_{doc.name}.pdf"
    _attach_to_doc(doc.doctype, doc.name, filename, pdf_bytes)
    frappe.sendmail(
        recipients=recipients,
        subject=f"WCFCB Claims Status Report: {doc.period_type} ({doc.date_from} \t {doc.date_to})",
        message="Attached is the latest Claims Status Report.",
        attachments=[{"fname": filename, "fcontent": pdf_bytes}],
    )
    return {"ok": True, "recipients": recipients}


@frappe.whitelist()
def get_ai_insights(name: str, query: str) -> Dict[str, Any]:
    """Return WorkCom-style insights for a Claims Status Report.

    We build a compact JSON context with the current window, high-level KPIs,
    full lifecycle status breakdown for the window, and a small history of
    previous reports. This is then passed to the WorkCom (OpenAI) engine via
    EnhancedAIService.
    """

    doc = frappe.get_doc("Claims Status Report", name)

    # Recent reports with the same period_type for trend analysis
    history = frappe.get_all(
        "Claims Status Report",
        filters={"period_type": doc.period_type},
        fields=[
            "name",
            "date_from",
            "date_to",
            "logged_count",
            "validated_count",
            "approved_count",
            "rejected_count",
            "escalated_count",
        ],
        order_by="date_from desc",
        limit=12,
    )

    # Re-aggregate using the latest lifecycle logic so WorkCom sees the
    # detailed lifecycle breakdown as well as the top-level KPIs.
    try:
        current_counts, _ = aggregate_claims(doc.date_from, doc.date_to)
    except Exception:
        current_counts = {
            "logged": doc.logged_count,
            "validated": doc.validated_count,
            "approved": doc.approved_count,
            "rejected": doc.rejected_count,
            "escalated": doc.escalated_count,
            "status_breakdown": {},
        }

    context = {
        "window": {"from": str(doc.date_from), "to": str(doc.date_to)},
        "current": {
            "logged": current_counts.get("logged", doc.logged_count),
            "validated": current_counts.get("validated", doc.validated_count),
            "approved": current_counts.get("approved", doc.approved_count),
            "rejected": current_counts.get("rejected", doc.rejected_count),
            "escalated": current_counts.get("escalated", doc.escalated_count),
        },
        "status_breakdown": current_counts.get("status_breakdown", {}),
        "history": history,
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService

        ai = EnhancedAIService()
        answer = ai.generate_claims_status_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Claims Status Report AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure WorkCom/OpenAI settings in Enhanced AI Settings."
            )
        }


def schedule_daily_claims_status_reports():
    """Cron hook stub  kept lightweight to avoid failures during rollout.

    We intentionally keep this as a no-op logger for now; once daily
    automation is validated, this can be extended to auto-create and
    email reports similar to the other status report schedulers.
    """
    try:
        frappe.logger().info("ClaimsStatusReport daily scheduler ran")
    except Exception:
        pass


def schedule_weekly_claims_status_reports():
    try:
        frappe.logger().info("ClaimsStatusReport weekly scheduler ran")
    except Exception:
        pass

