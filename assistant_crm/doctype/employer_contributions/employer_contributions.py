# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, add_months


class EmployerContributions(Document):
	"""Employer Contributions DocType for WCFCB Assistant CRM"""
	
	def validate(self):
		"""Validate employer contributions data"""
		self.calculate_outstanding_amount()
		self.update_compliance_status()
		
		if not self.last_updated:
			self.last_updated = frappe.utils.now()
	
	def calculate_outstanding_amount(self):
		"""Calculate outstanding contribution amount"""
		contribution_amount = flt(self.contribution_amount)
		amount_paid = flt(self.amount_paid)
		self.outstanding_amount = contribution_amount - amount_paid
	
	def update_compliance_status(self):
		"""Update compliance status based on payment status and due dates"""
		if self.status == "Paid":
			self.compliance_status = "Compliant"
		elif self.status == "Overdue":
			self.compliance_status = "Non-Compliant"
		elif self.status == "Exempt":
			self.compliance_status = "Exempt"
		else:
			self.compliance_status = "Under Review"
	
	def get_contribution_summary(self):
		"""Get contribution summary for employer"""
		return {
			'employer_id': self.employer_id,
			'employer_name': self.employer_name,
			'contribution_period': self.contribution_period,
			'status': self.status,
			'contribution_amount': self.contribution_amount,
			'amount_paid': self.amount_paid,
			'outstanding_amount': self.outstanding_amount,
			'due_date': self.due_date,
			'compliance_status': self.compliance_status
		}
	
	def record_payment(self, amount, payment_date=None):
		"""Record a payment for this contribution"""
		if not payment_date:
			payment_date = nowdate()
		
		old_amount_paid = flt(self.amount_paid)
		self.amount_paid = old_amount_paid + flt(amount)
		self.payment_date = payment_date
		
		# Update status based on payment
		if self.amount_paid >= self.contribution_amount:
			self.status = "Paid"
		elif self.amount_paid > 0:
			self.status = "Partial"
		
		# Update payment history
		current_history = self.payment_history or ""
		new_entry = f"\n[{payment_date}] Payment of {amount} recorded. Total paid: {self.amount_paid}"
		self.payment_history = current_history + new_entry
		
		self.save()
		
		# Log the payment
		frappe.log_error(
			f"Payment of {amount} recorded for employer {self.employer_id} - {self.contribution_period}",
			"Employer Contributions Payment"
		)
	
	def send_reminder(self):
		"""Send payment reminder to employer"""
		# This would integrate with notification system
		self.reminder_sent = 1
		self.save()
		
		return {
			'success': True,
			'message': f'Reminder sent to {self.employer_name} for contribution period {self.contribution_period}'
		}
	
	@frappe.whitelist()
	def calculate_penalties(self):
		"""Calculate penalties for overdue contributions"""
		if self.status != "Overdue" or not self.due_date:
			return 0
		
		from datetime import datetime
		due_date = datetime.strptime(str(self.due_date), '%Y-%m-%d')
		current_date = datetime.strptime(nowdate(), '%Y-%m-%d')
		
		days_overdue = (current_date - due_date).days
		
		if days_overdue > 0:
			# Calculate penalty: 1% per month overdue
			months_overdue = days_overdue / 30
			penalty_rate = 0.01 * months_overdue
			penalty_amount = flt(self.outstanding_amount) * penalty_rate
			
			self.penalties = penalty_amount
			self.save()
			
			return penalty_amount
		
		return 0


@frappe.whitelist()
def get_employer_contributions(employer_id=None):
	"""Get contributions for a specific employer"""
	filters = {}
	
	if employer_id:
		filters['employer_id'] = employer_id
	else:
		# Get current user's employer ID if they are an employer
		user_roles = frappe.get_roles()
		if 'Employer' in user_roles:
			# This would be linked to user's employer profile
			filters['employer_id'] = frappe.session.user
	
	contributions = frappe.get_all(
		'Employer Contributions',
		filters=filters,
		fields=['name', 'employer_id', 'employer_name', 'contribution_period', 'status', 
		        'contribution_amount', 'outstanding_amount', 'due_date', 'compliance_status'],
		order_by='due_date desc'
	)
	
	return contributions


@frappe.whitelist()
def get_contribution_status(employer_id, period=None):
	"""Get contribution status for employer and period"""
	filters = {'employer_id': employer_id}
	
	if period:
		filters['contribution_period'] = period
	
	try:
		contributions = frappe.get_all(
			'Employer Contributions',
			filters=filters,
			fields=['*'],
			order_by='contribution_period desc',
			limit=10
		)
		
		return {
			'success': True,
			'contributions': contributions,
			'total_outstanding': sum(flt(c.get('outstanding_amount', 0)) for c in contributions)
		}
	except Exception as e:
		return {'error': str(e)}


@frappe.whitelist()
def record_contribution_payment(contribution_name, amount, payment_date=None):
	"""Record payment for a contribution"""
	try:
		contribution = frappe.get_doc('Employer Contributions', contribution_name)
		contribution.record_payment(amount, payment_date)
		return {'success': True, 'message': 'Payment recorded successfully'}
	except Exception as e:
		return {'error': str(e)}
