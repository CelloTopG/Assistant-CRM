# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import re
import frappe


class SecurityService:
	"""Service class for handling security, permissions, and data sanitization"""
	
	def __init__(self):
		self.user = frappe.session.user
		self.user_roles = frappe.get_roles(self.user)
	
	def validate_user_access(self):
		"""Validate if user has access to chat functionality"""
		try:
			# Allow guest users with limited functionality
			if self.user == "Guest":
				return {
					"valid": True,
					"guest_user": True,
					"limited_access": True,
					"message": "Guest access enabled with limited functionality."
				}
			
			# Check if user is active
			user_doc = frappe.get_doc("User", self.user)
			if user_doc.enabled == 0:
				return {
					"valid": False,
					"error": "Your account is disabled. Please contact your administrator."
				}
			
			# Check for basic roles (all users should have at least one role)
			if not self.user_roles:
				return {
					"valid": False,
					"error": "No roles assigned. Please contact your administrator."
				}
			
			return {"valid": True}
			
		except Exception as e:
			frappe.log_error(f"Error validating user access: {str(e)}", "Security Service")
			return {
				"valid": False,
				"error": "Unable to validate user access. Please try again."
			}
	
	def sanitize_input(self, message):
		"""Sanitize user input to prevent injection attacks"""
		try:
			if not message:
				return ""
			
			# Remove potentially dangerous characters and patterns
			message = str(message).strip()
			
			# Remove HTML tags
			message = re.sub(r'<[^>]+>', '', message)
			
			# Remove script tags and javascript
			message = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', message, flags=re.IGNORECASE)
			message = re.sub(r'javascript:', '', message, flags=re.IGNORECASE)
			
			# Remove SQL injection patterns
			sql_patterns = [
				r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
				r'(--|#|\/\*|\*\/)',
				r'(\bOR\b.*=.*\bOR\b)',
				r'(\bAND\b.*=.*\bAND\b)'
			]
			
			for pattern in sql_patterns:
				message = re.sub(pattern, '', message, flags=re.IGNORECASE)
			
			# Limit message length
			if len(message) > 2000:
				message = message[:2000] + "..."
			
			return message
			
		except Exception as e:
			frappe.log_error(f"Error sanitizing input: {str(e)}", "Security Service")
			return ""
	
	def validate_doctype_access(self, doctype, permission_type="read"):
		"""Validate if user has permission to access a doctype"""
		try:
			return frappe.has_permission(doctype, permission_type)
		except Exception:
			return False
	
	def validate_document_access(self, doctype, name, permission_type="read"):
		"""Validate if user has permission to access a specific document"""
		try:
			return frappe.has_permission(doctype, permission_type, name)
		except Exception:
			return False
	
	def filter_sensitive_data(self, data, doctype=None):
		"""Filter out sensitive data based on user permissions and doctype"""
		try:
			if not data:
				return data
			
			# Define sensitive fields that should be filtered
			sensitive_fields = {
				"User": ["password", "api_key", "api_secret"],
				"Employee": ["salary", "bank_account", "personal_email"],
				"Customer": ["credit_limit", "payment_terms"],
				"Supplier": ["payment_terms", "tax_id"],
				"Company": ["tax_id", "registration_details"]
			}
			
			# If it's a list of documents
			if isinstance(data, list):
				return [self._filter_document_fields(doc, doctype, sensitive_fields) for doc in data]
			
			# If it's a single document
			elif isinstance(data, dict):
				return self._filter_document_fields(data, doctype, sensitive_fields)
			
			return data
			
		except Exception as e:
			frappe.log_error(f"Error filtering sensitive data: {str(e)}", "Security Service")
			return data
	
	def _filter_document_fields(self, doc, doctype, sensitive_fields):
		"""Filter sensitive fields from a single document"""
		if not isinstance(doc, dict) or not doctype:
			return doc
		
		filtered_doc = doc.copy()
		
		# Remove sensitive fields for this doctype
		if doctype in sensitive_fields:
			for field in sensitive_fields[doctype]:
				if field in filtered_doc:
					filtered_doc[field] = "[FILTERED]"
		
		# Always filter these fields regardless of doctype
		always_filter = ["password", "api_key", "api_secret", "access_token"]
		for field in always_filter:
			if field in filtered_doc:
				filtered_doc[field] = "[FILTERED]"
		
		return filtered_doc
	
	def validate_query_safety(self, query):
		"""Validate if a query is safe to process"""
		try:
			query_lower = query.lower()
			
			# Check for potentially dangerous queries
			dangerous_patterns = [
				"delete",
				"drop table",
				"truncate",
				"alter table",
				"create table",
				"insert into",
				"update set",
				"grant",
				"revoke",
				"exec",
				"execute"
			]
			
			for pattern in dangerous_patterns:
				if pattern in query_lower:
					return {
						"safe": False,
						"reason": f"Query contains potentially dangerous operation: {pattern}"
					}
			
			# Check for excessive data requests
			if len(query) > 1000:
				return {
					"safe": False,
					"reason": "Query is too long"
				}
			
			return {"safe": True}
			
		except Exception as e:
			frappe.log_error(f"Error validating query safety: {str(e)}", "Security Service")
			return {
				"safe": False,
				"reason": "Unable to validate query safety"
			}
	
	def log_chat_activity(self, message, response, session_id, status="success"):
		"""Log chat activity for security monitoring"""
		try:
			# Create a security log entry
			frappe.get_doc({
				"doctype": "Activity Log",
				"subject": f"Chat Assistant - {status.title()}",
				"content": f"User: {self.user}\nSession: {session_id}\nMessage Length: {len(message)}\nResponse Length: {len(response) if response else 0}",
				"communication_date": frappe.utils.now(),
				"reference_doctype": "Chat History",
				"status": status.title()
			}).insert(ignore_permissions=True)
			
		except Exception as e:
			frappe.log_error(f"Error logging chat activity: {str(e)}", "Security Service")
	
	def check_rate_limit(self, session_id, limit_per_minute=10):
		"""Check if user is within rate limits"""
		try:
			# Get recent chat history for this session
			recent_chats = frappe.db.count("Chat History", {
				"user": self.user,
				"session_id": session_id,
				"timestamp": [">=", frappe.utils.add_to_date(frappe.utils.now(), minutes=-1)]
			})
			
			if recent_chats >= limit_per_minute:
				return {
					"allowed": False,
					"reason": f"Rate limit exceeded. Maximum {limit_per_minute} messages per minute."
				}
			
			return {"allowed": True}
			
		except Exception as e:
			frappe.log_error(f"Error checking rate limit: {str(e)}", "Security Service")
			return {"allowed": True}  # Allow on error to avoid blocking users
	
	def validate_session_integrity(self, session_id):
		"""Validate session integrity and ownership"""
		try:
			if not session_id:
				return {"valid": False, "reason": "No session ID provided"}
			
			# Check if session belongs to current user
			session_owner = frappe.db.get_value("Chat History", 
				{"session_id": session_id}, "user")
			
			if session_owner and session_owner != self.user:
				return {
					"valid": False, 
					"reason": "Session does not belong to current user"
				}
			
			return {"valid": True}
			
		except Exception as e:
			frappe.log_error(f"Error validating session: {str(e)}", "Security Service")
			return {"valid": False, "reason": "Unable to validate session"}
	
	def get_user_permissions_summary(self):
		"""Get summary of user permissions for context"""
		try:
			permissions = {
				"roles": self.user_roles,
				"can_access": {},
				"restrictions": []
			}
			
			# Check access to common doctypes
			common_doctypes = [
				"Material Request", "Purchase Order", "Purchase Receipt",
				"Leave Application", "Employee", "User", "Company"
			]
			
			for doctype in common_doctypes:
				permissions["can_access"][doctype] = {
					"read": self.validate_doctype_access(doctype, "read"),
					"write": self.validate_doctype_access(doctype, "write"),
					"create": self.validate_doctype_access(doctype, "create"),
					"delete": self.validate_doctype_access(doctype, "delete")
				}
			
			# Add any specific restrictions
			if "System Manager" not in self.user_roles:
				permissions["restrictions"].append("Limited system access")
			
			return permissions
			
		except Exception as e:
			frappe.log_error(f"Error getting permissions summary: {str(e)}", "Security Service")
			return {"roles": self.user_roles, "can_access": {}, "restrictions": []}
