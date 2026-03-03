/**
 * Agent Performance Analysis Frontend
 */

frappe.query_reports["Agent Performance Analysis"] = {
    default_print_format: "Assistant CRM - Agent Performance",
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

        if (column.fieldname === "sla_compliance" && data) {
            let val = parseFloat(data.sla_compliance);
            let color = "red";
            if (val >= 90) color = "green";
            else if (val >= 75) color = "orange";
            value = `<span style="color: ${color}; font-weight: 700;">${value}%</span>`;
        }

        if (column.fieldname === "breached_tickets" && data) {
            if (data.breached_tickets > 0) {
                value = `<span class="indicator-pill red">${value} Breached</span>`;
            }
        }

        return value;
    }
};
