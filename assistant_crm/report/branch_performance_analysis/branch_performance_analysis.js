/**
 * Branch Performance Analysis - Script Report Frontend
 *
 * Native ERPNext Script Report with filters, charts, and Antoine AI integration.
 * Uses Issue, Claim, and Unified Inbox Conversation doctypes as data sources.
 */

frappe.query_reports["Branch Performance Analysis"] = {
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
                    frappe.query_report.set_filter_value("date_from", frappe.datetime.month_start());
                    frappe.query_report.set_filter_value("date_to", frappe.datetime.get_today());
                } else if (period_type === "Quarterly") {
                    let today = frappe.datetime.get_today();
                    let month = new Date(today).getMonth();
                    let qStart = new Date(new Date(today).getFullYear(), Math.floor(month / 3) * 3, 1);
                    frappe.query_report.set_filter_value("date_from", frappe.datetime.obj_to_str(qStart));
                    frappe.query_report.set_filter_value("date_to", frappe.datetime.get_today());
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
            fieldname: "region",
            label: __("Region"),
            fieldtype: "Select",
            options: "\nAll\nLusaka\nCopperbelt\nNorthern\nEastern\nSouthern\nWestern\nCentral\nLuapula\nMuchinga\nNorth-Western",
            default: "All"
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch"
        },
        {
            fieldname: "channel",
            label: __("Channel"),
            fieldtype: "Select",
            options: "\nAll\nWhatsApp\nFacebook\nTelegram\nEmail\nPhone\nWalk-in",
            default: "All"
        },
        {
            fieldname: "priority",
            label: __("Priority"),
            fieldtype: "Link",
            options: "Issue Priority"
        }
    ],

    onload: function(report) {
        // Add Antoine AI button
        report.page.add_inner_button(__("Ask Antoine"), function() {
            show_antoine_dialog(report);
        }, __("AI Insights"));

        // Add additional chart buttons
        report.page.add_inner_button(__("SLA by Branch"), function() {
            show_sla_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Regional Comparison"), function() {
            show_regional_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("6-Month Trend"), function() {
            show_trend_chart(report);
        }, __("Charts"));
    },

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "sla_percent" && data) {
            let sla = parseFloat(data.sla_percent) || 0;
            if (sla >= 90) {
                value = `<span class="indicator-pill green">${value}</span>`;
            } else if (sla >= 75) {
                value = `<span class="indicator-pill orange">${value}</span>`;
            } else {
                value = `<span class="indicator-pill red">${value}</span>`;
            }
        }

        if (column.fieldname === "complaints_escalated" && data && data.complaints_escalated > 0) {
            value = `<span class="indicator-pill red">${value}</span>`;
        }

        return value;
    }
};

function show_antoine_dialog(report) {
    let d = new frappe.ui.Dialog({
        title: __("Ask Antoine - Branch Performance AI Assistant"),
        fields: [
            {
                fieldname: "query",
                label: __("Your Question"),
                fieldtype: "Small Text",
                reqd: 1,
                placeholder: __("e.g., Which branches have the lowest SLA compliance and why?")
            },
            {
                fieldname: "response_section",
                fieldtype: "Section Break",
                label: __("Antoine's Response")
            },
            {
                fieldname: "response",
                fieldtype: "HTML",
                options: '<div class="antoine-response" style="min-height:100px;padding:10px;background:#f5f7fa;border-radius:4px;"><em>Ask a question to get AI-powered insights about branch performance...</em></div>'
            }
        ],
        primary_action_label: __("Ask Antoine"),
        primary_action: function(values) {
            let $response = d.$wrapper.find(".antoine-response");
            $response.html('<div class="text-muted"><i class="fa fa-spinner fa-spin"></i> Antoine is analyzing branch data...</div>');

            frappe.call({
                method: "assistant_crm.assistant_crm.report.branch_performance_analysis.branch_performance_analysis.get_ai_insights",
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

function show_sla_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.branch_performance_analysis.branch_performance_analysis.get_sla_chart",
        args: {
            filters: JSON.stringify(report.get_filter_values())
        },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("SLA Compliance by Branch"), r.message);
            }
        }
    });
}

function show_regional_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.branch_performance_analysis.branch_performance_analysis.get_regional_chart",
        args: {
            filters: JSON.stringify(report.get_filter_values())
        },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Regional Comparison"), r.message);
            }
        }
    });
}

function show_trend_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.branch_performance_analysis.branch_performance_analysis.get_trend_chart",
        args: {
            filters: JSON.stringify(report.get_filter_values()),
            months: 6
        },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("6-Month Trend"), r.message);
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

