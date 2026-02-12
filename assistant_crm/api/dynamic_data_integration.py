#!/usr/bin/env python3

import frappe
from frappe import _
from frappe.utils import now, add_days, get_datetime, flt
import json
import requests
from datetime import datetime, timedelta
import hashlib
import time

@frappe.whitelist(allow_guest=True)
def get_dynamic_response(intent, user_context=None, query_params=None):
    """
    Main entry point for dynamic data integration
    Routes requests to appropriate handlers based on intent
    """
    try:
        # Parse user context
        context = json.loads(user_context) if user_context else {}
        params = json.loads(query_params) if query_params else {}
        
        # Route to appropriate handler
        handlers = {
            'payment_status_inquiry': handle_payment_status_query,
            'due_date_inquiry': handle_due_date_query,
            'claim_status_inquiry': handle_claim_status_query,
            'contribution_history': handle_contribution_history,
            'outstanding_balance': handle_outstanding_balance,
            'benefit_payment_status': handle_benefit_payment_status,
            'document_status': handle_document_status,
            'assessment_calculation': handle_assessment_calculation
        }
        
        handler = handlers.get(intent)
        if not handler:
            return {
                'success': False,
                'message': 'Intent not supported for dynamic data',
                'fallback_to_static': True
            }
        
        # Execute handler with authentication check
        return handler(context, params)
        
    except Exception as e:
        frappe.log_error(f"Dynamic data integration error: {str(e)}", "Dynamic Data API")
        return {
            'success': False,
            'message': 'Unable to retrieve real-time data. Please try again or contact support.',
            'escalate': True,
            'error': str(e)
        }

def handle_payment_status_query(context, params):
    """Handle employer payment status queries"""
    
    # Check authentication
    auth_result = authenticate_user(context, required_role='Employer')
    if not auth_result['success']:
        return auth_result
    
    employer_number = context.get('employer_number')
    if not employer_number:
        return {
            'success': False,
            'message': 'Employer number required for payment status inquiry',
            'escalate': True,
            'action': 'request_employer_number'
        }
    
    try:
        # Call CoreBusiness Assessment API
        api_response = call_corebusiness_api('payment_status', {
            'employer_number': employer_number,
            'include_history': params.get('include_history', False)
        })
        
        if api_response['success']:
            data = api_response['data']
            
            # Format response
            response = {
                'success': True,
                'data_type': 'payment_status',
                'employer_number': employer_number,
                'current_status': data.get('current_status'),
                'last_payment_date': data.get('last_payment_date'),
                'last_payment_amount': data.get('last_payment_amount'),
                'next_due_date': data.get('next_due_date'),
                'next_due_amount': data.get('next_due_amount'),
                'account_balance': data.get('account_balance'),
                'formatted_response': format_payment_status_response(data)
            }
            
            # Add escalation trigger if issues found
            if data.get('overdue_amount', 0) > 0:
                response['escalation_suggested'] = True
                response['escalation_reason'] = 'Overdue payments detected'
            
            return response
            
        else:
            return {
                'success': False,
                'message': 'Unable to retrieve payment status from CoreBusiness system',
                'escalate': True,
                'technical_error': api_response.get('error')
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': 'Payment status service temporarily unavailable',
            'escalate': True,
            'error': str(e)
        }

def handle_due_date_query(context, params):
    """Handle assessment due date queries"""
    
    auth_result = authenticate_user(context, required_role='Employer')
    if not auth_result['success']:
        return auth_result
    
    employer_number = context.get('employer_number')
    
    try:
        # Call CoreBusiness Assessment API
        api_response = call_corebusiness_api('due_dates', {
            'employer_number': employer_number,
            'period': params.get('period', 'current_quarter')
        })
        
        if api_response['success']:
            data = api_response['data']
            
            return {
                'success': True,
                'data_type': 'due_dates',
                'employer_number': employer_number,
                'upcoming_due_dates': data.get('upcoming_due_dates', []),
                'overdue_items': data.get('overdue_items', []),
                'next_critical_date': data.get('next_critical_date'),
                'formatted_response': format_due_dates_response(data)
            }
            
        else:
            # Fallback to static information
            return {
                'success': True,
                'fallback_to_static': True,
                'message': 'Showing general due date information. For specific dates, please contact support.',
                'static_content': get_static_due_dates_info()
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': 'Due date service temporarily unavailable',
            'escalate': True,
            'error': str(e)
        }

def handle_claim_status_query(context, params):
    """Handle beneficiary claim status queries"""
    
    auth_result = authenticate_user(context, required_role='Beneficiary')
    if not auth_result['success']:
        return auth_result
    
    claim_number = context.get('claim_number') or params.get('claim_number')
    beneficiary_number = context.get('beneficiary_number')
    
    if not claim_number and not beneficiary_number:
        return {
            'success': False,
            'message': 'Claim number or beneficiary number required',
            'escalate': True,
            'action': 'request_claim_details'
        }
    
    try:
        # Call Claims Management API
        api_response = call_claims_api('claim_status', {
            'claim_number': claim_number,
            'beneficiary_number': beneficiary_number
        })
        
        if api_response['success']:
            data = api_response['data']
            
            response = {
                'success': True,
                'data_type': 'claim_status',
                'claim_number': data.get('claim_number'),
                'status': data.get('status'),
                'stage': data.get('current_stage'),
                'last_update': data.get('last_update'),
                'estimated_completion': data.get('estimated_completion'),
                'required_actions': data.get('required_actions', []),
                'formatted_response': format_claim_status_response(data)
            }
            
            # Add escalation triggers
            if data.get('status') == 'Disputed' or data.get('days_pending', 0) > 45:
                response['escalation_suggested'] = True
                response['escalation_reason'] = 'Complex claim requiring attention'
            
            return response
            
        else:
            return {
                'success': False,
                'message': 'Unable to retrieve claim status',
                'escalate': True,
                'technical_error': api_response.get('error')
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': 'Claim status service temporarily unavailable',
            'escalate': True,
            'error': str(e)
        }

def authenticate_user(context, required_role=None):
    """Authenticate user and validate role"""
    
    # Check if user is authenticated
    user_id = context.get('user_id')
    session_token = context.get('session_token')
    
    if not user_id or not session_token:
        return {
            'success': False,
            'message': 'Authentication required for personalized information',
            'action': 'redirect_to_login',
            'login_url': get_login_url(required_role)
        }
    
    # Validate session
    session_valid = validate_session(user_id, session_token)
    if not session_valid:
        return {
            'success': False,
            'message': 'Session expired. Please log in again.',
            'action': 'redirect_to_login',
            'login_url': get_login_url(required_role)
        }
    
    # Check role if required
    if required_role:
        user_role = get_user_role(user_id)
        if user_role != required_role:
            return {
                'success': False,
                'message': f'Access denied. {required_role} role required.',
                'escalate': True
            }
    
    return {'success': True, 'user_id': user_id, 'role': get_user_role(user_id)}

def call_corebusiness_api(endpoint, params):
    """Call CoreBusiness Assessment API"""
    
    try:
        # Get API configuration
        api_config = get_api_config('corebusiness')
        if not api_config:
            return {'success': False, 'error': 'API configuration not found'}
        
        # Prepare request
        url = f"{api_config['base_url']}/{endpoint}"
        headers = {
            'Authorization': f"Bearer {api_config['api_key']}",
            'Content-Type': 'application/json',
            'X-Client-ID': 'wcfcb-assistant'
        }
        
        # Add caching check
        cache_key = f"corebusiness_{endpoint}_{hashlib.md5(str(params).encode()).hexdigest()}"
        cached_response = get_cached_response(cache_key)
        if cached_response:
            return cached_response
        
        # Make API call
        response = requests.post(url, json=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            # Cache successful response
            cache_response(cache_key, result, ttl=300)  # 5 minutes
            
            return {'success': True, 'data': result}
        else:
            return {
                'success': False,
                'error': f"API returned status {response.status_code}",
                'details': response.text
            }
            
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'API request timeout'}
    except requests.exceptions.ConnectionError:
        return {'success': False, 'error': 'Unable to connect to CoreBusiness API'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def call_claims_api(endpoint, params):
    """Call Claims Management API"""
    
    try:
        # Get API configuration
        api_config = get_api_config('claims')
        if not api_config:
            return {'success': False, 'error': 'Claims API configuration not found'}
        
        # Prepare request
        url = f"{api_config['base_url']}/{endpoint}"
        headers = {
            'Authorization': f"Bearer {api_config['api_key']}",
            'Content-Type': 'application/json',
            'X-Client-ID': 'wcfcb-assistant'
        }
        
        # Add caching check
        cache_key = f"claims_{endpoint}_{hashlib.md5(str(params).encode()).hexdigest()}"
        cached_response = get_cached_response(cache_key)
        if cached_response:
            return cached_response
        
        # Make API call
        response = requests.post(url, json=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            # Cache successful response
            cache_response(cache_key, result, ttl=180)  # 3 minutes
            
            return {'success': True, 'data': result}
        else:
            return {
                'success': False,
                'error': f"Claims API returned status {response.status_code}",
                'details': response.text
            }
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_api_config(service):
    """Get API configuration for external services"""

    try:
        # Get from Assistant CRM Settings
        settings = frappe.get_single("Assistant CRM Settings")

        # Use the new get_api_config method from the doctype
        config = settings.get_api_config(service)

        if config and config.get('base_url') and config.get('api_key'):
            return config

        return None

    except Exception as e:
        frappe.log_error(f"API config error: {str(e)}", "API Configuration")
        return None

def validate_session(user_id, session_token):
    """Validate user session token"""

    try:
        # Check session in database
        session = frappe.db.get_value("Chat History",
                                     {"user_id": user_id, "session_token": session_token},
                                     ["name", "creation", "modified"])

        if not session:
            return False

        # Check if session is still valid (24 hours)
        session_age = get_datetime() - get_datetime(session[2])
        if session_age.total_seconds() > 86400:  # 24 hours
            return False

        return True

    except Exception as e:
        frappe.log_error(f"Session validation error: {str(e)}", "Session Management")
        return False

def get_user_role(user_id):
    """Get user role from database - Uses ERPNext doctypes

    NOTE: Employer Profile, Employee Profile, and Beneficiary Profile have been removed.
    Now uses ERPNext Customer and Employee doctypes.
    """
    try:
        # Check if user is linked to an Employee
        employee = frappe.db.exists("Employee", {"user_id": user_id})
        if employee:
            return "Employee"

        # Check if user is linked to a Customer (Employer)
        customer = frappe.db.get_value("Customer", {"custom_user_id": user_id}, "name")
        if customer:
            return "Employer"

        return "General"

    except Exception as e:
        frappe.log_error(f"User role error: {str(e)}", "User Management")
        return "General"

def get_login_url(required_role):
    """Get appropriate login URL based on role"""
    from assistant_crm.utils import get_public_url
    base_url = get_public_url()

    if required_role == "Employer":
        return f"{base_url}/employers/login"
    elif required_role == "Beneficiary":
        return f"{base_url}/beneficiaries/login"
    else:
        return f"{base_url}/login"

def get_cached_response(cache_key):
    """Get cached API response"""

    try:
        cached = frappe.cache().get_value(cache_key)
        if cached:
            return json.loads(cached)
        return None

    except Exception as e:
        frappe.log_error(f"Cache retrieval error: {str(e)}", "Cache Management")
        return None

def cache_response(cache_key, response, ttl=300):
    """Cache API response"""

    try:
        frappe.cache().set_value(cache_key, json.dumps(response), expires_in_sec=ttl)

    except Exception as e:
        frappe.log_error(f"Cache storage error: {str(e)}", "Cache Management")

def format_payment_status_response(data):
    """Format payment status data for user-friendly response"""

    try:
        current_status = data.get('current_status', 'Unknown')
        last_payment = data.get('last_payment_date')
        next_due = data.get('next_due_date')
        balance = flt(data.get('account_balance', 0))
        overdue = flt(data.get('overdue_amount', 0))

        response = f"**Payment Status Summary**\n\n"
        response += f"• **Current Status:** {current_status}\n"

        if last_payment:
            response += f"• **Last Payment:** {last_payment} (K{flt(data.get('last_payment_amount', 0)):,.2f})\n"

        if next_due:
            response += f"• **Next Due Date:** {next_due} (K{flt(data.get('next_due_amount', 0)):,.2f})\n"

        if balance != 0:
            if balance > 0:
                response += f"• **Account Credit:** K{balance:,.2f}\n"
            else:
                response += f"• **Outstanding Balance:** K{abs(balance):,.2f}\n"

        if overdue > 0:
            response += f"• **⚠️ Overdue Amount:** K{overdue:,.2f}\n"
            response += f"• **Action Required:** Please make payment to avoid penalties\n"

        # Add quick actions
        response += f"\n**Quick Actions:**\n"
        response += f"• Make payment online\n"
        response += f"• View detailed statement\n"
        response += f"• Contact support for assistance\n"

        return response

    except Exception as e:
        return f"Payment status information available. Please contact support for details. Error: {str(e)}"

def format_due_dates_response(data):
    """Format due dates data for user-friendly response"""

    try:
        upcoming = data.get('upcoming_due_dates', [])
        overdue = data.get('overdue_items', [])
        next_critical = data.get('next_critical_date')

        response = f"**Assessment Due Dates**\n\n"

        if next_critical:
            response += f"🔴 **Next Critical Date:** {next_critical}\n\n"

        if upcoming:
            response += f"**Upcoming Due Dates:**\n"
            for item in upcoming[:5]:  # Show max 5 items
                response += f"• {item.get('description', 'Assessment')}: {item.get('due_date')} (K{flt(item.get('amount', 0)):,.2f})\n"

        if overdue:
            response += f"\n**⚠️ Overdue Items:**\n"
            for item in overdue[:3]:  # Show max 3 overdue items
                response += f"• {item.get('description', 'Assessment')}: {item.get('due_date')} (K{flt(item.get('amount', 0)):,.2f})\n"

            if len(overdue) > 3:
                response += f"• ... and {len(overdue) - 3} more overdue items\n"

        response += f"\n**Quick Actions:**\n"
        response += f"• Make payment now\n"
        response += f"• Set up payment reminders\n"
        response += f"• Download payment schedule\n"

        return response

    except Exception as e:
        return f"Due date information available. Please contact support for details. Error: {str(e)}"

def format_claim_status_response(data):
    """Format claim status data for user-friendly response"""

    try:
        claim_number = data.get('claim_number', 'N/A')
        status = data.get('status', 'Unknown')
        stage = data.get('current_stage', 'Unknown')
        last_update = data.get('last_update')
        estimated_completion = data.get('estimated_completion')
        required_actions = data.get('required_actions', [])

        response = f"**Claim Status: {claim_number}**\n\n"
        response += f"• **Status:** {status}\n"
        response += f"• **Current Stage:** {stage}\n"

        if last_update:
            response += f"• **Last Update:** {last_update}\n"

        if estimated_completion:
            response += f"• **Estimated Completion:** {estimated_completion}\n"

        if required_actions:
            response += f"\n**Required Actions:**\n"
            for action in required_actions:
                response += f"• {action}\n"

        # Add status-specific information
        if status.lower() == 'approved':
            response += f"\n✅ **Good News:** Your claim has been approved!\n"
        elif status.lower() == 'pending':
            response += f"\n⏳ **Status:** Your claim is being processed.\n"
        elif status.lower() == 'disputed':
            response += f"\n⚠️ **Attention:** Your claim requires additional review.\n"

        response += f"\n**Quick Actions:**\n"
        response += f"• Upload additional documents\n"
        response += f"• Contact claims officer\n"
        response += f"• View claim history\n"

        return response

    except Exception as e:
        return f"Claim status information available. Please contact support for details. Error: {str(e)}"

def get_static_due_dates_info():
    """Get static due dates information as fallback"""

    return """**General Assessment Due Dates**

**Monthly Contributions:**
• Due: 15th of following month
• Grace Period: 5 days without penalty

**Quarterly Returns:**
• Q1 (Jan-Mar): Due April 30th
• Q2 (Apr-Jun): Due July 31st
• Q3 (Jul-Sep): Due October 31st
• Q4 (Oct-Dec): Due January 31st

**Annual Returns:**
• Due: March 31st each year

For your specific due dates and amounts, please log into your employer portal or contact support."""
