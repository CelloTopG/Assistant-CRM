/**
 * Employer Compliance Analysis Frontend
 */

frappe.query_reports["Employer Compliance Analysis"] = {
    default_print_format: "Assistant CRM - Employer Compliance",
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
            fieldname: "status",
            label: __("Compliance Status"),
            fieldtype: "Select",
            options: "\nCompliant\nNon-Compliant\nUnder Review\nExempt"
        }
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "compliance_status" && data) {
            let status = (data.compliance_status || "").toLowerCase();
            let cls = "gray";
            if (status === "compliant") cls = "green";
            else if (status === "non-compliant") cls = "red";
            else if (status === "under review") cls = "orange";
            value = `<span class="indicator-pill ${cls}">${value}</span>`;
        }

        if (column.fieldname === "assessment_status" && data) {
            if (data.assessment_status === "Assessed") {
                value = `<span style="color: green;">✔ ${value}</span>`;
            } else {
                value = `<span style="color: red;">✘ ${value}</span>`;
            }
        }

        return value;
    }
};
