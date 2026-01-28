# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class FailedQueryLog(Document):
	def validate(self):
		"""Validate failed query data before saving"""
		self.validate_confidence_score()
		self.validate_priority_score()
	
	def validate_confidence_score(self):
		"""Validate confidence score is between 0 and 1"""
		if self.confidence_score is not None:
			if self.confidence_score < 0 or self.confidence_score > 1:
				frappe.throw("Confidence score must be between 0 and 1")
	
	def validate_priority_score(self):
		"""Validate priority score is between 0 and 100"""
		if self.priority_score is not None:
			if self.priority_score < 0 or self.priority_score > 100:
				frappe.throw("Priority score must be between 0 and 100")
	
	def after_insert(self):
		"""Process failed query after insertion"""
		self.trigger_failure_analysis()
	
	def trigger_failure_analysis(self):
		"""Trigger failure analysis for this query"""
		try:
			# Import and run failure analysis
			from assistant_crm.api.failure_analysis import analyze_failure_patterns
			analyze_failure_patterns(self.name)
		except Exception as e:
			frappe.log_error(f"Failure analysis error: {str(e)}", "Failure Analysis")
