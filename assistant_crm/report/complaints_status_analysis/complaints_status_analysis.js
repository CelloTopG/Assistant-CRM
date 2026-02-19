/**
 * Complaints Status Analysis - Native ERPNext Script Report Frontend
 *
 * Comprehensive complaints analysis with filters, charts, and WorkCom AI integration.
 * Uses native Issue doctype and Unified Inbox Conversation as data sources.
 */

frappe.query_reports["Complaints Status Analysis"] = {
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
            fieldname: "category",
            label: __("Category"),
            fieldtype: "Select",
            options: "\nClaims\nCompliance\nGeneral"
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nOpen\nResolved\nClosed"
        },
        {
            fieldname: "platform",
            label: __("Platform"),
            fieldtype: "Select",
            options: "\nWhatsApp\nFacebook\nTelegram\nEmail\nWeb"
        }
    ],

    onload: function (report) {
        // Add WorkCom AI button
        report.page.add_inner_button(__("Ask WorkCom"), function () {
            show_WorkCom_dialog(report);
        }, __("AI Insights"));

        // Add chart buttons
        report.page.add_inner_button(__("By Category"), function () {
            show_category_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("By Status"), function () {
            show_status_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("By Platform"), function () {
            show_platform_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Platform x Category"), function () {
            show_stacked_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Trend"), function () {
            show_trend_chart(report);
        }, __("Charts"));
    },

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "final_category" && data) {
            let cat = (data.final_category || "").toLowerCase();
            let cls = "gray";
            if (cat === "claims") cls = "blue";
            else if (cat === "compliance") cls = "orange";
            else if (cat === "general") cls = "green";
            value = `<span class="indicator-pill ${cls}">${value}</span>`;
        }

        if (column.fieldname === "status" && data) {
            let status = (data.status || "").toLowerCase();
            let cls = "gray";
            if (status === "resolved" || status === "closed") cls = "green";
            else if (status === "open") cls = "orange";
            value = `<span class="indicator-pill ${cls}">${value}</span>`;
        }

        if (column.fieldname === "escalated" && data) {
            if (data.escalated) {
                value = `<span class="indicator-pill red">Yes</span>`;
            } else {
                value = `<span class="indicator-pill gray">No</span>`;
            }
        }

        return value;
    }
};

function show_WorkCom_dialog(report) {
    let d = new frappe.ui.Dialog({
        title: __("Ask WorkCom - Complaints Analytics Assistant"),
        fields: [
            {
                fieldname: "query",
                label: __("Your Question"),
                fieldtype: "Small Text",
                reqd: 1,
                placeholder: __("e.g., What are the key trends in complaints this period?")
            },
            {
                fieldname: "response_section",
                fieldtype: "Section Break",
                label: __("WorkCom's Response")
            },
            {
                fieldname: "response",
                fieldtype: "HTML",
                options: '<div class="WorkCom-response" style="min-height:120px;padding:12px;background:#f5f7fa;border-radius:4px;"><em>Ask a question to get AI-powered complaints insights...</em></div>'
            }
        ],
        primary_action_label: __("Ask WorkCom"),
        primary_action: function (values) {
            let $response = d.$wrapper.find(".WorkCom-response");
            $response.html('<div class="text-muted"><i class="fa fa-spinner fa-spin"></i> WorkCom is analyzing complaints data...</div>');

            frappe.call({
                method: "assistant_crm.assistant_crm.report.complaints_status_analysis.complaints_status_analysis.get_ai_insights",
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

function show_category_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.complaints_status_analysis.complaints_status_analysis.get_category_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("Complaints by Category"), r.message);
            }
        }
    });
}

function show_status_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.complaints_status_analysis.complaints_status_analysis.get_status_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("Complaints by Status"), r.message);
            }
        }
    });
}

function show_platform_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.complaints_status_analysis.complaints_status_analysis.get_platform_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("Complaints by Platform"), r.message);
            }
        }
    });
}

function show_stacked_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.complaints_status_analysis.complaints_status_analysis.get_stacked_platform_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("Platform × Category"), r.message);
            }
        }
    });
}

function show_trend_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.complaints_status_analysis.complaints_status_analysis.get_trend_chart",
        args: { filters: JSON.stringify(report.get_filter_values()), windows: 8 },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("Complaints Trend"), r.message);
            }
        }
    });
}

function show_chart_dialog(title, chart_data) {
    let d = new frappe.ui.Dialog({
        title: title,
        size: "large"
    });

    let chart_container = $('<div class="chart-container" style="height:400px; width:100%;"></div>');
    d.$body.append(chart_container);

    d.show();

    // Handle no data case
    if (chart_data.no_data) {
        chart_container.html('<div class="text-muted text-center" style="padding:100px;"><i class="fa fa-bar-chart fa-3x mb-3" style="opacity:0.3;"></i><br>No complaints data available for the selected period.</div>');
        return;
    }

    setTimeout(function () {
        let chart_options = {
            data: chart_data.data,
            type: chart_data.type || "bar",
            height: 350,
            colors: chart_data.colors || ["#5e64ff"]
        };

        if (chart_data.type === "bar" || chart_data.type === "line") {
            chart_options.barOptions = chart_data.barOptions || {};
            chart_options.lineOptions = chart_data.lineOptions || {};
        }

        if (chart_data.type === "pie" || chart_data.type === "percentage") {
            chart_options.maxSlices = chart_data.maxSlices || 10;
        }

        try {
            new frappe.Chart(chart_container[0], chart_options);
        } catch (e) {
            console.error("Chart rendering error:", e);
            chart_container.html('<div class="text-muted text-center" style="padding:100px;">Unable to render chart: ' + e.message + '</div>');
        }
    }, 100);
}


