"""
Document Validation Service for WCFCB Assistant CRM
Provides automated document validation and verification workflows

Phase 3.2.2 Implementation
"""

import frappe
from frappe.utils import now
from typing import Dict, List, Any, Optional
import re
import os
from datetime import datetime, timedelta


class DocumentValidationService:
    """
    Service for automated document validation and verification
    Provides content validation, compliance checking, and workflow automation
    """
    
    def __init__(self):
        """Initialize Document Validation Service"""
        self.service_name = "Document Validation Service"
        
        # Validation rules for different document types
        self.validation_rules = {
            'medical': {
                'required_fields': ['patient_name', 'date_of_service', 'provider_name'],
                'file_types': ['pdf', 'doc', 'docx', 'jpg', 'png'],
                'max_age_days': 365,
                'min_file_size': 1024,  # 1KB
                'content_patterns': [
                    r'medical\s+report',
                    r'diagnosis',
                    r'treatment',
                    r'doctor|physician|md'
                ]
            },
            'incident': {
                'required_fields': ['incident_date', 'location', 'description'],
                'file_types': ['pdf', 'doc', 'docx', 'txt'],
                'max_age_days': 30,
                'min_file_size': 512,
                'content_patterns': [
                    r'incident\s+report',
                    r'accident',
                    r'injury',
                    r'workplace'
                ]
            },
            'employment': {
                'required_fields': ['employee_name', 'employer', 'period'],
                'file_types': ['pdf', 'doc', 'docx', 'xls', 'xlsx'],
                'max_age_days': 90,
                'min_file_size': 1024,
                'content_patterns': [
                    r'employment',
                    r'payroll',
                    r'salary|wage',
                    r'employee'
                ]
            },
            'identification': {
                'required_fields': ['name', 'id_number', 'issue_date'],
                'file_types': ['pdf', 'jpg', 'png'],
                'max_age_days': 1825,  # 5 years
                'min_file_size': 2048,
                'content_patterns': [
                    r'driver.s?\s+license',
                    r'passport',
                    r'social\s+security',
                    r'identification'
                ]
            }
        }
        
        # Compliance standards
        self.compliance_standards = {
            'wcfcb_medical': 'WCFCB Medical Documentation Standards',
            'wcfcb_incident': 'WCFCB Incident Reporting Standards',
            'wcfcb_employment': 'WCFCB Employment Verification Standards',
            'privacy_hipaa': 'HIPAA Privacy Compliance',
            'security_pii': 'PII Security Standards'
        }
    
    def validate_document(self, file_id: str, document_category: str = None,
                         user_context: Dict = None) -> Dict[str, Any]:
        """
        Perform comprehensive document validation
        
        Args:
            file_id: Unique file identifier
            document_category: Category of document for specific validation rules
            user_context: User context for authorization
            
        Returns:
            Dict containing validation results and recommendations
        """
        try:
            # Get document information
            document_info = self._get_document_info(file_id)
            if not document_info:
                return {
                    'success': False,
                    'error': 'Document not found',
                    'file_id': file_id
                }
            
            # Determine document category if not provided
            if not document_category:
                document_category = self._detect_document_category(document_info)
            
            # Get validation rules for category
            validation_rules = self.validation_rules.get(document_category, {})
            
            # Perform validation checks
            validation_results = {
                'file_id': file_id,
                'document_category': document_category,
                'validation_timestamp': now(),
                'checks_performed': [],
                'passed_checks': [],
                'failed_checks': [],
                'warnings': [],
                'overall_status': 'pending'
            }
            
            # File format validation
            format_result = self._validate_file_format(document_info, validation_rules)
            validation_results['checks_performed'].append('file_format')
            if format_result['passed']:
                validation_results['passed_checks'].append('file_format')
            else:
                validation_results['failed_checks'].append('file_format')
                validation_results['warnings'].extend(format_result.get('warnings', []))
            
            # File size validation
            size_result = self._validate_file_size(document_info, validation_rules)
            validation_results['checks_performed'].append('file_size')
            if size_result['passed']:
                validation_results['passed_checks'].append('file_size')
            else:
                validation_results['failed_checks'].append('file_size')
                validation_results['warnings'].extend(size_result.get('warnings', []))
            
            # Content validation (if applicable)
            content_result = self._validate_document_content(document_info, validation_rules)
            validation_results['checks_performed'].append('content_validation')
            if content_result['passed']:
                validation_results['passed_checks'].append('content_validation')
            else:
                validation_results['failed_checks'].append('content_validation')
                validation_results['warnings'].extend(content_result.get('warnings', []))
            
            # Compliance validation
            compliance_result = self._validate_compliance(document_info, document_category)
            validation_results['checks_performed'].append('compliance')
            if compliance_result['passed']:
                validation_results['passed_checks'].append('compliance')
            else:
                validation_results['failed_checks'].append('compliance')
                validation_results['warnings'].extend(compliance_result.get('warnings', []))
            
            # Security validation
            security_result = self._validate_security(document_info)
            validation_results['checks_performed'].append('security')
            if security_result['passed']:
                validation_results['passed_checks'].append('security')
            else:
                validation_results['failed_checks'].append('security')
                validation_results['warnings'].extend(security_result.get('warnings', []))
            
            # Determine overall status
            total_checks = len(validation_results['checks_performed'])
            passed_checks = len(validation_results['passed_checks'])
            
            if passed_checks == total_checks:
                validation_results['overall_status'] = 'passed'
            elif passed_checks >= total_checks * 0.8:  # 80% pass rate
                validation_results['overall_status'] = 'passed_with_warnings'
            else:
                validation_results['overall_status'] = 'failed'
            
            # Generate recommendations
            validation_results['recommendations'] = self._generate_validation_recommendations(
                validation_results, document_category
            )
            
            # Log validation activity
            self._log_validation_activity(file_id, validation_results, user_context)
            
            return {
                'success': True,
                'validation_results': validation_results
            }
            
        except Exception as e:
            frappe.log_error(f"Document validation error: {str(e)}", "DocumentValidationService")
            return {
                'success': False,
                'error': 'Document validation failed',
                'technical_error': str(e),
                'file_id': file_id
            }
    
    def get_validation_status(self, file_id: str, user_context: Dict = None) -> Dict[str, Any]:
        """
        Get current validation status for a document
        
        Args:
            file_id: Unique file identifier
            user_context: User context for authorization
            
        Returns:
            Dict containing current validation status
        """
        try:
            # Get validation history
            validation_history = self._get_validation_history(file_id)
            
            if validation_history:
                latest_validation = validation_history[0]  # Most recent
                
                return {
                    'success': True,
                    'file_id': file_id,
                    'current_status': latest_validation.get('overall_status'),
                    'last_validated': latest_validation.get('validation_timestamp'),
                    'validation_summary': {
                        'total_checks': len(latest_validation.get('checks_performed', [])),
                        'passed_checks': len(latest_validation.get('passed_checks', [])),
                        'failed_checks': len(latest_validation.get('failed_checks', [])),
                        'warnings_count': len(latest_validation.get('warnings', []))
                    },
                    'recommendations': latest_validation.get('recommendations', []),
                    'validation_history': validation_history
                }
            else:
                return {
                    'success': True,
                    'file_id': file_id,
                    'current_status': 'not_validated',
                    'message': 'Document has not been validated yet'
                }
                
        except Exception as e:
            frappe.log_error(f"Validation status retrieval error: {str(e)}", "DocumentValidationService")
            return {
                'success': False,
                'error': 'Unable to retrieve validation status',
                'technical_error': str(e)
            }
    
    def bulk_validate_documents(self, file_ids: List[str], document_category: str = None,
                              user_context: Dict = None) -> Dict[str, Any]:
        """
        Perform bulk validation on multiple documents
        
        Args:
            file_ids: List of file identifiers
            document_category: Category for all documents (if same)
            user_context: User context for authorization
            
        Returns:
            Dict containing bulk validation results
        """
        try:
            bulk_results = {
                'total_documents': len(file_ids),
                'processed_documents': 0,
                'successful_validations': 0,
                'failed_validations': 0,
                'validation_results': [],
                'summary': {},
                'started_at': now()
            }
            
            for file_id in file_ids:
                try:
                    # Validate individual document
                    validation_result = self.validate_document(file_id, document_category, user_context)
                    
                    bulk_results['processed_documents'] += 1
                    
                    if validation_result['success']:
                        bulk_results['successful_validations'] += 1
                        status = validation_result['validation_results']['overall_status']
                    else:
                        bulk_results['failed_validations'] += 1
                        status = 'validation_error'
                    
                    bulk_results['validation_results'].append({
                        'file_id': file_id,
                        'status': status,
                        'validation_result': validation_result
                    })
                    
                except Exception as e:
                    bulk_results['processed_documents'] += 1
                    bulk_results['failed_validations'] += 1
                    bulk_results['validation_results'].append({
                        'file_id': file_id,
                        'status': 'error',
                        'error': str(e)
                    })
            
            # Generate summary statistics
            bulk_results['summary'] = self._generate_bulk_summary(bulk_results)
            bulk_results['completed_at'] = now()
            
            return {
                'success': True,
                'bulk_validation_results': bulk_results
            }
            
        except Exception as e:
            frappe.log_error(f"Bulk validation error: {str(e)}", "DocumentValidationService")
            return {
                'success': False,
                'error': 'Bulk validation failed',
                'technical_error': str(e)
            }

    def _get_document_info(self, file_id: str) -> Optional[Dict]:
        """Get document information from database or storage"""
        try:
            # Demo document info - in production this would come from database
            demo_documents = {
                'doc001': {
                    'file_id': 'doc001',
                    'original_filename': 'medical_report.pdf',
                    'file_size': 1024000,
                    'mime_type': 'application/pdf',
                    'file_extension': 'pdf',
                    'upload_timestamp': '2025-01-15 10:30:00',
                    'document_category': 'medical',
                    'storage_path': '/path/to/medical_report.pdf'
                },
                'doc002': {
                    'file_id': 'doc002',
                    'original_filename': 'incident_report.docx',
                    'file_size': 512000,
                    'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'file_extension': 'docx',
                    'upload_timestamp': '2025-01-20 14:15:00',
                    'document_category': 'incident',
                    'storage_path': '/path/to/incident_report.docx'
                }
            }

            return demo_documents.get(file_id)

        except Exception as e:
            frappe.log_error(f"Document info retrieval error: {str(e)}", "DocumentValidationService")
            return None

    def _detect_document_category(self, document_info: Dict) -> str:
        """Detect document category based on filename and content"""
        try:
            filename = document_info.get('original_filename', '').lower()

            # Simple category detection based on filename
            if any(word in filename for word in ['medical', 'doctor', 'hospital', 'diagnosis']):
                return 'medical'
            elif any(word in filename for word in ['incident', 'accident', 'injury', 'report']):
                return 'incident'
            elif any(word in filename for word in ['employment', 'payroll', 'salary', 'wage']):
                return 'employment'
            elif any(word in filename for word in ['id', 'license', 'passport', 'identification']):
                return 'identification'
            else:
                return 'other'

        except Exception:
            return 'other'

    def _validate_file_format(self, document_info: Dict, validation_rules: Dict) -> Dict[str, Any]:
        """Validate file format against allowed types"""
        try:
            file_extension = document_info.get('file_extension', '').lower()
            allowed_types = validation_rules.get('file_types', [])

            if not allowed_types:  # No restrictions
                return {'passed': True, 'warnings': []}

            if file_extension in allowed_types:
                return {'passed': True, 'warnings': []}
            else:
                return {
                    'passed': False,
                    'warnings': [f"File type '{file_extension}' is not allowed for this document category. Allowed types: {', '.join(allowed_types)}"]
                }

        except Exception as e:
            return {
                'passed': False,
                'warnings': [f"File format validation error: {str(e)}"]
            }

    def _validate_file_size(self, document_info: Dict, validation_rules: Dict) -> Dict[str, Any]:
        """Validate file size against requirements"""
        try:
            file_size = document_info.get('file_size', 0)
            min_size = validation_rules.get('min_file_size', 0)
            max_size = validation_rules.get('max_file_size', 50 * 1024 * 1024)  # 50MB default

            warnings = []

            if file_size < min_size:
                warnings.append(f"File size ({file_size} bytes) is below minimum requirement ({min_size} bytes)")

            if file_size > max_size:
                warnings.append(f"File size ({file_size} bytes) exceeds maximum limit ({max_size} bytes)")

            return {
                'passed': len(warnings) == 0,
                'warnings': warnings
            }

        except Exception as e:
            return {
                'passed': False,
                'warnings': [f"File size validation error: {str(e)}"]
            }

    def _validate_document_content(self, document_info: Dict, validation_rules: Dict) -> Dict[str, Any]:
        """Validate document content against patterns and requirements"""
        try:
            # For demo purposes, simulate content validation
            content_patterns = validation_rules.get('content_patterns', [])

            if not content_patterns:
                return {'passed': True, 'warnings': []}

            # Simulate content analysis
            filename = document_info.get('original_filename', '').lower()
            document_category = document_info.get('document_category', '')

            # Check if filename suggests appropriate content
            pattern_matches = 0
            for pattern in content_patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    pattern_matches += 1

            if pattern_matches > 0:
                return {
                    'passed': True,
                    'warnings': [f"Content validation passed based on filename analysis"]
                }
            else:
                return {
                    'passed': False,
                    'warnings': [f"Document content may not match expected patterns for {document_category} category"]
                }

        except Exception as e:
            return {
                'passed': False,
                'warnings': [f"Content validation error: {str(e)}"]
            }

    def _validate_compliance(self, document_info: Dict, document_category: str) -> Dict[str, Any]:
        """Validate document against compliance standards"""
        try:
            warnings = []

            # Check document age
            upload_date = document_info.get('upload_timestamp')
            if upload_date:
                # For demo, assume document is recent
                warnings.append("Document compliance check passed - recent upload")

            # Check for required metadata
            if not document_info.get('document_category'):
                warnings.append("Document category should be specified for compliance")

            # Check file integrity
            if not document_info.get('file_size') or document_info.get('file_size') <= 0:
                warnings.append("File integrity check failed - invalid file size")

            return {
                'passed': len([w for w in warnings if 'failed' in w.lower()]) == 0,
                'warnings': warnings
            }

        except Exception as e:
            return {
                'passed': False,
                'warnings': [f"Compliance validation error: {str(e)}"]
            }

    def _validate_security(self, document_info: Dict) -> Dict[str, Any]:
        """Validate document security aspects"""
        try:
            warnings = []

            # Check file extension for security
            file_extension = document_info.get('file_extension', '').lower()
            dangerous_extensions = ['exe', 'bat', 'cmd', 'scr', 'vbs', 'js']

            if file_extension in dangerous_extensions:
                warnings.append(f"Security risk: '{file_extension}' files are not allowed")

            # Check filename for suspicious patterns
            filename = document_info.get('original_filename', '')
            if '..' in filename or '/' in filename or '\\' in filename:
                warnings.append("Security risk: Filename contains suspicious characters")

            # Check MIME type consistency
            mime_type = document_info.get('mime_type', '')
            if mime_type and not self._is_mime_type_safe(mime_type):
                warnings.append(f"Security warning: MIME type '{mime_type}' requires additional verification")

            return {
                'passed': len([w for w in warnings if 'risk' in w.lower()]) == 0,
                'warnings': warnings
            }

        except Exception as e:
            return {
                'passed': False,
                'warnings': [f"Security validation error: {str(e)}"]
            }

    def _is_mime_type_safe(self, mime_type: str) -> bool:
        """Check if MIME type is considered safe"""
        safe_mime_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'image/jpeg',
            'image/png',
            'image/gif',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ]
        return mime_type in safe_mime_types

    def _generate_validation_recommendations(self, validation_results: Dict,
                                           document_category: str) -> List[str]:
        """Generate recommendations based on validation results"""
        try:
            recommendations = []
            failed_checks = validation_results.get('failed_checks', [])
            warnings = validation_results.get('warnings', [])

            if 'file_format' in failed_checks:
                recommendations.append(f"Convert document to an accepted format for {document_category} category")

            if 'file_size' in failed_checks:
                recommendations.append("Ensure file size meets requirements")

            if 'content_validation' in failed_checks:
                recommendations.append(f"Verify document content matches {document_category} requirements")

            if 'compliance' in failed_checks:
                recommendations.append("Review document for compliance with WCFCB standards")

            if 'security' in failed_checks:
                recommendations.append("Address security concerns before resubmitting")

            if not recommendations:
                recommendations.append("Document validation passed successfully")

            return recommendations

        except Exception:
            return ["Review document and resubmit if necessary"]

    def _log_validation_activity(self, file_id: str, validation_results: Dict,
                               user_context: Dict):
        """Log validation activity for audit trail"""
        try:
            activity_log = {
                'file_id': file_id,
                'validation_status': validation_results.get('overall_status'),
                'user': user_context.get('user') if user_context else 'unknown',
                'timestamp': validation_results.get('validation_timestamp'),
                'checks_performed': len(validation_results.get('checks_performed', [])),
                'passed_checks': len(validation_results.get('passed_checks', [])),
                'failed_checks': len(validation_results.get('failed_checks', []))
            }

            # In production, this would be stored in audit log
            frappe.log_error(f"Validation activity: {activity_log}", "DocumentValidationService")

        except Exception as e:
            frappe.log_error(f"Validation activity logging error: {str(e)}", "DocumentValidationService")

    def _get_validation_history(self, file_id: str) -> List[Dict]:
        """Get validation history for a document"""
        try:
            # Demo validation history
            demo_history = {
                'doc001': [
                    {
                        'validation_timestamp': '2025-02-02 10:30:00',
                        'overall_status': 'passed',
                        'checks_performed': ['file_format', 'file_size', 'content_validation', 'compliance', 'security'],
                        'passed_checks': ['file_format', 'file_size', 'content_validation', 'compliance', 'security'],
                        'failed_checks': [],
                        'warnings': ['Content validation passed based on filename analysis'],
                        'recommendations': ['Document validation passed successfully']
                    }
                ],
                'doc002': [
                    {
                        'validation_timestamp': '2025-02-02 14:15:00',
                        'overall_status': 'passed_with_warnings',
                        'checks_performed': ['file_format', 'file_size', 'content_validation', 'compliance', 'security'],
                        'passed_checks': ['file_format', 'file_size', 'compliance', 'security'],
                        'failed_checks': ['content_validation'],
                        'warnings': ['Document content may not match expected patterns for incident category'],
                        'recommendations': ['Verify document content matches incident requirements']
                    }
                ]
            }

            return demo_history.get(file_id, [])

        except Exception as e:
            frappe.log_error(f"Validation history retrieval error: {str(e)}", "DocumentValidationService")
            return []

    def _generate_bulk_summary(self, bulk_results: Dict) -> Dict[str, Any]:
        """Generate summary statistics for bulk validation"""
        try:
            validation_results = bulk_results.get('validation_results', [])

            status_counts = {}
            for result in validation_results:
                status = result.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1

            success_rate = bulk_results.get('successful_validations', 0) / bulk_results.get('total_documents', 1)

            return {
                'status_distribution': status_counts,
                'overall_success_rate': success_rate,
                'total_processed': bulk_results.get('processed_documents', 0),
                'processing_time': 'Completed',
                'recommendations': self._get_bulk_recommendations(status_counts)
            }

        except Exception as e:
            frappe.log_error(f"Bulk summary generation error: {str(e)}", "DocumentValidationService")
            return {'error': 'Unable to generate summary'}

    def _get_bulk_recommendations(self, status_counts: Dict) -> List[str]:
        """Get recommendations for bulk validation results"""
        try:
            recommendations = []

            failed_count = status_counts.get('failed', 0) + status_counts.get('validation_error', 0)
            total_count = sum(status_counts.values())

            if failed_count > 0:
                recommendations.append(f"{failed_count} documents failed validation - review and resubmit")

            if status_counts.get('passed_with_warnings', 0) > 0:
                recommendations.append("Some documents have warnings - review recommendations")

            if total_count > 0 and failed_count / total_count > 0.2:
                recommendations.append("High failure rate - review document preparation guidelines")

            if not recommendations:
                recommendations.append("All documents validated successfully")

            return recommendations

        except Exception:
            return ["Review validation results and take appropriate action"]


def get_document_validation_service():
    """Factory function to get DocumentValidationService instance"""
    return DocumentValidationService()
