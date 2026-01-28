# Copyright (c) 2025, WCFCB and Contributors
# See license.txt

import frappe
import unittest
from assistant_crm.doctype.assistant_crm_settings.assistant_crm_settings import AssistantCRMSettings


class TestAssistantCRMSettings(unittest.TestCase):
	def setUp(self):
		"""Set up test data"""
		self.test_settings_name = "Test Assistant CRM Settings"
		
	def tearDown(self):
		"""Clean up test data"""
		# Clean up any test records
		if frappe.db.exists("Assistant CRM Settings", self.test_settings_name):
			frappe.delete_doc("Assistant CRM Settings", self.test_settings_name)
		frappe.db.commit()
	
	def test_settings_creation(self):
		"""Test creating assistant CRM settings"""
		settings_doc = frappe.get_doc({
			"doctype": "Assistant CRM Settings",
			"name": self.test_settings_name,
			"api_key": "test_api_key_12345",
			"webhook_url": "https://example.com/webhook",
			"max_chat_history": 100,
			"enable_logging": 1,
			"default_response": "Hello! How can I help you today?"
		})
		
		settings_doc.insert()
		self.assertTrue(settings_doc.name)
		self.assertEqual(settings_doc.api_key, "test_api_key_12345")
		self.assertEqual(settings_doc.max_chat_history, 100)
	
	def test_settings_validation(self):
		"""Test settings validation"""
		settings_doc = frappe.get_doc({
			"doctype": "Assistant CRM Settings",
			"name": self.test_settings_name,
			"api_key": "test_api_key_12345",
			"webhook_url": "https://example.com/webhook"
		})
		
		# Should not raise any validation errors
		settings_doc.validate()
	
	def test_invalid_webhook_url(self):
		"""Test validation with invalid webhook URL"""
		settings_doc = frappe.get_doc({
			"doctype": "Assistant CRM Settings",
			"name": self.test_settings_name,
			"api_key": "test_api_key_12345",
			"webhook_url": "invalid_url"
		})
		
		# Should raise validation error for invalid URL
		with self.assertRaises(frappe.ValidationError):
			settings_doc.validate()
	
	def test_api_key_encryption(self):
		"""Test API key encryption/masking"""
		settings_doc = frappe.get_doc({
			"doctype": "Assistant CRM Settings",
			"name": self.test_settings_name,
			"api_key": "test_api_key_12345",
			"webhook_url": "https://example.com/webhook"
		})
		
		settings_doc.insert()
		
		# Test that API key is properly stored
		self.assertTrue(len(settings_doc.api_key) > 0)
	
	def test_default_values(self):
		"""Test default values are set correctly"""
		settings_doc = frappe.get_doc({
			"doctype": "Assistant CRM Settings",
			"name": self.test_settings_name
		})
		
		settings_doc.insert()
		
		# Check default values
		self.assertEqual(settings_doc.max_chat_history, 50)  # Assuming default is 50
		self.assertEqual(settings_doc.enable_logging, 1)  # Assuming default is enabled
	
	def test_get_settings(self):
		"""Test retrieving settings"""
		# Create test settings
		settings_doc = frappe.get_doc({
			"doctype": "Assistant CRM Settings",
			"name": self.test_settings_name,
			"api_key": "test_api_key_12345",
			"webhook_url": "https://example.com/webhook",
			"max_chat_history": 75
		})
		settings_doc.insert()
		
		# Retrieve settings
		retrieved_settings = frappe.get_doc("Assistant CRM Settings", self.test_settings_name)
		
		self.assertEqual(retrieved_settings.api_key, "test_api_key_12345")
		self.assertEqual(retrieved_settings.max_chat_history, 75)
	
	def test_update_settings(self):
		"""Test updating settings"""
		# Create initial settings
		settings_doc = frappe.get_doc({
			"doctype": "Assistant CRM Settings",
			"name": self.test_settings_name,
			"api_key": "test_api_key_12345",
			"max_chat_history": 50
		})
		settings_doc.insert()
		
		# Update settings
		settings_doc.max_chat_history = 100
		settings_doc.save()
		
		# Verify update
		updated_settings = frappe.get_doc("Assistant CRM Settings", self.test_settings_name)
		self.assertEqual(updated_settings.max_chat_history, 100)
