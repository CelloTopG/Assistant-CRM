# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import re
import json


class MarkdownFormatter:
	"""Service for formatting responses with proper markdown"""
	
	def __init__(self):
		self.user = frappe.session.user
	
	def format_employee_data(self, employee_data, query_type="general"):
		"""Format employee data response with markdown"""
		try:
			data = employee_data.get("data", {})
			employee_name = data.get("employee_name", "Unknown Employee")
			employee_id = data.get("employee_id", "N/A")
			
			if query_type == "employee_id":
				return f"**{employee_name}**'s Employee ID is: **{employee_id}**"
			
			elif query_type == "position":
				designation = data.get("designation", "N/A")
				department = data.get("department", "N/A")
				return f"**{employee_name}** holds the position of **{designation}** in the **{department}** department."
			
			elif query_type == "department":
				department = data.get("department", "N/A")
				branch = data.get("branch", "N/A")
				return f"**{employee_name}** works in:\n- **Department:** {department}\n- **Branch:** {branch}"
			
			elif query_type == "contact":
				contact_info = []
				if data.get("cell_number"):
					contact_info.append(f"- **Phone:** {data['cell_number']}")
				if data.get("company_email"):
					contact_info.append(f"- **Company Email:** {data['company_email']}")
				if data.get("personal_email"):
					contact_info.append(f"- **Personal Email:** {data['personal_email']}")
				
				if contact_info:
					return f"**{employee_name}**'s contact information:\n" + "\n".join(contact_info)
				else:
					return f"No contact information available for **{employee_name}**."
			
			elif query_type == "manager":
				manager = data.get("reports_to", "N/A")
				return f"**{employee_name}** reports to: **{manager}**"
			
			elif query_type == "joining_date":
				joining_date = data.get("date_of_joining", "N/A")
				return f"**{employee_name}** joined on: **{joining_date}**"
			
			else:  # general - comprehensive employee profile
				response = f"# 👤 Employee Profile\n\n"

				# Header section with key info
				response += f"## {employee_name}\n\n"
				designation = data.get('designation', 'Position Not Specified')
				department = data.get('department', 'Department Not Specified')
				response += f"**{designation}** | **{department}**\n\n"

				# Quick stats section with enhanced formatting
				response += f"### 📊 Quick Overview\n\n"
				response += f"| Attribute | Value |\n"
				response += f"|-----------|-------|\n"
				response += f"| 🆔 **Employee ID** | `{employee_id}` |\n"

				if data.get("designation"):
					response += f"| 💼 **Position** | {data['designation']} |\n"
				if data.get("department"):
					response += f"| 🏢 **Department** | {data['department']} |\n"
				if data.get("branch"):
					response += f"| 🌍 **Branch** | {data['branch']} |\n"
				if data.get("status"):
					status_emoji = "✅" if data['status'] == "Active" else "⚠️"
					response += f"| {status_emoji} **Status** | {data['status']} |\n"
				if data.get("date_of_joining"):
					response += f"| 📅 **Joined** | {data['date_of_joining']} |\n"

				response += "\n"

				# Contact section if available
				contact_items = []
				if data.get('company_email'):
					contact_items.append(f"📧 **Email**: {data['company_email']}")
				if data.get('cell_number'):
					contact_items.append(f"📱 **Phone**: {data['cell_number']}")

				if contact_items:
					response += f"### 📞 Contact Information\n\n"
					response += "\n".join(contact_items) + "\n\n"

				# Reporting structure if available
				if data.get('reports_to'):
					response += f"### 👥 Reporting Structure\n\n"
					response += f"**Reports to**: {data['reports_to']}\n\n"

				# Quick actions section
				response += f"### 🔗 Quick Actions\n\n"
				response += f"- View full employee profile in HR module\n"
				response += f"- Check department team members\n"
				response += f"- Access employee documents\n"

				return response
			
		except Exception as e:
			frappe.log_error(f"Error formatting employee data: {str(e)}", "Markdown Formatter")
			return "Error formatting employee information."
	
	def format_budget_data(self, budget_data, query_type="summary"):
		"""Format budget data response with markdown"""
		try:
			data = budget_data.get("data", [])
			
			if not data:
				return "No budget data found matching your criteria."
			
			if query_type == "amount":
				response = "## Budget Allocations\n\n"
				for budget in data:
					response += f"### {budget.get('budget_name', 'Unknown Budget')}\n"
					response += f"- **Cost Center:** {budget.get('cost_center', 'N/A')}\n"
					response += f"- **Fiscal Year:** {budget.get('fiscal_year', 'N/A')}\n"
					response += f"- **Total Budget:** **${budget.get('total_budget', 0):,.2f}**\n\n"
				
				return response
			
			elif query_type == "utilization":
				response = "## Budget Utilization\n\n"
				for budget in data:
					utilization = budget.get('utilization_percent', 0)
					status_emoji = "🟢" if utilization < 75 else "🟡" if utilization < 90 else "🔴"
					
					response += f"### {status_emoji} {budget.get('budget_name', 'Unknown Budget')}\n"
					response += f"- **Utilization:** **{utilization:.1f}%**\n"
					response += f"- **Amount Spent:** ${budget.get('total_actual', 0):,.2f}\n"
					response += f"- **Cost Center:** {budget.get('cost_center', 'N/A')}\n\n"
				
				return response
			
			elif query_type == "remaining":
				response = "## Remaining Budget\n\n"
				for budget in data:
					remaining = budget.get('remaining_budget', 0)
					total = budget.get('total_budget', 0)
					percentage = (remaining / total * 100) if total > 0 else 0
					
					response += f"### {budget.get('budget_name', 'Unknown Budget')}\n"
					response += f"- **Remaining:** **${remaining:,.2f}** ({percentage:.1f}% of total)\n"
					response += f"- **Total Budget:** ${total:,.2f}\n"
					response += f"- **Cost Center:** {budget.get('cost_center', 'N/A')}\n\n"
				
				return response
			
			else:  # summary
				response = "# 💰 Budget Summary Dashboard\n\n"

				# Calculate totals for overview
				total_budget = sum(budget.get('total_budget', 0) for budget in data)
				total_actual = sum(budget.get('total_actual', 0) for budget in data)
				avg_utilization = sum(budget.get('utilization_percent', 0) for budget in data) / len(data) if data else 0

				# Add overview section
				response += "## 📊 Overview\n\n"
				response += f"| Metric | Value |\n"
				response += f"|--------|-------|\n"
				response += f"| **Total Budget** | ${total_budget:,.2f} |\n"
				response += f"| **Total Spent** | ${total_actual:,.2f} |\n"
				response += f"| **Average Utilization** | {avg_utilization:.1f}% |\n"
				response += f"| **Budget Items** | {len(data)} |\n\n"

				# Enhanced budget breakdown with visual indicators
				response += "## 📋 Budget Breakdown\n\n"
				response += "| Budget | Cost Center | Total | Spent | Remaining | Utilization | Status |\n"
				response += "|--------|-------------|-------|-------|-----------|-------------|--------|\n"

				for budget in data:
					budget_name = budget.get('budget_name', 'Unknown Budget')
					cost_center = budget.get('cost_center', 'N/A')
					total = budget.get('total_budget', 0)
					spent = budget.get('total_actual', 0)
					remaining = budget.get('remaining_budget', 0)
					utilization = budget.get('utilization_percent', 0)

					# Status indicator
					if utilization >= 100:
						status = "🔴 Over"
					elif utilization >= 80:
						status = "🟡 High"
					elif utilization >= 50:
						status = "🟢 Good"
					else:
						status = "🔵 Low"

					response += f"| **{budget_name}** | {cost_center} | ${total:,.2f} | ${spent:,.2f} | ${remaining:,.2f} | **{utilization:.1f}%** | {status} |\n"

				# Add utilization chart
				response += "\n## 📈 Utilization Chart\n\n"
				for budget in data:
					budget_name = budget.get('budget_name', 'Unknown Budget')
					utilization = budget.get('utilization_percent', 0)

					# Create visual progress bar
					filled_blocks = int(utilization / 10)
					empty_blocks = 10 - filled_blocks
					progress_bar = "█" * filled_blocks + "░" * empty_blocks

					response += f"**{budget_name}**: {progress_bar} {utilization:.1f}%\n"

				response += "\n"
				return response
			
		except Exception as e:
			frappe.log_error(f"Error formatting budget data: {str(e)}", "Markdown Formatter")
			return "Error formatting budget information."
	
	def format_project_data(self, project_data, query_type="general"):
		"""Format project data response with markdown"""
		try:
			data = project_data.get("data", {})
			project_name = data.get("project_name", "Unknown Project")
			project_id = data.get("project_id", "N/A")
			
			if query_type == "status":
				status = data.get("status", "N/A")
				progress = data.get("percent_complete", 0)
				status_emoji = "🟢" if status == "Open" else "🔴" if status == "Cancelled" else "🟡"
				
				return f"**{project_name}** ({project_id})\n\n{status_emoji} **Status:** {status}\n📊 **Progress:** {progress}% complete"
			
			elif query_type == "progress":
				progress = data.get("percent_complete", 0)
				status = data.get("status", "N/A")
				
				progress_bar = self._create_progress_bar(progress)
				return f"**{project_name}** Progress:\n\n{progress_bar}\n\n**{progress}%** complete | Status: **{status}**"
			
			elif query_type == "timeline":
				response = f"## {project_name} Timeline\n\n"
				response += f"| Date Type | Date |\n"
				response += f"|-----------|------|\n"
				
				if data.get("expected_start_date"):
					response += f"| **Expected Start** | {data['expected_start_date']} |\n"
				if data.get("expected_end_date"):
					response += f"| **Expected End** | {data['expected_end_date']} |\n"
				if data.get("actual_start_date"):
					response += f"| **Actual Start** | {data['actual_start_date']} |\n"
				if data.get("actual_end_date"):
					response += f"| **Actual End** | {data['actual_end_date']} |\n"
				
				return response
			
			else:  # general
				response = f"## Project Information: {project_name}\n\n"
				response += f"| Field | Value |\n"
				response += f"|-------|-------|\n"
				response += f"| **Project ID** | {project_id} |\n"
				
				if data.get("status"):
					response += f"| **Status** | {data['status']} |\n"
				if data.get("percent_complete") is not None:
					response += f"| **Progress** | {data['percent_complete']}% |\n"
				if data.get("project_type"):
					response += f"| **Type** | {data['project_type']} |\n"
				if data.get("department"):
					response += f"| **Department** | {data['department']} |\n"
				if data.get("expected_start_date"):
					response += f"| **Expected Start** | {data['expected_start_date']} |\n"
				if data.get("expected_end_date"):
					response += f"| **Expected End** | {data['expected_end_date']} |\n"
				
				return response
			
		except Exception as e:
			frappe.log_error(f"Error formatting project data: {str(e)}", "Markdown Formatter")
			return "Error formatting project information."
	
	def format_error_response(self, error_message, suggestions=None):
		"""Format error response with helpful suggestions"""
		response = f"❌ **Error:** {error_message}\n\n"
		
		if suggestions:
			response += "💡 **Suggestions:**\n"
			for i, suggestion in enumerate(suggestions, 1):
				response += f"{i}. {suggestion}\n"
		
		return response
	
	def format_instruction_response(self, title, steps, additional_info=None):
		"""Format instructional response with clear steps"""
		response = f"## {title}\n\n"
		
		if steps:
			response += "**Steps:**\n"
			for i, step in enumerate(steps, 1):
				response += f"{i}. {step}\n"
			response += "\n"
		
		if additional_info:
			response += f"💡 **Additional Information:**\n{additional_info}\n"
		
		return response
	
	def format_list_data(self, title, items, item_formatter=None):
		"""Format list data with proper markdown"""
		if not items:
			return f"No {title.lower()} found."
		
		response = f"## {title}\n\n"
		
		for item in items:
			if item_formatter:
				response += f"- {item_formatter(item)}\n"
			else:
				response += f"- {item}\n"
		
		return response
	
	def format_table_data(self, title, headers, rows):
		"""Format tabular data with markdown table"""
		if not rows:
			return f"No {title.lower()} found."
		
		response = f"## {title}\n\n"
		
		# Create table header
		response += "| " + " | ".join(headers) + " |\n"
		response += "|" + "|".join(["-------"] * len(headers)) + "|\n"
		
		# Add rows
		for row in rows:
			response += "| " + " | ".join(str(cell) for cell in row) + " |\n"
		
		return response
	
	def _create_progress_bar(self, percentage):
		"""Create a visual progress bar using Unicode characters"""
		filled_blocks = int(percentage / 10)
		empty_blocks = 10 - filled_blocks
		
		progress_bar = "█" * filled_blocks + "░" * empty_blocks
		return f"[{progress_bar}]"
	
	def format_mixed_response(self, data_response, instruction_response):
		"""Format response that includes both data and instructions"""
		response = data_response + "\n\n---\n\n"
		response += "💡 **Need more help?**\n\n" + instruction_response
		return response
	
	def format_financial_summary(self, financial_data):
		"""Format financial data summary with proper markdown"""
		try:
			if not financial_data:
				return "No financial data available."
			
			response = "## 💰 Financial Summary\n\n"
			
			# KPIs section
			if financial_data.get("kpis"):
				kpis = financial_data["kpis"]
				response += "### Key Performance Indicators\n\n"
				response += f"| Metric | Value |\n"
				response += f"|--------|-------|\n"
				response += f"| **Total Budget** | ${kpis.get('total_budget_amount', 0):,.2f} |\n"
				response += f"| **Total Spent** | ${kpis.get('total_actual_spending', 0):,.2f} |\n"
				response += f"| **Utilization** | {kpis.get('overall_utilization_percent', 0):.1f}% |\n"
				response += f"| **Budget Lines** | {kpis.get('total_budget_lines', 0)} |\n\n"
			
			# Alerts section
			if financial_data.get("alerts"):
				alerts = financial_data["alerts"]
				response += "### 🚨 Budget Alerts\n\n"
				for alert in alerts[:5]:  # Show top 5 alerts
					alert_type = alert.get("type", "info")
					emoji = "🔴" if alert_type == "critical" else "🟡" if alert_type == "warning" else "🔵"
					response += f"{emoji} **{alert.get('account', 'Unknown')}:** {alert.get('message', 'No details')}\n"
				response += "\n"
			
			# Insights section
			if financial_data.get("insights"):
				insights = financial_data["insights"]
				response += "### 💡 Insights\n\n"
				for insight in insights[:3]:  # Show top 3 insights
					priority = insight.get("priority", "low")
					emoji = "🔥" if priority == "high" else "⚠️" if priority == "medium" else "💡"
					response += f"{emoji} **{insight.get('title', 'Insight')}:** {insight.get('message', 'No details')}\n"
			
			return response
			
		except Exception as e:
			frappe.log_error(f"Error formatting financial summary: {str(e)}", "Markdown Formatter")
			return "Error formatting financial summary."
