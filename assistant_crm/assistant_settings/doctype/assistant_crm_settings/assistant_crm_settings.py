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
