"""
Survey Feedback Analysis - Native ERPNext Script Report

Comprehensive analysis of survey campaigns, responses, sentiment distribution,
channel performance, and response metrics using native ERPNext doctypes.

Includes Antoine AI integration for intelligent insights.
"""

import json
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe.utils import getdate, get_first_day, get_last_day, now_datetime, formatdate

# Platforms for channel breakdown
PLATFORMS = ["WhatsApp", "Facebook", "Instagram", "Telegram", "Tawk.to", "USSD"]

# Sentiment score thresholds
SENT_THRESHOLDS = {
    "very_positive": 0.8,
    "positive": 0.4,
    "neutral": -0.2,
    "negative": -0.6
}


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple:
    """Main entry point for Script Report."""
    filters = frappe._dict(filters or {})
    _ensure_dates(filters)

    columns = get_columns()
    data, summary_data = get_data(filters)
    chart = get_chart_data(summary_data)
    report_summary = get_report_summary(summary_data)

    return columns, data, None, chart, report_summary, False


def _ensure_dates(filters: frappe._dict):
    """Infer dates based on period_type when missing."""
    period_type = filters.get("period_type", "Monthly")

    if period_type == "Monthly":
        today = getdate()
        first_this_month = date(today.year, today.month, 1)
        last_prev_month = first_this_month - timedelta(days=1)
        first_prev_month = date(last_prev_month.year, last_prev_month.month, 1)
        filters.date_from = filters.get("date_from") or first_prev_month
        filters.date_to = filters.get("date_to") or last_prev_month
    elif period_type == "Quarterly":
        today = getdate()
        q = (today.month - 1) // 3
        prev_q = (q - 1) % 4
        year = today.year if q > 0 else today.year - 1
        start_month = prev_q * 3 + 1
        quarter_start = date(year, start_month, 1)
        quarter_end = date(year, start_month + 2, 1)
        quarter_end = date(quarter_end.year, quarter_end.month + 1, 1) - timedelta(days=1) if quarter_end.month < 12 else date(quarter_end.year, 12, 31)
        filters.date_from = filters.get("date_from") or quarter_start
        filters.date_to = filters.get("date_to") or quarter_end
    else:  # Custom
        if not filters.get("date_from") or not filters.get("date_to"):
            filters.date_to = getdate()
            filters.date_from = frappe.utils.add_days(filters.date_to, -29)


def get_columns() -> List[Dict[str, Any]]:
    """Define report columns for response-level data."""
    return [
        {"fieldname": "name", "label": "Response ID", "fieldtype": "Link", "options": "Survey Response", "width": 150},
        {"fieldname": "campaign", "label": "Campaign", "fieldtype": "Link", "options": "Survey Campaign", "width": 180},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 100},
        {"fieldname": "sentiment_score", "label": "Sentiment", "fieldtype": "Float", "width": 100, "precision": 2},
        {"fieldname": "sentiment_label", "label": "Sentiment Label", "fieldtype": "Data", "width": 120},
        {"fieldname": "recipient_phone", "label": "Phone", "fieldtype": "Data", "width": 130},
        {"fieldname": "sent_time", "label": "Sent Time", "fieldtype": "Datetime", "width": 150},
        {"fieldname": "response_time", "label": "Response Time", "fieldtype": "Datetime", "width": 150},
        {"fieldname": "response_duration_min", "label": "Duration (min)", "fieldtype": "Float", "width": 110, "precision": 1},
    ]


def get_sentiment_label(score: float) -> str:
    """Convert sentiment score to label."""
    if score is None:
        return "Unknown"
    if score >= SENT_THRESHOLDS["very_positive"]:
        return "Very Positive"
    if score >= SENT_THRESHOLDS["positive"]:
        return "Positive"
    if score >= SENT_THRESHOLDS["neutral"]:
        return "Neutral"
    if score >= SENT_THRESHOLDS["negative"]:
        return "Negative"
    return "Very Negative"


def get_data(filters: frappe._dict) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch survey responses and compute summary metrics."""
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    # Build conditions
    conditions = ["sr.response_time BETWEEN %(df)s AND %(dt)s"]
    values = {"df": df, "dt": dt}

    if filters.get("campaign"):
        conditions.append("sr.campaign = %(campaign)s")
        values["campaign"] = filters.campaign

    if filters.get("status"):
        conditions.append("sr.status = %(status)s")
        values["status"] = filters.status

    where_clause = " AND ".join(conditions)

    # Fetch responses
    responses = frappe.db.sql(f"""
        SELECT
            sr.name, sr.campaign, sr.status, sr.sentiment_score,
            sr.recipient_phone, sr.sent_time, sr.response_time
        FROM `tabSurvey Response` sr
        WHERE {where_clause}
        ORDER BY sr.response_time DESC
        LIMIT 5000
    """, values, as_dict=True)

    # Build data rows and compute summary
    data = []
    summary = {
        "total_responses": 0,
        "very_positive": 0, "positive": 0, "neutral": 0, "negative": 0, "very_negative": 0,
        "sentiment_scores": [],
        "response_durations": [],
    }

    for r in responses:
        summary["total_responses"] += 1
        score = r.get("sentiment_score")
        label = get_sentiment_label(score)

        # Count sentiment distribution
        if label == "Very Positive":
            summary["very_positive"] += 1
        elif label == "Positive":
            summary["positive"] += 1
        elif label == "Neutral":
            summary["neutral"] += 1
        elif label == "Negative":
            summary["negative"] += 1
        elif label == "Very Negative":
            summary["very_negative"] += 1

        if score is not None:
            summary["sentiment_scores"].append(float(score))

        # Calculate response duration
        duration_min = None
        if r.get("sent_time") and r.get("response_time"):
            try:
                from frappe.utils import get_datetime
                sent = get_datetime(r["sent_time"])
                resp = get_datetime(r["response_time"])
                duration_min = max(0, (resp - sent).total_seconds() / 60.0)
                summary["response_durations"].append(duration_min)
            except Exception:
                pass

        data.append({
            "name": r.get("name"),
            "campaign": r.get("campaign"),
            "status": r.get("status"),
            "sentiment_score": score,
            "sentiment_label": label,
            "recipient_phone": r.get("recipient_phone"),
            "sent_time": r.get("sent_time"),
            "response_time": r.get("response_time"),
            "response_duration_min": round(duration_min, 1) if duration_min else None,
        })

    # Compute additional summary metrics
    summary["avg_sentiment"] = round(sum(summary["sentiment_scores"]) / len(summary["sentiment_scores"]), 3) if summary["sentiment_scores"] else 0
    summary["avg_response_duration"] = round(sum(summary["response_durations"]) / len(summary["response_durations"]), 2) if summary["response_durations"] else 0

    # Get campaign-level aggregates
    campaigns = frappe.get_all(
        "Survey Campaign",
        filters={"creation": ["between", [df, dt]]},
        fields=["name", "campaign_name", "total_sent", "total_responses", "response_rate"],
        order_by="total_sent desc",
        limit=1000,
    )
    summary["total_campaigns"] = len(campaigns)
    summary["total_surveys_sent"] = sum((c.get("total_sent") or 0) for c in campaigns)
    summary["response_rate"] = round((summary["total_responses"] / summary["total_surveys_sent"] * 100.0), 2) if summary["total_surveys_sent"] else 0

    # Get channel interactions
    channel_data = _get_channel_metrics(df, dt)
    summary.update(channel_data)

    return data, summary


def _get_channel_metrics(df, dt) -> Dict[str, Any]:
    """Get channel/interaction metrics from Unified Inbox."""
    msgs = frappe.get_all(
        "Unified Inbox Message",
        filters={"timestamp": ["between", [df, dt]]},
        fields=["platform", "direction"],
        limit=50000,
    )

    platform_counts = {p: {"in": 0, "out": 0} for p in PLATFORMS}
    inbound = outbound = 0

    for m in msgs:
        plat = (m.get("platform") or "").strip() or "Unknown"
        direction = (m.get("direction") or "").lower()
        if plat not in platform_counts:
            platform_counts[plat] = {"in": 0, "out": 0}
        if direction.startswith("in"):
            platform_counts[plat]["in"] += 1
            inbound += 1
        else:
            platform_counts[plat]["out"] += 1
            outbound += 1

    return {
        "inbound_count": inbound,
        "outbound_count": outbound,
        "total_interactions": inbound + outbound,
        "platform_counts": platform_counts,
    }


def get_chart_data(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Build primary sentiment distribution chart."""
    return {
        "data": {
            "labels": ["Very Positive", "Positive", "Neutral", "Negative", "Very Negative"],
            "datasets": [{
                "name": "Responses",
                "values": [
                    summary.get("very_positive", 0),
                    summary.get("positive", 0),
                    summary.get("neutral", 0),
                    summary.get("negative", 0),
                    summary.get("very_negative", 0),
                ]
            }]
        },
        "type": "pie",
        "colors": ["#28a745", "#7cd6fd", "#f4a100", "#ff6b6b", "#dc3545"],
    }


def get_report_summary(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build report summary cards."""
    return [
        {"value": summary.get("total_campaigns", 0), "label": "Campaigns", "datatype": "Int"},
        {"value": summary.get("total_surveys_sent", 0), "label": "Surveys Sent", "datatype": "Int"},
        {"value": summary.get("total_responses", 0), "label": "Responses", "datatype": "Int", "indicator": "green"},
        {"value": f"{summary.get('response_rate', 0):.1f}%", "label": "Response Rate", "datatype": "Data"},
        {"value": summary.get("avg_sentiment", 0), "label": "Avg Sentiment", "datatype": "Float"},
        {"value": f"{summary.get('avg_response_duration', 0):.1f}", "label": "Avg Resp (min)", "datatype": "Data"},
        {"value": summary.get("inbound_count", 0), "label": "Inbound", "datatype": "Int", "indicator": "blue"},
        {"value": summary.get("outbound_count", 0), "label": "Outbound", "datatype": "Int", "indicator": "orange"},
    ]


@frappe.whitelist()
def get_ai_insights(filters: str, query: str) -> Dict[str, Any]:
    """Return Antoine-style insights for the Survey Feedback Analysis report."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)

    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    # Get current data
    _, summary = get_data(filters)

    # Get historical reports for trend analysis
    history = []
    try:
        history = frappe.get_all(
            "Survey Feedback Report",
            filters={"period_type": filters.get("period_type", "Monthly")},
            fields=[
                "name", "date_from", "date_to", "total_campaigns", "total_surveys_sent",
                "total_responses", "response_rate", "avg_sentiment_score",
                "very_positive_count", "positive_count", "neutral_count",
                "negative_count", "very_negative_count", "inbound_count",
                "outbound_count", "avg_first_response_minutes"
            ],
            order_by="date_from desc",
            limit=12,
        )
    except Exception:
        pass

    context = {
        "window": {
            "period_type": filters.get("period_type", "Monthly"),
            "from": str(df),
            "to": str(dt),
        },
        "current": {
            "total_campaigns": summary.get("total_campaigns", 0),
            "total_surveys_sent": summary.get("total_surveys_sent", 0),
            "total_responses": summary.get("total_responses", 0),
            "response_rate": summary.get("response_rate", 0),
            "avg_sentiment_score": summary.get("avg_sentiment", 0),
            "very_positive_count": summary.get("very_positive", 0),
            "positive_count": summary.get("positive", 0),
            "neutral_count": summary.get("neutral", 0),
            "negative_count": summary.get("negative", 0),
            "very_negative_count": summary.get("very_negative", 0),
            "inbound_count": summary.get("inbound_count", 0),
            "outbound_count": summary.get("outbound_count", 0),
            "total_interactions": summary.get("total_interactions", 0),
            "avg_response_duration_minutes": summary.get("avg_response_duration", 0),
        },
        "history": history,
    }

    try:
        from assistant_crm.services.enhanced_ai_service import EnhancedAIService
        ai = EnhancedAIService()
        answer = ai.generate_survey_feedback_report_insights(query=query, context=context)
        return {"insights": answer}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Survey Feedback Analysis AI Insights Error")
        return {
            "insights": (
                "AI insights are temporarily unavailable. Please ask your system "
                "administrator to configure Antoine/OpenAI settings in Enhanced AI Settings."
            )
        }


@frappe.whitelist()
def get_sentiment_chart(filters: str) -> Dict[str, Any]:
    """Get sentiment distribution chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    _, summary = get_data(filters)

    return {
        "data": {
            "labels": ["Very Positive", "Positive", "Neutral", "Negative", "Very Negative"],
            "datasets": [{"name": "Count", "values": [
                summary.get("very_positive", 0),
                summary.get("positive", 0),
                summary.get("neutral", 0),
                summary.get("negative", 0),
                summary.get("very_negative", 0),
            ]}]
        },
        "type": "pie",
        "colors": ["#28a745", "#7cd6fd", "#f4a100", "#ff6b6b", "#dc3545"],
    }


@frappe.whitelist()
def get_channel_chart(filters: str) -> Dict[str, Any]:
    """Get channel interaction chart data."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    _, summary = get_data(filters)

    platform_counts = summary.get("platform_counts", {})
    plats = list(platform_counts.keys())
    inbound = [platform_counts[p]["in"] for p in plats]
    outbound = [platform_counts[p]["out"] for p in plats]

    return {
        "data": {
            "labels": plats,
            "datasets": [
                {"name": "Inbound", "values": inbound},
                {"name": "Outbound", "values": outbound}
            ]
        },
        "type": "bar",
        "barOptions": {"stacked": 1},
        "colors": ["#5e64ff", "#ffa00a"],
    }


@frappe.whitelist()
def get_survey_trend_chart(filters: str, months: int = 6) -> Dict[str, Any]:
    """Get survey response trend chart over months."""
    from frappe.utils import add_months, get_first_day

    labels = []
    response_values = []
    sent_values = []
    anchor = getdate()

    for i in range(months - 1, -1, -1):
        month_start = get_first_day(add_months(anchor, -i))
        if i > 0:
            month_end = get_first_day(add_months(anchor, -i + 1)) - timedelta(days=1)
        else:
            month_end = anchor

        # Count responses in this month
        resp_count = frappe.db.count(
            "Survey Response",
            filters={
                "response_time": ["between", [month_start, month_end]],
                "status": ["in", ["Completed", "Partial"]]
            }
        )

        # Count sent in this month
        sent_count = frappe.db.count(
            "Survey Response",
            filters={"sent_time": ["between", [month_start, month_end]]}
        )

        labels.append(month_start.strftime("%b %Y"))
        response_values.append(int(resp_count))
        sent_values.append(int(sent_count))

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Sent", "values": sent_values},
                {"name": "Responses", "values": response_values}
            ]
        },
        "type": "line",
        "colors": ["#7cd6fd", "#28a745"],
    }


@frappe.whitelist()
def get_campaign_performance_chart(filters: str, limit: int = 10) -> Dict[str, Any]:
    """Get top campaigns by response rate."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    campaigns = frappe.get_all(
        "Survey Campaign",
        filters={"creation": ["between", [df, dt]], "total_sent": [">", 0]},
        fields=["campaign_name", "total_sent", "total_responses", "response_rate"],
        order_by="response_rate desc",
        limit=limit,
    )

    labels = [c.get("campaign_name", "")[:20] for c in campaigns]
    rates = [float(c.get("response_rate") or 0) for c in campaigns]

    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": "Response Rate %", "values": rates}]
        },
        "type": "bar",
        "colors": ["#5EAD56"],
    }


@frappe.whitelist()
def get_response_rate_by_platform(filters: str) -> Dict[str, Any]:
    """Get response rates broken down by platform."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    _ensure_dates(filters)
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    # Get single-channel campaigns to attribute responses to platforms
    campaign_names = [c["name"] for c in frappe.get_all(
        "Survey Campaign",
        filters={"creation": ["between", [df, dt]]},
        fields=["name"],
        limit=5000
    )]

    if not campaign_names:
        return {"data": {"labels": [], "datasets": []}, "type": "bar"}

    # Get channels per campaign
    channels = frappe.get_all(
        "Survey Distribution Channel",
        filters={"parent": ["in", campaign_names], "is_active": 1},
        fields=["parent", "channel"],
        limit=50000,
    )

    channels_by_campaign = {}
    for ch in channels:
        channels_by_campaign.setdefault(ch["parent"], set()).add(ch["channel"])

    # Single-channel campaigns only
    single_channel = {c: list(chs)[0] for c, chs in channels_by_campaign.items() if len(chs) == 1}

    if not single_channel:
        return {"data": {"labels": [], "datasets": []}, "type": "bar"}

    # Compute per-platform sent/responded
    denom = {}
    numer = {}

    deliveries = frappe.get_all(
        "Survey Response",
        filters={"sent_time": ["between", [df, dt]], "campaign": ["in", list(single_channel.keys())]},
        fields=["campaign"],
        limit=50000,
    )
    for d in deliveries:
        plat = single_channel.get(d["campaign"])
        if plat:
            denom[plat] = denom.get(plat, 0) + 1

    responses = frappe.get_all(
        "Survey Response",
        filters={
            "response_time": ["between", [df, dt]],
            "status": ["in", ["Completed", "Partial"]],
            "campaign": ["in", list(single_channel.keys())]
        },
        fields=["campaign"],
        limit=50000,
    )
    for r in responses:
        plat = single_channel.get(r["campaign"])
        if plat:
            numer[plat] = numer.get(plat, 0) + 1

    # Compute rates
    plats = sorted(denom.keys())
    rates = [min(100.0, round((numer.get(p, 0) / denom[p] * 100.0), 2)) if denom.get(p) else 0 for p in plats]

    return {
        "data": {
            "labels": plats,
            "datasets": [{"name": "Response Rate %", "values": rates}]
        },
        "type": "bar",
        "colors": ["#5EAD56"],
    }

