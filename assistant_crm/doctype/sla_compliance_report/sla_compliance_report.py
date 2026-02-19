import json
from datetime import datetime, timedelta, time, date
from typing import Dict, List, Optional, Tuple

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, now_datetime
from frappe.utils.pdf import get_pdf


CATEGORY_CLAIMS = "Claims"
CATEGORY_COMPLIANCE = "Compliance"
CATEGORY_GENERAL = "General"

BUSINESS_START = time(8, 0)
BUSINESS_END = time(17, 0)
BUSINESS_DAYS = {0, 1, 2, 3, 4}  # Mon-Fri


class SLAComplianceReport(Document):
    def before_insert(self):
        self._ensure_dates()

    def before_save(self):
        self._ensure_dates()

    def _ensure_dates(self):
        if (self.period_type or "Monthly") == "Monthly":
            # default to previous full month window if missing
            if not self.date_from or not self.date_to:
                today = getdate()
                first_this_month = today.replace(day=1)
                last_prev_month = first_this_month - timedelta(days=1)
                first_prev_month = last_prev_month.replace(day=1)
                self.date_from = first_prev_month
                self.date_to = last_prev_month

    @frappe.whitelist()
    def run_generation(self):
        self._ensure_dates()
        filters = {
            "branch": (self.branch_filter or "").strip() or None,
            "role": (self.role_filter or "").strip() or None,
            "channel": None if (self.channel_filter or "All") == "All" else self.channel_filter,
            "priority": None if (self.priority_filter or "All") == "All" else self.priority_filter,
        }
        counts, charts, rows = aggregate_sla_compliance(self.date_from, self.date_to, filters)

        # KPIs
        self.total_items = counts.get("total_items", 0)
        self.within_sla_count = counts.get("within_sla", 0)
        self.breached_sla_count = counts.get("breached_sla", 0)
        self.compliance_percent = round(counts.get("compliance_percent", 0.0), 2)

        self.frt_avg_minutes = round(counts.get("frt_avg", 0.0), 2)
        self.frt_p90 = round(counts.get("frt_p90", 0.0), 2)
        self.frt_within_sla_percent = round(counts.get("frt_within_percent", 0.0), 2)

        self.rt_avg_hours = round(counts.get("rt_avg", 0.0), 2)
        self.rt_p90 = round(counts.get("rt_p90", 0.0), 2)
        self.rt_within_sla_percent = round(counts.get("rt_within_percent", 0.0), 2)

        self.escalations_total = counts.get("escalations_total", 0)
        self.escalations_within_sla = counts.get("escalations_within", 0)
        self.escalations_breached = counts.get("escalations_breached", 0)

        self.ai_first_responses = counts.get("ai_first_responses", 0)

        # Charts and HTML
        self.chart_overview_json = json.dumps(charts.get("overview", {}))
        self.branch_breakdown_chart_json = json.dumps(charts.get("branch_breakdown", {}))
        self.role_breakdown_chart_json = json.dumps(charts.get("role_breakdown", {}))
        self.trend_chart_json = json.dumps(build_trend_chart(self))

        self.rows_json = json.dumps(rows)
        self.filters_json = json.dumps(filters)
        self.report_html = build_report_html(self, counts)

        self.generated_at = now_datetime()
        self.generated_by = frappe.session.user
        self.save()
        return {"message": "ok", "counts": counts}

    @frappe.whitelist()
    def generate_pdf(self):
        # Use stored HTML if present; otherwise rebuild from current doc fields
        html = getattr(self, "report_html", None) or build_report_html(self, {})
        fname = f"SLA_Compliance_{self.name}.pdf"
        pdf = get_pdf(html)
        filedoc = frappe.get_doc({
            "doctype": "File",
            "file_name": fname,
            "content": pdf,
            "is_private": 1,
            "attached_to_doctype": "SLA Compliance Report",
            "attached_to_name": self.name,
        }).insert(ignore_permissions=True)
        return {"file_url": filedoc.file_url, "file_name": fname}

    @frappe.whitelist()
    def email_report(self):
        recipients = _get_manager_emails()
        if not recipients:
            return {"ok": False, "message": "No manager recipients found"}
        attach = self.generate_pdf()
        frappe.sendmail(
            recipients=recipients,
            subject=f"SLA Compliance Report: {self.title or self.name}",
            message=(getattr(self, "report_html", None) or "SLA Compliance report attached."),
            attachments=[{"fname": attach.get("file_name"), "fcontent": frappe.utils.file_manager.get_file(attach.get("file_url"))[1]}],
        )
        return {"ok": True, "sent": len(recipients)}


@frappe.whitelist()
def get_ai_insights(name: str, query: str):
    """Return WorkCom-style insights for an SLA Compliance Report.

    Builds a JSON context with SLA compliance %, FRT/RT metrics, escalation
    behaviour and trend history, and passes it to WorkCom via EnhancedAIService.
    """
    doc = frappe.get_doc("SLA Compliance Report", name)

    history = frappe.get_all(
        "SLA Compliance Report",
        filters={"period_type": doc.period_type},
        fields=[
            "name",
            "date_from",
            "date_to",
            "compliance_percent",
            "frt_avg_minutes",
            "rt_avg_hours",
            "escalations_total",
        ],
        order_by="date_from desc",
        limit=12,
    )

    # Recompute counts for the current window using the same filters as run_generation
    filters = {
        "branch": (doc.branch_filter or "").strip() or None,
        "role": (doc.role_filter or "").strip() or None,
        "channel": None if (doc.channel_filter or "All") == "All" else doc.channel_filter,
        "priority": None if (doc.priority_filter or "All") == "All" else doc.priority_filter,
    }
    try:
        counts, charts, rows = aggregate_sla_compliance(doc.date_from, doc.date_to, filters)
    except Exception:
        counts = {
            "total_items": doc.total_items,
            "within_sla": doc.within_sla_count,
            "breached_sla": doc.breached_sla_count,
            "compliance_percent": float(doc.compliance_percent or 0.0),
            "frt_avg": float(doc.frt_avg_minutes or 0.0),
            "rt_avg": float(doc.rt_avg_hours or 0.0),
            "escalations_total": int(doc.escalations_total or 0),
            "ai_first_responses": int(doc.ai_first_responses or 0),
        }
        charts, rows = {}, []

    context = {
        "window": {
            "period_type": doc.period_type,
            "from": str(doc.date_from),
            "to": str(doc.date_to),
        },
        "current": {
            "total_items": counts.get("total_items", doc.total_items),
            "within_sla": counts.get("within_sla", doc.within_sla_count),
            "breached_sla": counts.get("breached_sla", doc.breached_sla_count),
            "compliance_percent": counts.get("compliance_percent", float(doc.compliance_percent or 0.0)),
            "frt_avg_minutes": counts.get("frt_avg", float(doc.frt_avg_minutes or 0.0)),
            "rt_avg_hours": counts.get("rt_avg", float(doc.rt_avg_hours or 0.0)),
            "escalations_total": counts.get("escalations_total", int(doc.escalations_total or 0)),
            "ai_first_responses": counts.get("ai_first_responses", int(doc.ai_first_responses or 0)),
        },
        "history": history,
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService

        ai = EnhancedAIService()
        answer = ai.generate_sla_compliance_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "SLA Compliance Report AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure WorkCom/OpenAI settings in Enhanced AI Settings."
            )
        }


@frappe.whitelist()
def schedule_monthly_sla_compliance_reports():
    # previous month window
    today = getdate()
    first_this_month = today.replace(day=1)
    last_prev_month = first_this_month - timedelta(days=1)
    first_prev_month = last_prev_month.replace(day=1)

    doc = frappe.get_doc({
        "doctype": "SLA Compliance Report",
        "title": f"SLA Compliance {first_prev_month.strftime('%b %Y')}",
        "period_type": "Monthly",
        "date_from": first_prev_month,
        "date_to": last_prev_month,
    }).insert(ignore_permissions=True)
    doc.run_generation()
    try:
        doc.email_report()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "SLA Compliance monthly email failed")
    return {"ok": True, "name": doc.name}


# ----------------------------
# Aggregation & helpers
# ----------------------------

def aggregate_sla_compliance(date_from, date_to, filters: Dict):
    df = getdate(date_from)
    dt = getdate(date_to)

    # Fetch conversations within window
    conv_filters = {}
    # Filter by creation date window
    conv_filters["creation"] = ["between", [df, dt]]

    if filters.get("channel"):
        conv_filters["platform"] = filters["channel"]
    if filters.get("priority"):
        conv_filters["priority"] = filters["priority"]

    conversations = frappe.get_all(
        "Unified Inbox Conversation",
        filters=conv_filters,
        fields=[
            "name", "platform", "priority", "status", "assigned_agent", "creation", "modified",
            "last_message_time", "branch"
        ],
        order_by="creation asc",
        limit=5000,
    )

    # Escalations within window (gracefully handle missing 'conversation' field on Escalation Workflow)
    esc_index = {}
    try:
        esc_meta = frappe.get_meta("Escalation Workflow")
        has_conv = esc_meta and esc_meta.has_field("conversation")
    except Exception:
        has_conv = False

    if has_conv:
        escalations = frappe.get_all(
            "Escalation Workflow",
            filters={"escalation_date": ["between", [df, dt]]},
            fields=["name", "conversation", "escalation_date"],
            limit=5000,
        )
        for e in escalations:
            esc_index.setdefault(e.conversation, []).append(e)
    else:
        # No link to conversation available; skip per-conversation escalation mapping
        # Still allow overall metrics to proceed without escalation counts
        escalations = []

    # SLA configurations
    sla_rules = frappe.get_all(
        "SLA Configuration",
        filters={"is_active": 1},
        fields=[
            "name", "channel", "priority", "first_response_time", "resolution_time", "escalation_time", "business_hours_only"
        ],
        limit=200,
    )

    def match_sla(channel: Optional[str], priority: Optional[str]):
        # most specific first
        candidates = []
        for r in sla_rules:
            if r.channel not in (None, "", "All") and channel and r.channel != channel:
                continue
            if r.priority not in (None, "", "All") and priority and r.priority != priority:
                continue
            candidates.append(r)
        # fallback to fully generic
        if not candidates:
            candidates = [r for r in sla_rules if (r.channel in (None, "", "All")) and (r.priority in (None, "", "All"))]
        return candidates[0] if candidates else None

    # Stats accumulators
    rows: List[Dict] = []
    frt_vals: List[float] = []
    rt_vals: List[float] = []
    frt_within = frt_total = 0
    rt_within = rt_total = 0
    total_items = within_sla = breached_sla = 0
    ai_first = 0
    branch_stats: Dict[str, Dict[str, int]] = {}
    role_stats: Dict[str, Dict[str, int]] = {}
    cat_stats: Dict[str, Dict[str, int]] = {CATEGORY_CLAIMS: {"within":0, "breached":0}, CATEGORY_COMPLIANCE: {"within":0, "breached":0}, CATEGORY_GENERAL: {"within":0, "breached":0}}
    escalations_total = escalations_within = escalations_breached = 0

    # Helper to derive branch/role bucket
    user_meta = frappe.get_meta("User")
    def derive_branch(user_id: Optional[str]) -> str:
        if not user_id:
            return "Unassigned"
        try:
            user = frappe.get_cached_doc("User", user_id)
            if user_meta.has_field("branch") and getattr(user, "branch", None):
                return user.branch
            if user_meta.has_field("department") and getattr(user, "department", None):
                return user.department
        except Exception:
            pass
        return "Unassigned"

    def derive_role_bucket(user_id: Optional[str]) -> str:
        if not user_id:
            return "Other"
        try:
            roles = [r.role for r in frappe.get_all("Has Role", filters={"parent": user_id}, fields=["role"], limit=100)]
            if any("Customer Service" in r for r in roles):
                return "Customer Service"
            if any("Corporate Affairs" in r for r in roles):
                return "Corporate Affairs"
        except Exception:
            pass
        return "Other"

    # Classifier reuse from complaints report if available
    def classify(text: str, dept: Optional[str]) -> str:
        try:
            from assistant_crm.assistant_crm.doctype.complaints_status_report.complaints_status_report import classify_complaint
            return classify_complaint(text=text or "", department=dept)
        except Exception:
            return CATEGORY_GENERAL

    for c in conversations:
        # Use branch field directly from conversation, fall back to deriving from assigned_agent
        branch = c.get("branch") or derive_branch(c.assigned_agent)
        role_bucket = derive_role_bucket(c.assigned_agent)
        # Optional filters by branch/role contains
        if filters.get("branch") and filters["branch"].lower() not in branch.lower():
            continue
        if filters.get("role") and filters["role"].lower() not in role_bucket.lower():
            continue

        sla = match_sla(c.platform, c.priority)
        first_inbound, first_outbound, responder_type, inbound_text = _get_first_response(c.name)

        frt_minutes = None
        frt_ok = None
        if first_inbound and first_outbound:
            frt_minutes = _business_minutes_between(first_inbound, first_outbound) if (sla and sla.business_hours_only) else _minutes_between(first_inbound, first_outbound)
            frt_vals.append(frt_minutes)
            frt_total += 1
            if sla and sla.first_response_time:
                frt_ok = frt_minutes <= float(sla.first_response_time)
                if frt_ok:
                    frt_within += 1
            if responder_type == "AI Response":
                ai_first += 1

        # Resolution
        rt_hours = None
        rt_ok = None
        if c.status in ("Resolved", "Closed"):
            # end time best-effort
            end_ts = _get_resolution_time(c)
            if end_ts and first_inbound:
                minutes = _business_minutes_between(first_inbound, end_ts) if (sla and sla.business_hours_only) else _minutes_between(first_inbound, end_ts)
                rt_hours = minutes / 60.0
                rt_vals.append(rt_hours)
                rt_total += 1
                if sla and sla.resolution_time:
                    rt_ok = rt_hours <= float(sla.resolution_time)
                    if rt_ok:
                        rt_within += 1

        # Escalation
        esc_ok = None
        escs = esc_index.get(c.name) or []
        if escs:
            escalations_total += 1
            e = sorted(escs, key=lambda x: x.escalation_date)[0]
            if first_inbound:
                esc_minutes = _business_minutes_between(first_inbound, get_datetime(e.escalation_date)) if (sla and sla.business_hours_only) else _minutes_between(first_inbound, get_datetime(e.escalation_date))
                if sla and sla.escalation_time:
                    esc_ok = esc_minutes <= float(sla.escalation_time)
                    if esc_ok:
                        escalations_within += 1
                    else:
                        escalations_breached += 1

        # Overall compliance (only consider defined checks)
        applicable = []
        for v in [frt_ok, rt_ok, esc_ok]:
            if v is not None:
                applicable.append(v)
        if applicable:
            total_items += 1
            if all(applicable):
                within_sla += 1
                overall = "Within"
            else:
                breached_sla += 1
                overall = "Breached"
        else:
            # If nothing to evaluate, skip from totals but keep as row sample
            overall = "N/A"

        # Category by simple heuristic (using first inbound text + branch hint)
        category = classify(text=inbound_text or "", dept=branch)
        cat_stats.setdefault(category, {"within": 0, "breached": 0})
        if overall == "Within":
            cat_stats[category]["within"] += 1
        elif overall == "Breached":
            cat_stats[category]["breached"] += 1

        # Accumulate branch/role stats
        for bucket, store in [(branch, branch_stats), (role_bucket, role_stats)]:
            store.setdefault(bucket, {"within": 0, "breached": 0})
            if overall == "Within":
                store[bucket]["within"] += 1
            elif overall == "Breached":
                store[bucket]["breached"] += 1

        rows.append({
            "source": "Conversation",
            "name": c.name,
            "platform": c.platform,
            "priority": c.priority,
            "branch": branch,
            "role": role_bucket,
            "category": category,
            "frt_minutes": frt_minutes,
            "frt_label": responder_type or None,
            "frt_within": frt_ok,
            "rt_hours": rt_hours,
            "rt_within": rt_ok,
            "escalated": bool(escs),
            "overall": overall,
        })

    # Compute KPIs
    def percentile(values: List[float], p: float) -> float:
        if not values:
            return 0.0
        arr = sorted(values)
        k = max(0, min(len(arr) - 1, int(round((p / 100.0) * (len(arr) - 1)))))
        return float(arr[k])

    frt_avg = sum(frt_vals) / len(frt_vals) if frt_vals else 0.0
    rt_avg = sum(rt_vals) / len(rt_vals) if rt_vals else 0.0
    frt_p90 = percentile(frt_vals, 90)
    rt_p90 = percentile(rt_vals, 90)

    comp_percent = (within_sla / total_items * 100.0) if total_items else 0.0
    frt_within_percent = (frt_within / frt_total * 100.0) if frt_total else 0.0
    rt_within_percent = (rt_within / rt_total * 100.0) if rt_total else 0.0

    # Charts
    overview = {
        "type": "bar",
        "data": {
            "labels": [CATEGORY_CLAIMS, CATEGORY_COMPLIANCE, CATEGORY_GENERAL],
            "datasets": [
                {"name": "Within SLA", "values": [
                    cat_stats.get(CATEGORY_CLAIMS, {}).get("within", 0),
                    cat_stats.get(CATEGORY_COMPLIANCE, {}).get("within", 0),
                    cat_stats.get(CATEGORY_GENERAL, {}).get("within", 0)
                ]},
                {"name": "Breached", "values": [
                    cat_stats.get(CATEGORY_CLAIMS, {}).get("breached", 0),
                    cat_stats.get(CATEGORY_COMPLIANCE, {}).get("breached", 0),
                    cat_stats.get(CATEGORY_GENERAL, {}).get("breached", 0)
                ]}
            ]
        },
        "barOptions": {"stacked": 1}
    }

    def to_stacked(store: Dict[str, Dict[str, int]]):
        labels = list(store.keys())[:12]
        within = [store[k]["within"] for k in labels]
        breached = [store[k]["breached"] for k in labels]
        return {
            "type": "bar",
            "data": {"labels": labels, "datasets": [{"name": "Within", "values": within}, {"name": "Breached", "values": breached}]},
            "barOptions": {"stacked": 1}
        }

    charts = {
        "overview": overview,
        "branch_breakdown": to_stacked(branch_stats),
        "role_breakdown": to_stacked(role_stats),
    }

    counts = {
        "total_items": total_items,
        "within_sla": within_sla,
        "breached_sla": breached_sla,
        "compliance_percent": comp_percent,
        "frt_avg": frt_avg,
        "frt_p90": frt_p90,
        "frt_within_percent": frt_within_percent,
        "rt_avg": rt_avg,
        "rt_p90": rt_p90,
        "rt_within_percent": rt_within_percent,
        "escalations_total": escalations_total,
        "escalations_within": escalations_within,
        "escalations_breached": escalations_breached,
        "ai_first_responses": ai_first,
    }

    return counts, charts, rows


def build_trend_chart(doc: SLAComplianceReport) -> Dict:
    # Last 6 months including current window's month
    trend = []
    current_start = getdate(doc.date_from)
    for i in range(6):
        start = (current_start.replace(day=1) - timedelta(days=1)).replace(day=1) if i > 0 else current_start
        end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        counts, _, _ = aggregate_sla_compliance(start, end, {
            "branch": (doc.branch_filter or "").strip() or None,
            "role": (doc.role_filter or "").strip() or None,
            "channel": None if (doc.channel_filter or "All") == "All" else doc.channel_filter,
            "priority": None if (doc.priority_filter or "All") == "All" else doc.priority_filter,
        })
        trend.append({"label": start.strftime('%b %Y'), "compliance": round(counts.get("compliance_percent", 0.0), 2)})
        current_start = start
    trend.reverse()
    return {
        "type": "line",
        "data": {
            "labels": [t["label"] for t in trend],
            "datasets": [{"name": "Compliance %", "values": [t["compliance"] for t in trend]}]
        }
    }


def build_report_html(doc: SLAComplianceReport, counts: Dict) -> str:
    comp = round(counts.get("compliance_percent", doc.compliance_percent or 0.0), 2)
    ai_first = counts.get("ai_first_responses", doc.ai_first_responses or 0)
    return f"""
    <div style='padding:10px;'>
      <h3 style='margin:0;'>SLA Compliance Report</h3>
      <div style='color:#666;'>Window: {doc.date_from} to {doc.date_to}</div>
      <div style='display:flex;gap:10px;margin-top:8px;flex-wrap:wrap;'>
        <div style='flex:1;min-width:200px;border:1px solid #eee;padding:8px;border-radius:6px;'>
          <div>Total Items</div><div style='font-size:18px;font-weight:600'>{counts.get('total_items', doc.total_items or 0)}</div>
        </div>
        <div style='flex:1;min-width:200px;border:1px solid #eee;padding:8px;border-radius:6px;'>
          <div>Compliance %</div><div style='font-size:18px;font-weight:600'>{comp}%</div>
        </div>
        <div style='flex:1;min-width:200px;border:1px solid #eee;padding:8px;border-radius:6px;'>
          <div>AI First Responses</div><div style='font-size:18px;font-weight:600'>{ai_first}</div>
          <div style='font-size:11px;color:#888;'>AI Response label applied where applicable</div>
        </div>
      </div>
      <div style='margin-top:10px;font-size:11px;color:#666'>Business Hours assumed: Mon–Fri 08:00–17:00</div>
    </div>
    """


def _get_first_response(conversation_name: str) -> Tuple[Optional[datetime], Optional[datetime], Optional[str], Optional[str]]:
    msgs = frappe.get_all(
        "Unified Inbox Message",
        filters={"conversation": conversation_name},
        fields=[
            "timestamp", "direction", "processed_by_ai", "ai_response", "handled_by_agent", "agent_response",
            "sender_name", "message_content"
        ],
        order_by="timestamp asc",
        limit=500,
    )
    first_in_msg = next((m for m in msgs if (m.direction or "").lower() == "inbound"), None)
    first_in = get_datetime(first_in_msg.timestamp) if first_in_msg else None
    first_out_msg = next((m for m in msgs if (m.direction or "").lower() == "outbound"), None)
    first_out = get_datetime(first_out_msg.timestamp) if first_out_msg else None
    resp_type = None
    if first_out_msg:
        if getattr(first_out_msg, "handled_by_agent", 0) or getattr(first_out_msg, "agent_response", 0):
            resp_type = "Human Response"
        elif getattr(first_out_msg, "processed_by_ai", 0) or getattr(first_out_msg, "ai_response", 0) or (first_out_msg.sender_name or "").lower().find("ai") >= 0:
            resp_type = "AI Response"
        else:
            resp_type = "Human Response"
    inbound_text = getattr(first_in_msg, "message_content", None) if first_in_msg else None
    return first_in, first_out, resp_type, inbound_text


def _get_resolution_time(conv) -> Optional[datetime]:
    # Try custom fields commonly used
    fields = ["resolved_at", "closed_at", "last_message_time", "modified"]
    for f in fields:
        try:
            val = conv.get(f) if isinstance(conv, dict) else getattr(conv, f, None)
            if val:
                return get_datetime(val)
        except Exception:
            continue
    return None


def _minutes_between(start: datetime, end: datetime) -> float:
    return max(0.0, (end - start).total_seconds() / 60.0)


def _business_minutes_between(start: datetime, end: datetime) -> float:
    # Clip to business hours Mon-Fri 08:00-17:00
    if end <= start:
        return 0.0
    total = 0.0
    cur = start
    while cur.date() <= end.date():
        if cur.weekday() in BUSINESS_DAYS:
            day_start = datetime.combine(cur.date(), BUSINESS_START)
            day_end = datetime.combine(cur.date(), BUSINESS_END)
            s = max(cur, day_start)
            e = min(end, day_end)
            if e > s:
                total += (e - s).total_seconds() / 60.0
        cur = datetime.combine(cur.date() + timedelta(days=1), time(0, 0))
    return total


def _get_manager_emails() -> List[str]:
    # Collect users with any 'Manager' role (includes Branch Managers), plus explicit roles if present
    role_names = [r.name for r in frappe.get_all("Role", filters={"name": ["like", "%Manager%"]}, fields=["name"], limit=200)]
    # Fetch users with those roles
    emails = set()
    if role_names:
        # Only consider role assignments where the parent is a User, to avoid pages/reports/etc
        for hr in frappe.get_all(
            "Has Role",
            filters={"role": ["in", role_names], "parenttype": "User"},
            fields=["parent"],
            limit=2000,
        ):
            try:
                u = frappe.get_cached_doc("User", hr.parent)
                if u.enabled and u.email:
                    emails.add(u.email)
            except Exception:
                continue
    return sorted(emails)


