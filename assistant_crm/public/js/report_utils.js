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

/**
 * Downloads report data as a Microsoft Word (.doc) file using HTML-to-Word trick.
 */
assistant_crm.report_utils.download_as_word = function (report, report_title) {
    if (!report || !report.data || report.data.length === 0) {
        frappe.msgprint(__("No data to export."));
        return;
    }

    let report_summary_html = "";
    if (report.report_summary && report.report_summary.length > 0) {
        report_summary_html = `<div style="margin-bottom: 20px; display: flex; flex-wrap: wrap;">`;
        report.report_summary.forEach(item => {
            report_summary_html += `
                <div style="padding: 10px; border: 1px solid #ddd; margin: 5px; min-width: 120px;">
                    <div style="font-size: 10px; color: #666;">${item.label}</div>
                    <div style="font-size: 16px; font-weight: bold;">${item.value}</div>
                </div>`;
        });
        report_summary_html += `</div>`;
    }

    let columns = report.columns;
    let data = report.data;

    let table_html = `<table border="1" cellpadding="5" cellspacing="0" style="width:100%; border-collapse: collapse; font-family: Arial, sans-serif; font-size: 11px;">`;

    // Header
    table_html += `<tr style="background-color: #f1f3f5; font-weight: bold;">`;
    columns.forEach(col => {
        table_html += `<th style="text-align: left; border: 1px solid #ddd;">${col.label || col.fieldname}</th>`;
    });
    table_html += `</tr>`;

    // Data
    data.forEach(row => {
        table_html += `<tr>`;
        columns.forEach(col => {
            let val = row[col.fieldname] || "";
            if (col.fieldtype === "Currency") {
                val = frappe.format(val, col);
            }
            table_html += `<td style="border: 1px solid #ddd;">${val}</td>`;
        });
        table_html += `</tr>`;
    });
    table_html += `</table>`;

    let header = `
        <div style="text-align: center; margin-bottom: 30px;">
            <h2 style="margin: 0;">WORKERS' COMPENSATION FUND CONTROL BOARD</h2>
            <h3 style="margin: 5px 0;">${report_title}</h3>
            <p style="font-size: 12px; color: #666;">Generated on ${frappe.datetime.now_date()}</p>
        </div>`;

    let content = `
        <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
        <head><meta charset='utf-8'>
        <style>
            @page { size: 8.5in 11in; margin: 1in; }
            body { font-family: 'Times New Roman', Times, serif; }
            table { width: 100%; border-collapse: collapse; }
            th, td { border: 1px solid black; padding: 5px; }
        </style>
        </head>
        <body>
            ${header}
            ${report_summary_html}
            ${table_html}
        </body>
        </html>`;

    let blob = new Blob(['\ufeff', content], {
        type: 'application/msword'
    });

    let url = URL.createObjectURL(blob);
    let link = document.createElement('a');
    link.href = url;
    link.download = `${report_title.replace(/\s+/g, '_')}_${frappe.datetime.now_date()}.doc`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};
