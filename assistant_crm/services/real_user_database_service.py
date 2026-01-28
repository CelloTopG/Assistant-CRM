# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

# Safe imports
try:
    import frappe
    from frappe.utils import now, add_to_date, cstr
    from frappe import _
    FRAPPE_AVAILABLE = True
except ImportError:
    frappe = None
    now = lambda: datetime.now().isoformat()
    add_to_date = lambda date, **kwargs: date + timedelta(**kwargs)
    cstr = str
    _ = lambda x: x
    FRAPPE_AVAILABLE = False

def safe_log_error(message: str, title: str = "Real User Database Service"):
    """Safe error logging function"""
    try:
        if frappe:
            frappe.log_error(message, title)
        else:
            print(f"[{title}] {message}")
    except:
        print(f"[{title}] {message}")

class RealUserDatabaseService:
    """
    Phase 2: Real User Database Integration Framework
    
    Provides secure connection to actual WCFCB user systems with:
    - Live credential verification
    - Secure session management
    - Role-based access control
    - Audit logging
    - Data privacy compliance
    """
    
    def __init__(self):
        self.connection_timeout = 30  # seconds
        self.max_retry_attempts = 3
        self.session_timeout_minutes = 30
        self.encryption_key = self._get_encryption_key()
        
        # User role permissions mapping
        self.role_permissions = {
            'beneficiary': [
                'view_own_claims', 'view_own_payments', 'view_own_account',
                'submit_claims', 'update_contact_info', 'view_documents'
            ],
            'employer': [
                'view_company_claims', 'view_premium_payments', 'register_employees',
                'submit_incident_reports', 'view_company_account', 'manage_employees'
            ],
            'supplier': [
                'view_vendor_payments', 'view_contracts', 'submit_invoices',
                'update_vendor_info', 'view_payment_schedule'
            ],
            'wcfcb_staff': [
                'view_all_claims', 'process_claims', 'manage_payments',
                'access_reports', 'manage_users', 'system_administration'
            ]
        }
        
        # Database connection configurations
        self.database_configs = {
            'primary': {
                'host': self._get_config('primary_db_host', 'localhost'),
                'port': self._get_config('primary_db_port', 5432),
                'database': self._get_config('primary_db_name', 'wcfcb_main'),
                'ssl_required': True
            },
            'claims': {
                'host': self._get_config('claims_db_host', 'localhost'),
                'port': self._get_config('claims_db_port', 5432),
                'database': self._get_config('claims_db_name', 'wcfcb_claims'),
                'ssl_required': True
            },
            'payments': {
                'host': self._get_config('payments_db_host', 'localhost'),
                'port': self._get_config('payments_db_port', 5432),
                'database': self._get_config('payments_db_name', 'wcfcb_payments'),
                'ssl_required': True
            }
        }

    def authenticate_user(self, national_id: str, reference_number: str, 
                         user_type: str = 'beneficiary') -> Dict[str, Any]:
        """
        Authenticate user against real WCFCB database systems.
        
        Args:
            national_id (str): User's national ID number
            reference_number (str): Claim number, account number, or other reference
            user_type (str): Type of user (beneficiary, employer, supplier, staff)
        
        Returns:
            Dict containing authentication result and user profile
        """
        try:
            # Input validation
            if not self._validate_credentials(national_id, reference_number, user_type):
                return {
                    'success': False,
                    'error': 'invalid_credentials',
                    'message': 'Invalid credential format provided.'
                }
            
            # Check rate limiting
            if not self._check_rate_limit(national_id):
                return {
                    'success': False,
                    'error': 'rate_limited',
                    'message': 'Too many authentication attempts. Please try again later.'
                }
            
            # Perform database authentication
            auth_result = self._perform_database_authentication(
                national_id, reference_number, user_type
            )
            
            if auth_result['success']:
                # Create secure session
                session_data = self._create_secure_session(auth_result['user_profile'])
                
                # Log successful authentication
                self._log_authentication_event(national_id, user_type, 'success')
                
                return {
                    'success': True,
                    'user_profile': auth_result['user_profile'],
                    'session_data': session_data,
                    'permissions': self.role_permissions.get(user_type, []),
                    'authentication_method': 'database_verified'
                }
            else:
                # Log failed authentication
                self._log_authentication_event(national_id, user_type, 'failed')
                
                return {
                    'success': False,
                    'error': auth_result.get('error', 'authentication_failed'),
                    'message': 'Unable to verify your credentials. Please check your information and try again.'
                }
                
        except Exception as e:
            safe_log_error(f"Authentication error for {national_id}: {str(e)}")
            return {
                'success': False,
                'error': 'system_error',
                'message': 'Authentication system temporarily unavailable. Please try again later.'
            }

    def _validate_credentials(self, national_id: str, reference_number: str, user_type: str) -> bool:
        """Validate credential formats before database lookup."""
        
        # National ID validation (6-12 digits)
        if not national_id or not national_id.isdigit() or len(national_id) < 6 or len(national_id) > 12:
            return False
        
        # Reference number validation based on user type
        if user_type == 'beneficiary':
            # Claim numbers: CL-YYYY-NNNNNN or Account numbers: ACC-NNNNNNNN
            if not (reference_number.startswith(('CL-', 'ACC-', 'BN-')) and len(reference_number) >= 8):
                return False
        elif user_type == 'employer':
            # Employer IDs: EMP-NNNNNNNN or Business registration: BUS-NNNNNNNN
            if not (reference_number.startswith(('EMP-', 'BUS-')) and len(reference_number) >= 10):
                return False
        elif user_type == 'supplier':
            # Vendor IDs: VEN-NNNNNNNN
            if not (reference_number.startswith('VEN-') and len(reference_number) >= 10):
                return False
        
        return True

    def _perform_database_authentication(self, national_id: str, reference_number: str, 
                                       user_type: str) -> Dict[str, Any]:
        """
        Perform actual database authentication.
        In production, this would connect to real WCFCB databases.
        """
        try:
            # Phase 2: Simulated database authentication for development
            # In production, replace with actual database queries
            
            if user_type == 'beneficiary':
                return self._authenticate_beneficiary(national_id, reference_number)
            elif user_type == 'employer':
                return self._authenticate_employer(national_id, reference_number)
            elif user_type == 'supplier':
                return self._authenticate_supplier(national_id, reference_number)
            elif user_type == 'wcfcb_staff':
                return self._authenticate_staff(national_id, reference_number)
            else:
                return {
                    'success': False,
                    'error': 'invalid_user_type'
                }
                
        except Exception as e:
            safe_log_error(f"Database authentication error: {str(e)}")
            return {
                'success': False,
                'error': 'database_error'
            }

    def _authenticate_beneficiary(self, national_id: str, reference_number: str) -> Dict[str, Any]:
        """Authenticate beneficiary.

        NOTE: Beneficiary Profile doctype has been removed.
        Beneficiary data is now managed externally.
        """
        # NOTE: Beneficiary Profile doctype has been removed - beneficiary data managed externally
        _ = national_id  # Unused - doctype removed
        _ = reference_number  # Unused - doctype removed
        return {
            'success': False,
            'error': 'beneficiary_data_external'
        }

    def _authenticate_employer(self, national_id: str, reference_number: str) -> Dict[str, Any]:
        """Authenticate employer against ERPNext Customer database.

        NOTE: Employer Profile doctype has been removed.
        Using ERPNext Customer (customer_type='Company') instead.
        """
        try:
            # LIVE DATA: Query ERPNext Customer doctype (replaces Employer Profile)
            # reference_number is expected to be the customer name or customer code
            customers = frappe.get_all(
                "Customer",
                filters={
                    "customer_type": "Company",
                    "name": reference_number
                },
                fields=[
                    "name", "customer_name", "customer_type", "customer_group",
                    "territory", "email_id", "mobile_no", "primary_address"
                ]
            )

            # Fallback: Try matching by customer_name if name doesn't match
            if not customers:
                customers = frappe.get_all(
                    "Customer",
                    filters={
                        "customer_type": "Company",
                        "customer_name": ["like", f"%{reference_number}%"]
                    },
                    fields=[
                        "name", "customer_name", "customer_type", "customer_group",
                        "territory", "email_id", "mobile_no", "primary_address"
                    ],
                    limit=1
                )

            if not customers:
                return {
                    'success': False,
                    'error': 'employer_not_found'
                }

            customer = customers[0]

            # LIVE DATA: Create authenticated employer profile from ERPNext Customer
            return {
                'success': True,
                'user_profile': {
                    'user_id': national_id,
                    'user_role': 'employer',
                    'user_type': 'authenticated',
                    'full_name': f"Contact Person ({national_id})",
                    'company_name': customer.get('customer_name'),
                    'employer_code': customer.get('name'),
                    'email': customer.get('email_id'),
                    'phone': customer.get('mobile_no'),
                    'industry_sector': customer.get('customer_group'),
                    'territory': customer.get('territory'),
                    'account_status': 'active',
                    'verification_level': 'business_verified',
                    'authentication_method': 'live_database'
                }
            }

        except Exception as e:
            safe_log_error(f"Live employer authentication error: {str(e)}")
            return {
                'success': False,
                'error': 'database_error'
            }

    def _authenticate_supplier(self, national_id: str, reference_number: str) -> Dict[str, Any]:
        """Authenticate supplier against vendor database."""
        
        # Simulated supplier authentication
        if national_id.startswith('3') and reference_number.startswith('VEN-'):
            return {
                'success': True,
                'user_profile': {
                    'user_id': national_id,
                    'user_role': 'supplier',
                    'user_type': 'authenticated',
                    'full_name': f'Vendor Contact ({national_id})',
                    'vendor_id': reference_number,
                    'contract_start': '2021-06-01',
                    'account_status': 'active',
                    'verification_level': 'vendor_verified'
                }
            }
        else:
            return {
                'success': False,
                'error': 'supplier_not_found'
            }

    def _authenticate_staff(self, national_id: str, reference_number: str) -> Dict[str, Any]:
        """Authenticate WCFCB staff against employee database."""
        
        # Simulated staff authentication
        if national_id.startswith('9') and reference_number.startswith('STAFF-'):
            return {
                'success': True,
                'user_profile': {
                    'user_id': national_id,
                    'user_role': 'wcfcb_staff',
                    'user_type': 'authenticated',
                    'full_name': f'WCFCB Staff ({national_id})',
                    'employee_id': reference_number,
                    'department': 'Claims Processing',
                    'hire_date': '2018-09-15',
                    'account_status': 'active',
                    'verification_level': 'staff_verified'
                }
            }
        else:
            return {
                'success': False,
                'error': 'staff_not_found'
            }

    def _create_secure_session(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Create secure session data for authenticated user."""
        
        session_id = self._generate_session_id()
        session_token = self._generate_session_token(user_profile['user_id'])
        
        session_data = {
            'session_id': session_id,
            'session_token': session_token,
            'user_id': user_profile['user_id'],
            'created_at': now(),
            'expires_at': add_to_date(datetime.now(), minutes=self.session_timeout_minutes).isoformat(),
            'last_activity': now(),
            'ip_address': self._get_client_ip(),
            'user_agent': self._get_user_agent()
        }
        
        # Store session in secure storage (in production: Redis/Database)
        self._store_session(session_id, session_data)
        
        return session_data

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        import uuid
        return str(uuid.uuid4())

    def _generate_session_token(self, user_id: str) -> str:
        """Generate secure session token."""
        timestamp = str(int(time.time()))
        data = f"{user_id}:{timestamp}:{self.encryption_key}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _get_encryption_key(self) -> str:
        """Get encryption key for session security."""
        return self._get_config('session_encryption_key', 'default_dev_key_change_in_production')

    def _get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value safely."""
        try:
            if frappe:
                return frappe.conf.get(key, default)
            else:
                return default
        except:
            return default

    def _check_rate_limit(self, national_id: str) -> bool:
        """Check authentication rate limiting."""
        # In production: implement Redis-based rate limiting
        return True

    def _validate_claim_reference(self, national_id: str, reference_number: str) -> bool:
        """Validate claim reference number against Claims Tracking database."""

        try:
            # LIVE DATA: Check if reference number exists in Claims Tracking
            claims = frappe.get_all(
                "Claims Tracking",
                filters={
                    "claim_id": reference_number,
                    "beneficiary": national_id  # Assuming beneficiary field stores NRC
                },
                fields=["name", "claim_id", "status"]
            )

            return len(claims) > 0

        except Exception as e:
            safe_log_error(f"Claim reference validation error: {str(e)}")
            return False

    def _log_authentication_event(self, national_id: str, user_type: str, result: str):
        """Log authentication events for audit trail."""
        try:
            log_data = {
                'timestamp': now(),
                'national_id_hash': hashlib.sha256(national_id.encode()).hexdigest()[:16],
                'user_type': user_type,
                'result': result,
                'ip_address': self._get_client_ip()
            }
            safe_log_error(f"Authentication event: {json.dumps(log_data)}", "Authentication Audit")
        except Exception as e:
            safe_log_error(f"Failed to log authentication event: {str(e)}")

    def _get_client_ip(self) -> str:
        """Get client IP address safely."""
        try:
            if frappe and hasattr(frappe, 'local') and hasattr(frappe.local, 'request'):
                return frappe.local.request.environ.get('REMOTE_ADDR', 'unknown')
            return 'unknown'
        except:
            return 'unknown'

    def _get_user_agent(self) -> str:
        """Get user agent safely."""
        try:
            if frappe and hasattr(frappe, 'local') and hasattr(frappe.local, 'request'):
                return frappe.local.request.environ.get('HTTP_USER_AGENT', 'unknown')
            return 'unknown'
        except:
            return 'unknown'

    def _store_session(self, session_id: str, session_data: Dict[str, Any]):
        """Store session data securely."""
        # In production: store in Redis or secure database
        if not hasattr(self, '_sessions'):
            self._sessions = {}
        self._sessions[session_id] = session_data

    def validate_session(self, session_id: str, session_token: str) -> Dict[str, Any]:
        """Validate existing session."""
        try:
            if not hasattr(self, '_sessions') or session_id not in self._sessions:
                return {'valid': False, 'error': 'session_not_found'}
            
            session_data = self._sessions[session_id]
            
            # Check expiration
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            if datetime.now() > expires_at:
                return {'valid': False, 'error': 'session_expired'}
            
            # Validate token
            if session_data['session_token'] != session_token:
                return {'valid': False, 'error': 'invalid_token'}
            
            # Update last activity
            session_data['last_activity'] = now()
            
            return {
                'valid': True,
                'session_data': session_data
            }
            
        except Exception as e:
            safe_log_error(f"Session validation error: {str(e)}")
            return {'valid': False, 'error': 'validation_error'}
