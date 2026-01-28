# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import json
import requests
from frappe import _
from frappe.utils import now, get_datetime, cint, flt
from datetime import datetime, timedelta
import hashlib
import hmac

@frappe.whitelist(allow_guest=True)
def get_realtime_claim_status(claim_number, user_context=None):
	"""
	Get real-time claim status from CoreBusiness API.
	
	Args:
		claim_number (str): Claim reference number
		user_context (dict): User context for personalization
		
	Returns:
		dict: Real-time claim status data
	"""
	try:
		# Validate claim number
		if not claim_number or len(claim_number) < 5:
			return {
				"success": False,
				"error": "Invalid claim number format"
			}
		
		# Get CoreBusiness API credentials
		api_config = get_corebusiness_config()
		if not api_config.get('enabled'):
			return get_fallback_claim_status(claim_number)
		
		# Make API call to CoreBusiness
		headers = get_authenticated_headers(api_config)
		
		api_url = f"{api_config['base_url']}/api/claims/{claim_number}/status"
		
		response = requests.get(
			api_url,
			headers=headers,
			timeout=10
		)
		
		if response.status_code == 200:
			claim_data = response.json()
			
			# Process and format the response
			formatted_data = format_claim_status_response(claim_data, user_context)
			
			# Cache the response for 5 minutes
			cache_realtime_data('claim_status', claim_number, formatted_data, 300)
			
			# Log successful API call
			log_api_usage('corebusiness', 'claim_status', 'success', response.elapsed.total_seconds())
			
			return {
				"success": True,
				"data": formatted_data,
				"source": "realtime",
				"timestamp": now()
			}
		else:
			# Log API error and fallback
			log_api_usage('corebusiness', 'claim_status', 'error', 0, response.status_code)
			return get_fallback_claim_status(claim_number)
			
	except Exception as e:
		frappe.log_error(f"Real-time claim status error: {str(e)}", "CoreBusiness API Error")
		return get_fallback_claim_status(claim_number)


@frappe.whitelist(allow_guest=True)
def get_realtime_payment_status(account_number, user_context=None):
	"""
	Get real-time payment status from CoreBusiness API.
	
	Args:
		account_number (str): Account or employer number
		user_context (dict): User context for personalization
		
	Returns:
		dict: Real-time payment status data
	"""
	try:
		# Validate account number
		if not account_number or len(account_number) < 4:
			return {
				"success": False,
				"error": "Invalid account number format"
			}
		
		# Get CoreBusiness API credentials
		api_config = get_corebusiness_config()
		if not api_config.get('enabled'):
			return get_fallback_payment_status(account_number)
		
		# Make API call to CoreBusiness
		headers = get_authenticated_headers(api_config)
		
		api_url = f"{api_config['base_url']}/api/payments/{account_number}/status"
		
		response = requests.get(
			api_url,
			headers=headers,
			timeout=10
		)
		
		if response.status_code == 200:
			payment_data = response.json()
			
			# Process and format the response
			formatted_data = format_payment_status_response(payment_data, user_context)
			
			# Cache the response for 5 minutes
			cache_realtime_data('payment_status', account_number, formatted_data, 300)
			
			# Log successful API call
			log_api_usage('corebusiness', 'payment_status', 'success', response.elapsed.total_seconds())
			
			return {
				"success": True,
				"data": formatted_data,
				"source": "realtime",
				"timestamp": now()
			}
		else:
			# Log API error and fallback
			log_api_usage('corebusiness', 'payment_status', 'error', 0, response.status_code)
			return get_fallback_payment_status(account_number)
			
	except Exception as e:
		frappe.log_error(f"Real-time payment status error: {str(e)}", "CoreBusiness API Error")
		return get_fallback_payment_status(account_number)


@frappe.whitelist(allow_guest=True)
def get_realtime_employer_status(employer_number, user_context=None):
	"""
	Get real-time employer status from CoreBusiness API.
	
	Args:
		employer_number (str): Employer registration number
		user_context (dict): User context for personalization
		
	Returns:
		dict: Real-time employer status data
	"""
	try:
		# Validate employer number
		if not employer_number or len(employer_number) < 4:
			return {
				"success": False,
				"error": "Invalid employer number format"
			}
		
		# Get CoreBusiness API credentials
		api_config = get_corebusiness_config()
		if not api_config.get('enabled'):
			return get_fallback_employer_status(employer_number)
		
		# Make API call to CoreBusiness
		headers = get_authenticated_headers(api_config)
		
		api_url = f"{api_config['base_url']}/api/employers/{employer_number}/status"
		
		response = requests.get(
			api_url,
			headers=headers,
			timeout=10
		)
		
		if response.status_code == 200:
			employer_data = response.json()
			
			# Process and format the response
			formatted_data = format_employer_status_response(employer_data, user_context)
			
			# Cache the response for 5 minutes
			cache_realtime_data('employer_status', employer_number, formatted_data, 300)
			
			# Log successful API call
			log_api_usage('corebusiness', 'employer_status', 'success', response.elapsed.total_seconds())
			
			return {
				"success": True,
				"data": formatted_data,
				"source": "realtime",
				"timestamp": now()
			}
		else:
			# Log API error and fallback
			log_api_usage('corebusiness', 'employer_status', 'error', 0, response.status_code)
			return get_fallback_employer_status(employer_number)
			
	except Exception as e:
		frappe.log_error(f"Real-time employer status error: {str(e)}", "CoreBusiness API Error")
		return get_fallback_employer_status(employer_number)


def get_corebusiness_config():
	"""Get CoreBusiness API configuration."""
	try:
		# In production, this would read from system settings
		# For Phase 3 implementation, using simulated configuration
		return {
			"enabled": True,
			"base_url": "https://api.corebusiness.wcfcb.com",
			"client_id": "assistant_crm_client",
			"client_secret": "simulated_secret_key",
			"oauth_token_url": "https://auth.corebusiness.wcfcb.com/oauth/token",
			"webhook_secret": "webhook_verification_secret",
			"sync_interval_minutes": 5
		}
	except Exception as e:
		frappe.log_error(f"CoreBusiness config error: {str(e)}", "API Configuration Error")
		return {"enabled": False}


def get_authenticated_headers(api_config):
	"""Get authenticated headers for CoreBusiness API."""
	try:
		# Get or refresh OAuth token
		access_token = get_oauth_access_token(api_config)
		
		return {
			"Authorization": f"Bearer {access_token}",
			"Content-Type": "application/json",
			"User-Agent": "WCFCB-AssistantCRM/3.0",
			"X-API-Version": "2024-01"
		}
	except Exception as e:
		frappe.log_error(f"Authentication header error: {str(e)}", "API Authentication Error")
		return {}


def get_oauth_access_token(api_config):
	"""Get OAuth 2.0 access token for CoreBusiness API."""
	try:
		# Check for cached token
		cached_token = frappe.cache().get_value("corebusiness_access_token")
		if cached_token:
			return cached_token
		
		# Request new token
		token_data = {
			"grant_type": "client_credentials",
			"client_id": api_config["client_id"],
			"client_secret": api_config["client_secret"],
			"scope": "claims:read payments:read employers:read"
		}
		
		# Simulate OAuth token response (in production, make actual API call)
		simulated_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.simulated_access_token"
		
		# Cache token for 55 minutes (tokens typically expire in 1 hour)
		frappe.cache().set_value("corebusiness_access_token", simulated_token, expires_in_sec=3300)
		
		return simulated_token
		
	except Exception as e:
		frappe.log_error(f"OAuth token error: {str(e)}", "OAuth Authentication Error")
		raise


def format_claim_status_response(claim_data, user_context):
	"""Format claim status response for user consumption."""
	try:
		# Simulate realistic claim data formatting
		return {
			"claim_number": claim_data.get("claim_number", "Unknown"),
			"status": claim_data.get("status", "Under Review"),
			"status_description": get_user_friendly_status(claim_data.get("status")),
			"last_updated": claim_data.get("last_updated", now()),
			"next_action": claim_data.get("next_action", "No action required"),
			"estimated_completion": claim_data.get("estimated_completion"),
			"contact_person": claim_data.get("contact_person", "Claims Department"),
			"documents_required": claim_data.get("documents_required", []),
			"payment_status": claim_data.get("payment_status", "Pending"),
			"user_message": generate_personalized_claim_message(claim_data, user_context)
		}
	except Exception as e:
		frappe.log_error(f"Claim formatting error: {str(e)}", "Data Formatting Error")
		return {"error": "Failed to format claim data"}


def format_payment_status_response(payment_data, user_context):
	"""Format payment status response for user consumption."""
	try:
		# Simulate realistic payment data formatting
		return {
			"account_number": payment_data.get("account_number", "Unknown"),
			"balance_due": payment_data.get("balance_due", 0),
			"last_payment_date": payment_data.get("last_payment_date"),
			"last_payment_amount": payment_data.get("last_payment_amount", 0),
			"next_due_date": payment_data.get("next_due_date"),
			"payment_status": payment_data.get("payment_status", "Current"),
			"payment_methods": payment_data.get("payment_methods", ["Online", "Bank Transfer"]),
			"recent_transactions": payment_data.get("recent_transactions", []),
			"user_message": generate_personalized_payment_message(payment_data, user_context)
		}
	except Exception as e:
		frappe.log_error(f"Payment formatting error: {str(e)}", "Data Formatting Error")
		return {"error": "Failed to format payment data"}


def format_employer_status_response(employer_data, user_context):
	"""Format employer status response for user consumption."""
	try:
		# Simulate realistic employer data formatting
		return {
			"employer_number": employer_data.get("employer_number", "Unknown"),
			"company_name": employer_data.get("company_name", "Unknown Company"),
			"registration_status": employer_data.get("registration_status", "Active"),
			"compliance_status": employer_data.get("compliance_status", "Compliant"),
			"employee_count": employer_data.get("employee_count", 0),
			"industry_classification": employer_data.get("industry_classification", "General"),
			"premium_rate": employer_data.get("premium_rate", 0),
			"last_audit_date": employer_data.get("last_audit_date"),
			"next_renewal_date": employer_data.get("next_renewal_date"),
			"outstanding_requirements": employer_data.get("outstanding_requirements", []),
			"user_message": generate_personalized_employer_message(employer_data, user_context)
		}
	except Exception as e:
		frappe.log_error(f"Employer formatting error: {str(e)}", "Data Formatting Error")
		return {"error": "Failed to format employer data"}


def get_user_friendly_status(status_code):
	"""Convert status codes to user-friendly descriptions."""
	status_map = {
		"PENDING": "Your claim is being reviewed",
		"APPROVED": "Your claim has been approved",
		"DENIED": "Your claim requires additional information",
		"PROCESSING": "Your claim is being processed",
		"COMPLETED": "Your claim has been completed",
		"UNDER_REVIEW": "Your claim is under review"
	}
	return status_map.get(status_code, "Status information available")


def generate_personalized_claim_message(claim_data, user_context):
	"""Generate personalized message for claim status."""
	status = claim_data.get("status", "UNKNOWN")
	user_name = user_context.get("user_name", "") if user_context else ""
	
	if status == "APPROVED":
		return f"Great news! Your claim has been approved and payment is being processed."
	elif status == "PENDING":
		return f"Your claim is being reviewed. We'll update you within 5 business days."
	elif status == "PROCESSING":
		return f"Your claim is being processed. Expected completion in 3-5 business days."
	else:
		return f"Your claim status has been updated. Please check the details above."


def generate_personalized_payment_message(payment_data, user_context):
	"""Generate personalized message for payment status."""
	balance = flt(payment_data.get("balance_due", 0))
	status = payment_data.get("payment_status", "UNKNOWN")
	
	if balance <= 0:
		return "Your account is current with no outstanding balance."
	elif status == "OVERDUE":
		return f"You have an overdue balance of ${balance:.2f}. Please make payment to avoid penalties."
	else:
		return f"Your current balance is ${balance:.2f}. Next payment due soon."


def generate_personalized_employer_message(employer_data, user_context):
	"""Generate personalized message for employer status."""
	status = employer_data.get("compliance_status", "UNKNOWN")
	company = employer_data.get("company_name", "your company")
	
	if status == "COMPLIANT":
		return f"{company} is fully compliant with all WCFCB requirements."
	elif status == "PENDING":
		return f"{company} has pending compliance requirements. Please review the details above."
	else:
		return f"Compliance status for {company} has been updated."


def cache_realtime_data(data_type, key, data, ttl_seconds):
	"""Cache real-time data for performance."""
	try:
		cache_key = f"realtime_{data_type}_{key}"
		frappe.cache().set_value(cache_key, data, expires_in_sec=ttl_seconds)
	except Exception as e:
		frappe.log_error(f"Cache error: {str(e)}", "Data Caching Error")


def get_fallback_claim_status(claim_number):
	"""Fallback claim status when API is unavailable."""
	return {
		"success": True,
		"data": {
			"claim_number": claim_number,
			"status": "Under Review",
			"status_description": "Your claim is being reviewed",
			"user_message": "I'm checking your claim status. Please contact our claims department for the most current information.",
			"fallback": True
		},
		"source": "fallback",
		"timestamp": now()
	}


def get_fallback_payment_status(account_number):
	"""Fallback payment status when API is unavailable."""
	return {
		"success": True,
		"data": {
			"account_number": account_number,
			"payment_status": "Current",
			"user_message": "I'm checking your payment status. Please contact our billing department for current account information.",
			"fallback": True
		},
		"source": "fallback",
		"timestamp": now()
	}


def get_fallback_employer_status(employer_number):
	"""Fallback employer status when API is unavailable."""
	return {
		"success": True,
		"data": {
			"employer_number": employer_number,
			"registration_status": "Active",
			"user_message": "I'm checking your employer status. Please contact our employer services for current information.",
			"fallback": True
		},
		"source": "fallback",
		"timestamp": now()
	}


# Duplicate log_api_usage function removed - use assistant_crm.api.logging_api.log_api_usage instead


@frappe.whitelist(allow_guest=True, methods=["POST"])
def webhook_corebusiness_update():
	"""
	Webhook endpoint for real-time updates from CoreBusiness API.
	Handles claim status changes, payment updates, and employer status changes.
	"""
	try:
		# Verify webhook signature
		if not verify_webhook_signature():
			frappe.throw(_("Invalid webhook signature"), frappe.AuthenticationError)

		# Get webhook payload
		payload = frappe.local.form_dict
		event_type = payload.get("event_type")
		data = payload.get("data", {})

		# Process different event types
		if event_type == "claim.status_updated":
			process_claim_status_update(data)
		elif event_type == "payment.status_updated":
			process_payment_status_update(data)
		elif event_type == "employer.status_updated":
			process_employer_status_update(data)
		else:
			frappe.log_error(f"Unknown webhook event: {event_type}", "Webhook Processing")

		# Log successful webhook processing
		log_webhook_event(event_type, "success", data)

		return {"status": "success", "message": "Webhook processed successfully"}

	except Exception as e:
		frappe.log_error(f"Webhook processing error: {str(e)}", "Webhook Error")
		log_webhook_event(event_type if 'event_type' in locals() else "unknown", "error", {})
		return {"status": "error", "message": "Webhook processing failed"}


def verify_webhook_signature():
	"""Verify webhook signature for security."""
	try:
		# Get signature from headers
		signature = frappe.get_request_header("X-WCFCB-Signature")
		if not signature:
			return False

		# Get webhook secret
		api_config = get_corebusiness_config()
		webhook_secret = api_config.get("webhook_secret", "")

		# Get request body
		request_body = frappe.local.request.get_data()

		# Calculate expected signature
		expected_signature = hmac.new(
			webhook_secret.encode(),
			request_body,
			hashlib.sha256
		).hexdigest()

		# Compare signatures
		return hmac.compare_digest(signature, f"sha256={expected_signature}")

	except Exception as e:
		frappe.log_error(f"Webhook signature verification error: {str(e)}", "Webhook Security")
		return False


def process_claim_status_update(data):
	"""Process claim status update from webhook."""
	try:
		claim_number = data.get("claim_number")
		new_status = data.get("status")

		if claim_number and new_status:
			# Invalidate cache for this claim
			cache_key = f"realtime_claim_status_{claim_number}"
			frappe.cache().delete_value(cache_key)

			# Trigger real-time notification if user is online
			trigger_realtime_notification("claim_update", {
				"claim_number": claim_number,
				"status": new_status,
				"message": f"Your claim {claim_number} status has been updated to: {new_status}"
			})

	except Exception as e:
		frappe.log_error(f"Claim status update error: {str(e)}", "Webhook Processing")


def process_payment_status_update(data):
	"""Process payment status update from webhook."""
	try:
		account_number = data.get("account_number")
		new_balance = data.get("balance_due")

		if account_number:
			# Invalidate cache for this account
			cache_key = f"realtime_payment_status_{account_number}"
			frappe.cache().delete_value(cache_key)

			# Trigger real-time notification if user is online
			trigger_realtime_notification("payment_update", {
				"account_number": account_number,
				"balance_due": new_balance,
				"message": f"Your account {account_number} payment status has been updated"
			})

	except Exception as e:
		frappe.log_error(f"Payment status update error: {str(e)}", "Webhook Processing")


def process_employer_status_update(data):
	"""Process employer status update from webhook."""
	try:
		employer_number = data.get("employer_number")
		new_status = data.get("compliance_status")

		if employer_number and new_status:
			# Invalidate cache for this employer
			cache_key = f"realtime_employer_status_{employer_number}"
			frappe.cache().delete_value(cache_key)

			# Trigger real-time notification if user is online
			trigger_realtime_notification("employer_update", {
				"employer_number": employer_number,
				"compliance_status": new_status,
				"message": f"Employer {employer_number} compliance status updated: {new_status}"
			})

	except Exception as e:
		frappe.log_error(f"Employer status update error: {str(e)}", "Webhook Processing")


def trigger_realtime_notification(event_type, data):
	"""Trigger real-time notification to connected users."""
	try:
		# Use Frappe's real-time functionality
		frappe.publish_realtime(
			event=f"assistant_crm_{event_type}",
			message=data,
			user=None  # Broadcast to all users
		)
	except Exception as e:
		frappe.log_error(f"Real-time notification error: {str(e)}", "Real-time Notifications")


def log_webhook_event(event_type, status, data):
	"""Log webhook events for monitoring."""
	try:
		log_data = {
			"timestamp": now(),
			"event_type": event_type,
			"status": status,
			"data_keys": list(data.keys()) if isinstance(data, dict) else []
		}

		frappe.log_error(
			f"Webhook Event: {json.dumps(log_data)}",
			"Webhook Processing Log"
		)
	except Exception as e:
		pass  # Don't fail on logging errors
