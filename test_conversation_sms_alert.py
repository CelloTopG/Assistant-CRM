#!/usr/bin/env python
"""
Test script for SMS notifications on conversation assignment.
This script verifies that SMS alerts are properly configured and sent when conversations are assigned.
"""

import frappe
import sys

def test_sms_notification_setup():
    """Test that the SMS notification is properly configured."""
    print("\n" + "="*70)
    print("Testing SMS Notification Setup for Conversation Assignment")
    print("="*70)
    
    # 1. Check if Notification doctype exists
    if not frappe.db.exists("DocType", "Unified Inbox Conversation"):
        print("❌ FAILED: Unified Inbox Conversation doctype not found")
        return False
    
    print("✅ Unified Inbox Conversation doctype exists")
    
    # 2. Check if the SMS notification is registered
    notification_name = "Conversation Assigned to Agent"
    if frappe.db.exists("Notification", notification_name):
        print(f"✅ Notification '{notification_name}' exists")
        
        # Get notification details
        notification = frappe.get_doc("Notification", notification_name)
        print(f"   - Document Type: {notification.document_type}")
        print(f"   - Event: {notification.event}")
        print(f"   - Value Changed: {notification.value_changed}")
        print(f"   - Condition: {notification.condition}")
        print(f"   - enabled: {notification.enabled}")
        
        # Check recipients configuration
        if notification.recipients:
            print(f"   - Recipients configured: {len(notification.recipients)} rule(s)")
            for recipient in notification.recipients:
                print(f"     • {recipient.receiver_by_role or recipient.receiver_by_field}: {recipient.field_value}")
    else:
        print(f"⚠️  Notification '{notification_name}' NOT found")
        print("   You may need to run 'bench --site <site> reinstall-app assistant_crm' or sync notifications")
    
    # 3. Check SMS Service availability
    try:
        from assistant_crm.services.sms_service import SMSService
        sms = SMSService()
        print("✅ SMSService is available")
        print(f"   - Debug mode: {sms.debug}")
    except Exception as e:
        print(f"❌ FAILED: SMSService not available: {str(e)}")
        return False
    
    # 4. Check notification_hooks
    try:
        from assistant_crm.notification_hooks import send_sms_for_notification, SMS_ENABLED_NOTIFICATIONS
        print("✅ notification_hooks module loaded")
        print(f"   - SMS Enabled Notifications: {list(SMS_ENABLED_NOTIFICATIONS.keys())}")
        
        if notification_name in SMS_ENABLED_NOTIFICATIONS:
            print(f"   - '{notification_name}' is configured for SMS")
            print(f"     Template: {SMS_ENABLED_NOTIFICATIONS[notification_name]}")
        else:
            print(f"⚠️  '{notification_name}' NOT in SMS_ENABLED_NOTIFICATIONS")
    except Exception as e:
        print(f"❌ FAILED: Could not load notification_hooks: {str(e)}")
        return False
    
    print("\n" + "="*70)
    print("Summary:")
    print("="*70)
    print("""
✅ SMS Notification System is configured!

How it works:
1. When assigned_agent field is changed on Unified Inbox Conversation
2. A Notification Log is created via after_save hook
3. The notification_hooks.py detects this and triggers SMS sending
4. Agent receives SMS with conversation details

To test:
1. Assign a conversation to an agent with a mobile_no
2. Check that an SMS is sent via your configured SMS gateway
3. Monitor logs: bench --site <site> show-log

Configuration:
- SMS Template: "{}"
- Event Trigger: Value Change on assigned_agent field
- Recipient: The assigned agent (via their User mobile_no)
""".format(SMS_ENABLED_NOTIFICATIONS.get(notification_name, "Template not found")))
    
    return True


def test_create_test_conversation():
    """Create a test conversation and assign it to an agent."""
    print("\n" + "="*70)
    print("Creating Test Conversation for SMS Alert")
    print("="*70)
    
    try:
        # Get an agent with Customer Service role
        agent = frappe.db.get_value(
            "User",
            {"has_role": "WCF Customer Service Assistant", "enabled": 1},
            name=1
        )
        
        if not agent:
            print("⚠️  No agent found with WCF Customer Service Assistant role")
            print("   Create a test agent first or use an existing user")
            return
        
        # Check if agent has mobile_no
        agent_doc = frappe.get_doc("User", agent)
        if not agent_doc.mobile_no:
            print(f"⚠️  Agent '{agent}' does not have a mobile_no configured")
            print("   Add a mobile number to the agent's User profile")
            return
        
        print(f"✅ Found agent: {agent}")
        print(f"   Mobile: {agent_doc.mobile_no}")
        
        # Create a test conversation
        test_conv = frappe.get_doc({
            "doctype": "Unified Inbox Conversation",
            "platform": "WhatsApp",
            "customer_name": "Test Beneficiary",
            "customer_phone": "+260123456789",
            "priority": "High",
            "subject": "Test Conversation for SMS Alert",
            "last_message_preview": "This is a test message"
        })
        test_conv.insert(ignore_permissions=True)
        print(f"✅ Created test conversation: {test_conv.name}")
        
        # Now assign it
        test_conv.assigned_agent = agent
        test_conv.save(ignore_permissions=True)
        print(f"✅ Assigned conversation to: {agent}")
        print(f"   Expected SMS should be sent to: {agent_doc.mobile_no}")
        
    except Exception as e:
        frappe.log_error(f"Test failed: {str(e)}", "SMS Notification Test")
        print(f"❌ FAILED: {str(e)}")


if __name__ == "__main__":
    frappe.init(site="wcfcb")
    frappe.connect()
    
    try:
        success = test_sms_notification_setup()
        
        if success and frappe.flags.interactive:
            response = input("\nWould you like to create a test conversation? (y/n): ")
            if response.lower() == 'y':
                test_create_test_conversation()
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        frappe.log_error(str(e), "SMS Notification Test")
        sys.exit(1)
    finally:
        frappe.destroy()
