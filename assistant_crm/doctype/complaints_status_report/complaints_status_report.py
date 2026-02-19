import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days, now_datetime
from frappe.utils.pdf import get_pdf



CATEGORY_CLAIMS = "Claims"
CATEGORY_COMPLIANCE = "Compliance"
CATEGORY_GENERAL = "General"


class ComplaintsStatusReport(Document):
    def before_insert(self):
        self._ensure_dates()

    def before_save(self):
        # Do not auto-run heavy aggregation on every save; buttons/whitelist handle it.
        self._ensure_dates()

    # ----- Public API (whitelisted) -----
    @frappe.whitelist()
    def run_generation(self):
        self._ensure_dates()
        counts, platform_counts, rows = aggregate_complaints(self.date_from, self.date_to)
        self.total_count = counts.get("total", 0)
        self.claims_count = counts.get("claims", 0)
        self.compliance_count = counts.get("compliance", 0)
        self.general_count = counts.get("general", 0)
        self.escalated_count = counts.get("escalated", 0)
        self.resolved_count = counts.get("resolved", 0)
        self.open_count = counts.get("open", 0)

        # Category bar chart
        self.chart_json = json.dumps({
            "data": {
                "labels": [CATEGORY_CLAIMS, CATEGORY_COMPLIANCE, CATEGORY_GENERAL],
                "datasets": [{
                    "name": "Complaints",
                    "values": [self.claims_count or 0, self.compliance_count or 0, self.general_count or 0],
                }]
            },
            "type": "bar"
        })
        # Status pie chart
        self.status_chart_json = json.dumps({
            "data": {
                "labels": ["Open", "Resolved", "Escalated"],
                "datasets": [{
                    "name": "Status",
                    "values": [self.open_count or 0, self.resolved_count or 0, self.escalated_count or 0],
                }]
            },
            "type": "pie"
        })

        # Stacked platform x category chart
        platforms = sorted({(r.get("platform") or "Unknown") for r in rows})
        def series_for(cat: str):
            vals = []
            for p in platforms:
                vals.append(sum(1 for r in rows if (r.get("platform") or "Unknown") == p and r.get("final_category") == cat))
            return vals
        self.stacked_chart_json = json.dumps({
            "data": {
                "labels": platforms,
                "datasets": [
                    {"name": CATEGORY_CLAIMS, "chartType": "bar", "values": series_for(CATEGORY_CLAIMS)},
                    {"name": CATEGORY_COMPLIANCE, "chartType": "bar", "values": series_for(CATEGORY_COMPLIANCE)},
                    {"name": CATEGORY_GENERAL, "chartType": "bar", "values": series_for(CATEGORY_GENERAL)},
                ]
            },
            "type": "bar",
            "barOptions": {"stacked": 1}
        })

        # Trend chart across last 8 windows of current period type
        trend_cfg = build_trend_chart(self.period_type or "Weekly", getdate(self.date_to), windows=8)
        self.trend_chart_json = json.dumps(trend_cfg)

        # Rows for manual overrides panel (limited)
        self.rows_json = json.dumps(rows[:200])

        # Report HTML (compact summary)
        self.report_html = build_report_html(self, platform_counts)
        self.generated_at = now_datetime()
        self.generated_by = frappe.session.user
        self.save()
        return {"message": "ok", "counts": counts}

    @frappe.whitelist()
    def generate_pdf(self) -> str:
        html = _build_pdf_html(self)
        # Attach generated PDF to the document and return the file name
        pdf_bytes = get_pdf(html)
        filename = f"Complaints_Status_Report_{self.name}.pdf"
        _attach_to_doc(self.doctype, self.name, filename, pdf_bytes)
        return filename

    @frappe.whitelist()
    def email_report(self, recipients: Optional[List[str]] = None) -> Dict[str, Any]:
        recipients = recipients or _get_role_emails(["Customer Service", "Corporate Affairs"]) or []
        if not recipients:
            return {"message": "no-recipients"}
        try:
            html = _build_pdf_html(self)
            pdf_bytes = get_pdf(html)
            filename = f"Complaints_Status_Report_{self.name}.pdf"
            _attach_to_doc(self.doctype, self.name, filename, pdf_bytes)
            frappe.sendmail(
                recipients=recipients,
                subject=f"WCFCB Complaints Status Report: {self.period_type} ({self.date_from} → {self.date_to})",
                message="Attached is the latest Complaints Status Report.",
                attachments=[{
                    "fname": filename,
                    "fcontent": pdf_bytes,
                }],
            )
            return {"message": "sent", "recipients": recipients}
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Complaints Status Report: email_report")
            frappe.throw(f"Failed to email report: {e}")

    @frappe.whitelist()
    def get_recipients(self) -> Dict[str, Any]:
        """Return default recipients based on Customer Service / Corporate Affairs roles.

        Used by the client to show an email preview dialog before sending.
        """
        recips = _get_role_emails(["Customer Service", "Corporate Affairs"]) or []
        return {"recipients": recips}



# ----- Schedulers -----

def _weekly_window() -> Tuple[date, date]:
    today = getdate()
    start = add_days(today, -6)
    return (start, today)


def _monthly_window() -> Tuple[date, date]:
    today = getdate()
    start = getdate(f"{today.year}-{today.month}-01")
    return (start, today)


@frappe.whitelist()
def schedule_weekly_complaints_status_reports():
    df, dt = _weekly_window()
    doc = frappe.new_doc("Complaints Status Report")
    doc.period_type = "Weekly"
    doc.date_from = df
    doc.date_to = dt
    doc.title = f"Complaints Weekly: {df} → {dt}"
    doc.insert(ignore_permissions=True)
    doc.run_generation()
    doc.email_report()


@frappe.whitelist()
def schedule_monthly_complaints_status_reports():
    df, dt = _monthly_window()
    doc = frappe.new_doc("Complaints Status Report")
    doc.period_type = "Monthly"
    doc.date_from = df
    doc.date_to = dt
    doc.title = f"Complaints Monthly: {df} → {dt}"
    doc.insert(ignore_permissions=True)
    doc.run_generation()
    doc.email_report()


# ----- Aggregation -----

def aggregate_complaints(date_from: Any, date_to: Any) -> Tuple[Dict[str, int], Dict[str, int], List[Dict[str, Any]]]:
    df = getdate(date_from)
    dt = getdate(date_to)

    counts = {
        "total": 0,
        "claims": 0,
        "compliance": 0,
        "general": 0,
        "escalated": 0,
        "resolved": 0,
        "open": 0,
    }
    platform_counts: Dict[str, int] = {}
    rows: List[Dict[str, Any]] = []

    # Escalations index (by conversation or reference)
    conv_escalations, ref_escalations = _build_escalation_index(df, dt)

    # Conversations (primary source)
    conversations = _get_conversations(df, dt)
    seen_conversations = set(x.get("name") for x in conversations)
    meta_conv = frappe.get_meta("Unified Inbox Conversation")
    has_conv_override = meta_conv.has_field("complaint_category_override")

    for c in conversations:
        override = c.get("complaint_category_override") if has_conv_override else None
        esc = conv_escalations.get(c.get("name"))
        dept = esc.get("department") if esc else None
        auto_category = classify_complaint(
            text=" ".join(filter(None, [c.get("subject"), c.get("last_message_preview"), c.get("tags")])),
            department=dept,
        )
        final_category = override if override in {CATEGORY_CLAIMS, CATEGORY_COMPLIANCE, CATEGORY_GENERAL} else auto_category
        status = (c.get("status") or "").lower()
        platform = c.get("platform") or "Unknown"
        escalated = bool(c.get("escalated_at") or esc)

        platform_counts[platform] = platform_counts.get(platform, 0) + 1
        counts["total"] += 1
        if final_category == CATEGORY_CLAIMS:
            counts["claims"] += 1
        elif final_category == CATEGORY_COMPLIANCE:
            counts["compliance"] += 1
        else:
            counts["general"] += 1

        if escalated:
            counts["escalated"] += 1
        if status in {"resolved", "closed"}:
            counts["resolved"] += 1
        else:
            counts["open"] += 1

        rows.append({
            "doctype": "Unified Inbox Conversation",
            "name": c.get("name"),
            "platform": platform,
            "status": status,
            "subject": c.get("subject"),
            "auto_category": auto_category,
            "override_category": override,
            "final_category": final_category,
            "escalated": escalated,
            "department": dept,
        })

    # Issues without conversations (secondary source)
    issues = _get_issues(df, dt)
    meta_issue = frappe.get_meta("Issue")
    has_conv_field = meta_issue.has_field("custom_conversation_id")
    has_src_field = meta_issue.has_field("custom_platform_source")
    has_issue_override = meta_issue.has_field("complaint_category_override")

    for i in issues:
        conv_id = (i.get("custom_conversation_id") or "") if has_conv_field else ""
        if conv_id and _conversation_exists(conv_id):
            continue  # de-duplicate

        override = i.get("complaint_category_override") if has_issue_override else None
        esc = ref_escalations.get(("Issue", i.get("name")))
        dept = esc.get("department") if esc else None
        text = " ".join(filter(None, [i.get("subject"), i.get("description")]))
        auto_category = classify_complaint(text=text, department=dept)
        final_category = override if override in {CATEGORY_CLAIMS, CATEGORY_COMPLIANCE, CATEGORY_GENERAL} else auto_category
        platform = (i.get("custom_platform_source") if has_src_field else None) or "Unknown"
        status = (i.get("status") or "").lower()
        escalated = bool(esc)

        platform_counts[platform] = platform_counts.get(platform, 0) + 1
        counts["total"] += 1
        if final_category == CATEGORY_CLAIMS:
            counts["claims"] += 1
        elif final_category == CATEGORY_COMPLIANCE:
            counts["compliance"] += 1
        else:
            counts["general"] += 1

        if escalated:
            counts["escalated"] += 1
        if status in {"resolved", "closed"}:
            counts["resolved"] += 1
        else:
            counts["open"] += 1

        rows.append({
            "doctype": "Issue",
            "name": i.get("name"),
            "platform": platform,
            "status": status,
            "subject": i.get("subject"),
            "auto_category": auto_category,
            "override_category": override,
            "final_category": final_category,
            "escalated": escalated,
            "department": dept,
        })

    return counts, platform_counts, rows


def _get_conversations(df: date, dt: date) -> List[Dict[str, Any]]:
    fields = [
        "name",
        "conversation_id",
        "platform",
        "status",
        "priority",
        "subject",
        "last_message_preview",
        "tags",
        "creation",
        "escalated_at",
    ]
    # Include manual override if present
    try:
        meta = frappe.get_meta("Unified Inbox Conversation")
        if meta.has_field("complaint_category_override"):
            fields.append("complaint_category_override")
    except Exception:
        pass
    # Prefer creation_time if present; else fall back to creation
    try:
        rows = frappe.get_all(
            "Unified Inbox Conversation",
            filters=[["creation", ">=", df], ["creation", "<=", dt]],
            fields=fields,
            limit=2000,
            order_by="creation asc",
        )
    except Exception:
        rows = []
    return rows or []


def _get_issues(df: date, dt: date) -> List[Dict[str, Any]]:
    fields = ["name", "subject", "status", "creation", "description"]
    meta_issue = frappe.get_meta("Issue")
    if meta_issue.has_field("custom_conversation_id"):
        fields.append("custom_conversation_id")
    if meta_issue.has_field("custom_platform_source"):
        fields.append("custom_platform_source")
    if meta_issue.has_field("complaint_category_override"):
        fields.append("complaint_category_override")

    rows = frappe.get_all(
        "Issue",
        filters=[["creation", ">=", df], ["creation", "<=", dt]],
        fields=fields,
        limit=2000,
        order_by="creation asc",
    )
    return rows or []


def _conversation_exists(name_or_id: str) -> bool:
    if not name_or_id:
        return False
    # Check by name
    if frappe.db.exists("Unified Inbox Conversation", name_or_id):
        return True
    # Check by conversation_id field
    try:
        found = frappe.get_all(
            "Unified Inbox Conversation",
            filters={"conversation_id": name_or_id},
            fields=["name"],
            limit=1,
        )
        return bool(found)
    except Exception:
        return False


def classify_complaint(text: Optional[str], department: Optional[str]) -> str:
    t = (text or "").lower()
    dept = (department or "").lower()

    claims_kw = [
        "claim", "compensation", "benefit", "injury", "accident", "pension", "settlement", "medical"
    ]
    compliance_kw = [
        "compliance", "regulation", "policy", "audit", "violation", "breach", "non-compliance", "inspection"
    ]

    if dept in {"claims", "payments"}:
        return CATEGORY_CLAIMS
    if dept in {"compliance"}:
        return CATEGORY_COMPLIANCE

    if any(k in t for k in claims_kw):
        return CATEGORY_CLAIMS
    if any(k in t for k in compliance_kw):
        return CATEGORY_COMPLIANCE
    return CATEGORY_GENERAL


# ----- Enrichment & Trends -----

def _build_escalation_index(df: date, dt: date) -> Tuple[Dict[str, Dict[str, Any]], Dict[Tuple[str, str], Dict[str, Any]]]:
    """Return two maps:
    - conv_escalations: by Unified Inbox Conversation name
    - ref_escalations: by (reference_doctype, reference_name)
    """
    conv_idx: Dict[str, Dict[str, Any]] = {}
    ref_idx: Dict[Tuple[str, str], Dict[str, Any]] = {}
    try:
        if not frappe.db.table_exists("Escalation Workflow"):
            return conv_idx, ref_idx
        meta = frappe.get_meta("Escalation Workflow")
        fields = ["name", "creation"]
        for f in [
            "conversation",
            "reference_doctype",
            "reference_name",
            "department",
            "status",
            "priority_level",
            "frustration_level",
        ]:
            if meta.has_field(f):
                fields.append(f)
        rows = frappe.get_all(
            "Escalation Workflow",
            filters=[["creation", ">=", df], ["creation", "<=", dt]],
            fields=fields,
            limit=2000,
            order_by="creation asc",
        )
        for r in rows:
            esc = {k: r.get(k) for k in ["department", "status", "priority_level", "frustration_level"] if k in r}
            if r.get("conversation"):
                conv_idx[r.get("conversation")] = esc
            rd, rn = r.get("reference_doctype"), r.get("reference_name")
            if rd and rn:
                ref_idx[(rd, rn)] = esc
    except Exception:
        # Be resilient if workflow is not installed or fields missing
        pass
    return conv_idx, ref_idx


def build_trend_chart(period_type: str, anchor_end_date: date, windows: int = 8) -> Dict[str, Any]:
    """Build a line chart config for the last N windows of the same period type.
    Does on-demand aggregation to avoid storing historical snapshots.
    """
    def _first_of_month(d: date) -> date:
        return getdate(f"{d.year}-{d.month:02d}-01")

    # Build windows from latest backwards
    wins: List[Tuple[date, date, str]] = []
    end = getdate(anchor_end_date)
    for _ in range(max(1, windows)):
        if (period_type or "Weekly").lower().startswith("month"):
            start = _first_of_month(end)
            label = start.strftime("%b %Y")
            wins.append((start, end, label))
            end = add_days(start, -1)
        else:
            start = add_days(end, -6)
            label = f"{start.strftime('%d %b')}–{end.strftime('%d %b')}"
            wins.append((start, end, label))
            end = add_days(start, -1)
    wins.reverse()

    labels: List[str] = []
    s_total: List[int] = []
    s_claims: List[int] = []
    s_compliance: List[int] = []
    s_general: List[int] = []
    s_escalated: List[int] = []

    for (s, e, lbl) in wins:
        counts, _p, _r = aggregate_complaints(s, e)
        labels.append(lbl)
        s_total.append(counts.get("total", 0))
        s_claims.append(counts.get("claims", 0))
        s_compliance.append(counts.get("compliance", 0))
        s_general.append(counts.get("general", 0))
        s_escalated.append(counts.get("escalated", 0))

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Total", "values": s_total},
                {"name": "Claims", "values": s_claims},
                {"name": "Compliance", "values": s_compliance},
                {"name": "General", "values": s_general},
                {"name": "Escalated", "values": s_escalated},
            ],
        },
        "type": "line",
    }


@frappe.whitelist()
def set_category_override(source_doctype: str, source_name: str, category: Optional[str] = None) -> Dict[str, Any]:
    """Set manual category override on the source object (Conversation or Issue)."""
    allowed = {"Unified Inbox Conversation", "Issue"}
    if source_doctype not in allowed:
        frappe.throw("Unsupported source doctype")
    valid = {CATEGORY_CLAIMS, CATEGORY_COMPLIANCE, CATEGORY_GENERAL}
    if category and category not in valid:
        frappe.throw("Invalid category")
    _ensure_override_field(source_doctype)
    doc = frappe.get_doc(source_doctype, source_name)
    # Use db_set to avoid full validation; this is a simple override field
    doc.db_set("complaint_category_override", category or None, update_modified=True)
    return {"ok": True}


def _ensure_override_field(doctype: str):
    try:
        meta = frappe.get_meta(doctype)
        if meta.has_field("complaint_category_override"):
            return
        # Create a custom field if not present
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field  # type: ignore
        create_custom_field(doctype, {
            "fieldname": "complaint_category_override",
            "label": "Complaint Category Override",
            "fieldtype": "Select",
            "options": f"{CATEGORY_CLAIMS}\n{CATEGORY_COMPLIANCE}\n{CATEGORY_GENERAL}",
            "insert_after": "status",
            "permlevel": 0,
        })
    except Exception:
        # If custom field creation fails (permissions), just skip; UI can handle missing field gracefully
        pass


def build_report_html(doc: "ComplaintsStatusReport", platform_counts: Dict[str, int]) -> str:
    def card(label: str, value: Any):
        return f"<div style='display:inline-block;margin:6px;padding:10px;border:1px solid #ddd;border-radius:6px'><div style='font-size:12px;color:#666'>{label}</div><div style='font-size:18px;font-weight:600'>{value}</div></div>"

    cards = "".join([
        card("Total", doc.total_count or 0),
        card("Claims", doc.claims_count or 0),
        card("Compliance", doc.compliance_count or 0),
        card("General", doc.general_count or 0),
        card("Escalated", doc.escalated_count or 0),
        card("Resolved", doc.resolved_count or 0),
        card("Open", doc.open_count or 0),
    ])

    plat_rows = "".join(
        f"<tr><td>{frappe.utils.escape_html(k)}</td><td style='text-align:right'>{v}</td></tr>"
        for k, v in sorted(platform_counts.items())
    ) or "<tr><td colspan='2'>No data</td></tr>"

    html = f"""
    <div>
      <div style='margin-bottom:10px'>{cards}</div>
      <div style='margin-top:10px'>
        <table class='table table-bordered'>
          <thead><tr><th>Platform</th><th style='text-align:right'>Count</th></tr></thead>
          <tbody>{plat_rows}</tbody>
        </table>
      </div>
    </div>
    """
    return html


def _build_pdf_html(doc: "ComplaintsStatusReport") -> str:
    subtitle = f"{doc.period_type} | {doc.date_from} → {doc.date_to}"
    header = f"<h2 style='margin:0'>WCFCB Complaints Status Report</h2><div style='color:#666'>{subtitle}</div>"
    body = build_report_html(doc, _recompute_platforms_for_pdf(doc))
    return f"<div style='font-family:Inter,Arial,sans-serif'>{header}<hr/>{body}</div>"


def _recompute_platforms_for_pdf(doc: "ComplaintsStatusReport") -> Dict[str, int]:
    counts, platforms, _rows = aggregate_complaints(doc.date_from, doc.date_to)
    # ensure fields reflect re-aggregation
    doc.total_count = counts.get("total", 0)
    doc.claims_count = counts.get("claims", 0)
    doc.compliance_count = counts.get("compliance", 0)
    doc.general_count = counts.get("general", 0)
    doc.escalated_count = counts.get("escalated", 0)
    doc.resolved_count = counts.get("resolved", 0)
    doc.open_count = counts.get("open", 0)
    return platforms


def _attach_to_doc(doctype: str, name: str, filename: str, content: bytes):
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "attached_to_doctype": doctype,
        "attached_to_name": name,
        "content": content,
        "is_private": 1,
    })
    file_doc.save(ignore_permissions=True)


def _get_role_emails(roles: List[str]) -> List[str]:
    if not roles:
        return []
    # Find users with any of the roles
    has_roles = frappe.get_all(
        "Has Role",
        filters={"role": ["in", roles]},
        fields=["parent"],
        limit=1000,
    )
    user_ids = {r["parent"] for r in has_roles if r.get("parent")}
    if not user_ids:
        return []
    users = frappe.get_all(
        "User",
        filters={"name": ["in", list(user_ids)], "enabled": 1, "user_type": "System User"},
        fields=["name", "email"],
        limit=1000,
    )
    emails = [u.get("email") for u in users if u.get("email")]
    return sorted(set(emails))


# ----- AI Insights -----
@frappe.whitelist()
def get_ai_insights(name: str, query: str) -> Dict[str, Any]:
    """Return WorkCom-style insights for a Complaints Status Report.

    Builds a JSON context with current KPI counts, category breakdown,
    escalation/open/resolved metrics and recent history, and passes it
    to WorkCom via EnhancedAIService.
    """
    doc = frappe.get_doc("Complaints Status Report", name)

    # Historical context: last 10 reports of same period type
    history = frappe.get_all(
        "Complaints Status Report",
        filters={"period_type": doc.period_type},
        fields=[
            "name",
            "date_from",
            "date_to",
            "total_count",
            "claims_count",
            "compliance_count",
            "general_count",
            "escalated_count",
            "resolved_count",
            "open_count",
        ],
        order_by="date_from desc",
        limit=10,
    )

    # Re-aggregate current window to ensure up-to-date counts and platform mix
    try:
        counts, platform_counts, rows = aggregate_complaints(doc.date_from, doc.date_to)
    except Exception:
        counts = {
            "total": doc.total_count,
            "claims": doc.claims_count,
            "compliance": doc.compliance_count,
            "general": doc.general_count,
            "escalated": doc.escalated_count,
            "resolved": doc.resolved_count,
            "open": doc.open_count,
        }
        platform_counts = {}
        rows = []

    context = {
        "window": {
            "period_type": doc.period_type,
            "from": str(doc.date_from),
            "to": str(doc.date_to),
        },
        "current": {
            "total": counts.get("total", doc.total_count),
            "claims": counts.get("claims", doc.claims_count),
            "compliance": counts.get("compliance", doc.compliance_count),
            "general": counts.get("general", doc.general_count),
            "escalated": counts.get("escalated", doc.escalated_count),
            "resolved": counts.get("resolved", doc.resolved_count),
            "open": counts.get("open", doc.open_count),
        },
        "platforms": platform_counts,
        "sample_rows": rows[:200],
        "history": history,
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService

        ai = EnhancedAIService()
        answer = ai.generate_complaints_status_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Complaints Status Report AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure WorkCom/OpenAI settings in Enhanced AI Settings."
            )
        }


# ----- Helpers -----

def _ensure_date(obj: Any) -> date:
    if isinstance(obj, date):
        return obj
    return getdate(obj)


def _ensure_dates_in(doc: Document):
    doc.date_from = _ensure_date(doc.date_from)
    doc.date_to = _ensure_date(doc.date_to)


def _today() -> date:
    return getdate()


def _ensure_dates(self: Document):
    # Attach as method for class above
    if not getattr(self, "date_from", None) or not getattr(self, "date_to", None):
        if getattr(self, "period_type", None) == "Monthly":
            df, dt = _monthly_window()
        else:
            # Default Weekly
            df, dt = _weekly_window()
        self.date_from, self.date_to = df, dt


# Bind helper as class method without changing signature
ComplaintsStatusReport._ensure_dates = _ensure_dates


