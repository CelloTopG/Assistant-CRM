# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import os
import json
from frappe.utils import cint, flt


class SettingsService:
	"""Service to manage Assistant CRM settings and configuration"""

	def __init__(self):
		self.settings = None
		self._load_settings()

	def _load_settings(self):
		"""Load settings from database or cache"""
		try:
			# Try to get from cache first
			cached_settings = frappe.cache().get_value("assistant_crm_settings")
			if cached_settings:
				self.settings = cached_settings
				return

			# Load from database - Single DocType
			try:
				self.settings = frappe.get_single("Assistant CRM Settings")
				# Cache for 5 minutes
				frappe.cache().set_value("assistant_crm_settings", self.settings, expires_in_sec=300)
			except Exception:
				# If Single DocType fails, create default settings
				self.settings = self._create_default_settings()

		except Exception as e:
			frappe.log_error(f"Error loading Assistant CRM settings: {str(e)}", "Settings Service")
			self.settings = self._get_fallback_settings()

	def _create_default_settings(self):
		"""Create default settings document"""
		try:
			default_settings = frappe.get_doc({
				"doctype": "Assistant CRM Settings",
				"name": "Assistant CRM Settings",
				"enabled": 0,  # Disabled by default until API key is configured
				"ai_provider": "Google Gemini",
				"model_name": "gemini-1.5-flash",
				"response_timeout": 30,
				"cache_duration": 300,
				"max_concurrent_requests": 5,
				"default_response_format": "Professional",
				"chat_bubble_position": "Bottom Right",
				"welcome_message": "Hello! I'm ExN Assistant. How can I help you today?",
				"show_typing_indicator": 1,
				"enable_audit_logging": 1,
				"log_retention_days": 30
			})

			default_settings.insert(ignore_permissions=True)
			return default_settings

		except Exception as e:
			frappe.log_error(f"Error creating default settings: {str(e)}", "Settings Service")
			return self._get_fallback_settings()

	def _get_fallback_settings(self):
		"""Get fallback settings from environment variables"""
		class FallbackSettings:
			def __init__(self):
				# Only enable if API key is provided in environment
				api_key = os.getenv("GEMINI_API_KEY", "") or "AIzaSyBJYdJ6NaBuFmSXzgTWlFR8kkPrtycnetQ"
				self.enabled = cint(os.getenv("ASSISTANT_CRM_ENABLED", "1"))  # Enable by default
				self.ai_provider = os.getenv("AI_PROVIDER", "Google Gemini")
				self.api_key = api_key
				self.model_name = os.getenv("AI_MODEL", "gemini-1.5-flash")
				self.api_endpoint = os.getenv("AI_API_ENDPOINT", "")
				self.response_timeout = cint(os.getenv("AI_RESPONSE_TIMEOUT", "30"))
				self.cache_duration = cint(os.getenv("CACHE_DURATION", "300"))
				self.max_concurrent_requests = cint(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
				self.enable_debug_logging = cint(os.getenv("DEBUG_LOGGING", "0"))
				self.default_response_format = "Professional"
				self.chat_bubble_position = "Bottom Right"
				self.welcome_message = "Hello! I'm ExN Assistant. How can I help you today?"
				self.show_typing_indicator = 1
				self.enable_audit_logging = 1
				self.log_retention_days = 30
				self.system_links = []
				self.custom_context_information = ""
				self.company_terminology = {}
				self.data_access_restrictions = {}

			def get_password(self, field):
				if field == "api_key":
					return self.api_key
				return ""

		return FallbackSettings()

	def is_enabled(self):
		"""Check if ExN Assistant is enabled"""
		return getattr(self.settings, 'enabled', False)

	def get_ai_config(self):
		"""Get AI configuration"""
		# Get API key from settings first, then fallback to .env.ai file
		api_key = ""
		if hasattr(self.settings, 'get_password'):
			api_key = self.settings.get_password("api_key") or ""
		else:
			api_key = getattr(self.settings, 'api_key', '')

		# If no API key in settings, try to read from .env.ai file
		if not api_key:
			api_key = self._get_api_key_from_env()

		return {
			"provider": getattr(self.settings, 'ai_provider', 'Google Gemini'),
			"api_key": api_key,
			"model_name": getattr(self.settings, 'model_name', 'gemini-1.5-flash'),
			"api_endpoint": getattr(self.settings, 'api_endpoint', ''),
			"custom_headers": self._parse_json_field('custom_headers'),
			"response_timeout": getattr(self.settings, 'response_timeout', 30),
			"enable_debug_logging": getattr(self.settings, 'enable_debug_logging', False)
		}

	def _get_api_key_from_env(self):
		"""Get API key from .env.ai file"""
		try:
			import os
			from pathlib import Path

			# Look for .env.ai file in the frappe-bench directory
			bench_path = Path(frappe.utils.get_bench_path())
			env_file = bench_path / '.env.ai'

			if env_file.exists():
				with open(env_file, 'r') as f:
					for line in f:
						line = line.strip()
						if line.startswith('google_gemini_api_key='):
							return line.split('=', 1)[1].strip().strip('"\'')
						elif line.startswith('GEMINI_API_KEY='):
							return line.split('=', 1)[1].strip().strip('"\'')
						elif line.startswith('GOOGLE_API_KEY='):
							return line.split('=', 1)[1].strip().strip('"\'')

			# Fallback default API key for development/testing only (user requested hardcoded endpoints)
			return "AIzaSyBJYdJ6NaBuFmSXzgTWlFR8kkPrtycnetQ"
		except Exception as e:
			frappe.log_error(f"Error reading API key from .env.ai: {str(e)}", "Settings Service")
			return ""

	def get_performance_config(self):
		"""Get performance configuration"""
		return {
			"response_timeout": getattr(self.settings, 'response_timeout', 30),
			"cache_duration": getattr(self.settings, 'cache_duration', 300),
			"max_concurrent_requests": getattr(self.settings, 'max_concurrent_requests', 5),
			"enable_debug_logging": getattr(self.settings, 'enable_debug_logging', False)
		}

	def get_ui_config(self):
		"""Get UI configuration"""
		return {
			"default_response_format": getattr(self.settings, 'default_response_format', 'Professional'),
			"chat_bubble_position": getattr(self.settings, 'chat_bubble_position', 'Bottom Right'),
			"welcome_message": getattr(self.settings, 'welcome_message', 'Hello! I\'m ExN Assistant. How can I help you today?'),
			"show_typing_indicator": getattr(self.settings, 'show_typing_indicator', True)
		}

	def get_system_links(self, user=None):
		"""Get system integration links for user"""
		if not user:
			user = frappe.session.user

		if hasattr(self.settings, 'get_system_links_for_user'):
			return self.settings.get_system_links_for_user(user)

		# Fallback for basic settings
		system_links = getattr(self.settings, 'system_links', [])
		if not system_links:
			return []

		user_roles = frappe.get_roles(user)
		accessible_links = []

		for link in system_links:
			if not getattr(link, 'enabled', True):
				continue

			# Basic role checking
			if hasattr(link, 'allowed_roles') and link.allowed_roles:
				link_roles = [role.role for role in link.allowed_roles]
				if not any(role in user_roles for role in link_roles):
					continue

			accessible_links.append({
				"system_name": getattr(link, 'system_name', ''),
				"display_label": getattr(link, 'display_label', ''),
				"target_url": getattr(link, 'target_url', ''),
				"icon": getattr(link, 'icon', '🔗'),
				"link_type": getattr(link, 'link_type', 'New Tab'),
				"description": getattr(link, 'description', '')
			})

		return accessible_links

	def get_context_config(self):
		"""Get context management configuration"""
		return {
			"custom_context_information": getattr(self.settings, 'custom_context_information', ''),
			"company_terminology": self._parse_json_field('company_terminology'),
			"data_access_restrictions": self._parse_json_field('data_access_restrictions')
		}

	def get_security_config(self):
		"""Get security and permissions configuration"""
		return {
			"allowed_roles": getattr(self.settings, 'allowed_roles', []),
			"data_access_restrictions": self._parse_json_field('data_access_restrictions'),
			"enable_audit_logging": getattr(self.settings, 'enable_audit_logging', True),
			"log_retention_days": getattr(self.settings, 'log_retention_days', 30)
		}

	def _parse_json_field(self, field_name):
		"""Parse JSON field safely"""
		try:
			field_value = getattr(self.settings, field_name, None)
			if field_value:
				if isinstance(field_value, str):
					return json.loads(field_value)
				return field_value
			return {}
		except (json.JSONDecodeError, AttributeError):
			return {}

	def refresh_settings(self):
		"""Refresh settings from database"""
		frappe.cache().delete_value("assistant_crm_settings")
		self._load_settings()

	def log_interaction(self, log_type, log_data=None, error_message=None, status="Success", **kwargs):
		"""Log user interaction if audit logging is enabled"""
		try:
			if not getattr(self.settings, 'enable_audit_logging', True):
				return

			# Use assistant_crm's own logging instead of exn_assistant
			# Create a simple log entry function
			def create_log_entry(log_type, log_data=None, error_message=None, status="Success", **kwargs):
				import frappe
				try:
					log_doc = frappe.get_doc({
						"doctype": "Assistant CRM Log",
						"log_type": log_type,
						"log_data": str(log_data) if log_data else "",
						"error_message": error_message,
						"status": status
					})
					log_doc.insert()
					return log_doc.name
				except:
					return None

			return create_log_entry(
				log_type=log_type,
				log_data=log_data,
				error_message=error_message,
				status=status,
				**kwargs
			)

		except Exception as e:
			frappe.log_error(f"Error logging interaction: {str(e)}", "Settings Service")

	def validate_user_access(self, user=None):
		"""Validate if user has access to ExN Assistant"""
		if not user:
			user = frappe.session.user

		if not self.is_enabled():
			return False

		# Allow guest users basic access for configuration checks
		if user == 'Guest':
			return True

		# Check allowed roles for authenticated users
		allowed_roles = getattr(self.settings, 'allowed_roles', [])
		if allowed_roles:
			try:
				user_roles = frappe.get_roles(user)
				role_names = [role.role for role in allowed_roles] if hasattr(allowed_roles[0], 'role') else allowed_roles

				if not any(role in user_roles for role in role_names):
					return False
			except Exception:
				# If role checking fails, allow access for authenticated users
				return True

		return True

	def get_all_config(self):
		"""Get complete configuration"""
		return {
			"enabled": self.is_enabled(),
			"ai_config": self.get_ai_config(),
			"performance_config": self.get_performance_config(),
			"ui_config": self.get_ui_config(),
			"context_config": self.get_context_config(),
			"security_config": self.get_security_config(),
			"system_links": self.get_system_links()
		}


# Global instance
_settings_service = None

def get_settings_service():
	"""Get global settings service instance"""
	global _settings_service
	if _settings_service is None:
		_settings_service = SettingsService()
	return _settings_service


@frappe.whitelist(allow_guest=True)
def get_settings():
	"""API endpoint to get settings"""
	service = get_settings_service()
	return service.get_all_config()


@frappe.whitelist()
def refresh_settings():
	"""API endpoint to refresh settings"""
	global _settings_service
	_settings_service = None
	service = get_settings_service()
	return {"success": True, "message": "Settings refreshed successfully"}


@frappe.whitelist(allow_guest=True)
def validate_access():
	"""API endpoint to validate user access"""
	service = get_settings_service()
	has_access = service.validate_user_access()

	return {
		"has_access": has_access,
		"enabled": service.is_enabled(),
		"user": frappe.session.user
	}



@frappe.whitelist()
def export_settings(include_secrets: int = 0):
	"""Export Assistant CRM Settings for transfer. Restricted to admins.
	include_secrets: 1 to include API keys/passwords; 0 to mask them.
	"""
	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	if not ({"System Manager", "WCFCB Assistant Admin"} & roles):
		frappe.throw("Not permitted", frappe.PermissionError)

	doc = frappe.get_single("Assistant CRM Settings")
	data = doc.as_dict(no_default_fields=True)
	# Mask secrets unless explicitly requested
	mask = (not bool(int(include_secrets or 0)))
	secret_fields = [
		"api_key",
		"telegram_bot_token",
		"corebusiness_api_key",
		"claims_api_key",
	]
	for f in secret_fields:
		if mask:
			data[f] = "***"
		else:
			try:
				# Password fields use get_password
				if f == "api_key":
					data[f] = doc.get_password("api_key")
				elif f == "telegram_bot_token":
					data[f] = doc.get_password("telegram_bot_token")
				elif f == "corebusiness_api_key":
					data[f] = doc.get_password("corebusiness_api_key")
				elif f == "claims_api_key":
					data[f] = doc.get_password("claims_api_key")
			except Exception:
				pass
	return {"success": True, "settings": data}


@frappe.whitelist()
def import_settings(settings: dict | None = None, settings_json: str | None = None):
	"""Import Assistant CRM Settings from a dict or JSON string. Restricted to admins."""
	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	if not ({"System Manager", "WCFCB Assistant Admin"} & roles):
		frappe.throw("Not permitted", frappe.PermissionError)

	try:
		if settings is None and settings_json:
			import json as _json
			settings = _json.loads(settings_json)
		doc = frappe.get_single("Assistant CRM Settings")
		if not isinstance(settings, dict):
			return {"success": False, "message": "Invalid payload"}

		# Update simple fields (skip name/doctype/meta fields)
		skip = {"doctype", "name", "owner", "creation", "modified", "modified_by"}
		for k, v in settings.items():
			if k in skip:
				continue
			# Secrets: allow overwrite if not masked
			if k in {"api_key", "telegram_bot_token", "corebusiness_api_key", "claims_api_key"}:
				if isinstance(v, str) and v and v != "***":
					setattr(doc, k, v)
				continue
			setattr(doc, k, v)
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		# Bust cache
		try:
			frappe.cache().delete_value("assistant_crm_settings")
		except Exception:
			pass
		return {"success": True, "message": "Settings imported"}
	except Exception as e:
		frappe.log_error(f"Settings import failed: {str(e)}", "Assistant CRM Settings Import")
		return {"success": False, "message": str(e)}
