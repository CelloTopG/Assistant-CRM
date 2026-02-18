"""
Survey Feedback Analysis - Native ERPNext Script Report

Comprehensive analysis of survey campaigns, responses, sentiment distribution,
channel performance, and response metrics using native ERPNext doctypes.

Data is sourced ONLY from Survey Response and Survey Campaign doctypes for accuracy.
Channel metrics come from Survey Distribution Channel (not Unified Inbox).

Includes Antoine AI integration for intelligent insights.
"""

import json
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe.utils import getdate, get_first_day, get_last_day, now_datetime, formatdate
from assistant_crm.report.report_utils import get_period_dates

# Supported survey distribution channels
SURVEY_CHANNELS = ["Email", "WhatsApp", "SMS", "Facebook", "Instagram", "Telegram", "Twitter", "LinkedIn"]

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
    get_period_dates(filters)

    columns = get_columns()
    data, summary_data = get_data(filters)
    chart = get_chart_data(summary_data)
    report_summary = get_report_summary(summary_data)

    return columns, data, None, chart, report_summary, False




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

    # Build conditions - use sent_time for date filtering (more reliable than response_time)
    conditions = ["DATE(sr.sent_time) BETWEEN %(df)s AND %(dt)s"]
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
        ORDER BY sr.sent_time DESC
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

    # Get campaign-level aggregates - use DATE() for consistent filtering
    campaigns = frappe.db.sql("""
        SELECT name, campaign_name, total_sent, total_responses, response_rate
        FROM `tabSurvey Campaign`
        WHERE DATE(creation) BETWEEN %(df)s AND %(dt)s
        ORDER BY total_sent DESC
        LIMIT 1000
    """, {"df": df, "dt": dt}, as_dict=True)

    summary["total_campaigns"] = len(campaigns)
    summary["total_surveys_sent"] = sum((c.get("total_sent") or 0) for c in campaigns)
    summary["response_rate"] = round((summary["total_responses"] / summary["total_surveys_sent"] * 100.0), 2) if summary["total_surveys_sent"] else 0

    # Get delivery metrics from Survey Response doctype (aligned with Campaign Analytics)
    # Count surveys by status to get delivery metrics
    status_counts = frappe.db.sql("""
        SELECT status, COUNT(*) as cnt
        FROM `tabSurvey Response` sr
        WHERE DATE(sr.sent_time) BETWEEN %(df)s AND %(dt)s
        GROUP BY status
    """, {"df": df, "dt": dt}, as_dict=True)

    status_map = {s["status"]: s["cnt"] for s in status_counts}
    total_sent = sum(status_map.values())
    bounced = status_map.get("Bounced", 0)
    delivered = total_sent - bounced
    completed = status_map.get("Completed", 0)
    partial = status_map.get("Partial", 0)
    closed = status_map.get("Closed", 0)

    summary["surveys_delivered"] = delivered
    summary["surveys_bounced"] = bounced
    summary["delivery_rate"] = round((delivered / total_sent * 100.0), 2) if total_sent else 0
    summary["completion_rate"] = round((completed / total_sent * 100.0), 2) if total_sent else 0
    summary["surveys_completed"] = completed
    summary["surveys_partial"] = partial
    summary["surveys_closed"] = closed

    # Get channel metrics from Survey Distribution Channel (NOT Unified Inbox)
    channel_data = _get_survey_channel_metrics(df, dt)
    summary.update(channel_data)

    return data, summary


def _get_survey_channel_metrics(df, dt) -> Dict[str, Any]:
    """Get channel metrics from Survey Distribution Channel - survey-specific data only.

    This function counts surveys sent per distribution channel, NOT general inbox messages.
    """
    # Get all campaigns in the date range using raw SQL for DATE() consistency
    campaign_rows = frappe.db.sql("""
        SELECT name FROM `tabSurvey Campaign`
        WHERE DATE(creation) BETWEEN %(df)s AND %(dt)s
        LIMIT 5000
    """, {"df": df, "dt": dt}, as_dict=True)
    campaign_names = [c["name"] for c in campaign_rows]

    if not campaign_names:
        return {
            "channel_breakdown": {},
            "total_channels_used": 0,
            "primary_channel": None,
        }

    # Get distribution channels for these campaigns
    channels = frappe.get_all(
        "Survey Distribution Channel",
        filters={"parent": ["in", campaign_names], "is_active": 1},
        fields=["parent", "channel"],
        limit=50000,
    )

    # Count surveys sent per channel
    channel_counts = {}
    for ch in channels:
        channel = ch.get("channel", "Unknown")
        if channel not in channel_counts:
            channel_counts[channel] = {"campaigns": 0, "surveys_sent": 0, "responses": 0}
        channel_counts[channel]["campaigns"] += 1

    # Get survey response counts per campaign to attribute to channels
    for campaign_name in campaign_names:
        campaign_channels = [ch["channel"] for ch in channels if ch["parent"] == campaign_name]

        # Get campaign stats
        campaign = frappe.db.get_value(
            "Survey Campaign", campaign_name,
            ["total_sent", "total_responses"], as_dict=True
        )

        if campaign and campaign_channels:
            # Distribute evenly across channels if multiple channels used
            per_channel_sent = (campaign.get("total_sent") or 0) / len(campaign_channels)
            per_channel_resp = (campaign.get("total_responses") or 0) / len(campaign_channels)

            for ch in campaign_channels:
                channel_counts[ch]["surveys_sent"] += per_channel_sent
                channel_counts[ch]["responses"] += per_channel_resp

    # Round the values
    for ch in channel_counts:
        channel_counts[ch]["surveys_sent"] = int(channel_counts[ch]["surveys_sent"])
        channel_counts[ch]["responses"] = int(channel_counts[ch]["responses"])

    # Find primary channel (most surveys sent)
    primary_channel = None
    max_sent = 0
    for ch, stats in channel_counts.items():
        if stats["surveys_sent"] > max_sent:
            max_sent = stats["surveys_sent"]
            primary_channel = ch

    return {
        "channel_breakdown": channel_counts,
        "total_channels_used": len(channel_counts),
        "primary_channel": primary_channel,
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
    """Build report summary cards - aligned with Campaign Analytics doctype structure."""
    primary_channel = summary.get("primary_channel") or "N/A"

    return [
        {"value": summary.get("total_campaigns", 0), "label": "Campaigns", "datatype": "Int"},
        {"value": summary.get("total_surveys_sent", 0), "label": "Surveys Sent", "datatype": "Int"},
        {"value": summary.get("surveys_delivered", 0), "label": "Delivered", "datatype": "Int", "indicator": "green"},
        {"value": f"{summary.get('delivery_rate', 0):.1f}%", "label": "Delivery Rate", "datatype": "Data"},
        {"value": summary.get("surveys_completed", 0), "label": "Completed", "datatype": "Int", "indicator": "green"},
        {"value": f"{summary.get('response_rate', 0):.1f}%", "label": "Response Rate", "datatype": "Data"},
        {"value": summary.get("avg_sentiment", 0), "label": "Avg Sentiment", "datatype": "Float"},
        {"value": f"{summary.get('avg_response_duration', 0):.1f}", "label": "Avg Resp (min)", "datatype": "Data"},
        {"value": primary_channel, "label": "Primary Channel", "datatype": "Data", "indicator": "blue"},
        {"value": summary.get("surveys_bounced", 0), "label": "Bounced", "datatype": "Int", "indicator": "red"},
    ]


@frappe.whitelist()
def get_ai_insights(filters: str, query: str) -> Dict[str, Any]:
    """Return Antoine-style insights for the Survey Feedback Analysis report."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    get_period_dates(filters)

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
            "surveys_delivered": summary.get("surveys_delivered", 0),
            "surveys_bounced": summary.get("surveys_bounced", 0),
            "delivery_rate": summary.get("delivery_rate", 0),
            "total_responses": summary.get("total_responses", 0),
            "surveys_completed": summary.get("surveys_completed", 0),
            "surveys_partial": summary.get("surveys_partial", 0),
            "response_rate": summary.get("response_rate", 0),
            "completion_rate": summary.get("completion_rate", 0),
            "avg_sentiment_score": summary.get("avg_sentiment", 0),
            "very_positive_count": summary.get("very_positive", 0),
            "positive_count": summary.get("positive", 0),
            "neutral_count": summary.get("neutral", 0),
            "negative_count": summary.get("negative", 0),
            "very_negative_count": summary.get("very_negative", 0),
            "avg_response_duration_minutes": summary.get("avg_response_duration", 0),
            "primary_channel": summary.get("primary_channel"),
            "channel_breakdown": summary.get("channel_breakdown", {}),
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
    get_period_dates(filters)
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
    """Get channel distribution chart data from Survey Distribution Channel."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    get_period_dates(filters)
    _, summary = get_data(filters)

    channel_breakdown = summary.get("channel_breakdown", {})
    channels = list(channel_breakdown.keys())
    surveys_sent = [channel_breakdown[ch]["surveys_sent"] for ch in channels]
    responses = [channel_breakdown[ch]["responses"] for ch in channels]

    return {
        "data": {
            "labels": channels,
            "datasets": [
                {"name": "Surveys Sent", "values": surveys_sent},
                {"name": "Responses", "values": responses}
            ]
        },
        "type": "bar",
        "barOptions": {"stacked": 0},
        "colors": ["#5e64ff", "#28a745"],
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
    get_period_dates(filters)
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    campaigns = frappe.db.sql("""
        SELECT campaign_name, total_sent, total_responses, response_rate
        FROM `tabSurvey Campaign`
        WHERE DATE(creation) BETWEEN %(df)s AND %(dt)s AND total_sent > 0
        ORDER BY response_rate DESC
        LIMIT %(limit)s
    """, {"df": df, "dt": dt, "limit": limit}, as_dict=True)

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
    """Get response rates broken down by platform/channel."""
    filters = frappe._dict(json.loads(filters) if isinstance(filters, str) else filters or {})
    get_period_dates(filters)
    df = getdate(filters.date_from)
    dt = getdate(filters.date_to)

    # Get single-channel campaigns to attribute responses to platforms
    campaign_rows = frappe.db.sql("""
        SELECT name FROM `tabSurvey Campaign`
        WHERE DATE(creation) BETWEEN %(df)s AND %(dt)s
        LIMIT 5000
    """, {"df": df, "dt": dt}, as_dict=True)
    campaign_names = [c["name"] for c in campaign_rows]

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

    # Single-channel campaigns only (for accurate attribution)
    single_channel = {c: list(chs)[0] for c, chs in channels_by_campaign.items() if len(chs) == 1}

    if not single_channel:
        return {"data": {"labels": [], "datasets": []}, "type": "bar"}

    # Compute per-channel sent/responded using SQL for DATE() consistency
    denom = {}
    numer = {}

    # Get surveys sent per campaign
    deliveries = frappe.db.sql("""
        SELECT campaign FROM `tabSurvey Response`
        WHERE DATE(sent_time) BETWEEN %(df)s AND %(dt)s
          AND campaign IN %(campaigns)s
        LIMIT 50000
    """, {"df": df, "dt": dt, "campaigns": list(single_channel.keys())}, as_dict=True)

    for d in deliveries:
        plat = single_channel.get(d["campaign"])
        if plat:
            denom[plat] = denom.get(plat, 0) + 1

    # Get responses (completed or partial)
    responses = frappe.db.sql("""
        SELECT campaign FROM `tabSurvey Response`
        WHERE DATE(sent_time) BETWEEN %(df)s AND %(dt)s
          AND status IN ('Completed', 'Partial')
          AND campaign IN %(campaigns)s
        LIMIT 50000
    """, {"df": df, "dt": dt, "campaigns": list(single_channel.keys())}, as_dict=True)

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

