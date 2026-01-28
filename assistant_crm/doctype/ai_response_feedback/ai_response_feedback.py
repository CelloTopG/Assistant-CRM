# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AIResponseFeedback(Document):
	def validate(self):
		"""Validate feedback data before saving"""
		self.validate_feedback_rating()
		self.validate_confidence_score()
		self.validate_response_time()
	
	def validate_feedback_rating(self):
		"""Validate feedback rating is in allowed values"""
		if self.feedback_rating and self.feedback_rating not in ['yes', 'no', 'partially']:
			frappe.throw("Feedback rating must be 'yes', 'no', or 'partially'")
	
	def validate_confidence_score(self):
		"""Validate confidence score is between 0 and 1"""
		if self.confidence_score is not None:
			if self.confidence_score < 0 or self.confidence_score > 1:
				frappe.throw("Confidence score must be between 0 and 1")
	
	def validate_response_time(self):
		"""Validate response time is positive"""
		if self.response_time is not None and self.response_time < 0:
			frappe.throw("Response time must be positive")
	
	def after_insert(self):
		"""Process feedback after insertion"""
		self.trigger_learning_analysis()
	
	def trigger_learning_analysis(self):
		"""Trigger learning analysis for this feedback"""
		try:
			# Import and run feedback analysis
			from assistant_crm.api.feedback_aggregation import analyze_feedback_for_learning
			analyze_feedback_for_learning(self.name)
		except Exception as e:
			frappe.log_error(f"Feedback analysis error: {str(e)}", "Feedback Analysis")
