# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta

class SLAConfiguration(Document):
	def validate(self):
		"""Validate SLA configuration"""
		self.validate_time_values()
		self.validate_unique_combination()
	
	def validate_time_values(self):
		"""Ensure time values are reasonable"""
		if self.first_response_time and self.first_response_time <= 0:
			frappe.throw("First response time must be greater than 0")
		
		if self.resolution_time and self.resolution_time <= 0:
			frappe.throw("Resolution time must be greater than 0")
		
		if self.escalation_time and self.escalation_time <= 0:
			frappe.throw("Escalation time must be greater than 0")
		
		# Ensure escalation time is less than first response time
		if (self.escalation_time and self.first_response_time and 
			self.escalation_time >= self.first_response_time):
			frappe.throw("Escalation time should be less than first response time")
	
	def validate_unique_combination(self):
		"""Ensure unique combination of priority and channel"""
		existing = frappe.db.get_value('SLA Configuration', {
			'priority': self.priority,
			'channel': self.channel,
			'name': ['!=', self.name],
			'is_active': 1
		})
		
		if existing:
			frappe.throw(f"Active SLA configuration already exists for {self.priority} priority and {self.channel} channel")

@frappe.whitelist(allow_guest=False)
def get_applicable_sla(priority, channel):
	"""Get applicable SLA configuration for given priority and channel"""
	# First try exact match
	sla = frappe.db.get_value('SLA Configuration', {
		'priority': priority,
		'channel': channel,
		'is_active': 1
	}, ['first_response_time', 'resolution_time', 'escalation_time', 'business_hours_only'], as_dict=True)
	
	if sla:
		return sla
	
	# Try priority match with 'All' channel
	sla = frappe.db.get_value('SLA Configuration', {
		'priority': priority,
		'channel': 'All',
		'is_active': 1
	}, ['first_response_time', 'resolution_time', 'escalation_time', 'business_hours_only'], as_dict=True)
	
	if sla:
		return sla
	
	# Try channel match with 'All' priority
	sla = frappe.db.get_value('SLA Configuration', {
		'priority': 'All',
		'channel': channel,
		'is_active': 1
	}, ['first_response_time', 'resolution_time', 'escalation_time', 'business_hours_only'], as_dict=True)
	
	if sla:
		return sla
	
	# Default fallback
	sla = frappe.db.get_value('SLA Configuration', {
		'priority': 'All',
		'channel': 'All',
		'is_active': 1
	}, ['first_response_time', 'resolution_time', 'escalation_time', 'business_hours_only'], as_dict=True)
	
	return sla

@frappe.whitelist(allow_guest=False)
def check_sla_breach(conversation_id):
	"""Check if conversation has breached SLA"""
	try:
		# Check if conversation exists
		if not frappe.db.exists('Omnichannel Conversation', conversation_id):
			return {'breached': False, 'message': 'Conversation not found'}

		conversation = frappe.get_doc('Omnichannel Conversation', conversation_id)

		# Get applicable SLA
		sla = get_applicable_sla(conversation.priority, conversation.primary_channel)

		if not sla:
			return {'breached': False, 'message': 'No SLA configuration found'}

		from datetime import datetime
		now = datetime.now()

		# Use creation_time field instead of creation
		created_time = conversation.creation_time if hasattr(conversation, 'creation_time') else conversation.creation
		if isinstance(created_time, str):
			created_time = frappe.utils.get_datetime(created_time)

		# Calculate elapsed time in minutes
		elapsed_minutes = (now - created_time).total_seconds() / 60

		# Check first response SLA
		if (sla.get('first_response_time') and
			not conversation.first_response_time and
			elapsed_minutes > sla.get('first_response_time')):
			return {
				'breached': True,
				'type': 'first_response',
				'elapsed_minutes': elapsed_minutes,
				'sla_minutes': sla.get('first_response_time')
			}

		# Check resolution SLA
		if (sla.get('resolution_time') and
			conversation.status not in ['Resolved', 'Closed'] and
			elapsed_minutes > (sla.get('resolution_time') * 60)):  # Convert hours to minutes
			return {
				'breached': True,
				'type': 'resolution',
				'elapsed_minutes': elapsed_minutes,
				'sla_minutes': sla.get('resolution_time') * 60
			}

		return {'breached': False}

	except Exception as e:
		frappe.log_error(f"SLA breach check error: {str(e)}")
		return {'breached': False, 'error': str(e)}

@frappe.whitelist(allow_guest=False)
def get_sla_breach_alerts():
	"""Get all conversations that have breached SLA"""
	try:
		# Check if Omnichannel Conversation doctype exists
		if not frappe.db.exists('DocType', 'Omnichannel Conversation'):
			return []

		conversations = frappe.db.sql("""
			SELECT name, conversation_id, priority, primary_channel,
				   creation_time as creation, assigned_agent, customer_id
			FROM `tabOmnichannel Conversation`
			WHERE status IN ('Open', 'Assigned', 'Pending')
			ORDER BY creation_time ASC
		""", as_dict=True)

		breached_conversations = []

		for conv in conversations:
			try:
				breach_info = check_sla_breach(conv.name)
				if breach_info.get('breached'):
					conv.update(breach_info)
					breached_conversations.append(conv)
			except Exception as e:
				frappe.log_error(f"SLA breach check error for {conv.name}: {str(e)}")
				continue

		return breached_conversations

	except Exception as e:
		frappe.log_error(f"SLA breach alerts error: {str(e)}")
		return []
