"""
Employer Contribution Service for WCFCB Assistant CRM
Provides real-time employer contribution tracking and status monitoring

Phase 3.1.3 Implementation
"""

import frappe
from frappe.utils import now, get_datetime, add_months
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class EmployerContributionService:
    """
    Service for real-time employer contribution tracking and status monitoring
    Provides comprehensive contribution management and compliance tracking
    """
    
    def __init__(self):
        """Initialize Employer Contribution Service"""
        self.service_name = "Employer Contribution Service"
        self.api_base_url = self._get_contribution_api_base_url()
        self.api_key = self._get_contribution_api_key()
        self.cache_duration = 600  # 10 minutes cache for contribution data
        
        # Contribution status definitions
        self.contribution_statuses = {
            'current': 'All contributions are up to date',
            'overdue': 'Contributions are overdue',
            'partial': 'Partial payment received',
            'pending': 'Payment is being processed',
            'delinquent': 'Account is delinquent',
            'suspended': 'Account is suspended due to non-payment',
            'under_review': 'Contribution amount under review',
            'adjusted': 'Contribution amount has been adjusted'
        }
        
        # Contribution types
        self.contribution_types = {
            'workers_comp': 'Workers Compensation Premium',
            'assessment': 'Special Assessment',
            'penalty': 'Late Payment Penalty',
            'interest': 'Interest on Overdue Amount',
            'adjustment': 'Premium Adjustment',
            'refund': 'Premium Refund'
        }
        
        # Payment frequencies
        self.payment_frequencies = {
            'monthly': 'Monthly payments',
            'quarterly': 'Quarterly payments',
            'annually': 'Annual payments',
            'as_needed': 'As needed basis'
        }
    
    def get_employer_contribution_status(self, employer_id: str, 
                                       user_context: Dict = None) -> Dict[str, Any]:
        """
        Get current contribution status for an employer
        
        Args:
            employer_id: Unique employer identifier
            user_context: User context for authorization
            
        Returns:
            Dict containing employer contribution status
        """
        try:
            # Validate user authorization
            if not self._validate_employer_access(user_context, employer_id):
                return {
                    'success': False,
                    'error': 'Unauthorized access to employer contribution information',
                    'employer_id': employer_id
                }
            
            # Check cache first
            cached_status = self._get_cached_contribution_status(employer_id)
            if cached_status:
                return cached_status
            
            # Fetch from live contribution system
            contribution_data = self._fetch_live_contribution_status(employer_id)
            
            if contribution_data:
                # Process and format contribution status
                formatted_status = self._format_contribution_status(contribution_data)
                
                # Cache the result
                self._cache_contribution_status(employer_id, formatted_status)
                
                return formatted_status
            else:
                return {
                    'success': False,
                    'error': 'Employer contribution data not found',
                    'employer_id': employer_id
                }
                
        except Exception as e:
            frappe.log_error(f"Employer contribution status error: {str(e)}", "EmployerContributionService")
            return {
                'success': False,
                'error': 'Unable to retrieve employer contribution status',
                'employer_id': employer_id,
                'technical_error': str(e)
            }
    
    def get_contribution_history(self, employer_id: str, months_back: int = 12,
                               user_context: Dict = None) -> Dict[str, Any]:
        """
        Get contribution payment history for an employer
        
        Args:
            employer_id: Unique employer identifier
            months_back: Number of months of history to retrieve
            user_context: User context for authorization
            
        Returns:
            Dict containing contribution payment history
        """
        try:
            # Validate access
            if not self._validate_employer_access(user_context, employer_id):
                return {
                    'success': False,
                    'error': 'Unauthorized access to contribution history'
                }
            
            # Fetch contribution history
            history_data = self._fetch_contribution_history(employer_id, months_back)
            
            if history_data:
                # Analyze payment patterns
                analysis = self._analyze_contribution_patterns(history_data)
                
                return {
                    'success': True,
                    'employer_id': employer_id,
                    'contribution_history': history_data,
                    'analysis': analysis,
                    'months_covered': months_back,
                    'total_payments': len(history_data),
                    'last_updated': now()
                }
            else:
                return {
                    'success': True,
                    'employer_id': employer_id,
                    'contribution_history': [],
                    'message': 'No contribution history found'
                }
                
        except Exception as e:
            frappe.log_error(f"Contribution history error: {str(e)}", "EmployerContributionService")
            return {
                'success': False,
                'error': 'Unable to retrieve contribution history',
                'technical_error': str(e)
            }
    
    def check_outstanding_contributions(self, employer_id: str,
                                      user_context: Dict = None) -> Dict[str, Any]:
        """
        Check for outstanding contributions that require attention
        
        Args:
            employer_id: Unique employer identifier
            user_context: User context for authorization
            
        Returns:
            Dict containing outstanding contribution information
        """
        try:
            # Validate access
            if not self._validate_employer_access(user_context, employer_id):
                return {
                    'success': False,
                    'error': 'Unauthorized access to outstanding contributions'
                }
            
            # Fetch outstanding contributions
            outstanding_data = self._fetch_outstanding_contributions(employer_id)
            
            if outstanding_data:
                # Categorize by urgency
                urgent_items = []
                standard_items = []
                
                for item in outstanding_data:
                    if self._is_contribution_urgent(item):
                        urgent_items.append(item)
                    else:
                        standard_items.append(item)
                
                # Calculate totals
                total_outstanding = sum(item.get('amount', 0) for item in outstanding_data)
                
                return {
                    'success': True,
                    'employer_id': employer_id,
                    'has_outstanding': True,
                    'urgent_items': urgent_items,
                    'standard_items': standard_items,
                    'total_outstanding': total_outstanding,
                    'total_items': len(outstanding_data),
                    'recommendations': self._get_contribution_recommendations(outstanding_data),
                    'payment_options': self._get_payment_options(employer_id),
                    'last_updated': now()
                }
            else:
                return {
                    'success': True,
                    'employer_id': employer_id,
                    'has_outstanding': False,
                    'message': 'No outstanding contributions'
                }
                
        except Exception as e:
            frappe.log_error(f"Outstanding contributions check error: {str(e)}", "EmployerContributionService")
            return {
                'success': False,
                'error': 'Unable to check outstanding contributions',
                'technical_error': str(e)
            }
    
    def get_contribution_schedule(self, employer_id: str,
                                user_context: Dict = None) -> Dict[str, Any]:
        """
        Get upcoming contribution schedule for an employer
        
        Args:
            employer_id: Unique employer identifier
            user_context: User context for authorization
            
        Returns:
            Dict containing contribution schedule information
        """
        try:
            # Validate access
            if not self._validate_employer_access(user_context, employer_id):
                return {
                    'success': False,
                    'error': 'Unauthorized access to contribution schedule'
                }
            
            # Fetch contribution schedule
            schedule_data = self._fetch_contribution_schedule(employer_id)
            
            if schedule_data:
                # Process upcoming payments
                upcoming_payments = self._process_upcoming_payments(schedule_data)
                
                return {
                    'success': True,
                    'employer_id': employer_id,
                    'contribution_schedule': schedule_data,
                    'upcoming_payments': upcoming_payments,
                    'payment_frequency': schedule_data.get('frequency', 'monthly'),
                    'next_due_date': self._get_next_due_date(schedule_data),
                    'estimated_amounts': self._get_estimated_amounts(schedule_data),
                    'last_updated': now()
                }
            else:
                return {
                    'success': False,
                    'error': 'Contribution schedule not found',
                    'employer_id': employer_id
                }
                
        except Exception as e:
            frappe.log_error(f"Contribution schedule error: {str(e)}", "EmployerContributionService")
            return {
                'success': False,
                'error': 'Unable to retrieve contribution schedule',
                'technical_error': str(e)
            }
    
    def calculate_contribution_estimate(self, employer_id: str, payroll_data: Dict,
                                      user_context: Dict = None) -> Dict[str, Any]:
        """
        Calculate estimated contribution based on payroll data
        
        Args:
            employer_id: Unique employer identifier
            payroll_data: Payroll information for calculation
            user_context: User context for authorization
            
        Returns:
            Dict containing contribution estimate
        """
        try:
            # Validate access
            if not self._validate_employer_access(user_context, employer_id):
                return {
                    'success': False,
                    'error': 'Unauthorized access to contribution calculation'
                }

            # For demo purposes, return a simple calculation
            return {
                'success': True,
                'employer_id': employer_id,
                'estimated_contribution': 2500.00,
                'calculation_breakdown': {
                    'base_premium': 2000.00,
                    'experience_modifier': 1.25,
                    'total': 2500.00
                },
                'rate_information': {
                    'base_rate': 0.05,
                    'experience_rate': 0.0125
                },
                'due_date': '2025-03-15',
                'calculation_date': now()
            }

        except Exception as e:
            frappe.log_error(f"Contribution calculation error: {str(e)}", "EmployerContributionService")
            return {
                'success': False,
                'error': 'Unable to calculate contribution estimate',
                'technical_error': str(e)
            }

    def _get_contribution_api_base_url(self) -> str:
        """Get contribution API base URL from settings"""
        try:
            return frappe.db.get_single_value("Assistant CRM Settings", "contribution_api_url") or "https://api.wcfcb.gov/contributions"
        except Exception:
            return "https://api.wcfcb.gov/contributions"

    def _get_contribution_api_key(self) -> str:
        """Get contribution API key from settings"""
        try:
            return frappe.db.get_single_value("Assistant CRM Settings", "contribution_api_key") or "demo_contribution_key"
        except Exception:
            return "demo_contribution_key"

    def _validate_employer_access(self, user_context: Dict, employer_id: str) -> bool:
        """Validate user has access to employer contribution information"""
        if not user_context:
            return False

        # Check if user is authorized for this employer
        user_roles = user_context.get('roles', [])
        if 'System Manager' in user_roles or 'WCFCB Staff' in user_roles:
            return True

        # Check if user is associated with this employer
        user_employer = user_context.get('employer_id')
        if user_employer == employer_id:
            return True

        return False

    def _get_cached_contribution_status(self, employer_id: str) -> Optional[Dict]:
        """Get cached contribution status if available and not expired"""
        try:
            cache_key = f"contribution_status_{employer_id}"
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

    def _cache_contribution_status(self, employer_id: str, status_data: Dict) -> None:
        """Cache contribution status for performance"""
        try:
            cache_key = f"contribution_status_{employer_id}"
            cache_data = {
                'data': status_data,
                'cached_at': now()
            }
            frappe.cache().set_value(cache_key, cache_data, expires_in_sec=self.cache_duration)
        except Exception as e:
            frappe.log_error(f"Contribution status caching error: {str(e)}", "EmployerContributionService")

    def _fetch_live_contribution_status(self, employer_id: str) -> Optional[Dict]:
        """Fetch contribution status from live WCFCB contribution system"""
        try:
            # Demo contribution data - in production this would come from WCFCB API
            demo_contributions = {
                'EMP001': {
                    'employer_id': 'EMP001',
                    'employer_name': 'ABC Construction Co.',
                    'account_number': 'WC-ACC-001',
                    'status': 'current',
                    'current_balance': 0.00,
                    'last_payment_date': '2025-01-15',
                    'last_payment_amount': 2500.00,
                    'next_due_date': '2025-02-15',
                    'estimated_next_amount': 2500.00,
                    'payment_frequency': 'monthly',
                    'policy_number': 'POL-2025-001',
                    'coverage_period': '2025-01-01 to 2025-12-31'
                },
                'EMP002': {
                    'employer_id': 'EMP002',
                    'employer_name': 'XYZ Manufacturing',
                    'account_number': 'WC-ACC-002',
                    'status': 'overdue',
                    'current_balance': 1250.00,
                    'last_payment_date': '2024-12-15',
                    'last_payment_amount': 1800.00,
                    'next_due_date': '2025-01-15',
                    'estimated_next_amount': 1800.00,
                    'payment_frequency': 'monthly',
                    'policy_number': 'POL-2025-002',
                    'coverage_period': '2025-01-01 to 2025-12-31',
                    'days_overdue': 18
                },
                'EMP003': {
                    'employer_id': 'EMP003',
                    'employer_name': 'Tech Solutions Inc.',
                    'account_number': 'WC-ACC-003',
                    'status': 'partial',
                    'current_balance': 500.00,
                    'last_payment_date': '2025-01-20',
                    'last_payment_amount': 1000.00,
                    'next_due_date': '2025-02-15',
                    'estimated_next_amount': 1500.00,
                    'payment_frequency': 'monthly',
                    'policy_number': 'POL-2025-003',
                    'coverage_period': '2025-01-01 to 2025-12-31'
                }
            }

            return demo_contributions.get(employer_id)

        except Exception as e:
            frappe.log_error(f"Live contribution status fetch error: {str(e)}", "EmployerContributionService")
            return None

    def _format_contribution_status(self, contribution_data: Dict) -> Dict[str, Any]:
        """Format contribution data for consistent response"""
        try:
            status = contribution_data.get('status', 'unknown')

            return {
                'success': True,
                'employer_id': contribution_data.get('employer_id'),
                'employer_name': contribution_data.get('employer_name'),
                'account_number': contribution_data.get('account_number'),
                'status': status,
                'status_description': self.contribution_statuses.get(status, 'Unknown status'),
                'current_balance': contribution_data.get('current_balance', 0.00),
                'last_payment_date': contribution_data.get('last_payment_date'),
                'last_payment_amount': contribution_data.get('last_payment_amount'),
                'next_due_date': contribution_data.get('next_due_date'),
                'estimated_next_amount': contribution_data.get('estimated_next_amount'),
                'payment_frequency': contribution_data.get('payment_frequency'),
                'policy_number': contribution_data.get('policy_number'),
                'coverage_period': contribution_data.get('coverage_period'),
                'days_overdue': contribution_data.get('days_overdue', 0),
                'last_updated': now(),
                'next_action': self._get_next_action_for_contribution(status),
                'urgency_level': self._get_urgency_level(status, contribution_data.get('days_overdue', 0)),
                'payment_methods': self._get_available_payment_methods()
            }
        except Exception as e:
            frappe.log_error(f"Contribution formatting error: {str(e)}", "EmployerContributionService")
            return {
                'success': False,
                'error': 'Unable to format contribution data'
            }

    def _get_next_action_for_contribution(self, status: str) -> str:
        """Get recommended next action based on contribution status"""
        actions = {
            'current': 'Account is current - no action needed',
            'overdue': 'Submit payment immediately to avoid penalties',
            'partial': 'Submit remaining balance to complete payment',
            'pending': 'Payment is being processed - no action needed',
            'delinquent': 'Contact WCFCB immediately to resolve delinquency',
            'suspended': 'Contact WCFCB to reinstate account',
            'under_review': 'Await review completion',
            'adjusted': 'Review adjustment and submit any additional payment if required'
        }
        return actions.get(status, 'Contact WCFCB for guidance')

    def _get_urgency_level(self, status: str, days_overdue: int) -> str:
        """Determine urgency level for contribution status"""
        if status in ['suspended', 'delinquent']:
            return 'critical'
        elif status == 'overdue':
            if days_overdue > 30:
                return 'high'
            elif days_overdue > 15:
                return 'medium'
            else:
                return 'low'
        elif status == 'partial':
            return 'medium'
        else:
            return 'low'

    def _get_available_payment_methods(self) -> List[str]:
        """Get available payment methods for contributions"""
        return [
            'Online payment portal',
            'Bank transfer',
            'Check payment',
            'Phone payment',
            'Automatic deduction'
        ]

    def _fetch_contribution_history(self, employer_id: str, months_back: int) -> List[Dict]:
        """Fetch contribution payment history"""
        try:
            # Demo contribution history
            demo_history = {
                'EMP001': [
                    {
                        'payment_date': '2025-01-15',
                        'amount': 2500.00,
                        'type': 'workers_comp',
                        'period': '2025-01',
                        'status': 'completed'
                    },
                    {
                        'payment_date': '2024-12-15',
                        'amount': 2500.00,
                        'type': 'workers_comp',
                        'period': '2024-12',
                        'status': 'completed'
                    },
                    {
                        'payment_date': '2024-11-15',
                        'amount': 2500.00,
                        'type': 'workers_comp',
                        'period': '2024-11',
                        'status': 'completed'
                    }
                ],
                'EMP002': [
                    {
                        'payment_date': '2024-12-15',
                        'amount': 1800.00,
                        'type': 'workers_comp',
                        'period': '2024-12',
                        'status': 'completed'
                    },
                    {
                        'payment_date': '2024-11-20',
                        'amount': 1800.00,
                        'type': 'workers_comp',
                        'period': '2024-11',
                        'status': 'completed'
                    }
                ]
            }

            return demo_history.get(employer_id, [])

        except Exception as e:
            frappe.log_error(f"Contribution history fetch error: {str(e)}", "EmployerContributionService")
            return []

    def _analyze_contribution_patterns(self, history_data: List[Dict]) -> Dict[str, Any]:
        """Analyze contribution payment patterns"""
        try:
            if not history_data:
                return {'total_paid': 0, 'average_payment': 0, 'payment_consistency': 'No data'}

            total_paid = sum(payment.get('amount', 0) for payment in history_data)
            average_payment = total_paid / len(history_data)

            # Check payment consistency
            on_time_payments = sum(1 for payment in history_data if payment.get('status') == 'completed')
            consistency_rate = on_time_payments / len(history_data)

            if consistency_rate >= 0.95:
                consistency = 'Excellent'
            elif consistency_rate >= 0.8:
                consistency = 'Good'
            elif consistency_rate >= 0.6:
                consistency = 'Fair'
            else:
                consistency = 'Poor'

            return {
                'total_paid': total_paid,
                'average_payment': round(average_payment, 2),
                'total_payments': len(history_data),
                'on_time_payments': on_time_payments,
                'consistency_rate': round(consistency_rate * 100, 1),
                'payment_consistency': consistency,
                'analysis_date': now()
            }

        except Exception as e:
            frappe.log_error(f"Contribution analysis error: {str(e)}", "EmployerContributionService")
            return {'error': 'Unable to analyze contribution patterns'}

    def _fetch_outstanding_contributions(self, employer_id: str) -> List[Dict]:
        """Fetch outstanding contributions for employer"""
        try:
            # Demo outstanding contributions
            demo_outstanding = {
                'EMP002': [
                    {
                        'type': 'workers_comp',
                        'period': '2025-01',
                        'amount': 1800.00,
                        'due_date': '2025-01-15',
                        'days_overdue': 18,
                        'penalty': 90.00,
                        'interest': 25.00
                    }
                ],
                'EMP003': [
                    {
                        'type': 'workers_comp',
                        'period': '2025-01',
                        'amount': 500.00,
                        'due_date': '2025-01-15',
                        'days_overdue': 18,
                        'penalty': 0.00,
                        'interest': 0.00
                    }
                ]
            }

            return demo_outstanding.get(employer_id, [])

        except Exception as e:
            frappe.log_error(f"Outstanding contributions fetch error: {str(e)}", "EmployerContributionService")
            return []

    def _is_contribution_urgent(self, contribution: Dict) -> bool:
        """Determine if contribution requires urgent attention"""
        try:
            days_overdue = contribution.get('days_overdue', 0)
            amount = contribution.get('amount', 0)

            # Urgent criteria
            if days_overdue > 30:  # More than 30 days overdue
                return True
            if amount > 5000 and days_overdue > 15:  # Large amounts overdue more than 15 days
                return True
            if contribution.get('penalty', 0) > 0:  # Any penalties applied
                return True

            return False

        except Exception:
            return False

    def _get_contribution_recommendations(self, outstanding_items: List[Dict]) -> List[str]:
        """Get recommendations for outstanding contributions"""
        try:
            recommendations = []

            total_overdue = sum(item.get('days_overdue', 0) for item in outstanding_items)
            total_amount = sum(item.get('amount', 0) for item in outstanding_items)

            if total_overdue > 30:
                recommendations.append("Contact WCFCB immediately to discuss payment arrangements")
            elif total_overdue > 15:
                recommendations.append("Submit payment as soon as possible to avoid additional penalties")

            if total_amount > 10000:
                recommendations.append("Consider setting up a payment plan for large outstanding amounts")

            if any(item.get('penalty', 0) > 0 for item in outstanding_items):
                recommendations.append("Penalties are being applied - immediate payment recommended")

            if not recommendations:
                recommendations.append("Submit outstanding payments by the next due date")

            return recommendations

        except Exception:
            return ["Contact WCFCB for payment guidance"]

    def _get_payment_options(self, employer_id: str) -> List[Dict]:
        """Get available payment options for employer"""
        return [
            {
                'method': 'online',
                'name': 'Online Payment Portal',
                'description': 'Pay securely online with bank account or credit card',
                'processing_time': 'Immediate'
            },
            {
                'method': 'bank_transfer',
                'name': 'Bank Transfer',
                'description': 'Direct bank transfer to WCFCB account',
                'processing_time': '1-2 business days'
            },
            {
                'method': 'phone',
                'name': 'Phone Payment',
                'description': 'Call WCFCB to make payment over the phone',
                'processing_time': 'Immediate'
            },
            {
                'method': 'check',
                'name': 'Check Payment',
                'description': 'Mail check to WCFCB office',
                'processing_time': '3-5 business days'
            }
        ]


def get_employer_contribution_service():
    """Factory function to get EmployerContributionService instance"""
    return EmployerContributionService()
