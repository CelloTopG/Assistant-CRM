#!/usr/bin/env python3
"""
Update Make.com Webhook URL with ngrok tunnel for testing
========================================================

This script updates the Social Media Settings to include the ngrok tunnel URL
for testing Make.com integrations.

Usage:
    python update_ngrok_webhook.py

Requirements:
    - WCFCB Assistant CRM installed
    - Database access
    - Admin privileges
"""

import frappe
import json
from frappe.utils import now


def update_ngrok_webhook():
    """Update Make.com webhook URL with ngrok tunnel"""
    
    print("🔗 Updating Make.com Webhook URL with ngrok tunnel")
    print("=" * 60)
    
    try:
        # Initialize Frappe
        frappe.init(site='dev')
        frappe.connect()
        
        # Get Social Media Settings
        if not frappe.db.exists("Social Media Settings", "Social Media Settings"):
            print("❌ Social Media Settings not found!")
            print("Please ensure the assistant_crm app is properly installed.")
            return False
        
        settings = frappe.get_doc("Social Media Settings", "Social Media Settings")
        
        # Update webhook URL with ngrok tunnel
        ngrok_url = "https://a9d168a9f208.ngrok-free.app"
        webhook_endpoint = "/api/method/assistant_crm.api.make_com_webhook.make_com_webhook"
        
        # Update the webhook URL
        settings.make_com_webhook_url = f"{ngrok_url}{webhook_endpoint}"
        
        # Ensure Make.com integration is enabled
        settings.make_com_enabled = 1
        
        # Save settings
        settings.save(ignore_permissions=True)
        frappe.db.commit()
        
        print("✅ Make.com Webhook URL updated successfully!")
        print("=" * 60)
        
        # Display updated configuration
        print("\n📊 UPDATED CONFIGURATION")
        print("=" * 60)
        
        print(f"🔗 Webhook URL:")
        print(f"   {settings.make_com_webhook_url}")
        
        print(f"\n🔑 Authentication:")
        print(f"   API Key: {settings.get_password('make_com_api_key') or 'Not configured'}")
        print(f"   Webhook Secret: {settings.get_password('make_com_webhook_secret') or 'Not configured'}")
        
        print(f"\n⚙️ Settings:")
        print(f"   Integration Enabled: {'Yes' if settings.make_com_enabled else 'No'}")
        print(f"   Rate Limit: {settings.make_com_rate_limit or 100} requests/hour")
        print(f"   Timeout: {settings.make_com_timeout or 30} seconds")
        
        print(f"\n🧪 Test URLs:")
        print(f"   GET Status: {ngrok_url}{webhook_endpoint}")
        print(f"   POST Webhook: {ngrok_url}{webhook_endpoint}")
        print(f"   Assistant CRM: {ngrok_url}/app/assistant-crm")
        
        print(f"\n📋 Make.com Configuration:")
        print(f"   1. Use webhook URL: {settings.make_com_webhook_url}")
        print(f"   2. Set method to: POST")
        print(f"   3. Add header: Content-Type: application/json")
        if settings.get_password('make_com_api_key'):
            print(f"   4. Add header: X-API-Key: {settings.get_password('make_com_api_key')}")
        
        # Test the webhook endpoint
        print(f"\n🧪 Testing webhook endpoint...")
        test_webhook_endpoint(ngrok_url, webhook_endpoint)
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating webhook URL: {str(e)}")
        frappe.log_error(f"Webhook URL update error: {str(e)}", "Make.com Webhook Update")
        return False
    
    finally:
        frappe.destroy()


def test_webhook_endpoint(base_url, endpoint):
    """Test the webhook endpoint to ensure it's accessible"""
    try:
        import requests
        
        webhook_url = f"{base_url}{endpoint}"
        
        print(f"   Testing GET request to {webhook_url}")
        
        try:
            # Test with ngrok headers to avoid warning page
            headers = {
                'ngrok-skip-browser-warning': 'true',
                'User-Agent': 'WCFCB-Assistant-CRM/1.0'
            }
            
            response = requests.get(webhook_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success"):
                        print("   ✅ Webhook endpoint is responding correctly")
                        print(f"   📊 Response: {data.get('message', 'No message')}")
                    else:
                        print("   ⚠️ Webhook endpoint responded but with unexpected data")
                        print(f"   📊 Response: {response.text[:200]}...")
                except json.JSONDecodeError:
                    print("   ⚠️ Webhook endpoint responded but not with JSON")
                    print(f"   📊 Response: {response.text[:200]}...")
            else:
                print(f"   ⚠️ Webhook endpoint returned status {response.status_code}")
                print(f"   📊 Response: {response.text[:200]}...")
                
        except requests.exceptions.ConnectionError:
            print("   ⚠️ Could not connect to webhook endpoint")
            print("   💡 Make sure the Frappe server is running and ngrok tunnel is active")
        except requests.exceptions.Timeout:
            print("   ⚠️ Request timed out")
        except Exception as e:
            print(f"   ⚠️ Error testing webhook: {str(e)}")
            
    except ImportError:
        print("   ⚠️ Requests library not available for testing")


def verify_ngrok_configuration():
    """Verify the ngrok configuration is working"""
    try:
        frappe.init(site='dev')
        frappe.connect()
        
        settings = frappe.get_doc("Social Media Settings", "Social Media Settings")
        
        print("\n🔍 NGROK CONFIGURATION VERIFICATION")
        print("=" * 60)
        
        checks = [
            ("Make.com Integration Enabled", settings.make_com_enabled),
            ("Webhook URL Contains ngrok", "ngrok" in (settings.make_com_webhook_url or "")),
            ("API Key Configured", bool(settings.get_password("make_com_api_key"))),
            ("Webhook Secret Configured", bool(settings.get_password("make_com_webhook_secret"))),
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
            print("   Make.com integration with ngrok is ready for testing.")
        else:
            print("\n⚠️ Some verification checks failed.")
            print("   Please review the configuration.")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Error verifying configuration: {str(e)}")
        return False
    
    finally:
        frappe.destroy()


def display_testing_instructions():
    """Display instructions for testing the Make.com integration"""
    print("\n📋 TESTING INSTRUCTIONS")
    print("=" * 60)
    print("1. 🌐 Open your browser and go to:")
    print("   https://a9d168a9f208.ngrok-free.app/app/assistant-crm")
    print()
    print("2. 🔧 In Make.com, configure your webhook scenario:")
    print("   - Webhook URL: https://a9d168a9f208.ngrok-free.app/api/method/assistant_crm.api.make_com_webhook.make_com_webhook")
    print("   - Method: POST")
    print("   - Content-Type: application/json")
    print("   - Add X-API-Key header with your API key")
    print()
    print("3. 🧪 Test the webhook with a sample payload:")
    print('   {')
    print('     "platform": "telegram",')
    print('     "event_type": "message",')
    print('     "data": {')
    print('       "message": {')
    print('         "content": "Hello Anna!",')
    print('         "type": "text"')
    print('       },')
    print('       "sender": {')
    print('         "id": "test_user_123",')
    print('         "name": "Test User"')
    print('       }')
    print('     }')
    print('   }')
    print()
    print("4. 📊 Monitor the webhook activity in the Assistant CRM system")
    print("5. 🔍 Check the logs for any errors or successful processing")


if __name__ == "__main__":
    print("WCFCB Assistant CRM - ngrok Webhook Configuration")
    print("=" * 60)
    
    # Update webhook URL
    if update_ngrok_webhook():
        # Verify configuration
        if verify_ngrok_configuration():
            # Display testing instructions
            display_testing_instructions()
        else:
            print("\n⚠️ Configuration updated but verification failed.")
            print("Please check the settings manually.")
    else:
        print("\n❌ Failed to update webhook URL.")
        print("Please check the error logs and try again.")
