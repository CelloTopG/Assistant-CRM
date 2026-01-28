import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime, now_datetime, add_days
from frappe.utils.pdf import get_pdf

PLATFORMS = ["WhatsApp","Facebook","Instagram","Telegram","Twitter","Tawk.to","Website Chat","Email","Phone","LinkedIn","USSD","YouTube"]

class InboxStatusReport(Document):
    def before_insert(self):
        self._ensure_dates()

    def before_save(self):
        self._ensure_dates()

    def _ensure_dates(self):
        if not getattr(self, "date_from", None) or not getattr(self, "date_to", None):
            if (self.period_type or "Weekly") == "Monthly":
                today = getdate()
                first_this = today.replace(day=1)
                last_prev = first_this - timedelta(days=1)
                self.date_from = last_prev.replace(day=1)
                self.date_to = last_prev
            else:
                # previous calendar week Mon-Sun
                today = getdate()
                this_monday = add_days(today, -today.weekday())
                start = add_days(this_monday, -7)
                self.date_from = start
                self.date_to = add_days(start, 6)

    @frappe.whitelist()
    def run_generation(self):
        self._ensure_dates()
        df, dt = getdate(self.date_from), getdate(self.date_to)

        convs = frappe.get_all(
            "Unified Inbox Conversation",
            filters={"creation": ["between", [df, dt]]},
            fields=["name","platform","status","priority","escalated_at","ai_handled","creation","last_message_time"],
            order_by="creation asc", limit=5000,
        ) or []
        msgs = frappe.get_all(
            "Unified Inbox Message",
            filters={"timestamp": ["between", [df, dt]]},
            fields=["platform","direction","conversation"], limit=20000,
        ) or []

        # Message volumes
        inbound = sum(1 for m in msgs if (m.get("direction") or "").lower()=="inbound")
        outbound = sum(1 for m in msgs if (m.get("direction") or "").lower()=="outbound")
        plat_msg: Dict[str,int] = {}
        for m in msgs:
            p = m.get("platform") or "Unknown"
            plat_msg[p] = plat_msg.get(p,0)+1

        # Conversation metrics
        total = len(convs)
        escalated = resolved = open_ = ai_handled = 0
        prio: Dict[str,int] = {}
        status_counts: Dict[str,int] = {}
        plat_conv: Dict[str,int] = {}
        frt_vals: List[float] = []
        rt_vals: List[float] = []
        ai_first = 0
        sample_rows: List[Dict[str,Any]] = []

        for c in convs:
            status = (c.get("status") or "").title()
            status_counts[status] = status_counts.get(status,0)+1
            prio[c.get("priority") or "Unknown"] = prio.get(c.get("priority") or "Unknown",0)+1
            plat = c.get("platform") or "Unknown"
            plat_conv[plat] = plat_conv.get(plat,0)+1
            if c.get("escalated_at"): escalated += 1
            if status in {"Resolved","Closed"}: resolved += 1
            else: open_ += 1
            if c.get("ai_handled"): ai_handled += 1

            fi, fo, resp_type = _get_first_response(c.get("name"))
            if fi and fo:
                frt = max(0.0,(get_datetime(fo)-get_datetime(fi)).total_seconds()/60.0)
                frt_vals.append(frt)
                if (resp_type or "").startswith("AI"): ai_first += 1
            if status in {"Resolved","Closed"}:
                end_ts = c.get("last_message_time") or c.get("modified")
                if fi and end_ts:
                    mins = max(0.0,(get_datetime(end_ts)-get_datetime(fi)).total_seconds()/60.0)
                    rt_vals.append(mins/60.0)

            if len(sample_rows)<100:
                sample_rows.append({"name":c.get("name"),"platform":plat,"status":status})

        def percentile(arr: List[float], p: float) -> float:
            if not arr: return 0.0
            a = sorted(arr); k = max(0,min(len(a)-1,int(round((p/100.0)*(len(a)-1)))))
            return float(a[k])

        self.title = self.title or f"Inbox {self.period_type or 'Weekly'}: {df} → {dt}"
        self.total_conversations = total
        self.total_messages = len(msgs)
        self.inbound_count = inbound
        self.outbound_count = outbound
        self.escalated_count = escalated
        self.resolved_count = resolved
        self.open_count = open_
        self.ai_first_response_count = ai_first
        self.ai_handled_conversations = ai_handled
        self.avg_first_response_minutes = round(sum(frt_vals)/len(frt_vals),2) if frt_vals else 0.0
        self.p90_first_response_minutes = round(percentile(frt_vals,90),2)
        self.avg_resolution_hours = round(sum(rt_vals)/len(rt_vals),2) if rt_vals else 0.0
        self.p90_resolution_hours = round(percentile(rt_vals,90),2)

        # Charts
        def chart_bar(labels, datasets):
            return {"type":"bar","data":{"labels":labels,"datasets":datasets}}
        def chart_pie(labels, values, name=""):
            return {"type":"pie","data":{"labels":labels,"datasets":[{"name":name or "Values","values":values}]}}

        plat_labels = sorted(set(list(PLATFORMS)+list(plat_conv.keys())+list(plat_msg.keys())))
        self.platform_chart_json = json.dumps(chart_bar(plat_labels,[{"name":"Conversations","values":[plat_conv.get(l,0) for l in plat_labels]},{"name":"Messages","values":[plat_msg.get(l,0) for l in plat_labels]}]))
        self.direction_chart_json = json.dumps(chart_pie(["Inbound","Outbound"],[inbound,outbound],"Messages"))
        self.status_chart_json = json.dumps(chart_pie(["Open","Resolved","Escalated"],[open_,resolved,escalated],"Conversations"))
        pr_labels = sorted(prio.keys()); self.priority_chart_json = json.dumps(chart_bar(pr_labels,[{"name":"Conversations","values":[prio[k] for k in pr_labels]}]))
        # Stacked platform x direction using message data
        inbound_by_p = {p:0 for p in plat_labels}; outbound_by_p = {p:0 for p in plat_labels}
        for m in msgs:
            p=(m.get("platform") or "Unknown"); d=(m.get("direction") or "").lower()
            if d=="inbound": inbound_by_p[p]=inbound_by_p.get(p,0)+1
            elif d=="outbound": outbound_by_p[p]=outbound_by_p.get(p,0)+1
        self.platform_direction_stacked_json = json.dumps({"type":"bar","data":{"labels":plat_labels,"datasets":[{"name":"Inbound","chartType":"bar","values":[inbound_by_p.get(l,0) for l in plat_labels]},{"name":"Outbound","chartType":"bar","values":[outbound_by_p.get(l,0) for l in plat_labels]}]},"barOptions":{"stacked":1}})

        self.trend_chart_json = json.dumps(build_trend_chart(self.period_type or "Weekly", getdate(self.date_to)))
        self.rows_json = json.dumps(sample_rows)
        self.report_html = build_report_html(self, plat_conv)
        self.generated_at = now_datetime(); self.generated_by = frappe.session.user
        self.save()
        return {"message":"ok"}

    @frappe.whitelist()
    def generate_pdf(self) -> str:
        html = _build_pdf_html(self)
        pdf = get_pdf(html)
        fname = f"Inbox_Status_Report_{self.name}.pdf"
        frappe.get_doc({"doctype":"File","file_name":fname,"content":pdf,"is_private":1,"attached_to_doctype":"Inbox Status Report","attached_to_name":self.name}).insert(ignore_permissions=True)
        return fname

    @frappe.whitelist()
    def email_report(self, recipients: Optional[List[str]] = None):
        recipients = recipients or _get_role_emails(["Customer Service","ICT"]) or []
        if not recipients: return {"message":"no-recipients"}
        html = _build_pdf_html(self)
        pdf = get_pdf(html)
        fname = f"Inbox_Status_Report_{self.name}.pdf"
        frappe.sendmail(recipients=recipients, subject=f"Inbox Status Report: {self.period_type} ({self.date_from} → {self.date_to})", message="Attached is the latest Inbox Status Report.", attachments=[{"fname": fname, "fcontent": pdf}])
        return {"message":"sent","recipients":recipients}

# Schedulers
@frappe.whitelist()
def schedule_weekly_inbox_status_reports():
    today = getdate(); this_monday = add_days(today, -today.weekday()); start = add_days(this_monday, -7); end = add_days(start,6)
    doc = frappe.get_doc({"doctype":"Inbox Status Report","period_type":"Weekly","date_from":start,"date_to":end,"title":f"Inbox Weekly: {start} → {end}"}).insert(ignore_permissions=True)
    doc.run_generation();
    try: doc.email_report()
    except Exception: frappe.log_error(frappe.get_traceback(), "Inbox Status Report weekly email failed")

@frappe.whitelist()
def schedule_monthly_inbox_status_reports():
    today = getdate(); first_this = today.replace(day=1); last_prev = first_this - timedelta(days=1); first_prev = last_prev.replace(day=1)
    doc = frappe.get_doc({"doctype":"Inbox Status Report","period_type":"Monthly","date_from":first_prev,"date_to":last_prev,"title":f"Inbox Monthly: {first_prev.strftime('%b %Y')}"}).insert(ignore_permissions=True)
    doc.run_generation();
    try: doc.email_report()
    except Exception: frappe.log_error(frappe.get_traceback(), "Inbox Status Report monthly email failed")

# AI Insights
@frappe.whitelist()
def get_ai_insights(name: str, query: str) -> Dict[str, Any]:
    """Return Antoine-style insights for an Inbox Status Report."""
    doc = frappe.get_doc("Inbox Status Report", name)

    history = frappe.get_all(
        "Inbox Status Report",
        filters={"period_type": doc.period_type},
        fields=[
            "name",
            "date_from",
            "date_to",
            "total_conversations",
            "total_messages",
            "inbound_count",
            "outbound_count",
            "escalated_count",
            "resolved_count",
            "open_count",
            "ai_first_response_count",
            "ai_handled_conversations",
            "avg_first_response_minutes",
            "p90_first_response_minutes",
            "avg_resolution_hours",
            "p90_resolution_hours",
        ],
        order_by="date_from desc",
        limit=10,
    )

    context = {
        "window": {
            "period_type": doc.period_type,
            "from": str(doc.date_from),
            "to": str(doc.date_to),
        },
        "current": {
            "total_conversations": int(doc.total_conversations or 0),
            "total_messages": int(doc.total_messages or 0),
            "inbound_messages": int(doc.inbound_count or 0),
            "outbound_messages": int(doc.outbound_count or 0),
            "escalated_conversations": int(doc.escalated_count or 0),
            "resolved_conversations": int(doc.resolved_count or 0),
            "open_conversations": int(doc.open_count or 0),
            "ai_first_response_count": int(doc.ai_first_response_count or 0),
            "ai_handled_conversations": int(doc.ai_handled_conversations or 0),
            "avg_first_response_minutes": float(doc.avg_first_response_minutes or 0),
            "p90_first_response_minutes": float(doc.p90_first_response_minutes or 0),
            "avg_resolution_hours": float(doc.avg_resolution_hours or 0),
            "p90_resolution_hours": float(doc.p90_resolution_hours or 0),
        },
        "history": history,
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService

        ai = EnhancedAIService()
        answer = ai.generate_inbox_status_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Inbox Status Report AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure Antoine/OpenAI settings in Enhanced AI Settings."
            )
        }

# Helpers

def _get_first_response(conversation_name: str) -> Tuple[Optional[datetime], Optional[datetime], Optional[str]]:
    msgs = frappe.get_all("Unified Inbox Message", filters={"conversation": conversation_name}, fields=["timestamp","direction","processed_by_ai","ai_response","handled_by_agent","sender_name"], order_by="timestamp asc", limit=500)
    fi = next((m for m in msgs if (m.get("direction") or "").lower()=="inbound"), None)
    fo = next((m for m in msgs if (m.get("direction") or "").lower()=="outbound"), None)
    resp = None
    if fo:
        if fo.get("handled_by_agent"): resp = "Human Response"
        elif fo.get("processed_by_ai") or fo.get("ai_response") or ((fo.get("sender_name") or "").lower().find("ai")>=0): resp = "AI Response"
        else: resp = "Human Response"
    return (get_datetime(fi.get("timestamp")) if fi else None, get_datetime(fo.get("timestamp")) if fo else None, resp)

def build_trend_chart(period_type: str, anchor_end: date, windows: int = 8) -> Dict[str, Any]:
    wins: List[Tuple[date,date,str]] = []
    end = getdate(anchor_end)
    for _ in range(max(1, windows)):
        if (period_type or "Weekly").lower().startswith("month"):
            start = getdate(f"{end.year}-{end.month:02d}-01"); label = start.strftime("%b %Y"); wins.append((start,end,label)); end = add_days(start,-1)
        else:
            start = add_days(end,-6); label = f"{start.strftime('%d %b')}–{end.strftime('%d %b')}"; wins.append((start,end,label)); end = add_days(start,-1)
    wins.reverse()
    labels: List[str] = []; totals: List[int] = []
    for (s,e,lbl) in wins:
        cnt = frappe.db.count("Unified Inbox Conversation", filters={"creation": ["between", [s,e]]})
        labels.append(lbl); totals.append(cnt)
    return {"type":"line","data":{"labels":labels,"datasets":[{"name":"Conversations","values":totals}]}}

def build_report_html(doc: "InboxStatusReport", platform_counts: Dict[str,int]) -> str:
    def card(l,v): return f"<div style='display:inline-block;margin:6px;padding:10px;border:1px solid #ddd;border-radius:6px'><div style='font-size:12px;color:#666'>{l}</div><div style='font-size:18px;font-weight:600'>{v}</div></div>"
    cards = "".join([
        card("Conversations", doc.total_conversations or 0), card("Messages", doc.total_messages or 0), card("Inbound", doc.inbound_count or 0), card("Outbound", doc.outbound_count or 0), card("AI First", doc.ai_first_response_count or 0), card("Escalated", doc.escalated_count or 0), card("Resolved", doc.resolved_count or 0), card("Open", doc.open_count or 0), card("Avg FRT (m)", doc.avg_first_response_minutes or 0), card("Avg RT (h)", doc.avg_resolution_hours or 0)
    ])
    plat_rows = "".join(f"<tr><td>{frappe.utils.escape_html(k)}</td><td style='text-align:right'>{v}</td></tr>" for k,v in sorted(platform_counts.items())) or "<tr><td colspan='2'>No data</td></tr>"
    html = f"""
    <div>
      <div style='margin-bottom:10px'>{cards}</div>
      <div style='margin-top:10px'>
        <table class='table table-bordered'>
          <thead><tr><th>Platform</th><th style='text-align:right'>Conversations</th></tr></thead>
          <tbody>{plat_rows}</tbody>
        </table>
      </div>
    </div>
    """
    return html

def _build_pdf_html(doc: "InboxStatusReport") -> str:
    subtitle = f"{doc.period_type} | {doc.date_from} → {doc.date_to}"
    body = build_report_html(doc, {})
    return f"<div style='font-family:Inter,Arial,sans-serif'><h2 style='margin:0'>WCFCB Inbox Status Report</h2><div style='color:#666'>{subtitle}</div><hr/>{body}</div>"

def _get_role_emails(roles: List[str]) -> List[str]:
    if not roles: return []
    has = frappe.get_all("Has Role", filters={"role":["in", roles]}, fields=["parent"], limit=1000)
    ids = {r.get("parent") for r in has if r.get("parent")}
    if not ids: return []
    users = frappe.get_all("User", filters={"name":["in", list(ids)], "enabled":1, "user_type":"System User"}, fields=["email"], limit=1000)
    return sorted({u.get("email") for u in users if u.get("email")})


@frappe.whitelist()
def get_latest_inbox_reports(limit: int = 3):
    try:
        lim = int(limit)
    except Exception:
        lim = 3
    return frappe.get_all("Inbox Status Report", fields=["name","period_type","date_from","date_to","total_conversations","total_messages"], order_by="creation desc", limit=lim)
@frappe.whitelist()
def ensure_ict_role():
    if not frappe.db.exists("Role", "ICT"):
        frappe.get_doc({"doctype":"Role","role_name":"ICT"}).insert(ignore_permissions=True)
    return True

@frappe.whitelist()
def generate_pdf_for(name: str):
    doc = frappe.get_doc("Inbox Status Report", name)
    return doc.generate_pdf()

