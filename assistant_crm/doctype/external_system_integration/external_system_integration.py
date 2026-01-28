# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
import json
from datetime import datetime

class ExternalSystemIntegration(Document):
	def validate(self):
		"""Validate external system integration configuration"""
		self.validate_api_endpoint()
		self.validate_authentication()
		self.validate_data_mappings()
	
	def validate_api_endpoint(self):
		"""Validate API endpoint URL"""
		if self.api_endpoint:
			if not self.api_endpoint.startswith(('http://', 'https://')):
				frappe.throw("API endpoint must start with http:// or https://")
	
	def validate_authentication(self):
		"""Validate authentication configuration"""
		if self.authentication_type == 'API Key' and not self.api_key:
			frappe.throw("API Key is required for API Key authentication")
		elif self.authentication_type == 'OAuth':
			if not self.client_id or not self.client_secret:
				frappe.throw("Client ID and Client Secret are required for OAuth authentication")
	
	def validate_data_mappings(self):
		"""Validate data field mappings"""
		if not self.data_mappings:
			frappe.msgprint("No data mappings configured. Please add field mappings for data synchronization.")
		
		# Check for duplicate mappings
		external_fields = [mapping.external_field for mapping in self.data_mappings]
		if len(external_fields) != len(set(external_fields)):
			frappe.throw("Duplicate external field mappings found")
	
	def test_connection(self):
		"""Test connection to external system"""
		try:
			headers = self.get_auth_headers()
			
			# Simple GET request to test connectivity
			test_url = f"{self.api_endpoint}/health" if self.api_endpoint.endswith('/') else f"{self.api_endpoint}/health"
			
			response = requests.get(test_url, headers=headers, timeout=30)
			
			if response.status_code == 200:
				return {
					'success': True,
					'message': 'Connection successful',
					'status_code': response.status_code
				}
			else:
				return {
					'success': False,
					'message': f'Connection failed with status code: {response.status_code}',
					'status_code': response.status_code
				}
		
		except requests.exceptions.RequestException as e:
			return {
				'success': False,
				'message': f'Connection error: {str(e)}'
			}
	
	def get_auth_headers(self):
		"""Get authentication headers for API requests"""
		headers = {'Content-Type': 'application/json'}
		
		if self.authentication_type == 'API Key':
			headers['Authorization'] = f'Bearer {self.api_key}'
		elif self.authentication_type == 'OAuth' and self.access_token:
			headers['Authorization'] = f'Bearer {self.access_token}'
		elif self.authentication_type == 'Basic Auth':
			# Implement basic auth if needed
			pass
		
		return headers
	
	def sync_data(self, data_type='all'):
		"""Sync data from external system"""
		try:
			self.sync_status = 'Pending'
			self.save()
			
			if self.system_type == 'CoreBusiness':
				from assistant_crm.services.corebusiness_integration_service import CoreBusinessIntegrationService
				service = CoreBusinessIntegrationService()
				
				if data_type == 'employers' or data_type == 'all':
					result = service.sync_employer_data()
					if not result.get('success'):
						raise Exception(f"Employer sync failed: {result.get('error')}")
				
				if data_type == 'beneficiaries' or data_type == 'all':
					result = service.sync_beneficiary_data()
					if not result.get('success'):
						raise Exception(f"Beneficiary sync failed: {result.get('error')}")
			
			# Update sync status
			self.last_sync_time = frappe.utils.now()
			self.sync_status = 'Success'
			self.last_error_message = ''
			self.save()
			
			return {
				'success': True,
				'message': 'Data synchronization completed successfully'
			}
		
		except Exception as e:
			self.sync_status = 'Failed'
			self.last_error_message = str(e)
			self.save()
			
			frappe.log_error(f"Data sync failed for {self.system_name}: {str(e)}")
			return {
				'success': False,
				'error': str(e)
			}
	
	def refresh_oauth_token(self):
		"""Refresh OAuth access token"""
		if self.authentication_type != 'OAuth' or not self.refresh_token:
			return False
		
		try:
			token_url = f"{self.api_endpoint}/oauth/token"
			
			data = {
				'grant_type': 'refresh_token',
				'refresh_token': self.refresh_token,
				'client_id': self.client_id,
				'client_secret': self.client_secret
			}
			
			response = requests.post(token_url, data=data, timeout=30)
			
			if response.status_code == 200:
				token_data = response.json()
				self.access_token = token_data.get('access_token')
				if token_data.get('refresh_token'):
					self.refresh_token = token_data.get('refresh_token')
				self.save()
				return True
			else:
				frappe.log_error(f"OAuth token refresh failed: {response.text}")
				return False
		
		except Exception as e:
			frappe.log_error(f"OAuth token refresh error: {str(e)}")
			return False

@frappe.whitelist(allow_guest=False)
def test_integration_connection(integration_name):
	"""Test connection to external system"""
	integration = frappe.get_doc('External System Integration', integration_name)
	return integration.test_connection()

@frappe.whitelist(allow_guest=False)
def sync_integration_data(integration_name, data_type='all'):
	"""Sync data from external system"""
	integration = frappe.get_doc('External System Integration', integration_name)
	return integration.sync_data(data_type)

@frappe.whitelist(allow_guest=False)
def get_integration_status():
	"""Get status of all integrations"""
	integrations = frappe.db.sql("""
		SELECT name, system_name, system_type, sync_status, 
			   last_sync_time, is_active
		FROM `tabExternal System Integration`
		ORDER BY system_name
	""", as_dict=True)
	
	return {
		'success': True,
		'integrations': integrations
	}

@frappe.whitelist(allow_guest=False)
def get_sync_logs(integration_name=None, limit=50):
	"""Get synchronization logs"""
	conditions = []
	values = []
	
	if integration_name:
		conditions.append('integration_name = %s')
		values.append(integration_name)
	
	# This would require a separate Sync Log doctype to track detailed sync history
	# For now, return basic information
	logs = frappe.db.sql(f"""
		SELECT name, system_name, sync_status, last_sync_time, 
			   last_error_message, modified
		FROM `tabExternal System Integration`
		{f'WHERE {" AND ".join(conditions)}' if conditions else ''}
		ORDER BY modified DESC
		LIMIT %s
	""", values + [limit], as_dict=True)
	
	return {
		'success': True,
		'logs': logs
	}
