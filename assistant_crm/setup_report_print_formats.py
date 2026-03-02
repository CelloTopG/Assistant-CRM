import frappe
import json

def ensure_report_print_formats():
    """Ensure custom Jinja Print Formats exist for the 3 main reports."""
    reports = [
        {
            "report_name": "Claims Status Analysis",
            "label": "Claims Status Report (PDF Format)",
            "html": get_claims_html()
        },
        {
            "report_name": "Beneficiary Status Analysis",
            "label": "Beneficiary Financial Report (PDF Format)",
            "html": get_beneficiary_html()
        },
        {
            "report_name": "Complaints Status Analysis",
            "label": "Complaints Status Report (PDF Format)",
            "html": get_complaints_html()
        }
    ]

    for r in reports:
        name = f"Assistant CRM - {r['report_name']}"
        if not frappe.db.exists("Print Format", name):
            doc = frappe.get_doc({
                "doctype": "Print Format",
                "name": name,
                "doc_type": r["report_name"], # For Script Reports, doc_type is the Report name
                "module": "Assistant Crm",
                "print_format_type": "Jinja",
                "html": r["html"],
                "standard": "No",
                "custom_format": 1
            })
            doc.insert(ignore_permissions=True)
            print(f"✅ Created Print Format: {name}")
        else:
            # Update existing to ensure latest HTML matches user request
            doc = frappe.get_doc("Print Format", name)
            doc.html = r["html"]
            doc.save(ignore_permissions=True)
            print(f"ℹ️  Updated Print Format: {name}")

    frappe.db.commit()

def get_claims_html():
    return """
<style>
    .report-header { text-align: center; margin-bottom: 30px; }
    .report-header h2 { margin: 0; color: #1a202c; }
    .report-header h3 { margin: 5px 0; color: #4a5568; }
    .report-header p { font-size: 14px; color: #718096; }
    
    .summary-cards { display: flex; flex-wrap: wrap; justify-content: center; margin-bottom: 25px; }
    .summary-card { min-width: 140px; padding: 12px; margin: 8px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; text-align: center; }
    .summary-label { font-size: 11px; color: #718096; text-transform: uppercase; margin-bottom: 4px; }
    .summary-value { font-size: 18px; font-weight: 700; color: #2d3748; }

    table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }
    th { background-color: #f7fafc; border: 1px solid #edf2f7; padding: 8px; text-align: left; font-weight: 600; }
    td { border: 1px solid #edf2f7; padding: 8px; vertical-align: top; }
    
    .indicator { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 600; color: #fff; }
    .green { background-color: #38a169; }
    .red { background-color: #e53e3e; }
    .orange { background-color: #dd6b20; }
    .blue { background-color: #3182ce; }
    .yellow { background-color: #ecc94b; color: #000; }
    .gray { background-color: #718096; }
    
    .text-right { text-align: right; }
    .footer { margin-top: 50px; text-align: center; font-size: 10px; color: #a0aec0; border-top: 1px solid #edf2f7; padding-top: 10px; }
</style>

<div class="report-header">
    <h2>WORKERS' COMPENSATION FUND CONTROL BOARD</h2>
    <h3>Claims Status Report</h3>
    <p>Period: {{ filters.get("period_type") }} ({{ frappe.format(filters.get("date_from"), "Date") }} to {{ frappe.format(filters.get("date_to"), "Date") }})</p>
</div>

<div class="summary-cards">
    {% for card in report_summary %}
    <div class="summary-card">
        <div class="summary-label">{{ card.label }}</div>
        <div class="summary-value" style="color: {{ card.indicator or '#2d3748' }}">{{ card.value }}</div>
    </div>
    {% endfor %}
</div>

<table>
    <thead>
        <tr>
            <th>Claim ID</th>
            <th>Claimant Name</th>
            <th>Branch</th>
            <th>Status</th>
            <th>Type</th>
            <th class="text-right">Amount</th>
            <th>Submitted</th>
            <th>Escalated</th>
        </tr>
    </thead>
    <tbody>
        {% for row in data %}
        <tr>
            <td>{{ row.get("claim_number") or row.get("name") }}</td>
            <td style="font-weight: 600;">{{ row.get("claimant_name") or row.get("claimant") }}</td>
            <td>{{ row.get("branch") or "-" }}</td>
            <td>
                {% set status = (row.get("status") or "").lower() %}
                {% if status == "approved" or status == "settled" %}<span class="indicator green">{{ row.status }}</span>
                {% elif status == "rejected" %}<span class="indicator red">{{ row.status }}</span>
                {% elif status == "escalated" %}<span class="indicator orange">{{ row.status }}</span>
                {% elif status == "validated" %}<span class="indicator blue">{{ row.status }}</span>
                {% else %}<span class="indicator gray">{{ row.status }}</span>{% endif %}
            </td>
            <td>{{ row.get("claim_type") }}</td>
            <td class="text-right">{{ frappe.format(row.amount, "Currency") }}</td>
            <td>{{ frappe.format(row.get("submitted_date") or row.get("creation"), "Date") }}</td>
            <td>
                {% if row.get("is_escalated") %}<span class="indicator red">Yes</span>
                {% else %}<span class="indicator gray">No</span>{% endif %}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<div class="footer">
    <p>Generated by WorkCom Analytics on {{ frappe.format(frappe.utils.now(), "Datetime") }}</p>
    <p>© Workers' Compensation Fund Control Board</p>
</div>
"""

def get_beneficiary_html():
    return """
<style>
    .report-header { text-align: center; margin-bottom: 25px; }
    .report-header h2 { margin: 0; font-size: 20px; }
    .report-header h3 { margin: 5px 0; color: #2c5282; }
    
    .period-section { margin-bottom: 35px; page-break-inside: avoid; }
    .period-title { background: #ebf8ff; padding: 10px; border-left: 5px solid #2b6cb0; font-weight: 700; margin-bottom: 10px; }
    
    table { width: 100%; border-collapse: collapse; font-size: 11px; }
    th { background: #edf2f7; border: 1px solid #cbd5e0; padding: 8px; text-align: left; }
    td { border: 1px solid #cbd5e0; padding: 8px; vertical-align: middle; }
    
    .summary-card { display: inline-block; min-width: 120px; padding: 10px; margin: 5px; border: 1px solid #e2e8f0; border-radius: 6px; }
    .summary-label { font-size: 10px; color: #718096; }
    .summary-value { font-size: 16px; font-weight: 700; }
    
    .text-right { text-align: right; }
    .text-center { text-align: center; }
    .footer { margin-top: 40px; font-size: 9px; color: #a0aec0; text-align: center; border-top: 1px solid #eee; padding-top: 10px; }
</style>

<div class="report-header">
    <h2>WORKERS' COMPENSATION FUND CONTROL BOARD</h2>
    <h3>Beneficiary Status Financial Report</h3>
    <p>As of {{ frappe.format(filters.get("date_to"), "Date") }}</p>
</div>

<div class="summary-cards" style="text-align: center; margin-bottom: 20px;">
    {% for card in report_summary %}
    <div class="summary-card">
        <div class="summary-label">{{ card.label }}</div>
        <div class="summary-value" style="color: {{ card.indicator or '#2d3748' }}">{{ card.value }}</div>
    </div>
    {% endfor %}
</div>

{% set grouped = {} %}
{% for row in data %}
    {% set p = row.get("period", "Unknown") %}
    {% if p not in grouped %}{% set _ = grouped.update({p: []}) %}{% endif %}
    {% set _ = grouped[p].append(row) %}
{% endfor %}

{% for period, rows in grouped.items() %}
<div class="period-section">
    <div class="period-title">Period: {{ period }}</div>
    <table>
        <thead>
            <tr>
                <th style="width: 25%;">Beneficiary (Name & NRC)</th>
                <th style="width: 12%;">Pension No.</th>
                <th class="text-right" style="width: 12%;">Paid</th>
                <th class="text-right" style="width: 12%;">Unpaid</th>
                <th class="text-center" style="width: 8%;">Cond. Met</th>
                <th class="text-right" style="width: 12%;">Balance</th>
            </tr>
        </thead>
        <tbody>
            {% set t_paid = 0 %}{% set t_unpaid = 0 %}
            {% for row in rows %}
                {% set t_paid = t_paid + (row.get("amount_paid") or 0) %}
                {% set t_unpaid = t_unpaid + (row.get("unpaid_compensation") or 0) %}
                <tr>
                    <td><b>{{ row.get("beneficiary_name") }}</b><br><small>{{ row.get("beneficiary_id") }} | NRC: {{ row.get("nrc_number") or "-" }}</small></td>
                    <td>{{ row.get("pas_number") or "-" }}</td>
                    <td class="text-right">{{ frappe.format(row.get("amount_paid"), "Currency") }}</td>
                    <td class="text-right">{{ frappe.format(row.get("unpaid_compensation"), "Currency") }}</td>
                    <td class="text-center">{% if row.get("conditions_met") %}<span style="color: green;">✔</span>{% else %}<span style="color: red;">✘</span>{% endif %}</td>
                    <td class="text-right" style="font-weight: 600;">{{ frappe.format(row.get("remaining_balance"), "Currency") }}</td>
                </tr>
            {% endfor %}
        </tbody>
        <tfoot>
            <tr style="background: #f7fafc; font-weight: 700;">
                <td colspan="2" class="text-right">Total for {{ period }}:</td>
                <td class="text-right">{{ frappe.format(t_paid, "Currency") }}</td>
                <td class="text-right">{{ frappe.format(t_unpaid, "Currency") }}</td>
                <td></td>
                <td class="text-right">{{ frappe.format(t_unpaid, "Currency") }}</td>
            </tr>
        </tfoot>
    </table>
</div>
{% endfor %}

<div class="footer">
    <p>Confidential Financial Document | Workers' Compensation Fund Control Board</p>
    <p>Generated on {{ frappe.format(frappe.utils.now(), "Datetime") }}</p>
</div>
"""

def get_complaints_html():
    return """
<style>
    .report-header { text-align: center; margin-bottom: 25px; }
    .report-header h2 { margin: 0; color: #2d3748; }
    .report-header h3 { margin: 5px 0; color: #2c7a7b; }
    
    .summary-card { display: inline-block; min-width: 110px; padding: 10px; margin: 4px; border: 1px solid #e2e8f0; border-radius: 8px; text-align: center; }
    .summary-label { font-size: 10px; color: #718096; text-transform: uppercase; }
    .summary-value { font-size: 16px; font-weight: 700; color: #2d3748; }

    table { width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 15px; }
    th { background-color: #f7fafc; border: 1px solid #edf2f7; padding: 8px; text-align: left; }
    td { border: 1px solid #edf2f7; padding: 8px; vertical-align: middle; }
    
    .indicator { display: inline-block; padding: 2px 6px; border-radius: 10px; font-size: 9px; font-weight: 600; color: #fff; }
    .green { background-color: #38a169; }
    .blue { background-color: #3182ce; }
    .orange { background-color: #dd6b20; }
    .red { background-color: #e53e3e; }
    .gray { background-color: #718096; }
    
    .escalated-badge { background: #fff5f5; border: 1px solid #feb2b2; color: #c53030; padding: 2px 4px; border-radius: 4px; font-weight: 700; font-size: 9px; text-align: center; }
    .text-center { text-align: center; }
    .footer { margin-top: 50px; text-align: center; font-size: 9px; color: #a0aec0; }
</style>

<div class="report-header">
    <h2>WORKERS' COMPENSATION FUND CONTROL BOARD</h2>
    <h3>Complaints Status Report</h3>
    <p>{{ frappe.format(filters.get("date_from"), "Date") }} to {{ frappe.format(filters.get("date_to"), "Date") }}</p>
</div>

<div class="summary-cards" style="text-align: center;">
    {% for card in report_summary %}
    <div class="summary-card">
        <div class="summary-label">{{ card.label }}</div>
        <div class="summary-value" style="color: {{ card.indicator or '#2d3748' }}">{{ card.value }}</div>
    </div>
    {% endfor %}
</div>

<table>
    <thead>
        <tr>
            <th>ID</th>
            <th>Name & NRC</th>
            <th>Type</th>
            <th>Branch</th>
            <th>Status</th>
            <th>Assigned Officer</th>
            <th>SLA</th>
            <th class="text-center">Escalated</th>
        </tr>
    </thead>
    <tbody>
        {% for row in data %}
        <tr>
            <td>{{ row.get("name") }}</td>
            <td style="font-weight: 600;">{{ row.get("complaint_name") }}</td>
            <td>{{ row.get("final_category") }}</td>
            <td>{{ row.get("branch") }}</td>
            <td>
                {% set status = (row.get("status") or "").lower() %}
                {% if status in ["resolved", "closed"] %}<span class="indicator green">{{ row.status }}</span>
                {% elif status in ["open", "replied"] %}<span class="indicator blue">{{ row.status }}</span>
                {% elif status == "hold" %}<span class="indicator orange">{{ row.status }}</span>
                {% else %}<span class="indicator gray">{{ row.status }}</span>{% endif %}
            </td>
            <td>{{ row.get("assigned_officer") or "-" }}</td>
            <td>
                {% if row.get("sla_status") == "Breached" %}<span style="color: #e53e3e; font-weight: 700;">⚠ Breached</span>
                {% elif row.get("sla_status") == "Met" %}<span style="color: #38a169;">Met</span>
                {% else %}{{ row.get("sla_status") or "-" }}{% endif %}
            </td>
            <td class="text-center">
                {% if row.get("escalated") %}<div class="escalated-badge">ESCALATED</div>{% else %}-{% endif %}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<div class="footer">
    <p>Complaints Management Division | Workers' Compensation Fund Control Board</p>
    <p>Confidential System Report | Generated on {{ frappe.format(frappe.utils.now(), "Datetime") }}</p>
</div>
"""

if __name__ == "__main__":
    ensure_report_print_formats()
