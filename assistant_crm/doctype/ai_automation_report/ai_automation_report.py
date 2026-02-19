import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate, now_datetime
from datetime import time, date, timedelta
from typing import Dict, Any, List

from assistant_crm.assistant_crm.production.monitoring_analytics_system import get_monitoring_system
from assistant_crm.assistant_crm.api.integration_monitoring import get_data_quality_metrics

# Import business hours utilities
from assistant_crm.business_utils import is_business_hours


class AIAutomationReport(Document):
    def before_insert(self):
        self._ensure_title_and_dates()

    def validate(self):
        self._ensure_title_and_dates()

    def _ensure_title_and_dates(self):
        if not self.date_from or not self.date_to:
            today = getdate()
            self.date_from = frappe.utils.get_first_day(today)
            self.date_to = frappe.utils.get_last_day(today)
        if not getattr(self, "title", None):
            self.title = f"AI Automation Report: {self.date_from} → {self.date_to}"

    def run_generation(self):
        df = getdate(self.date_from)
        dt = getdate(self.date_to)
        self._build_metrics(df, dt)
        self.generated_at = now_datetime()
        self.generated_by = frappe.session.user if getattr(frappe, "session", None) else "Administrator"
        self.save(ignore_permissions=True)
        return {"status": "ok"}

    def _build_metrics(self, df: date, dt: date):
        auto = _aggregate_automation_events(df, dt)
        after_hours = _aggregate_after_hours(df, dt)
        docs = _aggregate_document_validation(df, dt)
        dq = _aggregate_data_quality(df, dt)
        health = _get_system_health()

        self.total_ai_automations = auto.get("total_events", 0)
        self.after_hours_tickets = after_hours.get("tickets_after_hours", 0)
        self.after_hours_ai_handled = after_hours.get("ai_after_hours", 0)
        self.invalid_documents_total = docs.get("total_validations", 0)
        self.invalid_documents_failed = docs.get("failed_validations", 0)
        self.data_quality_issues_total = dq.get("issues_total", 0)
        self.ai_failures_total = dq.get("ai_failures_total", 0)
        self.system_health_score = health.get("score", 0)
        self.system_health_status = health.get("status", "unknown")

        self.data_quality_snapshot = frappe.as_json(dq.get("snapshot", {}))
        self.automation_chart_json = frappe.as_json(auto.get("chart", {}))
        self.after_hours_chart_json = frappe.as_json(after_hours.get("chart", {}))
        self.document_validation_chart_json = frappe.as_json(docs.get("chart", {}))
        self.data_quality_chart_json = frappe.as_json(dq.get("chart", {}))
        self.ai_failure_chart_json = frappe.as_json(dq.get("failure_chart", {}))
        self.system_health_chart_json = frappe.as_json(health.get("chart", {}))

        self.rows_json = frappe.as_json({
            "automation": auto,
            "after_hours": after_hours,
            "documents": docs,
            "data_quality": dq,
            "system_health": health,
        })

        self.report_html = build_report_html(self, auto, after_hours, docs, dq, health)
        self.filters_json = frappe.as_json({
            "period_type": self.period_type,
            "date_from": str(df),
            "date_to": str(dt),
        })

    def generate_pdf(self) -> str:
        from frappe.utils.pdf import get_pdf

        html = _build_pdf_html(self)
        pdf_content = get_pdf(html)
        fname = f"{self.name}.pdf"
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": fname,
            "is_private": 1,
            "content": pdf_content,
            "attached_to_doctype": "AI Automation Report",
            "attached_to_name": self.name,
        })
        file_doc.save(ignore_permissions=True)
        # Return bare filename so it can be used with get_site_path('private', 'files', fname)
        return file_doc.file_name.split("/")[-1]

    def email_report(self):
        recipients = _get_role_emails(["CRM Administrator", "ICT"])
        if not recipients:
            return

        subject = self.title or f"AI Automation Report {self.name}"
        message = f"<p>Attached is the AI Automation Report for {self.date_from} to {self.date_to}.</p>"
        summary = _build_ai_email_summary(self)
        if summary:
            message += f"<p><strong>AI Summary</strong>: {frappe.utils.escape_html(summary)}</p>"

        fname = self.generate_pdf()
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            attachments=[{"fname": fname, "fcontent": frappe.read_file(frappe.get_site_path("private", "files", fname))}],
        )




@frappe.whitelist()
def generate_ai_automation_report(name: str) -> Dict[str, Any]:
    """Whitelisted wrapper to generate an AI Automation Report from the UI.

    Enforces write permission on the document before running aggregation.
    """
    doc = frappe.get_doc("AI Automation Report", name)
    if not doc.has_permission("write"):
        frappe.throw("Not permitted", frappe.PermissionError)
    return doc.run_generation()


@frappe.whitelist()
def generate_pdf(name: str) -> str:
    """Whitelisted export endpoint for Download PDF button.

    Returns the attached file name; the UI shows a success alert
    and the file is available in the Attachments section.
    """
    doc = frappe.get_doc("AI Automation Report", name)
    if not doc.has_permission("read"):
        frappe.throw("Not permitted", frappe.PermissionError)
    return doc.generate_pdf()


@frappe.whitelist()
def email_report(name: str) -> Dict[str, Any]:
    """Whitelisted endpoint used by the Email Report button."""
    doc = frappe.get_doc("AI Automation Report", name)
    if not doc.has_permission("read"):
        frappe.throw("Not permitted", frappe.PermissionError)
    doc.email_report()
    return {"status": "sent"}


def _aggregate_automation_events(df: date, dt: date) -> Dict[str, Any]:
    logs = frappe.get_all(
        "Automation Execution Log",
        filters={"execution_timestamp": ["between", [df, dt]]},
        fields=["execution_status"],
        limit=100000,
    )
    total = len(logs)
    success = sum(1 for l in logs if (l.execution_status or "").lower() == "success")
    failed = sum(1 for l in logs if (l.execution_status or "").lower() in {"failed", "error"})
    chart = {
        "type": "bar",
        "data": {
            "labels": ["Success", "Failed"],
            "datasets": [{"name": "Automation Events", "values": [success, failed]}],
        },
    }
    return {"total_events": total, "success": success, "failed": failed, "chart": chart}


def _is_business_hours(ts) -> bool:
    """Check if timestamp is within business hours using centralized utility."""
    return is_business_hours(ts)


def _aggregate_after_hours(df: date, dt: date) -> Dict[str, Any]:
    convs = frappe.get_all(
        "Unified Inbox Conversation",
        filters={"creation_time": ["between", [df, dt]]},
        fields=["creation_time", "ai_handled", "platform"],
        limit=100000,
    )
    after = [c for c in convs if not _is_business_hours(c.creation_time)]
    total_after = len(after)
    ai_after = sum(1 for c in after if c.ai_handled)

    by_platform: Dict[str, int] = {}
    for c in after:
        p = c.platform or "Unknown"
        by_platform[p] = by_platform.get(p, 0) + 1

    chart = {
        "type": "bar",
        "data": {
            "labels": list(by_platform.keys()),
            "datasets": [{"name": "After-Hours Tickets", "values": list(by_platform.values())}],
        },
    }
    return {
        "tickets_after_hours": total_after,
        "ai_after_hours": ai_after,
        "by_platform": by_platform,
        "chart": chart,
    }


def _aggregate_document_validation(df: date, dt: date) -> Dict[str, Any]:
    docs = frappe.get_all(
        "Document Validation",
        filters={"validation_date": ["between", [df, dt]]},
        fields=["validation_status"],
        limit=100000,
    )
    total = len(docs)
    status_counts: Dict[str, int] = {}
    for d in docs:
        s = (d.validation_status or "Unknown").title()
        status_counts[s] = status_counts.get(s, 0) + 1

    failed = status_counts.get("Failed", 0) + status_counts.get("Passed With Warnings", 0)
    chart = {
        "type": "pie",
        "data": {
            "labels": list(status_counts.keys()),
            "datasets": [{"name": "Validations", "values": list(status_counts.values())}],
        },
    }
    return {
        "total_validations": total,
        "status_counts": status_counts,
        "failed_validations": failed,
        "chart": chart,
    }


def _aggregate_data_quality(df: date, dt: date) -> Dict[str, Any]:
    snapshot = get_data_quality_metrics() or {}
    issues = snapshot.get("quality_issues") or []
    issues_total = sum(i.get("count", 0) for i in issues)

    dq_chart = {
        "type": "bar",
        "data": {
            "labels": [i.get("type") for i in issues],
            "datasets": [{"name": "Data Issues", "values": [i.get("count", 0) for i in issues]}],
        },
    }

    failures = frappe.get_all(
        "Failed Query Log",
        filters={"creation": ["between", [df, dt]]},
        fields=["failure_reason"],
        limit=100000,
    )
    ai_failures_total = len(failures)
    by_reason: Dict[str, int] = {}
    for f in failures:
        r = f.failure_reason or "Unknown"
        by_reason[r] = by_reason.get(r, 0) + 1

    failure_chart = {
        "type": "bar",
        "data": {
            "labels": list(by_reason.keys()),
            "datasets": [{"name": "AI Failures", "values": list(by_reason.values())}],
        },
    }

    return {
        "snapshot": snapshot,
        "issues_total": issues_total,
        "chart": dq_chart,
        "ai_failures_total": ai_failures_total,
        "failure_chart": failure_chart,
    }


def _get_system_health() -> Dict[str, Any]:
    try:
        health = get_monitoring_system().calculate_system_health()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AI Automation Report system health error")
        health = {"overall_score": 0, "status": "unknown", "factors": {}}

    score = float(health.get("overall_score") or 0)
    status = health.get("status") or "unknown"
    chart = {
        "type": "pie",
        "data": {
            "labels": ["Health", "Remaining"],
            "datasets": [{
                "name": "System Health",
                "values": [round(score, 1), max(0, 100 - round(score, 1))],
            }],
        },
    }
    return {
        "score": score,
        "status": status,
        "factors": health.get("factors") or {},
        "chart": chart,
    }


def build_report_html(doc, auto, after_hours, docs, dq, health) -> str:
    def card(title, value, subtitle=""):
        return f"""<div class='col-sm-4'><div class='border rounded p-3 mb-3'>
<h4 class='text-muted small'>{frappe._(title)}</h4><div class='h3'>{value}</div>
<div class='text-muted small'>{frappe._(subtitle)}</div></div></div>"""

    html = "<div class='container-fluid ai-automation-report'>"
    html += "<div class='row'>"
    html += card("Automation Events", auto.get("total_events", 0), "Total AI-triggered automations")
    html += card("After-Hours Tickets", after_hours.get("tickets_after_hours", 0), "Conversations started outside business hours")
    html += card("AI Failures", dq.get("ai_failures_total", 0), "Logged AI query failures")
    html += card("Invalid Documents", docs.get("failed_validations", 0), "Failed or warning validations")
    html += card("Data Quality Issues", dq.get("issues_total", 0), "Duplicates, missing data, outdated records")
    html += card("System Health", f"{health.get('score', 0):.1f}% ({health.get('status', 'unknown')})", "Overall AI system health gauge")
    html += "</div></div>"
    return html


def _build_pdf_html(doc) -> str:
    header = f"""<h2>AI Automation Report</h2><p>Period: {doc.date_from} → {doc.date_to}</p>"""
    # Use getattr to avoid AttributeError on older docs or when report_html
    # was not yet generated on this instance. Fall back to rebuilding from
    # rows_json if available.
    body = getattr(doc, "report_html", None)
    if not body:
        try:
            import json
            rows = json.loads(getattr(doc, "rows_json", "") or "{}")
            auto = rows.get("automation") or {}
            after_hours = rows.get("after_hours") or {}
            docs = rows.get("documents") or {}
            dq = rows.get("data_quality") or {}
            health = rows.get("system_health") or {}
            body = build_report_html(doc, auto, after_hours, docs, dq, health)
        except Exception:
            body = ""
    return header + (body or "")


def _get_role_emails(roles: List[str]) -> List[str]:
    if not roles:
        return []
    has = frappe.get_all("Has Role", filters={"role": ["in", roles]}, fields=["parent"], limit=1000)
    ids = {r.parent for r in has if r.parent}
    if not ids:
        return []
    users = frappe.get_all(
        "User",
        filters={"name": ["in", list(ids)], "enabled": 1, "user_type": "System User"},
        fields=["email"],
        limit=1000,
    )
    return sorted({u.email for u in users if u.email})


def _is_first_business_day(d: date) -> bool:
    first = frappe.utils.get_first_day(d)
    first_bd = first
    while first_bd.weekday() > 4:
        first_bd = frappe.utils.add_days(first_bd, 1)
    return d == first_bd


@frappe.whitelist()
def schedule_monthly_ai_automation_reports():
    today = getdate()
    if not _is_first_business_day(today):
        return

    prev = frappe.utils.add_months(today, -1)
    start = frappe.utils.get_first_day(prev)
    end = frappe.utils.get_last_day(prev)

    doc = frappe.new_doc("AI Automation Report")
    doc.period_type = "Monthly"
    doc.date_from = start
    doc.date_to = end
    doc.title = f"AI Automation Monthly: {start} → {end}"
    doc.insert(ignore_permissions=True)
    doc.run_generation()

    try:
        doc.email_report()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AI Automation Report email failed")



@frappe.whitelist()
def smoke_create_and_generate_ai_automation_report(period_type: str = "Monthly") -> Dict[str, Any]:
    """Create a test AI Automation Report for the previous period and run aggregation.

    Intended to be called via:
      bench --site <site> execute \
        assistant_crm.assistant_crm.doctype.ai_automation_report.ai_automation_report.smoke_create_and_generate_ai_automation_report
    """
    today = date.today()
    if (period_type or "").lower().startswith("month"):
        first_this_month = date(today.year, today.month, 1)
        last_prev_month = first_this_month - timedelta(days=1)
        df = date(last_prev_month.year, last_prev_month.month, 1)
        dt = last_prev_month
        ptype = "Monthly"
    else:
        dt = today
        df = today - timedelta(days=30)
        ptype = "Custom"

    doc = frappe.get_doc({
        "doctype": "AI Automation Report",
        "period_type": ptype,
        "date_from": df,
        "date_to": dt,
        "title": f"Smoke {ptype} AI Automation Report {df} to {dt}",
    })
    doc.insert(ignore_permissions=True)
    doc.run_generation()
    return {
        "name": doc.name,
        "period_type": doc.period_type,
        "date_from": str(doc.date_from),
        "date_to": str(doc.date_to),
        "total_ai_automations": doc.total_ai_automations,
        "after_hours_tickets": doc.after_hours_tickets,
        "invalid_documents_failed": doc.invalid_documents_failed,
        "data_quality_issues_total": doc.data_quality_issues_total,
        "ai_failures_total": doc.ai_failures_total,
        "system_health_score": doc.system_health_score,
    }


@frappe.whitelist()
def get_ai_insights(name: str, query: str) -> Dict[str, Any]:
    """Return WorkCom-style insights for an AI Automation Report."""
    doc = frappe.get_doc("AI Automation Report", name)
    history = frappe.get_all(
        "AI Automation Report",
        filters={"period_type": doc.period_type},
        fields=[
            "name",
            "date_from",
            "date_to",
            "total_ai_automations",
            "after_hours_tickets",
            "after_hours_ai_handled",
            "invalid_documents_total",
            "invalid_documents_failed",
            "data_quality_issues_total",
            "ai_failures_total",
            "system_health_score",
            "system_health_status",
        ],
        order_by="date_from desc",
        limit=12,
    )

    context = {
        "window": {
            "period_type": doc.period_type,
            "from": str(doc.date_from),
            "to": str(doc.date_to),
        },
        "current": {
            "total_ai_automations": int(doc.total_ai_automations or 0),
            "after_hours_tickets": int(doc.after_hours_tickets or 0),
            "after_hours_ai_handled": int(doc.after_hours_ai_handled or 0),
            "invalid_documents_total": int(doc.invalid_documents_total or 0),
            "invalid_documents_failed": int(doc.invalid_documents_failed or 0),
            "data_quality_issues_total": int(doc.data_quality_issues_total or 0),
            "ai_failures_total": int(doc.ai_failures_total or 0),
            "system_health_score": float(doc.system_health_score or 0),
            "system_health_status": doc.system_health_status or "",
        },
        "history": history,
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService

        ai = EnhancedAIService()
        answer = ai.generate_ai_automation_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AI Automation Report AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure WorkCom/OpenAI settings in Enhanced AI Settings."
            )
        }


def _build_ai_email_summary(doc) -> str:
    try:
        from assistant_crm.assistant_crm.services.gemini_service import GeminiService
    except Exception:
        return ""

    context = {
        "total_ai_automations": doc.total_ai_automations,
        "after_hours_tickets": doc.after_hours_tickets,
        "after_hours_ai_handled": doc.after_hours_ai_handled,
        "invalid_documents_failed": doc.invalid_documents_failed,
        "data_quality_issues_total": doc.data_quality_issues_total,
        "ai_failures_total": doc.ai_failures_total,
        "system_health_score": doc.system_health_score,
        "system_health_status": doc.system_health_status,
    }

    try:
        gem = GeminiService()
        return gem.generate_response_with_context(
            message=(
                "Provide a short, executive summary (3 sentences) of this AI Automation "
                "Report focusing on trends, correlations between data quality and AI "
                "behaviour, and any emerging risks."
            ),
            context=context,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AI Automation Report email summary error")
        return ""


