# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class OmnichannelConversation(Document):
	def validate(self):
		"""Validate conversation data"""
		if not self.conversation_id:
			self.conversation_id = self.name
		
		if not self.creation_time:
			self.creation_time = frappe.utils.now()
	
	def on_update(self):
		"""Update last message time when conversation is updated"""
		self.last_message_time = frappe.utils.now()
	
	def assign_to_agent(self, agent_id):
		"""Assign conversation to an agent"""
		self.assigned_agent = agent_id
		self.status = 'Assigned'
		self.save()
	
	def escalate(self, reason=None):
		"""Escalate conversation"""
		self.escalation_level += 1
		self.escalation_reason = reason
		self.save()
	
	def resolve(self, summary=None):
		"""Mark conversation as resolved"""
		self.status = 'Resolved'
		self.resolution_time = frappe.utils.now()
		if summary:
			self.summary = summary
		self.save()
	
	def close(self):
		"""Close conversation"""
		self.status = 'Closed'
		self.save()

@frappe.whitelist(allow_guest=False)
def create_conversation(customer_id, channel, priority='Medium'):
	"""Create a new conversation"""
	conversation = frappe.get_doc({
		'doctype': 'Omnichannel Conversation',
		'customer_id': customer_id,
		'primary_channel': channel,
		'priority': priority,
		'status': 'Open'
	})
	conversation.insert()
	return conversation.name

@frappe.whitelist(allow_guest=False)
def get_agent_conversations(agent_id=None):
	"""Get conversations assigned to an agent"""
	if not agent_id:
		agent_id = frappe.session.user
	
	conversations = frappe.db.get_all('Omnichannel Conversation',
		filters={'assigned_agent': agent_id, 'status': ['in', ['Open', 'Assigned', 'Pending']]},
		fields=['name', 'conversation_id', 'customer_name', 'primary_channel', 'priority', 'creation_time'],
		order_by='creation_time desc'
	)
	
	return conversations
