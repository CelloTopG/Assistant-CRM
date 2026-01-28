# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class LearningMetrics(Document):
	def validate(self):
		"""Validate learning metrics data before saving"""
		self.validate_metric_value()
		self.validate_quality_score()
		self.calculate_improvement_percentage()
	
	def validate_metric_value(self):
		"""Validate metric value based on unit type"""
		if self.metric_value is not None:
			if self.metric_unit == "percentage" and (self.metric_value < 0 or self.metric_value > 100):
				frappe.throw("Percentage values must be between 0 and 100")
			elif self.metric_unit == "score" and (self.metric_value < 0 or self.metric_value > 100):
				frappe.throw("Score values must be between 0 and 100")
			elif self.metric_unit == "ratio" and self.metric_value < 0:
				frappe.throw("Ratio values must be non-negative")
			elif self.metric_unit == "seconds" and self.metric_value < 0:
				frappe.throw("Time values must be non-negative")
	
	def validate_quality_score(self):
		"""Validate quality score is between 0 and 100"""
		if self.quality_score is not None:
			if self.quality_score < 0 or self.quality_score > 100:
				frappe.throw("Quality score must be between 0 and 100")
	
	def calculate_improvement_percentage(self):
		"""Calculate improvement percentage from baseline"""
		if self.metric_value is not None and self.baseline_value is not None and self.baseline_value != 0:
			self.improvement_percentage = ((self.metric_value - self.baseline_value) / self.baseline_value) * 100
	
	def after_insert(self):
		"""Process metrics after insertion"""
		self.check_for_alerts()
	
	def check_for_alerts(self):
		"""Check if metric requires alerts or actions"""
		try:
			# Check if target is missed significantly
			if self.target_value and self.metric_value:
				deviation = abs(self.metric_value - self.target_value) / self.target_value * 100
				
				if deviation > 20:  # 20% deviation threshold
					self.action_required = 1
					self.save()
					
					# Create alert for significant deviations
					self.create_metric_alert(deviation)
					
		except Exception as e:
			frappe.log_error(f"Metrics alert check error: {str(e)}", "Metrics Alert")
	
	def create_metric_alert(self, deviation):
		"""Create alert for metric deviation"""
		try:
			alert_message = f"Metric '{self.metric_type}' deviates {deviation:.1f}% from target"
			
			# Log the alert
			frappe.log_error(alert_message, "Learning Metrics Alert")
			
			# Could also send email notifications here
			
		except Exception as e:
			frappe.log_error(f"Metric alert creation error: {str(e)}", "Metric Alert Creation")
