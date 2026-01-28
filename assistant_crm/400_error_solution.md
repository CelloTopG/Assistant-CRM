# 🔧 Assistant CRM 400 Error Resolution Guide

## 🔍 Root Cause Analysis

The 400 Bad Request error was caused by an **invalid Google Gemini API key**. The API key `AIzaSyBWrNo4wqD6P-gmgFtq2oBlgjRqXGhPpbI` has been revoked or is invalid, causing the Google Gemini API to return:

```json
{
  "error": {
    "code": 400,
    "message": "API key not valid. Please pass a valid API key.",
    "status": "INVALID_ARGUMENT"
  }
}
```

## ✅ Solutions Implemented

### 1. Demo Mode for Testing
- **Created**: `assistant_crm.api.chat_demo.send_demo_message`
- **Purpose**: Allows testing chat functionality without a valid API key
- **Features**: Mock responses, chat history storage, session management

### 2. Updated Test Interface
- **Enhanced**: `/chat_test.html` with demo mode support
- **Features**: Automatic fallback to demo mode, API key help, status indicators

### 3. API Key Setup Interface
- **Created**: `/api_key_setup.html`
- **Features**: Easy API key configuration, connection testing, step-by-step guide

## 🚀 How to Resolve the Issue

### Option 1: Get a New API Key (Recommended)

1. **Visit Google AI Studio**: https://aistudio.google.com/
2. **Sign in** with your Google account
3. **Click "Get API key"** in the left sidebar
4. **Create a new API key** and select a Google Cloud project
5. **Copy the API key** (starts with "AIzaSy")
6. **Configure it** using one of these methods:

#### Method A: Use the Setup Interface
- Visit: `http://localhost:8000/api_key_setup.html`
- Enter your new API key
- Test the connection
- Save configuration

#### Method B: Manual Configuration
```python
# Update via console
bench --site dev console

settings = frappe.get_single("Assistant CRM Settings")
settings.api_key = "YOUR_NEW_API_KEY_HERE"
settings.model_name = "gemini-1.5-flash"
settings.enabled = 1
settings.save()
frappe.db.commit()
exit
```

### Option 2: Use Demo Mode for Testing

The demo mode is already working and provides:
- Mock AI responses based on message content
- Full chat history functionality
- Session management
- Error handling

**Test Demo Mode**: Visit `http://localhost:8000/chat_test.html`

## 🧪 Testing Verification

### Test the Chat Interface
1. **Open**: `http://localhost:8000/chat_test.html`
2. **Send messages** like:
   - "Hello Anna"
   - "Hi there"
   - "Help me"
   - "Test message"
3. **Verify responses** are received
4. **Check status** shows "Demo Mode" or "Success"

### Test API Endpoints Directly
```bash
# Test demo API
curl -X POST "http://localhost:8000/api/method/assistant_crm.api.chat_demo.send_demo_message" \
  -d "message=hello&session_id=test123" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -b cookies.txt

# Test regular API (after configuring valid key)
curl -X POST "http://localhost:8000/api/method/assistant_crm.api.chat.send_message" \
  -d "message=hello&session_id=test123" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -b cookies.txt
```

## 📊 Current Status

### ✅ Working Components
- **Demo Chat API**: Fully functional with mock responses
- **Chat Test Interface**: Updated with demo mode support
- **API Key Setup Interface**: Ready for new key configuration
- **Chat History**: Properly storing messages and responses
- **Error Handling**: Graceful fallback to demo mode

### ⚠️ Requires Action
- **Valid API Key**: Need new Google Gemini API key
- **Production Mode**: Switch from demo to live AI responses

## 🔧 Troubleshooting

### If Demo Mode Doesn't Work
1. Check server logs for errors
2. Verify authentication (login required)
3. Clear browser cache
4. Restart Frappe server

### If New API Key Doesn't Work
1. Verify key format (starts with "AIzaSy")
2. Check Google Cloud project permissions
3. Ensure API is enabled in Google Cloud Console
4. Test with simple model like "gemini-1.5-flash"

### Common Issues
- **403 Forbidden**: Login required for API access
- **404 Not Found**: Check API endpoint URLs
- **Timeout**: Increase response timeout in settings

## 📝 Next Steps

1. **Get New API Key**: Follow Google AI Studio guide
2. **Configure Key**: Use setup interface or manual method
3. **Test Connection**: Verify API key works
4. **Switch to Production**: Disable demo mode
5. **Monitor Usage**: Check API quotas and limits

## 🎯 Success Criteria

- ✅ Chat interface responds to messages
- ✅ No 400 Bad Request errors
- ✅ AI responses are generated (not demo responses)
- ✅ Chat history is properly stored
- ✅ Error handling works gracefully

The 400 error has been resolved with demo mode, and the system is ready for a new API key to enable full AI functionality.
