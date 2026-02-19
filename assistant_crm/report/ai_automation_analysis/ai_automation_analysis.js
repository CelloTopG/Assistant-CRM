/**
 * AI Automation Analysis - Native ERPNext Script Report Frontend
 *
 * Comprehensive AI automation analysis with filters, charts, and WorkCom AI integration.
 * Uses native Scheduled Job Log as the primary data source with aggregated metrics.
 */

frappe.query_reports["AI Automation Analysis"] = {
    filters: [
        {
            fieldname: "period_type",
            label: __("Period Type"),
            fieldtype: "Select",
            options: assistant_crm.report_utils.period_type_options,
            default: "Monthly",
            reqd: 1,
            on_change: function () {
                assistant_crm.report_utils.handle_period_change();
            }
        },
        {
            fieldname: "date_from",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_days(frappe.datetime.month_start(), -1),
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
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nScheduled\nComplete\nFailed"
        },
        {
            fieldname: "job_type",
            label: __("Job Type"),
            fieldtype: "Link",
            options: "Scheduled Job Type"
        }
    ],

    onload: function (report) {
        // Add WorkCom AI button
        report.page.add_inner_button(__("Ask WorkCom"), function () {
            show_WorkCom_dialog(report);
        }, __("AI Insights"));

        // Add chart buttons
        report.page.add_inner_button(__("Automation Status"), function () {
            show_automation_status_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("After-Hours Tickets"), function () {
            show_after_hours_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Document Validation"), function () {
            show_document_validation_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Data Quality Issues"), function () {
            show_data_quality_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("AI Failures"), function () {
            show_ai_failures_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("System Health"), function () {
            show_system_health_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Automation Trend"), function () {
            show_trend_chart(report);
        }, __("Charts"));
    },

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "execution_status" && data) {
            let status = (data.execution_status || "").toLowerCase();
            let cls = "gray";
            if (status === "success") cls = "green";
            else if (status === "failed" || status === "error") cls = "red";
            value = `<span class="indicator-pill ${cls}">${value}</span>`;
        }

        if (column.fieldname === "is_after_hours" && data) {
            if (data.is_after_hours) {
                value = `<span class="indicator-pill orange">Yes</span>`;
            } else {
                value = `<span class="indicator-pill gray">No</span>`;
            }
        }

        return value;
    }
};

function show_WorkCom_dialog(report) {
    let d = new frappe.ui.Dialog({
        title: __("Ask WorkCom - AI Automation Analytics Assistant"),
        fields: [
            {
                fieldname: "query",
                label: __("Your Question"),
                fieldtype: "Small Text",
                reqd: 1,
                placeholder: __("e.g., What are the key insights from AI automation this period?")
            },
            {
                fieldname: "response_section",
                fieldtype: "Section Break",
                label: __("WorkCom's Response")
            },
            {
                fieldname: "response",
                fieldtype: "HTML",
                options: '<div class="WorkCom-response" style="min-height:120px;padding:12px;background:#f5f7fa;border-radius:4px;"><em>Ask a question to get AI-powered automation insights...</em></div>'
            }
        ],
        primary_action_label: __("Ask WorkCom"),
        primary_action: function (values) {
            let $response = d.$wrapper.find(".WorkCom-response");
            $response.html('<div class="text-muted"><i class="fa fa-spinner fa-spin"></i> WorkCom is analyzing automation data...</div>');

            frappe.call({
                method: "assistant_crm.assistant_crm.report.ai_automation_analysis.ai_automation_analysis.get_ai_insights",
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

function show_automation_status_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.ai_automation_analysis.ai_automation_analysis.get_automation_status_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("Automation Status"), r.message);
            }
        }
    });
}

function show_after_hours_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.ai_automation_analysis.ai_automation_analysis.get_after_hours_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("After-Hours Tickets by Platform"), r.message);
            }
        }
    });
}

function show_document_validation_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.ai_automation_analysis.ai_automation_analysis.get_document_validation_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("Document Validation Status"), r.message);
            }
        }
    });
}

function show_data_quality_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.ai_automation_analysis.ai_automation_analysis.get_data_quality_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("Data Quality Issues"), r.message);
            }
        }
    });
}

function show_ai_failures_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.ai_automation_analysis.ai_automation_analysis.get_ai_failures_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("AI Failures by Reason"), r.message);
            }
        }
    });
}

function show_system_health_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.ai_automation_analysis.ai_automation_analysis.get_system_health_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            console.log("System health chart response:", r);
            if (r && r.message) {
                show_chart_dialog(__("System Health"), r.message);
            } else {
                frappe.msgprint(__("No data available for system health chart"));
            }
        },
        error: function (err) {
            console.error("System health chart error:", err);
            frappe.msgprint(__("Error loading system health chart"));
        }
    });
}

function show_trend_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.ai_automation_analysis.ai_automation_analysis.get_automation_trend_chart",
        args: { filters: JSON.stringify(report.get_filter_values()), months: 6 },
        callback: function (r) {
            if (r && r.message) {
                show_chart_dialog(__("Automation Trend (Last 6 Months)"), r.message);
            }
        }
    });
}

function show_chart_dialog(title, chart_data) {
    let d = new frappe.ui.Dialog({
        title: title,
        size: "large"
    });

    // Create chart container
    let chart_container = $('<div class="chart-container" style="height:400px; width:100%;"></div>');
    d.$body.append(chart_container);

    // Show dialog first
    d.show();

    // Use setTimeout to ensure DOM is ready before rendering chart
    setTimeout(function () {
        // Build chart options based on chart type
        let chart_options = {
            data: chart_data.data,
            type: chart_data.type || "bar",
            height: 350,
            colors: chart_data.colors || ["#5e64ff"]
        };

        // Add type-specific options
        if (chart_data.type === "bar" || chart_data.type === "line" || chart_data.type === "axis-mixed") {
            chart_options.barOptions = chart_data.barOptions || {};
            chart_options.lineOptions = chart_data.lineOptions || {};
        }

        // For pie/percentage charts, ensure proper data format
        if (chart_data.type === "pie" || chart_data.type === "percentage") {
            chart_options.maxSlices = chart_data.maxSlices || 10;
        }

        try {
            console.log("Rendering chart with options:", chart_options);
            new frappe.Chart(chart_container[0], chart_options);
        } catch (e) {
            console.error("Chart rendering error:", e);
            chart_container.html('<div class="text-muted text-center" style="padding: 100px;">Unable to render chart: ' + e.message + '</div>');
        }
    }, 100);
}


