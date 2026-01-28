# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from frappe.utils import now, get_datetime, time_diff_in_seconds


class OmnichannelMessage(Document):
	"""Omnichannel Message DocType for handling all channel communications"""
	
	def before_insert(self):
		"""Set default values before inserting"""
		if not self.received_at:
			self.received_at = now()
		
		if not self.status:
			self.status = "Received"
		
		if not self.priority:
			self.priority = "Medium"
	
	def update_status(self, new_status, additional_data=None):
		"""Update message status with timestamp tracking"""
		old_status = self.status
		self.status = new_status
		
		# Set processed timestamp
		if new_status in ["Processing", "Responded", "Escalated"]:
			if not self.processed_at:
				self.processed_at = now()
				
				# Calculate response time
				if self.received_at:
					received_dt = get_datetime(self.received_at)
					processed_dt = get_datetime(self.processed_at)
					self.response_time = time_diff_in_seconds(processed_dt, received_dt)
		
		# Set escalation timestamp
		if new_status == "Escalated":
			self.escalated_at = now()
			self.escalated_to_agent = 1
		
		# Update additional data if provided
		if additional_data:
			for key, value in additional_data.items():
				if hasattr(self, key):
					setattr(self, key, value)
		
		self.save()
		
		# Log status change
		frappe.logger().info(f"Message {self.name} status changed from {old_status} to {new_status}")
	
	def escalate_to_agent(self, reason, agent=None):
		"""Escalate message to human agent"""
		self.escalation_reason = reason
		self.escalated_to_agent = 1
		self.escalated_at = now()
		
		if agent:
			self.agent_assigned = agent
		
		self.update_status("Escalated")
		
		# Create notification for agent
		if self.agent_assigned:
			self.create_agent_notification()
	
	def create_agent_notification(self):
		"""Create notification for assigned agent"""
		try:
			notification = frappe.get_doc({
				"doctype": "Notification Log",
				"subject": f"New message escalated: {self.channel_type}",
				"email_content": f"""
				<p>A new message has been escalated to you:</p>
				<p><strong>Channel:</strong> {self.channel_type}</p>
				<p><strong>Customer:</strong> {self.customer_name or 'Unknown'}</p>
				<p><strong>Message:</strong> {self.message_content[:200]}...</p>
				<p><strong>Reason:</strong> {self.escalation_reason}</p>
				""",
				"for_user": self.agent_assigned,
				"type": "Alert",
				"document_type": "Omnichannel Message",
				"document_name": self.name
			})
			notification.insert(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(f"Failed to create agent notification: {str(e)}", "Omnichannel Message")
	
	def get_response_context(self):
		"""Get context for AI response generation"""
		context = {
			"message": {
				"content": self.message_content,
				"channel": self.channel_type,
				"timestamp": self.received_at,
				"priority": self.priority
			},
			"customer": {
				"name": self.customer_name,
				"phone": self.customer_phone,
				"email": self.customer_email,
				"id": self.customer_id
			},
			"conversation_history": self.get_conversation_history()
		}
		
		# Add metadata if available
		if self.metadata:
			try:
				metadata = json.loads(self.metadata) if isinstance(self.metadata, str) else self.metadata
				context["metadata"] = metadata
			except:
				pass
		
		# Add sender info if available
		if self.sender_info:
			try:
				sender_info = json.loads(self.sender_info) if isinstance(self.sender_info, str) else self.sender_info
				context["sender"] = sender_info
			except:
				pass
		
		return context
	
	def get_conversation_history(self, limit=10):
		"""Get recent conversation history for context"""
		try:
			# Get recent messages from same channel/customer
			filters = {
				"channel_type": self.channel_type,
				"channel_id": self.channel_id,
				"name": ["!=", self.name]
			}
			
			if self.customer_id:
				filters["customer_id"] = self.customer_id
			
			history = frappe.get_all(
				"Omnichannel Message",
				filters=filters,
				fields=["message_content", "ai_response", "received_at", "direction"],
				order_by="received_at desc",
				limit=limit
			)
			
			return history
			
		except Exception as e:
			frappe.log_error(f"Error getting conversation history: {str(e)}", "Omnichannel Message")
			return []
	
	def get_sentiment_analysis(self):
		"""Get sentiment analysis from metadata"""
		try:
			if self.metadata:
				metadata = json.loads(self.metadata) if isinstance(self.metadata, str) else self.metadata
				return metadata.get("sentiment_analysis", {})
		except:
			pass
		return {}
	
	def add_metadata(self, key, value):
		"""Add metadata to the message"""
		try:
			metadata = {}
			if self.metadata:
				metadata = json.loads(self.metadata) if isinstance(self.metadata, str) else self.metadata
			
			metadata[key] = value
			self.metadata = json.dumps(metadata)
			
		except Exception as e:
			frappe.log_error(f"Error adding metadata: {str(e)}", "Omnichannel Message")
