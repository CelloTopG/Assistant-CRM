/**
 * Payout Summary Analysis - Native ERPNext Script Report Frontend
 *
 * Comprehensive payout summary analysis with filters, charts, and Antoine AI integration.
 * Uses Payment Entry as the primary reference doctype.
 */

frappe.query_reports["Payout Summary Analysis"] = {
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
                    // Show month/year, hide dates
                    frappe.query_report.toggle_filter_display("month", false);
                    frappe.query_report.toggle_filter_display("year", false);
                    frappe.query_report.toggle_filter_display("date_from", true);
                    frappe.query_report.toggle_filter_display("date_to", true);
                } else {
                    // Hide month/year, show dates
                    frappe.query_report.toggle_filter_display("month", true);
                    frappe.query_report.toggle_filter_display("year", true);
                    frappe.query_report.toggle_filter_display("date_from", false);
                    frappe.query_report.toggle_filter_display("date_to", false);
                }
            }
        },
        {
            fieldname: "month",
            label: __("Month"),
            fieldtype: "Select",
            options: "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember",
            default: get_previous_month()
        },
        {
            fieldname: "year",
            label: __("Year"),
            fieldtype: "Select",
            options: get_year_options(),
            default: get_previous_month_year()
        },
        {
            fieldname: "date_from",
            label: __("From Date"),
            fieldtype: "Date",
            hidden: 1
        },
        {
            fieldname: "date_to",
            label: __("To Date"),
            fieldtype: "Date",
            hidden: 1
        },
        {
            fieldname: "employer",
            label: __("Employer"),
            fieldtype: "Link",
            options: "Company"
        }
    ],

    onload: function(report) {
        // Add Antoine AI button
        report.page.add_inner_button(__("Ask Antoine"), function() {
            show_antoine_dialog(report);
        }, __("AI Insights"));

        // Add chart buttons
        report.page.add_inner_button(__("Overview"), function() {
            show_overview_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("By Employer"), function() {
            show_employer_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("By Benefit Type"), function() {
            show_benefit_type_chart(report);
        }, __("Charts"));

        report.page.add_inner_button(__("Exceptions"), function() {
            show_exception_chart(report);
        }, __("Charts"));

        // Add PDF button
        report.page.add_inner_button(__("Download PDF"), function() {
            download_pdf(report);
        }, __("Actions"));
    },

    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "exception_codes" && data && data.exception_codes) {
            let codes = data.exception_codes;
            if (codes) {
                value = `<span class="indicator-pill red">${value}</span>`;
            }
        }

        if (column.fieldname === "source" && data && data.source) {
            let src = data.source.toLowerCase();
            let cls = "gray";
            if (src.includes("payment entry")) cls = "blue";
            else if (src.includes("corebusiness")) cls = "green";
            else if (src.includes("salary")) cls = "purple";
            value = `<span class="indicator-pill ${cls}">${value}</span>`;
        }

        if (column.fieldname === "net_payout" && data) {
            let net = parseFloat(data.net_payout || 0);
            if (net < 0) {
                value = `<span class="text-danger">${value}</span>`;
            }
        }

        return value;
    }
};

// =====================
// Helper Functions
// =====================

function get_previous_month() {
    let now = new Date();
    now.setMonth(now.getMonth() - 1);
    let months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"];
    return months[now.getMonth()];
}

function get_previous_month_year() {
    let now = new Date();
    now.setMonth(now.getMonth() - 1);
    return now.getFullYear().toString();
}

function get_year_options() {
    let current_year = new Date().getFullYear();
    let years = [];
    for (let i = current_year; i >= current_year - 5; i--) {
        years.push(i.toString());
    }
    return "\n" + years.join("\n");
}

// =====================
// Antoine AI Dialog
// =====================

function show_antoine_dialog(report) {
    let d = new frappe.ui.Dialog({
        title: __("Ask Antoine - Payout Summary Insights"),
        size: "large",
        fields: [
            {
                fieldname: "query",
                label: __("Your Question"),
                fieldtype: "Small Text",
                reqd: 1,
                placeholder: __("e.g., What are the main exceptions in payouts this month?")
            },
            {
                fieldname: "response_section",
                fieldtype: "Section Break",
                label: __("Antoine's Response")
            },
            {
                fieldname: "response_html",
                fieldtype: "HTML"
            }
        ],
        primary_action_label: __("Ask"),
        primary_action: function() {
            let query = d.get_value("query");
            if (!query) {
                frappe.msgprint(__("Please enter a question."));
                return;
            }

            d.fields_dict.response_html.$wrapper.html(`
                <div class="text-center" style="padding: 30px;">
                    <div class="spinner-border text-primary" role="status">
                        <span class="sr-only">${__("Loading...")}</span>
                    </div>
                    <p class="mt-3 text-muted">${__("Antoine is analyzing your payout data...")}</p>
                </div>
            `);

            frappe.call({
                method: "assistant_crm.assistant_crm.report.payout_summary_analysis.payout_summary_analysis.get_ai_insights",
                args: {
                    filters: JSON.stringify(report.get_filter_values()),
                    query: query
                },
                callback: function(r) {
                    if (r.message && r.message.insights) {
                        d.fields_dict.response_html.$wrapper.html(`
                            <div style="padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #5e64ff;">
                                <div style="white-space: pre-wrap; line-height: 1.6;">${frappe.utils.escape_html(r.message.insights).replace(/\n/g, '<br>')}</div>
                            </div>
                        `);
                    } else {
                        d.fields_dict.response_html.$wrapper.html(`
                            <div class="alert alert-warning">
                                ${__("No insights available. Please try rephrasing your question.")}
                            </div>
                        `);
                    }
                },
                error: function() {
                    d.fields_dict.response_html.$wrapper.html(`
                        <div class="alert alert-danger">
                            ${__("An error occurred. Please try again later.")}
                        </div>
                    `);
                }
            });
        }
    });

    d.fields_dict.response_html.$wrapper.html(`
        <div class="text-muted text-center" style="padding: 30px;">
            <i class="fa fa-comments fa-3x mb-3" style="color: #5e64ff;"></i>
            <p>${__("Ask Antoine about payout trends, exceptions, employer breakdowns, or any insights about your payout data.")}</p>
        </div>
    `);

    d.show();
}

// =====================
// Chart Functions
// =====================

function show_overview_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.payout_summary_analysis.payout_summary_analysis.get_overview_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function(r) {
            if (r.message) {
                show_chart_dialog(__("Payout Overview"), r.message);
            }
        }
    });
}

function show_employer_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.payout_summary_analysis.payout_summary_analysis.get_employer_breakdown_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function(r) {
            if (r.message) {
                show_chart_dialog(__("Payouts by Employer"), r.message);
            }
        }
    });
}

function show_benefit_type_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.payout_summary_analysis.payout_summary_analysis.get_benefit_type_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function(r) {
            if (r.message) {
                show_chart_dialog(__("Payouts by Benefit Type"), r.message);
            }
        }
    });
}

function show_exception_chart(report) {
    frappe.call({
        method: "assistant_crm.assistant_crm.report.payout_summary_analysis.payout_summary_analysis.get_exception_chart",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function(r) {
            if (r.message) {
                show_chart_dialog(__("Exception Breakdown"), r.message);
            }
        }
    });
}

function show_chart_dialog(title, chart_data) {
    let d = new frappe.ui.Dialog({
        title: title,
        size: "large",
        fields: [
            {
                fieldname: "chart_html",
                fieldtype: "HTML"
            }
        ]
    });

    d.show();

    // Render chart after dialog is shown
    setTimeout(function() {
        let chart_wrapper = d.fields_dict.chart_html.$wrapper;
        chart_wrapper.html('<div id="payout-chart" style="height: 400px;"></div>');

        if (chart_data && chart_data.data && chart_data.data.labels && chart_data.data.labels.length > 0) {
            new frappe.Chart("#payout-chart", {
                title: title,
                data: chart_data.data,
                type: chart_data.type || "bar",
                height: 350,
                colors: chart_data.colors || ["#5e64ff"],
                axisOptions: {
                    xAxisMode: "tick",
                    xIsSeries: false
                },
                tooltipOptions: {
                    formatTooltipY: d => format_currency(d)
                }
            });
        } else {
            chart_wrapper.html(`
                <div class="text-center text-muted" style="padding: 50px;">
                    <i class="fa fa-chart-bar fa-3x mb-3"></i>
                    <p>${__("No data available for this chart.")}</p>
                </div>
            `);
        }
    }, 100);
}

// =====================
// PDF Download
// =====================

function download_pdf(report) {
    frappe.show_alert({
        message: __("Generating PDF..."),
        indicator: "blue"
    });

    frappe.call({
        method: "assistant_crm.assistant_crm.report.payout_summary_analysis.payout_summary_analysis.generate_pdf",
        args: { filters: JSON.stringify(report.get_filter_values()) },
        callback: function(r) {
            if (r.message && r.message.file_url) {
                frappe.show_alert({
                    message: __("PDF generated successfully!"),
                    indicator: "green"
                });
                // Open the PDF in a new tab
                window.open(r.message.file_url, "_blank");
            } else {
                frappe.msgprint(__("Failed to generate PDF. Please try again."));
            }
        },
        error: function() {
            frappe.msgprint(__("An error occurred while generating PDF."));
        }
    });
}

// =====================
// Utility Functions
// =====================

function format_currency(value) {
    if (typeof value !== "number") return value;
    return frappe.format(value, { fieldtype: "Currency" });
}

