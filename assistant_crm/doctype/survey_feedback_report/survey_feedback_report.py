# Copyright (c) 2025, ExN and contributors
# License: MIT

import json
from datetime import date, datetime, timedelta
from typing import Dict, Any, List

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, formatdate, get_datetime
from frappe.utils.pdf import get_pdf

PLATFORMS = [
    "WhatsApp", "Facebook", "Instagram", "Telegram", "Tawk.to", "USSD"
]

SENT_THRESHOLDS = {
    "very_positive": 0.8,
    "positive": 0.4,
    "neutral": -0.2,
    "negative": -0.6
}

class SurveyFeedbackReport(Document):
    def before_insert(self):
        self._ensure_dates()

    def before_save(self):
        self._ensure_dates()

    def _ensure_dates(self):
        # Infer dates based on period_type when missing
        if self.period_type in (None, "Monthly"):
            # default to previous full month
            today = getdate()
            first_this_month = date(today.year, today.month, 1)
            last_prev_month = first_this_month - timedelta(days=1)
            first_prev_month = date(last_prev_month.year, last_prev_month.month, 1)
            self.date_from = self.date_from or first_prev_month
            self.date_to = self.date_to or last_prev_month
        elif self.period_type == "Quarterly":
            today = getdate()
            # previous quarter
            q = (today.month - 1) // 3  # 0..3 current quarter index
            prev_q = (q - 1) % 4
            year = today.year if q > 0 else today.year - 1
            start_month = prev_q * 3 + 1
            quarter_start = date(year, start_month, 1)
            quarter_end = date(year, start_month + 3, 1) - timedelta(days=1)
            self.date_from = self.date_from or quarter_start
            self.date_to = self.date_to or quarter_end
        # else Custom: expect user-provided

    @frappe.whitelist()
    def run_generation(self):
        self._ensure_dates()
        df, dt = getdate(self.date_from), getdate(self.date_to)

        # Snapshot cache check (12h TTL)
        key = f"sf_rep:{df}:{dt}"
        try:
            cached_raw = frappe.cache().get_value(key)
            if cached_raw:
                snap = json.loads(cached_raw) if isinstance(cached_raw, str) else cached_raw
                ts = get_datetime(snap.get("ts")) if snap.get("ts") else None
                if ts and (now_datetime() - ts) < timedelta(hours=12):
                    self._apply_snapshot(snap)
                    self.cache_key = key
                    self.cached_at = now_datetime()
                    self.generated_at = now_datetime()
                    self.generated_by = frappe.session.user
                    self.save()
                    return {"ok": True}
        except Exception:
            pass

        # Campaigns in period
        campaigns = frappe.get_all(
            "Survey Campaign",
            filters={"creation": ["between", [df, dt]]},
            fields=["name", "campaign_name", "total_sent", "total_responses", "response_rate"],
            order_by="total_sent desc",
            limit=1000,
        )
        self.total_campaigns = len(campaigns)
        sent_sum = sum((c.get("total_sent") or 0) for c in campaigns)
        resp_sum = sum((c.get("total_responses") or 0) for c in campaigns)

        # Responses in period (for sentiment + robust counts)
        responses = frappe.get_all(
            "Survey Response",
            filters={"response_time": ["between", [df, dt]], "status": ["in", ["Completed", "Partial"]]},
            fields=["name", "campaign", "sentiment_score", "response_time"],
            limit=20000,
        )
        resp_completed = [r for r in responses if r.get("sentiment_score") is not None]
        self.total_responses = len(responses)

        # If campaigns have no sent stats, compute from responses' sent_time
        if not sent_sum:
            try:
                sent_sum = frappe.db.count(
                    "Survey Response",
                    filters={"sent_time": ["between", [df, dt]]},
                )
            except Exception:
                pass
        self.total_surveys_sent = sent_sum
        self.response_rate = round((self.total_responses / sent_sum * 100.0), 2) if sent_sum else 0

        # Sentiment aggregation
        scores = [float(r.get("sentiment_score")) for r in resp_completed if r.get("sentiment_score") is not None]
        self.avg_sentiment_score = round(sum(scores) / len(scores), 3) if scores else 0
        dist = {"very_positive": 0, "positive": 0, "neutral": 0, "negative": 0, "very_negative": 0}
        for s in scores:
            if s >= SENT_THRESHOLDS["very_positive"]:
                dist["very_positive"] += 1
            elif s >= SENT_THRESHOLDS["positive"]:
                dist["positive"] += 1
            elif s >= SENT_THRESHOLDS["neutral"]:
                dist["neutral"] += 1
            elif s >= SENT_THRESHOLDS["negative"]:
                dist["negative"] += 1
            else:
                dist["very_negative"] += 1
        self.very_positive_count = dist["very_positive"]
        self.positive_count = dist["positive"]
        self.neutral_count = dist["neutral"]
        self.negative_count = dist["negative"]
        self.very_negative_count = dist["very_negative"]

        # Channel interactions (Unified Inbox Message)
        msgs = frappe.get_all(
            "Unified Inbox Message",
            filters={"timestamp": ["between", [df, dt]]},
            fields=["platform", "direction", "delivery_status", "platform_metadata", "conversation"],
            limit=50000,
        )
        platform_counts = {p: {"in": 0, "out": 0} for p in PLATFORMS}
        inbound = outbound = 0
        inbound_by_p: Dict[str,int] = {}
        outbound_by_p: Dict[str,int] = {}
        delivery_by_p: Dict[str,Dict[str,int]] = {}
        failure_reasons: Dict[str,int] = {}
        for m in msgs:
            plat = (m.get("platform") or "").strip() or "Unknown"
            direction = (m.get("direction") or "").lower()
            if plat not in platform_counts:
                platform_counts[plat] = {"in": 0, "out": 0}
            if direction.startswith("in"):
                platform_counts[plat]["in"] += 1
                inbound += 1
                inbound_by_p[plat] = inbound_by_p.get(plat, 0) + 1
            else:
                platform_counts[plat]["out"] += 1
                outbound += 1
                outbound_by_p[plat] = outbound_by_p.get(plat, 0) + 1
                # delivery breakdown only for outbound
                status = (m.get("delivery_status") or "Pending").title()
                delivery_by_p.setdefault(plat, {})
                delivery_by_p[plat][status] = delivery_by_p[plat].get(status, 0) + 1
                # failure reason detection
                if status == "Failed":
                    md = m.get("platform_metadata")
                    try:
                        meta = json.loads(md) if isinstance(md, str) else (md or {})
                    except Exception:
                        meta = {}
                    reason = meta.get("error_reason") or meta.get("error") or meta.get("status_message") or "Unknown"
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        self.inbound_count = inbound
        self.outbound_count = outbound
        self.total_interactions = inbound + outbound

        # Avg First Response Time (minutes) across conversations created in period
        convs = frappe.get_all(
            "Unified Inbox Conversation",
            filters={"creation": ["between", [df, dt]]},
            fields=["name", "platform"],
            limit=20000,
        )
        plat_conv: Dict[str,int] = {}
        frt_values: List[float] = []
        for c in convs:
            plat_conv[c.get("platform") or "Unknown"] = plat_conv.get(c.get("platform") or "Unknown", 0) + 1
            try:
                first_in = frappe.get_all(
                    "Unified Inbox Message",
                    filters={"conversation": c["name"], "direction": "Inbound"},
                    fields=["timestamp"], order_by="timestamp asc", limit=1
                )
                first_out = frappe.get_all(
                    "Unified Inbox Message",
                    filters={"conversation": c["name"], "direction": ["in", ["Outbound", "AI Outbound"]]},
                    fields=["timestamp"], order_by="timestamp asc", limit=1
                )
                if first_in and first_out:
                    t1 = get_datetime(first_in[0]["timestamp"]) if first_in[0].get("timestamp") else None
                    t2 = get_datetime(first_out[0]["timestamp"]) if first_out[0].get("timestamp") else None
                    if t1 and t2:
                        delta_min = max(0.0, (t2 - t1).total_seconds() / 60.0)
                        frt_values.append(delta_min)
            except Exception:
                continue
        def _percentile(arr: List[float], p: float) -> float:
            if not arr:
                return 0.0
            a = sorted(arr)
            k = max(0, min(len(a)-1, int(round((p/100.0)*(len(a)-1)))))
            return float(a[k])


        # FRT metrics
        self.avg_first_response_minutes = round(sum(frt_values) / len(frt_values), 2) if frt_values else 0
        self.p90_first_response_minutes = round(_percentile(frt_values, 90), 2)
        self.p95_first_response_minutes = round(_percentile(frt_values, 95), 2)

        # Charts
        self.survey_chart_json = json.dumps(self._build_survey_chart(campaigns, sent_sum, resp_sum))
        self.sentiment_chart_json = json.dumps(self._build_sentiment_chart(dist))
        self.channel_chart_json = json.dumps(self._build_channel_chart(platform_counts))
        self.trend_chart_json = json.dumps(self._build_trend_chart(responses))
        self.delivery_chart_json = json.dumps(self._build_delivery_chart(delivery_by_p))
        linked_rates = self._compute_survey_linked_platform_rates(df, dt)
        all_plats = set(inbound_by_p.keys()) | set(outbound_by_p.keys())
        if linked_rates:
            covered = len(linked_rates)
            total = len(all_plats | set(linked_rates.keys()))
            if covered < total:
                self.platform_rr_mode = "Mixed (Linked + Estimated)"
            else:
                self.platform_rr_mode = "Survey-linked"
        else:
            self.platform_rr_mode = "Estimated"
        self.platform_response_rate_json = json.dumps(
            self._build_platform_response_rate_chart(inbound_by_p, outbound_by_p, linked_rates=linked_rates or None)
        )

        # KPIs/Alerts and main HTML
        kpi_html, alerts_html = self._build_kpis_and_alerts(campaigns, responses, failure_reasons)
        self.kpi_html = kpi_html
        self.alerts_html = alerts_html
        self.report_html = self._build_report_html(df, dt, plat_conv)


        # Persist snapshot to cache for faster subsequent loads of same window
        try:
            snapshot = {
                "ts": str(now_datetime()),
                "period": {"from": str(df), "to": str(dt)},
                "metrics": {
                    "total_campaigns": self.total_campaigns,
                    "total_surveys_sent": self.total_surveys_sent,
                    "total_responses": self.total_responses,
                    "response_rate": self.response_rate,
                    "avg_sentiment_score": self.avg_sentiment_score,
                    "very_positive": self.very_positive_count,
                    "positive": self.positive_count,
                    "neutral": self.neutral_count,
                    "negative": self.negative_count,
                    "very_negative": self.very_negative_count,
                    "inbound": self.inbound_count,
                    "outbound": self.outbound_count,
                    "total_interactions": self.total_interactions,
                    "avg_frt": self.avg_first_response_minutes,
                    "p90_frt": self.p90_first_response_minutes,
                    "p95_frt": self.p95_first_response_minutes,
                },
                "charts": {
                    "survey": self.survey_chart_json,
                    "sentiment": self.sentiment_chart_json,
                    "channel": self.channel_chart_json,
                    "delivery": self.delivery_chart_json,
                    "platform_rr": self.platform_response_rate_json,
                    "trend": self.trend_chart_json,
                },
                "kpi_html": self.kpi_html,
                "alerts_html": self.alerts_html,
                "report_html": self.report_html,
            }
            frappe.cache().set_value(key, json.dumps(snapshot))
            self.cache_key = key
            self.cached_at = now_datetime()
            self.snapshot_json = json.dumps(snapshot)
        except Exception:
            pass

        # stamp and save results
        self.generated_at = now_datetime()
        self.generated_by = frappe.session.user
        self.save(ignore_permissions=True)

    def _build_delivery_chart(self, delivery_by_p: Dict[str, Dict[str, int]]):
        plats = sorted(delivery_by_p.keys())
        known_statuses = ["Delivered", "Read", "Sent", "Pending", "Failed"]
        all_statuses = list({s for p in plats for s in delivery_by_p.get(p, {}).keys()})
        statuses = [s for s in known_statuses if s in all_statuses] + [s for s in all_statuses if s not in known_statuses]
        datasets = []
        for st in statuses:
            values = [delivery_by_p.get(p, {}).get(st, 0) for p in plats]
            datasets.append({"name": st, "values": values})
        return {
            "data": {"labels": plats, "datasets": datasets},
            "type": "bar",
            "barOptions": {"stacked": 1}
        }

    def _build_platform_response_rate_chart(self, inbound_by_p: Dict[str, int], outbound_by_p: Dict[str, int], linked_rates: Dict[str, float] | None = None):
        # Build platform list as union of all sources so we can mix linked and estimated
        all_plats = set(inbound_by_p.keys()) | set(outbound_by_p.keys())
        if linked_rates:
            all_plats |= set(linked_rates.keys())
        plats = sorted(all_plats)
        rates = []
        for p in plats:
            if linked_rates and p in linked_rates:
                rate = float(linked_rates[p])
            else:
                inbound = inbound_by_p.get(p, 0)
                outbound = outbound_by_p.get(p, 0)
                rate = (inbound / outbound * 100.0) if outbound else 0
            rates.append(min(100.0, round(rate, 2)))
        return {
            "data": {"labels": plats, "datasets": [{"name": "Response Rate %", "values": rates}]},
            "type": "bar",
            "colors": ["#5EAD56"]
        }

    def _compute_survey_linked_platform_rates(self, df, dt) -> Dict[str, float]:
        """
        Compute per-platform response rates using Survey Responses linked via
        single-channel campaigns (survey-linked). If a campaign has more than
        one active channel, it is ambiguous and excluded from per-platform split.
        Denominator: Survey Responses with sent_time in window (any status)
        Numerator: Survey Responses with response_time in window and status in Completed/Partial
        """
        # Find responses (deliveries) sent in window
        deliveries = frappe.get_all(
            "Survey Response",
            filters={"sent_time": ["between", [df, dt]]},
            fields=["name", "campaign", "status"],
            limit=50000,
        )
        if not deliveries:
            return {}
        # Prefetch channels per campaign
        campaign_names = list({d["campaign"] for d in deliveries if d.get("campaign")})
        if not campaign_names:
            return {}
        chan_rows = frappe.get_all(
            "Survey Distribution Channel",
            filters={"parent": ["in", campaign_names], "is_active": 1},
            fields=["parent", "channel"],
            limit=50000,
        )
        channels_by_campaign: Dict[str, set] = {}
        for r in chan_rows:
            channels_by_campaign.setdefault(r["parent"], set()).add(r["channel"])
        single_channel_map = {c: list(chs)[0] for c, chs in channels_by_campaign.items() if len(chs) == 1}
        if not single_channel_map:
            return {}
        # Build denominators per platform from unambiguous campaigns
        denom: Dict[str, int] = {}
        for d in deliveries:
            camp = d.get("campaign")
            if not camp or camp not in single_channel_map:
                continue
            plat = single_channel_map[camp]
            denom[plat] = denom.get(plat, 0) + 1
        if not denom:
            return {}
        # Numerators: completed/partial in window from same single-channel campaigns
        responses = frappe.get_all(
            "Survey Response",
            filters={"response_time": ["between", [df, dt]], "status": ["in", ["Completed", "Partial"]]},
            fields=["name", "campaign"],
            limit=50000,
        )
        numer: Dict[str, int] = {}
        for r in responses:
            camp = r.get("campaign")
            if not camp or camp not in single_channel_map:
                continue
            plat = single_channel_map[camp]
            numer[plat] = numer.get(plat, 0) + 1
        # Compute rates
        rates: Dict[str, float] = {}
        for plat, dcount in denom.items():
            ncount = numer.get(plat, 0)
            rates[plat] = (ncount / dcount * 100.0) if dcount else 0.0
        return rates

    def _build_kpis_and_alerts(self, campaigns, responses, failure_reasons: Dict[str,int]):
        camp_name = {c.get("name"): (c.get("campaign_name") or c.get("name")) for c in campaigns}
        totals: Dict[str, int] = {}
        negs: Dict[str, int] = {}
        for r in responses:
            c = r.get("campaign")
            if not c:
                continue
            totals[c] = totals.get(c, 0) + 1
            try:
                score = float(r.get("sentiment_score")) if r.get("sentiment_score") is not None else 0
            except Exception:
                score = 0
            if score < 0:
                negs[c] = negs.get(c, 0) + 1
        rows = []
        for c, t in totals.items():
            n = negs.get(c, 0)
            ratio = (n / t * 100.0) if t else 0
            rows.append((c, camp_name.get(c, c), round(ratio, 2), n, t))
        top_neg = sorted(rows, key=lambda x: (x[2], x[3]), reverse=True)[:5]
        top_li = "".join([
            f"<li><a href='#' class='sf-route' data-doctype='Survey Response' data-filters='{json.dumps({'campaign': name})}'>"
            f"{frappe.utils.escape_html(label)}</a> — {ratio}% negative ({n}/{t})</li>" for name, label, ratio, n, t in top_neg
        ]) or "<li>No data</li>"
        kpi_html = f"<div><strong>Top negative campaigns</strong><ul>{top_li}</ul></div>"

        alerts = []
        for c in campaigns:
            sent = int(c.get('total_sent') or 0)
            rr = float(c.get('response_rate') or 0)
            if sent > 10 and rr < 20.0:
                label = camp_name.get(c.get('name'), c.get('name'))
                filt = json.dumps({"name": c.get('name')})
                alerts.append(f"<li><a href='#' class='sf-route' data-doctype='Survey Campaign' data-filters='{filt}'>"
                               f"{frappe.utils.escape_html(label)}</a> — Response rate {rr}% on {sent} sent</li>")
        fr_sorted = sorted(failure_reasons.items(), key=lambda kv: kv[1], reverse=True)[:5]
        fr_html = "".join([f"<li>{frappe.utils.escape_html(k)} — {v}</li>" for k, v in fr_sorted]) or "<li>No failures</li>"
        alerts_html = f"<div><strong>Low response-rate campaigns</strong><ul>{''.join(alerts) or '<li>None</li>'}</ul>" \
                       f"<div class='mt-2'><strong>Top delivery failure reasons</strong><ul>{fr_html}</ul></div></div>"
        return kpi_html, alerts_html

    def _apply_snapshot(self, snap: Dict[str, Any]):
        m = snap.get("metrics", {})
        self.total_campaigns = m.get("total_campaigns", 0)
        self.total_surveys_sent = m.get("total_surveys_sent", 0)
        self.total_responses = m.get("total_responses", 0)
        self.response_rate = m.get("response_rate", 0)
        self.avg_sentiment_score = m.get("avg_sentiment_score", 0)
        self.very_positive_count = m.get("very_positive", 0)
        self.positive_count = m.get("positive", 0)
        self.neutral_count = m.get("neutral", 0)
        self.negative_count = m.get("negative", 0)
        self.very_negative_count = m.get("very_negative", 0)
        self.inbound_count = m.get("inbound", 0)
        self.outbound_count = m.get("outbound", 0)
        self.total_interactions = m.get("total_interactions", 0)
        self.avg_first_response_minutes = m.get("avg_frt", 0)
        self.p90_first_response_minutes = m.get("p90_frt", 0)
        self.p95_first_response_minutes = m.get("p95_frt", 0)
        charts = snap.get("charts", {})
        self.survey_chart_json = charts.get("survey")
        self.sentiment_chart_json = charts.get("sentiment")
        self.channel_chart_json = charts.get("channel")
        self.delivery_chart_json = charts.get("delivery")
        self.platform_response_rate_json = charts.get("platform_rr")
        self.trend_chart_json = charts.get("trend")
        self.kpi_html = snap.get("kpi_html")
        self.alerts_html = snap.get("alerts_html")
        self.report_html = snap.get("report_html") or self.report_html

        self.generated_at = now_datetime()
        self.generated_by = frappe.session.user
        self.save()
        return {"ok": True}

    def _build_survey_chart(self, campaigns, sent_sum, resp_sum):
        # Simple totals chart
        labels = ["Sent", "Responses"]
        return {
            "data": {"labels": labels, "datasets": [{"name": "All Surveys", "values": [sent_sum, resp_sum]}]},
            "type": "bar",
            "colors": ["#4B9CD3"],
        }

    def _build_sentiment_chart(self, dist):
        labels = ["Very Positive", "Positive", "Neutral", "Negative", "Very Negative"]
        values = [dist["very_positive"], dist["positive"], dist["neutral"], dist["negative"], dist["very_negative"]]
        return {"data": {"labels": labels, "datasets": [{"name": "Sentiment", "values": values}]}, "type": "pie"}

    def _build_channel_chart(self, platform_counts):
        plats = list(platform_counts.keys())
        inbound = [platform_counts[p]["in"] for p in plats]
        outbound = [platform_counts[p]["out"] for p in plats]
        return {
            "data": {"labels": plats, "datasets": [
                {"name": "Inbound", "values": inbound},
                {"name": "Outbound", "values": outbound}
            ]},
            "type": "bar",
            "barOptions": {"stacked": 1}
        }

    def _build_trend_chart(self, responses):
        # Avg sentiment per day (response_time)
        by_day = {}
        for r in responses:
            ts = r.get("response_time")
            if not ts:
                continue
            day = str(ts)[:10]
            by_day.setdefault(day, []).append(float(r.get("sentiment_score") or 0))
        labels = sorted(by_day.keys())
        values = [round(sum(v)/len(v), 3) for k, v in sorted(by_day.items())]
        return {"data": {"labels": labels, "datasets": [{"name": "Avg Sentiment", "values": values}]}, "type": "line"}

    def _build_report_html(self, df, dt, plat_conv):
        safe = frappe.utils.escape_html
        # KPI cards (compact grid)
        cards = [
            ("Campaigns", self.total_campaigns),
            ("Sent", self.total_surveys_sent),
            ("Responses", self.total_responses),
            ("Resp Rate %", self.response_rate),
            ("Avg Sent", self.avg_sentiment_score),
            ("Inbound", self.inbound_count),
            ("Outbound", self.outbound_count),
            ("Avg FRT (min)", self.avg_first_response_minutes),
            ("p90 FRT", self.p90_first_response_minutes),
            ("p95 FRT", self.p95_first_response_minutes),
        ]
        items = "".join([
            f'<div class="col-md-3 col-sm-4 col-6"><div class="card"><div class="card-body p-2"><div class="text-muted small">{safe(k)}</div><div class="h4 m-0">{safe(v)}</div></div></div></div>'
            for k, v in cards
        ])
        header = f"<h4 class='mb-1'>Survey Feedback Report</h4><div class='text-muted'>{formatdate(df)} – {formatdate(dt)}</div>"
        filt_campaigns = json.dumps({"creation": ["between", [str(df), str(dt)]]})
        filt_responses = json.dumps({"response_time": ["between", [str(df), str(dt)]], "status": ["in", ["Completed", "Partial"]]})
        filt_convos_all = json.dumps({"creation": ["between", [str(df), str(dt)]]})
        links = (
            f"<div class='mt-2 small'>"
            f"<a href='#' class='sf-route' data-doctype='Survey Campaign' data-filters='{filt_campaigns}'>Campaigns</a> · "
            f"<a href='#' class='sf-route' data-doctype='Survey Response' data-filters='{filt_responses}'>Responses</a> · "
            f"<a href='#' class='sf-route' data-doctype='Unified Inbox Conversation' data-filters='{filt_convos_all}'>Conversations</a>"
            f"</div>"
        )
        # Conversations by platform drilldown
        plat_rows = []
        for p, n in sorted((plat_conv or {}).items(), key=lambda kv: kv[1], reverse=True):
            filt = json.dumps({"creation": ["between", [str(df), str(dt)]], "platform": p})
            plat_rows.append(f"<li><a href='#' class='sf-route' data-doctype='Unified Inbox Conversation' data-filters='{filt}'>"
                             f"{safe(p)}</a> — {n}</li>")
        plat_html = f"<div class='mt-2'><strong>Conversations by platform</strong><ul class='mt-1 mb-2'>{''.join(plat_rows) or '<li>None</li>'}</ul></div>"
        # Insights + Alerts side-by-side if available
        insights = (
            f"<div class='row mt-2'>"
            f"<div class='col-md-6'>{self.kpi_html or ''}</div>"
            f"<div class='col-md-6'>{self.alerts_html or ''}</div>"
            f"</div>"
        )
        # Chart placeholders
        charts = (
            "<div class='row mt-3'>"
            "<div class='col-md-6'><div id='survey_chart'></div></div>"
            "<div class='col-md-6'><div id='sentiment_chart'></div></div>"
            "<div class='col-md-6 mt-3'><div id='channel_chart'></div></div>"
            "<div class='col-md-6 mt-3'><div id='delivery_chart'></div></div>"
            f"<div class='col-md-6 mt-3'><div class='small text-muted'>Platform Response Rates ({safe(getattr(self, 'platform_rr_mode', '') or 'Estimated')})</div><div id='platform_rr_chart'></div></div>"
            "<div class='col-md-6 mt-3'><div id='trend_chart'></div></div>"
            "</div>"
        )
        return f"<div class=\"mb-2\">{header}{links}</div><div class=\"row\">{items}</div>{plat_html}{insights}{charts}"

    @frappe.whitelist()
    def generate_pdf(self):
        html = f"<div class='print-format'>{getattr(self, 'report_html', '') or ''}</div>"
        pdf = get_pdf(html)
        fname = f"Survey-Feedback-Report-{self.name}.pdf"
        frappe.response.filename = fname
        frappe.response.filecontent = pdf
        frappe.response.type = "download"

    @frappe.whitelist()
    def email_report(self, recipients=None):
        recipients = recipients or self._get_role_emails(["Corporate Affairs", "WCFCB Manager"])
        if not recipients:
            return {"ok": False, "message": "No recipients"}
        self.generate_pdf()
        frappe.sendmail(
            recipients=recipients,
            subject=f"Survey Feedback Report {formatdate(self.date_from)}–{formatdate(self.date_to)}",
            message="Please find the attached Survey Feedback Report.",
            attachments=[{"fname": frappe.response.filename, "fcontent": frappe.response.filecontent}],
        )
        return {"ok": True, "sent_to": recipients}

    def _get_role_emails(self, roles):
        emails = []
        for role in roles:
            users = frappe.db.get_all("Has Role", filters={"role": role}, fields=["parent"], limit=500)
            for u in users:
                email = frappe.db.get_value("User", u["parent"], "email")
                if email:
                    emails.append(email)
        # de-duplicate
        return sorted(list({e.lower(): e for e in emails}.values()))

@frappe.whitelist()
def get_ai_insights(name: str, query: str):
    """Return Antoine-style insights for a Survey Feedback Report."""
    doc = frappe.get_doc("Survey Feedback Report", name)

    history = frappe.get_all(
        "Survey Feedback Report",
        filters={"period_type": doc.period_type},
        fields=[
            "name",
            "date_from",
            "date_to",
            "total_campaigns",
            "total_surveys_sent",
            "total_responses",
            "response_rate",
            "avg_sentiment_score",
            "very_positive_count",
            "positive_count",
            "neutral_count",
            "negative_count",
            "very_negative_count",
            "inbound_count",
            "outbound_count",
            "total_interactions",
            "avg_first_response_minutes",
            "p90_first_response_minutes",
            "p95_first_response_minutes",
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
            "total_campaigns": int(doc.total_campaigns or 0),
            "total_surveys_sent": int(doc.total_surveys_sent or 0),
            "total_responses": int(doc.total_responses or 0),
            "response_rate": float(doc.response_rate or 0),
            "avg_sentiment_score": float(doc.avg_sentiment_score or 0),
            "very_positive_count": int(doc.very_positive_count or 0),
            "positive_count": int(doc.positive_count or 0),
            "neutral_count": int(doc.neutral_count or 0),
            "negative_count": int(doc.negative_count or 0),
            "very_negative_count": int(doc.very_negative_count or 0),
            "inbound_count": int(doc.inbound_count or 0),
            "outbound_count": int(doc.outbound_count or 0),
            "total_interactions": int(doc.total_interactions or 0),
            "avg_first_response_minutes": float(doc.avg_first_response_minutes or 0),
            "p90_first_response_minutes": float(getattr(doc, "p90_first_response_minutes", 0) or 0),
            "p95_first_response_minutes": float(getattr(doc, "p95_first_response_minutes", 0) or 0),
        },
        "history": history,
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService

        ai = EnhancedAIService()
        answer = ai.generate_survey_feedback_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Survey Feedback Report AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure Antoine/OpenAI settings in Enhanced AI Settings."
            )
        }

# Schedulers
def _create_and_send(period_type: str):
    doc = frappe.get_doc({
        "doctype": "Survey Feedback Report",
        "period_type": period_type,
    })
    doc.insert(ignore_permissions=True)
    doc.run_generation()
    try:
        doc.email_report()
    except Exception:
        pass

def schedule_monthly_survey_feedback_reports():
    _create_and_send("Monthly")

# Backward-compatible wrappers so both doc.run_generation and module path method calls work
@frappe.whitelist()
def run_generation(name: str = None):
    # Accept name via arg, form_dict.name, or embedded doc/docs payload
    if not name:
        name = frappe.form_dict.get("name")
    if not name:
        doc_arg = frappe.form_dict.get("doc") or frappe.form_dict.get("docs")
        if doc_arg:
            try:
                payload = json.loads(doc_arg) if isinstance(doc_arg, str) else doc_arg
                if isinstance(payload, dict):
                    name = payload.get("name")
            except Exception:
                pass
    if not name:
        frappe.throw("Document name is required")
    doc = frappe.get_doc("Survey Feedback Report", name)
    return doc.run_generation()

@frappe.whitelist()
def generate_pdf(name: str = None):
    if not name:
        name = frappe.form_dict.get("name")
    if not name:
        doc_arg = frappe.form_dict.get("doc") or frappe.form_dict.get("docs")
        if doc_arg:
            try:
                payload = json.loads(doc_arg) if isinstance(doc_arg, str) else doc_arg
                if isinstance(payload, dict):
                    name = payload.get("name")
            except Exception:
                pass
    if not name:
        frappe.throw("Document name is required")
    doc = frappe.get_doc("Survey Feedback Report", name)
    return doc.generate_pdf()

@frappe.whitelist()
def email_report(name: str = None, recipients=None):
    if not name:
        name = frappe.form_dict.get("name")
    if not name:
        doc_arg = frappe.form_dict.get("doc") or frappe.form_dict.get("docs")
        if doc_arg:
            try:
                payload = json.loads(doc_arg) if isinstance(doc_arg, str) else doc_arg
                if isinstance(payload, dict):
                    name = payload.get("name")
            except Exception:
                pass
    if not name:
        frappe.throw("Document name is required")
    doc = frappe.get_doc("Survey Feedback Report", name)
    return doc.email_report(recipients=recipients)


def schedule_quarterly_survey_feedback_reports():
    _create_and_send("Quarterly")

