import os
import requests
import frappe
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json


class WorkersNotifyGateway:
    """
    Production-ready gateway for Workers Notify API.
    Supports development and production endpoints with automatic retries.
    """

    def __init__(self):
        # Fetch settings from the new DocType
        try:
            settings = frappe.get_single("Assistant CRM SMS Settings")
        except frappe.DoesNotExistError:
            # Fallback to general settings if separate DocType not found yet
            settings = frappe.get_single("Assistant CRM Settings")

        prod_url = settings.get("production_base_url") or "https://notify.workers.com.zm"
        dev_url = settings.get("development_base_url") or "https://notify.workers.com.zm"

        # WORKERS_NOTIFY_URL env var overrides the database setting (useful when DNS
        # for the public hostname is not resolvable from this server, e.g. use the
        # internal IP: WORKERS_NOTIFY_URL=http://192.168.1.32:9002)
        env_url = os.environ.get("WORKERS_NOTIFY_URL")
        if env_url:
            self.base_url = env_url.rstrip("/")
        else:
            self.base_url = (
                prod_url if settings.get("environment") == "Production" else dev_url
            ).rstrip("/")

        self.timeout = settings.get("timeout") or 30
        self.debug = settings.get("enable_debug_logging")

        # Proper Password retrieval for Frappe DocTypes
        try:
            self.api_key = settings.get_password("api_key")
        except Exception:
            self.api_key = settings.get("api_key")

        # Fallback: allow API key to be supplied via environment variable
        # (WORKERS_NOTIFY_API_KEY) when the database field is not yet populated
        if not self.api_key:
            self.api_key = os.environ.get("WORKERS_NOTIFY_API_KEY")

        self.session = self._build_session()

    def _build_session(self):
        session = requests.Session()

        # Enterprise-grade retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def send_single(self, recipient, message, created_by="assistant_crm"):
        """Send a single SMS message."""
        url = f"{self.base_url}/api/v1/notifier/sms"

        payload = {
            "recipient": recipient,
            "text": message,
            "createdBy": created_by,
        }

        return self._post(url, payload)

    def send_bulk(self, recipients, message, created_by="assistant_crm"):
        """Send bulk SMS messages."""
        url = f"{self.base_url}/api/v1/notifier/sms/bulk"

        payload = {
            "recipients": recipients,
            "text": message,
            "createdBy": created_by,
        }

        return self._post(url, payload)

    def _post(self, url, payload):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            if self.debug:
                frappe.log_error(
                    title="Workers SMS Gateway Payload",
                    message=f"URL: {url}\nHeaders: {headers}\nPayload: {json.dumps(payload, indent=2)}"
                )

            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )

            # Log raw response in debug mode
            if self.debug:
                frappe.log_error(
                    title="Workers SMS Gateway Raw Response",
                    message=f"Status: {response.status_code}\nHeaders: {dict(response.headers)}\nText: {response.text[:1000]}"
                )

            # Check for HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.reason}"
                try:
                    error_data = response.json()
                    if error_data.get("message"):
                        error_msg += f" - {error_data['message']}"
                    if error_data.get("error"):
                        error_msg += f" - {error_data['error']}"
                except:
                    pass

                frappe.log_error(
                    title="Workers SMS Gateway HTTP Error",
                    message=f"{error_msg}\nURL: {url}\nPayload: {json.dumps(payload)}\nResponse: {response.text[:500]}"
                )
                return {"success": False, "error": error_msg, "status_code": response.status_code}

            response.raise_for_status()
            data = response.json()

            # Check for API-level errors
            if not data.get("success", False):
                error_msg = data.get("message", data.get("error", "API returned success=false"))
                frappe.log_error(
                    title="Workers SMS Gateway API Error",
                    message=f"API Error: {error_msg}\nResponse: {json.dumps(data)}\nPayload: {json.dumps(payload)}"
                )
                return {"success": False, "error": error_msg, "response": data}

            return data

        except requests.exceptions.Timeout as e:
            error_msg = f"Workers SMS Gateway Timeout: {str(e)}"
            frappe.log_error(
                title="Workers SMS Gateway Timeout",
                message=f"{error_msg}\nURL: {url}\nTimeout: {self.timeout}s\nPayload: {json.dumps(payload)}"
            )
            return {"success": False, "error": error_msg}

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Workers SMS Gateway Connection Error: {str(e)}"
            frappe.log_error(
                title="Workers SMS Gateway Connection Error",
                message=f"{error_msg}\nURL: {url}\nPayload: {json.dumps(payload)}"
            )
            return {"success": False, "error": error_msg}

        except requests.exceptions.RequestException as e:
            error_msg = f"Workers SMS Gateway Request Error: {str(e)}"
            frappe.log_error(
                title="Workers SMS Gateway Request Error",
                message=f"{error_msg}\nURL: {url}\nPayload: {json.dumps(payload)}"
            )
            return {"success": False, "error": error_msg}

        except json.JSONDecodeError as e:
            error_msg = f"Workers SMS Gateway JSON Parse Error: {str(e)}"
            frappe.log_error(
                title="Workers SMS Gateway JSON Error",
                message=f"{error_msg}\nResponse text: {response.text[:500] if 'response' in locals() else 'No response'}"
            )
            return {"success": False, "error": error_msg}

        except Exception as e:
            error_msg = f"Workers SMS Gateway Unexpected Error: {str(e)}"
            frappe.log_error(
                title="Workers SMS Gateway Fatal Error",
                message=f"{error_msg}\n{frappe.get_traceback()}"
            )
            return {"success": False, "error": error_msg}
