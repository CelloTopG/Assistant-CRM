import frappe
import json

def ensure_report_print_formats():
    """Ensure custom Jinja Print Formats exist for the 3 main reports."""
    reports = [
        {
            "report_name": "Claims Status Analysis",
            "label": "Assistant CRM - Claims Status",
            "html": get_claims_html()
        },
        {
            "report_name": "Beneficiary Status Analysis",
            "label": "Assistant CRM - Beneficiary Status",
            "html": get_beneficiary_html()
        },
        {
            "report_name": "Complaints Status Analysis",
            "label": "Assistant CRM - Complaints Status",
            "html": get_complaints_html()
        },
        {
            "report_name": "Employer Compliance Analysis",
            "label": "Assistant CRM - Employer Compliance",
            "html": get_employer_compliance_html()
        },
        {
            "report_name": "Survey Feedback Analysis",
            "label": "Assistant CRM - Survey Feedback",
            "html": get_survey_feedback_html()
        },
        {
            "report_name": "Agent Performance Analysis",
            "label": "Assistant CRM - Agent Performance",
            "html": get_agent_performance_html()
        },
        {
            "report_name": "Omnichannel Interaction Analysis",
            "label": "Assistant CRM - Omnichannel Interaction",
            "html": get_omnichannel_interaction_html()
        },
        {
            "report_name": "AI Automation Analysis",
            "label": "Assistant CRM - AI Automation",
            "html": get_ai_automation_html()
        },
        {
            "report_name": "Issue Turnaround Analysis",
            "label": "Assistant CRM - Issue Turnaround",
            "html": get_issue_turnaround_html()
        }
    ]

    for r in reports:
        name = r["label"]
        if not frappe.db.exists("Print Format", name):
            doc = frappe.get_doc({
                "doctype": "Print Format",
                "name": name,
                "doc_type": r["report_name"], 
                "module": "Assistant Crm",
                "print_format_type": "Jinja",
                "html": r["html"],
                "standard": "No",
                "custom_format": 1
            })
            doc.insert(ignore_permissions=True)
            print(f"✅ Created Print Format: {name}")
        else:
            doc = frappe.get_doc("Print Format", name)
            doc.html = r["html"]
            doc.save(ignore_permissions=True)
            print(f"ℹ️  Updated Print Format: {name}")

    frappe.db.commit()

def ensure_conversation_export_print_format():
    """Ensure a print format exists for Unified Inbox Conversation exports."""
    name = "Assistant CRM - Conversation Export"
    if not frappe.db.exists("Print Format", name):
        doc = frappe.get_doc({
            "doctype": "Print Format",
            "name": name,
            "doc_type": "Unified Inbox Conversation",
            "module": "Assistant Crm",
            "print_format_type": "Jinja",
            "html": get_conversation_html(),
            "standard": "No",
            "custom_format": 1
        })
        doc.insert(ignore_permissions=True)
    frappe.db.commit()

def get_claims_html():
    return """
<div class="report-header">
    <div style="text-align: center; margin-bottom: 25px;">
        <h2 style="margin: 0; color: #1a202c; letter-spacing: 1px;">WORKERS' COMPENSATION FUND CONTROL BOARD</h2>
        <h3 style="margin: 5px 0; color: #4a5568;">Claims Status Analysis Report</h3>
        <p style="font-size: 13px; color: #718096;">
            Period: {{ filters.get("period_type") }} ({{ frappe.format(filters.get("date_from"), "Date") }} to {{ frappe.format(filters.get("date_to"), "Date") }})
        </p>
    </div>
</div>

{% if report_summary %}
<div style="display: flex; flex-wrap: wrap; justify-content: space-around; margin-bottom: 25px; border-bottom: 2px solid #edf2f7; padding-bottom: 15px;">
    {% for item in report_summary %}
        <div style="text-align: center; padding: 10px; min-width: 120px;">
            <div style="font-size: 10px; color: #718096; text-transform: uppercase;">{{ item.label }}</div>
            <div style="font-size: 18px; font-weight: 700; color: {{ item.indicator or '#2d3748' }}">{{ item.value }}</div>
        </div>
    {% endfor %}
</div>
{% endif %}

<table style="width: 100%; border-collapse: collapse; font-size: 11px;">
    <thead>
        <tr style="background-color: #f7fafc;">
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: left;">Claim ID</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: left;">Claimant</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: left;">Branch</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: left;">Status</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: left;">Type</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: right;">Amount</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: left;">Submitted</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: center;">Esc.</th>
        </tr>
    </thead>
    <tbody>
        {% for row in data %}
        <tr>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.claim_number or row.name }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px; font-weight: 600;">{{ row.claimant_name or row.claimant }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.branch or "-" }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">
                {% set st = (row.status or "").lower() %}
                {% set color = "#718096" %}
                {% if st in ["approved", "settled"] %}{% set color = "#38a169" %}
                {% elif st == "rejected" %}{% set color = "#e53e3e" %}
                {% elif st == "escalated" %}{% set color = "#dd6b20" %}
                {% elif st == "validated" %}{% set color = "#3182ce" %}
                {% endif %}
                <span style="color: {{ color }}; font-weight: 700;">{{ row.status }}</span>
            </td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.claim_type }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px; text-align: right;">{{ frappe.format(row.amount, "Currency") }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ frappe.format(row.submitted_date or row.creation, "Date") }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px; text-align: center;">{% if row.is_escalated %}⚠️{% else %}-{% endif %}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<div style="margin-top: 30px; text-align: center; font-size: 10px; color: #a0aec0; border-top: 1px solid #edf2f7; padding-top: 10px;">
    System Generated Official Report | Workers' Compensation Fund Control Board | {{ frappe.format(frappe.utils.now(), "Datetime") }}
</div>
"""

def get_beneficiary_html():
    return """
<div style="text-align: center; border-bottom: 2px solid #2b6cb0; padding-bottom: 15px; margin-bottom: 25px;">
    <h2 style="margin: 0; color: #2c5282;">WORKERS' COMPENSATION FUND CONTROL BOARD</h2>
    <h3 style="margin: 5px 0; color: #2d3748;">Beneficiary Status Financial Summary</h3>
</div>

{% set grouped = {} %}
{% for row in data %}
    {% set p = row.period or "Jan 2025" %}
    {% if p not in grouped %}{% set _ = grouped.update({p: []}) %}{% endif %}
    {% set _ = grouped[p].append(row) %}
{% endfor %}

{% for p_key in grouped.keys()|sort %}
<div style="margin-bottom: 40px; page-break-inside: avoid;">
    <h4 style="background: #f1f5f9; padding: 8px; border-left: 4px solid #2b6cb0; margin-bottom: 10px;">Period: {{ p_key }}</h4>
    <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
        <thead>
            <tr style="background: #e2e8f0;">
                <th style="border: 1px solid #cbd5e0; padding: 8px; text-align: left;">Beneficiary Details</th>
                <th style="border: 1px solid #cbd5e0; padding: 8px; text-align: left;">Pension No</th>
                <th style="border: 1px solid #cbd5e0; padding: 8px; text-align: right;">Paid</th>
                <th style="border: 1px solid #cbd5e0; padding: 8px; text-align: right;">Unpaid</th>
                <th style="border: 1px solid #cbd5e0; padding: 8px; text-align: center;">Cond.</th>
                <th style="border: 1px solid #cbd5e0; padding: 8px; text-align: right;">Balance</th>
            </tr>
        </thead>
        <tbody>
            {% set s_paid = 0 %}{% set s_unpaid = 0 %}
            {% for row in grouped[p_key] %}
                {% set s_paid = s_paid + (row.amount_paid or 0) %}
                {% set s_unpaid = s_unpaid + (row.unpaid_compensation or 0) %}
                <tr>
                    <td style="border: 1px solid #cbd5e0; padding: 8px;">
                        <span style="font-weight: 700;">{{ row.beneficiary_name }}</span><br>
                        <small style="color: #4a5568;">{{ row.beneficiary_id }} | NRC: {{ row.nrc_number }}</small>
                    </td>
                    <td style="border: 1px solid #cbd5e0; padding: 8px;">{{ row.pas_number or "-" }}</td>
                    <td style="border: 1px solid #cbd5e0; padding: 8px; text-align: right;">{{ frappe.format(row.amount_paid, "Currency") }}</td>
                    <td style="border: 1px solid #cbd5e0; padding: 8px; text-align: right;">{{ frappe.format(row.unpaid_compensation, "Currency") }}</td>
                    <td style="border: 1px solid #cbd5e0; padding: 8px; text-align: center;">{% if row.conditions_met %}✔{% else %}✘{% endif %}</td>
                    <td style="border: 1px solid #cbd5e0; padding: 8px; text-align: right; font-weight: 700;">{{ frappe.format(row.remaining_balance, "Currency") }}</td>
                </tr>
            {% endfor %}
        </tbody>
        <tfoot>
            <tr style="background: #f8fafc; font-weight: 800;">
                <td colspan="2" style="border: 1px solid #cbd5e0; padding: 8px; text-align: right;">PERIOD TOTAL:</td>
                <td style="border: 1px solid #cbd5e0; padding: 8px; text-align: right;">{{ frappe.format(s_paid, "Currency") }}</td>
                <td style="border: 1px solid #cbd5e0; padding: 8px; text-align: right;">{{ frappe.format(s_unpaid, "Currency") }}</td>
                <td style="border: 1px solid #cbd5e0; padding: 8px;"></td>
                <td style="border: 1px solid #cbd5e0; padding: 8px; text-align: right;">{{ frappe.format(s_unpaid, "Currency") }}</td>
            </tr>
        </tfoot>
    </table>
</div>
{% endfor %}

<div style="font-size: 9px; color: #718096; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 15px; margin-top: 30px;">
    Finance Division Confidential | WCFCB System Audit Report | Generated {{ frappe.format(frappe.utils.now(), "Datetime") }}
</div>
"""

def get_complaints_html():
    return """
<div style="text-align: center; margin-bottom: 25px;">
    <h2 style="margin: 0; color: #2d3748;">WORKERS' COMPENSATION FUND CONTROL BOARD</h2>
    <h3 style="margin: 5px 0; color: #3182ce;">Enterprise Complaints Status Report</h3>
    <p style="font-size: 13px; color: #4a5568;">Report Period: {{ frappe.format(filters.get("date_from"), "Date") }} to {{ frappe.format(filters.get("date_to"), "Date") }}</p>
</div>

{% if report_summary %}
<div style="display: flex; flex-wrap: wrap; justify-content: center; margin-bottom: 20px;">
    {% for item in report_summary %}
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; margin: 5px; min-width: 110px; text-align: center; background: #fff;">
            <div style="font-size: 10px; color: #718096; text-transform: uppercase;">{{ item.label }}</div>
            <div style="font-size: 18px; font-weight: 700; color: {{ item.indicator or '#2d3748' }}">{{ item.value }}</div>
        </div>
    {% endfor %}
</div>
{% endif %}

<table style="width: 100%; border-collapse: collapse; font-size: 11px;">
    <thead>
        <tr style="background: #f7fafc;">
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: left;">Complaint ID</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: left;">Beneficiary & NRC</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: left;">Category</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: left;">Branch</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: left;">Status</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: left;">Officer</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: center;">SLA</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: center;">Esc.</th>
        </tr>
    </thead>
    <tbody>
        {% for row in data %}
        <tr>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.name }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px; font-weight: 600;">{{ row.complaint_name }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.final_category }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.branch }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">
                {% set st = (row.status or "").lower() %}
                {% set color = "#718096" %}
                {% if st in ["resolved", "closed"] %}{% set color = "#38a169" %}{% elif st in ["open", "replied"] %}{% set color = "#3182ce" %}{% endif %}
                <span style="color: {{ color }}; font-weight: 700;">{{ row.status }}</span>
            </td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.assigned_officer or "-" }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px; text-align: center;">
                {% if row.sla_status == "Breached" %}<span style="color: #e53e3e; font-weight: 700;">⚠</span>
                {% elif row.sla_status == "Met" %}<span style="color: #38a169;">✅</span>
                {% else %}-{% endif %}
            </td>
            <td style="border: 1px solid #e2e8f0; padding: 8px; text-align: center;">{% if row.escalated %}<span style="color: #e53e3e; font-weight: 800;">YES</span>{% else %}-{% endif %}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<div style="margin-top: 40px; text-align: center; font-size: 10px; color: #a0aec0; border-top: 1px solid #eee; padding-top: 10px;">
    Complaints & Customer Service Department | WCFCB Enterprise | {{ frappe.format(frappe.utils.now(), "Datetime") }}
</div>
"""

def get_conversation_html():
    return """
<div style="padding: 20px;">
    <h2 style="text-align: center;">Conversation History</h2>
    <div style="margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px;">
        <strong>ID:</strong> {{ doc.name }} <br>
        <strong>Platform:</strong> {{ doc.platform }} <br>
        <strong>Status:</strong> {{ doc.status }} <br>
        <strong>Started:</strong> {{ frappe.format(doc.creation, "Datetime") }}
    </div>
    
    <div class="chat-history">
        {% set turns = frappe.get_all("Conversation Turn", filters={"parent": doc.name}, fields=["sender", "content", "creation"], order_by="creation asc") %}
        {% for turn in turns %}
            <div style="margin-bottom: 15px; padding: 10px; border-radius: 8px; background: {{ '#f1f5f9' if turn.sender == 'Customer' else '#def7ec' }};">
                <div style="font-weight: 700; font-size: 11px; margin-bottom: 4px;">{{ turn.sender }} | {{ frappe.format(turn.creation, "Datetime") }}</div>
                <div>{{ turn.content }}</div>
            </div>
        {% endfor %}
    </div>
</div>
"""

def get_employer_compliance_html():
    return """
<div style="text-align: center; border-bottom: 2px solid #28a745; padding-bottom: 15px; margin-bottom: 25px;">
    <h2 style="margin: 0; color: #1e7e34;">WORKERS' COMPENSATION FUND CONTROL BOARD</h2>
    <h3 style="margin: 5px 0; color: #333;">Employer Compliance Analysis</h3>
    <p style="font-size: 13px;">Period: {{ frappe.format(filters.get("date_from"), "Date") }} to {{ frappe.format(filters.get("date_to"), "Date") }}</p>
</div>

{% if report_summary %}
<div style="display: flex; flex-wrap: wrap; justify-content: center; margin-bottom: 20px;">
    {% for item in report_summary %}
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; margin: 5px; min-width: 130px; text-align: center; background: #fff;">
            <div style="font-size: 10px; color: #718096; text-transform: uppercase;">{{ item.label }}</div>
            <div style="font-size: 18px; font-weight: 700; color: {{ item.indicator or '#2d3748' }}">
                {% if item.datatype == "Currency" %}{{ frappe.format(item.value, "Currency") }}{% else %}{{ item.value }}{% endif %}
            </div>
        </div>
    {% endfor %}
</div>
{% endif %}

<table style="width: 100%; border-collapse: collapse; font-size: 11px;">
    <thead>
        <tr style="background: #f7fafc;">
            <th style="border: 1px solid #e2e8f0; padding: 8px;">Employer Name</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px;">Employer No.</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px;">ZRA TPIN</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px;">Compliance</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px;">Assessment</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px;">Payment</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px; text-align: right;">Outstanding</th>
        </tr>
    </thead>
    <tbody>
        {% for row in data %}
        <tr>
            <td style="border: 1px solid #e2e8f0; padding: 8px; font-weight: 600;">{{ row.employer_name }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.employer_no }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.zra_tpin }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.compliance_status }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.assessment_status }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.payment_status }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px; text-align: right;">{{ frappe.format(row.outstanding_amount, "Currency") }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
"""

def get_survey_feedback_html():
    return """
<div style="text-align: center; border-bottom: 2px solid #5e64ff; padding-bottom: 15px; margin-bottom: 25px;">
    <h2 style="margin: 0; color: #4834d4;">WORKERS' COMPENSATION FUND CONTROL BOARD</h2>
    <h3 style="margin: 5px 0; color: #333;">Survey Feedback Analysis</h3>
</div>

{% if report_summary %}
<div style="display: flex; flex-wrap: wrap; justify-content: center; margin-bottom: 20px;">
    {% for item in report_summary %}
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; margin: 5px; min-width: 100px; text-align: center; background: #fff;">
            <div style="font-size: 10px; color: #718096; text-transform: uppercase;">{{ item.label }}</div>
            <div style="font-size: 16px; font-weight: 700; color: {{ item.indicator or '#2d3748' }}">{{ item.value }}</div>
        </div>
    {% endfor %}
</div>
{% endif %}

<table style="width: 100%; border-collapse: collapse; font-size: 11px;">
    <thead>
        <tr style="background: #f7fafc;">
            <th style="border: 1px solid #e2e8f0; padding: 8px;">Response ID</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px;">Campaign</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px;">Status</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px;">Sentiment</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px;">Sent Time</th>
            <th style="border: 1px solid #e2e8f0; padding: 8px;">Response Time</th>
        </tr>
    </thead>
    <tbody>
        {% for row in data %}
        <tr>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.name }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.campaign }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ row.status }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px; font-weight: 700;">{{ row.sentiment_label }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ frappe.format(row.sent_time, "Datetime") }}</td>
            <td style="border: 1px solid #e2e8f0; padding: 8px;">{{ frappe.format(row.response_time, "Datetime") }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
"""

def get_agent_performance_html():
    return """
<div style="text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 15px; margin-bottom: 25px;">
    <h2 style="margin: 0; color: #2980b9;">WORKERS' COMPENSATION FUND CONTROL BOARD</h2>
    <h3 style="margin: 5px 0; color: #333;">Agent Performance KPI Report</h3>
</div>

{% if report_summary %}
<div style="display: flex; flex-wrap: wrap; justify-content: space-around; margin-bottom: 20px;">
    {% for item in report_summary %}
        <div style="text-align: center; padding: 10px; min-width: 150px;">
            <div style="font-size: 10px; color: #7f8c8d; text-transform: uppercase;">{{ item.label }}</div>
            <div style="font-size: 20px; font-weight: 700; color: {{ item.indicator or '#2c3e50' }}">{{ item.value }}</div>
        </div>
    {% endfor %}
</div>
{% endif %}

<table style="width: 100%; border-collapse: collapse; font-size: 11px;">
    <thead>
        <tr style="background: #ecf0f1;">
            <th style="border: 1px solid #bdc3c7; padding: 10px;">Agent Name</th>
            <th style="border: 1px solid #bdc3c7; padding: 10px;">Tickets Handled</th>
            <th style="border: 1px solid #bdc3c7; padding: 10px;">Avg Resolution (Hrs)</th>
            <th style="border: 1px solid #bdc3c7; padding: 10px;">SLA Compliance %</th>
            <th style="border: 1px solid #bdc3c7; padding: 10px;">Breached</th>
        </tr>
    </thead>
    <tbody>
        {% for row in data %}
        <tr>
            <td style="border: 1px solid #bdc3c7; padding: 10px; font-weight: 600;">{{ row.agent }}</td>
            <td style="border: 1px solid #bdc3c7; padding: 10px; text-align: center;">{{ row.tickets_handled }}</td>
            <td style="border: 1px solid #bdc3c7; padding: 10px; text-align: center;">{{ row.avg_resolution_time }}h</td>
            <td style="border: 1px solid #bdc3c7; padding: 10px; text-align: center; font-weight: 700; color: {{ '#27ae60' if row.sla_compliance >= 90 else '#e67e22' }}">{{ row.sla_compliance }}%</td>
            <td style="border: 1px solid #bdc3c7; padding: 10px; text-align: center; color: #e74c3c;">{{ row.breached_tickets }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
"""

def get_omnichannel_interaction_html():
    return """
<div style="text-align: center; border-bottom: 2px solid #16a085; padding-bottom: 15px; margin-bottom: 25px;">
    <h2 style="margin: 0; color: #0e6655;">WORKERS' COMPENSATION FUND CONTROL BOARD</h2>
    <h3 style="margin: 5px 0; color: #333;">Omnichannel Interaction Report</h3>
</div>

{% if report_summary %}
<div style="display: flex; flex-wrap: wrap; justify-content: center; margin-bottom: 20px;">
    {% for item in report_summary %}
        <div style="border: 1px solid #d1d5db; border-radius: 6px; padding: 10px; margin: 5px; min-width: 140px; text-align: center; background: #fff;">
            <div style="font-size: 10px; color: #6b7280; text-transform: uppercase;">{{ item.label }}</div>
            <div style="font-size: 18px; font-weight: 700; color: {{ item.indicator or '#111827' }}">{{ item.value }}</div>
        </div>
    {% endfor %}
</div>
{% endif %}

<table style="width: 100%; border-collapse: collapse; font-size: 10px;">
    <thead>
        <tr style="background: #f3f4f6;">
            <th style="border: 1px solid #e5e7eb; padding: 8px;">Channel</th>
            <th style="border: 1px solid #e5e7eb; padding: 8px;">Interaction ID</th>
            <th style="border: 1px solid #e5e7eb; padding: 8px;">Agent</th>
            <th style="border: 1px solid #e5e7eb; padding: 8px;">TAT (min)</th>
            <th style="border: 1px solid #e5e7eb; padding: 8px;">Status</th>
            <th style="border: 1px solid #e5e7eb; padding: 8px;">SLA</th>
        </tr>
    </thead>
    <tbody>
        {% for row in data %}
        <tr>
            <td style="border: 1px solid #e5e7eb; padding: 8px;">{{ row.channel }}</td>
            <td style="border: 1px solid #e5e7eb; padding: 8px;">{{ row.interaction_id }}</td>
            <td style="border: 1px solid #e5e7eb; padding: 8px;">{{ row.agent }}</td>
            <td style="border: 1px solid #e5e7eb; padding: 8px; text-align: center;">{{ row.response_time }}m</td>
            <td style="border: 1px solid #e5e7eb; padding: 8px;">{{ row.status }}</td>
            <td style="border: 1px solid #e5e7eb; padding: 8px;">{{ row.sla_status }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
"""

def get_ai_automation_html():
    return """
<div style="text-align: center; border-bottom: 2px solid #8e44ad; padding-bottom: 15px; margin-bottom: 25px;">
    <h2 style="margin: 0; color: #5b2c6f;">WORKERS' COMPENSATION FUND CONTROL BOARD</h2>
    <h3 style="margin: 5px 0; color: #333;">AI Automation Exception Report</h3>
</div>

{% if report_summary %}
<div style="display: flex; flex-wrap: wrap; justify-content: center; margin-bottom: 20px;">
    {% for item in report_summary %}
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; margin: 5px; min-width: 120px; text-align: center; background: #fff;">
            <div style="font-size: 10px; color: #718096; text-transform: uppercase;">{{ item.label }}</div>
            <div style="font-size: 16px; font-weight: 700; color: {{ item.indicator or '#2d3748' }}">{{ item.value }}</div>
        </div>
    {% endfor %}
</div>
{% endif %}

<table style="width: 100%; border-collapse: collapse; font-size: 10px;">
    <thead>
        <tr style="background: #f8f9fa;">
            <th style="border: 1px solid #dee2e6; padding: 8px;">Ticket ID</th>
            <th style="border: 1px solid #dee2e6; padding: 8px;">Timestamp</th>
            <th style="border: 1px solid #dee2e6; padding: 8px;">Flag Type</th>
            <th style="border: 1px solid #dee2e6; padding: 8px;">Validation</th>
            <th style="border: 1px solid #dee2e6; padding: 8px;">Status</th>
            <th style="border: 1px solid #dee2e6; padding: 8px;">Details</th>
        </tr>
    </thead>
    <tbody>
        {% for row in data %}
        <tr>
            <td style="border: 1px solid #dee2e6; padding: 8px; font-weight: 600;">{{ row.name }}</td>
            <td style="border: 1px solid #dee2e6; padding: 8px;">{{ frappe.format(row.creation, "Datetime") }}</td>
            <td style="border: 1px solid #dee2e6; padding: 8px;">{{ row.scheduled_job_type }}</td>
            <td style="border: 1px solid #dee2e6; padding: 8px;">{% if row.is_after_hours %}After Hours{% else %}Standard{% endif %}</td>
            <td style="border: 1px solid #dee2e6; padding: 8px; font-weight: 700; color: {{ '#28a745' if row.status == 'Complete' else '#dc3545' }}">{{ row.status }}</td>
            <td style="border: 1px solid #dee2e6; padding: 8px;">{{ row.details }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
"""

def get_issue_turnaround_html():
    return """
<div style="text-align: center; border-bottom: 2px solid #e67e22; padding-bottom: 15px; margin-bottom: 25px;">
    <h2 style="margin: 0; color: #ca6f1e;">WORKERS' COMPENSATION FUND CONTROL BOARD</h2>
    <h3 style="margin: 5px 0; color: #333;">Issue Turnaround Analysis</h3>
</div>

{% if report_summary %}
<div style="display: flex; flex-wrap: wrap; justify-content: space-around; margin-bottom: 20px;">
    {% for item in report_summary %}
        <div style="text-align: center; padding: 10px; min-width: 150px; border-right: 1px solid #eee;">
            <div style="font-size: 10px; color: #7f8c8d; text-transform: uppercase;">{{ item.label }}</div>
            <div style="font-size: 20px; font-weight: 700; color: {{ item.indicator or '#2c3e50' }}">{{ item.value }}</div>
        </div>
    {% endfor %}
</div>
{% endif %}

<table style="width: 100%; border-collapse: collapse; font-size: 11px;">
    <thead>
        <tr style="background: #fdf2e9;">
            <th style="border: 1px solid #edbb99; padding: 8px;">Ticket ID</th>
            <th style="border: 1px solid #edbb99; padding: 8px;">Type</th>
            <th style="border: 1px solid #edbb99; padding: 8px;">Logged</th>
            <th style="border: 1px solid #edbb99; padding: 8px;">Resolved</th>
            <th style="border: 1px solid #edbb99; padding: 8px; text-align: right;">TAT (Hrs)</th>
            <th style="border: 1px solid #edbb99; padding: 8px; text-align: center;">SLA</th>
        </tr>
    </thead>
    <tbody>
        {% for row in data %}
        <tr>
            <td style="border: 1px solid #edbb99; padding: 8px; font-weight: 600;">{{ row.ticket_id }}</td>
            <td style="border: 1px solid #edbb99; padding: 8px;">{{ row.issue_type }}</td>
            <td style="border: 1px solid #edbb99; padding: 8px;">{{ frappe.format(row.date_logged, "Datetime") }}</td>
            <td style="border: 1px solid #edbb99; padding: 8px;">{{ frappe.format(row.date_resolved, "Datetime") if row.date_resolved else "-" }}</td>
            <td style="border: 1px solid #edbb99; padding: 8px; text-align: right; font-weight: 700; color: {{ '#e74c3c' if row.tat_hours > 24 else '#2c3e50' }}">{{ row.tat_hours }}h</td>
            <td style="border: 1px solid #edbb99; padding: 8px; text-align: center;">{{ row.sla_status }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
"""
