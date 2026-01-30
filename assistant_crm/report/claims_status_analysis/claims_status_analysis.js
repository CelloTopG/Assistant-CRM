/**
 * Claims Status Analysis - Native ERPNext Script Report Frontend
 *
 * Comprehensive claims analysis with filters, charts, and Antoine AI integration.
 * Uses native Claim doctype as the primary data source with aggregated metrics.
 */

frappe.query_reports["Claims Status Analysis"] = {
    filters: [
        {
            fieldname: "period_type",
            label: __("Period Type"),
            fieldtype: "Select",
            options: "Weekly\nMonthly\nCustom",
            default: "Weekly",
            reqd: 1,
            on_change: function() {
                let period_type = frappe.query_report.get_filter_value("period_type");
                if (period_type === "Monthly") {
                    let now = frappe.datetime.get_today();
                    let first_this_month = frappe.datetime.month_start(now);
                    let last_prev = frappe.datetime.add_days(first_this_month, -1);
                    let first_prev = frappe.datetime.month_start(last_prev);
                    frappe.query_report.set_filter_value("date_from", first_prev);
                    frappe.query_report.set_filter_value("date_to", last_prev);
                } else if (period_type === "Weekly") {
                    let now = frappe.datetime.get_today();
                    frappe.query_report.set_filter_value("date_from", frappe.datetime.add_days(now, -6));
                    frappe.query_report.set_filter_value("date_to", now);
                }
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
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nSubmitted\nUnder Review\nPending Documentation\nMedical Review\nValidated\nApproved\nRejected\nClosed\nAppealed\nSettled\nReopened\nEscalated"
        },
        {
            fieldname: "claim_type",
            label: __("Claim Type"),
            fieldtype: "Select",
            options: "\nInjury\nIllness\nMedical\nDisability\nDeath\nRehabilitation\nReimbursement"
        },
        {
            fieldname: "employer",
            label: __("Employer"),
            fieldtype: "Link",
            options: "Employer"
        }
    ],

    onload: function(report) {
        // Add Antoine AI button
        report.page.add_inner_button(__("Ask Antoine"), function() {
            show_antoine_dialog(report);
        }, __("AI Insights"));

        // Add chart buttons
        report.page.add_inner_button(__("By Status"), function() {
            show_status_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("By Type"), function() {
            show_type_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Outcome"), function() {
            show_outcome_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Amount by Type"), function() {
            show_amount_by_type_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("By Employer"), function() {
            show_employer_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Trend"), function() {
            show_trend_chart(report);
        }, __("Charts"));
    },

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "status" && data) {
            let status = (data.status || "").toLowerCase();
            let cls = "gray";
            if (status === "approved" || status === "settled") cls = "green";
            else if (status === "rejected") cls = "red";
            else if (status === "escalated") cls = "orange";
            else if (status === "validated") cls = "blue";
            else if (["submitted", "under review", "pending documentation", "medical review"].includes(status)) cls = "yellow";
            value = `<span class="indicator-pill ${cls}">${value}</span>`;
        }

        if (column.fieldname === "is_escalated" && data) {
            if (data.is_escalated) {
                value = `<span class="indicator-pill red">Yes</span>`;
            } else {
                value = `<span class="indicator-pill gray">No</span>`;
            }
        }

        return value;
    }
};

function show_antoine_dialog(report) {
    let d = new frappe.ui.Dialog({
        title: __("Ask Antoine - Claims Analytics Assistant"),
        fields: [
            {
                fieldname: "query",
                label: __("Your Question"),
                fieldtype: "Small Text",
                reqd: 1,
                placeholder: __("e.g., What are the key trends in claims processing this period?")
            },
            {
                fieldname: "response_section",
                fieldtype: "Section Break",
                label: __("Antoine's Response")
            },
            {
                fieldname: "response",
                fieldtype: "HTML",
                options: '<div class="antoine-response" style="min-height:120px;padding:12px;background:#f5f7fa;border-radius:4px;"><em>Ask a question to get AI-powered claims insights...</em></div>'
            }
        ],
        primary_action_label: __("Ask Antoine"),
        primary_action: function(values) {
            let $response = d.$wrapper.find(".antoine-response");
            $response.html('<div class="text-muted"><i class="fa fa-spinner fa-spin"></i> Antoine is analyzing claims data...</div>');

            frappe.call({
                method: "assistant_crm.assistant_crm.report.claims_status_analysis.claims_status_analysis.get_ai_insights",
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

function show_status_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.claims_status_analysis.claims_status_analysis.get_status_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Claims by Status"), r.message);
            }
        }
    });
}

function show_type_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.claims_status_analysis.claims_status_analysis.get_type_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Claims by Type"), r.message);
            }
        }
    });
}

function show_outcome_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.claims_status_analysis.claims_status_analysis.get_outcome_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Claims Outcome Distribution"), r.message);
            }
        }
    });
}

function show_amount_by_type_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.claims_status_analysis.claims_status_analysis.get_amount_by_type_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Claim Amounts by Type"), r.message);
            }
        }
    });
}

function show_employer_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.claims_status_analysis.claims_status_analysis.get_employer_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Top Employers by Claims"), r.message);
            }
        }
    });
}

function show_trend_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.claims_status_analysis.claims_status_analysis.get_trend_chart",
        args: { filters: JSON.stringify(report.get_filter_values()), windows: 8 },
        callback: function(r) {
            if (r && r.message) {
                show_chart_dialog(__("Claims Trend"), r.message);
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
        chart_container.html('<div class="text-muted text-center" style="padding:100px;"><i class="fa fa-bar-chart fa-3x mb-3" style="opacity:0.3;"></i><br>No claims data available for the selected period.</div>');
        return;
    }

    setTimeout(function() {
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

