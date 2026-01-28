# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class QueryPatternAnalysis(Document):
	def validate(self):
		"""Validate query pattern data before saving"""
		self.validate_scores()
		self.validate_rates()
	
	def validate_scores(self):
		"""Validate that scores are within valid ranges"""
		score_fields = ['knowledge_gap_score', 'business_impact_score', 'effectiveness_score']
		
		for field in score_fields:
			value = getattr(self, field, None)
			if value is not None:
				if value < 0 or value > 100:
					frappe.throw(f"{self.meta.get_label(field)} must be between 0 and 100")
	
	def validate_rates(self):
		"""Validate that rates are within valid ranges"""
		rate_fields = ['success_rate']
		
		for field in rate_fields:
			value = getattr(self, field, None)
			if value is not None:
				if value < 0 or value > 100:
					frappe.throw(f"{self.meta.get_label(field)} must be between 0 and 100")
		
		# Validate confidence score
		if self.average_confidence is not None:
			if self.average_confidence < 0 or self.average_confidence > 1:
				frappe.throw("Average confidence must be between 0 and 1")
	
	def after_insert(self):
		"""Process pattern analysis after insertion"""
		self.trigger_pattern_analysis()
	
	def trigger_pattern_analysis(self):
		"""Trigger pattern analysis workflows"""
		try:
			# Check if this pattern indicates a trending topic
			if self.trend_direction == "increasing" and self.business_impact_score >= 70:
				self.create_knowledge_gap_if_needed()
		except Exception as e:
			frappe.log_error(f"Pattern analysis error: {str(e)}", "Pattern Analysis")
	
	def create_knowledge_gap_if_needed(self):
		"""Create knowledge gap if pattern indicates need"""
		# Disabled per user request: Knowledge Gap Analysis feature is deprecated.
		frappe.log_error("Knowledge Gap Analysis creation is disabled.", "Pattern Analysis")
		return
