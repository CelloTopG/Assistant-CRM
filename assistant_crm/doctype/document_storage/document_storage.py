# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DocumentStorage(Document):
	"""Document Storage DocType for WCFCB Assistant CRM"""
	
	def validate(self):
		"""Validate document storage data"""
		if not self.storage_id:
			self.storage_id = self.generate_storage_id()
		
		if not self.storage_date:
			self.storage_date = frappe.utils.now()
		
		if not self.stored_by:
			self.stored_by = frappe.session.user
	
	def generate_storage_id(self):
		"""Generate unique storage ID"""
		import random
		import string
		
		# Generate storage ID format: STR-YYYY-XXXXXX
		year = frappe.utils.nowdate()[:4]
		random_part = ''.join(random.choices(string.digits, k=6))
		return f"STR-{year}-{random_part}"


@frappe.whitelist()
def store_document(file_id, metadata):
	"""Store a document securely"""
	try:
		# Create storage record
		storage = frappe.new_doc('Document Storage')
		storage.file_id = file_id
		storage.access_level = metadata.get('access_level', 'Internal')
		storage.storage_status = "Stored"
		storage.encryption_enabled = 1
		storage.storage_tier = "Hot"
		storage.audit_enabled = 1
		storage.version = "1.0"
		storage.backup_status = "Completed"
		storage.insert()
		
		return {
			'success': True,
			'storage_id': storage.storage_id,
			'status': storage.storage_status
		}
		
	except Exception as e:
		return {'error': str(e)}


@frappe.whitelist()
def retrieve_document(storage_id):
	"""Retrieve a document from storage"""
	try:
		storage = frappe.get_doc('Document Storage', {'storage_id': storage_id})
		
		# Update access statistics
		storage.access_count = (storage.access_count or 0) + 1
		storage.last_accessed = frappe.utils.now()
		storage.save()
		
		return {
			'success': True,
			'storage_id': storage.storage_id,
			'file_id': storage.file_id,
			'access_level': storage.access_level
		}
	except frappe.DoesNotExistError:
		return {'error': 'Document not found in storage'}
