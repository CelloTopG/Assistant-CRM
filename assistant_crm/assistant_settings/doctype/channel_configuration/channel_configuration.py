# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ChannelConfiguration(Document):
	"""Channel Configuration DocType for managing communication channels"""
	
	def validate(self):
		"""Validate channel configuration"""
		self.validate_channel_type_requirements()
		self.validate_rate_limits()
		self.validate_timeouts()
	
	def validate_channel_type_requirements(self):
		"""Validate required fields based on channel type"""
		if self.channel_type == "WhatsApp":
			if not self.api_key:
				frappe.throw("API Key is required for WhatsApp channel")
			if not self.phone_number:
				frappe.throw("Phone Number ID is required for WhatsApp channel")
		
		elif self.channel_type == "Facebook":
			if not self.access_token:
				frappe.throw("Access Token is required for Facebook channel")
		
		elif self.channel_type == "Instagram":
			if not self.access_token:
				frappe.throw("Access Token is required for Instagram channel")
		
		elif self.channel_type == "Telegram":
			if not self.api_key:
				frappe.throw("Bot Token (API Key) is required for Telegram channel")
	
	def validate_rate_limits(self):
		"""Validate rate limit settings"""
		if self.rate_limit_per_minute and self.rate_limit_per_minute < 1:
			frappe.throw("Rate limit must be at least 1 message per minute")
		
		if self.rate_limit_per_minute and self.rate_limit_per_minute > 1000:
			frappe.throw("Rate limit cannot exceed 1000 messages per minute")
	
	def validate_timeouts(self):
		"""Validate timeout settings"""
		if self.response_timeout and self.response_timeout < 5:
			frappe.throw("Response timeout must be at least 5 seconds")
		
		if self.response_timeout and self.response_timeout > 300:
			frappe.throw("Response timeout cannot exceed 300 seconds (5 minutes)")
	
	def get_api_config(self):
		"""Get API configuration as dictionary"""
		config = {
			"channel_type": self.channel_type,
			"api_endpoint": self.api_endpoint,
			"phone_number": self.phone_number,
			"max_message_length": self.max_message_length,
			"response_timeout": self.response_timeout,
			"rate_limit_per_minute": self.rate_limit_per_minute
		}
		
		# Add sensitive data using get_password
		if self.api_key:
			config["api_key"] = self.get_password("api_key")
		if self.access_token:
			config["access_token"] = self.get_password("access_token")
		if self.verification_token:
			config["verification_token"] = self.get_password("verification_token")
		if self.webhook_secret:
			config["webhook_secret"] = self.get_password("webhook_secret")
		
		return config
	
	def get_webhook_config(self):
		"""Get webhook configuration"""
		return {
			"webhook_url": self.webhook_url,
			"webhook_secret": self.get_password("webhook_secret") if self.webhook_secret else None,
			"verify_token": self.verify_token,
			"enable_logging": self.enable_message_logging
		}
	
	def test_connection(self):
		"""Test connection to the channel API"""
		try:
			if self.channel_type == "WhatsApp":
				return self._test_whatsapp_connection()
			elif self.channel_type == "Facebook":
				return self._test_facebook_connection()
			elif self.channel_type == "Instagram":
				return self._test_instagram_connection()
			elif self.channel_type == "Telegram":
				return self._test_telegram_connection()
			elif self.channel_type == "Website Chat":
				return {"success": True, "message": "Website Chat channel is always available"}
			else:
				return {"success": False, "message": f"Connection test not implemented for {self.channel_type}"}
		
		except Exception as e:
			return {"success": False, "message": f"Connection test failed: {str(e)}"}
	
	def _test_whatsapp_connection(self):
		"""Test WhatsApp API connection"""
		import requests
		
		if not self.api_key or not self.phone_number:
			return {"success": False, "message": "API Key and Phone Number are required"}
		
		try:
			url = f"https://graph.facebook.com/v18.0/{self.phone_number}"
			headers = {"Authorization": f"Bearer {self.get_password('api_key')}"}
			
			response = requests.get(url, headers=headers, timeout=10)
			
			if response.status_code == 200:
				return {"success": True, "message": "WhatsApp connection successful"}
			else:
				return {"success": False, "message": f"WhatsApp API error: {response.status_code}"}
		
		except Exception as e:
			return {"success": False, "message": f"WhatsApp connection failed: {str(e)}"}
	
	def _test_facebook_connection(self):
		"""Test Facebook API connection"""
		import requests
		
		if not self.access_token:
			return {"success": False, "message": "Access Token is required"}
		
		try:
			url = "https://graph.facebook.com/v18.0/me"
			params = {"access_token": self.get_password("access_token")}
			
			response = requests.get(url, params=params, timeout=10)
			
			if response.status_code == 200:
				return {"success": True, "message": "Facebook connection successful"}
			else:
				return {"success": False, "message": f"Facebook API error: {response.status_code}"}
		
		except Exception as e:
			return {"success": False, "message": f"Facebook connection failed: {str(e)}"}
	
	def _test_instagram_connection(self):
		"""Test Instagram API connection"""
		# Instagram uses Facebook Graph API
		return self._test_facebook_connection()
	
	def _test_telegram_connection(self):
		"""Test Telegram Bot API connection"""
		import requests
		
		if not self.api_key:
			return {"success": False, "message": "Bot Token (API Key) is required"}
		
		try:
			url = f"https://api.telegram.org/bot{self.get_password('api_key')}/getMe"
			
			response = requests.get(url, timeout=10)
			
			if response.status_code == 200:
				return {"success": True, "message": "Telegram connection successful"}
			else:
				return {"success": False, "message": f"Telegram API error: {response.status_code}"}
		
		except Exception as e:
			return {"success": False, "message": f"Telegram connection failed: {str(e)}"}
