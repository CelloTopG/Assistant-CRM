# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def after_install():
	"""Setup after WCFCB Assistant CRM installation"""
	try:
		# Setup WCFCB roles and permissions
		setup_wcfcb_roles()

		# Setup system settings
		setup_system_settings()

		# Ensure Contact has social channel identifiers (Telegram/Facebook/Instagram/LinkedIn)
		setup_contact_social_fields()

		# Ensure Survey Campaign Workflow exists
		setup_survey_campaign_workflow()

		# Ensure Issue has Employer link field for per-employer case linking
		try:
			ensure_issue_employer_link_field()
		except Exception as e:
			frappe.log_error(f"Error ensuring Issue employer link field: {str(e)}", "Assistant CRM Install")

		# Ensure Issue has Branch field for branch-based reporting
		try:
			ensure_issue_branch_field()
		except Exception as e:
			frappe.log_error(f"Error ensuring Issue branch field: {str(e)}", "Assistant CRM Install")

		# Ensure Customer has WCFCB-specific fields (PAS Number, NRC, Dependant Code)
		try:
			ensure_customer_wcfcb_fields()
		except Exception as e:
			frappe.log_error(f"Error ensuring Customer WCFCB fields: {str(e)}", "Assistant CRM Install")

		# Data Mapping Profile functionality has been deprecated

		# Ensure Issue Platform Source field options cover all omnichannel platforms (e.g. USSD)
		try:
			ensure_issue_platform_source_field_options()
		except Exception as e:
			frappe.log_error(
				f"Error ensuring Issue platform source options: {str(e)}",
				"Assistant CRM Install",
			)

		# Seed API keys from site_config.json (idempotent)
		# This enables new instances to auto-configure from site config
		try:
			ensure_assistant_crm_settings_seed()
		except Exception as e:
			frappe.log_error(f"Error seeding Assistant CRM Settings: {str(e)}", "Assistant CRM Install")

		try:
			ensure_enhanced_ai_settings_seed()
		except Exception as e:
			frappe.log_error(f"Error seeding Enhanced AI Settings: {str(e)}", "Assistant CRM Install")

		try:
			ensure_social_media_settings_seed()
		except Exception as e:
			frappe.log_error(f"Error seeding Social Media Settings: {str(e)}", "Assistant CRM Install")

		# Print success message
		print("✅ WCFCB Assistant CRM installed successfully!")
		print("🤖 Omnichannel AI assistant is now available")
		print("📍 Configure at: Assistant CRM Settings")
		print("📍 Configure AI: Enhanced AI Settings")
		print("📍 Configure Social: Social Media Settings")
		print("🔗 Test Chat: /test_chat")
		print("🔗 Agent Workspace: /app/agent_workspace")
		print("")
		print("💡 TIP: Add API keys to site_config.json with prefix 'assistant_crm_'")
		print("   Example: assistant_crm_openai_api_key, assistant_crm_gemini_api_key")

	except Exception as e:
		frappe.log_error(f"Error in WCFCB Assistant CRM installation: {str(e)}", "WCFCB Assistant Install")
		print(f"❌ Installation completed with errors: {str(e)}")


def setup_wcfcb_roles():
	"""Setup WCFCB roles and permissions"""
	try:
		# Create WCFCB Agent role
		if not frappe.db.exists("Role", "WCFCB Agent"):
			agent_role = frappe.get_doc({
				"doctype": "Role",
				"role_name": "WCFCB Agent",
				"desk_access": 1,
				"is_custom": 1
			})
			agent_role.insert(ignore_permissions=True)
			print("✅ Created WCFCB Agent role")

		# Create WCFCB Assistant Admin role
		if not frappe.db.exists("Role", "WCFCB Assistant Admin"):
			admin_role = frappe.get_doc({
				"doctype": "Role",
				"role_name": "WCFCB Assistant Admin",
				"desk_access": 1,
				"is_custom": 1
			})
			admin_role.insert(ignore_permissions=True)
			print("✅ Created WCFCB Assistant Admin role")

		frappe.db.commit()
		print("✅ WCFCB roles configured")

	except Exception as e:
		frappe.log_error(f"Error setting up WCFCB roles: {str(e)}", "WCFCB Assistant Install")
		print(f"⚠️  Warning: Could not setup WCFCB roles: {str(e)}")


def setup_system_settings():
	"""Setup system settings for WCFCB Assistant CRM"""
	try:
		# Create Assistant CRM Settings if it doesn't exist
		if not frappe.db.exists("Assistant CRM Settings", "Assistant CRM Settings"):
			settings = frappe.get_doc({
				"doctype": "Assistant CRM Settings",
				"name": "Assistant CRM Settings",
				"ai_service_provider": "Gemini",
				"default_language": "en",
				"enable_multilingual": 1,
				"enable_sentiment_analysis": 1,
				"auto_escalation_enabled": 1,
				"business_hours_start": "08:00:00",
				"business_hours_end": "17:00:00",
				"wcfcb_contact_phone": "+260-211-123456",
				"wcfcb_contact_email": "info@wcfcb.gov.zm",
				"wcfcb_office_address": "WCFCB House, Lusaka, Zambia"
			})
			settings.insert(ignore_permissions=True)
			print("✅ Created Assistant CRM Settings")

		frappe.db.commit()
		print("✅ System settings configured")

	except Exception as e:
		frappe.log_error(f"Error setting up system settings: {str(e)}", "WCFCB Assistant Install")
		print(f"⚠️  Warning: Could not setup system settings: {str(e)}")



def ensure_social_media_settings_seed():
	"""Idempotently ensure Social Media Settings baseline values from site config.

	Reads optional keys from frappe.conf (site_config.json) so new instances can
	bootstrap credentials without fixtures. Supports ALL platform credentials:
	- Twitter, Facebook, Instagram, LinkedIn, Make.com, USSD
	"""
	try:
		if not frappe.db.exists("DocType", "Social Media Settings"):
			return
		doc = frappe.get_single("Social Media Settings")
		conf = frappe.conf or {}

		updated = False

		def set_if_absent(field, value):
			"""Set field only if value provided and field currently empty."""
			nonlocal updated
			if value is None or value == "":
				return
			current = None
			try:
				# Password fields return via get_password; others via get
				current = doc.get_password(field)
			except Exception:
				current = doc.get(field)
			if not current:
				doc.set(field, value)
				updated = True

		# Public URL -> webhook URL
		public_url = conf.get("assistant_crm_public_base_url")
		if public_url and not (doc.get("webhook_url") or "").strip():
			doc.set("webhook_url", f"{public_url.rstrip('/')}" + "/api/omnichannel/webhook/twitter")
			updated = True

		# Twitter credentials
		enabled_flag = conf.get("assistant_crm_twitter_enabled")
		if str(enabled_flag).lower() in ("1", "true", "yes"):
			try:
				doc.set("twitter_enabled", 1)
				updated = True
			except Exception:
				pass
		set_if_absent("twitter_client_id", conf.get("assistant_crm_twitter_client_id"))
		set_if_absent("twitter_client_secret", conf.get("assistant_crm_twitter_client_secret"))
		set_if_absent("twitter_api_key", conf.get("assistant_crm_twitter_api_key"))
		set_if_absent("twitter_api_secret", conf.get("assistant_crm_twitter_api_secret"))
		set_if_absent("twitter_bearer_token", conf.get("assistant_crm_twitter_bearer_token"))
		set_if_absent("twitter_access_token", conf.get("assistant_crm_twitter_access_token"))
		set_if_absent("twitter_access_token_secret", conf.get("assistant_crm_twitter_access_token_secret"))
		set_if_absent("twitter_webhook_env", conf.get("assistant_crm_twitter_webhook_env"))
		set_if_absent("twitter_webhook_secret", conf.get("assistant_crm_twitter_webhook_secret"))

		# Make.com credentials
		set_if_absent("make_com_api_key", conf.get("assistant_crm_make_com_api_key"))
		set_if_absent("make_com_webhook_secret", conf.get("assistant_crm_make_com_webhook_secret"))

		# Facebook credentials
		set_if_absent("facebook_app_secret", conf.get("assistant_crm_facebook_app_secret"))
		set_if_absent("facebook_page_access_token", conf.get("assistant_crm_facebook_page_access_token"))

		# Instagram credentials
		set_if_absent("instagram_access_token", conf.get("assistant_crm_instagram_access_token"))

		# LinkedIn credentials
		set_if_absent("linkedin_client_secret", conf.get("assistant_crm_linkedin_client_secret"))
		set_if_absent("linkedin_access_token", conf.get("assistant_crm_linkedin_access_token"))
		set_if_absent("linkedin_webhook_secret", conf.get("assistant_crm_linkedin_webhook_secret"))

		# USSD credentials
		set_if_absent("ussd_api_key", conf.get("assistant_crm_ussd_api_key"))
		set_if_absent("ussd_webhook_secret", conf.get("assistant_crm_ussd_webhook_secret"))

		if updated:
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			print("✅ Seeded Social Media Settings from site config (idempotent)")
	except Exception as e:
		frappe.log_error(f"Error ensuring Social Media Settings seed: {str(e)}", "Assistant CRM Install")


def ensure_enhanced_ai_settings_seed():
	"""Idempotently seed Enhanced AI Settings (OpenAI for Antoine/Anna) from site config.

	Reads from frappe.conf (site_config.json):
	- assistant_crm_openai_api_key
	- assistant_crm_openai_model
	- assistant_crm_chat_model
	"""
	try:
		if not frappe.db.exists("DocType", "Enhanced AI Settings"):
			return

		# Create if not exists
		if not frappe.db.exists("Enhanced AI Settings", "Enhanced AI Settings"):
			doc = frappe.get_doc({
				"doctype": "Enhanced AI Settings",
				"name": "Enhanced AI Settings",
				"openai_model": "gpt-4",
				"tone_adjustment_enabled": 1,
				"grammar_correction_enabled": 1,
				"style_optimization_enabled": 1,
			})
			doc.insert(ignore_permissions=True)
			print("✅ Created Enhanced AI Settings")

		doc = frappe.get_single("Enhanced AI Settings")
		conf = frappe.conf or {}
		updated = False

		def set_if_absent(field, value, is_password=False):
			"""Set field only if value provided and field currently empty."""
			nonlocal updated
			if value is None or value == "":
				return
			current = None
			try:
				if is_password:
					current = doc.get_password(field)
				else:
					current = doc.get(field)
			except Exception:
				current = doc.get(field)
			if not current:
				doc.set(field, value)
				updated = True

		# OpenAI API Key
		set_if_absent("openai_api_key", conf.get("assistant_crm_openai_api_key"), is_password=True)

		# Model configuration
		set_if_absent("openai_model", conf.get("assistant_crm_openai_model"))
		set_if_absent("chat_model", conf.get("assistant_crm_chat_model"))

		if updated:
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			print("✅ Seeded Enhanced AI Settings from site config (idempotent)")

	except Exception as e:
		frappe.log_error(f"Error ensuring Enhanced AI Settings seed: {str(e)}", "Assistant CRM Install")


def ensure_assistant_crm_settings_seed():
	"""Idempotently seed Assistant CRM Settings (Gemini API for Anna) from site config.

	Reads from frappe.conf (site_config.json):
	- assistant_crm_gemini_api_key (or assistant_crm_api_key)
	- assistant_crm_corebusiness_api_key
	- assistant_crm_claims_api_key
	- assistant_crm_telegram_bot_token
	"""
	try:
		if not frappe.db.exists("DocType", "Assistant CRM Settings"):
			return

		# Create if not exists (setup_system_settings should have created it)
		if not frappe.db.exists("Assistant CRM Settings", "Assistant CRM Settings"):
			setup_system_settings()

		doc = frappe.get_single("Assistant CRM Settings")
		conf = frappe.conf or {}
		updated = False

		def set_if_absent(field, value, is_password=False):
			"""Set field only if value provided and field currently empty."""
			nonlocal updated
			if value is None or value == "":
				return
			current = None
			try:
				if is_password:
					current = doc.get_password(field)
				else:
					current = doc.get(field)
			except Exception:
				current = doc.get(field)
			if not current:
				doc.set(field, value)
				updated = True

		# Gemini API Key (main AI provider for Anna)
		gemini_key = conf.get("assistant_crm_gemini_api_key") or conf.get("assistant_crm_api_key")
		set_if_absent("api_key", gemini_key, is_password=True)

		# CoreBusiness API Key
		set_if_absent("corebusiness_api_key", conf.get("assistant_crm_corebusiness_api_key"), is_password=True)

		# Claims API Key
		set_if_absent("claims_api_key", conf.get("assistant_crm_claims_api_key"), is_password=True)

		# Telegram Bot Token
		set_if_absent("telegram_bot_token", conf.get("assistant_crm_telegram_bot_token"), is_password=True)

		# Enable AI if API key is set
		if gemini_key and not doc.get("enabled"):
			doc.set("enabled", 1)
			doc.set("ai_provider", "Google Gemini")
			updated = True

		if updated:
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			print("✅ Seeded Assistant CRM Settings from site config (idempotent)")

	except Exception as e:
		frappe.log_error(f"Error ensuring Assistant CRM Settings seed: {str(e)}", "Assistant CRM Install")


def setup_contact_social_fields():
	"""Create or ensure social channel ID fields on Contact as Custom Fields.
	Fields: telegram_chat_id, facebook_psid, instagram_user_id, linkedin_chat_id
	"""
	try:
		from frappe.custom.doctype.custom_field.custom_field import create_custom_field

		fields = [
			{
				"fieldname": "telegram_chat_id",
				"label": "Telegram Chat ID",
				"fieldtype": "Data",
				"insert_after": "mobile_no",
			},
			{
				"fieldname": "facebook_psid",
				"label": "Facebook PSID",
				"fieldtype": "Data",
				"insert_after": "telegram_chat_id",
			},
			{
				"fieldname": "instagram_user_id",
				"label": "Instagram User ID",
				"fieldtype": "Data",
				"insert_after": "facebook_psid",
			},
			{
				"fieldname": "linkedin_chat_id",
				"label": "LinkedIn Chat ID",
				"fieldtype": "Data",
				"insert_after": "instagram_user_id",
			},
		]

		for f in fields:
			# Create if missing
			if not frappe.db.exists("Custom Field", {"dt": "Contact", "fieldname": f["fieldname"]}):
				try:
					create_custom_field("Contact", f)
					print(f"✅ Added Contact field: {f['label']}")
				except Exception as ce:
					frappe.log_error(f"Error creating custom field {f['fieldname']}: {str(ce)}", "Assistant CRM Install")
			# else: leave existing as-is

		# Refresh metadata for Contact
		try:
			frappe.clear_cache(doctype="Contact")
		except Exception:
			pass

		frappe.db.commit()
		print("✅ Contact social fields ensured")

	except Exception as e:
		frappe.log_error(f"Error ensuring Contact social fields: {str(e)}", "Assistant CRM Install")


def ensure_default_mapping_profiles():
	"""Data Mapping Profile functionality has been deprecated."""
	pass


def _get_issue_platform_source_baseline_options():
	"""Return baseline platform options list for Issue.custom_platform_source.

	Prefer Unified Inbox Conversation.platform options; fall back to a static list
	that includes all supported omnichannel channels (WhatsApp, Facebook, Instagram,
	Telegram, Twitter, Tawk.to, Website Chat, Email, Phone, LinkedIn, USSD, YouTube).
	"""
	try:
		if frappe.db.exists("DocType", "Unified Inbox Conversation"):
			meta = frappe.get_meta("Unified Inbox Conversation")
			field = getattr(meta, "get_field", None) and meta.get_field("platform") or None
			raw_opts = (getattr(field, "options", "") or "") if field else ""
			if raw_opts:
				return [o.strip() for o in raw_opts.split("\n") if o.strip()]
	except Exception:
		# Fall back to static defaults below
		pass

	return [
		"WhatsApp",
		"Facebook",
		"Instagram",
		"Telegram",
		"Twitter",
		"Tawk.to",
		"Website Chat",
		"Email",
		"Phone",
		"LinkedIn",
		"USSD",
		"YouTube",
	]


def ensure_issue_platform_source_field_options():
	"""Ensure Issue.custom_platform_source Select options include all omnichannel platforms.

	This prevents ticket creation failures such as:
	"Platform Source cannot be 'USSD'. It should be one of 'WhatsApp', ...".
	"""
	try:
		if not frappe.db.exists("DocType", "Issue"):
			return

		cf_name = frappe.db.get_value(
			"Custom Field",
			{"dt": "Issue", "fieldname": "custom_platform_source"},
			"name",
		)
		if not cf_name:
			return

		cf = frappe.get_doc("Custom Field", cf_name)
		current_raw = (cf.options or "").strip()
		current_list = [o.strip() for o in current_raw.split("\n") if o.strip()]

		baseline = _get_issue_platform_source_baseline_options()
		merged = []
		for opt in current_list:
			if opt and opt not in merged:
				merged.append(opt)
		for opt in baseline:
			if opt and opt not in merged:
				merged.append(opt)

		new_raw = "\n".join(merged)
		if new_raw != current_raw:
			cf.options = new_raw
			cf.save(ignore_permissions=True)
			try:
				frappe.clear_cache(doctype="Issue")
			except Exception:
				pass
			print("Ensured Issue.custom_platform_source options include all omnichannel platforms")
	except Exception as e:
		frappe.log_error(
			f"Error ensuring Issue platform source options: {str(e)}",
			"Assistant CRM Install",
		)



def ensure_issue_employer_link_field():
	"""Create or ensure Employer Link field on Issue (idempotent)."""
	try:
		# Only if Issue DocType exists on this site
		if not frappe.db.exists("DocType", "Issue"):
			return
		from frappe.custom.doctype.custom_field.custom_field import create_custom_field

		# NOTE: Employer Profile doctype has been removed - using ERPNext Customer instead
		field_def = {
			"fieldname": "employer",
			"label": "Employer",
			"fieldtype": "Link",
			"options": "Customer",  # Using ERPNext Customer (Employer Profile removed)
			"insert_after": "custom_customer_nrc",
		}
		if not frappe.db.exists("Custom Field", {"dt": "Issue", "fieldname": field_def["fieldname"]}):
			create_custom_field("Issue", field_def)
			print("✅ Added Issue field: Employer (Link to Customer)")
	except Exception as e:
		frappe.log_error(f"Error ensuring Issue employer field: {str(e)}", "Assistant CRM Install")
	finally:
		try:
			frappe.clear_cache(doctype="Issue")
		except Exception:
			pass


def ensure_issue_branch_field():
	"""Create or ensure Branch Select field on Issue (idempotent)."""
	try:
		# Only if Issue DocType exists on this site
		if not frappe.db.exists("DocType", "Issue"):
			return
		from frappe.custom.doctype.custom_field.custom_field import create_custom_field

		field_def = {
			"fieldname": "custom_branch",
			"label": "Branch",
			"fieldtype": "Select",
			"options": "Head Office\nLusaka\nKitwe\nNdola\nLivingstone\nChipata\nKasama\nSolwezi\nKabwe\nChingola\nMufulira",
			"insert_after": "employer",
		}
		if not frappe.db.exists("Custom Field", {"dt": "Issue", "fieldname": field_def["fieldname"]}):
			create_custom_field("Issue", field_def)
			print("✅ Added Issue field: Branch (Select)")
	except Exception as e:
		frappe.log_error(f"Error ensuring Issue branch field: {str(e)}", "Assistant CRM Install")
	finally:
		try:
			frappe.clear_cache(doctype="Issue")
		except Exception:
			pass


def ensure_customer_wcfcb_fields():
	"""Create or ensure WCFCB-specific fields on Customer (idempotent)."""
	try:
		if not frappe.db.exists("DocType", "Customer"):
			return
		from frappe.custom.doctype.custom_field.custom_field import create_custom_field

		fields = [
			{
				"fieldname": "custom_pas_number",
				"label": "PAS Number",
				"fieldtype": "Data",
				"insert_after": "customer_name",
			},
			{
				"fieldname": "custom_nrc_number",
				"label": "NRC Number",
				"fieldtype": "Data",
				"insert_after": "custom_pas_number",
			},
			{
				"fieldname": "custom_dependant_code",
				"label": "Dependant Code",
				"fieldtype": "Data",
				"insert_after": "custom_nrc_number",
			},
		]

		for f in fields:
			if not frappe.db.exists("Custom Field", {"dt": "Customer", "fieldname": f["fieldname"]}):
				create_custom_field("Customer", f)
				print(f"✅ Added Customer field: {f['label']}")
	except Exception as e:
		frappe.log_error(f"Error ensuring Customer WCFCB fields: {str(e)}", "Assistant CRM Install")
	finally:
		try:
			frappe.clear_cache(doctype="Customer")
		except Exception:
			pass


def ensure_customer_wcfcb_fields():
	"""Create or ensure WCFCB-specific custom fields on Customer (idempotent)."""
	try:
		if not frappe.db.exists("DocType", "Customer"):
			return
		from frappe.custom.doctype.custom_field.custom_field import create_custom_field

		fields = [
			{
				"fieldname": "custom_pas_number",
				"label": "PAS Number",
				"fieldtype": "Data",
				"insert_after": "customer_name",
			},
			{
				"fieldname": "custom_nrc_number",
				"label": "NRC Number",
				"fieldtype": "Data",
				"insert_after": "custom_pas_number",
			},
			{
				"fieldname": "custom_dependant_code",
				"label": "Dependant Code",
				"fieldtype": "Data",
				"insert_after": "custom_nrc_number",
			},
		]

		for f in fields:
			if not frappe.db.exists("Custom Field", {"dt": "Customer", "fieldname": f["fieldname"]}):
				create_custom_field("Customer", f)
				print(f"✅ Added Customer field: {f['label']}")
	except Exception as e:
		frappe.log_error(f"Error ensuring Customer WCFCB fields: {str(e)}", "Assistant CRM Install")
	finally:
		try:
			frappe.clear_cache(doctype="Customer")
		except Exception:
			pass


def setup_survey_campaign_workflow():
	"""Ensure Survey Campaign Approval workflow exists and is active."""
	try:
		if frappe.db.exists("Workflow", "Survey Campaign Approval"):
			return

		wf = frappe.get_doc({
			"doctype": "Workflow",
			"workflow_name": "Survey Campaign Approval",
			"document_type": "Survey Campaign",
			"workflow_state_field": "workflow_state",
			"is_active": 1,
			"send_email_alert": 0,
			"states": [
				{
					"state": "Draft",
					"doc_status": 0,
					"is_default": 1,
					"allow_edit": "System Manager"
				},
				{
					"state": "In Review",
					"doc_status": 0,
					"allow_edit": "System Manager"
				},
				{
					"state": "Launched",
					"doc_status": 1
				},
				{
					"state": "Cancelled",
					"doc_status": 2
				}
			],
			"transitions": [
				{
					"state": "Draft",
					"action": "Send for Review",
					"next_state": "In Review",
					"allowed": "System Manager",
					"allow_self_approval": 1
				},
				{
					"state": "In Review",
					"action": "Approve & Launch",
					"next_state": "Launched",
					"allowed": "System Manager",
					"allow_self_approval": 1
				},
				{
					"state": "Launched",
					"action": "Cancel",
					"next_state": "Cancelled",
					"allowed": "System Manager",
					"allow_self_approval": 1
				}
			]
		})
		wf.insert(ignore_permissions=True)
		frappe.db.commit()
		print("✅ Survey Campaign Approval workflow ensured")
	except Exception as e:
		frappe.log_error(f"Error ensuring Survey Campaign workflow: {str(e)}", "Assistant CRM Install")

def before_uninstall():
	"""Cleanup before app uninstallation"""
	try:
		print("⚠️  Uninstalling WCFCB Assistant CRM...")
		print("💬 Message history will be preserved unless manually deleted")

		frappe.db.commit()
		print("✅ WCFCB Assistant CRM cleanup completed")

	except Exception as e:
		frappe.log_error(f"Error in WCFCB Assistant CRM uninstall: {str(e)}", "WCFCB Assistant Uninstall")
		print(f"❌ Uninstall completed with errors: {str(e)}")



def after_migrate():
    """Post-migrate cleanup to prevent runtime errors related to removed doctypes.

    - Remove any Custom Field on Employee that references non-existent child DocType
      like "Employee Emergency Contact" (older ERPNext versions used this).
    - Clear metadata cache so forms reload with correct schema.
    """
    try:
        to_remove = frappe.get_all(
            "Custom Field",
            filters={
                "dt": "Employee",
                "fieldtype": "Table",
                "options": "Employee Emergency Contact",
            },
            pluck="name",
        )
        for cf in to_remove:
            try:
                frappe.delete_doc("Custom Field", cf, force=1, ignore_permissions=True)
            except Exception:
                # Continue even if one fails
                pass

        # Also remove any Property Setter that points to missing options (defensive)
        bad_props = frappe.get_all(
            "Property Setter",
            filters={"doc_type": "Employee", "value": ["like", "%Employee Emergency Contact%"]},
            pluck="name",
        )

        for ps in bad_props:
            try:
                frappe.delete_doc("Property Setter", ps, force=1, ignore_permissions=True)
            except Exception:
                pass

        # Ensure Issue Employer field after migrations as well
        try:
            ensure_issue_employer_link_field()
        except Exception as e:
            frappe.log_error(f"after_migrate employer field setup error: {str(e)}", "Assistant CRM Install")

        # Ensure Issue Branch field after migrations as well
        try:
            ensure_issue_branch_field()
        except Exception as e:
            frappe.log_error(f"after_migrate branch field setup error: {str(e)}", "Assistant CRM Install")

        # Ensure Customer WCFCB fields after migrations as well
        try:
            ensure_customer_wcfcb_fields()
        except Exception as e:
            frappe.log_error(f"after_migrate Customer WCFCB fields setup error: {str(e)}", "Assistant CRM Install")

        # Remove legacy Customer Satisfaction Survey DocType if present
        try:
            if frappe.db.exists("DocType", "Customer Satisfaction Survey"):
                frappe.delete_doc("DocType", "Customer Satisfaction Survey", force=1, ignore_permissions=True)
                frappe.db.sql("DROP TABLE IF EXISTS `tabCustomer Satisfaction Survey`")
                print("✅ Removed legacy 'Customer Satisfaction Survey' DocType and table")
        except Exception as e:
            frappe.log_error(f"Failed to remove legacy CSAT DocType: {str(e)}", "Assistant CRM Install")

        # Remove Reports that referenced the legacy CSAT DocType
        try:
            reports = frappe.get_all("Report", filters={"ref_doctype": "Customer Satisfaction Survey"}, pluck="name")
            for r in reports:
                frappe.delete_doc("Report", r, force=1, ignore_permissions=True)
                print(f"🧹 Removed legacy Report: {r}")
        except Exception as e:
            frappe.log_error(f"Failed to remove legacy CSAT Reports: {str(e)}", "Assistant CRM Install")

        # Ensure Contact social fields exist after any migration
        try:
            setup_contact_social_fields()
        except Exception as e:
            frappe.log_error(f"after_migrate social fields setup error: {str(e)}", "Assistant CRM Install")

        # Re-seed API keys from site_config.json on every migration
        # This ensures new config values are picked up without reinstalling
        try:
            ensure_assistant_crm_settings_seed()
        except Exception as e:
            frappe.log_error(f"after_migrate Assistant CRM Settings seed error: {str(e)}", "Assistant CRM Install")

        try:
            ensure_enhanced_ai_settings_seed()
        except Exception as e:
            frappe.log_error(f"after_migrate Enhanced AI Settings seed error: {str(e)}", "Assistant CRM Install")

        try:
            ensure_social_media_settings_seed()
        except Exception as e:
            frappe.log_error(f"after_migrate Social Media Settings seed error: {str(e)}", "Assistant CRM Install")

    finally:
        try:
            frappe.clear_cache(doctype="Employee")
            frappe.clear_cache(doctype="Contact")
        except Exception:
            pass

