/**
 * Issue Turnaround Analysis Frontend
 */

frappe.query_reports["Issue Turnaround Analysis"] = {
    default_print_format: "Assistant CRM - Issue Turnaround",
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
        }
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "sla_status" && data) {
            let status = (data.sla_status || "").toLowerCase();
            let cls = "gray";
            if (status === "met") cls = "green";
            else if (status === "breached") cls = "red";
            value = `<span class="indicator-pill ${cls}">${value}</span>`;
        }

        if (column.fieldname === "tat_hours" && data) {
            if (data.tat_hours > 24) {
                value = `<span style="color: #e53e3e; font-weight: 700;">${value}h</span>`;
            } else {
                value = `<span>${value}h</span>`;
            }
        }

        return value;
    }
};
