# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import hashlib
import os
from frappe.utils import get_site_path


class DocumentUpload(Document):
	"""Document Upload DocType for WCFCB Assistant CRM"""
	
	def validate(self):
		"""Validate document upload data"""
		if not self.file_id:
			self.file_id = self.generate_file_id()
		
		if not self.upload_date:
			self.upload_date = frappe.utils.now()
		
		if not self.uploaded_by:
			self.uploaded_by = frappe.session.user
		
		# Set file extension and type
		if self.original_filename and '.' in self.original_filename:
			self.file_extension = self.original_filename.split('.')[-1].lower()
			self.file_type = self.get_file_type_from_extension()
	
	def generate_file_id(self):
		"""Generate unique file ID"""
		import random
		import string
		
		# Generate file ID format: DOC-YYYY-XXXXXX
		year = frappe.utils.nowdate()[:4]
		random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
		return f"DOC-{year}-{random_part}"
	
	def get_file_type_from_extension(self):
		"""Get file type based on extension"""
		extension_map = {
			'pdf': 'PDF Document',
			'doc': 'Word Document',
			'docx': 'Word Document',
			'xls': 'Excel Spreadsheet',
			'xlsx': 'Excel Spreadsheet',
			'jpg': 'Image',
			'jpeg': 'Image',
			'png': 'Image',
			'gif': 'Image',
			'txt': 'Text File',
			'csv': 'CSV File'
		}
		
		return extension_map.get(self.file_extension, 'Unknown')
	
	def calculate_file_hash(self, file_content):
		"""Calculate SHA-256 hash of file content"""
		if isinstance(file_content, str):
			file_content = file_content.encode('utf-8')
		
		return hashlib.sha256(file_content).hexdigest()
	
	def update_upload_progress(self, progress):
		"""Update upload progress"""
		self.upload_progress = progress
		
		if progress >= 100:
			self.upload_status = "Completed"
		elif progress > 0:
			self.upload_status = "Uploading"
		
		self.save()
	
	def validate_document(self):
		"""Validate uploaded document"""
		validation_results = []
		
		# File size validation
		max_size = 50 * 1024 * 1024  # 50MB
		if self.file_size > max_size:
			validation_results.append("File size exceeds maximum limit of 50MB")
		
		# File type validation
		allowed_extensions = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'xls', 'xlsx', 'txt', 'csv']
		if self.file_extension not in allowed_extensions:
			validation_results.append(f"File type '{self.file_extension}' is not allowed")
		
		# Set validation status
		if validation_results:
			self.validation_status = "Failed"
			self.error_message = "; ".join(validation_results)
		else:
			self.validation_status = "Passed"
			validation_results.append("All validation checks passed")
		
		self.validation_results = "\n".join(validation_results)
		self.save()
		
		return len(validation_results) == 1  # Only success message
	
	def get_upload_info(self):
		"""Get upload information"""
		return {
			'file_id': self.file_id,
			'original_filename': self.original_filename,
			'file_size': self.file_size,
			'document_category': self.document_category,
			'upload_status': self.upload_status,
			'upload_progress': self.upload_progress,
			'validation_status': self.validation_status,
			'uploaded_by': self.uploaded_by,
			'upload_date': self.upload_date
		}
	
	def move_to_secure_storage(self):
		"""Move file to secure storage location"""
		try:
			# Create secure storage directory
			site_path = get_site_path()
			secure_dir = os.path.join(site_path, 'private', 'documents', self.document_category)
			os.makedirs(secure_dir, exist_ok=True)
			
			# Generate secure filename
			secure_filename = f"{self.file_id}_{self.original_filename}"
			secure_path = os.path.join(secure_dir, secure_filename)
			
			self.storage_path = secure_path
			self.processing_status = "Stored securely"
			self.save()
			
			return True
		except Exception as e:
			self.error_message = f"Storage error: {str(e)}"
			self.processing_status = "Storage failed"
			self.save()
			return False


@frappe.whitelist()
def upload_document(file_data, metadata):
	"""Upload a new document"""
	try:
		# Create document upload record
		doc = frappe.new_doc('Document Upload')
		doc.original_filename = file_data.get('filename')
		doc.file_size = file_data.get('size', 0)
		doc.document_category = metadata.get('category', 'Other')
		doc.description = metadata.get('description', '')
		doc.related_claim = metadata.get('related_claim')
		doc.related_employer = metadata.get('related_employer')
		doc.access_level = metadata.get('access_level', 'Internal')
		doc.upload_status = "Uploading"
		doc.upload_progress = 0
		
		# Set MIME type if provided
		if 'mime_type' in file_data:
			doc.mime_type = file_data['mime_type']
		
		doc.insert()
		
		# Simulate file processing
		doc.update_upload_progress(50)
		doc.validate_document()
		doc.move_to_secure_storage()
		doc.update_upload_progress(100)
		
		return {
			'success': True,
			'file_id': doc.file_id,
			'upload_info': doc.get_upload_info()
		}
		
	except Exception as e:
		frappe.log_error(f"Document upload error: {str(e)}", "Document Upload")
		return {'error': str(e)}


@frappe.whitelist()
def get_user_documents(user=None):
	"""Get documents uploaded by user"""
	if not user:
		user = frappe.session.user
	
	# Get user roles to determine access
	user_roles = frappe.get_roles(user)
	
	filters = {}
	
	# Filter based on user role
	if 'Beneficiary' in user_roles or 'Employer' in user_roles:
		filters['uploaded_by'] = user
	# WCFCB Staff and System Manager can see all documents
	
	documents = frappe.get_all(
		'Document Upload',
		filters=filters,
		fields=['name', 'file_id', 'original_filename', 'document_category', 'upload_status', 
		        'validation_status', 'file_size', 'upload_date'],
		order_by='upload_date desc'
	)
	
	return documents


@frappe.whitelist()
def get_upload_progress(file_id):
	"""Get upload progress for a file"""
	try:
		doc = frappe.get_doc('Document Upload', {'file_id': file_id})
		return {
			'success': True,
			'progress': doc.upload_progress,
			'status': doc.upload_status,
			'validation_status': doc.validation_status
		}
	except frappe.DoesNotExistError:
		return {'error': 'Document not found'}


@frappe.whitelist()
def delete_document(file_id):
	"""Delete a document"""
	try:
		doc = frappe.get_doc('Document Upload', {'file_id': file_id})
		
		# Check permissions
		if doc.uploaded_by != frappe.session.user and 'WCFCB Staff' not in frappe.get_roles():
			return {'error': 'Permission denied'}
		
		# Delete file from storage if exists
		if doc.storage_path and os.path.exists(doc.storage_path):
			os.remove(doc.storage_path)
		
		# Delete document record
		doc.delete()
		
		return {'success': True, 'message': 'Document deleted successfully'}
		
	except frappe.DoesNotExistError:
		return {'error': 'Document not found'}
	except Exception as e:
		return {'error': str(e)}
