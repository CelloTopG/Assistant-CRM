# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
from frappe.utils import now, get_datetime, add_days, cstr
from frappe.contacts.doctype.contact.contact import get_contact_details


class CRMIntegrationService:
	"""CRM Integration service for WCFCB Assistant CRM"""
	
	def __init__(self):
		self.customer_cache = {}
	
	def get_or_create_customer(self, channel_type, channel_id, sender_info=None):
		"""Get existing customer or create new one"""
		try:
			# Try to find existing customer by channel
			existing_customer = self._find_customer_by_channel(channel_type, channel_id)
			if existing_customer:
				return existing_customer
			
			# Create new customer
			return self._create_customer_from_channel(channel_type, channel_id, sender_info)
			
		except Exception as e:
			frappe.log_error(f"Error in get_or_create_customer: {str(e)}", "CRM Integration Service")
			return None
	
	def _find_customer_by_channel(self, channel_type, channel_id):
		"""Find customer by channel information"""
		try:
			# Check customer communication records
			communications = frappe.get_all(
				"Communication",
				filters={
					"communication_medium": channel_type,
					"phone_no": channel_id if channel_type in ["WhatsApp", "Phone Call"] else None,
					"sender": channel_id if channel_type not in ["WhatsApp", "Phone Call"] else None
				},
				fields=["reference_doctype", "reference_name"],
				limit=1
			)
			
			if communications and communications[0].reference_doctype == "Customer":
				return communications[0].reference_name
			
			# Check by phone number for WhatsApp
			if channel_type == "WhatsApp":
				contacts = frappe.get_all(
					"Contact Phone",
					filters={"phone": channel_id},
					fields=["parent"],
					limit=1
				)
				
				if contacts:
					contact = frappe.get_doc("Contact", contacts[0].parent)
					if contact.links:
						for link in contact.links:
							if link.link_doctype == "Customer":
								return link.link_name
			
			# Check by email for other channels
			if "@" in channel_id:
				contacts = frappe.get_all(
					"Contact Email",
					filters={"email_id": channel_id},
					fields=["parent"],
					limit=1
				)
				
				if contacts:
					contact = frappe.get_doc("Contact", contacts[0].parent)
					if contact.links:
						for link in contact.links:
							if link.link_doctype == "Customer":
								return link.link_name
			
			return None
			
		except Exception as e:
			frappe.log_error(f"Error finding customer by channel: {str(e)}", "CRM Integration Service")
			return None
	
	def _create_customer_from_channel(self, channel_type, channel_id, sender_info=None):
		"""Create new customer from channel information"""
		try:
			sender_info = sender_info or {}
			
			# Generate customer name
			customer_name = self._generate_customer_name(channel_type, channel_id, sender_info)
			
			# Create customer
			customer_doc = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": customer_name,
				"customer_type": "Individual",
				"customer_group": "WCFCB Clients",
				"territory": "Zambia",
				"language": "en"  # Default, will be updated based on interactions
			})
			
			customer_doc.insert(ignore_permissions=True)
			
			# Create contact
			contact_doc = self._create_contact_for_customer(
				customer_doc.name, 
				channel_type, 
				channel_id, 
				sender_info
			)
			
			# Create initial communication record
			self._create_initial_communication(
				customer_doc.name, 
				channel_type, 
				channel_id, 
				contact_doc.name if contact_doc else None
			)
			
			return customer_doc.name
			
		except Exception as e:
			frappe.log_error(f"Error creating customer: {str(e)}", "CRM Integration Service")
			return None
	
	def _generate_customer_name(self, channel_type, channel_id, sender_info):
		"""Generate customer name from available information"""
		if sender_info.get("name"):
			return sender_info["name"]
		elif sender_info.get("first_name"):
			last_name = sender_info.get("last_name", "")
			return f"{sender_info['first_name']} {last_name}".strip()
		else:
			# Generate name based on channel
			if channel_type == "WhatsApp":
				return f"WhatsApp User {channel_id[-4:]}"
			elif channel_type == "Facebook":
				return f"Facebook User {channel_id[-4:]}"
			elif channel_type == "Telegram":
				username = sender_info.get("username", "")
				return f"Telegram {username}" if username else f"Telegram User {channel_id[-4:]}"
			else:
				return f"{channel_type} User {channel_id[-4:]}"
	
	def _create_contact_for_customer(self, customer_name, channel_type, channel_id, sender_info):
		"""Create contact record for customer"""
		try:
			sender_info = sender_info or {}
			
			contact_doc = frappe.get_doc({
				"doctype": "Contact",
				"first_name": sender_info.get("first_name") or sender_info.get("name") or f"{channel_type} Contact",
				"last_name": sender_info.get("last_name", ""),
				"status": "Open"
			})
			
			# Add customer link
			contact_doc.append("links", {
				"link_doctype": "Customer",
				"link_name": customer_name
			})
			
			# Add phone number for WhatsApp/Phone
			if channel_type in ["WhatsApp", "Phone Call"] and channel_id:
				contact_doc.append("phone_nos", {
					"phone": channel_id,
					"is_primary_phone": 1
				})
			
			# Add email if available
			if "@" in channel_id:
				contact_doc.append("email_ids", {
					"email_id": channel_id,
					"is_primary": 1
				})
			
			contact_doc.insert(ignore_permissions=True)
			return contact_doc
			
		except Exception as e:
			frappe.log_error(f"Error creating contact: {str(e)}", "CRM Integration Service")
			return None
	
	def _create_initial_communication(self, customer_name, channel_type, channel_id, contact_name=None):
		"""Create initial communication record"""
		try:
			comm_doc = frappe.get_doc({
				"doctype": "Communication",
				"communication_type": "Communication",
				"communication_medium": channel_type,
				"sent_or_received": "Received",
				"reference_doctype": "Customer",
				"reference_name": customer_name,
				"subject": f"Initial contact via {channel_type}",
				"content": f"Customer initiated contact via {channel_type}",
				"status": "Open",
				"sender": channel_id,
				"phone_no": channel_id if channel_type in ["WhatsApp", "Phone Call"] else None
			})
			
			if contact_name:
				comm_doc.timeline_links = json.dumps([{
					"link_doctype": "Contact",
					"link_name": contact_name
				}])
			
			comm_doc.insert(ignore_permissions=True)
			return comm_doc
			
		except Exception as e:
			frappe.log_error(f"Error creating communication: {str(e)}", "CRM Integration Service")
			return None
	
	def log_interaction(self, customer_name, message_doc, ai_response=None):
		"""Log customer interaction in CRM"""
		try:
			if not customer_name:
				return
			
			# Create communication record
			comm_doc = frappe.get_doc({
				"doctype": "Communication",
				"communication_type": "Communication",
				"communication_medium": message_doc.channel_type,
				"sent_or_received": "Received" if message_doc.direction == "Inbound" else "Sent",
				"reference_doctype": "Customer",
				"reference_name": customer_name,
				"subject": f"{message_doc.channel_type} conversation",
				"content": message_doc.message_content,
				"status": "Open",
				"sender": message_doc.channel_id,
				"phone_no": message_doc.channel_id if message_doc.channel_type in ["WhatsApp", "Phone Call"] else None,
				"communication_date": message_doc.received_at
			})
			
			# Add AI response if available
			if ai_response:
				comm_doc.content += f"\n\nAI Response: {ai_response}"
			
			comm_doc.insert(ignore_permissions=True)
			
			# Update customer's last interaction
			self._update_customer_last_interaction(customer_name, message_doc)
			
			return comm_doc
			
		except Exception as e:
			frappe.log_error(f"Error logging interaction: {str(e)}", "CRM Integration Service")
			return None
	
	def _update_customer_last_interaction(self, customer_name, message_doc):
		"""Update customer's last interaction details"""
		try:
			customer_doc = frappe.get_doc("Customer", customer_name)
			
			# Update custom fields (these would need to be added to Customer doctype)
			if hasattr(customer_doc, 'last_interaction_date'):
				customer_doc.last_interaction_date = message_doc.received_at
			if hasattr(customer_doc, 'last_interaction_channel'):
				customer_doc.last_interaction_channel = message_doc.channel_type
			if hasattr(customer_doc, 'preferred_language'):
				detected_lang = message_doc.get_detected_language()
				if detected_lang and detected_lang != "en":
					customer_doc.preferred_language = detected_lang
			
			customer_doc.save(ignore_permissions=True)
			
		except Exception as e:
			frappe.log_error(f"Error updating customer interaction: {str(e)}", "CRM Integration Service")
	
	def get_customer_interaction_history(self, customer_name, limit=50):
		"""Get customer interaction history"""
		try:
			# Get communications
			communications = frappe.get_all(
				"Communication",
				filters={
					"reference_doctype": "Customer",
					"reference_name": customer_name
				},
				fields=[
					"name", "communication_medium", "sent_or_received", 
					"subject", "content", "communication_date", "status"
				],
				order_by="communication_date desc",
				limit=limit
			)
			
			# Get omnichannel messages
			messages = frappe.get_all(
				"Omnichannel Message",
				filters={"customer_id": customer_name},
				fields=[
					"name", "channel_type", "direction", "message_content",
					"ai_response", "received_at", "status", "escalated_to_agent"
				],
				order_by="received_at desc",
				limit=limit
			)
			
			# Combine and sort by date
			all_interactions = []
			
			for comm in communications:
				all_interactions.append({
					"type": "communication",
					"date": comm.communication_date,
					"channel": comm.communication_medium,
					"direction": comm.sent_or_received,
					"content": comm.content,
					"status": comm.status,
					"id": comm.name
				})
			
			for msg in messages:
				all_interactions.append({
					"type": "omnichannel_message",
					"date": msg.received_at,
					"channel": msg.channel_type,
					"direction": msg.direction,
					"content": msg.message_content,
					"ai_response": msg.ai_response,
					"status": msg.status,
					"escalated": msg.escalated_to_agent,
					"id": msg.name
				})
			
			# Sort by date descending
			all_interactions.sort(key=lambda x: get_datetime(x["date"]), reverse=True)
			
			return all_interactions[:limit]
			
		except Exception as e:
			frappe.log_error(f"Error getting interaction history: {str(e)}", "CRM Integration Service")
			return []
	
	def get_customer_summary(self, customer_name):
		"""Get customer summary for agent dashboard"""
		try:
			customer_doc = frappe.get_doc("Customer", customer_name)
			
			# Get contact details
			contact_details = get_contact_details(customer_name)
			
			# Get interaction statistics
			total_interactions = frappe.db.count("Communication", {
				"reference_doctype": "Customer",
				"reference_name": customer_name
			})
			
			recent_interactions = frappe.db.count("Communication", {
				"reference_doctype": "Customer",
				"reference_name": customer_name,
				"communication_date": [">=", add_days(now(), -30)]
			})
			
			# Get escalated messages count
			escalated_count = frappe.db.count("Omnichannel Message", {
				"customer_id": customer_name,
				"escalated_to_agent": 1
			})
			
			# Get preferred language
			preferred_language = getattr(customer_doc, 'preferred_language', 'en')
			
			return {
				"customer_name": customer_doc.customer_name,
				"customer_group": customer_doc.customer_group,
				"territory": customer_doc.territory,
				"contact_details": contact_details,
				"total_interactions": total_interactions,
				"recent_interactions": recent_interactions,
				"escalated_count": escalated_count,
				"preferred_language": preferred_language,
				"last_interaction": getattr(customer_doc, 'last_interaction_date', None),
				"last_channel": getattr(customer_doc, 'last_interaction_channel', None),
				"creation_date": customer_doc.creation
			}
			
		except Exception as e:
			frappe.log_error(f"Error getting customer summary: {str(e)}", "CRM Integration Service")
			return {}
	
	def create_opportunity_from_interaction(self, customer_name, message_doc, opportunity_type="WCFCB Service Inquiry"):
		"""Create sales opportunity from customer interaction"""
		try:
			# Check if recent opportunity exists
			existing_opportunity = frappe.get_all(
				"Opportunity",
				filters={
					"party_name": customer_name,
					"opportunity_type": opportunity_type,
					"creation": [">=", add_days(now(), -7)]  # Within last 7 days
				},
				limit=1
			)
			
			if existing_opportunity:
				return existing_opportunity[0].name
			
			# Create new opportunity
			opportunity_doc = frappe.get_doc({
				"doctype": "Opportunity",
				"opportunity_from": "Customer",
				"party_name": customer_name,
				"opportunity_type": opportunity_type,
				"source": message_doc.channel_type,
				"status": "Open",
				"title": f"{opportunity_type} - {message_doc.channel_type}",
				"with_items": 0
			})
			
			# Add notes about the interaction
			opportunity_doc.notes = f"Generated from {message_doc.channel_type} interaction.\n\nCustomer Message: {message_doc.message_content}"
			
			opportunity_doc.insert(ignore_permissions=True)
			
			return opportunity_doc.name
			
		except Exception as e:
			frappe.log_error(f"Error creating opportunity: {str(e)}", "CRM Integration Service")
			return None
	
	def update_customer_language_preference(self, customer_name, detected_language):
		"""Update customer's preferred language"""
		try:
			if not customer_name or not detected_language:
				return
			
			customer_doc = frappe.get_doc("Customer", customer_name)
			
			# Update language if it's different and supported
			supported_languages = ["en", "bem", "ny", "to"]
			if detected_language in supported_languages:
				if hasattr(customer_doc, 'preferred_language'):
					customer_doc.preferred_language = detected_language
				customer_doc.language = detected_language
				customer_doc.save(ignore_permissions=True)
			
		except Exception as e:
			frappe.log_error(f"Error updating language preference: {str(e)}", "CRM Integration Service")
