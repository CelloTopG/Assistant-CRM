/**
 * Shared utility functions for Assistant CRM Reports.
 */

frappe.provide("assistant_crm.report_utils");

/**
 * Common Period Type options for reports.
 */
assistant_crm.report_utils.period_type_options = "Weekly\nMonthly\nQuarterly\nAnnual\nCustom";

/**
 * Handle period_type change to update date_from and date_to.
 */
assistant_crm.report_utils.handle_period_change = function () {
    let period_type = frappe.query_report.get_filter_value("period_type");
    let today = frappe.datetime.get_today();
    let date_from = "";
    let date_to = today;

    if (period_type === "Weekly") {
        // Start of current week (Monday)
        // JavaScript getDay(): 0 is Sunday, 1 is Monday...
        let d = new Date();
        let day = d.getDay();
        let diff = d.getDate() - day + (day == 0 ? -6 : 1); // adjust when day is sunday
        let weekStart = new Date(d.setDate(diff));
        date_from = frappe.datetime.str_to_user(weekStart);
    } else if (period_type === "Monthly") {
        date_from = frappe.datetime.month_start();
    } else if (period_type === "Quarterly") {
        let d = new Date();
        let quarter = Math.floor(d.getMonth() / 3);
        let startMonth = quarter * 3;
        let quarterStart = new Date(d.getFullYear(), startMonth, 1);
        date_from = frappe.datetime.str_to_user(quarterStart);
    } else if (period_type === "Annual") {
        date_from = frappe.datetime.year_start();
    }

    if (date_from && period_type !== "Custom") {
        frappe.query_report.set_filter_value("date_from", date_from);
        frappe.query_report.set_filter_value("date_to", date_to);
    }
};
