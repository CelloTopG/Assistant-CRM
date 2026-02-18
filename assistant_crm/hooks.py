app_name = "assistant_crm"
app_title = "WCFCB Assistant CRM"
app_publisher = "WCFCB"
app_description = "WCFCB CRM Chatbot - Omnichannel AI Assistant"
app_email = "support@wcfcb.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# Removed standalone unified inbox app - now integrated as ERPNext page

# Includes in <head>
# ------------------

# include js, css files in header of desk.html - DASHBOARD ASSETS REMOVED
app_include_css = [
    "/assets/assistant_crm/css/chat_bubble.css"
]
app_include_js = [
    "/assets/assistant_crm/js/chat_bubble.js",
    "/assets/assistant_crm/js/report_utils.js"
]

# Also include in web pages
web_include_css = "/assets/assistant_crm/css/chat_bubble.css"
web_include_js = "/assets/assistant_crm/js/chat_bubble.js"


# Run cleanup after migrations to remove stale customizations that reference removed doctypes
after_migrate = "assistant_crm.install.after_migrate"

# Fixtures removed - using programmatic installation instead

# Scheduled Tasks (commented out to avoid loading issues)
# scheduler_events = {
#     "daily": [
#         "assistant_crm.doctype.assistant_crm_log.assistant_crm_log.cleanup_old_logs"
#     ]
# }

# Installation hooks (removed duplicate)

# Boot Session - ENABLED for proper initialization
# ----------------
# Load environment variables on boot
boot_session = "assistant_crm.boot.load_environment_variables"

# include js, css files in header of web template
# web_include_css = "/assets/assistant_crm/css/assistant_crm.css"
# web_include_js = "/assets/assistant_crm/js/assistant_crm.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "assistant_crm/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
page_js = {"assistant-crm" : "public/js/chat_bubble.js"}

# include js in doctype views
doctype_js = {
    "Issue": "public/js/issue_platform_guard.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "assistant_crm/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "assistant_crm.utils.jinja_methods",
# 	"filters": "assistant_crm.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "assistant_crm.install.before_install"
after_install = "assistant_crm.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "assistant_crm.uninstall.before_uninstall"
# after_uninstall = "assistant_crm.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "assistant_crm.utils.before_app_install"
# after_app_install = "assistant_crm.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "assistant_crm.utils.before_app_uninstall"
# after_app_uninstall = "assistant_crm.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "assistant_crm.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }


# Employer scoping for Payout Summary Report
permission_query_conditions = {
    "Payout Summary Report": "assistant_crm.assistant_crm.doctype.payout_summary_report.payout_summary_report.get_permission_query_conditions",
}
has_permission = {
    "Payout Summary Report": "assistant_crm.assistant_crm.doctype.payout_summary_report.payout_summary_report.has_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    # Guardrail: prevent editing system-managed platform source on Issue after creation
    # Branch assignment: enqueue background job to assign branch based on beneficiary location
    "Issue": {
        "validate": "assistant_crm.issue_hooks.prevent_platform_source_edit",
        "after_insert": "assistant_crm.issue_hooks.enqueue_branch_assignment"
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"assistant_crm.tasks.all"
# 	],
# 	"daily": [
# 		"assistant_crm.tasks.daily"
# 	],
# 	"hourly": [
# 		"assistant_crm.tasks.hourly"
# 	],
# 	"weekly": [
# 		"assistant_crm.tasks.weekly"
# 	],
# 	"monthly": [
# 		"assistant_crm.tasks.monthly"
# 	],
# }

# Twitter polling every 10 minutes and escalation sweep hourly + Claims/Complaints reports emailers
# Using short wrapper paths from assistant_crm.tasks to avoid exceeding Scheduled Job Type method column length
scheduler_events = {
    "cron": {
        "*/10 * * * *": [
            "assistant_crm.tasks.poll_twitter"
        ],
        "0 * * * *": [
            "assistant_crm.tasks.sweep_escalations"
        ],
        # USSD session cleanup every 6 hours
        "0 */6 * * *": [
            "assistant_crm.tasks.cleanup_ussd"
        ],
        # Daily Claims Status Report at 07:15
        "15 7 * * *": [
            "assistant_crm.tasks.daily_claims"
        ],
        # Weekly Claims Status Report every Monday at 07:30
        "30 7 * * 1": [
            "assistant_crm.tasks.weekly_claims"
        ],
        # Weekly Complaints Status Report every Monday at 07:45
        "45 7 * * 1": [
            "assistant_crm.tasks.weekly_complaints"
        ],
        # Monthly Complaints Status Report on the 1st day at 07:35
        "35 7 1 * *": [
            "assistant_crm.tasks.monthly_complaints"
        ],
        # Monthly SLA Compliance Report on the 1st day at 08:05
        "5 8 1 * *": [
            "assistant_crm.tasks.monthly_sla"
        ],
        # Payout Summary Report: check 1st business day each weekday at 07:00
        "0 7 * * 1-5": [
            "assistant_crm.tasks.monthly_payout"
        ],
        # Beneficiary Status Report: check 1st business day each weekday at 07:15 and send Excel+PDF to Finance
        "15 7 * * 1-5": [
            "assistant_crm.tasks.monthly_beneficiary"
        ],
        # AI Automation Report - check 1st business day each weekday at 07:45
        "45 7 * * 1-5": [
            "assistant_crm.tasks.monthly_ai_automation"
        ],
        # Employer Status Report - Monthly on the 1st at 07:25
        "25 7 1 * *": [
            "assistant_crm.tasks.monthly_employer"
        ],
        # Employer Status Report - Quarterly on Jan/Apr/Jul/Oct 1st at 07:35
        "35 7 1 1,4,7,10 *": [
            "assistant_crm.tasks.quarterly_employer"
        ],
        # Branch Performance Report - Monthly: check 1st business day each weekday at 07:55
        "55 7 * * 1-5": [
            "assistant_crm.tasks.monthly_branch"
        ],
        # Branch Performance Report - Quarterly: on Jan/Apr/Jul/Oct 1st at 08:05 for previous quarter
        "5 8 1 1,4,7,10 *": [
            "assistant_crm.tasks.quarterly_branch"
        ],
        # Inbox Status Report - Weekly every Monday at 08:00 (calendar week aligned)
        "0 8 * * 1": [
            "assistant_crm.tasks.weekly_inbox"
        ],
        # Inbox Status Report - Monthly on the 1st at 08:15 (previous full month)
        "15 8 1 * *": [
            "assistant_crm.tasks.monthly_inbox"
        ],
        # Survey Feedback Report - Monthly on the 1st at 07:20
        "20 7 1 * *": [
            "assistant_crm.tasks.monthly_survey"
        ],
        # Survey Feedback Report - Quarterly on Jan/Apr/Jul/Oct 1st at 07:30
        "30 7 1 1,4,7,10 *": [
            "assistant_crm.tasks.quarterly_survey"
        ],
    }
}


# Scheduled jobs for survey follow-up sweeps (disabled)
# Reason: assistant_crm.services.survey_service.sweep_low_score_followups
# is not a module-level function, so Frappe cannot import it via hooks.
# If needed later, expose a module-level wrapper and re-enable this.
# scheduler_events = {
#     "cron": {
#         # At minute 0 past every 2nd hour
#         "0 */2 * * *": [
#             "assistant_crm.services.survey_service.sweep_low_score_followups"
#         ]
#     }
# }


# Testing
# -------

# before_tests = "assistant_crm.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "assistant_crm.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "assistant_crm.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["assistant_crm.utils.before_request"]
# after_request = ["assistant_crm.utils.after_request"]

# Job Events
# ----------
# before_job = ["assistant_crm.utils.before_job"]
# after_job = ["assistant_crm.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"assistant_crm.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Real-time Communication Configuration
# ------------------------------------

# Real-time event handlers for omnichannel communication
realtime_events = {
	"omnichannel_message": "assistant_crm.services.realtime_service.handle_omnichannel_message",
	"agent_assignment": "assistant_crm.services.realtime_service.handle_agent_assignment",
	"conversation_update": "assistant_crm.services.realtime_service.handle_conversation_update",
	"typing_indicator": "assistant_crm.services.realtime_service.handle_typing_indicator",
	"message_status_update": "assistant_crm.services.realtime_service.handle_message_status_update"
}

# WebSocket event handlers for live communication
socketio_events = {
	"join_conversation": "assistant_crm.services.realtime_service.join_conversation_room",
	"leave_conversation": "assistant_crm.services.realtime_service.leave_conversation_room",
	"agent_status_change": "assistant_crm.services.realtime_service.update_agent_status",
	"typing_start": "assistant_crm.services.realtime_service.handle_typing_start",
	"typing_stop": "assistant_crm.services.realtime_service.handle_typing_stop"
}

# Website route rules for omnichannel endpoints
website_route_rules = [
	# Make.com centralized integration endpoint
	{"from_route": "/api/omnichannel/webhook/make-com", "to_route": "assistant_crm.api.make_com_webhook.make_com_webhook"},

	# Legacy direct platform webhooks (maintained for backward compatibility)
	{"from_route": "/api/omnichannel/webhook/whatsapp", "to_route": "assistant_crm.api.realtime_webhooks.whatsapp_webhook"},
	{"from_route": "/api/omnichannel/webhook/facebook", "to_route": "assistant_crm.api.social_media_ports.social_media_webhook"},
	{"from_route": "/api/omnichannel/webhook/telegram", "to_route": "assistant_crm.api.realtime_webhooks.telegram_webhook"},
	# New USSD webhook (synchronous response as text/plain)
	{"from_route": "/api/omnichannel/webhook/ussd", "to_route": "assistant_crm.api.ussd_integration.ussd_webhook"},
	# YouTube webhook (PubSubHubbub and custom integrations)
	{"from_route": "/api/omnichannel/webhook/youtube", "to_route": "assistant_crm.api.realtime_webhooks.youtube_webhook"},

	# Assistant CRM web interface - REMOVED to prevent homepage interference
	# {"from_route": "/assistant-crm/<path:app_path>", "to_route": "assistant-crm"}
]

