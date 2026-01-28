#!/usr/bin/env python3
"""
Phase 4: User Identification Service
===================================

Enhanced user identification and role-based access control system for WCFCB Assistant CRM.
Integrates with CoreBusiness API for user data retrieval and implements comprehensive
role-based access control for beneficiaries, employers, suppliers, and WCFCB staff.

Features:
- CoreBusiness API integration for user data retrieval
- Role-based access control system
- User context management and validation
- Permission-based data filtering
- Secure user identification workflows
"""

import frappe
from frappe import _
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from frappe.utils import now, get_datetime, cstr

# Safe imports for standalone operation
try:
    from assistant_crm.services.corebusiness_integration_service import CoreBusinessIntegrationService
    from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService
    from assistant_crm.services.security_service import SecurityService
except ImportError:
    # Fallback for when services are not available
    CoreBusinessIntegrationService = None
    LiveDataRetrievalService = None
    SecurityService = None


class UserIdentificationService:
    """
    Phase 4: Enhanced User Identification Service
    
    Provides comprehensive user identification, role-based access control,
    and CoreBusiness API integration for WCFCB Assistant CRM.
    """
    
    def __init__(self):
        self.service_name = "User Identification Service"
        self.version = "4.0.0"
        
        # Initialize dependent services
        self.corebusiness_service = CoreBusinessIntegrationService() if CoreBusinessIntegrationService else None
        self.live_data_service = LiveDataRetrievalService() if LiveDataRetrievalService else None
        self.security_service = SecurityService() if SecurityService else None
        
        # User role definitions
        self.user_roles = {
            'beneficiary': {
                'permissions': ['view_own_data', 'submit_claims', 'view_payments', 'update_contact_info'],
                'data_access': ['personal_info', 'benefit_info', 'payment_history', 'claim_status'],
                'api_endpoints': ['beneficiaries', 'payments', 'claims']
            },
            'employer': {
                'permissions': ['view_company_data', 'submit_returns', 'view_contributions', 'manage_employees'],
                'data_access': ['company_info', 'employee_list', 'contribution_history', 'compliance_status'],
                'api_endpoints': ['employers', 'contributions', 'compliance', 'employees']
            },
            'supplier': {
                'permissions': ['view_contracts', 'submit_invoices', 'view_payments'],
                'data_access': ['contract_info', 'invoice_history', 'payment_status'],
                'api_endpoints': ['suppliers', 'contracts', 'invoices']
            },
            'wcfcb_staff': {
                'permissions': ['view_all_data', 'manage_claims', 'generate_reports', 'admin_functions'],
                'data_access': ['all_data'],
                'api_endpoints': ['all_endpoints']
            }
        }
    
    def identify_user(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 4: Enhanced user identification with CoreBusiness integration
        
        Args:
            user_context: User context containing identification information
            
        Returns:
            Enhanced user profile with role-based permissions
        """
        try:
            # Extract identification information
            user_id = user_context.get('user_id')
            user_role = user_context.get('user_role', 'beneficiary')
            
            if not user_id:
                return self._create_anonymous_user_profile()
            
            # Attempt CoreBusiness API lookup
            user_profile = self._lookup_user_in_corebusiness(user_id, user_role)
            
            if not user_profile:
                # Fallback to local database lookup
                user_profile = self._lookup_user_locally(user_id, user_role)
            
            if not user_profile:
                return self._create_guest_user_profile(user_id, user_role)
            
            # Enhance profile with role-based permissions
            enhanced_profile = self._enhance_user_profile(user_profile, user_role)
            
            # Log user identification for analytics
            self._log_user_identification(enhanced_profile)
            
            return enhanced_profile
            
        except Exception as e:
            frappe.log_error(f"User identification error: {str(e)}", "User Identification Service")
            return self._create_error_user_profile(str(e))
    
    def _lookup_user_in_corebusiness(self, user_id: str, user_role: str) -> Optional[Dict[str, Any]]:
        """Lookup user in CoreBusiness API"""
        try:
            if not self.corebusiness_service or not self.corebusiness_service.is_available():
                return None
            
            # Determine API endpoint based on user role
            if user_role == 'beneficiary':
                return self.corebusiness_service.get_beneficiary_data(user_id)
            elif user_role == 'employer':
                return self.corebusiness_service.get_employer_data(user_id)
            elif user_role == 'supplier':
                return self.corebusiness_service.get_supplier_data(user_id)
            elif user_role == 'wcfcb_staff':
                return self.corebusiness_service.get_staff_data(user_id)
            
            return None
            
        except Exception as e:
            frappe.log_error(f"CoreBusiness lookup error: {str(e)}", "User Identification Service")
            return None
    
    def _lookup_user_locally(self, user_id: str, user_role: str) -> Optional[Dict[str, Any]]:
        """Lookup user in local database.

        NOTE: Using ERPNext doctypes (Beneficiary/Employer/Employee Profile removed).
        """
        try:
            if user_role == 'beneficiary':
                # NOTE: Beneficiary Profile removed - beneficiary data managed externally
                return None
            elif user_role == 'employer':
                # Using ERPNext Customer (Employer Profile removed)
                return frappe.db.get_value('Customer', {"name": user_id, "customer_type": "Company"}, '*', as_dict=True)
            elif user_role == 'employee':
                # Using ERPNext Employee (Employee Profile removed)
                return frappe.db.get_value('Employee', user_id, '*', as_dict=True)

            return None

        except Exception as e:
            frappe.log_error(f"Local lookup error: {str(e)}", "User Identification Service")
            return None
    
    def _enhance_user_profile(self, user_profile: Dict[str, Any], user_role: str) -> Dict[str, Any]:
        """Enhance user profile with role-based permissions and access control"""
        role_config = self.user_roles.get(user_role, self.user_roles['beneficiary'])
        
        enhanced_profile = {
            'user_id': user_profile.get('beneficiary_number') or user_profile.get('employer_number') or user_profile.get('employee_number'),
            'user_role': user_role,
            'user_type': user_role,
            'full_name': user_profile.get('full_name') or f"{user_profile.get('first_name', '')} {user_profile.get('last_name', '')}".strip(),
            'email': user_profile.get('email'),
            'phone': user_profile.get('phone') or user_profile.get('mobile'),
            'permissions': role_config['permissions'],
            'data_access': role_config['data_access'],
            'api_endpoints': role_config['api_endpoints'],
            'profile_data': user_profile,
            'identification_method': 'corebusiness_api' if self.corebusiness_service else 'local_database',
            'identification_timestamp': now(),
            'session_permissions': self._generate_session_permissions(role_config)
        }
        
        return enhanced_profile
    
    def _generate_session_permissions(self, role_config: Dict[str, Any]) -> Dict[str, bool]:
        """Generate session-specific permissions"""
        return {
            'can_view_personal_data': 'view_own_data' in role_config['permissions'],
            'can_submit_claims': 'submit_claims' in role_config['permissions'],
            'can_view_payments': 'view_payments' in role_config['permissions'],
            'can_manage_employees': 'manage_employees' in role_config['permissions'],
            'can_access_admin_functions': 'admin_functions' in role_config['permissions'],
            'can_generate_reports': 'generate_reports' in role_config['permissions']
        }
    
    def _create_anonymous_user_profile(self) -> Dict[str, Any]:
        """Create profile for anonymous users"""
        return {
            'user_id': 'anonymous',
            'user_role': 'anonymous',
            'user_type': 'anonymous',
            'full_name': 'Anonymous User',
            'permissions': ['view_public_info'],
            'data_access': ['public_info'],
            'api_endpoints': ['public_endpoints'],
            'identification_method': 'anonymous',
            'identification_timestamp': now(),
            'session_permissions': {
                'can_view_personal_data': False,
                'can_submit_claims': False,
                'can_view_payments': False,
                'can_manage_employees': False,
                'can_access_admin_functions': False,
                'can_generate_reports': False
            }
        }
    
    def _create_guest_user_profile(self, user_id: str, user_role: str) -> Dict[str, Any]:
        """Create profile for guest users with limited access"""
        return {
            'user_id': user_id,
            'user_role': user_role,
            'user_type': 'guest',
            'full_name': f'Guest User ({user_id})',
            'permissions': ['view_public_info', 'basic_inquiries'],
            'data_access': ['public_info'],
            'api_endpoints': ['public_endpoints'],
            'identification_method': 'guest',
            'identification_timestamp': now(),
            'session_permissions': {
                'can_view_personal_data': False,
                'can_submit_claims': False,
                'can_view_payments': False,
                'can_manage_employees': False,
                'can_access_admin_functions': False,
                'can_generate_reports': False
            }
        }
    
    def _create_error_user_profile(self, error_message: str) -> Dict[str, Any]:
        """Create profile for error scenarios"""
        return {
            'user_id': 'error',
            'user_role': 'error',
            'user_type': 'error',
            'full_name': 'Error User',
            'permissions': [],
            'data_access': [],
            'api_endpoints': [],
            'identification_method': 'error',
            'identification_timestamp': now(),
            'error_message': error_message,
            'session_permissions': {
                'can_view_personal_data': False,
                'can_submit_claims': False,
                'can_view_payments': False,
                'can_manage_employees': False,
                'can_access_admin_functions': False,
                'can_generate_reports': False
            }
        }
    
    def _log_user_identification(self, user_profile: Dict[str, Any]) -> None:
        """Log user identification for analytics and security"""
        try:
            if frappe:
                frappe.log_error(
                    f"User identified: {user_profile.get('user_id')} ({user_profile.get('user_role')}) via {user_profile.get('identification_method')}",
                    "User Identification Log"
                )
        except:
            pass
    
    def validate_user_permissions(self, user_profile: Dict[str, Any], required_permission: str) -> bool:
        """Validate if user has required permission"""
        user_permissions = user_profile.get('permissions', [])
        return required_permission in user_permissions or 'admin_functions' in user_permissions
    
    def filter_data_by_permissions(self, user_profile: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter data based on user permissions"""
        user_data_access = user_profile.get('data_access', [])
        
        if 'all_data' in user_data_access:
            return data
        
        filtered_data = {}
        for key, value in data.items():
            if any(access in key.lower() for access in user_data_access):
                filtered_data[key] = value
        
        return filtered_data
    
    def get_user_role_config(self, user_role: str) -> Dict[str, Any]:
        """Get configuration for specific user role"""
        return self.user_roles.get(user_role, self.user_roles['beneficiary'])
    
    def is_service_available(self) -> bool:
        """Check if user identification service is available"""
        return True  # Always available with fallbacks
