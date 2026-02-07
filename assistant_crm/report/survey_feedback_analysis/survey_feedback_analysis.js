/**
 * Survey Feedback Analysis - Native ERPNext Script Report Frontend
 *
 * Comprehensive survey analysis with filters, charts, and Antoine AI integration.
 * Uses Survey Response doctype as the primary data source.
 */

frappe.query_reports["Survey Feedback Analysis"] = {
    filters: [
        {
            fieldname: "period_type",
            label: __("Period Type"),
            fieldtype: "Select",
            options: "Monthly\nQuarterly\nCustom",
            default: "Monthly",
            reqd: 1,
            on_change: function() {
                let period_type = frappe.query_report.get_filter_value("period_type");
                if (period_type === "Monthly") {
                    // Current month (to show recent data)
                    let now = frappe.datetime.get_today();
                    let first_this_month = frappe.datetime.month_start(now);
                    frappe.query_report.set_filter_value("date_from", first_this_month);
                    frappe.query_report.set_filter_value("date_to", now);
                } else if (period_type === "Quarterly") {
                    // Current quarter
                    let now = frappe.datetime.get_today();
                    let m = parseInt(now.split("-")[1], 10);
                    let y = parseInt(now.split("-")[0], 10);
                    let q = Math.floor((m - 1) / 3);
                    let start_month = q * 3 + 1;
                    let start = `${y}-${('0' + start_month).slice(-2)}-01`;
                    frappe.query_report.set_filter_value("date_from", start);
                    frappe.query_report.set_filter_value("date_to", now);
                }
            }
        },
        {
            fieldname: "date_from",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
            reqd: 1
        },
        {
            fieldname: "date_to",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1
        },
        {
            fieldname: "campaign",
            label: __("Campaign"),
            fieldtype: "Link",
            options: "Survey Campaign"
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nSent\nCompleted\nPartial\nBounced\nClosed"
        }
    ],

    onload: function(report) {
        // Add Antoine AI button
        report.page.add_inner_button(__("Ask Antoine"), function() {
            show_antoine_dialog(report);
        }, __("AI Insights"));

        // Add chart buttons
        report.page.add_inner_button(__("Sentiment Distribution"), function() {
            show_sentiment_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Channel Distribution"), function() {
            show_channel_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Survey Trend"), function() {
            show_trend_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Top Campaigns"), function() {
            show_campaign_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Platform Response Rates"), function() {
            show_platform_rr_chart(report);
        }, __("Charts"));
    },

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "sentiment_label" && data) {
            let label = data.sentiment_label || "";
            let cls = "gray";
            if (label === "Very Positive") cls = "green";
            else if (label === "Positive") cls = "blue";
            else if (label === "Neutral") cls = "yellow";
            else if (label === "Negative") cls = "orange";
            else if (label === "Very Negative") cls = "red";
            value = `<span class="indicator-pill ${cls}">${value}</span>`;
        }

        if (column.fieldname === "status" && data) {
            let status = data.status || "";
            let cls = "gray";
            if (status === "Completed") cls = "green";
            else if (status === "Partial") cls = "blue";
            else if (status === "Bounced") cls = "red";
            value = `<span class="indicator-pill ${cls}">${value}</span>`;
        }

        return value;
    }
};

function show_antoine_dialog(report) {
    let d = new frappe.ui.Dialog({
        title: __("Ask Antoine - AI Survey Analytics Assistant"),
        fields: [
            {
                fieldname: "query",
                label: __("Your Question"),
                fieldtype: "Small Text",
                reqd: 1,
                placeholder: __("e.g., What are the key insights from survey feedback this period?")
            },
            {
                fieldname: "response_section",
                fieldtype: "Section Break",
                label: __("Antoine's Response")
            },
            {
                fieldname: "response",
                fieldtype: "HTML",
                options: '<div class="antoine-response" style="min-height:120px;padding:12px;background:#f5f7fa;border-radius:4px;"><em>Ask a question to get AI-powered survey insights...</em></div>'
            }
        ],
        primary_action_label: __("Ask Antoine"),
        primary_action: function(values) {
            let $response = d.$wrapper.find(".antoine-response");
            $response.html('<div class="text-muted"><i class="fa fa-spinner fa-spin"></i> Antoine is analyzing survey data...</div>');

            frappe.call({
                method: "assistant_crm.assistant_crm.report.survey_feedback_analysis.survey_feedback_analysis.get_ai_insights",
                args: {
                    filters: JSON.stringify(report.get_filter_values()),
                    query: values.query
                },
                callback: function(r) {
                    let answer = (r && r.message && r.message.insights) || "No response received.";
                    $response.html(`<div style="white-space:pre-wrap;">${answer}</div>`);
                },
                error: function() {
                    $response.html('<div class="text-danger">Error getting AI insights. Please try again.</div>');
                }
            });
        }
    });
    d.show();
}

function show_sentiment_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.survey_feedback_analysis.survey_feedback_analysis.get_sentiment_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Sentiment Distribution"), r.message);
            }
        }
    });
}

function show_channel_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.survey_feedback_analysis.survey_feedback_analysis.get_channel_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Survey Channel Distribution"), r.message);
            }
        }
    });
}

function show_trend_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.survey_feedback_analysis.survey_feedback_analysis.get_survey_trend_chart",
        args: { filters: JSON.stringify(report.get_filter_values()), months: 6 },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Survey Trend (Last 6 Months)"), r.message);
            }
        }
    });
}

function show_campaign_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.survey_feedback_analysis.survey_feedback_analysis.get_campaign_performance_chart",
        args: { filters: JSON.stringify(report.get_filter_values()), limit: 10 },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Top Campaigns by Response Rate"), r.message);
            }
        }
    });
}

function show_platform_rr_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.survey_feedback_analysis.survey_feedback_analysis.get_response_rate_by_platform",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Response Rates by Platform"), r.message);
            }
        }
    });
}

function show_chart_dialog(title, chart_data) {
    let d = new frappe.ui.Dialog({
        title: title,
        size: "large"
    });

    d.show();

    // Render chart in dialog body
    let chart_container = $('<div class="chart-container" style="height:400px;"></div>');
    d.$body.append(chart_container);

    new frappe.Chart(chart_container[0], {
        data: chart_data.data,
        type: chart_data.type || "bar",
        height: 350,
        colors: chart_data.colors || ["#5e64ff"],
        barOptions: chart_data.barOptions || {}
    });
}
