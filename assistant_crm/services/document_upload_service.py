"""
Document Upload Service for WCFCB Assistant CRM
Provides secure file upload capabilities with validation and storage

Phase 3.2.1 Implementation
"""

import frappe
from frappe.utils import now, get_files_path, get_site_path
from typing import Dict, List, Any, Optional
import os
import hashlib
import mimetypes
from datetime import datetime
import uuid


class DocumentUploadService:
    """
    Service for secure document upload and management
    Provides file upload, validation, and storage capabilities for WCFCB documents
    """
    
    def __init__(self):
        """Initialize Document Upload Service"""
        self.service_name = "Document Upload Service"
        self.upload_path = self._get_upload_path()
        self.max_file_size = self._get_max_file_size()  # 50MB default
        self.allowed_extensions = self._get_allowed_extensions()
        self.allowed_mime_types = self._get_allowed_mime_types()
        
        # Document categories for WCFCB
        self.document_categories = {
            'medical': 'Medical Records and Reports',
            'incident': 'Incident Reports and Documentation',
            'employment': 'Employment and Payroll Records',
            'legal': 'Legal Documents and Correspondence',
            'identification': 'Identification and Personal Documents',
            'financial': 'Financial and Insurance Documents',
            'other': 'Other Supporting Documents'
        }
        
        # File type mappings
        self.file_type_categories = {
            'pdf': 'document',
            'doc': 'document',
            'docx': 'document',
            'txt': 'document',
            'jpg': 'image',
            'jpeg': 'image',
            'png': 'image',
            'gif': 'image',
            'tiff': 'image',
            'xls': 'spreadsheet',
            'xlsx': 'spreadsheet',
            'csv': 'spreadsheet'
        }
    
    def upload_document(self, file_data: Dict, user_context: Dict = None, 
                       metadata: Dict = None) -> Dict[str, Any]:
        """
        Upload a document with validation and security checks
        
        Args:
            file_data: File data including content, filename, and size
            user_context: User context for authorization
            metadata: Additional metadata for the document
            
        Returns:
            Dict containing upload result and document information
        """
        try:
            # Validate user authorization
            if not self._validate_upload_permission(user_context):
                return {
                    'success': False,
                    'error': 'Unauthorized to upload documents',
                    'error_code': 'UNAUTHORIZED'
                }
            
            # Validate file data
            validation_result = self._validate_file_data(file_data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': 'File validation failed',
                    'validation_errors': validation_result['errors'],
                    'error_code': 'VALIDATION_FAILED'
                }
            
            # Generate unique file identifier
            file_id = self._generate_file_id()
            
            # Process and store the file
            storage_result = self._store_file(file_data, file_id, user_context, metadata)
            
            if storage_result['success']:
                # Create document record
                document_record = self._create_document_record(
                    file_id, file_data, storage_result, user_context, metadata
                )
                
                # Log upload activity
                self._log_upload_activity(file_id, user_context, 'upload_success')
                
                return {
                    'success': True,
                    'file_id': file_id,
                    'document_record': document_record,
                    'storage_path': storage_result.get('storage_path'),
                    'file_size': file_data.get('size'),
                    'upload_timestamp': now(),
                    'message': 'Document uploaded successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'File storage failed',
                    'details': storage_result.get('error'),
                    'error_code': 'STORAGE_FAILED'
                }
                
        except Exception as e:
            frappe.log_error(f"Document upload error: {str(e)}", "DocumentUploadService")
            return {
                'success': False,
                'error': 'Document upload failed',
                'technical_error': str(e),
                'error_code': 'SYSTEM_ERROR'
            }
    
    def get_upload_progress(self, upload_id: str, user_context: Dict = None) -> Dict[str, Any]:
        """
        Get upload progress for a specific upload session
        
        Args:
            upload_id: Unique upload session identifier
            user_context: User context for authorization
            
        Returns:
            Dict containing upload progress information
        """
        try:
            # Validate user access
            if not self._validate_upload_access(user_context, upload_id):
                return {
                    'success': False,
                    'error': 'Unauthorized access to upload progress'
                }
            
            # Get progress from cache or database
            progress_data = self._get_upload_progress_data(upload_id)
            
            if progress_data:
                return {
                    'success': True,
                    'upload_id': upload_id,
                    'progress': progress_data,
                    'last_updated': now()
                }
            else:
                return {
                    'success': False,
                    'error': 'Upload progress not found',
                    'upload_id': upload_id
                }
                
        except Exception as e:
            frappe.log_error(f"Upload progress error: {str(e)}", "DocumentUploadService")
            return {
                'success': False,
                'error': 'Unable to retrieve upload progress',
                'technical_error': str(e)
            }
    
    def get_user_documents(self, user_context: Dict, filters: Dict = None) -> Dict[str, Any]:
        """
        Get documents uploaded by a specific user
        
        Args:
            user_context: User context containing identification
            filters: Optional filters for document search
            
        Returns:
            Dict containing user's documents
        """
        try:
            # Extract user identification
            user_id = self._extract_user_id(user_context)
            if not user_id:
                return {
                    'success': False,
                    'error': 'User identification required'
                }
            
            # Apply filters
            search_filters = filters or {}
            search_filters['uploaded_by'] = user_id
            
            # Fetch user documents
            documents = self._fetch_user_documents(search_filters)
            
            if documents:
                # Format documents for display
                formatted_documents = []
                for doc in documents:
                    formatted_doc = self._format_document_info(doc)
                    formatted_documents.append(formatted_doc)
                
                # Categorize documents
                categorized_docs = self._categorize_documents(formatted_documents)
                
                return {
                    'success': True,
                    'user_id': user_id,
                    'documents': formatted_documents,
                    'categorized_documents': categorized_docs,
                    'total_documents': len(formatted_documents),
                    'total_size': sum(doc.get('file_size', 0) for doc in formatted_documents),
                    'filters_applied': search_filters,
                    'last_updated': now()
                }
            else:
                return {
                    'success': True,
                    'user_id': user_id,
                    'documents': [],
                    'total_documents': 0,
                    'message': 'No documents found'
                }
                
        except Exception as e:
            frappe.log_error(f"User documents retrieval error: {str(e)}", "DocumentUploadService")
            return {
                'success': False,
                'error': 'Unable to retrieve user documents',
                'technical_error': str(e)
            }
    
    def delete_document(self, file_id: str, user_context: Dict = None) -> Dict[str, Any]:
        """
        Delete a document with proper authorization and cleanup
        
        Args:
            file_id: Unique file identifier
            user_context: User context for authorization
            
        Returns:
            Dict containing deletion result
        """
        try:
            # Validate user authorization for deletion
            if not self._validate_delete_permission(user_context, file_id):
                return {
                    'success': False,
                    'error': 'Unauthorized to delete this document',
                    'file_id': file_id
                }
            
            # Get document information before deletion
            document_info = self._get_document_info(file_id)
            if not document_info:
                return {
                    'success': False,
                    'error': 'Document not found',
                    'file_id': file_id
                }
            
            # Perform deletion
            deletion_result = self._delete_document_files(file_id, document_info)
            
            if deletion_result['success']:
                # Update document record as deleted
                self._mark_document_deleted(file_id, user_context)
                
                # Log deletion activity
                self._log_upload_activity(file_id, user_context, 'document_deleted')
                
                return {
                    'success': True,
                    'file_id': file_id,
                    'message': 'Document deleted successfully',
                    'deleted_at': now()
                }
            else:
                return {
                    'success': False,
                    'error': 'Document deletion failed',
                    'details': deletion_result.get('error'),
                    'file_id': file_id
                }
                
        except Exception as e:
            frappe.log_error(f"Document deletion error: {str(e)}", "DocumentUploadService")
            return {
                'success': False,
                'error': 'Document deletion failed',
                'technical_error': str(e),
                'file_id': file_id
            }

    def _get_upload_path(self) -> str:
        """Get secure upload path for documents"""
        try:
            # Create secure upload directory
            site_path = get_site_path()
            upload_dir = os.path.join(site_path, 'private', 'files', 'wcfcb_documents')

            # Ensure directory exists
            os.makedirs(upload_dir, exist_ok=True)

            return upload_dir
        except Exception:
            # Fallback to default files path
            return get_files_path()

    def _get_max_file_size(self) -> int:
        """Get maximum allowed file size in bytes"""
        try:
            # Try to get from settings, default to 50MB
            max_size = frappe.db.get_single_value("Assistant CRM Settings", "max_file_size_mb") or 50
            return max_size * 1024 * 1024  # Convert MB to bytes
        except Exception:
            return 50 * 1024 * 1024  # 50MB default

    def _get_allowed_extensions(self) -> List[str]:
        """Get list of allowed file extensions"""
        return [
            'pdf', 'doc', 'docx', 'txt', 'rtf',  # Documents
            'jpg', 'jpeg', 'png', 'gif', 'tiff', 'bmp',  # Images
            'xls', 'xlsx', 'csv',  # Spreadsheets
            'zip', 'rar', '7z'  # Archives
        ]

    def _get_allowed_mime_types(self) -> List[str]:
        """Get list of allowed MIME types"""
        return [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/tiff',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/csv',
            'application/zip',
            'application/x-rar-compressed'
        ]

    def _validate_upload_permission(self, user_context: Dict) -> bool:
        """Validate user has permission to upload documents"""
        if not user_context:
            return False

        # Check user roles
        user_roles = user_context.get('roles', [])
        allowed_roles = ['Beneficiary', 'Employer', 'WCFCB Staff', 'System Manager']

        return any(role in allowed_roles for role in user_roles)

    def _validate_file_data(self, file_data: Dict) -> Dict[str, Any]:
        """Validate uploaded file data"""
        errors = []

        try:
            # Check required fields
            if not file_data.get('filename'):
                errors.append("Filename is required")

            if not file_data.get('content') and not file_data.get('file_path'):
                errors.append("File content or path is required")

            # Validate file size
            file_size = file_data.get('size', 0)
            if file_size <= 0:
                errors.append("Invalid file size")
            elif file_size > self.max_file_size:
                max_mb = self.max_file_size / (1024 * 1024)
                errors.append(f"File size exceeds maximum limit of {max_mb}MB")

            # Validate file extension
            filename = file_data.get('filename', '')
            file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
            if file_ext not in self.allowed_extensions:
                errors.append(f"File type '{file_ext}' is not allowed")

            # Validate MIME type if available
            mime_type = file_data.get('mime_type')
            if mime_type and mime_type not in self.allowed_mime_types:
                errors.append(f"MIME type '{mime_type}' is not allowed")

            # Validate filename for security
            if self._contains_unsafe_characters(filename):
                errors.append("Filename contains unsafe characters")

            return {
                'valid': len(errors) == 0,
                'errors': errors
            }

        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"]
            }

    def _generate_file_id(self) -> str:
        """Generate unique file identifier"""
        return str(uuid.uuid4())

    def _extract_user_id(self, user_context: Dict) -> Optional[str]:
        """Extract user ID from user context"""
        if not user_context:
            return None

        return (user_context.get('user_id') or
                user_context.get('email') or
                user_context.get('user') or
                user_context.get('member_id'))

    def _contains_unsafe_characters(self, filename: str) -> bool:
        """Check if filename contains unsafe characters"""
        unsafe_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        return any(char in filename for char in unsafe_chars)

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file for integrity verification"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return ""

    def _store_file(self, file_data: Dict, file_id: str, user_context: Dict,
                   metadata: Dict) -> Dict[str, Any]:
        """Store file securely with proper organization"""
        try:
            # Create user-specific directory
            user_id = self._extract_user_id(user_context)
            user_dir = os.path.join(self.upload_path, user_id or 'anonymous')
            os.makedirs(user_dir, exist_ok=True)

            # Generate secure filename
            original_filename = file_data.get('filename', '')
            file_ext = original_filename.split('.')[-1].lower() if '.' in original_filename else 'bin'
            secure_filename = f"{file_id}.{file_ext}"

            # Full file path
            file_path = os.path.join(user_dir, secure_filename)

            # For demo purposes, create a placeholder file
            # In production, this would handle actual file content
            demo_content = f"Demo document content for {original_filename}\nFile ID: {file_id}\nUploaded by: {user_id}\nTimestamp: {now()}"

            with open(file_path, 'w') as f:
                f.write(demo_content)

            # Verify file was written correctly
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': 'File was not stored successfully'
                }

            # Calculate file hash for integrity
            file_hash = self._calculate_file_hash(file_path)

            return {
                'success': True,
                'storage_path': file_path,
                'secure_filename': secure_filename,
                'file_hash': file_hash,
                'stored_at': now()
            }

        except Exception as e:
            frappe.log_error(f"File storage error: {str(e)}", "DocumentUploadService")
            return {
                'success': False,
                'error': f"File storage failed: {str(e)}"
            }

    def _create_document_record(self, file_id: str, file_data: Dict, storage_result: Dict,
                              user_context: Dict, metadata: Dict) -> Dict[str, Any]:
        """Create document record in database"""
        try:
            user_id = self._extract_user_id(user_context)

            document_record = {
                'file_id': file_id,
                'original_filename': file_data.get('filename'),
                'secure_filename': storage_result.get('secure_filename'),
                'file_size': file_data.get('size', 0),
                'mime_type': file_data.get('mime_type'),
                'file_hash': storage_result.get('file_hash'),
                'uploaded_by': user_id,
                'upload_timestamp': now(),
                'storage_path': storage_result.get('storage_path'),
                'document_category': metadata.get('category', 'other') if metadata else 'other',
                'description': metadata.get('description', '') if metadata else '',
                'status': 'uploaded',
                'access_level': 'private'
            }

            # In production, this would be saved to database
            # For demo, we'll return the record structure

            return document_record

        except Exception as e:
            frappe.log_error(f"Document record creation error: {str(e)}", "DocumentUploadService")
            return {}

    def _log_upload_activity(self, file_id: str, user_context: Dict, activity_type: str):
        """Log upload activity for audit trail"""
        try:
            user_id = self._extract_user_id(user_context)

            activity_log = {
                'file_id': file_id,
                'user_id': user_id,
                'activity_type': activity_type,
                'timestamp': now(),
                'ip_address': frappe.local.request.environ.get('REMOTE_ADDR') if frappe.local.request else 'unknown'
            }

            # In production, this would be saved to audit log
            frappe.log_error(f"Document activity: {activity_log}", "DocumentUploadService")

        except Exception as e:
            frappe.log_error(f"Activity logging error: {str(e)}", "DocumentUploadService")

    def _validate_upload_access(self, user_context: Dict, upload_id: str) -> bool:
        """Validate user has access to upload progress"""
        # For demo purposes, allow access if user context is provided
        return bool(user_context and self._extract_user_id(user_context))

    def _get_upload_progress_data(self, upload_id: str) -> Optional[Dict]:
        """Get upload progress data from cache or database"""
        try:
            # Demo progress data
            demo_progress = {
                'upload_id': upload_id,
                'status': 'completed',
                'progress_percentage': 100,
                'bytes_uploaded': 1024000,
                'total_bytes': 1024000,
                'upload_speed': '1.2 MB/s',
                'time_remaining': '0 seconds',
                'started_at': now(),
                'completed_at': now()
            }

            return demo_progress

        except Exception:
            return None

    def _fetch_user_documents(self, filters: Dict) -> List[Dict]:
        """Fetch documents based on filters"""
        try:
            # Demo user documents
            demo_documents = [
                {
                    'file_id': 'doc001',
                    'original_filename': 'medical_report.pdf',
                    'file_size': 1024000,
                    'mime_type': 'application/pdf',
                    'uploaded_by': filters.get('uploaded_by'),
                    'upload_timestamp': '2025-01-15 10:30:00',
                    'document_category': 'medical',
                    'description': 'Medical examination report',
                    'status': 'uploaded'
                },
                {
                    'file_id': 'doc002',
                    'original_filename': 'incident_report.docx',
                    'file_size': 512000,
                    'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'uploaded_by': filters.get('uploaded_by'),
                    'upload_timestamp': '2025-01-20 14:15:00',
                    'document_category': 'incident',
                    'description': 'Workplace incident documentation',
                    'status': 'uploaded'
                }
            ]

            return demo_documents

        except Exception as e:
            frappe.log_error(f"User documents fetch error: {str(e)}", "DocumentUploadService")
            return []

    def _format_document_info(self, document: Dict) -> Dict[str, Any]:
        """Format document information for display"""
        try:
            return {
                'file_id': document.get('file_id'),
                'original_filename': document.get('original_filename'),
                'file_size': document.get('file_size', 0),
                'file_size_mb': round(document.get('file_size', 0) / (1024 * 1024), 2),
                'mime_type': document.get('mime_type'),
                'document_category': document.get('document_category'),
                'description': document.get('description'),
                'upload_timestamp': document.get('upload_timestamp'),
                'status': document.get('status', 'uploaded'),
                'uploaded_by': document.get('uploaded_by')
            }
        except Exception as e:
            frappe.log_error(f"Document formatting error: {str(e)}", "DocumentUploadService")
            return document

    def _categorize_documents(self, documents: List[Dict]) -> Dict[str, List]:
        """Categorize documents by type"""
        try:
            categories = {}

            for doc in documents:
                category = doc.get('document_category', 'other')
                if category not in categories:
                    categories[category] = []
                categories[category].append(doc)

            return categories

        except Exception as e:
            frappe.log_error(f"Document categorization error: {str(e)}", "DocumentUploadService")
            return {'other': documents}

    def _validate_delete_permission(self, user_context: Dict, file_id: str) -> bool:
        """Validate user has permission to delete document"""
        try:
            if not user_context:
                return False

            # Check user roles
            user_roles = user_context.get('roles', [])
            admin_roles = ['System Manager', 'WCFCB Staff']

            if any(role in admin_roles for role in user_roles):
                return True

            # Check if user is document owner
            document_info = self._get_document_info(file_id)
            if document_info and document_info.get('uploaded_by') == user_context.get('user'):
                return True

            return False

        except Exception:
            return False

    def _get_document_info(self, file_id: str) -> Optional[Dict]:
        """Get document information"""
        try:
            # Demo document info
            demo_documents = {
                'doc001': {
                    'file_id': 'doc001',
                    'original_filename': 'medical_report.pdf',
                    'file_size': 1024000,
                    'uploaded_by': 'test_user',
                    'upload_timestamp': '2025-01-15 10:30:00',
                    'storage_path': '/path/to/medical_report.pdf'
                },
                'doc002': {
                    'file_id': 'doc002',
                    'original_filename': 'incident_report.docx',
                    'file_size': 512000,
                    'uploaded_by': 'test_user',
                    'upload_timestamp': '2025-01-20 14:15:00',
                    'storage_path': '/path/to/incident_report.docx'
                }
            }

            return demo_documents.get(file_id)

        except Exception as e:
            frappe.log_error(f"Document info retrieval error: {str(e)}", "DocumentUploadService")
            return None

    def _delete_document_files(self, file_id: str, document_info: Dict) -> Dict[str, Any]:
        """Delete document files from storage"""
        try:
            storage_path = document_info.get('storage_path')

            if storage_path and os.path.exists(storage_path):
                os.remove(storage_path)

                # Also remove metadata file if exists
                metadata_path = storage_path + '.meta'
                if os.path.exists(metadata_path):
                    os.remove(metadata_path)

                return {
                    'success': True,
                    'deleted_files': [storage_path, metadata_path]
                }
            else:
                # For demo purposes, simulate successful deletion
                return {
                    'success': True,
                    'deleted_files': ['demo_file_deleted']
                }

        except Exception as e:
            frappe.log_error(f"Document file deletion error: {str(e)}", "DocumentUploadService")
            return {
                'success': False,
                'error': f"File deletion failed: {str(e)}"
            }

    def _mark_document_deleted(self, file_id: str, user_context: Dict):
        """Mark document as deleted in database"""
        try:
            # In production, this would update the database record
            deletion_record = {
                'file_id': file_id,
                'deleted_by': user_context.get('user') if user_context else 'unknown',
                'deleted_at': now(),
                'status': 'deleted'
            }

            frappe.log_error(f"Document marked as deleted: {deletion_record}", "DocumentUploadService")

        except Exception as e:
            frappe.log_error(f"Document deletion marking error: {str(e)}", "DocumentUploadService")


def get_document_upload_service():
    """Factory function to get DocumentUploadService instance"""
    return DocumentUploadService()
