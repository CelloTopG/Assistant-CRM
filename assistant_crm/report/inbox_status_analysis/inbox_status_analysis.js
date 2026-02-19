/**
 * Inbox Status Analysis - Script Report Frontend
 *
 * Native ERPNext Script Report with filters, charts, and WorkCom AI integration.
 * Uses Unified Inbox Conversation, Unified Inbox Message, and Issue doctypes.
 */

frappe.query_reports["Inbox Status Analysis"] = {
    filters: [
        {
            fieldname: "period_type",
            label: __("Period Type"),
            fieldtype: "Select",
            options: assistant_crm.report_utils.period_type_options,
            default: "Weekly",
            reqd: 1,
            on_change: function () {
                assistant_crm.report_utils.handle_period_change();
            }
        },
        {
            fieldname: "date_from",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_days(frappe.datetime.get_today(), -6),
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
            fieldname: "platform",
            label: __("Platform"),
            fieldtype: "Select",
            options: "\nWhatsApp\nFacebook\nInstagram\nTelegram\nTwitter\nTawk.to\nWebsite Chat\nEmail\nPhone\nLinkedIn\nUSSD\nYouTube"
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nNew\nIn Progress\nPending Customer\nEscalated\nResolved\nClosed"
        },
        {
            fieldname: "assigned_agent",
            label: __("Assigned Agent"),
            fieldtype: "Link",
            options: "User"
        },
        {
            fieldname: "ai_mode",
            label: __("AI Mode"),
            fieldtype: "Select",
            options: "\nAuto\nOn\nOff"
        }
    ],

    onload: function (report) {
        // Add WorkCom AI button
        report.page.add_inner_button(__("Ask WorkCom"), function () {
            show_WorkCom_dialog(report);
        }, __("AI Insights"));

        // Add chart buttons
        report.page.add_inner_button(__("Platform Distribution"), function () {
            show_platform_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("AI vs Human"), function () {
            show_ai_vs_human_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Status Distribution"), function () {
            show_status_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("8-Week Trend"), function () {
            show_trend_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Response Times"), function () {
            show_response_time_chart(report);
        }, __("Charts"));
    },

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "escalated" && data && parseInt(data.escalated) > 0) {
            value = `<span class="indicator-pill red">${value}</span>`;
        }

        if (column.fieldname === "ai_handled" && data && parseInt(data.ai_handled) > 0) {
            value = `<span class="indicator-pill blue">${value}</span>`;
        }

        if (column.fieldname === "avg_frt_min" && data) {
            let frt = parseFloat(data.avg_frt_min) || 0;
            if (frt <= 5) {
                value = `<span class="indicator-pill green">${value}</span>`;
            } else if (frt <= 15) {
                value = `<span class="indicator-pill orange">${value}</span>`;
            } else {
                value = `<span class="indicator-pill red">${value}</span>`;
            }
        }

        return value;
    }
};

function show_WorkCom_dialog(report) {
    let d = new frappe.ui.Dialog({
        title: __("Ask WorkCom - Inbox Analytics AI Assistant"),
        fields: [
            {
                fieldname: "query",
                label: __("Your Question"),
                fieldtype: "Small Text",
                reqd: 1,
                placeholder: __("e.g., What are the busiest channels and how is AI performing?")
            },
            {
                fieldname: "response_section",
                fieldtype: "Section Break",
                label: __("WorkCom's Response")
            },
            {
                fieldname: "response",
                fieldtype: "HTML",
                options: '<div class="WorkCom-response" style="min-height:100px;padding:10px;background:#f5f7fa;border-radius:4px;"><em>Ask a question to get AI-powered insights about inbox performance...</em></div>'
            }
        ],
        primary_action_label: __("Ask WorkCom"),
        primary_action: function (values) {
            let $response = d.$wrapper.find(".WorkCom-response");
            $response.html('<div class="text-muted"><i class="fa fa-spinner fa-spin"></i> WorkCom is analyzing inbox data...</div>');

            frappe.call({
                method: "assistant_crm.assistant_crm.report.inbox_status_analysis.inbox_status_analysis.get_ai_insights",
                args: {
                    filters: JSON.stringify(report.get_filter_values()),
                    query: values.query
                },
                callback: function (r) {
                    let answer = (r && r.message && r.message.insights) || "No response received.";
                    $response.html(`<div style="white-space:pre-wrap;">${answer}</div>`);
                },
                error: function () {
                    $response.html('<div class="text-danger">Error getting AI insights. Please try again.</div>');
                }
            });
        }
    });
    d.show();
}

function show_platform_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.inbox_status_analysis.inbox_status_analysis.get_platform_distribution_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("Platform Distribution"), r.message);
            }
        }
    });
}

function show_ai_vs_human_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.inbox_status_analysis.inbox_status_analysis.get_ai_vs_human_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("AI vs Human Handling"), r.message);
            }
        }
    });
}

function show_status_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.inbox_status_analysis.inbox_status_analysis.get_status_distribution_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("Status Distribution"), r.message);
            }
        }
    });
}

function show_trend_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.inbox_status_analysis.inbox_status_analysis.get_trend_chart",
        args: { filters: JSON.stringify(report.get_filter_values()), weeks: 8 },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("8-Week Trend"), r.message);
            }
        }
    });
}

function show_response_time_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.inbox_status_analysis.inbox_status_analysis.get_response_time_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("Response Times by Platform"), r.message);
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


