# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class KnowledgeGapAnalysis(Document):
	def validate(self):
		"""Validate knowledge gap data before saving"""
		self.validate_scores()
		self.calculate_overall_priority()
	
	def validate_scores(self):
		"""Validate that all scores are between 0 and 100"""
		score_fields = ['impact_score', 'frequency_score', 'urgency_score', 'overall_priority_score', 'effectiveness_rating']
		
		for field in score_fields:
			value = getattr(self, field, None)
			if value is not None:
				if value < 0 or value > 100:
					frappe.throw(f"{self.meta.get_label(field)} must be between 0 and 100")
	
	def calculate_overall_priority(self):
		"""Calculate overall priority score from component scores"""
		if self.impact_score is not None and self.frequency_score is not None and self.urgency_score is not None:
			self.overall_priority_score = (self.impact_score + self.frequency_score + self.urgency_score) / 3
	
	def after_insert(self):
		"""Process knowledge gap after insertion"""
		self.trigger_gap_analysis()
	
	def trigger_gap_analysis(self):
		"""Trigger knowledge gap analysis workflows"""
		try:
			# Import and run gap analysis
			from assistant_crm.api.automated_kb_updates import trigger_automated_kb_update
			trigger_automated_kb_update(self.name)
		except Exception as e:
			frappe.log_error(f"Knowledge gap analysis error: {str(e)}", "Knowledge Gap Analysis")
