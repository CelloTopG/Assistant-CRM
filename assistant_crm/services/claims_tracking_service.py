"""
Claims Tracking Service for WCFCB Assistant CRM
Provides real-time claims tracking and status updates

Phase 3.1.2 Implementation
"""

import frappe
from frappe.utils import now, get_datetime
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class ClaimsTrackingService:
    """
    Service for real-time claims tracking and status updates
    Provides comprehensive claim lifecycle management and status monitoring
    """

    def __init__(self):
        """Initialize Claims Tracking Service"""
        self.service_name = "Claims Tracking Service"
        self.api_base_url = self._get_claims_api_base_url()
        self.api_key = self._get_claims_api_key()
        self.cache_duration = self._get_cache_ttl()

        # Claim status definitions
        self.claim_statuses = {
            'submitted': 'Claim has been submitted and is awaiting review',
            'under_review': 'Claim is currently being reviewed by WCFCB',
            'pending_documentation': 'Additional documentation required',
            'medical_review': 'Claim is under medical review',
            'validated': 'Claim has been validated by WCFCB',
            'approved': 'Claim has been approved for payment',
            'rejected': 'Claim has been rejected',
            'denied': 'Claim has been denied',
            'escalated': 'Claim has been escalated for higher attention',
            'closed': 'Claim has been closed',
            'appealed': 'Claim is under appeal process',
            'settled': 'Claim has been settled',
            'reopened': 'Previously closed claim has been reopened'
        }

        # Claim types for WCFCB
        self.claim_types = {
            'injury': 'Work-related injury claim',
            'illness': 'Occupational illness claim',
            'medical': 'Medical treatment claim',
            'disability': 'Disability benefits claim',
            'death': 'Death benefits claim',
            'rehabilitation': 'Vocational rehabilitation claim',
            'reimbursement': 'Medical expense reimbursement'
        }

        # Priority levels
        self.priority_levels = {
            'low': 'Standard processing',
            'medium': 'Expedited processing',
            'high': 'Priority processing',
            'urgent': 'Emergency processing'
        }

    def get_claim_status(self, claim_id: str, user_context: Dict = None) -> Dict[str, Any]:
        """
        Get real-time status for a specific claim

        Args:
            claim_id: Unique claim identifier
            user_context: User context for authorization

        Returns:
            Dict containing claim status information
        """
        try:
            # Validate user authorization
            if not self._validate_user_access(user_context, claim_id):
                return {
                    'success': False,
                    'error': 'Unauthorized access to claim information',
                    'claim_id': claim_id
                }

            # Check cache first
            cached_status = self._get_cached_claim_status(claim_id)
            if cached_status:
                return cached_status

            # Fetch from live claims system
            claim_data = self._fetch_live_claim_status(claim_id)

            if claim_data:
                # Process and format claim status
                formatted_status = self._format_claim_status(claim_data)

                # Cache the result
                self._cache_claim_status(claim_id, formatted_status)

                return formatted_status
            else:
                return {
                    'success': False,
                    'error': 'Claim not found',
                    'claim_id': claim_id
                }

        except Exception as e:
            frappe.log_error(f"Claim status retrieval error: {str(e)}", "ClaimsTrackingService")
            return {
                'success': False,
                'error': 'Unable to retrieve claim status',
                'claim_id': claim_id,
                'technical_error': str(e)
            }

    def get_user_claims(self, user_context: Dict, status_filter: str = None,
                       limit: int = 20) -> Dict[str, Any]:
        """
        Get all claims for a specific user

        Args:
            user_context: User context containing identification
            status_filter: Optional status filter (e.g., 'active', 'pending', 'closed')
            limit: Maximum number of claims to return

        Returns:
            Dict containing user's claims
        """
        try:
            # Extract user identification
            user_id = self._extract_user_id(user_context)
            if not user_id:
                return {
                    'success': False,
                    'error': 'User identification required'
                }

            # Fetch user claims from live system
            claims_data = self._fetch_user_claims(user_id, status_filter, limit)

            if claims_data:
                # Format claims for display
                formatted_claims = []
                for claim in claims_data:
                    formatted_claim = self._format_claim_status(claim)
                    formatted_claims.append(formatted_claim)

                # Categorize claims by status
                categorized_claims = self._categorize_claims(formatted_claims)

                return {
                    'success': True,
                    'user_id': user_id,
                    'claims': formatted_claims,
                    'categorized_claims': categorized_claims,
                    'total_claims': len(formatted_claims),
                    'status_filter': status_filter,
                    'last_updated': now()
                }
            else:
                return {
                    'success': True,
                    'user_id': user_id,
                    'claims': [],
                    'total_claims': 0,
                    'message': 'No claims found for this user'
                }

        except Exception as e:
            frappe.log_error(f"User claims retrieval error: {str(e)}", "ClaimsTrackingService")
            return {
                'success': False,
                'error': 'Unable to retrieve user claims',
                'technical_error': str(e)
            }

    def get_claim_timeline(self, claim_id: str, user_context: Dict = None) -> Dict[str, Any]:
        """
        Get detailed timeline for a specific claim

        Args:
            claim_id: Unique claim identifier
            user_context: User context for authorization

        Returns:
            Dict containing claim timeline and history
        """
        try:
            # Validate access
            if not self._validate_user_access(user_context, claim_id):
                return {
                    'success': False,
                    'error': 'Unauthorized access to claim timeline'
                }

            # Fetch claim timeline
            timeline_data = self._fetch_claim_timeline(claim_id)

            if timeline_data:
                # Process timeline events
                processed_timeline = self._process_timeline_events(timeline_data)

                return {
                    'success': True,
                    'claim_id': claim_id,
                    'timeline': processed_timeline,
                    'total_events': len(processed_timeline),
                    'last_updated': now()
                }
            else:
                return {
                    'success': False,
                    'error': 'Timeline not found for claim',
                    'claim_id': claim_id
                }

        except Exception as e:
            frappe.log_error(f"Claim timeline retrieval error: {str(e)}", "ClaimsTrackingService")
            return {
                'success': False,
                'error': 'Unable to retrieve claim timeline',
                'technical_error': str(e)
            }

    def check_claims_requiring_action(self, user_context: Dict) -> Dict[str, Any]:
        """
        Check for claims that require user attention or action

        Args:
            user_context: User context containing identification

        Returns:
            Dict containing claims requiring action
        """
        try:
            user_id = self._extract_user_id(user_context)
            if not user_id:
                return {
                    'success': False,
                    'error': 'User identification required'
                }

            # Fetch claims requiring action
            action_claims = self._fetch_claims_requiring_action(user_id)

            if action_claims:
                # Categorize by action type
                urgent_actions = []
                standard_actions = []
                informational = []

                for claim in action_claims:
                    action_type = claim.get('action_type', 'standard')
                    if action_type == 'urgent':
                        urgent_actions.append(claim)
                    elif action_type == 'standard':
                        standard_actions.append(claim)
                    else:
                        informational.append(claim)

                return {
                    'success': True,
                    'user_id': user_id,
                    'has_action_required': True,
                    'urgent_actions': urgent_actions,
                    'standard_actions': standard_actions,
                    'informational': informational,
                    'total_actions': len(action_claims),
                    'recommendations': self._get_action_recommendations(action_claims),
                    'last_updated': now()
                }
            else:
                return {
                    'success': True,
                    'user_id': user_id,
                    'has_action_required': False,
                    'message': 'No claims require immediate action'
                }

        except Exception as e:
            frappe.log_error(f"Claims action check error: {str(e)}", "ClaimsTrackingService")
            return {
                'success': False,
                'error': 'Unable to check claims requiring action',
                'technical_error': str(e)
            }

    def submit_claim_update(self, claim_id: str, update_data: Dict,
                           user_context: Dict = None) -> Dict[str, Any]:
        """
        Submit an update or additional information for a claim

        Args:
            claim_id: Unique claim identifier
            update_data: Update information to submit
            user_context: User context for authorization

        Returns:
            Dict containing submission result
        """
        try:
            # Validate access
            if not self._validate_user_access(user_context, claim_id):
                return {
                    'success': False,
                    'error': 'Unauthorized to update claim'
                }

            # Validate update data
            validation_result = self._validate_update_data(update_data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': 'Invalid update data',
                    'validation_errors': validation_result['errors']
                }

            # Submit update to claims system
            submission_result = self._submit_claim_update(claim_id, update_data)

            if submission_result['success']:
                return {
                    'success': True,
                    'claim_id': claim_id,
                    'update_id': submission_result.get('update_id'),
                    'message': 'Claim update submitted successfully',
                    'next_steps': self._get_next_steps_after_update(claim_id, update_data),
                    'submitted_at': now()
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to submit claim update',
                    'details': submission_result.get('error')
                }

        except Exception as e:
            frappe.log_error(f"Claim update submission error: {str(e)}", "ClaimsTrackingService")
            return {
                'success': False,
                'error': 'Unable to submit claim update',
                'technical_error': str(e)
            }

    def _get_claims_api_base_url(self) -> str:
        """Get claims API base URL from settings"""
        try:
            return frappe.db.get_single_value("Assistant CRM Settings", "claims_api_url") or "https://api.wcfcb.gov/claims"
        except Exception:
            return "https://api.wcfcb.gov/claims"

    def _get_claims_api_key(self) -> str:
        """Get claims API key from settings"""
        try:
            return frappe.db.get_single_value("Assistant CRM Settings", "claims_api_key") or "demo_claims_key"
        except Exception:
            return "demo_claims_key"

    def _get_cache_ttl(self) -> int:
        """Get cache TTL (seconds) from settings, defaults to 1 hour for richer context"""
        try:
            val = frappe.db.get_single_value("Assistant CRM Settings", "claims_cache_ttl")
            return int(val) if val else 3600
        except Exception:
            return 3600

    def _validate_user_access(self, user_context: Dict, claim_id: str) -> bool:
        """Validate user has access to claim information"""
        if not user_context:
            return False

        user_id = self._extract_user_id(user_context)
        if not user_id:
            return False

        # In production, this would check against WCFCB authorization system
        return True

    def _extract_user_id(self, user_context: Dict) -> Optional[str]:
        """Extract user ID from user context"""
        if not user_context:
            return None

        return (user_context.get('user_id') or
                user_context.get('email') or
                user_context.get('user') or
                user_context.get('member_id'))

    def _get_cached_claim_status(self, claim_id: str) -> Optional[Dict]:
        """Get cached claim status if available and not expired"""
        try:
            cache_key = f"claim_status_{claim_id}"
            cached_data = frappe.cache().get_value(cache_key)

            if cached_data:
                cache_time = cached_data.get('cached_at')
                if cache_time:
                    cache_datetime = get_datetime(cache_time)
                    if (datetime.now() - cache_datetime).seconds < self.cache_duration:
                        return cached_data.get('data')

            return None
        except Exception:
            return None

    def _cache_claim_status(self, claim_id: str, status_data: Dict) -> None:
        """Cache claim status for performance"""
        try:
            cache_key = f"claim_status_{claim_id}"
            cache_data = {
                'data': status_data,
                'cached_at': now()
            }
            frappe.cache().set_value(cache_key, cache_data, expires_in_sec=self.cache_duration)
        except Exception as e:
            frappe.log_error(f"Claim status caching error: {str(e)}", "ClaimsTrackingService")

    def _fetch_live_claim_status(self, claim_id: str) -> Optional[Dict]:
        """Fetch claim status from live WCFCB claims system"""
        try:
            # ERPNext Claim (if present)
            erp_claim = None
            if frappe.db.table_exists("Claim"):
                fields = [
                    "name", "claim_number", "status", "claim_type", "priority",
                    "submitted_date", "incident_date", "claimant", "employer",
                    "approved_by", "approved_on", "is_escalated", "amount"
                ]
                erp_claim = frappe.db.get_value("Claim", {"name": claim_id}, fields, as_dict=True) or \
                            frappe.db.get_value("Claim", {"claim_number": claim_id}, fields, as_dict=True)
                if erp_claim:
                    erp_claim["claim_id"] = erp_claim.pop("name")

            # CoreBusiness (CBS)
            cbs_claim = None
            try:
                from assistant_crm.services.corebusiness_integration_service import CoreBusinessIntegrationService
                cbs = CoreBusinessIntegrationService()
                cbs_claim = cbs.get_claim_by_id(claim_id)
            except Exception as e:
                frappe.log_error(f"CBS claim fetch error: {str(e)}", "ClaimsTrackingService")

            # Prefer ERPNext if both present; otherwise whichever exists
            return erp_claim or cbs_claim

        except Exception as e:
            frappe.log_error(f"Live claim status fetch error: {str(e)}", "ClaimsTrackingService")
            return None

    def _format_claim_status(self, claim_data: Dict) -> Dict[str, Any]:
        """Format claim data for consistent response"""
        try:
            status = claim_data.get('status', 'unknown')
            claim_type = claim_data.get('claim_type', 'unknown')
            priority = claim_data.get('priority', 'low')

            return {
                'success': True,
                'claim_id': claim_data.get('claim_id'),
                'claim_number': claim_data.get('claim_number'),
                'status': status,
                'status_description': self.claim_statuses.get(status, 'Unknown status'),
                'claim_type': claim_type,
                'claim_type_description': self.claim_types.get(claim_type, 'Unknown claim type'),
                'priority': priority,
                'priority_description': self.priority_levels.get(priority, 'Standard processing'),
                'submitted_date': claim_data.get('submitted_date'),
                'incident_date': claim_data.get('incident_date'),
                'claimant_id': claim_data.get('claimant_id') or claim_data.get('claimant'),
                'employer': claim_data.get('employer'),
                'description': claim_data.get('description'),
                'estimated_amount': claim_data.get('estimated_amount') or claim_data.get('amount'),
                'assigned_adjuster': claim_data.get('assigned_adjuster'),
                'approved_by': claim_data.get('approved_by'),
                'approved_on': claim_data.get('approved_on'),
                'is_escalated': claim_data.get('is_escalated'),
                'last_updated': now(),
                'next_action': self._get_next_action_for_claim(status),
                'estimated_resolution': self._get_estimated_resolution(status, priority),
                'required_documents': self._get_required_documents(status, claim_type)
            }
        except Exception as e:
            frappe.log_error(f"Claim formatting error: {str(e)}", "ClaimsTrackingService")
            return {
                'success': False,
                'error': 'Unable to format claim data'
            }

    def _fetch_user_claims(self, user_id: str, status_filter: str, limit: int) -> List[Dict]:
        """Fetch all claims for a user"""
        try:
            # Demo user claims data
            demo_user_claims = {
                'BEN001': [
                    {
                        'claim_id': 'CLM001',
                        'claim_number': 'WC-2025-001',
                        'status': 'under_review',
                        'claim_type': 'injury',
                        'priority': 'medium',
                        'submitted_date': '2025-01-15',
                        'incident_date': '2025-01-10',
                        'claimant_id': 'BEN001',
                        'employer': 'ABC Construction Co.',
                        'description': 'Back injury from lifting heavy materials',
                        'estimated_amount': 5000.00,
                        'assigned_adjuster': 'John Smith'
                    },
                    {
                        'claim_id': 'CLM003',
                        'claim_number': 'WC-2025-003',
                        'status': 'approved',
                        'claim_type': 'disability',
                        'priority': 'low',
                        'submitted_date': '2024-12-15',
                        'incident_date': '2024-12-10',
                        'claimant_id': 'BEN001',
                        'employer': 'ABC Construction Co.',
                        'description': 'Temporary disability due to workplace injury',
                        'estimated_amount': 8000.00,
                        'assigned_adjuster': 'John Smith'
                    }
                ],
                'BEN002': [
                    {
                        'claim_id': 'CLM002',
                        'claim_number': 'WC-2025-002',
                        'status': 'pending_documentation',
                        'claim_type': 'medical',
                        'priority': 'high',
                        'submitted_date': '2025-01-20',
                        'incident_date': '2025-01-18',
                        'claimant_id': 'BEN002',
                        'employer': 'XYZ Manufacturing',
                        'description': 'Chemical exposure requiring medical treatment',
                        'estimated_amount': 2500.00,
                        'assigned_adjuster': 'Jane Doe'
                    }
                ]
            }

            user_claims = demo_user_claims.get(user_id, [])

            # Apply status filter if provided
            if status_filter:
                if status_filter == 'active':
                    user_claims = [c for c in user_claims if c['status'] not in ['closed', 'denied', 'settled']]
                elif status_filter == 'pending':
                    user_claims = [c for c in user_claims if c['status'] in ['submitted', 'under_review', 'pending_documentation']]
                elif status_filter == 'closed':
                    user_claims = [c for c in user_claims if c['status'] in ['closed', 'denied', 'settled']]

            return user_claims[:limit]

        except Exception as e:
            frappe.log_error(f"User claims fetch error: {str(e)}", "ClaimsTrackingService")
            return []

    def _categorize_claims(self, claims: List[Dict]) -> Dict[str, List]:
        """Categorize claims by status for better organization"""
        try:
            categories = {
                'active': [],
                'pending_action': [],
                'completed': [],
                'under_review': []
            }

            for claim in claims:
                status = claim.get('status', 'unknown')

                if status in ['submitted', 'under_review', 'medical_review']:
                    categories['under_review'].append(claim)
                elif status in ['pending_documentation', 'appealed']:
                    categories['pending_action'].append(claim)
                elif status in ['approved', 'closed', 'settled']:
                    categories['completed'].append(claim)
                else:
                    categories['active'].append(claim)

            return categories

        except Exception:
            return {'active': claims, 'pending_action': [], 'completed': [], 'under_review': []}

    def _get_next_action_for_claim(self, status: str) -> str:
        """Get recommended next action based on claim status"""
        actions = {
            'submitted': 'Claim submitted - awaiting initial review',
            'under_review': 'Claim is being reviewed - no action needed',
            'pending_documentation': 'Submit required documentation',
            'medical_review': 'Awaiting medical review completion',
            'approved': 'Claim approved - payment processing',
            'denied': 'Review denial reason and consider appeal if appropriate',
            'closed': 'Claim closed - contact WCFCB if you have questions',
            'appealed': 'Appeal is being processed',
            'settled': 'Claim has been settled',
            'reopened': 'Provide any additional information requested'
        }
        return actions.get(status, 'Contact WCFCB for guidance')

    def _get_estimated_resolution(self, status: str, priority: str) -> str:
        """Get estimated resolution timeframe"""
        try:
            base_days = {
                'submitted': 5,
                'under_review': 14,
                'pending_documentation': 7,
                'medical_review': 21,
                'approved': 3,
                'appealed': 30
            }

            days = base_days.get(status, 14)

            # Adjust for priority
            if priority == 'urgent':
                days = max(1, days // 2)
            elif priority == 'high':
                days = max(2, int(days * 0.7))
            elif priority == 'low':
                days = int(days * 1.5)

            if days <= 1:
                return "1 business day"
            elif days <= 7:
                return f"{days} business days"
            elif days <= 14:
                return "1-2 weeks"
            elif days <= 30:
                return "2-4 weeks"
            else:
                return "4+ weeks"

        except Exception:
            return "Contact WCFCB for timeline"

    def _get_required_documents(self, status: str, claim_type: str) -> List[str]:
        """Get list of required documents based on status and claim type"""
        try:
            documents = []

            if status == 'pending_documentation':
                if claim_type == 'injury':
                    documents = ['Medical records', 'Incident report', 'Witness statements']
                elif claim_type == 'medical':
                    documents = ['Medical bills', 'Treatment records', 'Doctor\'s report']
                elif claim_type == 'disability':
                    documents = ['Disability assessment', 'Medical certification', 'Employment records']
                else:
                    documents = ['Additional documentation as requested by adjuster']

            return documents

        except Exception:
            return []

    def _fetch_claim_timeline(self, claim_id: str) -> Optional[List[Dict]]:
        """Fetch claim timeline events"""
        try:
            # Demo timeline data
            demo_timelines = {
                'CLM001': [
                    {
                        'date': '2025-01-15',
                        'event': 'Claim submitted',
                        'description': 'Initial claim submission received',
                        'status': 'submitted',
                        'user': 'System'
                    },
                    {
                        'date': '2025-01-16',
                        'event': 'Initial review started',
                        'description': 'Claim assigned to adjuster for initial review',
                        'status': 'under_review',
                        'user': 'John Smith'
                    },
                    {
                        'date': '2025-01-18',
                        'event': 'Medical records requested',
                        'description': 'Additional medical documentation requested',
                        'status': 'under_review',
                        'user': 'John Smith'
                    }
                ],
                'CLM002': [
                    {
                        'date': '2025-01-20',
                        'event': 'Claim submitted',
                        'description': 'Chemical exposure claim submitted',
                        'status': 'submitted',
                        'user': 'System'
                    },
                    {
                        'date': '2025-01-21',
                        'event': 'Documentation required',
                        'description': 'Medical reports and incident documentation needed',
                        'status': 'pending_documentation',
                        'user': 'Jane Doe'
                    }
                ]
            }

            return demo_timelines.get(claim_id, [])

        except Exception as e:
            frappe.log_error(f"Claim timeline fetch error: {str(e)}", "ClaimsTrackingService")
            return []

    def _process_timeline_events(self, timeline_data: List[Dict]) -> List[Dict]:
        """Process and format timeline events"""
        try:
            processed_events = []

            for event in timeline_data:
                processed_event = {
                    'date': event.get('date'),
                    'event': event.get('event'),
                    'description': event.get('description'),
                    'status': event.get('status'),
                    'user': event.get('user'),
                    'formatted_date': self._format_timeline_date(event.get('date')),
                    'event_type': self._categorize_timeline_event(event.get('event'))
                }
                processed_events.append(processed_event)

            # Sort by date (most recent first)
            processed_events.sort(key=lambda x: x.get('date', ''), reverse=True)

            return processed_events

        except Exception as e:
            frappe.log_error(f"Timeline processing error: {str(e)}", "ClaimsTrackingService")
            return timeline_data

    def _fetch_claims_requiring_action(self, user_id: str) -> List[Dict]:
        """Fetch claims that require user action"""
        try:
            # Demo claims requiring action
            demo_action_claims = {
                'BEN001': [
                    {
                        'claim_id': 'CLM001',
                        'claim_number': 'WC-2025-001',
                        'action_type': 'standard',
                        'action_required': 'Submit medical records',
                        'description': 'Additional medical documentation needed for claim review',
                        'due_date': '2025-02-15',
                        'priority': 'medium',
                        'days_remaining': 13
                    }
                ],
                'BEN002': [
                    {
                        'claim_id': 'CLM002',
                        'claim_number': 'WC-2025-002',
                        'action_type': 'urgent',
                        'action_required': 'Provide incident report',
                        'description': 'Detailed incident report required for chemical exposure claim',
                        'due_date': '2025-02-05',
                        'priority': 'high',
                        'days_remaining': 3
                    }
                ]
            }

            return demo_action_claims.get(user_id, [])

        except Exception as e:
            frappe.log_error(f"Claims requiring action fetch error: {str(e)}", "ClaimsTrackingService")
            return []

    def _get_action_recommendations(self, action_claims: List[Dict]) -> List[str]:
        """Get recommendations for claims requiring action"""
        try:
            recommendations = []

            urgent_claims = [c for c in action_claims if c.get('action_type') == 'urgent']
            overdue_claims = [c for c in action_claims if c.get('days_remaining', 0) < 0]

            if urgent_claims:
                recommendations.append(f"Immediate attention required for {len(urgent_claims)} urgent claim(s)")

            if overdue_claims:
                recommendations.append(f"{len(overdue_claims)} claim(s) are overdue - submit required documents immediately")

            for claim in action_claims:
                days_remaining = claim.get('days_remaining', 0)
                if days_remaining <= 3 and days_remaining > 0:
                    recommendations.append(f"Claim {claim.get('claim_number')} due in {days_remaining} days")

            if not recommendations:
                recommendations.append("All claims are up to date")

            return recommendations

        except Exception:
            return ["Review all claims requiring action"]

    def _validate_update_data(self, update_data: Dict) -> Dict[str, Any]:
        """Validate claim update data"""
        try:
            errors = []

            # Check required fields
            if not update_data.get('update_type'):
                errors.append("Update type is required")

            if not update_data.get('description'):
                errors.append("Update description is required")

            # Validate update type
            valid_types = ['document_submission', 'status_inquiry', 'additional_info', 'appeal']
            if update_data.get('update_type') not in valid_types:
                errors.append(f"Invalid update type. Must be one of: {', '.join(valid_types)}")

            # Validate description length
            description = update_data.get('description', '')
            if len(description) < 10:
                errors.append("Description must be at least 10 characters")
            elif len(description) > 1000:
                errors.append("Description must be less than 1000 characters")

            return {
                'valid': len(errors) == 0,
                'errors': errors
            }

        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"]
            }

    def _submit_claim_update(self, claim_id: str, update_data: Dict) -> Dict[str, Any]:
        """Submit claim update to claims system"""
        try:
            # In production, this would submit to the actual claims system
            # For demo, we'll simulate a successful submission

            import uuid
            update_id = str(uuid.uuid4())[:8]

            return {
                'success': True,
                'update_id': update_id,
                'submitted_at': now(),
                'status': 'submitted'
            }

        except Exception as e:
            frappe.log_error(f"Claim update submission error: {str(e)}", "ClaimsTrackingService")
            return {
                'success': False,
                'error': str(e)
            }

    def _get_next_steps_after_update(self, claim_id: str, update_data: Dict) -> List[str]:
        """Get next steps after submitting claim update"""
        try:
            update_type = update_data.get('update_type', '')

            next_steps = []

            if update_type == 'document_submission':
                next_steps = [
                    "Your documents have been submitted for review",
                    "You will receive confirmation within 2-3 business days",
                    "Check claim status regularly for updates"
                ]
            elif update_type == 'status_inquiry':
                next_steps = [
                    "Your inquiry has been forwarded to the assigned adjuster",
                    "Expect a response within 5 business days",
                    "You will be notified of any status changes"
                ]
            elif update_type == 'additional_info':
                next_steps = [
                    "Additional information has been added to your claim",
                    "The adjuster will review and update claim status accordingly",
                    "Monitor your claim for any further requests"
                ]
            elif update_type == 'appeal':
                next_steps = [
                    "Your appeal has been submitted to the appeals board",
                    "Appeal review process typically takes 30-45 days",
                    "You will receive written notification of the appeal decision"
                ]
            else:
                next_steps = [
                    "Your update has been submitted successfully",
                    "The claims team will review and respond as needed"
                ]

            return next_steps

        except Exception:
            return ["Your update has been submitted and will be reviewed"]

    def _format_timeline_date(self, date_str: str) -> str:
        """Format timeline date for display"""
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%B %d, %Y')
        except Exception:
            return date_str

    def _categorize_timeline_event(self, event: str) -> str:
        """Categorize timeline event type"""
        try:
            event_lower = event.lower()

            if 'submit' in event_lower:
                return 'submission'
            elif 'review' in event_lower:
                return 'review'
            elif 'request' in event_lower or 'require' in event_lower:
                return 'request'
            elif 'approv' in event_lower:
                return 'approval'
            elif 'deny' in event_lower or 'reject' in event_lower:
                return 'denial'
            else:
                return 'general'

        except Exception:
            return 'general'


def get_claims_tracking_service():
    """Factory function to get ClaimsTrackingService instance"""
    return ClaimsTrackingService()
