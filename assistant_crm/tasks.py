# -*- coding: utf-8 -*-
"""
Short wrapper functions for scheduled tasks.

These wrappers provide shorter method paths for Frappe's Scheduled Job Type table,
which has a limited column length for the 'method' field.

Each wrapper imports and calls the actual function from the appropriate doctype module.
"""


def poll_twitter():
    """Poll Twitter inbox for new messages."""
    from assistant_crm.api.social_media_ports import poll_twitter_inbox
    poll_twitter_inbox()


def sweep_escalations():
    """Sweep and escalate inactive conversations."""
    from assistant_crm.api.unified_inbox_api import sweep_escalate_inactive_conversations
    sweep_escalate_inactive_conversations()


def cleanup_ussd():
    """Cleanup expired USSD sessions."""
    from assistant_crm.api.ussd_integration import cleanup_expired_ussd_sessions
    cleanup_expired_ussd_sessions()


def daily_claims():
    """Schedule daily claims status reports."""
    from assistant_crm.assistant_crm.doctype.claims_status_report.claims_status_report import (
        schedule_daily_claims_status_reports,
    )
    schedule_daily_claims_status_reports()


def weekly_claims():
    """Schedule weekly claims status reports."""
    from assistant_crm.assistant_crm.doctype.claims_status_report.claims_status_report import (
        schedule_weekly_claims_status_reports,
    )
    schedule_weekly_claims_status_reports()


def weekly_complaints():
    """Schedule weekly complaints status reports."""
    from assistant_crm.assistant_crm.doctype.complaints_status_report.complaints_status_report import (
        schedule_weekly_complaints_status_reports,
    )
    schedule_weekly_complaints_status_reports()


def monthly_complaints():
    """Schedule monthly complaints status reports."""
    from assistant_crm.assistant_crm.doctype.complaints_status_report.complaints_status_report import (
        schedule_monthly_complaints_status_reports,
    )
    schedule_monthly_complaints_status_reports()


def monthly_sla():
    """Schedule monthly SLA compliance reports."""
    from assistant_crm.assistant_crm.doctype.sla_compliance_report.sla_compliance_report import (
        schedule_monthly_sla_compliance_reports,
    )
    schedule_monthly_sla_compliance_reports()


def monthly_payout():
    """Schedule monthly payout summary reports."""
    from assistant_crm.assistant_crm.doctype.payout_summary_report.payout_summary_report import (
        schedule_monthly_payout_summary,
    )
    schedule_monthly_payout_summary()


def monthly_beneficiary():
    """Schedule monthly beneficiary status reports."""
    from assistant_crm.assistant_crm.doctype.beneficiary_status_report.beneficiary_status_report import (
        schedule_monthly_beneficiary_status_reports,
    )
    schedule_monthly_beneficiary_status_reports()


def monthly_ai_automation():
    """Schedule monthly AI automation reports."""
    from assistant_crm.assistant_crm.doctype.ai_automation_report.ai_automation_report import (
        schedule_monthly_ai_automation_reports,
    )
    schedule_monthly_ai_automation_reports()


def monthly_employer():
    """Schedule monthly employer status reports."""
    from assistant_crm.assistant_crm.doctype.employer_status_report.employer_status_report import (
        schedule_monthly_employer_status_reports,
    )
    schedule_monthly_employer_status_reports()


def quarterly_employer():
    """Schedule quarterly employer status reports."""
    from assistant_crm.assistant_crm.doctype.employer_status_report.employer_status_report import (
        schedule_quarterly_employer_status_reports,
    )
    schedule_quarterly_employer_status_reports()


def monthly_branch():
    """Schedule monthly branch performance reports."""
    from assistant_crm.assistant_crm.doctype.branch_performance_report.branch_performance_report import (
        schedule_monthly_branch_performance_reports,
    )
    schedule_monthly_branch_performance_reports()


def quarterly_branch():
    """Schedule quarterly branch performance reports."""
    from assistant_crm.assistant_crm.doctype.branch_performance_report.branch_performance_report import (
        schedule_quarterly_branch_performance_reports,
    )
    schedule_quarterly_branch_performance_reports()


def weekly_inbox():
    """Schedule weekly inbox status reports."""
    from assistant_crm.assistant_crm.doctype.inbox_status_report.inbox_status_report import (
        schedule_weekly_inbox_status_reports,
    )
    schedule_weekly_inbox_status_reports()


def monthly_inbox():
    """Schedule monthly inbox status reports."""
    from assistant_crm.assistant_crm.doctype.inbox_status_report.inbox_status_report import (
        schedule_monthly_inbox_status_reports,
    )
    schedule_monthly_inbox_status_reports()


def monthly_survey():
    """Schedule monthly survey feedback reports."""
    from assistant_crm.assistant_crm.doctype.survey_feedback_report.survey_feedback_report import (
        schedule_monthly_survey_feedback_reports,
    )
    schedule_monthly_survey_feedback_reports()


def quarterly_survey():
    """Schedule quarterly survey feedback reports."""
    from assistant_crm.assistant_crm.doctype.survey_feedback_report.survey_feedback_report import (
        schedule_quarterly_survey_feedback_reports,
    )
    schedule_quarterly_survey_feedback_reports()

