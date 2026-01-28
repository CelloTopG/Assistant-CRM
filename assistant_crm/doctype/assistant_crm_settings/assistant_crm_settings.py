# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AssistantCRMSettings(Document):
	"""Assistant CRM Settings DocType for system configuration"""
	
	def validate(self):
		"""Validate settings before saving"""
		self.validate_api_key()
		self.validate_business_hours()
		self.validate_escalation_threshold()
		self.validate_api_urls()
		self.validate_cache_settings()
		self.validate_rate_limits()
	
	def validate_api_key(self):
		"""Validate API key is provided when enabled"""
		if self.enabled and not self.api_key:
			frappe.throw("API Key is required when Assistant CRM is enabled")
	
	def validate_business_hours(self):
		"""Validate business hours are logical"""
		if self.business_hours_start and self.business_hours_end:
			if self.business_hours_start >= self.business_hours_end:
				frappe.throw("Business hours start time must be before end time")
	
	def validate_escalation_threshold(self):
		"""Validate escalation threshold is within valid range"""
		if self.escalation_threshold:
			if not (-1.0 <= self.escalation_threshold <= 1.0):
				frappe.throw("Escalation threshold must be between -1.0 and 1.0")
	
	def get_ai_config(self):
		"""Get AI configuration as dictionary"""
		return {
			"provider": self.ai_provider,
			"api_key": self.get_password("api_key"),
			"model_name": self.model_name,
			"response_timeout": self.response_timeout,
			"max_tokens": self.max_tokens,
			"temperature": self.temperature
		}
	
	def get_business_config(self):
		"""Get business configuration as dictionary"""
		return {
			"contact_phone": self.wcfcb_contact_phone,
			"contact_email": self.wcfcb_contact_email,
			"office_address": self.wcfcb_office_address,
			"business_hours_start": self.business_hours_start,
			"business_hours_end": self.business_hours_end
		}
	
	def get_language_config(self):
		"""Get language configuration as dictionary"""
		return {
			"default_language": self.default_language,
			"enable_multilingual": self.enable_multilingual,
			"supported_languages": self.supported_languages.split(", ") if self.supported_languages else []
		}
	
	def get_features_config(self):
		"""Get features configuration as dictionary"""
		return {
			"enable_sentiment_analysis": self.enable_sentiment_analysis,
			"auto_escalation_enabled": self.auto_escalation_enabled,
			"escalation_threshold": self.escalation_threshold,
			"enable_conversation_logging": self.enable_conversation_logging,
			"max_conversation_history": self.max_conversation_history
		}

	def validate_api_urls(self):
		"""Validate API URL formats"""
		urls_to_check = [
			('corebusiness_api_url', 'CoreBusiness API URL'),
			('claims_api_url', 'Claims API URL')
		]

		for field, label in urls_to_check:
			url = self.get(field)
			if url and not (url.startswith('http://') or url.startswith('https://')):
				frappe.throw(f"{label} must start with http:// or https://")

	def validate_cache_settings(self):
		"""Validate cache TTL settings"""
		cache_fields = [
			'assessment_cache_ttl',
			'claims_cache_ttl',
			'session_cache_ttl'
		]

		for field in cache_fields:
			value = self.get(field)
			if value and value < 60:
				frappe.throw(f"{self.meta.get_label(field)} must be at least 60 seconds")

	def validate_rate_limits(self):
		"""Validate rate limit settings"""
		rate_fields = [
			('corebusiness_rate_limit', 1, 1000),
			('claims_rate_limit', 1, 1000)
		]

		for field, min_val, max_val in rate_fields:
			value = self.get(field)
			if value and (value < min_val or value > max_val):
				frappe.throw(f"{self.meta.get_label(field)} must be between {min_val} and {max_val}")

	def get_api_config(self, service):
		"""Get API configuration for a specific service"""
		if service == 'corebusiness':
			return {
				'base_url': self.corebusiness_api_url,
				'api_key': self.get_password('corebusiness_api_key') if self.corebusiness_api_key else None,
				'timeout': self.corebusiness_api_timeout or 10,
				'rate_limit': self.corebusiness_rate_limit or 100
			}
		elif service == 'claims':
			return {
				'base_url': self.claims_api_url,
				'api_key': self.get_password('claims_api_key') if self.claims_api_key else None,
				'timeout': self.claims_api_timeout or 10,
				'rate_limit': self.claims_rate_limit or 50
			}

		return None
