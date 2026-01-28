# Copyright (c) 2025, WCFCB and Contributors
# See license.txt

import frappe
import unittest
from assistant_crm.doctype.chat_history.chat_history import ChatHistory


class TestChatHistory(unittest.TestCase):
	def setUp(self):
		"""Set up test data"""
		self.test_user = "test@example.com"
		self.test_session_id = "test_session_123"
		
	def tearDown(self):
		"""Clean up test data"""
		# Clean up any test records
		frappe.db.delete("Chat History", {"session_id": self.test_session_id})
		frappe.db.commit()
	
	def test_chat_history_creation(self):
		"""Test creating a chat history record"""
		chat_doc = frappe.get_doc({
			"doctype": "Chat History",
			"user": self.test_user,
			"session_id": self.test_session_id,
			"message": "Test message",
			"response": "Test response",
			"status": "Completed"
		})
		
		chat_doc.insert()
		self.assertTrue(chat_doc.name)
		self.assertEqual(chat_doc.user, self.test_user)
		self.assertEqual(chat_doc.session_id, self.test_session_id)
	
	def test_chat_history_validation(self):
		"""Test chat history validation"""
		chat_doc = frappe.get_doc({
			"doctype": "Chat History",
			"user": self.test_user,
			"session_id": self.test_session_id,
			"message": "Test message"
		})
		
		# Should not raise any validation errors
		chat_doc.validate()
		
	def test_get_chat_history_by_session(self):
		"""Test retrieving chat history by session"""
		# Create test records
		for i in range(3):
			chat_doc = frappe.get_doc({
				"doctype": "Chat History",
				"user": self.test_user,
				"session_id": self.test_session_id,
				"message": f"Test message {i}",
				"response": f"Test response {i}",
				"status": "Completed"
			})
			chat_doc.insert()
		
		# Retrieve chat history
		chat_history = frappe.get_all(
			"Chat History",
			filters={"session_id": self.test_session_id},
			fields=["name", "message", "response"],
			order_by="creation asc"
		)
		
		self.assertEqual(len(chat_history), 3)
		self.assertEqual(chat_history[0]["message"], "Test message 0")
