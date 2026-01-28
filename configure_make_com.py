#!/usr/bin/env python3
"""
Direct Make.com Integration Configuration
========================================

This script directly configures the Make.com integration by creating the necessary
configuration files and providing the integration details.

Usage:
    python configure_make_com.py
"""

import json
import secrets
import string
import os
from datetime import datetime


def generate_secure_api_key(length=32):
    """Generate a secure API key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_webhook_secret(length=64):
    """Generate a secure webhook secret"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_integration_config():
    """Create Make.com integration configuration"""
    
    print("🚀 WCFCB Assistant CRM - Make.com Integration Setup")
    print("=" * 60)
    
    # Generate secure credentials
    api_key = generate_secure_api_key()
    webhook_secret = generate_webhook_secret()
    
    print("\n🔐 Generating secure credentials...")
    print(f"✅ API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"✅ Webhook Secret: {webhook_secret[:8]}...{webhook_secret[-4:]}")
    
    # Configuration data
    config = {
        "make_com_integration": {
            "enabled": True,
            "api_key": api_key,
            "webhook_secret": webhook_secret,
            "webhook_url": "https://your-domain.com/api/method/assistant_crm.api.make_com_webhook.send_message_to_make_com",
            "rate_limit": 1000,  # requests per hour
            "timeout": 30,  # seconds
            "created_at": datetime.now().isoformat(),
            "version": "1.0"
        }
    }
    
    # Save configuration to file
    config_file = "make_com_integration_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n💾 Configuration saved to: {config_file}")
    
    return config


def display_integration_details(config):
    """Display integration details for Make.com setup"""
    
    make_com_config = config["make_com_integration"]
    
    print("\n" + "=" * 60)
    print("📋 MAKE.COM INTEGRATION CONFIGURATION")
    print("=" * 60)
    
    print("\n🔗 WEBHOOK ENDPOINT:")
    print("   https://your-domain.com/api/omnichannel/webhook/make-com")
    print("   (Replace 'your-domain.com' with your actual domain)")
    
    print("\n🔑 AUTHENTICATION CREDENTIALS:")
    print(f"   API Key: {make_com_config['api_key']}")
    print(f"   Webhook Secret: {make_com_config['webhook_secret']}")
    
    print("\n📋 REQUIRED HEADERS FOR MAKE.COM:")
    print("   Content-Type: application/json")
    print(f"   X-API-Key: {make_com_config['api_key']}")
    print("   X-Webhook-Signature: sha256=<calculated_signature> (optional)")
    
    print("\n⚙️ CONFIGURATION SETTINGS:")
    print(f"   Rate Limit: {make_com_config['rate_limit']} requests/hour")
    print(f"   Timeout: {make_com_config['timeout']} seconds")
    print(f"   Integration Enabled: {'Yes' if make_com_config['enabled'] else 'No'}")
    
    print("\n🔧 MAKE.COM SCENARIO SETUP STEPS:")
    print("   1. Create a new scenario in Make.com")
    print("   2. Add a webhook trigger for your social media platform")
    print("   3. Add an HTTP module to send data to WCFCB")
    print("   4. Configure the HTTP module with:")
    print("      - URL: https://your-domain.com/api/omnichannel/webhook/make-com")
    print("      - Method: POST")
    print(f"      - Headers: X-API-Key: {make_com_config['api_key']}")
    print("      - Content-Type: application/json")
    print("   5. Map the social media data to the required format (see documentation)")
    print("   6. Test the scenario with a sample message")
    
    print("\n📄 SAMPLE REQUEST FORMAT:")
    sample_request = {
        "platform": "facebook",
        "event_type": "message",
        "timestamp": "2025-01-10T12:00:00Z",
        "data": {
            "message": {
                "id": "message_123",
                "content": "Hello Anna, I need help with my pension",
                "type": "text"
            },
            "sender": {
                "id": "user_456",
                "name": "John Doe"
            },
            "conversation": {
                "channel_id": "channel_789"
            }
        }
    }
    
    print(json.dumps(sample_request, indent=2))
    
    print("\n🧪 TESTING THE INTEGRATION:")
    print("   1. Use curl or Postman to test the webhook endpoint:")
    print("   2. Send a GET request to check status:")
    print("      curl -X GET https://your-domain.com/api/omnichannel/webhook/make-com")
    print("   3. Send a POST request with sample data:")
    print(f"      curl -X POST https://your-domain.com/api/omnichannel/webhook/make-com \\")
    print("           -H 'Content-Type: application/json' \\")
    print(f"           -H 'X-API-Key: {make_com_config['api_key']}' \\")
    print("           -d '<sample_json_data>'")
    
    print("\n📊 MONITORING:")
    print("   - Check webhook activity logs in WCFCB Assistant CRM")
    print("   - Monitor error logs for any issues")
    print("   - Review response times and success rates")
    
    print("\n🔒 SECURITY NOTES:")
    print("   - Keep API key and webhook secret secure")
    print("   - Use HTTPS for all communications")
    print("   - Consider IP whitelisting for additional security")
    print("   - Rotate credentials periodically")
    
    print("\n✅ NEXT STEPS:")
    print("   1. Replace 'your-domain.com' with your actual WCFCB domain")
    print("   2. Update Social Media Settings in WCFCB with these credentials")
    print("   3. Configure your Make.com scenarios")
    print("   4. Test the integration thoroughly")
    print("   5. Monitor the webhook activity logs")


def create_frappe_migration_script(config):
    """Create a Frappe migration script to update the database"""
    
    make_com_config = config["make_com_integration"]
    
    migration_script = f'''#!/usr/bin/env python3
"""
Frappe Migration Script for Make.com Integration
===============================================

Run this script in Frappe console to update the Social Media Settings.

Usage in Frappe console:
    exec(open('update_social_media_settings.py').read())
"""

import frappe

def update_social_media_settings():
    """Update Social Media Settings with Make.com configuration"""
    try:
        # Get or create Social Media Settings
        if frappe.db.exists("Social Media Settings", "Social Media Settings"):
            settings = frappe.get_doc("Social Media Settings", "Social Media Settings")
            print("📋 Found existing Social Media Settings")
        else:
            settings = frappe.get_doc({{
                "doctype": "Social Media Settings",
                "name": "Social Media Settings"
            }})
            print("📋 Creating new Social Media Settings")
        
        # Update Make.com configuration
        settings.make_com_enabled = 1
        settings.make_com_api_key = "{make_com_config['api_key']}"
        settings.make_com_webhook_secret = "{make_com_config['webhook_secret']}"
        settings.make_com_webhook_url = "{make_com_config['webhook_url']}"
        settings.make_com_rate_limit = {make_com_config['rate_limit']}
        settings.make_com_timeout = {make_com_config['timeout']}
        
        # Save settings
        if settings.is_new():
            settings.insert(ignore_permissions=True)
            print("✅ Created new Social Media Settings with Make.com configuration")
        else:
            settings.save(ignore_permissions=True)
            print("✅ Updated existing Social Media Settings with Make.com configuration")
        
        frappe.db.commit()
        print("💾 Changes committed to database")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating settings: {{str(e)}}")
        frappe.log_error(f"Make.com settings update error: {{str(e)}}", "Make.com Setup")
        return False

# Run the update
if __name__ == "__main__":
    update_social_media_settings()
'''
    
    script_file = "update_social_media_settings.py"
    with open(script_file, 'w') as f:
        f.write(migration_script)
    
    print(f"\n📝 Frappe migration script created: {script_file}")
    print("   Run this script in Frappe console to update the database")


def create_test_script(config):
    """Create a test script for the integration"""
    
    make_com_config = config["make_com_integration"]
    
    test_script = f'''#!/usr/bin/env python3
"""
Make.com Integration Test Script
===============================

Test the Make.com webhook integration.
"""

import requests
import json

# Configuration
WEBHOOK_URL = "https://your-domain.com/api/omnichannel/webhook/make-com"
API_KEY = "{make_com_config['api_key']}"

def test_webhook_status():
    """Test webhook status endpoint"""
    print("🧪 Testing webhook status...")
    
    try:
        response = requests.get(WEBHOOK_URL, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Webhook is active and responding")
            print(f"   Response: {{data.get('message', 'No message')}}")
        else:
            print(f"❌ Webhook returned status {{response.status_code}}")
            
    except Exception as e:
        print(f"❌ Error testing webhook: {{str(e)}}")

def test_webhook_message():
    """Test webhook message processing"""
    print("\\n🧪 Testing webhook message processing...")
    
    sample_data = {{
        "platform": "facebook",
        "event_type": "message",
        "timestamp": "2025-01-10T12:00:00Z",
        "data": {{
            "message": {{
                "id": "test_123",
                "content": "Hello Anna, this is a test message",
                "type": "text"
            }},
            "sender": {{
                "id": "test_user",
                "name": "Test User"
            }},
            "conversation": {{
                "channel_id": "test_channel"
            }}
        }}
    }}
    
    headers = {{
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }}
    
    try:
        response = requests.post(WEBHOOK_URL, json=sample_data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Message processed successfully")
            print(f"   Response: {{data.get('message', 'No message')}}")
            if data.get('response'):
                print(f"   Anna's Reply: {{data['response'].get('reply', 'No reply')}}")
        else:
            print(f"❌ Message processing failed with status {{response.status_code}}")
            print(f"   Response: {{response.text}}")
            
    except Exception as e:
        print(f"❌ Error testing message processing: {{str(e)}}")

if __name__ == "__main__":
    print("🚀 Make.com Integration Test")
    print("=" * 40)
    print("⚠️  Make sure to replace 'your-domain.com' with your actual domain")
    print()
    
    test_webhook_status()
    test_webhook_message()
'''
    
    test_file = "test_make_com_webhook.py"
    with open(test_file, 'w') as f:
        f.write(test_script)
    
    print(f"\n🧪 Test script created: {test_file}")
    print("   Use this script to test the webhook integration")


def main():
    """Main configuration function"""
    
    # Create configuration
    config = create_integration_config()
    
    # Display integration details
    display_integration_details(config)
    
    # Create additional scripts
    create_frappe_migration_script(config)
    create_test_script(config)
    
    print("\n" + "=" * 60)
    print("🎉 MAKE.COM INTEGRATION SETUP COMPLETE!")
    print("=" * 60)
    print("\nFiles created:")
    print("   📄 make_com_integration_config.json - Configuration file")
    print("   📝 update_social_media_settings.py - Frappe migration script")
    print("   🧪 test_make_com_webhook.py - Test script")
    print("\nNext steps:")
    print("   1. Update your domain in the webhook URL")
    print("   2. Run the migration script in Frappe console")
    print("   3. Configure your Make.com scenarios")
    print("   4. Test the integration")
    print("\n✨ Your Make.com integration is ready to use!")


if __name__ == "__main__":
    main()
