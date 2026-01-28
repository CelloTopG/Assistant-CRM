# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate


class PaymentStatus(Document):
	"""Payment Status DocType for WCFCB Assistant CRM"""
	
	def validate(self):
		"""Validate payment status data"""
		if not self.payment_id:
			self.payment_id = self.generate_payment_id()
		
		if not self.last_updated:
			self.last_updated = frappe.utils.now()
		
		# Auto-update processing stage based on status
		self.update_processing_stage()
	
	def generate_payment_id(self):
		"""Generate unique payment ID"""
		import random
		import string
		
		# Generate payment ID format: PAY-YYYY-XXXXXX
		year = frappe.utils.nowdate()[:4]
		random_part = ''.join(random.choices(string.digits, k=6))
		return f"PAY-{year}-{random_part}"
	
	def update_processing_stage(self):
		"""Update processing stage based on status"""
		status_to_stage = {
			'Pending': 'Initiated',
			'Processing': 'Processing',
			'Approved': 'Approval',
			'Paid': 'Completed',
			'Failed': 'Completed',
			'Cancelled': 'Completed'
		}
		
		if self.status in status_to_stage:
			self.processing_stage = status_to_stage[self.status]
	
	def get_payment_details(self):
		"""Get detailed payment information"""
		return {
			'payment_id': self.payment_id,
			'payment_type': self.payment_type,
			'status': self.status,
			'amount': self.amount,
			'currency': self.currency,
			'beneficiary': self.beneficiary,
			'payment_date': self.payment_date,
			'processing_stage': self.processing_stage,
			'expected_completion': self.expected_completion,
			'last_updated': self.last_updated
		}
	
	def update_payment_status(self, new_status, notes=None):
		"""Update payment status with notes"""
		old_status = self.status
		self.status = new_status
		self.last_updated = frappe.utils.now()
		
		# Update processing stage
		self.update_processing_stage()
		
		if notes:
			current_history = self.payment_history or ""
			timestamp = frappe.utils.now()
			new_entry = f"\n[{timestamp}] Status changed from '{old_status}' to '{new_status}': {notes}"
			self.payment_history = current_history + new_entry
		
		self.save()
		
		# Log the status change
		frappe.log_error(
			f"Payment {self.payment_id} status updated from {old_status} to {new_status}",
			"Payment Status Update"
		)
	
	def approve_payment(self, approved_by):
		"""Approve payment"""
		self.approval_status = "Approved"
		self.approved_by = approved_by
		self.approved_date = nowdate()
		self.status = "Approved"
		
		# Add to payment history
		current_history = self.payment_history or ""
		timestamp = frappe.utils.now()
		new_entry = f"\n[{timestamp}] Payment approved by {approved_by}"
		self.payment_history = current_history + new_entry
		
		self.save()
	
	def process_payment(self, transaction_id=None, reference_number=None):
		"""Process the payment"""
		self.status = "Processing"
		
		if transaction_id:
			self.transaction_id = transaction_id
		
		if reference_number:
			self.reference_number = reference_number
		
		# Add to payment history
		current_history = self.payment_history or ""
		timestamp = frappe.utils.now()
		new_entry = f"\n[{timestamp}] Payment processing initiated"
		if transaction_id:
			new_entry += f" - Transaction ID: {transaction_id}"
		self.payment_history = current_history + new_entry
		
		self.save()
	
	def complete_payment(self, payment_date=None):
		"""Mark payment as completed"""
		self.status = "Paid"
		self.payment_date = payment_date or nowdate()
		
		# Add to payment history
		current_history = self.payment_history or ""
		timestamp = frappe.utils.now()
		new_entry = f"\n[{timestamp}] Payment completed successfully on {self.payment_date}"
		self.payment_history = current_history + new_entry
		
		self.save()
		
		# Send notification to beneficiary
		self.send_payment_notification()
	
	def send_payment_notification(self):
		"""Send payment notification to beneficiary"""
		# This would integrate with notification system
		return {
			'success': True,
			'message': f'Payment notification sent to {self.beneficiary} for payment {self.payment_id}'
		}


@frappe.whitelist()
def get_payments_for_user(user=None):
	"""Get payments for a specific user"""
	if not user:
		user = frappe.session.user
	
	# Get user roles to determine access
	user_roles = frappe.get_roles(user)
	
	filters = {}
	
	# Filter based on user role
	if 'Beneficiary' in user_roles:
		filters['beneficiary'] = user
	# WCFCB Staff and System Manager can see all payments
	
	payments = frappe.get_all(
		'Payment Status',
		filters=filters,
		fields=['name', 'payment_id', 'payment_type', 'status', 'amount', 'currency', 
		        'payment_date', 'expected_completion', 'last_updated'],
		order_by='last_updated desc'
	)
	
	return payments


@frappe.whitelist()
def get_payment_status(payment_id):
	"""Get status of a specific payment"""
	try:
		payment = frappe.get_doc('Payment Status', {'payment_id': payment_id})
		return payment.get_payment_details()
	except frappe.DoesNotExistError:
		return {'error': 'Payment not found'}


@frappe.whitelist()
def update_payment_status(payment_id, new_status, notes=None):
	"""Update payment status"""
	try:
		payment = frappe.get_doc('Payment Status', {'payment_id': payment_id})
		payment.update_payment_status(new_status, notes)
		return {'success': True, 'message': 'Payment status updated successfully'}
	except frappe.DoesNotExistError:
		return {'error': 'Payment not found'}
	except Exception as e:
		return {'error': str(e)}


@frappe.whitelist()
def approve_payment(payment_id, approved_by):
	"""Approve a payment"""
	try:
		payment = frappe.get_doc('Payment Status', {'payment_id': payment_id})
		payment.approve_payment(approved_by)
		return {'success': True, 'message': 'Payment approved successfully'}
	except frappe.DoesNotExistError:
		return {'error': 'Payment not found'}
	except Exception as e:
		return {'error': str(e)}
