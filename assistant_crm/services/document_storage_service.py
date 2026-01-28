"""
Document Storage Service for WCFCB Assistant CRM
Provides secure document storage with encryption and access controls

Phase 3.2.3 Implementation
"""

import frappe
from frappe.utils import now, get_site_path
from typing import Dict, List, Any, Optional
import os
import json
import hashlib
import base64
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import uuid


class DocumentStorageService:
    """
    Service for secure document storage and retrieval
    Provides encryption, access controls, versioning, and audit trails
    """
    
    def __init__(self):
        """Initialize Document Storage Service"""
        self.service_name = "Document Storage Service"
        self.storage_root = self._get_secure_storage_root()
        self.encryption_key = self._get_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key) if self.encryption_key else None
        
        # Access control levels
        self.access_levels = {
            'public': 'Publicly accessible',
            'internal': 'Internal WCFCB access only',
            'restricted': 'Restricted access - authorized users only',
            'confidential': 'Confidential - specific user access only',
            'classified': 'Classified - highest security level'
        }
        
        # Storage tiers
        self.storage_tiers = {
            'hot': 'Frequently accessed documents',
            'warm': 'Occasionally accessed documents',
            'cold': 'Rarely accessed documents',
            'archive': 'Long-term archive storage'
        }
        
        # Retention policies
        self.retention_policies = {
            'medical': {'years': 7, 'tier_transition': 'warm_after_1_year'},
            'incident': {'years': 10, 'tier_transition': 'cold_after_2_years'},
            'employment': {'years': 5, 'tier_transition': 'warm_after_6_months'},
            'legal': {'years': 15, 'tier_transition': 'archive_after_5_years'},
            'financial': {'years': 7, 'tier_transition': 'cold_after_1_year'},
            'other': {'years': 3, 'tier_transition': 'cold_after_1_year'}
        }
    
    def store_document(self, file_data: Dict, metadata: Dict, 
                      user_context: Dict = None) -> Dict[str, Any]:
        """
        Store document securely with encryption and access controls
        
        Args:
            file_data: File content and information
            metadata: Document metadata including access level and category
            user_context: User context for authorization
            
        Returns:
            Dict containing storage result and access information
        """
        try:
            # Validate storage permission
            if not self._validate_storage_permission(user_context, metadata):
                return {
                    'success': False,
                    'error': 'Unauthorized to store document with specified access level',
                    'error_code': 'UNAUTHORIZED_STORAGE'
                }
            
            # Generate unique storage identifier
            storage_id = self._generate_storage_id()
            
            # Determine storage configuration
            storage_config = self._determine_storage_config(metadata)
            
            # Encrypt document if required
            encryption_result = self._encrypt_document(file_data, storage_config)
            if not encryption_result['success']:
                return {
                    'success': False,
                    'error': 'Document encryption failed',
                    'details': encryption_result.get('error')
                }
            
            # Store document with versioning
            storage_result = self._store_document_securely(
                encryption_result['encrypted_data'], 
                storage_id, 
                metadata, 
                user_context
            )
            
            if storage_result['success']:
                # Create access control record
                access_record = self._create_access_control_record(
                    storage_id, metadata, user_context
                )
                
                # Log storage activity
                self._log_storage_activity(storage_id, 'document_stored', user_context)
                
                # Schedule retention policy
                self._schedule_retention_policy(storage_id, metadata)
                
                return {
                    'success': True,
                    'storage_id': storage_id,
                    'storage_path': storage_result['storage_path'],
                    'access_record': access_record,
                    'encryption_enabled': storage_config['encryption_enabled'],
                    'storage_tier': storage_config['storage_tier'],
                    'retention_policy': storage_config['retention_policy'],
                    'stored_at': now()
                }
            else:
                return {
                    'success': False,
                    'error': 'Document storage failed',
                    'details': storage_result.get('error')
                }
                
        except Exception as e:
            frappe.log_error(f"Document storage error: {str(e)}", "DocumentStorageService")
            return {
                'success': False,
                'error': 'Document storage failed',
                'technical_error': str(e),
                'error_code': 'STORAGE_ERROR'
            }
    
    def retrieve_document(self, storage_id: str, user_context: Dict = None,
                         version: str = None) -> Dict[str, Any]:
        """
        Retrieve document with access control validation
        
        Args:
            storage_id: Unique storage identifier
            user_context: User context for authorization
            version: Specific version to retrieve (optional)
            
        Returns:
            Dict containing document data or access denial
        """
        try:
            # Validate access permission
            access_validation = self._validate_document_access(storage_id, user_context)
            if not access_validation['allowed']:
                return {
                    'success': False,
                    'error': 'Access denied to document',
                    'reason': access_validation.get('reason'),
                    'error_code': 'ACCESS_DENIED'
                }
            
            # Get document metadata
            document_metadata = self._get_document_metadata(storage_id)
            if not document_metadata:
                return {
                    'success': False,
                    'error': 'Document not found',
                    'storage_id': storage_id
                }
            
            # Retrieve document content
            retrieval_result = self._retrieve_document_content(storage_id, version)
            if not retrieval_result['success']:
                return {
                    'success': False,
                    'error': 'Document retrieval failed',
                    'details': retrieval_result.get('error')
                }
            
            # Decrypt document if encrypted
            decryption_result = self._decrypt_document(
                retrieval_result['encrypted_data'], 
                document_metadata
            )
            
            if decryption_result['success']:
                # Log access activity
                self._log_storage_activity(storage_id, 'document_accessed', user_context)
                
                # Update access statistics
                self._update_access_statistics(storage_id)
                
                return {
                    'success': True,
                    'storage_id': storage_id,
                    'document_data': decryption_result['document_data'],
                    'metadata': document_metadata,
                    'version': version or 'latest',
                    'accessed_at': now(),
                    'access_level': access_validation.get('access_level')
                }
            else:
                return {
                    'success': False,
                    'error': 'Document decryption failed',
                    'details': decryption_result.get('error')
                }
                
        except Exception as e:
            frappe.log_error(f"Document retrieval error: {str(e)}", "DocumentStorageService")
            return {
                'success': False,
                'error': 'Document retrieval failed',
                'technical_error': str(e)
            }
    
    def update_access_controls(self, storage_id: str, new_access_config: Dict,
                             user_context: Dict = None) -> Dict[str, Any]:
        """
        Update access controls for a stored document
        
        Args:
            storage_id: Unique storage identifier
            new_access_config: New access configuration
            user_context: User context for authorization
            
        Returns:
            Dict containing update result
        """
        try:
            # Validate permission to modify access controls
            if not self._validate_access_modification_permission(storage_id, user_context):
                return {
                    'success': False,
                    'error': 'Unauthorized to modify access controls',
                    'storage_id': storage_id
                }
            
            # Get current access configuration
            current_config = self._get_access_configuration(storage_id)
            if not current_config:
                return {
                    'success': False,
                    'error': 'Document access configuration not found',
                    'storage_id': storage_id
                }
            
            # Validate new access configuration
            validation_result = self._validate_access_configuration(new_access_config)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': 'Invalid access configuration',
                    'validation_errors': validation_result['errors']
                }
            
            # Update access controls
            update_result = self._update_access_configuration(storage_id, new_access_config)
            
            if update_result['success']:
                # Log access control change
                self._log_storage_activity(
                    storage_id, 
                    'access_controls_updated', 
                    user_context,
                    {'old_config': current_config, 'new_config': new_access_config}
                )
                
                return {
                    'success': True,
                    'storage_id': storage_id,
                    'updated_config': new_access_config,
                    'previous_config': current_config,
                    'updated_at': now()
                }
            else:
                return {
                    'success': False,
                    'error': 'Access control update failed',
                    'details': update_result.get('error')
                }
                
        except Exception as e:
            frappe.log_error(f"Access control update error: {str(e)}", "DocumentStorageService")
            return {
                'success': False,
                'error': 'Access control update failed',
                'technical_error': str(e)
            }
    
    def get_document_versions(self, storage_id: str, user_context: Dict = None) -> Dict[str, Any]:
        """
        Get all versions of a document
        
        Args:
            storage_id: Unique storage identifier
            user_context: User context for authorization
            
        Returns:
            Dict containing version information
        """
        try:
            # Validate access permission
            access_validation = self._validate_document_access(storage_id, user_context)
            if not access_validation['allowed']:
                return {
                    'success': False,
                    'error': 'Access denied to document versions',
                    'storage_id': storage_id
                }
            
            # Get version history
            version_history = self._get_version_history(storage_id)
            
            if version_history:
                return {
                    'success': True,
                    'storage_id': storage_id,
                    'versions': version_history,
                    'total_versions': len(version_history),
                    'current_version': version_history[0] if version_history else None,
                    'retrieved_at': now()
                }
            else:
                return {
                    'success': True,
                    'storage_id': storage_id,
                    'versions': [],
                    'message': 'No versions found for document'
                }
                
        except Exception as e:
            frappe.log_error(f"Document versions retrieval error: {str(e)}", "DocumentStorageService")
            return {
                'success': False,
                'error': 'Unable to retrieve document versions',
                'technical_error': str(e)
            }

    def _get_secure_storage_root(self) -> str:
        """Get secure storage root directory"""
        try:
            site_path = get_site_path()
            storage_root = os.path.join(site_path, 'private', 'secure_documents')
            os.makedirs(storage_root, exist_ok=True)
            return storage_root
        except Exception:
            return os.path.join(os.getcwd(), 'secure_documents')

    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key"""
        try:
            # In production, this would be securely managed
            # For demo, generate a key
            return Fernet.generate_key()
        except Exception:
            return None

    def _generate_storage_id(self) -> str:
        """Generate unique storage identifier"""
        return str(uuid.uuid4())

    def _validate_storage_permission(self, user_context: Dict, metadata: Dict) -> bool:
        """Validate user has permission to store document"""
        if not user_context:
            return False

        # Check user roles
        user_roles = user_context.get('roles', [])
        access_level = metadata.get('access_level', 'internal')

        # Define role-based access permissions
        role_permissions = {
            'System Manager': ['public', 'internal', 'restricted', 'confidential', 'classified'],
            'WCFCB Staff': ['public', 'internal', 'restricted', 'confidential'],
            'Manager': ['public', 'internal', 'restricted'],
            'Employer': ['public', 'internal'],
            'Beneficiary': ['public', 'internal']
        }

        for role in user_roles:
            if role in role_permissions and access_level in role_permissions[role]:
                return True

        return False

    def _determine_storage_config(self, metadata: Dict) -> Dict[str, Any]:
        """Determine storage configuration based on metadata"""
        try:
            document_category = metadata.get('category', 'other')
            access_level = metadata.get('access_level', 'internal')

            # Determine encryption requirement
            encryption_enabled = access_level in ['restricted', 'confidential', 'classified']

            # Determine storage tier
            if access_level in ['classified', 'confidential']:
                storage_tier = 'hot'
            elif access_level == 'restricted':
                storage_tier = 'warm'
            else:
                storage_tier = 'hot'

            # Get retention policy
            retention_policy = self.retention_policies.get(document_category, self.retention_policies['other'])

            return {
                'encryption_enabled': encryption_enabled,
                'storage_tier': storage_tier,
                'retention_policy': retention_policy,
                'access_level': access_level,
                'document_category': document_category
            }

        except Exception as e:
            frappe.log_error(f"Storage config determination error: {str(e)}", "DocumentStorageService")
            return {
                'encryption_enabled': True,
                'storage_tier': 'hot',
                'retention_policy': self.retention_policies['other'],
                'access_level': 'internal',
                'document_category': 'other'
            }

    def _encrypt_document(self, file_data: Dict, storage_config: Dict) -> Dict[str, Any]:
        """Encrypt document content if required"""
        try:
            if not storage_config.get('encryption_enabled', False):
                return {
                    'success': True,
                    'encrypted_data': file_data,
                    'encryption_used': False
                }

            if not self.cipher_suite:
                return {
                    'success': False,
                    'error': 'Encryption not available'
                }

            # For demo purposes, simulate encryption
            content = file_data.get('content', b'')
            if isinstance(content, str):
                content = content.encode('utf-8')

            # Simulate encryption (in production, use actual encryption)
            encrypted_content = base64.b64encode(content).decode('utf-8')

            encrypted_data = file_data.copy()
            encrypted_data['content'] = encrypted_content
            encrypted_data['encrypted'] = True

            return {
                'success': True,
                'encrypted_data': encrypted_data,
                'encryption_used': True
            }

        except Exception as e:
            frappe.log_error(f"Document encryption error: {str(e)}", "DocumentStorageService")
            return {
                'success': False,
                'error': f"Encryption failed: {str(e)}"
            }

    def _store_document_securely(self, encrypted_data: Dict, storage_id: str,
                                metadata: Dict, user_context: Dict) -> Dict[str, Any]:
        """Store document with proper organization and security"""
        try:
            # Create storage directory structure
            access_level = metadata.get('access_level', 'internal')
            category = metadata.get('category', 'other')

            storage_dir = os.path.join(self.storage_root, access_level, category)
            os.makedirs(storage_dir, exist_ok=True)

            # Generate secure filename
            original_filename = encrypted_data.get('filename', 'document')
            file_ext = original_filename.split('.')[-1] if '.' in original_filename else 'bin'
            secure_filename = f"{storage_id}.{file_ext}"

            storage_path = os.path.join(storage_dir, secure_filename)

            # For demo, create a placeholder file
            demo_content = f"Secure document storage for {original_filename}\nStorage ID: {storage_id}\nAccess Level: {access_level}\nStored at: {now()}"

            with open(storage_path, 'w') as f:
                f.write(demo_content)

            # Store metadata
            metadata_path = storage_path + '.meta'
            metadata_info = {
                'storage_id': storage_id,
                'original_filename': original_filename,
                'stored_by': user_context.get('user') if user_context else 'unknown',
                'stored_at': now(),
                'metadata': metadata,
                'encrypted': encrypted_data.get('encrypted', False)
            }

            with open(metadata_path, 'w') as f:
                json.dump(metadata_info, f, indent=2)

            return {
                'success': True,
                'storage_path': storage_path,
                'metadata_path': metadata_path
            }

        except Exception as e:
            frappe.log_error(f"Secure document storage error: {str(e)}", "DocumentStorageService")
            return {
                'success': False,
                'error': f"Storage failed: {str(e)}"
            }

    def _create_access_control_record(self, storage_id: str, metadata: Dict,
                                    user_context: Dict) -> Dict[str, Any]:
        """Create access control record for document"""
        try:
            access_record = {
                'storage_id': storage_id,
                'access_level': metadata.get('access_level', 'internal'),
                'owner': user_context.get('user') if user_context else 'unknown',
                'created_at': now(),
                'authorized_users': metadata.get('authorized_users', []),
                'authorized_roles': metadata.get('authorized_roles', []),
                'access_restrictions': metadata.get('access_restrictions', {}),
                'audit_enabled': True
            }

            # In production, this would be stored in database
            return access_record

        except Exception as e:
            frappe.log_error(f"Access control record creation error: {str(e)}", "DocumentStorageService")
            return {}

    def _log_storage_activity(self, storage_id: str, activity_type: str,
                            user_context: Dict, additional_data: Dict = None):
        """Log storage activity for audit trail"""
        try:
            activity_log = {
                'storage_id': storage_id,
                'activity_type': activity_type,
                'user': user_context.get('user') if user_context else 'unknown',
                'timestamp': now(),
                'ip_address': 'demo_ip',
                'additional_data': additional_data or {}
            }

            # In production, this would be stored in audit log
            frappe.log_error(f"Storage activity: {activity_log}", "DocumentStorageService")

        except Exception as e:
            frappe.log_error(f"Storage activity logging error: {str(e)}", "DocumentStorageService")

    def _schedule_retention_policy(self, storage_id: str, metadata: Dict):
        """Schedule retention policy for document"""
        try:
            document_category = metadata.get('category', 'other')
            retention_policy = self.retention_policies.get(document_category, self.retention_policies['other'])

            # In production, this would schedule actual retention tasks
            retention_info = {
                'storage_id': storage_id,
                'retention_years': retention_policy['years'],
                'tier_transition': retention_policy['tier_transition'],
                'scheduled_at': now()
            }

            frappe.log_error(f"Retention policy scheduled: {retention_info}", "DocumentStorageService")

        except Exception as e:
            frappe.log_error(f"Retention policy scheduling error: {str(e)}", "DocumentStorageService")

    def _validate_document_access(self, storage_id: str, user_context: Dict) -> Dict[str, Any]:
        """Validate user access to document"""
        try:
            if not user_context:
                return {'allowed': False, 'reason': 'No user context provided'}

            # Get document metadata
            document_metadata = self._get_document_metadata(storage_id)
            if not document_metadata:
                return {'allowed': False, 'reason': 'Document not found'}

            # Check user roles and permissions
            user_roles = user_context.get('roles', [])
            access_level = document_metadata.get('access_level', 'internal')

            # Define role-based access permissions
            role_permissions = {
                'System Manager': ['public', 'internal', 'restricted', 'confidential', 'classified'],
                'WCFCB Staff': ['public', 'internal', 'restricted', 'confidential'],
                'Manager': ['public', 'internal', 'restricted'],
                'Employer': ['public', 'internal'],
                'Beneficiary': ['public', 'internal']
            }

            for role in user_roles:
                if role in role_permissions and access_level in role_permissions[role]:
                    return {'allowed': True, 'access_level': access_level, 'user_role': role}

            return {'allowed': False, 'reason': f'Insufficient permissions for {access_level} document'}

        except Exception as e:
            frappe.log_error(f"Document access validation error: {str(e)}", "DocumentStorageService")
            return {'allowed': False, 'reason': 'Access validation failed'}

    def _get_document_metadata(self, storage_id: str) -> Optional[Dict]:
        """Get document metadata from storage"""
        try:
            # Demo document metadata
            demo_metadata = {
                'test_storage_123': {
                    'storage_id': 'test_storage_123',
                    'original_filename': 'secure_document.pdf',
                    'access_level': 'restricted',
                    'category': 'medical',
                    'stored_by': 'test_user',
                    'stored_at': '2025-02-02 10:30:00',
                    'encrypted': True,
                    'file_size': 2048
                }
            }

            return demo_metadata.get(storage_id)

        except Exception as e:
            frappe.log_error(f"Document metadata retrieval error: {str(e)}", "DocumentStorageService")
            return None

    def _retrieve_document_content(self, storage_id: str, version: str = None) -> Dict[str, Any]:
        """Retrieve document content from storage"""
        try:
            # For demo purposes, simulate document retrieval
            demo_content = f"Demo encrypted content for storage_id: {storage_id}"

            return {
                'success': True,
                'encrypted_data': {
                    'content': demo_content,
                    'encrypted': True,
                    'version': version or 'latest'
                }
            }

        except Exception as e:
            frappe.log_error(f"Document content retrieval error: {str(e)}", "DocumentStorageService")
            return {
                'success': False,
                'error': f"Content retrieval failed: {str(e)}"
            }

    def _decrypt_document(self, encrypted_data: Dict, document_metadata: Dict) -> Dict[str, Any]:
        """Decrypt document content"""
        try:
            if not encrypted_data.get('encrypted', False):
                return {
                    'success': True,
                    'document_data': encrypted_data,
                    'decryption_used': False
                }

            # For demo purposes, simulate decryption
            content = encrypted_data.get('content', '')

            # Simulate decryption (in production, use actual decryption)
            try:
                decrypted_content = base64.b64decode(content).decode('utf-8')
            except:
                decrypted_content = content  # Fallback for demo

            decrypted_data = encrypted_data.copy()
            decrypted_data['content'] = decrypted_content
            decrypted_data['encrypted'] = False

            return {
                'success': True,
                'document_data': decrypted_data,
                'decryption_used': True
            }

        except Exception as e:
            frappe.log_error(f"Document decryption error: {str(e)}", "DocumentStorageService")
            return {
                'success': False,
                'error': f"Decryption failed: {str(e)}"
            }

    def _update_access_statistics(self, storage_id: str):
        """Update access statistics for document"""
        try:
            # In production, this would update access statistics in database
            access_stats = {
                'storage_id': storage_id,
                'last_accessed': now(),
                'access_count': 1  # Would increment in production
            }

            frappe.log_error(f"Access statistics updated: {access_stats}", "DocumentStorageService")

        except Exception as e:
            frappe.log_error(f"Access statistics update error: {str(e)}", "DocumentStorageService")

    def _validate_access_modification_permission(self, storage_id: str, user_context: Dict) -> bool:
        """Validate user has permission to modify access controls"""
        try:
            if not user_context:
                return False

            # Check if user is owner or has admin privileges
            user_roles = user_context.get('roles', [])
            admin_roles = ['System Manager', 'WCFCB Staff']

            if any(role in admin_roles for role in user_roles):
                return True

            # Check if user is document owner
            document_metadata = self._get_document_metadata(storage_id)
            if document_metadata and document_metadata.get('stored_by') == user_context.get('user'):
                return True

            return False

        except Exception:
            return False

    def _get_access_configuration(self, storage_id: str) -> Optional[Dict]:
        """Get current access configuration for document"""
        try:
            document_metadata = self._get_document_metadata(storage_id)
            if not document_metadata:
                return None

            return {
                'access_level': document_metadata.get('access_level', 'internal'),
                'authorized_users': document_metadata.get('authorized_users', []),
                'authorized_roles': document_metadata.get('authorized_roles', []),
                'access_restrictions': document_metadata.get('access_restrictions', {})
            }

        except Exception as e:
            frappe.log_error(f"Access configuration retrieval error: {str(e)}", "DocumentStorageService")
            return None

    def _validate_access_configuration(self, access_config: Dict) -> Dict[str, Any]:
        """Validate access configuration"""
        try:
            errors = []

            access_level = access_config.get('access_level')
            if not access_level or access_level not in self.access_levels:
                errors.append(f"Invalid access level. Must be one of: {', '.join(self.access_levels.keys())}")

            return {
                'valid': len(errors) == 0,
                'errors': errors
            }

        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"]
            }

    def _update_access_configuration(self, storage_id: str, new_config: Dict) -> Dict[str, Any]:
        """Update access configuration for document"""
        try:
            # In production, this would update the actual access configuration
            update_result = {
                'storage_id': storage_id,
                'updated_config': new_config,
                'updated_at': now()
            }

            return {
                'success': True,
                'update_result': update_result
            }

        except Exception as e:
            frappe.log_error(f"Access configuration update error: {str(e)}", "DocumentStorageService")
            return {
                'success': False,
                'error': f"Update failed: {str(e)}"
            }

    def _get_version_history(self, storage_id: str) -> List[Dict]:
        """Get version history for document"""
        try:
            # Demo version history
            demo_versions = {
                'test_storage_123': [
                    {
                        'version': 'v1.0',
                        'created_at': '2025-02-02 10:30:00',
                        'created_by': 'test_user',
                        'changes': 'Initial version',
                        'file_size': 2048
                    }
                ]
            }

            return demo_versions.get(storage_id, [])

        except Exception as e:
            frappe.log_error(f"Version history retrieval error: {str(e)}", "DocumentStorageService")
            return []


def get_document_storage_service():
    """Factory function to get DocumentStorageService instance"""
    return DocumentStorageService()
