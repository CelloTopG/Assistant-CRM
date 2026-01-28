// Copyright (c) 2025, WCFCB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employer Dashboard", {
    refresh(frm) {
        // Add Generate Dashboard button
        frm.add_custom_button(__("Generate Dashboard"), function() {
            frm.trigger("generate_dashboard");
        }, __("Actions"));
        
        // Add Export buttons
        frm.add_custom_button(__("Export PDF"), function() {
            frm.trigger("export_pdf");
        }, __("Export"));
        
        frm.add_custom_button(__("Export Excel"), function() {
            frm.trigger("export_excel");
        }, __("Export"));
        
        // Set default dates if not set
        if (!frm.doc.date_from || !frm.doc.date_to) {
            const today = frappe.datetime.get_today();
            const firstOfMonth = frappe.datetime.month_start(today);
            const lastMonth = frappe.datetime.add_months(firstOfMonth, -1);
            const lastMonthEnd = frappe.datetime.add_days(firstOfMonth, -1);
            
            frm.set_value("date_from", lastMonth);
            frm.set_value("date_to", lastMonthEnd);
        }
        
        // Initialize charts if data exists
        if (frm.doc.compliance_trend_chart_json) {
            frm.trigger("render_charts");
        }
    },
    
    generate_dashboard(frm) {
        if (!frm.doc.date_from || !frm.doc.date_to) {
            frappe.msgprint(__("Please set the date range first."));
            return;
        }
        
        frappe.show_alert({
            message: __("Generating dashboard..."),
            indicator: "blue"
        });
        
        frm.call({
            method: "run_generation",
            doc: frm.doc,
            freeze: true,
            freeze_message: __("Aggregating employer data..."),
            callback: function(r) {
                if (r.message && r.message.ok) {
                    frappe.show_alert({
                        message: __("Dashboard generated successfully!"),
                        indicator: "green"
                    });
                    frm.reload_doc();
                } else {
                    frappe.msgprint(__("Error generating dashboard. Check error logs."));
                }
            }
        });
    },
    
    render_charts(frm) {
        // Render compliance trend chart
        try {
            const complianceData = JSON.parse(frm.doc.compliance_trend_chart_json || "{}");
            if (complianceData.data && complianceData.data.labels) {
                const chartContainer = document.getElementById("compliance-trend-chart");
                if (chartContainer) {
                    new frappe.Chart(chartContainer, {
                        data: complianceData.data,
                        type: complianceData.type || "line",
                        height: 200,
                        colors: ["#3b82f6"]
                    });
                }
            }
        } catch (e) {
            console.log("Chart render error:", e);
        }
    },
    
    export_pdf(frm) {
        if (!frm.doc.report_html) {
            frappe.msgprint(__("Please generate the dashboard first."));
            return;
        }
        
        frappe.call({
            method: "frappe.utils.print_format.download_pdf",
            args: {
                doctype: frm.doctype,
                name: frm.doc.name,
                format: "Standard"
            }
        });
    },
    
    export_excel(frm) {
        if (!frm.doc.rows_json) {
            frappe.msgprint(__("Please generate the dashboard first."));
            return;
        }
        
        try {
            const data = JSON.parse(frm.doc.rows_json);
            const rows = [];
            
            // Executive Summary
            rows.push(["=== Executive Summary ==="]);
            rows.push(["Total Employers", data.executive?.total_employers || 0]);
            rows.push(["Active Employers", data.executive?.active_employers || 0]);
            rows.push(["Collection Rate %", data.executive?.collection_rate_percent || 0]);
            rows.push(["Outstanding Amount", data.executive?.outstanding_amount || 0]);
            rows.push([""]);
            
            // Financial Performance
            rows.push(["=== Financial Performance ==="]);
            rows.push(["Expected Contributions", data.financial?.expected || 0]);
            rows.push(["Collected Contributions", data.financial?.collected || 0]);
            rows.push(["Total Outstanding", data.financial?.outstanding || 0]);
            rows.push(["Penalties Generated", data.financial?.penalties || 0]);
            rows.push([""]);
            
            // Branch Data
            if (data.branch?.data) {
                rows.push(["=== Branch Comparison ==="]);
                rows.push(["Branch", "Employers", "Employees", "Compliance %", "Collection %", "Revenue"]);
                data.branch.data.forEach(b => {
                    rows.push([b.branch, b.employers, b.employees, b.compliance_pct, b.collection_pct, b.collected]);
                });
            }
            
            // Create and download CSV
            const csv = rows.map(r => r.join(",")).join("\n");
            const blob = new Blob([csv], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `employer_dashboard_${frm.doc.name}.csv`;
            a.click();
            URL.revokeObjectURL(url);
            
            frappe.show_alert({
                message: __("Excel export downloaded!"),
                indicator: "green"
            });
        } catch (e) {
            frappe.msgprint(__("Error exporting data: ") + e.message);
        }
    },
    
    period_type(frm) {
        // Auto-set date range based on period type
        const today = frappe.datetime.get_today();
        const periodType = frm.doc.period_type;
        
        if (periodType === "Monthly") {
            const firstOfMonth = frappe.datetime.month_start(today);
            const lastMonth = frappe.datetime.add_months(firstOfMonth, -1);
            const lastMonthEnd = frappe.datetime.add_days(firstOfMonth, -1);
            frm.set_value("date_from", lastMonth);
            frm.set_value("date_to", lastMonthEnd);
        } else if (periodType === "Quarterly") {
            // Previous quarter
            const month = new Date(today).getMonth();
            const qStart = Math.floor(month / 3) * 3;
            const prevQStart = qStart - 3;
            const year = new Date(today).getFullYear();
            const startYear = prevQStart < 0 ? year - 1 : year;
            const startMonth = prevQStart < 0 ? prevQStart + 12 : prevQStart;
            
            const qStartDate = new Date(startYear, startMonth, 1);
            const qEndDate = new Date(startYear, startMonth + 3, 0);
            
            frm.set_value("date_from", frappe.datetime.obj_to_str(qStartDate));
            frm.set_value("date_to", frappe.datetime.obj_to_str(qEndDate));
        } else if (periodType === "Yearly") {
            const lastYear = new Date(today).getFullYear() - 1;
            frm.set_value("date_from", `${lastYear}-01-01`);
            frm.set_value("date_to", `${lastYear}-12-31`);
        }
    }
});

