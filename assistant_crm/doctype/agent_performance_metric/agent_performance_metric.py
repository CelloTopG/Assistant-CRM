# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AgentPerformanceMetric(Document):
	def validate(self):
		"""Validate agent performance metric data"""
		self.validate_metric_date()
		self.calculate_derived_metrics()
	
	def validate_metric_date(self):
		"""Ensure metric date is not in the future"""
		if self.metric_date and frappe.utils.getdate(self.metric_date) > frappe.utils.today():
			frappe.throw("Metric date cannot be in the future")
	
	def calculate_derived_metrics(self):
		"""Calculate derived metrics from base data"""
		# Calculate utilization rate if active hours is provided
		if self.active_hours:
			# Assuming 8-hour work day
			standard_work_hours = 8
			self.utilization_rate = min(100, (self.active_hours / standard_work_hours) * 100)
		
		# Calculate quality score based on various factors
		self.quality_score = self.calculate_quality_score()
	
	def calculate_quality_score(self):
		"""Calculate overall quality score based on performance metrics"""
		score = 0
		weight_total = 0
		
		# SLA compliance (30% weight)
		if self.sla_compliance_rate is not None:
			score += (self.sla_compliance_rate / 100) * 30
			weight_total += 30
		
		# Customer satisfaction (40% weight)
		if self.customer_satisfaction_score is not None:
			# Assuming CSAT is on a 5-point scale
			normalized_csat = (self.customer_satisfaction_score / 5) * 100
			score += (normalized_csat / 100) * 40
			weight_total += 40
		
		# Response time performance (20% weight)
		if self.average_response_time is not None:
			# Good response time is under 5 minutes
			response_score = max(0, 100 - (self.average_response_time / 5) * 100)
			score += (response_score / 100) * 20
			weight_total += 20
		
		# Escalation resolution rate (10% weight)
		if self.escalations_received and self.escalations_received > 0:
			resolution_rate = (self.escalations_resolved / self.escalations_received) * 100
			score += (resolution_rate / 100) * 10
			weight_total += 10
		
		# Return normalized score
		return (score / weight_total * 100) if weight_total > 0 else 0

	def on_submit(self):
		"""Actions to perform when metric is submitted"""
		self.update_agent_summary()
	
	def update_agent_summary(self):
		"""Update agent's overall performance summary"""
		# This could update a separate Agent Summary doctype
		# or trigger notifications for performance issues
		pass

@frappe.whitelist(allow_guest=False)
def get_agent_performance_summary(agent, start_date=None, end_date=None):
	"""Get performance summary for an agent over a date range"""
	if not start_date:
		start_date = frappe.utils.add_days(frappe.utils.today(), -30)
	if not end_date:
		end_date = frappe.utils.today()
	
	metrics = frappe.db.sql("""
		SELECT 
			AVG(conversations_handled) as avg_conversations,
			AVG(average_response_time) as avg_response_time,
			AVG(average_resolution_time) as avg_resolution_time,
			AVG(sla_compliance_rate) as avg_sla_compliance,
			AVG(customer_satisfaction_score) as avg_csat,
			AVG(quality_score) as avg_quality_score,
			SUM(conversations_handled) as total_conversations,
			COUNT(*) as metric_days
		FROM `tabAgent Performance Metric`
		WHERE agent = %s 
		AND metric_date BETWEEN %s AND %s
	""", (agent, start_date, end_date), as_dict=True)
	
	return metrics[0] if metrics else {}

@frappe.whitelist(allow_guest=False)
def calculate_team_performance(start_date=None, end_date=None):
	"""Calculate team-wide performance metrics"""
	if not start_date:
		start_date = frappe.utils.add_days(frappe.utils.today(), -7)
	if not end_date:
		end_date = frappe.utils.today()
	
	team_metrics = frappe.db.sql("""
		SELECT 
			agent,
			AVG(conversations_handled) as avg_conversations,
			AVG(sla_compliance_rate) as avg_sla_compliance,
			AVG(customer_satisfaction_score) as avg_csat,
			AVG(quality_score) as avg_quality_score
		FROM `tabAgent Performance Metric`
		WHERE metric_date BETWEEN %s AND %s
		GROUP BY agent
		ORDER BY avg_quality_score DESC
	""", (start_date, end_date), as_dict=True)
	
	return team_metrics
