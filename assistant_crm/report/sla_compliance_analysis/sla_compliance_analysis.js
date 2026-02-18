/**
 * SLA Compliance Analysis - Native ERPNext Script Report Frontend
 *
 * Comprehensive SLA compliance analysis with filters, charts, and Antoine AI integration.
 * Uses Unified Inbox Conversation as the primary data source.
 */

frappe.query_reports["SLA Compliance Analysis"] = {
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
            fieldname: "channel",
            label: __("Channel"),
            fieldtype: "Select",
            options: "\nAll\nWhatsApp\nEmail\nFacebook\nTwitter\nLinkedIn\nInstagram\nWeb"
        },
        {
            fieldname: "priority",
            label: __("Priority"),
            fieldtype: "Select",
            options: "\nAll\nLow\nMedium\nHigh\nUrgent"
        },
        {
            fieldname: "branch_filter",
            label: __("Branch"),
            fieldtype: "Data",
            placeholder: __("Filter by branch name...")
        },
        {
            fieldname: "role_filter",
            label: __("Role"),
            fieldtype: "Data",
            placeholder: __("Filter by role...")
        }
    ],

    onload: function (report) {
        // Add Antoine AI button
        report.page.add_inner_button(__("Ask Antoine"), function () {
            show_antoine_dialog(report);
        }, __("AI Insights"));

        // Add chart buttons
        report.page.add_inner_button(__("Overview"), function () {
            show_overview_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Branch Breakdown"), function () {
            show_branch_breakdown_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Role Breakdown"), function () {
            show_role_breakdown_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Compliance Trend"), function () {
            show_trend_chart(report);
        }, __("Charts"));
    },

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "overall_status" && data) {
            let status = (data.overall_status || "").toLowerCase();
            let cls = "gray";
            if (status === "within") cls = "green";
            else if (status === "breached") cls = "red";
            value = `<span class="indicator-pill ${cls}">${value}</span>`;
        }

        if (column.fieldname === "frt_status" && data) {
            let status = (data.frt_status || "").toLowerCase();
            let cls = "gray";
            if (status === "within") cls = "green";
            else if (status === "breached") cls = "red";
            value = `<span class="indicator-pill ${cls}">${value}</span>`;
        }

        if (column.fieldname === "rt_status" && data) {
            let status = (data.rt_status || "").toLowerCase();
            let cls = "gray";
            if (status === "within") cls = "green";
            else if (status === "breached") cls = "red";
            value = `<span class="indicator-pill ${cls}">${value}</span>`;
        }

        if (column.fieldname === "escalated" && data) {
            if (data.escalated === "Yes") {
                value = `<span class="indicator-pill orange">Yes</span>`;
            } else {
                value = `<span class="indicator-pill gray">No</span>`;
            }
        }

        if (column.fieldname === "frt_label" && data) {
            let label = (data.frt_label || "").toLowerCase();
            if (label.includes("ai")) {
                value = `<span class="indicator-pill blue">${data.frt_label}</span>`;
            }
        }

        return value;
    }
};


// =====================
// Antoine AI Dialog
// =====================

function show_antoine_dialog(report) {
    let d = new frappe.ui.Dialog({
        title: __("Ask Antoine - SLA Compliance Insights"),
        size: "large",
        fields: [
            {
                fieldname: "query",
                label: __("Your Question"),
                fieldtype: "Small Text",
                placeholder: __("Ask Antoine about SLA compliance, trends, or recommendations..."),
                reqd: 1
            },
            {
                fieldname: "response_html",
                fieldtype: "HTML"
            }
        ],
        primary_action_label: __("Ask"),
        primary_action: function () {
            let query = d.get_value("query");
            if (!query) {
                frappe.msgprint(__("Please enter a question."));
                return;
            }

            d.get_field("response_html").$wrapper.html(`
                <div class="text-center text-muted" style="padding: 40px;">
                    <i class="fa fa-spinner fa-spin fa-2x"></i>
                    <p style="margin-top: 10px;">${__("Antoine is thinking...")}</p>
                </div>
            `);

            frappe.call({
                method: "assistant_crm.assistant_crm.report.sla_compliance_analysis.sla_compliance_analysis.get_ai_insights",
                args: {
                    filters: JSON.stringify(report.get_filter_values()),
                    query: query
                },
                callback: function (r) {
                    if (r.message && r.message.insights) {
                        d.get_field("response_html").$wrapper.html(`
                            <div class="antoine-response" style="padding: 15px; background: var(--bg-light-gray); border-radius: 8px; max-height: 400px; overflow-y: auto;">
                                <div style="margin-bottom: 10px;">
                                    <strong><i class="fa fa-robot"></i> ${__("Antoine's Analysis:")}</strong>
                                </div>
                                <div style="white-space: pre-wrap;">${r.message.insights}</div>
                            </div>
                        `);
                    } else {
                        d.get_field("response_html").$wrapper.html(`
                            <div class="text-muted text-center" style="padding: 20px;">
                                ${__("Could not get AI insights. Please try again.")}
                            </div>
                        `);
                    }
                },
                error: function () {
                    d.get_field("response_html").$wrapper.html(`
                        <div class="text-danger text-center" style="padding: 20px;">
                            ${__("An error occurred. Please try again.")}
                        </div>
                    `);
                }
            });
        }
    });

    // Add suggested questions
    d.get_field("response_html").$wrapper.html(`
        <div style="padding: 15px; background: var(--bg-light-gray); border-radius: 8px;">
            <p><strong>${__("Suggested Questions:")}</strong></p>
            <ul style="margin: 0; padding-left: 20px;">
                <li>${__("What are the main SLA compliance issues this period?")}</li>
                <li>${__("Which branches have the best and worst performance?")}</li>
                <li>${__("How can we improve first response time?")}</li>
                <li>${__("What trends do you see in escalation behavior?")}</li>
                <li>${__("What recommendations do you have for improving compliance?")}</li>
            </ul>
        </div>
    `);

    d.show();
}


// =====================
// Chart Functions
// =====================

function show_overview_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.sla_compliance_analysis.sla_compliance_analysis.get_overview_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r.message) {
                show_chart_dialog(__("SLA Compliance Overview"), r.message);
            }
        }
    });
}

function show_branch_breakdown_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.sla_compliance_analysis.sla_compliance_analysis.get_branch_breakdown_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r.message) {
                show_chart_dialog(__("Branch Breakdown"), r.message);
            }
        }
    });
}

function show_role_breakdown_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.sla_compliance_analysis.sla_compliance_analysis.get_role_breakdown_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function (r) {
            if (r.message) {
                show_chart_dialog(__("Role Breakdown"), r.message);
            }
        }
    });
}

function show_trend_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.sla_compliance_analysis.sla_compliance_analysis.get_trend_chart",
        args: {
            filters: JSON.stringify(report.get_filter_values()),
            months: 6
        },
        callback: function (r) {
            if (r.message) {
                show_chart_dialog(__("Compliance Trend (6 Months)"), r.message);
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
        colors: chart_data.colors || ["#5e64ff", "#ffa00a"],
        barOptions: chart_data.barOptions || {}
    });
}
