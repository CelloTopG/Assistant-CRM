# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, get_datetime, time_diff_in_seconds


class AgentDashboard(Document):
	"""Agent Dashboard DocType for managing agent availability and performance"""
	
	def validate(self):
		"""Validate agent dashboard settings"""
		self.validate_working_hours()
		self.validate_concurrent_chats()
		self.validate_channels()
	
	def validate_working_hours(self):
		"""Validate working hours are logical"""
		if self.working_hours_start and self.working_hours_end:
			if self.working_hours_start >= self.working_hours_end:
				frappe.throw("Working hours start time must be before end time")
	
	def validate_concurrent_chats(self):
		"""Validate concurrent chat limits"""
		if self.max_concurrent_chats and self.max_concurrent_chats < 1:
			frappe.throw("Maximum concurrent chats must be at least 1")
		
		if self.max_concurrent_chats and self.max_concurrent_chats > 50:
			frappe.throw("Maximum concurrent chats cannot exceed 50")
	
	def validate_channels(self):
		"""Validate available channels"""
		if self.available_channels:
			valid_channels = ["Website Chat", "WhatsApp", "Facebook", "Instagram", "Telegram", "USSD", "Phone"]
			channels = [ch.strip() for ch in self.available_channels.split(",")]
			
			for channel in channels:
				if channel not in valid_channels:
					frappe.throw(f"Invalid channel: {channel}")
	
	def update_activity(self):
		"""Update last activity timestamp"""
		self.last_activity = now()
		self.save(ignore_permissions=True)
	
	def is_available(self):
		"""Check if agent is available for new assignments"""
		if self.status != "Available":
			return False
		
		if not self.auto_assignment_enabled:
			return False
		
		if self.current_active_chats >= self.max_concurrent_chats:
			return False
		
		# Check working hours
		if not self.is_within_working_hours():
			return False
		
		return True
	
	def is_within_working_hours(self):
		"""Check if current time is within agent's working hours"""
		try:
			from frappe.utils import now_datetime, get_time
			
			current_time = get_time(now_datetime())
			
			if self.working_hours_start and self.working_hours_end:
				start_time = get_time(self.working_hours_start)
				end_time = get_time(self.working_hours_end)
				
				return start_time <= current_time <= end_time
			
			return True  # No working hours restriction
			
		except Exception:
			return True  # Default to available if check fails
	
	def can_handle_channel(self, channel_type):
		"""Check if agent can handle specific channel type"""
		if not self.available_channels:
			return True  # No restriction
		
		available_channels = [ch.strip() for ch in self.available_channels.split(",")]
		return channel_type in available_channels
	
	def assign_message(self, message_id):
		"""Assign a message to this agent"""
		try:
			if not self.is_available():
				return {"success": False, "error": "Agent is not available"}
			
			# Update current active chats
			self.current_active_chats += 1
			self.update_activity()
			
			# Update message with agent assignment
			message_doc = frappe.get_doc("Omnichannel Message", message_id)
			message_doc.agent_assigned = self.agent_user
			message_doc.escalated_to_agent = 1
			message_doc.escalated_at = now()
			message_doc.save()
			
			return {"success": True, "agent": self.agent_user}
			
		except Exception as e:
			frappe.log_error(f"Error assigning message to agent: {str(e)}", "Agent Dashboard")
			return {"success": False, "error": str(e)}
	
	def complete_message(self, message_id, response_time=None):
		"""Mark a message as completed by this agent"""
		try:
			# Decrease active chats count
			if self.current_active_chats > 0:
				self.current_active_chats -= 1
			
			# Update performance metrics
			self.total_messages_handled += 1
			
			if response_time:
				# Update average response time
				if self.average_response_time:
					self.average_response_time = (
						(self.average_response_time * (self.total_messages_handled - 1) + response_time) 
						/ self.total_messages_handled
					)
				else:
					self.average_response_time = response_time
			
			self.update_activity()
			
		except Exception as e:
			frappe.log_error(f"Error completing message for agent: {str(e)}", "Agent Dashboard")
	
	def update_satisfaction_score(self, new_score):
		"""Update customer satisfaction score"""
		try:
			if self.customer_satisfaction_score:
				# Calculate weighted average
				total_weight = self.total_messages_handled
				current_weight = total_weight - 1
				
				self.customer_satisfaction_score = (
					(self.customer_satisfaction_score * current_weight + new_score) / total_weight
				)
			else:
				self.customer_satisfaction_score = new_score
			
			self.save(ignore_permissions=True)
			
		except Exception as e:
			frappe.log_error(f"Error updating satisfaction score: {str(e)}", "Agent Dashboard")
	
	@staticmethod
	def sync_unified_inbox_load_for_agent(agent_user: str) -> int:
		"""Sync ``current_active_chats`` from Unified Inbox conversations.

		This keeps the Agent Dashboard load metric in line with the real number
		of open Unified Inbox conversations so that auto-assignment can make
		fair decisions across agents.
		"""
		if not agent_user:
			return 0
		try:
			active_count = frappe.db.count(
				"Unified Inbox Conversation",
				{
					"assigned_agent": agent_user,
					"status": ["not in", ["Resolved", "Closed"]],
				},
			)
			dashboard_name = frappe.db.get_value(
				"Agent Dashboard", {"agent_user": agent_user}, "name"
			)
			if dashboard_name:
				frappe.db.set_value(
					"Agent Dashboard",
					dashboard_name,
					{
						"current_active_chats": active_count,
						"last_activity": now(),
					},
				)
			return active_count
		except Exception as e:
			frappe.log_error(
				f"Error syncing Unified Inbox load for agent {agent_user}: {str(e)}",
				"Agent Dashboard",
			)
			return 0
	
	@staticmethod
	def get_available_agents(channel_type=None, limit=10, routing_branch=None):
		"""Get list of available agents for assignment.

		Optional ``routing_branch`` allows separating agents into logical pools
		(e.g. "Unified Inbox" vs "Omnichannel"). Agents with
		``routing_branch`` set to "Both" or left empty are eligible for all
		branches for backward compatibility.
		"""
		try:
			filters = {
				"status": "Available",
				"auto_assignment_enabled": 1,
			}
			
			agents = frappe.get_all(
				"Agent Dashboard",
				filters=filters,
				fields=[
					"name",
					"agent_user",
					"agent_name",
					"current_active_chats",
					"max_concurrent_chats",
					"available_channels",
					"routing_branch",
				],
				order_by="current_active_chats asc, last_activity desc",
				limit=limit,
			)
			
			available_agents = []
			for agent in agents:
				agent_doc = frappe.get_doc("Agent Dashboard", agent.name)
				
				# If a routing branch is specified, ensure the agent belongs to it
				# or is configured as a generic ("Both" / empty) agent.
				if routing_branch:
					agent_branch = getattr(agent_doc, "routing_branch", None)
					if agent_branch not in (routing_branch, "Both", "", None):
						continue
				
				# Keep current_active_chats in sync with Unified Inbox so routing
				# decisions are based on real workload, not stale counters.
				AgentDashboard.sync_unified_inbox_load_for_agent(agent_doc.agent_user)
				# Refresh the in-memory value after sync
				agent_doc.reload()
				
				# Check if agent can handle the channel
				if channel_type and not agent_doc.can_handle_channel(channel_type):
					continue
				
				# Check if agent is truly available
				if agent_doc.is_available():
					available_agents.append(agent_doc)
			
			return available_agents
		
		except Exception as e:
			frappe.log_error(f"Error getting available agents: {str(e)}", "Agent Dashboard")
			return []
		
		@staticmethod
		def auto_assign_conversation(message_id, routing_branch=None):
			"""Auto-assign conversation to best available agent"""
			try:
				message_doc = frappe.get_doc("Omnichannel Message", message_id)
				available_agents = AgentDashboard.get_available_agents(
					message_doc.channel_type,
					routing_branch=routing_branch,
				)
				
				if not available_agents:
					return {"success": False, "error": "No agents available"}
				
				# Select best agent (least busy)
				best_agent = available_agents[0]
				result = best_agent.assign_message(message_id)
				
				if result.get("success"):
					return {
						"success": True,
						"agent": best_agent.agent_user,
						"agent_name": best_agent.agent_name
					}
				else:
					return result
						
			except Exception as e:
				frappe.log_error(f"Error in auto-assignment: {str(e)}", "Agent Dashboard")
				return {"success": False, "error": str(e)}
