import frappe
from frappe import _
import requests
import json
from datetime import datetime, timedelta
import hashlib
import hmac
from typing import Dict, List, Optional, Any

class CoreBusinessIntegrationService:
    """
    Enhanced CoreBusiness Integration Service for WCFCB Assistant CRM
    Provides real-time data synchronization with WCFCB's CoreBusiness systems
    Phase A Compliance Enhancement
    """

    def __init__(self):
        self.integration_config = self.load_integration_config()
        self.api_base_url = self.integration_config.get('api_endpoint') if self.integration_config else None
        self.auth_headers = self.get_auth_headers()
        self.config = self.get_enhanced_configuration()
        self.auth_token = None
        self.token_expires_at = None

    def load_integration_config(self):
        """Load CoreBusiness integration configuration"""
        config = frappe.db.get_value('External System Integration',
                                   {'system_type': 'CoreBusiness', 'is_active': 1},
                                   ['api_endpoint', 'authentication_type', 'api_key', 'access_token'],
                                   as_dict=True)
        return config

    def get_auth_headers(self):
        """Get authentication headers for CoreBusiness API"""
        if not self.integration_config:
            return {}

        headers = {'Content-Type': 'application/json'}

        if self.integration_config.get('authentication_type') == 'API Key':
            headers['Authorization'] = f"Bearer {self.integration_config.get('api_key')}"
        elif self.integration_config.get('authentication_type') == 'OAuth':
            headers['Authorization'] = f"Bearer {self.integration_config.get('access_token')}"

        return headers

    def validate_api_connection(self) -> Dict[str, Any]:
        """Validate CoreBusiness API connection and credentials with comprehensive testing."""
        try:
            # Check if configuration exists
            if not self.integration_config:
                return {
                    "valid": False,
                    "error": "CoreBusiness integration not configured",
                    "anna_message": "I'm having trouble connecting to our main system. Let me get our technical team to check this."
                }

            api_url = self.integration_config.get('api_endpoint')
            if not api_url:
                return {
                    "valid": False,
                    "error": "API endpoint not configured",
                    "anna_message": "Our system connection needs to be set up. I'll notify our technical team."
                }

            # Test connection with timeout and proper error handling
            try:
                import requests
                test_url = f"{api_url.rstrip('/')}/health"

                response = requests.get(
                    test_url,
                    headers=self.auth_headers,
                    timeout=5,
                    verify=True  # SSL verification
                )

                if response.status_code == 200:
                    response_data = response.json() if response.content else {}
                    return {
                        "valid": True,
                        "response_time": response.elapsed.total_seconds(),
                        "api_version": response_data.get("version", "unknown"),
                        "status": "connected",
                        "anna_message": "Great! I'm connected to our main system and ready to help you with live data."
                    }
                elif response.status_code == 401:
                    return {
                        "valid": False,
                        "error": "Authentication failed - invalid credentials",
                        "anna_message": "I'm having authentication issues with our main system. Let me use our backup information for now."
                    }
                elif response.status_code == 403:
                    return {
                        "valid": False,
                        "error": "Access forbidden - insufficient permissions",
                        "anna_message": "I don't have the right permissions to access some data. I'll work with what I can access."
                    }
                else:
                    return {
                        "valid": False,
                        "error": f"API returned status {response.status_code}",
                        "anna_message": "Our main system is responding but there might be some issues. I'll try to help you anyway."
                    }

            except requests.exceptions.Timeout:
                return {
                    "valid": False,
                    "error": "Connection timeout",
                    "anna_message": "Our main system is taking too long to respond. I'll use cached information to help you."
                }
            except requests.exceptions.ConnectionError:
                return {
                    "valid": False,
                    "error": "Connection failed",
                    "anna_message": "I can't reach our main system right now, but I can still help you with general information."
                }
            except Exception as e:
                return {
                    "valid": False,
                    "error": f"Connection test failed: {str(e)}",
                    "anna_message": "I'm having some technical difficulties, but I'm still here to help you as best I can."
                }

        except Exception as e:
            frappe.log_error(f"CoreBusiness API validation error: {str(e)}", "CoreBusiness Integration")
            return {
                "valid": False,
                "error": f"Validation failed: {str(e)}",
                "anna_message": "I'm experiencing some technical issues, but I'll do my best to help you with the information I have."
            }

    def get_enhanced_configuration(self) -> Dict[str, Any]:
        """Get enhanced CoreBusiness API configuration for Phase A compliance"""
        try:
            settings = frappe.get_single("CoreBusiness Settings")
            return {
                "base_url": settings.get("base_url", self.api_base_url or "https://corebusiness.wcfcb.gov.zm/api"),
                "api_key": settings.get("api_key", self.integration_config.get('api_key') if self.integration_config else ""),
                "api_secret": settings.get("api_secret"),
                "username": settings.get("username"),
                "password": settings.get("password"),
                "timeout": settings.get("timeout", 30),
                "enabled": settings.get("enabled", 1),
                "sync_interval_minutes": settings.get("sync_interval_minutes", 15),
                "real_time_sync": settings.get("real_time_sync", 1),
                "endpoints": {
                    "auth": settings.get("auth_endpoint", "/auth/login"),
                    "employers": settings.get("employers_endpoint", "/employers"),
                    "beneficiaries": settings.get("beneficiaries_endpoint", "/beneficiaries"),
                    "payments": settings.get("payments_endpoint", "/payments"),
                    "returns": settings.get("returns_endpoint", "/returns"),
                    "claims": settings.get("claims_endpoint", "/claims"),
                    "compliance": settings.get("compliance_endpoint", "/compliance"),
                    "deadlines": settings.get("deadlines_endpoint", "/deadlines"),
                    "customer_lookup": settings.get("customer_lookup_endpoint", "/customers/lookup")
                }
            }
        except Exception:
            # Fallback to existing configuration
            return {
                "base_url": self.api_base_url or "https://corebusiness.wcfcb.gov.zm/api",
                "api_key": self.integration_config.get('api_key') if self.integration_config else "",
                "api_secret": "",
                "username": "",
                "password": "",
                "timeout": 30,
                "enabled": 1,
                "sync_interval_minutes": 15,
                "real_time_sync": 1,
                "endpoints": {
                    "auth": "/auth/login",
                    "employers": "/employers",
                    "beneficiaries": "/beneficiaries",
                    "payments": "/payments",
                    "returns": "/returns",
                    "claims": "/claims",
                    "compliance": "/compliance",
                    "deadlines": "/deadlines",
                    "customer_lookup": "/customers/lookup"
                }
            }

    def authenticate_enhanced(self) -> bool:
        """Enhanced authentication with CoreBusiness API for real-time sync"""
        try:
            if not self.config["enabled"]:
                return False

            # Check if current token is still valid
            if (self.auth_token and self.token_expires_at and
                datetime.now() < self.token_expires_at):
                return True

            # Use existing auth headers if available
            if self.auth_headers and self.auth_headers.get('Authorization'):
                self.auth_token = self.auth_headers.get('Authorization').replace('Bearer ', '')
                self.token_expires_at = datetime.now() + timedelta(hours=1)
                return True

            # Authenticate with enhanced method
            auth_url = f"{self.config['base_url']}{self.config['endpoints']['auth']}"

            auth_data = {
                "username": self.config["username"],
                "password": self.config["password"],
                "api_key": self.config["api_key"]
            }

            # Add API signature if secret is provided
            if self.config["api_secret"]:
                timestamp = str(int(datetime.now().timestamp()))
                signature_data = f"{self.config['api_key']}{timestamp}{self.config['api_secret']}"
                signature = hashlib.sha256(signature_data.encode()).hexdigest()

                auth_data.update({
                    "timestamp": timestamp,
                    "signature": signature
                })

            response = requests.post(
                auth_url,
                json=auth_data,
                timeout=self.config["timeout"]
            )

            if response.status_code == 200:
                auth_result = response.json()

                if auth_result.get("success"):
                    self.auth_token = auth_result.get("access_token")
                    expires_in = auth_result.get("expires_in", 3600)
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)

                    # Update auth headers
                    self.auth_headers["Authorization"] = f"Bearer {self.auth_token}"

                    return True

            # Fallback to existing authentication
            return bool(self.auth_headers.get('Authorization'))

        except Exception as e:
            frappe.log_error(f"Error in enhanced CoreBusiness authentication: {str(e)}")
            # Fallback to existing authentication
            return bool(self.auth_headers.get('Authorization'))

    def make_enhanced_api_request(self, endpoint: str, method: str = "GET", data: Dict = None, params: Dict = None) -> Dict[str, Any]:
        """Make enhanced authenticated API request to CoreBusiness"""
        try:
            if not self.authenticate_enhanced():
                return {
                    "success": False,
                    "error": "Authentication failed"
                }

            url = f"{self.config['base_url']}{endpoint}"
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json",
                "X-API-Key": self.config["api_key"],
                "X-CRM-Integration": "WCFCB-Assistant-CRM"
            }

            request_kwargs = {
                "headers": headers,
                "timeout": self.config["timeout"]
            }

            if params:
                request_kwargs["params"] = params

            if data and method in ["POST", "PUT", "PATCH"]:
                request_kwargs["json"] = data

            response = requests.request(method, url, **request_kwargs)

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json(),
                    "status_code": response.status_code
                }
            else:
                return {
                    "success": False,
                    "error": f"API request failed with status {response.status_code}",
                    "status_code": response.status_code,
                    "response_text": response.text
                }

        except requests.exceptions.RequestException as e:
            frappe.log_error(f"Enhanced CoreBusiness API request failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            }
        except Exception as e:
            frappe.log_error(f"Error making enhanced CoreBusiness API request: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def sync_employer_data(self):
        """Sync employer data from CoreBusiness"""
        try:
            if not self.api_base_url:
                return {'success': False, 'error': 'CoreBusiness integration not configured'}

            # Fetch employers from CoreBusiness API
            employers_url = f"{self.api_base_url}/api/employers"
            response = requests.get(employers_url, headers=self.auth_headers, timeout=60)

            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'API request failed with status {response.status_code}: {response.text}'
                }

            employers_data = response.json()

            # Process and sync employer data
            synced_count = 0
            errors = []

            for employer_data in employers_data.get('data', []):
                try:
                    self.process_employer_record(employer_data)
                    synced_count += 1
                except Exception as e:
                    errors.append(f"Error processing employer {employer_data.get('id', 'unknown')}: {str(e)}")

            return {
                'success': True,
                'synced_count': synced_count,
                'errors': errors,
                'message': f'Successfully synced {synced_count} employers'
            }

        except Exception as e:
            frappe.log_error(f"CoreBusiness employer sync failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    def process_employer_record(self, employer_data):
        """Process and create/update employer record"""
        # Map CoreBusiness fields to Frappe Contact fields
        employer_id = employer_data.get('employer_id')

        if not employer_id:
            raise Exception("Employer ID is required")

        # Check if employer already exists
        existing_contact = frappe.db.get_value('Contact',
                                             {'corebusiness_id': employer_id},
                                             'name')

        contact_data = {
            'doctype': 'Contact',
            'first_name': employer_data.get('company_name', ''),
            'company_name': employer_data.get('company_name', ''),
            'email_id': employer_data.get('email', ''),
            'phone': employer_data.get('phone', ''),
            'mobile_no': employer_data.get('mobile', ''),
            'stakeholder_type': 'Employer',
            'corebusiness_id': employer_id,
            'address_line1': employer_data.get('address', ''),
            'city': employer_data.get('city', ''),
            'state': employer_data.get('state', ''),
            'pincode': employer_data.get('postal_code', ''),
            'is_primary_contact': 1
        }

        if existing_contact:
            # Update existing contact
            contact = frappe.get_doc('Contact', existing_contact)
            for field, value in contact_data.items():
                if field != 'doctype' and value:
                    setattr(contact, field, value)
            contact.save()
        else:
            # Create new contact
            contact = frappe.get_doc(contact_data)
            contact.insert()

        # Sync additional employer-specific data
        self.sync_employer_benefits(employer_id, employer_data.get('benefits', []))

    def sync_employer_benefits(self, employer_id, benefits_data):
        """Sync employer benefits information"""
        # This could create records in a custom Benefits doctype
        # For now, we'll store it as JSON in a custom field
        try:
            contact = frappe.db.get_value('Contact', {'corebusiness_id': employer_id}, 'name')
            if contact:
                frappe.db.set_value('Contact', contact, 'benefits_data', json.dumps(benefits_data))
        except Exception as e:
            frappe.log_error(f"Failed to sync benefits for employer {employer_id}: {str(e)}")

    def sync_beneficiary_data(self):
        """Sync beneficiary data from CoreBusiness"""
        try:
            if not self.api_base_url:
                return {'success': False, 'error': 'CoreBusiness integration not configured'}

            # Fetch beneficiaries from CoreBusiness API
            beneficiaries_url = f"{self.api_base_url}/api/beneficiaries"
            response = requests.get(beneficiaries_url, headers=self.auth_headers, timeout=60)

            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'API request failed with status {response.status_code}: {response.text}'
                }

            beneficiaries_data = response.json()

            # Process and sync beneficiary data
            synced_count = 0
            errors = []

            for beneficiary_data in beneficiaries_data.get('data', []):
                try:
                    self.process_beneficiary_record(beneficiary_data)
                    synced_count += 1
                except Exception as e:
                    errors.append(f"Error processing beneficiary {beneficiary_data.get('id', 'unknown')}: {str(e)}")

            return {
                'success': True,
                'synced_count': synced_count,
                'errors': errors,
                'message': f'Successfully synced {synced_count} beneficiaries'
            }

        except Exception as e:
            frappe.log_error(f"CoreBusiness beneficiary sync failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    def process_beneficiary_record(self, beneficiary_data):
        """Process and create/update beneficiary record"""
        beneficiary_id = beneficiary_data.get('beneficiary_id')

        if not beneficiary_id:
            raise Exception("Beneficiary ID is required")

        # Check if beneficiary already exists
        existing_contact = frappe.db.get_value('Contact',
                                             {'corebusiness_id': beneficiary_id},
                                             'name')

        contact_data = {
            'doctype': 'Contact',
            'first_name': beneficiary_data.get('first_name', ''),
            'last_name': beneficiary_data.get('last_name', ''),
            'email_id': beneficiary_data.get('email', ''),
            'phone': beneficiary_data.get('phone', ''),
            'mobile_no': beneficiary_data.get('mobile', ''),
            'stakeholder_type': 'Beneficiary',
            'corebusiness_id': beneficiary_id,
            'address_line1': beneficiary_data.get('address', ''),
            'city': beneficiary_data.get('city', ''),
            'state': beneficiary_data.get('state', ''),
            'pincode': beneficiary_data.get('postal_code', ''),
            'date_of_birth': beneficiary_data.get('date_of_birth'),
            'gender': beneficiary_data.get('gender'),
            'is_primary_contact': 1
        }

        if existing_contact:
            # Update existing contact
            contact = frappe.get_doc('Contact', existing_contact)
            for field, value in contact_data.items():
                if field != 'doctype' and value:
                    setattr(contact, field, value)
            contact.save()
        else:
            # Create new contact
            contact = frappe.get_doc(contact_data)
            contact.insert()

        # Sync beneficiary claims and coverage
        self.sync_beneficiary_claims(beneficiary_id, beneficiary_data.get('claims', []))
        self.sync_beneficiary_coverage(beneficiary_id, beneficiary_data.get('coverage', {}))

    def sync_beneficiary_claims(self, beneficiary_id, claims_data):
        """Sync beneficiary claims information"""
        try:
            contact = frappe.db.get_value('Contact', {'corebusiness_id': beneficiary_id}, 'name')
            if contact:
                frappe.db.set_value('Contact', contact, 'claims_data', json.dumps(claims_data))
        except Exception as e:
            frappe.log_error(f"Failed to sync claims for beneficiary {beneficiary_id}: {str(e)}")

    def sync_beneficiary_coverage(self, beneficiary_id, coverage_data):
        """Sync beneficiary coverage information"""
        try:
            contact = frappe.db.get_value('Contact', {'corebusiness_id': beneficiary_id}, 'name')
            if contact:
                frappe.db.set_value('Contact', contact, 'coverage_data', json.dumps(coverage_data))
        except Exception as e:
            frappe.log_error(f"Failed to sync coverage for beneficiary {beneficiary_id}: {str(e)}")

    def get_customer_360_view(self, contact_id):
        """Get comprehensive 360-degree view of customer"""
        try:
            # Get basic contact information
            contact = frappe.get_doc('Contact', contact_id)

            # Get conversation history
            conversations = frappe.db.sql("""
                SELECT conversation_id, status, priority, creation,
                       assigned_agent, resolution_time
                FROM `tabOmnichannel Conversation`
                WHERE customer_id = %s
                ORDER BY creation DESC
                LIMIT 10
            """, (contact_id,), as_dict=True)

            # Get CSAT history (legacy CSAT DocType removed). For now, return empty list or later map from Survey Responses
            csat_history = []

            # Get CoreBusiness data if available
            corebusiness_data = {}
            if contact.corebusiness_id:
                corebusiness_data = self.fetch_realtime_customer_data(contact.corebusiness_id)

            # Compile 360-degree view
            customer_360 = {
                'contact_info': {
                    'name': f"{contact.first_name} {contact.last_name or ''}".strip(),
                    'email': contact.email_id,
                    'phone': contact.mobile_no or contact.phone,
                    'stakeholder_type': contact.stakeholder_type,
                    'address': f"{contact.address_line1 or ''} {contact.city or ''} {contact.state or ''}".strip()
                },
                'conversation_history': conversations,
                'satisfaction_history': csat_history,
                'corebusiness_data': corebusiness_data,
                'summary_stats': {
                    'total_conversations': len(conversations),
                    'avg_csat': sum(float(c.get('rating', 0)) for c in csat_history) / len(csat_history) if csat_history else 0,
                    'last_interaction': conversations[0].get('creation') if conversations else None
                }
            }

            return {
                'success': True,
                'customer_360': customer_360
            }

        except Exception as e:
            frappe.log_error(f"Failed to get customer 360 view: {str(e)}")
            return {'success': False, 'error': str(e)}

    def fetch_realtime_customer_data(self, corebusiness_id):
        """Fetch real-time customer data from CoreBusiness"""
        try:
            if not self.api_base_url:
                return {}

            # Fetch real-time data
            customer_url = f"{self.api_base_url}/api/customer/{corebusiness_id}"
            response = requests.get(customer_url, headers=self.auth_headers, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                return {}

        except Exception as e:
            frappe.log_error(f"Failed to fetch real-time customer data: {str(e)}")
            return {}

    def search_corebusiness_customer(self, search_term):
        """Search for customer in CoreBusiness system"""
        try:
            if not self.api_base_url:
                return {'success': False, 'error': 'CoreBusiness integration not configured'}

            search_url = f"{self.api_base_url}/api/search/customer"
            params = {'q': search_term}

            response = requests.get(search_url, headers=self.auth_headers, params=params, timeout=30)

            if response.status_code == 200:
                search_results = response.json()
                return {
                    'success': True,
                    'results': search_results.get('data', [])
                }
            else:
                return {
                    'success': False,
                    'error': f'Search failed with status {response.status_code}'
                }

        except Exception as e:
            frappe.log_error(f"CoreBusiness customer search failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    def validate_customer_eligibility(self, corebusiness_id, service_type):
        """Validate customer eligibility for specific services"""
        try:
            if not self.api_base_url:
                return {'success': False, 'error': 'CoreBusiness integration not configured'}

            eligibility_url = f"{self.api_base_url}/api/eligibility/{corebusiness_id}"
            params = {'service_type': service_type}

            response = requests.get(eligibility_url, headers=self.auth_headers, params=params, timeout=30)

            if response.status_code == 200:
                eligibility_data = response.json()
                return {
                    'success': True,
                    'eligible': eligibility_data.get('eligible', False),
                    'details': eligibility_data.get('details', {}),
                    'restrictions': eligibility_data.get('restrictions', [])
                }
            else:
                return {
                    'success': False,
                    'error': f'Eligibility check failed with status {response.status_code}'
                }

        except Exception as e:
            frappe.log_error(f"Eligibility validation failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_integration_health_status(self):
        """Get health status of CoreBusiness integration"""
        try:
            if not self.api_base_url:
                return {
                    'status': 'Not Configured',
                    'message': 'CoreBusiness integration not configured'
                }

            # Test API connectivity
            health_url = f"{self.api_base_url}/api/health"
            response = requests.get(health_url, headers=self.auth_headers, timeout=10)

            if response.status_code == 200:
                health_data = response.json()
                return {
                    'status': 'Healthy',
                    'response_time': response.elapsed.total_seconds(),
                    'api_version': health_data.get('version', 'Unknown'),
                    'last_checked': frappe.utils.now()
                }
            else:
                return {
                    'status': 'Unhealthy',
                    'message': f'API returned status {response.status_code}',
                    'last_checked': frappe.utils.now()
                }

        except Exception as e:
            return {
                'status': 'Error',
                'message': str(e),
                'last_checked': frappe.utils.now()
            }


    def get_claim_by_id(self, claim_id: str):
        """Fetch a single claim by ID/number from CoreBusiness."""
        try:
            if not self.api_base_url:
                return None
            url = f"{self.api_base_url}/api/claims/{claim_id}"
            resp = requests.get(url, headers=self.auth_headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data.get('data') if isinstance(data, dict) and 'data' in data else data
            return None
        except Exception as e:
            frappe.log_error(f"CoreBusiness get_claim_by_id error: {str(e)}")
            return None

    def get_claims(self, date_from: str = None, date_to: str = None, status: str = None, limit: int = 500):
        """Fetch claims list from CoreBusiness with optional filters."""
        try:
            if not self.api_base_url:
                return []
            url = f"{self.api_base_url}/api/claims"
            params = {}
            if date_from:
                params['from'] = date_from
            if date_to:
                params['to'] = date_to
            if status:
                params['status'] = status
            if limit:
                params['limit'] = limit
            resp = requests.get(url, headers=self.auth_headers, params=params, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    if 'data' in data and isinstance(data['data'], list):
                        return data['data']
                    if 'results' in data and isinstance(data['results'], list):
                        return data['results']
                    return []
                return data if isinstance(data, list) else []
            return []
        except Exception as e:
            frappe.log_error(f"CoreBusiness get_claims error: {str(e)}")
            return []

    def get_payments(self, date_from: str = None, date_to: str = None, beneficiary_id: str = None, status: str = None, limit: int = 1000):
        """Fetch payments list from CoreBusiness with optional filters.
        Returns a list (empty on failure) and is tolerant to {data:[...]} or direct list responses.
        """
        try:
            if not self.api_base_url:
                return []
            url = f"{self.api_base_url}/api/payments"
            params = {}
            if date_from:
                params['from'] = date_from
            if date_to:
                params['to'] = date_to
            if beneficiary_id:
                params['beneficiary_id'] = beneficiary_id
            if status:
                params['status'] = status
            if limit:
                params['limit'] = limit
            resp = requests.get(url, headers=self.auth_headers, params=params, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    if 'data' in data and isinstance(data['data'], list):
                        return data['data']
                    if 'results' in data and isinstance(data['results'], list):
                        return data['results']
                    return []
                return data if isinstance(data, list) else []
            return []
        except Exception as e:
            frappe.log_error(f"CoreBusiness get_payments error: {str(e)}")
            return []


@frappe.whitelist(allow_guest=False)
def sync_corebusiness_data(data_type='all'):
    """API endpoint to sync CoreBusiness data"""
    service = CoreBusinessIntegrationService()

    results = {}

    if data_type in ['employers', 'all']:
        results['employers'] = service.sync_employer_data()

    if data_type in ['beneficiaries', 'all']:
        results['beneficiaries'] = service.sync_beneficiary_data()

    return results

@frappe.whitelist(allow_guest=False)
def get_customer_360_view(contact_id):
    """API endpoint to get customer 360-degree view"""
    service = CoreBusinessIntegrationService()
    return service.get_customer_360_view(contact_id)

@frappe.whitelist(allow_guest=False)
def search_corebusiness_customer(search_term):
    """API endpoint to search CoreBusiness customers"""
    service = CoreBusinessIntegrationService()
    return service.search_corebusiness_customer(search_term)

@frappe.whitelist(allow_guest=False)
def validate_customer_eligibility(corebusiness_id, service_type):
    """API endpoint to validate customer eligibility"""
    service = CoreBusinessIntegrationService()
    return service.validate_customer_eligibility(corebusiness_id, service_type)
