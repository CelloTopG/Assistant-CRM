# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now
from typing import Dict, Any, Optional, List
import logging

import os

# Oracle database integration (prefer python-oracledb)
ORACLE_AVAILABLE = False
try:
    import oracledb as cx_Oracle  # python-oracledb in thin mode
    ORACLE_AVAILABLE = True
except Exception:
    try:
        import cx_Oracle  # fallback if legacy driver is installed
        ORACLE_AVAILABLE = True
    except Exception:
        ORACLE_AVAILABLE = False
        frappe.log_error("Neither python-oracledb nor cx_Oracle available. Install with: pip install oracledb", "CoreBusiness Integration")

# Set up logging
logger = logging.getLogger(__name__)

class CoreBusinessConnector:
    """Secure connector for CoreBusiness Oracle database."""

    def __init__(self):
        self.settings = self.get_settings()
        self.connection = None

    def get_settings(self):
        """Get CoreBusiness settings from DocType."""
        try:
            settings = frappe.get_single("CoreBusiness Settings")
            if not settings.enabled:
                raise Exception("CoreBusiness integration is disabled")
            return settings
        except Exception as e:
            frappe.log_error(f"Error getting CoreBusiness settings: {str(e)}", "CoreBusiness Integration")
            raise

    def get_connection(self):
        """Establish secure connection to CoreBusiness Oracle database."""
        if not ORACLE_AVAILABLE:
            raise Exception("Oracle client not available. Please install 'oracledb' (python-oracledb).")

        if self.connection:
            try:
                # Test if connection is still alive
                cursor = self.connection.cursor()
                cursor.execute("SELECT 1 FROM DUAL")
                cursor.close()
                return self.connection
            except:
                self.connection = None

        try:
            # Prefer settings, then env vars, then safe defaults (for dev only)
            host = getattr(self.settings, "oracle_host", None) or frappe.conf.get("cbs_oracle_host") or os.environ.get("CBS_ORACLE_HOST") or "192.168.1.250"
            port = int(getattr(self.settings, "oracle_port", None) or frappe.conf.get("cbs_oracle_port") or os.environ.get("CBS_ORACLE_PORT") or 1521)
            service_name = getattr(self.settings, "oracle_service_name", None) or frappe.conf.get("cbs_oracle_service") or os.environ.get("CBS_ORACLE_SERVICE") or "testpas12cew"
            user = getattr(self.settings, "oracle_username", None) or frappe.conf.get("cbs_oracle_user") or os.environ.get("CBS_ORACLE_USER") or "workcom"
            password = getattr(self.settings, "oracle_password", None) or frappe.conf.get("cbs_oracle_password") or os.environ.get("CBS_ORACLE_PASSWORD") or "qK7zM3kU45X2s1qG47"

            if hasattr(cx_Oracle, "makedsn"):
                dsn = cx_Oracle.makedsn(host=host, port=port, service_name=service_name)
            else:
                dsn = f"{host}:{port}/{service_name}"

            self.connection = cx_Oracle.connect(user=user, password=password, dsn=dsn, encoding="UTF-8")

            logger.info("Successfully connected to CoreBusiness database")
            return self.connection

        except Exception as e:
            error_msg = f"Failed to connect to CoreBusiness database: {str(e)}"
            frappe.log_error(error_msg, "CoreBusiness Connection Error")
            raise Exception(error_msg)

    def execute_query(self, query: str, params: Dict = None) -> List[Dict]:
        """Execute SQL query and return results as list of dictionaries."""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Get column names
            columns = [desc[0] for desc in cursor.description]

            # Fetch all rows and convert to list of dictionaries
            rows = cursor.fetchall()
            results = []

            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    # Handle Oracle data types
                    if hasattr(value, 'read'):  # LOB objects
                        value = value.read()
                    elif hasattr(value, 'isoformat'):  # datetime objects
                        value = value.isoformat()
                    row_dict[columns[i]] = value
                results.append(row_dict)

            cursor.close()
            return results

        except Exception as e:
            error_msg = f"Database query error: {str(e)}"
            frappe.log_error(error_msg, "CoreBusiness Query Error")
            raise Exception(error_msg)

    def close_connection(self):
        """Close database connection."""
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
            except:
                pass


@frappe.whitelist()
def test_corebusiness_connection():
    """Test connection to CoreBusiness database"""
    try:
        connector = CoreBusinessConnector()
        connection = connector.get_connection()

        # Test with a simple query
        test_query = "SELECT SYSDATE FROM DUAL"
        results = connector.execute_query(test_query)
        connector.close_connection()

        return {
            "success": True,
            "message": "Successfully connected to CoreBusiness database",
            "server_time": results[0].get("SYSDATE") if results else None,
            "timestamp": now()
        }

    except Exception as e:
        frappe.log_error(f"Error testing CoreBusiness connection: {str(e)}")
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "timestamp": now()
        }

@frappe.whitelist()
def get_beneficiary_info(nrc_number: str = None, beneficiary_id: str = None):
    """Get beneficiary information from CoreBusiness database."""
    try:
        if not nrc_number and not beneficiary_id:
            return {"status": "error", "message": "NRC number or beneficiary ID is required"}

        connector = CoreBusinessConnector()

        # If Oracle is not available, return error (no simulation)
        if not ORACLE_AVAILABLE:
            return {"status": "error", "message": "Oracle driver not available; install python-oracledb"}

        # Query beneficiary information
        if nrc_number:
            query = """
                SELECT
                    BENEFICIARY_ID,
                    NRC_NUMBER,
                    FIRST_NAME,
                    LAST_NAME,
                    PHONE_NUMBER,
                    EMAIL_ADDRESS,
                    DATE_OF_BIRTH,
                    GENDER,
                    ADDRESS,
                    EMPLOYMENT_STATUS,
                    EMPLOYER_NAME,
                    REGISTRATION_DATE,
                    STATUS
                FROM BENEFICIARIES
                WHERE UPPER(NRC_NUMBER) = UPPER(:nrc_number)
                AND STATUS = 'ACTIVE'
            """
            params = {"nrc_number": nrc_number}
        else:
            query = """
                SELECT
                    BENEFICIARY_ID,
                    NRC_NUMBER,
                    FIRST_NAME,
                    LAST_NAME,
                    PHONE_NUMBER,
                    EMAIL_ADDRESS,
                    DATE_OF_BIRTH,
                    GENDER,
                    ADDRESS,
                    EMPLOYMENT_STATUS,
                    EMPLOYER_NAME,
                    REGISTRATION_DATE,
                    STATUS
                FROM BENEFICIARIES
                WHERE BENEFICIARY_ID = :beneficiary_id
                AND STATUS = 'ACTIVE'
            """
            params = {"beneficiary_id": beneficiary_id}

        results = connector.execute_query(query, params)
        connector.close_connection()

        if not results:
            return {
                "status": "error",
                "message": "No beneficiary found with the provided credentials"
            }

        beneficiary = results[0]

        return {
            "status": "success",
            "data": {
                "beneficiary_id": beneficiary.get("BENEFICIARY_ID"),
                "nrc_number": beneficiary.get("NRC_NUMBER"),
                "full_name": f"{beneficiary.get('FIRST_NAME', '')} {beneficiary.get('LAST_NAME', '')}".strip(),
                "phone_number": beneficiary.get("PHONE_NUMBER"),
                "email_address": beneficiary.get("EMAIL_ADDRESS"),
                "date_of_birth": beneficiary.get("DATE_OF_BIRTH"),
                "gender": beneficiary.get("GENDER"),
                "address": beneficiary.get("ADDRESS"),
                "employment_status": beneficiary.get("EMPLOYMENT_STATUS"),
                "employer_name": beneficiary.get("EMPLOYER_NAME"),
                "registration_date": beneficiary.get("REGISTRATION_DATE"),
                "status": beneficiary.get("STATUS")
            }
        }

    except Exception as e:
        frappe.log_error(f"Error getting beneficiary info: {str(e)}", "CoreBusiness API Error")
        return {"status": "error", "message": f"Database error: {str(e)}"}

@frappe.whitelist()
def get_pension_payments(beneficiary_id: str, limit: int = 10):
    """Get pension payment history for a beneficiary."""
    try:
        if not beneficiary_id:
            return {"status": "error", "message": "Beneficiary ID is required"}

        connector = CoreBusinessConnector()

        # If Oracle is not available, return error (no simulation)
        if not ORACLE_AVAILABLE:
            return {"status": "error", "message": "Oracle driver not available; install python-oracledb"}

        query = """
            SELECT
                PAYMENT_ID,
                BENEFICIARY_ID,
                PAYMENT_DATE,
                PAYMENT_AMOUNT,
                PAYMENT_METHOD,
                PAYMENT_STATUS,
                PAYMENT_REFERENCE,
                BANK_NAME,
                ACCOUNT_NUMBER,
                CREATED_DATE,
                PROCESSED_BY
            FROM PENSION_PAYMENTS
            WHERE BENEFICIARY_ID = :beneficiary_id
            ORDER BY PAYMENT_DATE DESC
            FETCH FIRST :limit ROWS ONLY
        """

        params = {"beneficiary_id": beneficiary_id, "limit": limit}
        results = connector.execute_query(query, params)
        connector.close_connection()

        return {
            "status": "success",
            "data": {
                "beneficiary_id": beneficiary_id,
                "payments": results,
                "total_payments": len(results)
            }
        }

    except Exception as e:
        frappe.log_error(f"Error getting pension payments: {str(e)}", "CoreBusiness API Error")
        return {"status": "error", "message": f"Database error: {str(e)}"}

@frappe.whitelist()
def get_claims_status(beneficiary_id: str = None, claim_number: str = None):
    """Get claims status for a beneficiary or specific claim."""
    try:
        if not beneficiary_id and not claim_number:
            return {"status": "error", "message": "Beneficiary ID or claim number is required"}

        connector = CoreBusinessConnector()

        # If Oracle is not available, return error (no simulation)
        if not ORACLE_AVAILABLE:
            return {"status": "error", "message": "Oracle driver not available; install python-oracledb"}

        if claim_number:
            query = """
                SELECT
                    CLAIM_ID,
                    CLAIM_NUMBER,
                    BENEFICIARY_ID,
                    CLAIM_TYPE,
                    CLAIM_STATUS,
                    CLAIM_AMOUNT,
                    SUBMISSION_DATE,
                    PROCESSING_DATE,
                    APPROVAL_DATE,
                    PAYMENT_DATE,
                    REJECTION_REASON,
                    ASSIGNED_OFFICER,
                    LAST_UPDATE_DATE
                FROM CLAIMS
                WHERE CLAIM_NUMBER = :claim_number
            """
            params = {"claim_number": claim_number}
        else:
            query = """
                SELECT
                    CLAIM_ID,
                    CLAIM_NUMBER,
                    BENEFICIARY_ID,
                    CLAIM_TYPE,
                    CLAIM_STATUS,
                    CLAIM_AMOUNT,
                    SUBMISSION_DATE,
                    PROCESSING_DATE,
                    APPROVAL_DATE,
                    PAYMENT_DATE,
                    REJECTION_REASON,
                    ASSIGNED_OFFICER,
                    LAST_UPDATE_DATE
                FROM CLAIMS
                WHERE BENEFICIARY_ID = :beneficiary_id
                ORDER BY SUBMISSION_DATE DESC
                FETCH FIRST 20 ROWS ONLY
            """
            params = {"beneficiary_id": beneficiary_id}

        results = connector.execute_query(query, params)
        connector.close_connection()

        return {
            "status": "success",
            "data": {
                "beneficiary_id": beneficiary_id,
                "claim_number": claim_number,
                "claims": results,
                "total_claims": len(results)
            }
        }

    except Exception as e:
        frappe.log_error(f"Error getting claims status: {str(e)}", "CoreBusiness API Error")
        return {"status": "error", "message": f"Database error: {str(e)}"}

# Demo data functions for when Oracle is not available
def get_demo_beneficiary_data(nrc_number: str = None, beneficiary_id: str = None):
    """Return demo beneficiary data for testing."""
    demo_beneficiaries = {
        "123456/78/1": {
            "beneficiary_id": "BEN001234",
            "nrc_number": "123456/78/1",
            "full_name": "Maria Santos",
            "phone_number": "+260977123456",
            "email_address": "maria.santos@email.com",
            "date_of_birth": "1978-05-15",
            "gender": "Female",
            "address": "Plot 123, Lusaka",
            "employment_status": "Retired",
            "employer_name": "Ministry of Health",
            "registration_date": "2020-01-15",
            "status": "ACTIVE"
        },
        "987654/32/1": {
            "beneficiary_id": "BEN005678",
            "nrc_number": "987654/32/1",
            "full_name": "John Mwanza",
            "phone_number": "+260966987654",
            "email_address": "john.mwanza@email.com",
            "date_of_birth": "1965-08-22",
            "gender": "Male",
            "address": "House 45, Kitwe",
            "employment_status": "Retired",
            "employer_name": "Konkola Copper Mines",
            "registration_date": "2018-03-10",
            "status": "ACTIVE"
        }
    }

    search_key = nrc_number or beneficiary_id
    for nrc, data in demo_beneficiaries.items():
        if search_key in [nrc, data["beneficiary_id"]]:
            return {"status": "success", "data": data}

    return {"status": "error", "message": "No beneficiary found with the provided credentials"}

def get_demo_pension_data(beneficiary_id: str, limit: int = 10):
    """Return demo pension payment data."""
    demo_payments = [
        {
            "PAYMENT_ID": "PAY001",
            "BENEFICIARY_ID": beneficiary_id,
            "PAYMENT_DATE": "2025-08-01",
            "PAYMENT_AMOUNT": 2500.00,
            "PAYMENT_METHOD": "Bank Transfer",
            "PAYMENT_STATUS": "Completed",
            "PAYMENT_REFERENCE": "REF2025080001",
            "BANK_NAME": "Zanaco Bank",
            "ACCOUNT_NUMBER": "****1234",
            "CREATED_DATE": "2025-08-01",
            "PROCESSED_BY": "System Auto"
        },
        {
            "PAYMENT_ID": "PAY002",
            "BENEFICIARY_ID": beneficiary_id,
            "PAYMENT_DATE": "2025-07-01",
            "PAYMENT_AMOUNT": 2500.00,
            "PAYMENT_METHOD": "Bank Transfer",
            "PAYMENT_STATUS": "Completed",
            "PAYMENT_REFERENCE": "REF2025070001",
            "BANK_NAME": "Zanaco Bank",
            "ACCOUNT_NUMBER": "****1234",
            "CREATED_DATE": "2025-07-01",
            "PROCESSED_BY": "System Auto"
        }
    ]

    return {
        "status": "success",
        "data": {
            "beneficiary_id": beneficiary_id,
            "payments": demo_payments[:limit],
            "total_payments": len(demo_payments)
        }
    }

def get_demo_claims_data(beneficiary_id: str = None, claim_number: str = None):
    """Return demo claims data."""
    demo_claims = [
        {
            "CLAIM_ID": "CLM001",
            "CLAIM_NUMBER": "WC2025001234",
            "BENEFICIARY_ID": beneficiary_id or "BEN001234",
            "CLAIM_TYPE": "Medical Expenses",
            "CLAIM_STATUS": "Under Review",
            "CLAIM_AMOUNT": 5000.00,
            "SUBMISSION_DATE": "2025-08-15",
            "PROCESSING_DATE": "2025-08-16",
            "APPROVAL_DATE": None,
            "PAYMENT_DATE": None,
            "REJECTION_REASON": None,
            "ASSIGNED_OFFICER": "Sarah Johnson",
            "LAST_UPDATE_DATE": "2025-08-20"
        }
    ]

    return {
        "status": "success",
        "data": {
            "beneficiary_id": beneficiary_id,
            "claim_number": claim_number,
            "claims": demo_claims,
            "total_claims": len(demo_claims)
        }
    }

# Utility functions for unified inbox integration
def get_customer_data_by_phone(phone_number: str):
    """Get customer data by phone number for unified inbox."""
    try:
        if not ORACLE_AVAILABLE:
            # No simulation; return empty when Oracle driver is unavailable
            return []

        # Clean phone number
        clean_phone = phone_number.replace("+", "").replace("-", "").replace(" ", "")

        connector = CoreBusinessConnector()

        query = """
            SELECT
                BENEFICIARY_ID,
                NRC_NUMBER,
                FIRST_NAME,
                LAST_NAME,
                PHONE_NUMBER,
                EMAIL_ADDRESS,
                EMPLOYER_NAME,
                STATUS
            FROM BENEFICIARIES
            WHERE REPLACE(REPLACE(REPLACE(PHONE_NUMBER, '+', ''), '-', ''), ' ', '') LIKE '%' || :phone || '%'
            AND STATUS = 'ACTIVE'
            FETCH FIRST 5 ROWS ONLY
        """

        params = {"phone": clean_phone[-9:]}  # Match last 9 digits
        results = connector.execute_query(query, params)
        connector.close_connection()

        return results

    except Exception as e:
        frappe.log_error(f"Error getting customer data by phone: {str(e)}", "CoreBusiness API Error")
        return []

def get_customer_context(customer_phone: str):
    """Get comprehensive customer context for AI responses."""
    try:
        customers = get_customer_data_by_phone(customer_phone)

        if not customers:
            return None

        customer = customers[0]
        beneficiary_id = customer.get("BENEFICIARY_ID")

        # Get recent payments
        payments_result = get_pension_payments(beneficiary_id, 3)
        recent_payments = payments_result.get("data", {}).get("payments", []) if payments_result.get("status") == "success" else []

        # Get recent claims
        claims_result = get_claims_status(beneficiary_id)
        recent_claims = claims_result.get("data", {}).get("claims", []) if claims_result.get("status") == "success" else []

        return {
            "customer_info": customer,
            "recent_payments": recent_payments,
            "recent_claims": recent_claims,
            "has_data": True
        }

    except Exception as e:
        frappe.log_error(f"Error getting customer context: {str(e)}", "CoreBusiness API Error")
        return None


@frappe.whitelist()
def configure_corebusiness_settings(**kwargs):
    """Configure CoreBusiness integration settings"""
    try:
        settings = frappe.get_single("CoreBusiness Settings")

        # Update settings from parameters
        if kwargs.get("base_url"):
            settings.base_url = kwargs["base_url"]
        if kwargs.get("api_key"):
            settings.api_key = kwargs["api_key"]
        if kwargs.get("auth_type"):
            settings.auth_type = kwargs["auth_type"]
        if kwargs.get("sync_interval_minutes"):
            settings.sync_interval_minutes = int(kwargs["sync_interval_minutes"])
        if kwargs.get("real_time_sync") is not None:
            settings.real_time_sync = int(kwargs["real_time_sync"])
        if kwargs.get("enabled") is not None:
            settings.enabled = int(kwargs["enabled"])

        # OAuth settings
        if kwargs.get("oauth_client_id"):
            settings.oauth_client_id = kwargs["oauth_client_id"]
        if kwargs.get("oauth_client_secret"):
            settings.oauth_client_secret = kwargs["oauth_client_secret"]
        if kwargs.get("oauth_token_url"):
            settings.oauth_token_url = kwargs["oauth_token_url"]
        if kwargs.get("oauth_scope"):
            settings.oauth_scope = kwargs["oauth_scope"]

        settings.save()
        frappe.db.commit()

        return {
            "success": True,
            "message": "CoreBusiness settings updated successfully",
            "timestamp": now()
        }

    except Exception as e:
        frappe.log_error(f"Error configuring CoreBusiness settings: {str(e)}")
        return {
            "success": False,
            "message": f"Configuration failed: {str(e)}",
            "timestamp": now()
        }


@frappe.whitelist()
def get_live_employer_data(employer_code):
    """Get live employer data from CoreBusiness"""
    try:
        from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService

        live_service = LiveDataRetrievalService()
        result = live_service.get_employer_data(employer_code)

        return {
            "success": result.get("success", False),
            "data": result.get("data", {}),
            "source": result.get("source", "unknown"),
            "error": result.get("error"),
            "last_updated": result.get("last_updated"),
            "timestamp": now()
        }

    except Exception as e:
        frappe.log_error(f"Error getting live employer data: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": now()
        }


@frappe.whitelist()
def get_live_beneficiary_data(beneficiary_id):
    """Get live beneficiary data from CoreBusiness"""
    try:
        from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService

        live_service = LiveDataRetrievalService()
        result = live_service.get_beneficiary_data(beneficiary_id)

        return {
            "success": result.get("success", False),
            "data": result.get("data", {}),
            "source": result.get("source", "unknown"),
            "error": result.get("error"),
            "last_updated": result.get("last_updated"),
            "timestamp": now()
        }

    except Exception as e:
        frappe.log_error(f"Error getting live beneficiary data: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": now()
        }


@frappe.whitelist()
def get_live_claim_status(claim_number):
    """Get live claim status from CoreBusiness"""
    try:
        from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService

        live_service = LiveDataRetrievalService()
        result = live_service.get_claim_status(claim_number)

        return {
            "success": result.get("success", False),
            "data": result.get("claim_data", {}),
            "source": result.get("source", "unknown"),
            "error": result.get("error"),
            "timestamp": now()
        }

    except Exception as e:
        frappe.log_error(f"Error getting live claim status: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": now()
        }


@frappe.whitelist()
def get_live_payment_status(payment_reference):
    """Get live payment status from CoreBusiness"""
    try:
        from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService

        live_service = LiveDataRetrievalService()
        result = live_service.get_payment_status(payment_reference)

        return {
            "success": result.get("success", False),
            "data": result.get("payment_data", {}),
            "source": result.get("source", "unknown"),
            "error": result.get("error"),
            "timestamp": now()
        }

    except Exception as e:
        frappe.log_error(f"Error getting live payment status: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": now()
        }


@frappe.whitelist()
def get_live_account_balance(account_identifier):
    """Get live account balance from CoreBusiness"""
    try:
        from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService

        live_service = LiveDataRetrievalService()
        result = live_service.get_account_balance(account_identifier)

        return {
            "success": result.get("success", False),
            "data": result.get("balance_data", {}),
            "source": result.get("source", "unknown"),
            "error": result.get("error"),
            "timestamp": now()
        }

    except Exception as e:
        frappe.log_error(f"Error getting live account balance: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": now()
        }


@frappe.whitelist()
def lookup_customer(phone=None, email=None, nrc=None):
    """Lookup customer by phone, email, or NRC"""
    try:
        from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService

        live_service = LiveDataRetrievalService()
        result = live_service.lookup_customer(phone=phone, email=email, nrc=nrc)

        return {
            "success": result.get("success", False),
            "data": result.get("customer_data", {}),
            "source": result.get("source", "unknown"),
            "error": result.get("error"),
            "timestamp": now()
        }

    except Exception as e:
        frappe.log_error(f"Error looking up customer: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": now()
        }


@frappe.whitelist()
def sync_employer_data(employer_code):
    """Manually sync employer data from CoreBusiness - Uses ERPNext Customer"""
    try:
        # WCFCBIntegrationService has been removed - use ERPNext Customer directly
        if frappe.db.exists("Customer", employer_code):
            customer = frappe.get_doc("Customer", employer_code)
            return {
                "success": True,
                "message": "Employer data available via ERPNext Customer",
                "data": {"customer_name": customer.customer_name},
                "timestamp": now()
            }

        return {
            "success": False,
            "message": "Employer not found in ERPNext Customer",
            "timestamp": now()
        }

    except Exception as e:
        frappe.log_error(f"Error syncing employer data: {str(e)}")
        return {
            "success": False,
            "message": f"Sync failed: {str(e)}",
            "timestamp": now()
        }


@frappe.whitelist()
def refresh_all_cache():
    """Refresh all cached data from CoreBusiness"""
    try:
        from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService

        live_service = LiveDataRetrievalService()
        result = live_service.refresh_all_cache()

        return {
            "success": result.get("success", False),
            "results": result.get("results", {}),
            "total_refreshed": result.get("total_refreshed", 0),
            "error_count": result.get("error_count", 0),
            "error": result.get("error"),
            "timestamp": now()
        }

    except Exception as e:
        frappe.log_error(f"Error refreshing cache: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": now()
        }


@frappe.whitelist()
def get_system_health():
    """Get CoreBusiness system health status"""
    try:
        from assistant_crm.services.live_data_retrieval_service import LiveDataRetrievalService

        live_service = LiveDataRetrievalService()
        result = live_service.get_system_health()

        return {
            "success": result.get("success", False),
            "status": result.get("status", "unknown"),
            "response_time": result.get("response_time"),
            "error": result.get("error"),
            "source": result.get("source", "unknown"),
            "timestamp": now()
        }

    except Exception as e:
        frappe.log_error(f"Error getting system health: {str(e)}")
        return {
            "success": False,
            "status": "error",
            "error": str(e),
            "timestamp": now()
        }
