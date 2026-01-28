#!/usr/bin/env python3
"""
Make.com Integration Setup Script for WCFCB Assistant CRM
=========================================================

This script configures the Make.com integration with secure credentials,
rate limits, and proper authentication settings.

Usage:
    python setup_make_com_integration.py

Requirements:
    - WCFCB Assistant CRM installed
    - Database access
    - Admin privileges
"""

import frappe
import secrets
import string
from frappe.utils import now


def generate_secure_api_key(length=32):
    """Generate a secure API key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_webhook_secret(length=64):
    """Generate a secure webhook secret"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def setup_make_com_integration():
    """Setup Make.com integration with secure configuration"""
    
    print("🚀 Setting up Make.com Integration for WCFCB Assistant CRM")
    print("=" * 60)
    
    try:
        # Initialize Frappe
        frappe.init(site='dev')
        frappe.connect()
        
        # Check if Social Media Settings exists
        if not frappe.db.exists("DocType", "Social Media Settings"):
            print("❌ Social Media Settings DocType not found!")
            print("Please ensure the assistant_crm app is properly installed.")
            return False
        
        # Get or create Social Media Settings
        if frappe.db.exists("Social Media Settings", "Social Media Settings"):
            settings = frappe.get_doc("Social Media Settings", "Social Media Settings")
            print("📋 Found existing Social Media Settings")
        else:
            settings = frappe.get_doc({
                "doctype": "Social Media Settings",
                "name": "Social Media Settings"
            })
            print("📋 Creating new Social Media Settings")
        
        # Generate secure credentials
        api_key = generate_secure_api_key()
        webhook_secret = generate_webhook_secret()
        
        print("\n🔐 Generating secure credentials...")
        print(f"✅ API Key generated: {api_key[:8]}...{api_key[-4:]}")
        print(f"✅ Webhook Secret generated: {webhook_secret[:8]}...{webhook_secret[-4:]}")
        
        # Configure Make.com integration
        settings.make_com_enabled = 1
        settings.make_com_api_key = api_key
        settings.make_com_webhook_secret = webhook_secret
        
        # Set production-ready rate limits and timeouts
        settings.make_com_rate_limit = 1000  # requests per hour
        settings.make_com_timeout = 30  # seconds
        
        # Set webhook URL (will be updated with actual domain)
        settings.make_com_webhook_url = "https://your-domain.com/api/method/assistant_crm.api.make_com_webhook.send_message_to_make_com"
        
        # Save settings
        if settings.is_new():
            settings.insert(ignore_permissions=True)
        else:
            settings.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        print("\n✅ Make.com Integration Configuration Complete!")
        print("=" * 60)
        
        # Display configuration details
        print("\n📊 INTEGRATION CONFIGURATION DETAILS")
        print("=" * 60)
        
        print(f"🔗 Webhook Endpoint URL:")
        print(f"   https://your-domain.com/api/omnichannel/webhook/make-com")
        
        print(f"\n🔑 Authentication Details:")
        print(f"   API Key: {api_key}")
        print(f"   Webhook Secret: {webhook_secret}")
        
        print(f"\n⚙️ Configuration Settings:")
        print(f"   Rate Limit: {settings.make_com_rate_limit} requests/hour")
        print(f"   Timeout: {settings.make_com_timeout} seconds")
        print(f"   Integration Enabled: {'Yes' if settings.make_com_enabled else 'No'}")
        
        print(f"\n📋 Required Headers for Make.com:")
        print(f"   Content-Type: application/json")
        print(f"   X-API-Key: {api_key}")
        print(f"   X-Webhook-Signature: sha256=<calculated_signature> (optional)")
        
        print(f"\n🔧 Make.com Scenario Configuration:")
        print(f"   1. Set webhook URL to: https://your-domain.com/api/omnichannel/webhook/make-com")
        print(f"   2. Add X-API-Key header with value: {api_key}")
        print(f"   3. Set Content-Type to: application/json")
        print(f"   4. Configure request timeout to: {settings.make_com_timeout} seconds")
        
        # Test webhook endpoint
        print(f"\n🧪 Testing webhook endpoint...")
        test_webhook_endpoint()
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up Make.com integration: {str(e)}")
        frappe.log_error(f"Make.com setup error: {str(e)}", "Make.com Setup")
        return False
    
    finally:
        frappe.destroy()


def test_webhook_endpoint():
    """Test the webhook endpoint to ensure it's working"""
    try:
        import requests
        import json
        
        # Test GET request (status check)
        webhook_url = "http://localhost:8000/api/omnichannel/webhook/make-com"
        
        print(f"   Testing GET request to {webhook_url}")
        
        try:
            response = requests.get(webhook_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print("   ✅ Webhook endpoint is responding correctly")
                else:
                    print("   ⚠️ Webhook endpoint responded but with unexpected data")
            else:
                print(f"   ⚠️ Webhook endpoint returned status {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("   ⚠️ Could not connect to webhook endpoint (server may not be running)")
        except Exception as e:
            print(f"   ⚠️ Error testing webhook: {str(e)}")
            
    except ImportError:
        print("   ⚠️ Requests library not available for testing")


def verify_integration():
    """Verify the integration is properly configured"""
    try:
        frappe.init(site='dev')
        frappe.connect()
        
        settings = frappe.get_doc("Social Media Settings", "Social Media Settings")
        
        print("\n🔍 INTEGRATION VERIFICATION")
        print("=" * 60)
        
        checks = [
            ("Make.com Integration Enabled", settings.make_com_enabled),
            ("API Key Configured", bool(settings.make_com_api_key)),
            ("Webhook Secret Configured", bool(settings.make_com_webhook_secret)),
            ("Rate Limit Set", bool(settings.make_com_rate_limit)),
            ("Timeout Configured", bool(settings.make_com_timeout))
        ]
        
        all_passed = True
        for check_name, check_result in checks:
            status = "✅ PASS" if check_result else "❌ FAIL"
            print(f"   {status} {check_name}")
            if not check_result:
                all_passed = False
        
        if all_passed:
            print("\n🎉 All verification checks passed!")
            print("   Make.com integration is ready for use.")
        else:
            print("\n⚠️ Some verification checks failed.")
            print("   Please review the configuration.")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Error verifying integration: {str(e)}")
        return False
    
    finally:
        frappe.destroy()


def display_integration_summary():
    """Display a summary of the integration setup"""
    try:
        frappe.init(site='dev')
        frappe.connect()
        
        settings = frappe.get_doc("Social Media Settings", "Social Media Settings")
        
        print("\n📋 MAKE.COM INTEGRATION SUMMARY")
        print("=" * 60)
        print("Copy the following details for your Make.com scenario setup:")
        print()
        
        print("🔗 WEBHOOK ENDPOINT:")
        print("   https://your-domain.com/api/omnichannel/webhook/make-com")
        print()
        
        print("🔑 AUTHENTICATION:")
        print(f"   API Key: {settings.make_com_api_key}")
        print(f"   Webhook Secret: {settings.make_com_webhook_secret}")
        print()
        
        print("📋 HEADERS:")
        print("   Content-Type: application/json")
        print(f"   X-API-Key: {settings.make_com_api_key}")
        print()
        
        print("⚙️ SETTINGS:")
        print(f"   Rate Limit: {settings.make_com_rate_limit} requests/hour")
        print(f"   Timeout: {settings.make_com_timeout} seconds")
        print()
        
        print("🚀 NEXT STEPS:")
        print("   1. Replace 'your-domain.com' with your actual domain")
        print("   2. Configure your Make.com scenario with the above details")
        print("   3. Test the integration with a sample message")
        print("   4. Monitor the webhook activity logs for successful processing")
        
    except Exception as e:
        print(f"❌ Error displaying summary: {str(e)}")
    
    finally:
        frappe.destroy()


if __name__ == "__main__":
    print("WCFCB Assistant CRM - Make.com Integration Setup")
    print("=" * 60)
    
    # Setup integration
    if setup_make_com_integration():
        # Verify configuration
        if verify_integration():
            # Display summary
            display_integration_summary()
        else:
            print("\n⚠️ Integration setup completed but verification failed.")
            print("Please check the configuration manually.")
    else:
        print("\n❌ Integration setup failed.")
        print("Please check the error logs and try again.")
