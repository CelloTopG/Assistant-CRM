# WCFCB Assistant CRM - ngrok Webhook Configuration

## Overview
This document provides the configuration details for testing Assistant CRM webhook integrations using an ngrok tunnel in a development environment.

## Configuration Details

### ngrok Tunnel URL
```
https://a9d168a9f208.ngrok-free.app
```

### Webhook Endpoints

#### Omnichannel Webhook Endpoint
- **URL**: `https://a9d168a9f208.ngrok-free.app/api/method/assistant_crm.api.telegram_webhook.telegram_webhook`
- **Methods**: POST
- **Status**: ✅ Active and responding

#### Assistant CRM Application
- **URL**: `https://a9d168a9f208.ngrok-free.app/app/assistant-crm`
- **Purpose**: Access the Assistant CRM interface for testing

## Webhook Integration Setup

### Webhook Configuration
1. **Webhook URL**: `https://a9d168a9f208.ngrok-free.app/api/method/assistant_crm.api.telegram_webhook.telegram_webhook`
2. **Method**: POST
3. **Content-Type**: application/json

### Required Headers
```
Content-Type: application/json
X-API-Key: [Your API Key from Social Media Settings]
User-Agent: WCFCB-Assistant-CRM/1.0
```

### Sample Webhook Payload
```json
{
  "platform": "telegram",
  "event_type": "message",
  "data": {
    "message": {
      "id": "msg_123",
      "content": "Hello Anna!",
      "type": "text"
    },
    "sender": {
      "id": "user_123",
      "name": "Test User"
    },
    "conversation": {
      "id": "conv_123",
      "channel_id": "channel_123"
    }
  },
  "timestamp": "2025-08-14T11:00:00Z"
}
```

### Expected Response
```json
{
  "success": true,
  "message": "Webhook processed successfully",
  "response": {
    "reply": "Anna's response to the message"
  },
  "conversation_id": "conv_123",
  "timestamp": "2025-08-14T11:00:00Z",
  "platform": "telegram",
  "event_type": "message"
}
```

## Testing Instructions

### 1. Test Webhook Status (GET Request)
```bash
curl -H "ngrok-skip-browser-warning: true" \
     -H "User-Agent: WCFCB-Assistant-CRM/1.0" \
     "https://a9d168a9f208.ngrok-free.app/api/method/assistant_crm.api.telegram_webhook.telegram_webhook"
```

**Expected Response**: Status 200 with success message

### 2. Test Webhook Processing (POST Request)
```bash
curl -X POST \
     -H "Content-Type: application/json" \
     -H "X-API-Key: [YOUR_API_KEY]" \
     -H "ngrok-skip-browser-warning: true" \
     -d '{
       "platform": "telegram",
       "event_type": "message",
       "data": {
         "message": {
           "content": "Hello Anna!",
           "type": "text"
         },
         "sender": {
           "id": "test_user",
           "name": "Test User"
         }
       }
     }' \
     "https://a9d168a9f208.ngrok-free.app/api/method/assistant_crm.api.telegram_webhook.telegram_webhook"
```

### 3. Access Assistant CRM Interface
Open in browser: `https://a9d168a9f208.ngrok-free.app/app/assistant-crm`

## Supported Platforms

The webhook supports the following social media platforms:
- Facebook Messenger
- Instagram Direct Messages
- Telegram
- WhatsApp
- Twitter/X
- LinkedIn

## Event Types

Supported event types:
- `message` - Incoming messages from users
- `status_update` - Message delivery/read receipts
- `user_action` - User typing indicators, online/offline status

## Security Features

1. **API Key Authentication**: X-API-Key header validation
2. **Webhook Signature Verification**: Optional HMAC-SHA256 signature validation
3. **Rate Limiting**: Configurable requests per hour limit
4. **Request Validation**: Comprehensive payload structure validation

## Monitoring and Logging

- All webhook activity is logged in the `Webhook Activity Log` DocType
- Successful and failed requests are tracked
- Response times and error details are recorded
- Real-time monitoring available through the Assistant CRM dashboard

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure Frappe server is running on port 8000
   - Verify ngrok tunnel is active

2. **Authentication Failed**
   - Check X-API-Key header is included
   - Verify API key matches Social Media Settings

3. **Invalid Payload**
   - Ensure Content-Type is application/json
   - Validate payload structure matches expected format

### Debug Commands

```bash
# Check webhook status
curl -I "https://a9d168a9f208.ngrok-free.app/api/method/assistant_crm.api.telegram_webhook.telegram_webhook"

# Test with verbose output
curl -v "https://a9d168a9f208.ngrok-free.app/api/method/assistant_crm.api.telegram_webhook.telegram_webhook"
```

## Next Steps

1. Configure your messaging channels (e.g. Telegram, WhatsApp, Facebook) with the provided ngrok webhook URL(s)
2. Test message flow from each channel through Assistant CRM
3. Monitor webhook activity logs for successful processing
4. Verify Anna's responses are being sent back to the originating channel

---

**Last Updated**: August 14, 2025  
**Status**: ✅ Active and Ready for Testing  
**Contact**: WCFCB Development Team
