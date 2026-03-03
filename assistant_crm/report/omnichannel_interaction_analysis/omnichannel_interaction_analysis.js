/**
 * Omnichannel Interaction Analysis Frontend
 */

frappe.query_reports["Omnichannel Interaction Analysis"] = {
    default_print_format: "Assistant CRM - Omnichannel Interaction",
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

        if (column.fieldname === "channel" && data) {
            let channel = (data.channel || "").toLowerCase();
            let icon = "fa-comment";
            if (channel === "whatsapp") icon = "fa-whatsapp";
            else if (channel === "facebook") icon = "fa-facebook";
            else if (channel === "telegram") icon = "fa-paper-plane";
            else if (channel === "email") icon = "fa-envelope";

            value = `<i class="fa ${icon} mr-2"></i> ${value}`;
        }

        return value;
    }
};
