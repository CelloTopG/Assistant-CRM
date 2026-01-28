#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Tunnel Testing API
Whitelisted methods for testing ngrok tunnel connectivity
"""

import frappe
from frappe import _
from frappe.utils import now
import json


@frappe.whitelist(allow_guest=True)
def ping():
    """
    Simple ping endpoint for tunnel testing
    URL: https://your-ngrok-url.ngrok.io/api/method/assistant_crm.api.tunnel_test.ping
    """
    return {
        "success": True,
        "message": "pong",
        "timestamp": now(),
        "service": "WCFCB Assistant CRM",
        "tunnel_status": "active"
    }


@frappe.whitelist(allow_guest=True)
def test_connection():
    """
    Comprehensive connection test for ngrok tunnel
    URL: https://your-ngrok-url.ngrok.io/api/method/assistant_crm.api.tunnel_test.test_connection
    """
    try:
        # Basic system info
        response = {
            "success": True,
            "message": "ngrok tunnel connection successful",
            "timestamp": now(),
            "service": "WCFCB Assistant CRM",
            "version": "1.0",
            "tunnel_status": "active",
            "system": {
                "frappe_version": frappe.__version__,
                "site": frappe.local.site,
                "user": frappe.session.user,
                "method": frappe.local.request.method if hasattr(frappe.local, 'request') else "Unknown"
            },
            "endpoints": {
                "webhook": "/api/omnichannel/webhook/make-com",
                "chatbot": "/app/assistant-crm",
                "ping": "/api/method/assistant_crm.api.tunnel_test.ping",
                "test": "/api/method/assistant_crm.api.tunnel_test.test_connection",
                "status": "/api/method/assistant_crm.api.tunnel_test.get_status"
            }
        }
        
        # Try to get Make.com integration status
        try:
            settings = frappe.get_single("Social Media Settings")
            response["make_com_integration"] = {
                "enabled": settings.get("make_com_enabled", False),
                "api_key_configured": bool(settings.get("make_com_api_key")),
                "webhook_secret_configured": bool(settings.get("make_com_webhook_secret")),
                "rate_limit": settings.get("make_com_rate_limit", 1000),
                "timeout": settings.get("make_com_timeout", 30)
            }
        except Exception as e:
            response["make_com_integration"] = {
                "error": "Settings not accessible",
                "details": str(e)
            }
        
        return response
        
    except Exception as e:
        frappe.log_error(f"Tunnel test error: {str(e)}", "Tunnel Test")
        return {
            "success": False,
            "error": "Tunnel test failed",
            "details": str(e),
            "timestamp": now()
        }


@frappe.whitelist(allow_guest=True)
def get_status():
    """
    Get detailed system and tunnel status
    URL: https://your-ngrok-url.ngrok.io/api/method/assistant_crm.api.tunnel_test.get_status
    """
    try:
        # Get request information
        request_info = {}
        if hasattr(frappe.local, 'request'):
            request_info = {
                "method": frappe.local.request.method,
                "url": frappe.local.request.url,
                "headers": dict(frappe.local.request.headers),
                "remote_addr": frappe.local.request.environ.get('REMOTE_ADDR', 'Unknown')
            }
        
        # Get database status
        db_status = "connected"
        try:
            frappe.db.sql("SELECT 1")
        except:
            db_status = "disconnected"
        
        # Get app status
        app_status = {}
        try:
            installed_apps = frappe.get_installed_apps()
            app_status = {
                "installed_apps": installed_apps,
                "assistant_crm_installed": "assistant_crm" in installed_apps
            }
        except:
            app_status = {"error": "Could not get app status"}
        
        return {
            "success": True,
            "message": "Status retrieved successfully",
            "timestamp": now(),
            "system": {
                "frappe_version": frappe.__version__,
                "site": frappe.local.site,
                "user": frappe.session.user,
                "database_status": db_status
            },
            "request": request_info,
            "apps": app_status,
            "tunnel": {
                "status": "active",
                "type": "ngrok",
                "accessible": True
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Status check error: {str(e)}", "Status Check")
        return {
            "success": False,
            "error": "Status check failed",
            "details": str(e),
            "timestamp": now()
        }


@frappe.whitelist(allow_guest=True)
def test_webhook_simulation():
    """
    Simulate webhook processing for testing
    URL: https://your-ngrok-url.ngrok.io/api/method/assistant_crm.api.tunnel_test.test_webhook_simulation
    """
    try:
        # Simulate a webhook payload
        test_payload = {
            "platform": "test",
            "event_type": "message",
            "timestamp": now(),
            "data": {
                "message": {
                    "id": "test_123",
                    "content": "Hello Anna, this is a test message from tunnel",
                    "type": "text"
                },
                "sender": {
                    "id": "test_user",
                    "name": "Test User"
                },
                "conversation": {
                    "channel_id": "test_channel"
                }
            }
        }
        
        # Simulate Anna's response
        anna_response = {
            "reply": "Hi! I'm Anna from WCFCB. I received your test message through the ngrok tunnel. The connection is working perfectly! How can I help you today?",
            "actions": [],
            "personality": "Anna - WCFCB Team Member",
            "confidence": 0.95
        }
        
        return {
            "success": True,
            "message": "Webhook simulation completed successfully",
            "timestamp": now(),
            "test_payload": test_payload,
            "simulated_response": {
                "success": True,
                "response": anna_response,
                "conversation_id": f"conv_test_{now()}",
                "platform": "test",
                "processing_time": "< 1 second"
            },
            "tunnel_status": "active and processing correctly"
        }
        
    except Exception as e:
        frappe.log_error(f"Webhook simulation error: {str(e)}", "Webhook Simulation")
        return {
            "success": False,
            "error": "Webhook simulation failed",
            "details": str(e),
            "timestamp": now()
        }
