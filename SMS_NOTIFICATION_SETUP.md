# SMS Alert Notification for Conversation Assignment

## Overview

This implementation adds SMS alerts to agents when new conversations are assigned to them in the Assistant CRM system. The solution uses the native ERPNext Notification system combined with custom SMS handling.

## What Was Implemented

### 1. **Notification Configuration** (`install.py`)

Added a new notification definition called **"Conversation Assigned to Agent"** that:
- Triggers when the `assigned_agent` field changes on a Unified Inbox Conversation
- Sends both System Notification (UI alert) and SMS
- Includes conversation details: customer name, platform, priority, and subject

**Notification Details:**
```python
{
    "name": "Conversation Assigned to Agent",
    "subject": "📱 New Conversation Assigned: {{ doc.customer_name }}",
    "document_type": "Unified Inbox Conversation",
    "event": "Value Change",
    "value_changed": "assigned_agent",
    "condition": "doc.assigned_agent",
    "message": "System notification with conversation details",
    ...
}
```

### 2. **DocType Hooks** (`unified_inbox_conversation.py`)

Added two new methods to the Unified Inbox Conversation DocType:

#### `after_save()` Method
- Detects when `assigned_agent` field is changed
- Calls `send_assignment_notification()` to create notification log

#### `send_assignment_notification()` Method
- Creates a Notification Log document with:
  - `for_user`: The assigned agent
  - `document_type`: Unified Inbox Conversation
  - `document_name`: The conversation ID
  - `notification_name`: "Conversation Assigned to Agent"
  
This log entry triggers the notification system automatically.

### 3. **SMS Handler Updates** (`notification_hooks.py`)

Enhanced the SMS notification system to handle conversation assignments:

#### Updated `SMS_ENABLED_NOTIFICATIONS` Dictionary
Added SMS template for the new notification:
```python
"Conversation Assigned to Agent": "📱 WCFCB Alert: New conversation from {customer} ({platform}) assigned to you. Priority: {priority}. Check your inbox."
```

#### Enhanced `send_sms_for_notification()` Function
Added logic to:
1. Detect "Conversation Assigned to Agent" notifications
2. Extract the assigned agent's phone number from User profile
3. Format SMS with conversation details
4. Send via configured SMS gateway

## How It Works

### Workflow

```
1. Conversation assigned to agent
   ↓
2. after_save hook triggered
   ↓
3. send_assignment_notification() creates Notification Log
   ↓
4. Frappe automatically detects Notification Log creation
   ↓
5. notification_hooks.handle_notification_log_after_insert() called
   ↓
6. SMS template matched and message formatted
   ↓
7. SMSService.send_message() sends SMS to agent
```

### Configuration Flow

```
Unified Inbox Conversation (DocType)
├── Field: assigned_agent (User link)
│
after_save Hook
├── Detects: has_value_changed("assigned_agent")
├── Creates: Notification Log
│
Notification System (Native ERPNext)
├── Notification: "Conversation Assigned to Agent"
├── Event: Value Change on assigned_agent
├── Recipients: via assigned_agent field
│
notification_hooks.py
├── Detects: Conversation Assigned to Agent notification
├── Gets: Agent's mobile_no from User profile
├── Sends: SMS via SMSService
```

## Prerequisites

### Required Setup

1. **User Mobile Numbers**
   - All agents must have `mobile_no` configured in their User profile
   - SMS cannot be sent without this

2. **SMS Gateway Configuration**
   - SMSService must be properly configured with credentials
   - The service is in: `assistant_crm/services/sms_service.py`

3. **Notification DocType**
   - Must exist in ERPNext (standard, should be available)
   - Enables/disables individual notifications

### Optional Enhancements

- **SMS Request Log**: Monitor sent SMS via SMS Request Log (if configured)
- **Error Handling**: All errors logged to "Notification SMS Hook Failed" error log

## Testing

### Manual Test

1. **Setup:**
   ```bash
   cd /workspace/development/frappe-bench
   python assistant_crm/test_conversation_sms_alert.py
   ```

2. **Steps:**
   - Script verifies notification is registered
   - Script checks SMSService is available
   - Optionally creates test conversation
   - Assigns it to an agent

3. **Verification:**
   - Check SMS Request Log for sent messages
   - Agent should receive SMS on their configured number
   - Check notifications window (UI) for System Notification

### API Trigger

```python
# Create conversation
conv = frappe.get_doc({
    "doctype": "Unified Inbox Conversation",
    "platform": "WhatsApp",
    "customer_name": "John Doe",
    "customer_phone": "+260123456789",
    "priority": "High"
})
conv.insert()

# Assign to agent (triggers SMS)
conv.assigned_agent = "agent@example.com"
conv.save()  # SMS sent here
```

## SMS Message Template

The SMS sent to the agent contains:

```
📱 WCFCB Alert: New conversation from [Customer Name] ([Platform]) 
assigned to you. Priority: [Priority]. Check your inbox.
```

**Example:**
```
📱 WCFCB Alert: New conversation from John Doe (WhatsApp) 
assigned to you. Priority: High. Check your inbox.
```

## Configuration Files Changed

### 1. `/assistant_crm/install.py`
- Added "Conversation Assigned to Agent" notification definition
- Integrated with existing notification setup flow

### 2. `/assistant_crm/notification_hooks.py`
- Added SMS template mapping
- Enhanced `send_sms_for_notification()` to handle new notification type
- Added agent phone lookup from User profile

### 3. `/assistant_crm/doctype/unified_inbox_conversation/unified_inbox_conversation.py`
- Added `after_save()` method
- Added `send_assignment_notification()` method

## System Integration Points

1. **Frappe Notification System**
   - Uses native "Value Change" event detection
   - Automatically matches conditions and sends notifications

2. **SMSService Integration**
   - Leverages existing SMS gateway
   - Reuses authentication and configuration
   - Maintains logging and error handling

3. **User Profile**
   - Reads `mobile_no` field from User doctype
   - No new fields required

## Error Handling

Errors are logged to:
- `Notification SMS Hook Failed` - Main error log
- `Unified Inbox - Assignment SMS` - DocType-specific errors

Monitor with:
```bash
bench --site wcfcb show-log
```

## Future Enhancements

1. **SMS Customization**
   - Make template configurable per role/branch
   - Support multilingual messages
   - Add customer context (CBS number, issue type, etc.)

2. **Delivery Tracking**
   - Log SMS delivery status (sent, delivered, failed)
   - Retry failed messages
   - Track SMS costs per agent

3. **Throttling**
   - Prevent spam if multiple assignments happen quickly
   - Batch notifications within a time window
   - Per-agent rate limiting

4. **Preferences**
   - Agent opt-in/opt-out for SMS alerts
   - Time-based quieting (do not disturb windows)
   - Alert severity filtering

## Troubleshooting

### SMS Not Sending

1. **Check agent has mobile_no:**
   ```python
   frappe.db.get_value("User", "agent@example.com", "mobile_no")
   ```

2. **Check notification is enabled:**
   - Go to Notification list
   - Find "Conversation Assigned to Agent"
   - Verify "enabled" is checked

3. **Check SMS gateway credentials:**
   - Review SMSService configuration
   - Test with: `SMSService().send_message("+260123456789", "test")`

4. **Check logs:**
   - Look for "Notification SMS Hook Failed" errors
   - Check system logs for SMSService errors

### Notification Not Triggering

1. **Verify doctype hook:**
   - Check if `after_save` is being called:
   ```python
   print("DEBUG: after_save called")
   ```

2. **Verify notification log creation:**
   - Check Notification Log list for recent entries
   - Filter by document_type: "Unified Inbox Conversation"

3. **Verify notification condition:**
   - Condition `doc.assigned_agent` must evaluate to True
   - assigned_agent must have a value (not empty/None)

## Support

For issues or questions:
1. Check error logs: `bench --site wcfcb show-log`
2. Review test script output: `test_conversation_sms_alert.py`
3. Verify all prerequisites are met
4. Check SMSService configuration
