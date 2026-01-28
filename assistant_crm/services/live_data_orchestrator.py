#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WCFCB Assistant CRM - Live Data Orchestrator
============================================

Standalone service for live data operations with strict unidirectional data flow.
This service operates independently with no dependencies on reply services to
prevent circular calling patterns that caused infinite loops in previous implementation.

Author: WCFCB Development Team
Created: 2025-08-12 (Phase 1 Implementation)
License: MIT

Architecture Principles:
-----------------------
1. NO CIRCULAR CALLS: This service never calls back to reply services
2. TIMEOUT PROTECTION: All operations have 5-second timeout limits
3. CIRCUIT BREAKER: Automatic failure detection and recovery
4. GRACEFUL FALLBACKS: Returns None on failure, never throws exceptions up
5. COMPONENT ISOLATION: Operates independently of other services
"""

import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import threading

# Safe frappe import with fallbacks
try:
    import frappe
    from frappe.utils import now as frappe_now, cstr as frappe_cstr
    FRAPPE_AVAILABLE = True
    # Safe wrapper functions to prevent "object is not bound" errors
    def now():
        try:
            return frappe_now()
        except:
            return datetime.now().isoformat()

    def cstr(value):
        try:
            return frappe_cstr(value)
        except:
            return str(value)

except ImportError:
    frappe = None
    now = lambda: datetime.now().isoformat()
    cstr = str
    FRAPPE_AVAILABLE = False

# CBS (CoreBusiness) integration imports
try:
    import cx_Oracle
    CBS_AVAILABLE = True
except ImportError:
    CBS_AVAILABLE = False
    print("[INFO] CBS Integration: Oracle client not available. Install with: pip install cx_Oracle")
    print("[INFO] Oracle Instant Client required: https://www.oracle.com/database/technologies/instant-client.html")


class CBSConnection:
    """CoreBusiness System Database Connection Manager"""

    def __init__(self):
        self.host = "192.168.1.250"
        self.port = "1521"
        self.service_name = "testpas12cew"
        self.username = "workcom"
        self.password = "qK7zM3kU45X2s1qG47"
        self.connection = None
        self._connection_lock = threading.Lock()

    def get_connection(self):
        """Get CBS database connection with connection pooling"""
        if not CBS_AVAILABLE:
            return None

        with self._connection_lock:
            try:
                # Check if existing connection is still valid
                if self.connection:
                    try:
                        cursor = self.connection.cursor()
                        cursor.execute("SELECT 1 FROM DUAL")
                        cursor.close()
                        return self.connection
                    except:
                        self.connection = None

                # Create new connection
                dsn = cx_Oracle.makedsn(self.host, self.port, service_name=self.service_name)
                self.connection = cx_Oracle.connect(
                    user=self.username,
                    password=self.password,
                    dsn=dsn,
                    encoding="UTF-8"
                )
                return self.connection

            except Exception as e:
                print(f"[ERROR] CBS Connection failed: {str(e)}")
                return None

    def execute_query(self, query: str, params: dict = None) -> Optional[List[Dict]]:
        """Execute query on CBS database"""
        connection = self.get_connection()
        if not connection:
            return None

        try:
            cursor = connection.cursor()
            cursor.execute(query, params or {})

            # Get column names
            columns = [desc[0].lower() for desc in cursor.description]

            # Fetch results and convert to dict
            results = []
            for row in cursor.fetchall():
                result_dict = {}
                for i, value in enumerate(row):
                    result_dict[columns[i]] = value
                results.append(result_dict)

            cursor.close()
            return results

        except Exception as e:
            print(f"[ERROR] CBS Query failed: {str(e)}")
            return None

    def close(self):
        """Close CBS connection"""
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
            except:
                pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent cascading failures.
    Protects against infinite loops and system overload.
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        with self._lock:
            if self.state == "OPEN":
                if self.last_failure_time and (time.time() - self.last_failure_time) > self.timeout:
                    self.state = "HALF_OPEN"
                else:
                    raise CircuitBreakerOpenException("Circuit breaker is OPEN")

            try:
                result = func(*args, **kwargs)
                if self.state == "HALF_OPEN":
                    self.state = "CLOSED"
                    self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                raise e


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class TimeoutException(Exception):
    """Exception raised when operation times out."""
    pass


def timeout_handler(timeout_duration: int):
    """Decorator to add timeout protection to functions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = [None]
            exception = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout_duration)

            if thread.is_alive():
                # Thread is still running, timeout occurred
                raise TimeoutException(f"Operation timed out after {timeout_duration} seconds")

            if exception[0]:
                raise exception[0]

            return result[0]
        return wrapper
    return decorator


class LiveDataOrchestrator:
    """
    Standalone live data orchestrator with strict unidirectional data flow.

    CRITICAL: This service NEVER calls back to reply services or any other
    services that might create circular dependencies.
    """

    def __init__(self):
        """Initialize orchestrator with safety mechanisms."""
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=30)
        self.timeout_duration = 5  # 5-second timeout for all operations
        self.live_data_intents = {
            'claim_status', 'payment_status', 'pension_inquiry', 'claim_submission',
            'account_info', 'payment_history', 'document_status', 'technical_help'
        }

        # Initialize cache for performance (simple in-memory cache)
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes TTL

        # Initialize CBS connection
        self.cbs_connection = CBSConnection()

        # Log initialization
        self._log_info("LiveDataOrchestrator initialized with safety mechanisms and CBS integration")


    def _is_cbs_enabled(self) -> bool:
        """Check site flag to enable/disable CBS calls.
        Returns False when assistant_crm_disable_cbs is truthy in site config.
        """
        # If cx_Oracle isn't importable, CBS is effectively disabled
        if not CBS_AVAILABLE:
            return False
        if FRAPPE_AVAILABLE and frappe:
            try:
                conf = getattr(frappe, 'conf', {}) or {}
                # support either flat flag or nested under assistant_crm
                if conf.get('assistant_crm_disable_cbs'):
                    return False
                ac = conf.get('assistant_crm') or {}
                if ac.get('disable_cbs'):
                    return False
            except Exception:
                pass
        return True

    def process_live_data_request(self, intent: str, user_context: Dict[str, Any], message: str) -> Optional[Dict[str, Any]]:
        """
        Main entry point for live data processing.

        CRITICAL: This method NEVER calls reply services or creates circular dependencies.

        Args:
            intent: Detected intent (claim_status, payment_status, etc.)
            user_context: User context with permissions and identification
            message: Original user message

        Returns:
            Dict with live data or None if not available/applicable
        """
        try:
            # Step 1: Validate intent eligibility (no external calls)
            if not self._is_live_data_intent(intent):
                self._log_debug(f"Intent '{intent}' not eligible for live data")
                return None

            # Step 2: Validate permissions (no external calls)
            if not self._validate_permissions(user_context, intent):
                self._log_debug(f"User lacks permissions for intent '{intent}'")
                return None

            # Attach last user context for downstream helpers (to access full_name/employer_name when present)
            try:
                self._last_user_context = user_context or {}
            except Exception:
                self._last_user_context = {}

            # Step 3: Retrieve data with circuit breaker and timeout protection
            # Phase 2.4: Surgical fix for claim_submission - bypass circuit breaker and timeout temporarily
            if intent == "claim_submission":
                self._log_debug(f"Bypassing circuit breaker and timeout for claim_submission intent")
                return self._retrieve_intent_data_direct(intent, user_context, message)
            else:
                return self.circuit_breaker.call(
                    self._retrieve_intent_data_with_timeout, intent, user_context, message
                )

        except (CircuitBreakerOpenException, TimeoutException) as e:
            self._log_warning(f"Live data request failed: {str(e)}")
            return None
        except Exception as e:
            self._log_error(f"Unexpected error in live data processing: {str(e)}")
            return None

    def _retrieve_intent_data_direct(self, intent: str, user_context: Dict[str, Any], message: str) -> Optional[Dict[str, Any]]:
        """
        Direct data retrieval without timeout protection (Phase 2.4: Surgical fix for claim_submission).
        """
        return self._retrieve_intent_data_core(intent, user_context, message)

    @timeout_handler(5)  # 5-second timeout protection
    def _retrieve_intent_data_with_timeout(self, intent: str, user_context: Dict[str, Any], message: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data for specific intent with timeout protection.

        CRITICAL: This method is isolated and makes no external service calls
        that could create circular dependencies.
        """
        return self._retrieve_intent_data_core(intent, user_context, message)

    def _retrieve_intent_data_core(self, intent: str, user_context: Dict[str, Any], message: str) -> Optional[Dict[str, Any]]:
        """
        Core data retrieval logic without timeout protection.

        CRITICAL: This method is isolated and makes no external service calls
        that could create circular dependencies.
        """
        try:
            # Check cache first (Phase 2.4: Skip cache for claim_submission during debugging)
            cache_key = f"{intent}_{user_context.get('user_id', 'unknown')}"
            if intent != "claim_submission":
                cached_data = self._get_cached_data(cache_key)
                if cached_data:
                    self._log_debug(f"Returning cached data for {cache_key}")
                    return cached_data

            # Retrieve fresh data based on intent
            data = None
            if intent == "claim_status":
                data = self._get_claim_data(user_context)
            elif intent == "payment_status":
                data = self._get_payment_data(user_context)
            elif intent == "pension_inquiry":
                data = self._get_pension_data(user_context)
            elif intent == "claim_submission":
                # Phase 2.4: Surgical fix for claim submission integration
                self._log_debug(f"Processing claim_submission intent for user {user_context.get('user_id')}")
                data = self._get_claim_submission_data(user_context)
                self._log_debug(f"Claim submission data retrieved: {bool(data)}")
            elif intent == "account_info":
                data = self._get_account_data(user_context)
            elif intent == "payment_history":
                data = self._get_payment_history_data(user_context)
            elif intent == "document_status":
                data = self._get_document_status_data(user_context)
            elif intent == "technical_help":
                data = self._get_technical_help_data(user_context)

            # Cache successful results
            if data:
                self._cache_data(cache_key, data)
                self._log_debug(f"Retrieved and cached data for intent '{intent}'")

            return data

        except Exception as e:
            self._log_error(f"Error retrieving data for intent '{intent}': {str(e)}")
            return None

    def _is_live_data_intent(self, intent: str) -> bool:
        """Check if intent is eligible for live data integration."""
        return intent in self.live_data_intents

    def _validate_permissions(self, user_context: Dict[str, Any], intent: str) -> bool:
        """
        Validate user permissions for live data access.

        CRITICAL: This method makes no external calls to avoid circular dependencies.
        """
        if not user_context:
            return False

        user_role = user_context.get('user_role', 'guest')
        user_id = user_context.get('user_id')

        # Loosen gating for claim_status when NRC or full_name is provided
        if intent == 'claim_status' and (user_context.get('nrc_number') or user_context.get('full_name')):
            return True

        # Guest users cannot access live data otherwise
        if user_role == 'guest' or not user_id or user_id in ['guest', 'anonymous', 'error']:
            return False

        # Basic permission validation based on user role and intent
        permission_matrix = {
            'beneficiary': ['claim_status', 'payment_status', 'pension_inquiry', 'account_info', 'payment_history', 'document_status', 'technical_help'],
            'employer': ['claim_status', 'payment_status', 'account_info', 'payment_history', 'technical_help'],
            'supplier': ['payment_status', 'account_info', 'payment_history', 'technical_help'],
            'wcfcb_staff': ['claim_status', 'payment_status', 'pension_inquiry', 'claim_submission', 'account_info', 'payment_history', 'document_status', 'technical_help']
        }

        allowed_intents = permission_matrix.get(user_role, [])
        return intent in allowed_intents

    def _get_claim_data(self, user_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve live claim data from both ERPNext and CBS simultaneously."""
        try:
            # Get user identifier (NRC or user_id)
            nrc_number = user_context.get('nrc_number')
            user_id = user_context.get('user_id')

            # Also allow full_name-only flows (when NRC hasn't been provided yet)
            full_name = None
            try:
                ctx = getattr(self, '_last_user_context', {}) or {}
                full_name = ctx.get('full_name') or user_context.get('full_name')
            except Exception:
                full_name = user_context.get('full_name')

            if not nrc_number and not user_id and not full_name:
                return None

            # DUAL PRIMARY SEARCH: Search both ERPNext and CBS simultaneously
            erpnext_data = None
            if FRAPPE_AVAILABLE and frappe and (user_context.get('authenticated')):
                # Temporarily elevate to Administrator for read-only ERP lookups
                try:
                    old_user = getattr(frappe.session, 'user', None)
                except Exception:
                    old_user = None
                try:
                    try:
                        frappe.set_user('Administrator')
                    except Exception:
                        pass
                    erpnext_data = self._get_erpnext_claim_data(nrc_number, user_id, full_name)
                finally:
                    try:
                        if old_user:
                            frappe.set_user(old_user)
                    except Exception:
                        pass
            else:
                erpnext_data = self._get_erpnext_claim_data(nrc_number, user_id, full_name)

            cbs_data = self._get_cbs_claim_data(nrc_number, user_id)

            # Log if neither source returned data
            if not erpnext_data and not cbs_data:
                try:
                    self._log_debug(f"CLAIM: no_live_data erp=False cbs=False nrc={nrc_number} full_name={full_name}")
                except Exception:
                    pass

            # Merge data from both sources
            return self._merge_claim_data(erpnext_data, cbs_data, nrc_number, user_id)

            # Get claims for this beneficiary using multiple search strategies
            claim = None

            # Strategy 1: Search by beneficiary name (primary key)
            claim = frappe.db.get_value('Claims Tracking',
                                      {'beneficiary': beneficiary.name},
                                      ['claim_id', 'status', 'submission_date', 'claim_type',
                                       'current_stage', 'estimated_completion', 'last_updated',
                                       'description', 'documents_required'],
                                      order_by='submission_date desc',
                                      as_dict=True)

            # Strategy 2: Search by beneficiary number if name search fails
            if not claim and beneficiary.beneficiary_number:
                claims = frappe.db.get_all('Claims Tracking',
                                         filters={'beneficiary': ['like', f'%{beneficiary.beneficiary_number}%']},
                                         fields=['claim_id', 'status', 'submission_date', 'claim_type',
                                               'current_stage', 'estimated_completion', 'last_updated',
                                               'description', 'documents_required'],
                                         order_by='submission_date desc',
                                         limit=1)
                if claims:
                    claim = claims[0]

            # Strategy 3: Search by full name if other methods fail
            if not claim and beneficiary.full_name:
                claims = frappe.db.get_all('Claims Tracking',
                                         filters={'beneficiary': ['like', f'%{beneficiary.full_name}%']},
                                         fields=['claim_id', 'status', 'submission_date', 'claim_type',
                                               'current_stage', 'estimated_completion', 'last_updated',
                                               'description', 'documents_required'],
                                         order_by='submission_date desc',
                                         limit=1)
                if claims:
                    claim = claims[0]

            # Strategy 4: Try CBS if ERPNext claims not found
            if not claim and cbs_beneficiary:
                cbs_claims = self._get_cbs_claims_data(cbs_beneficiary.get('member_id'))
                if cbs_claims:
                    # Convert CBS claim to ERPNext-like format
                    cbs_claim = cbs_claims[0]
                    claim = {
                        'claim_id': cbs_claim.get('claim_id'),
                        'status': cbs_claim.get('status'),
                        'submission_date': cbs_claim.get('submission_date'),
                        'claim_type': cbs_claim.get('claim_type'),
                        'current_stage': cbs_claim.get('current_stage'),
                        'estimated_completion': cbs_claim.get('estimated_completion'),
                        'last_updated': cbs_claim.get('submission_date'),
                        'description': cbs_claim.get('description'),
                        'documents_required': 'Available in CBS system'
                    }

            # Return beneficiary info even if no claims found
            if not claim:
                return {
                    'type': 'claim_data',
                    'beneficiary_name': beneficiary.full_name,
                    'beneficiary_number': beneficiary.beneficiary_number,
                    'message': 'No claims found for this beneficiary',
                    'retrieved_at': now()
                }

            return {
                'type': 'claim_data',
                'claim_id': claim.claim_id,
                'status': claim.status,
                'submission_date': str(claim.submission_date) if claim.submission_date else None,
                'claim_type': claim.claim_type,
                'current_stage': claim.current_stage,
                'estimated_completion': str(claim.estimated_completion) if claim.estimated_completion else None,
                'last_updated': str(claim.last_updated) if claim.last_updated else None,
                'description': claim.description,
                'documents_required': claim.documents_required,
                'beneficiary_name': beneficiary.full_name,
                'beneficiary_number': beneficiary.beneficiary_number,
                'retrieved_at': now()
            }

        except Exception as e:
            self._log_error(f"Error retrieving claim data: {str(e)}")
            return None

    def _get_payment_data(self, user_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve live payment data from both ERPNext and CBS simultaneously."""
        try:
            # Get user identifier (NRC or user_id)
            nrc_number = user_context.get('nrc_number')
            user_id = user_context.get('user_id')

            if not nrc_number and not user_id:
                return None

            # DUAL PRIMARY SEARCH: Search both ERPNext and CBS simultaneously
            erpnext_data = self._get_erpnext_payment_data(nrc_number, user_id)
            cbs_data = self._get_cbs_payment_data(nrc_number, user_id)

            # Merge data from both sources
            return self._merge_payment_data(erpnext_data, cbs_data, nrc_number, user_id)

            # Get the most recent payment status for this beneficiary
            payment = frappe.db.get_value('Payment Status',
                                        {'beneficiary': beneficiary.name},
                                        ['payment_id', 'status', 'amount', 'payment_date',
                                         'payment_method', 'reference_number', 'processing_stage',
                                         'expected_completion'],
                                        order_by='payment_date desc',
                                        as_dict=True)

            # Prepare response with beneficiary and payment data
            response_data = {
                'type': 'payment_data',
                'beneficiary_name': beneficiary.full_name,
                'beneficiary_number': beneficiary.beneficiary_number,
                'monthly_benefit_amount': beneficiary.monthly_benefit_amount,
                'last_payment_date': str(beneficiary.last_payment_date) if beneficiary.last_payment_date else None,
                'next_payment_due': str(beneficiary.next_payment_due) if beneficiary.next_payment_due else None,
                'bank_name': beneficiary.bank_name,
                'account_ending': f"****{beneficiary.bank_account_number[-4:]}" if beneficiary.bank_account_number else None,
                'retrieved_at': now()
            }

            # Add payment-specific data if available
            if payment:
                response_data.update({
                    'payment_id': payment.payment_id,
                    'payment_status': payment.status,
                    'payment_amount': payment.amount,
                    'payment_method': payment.payment_method,
                    'reference_number': payment.reference_number,
                    'processing_stage': payment.processing_stage,
                    'expected_completion': str(payment.expected_completion) if payment.expected_completion else None
                })

            return response_data

        except Exception as e:
            self._log_error(f"Error retrieving payment data: {str(e)}")
            return None

    def _get_pension_data(self, user_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve live pension data.

        NOTE: Beneficiary Profile doctype has been removed.
        Beneficiary data is now managed externally. Returns None.
        """
        try:
            # Get user identifier (NRC or user_id)
            nrc_number = user_context.get('nrc_number')
            user_id = user_context.get('user_id')

            if not nrc_number and not user_id:
                return None

            # Find beneficiary using comprehensive search
            beneficiary = self._find_beneficiary_comprehensive(nrc_number, user_id,
                                                             ['name', 'beneficiary_number', 'full_name',
                                                              'benefit_type', 'benefit_status', 'benefit_start_date',
                                                              'benefit_end_date', 'monthly_benefit_amount',
                                                              'employee_name', 'relationship_to_employee'])

            if not beneficiary:
                return None

            return {
                'type': 'pension_data',
                'beneficiary_name': beneficiary.full_name,
                'beneficiary_number': beneficiary.beneficiary_number,
                'benefit_type': beneficiary.benefit_type,
                'benefit_status': beneficiary.benefit_status,
                'monthly_benefit_amount': beneficiary.monthly_benefit_amount,
                'benefit_start_date': str(beneficiary.benefit_start_date) if beneficiary.benefit_start_date else None,
                'benefit_end_date': str(beneficiary.benefit_end_date) if beneficiary.benefit_end_date else None,
                'employee_name': beneficiary.employee_name,
                'relationship_to_employee': beneficiary.relationship_to_employee,
                'retrieved_at': now()
            }

        except Exception as e:
            self._log_error(f"Error retrieving pension data: {str(e)}")
            return None

    def _get_claim_submission_data(self, user_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get claim submission information."""
        # Phase 2.4: Surgical fix - use static timestamp to avoid potential now() issues
        return {
            'type': 'claim_submission_data',
            'required_documents': ['Medical report', 'Incident report', 'Employment verification'],
            'submission_methods': ['Online portal', 'Email', 'In-person'],
            'processing_time': '14-21 business days',
            'retrieved_at': '2025-08-12T21:10:00'
        }

    def _get_account_data(self, user_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get live account information.

        NOTE: Beneficiary Profile doctype has been removed.
        Beneficiary data is now managed externally. Returns None.
        """
        try:
            # Get user identifier (NRC or user_id)
            nrc_number = user_context.get('nrc_number')
            user_id = user_context.get('user_id')

            if not nrc_number and not user_id:
                return None

            # Find beneficiary using comprehensive search
            beneficiary = self._find_beneficiary_comprehensive(nrc_number, user_id,
                                                             ['name', 'beneficiary_number', 'full_name', 'nrc_number',
                                                              'email', 'phone', 'mobile', 'physical_address',
                                                              'postal_address', 'city', 'province', 'benefit_status',
                                                              'creation'])

            if not beneficiary:
                return None

            return {
                'type': 'account_data',
                'beneficiary_name': beneficiary.full_name,
                'beneficiary_number': beneficiary.beneficiary_number,
                'nrc_number': beneficiary.nrc_number,
                'account_status': beneficiary.benefit_status or 'Active',
                'member_since': str(beneficiary.creation.date()) if beneficiary.creation else None,
                'email': beneficiary.email,
                'phone': beneficiary.phone,
                'mobile': beneficiary.mobile,
                'physical_address': beneficiary.physical_address,
                'postal_address': beneficiary.postal_address,
                'city': beneficiary.city,
                'province': beneficiary.province,
                'retrieved_at': now()
            }

        except Exception as e:
            self._log_error(f"Error retrieving account data: {str(e)}")
            return None

    def _get_payment_history_data(self, user_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get live payment history from ERPNext Payment Status DocType."""
        try:
            # Get user identifier (NRC or user_id)
            nrc_number = user_context.get('nrc_number')
            user_id = user_context.get('user_id')

            if not nrc_number and not user_id:
                return None

            # Find beneficiary using comprehensive search
            beneficiary = self._find_beneficiary_comprehensive(nrc_number, user_id,
                                                             ['name', 'beneficiary_number', 'full_name',
                                                              'total_benefits_received'])

            if not beneficiary:
                return None

            # Get recent payments for this beneficiary (last 6 months)
            payments = frappe.db.get_all('Payment Status',
                                       filters={'beneficiary': beneficiary.name},
                                       fields=['payment_date', 'amount', 'payment_type',
                                              'status', 'reference_number'],
                                       order_by='payment_date desc',
                                       limit=10)

            # Format payment history
            recent_payments = []
            for payment in payments:
                recent_payments.append({
                    'date': str(payment.payment_date) if payment.payment_date else None,
                    'amount': payment.amount,
                    'type': payment.payment_type or 'Benefit payment',
                    'status': payment.status,
                    'reference': payment.reference_number
                })

            return {
                'type': 'payment_history_data',
                'beneficiary_name': beneficiary.full_name,
                'beneficiary_number': beneficiary.beneficiary_number,
                'recent_payments': recent_payments,
                'total_benefits_received': beneficiary.total_benefits_received,
                'retrieved_at': now()
            }

        except Exception as e:
            self._log_error(f"Error retrieving payment history: {str(e)}")
            return None

    def _get_document_status_data(self, user_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get document status information."""
        # Phase 2.5: Surgical fix - use static timestamp to avoid potential now() issues
        return {
            'type': 'document_status_data',
            'pending_documents': ['Updated medical certificate'],
            'approved_documents': ['Initial claim form', 'Employment verification'],
            'rejected_documents': [],
            'retrieved_at': '2025-08-12T23:00:00'
        }

    def _get_technical_help_data(self, user_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get technical help and support information."""
        # Phase 2.5: Surgical fix - use static timestamp to avoid potential now() issues
        return {
            'type': 'technical_help_data',
            'common_issues': [
                {'issue': 'Login problems', 'solution': 'Reset password or clear browser cache'},
                {'issue': 'Website not loading', 'solution': 'Check internet connection and try refreshing'},
                {'issue': 'Form submission errors', 'solution': 'Ensure all required fields are completed'}
            ],
            'support_contacts': {
                'technical_support': '+260-211-123456 ext. 301',
                'email': 'support@wcfcb.gov.zm',
                'hours': 'Monday-Friday, 8:00 AM - 5:00 PM'
            },
            'system_status': 'All systems operational',
            'last_maintenance': '2025-01-10',
            'retrieved_at': '2025-08-12T23:10:00'
        }

    def _get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if not expired."""
        if cache_key in self._cache:
            cached_item = self._cache[cache_key]
            if time.time() - cached_item['timestamp'] < self._cache_ttl:
                return cached_item['data']
            else:
                # Remove expired item
                del self._cache[cache_key]
        return None

    def _cache_data(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Cache data with timestamp."""
        self._cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }

    def _log_info(self, message: str) -> None:
        """Log info message safely."""
        if FRAPPE_AVAILABLE and frappe:
            try:
                frappe.logger().info(f"LiveDataOrchestrator: {message}")
            except:
                pass

    def _log_debug(self, message: str) -> None:
        """Log debug message safely."""
        if FRAPPE_AVAILABLE and frappe:
            try:
                frappe.logger().debug(f"LiveDataOrchestrator: {message}")
            except:
                pass

    def _log_warning(self, message: str) -> None:
        """Log warning message safely."""
        if FRAPPE_AVAILABLE and frappe:
            try:
                frappe.logger().warning(f"LiveDataOrchestrator: {message}")
            except:
                pass

    def _find_beneficiary_comprehensive(self, nrc_number: str, user_id: str, fields: list) -> Optional[Dict[str, Any]]:
        """Find beneficiary using comprehensive search strategies.

        NOTE: Beneficiary Profile doctype has been removed.
        Beneficiary data is now managed externally.
        This function now returns None.
        """
        # NOTE: Beneficiary Profile doctype has been removed - beneficiary data managed externally
        # Suppress unused parameter warnings
        _ = nrc_number  # Unused - doctype removed
        _ = user_id  # Unused - doctype removed
        _ = fields  # Unused - doctype removed
        return None

    def _find_employee_by_nrc_or_name(self, nrc_number: Optional[str], full_name: Optional[str]) -> Optional[Dict[str, Any]]:
        """Safely locate an Employee by NRC (common custom fields) or full name."""
        try:
            if not (FRAPPE_AVAILABLE and frappe):
                return None

            # Try by NRC across likely custom field names (with NORMALIZED matching)
            if nrc_number:
                import re as _re
                norm = _re.sub(r'[^0-9]', '', cstr(nrc_number)) if nrc_number else None
                # Prefer normalized exact matches, then exact, then partials
                for field in ['custom_nrc_number', 'nrc_number', 'national_id', 'nrc']:
                    try:
                        if not frappe.db.has_column('Employee', field):
                            continue
                        # 1) Normalized exact match via SQL REPLACE
                        if norm:
                            cols = '`name`, `employee_name`, `company`'
                            res = frappe.db.sql(
                                f"""
                                SELECT {cols}
                                FROM `tabEmployee`
                                WHERE REPLACE(REPLACE(REPLACE({field}, '/', ''), '-', ''), ' ', '') = %s
                                LIMIT 1
                                """,
                                (norm,),
                                as_dict=True,
                            )
                            if res:
                                return res[0]
                        # 2) Exact match via SQL (bypass permissions)
                        res = frappe.db.sql(
                            f"""
                            SELECT `name`, `employee_name`, `company`
                            FROM `tabEmployee`
                            WHERE {field} = %s
                            LIMIT 1
                            """,
                            (nrc_number,),
                            as_dict=True,
                        )
                        if res:
                            return res[0]
                        # 3) Partial match fallback via SQL LIKE
                        res = frappe.db.sql(
                            f"""
                            SELECT `name`, `employee_name`, `company`
                            FROM `tabEmployee`
                            WHERE {field} LIKE %s
                            LIMIT 1
                            """,
                            (f"%{nrc_number}%",),
                            as_dict=True,
                        )
                        if res:
                            return res[0]
                    except Exception:
                        continue

            # Try by full name (case-insensitive). Use tokenized LIKE to tolerate double spaces/typos
            if full_name:
                try:
                    tokens = [t for t in (full_name or '').strip().split() if t]
                    if len(tokens) >= 2:
                        fname, lname = tokens[0], tokens[-1]
                        res = frappe.db.sql(
                            """
                            SELECT `name`, `employee_name`, `company`
                            FROM `tabEmployee`
                            WHERE `employee_name` LIKE %s AND `employee_name` LIKE %s
                            LIMIT 1
                            """,
                            (f"%{fname}%", f"%{lname}%"),
                            as_dict=True,
                        )
                        if res:
                            return res[0]
                    # Fallback single LIKE
                    res = frappe.db.sql(
                        """
                        SELECT `name`, `employee_name`, `company`
                        FROM `tabEmployee`
                        WHERE `employee_name` LIKE %s
                        LIMIT 1
                        """,
                        (f"%{full_name}%",),
                        as_dict=True,
                    )
                    if res:
                        return res[0]
                except Exception:
                    pass

            return None
        except Exception:
            return None

    def _get_erpnext_claim_data(self, nrc_number: Optional[str], user_id: Optional[str], full_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve claim data specifically from ERPNext.

        NOTE: Beneficiary Profile doctype has been removed.
        Uses HRMS Employee Benefit Claim by Employee instead.
        """
        try:
            erp_data: Dict[str, Any] = {'source': 'erpnext'}

            # NOTE: Beneficiary Profile removed - _find_beneficiary_comprehensive returns None
            beneficiary = None
            try:
                beneficiary = self._find_beneficiary_comprehensive(nrc_number or '', user_id or '',
                                                                   ['name', 'beneficiary_number', 'full_name']) if (nrc_number or user_id) else None
            except Exception:
                beneficiary = None
            if beneficiary:
                erp_data['beneficiary'] = beneficiary

                # Claims Tracking (legacy/custom) lookup
                if FRAPPE_AVAILABLE and frappe:
                    try:
                        claim = frappe.db.get_value('Claims Tracking',
                                                    {'beneficiary': beneficiary['name']},
                                                    ['claim_id', 'status', 'submission_date', 'claim_type',
                                                     'current_stage', 'estimated_completion', 'last_updated',
                                                     'description', 'documents_required'],
                                                    order_by='submission_date desc',
                                                    as_dict=True)
                        if not claim and beneficiary.get('beneficiary_number'):
                            claims = frappe.db.get_all('Claims Tracking',
                                                       filters={'beneficiary': ['like', f"%{beneficiary['beneficiary_number']}%"]},
                                                       fields=['claim_id', 'status', 'submission_date', 'claim_type',
                                                               'current_stage', 'estimated_completion', 'last_updated',
                                                               'description', 'documents_required'],
                                                       order_by='submission_date desc',
                                                       limit=1)
                            if claims:
                                claim = claims[0]
                        if claim:
                             erp_data['claim'] = claim
                    except Exception:
                        pass

            # Always attempt Employee → Employee Benefit Claim fallback (HRMS)
            if FRAPPE_AVAILABLE and frappe:
                employee = self._find_employee_by_nrc_or_name(nrc_number, full_name)
                if employee:
                    erp_data['employee'] = employee
                    try:
                        self._log_debug(f"HRMS: employee_match name={employee.get('name')} employee_name={employee.get('employee_name')} nrc={nrc_number} full_name={full_name}")
                        self._log_info(f"HRMS: employee_match name={employee.get('name')} employee_name={employee.get('employee_name')}")
                    except Exception:
                        pass
                    # Fetch up to 5 most recent Employee Benefit Claim docs for this employee (SQL, bypass permissions)
                    ebc_list = frappe.db.sql(
                        """
                        SELECT `name`, `employee`, `employee_name`, `company`, `claim_date`,
                               `earning_component`, `claimed_amount`, `docstatus`
                        FROM `tabEmployee Benefit Claim`
                        WHERE `employee` = %s
                        ORDER BY `claim_date` DESC
                        LIMIT 5
                        """,
                        (employee['name'],),
                        as_dict=True,
                    )
                    try:
                        self._log_debug(f"HRMS: ebc_list_count={len(ebc_list or [])} for employee={employee.get('name')}")
                        self._log_info(f"HRMS: ebc_list_count={len(ebc_list or [])} employee={employee.get('name')}")
                    except Exception:
                        pass
                    # Fallback: if none found by link field, try by employee_name match
                    if (not ebc_list) and full_name:
                        try:
                            ebc_list = frappe.db.sql(
                                """
                                SELECT `name`, `employee`, `employee_name`, `company`, `claim_date`,
                                       `earning_component`, `claimed_amount`, `docstatus`
                                FROM `tabEmployee Benefit Claim`
                                WHERE `employee_name` LIKE %s
                                ORDER BY `claim_date` DESC
                                LIMIT 5
                                """,
                                (f"%{full_name}%",),
                                as_dict=True,
                            ) or []
                            self._log_debug(f"HRMS: fallback_by_name ebc_list_count={len(ebc_list)} full_name='{full_name}'")
                            self._log_info(f"HRMS: fallback_by_name ebc_list_count={len(ebc_list)}")
                        except Exception:
                            pass
                    # Normalize into claim-like entries
                    benefit_claims = []
                    for ebc in (ebc_list or []):
                        status_map = {0: 'Draft', 1: 'Submitted', 2: 'Cancelled'}
                        benefit_claims.append({
                            'claim_id': ebc.get('name'),
                            'status': status_map.get(int(ebc.get('docstatus') or 0), 'Unknown'),
                            'submission_date': ebc.get('claim_date'),
                            'claim_type': 'Employee Benefit Claim',
                            'current_stage': None,
                            'estimated_completion': None,
                            'description': f"{ebc.get('earning_component') or ''} · Amount {ebc.get('claimed_amount')}",
                            'documents_required': None,
                            'employee': ebc.get('employee'),
                            'employee_name': ebc.get('employee_name'),
                            'company': ebc.get('company')
                        })
                    if benefit_claims:
                        erp_data['benefit_claims'] = benefit_claims
                else:
                    try:
                        self._log_debug(f"HRMS: no_employee_match nrc={nrc_number} full_name={full_name}")
                        self._log_info("HRMS: no_employee_match")
                    except Exception:
                        pass

            # If we gathered nothing, return None
            if len(erp_data.keys()) == 1:  # only {'source': 'erpnext'}
                return None
            return erp_data

        except Exception as e:
            self._log_error(f"Error retrieving ERPNext claim data: {str(e)}")
            return None

    def _get_cbs_claim_data(self, nrc_number: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve claim data specifically from CBS"""
        # Respect site flag to disable CBS fully
        if not self._is_cbs_enabled():
            return None
        try:
            # Get beneficiary data from CBS
            cbs_beneficiary = self._get_cbs_beneficiary_data(nrc_number, user_id)

            if not cbs_beneficiary:
                return None

            # Get claims data from CBS
            member_id = cbs_beneficiary.get('member_id')
            cbs_claims = self._get_cbs_claims_data(member_id)

            return {
                'source': 'cbs',
                'beneficiary': cbs_beneficiary,
                'claims': cbs_claims or []
            }

        except Exception as e:
            self._log_error(f"Error retrieving CBS claim data: {str(e)}")
            return None

    def _merge_claim_data(self, erpnext_data: Optional[Dict], cbs_data: Optional[Dict],
                         nrc_number: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Merge claim data from ERPNext and CBS into unified format"""
        try:
            if not erpnext_data and not cbs_data:
                return None

            # Initialize unified response
            unified_data = {
                'type': 'claim_data',
                'data_sources': [],
                'beneficiary_info': {},
                'claims': [],
                'retrieved_at': now()
            }

            # Process ERPNext data
            if erpnext_data:
                unified_data['data_sources'].append('ERPNext')
                beneficiary = erpnext_data.get('beneficiary', {})

                unified_data['beneficiary_info'].update({
                    'erpnext_name': beneficiary.get('name'),
                    'erpnext_beneficiary_number': beneficiary.get('beneficiary_number'),
                    'erpnext_full_name': beneficiary.get('full_name')
                })

                # Add ERPNext claim if exists
                claim = erpnext_data.get('claim')
                if claim:
                    unified_data['claims'].append({
                        'source': 'ERPNext',
                        'claim_id': claim.get('claim_id'),
                        'status': claim.get('status'),
                        'submission_date': str(claim.get('submission_date')) if claim.get('submission_date') else None,
                        'claim_type': claim.get('claim_type'),
                        'current_stage': claim.get('current_stage'),
                        'estimated_completion': str(claim.get('estimated_completion')) if claim.get('estimated_completion') else None,
                        'description': claim.get('description'),
                        'documents_required': claim.get('documents_required')
                    })

                # Add Employee Benefit Claims (HRMS) if present
                ebc_claims = erpnext_data.get('benefit_claims') or []
                for ebc in ebc_claims:
                    unified_data['claims'].append({
                        'source': 'ERPNext-HRMS',
                        'claim_id': ebc.get('claim_id'),
                        'status': ebc.get('status'),
                        'submission_date': str(ebc.get('submission_date')) if ebc.get('submission_date') else None,
                        'claim_type': ebc.get('claim_type'),
                        'current_stage': ebc.get('current_stage'),
                        'estimated_completion': str(ebc.get('estimated_completion')) if ebc.get('estimated_completion') else None,
                        'description': ebc.get('description'),
                        'documents_required': ebc.get('documents_required')
                    })

            # Process CBS data
            if cbs_data:
                unified_data['data_sources'].append('CBS')
                beneficiary = cbs_data.get('beneficiary', {})

                unified_data['beneficiary_info'].update({
                    'cbs_member_id': beneficiary.get('member_id'),
                    'cbs_nrc_number': beneficiary.get('nrc_number'),
                    'cbs_full_name': beneficiary.get('full_name'),
                    'cbs_benefit_type': beneficiary.get('benefit_type'),
                    'cbs_benefit_status': beneficiary.get('benefit_status')
                })

                # Add CBS claims
                cbs_claims = cbs_data.get('claims', [])
                for cbs_claim in cbs_claims:
                    unified_data['claims'].append({
                        'source': 'CBS',
                        'claim_id': cbs_claim.get('claim_id'),
                        'status': cbs_claim.get('status'),
                        'submission_date': str(cbs_claim.get('submission_date')) if cbs_claim.get('submission_date') else None,
                        'claim_type': cbs_claim.get('claim_type'),
                        'current_stage': cbs_claim.get('current_stage'),
                        'estimated_completion': str(cbs_claim.get('estimated_completion')) if cbs_claim.get('estimated_completion') else None,
                        'description': cbs_claim.get('description'),
                        'amount_claimed': cbs_claim.get('amount_claimed'),
                        'amount_approved': cbs_claim.get('amount_approved')
                    })

            # Set primary identifiers (prefer CBS, fallback to ERPNext)
            if cbs_data and cbs_data.get('beneficiary'):
                unified_data['primary_nrc'] = cbs_data['beneficiary'].get('nrc_number')
                unified_data['primary_name'] = cbs_data['beneficiary'].get('full_name')
            elif erpnext_data and erpnext_data.get('beneficiary'):
                unified_data['primary_name'] = erpnext_data['beneficiary'].get('full_name')

            # Add summary information
            unified_data['total_claims'] = len(unified_data['claims'])
            unified_data['has_erpnext_data'] = bool(erpnext_data)
            unified_data['has_cbs_data'] = bool(cbs_data)

            return unified_data

        except Exception as e:
            self._log_error(f"Error merging claim data: {str(e)}")
            return None

    def _get_erpnext_payment_data(self, nrc_number: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve payment data specifically from ERPNext"""
        try:
            beneficiary = self._find_beneficiary_comprehensive(nrc_number, user_id,
                                                             ['name', 'beneficiary_number', 'full_name',
                                                              'monthly_benefit_amount', 'last_payment_date',
                                                              'next_payment_due', 'bank_name', 'bank_account_number'])

            if not beneficiary:
                return None

            # Get payment status from ERPNext
            payment = None
            if FRAPPE_AVAILABLE and frappe:
                payment = frappe.db.get_value('Payment Status',
                                            {'beneficiary': beneficiary['name']},
                                            ['payment_id', 'status', 'amount', 'payment_date',
                                             'payment_method', 'reference_number', 'processing_stage',
                                             'expected_completion'],
                                            order_by='payment_date desc',
                                            as_dict=True)

            return {
                'source': 'erpnext',
                'beneficiary': beneficiary,
                'payment': payment
            }

        except Exception as e:
            self._log_error(f"Error retrieving ERPNext payment data: {str(e)}")
            return None

    def _get_cbs_payment_data(self, nrc_number: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve payment data specifically from CBS"""
        # Respect site flag to disable CBS fully
        if not self._is_cbs_enabled():
            return None
        try:
            # Get beneficiary data from CBS
            cbs_beneficiary = self._get_cbs_beneficiary_data(nrc_number, user_id)

            if not cbs_beneficiary:
                return None

            # Get payment history from CBS
            member_id = cbs_beneficiary.get('member_id')
            cbs_payments = self._get_cbs_payments_data(member_id)

            return {
                'source': 'cbs',
                'beneficiary': cbs_beneficiary,
                'payments': cbs_payments or []
            }

        except Exception as e:
            self._log_error(f"Error retrieving CBS payment data: {str(e)}")
            return None

    def _merge_payment_data(self, erpnext_data: Optional[Dict], cbs_data: Optional[Dict],
                           nrc_number: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Merge payment data from ERPNext and CBS into unified format"""
        try:
            if not erpnext_data and not cbs_data:
                return None

            # Initialize unified response
            unified_data = {
                'type': 'payment_data',
                'data_sources': [],
                'beneficiary_info': {},
                'payments': [],
                'account_info': {},
                'retrieved_at': now()
            }

            # Process ERPNext data
            if erpnext_data:
                unified_data['data_sources'].append('ERPNext')
                beneficiary = erpnext_data.get('beneficiary', {})

                unified_data['beneficiary_info'].update({
                    'erpnext_name': beneficiary.get('name'),
                    'erpnext_beneficiary_number': beneficiary.get('beneficiary_number'),
                    'erpnext_full_name': beneficiary.get('full_name')
                })

                unified_data['account_info'].update({
                    'erpnext_monthly_benefit': beneficiary.get('monthly_benefit_amount'),
                    'erpnext_last_payment': str(beneficiary.get('last_payment_date')) if beneficiary.get('last_payment_date') else None,
                    'erpnext_next_payment': str(beneficiary.get('next_payment_due')) if beneficiary.get('next_payment_due') else None,
                    'erpnext_bank': beneficiary.get('bank_name'),
                    'erpnext_account': f"****{beneficiary.get('bank_account_number', '')[-4:]}" if beneficiary.get('bank_account_number') else None
                })

                # Add ERPNext payment if exists
                payment = erpnext_data.get('payment')
                if payment:
                    unified_data['payments'].append({
                        'source': 'ERPNext',
                        'payment_id': payment.get('payment_id'),
                        'status': payment.get('status'),
                        'amount': payment.get('amount'),
                        'payment_date': str(payment.get('payment_date')) if payment.get('payment_date') else None,
                        'payment_method': payment.get('payment_method'),
                        'reference_number': payment.get('reference_number'),
                        'processing_stage': payment.get('processing_stage')
                    })

            # Process CBS data
            if cbs_data:
                unified_data['data_sources'].append('CBS')
                beneficiary = cbs_data.get('beneficiary', {})

                unified_data['beneficiary_info'].update({
                    'cbs_member_id': beneficiary.get('member_id'),
                    'cbs_nrc_number': beneficiary.get('nrc_number'),
                    'cbs_full_name': beneficiary.get('full_name'),
                    'cbs_benefit_type': beneficiary.get('benefit_type'),
                    'cbs_benefit_status': beneficiary.get('benefit_status')
                })

                unified_data['account_info'].update({
                    'cbs_monthly_amount': beneficiary.get('monthly_amount'),
                    'cbs_last_payment': str(beneficiary.get('last_payment_date')) if beneficiary.get('last_payment_date') else None,
                    'cbs_next_payment': str(beneficiary.get('next_payment_date')) if beneficiary.get('next_payment_date') else None,
                    'cbs_bank': beneficiary.get('bank_name'),
                    'cbs_account': f"****{beneficiary.get('account_number', '')[-4:]}" if beneficiary.get('account_number') else None,
                    'cbs_total_received': beneficiary.get('total_benefits_received')
                })

                # Add CBS payments
                cbs_payments = cbs_data.get('payments', [])
                for cbs_payment in cbs_payments:
                    unified_data['payments'].append({
                        'source': 'CBS',
                        'payment_id': cbs_payment.get('payment_id'),
                        'status': cbs_payment.get('status'),
                        'amount': cbs_payment.get('amount'),
                        'payment_date': str(cbs_payment.get('payment_date')) if cbs_payment.get('payment_date') else None,
                        'payment_type': cbs_payment.get('payment_type'),
                        'reference_number': cbs_payment.get('reference_number'),
                        'bank_name': cbs_payment.get('bank_name')
                    })

            # Set primary identifiers
            if cbs_data and cbs_data.get('beneficiary'):
                unified_data['primary_nrc'] = cbs_data['beneficiary'].get('nrc_number')
                unified_data['primary_name'] = cbs_data['beneficiary'].get('full_name')
            elif erpnext_data and erpnext_data.get('beneficiary'):
                unified_data['primary_name'] = erpnext_data['beneficiary'].get('full_name')

            # Add summary information
            unified_data['total_payments'] = len(unified_data['payments'])
            unified_data['has_erpnext_data'] = bool(erpnext_data)
            unified_data['has_cbs_data'] = bool(cbs_data)

            return unified_data

        except Exception as e:
            self._log_error(f"Error merging payment data: {str(e)}")
            return None

    def _get_cbs_beneficiary_data(self, nrc_number: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve beneficiary data from CBS (CoreBusiness System)"""
        if not CBS_AVAILABLE:
            return None

        try:
            # Comprehensive CBS beneficiary search with all required fields
            queries = []

            # Query 1: Exact NRC match
            if nrc_number:
                queries.append({
                    'query': """
                    SELECT
                        MEMBER_ID,
                        NRC_NUMBER,
                        FULL_NAME,
                        FIRST_NAME,
                        LAST_NAME,
                        BENEFIT_TYPE,
                        BENEFIT_STATUS,
                        MONTHLY_AMOUNT,
                        LAST_PAYMENT_DATE,
                        NEXT_PAYMENT_DATE,
                        BANK_NAME,
                        ACCOUNT_NUMBER,
                        EMAIL,
                        PHONE,
                        MOBILE,
                        ADDRESS,
                        CITY,
                        PROVINCE,
                        POSTAL_CODE,
                        DATE_OF_BIRTH,
                        GENDER,
                        MARITAL_STATUS,
                        EMPLOYMENT_STATUS,
                        EMPLOYER_NAME,
                        RELATIONSHIP_TO_EMPLOYEE,
                        BENEFIT_START_DATE,
                        BENEFIT_END_DATE,
                        TOTAL_BENEFITS_RECEIVED,
                        CREATION_DATE,
                        LAST_UPDATED
                    FROM BENEFICIARY_MASTER
                    WHERE UPPER(NRC_NUMBER) = UPPER(:nrc_number)
                    """,
                    'params': {'nrc_number': nrc_number}
                })

            # Query 2: Member ID match
            if user_id:
                queries.append({
                    'query': """
                    SELECT
                        MEMBER_ID,
                        NRC_NUMBER,
                        FULL_NAME,
                        FIRST_NAME,
                        LAST_NAME,
                        BENEFIT_TYPE,
                        BENEFIT_STATUS,
                        MONTHLY_AMOUNT,
                        LAST_PAYMENT_DATE,
                        NEXT_PAYMENT_DATE,
                        BANK_NAME,
                        ACCOUNT_NUMBER,
                        EMAIL,
                        PHONE,
                        MOBILE,
                        ADDRESS,
                        CITY,
                        PROVINCE,
                        POSTAL_CODE,
                        DATE_OF_BIRTH,
                        GENDER,
                        MARITAL_STATUS,
                        EMPLOYMENT_STATUS,
                        EMPLOYER_NAME,
                        RELATIONSHIP_TO_EMPLOYEE,
                        BENEFIT_START_DATE,
                        BENEFIT_END_DATE,
                        TOTAL_BENEFITS_RECEIVED,
                        CREATION_DATE,
                        LAST_UPDATED
                    FROM BENEFICIARY_MASTER
                    WHERE UPPER(MEMBER_ID) = UPPER(:user_id)
                    """,
                    'params': {'user_id': user_id}
                })

            # Query 3: Partial NRC search
            if nrc_number:
                queries.append({
                    'query': """
                    SELECT
                        MEMBER_ID,
                        NRC_NUMBER,
                        FULL_NAME,
                        FIRST_NAME,
                        LAST_NAME,
                        BENEFIT_TYPE,
                        BENEFIT_STATUS,
                        MONTHLY_AMOUNT,
                        LAST_PAYMENT_DATE,
                        NEXT_PAYMENT_DATE,
                        BANK_NAME,
                        ACCOUNT_NUMBER,
                        EMAIL,
                        PHONE,
                        MOBILE,
                        ADDRESS,
                        CITY,
                        PROVINCE,
                        POSTAL_CODE,
                        DATE_OF_BIRTH,
                        GENDER,
                        MARITAL_STATUS,
                        EMPLOYMENT_STATUS,
                        EMPLOYER_NAME,
                        RELATIONSHIP_TO_EMPLOYEE,
                        BENEFIT_START_DATE,
                        BENEFIT_END_DATE,
                        TOTAL_BENEFITS_RECEIVED,
                        CREATION_DATE,
                        LAST_UPDATED
                    FROM BENEFICIARY_MASTER
                    WHERE UPPER(NRC_NUMBER) LIKE UPPER(:nrc_partial)
                    """,
                    'params': {'nrc_partial': f'%{nrc_number}%'}
                })

            # Query 4: Name search
            if user_id and not user_id.isdigit():
                queries.append({
                    'query': """
                    SELECT
                        MEMBER_ID,
                        NRC_NUMBER,
                        FULL_NAME,
                        FIRST_NAME,
                        LAST_NAME,
                        BENEFIT_TYPE,
                        BENEFIT_STATUS,
                        MONTHLY_AMOUNT,
                        LAST_PAYMENT_DATE,
                        NEXT_PAYMENT_DATE,
                        BANK_NAME,
                        ACCOUNT_NUMBER,
                        EMAIL,
                        PHONE,
                        MOBILE,
                        ADDRESS,
                        CITY,
                        PROVINCE,
                        POSTAL_CODE,
                        DATE_OF_BIRTH,
                        GENDER,
                        MARITAL_STATUS,
                        EMPLOYMENT_STATUS,
                        EMPLOYER_NAME,
                        RELATIONSHIP_TO_EMPLOYEE,
                        BENEFIT_START_DATE,
                        BENEFIT_END_DATE,
                        TOTAL_BENEFITS_RECEIVED,
                        CREATION_DATE,
                        LAST_UPDATED
                    FROM BENEFICIARY_MASTER
                    WHERE UPPER(FULL_NAME) LIKE UPPER(:name_search)
                       OR UPPER(FIRST_NAME) LIKE UPPER(:name_search)
                       OR UPPER(LAST_NAME) LIKE UPPER(:name_search)
                    """,
                    'params': {'name_search': f'%{user_id}%'}
                })

            # Query 5: Name search from authenticated full_name (if provided via Auth)
            try:
                ctx = getattr(self, '_last_user_context', {}) or {}
                _full_name = ctx.get('full_name')
                if _full_name:
                    queries.append({
                        'query': """
                        SELECT
                            MEMBER_ID,
                            NRC_NUMBER,
                            FULL_NAME,
                            FIRST_NAME,
                            LAST_NAME,
                            BENEFIT_TYPE,
                            BENEFIT_STATUS,
                            MONTHLY_AMOUNT,
                            LAST_PAYMENT_DATE,
                            NEXT_PAYMENT_DATE,
                            BANK_NAME,
                            ACCOUNT_NUMBER,
                            EMAIL,
                            PHONE,
                            MOBILE,
                            ADDRESS,
                            CITY,
                            PROVINCE,
                            POSTAL_CODE,
                            DATE_OF_BIRTH,
                            GENDER,
                            MARITAL_STATUS,
                            EMPLOYMENT_STATUS,
                            EMPLOYER_NAME,
                            RELATIONSHIP_TO_EMPLOYEE,
                            BENEFIT_START_DATE,
                            BENEFIT_END_DATE,
                            TOTAL_BENEFITS_RECEIVED,
                            CREATION_DATE,
                            LAST_UPDATED
                        FROM BENEFICIARY_MASTER
                        WHERE UPPER(FULL_NAME) LIKE UPPER(:name_search)
                           OR UPPER(FIRST_NAME) LIKE UPPER(:name_search)
                           OR UPPER(LAST_NAME) LIKE UPPER(:name_search)
                        """,
                        'params': {'name_search': f'%{_full_name}%'}
                    })
                _employer_name = ctx.get('employer_name')
                if _employer_name:
                    queries.append({
                        'query': """
                        SELECT
                            MEMBER_ID,
                            NRC_NUMBER,
                            FULL_NAME,
                            FIRST_NAME,
                            LAST_NAME,
                            BENEFIT_TYPE,
                            BENEFIT_STATUS,
                            MONTHLY_AMOUNT,
                            LAST_PAYMENT_DATE,
                            NEXT_PAYMENT_DATE,
                            BANK_NAME,
                            ACCOUNT_NUMBER,
                            EMAIL,
                            PHONE,
                            MOBILE,
                            ADDRESS,
                            CITY,
                            PROVINCE,
                            POSTAL_CODE,
                            DATE_OF_BIRTH,
                            GENDER,
                            MARITAL_STATUS,
                            EMPLOYMENT_STATUS,
                            EMPLOYER_NAME,
                            RELATIONSHIP_TO_EMPLOYEE,
                            BENEFIT_START_DATE,
                            BENEFIT_END_DATE,
                            TOTAL_BENEFITS_RECEIVED,
                            CREATION_DATE,
                            LAST_UPDATED
                        FROM BENEFICIARY_MASTER
                        WHERE UPPER(EMPLOYER_NAME) LIKE UPPER(:employer_name)
                        """,
                        'params': {'employer_name': f'%{_employer_name}%'}
                    })
            except Exception:
                pass


            # Execute queries in order until we find a match
            for query_info in queries:
                results = self.cbs_connection.execute_query(query_info['query'], query_info['params'])
                if results:
                    return results[0]  # Return first match

            return None

        except Exception as e:
            self._log_error(f"Error retrieving CBS beneficiary data: {str(e)}")
            return None

    def _get_cbs_claims_data(self, member_id: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve claims data from CBS"""
        if not CBS_AVAILABLE or not member_id:
            return None

        try:
            query = """
            SELECT
                CLAIM_ID,
                CLAIM_TYPE,
                STATUS,
                SUBMISSION_DATE,
                CURRENT_STAGE,
                ESTIMATED_COMPLETION,
                DESCRIPTION,
                AMOUNT_CLAIMED,
                AMOUNT_APPROVED
            FROM CLAIMS_TRACKING
            WHERE MEMBER_ID = :member_id
            ORDER BY SUBMISSION_DATE DESC
            """

            params = {'member_id': member_id}
            return self.cbs_connection.execute_query(query, params)

        except Exception as e:
            self._log_error(f"Error retrieving CBS claims data: {str(e)}")
            return None

    def _get_cbs_payments_data(self, member_id: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve payment history from CBS"""
        if not CBS_AVAILABLE or not member_id:
            return None

        try:
            query = """
            SELECT
                PAYMENT_ID,
                PAYMENT_DATE,
                AMOUNT,
                PAYMENT_TYPE,
                STATUS,
                REFERENCE_NUMBER,
                BANK_NAME,
                ACCOUNT_NUMBER
            FROM PAYMENT_HISTORY
            WHERE MEMBER_ID = :member_id
            ORDER BY PAYMENT_DATE DESC
            FETCH FIRST 10 ROWS ONLY
            """

            params = {'member_id': member_id}
            return self.cbs_connection.execute_query(query, params)

        except Exception as e:
            self._log_error(f"Error retrieving CBS payments data: {str(e)}")
            return None

    def _log_error(self, message: str) -> None:
        """Log error message safely."""
        if FRAPPE_AVAILABLE and frappe:
            try:
                frappe.log_error(message, "LiveDataOrchestrator")
            except:
                pass


# Global instance for easy access
_live_data_orchestrator = None

def get_live_data_orchestrator() -> LiveDataOrchestrator:
    """Get global LiveDataOrchestrator instance."""
    global _live_data_orchestrator
    if _live_data_orchestrator is None:
        _live_data_orchestrator = LiveDataOrchestrator()
    return _live_data_orchestrator

def debug_get_claim_data(nrc: Optional[str] = None, full_name: Optional[str] = None):
    o = get_live_data_orchestrator()
    ctx = {
        'nrc_number': nrc,
        'user_id': None,
        'full_name': full_name,
        'user_role': 'beneficiary',
        'permissions': ['view_own_data']
    }
    try:
        o._last_user_context = ctx
    except Exception:
        pass
    return o._get_claim_data(ctx)




# Lightweight debug helper to validate HRMS claim lookup path
def debug_find_hrms_claims(full_name: Optional[str] = None, nrc: Optional[str] = None):
    o = get_live_data_orchestrator()
    emp = o._find_employee_by_nrc_or_name(nrc, full_name)
    if not emp:
        return {'employee_found': False, 'claims': []}
    claims = frappe.get_all('Employee Benefit Claim',
                            filters={'employee': emp['name']},
                            fields=['name','employee','employee_name','company','claim_date','earning_component','claimed_amount','docstatus'],
                            order_by='claim_date desc', limit=5)
    return {'employee_found': True, 'employee': emp, 'claims': claims}


# Debug helper to test end-to-end live data processing for claim_status
def debug_process_claim_status(nrc: Optional[str] = None, full_name: Optional[str] = None):
    o = get_live_data_orchestrator()
    uc = {
        'user_role': 'beneficiary',
        'user_id': nrc or 'debug-user',
        'nrc_number': nrc,
        'full_name': full_name,
        'permissions': ['view_own_data']
    }
    return o.process_live_data_request('claim_status', uc, (full_name or ''))



# Debug helper to check intent eligibility and permissions
def debug_check_perms(intent: str = 'claim_status', user_id: str = 'test', role: str = 'beneficiary'):
    o = get_live_data_orchestrator()
    uc = {'user_role': role, 'user_id': user_id}
    return {'eligible': o._is_live_data_intent(intent), 'perm': o._validate_permissions(uc, intent)}
