# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ClaimsTracking(Document):
	"""Claims Tracking DocType for WCFCB Assistant CRM"""
	
	def validate(self):
		"""Validate claims tracking data"""
		if not self.claim_id:
			self.claim_id = self.generate_claim_id()
		
		if not self.last_updated:
			self.last_updated = frappe.utils.now()
	
	def generate_claim_id(self):
		"""Generate unique claim ID"""
		import random
		import string
		
		# Generate claim ID format: CLM-YYYY-XXXXXX
		year = frappe.utils.nowdate()[:4]
		random_part = ''.join(random.choices(string.digits, k=6))
		return f"CLM-{year}-{random_part}"
	
	def get_claim_status_details(self):
		"""Get detailed claim status information"""
		return {
			'claim_id': self.claim_id,
			'status': self.status,
			'current_stage': self.current_stage,
			'next_action': self.next_action,
			'estimated_completion': self.estimated_completion,
			'last_updated': self.last_updated
		}
	
	def update_claim_status(self, new_status, notes=None):
		"""Update claim status with notes"""
		old_status = self.status
		self.status = new_status
		self.last_updated = frappe.utils.now()
		
		if notes:
			current_notes = self.notes or ""
			timestamp = frappe.utils.now()
			new_note = f"\n[{timestamp}] Status changed from '{old_status}' to '{new_status}': {notes}"
			self.notes = current_notes + new_note
		
		self.save()
		
		# Log the status change
		frappe.log_error(
			f"Claim {self.claim_id} status updated from {old_status} to {new_status}",
			"Claims Tracking Status Update"
		)
	
	def get_timeline_data(self):
		"""Get timeline data for the claim"""
		timeline_events = []
		
		# Parse notes for timeline events
		if self.notes:
			lines = self.notes.split('\n')
			for line in lines:
				if line.strip().startswith('['):
					timeline_events.append(line.strip())
		
		return timeline_events
	
	@frappe.whitelist()
	def get_claim_documents(self):
		"""Get documents associated with this claim"""
		# This would integrate with document management system
		return {
			'required_documents': self.documents_required,
			'submitted_documents': [],  # Would be populated from document system
			'pending_documents': []     # Would be calculated
		}


@frappe.whitelist()
def get_claims_for_user(user=None):
	"""Get claims for a specific user"""
	if not user:
		user = frappe.session.user
	
	# Get user roles to determine access
	user_roles = frappe.get_roles(user)
	
	filters = {}
	
	# Filter based on user role
	if 'Beneficiary' in user_roles:
		filters['beneficiary'] = user
	elif 'Employer' in user_roles:
		filters['employer'] = user
	# WCFCB Staff and System Manager can see all claims
	
	claims = frappe.get_all(
		'Claims Tracking',
		filters=filters,
		fields=['name', 'claim_id', 'claim_type', 'status', 'submission_date', 'last_updated'],
		order_by='last_updated desc'
	)
	
	return claims


@frappe.whitelist()
def get_claim_status(claim_id):
	"""Get status of a specific claim"""
	try:
		claim = frappe.get_doc('Claims Tracking', {'claim_id': claim_id})
		return claim.get_claim_status_details()
	except frappe.DoesNotExistError:
		return {'error': 'Claim not found'}


@frappe.whitelist()
def update_claim_status(claim_id, new_status, notes=None):
	"""Update claim status"""
	try:
		claim = frappe.get_doc('Claims Tracking', {'claim_id': claim_id})
		claim.update_claim_status(new_status, notes)
		return {'success': True, 'message': 'Claim status updated successfully'}
	except frappe.DoesNotExistError:
		return {'error': 'Claim not found'}
	except Exception as e:
		return {'error': str(e)}
