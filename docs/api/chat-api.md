# Chat API Reference

The Chat API is the core interface for all conversational interactions in the WCFCB Assistant CRM system. This document provides comprehensive documentation for all chat-related endpoints.

## Base URL

```
https://your-domain.com/api/method/assistant_crm.api.chat
```

## Authentication

The Chat API supports multiple authentication modes:
- **Guest Access**: Limited functionality for unauthenticated users
- **Session-based**: Full functionality for authenticated users
- **API Key**: For programmatic access (admin only)

## Core Endpoints

### 1. Send Message

Send a message to Anna and receive an AI-generated response.

#### Endpoint
```http
POST /api/method/assistant_crm.api.chat.send_message
```

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | string | Yes | User's message content |
| `session_id` | string | No | Chat session identifier |
| `user_id` | string | No | User identifier for authenticated sessions |
| `channel` | string | No | Communication channel (web, whatsapp, telegram, etc.) |
| `metadata` | object | No | Additional context information |

#### Request Example

```json
{
  "message": "What is the status of my claim?",
  "session_id": "sess_123456789",
  "user_id": "user_wcfcb_001",
  "channel": "web",
  "metadata": {
    "user_agent": "Mozilla/5.0...",
    "ip_address": "192.168.1.1",
    "language": "en"
  }
}
```

#### Response Format

```json
{
  "success": true,
  "data": {
    "response": "Hi! I'd be happy to help you check your claim status. To provide accurate information, I'll need to verify your identity first. Could you please provide your National Registration Card (NRC) number and full name?",
    "session_id": "sess_123456789",
    "message_id": "msg_987654321",
    "intent": "claim_status_inquiry",
    "requires_authentication": true,
    "suggested_actions": [
      {
        "type": "quick_reply",
        "text": "Provide NRC",
        "payload": "auth_nrc"
      }
    ],
    "metadata": {
      "response_time": 1.2,
      "ai_confidence": 0.95,
      "persona": "beneficiary",
      "escalation_suggested": false
    }
  }
}
```

#### Error Response

```json
{
  "success": false,
  "error": {
    "code": "INVALID_MESSAGE",
    "message": "Message content is required",
    "details": {
      "field": "message",
      "received": null
    }
  }
}
```

### 2. Get Chat History

Retrieve conversation history for a specific session or user.

#### Endpoint
```http
GET /api/method/assistant_crm.api.chat.get_chat_history
```

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | No | Specific session ID |
| `user_id` | string | No | User ID for all sessions |
| `limit` | integer | No | Number of messages to retrieve (default: 50) |
| `offset` | integer | No | Pagination offset (default: 0) |
| `start_date` | string | No | Filter from date (ISO format) |
| `end_date` | string | No | Filter to date (ISO format) |

#### Response Example

```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "id": "msg_001",
        "session_id": "sess_123456789",
        "user_message": "Hello",
        "ai_response": "Hi! I'm Anna, how can I help? 😊",
        "timestamp": "2025-08-15T10:30:00Z",
        "intent": "greeting",
        "channel": "web"
      }
    ],
    "total_count": 25,
    "has_more": true,
    "session_info": {
      "session_id": "sess_123456789",
      "user_id": "user_wcfcb_001",
      "created_at": "2025-08-15T10:30:00Z",
      "last_activity": "2025-08-15T11:45:00Z",
      "message_count": 25
    }
  }
}
```

### 3. Get User Sessions

Retrieve all chat sessions for a specific user.

#### Endpoint
```http
GET /api/method/assistant_crm.api.chat.get_user_sessions
```

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | User identifier |
| `limit` | integer | No | Number of sessions (default: 20) |
| `status` | string | No | Session status filter (active, completed, escalated) |

#### Response Example

```json
{
  "success": true,
  "data": {
    "sessions": [
      {
        "session_id": "sess_123456789",
        "created_at": "2025-08-15T10:30:00Z",
        "last_activity": "2025-08-15T11:45:00Z",
        "message_count": 25,
        "status": "active",
        "channel": "web",
        "summary": "Claim status inquiry and document upload"
      }
    ],
    "total_count": 5
  }
}
```

### 4. Get Chat Status

Check the current status and health of the chat system.

#### Endpoint
```http
GET /api/method/assistant_crm.api.chat.get_chat_status
```

#### Response Example

```json
{
  "success": true,
  "data": {
    "status": "operational",
    "ai_service": {
      "provider": "google_gemini",
      "model": "gemini-1.5-pro",
      "status": "connected",
      "response_time": 0.8
    },
    "database": {
      "status": "connected",
      "response_time": 0.05
    },
    "cache": {
      "status": "connected",
      "hit_rate": 0.85
    },
    "active_sessions": 42,
    "messages_today": 1247,
    "average_response_time": 1.2
  }
}
```

## Advanced Features

### 1. File Upload Support

The chat API supports file uploads for document submission.

#### Endpoint
```http
POST /api/method/assistant_crm.api.chat.upload_file
```

#### Request (Multipart Form Data)

```
Content-Type: multipart/form-data

file: [binary file data]
session_id: sess_123456789
file_type: claim_document
description: Medical certificate for claim
```

#### Response Example

```json
{
  "success": true,
  "data": {
    "file_id": "file_789012345",
    "filename": "medical_cert.pdf",
    "file_size": 245760,
    "file_type": "application/pdf",
    "upload_status": "completed",
    "validation_status": "pending",
    "download_url": "/api/method/assistant_crm.api.files.download?file_id=file_789012345"
  }
}
```

### 2. Real-time Typing Indicators

WebSocket endpoint for real-time typing indicators.

#### WebSocket Connection
```javascript
const socket = io('/assistant_crm');

// Join conversation room
socket.emit('join_conversation', {
  session_id: 'sess_123456789',
  user_id: 'user_wcfcb_001'
});

// Send typing indicator
socket.emit('typing_start', {
  session_id: 'sess_123456789'
});

// Stop typing indicator
socket.emit('typing_stop', {
  session_id: 'sess_123456789'
});
```

### 3. Quick Replies and Suggested Actions

The API supports structured responses with quick reply buttons.

#### Quick Reply Format

```json
{
  "suggested_actions": [
    {
      "type": "quick_reply",
      "text": "Check Claim Status",
      "payload": "claim_status",
      "icon": "📋"
    },
    {
      "type": "quick_reply",
      "text": "Submit New Claim",
      "payload": "submit_claim",
      "icon": "📝"
    },
    {
      "type": "url",
      "text": "Download Form",
      "url": "https://wcfcb.com/forms/claim-form.pdf",
      "icon": "📄"
    }
  ]
}
```

## Error Handling

### Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `INVALID_MESSAGE` | Message content is missing or invalid | 400 |
| `SESSION_NOT_FOUND` | Session ID not found | 404 |
| `AUTHENTICATION_REQUIRED` | User authentication required | 401 |
| `RATE_LIMIT_EXCEEDED` | Too many requests | 429 |
| `AI_SERVICE_UNAVAILABLE` | AI service is down | 503 |
| `INTERNAL_ERROR` | Unexpected server error | 500 |

### Rate Limiting

The API implements rate limiting to prevent abuse:

- **Guest Users**: 10 requests per minute
- **Authenticated Users**: 60 requests per minute
- **Admin Users**: 300 requests per minute

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1692097200
```

## SDK and Examples

### JavaScript SDK

```javascript
class AssistantCRMClient {
  constructor(baseUrl, apiKey = null) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }

  async sendMessage(message, sessionId = null) {
    const response = await fetch(`${this.baseUrl}/api/method/assistant_crm.api.chat.send_message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
      },
      body: JSON.stringify({
        message,
        session_id: sessionId
      })
    });
    
    return response.json();
  }

  async getChatHistory(sessionId, limit = 50) {
    const params = new URLSearchParams({
      session_id: sessionId,
      limit: limit.toString()
    });
    
    const response = await fetch(`${this.baseUrl}/api/method/assistant_crm.api.chat.get_chat_history?${params}`);
    return response.json();
  }
}

// Usage
const client = new AssistantCRMClient('https://your-domain.com');
const response = await client.sendMessage('Hello Anna!');
console.log(response.data.response);
```

### Python SDK

```python
import requests
from typing import Optional, Dict, Any

class AssistantCRMClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
    
    def send_message(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/method/assistant_crm.api.chat.send_message"
        data = {
            'message': message,
            'session_id': session_id
        }
        
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_chat_history(self, session_id: str, limit: int = 50) -> Dict[str, Any]:
        url = f"{self.base_url}/api/method/assistant_crm.api.chat.get_chat_history"
        params = {
            'session_id': session_id,
            'limit': limit
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

# Usage
client = AssistantCRMClient('https://your-domain.com')
response = client.send_message('Hello Anna!')
print(response['data']['response'])
```

---

**Next**: [Authentication API](authentication.md) | [Live Data API](live-data.md)
