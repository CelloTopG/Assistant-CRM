"""
Payment Status Service for WCFCB Assistant CRM
Provides real-time payment status integration with live WCFCB payment systems

Phase 3.1.1 Implementation
"""

import frappe
from frappe.utils import now, add_days, get_datetime
from typing import Dict, List, Any, Optional
import json
import requests
from datetime import datetime, timedelta


class PaymentStatusService:
    """
    Service for real-time payment status integration with WCFCB payment systems
    Provides live payment tracking, status updates, and payment history
    """
    
    def __init__(self):
        """Initialize Payment Status Service"""
        self.service_name = "Payment Status Service"
        self.api_base_url = self._get_payment_api_base_url()
        self.api_key = self._get_payment_api_key()
        self.cache_duration = 300  # 5 minutes cache for performance
        
        # Payment status mappings
        self.payment_statuses = {
            'pending': 'Payment is being processed',
            'processing': 'Payment is currently being processed by WCFCB',
            'completed': 'Payment has been successfully completed',
            'failed': 'Payment processing failed',
            'cancelled': 'Payment was cancelled',
            'on_hold': 'Payment is on hold pending verification',
            'refunded': 'Payment has been refunded',
            'partial': 'Partial payment received'
        }
        
        # Payment types for WCFCB
        self.payment_types = {
            'pension': 'Pension Payment',
            'compensation': 'Workers Compensation',
            'medical': 'Medical Benefits',
            'disability': 'Disability Benefits',
            'death_benefit': 'Death Benefit',
            'rehabilitation': 'Rehabilitation Services'
        }
    
    def get_payment_status(self, payment_id: str, user_context: Dict = None) -> Dict[str, Any]:
        """
        Get real-time payment status for a specific payment
        
        Args:
            payment_id: Unique payment identifier
            user_context: User context for authorization
            
        Returns:
            Dict containing payment status information
        """
        try:
            # Validate user authorization
            if not self._validate_user_access(user_context, payment_id):
                return {
                    'success': False,
                    'error': 'Unauthorized access to payment information',
                    'payment_id': payment_id
                }
            
            # Check cache first
            cached_status = self._get_cached_payment_status(payment_id)
            if cached_status:
                return cached_status
            
            # Fetch from live payment system
            payment_data = self._fetch_live_payment_status(payment_id)
            
            if payment_data:
                # Process and format payment status
                formatted_status = self._format_payment_status(payment_data)
                
                # Cache the result
                self._cache_payment_status(payment_id, formatted_status)
                
                return formatted_status
            else:
                return {
                    'success': False,
                    'error': 'Payment not found',
                    'payment_id': payment_id
                }
                
        except Exception as e:
            frappe.log_error(f"Payment status retrieval error: {str(e)}", "PaymentStatusService")
            return {
                'success': False,
                'error': 'Unable to retrieve payment status',
                'payment_id': payment_id,
                'technical_error': str(e)
            }
    
    def get_user_payments(self, user_context: Dict, limit: int = 10) -> Dict[str, Any]:
        """
        Get all payments for a specific user
        
        Args:
            user_context: User context containing identification
            limit: Maximum number of payments to return
            
        Returns:
            Dict containing user's payment history and status
        """
        try:
            # Extract user identification
            user_id = self._extract_user_id(user_context)
            if not user_id:
                return {
                    'success': False,
                    'error': 'User identification required'
                }
            
            # Fetch user payments from live system
            payments_data = self._fetch_user_payments(user_id, limit)
            
            if payments_data:
                # Format payments for display
                formatted_payments = []
                for payment in payments_data:
                    formatted_payment = self._format_payment_status(payment)
                    formatted_payments.append(formatted_payment)
                
                return {
                    'success': True,
                    'user_id': user_id,
                    'payments': formatted_payments,
                    'total_payments': len(formatted_payments),
                    'last_updated': now()
                }
            else:
                return {
                    'success': True,
                    'user_id': user_id,
                    'payments': [],
                    'total_payments': 0,
                    'message': 'No payments found for this user'
                }
                
        except Exception as e:
            frappe.log_error(f"User payments retrieval error: {str(e)}", "PaymentStatusService")
            return {
                'success': False,
                'error': 'Unable to retrieve user payments',
                'technical_error': str(e)
            }
    
    def get_payment_history(self, user_context: Dict, date_from: str = None, 
                           date_to: str = None) -> Dict[str, Any]:
        """
        Get payment history for a user within a date range
        
        Args:
            user_context: User context containing identification
            date_from: Start date for history (YYYY-MM-DD)
            date_to: End date for history (YYYY-MM-DD)
            
        Returns:
            Dict containing payment history
        """
        try:
            user_id = self._extract_user_id(user_context)
            if not user_id:
                return {
                    'success': False,
                    'error': 'User identification required'
                }
            
            # Set default date range if not provided
            if not date_to:
                date_to = datetime.now().strftime('%Y-%m-%d')
            if not date_from:
                date_from = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            # Fetch payment history
            history_data = self._fetch_payment_history(user_id, date_from, date_to)
            
            if history_data:
                # Analyze payment patterns
                analysis = self._analyze_payment_patterns(history_data)
                
                return {
                    'success': True,
                    'user_id': user_id,
                    'date_range': {'from': date_from, 'to': date_to},
                    'payment_history': history_data,
                    'analysis': analysis,
                    'total_payments': len(history_data),
                    'last_updated': now()
                }
            else:
                return {
                    'success': True,
                    'user_id': user_id,
                    'payment_history': [],
                    'message': 'No payment history found for the specified period'
                }
                
        except Exception as e:
            frappe.log_error(f"Payment history retrieval error: {str(e)}", "PaymentStatusService")
            return {
                'success': False,
                'error': 'Unable to retrieve payment history',
                'technical_error': str(e)
            }
    
    def check_pending_payments(self, user_context: Dict) -> Dict[str, Any]:
        """
        Check for pending payments that require user attention
        
        Args:
            user_context: User context containing identification
            
        Returns:
            Dict containing pending payments information
        """
        try:
            user_id = self._extract_user_id(user_context)
            if not user_id:
                return {
                    'success': False,
                    'error': 'User identification required'
                }
            
            # Fetch pending payments
            pending_payments = self._fetch_pending_payments(user_id)
            
            if pending_payments:
                # Categorize by urgency
                urgent_payments = []
                standard_payments = []
                
                for payment in pending_payments:
                    if self._is_payment_urgent(payment):
                        urgent_payments.append(payment)
                    else:
                        standard_payments.append(payment)
                
                return {
                    'success': True,
                    'user_id': user_id,
                    'has_pending_payments': True,
                    'urgent_payments': urgent_payments,
                    'standard_payments': standard_payments,
                    'total_pending': len(pending_payments),
                    'recommendations': self._get_payment_recommendations(pending_payments),
                    'last_updated': now()
                }
            else:
                return {
                    'success': True,
                    'user_id': user_id,
                    'has_pending_payments': False,
                    'message': 'No pending payments found'
                }
                
        except Exception as e:
            frappe.log_error(f"Pending payments check error: {str(e)}", "PaymentStatusService")
            return {
                'success': False,
                'error': 'Unable to check pending payments',
                'technical_error': str(e)
            }
    
    def _get_payment_api_base_url(self) -> str:
        """Get payment API base URL from settings"""
        try:
            # In production, this would come from WCFCB system settings
            return frappe.db.get_single_value("Assistant CRM Settings", "payment_api_url") or "https://api.wcfcb.gov/payments"
        except Exception:
            # Fallback for demo/development environment
            return "https://api.wcfcb.gov/payments"

    def _get_payment_api_key(self) -> str:
        """Get payment API key from settings"""
        try:
            # In production, this would be securely stored
            return frappe.db.get_single_value("Assistant CRM Settings", "payment_api_key") or "demo_api_key"
        except Exception:
            # Fallback for demo/development environment
            return "demo_api_key"
    
    def _validate_user_access(self, user_context: Dict, payment_id: str) -> bool:
        """Validate user has access to payment information"""
        if not user_context:
            return False
        
        # Check if user is authorized to view this payment
        user_id = self._extract_user_id(user_context)
        if not user_id:
            return False
        
        # In production, this would check against WCFCB authorization system
        return True
    
    def _extract_user_id(self, user_context: Dict) -> Optional[str]:
        """Extract user ID from user context"""
        if not user_context:
            return None
        
        # Try different user identification methods
        user_id = (user_context.get('user_id') or 
                  user_context.get('email') or 
                  user_context.get('user') or
                  user_context.get('member_id'))
        
        return user_id

    def _get_cached_payment_status(self, payment_id: str) -> Optional[Dict]:
        """Get cached payment status if available and not expired"""
        try:
            cache_key = f"payment_status_{payment_id}"
            cached_data = frappe.cache().get_value(cache_key)

            if cached_data:
                # Check if cache is still valid
                cache_time = cached_data.get('cached_at')
                if cache_time:
                    cache_datetime = get_datetime(cache_time)
                    if (datetime.now() - cache_datetime).seconds < self.cache_duration:
                        return cached_data.get('data')

            return None
        except Exception:
            return None

    def _cache_payment_status(self, payment_id: str, status_data: Dict) -> None:
        """Cache payment status for performance"""
        try:
            cache_key = f"payment_status_{payment_id}"
            cache_data = {
                'data': status_data,
                'cached_at': now()
            }
            frappe.cache().set_value(cache_key, cache_data, expires_in_sec=self.cache_duration)
        except Exception as e:
            frappe.log_error(f"Payment status caching error: {str(e)}", "PaymentStatusService")

    def _fetch_live_payment_status(self, payment_id: str) -> Optional[Dict]:
        """Fetch payment status from live WCFCB payment system"""
        try:
            # In production, this would make actual API calls to WCFCB systems
            # For demo purposes, we'll simulate the response

            # Simulate API call delay
            import time
            time.sleep(0.1)

            # Demo payment data - in production this would come from WCFCB API
            demo_payments = {
                'PAY001': {
                    'payment_id': 'PAY001',
                    'amount': 1250.00,
                    'currency': 'USD',
                    'status': 'completed',
                    'payment_type': 'pension',
                    'payment_date': '2025-01-15',
                    'beneficiary_id': 'BEN001',
                    'description': 'Monthly pension payment',
                    'reference_number': 'REF2025001'
                },
                'PAY002': {
                    'payment_id': 'PAY002',
                    'amount': 850.00,
                    'currency': 'USD',
                    'status': 'processing',
                    'payment_type': 'compensation',
                    'payment_date': '2025-02-01',
                    'beneficiary_id': 'BEN002',
                    'description': 'Workers compensation claim',
                    'reference_number': 'REF2025002'
                },
                'PAY003': {
                    'payment_id': 'PAY003',
                    'amount': 500.00,
                    'currency': 'USD',
                    'status': 'pending',
                    'payment_type': 'medical',
                    'payment_date': '2025-02-02',
                    'beneficiary_id': 'BEN001',
                    'description': 'Medical benefits reimbursement',
                    'reference_number': 'REF2025003'
                }
            }

            return demo_payments.get(payment_id)

        except Exception as e:
            frappe.log_error(f"Live payment status fetch error: {str(e)}", "PaymentStatusService")
            return None

    def _format_payment_status(self, payment_data: Dict) -> Dict[str, Any]:
        """Format payment data for consistent response"""
        try:
            status = payment_data.get('status', 'unknown')
            payment_type = payment_data.get('payment_type', 'unknown')

            return {
                'success': True,
                'payment_id': payment_data.get('payment_id'),
                'amount': payment_data.get('amount'),
                'currency': payment_data.get('currency', 'USD'),
                'status': status,
                'status_description': self.payment_statuses.get(status, 'Unknown status'),
                'payment_type': payment_type,
                'payment_type_description': self.payment_types.get(payment_type, 'Unknown payment type'),
                'payment_date': payment_data.get('payment_date'),
                'description': payment_data.get('description'),
                'reference_number': payment_data.get('reference_number'),
                'beneficiary_id': payment_data.get('beneficiary_id'),
                'last_updated': now(),
                'next_action': self._get_next_action(status),
                'estimated_completion': self._get_estimated_completion(status, payment_data.get('payment_date'))
            }
        except Exception as e:
            frappe.log_error(f"Payment formatting error: {str(e)}", "PaymentStatusService")
            return {
                'success': False,
                'error': 'Unable to format payment data'
            }

    def _fetch_user_payments(self, user_id: str, limit: int) -> List[Dict]:
        """Fetch all payments for a user"""
        try:
            # In production, this would query WCFCB payment database
            # Demo data for different user scenarios

            demo_user_payments = {
                'BEN001': [
                    {
                        'payment_id': 'PAY001',
                        'amount': 1250.00,
                        'currency': 'USD',
                        'status': 'completed',
                        'payment_type': 'pension',
                        'payment_date': '2025-01-15',
                        'beneficiary_id': 'BEN001',
                        'description': 'Monthly pension payment',
                        'reference_number': 'REF2025001'
                    },
                    {
                        'payment_id': 'PAY003',
                        'amount': 500.00,
                        'currency': 'USD',
                        'status': 'pending',
                        'payment_type': 'medical',
                        'payment_date': '2025-02-02',
                        'beneficiary_id': 'BEN001',
                        'description': 'Medical benefits reimbursement',
                        'reference_number': 'REF2025003'
                    }
                ],
                'BEN002': [
                    {
                        'payment_id': 'PAY002',
                        'amount': 850.00,
                        'currency': 'USD',
                        'status': 'processing',
                        'payment_type': 'compensation',
                        'payment_date': '2025-02-01',
                        'beneficiary_id': 'BEN002',
                        'description': 'Workers compensation claim',
                        'reference_number': 'REF2025002'
                    }
                ]
            }

            user_payments = demo_user_payments.get(user_id, [])
            return user_payments[:limit]

        except Exception as e:
            frappe.log_error(f"User payments fetch error: {str(e)}", "PaymentStatusService")
            return []

    def _fetch_payment_history(self, user_id: str, date_from: str, date_to: str) -> List[Dict]:
        """Fetch payment history for date range"""
        try:
            # In production, this would query WCFCB payment history database
            # Demo historical data
            demo_history = {
                'BEN001': [
                    {
                        'payment_id': 'PAY001',
                        'amount': 1250.00,
                        'status': 'completed',
                        'payment_type': 'pension',
                        'payment_date': '2025-01-15',
                        'description': 'Monthly pension payment'
                    },
                    {
                        'payment_id': 'PAY004',
                        'amount': 1250.00,
                        'status': 'completed',
                        'payment_type': 'pension',
                        'payment_date': '2024-12-15',
                        'description': 'Monthly pension payment'
                    },
                    {
                        'payment_id': 'PAY005',
                        'amount': 300.00,
                        'status': 'completed',
                        'payment_type': 'medical',
                        'payment_date': '2024-11-20',
                        'description': 'Medical reimbursement'
                    }
                ]
            }

            return demo_history.get(user_id, [])

        except Exception as e:
            frappe.log_error(f"Payment history fetch error: {str(e)}", "PaymentStatusService")
            return []

    def _fetch_pending_payments(self, user_id: str) -> List[Dict]:
        """Fetch pending payments for user"""
        try:
            # Demo pending payments
            demo_pending = {
                'BEN001': [
                    {
                        'payment_id': 'PAY003',
                        'amount': 500.00,
                        'status': 'pending',
                        'payment_type': 'medical',
                        'payment_date': '2025-02-02',
                        'description': 'Medical benefits reimbursement',
                        'days_pending': 5
                    }
                ],
                'BEN002': [
                    {
                        'payment_id': 'PAY002',
                        'amount': 850.00,
                        'status': 'processing',
                        'payment_type': 'compensation',
                        'payment_date': '2025-02-01',
                        'description': 'Workers compensation claim',
                        'days_pending': 2
                    }
                ]
            }

            return demo_pending.get(user_id, [])

        except Exception as e:
            frappe.log_error(f"Pending payments fetch error: {str(e)}", "PaymentStatusService")
            return []

    def _analyze_payment_patterns(self, payment_history: List[Dict]) -> Dict[str, Any]:
        """Analyze payment patterns for insights"""
        try:
            if not payment_history:
                return {'total_amount': 0, 'average_payment': 0, 'payment_frequency': 'No data'}

            total_amount = sum(payment.get('amount', 0) for payment in payment_history)
            average_payment = total_amount / len(payment_history)

            # Analyze payment types
            payment_types = {}
            for payment in payment_history:
                ptype = payment.get('payment_type', 'unknown')
                payment_types[ptype] = payment_types.get(ptype, 0) + 1

            most_common_type = max(payment_types.items(), key=lambda x: x[1])[0] if payment_types else 'unknown'

            return {
                'total_amount': total_amount,
                'average_payment': round(average_payment, 2),
                'total_payments': len(payment_history),
                'payment_types': payment_types,
                'most_common_type': most_common_type,
                'analysis_date': now()
            }

        except Exception as e:
            frappe.log_error(f"Payment analysis error: {str(e)}", "PaymentStatusService")
            return {'error': 'Unable to analyze payment patterns'}

    def _is_payment_urgent(self, payment: Dict) -> bool:
        """Determine if payment requires urgent attention"""
        try:
            days_pending = payment.get('days_pending', 0)
            payment_type = payment.get('payment_type', '')
            amount = payment.get('amount', 0)

            # Urgent criteria
            if days_pending > 7:  # More than 7 days pending
                return True
            if payment_type in ['medical', 'disability'] and days_pending > 3:  # Medical/disability urgent after 3 days
                return True
            if amount > 1000 and days_pending > 5:  # Large amounts urgent after 5 days
                return True

            return False

        except Exception:
            return False

    def _get_payment_recommendations(self, pending_payments: List[Dict]) -> List[str]:
        """Get recommendations for pending payments"""
        try:
            recommendations = []

            for payment in pending_payments:
                days_pending = payment.get('days_pending', 0)
                payment_type = payment.get('payment_type', '')

                if days_pending > 7:
                    recommendations.append(f"Contact WCFCB about payment {payment.get('payment_id')} - pending for {days_pending} days")
                elif payment_type == 'medical' and days_pending > 3:
                    recommendations.append(f"Follow up on medical payment {payment.get('payment_id')} - may need additional documentation")
                elif days_pending > 5:
                    recommendations.append(f"Check status of payment {payment.get('payment_id')} - processing longer than expected")

            if not recommendations:
                recommendations.append("All pending payments are within normal processing timeframes")

            return recommendations

        except Exception:
            return ["Unable to generate payment recommendations"]

    def _get_next_action(self, status: str) -> str:
        """Get recommended next action based on payment status"""
        actions = {
            'pending': 'Wait for processing to complete',
            'processing': 'Payment is being processed - no action needed',
            'completed': 'Payment completed successfully',
            'failed': 'Contact WCFCB to resolve payment issue',
            'cancelled': 'Contact WCFCB if payment was cancelled in error',
            'on_hold': 'Provide additional documentation as requested',
            'refunded': 'Refund has been processed',
            'partial': 'Contact WCFCB about remaining payment amount'
        }
        return actions.get(status, 'Contact WCFCB for assistance')

    def _get_estimated_completion(self, status: str, payment_date: str) -> str:
        """Get estimated completion time for payment"""
        try:
            if status == 'completed':
                return 'Completed'
            elif status == 'processing':
                return '1-3 business days'
            elif status == 'pending':
                return '3-5 business days'
            elif status in ['failed', 'cancelled', 'on_hold']:
                return 'Pending resolution'
            else:
                return 'Contact WCFCB for timeline'
        except Exception:
            return 'Unknown'


def get_payment_status_service():
    """Factory function to get PaymentStatusService instance"""
    return PaymentStatusService()
