/**
 * Employer Status Analysis - Script Report Frontend
 *
 * Production-ready ERPNext Script Report with filters, charts, and Antoine AI integration.
 * Uses Employer doctype as the data source.
 */

frappe.query_reports["Employer Status Analysis"] = {
    filters: [
        {
            fieldname: "period_type",
            label: __("Period Type"),
            fieldtype: "Select",
            options: "Monthly\nCustom",
            default: "Monthly",
            reqd: 1,
            on_change: function() {
                let period_type = frappe.query_report.get_filter_value("period_type");
                if (period_type === "Monthly") {
                    frappe.query_report.set_filter_value("date_from", frappe.datetime.month_start());
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
            fieldname: "filter_by_date",
            label: __("Filter by Registration Date"),
            fieldtype: "Check",
            default: 0
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch"
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nActive\nInactive\nSuspended\nPending Verification\nBlacklisted"
        }
    ],

    onload: function(report) {
        // Add Antoine AI button
        report.page.add_inner_button(__("Ask Antoine"), function() {
            show_antoine_dialog(report);
        }, __("AI Insights"));

        // Add additional chart buttons
        report.page.add_inner_button(__("Status Chart"), function() {
            show_status_chart();
        }, __("Charts"));

        report.page.add_inner_button(__("Branch Chart"), function() {
            show_branch_chart();
        }, __("Charts"));

        report.page.add_inner_button(__("Trend Chart"), function() {
            show_trend_chart();
        }, __("Charts"));
    },

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "status" && data) {
            let status = data.status || "";
            if (status === "Active") {
                value = `<span class="indicator-pill green">${value}</span>`;
            } else if (status === "Inactive") {
                value = `<span class="indicator-pill grey">${value}</span>`;
            } else if (status === "Suspended") {
                value = `<span class="indicator-pill orange">${value}</span>`;
            } else if (status === "Pending Verification") {
                value = `<span class="indicator-pill blue">${value}</span>`;
            } else if (status === "Blacklisted") {
                value = `<span class="indicator-pill red">${value}</span>`;
            }
        }

        return value;
    }
};

function show_antoine_dialog(report) {
    let d = new frappe.ui.Dialog({
        title: __("Ask Antoine - AI Analytics Assistant"),
        fields: [
            {
                fieldname: "query",
                label: __("Your Question"),
                fieldtype: "Small Text",
                reqd: 1,
                placeholder: __("e.g., What trends do you see in employer registrations?")
            },
            {
                fieldname: "response_section",
                fieldtype: "Section Break",
                label: __("Antoine's Response")
            },
            {
                fieldname: "response",
                fieldtype: "HTML",
                options: '<div class="antoine-response" style="min-height:100px;padding:10px;background:#f5f7fa;border-radius:4px;"><em>Ask a question to get AI-powered insights...</em></div>'
            }
        ],
        primary_action_label: __("Ask Antoine"),
        primary_action: function(values) {
            let $response = d.$wrapper.find(".antoine-response");
            $response.html('<div class="text-muted"><i class="fa fa-spinner fa-spin"></i> Antoine is thinking...</div>');

            frappe.call({
                method: "assistant_crm.assistant_crm.report.employer_status_analysis.employer_status_analysis.get_ai_insights",
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

function show_status_chart() {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.employer_status_analysis.employer_status_analysis.get_status_chart",
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Employers by Status"), r.message);
            }
        }
    });
}

function show_branch_chart() {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.employer_status_analysis.employer_status_analysis.get_branch_chart",
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Top 10 Branches by Employer Count"), r.message);
            }
        }
    });
}

function show_trend_chart() {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.employer_status_analysis.employer_status_analysis.get_trend_chart",
        args: { months: 6 },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Employer Registration Trend (Last 6 Months)"), r.message);
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
        colors: chart_data.colors || ["#5e64ff"]
    });
}

