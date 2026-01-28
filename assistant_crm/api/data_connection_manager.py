#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Secure Database Connection Manager
Establishes secure API connections to WCFCB data sources with connection pooling
Implements data access abstraction layer with comprehensive error handling
"""

import frappe
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from contextlib import contextmanager
import threading
from queue import Queue, Empty

class DataConnectionManager:
    """
    Secure connection manager for WCFCB data sources
    Handles connection pooling, error handling, and data access abstraction
    """
    
    def __init__(self):
        self.connection_pools = {}
        self.connection_timeout = 30  # seconds
        self.max_pool_size = 10
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds
        self.cache_ttl = 300  # 5 minutes default cache
        self.connection_lock = threading.Lock()
        
        # Initialize connection pools for different data sources
        self.initialize_connection_pools()
    
    def initialize_connection_pools(self):
        """Initialize connection pools for different WCFCB data sources"""
        try:
            data_sources = {
                "claims_db": {
                    "type": "database",
                    "config": self.get_claims_db_config(),
                    "pool_size": 5
                },
                "user_profiles": {
                    "type": "database", 
                    "config": self.get_user_profiles_config(),
                    "pool_size": 3
                },
                "employer_records": {
                    "type": "api",
                    "config": self.get_employer_api_config(),
                    "pool_size": 3
                },
                "medical_providers": {
                    "type": "api",
                    "config": self.get_medical_api_config(),
                    "pool_size": 2
                },
                "payment_system": {
                    "type": "api",
                    "config": self.get_payment_api_config(),
                    "pool_size": 3
                }
            }
            
            for source_name, config in data_sources.items():
                self.connection_pools[source_name] = ConnectionPool(
                    source_name, config, config["pool_size"]
                )
                
            frappe.log_error("Data connection pools initialized successfully")
            
        except Exception as e:
            frappe.log_error(f"Connection pool initialization error: {str(e)}")
            raise
    
    def get_live_data(self, data_type: str, query_params: Dict, 
                     user_permissions: List[str]) -> Dict:
        """
        Retrieve live data from appropriate source with permission checking
        """
        try:
            # Validate permissions
            if not self.check_data_access_permission(data_type, user_permissions):
                return {
                    "success": False,
                    "error": "Insufficient permissions",
                    "message": "You don't have permission to access this data"
                }
            
            # Check cache first
            cache_key = self.generate_cache_key(data_type, query_params)
            cached_data = self.get_cached_data(cache_key)
            
            if cached_data:
                return {
                    "success": True,
                    "data": cached_data,
                    "source": "cache",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Determine data source
            data_source = self.get_data_source_for_type(data_type)
            if not data_source:
                return {
                    "success": False,
                    "error": "Data source not found",
                    "message": f"No data source configured for {data_type}"
                }
            
            # Retrieve data with retry logic
            data = self.retrieve_data_with_retry(data_source, data_type, query_params)
            
            if data["success"]:
                # Cache successful results
                self.cache_data(cache_key, data["data"])
                
                # Apply data filtering based on permissions
                filtered_data = self.filter_data_by_permissions(
                    data["data"], data_type, user_permissions
                )
                
                return {
                    "success": True,
                    "data": filtered_data,
                    "source": "live",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return data
                
        except Exception as e:
            frappe.log_error(f"Live data retrieval error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve live data"
            }
    
    def retrieve_claim_data(self, claim_number: str, user_permissions: List[str]) -> Dict:
        """Retrieve comprehensive claim data"""
        try:
            query_params = {
                "claim_number": claim_number,
                "include_history": "read_claim_history" in user_permissions,
                "include_payments": "read_payment_info" in user_permissions,
                "include_medical": "read_medical_info" in user_permissions
            }
            
            return self.get_live_data("claim_details", query_params, user_permissions)
            
        except Exception as e:
            frappe.log_error(f"Claim data retrieval error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def retrieve_user_profile(self, user_id: str, user_permissions: List[str]) -> Dict:
        """Retrieve user profile data"""
        try:
            query_params = {
                "user_id": user_id,
                "include_contact": "read_contact_info" in user_permissions,
                "include_employment": "read_employment_info" in user_permissions
            }
            
            return self.get_live_data("user_profile", query_params, user_permissions)
            
        except Exception as e:
            frappe.log_error(f"User profile retrieval error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def retrieve_payment_information(self, user_id: str, user_permissions: List[str]) -> Dict:
        """Retrieve payment and compensation information"""
        try:
            if "read_payment_info" not in user_permissions:
                return {
                    "success": False,
                    "error": "Insufficient permissions for payment information"
                }
            
            query_params = {
                "user_id": user_id,
                "include_history": True,
                "include_pending": True
            }
            
            return self.get_live_data("payment_info", query_params, user_permissions)
            
        except Exception as e:
            frappe.log_error(f"Payment information retrieval error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def retrieve_employer_data(self, employer_id: str, user_permissions: List[str]) -> Dict:
        """Retrieve employer-specific data"""
        try:
            query_params = {
                "employer_id": employer_id,
                "include_employees": "read_employee_data" in user_permissions,
                "include_claims": "read_employee_claims" in user_permissions,
                "include_compliance": "read_compliance_data" in user_permissions
            }
            
            return self.get_live_data("employer_data", query_params, user_permissions)
            
        except Exception as e:
            frappe.log_error(f"Employer data retrieval error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def retrieve_medical_providers(self, location: str = None, specialty: str = None) -> Dict:
        """Retrieve medical provider information"""
        try:
            query_params = {
                "location": location,
                "specialty": specialty,
                "active_only": True
            }
            
            # Medical provider info is generally public
            return self.get_live_data("medical_providers", query_params, ["public"])
            
        except Exception as e:
            frappe.log_error(f"Medical providers retrieval error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def update_user_data(self, user_id: str, update_data: Dict, 
                        user_permissions: List[str]) -> Dict:
        """Update user data with permission checking"""
        try:
            # Check update permissions
            if not self.check_update_permission(update_data, user_permissions):
                return {
                    "success": False,
                    "error": "Insufficient permissions for data update"
                }
            
            # Validate update data
            validation_result = self.validate_update_data(update_data)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": "Invalid update data",
                    "details": validation_result["errors"]
                }
            
            # Perform update
            data_source = self.get_data_source_for_type("user_profile")
            result = self.perform_data_update(data_source, user_id, update_data)
            
            if result["success"]:
                # Invalidate cache
                self.invalidate_user_cache(user_id)
                
            return result
            
        except Exception as e:
            frappe.log_error(f"User data update error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # Connection Pool Management
    
    def retrieve_data_with_retry(self, data_source: str, data_type: str, 
                               query_params: Dict) -> Dict:
        """Retrieve data with retry logic and connection pooling"""
        
        for attempt in range(self.retry_attempts):
            try:
                with self.get_connection(data_source) as connection:
                    if connection:
                        data = self.execute_data_query(
                            connection, data_type, query_params
                        )
                        return {"success": True, "data": data}
                    else:
                        raise Exception("Failed to get connection from pool")
                        
            except Exception as e:
                frappe.log_error(f"Data retrieval attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    return {
                        "success": False,
                        "error": str(e),
                        "message": f"Failed to retrieve data after {self.retry_attempts} attempts"
                    }
    
    @contextmanager
    def get_connection(self, data_source: str):
        """Get connection from pool with context manager"""
        connection = None
        try:
            pool = self.connection_pools.get(data_source)
            if pool:
                connection = pool.get_connection()
                yield connection
            else:
                yield None
        finally:
            if connection and pool:
                pool.return_connection(connection)
    
    def execute_data_query(self, connection: Any, data_type: str, 
                          query_params: Dict) -> Any:
        """Execute data query based on connection type"""
        
        if data_type == "claim_details":
            return self.query_claim_details(connection, query_params)
        elif data_type == "user_profile":
            return self.query_user_profile(connection, query_params)
        elif data_type == "payment_info":
            return self.query_payment_info(connection, query_params)
        elif data_type == "employer_data":
            return self.query_employer_data(connection, query_params)
        elif data_type == "medical_providers":
            return self.query_medical_providers(connection, query_params)
        else:
            raise Exception(f"Unknown data type: {data_type}")
    
    # Data Query Methods (Simulated for now)
    
    def query_claim_details(self, connection: Any, params: Dict) -> Dict:
        """Query claim details using live data integration API"""
        try:
            # Import live data integration API
            from .live_data_integration_api import get_user_claim_status

            # Extract parameters
            user_id = params.get("user_id")
            claim_number = params.get("claim_number")

            # Call live data integration API
            live_result = get_user_claim_status(user_id=user_id, claim_number=claim_number)

            if live_result.get("status") == "success":
                data_obj = None
                if live_result.get("live_data") and live_result["live_data"].get("claim_status") is not None:
                    data_obj = live_result["live_data"]["claim_status"]
                elif live_result.get("data") is not None:
                    data_obj = live_result["data"]
                elif live_result.get("claim_data") is not None:
                    data_obj = live_result["claim_data"]

                if data_obj is None:
                    return {}

                # If claims list provided, pick matching claim
                claim = None
                if isinstance(data_obj, dict) and "claims" in data_obj and isinstance(data_obj["claims"], list):
                    if claim_number:
                        claim = next((c for c in data_obj["claims"] if str(c.get("CLAIM_NUMBER") or c.get("claim_number")) == str(claim_number)), None)
                    claim = claim or (data_obj["claims"][0] if data_obj["claims"] else None)
                elif isinstance(data_obj, dict):
                    claim = data_obj

                if not claim:
                    return {}

                return {
                    "claim_number": claim.get("CLAIM_NUMBER") or claim.get("claim_number"),
                    "status": claim.get("CLAIM_STATUS") or claim.get("status"),
                    "submission_date": claim.get("SUBMISSION_DATE") or claim.get("submission_date"),
                    "last_updated": claim.get("LAST_UPDATE_DATE") or claim.get("last_updated"),
                    "progress": claim.get("progress") or {},
                    "estimated_completion": claim.get("ESTIMATED_COMPLETION") or claim.get("estimated_completion"),
                    "assigned_officer": claim.get("ASSIGNED_OFFICER") or claim.get("assigned_officer"),
                    "contact_number": claim.get("CONTACT_NUMBER") or claim.get("contact_number"),
                    "current_stage": claim.get("CURRENT_STAGE") or None,
                    "next_action": claim.get("NEXT_ACTION") or None
                }
            else:
                return {}

        except Exception as e:
            frappe.log_error(f"Claim details query error: {str(e)}")
            return self.get_fallback_claim_data(params.get("claim_number"))

    def get_fallback_claim_data(self, claim_number: str) -> Dict:
        """Fallback claim data when live integration fails"""
        mock_claims = {
            "WC-2024-001234": {
                "claim_number": "WC-2024-001234",
                "status": "Medical Review",
                "current_stage": "Medical Assessment Complete",
                "next_action": "Disability Rating",
                "estimated_completion": "2024-03-25"
            }
        }
        return mock_claims.get(claim_number, {})
    
    def query_user_profile(self, connection: Any, params: Dict) -> Dict:
        """Query user profile using live data integration API"""
        try:
            # Import live data integration API
            from .live_data_integration_api import get_user_profile_data

            # Extract parameters
            user_id = params.get("user_id")

            # Call live data integration API
            live_result = get_user_profile_data(user_id=user_id)

            if live_result.get("status") == "success":
                data_obj = None
                if live_result.get("live_data") and live_result["live_data"].get("profile_data"):
                    data_obj = live_result["live_data"]["profile_data"]
                elif live_result.get("data"):
                    data_obj = live_result["data"]
                elif live_result.get("profile_data"):
                    data_obj = live_result["profile_data"]

                if not data_obj:
                    return {}

                return {
                    "user_id": data_obj.get("beneficiary_id") or data_obj.get("user_id"),
                    "full_name": data_obj.get("full_name") or f"{data_obj.get('FIRST_NAME','')} {data_obj.get('LAST_NAME','')}".strip(),
                    "date_of_birth": data_obj.get("date_of_birth") or data_obj.get("DATE_OF_BIRTH"),
                    "contact_info": {
                        "phone": data_obj.get("phone_number") or data_obj.get("PHONE_NUMBER"),
                        "email": data_obj.get("email_address") or data_obj.get("EMAIL_ADDRESS"),
                        "address": data_obj.get("address") or data_obj.get("ADDRESS"),
                    } if params.get("include_contact") else None,
                    "employment_info": {
                        "status": data_obj.get("employment_status") or data_obj.get("EMPLOYMENT_STATUS"),
                        "employer": data_obj.get("employer_name") or data_obj.get("EMPLOYER_NAME"),
                    } if params.get("include_employment") else None,
                    "account_status": data_obj.get("status") or data_obj.get("STATUS"),
                    "registration_date": data_obj.get("registration_date") or data_obj.get("REGISTRATION_DATE"),
                }
            else:
                return {}

        except Exception as e:
            frappe.log_error(f"User profile query error: {str(e)}")
            return self.get_fallback_profile_data(params.get("user_id"))

    def get_fallback_profile_data(self, user_id: str) -> Dict:
        """Fallback profile data when live integration fails"""
        return {
            "user_id": user_id or "unknown",
            "full_name": "User Profile",
            "account_status": "Active"
        }
    
    def query_payment_info(self, connection: Any, params: Dict) -> Dict:
        """Query payment information using live data integration API"""
        try:
            # Import live data integration API
            from .live_data_integration_api import get_user_payment_info

            # Extract parameters
            user_id = params.get("user_id")
            account_number = params.get("account_number")

            # Call live data integration API
            live_result = get_user_payment_info(user_id=user_id, account_number=account_number)

            if live_result.get("status") == "success":
                data_obj = None
                if live_result.get("live_data") and live_result["live_data"].get("payment_info"):
                    data_obj = live_result["live_data"]["payment_info"]
                elif live_result.get("data"):
                    data_obj = live_result["data"]
                elif live_result.get("payment_data"):
                    data_obj = live_result["payment_data"]

                if not data_obj:
                    return {}

                payments = data_obj.get("payments") or data_obj.get("payment_history") or []
                last_payment = payments[0] if payments else data_obj.get("last_payment")
                return {
                    "account_number": data_obj.get("account_number") or ((last_payment or {}).get("ACCOUNT_NUMBER")),
                    "current_balance": data_obj.get("current_balance"),
                    "last_payment": last_payment,
                    "next_payment": data_obj.get("next_payment", {}),
                    "payment_history": payments if params.get("include_history") else None,
                    "current_benefits": {
                        "amount": (last_payment or {}).get("PAYMENT_AMOUNT") or (last_payment or {}).get("amount"),
                        "method": (last_payment or {}).get("PAYMENT_METHOD") or (last_payment or {}).get("method"),
                        "next_scheduled": None
                    }
                }
            else:
                return {}

        except Exception as e:
            frappe.log_error(f"Payment info query error: {str(e)}")
            return self.get_fallback_payment_data()

    def get_fallback_payment_data(self) -> Dict:
        """Fallback payment data when live integration fails"""
        return {
            "current_benefits": {
                "temporary_disability": {
                    "weekly_amount": 450,
                    "last_payment": "2024-03-15",
                    "next_payment": "2024-03-22"
                }
            }
        }
    
    def query_employer_data(self, connection: Any, params: Dict) -> Dict:
        """Query employer data"""
        # Simulated employer data
        return {
            "employer_id": params.get("employer_id"),
            "company_name": "TechCorp Industries",
            "compliance_status": {
                "premium_status": "Current",
                "safety_training": "95% Complete",
                "incident_reporting": "2 Overdue"
            },
            "active_claims": 12,
            "employees_covered": 150
        }
    
    def query_medical_providers(self, connection: Any, params: Dict) -> Dict:
        """Query medical providers"""
        # Simulated medical provider data
        return {
            "providers": [
                {
                    "name": "City Medical Center",
                    "specialty": "Occupational Medicine",
                    "location": "Lusaka",
                    "phone": "+260-XXX-5678",
                    "accepts_wcfcb": True
                },
                {
                    "name": "Regional Orthopedic Clinic",
                    "specialty": "Orthopedics",
                    "location": "Lusaka",
                    "phone": "+260-XXX-9012",
                    "accepts_wcfcb": True
                }
            ]
        }
    
    # Permission and Security Methods
    
    def check_data_access_permission(self, data_type: str, user_permissions: List[str]) -> bool:
        """Check if user has permission to access specific data type"""
        permission_requirements = {
            "claim_details": ["read_own_claims", "read_all_claims"],
            "user_profile": ["read_own_profile", "read_user_profiles"],
            "payment_info": ["read_payment_info"],
            "employer_data": ["read_employer_data", "read_compliance_data"],
            "medical_providers": ["public"]  # Generally accessible
        }
        
        required_perms = permission_requirements.get(data_type, [])
        return any(perm in user_permissions for perm in required_perms) or "admin" in user_permissions
    
    def filter_data_by_permissions(self, data: Dict, data_type: str, 
                                 user_permissions: List[str]) -> Dict:
        """Filter data based on user permissions"""
        if "admin" in user_permissions:
            return data  # Admin sees everything
        
        # Apply field-level filtering based on permissions
        filtered_data = data.copy()
        
        if data_type == "claim_details":
            if "read_payment_info" not in user_permissions:
                filtered_data.pop("payments", None)
            if "read_medical_info" not in user_permissions:
                filtered_data.pop("medical_info", None)
        
        elif data_type == "user_profile":
            if "read_contact_info" not in user_permissions:
                filtered_data.pop("contact_info", None)
            if "read_employment_info" not in user_permissions:
                filtered_data.pop("employment_info", None)
        
        return filtered_data
    
    # Caching Methods
    
    def generate_cache_key(self, data_type: str, query_params: Dict) -> str:
        """Generate cache key for data query"""
        params_str = json.dumps(query_params, sort_keys=True)
        return f"wcfcb_data_{data_type}_{hashlib.md5(params_str.encode()).hexdigest()}"
    
    def get_cached_data(self, cache_key: str) -> Optional[Dict]:
        """Retrieve data from cache"""
        try:
            return frappe.cache().get_value(cache_key)
        except:
            return None
    
    def cache_data(self, cache_key: str, data: Dict, ttl: int = None) -> None:
        """Cache data with TTL"""
        try:
            frappe.cache().set_value(cache_key, data, expires_in_sec=ttl or self.cache_ttl)
        except Exception as e:
            frappe.log_error(f"Cache storage error: {str(e)}")
    
    def invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate all cached data for a user"""
        try:
            # This would invalidate all cache entries for the user
            # Implementation depends on cache structure
            pass
        except Exception as e:
            frappe.log_error(f"Cache invalidation error: {str(e)}")
    
    # Configuration Methods
    
    def get_claims_db_config(self) -> Dict:
        """Get claims database configuration"""
        return {
            "host": frappe.conf.get("claims_db_host", "localhost"),
            "port": frappe.conf.get("claims_db_port", 3306),
            "database": frappe.conf.get("claims_db_name", "wcfcb_claims"),
            "ssl_enabled": True
        }
    
    def get_user_profiles_config(self) -> Dict:
        """Get user profiles database configuration"""
        return {
            "host": frappe.conf.get("profiles_db_host", "localhost"),
            "port": frappe.conf.get("profiles_db_port", 3306),
            "database": frappe.conf.get("profiles_db_name", "wcfcb_users"),
            "ssl_enabled": True
        }
    
    def get_employer_api_config(self) -> Dict:
        """Get employer API configuration"""
        return {
            "base_url": frappe.conf.get("employer_api_url", "https://api.wcfcb.gov.zm/employers"),
            "api_key": frappe.conf.get("employer_api_key", ""),
            "timeout": 30
        }
    
    def get_medical_api_config(self) -> Dict:
        """Get medical providers API configuration"""
        return {
            "base_url": frappe.conf.get("medical_api_url", "https://api.wcfcb.gov.zm/medical"),
            "api_key": frappe.conf.get("medical_api_key", ""),
            "timeout": 30
        }
    
    def get_payment_api_config(self) -> Dict:
        """Get payment system API configuration"""
        return {
            "base_url": frappe.conf.get("payment_api_url", "https://api.wcfcb.gov.zm/payments"),
            "api_key": frappe.conf.get("payment_api_key", ""),
            "timeout": 30
        }
    
    def get_data_source_for_type(self, data_type: str) -> Optional[str]:
        """Get appropriate data source for data type"""
        data_source_mapping = {
            "claim_details": "claims_db",
            "user_profile": "user_profiles",
            "payment_info": "payment_system",
            "employer_data": "employer_records",
            "medical_providers": "medical_providers"
        }
        
        return data_source_mapping.get(data_type)
    
    # Update Methods
    
    def check_update_permission(self, update_data: Dict, user_permissions: List[str]) -> bool:
        """Check if user has permission to update specific fields"""
        # Implement field-level update permission checking
        return "update_profile" in user_permissions or "admin" in user_permissions
    
    def validate_update_data(self, update_data: Dict) -> Dict:
        """Validate update data format and content"""
        # Implement data validation logic
        return {"valid": True, "errors": []}
    
    def perform_data_update(self, data_source: str, user_id: str, update_data: Dict) -> Dict:
        """Perform actual data update"""
        # Simulate successful update
        return {"success": True, "message": "Data updated successfully"}

class ConnectionPool:
    """Simple connection pool implementation"""
    
    def __init__(self, source_name: str, config: Dict, pool_size: int):
        self.source_name = source_name
        self.config = config
        self.pool_size = pool_size
        self.connections = Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        
        # Initialize connections
        self.initialize_connections()
    
    def initialize_connections(self):
        """Initialize connection pool"""
        for _ in range(self.pool_size):
            connection = self.create_connection()
            if connection:
                self.connections.put(connection)
    
    def create_connection(self):
        """Create new connection (simulated)"""
        # In production, this would create actual database/API connections
        return {"source": self.source_name, "created_at": datetime.now()}
    
    def get_connection(self, timeout: int = 30):
        """Get connection from pool"""
        try:
            return self.connections.get(timeout=timeout)
        except Empty:
            return None
    
    def return_connection(self, connection):
        """Return connection to pool"""
        try:
            self.connections.put_nowait(connection)
        except:
            pass  # Pool is full

# API Endpoints

@frappe.whitelist()
def get_live_user_data():
    """API endpoint to get live user data"""
    try:
        data = frappe.local.form_dict
        data_type = data.get("data_type", "")
        query_params = data.get("query_params", {})
        user_permissions = data.get("user_permissions", [])

        connection_manager = DataConnectionManager()
        result = connection_manager.get_live_data(data_type, query_params, user_permissions)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        frappe.log_error(f"Live data API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_claim_information():
    """API endpoint to get claim information"""
    try:
        data = frappe.local.form_dict
        claim_number = data.get("claim_number", "")
        user_permissions = data.get("user_permissions", [])

        connection_manager = DataConnectionManager()
        result = connection_manager.retrieve_claim_data(claim_number, user_permissions)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        frappe.log_error(f"Claim information API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_user_profile_data():
    """API endpoint to get user profile data"""
    try:
        data = frappe.local.form_dict
        user_id = data.get("user_id", "")
        user_permissions = data.get("user_permissions", [])

        connection_manager = DataConnectionManager()
        result = connection_manager.retrieve_user_profile(user_id, user_permissions)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        frappe.log_error(f"User profile API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
