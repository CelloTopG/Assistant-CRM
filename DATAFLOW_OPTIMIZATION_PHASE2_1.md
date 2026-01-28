# **PHASE 2.1: UNIFIED API ENDPOINT CONSOLIDATION**

## **Objective**
Consolidate multiple chat API endpoints into a single, optimized endpoint with consistent response formats and improved frontend-backend synchronization.

## **Current State Analysis**

### **Existing API Endpoints:**
1. `unified_chat_api.py` - Main unified endpoint
2. `optimized_chat.py` - Performance-optimized endpoint  
3. `chat.py` - Legacy chat endpoint
4. `chatbot.py` - Basic chatbot endpoint

### **Issues Identified:**
- **Multiple Entry Points:** Frontend confusion about which endpoint to use
- **Response Format Inconsistency:** Different response structures across endpoints
- **Feature Fragmentation:** Features scattered across different endpoints
- **Maintenance Overhead:** Updates required in multiple locations

## **Technical Specifications**

### **2.1.1: Master Chat API Endpoint**

**File:** `assistant_crm/api/master_chat_api.py`

```python
#!/usr/bin/env python3
"""
Master Chat API for Assistant CRM
Single, optimized endpoint for all chat interactions with consistent response format
"""

import json
import time
from typing import Dict, Any, Optional

# Enhanced error-safe frappe import
try:
    import frappe
    from frappe import _
    from frappe.utils import now, cstr
    FRAPPE_AVAILABLE = True
except ImportError:
    frappe = None
    _ = lambda x: x
    now = lambda: '2025-08-12T23:40:00'
    cstr = str
    FRAPPE_AVAILABLE = False

# Import optimized services
from assistant_crm.services.intent_router import get_intent_router
from assistant_crm.services.response_assembler import get_response_assembler
from assistant_crm.services.enhanced_cache_service import get_cache_service

class MasterChatAPI:
    """
    Master chat API with unified response format and optimized performance
    """
    
    def __init__(self):
        self.intent_router = get_intent_router()
        self.response_assembler = get_response_assembler()
        self.cache_service = get_cache_service()
        self.api_stats = {
            'total_requests': 0,
            'successful_responses': 0,
            'error_responses': 0,
            'average_response_time': 0
        }
    
    def process_chat_message(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process chat message with unified response format
        
        Returns:
        {
            "success": bool,
            "response": str,
            "metadata": {
                "intent": str,
                "source": str,
                "confidence": float,
                "response_time_ms": float,
                "live_data_used": bool,
                "cache_hit": bool
            },
            "quick_replies": List[str],
            "actions": Dict[str, Any],
            "error": Optional[str]
        }
        """
        start_time = time.time()
        self.api_stats['total_requests'] += 1
        
        try:
            # Validate input
            if not message or not message.strip():
                return self._create_error_response("Message cannot be empty", start_time)
            
            # Prepare user context
            if user_context is None:
                user_context = self._extract_user_context()
            
            # Route request through intent router
            routing_result = self.intent_router.route_request(message.strip(), user_context)
            
            # Assemble response
            assembled_response = self.response_assembler.assemble_response(routing_result)
            
            # Create unified response format
            response = self._create_success_response(
                assembled_response, 
                routing_result, 
                start_time
            )
            
            self.api_stats['successful_responses'] += 1
            self._update_performance_stats(start_time)
            
            return response
            
        except Exception as e:
            self.api_stats['error_responses'] += 1
            error_msg = f"An error occurred while processing your message: {str(e)}"
            return self._create_error_response(error_msg, start_time)
    
    def _create_success_response(self, assembled_response: Dict[str, Any], 
                               routing_result: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Create standardized success response"""
        response_time = (time.time() - start_time) * 1000
        
        return {
            "success": True,
            "response": assembled_response.get('response', 'I apologize, but I could not generate a response.'),
            "metadata": {
                "intent": routing_result.get('intent', 'unknown'),
                "source": routing_result.get('source', 'unknown'),
                "confidence": routing_result.get('confidence', 0.0),
                "response_time_ms": round(response_time, 2),
                "live_data_used": routing_result.get('source') == 'live_data',
                "cache_hit": routing_result.get('cache_hit', False),
                "timestamp": now()
            },
            "quick_replies": assembled_response.get('quick_replies', []),
            "actions": assembled_response.get('actions', {}),
            "error": None
        }
    
    def _create_error_response(self, error_message: str, start_time: float) -> Dict[str, Any]:
        """Create standardized error response"""
        response_time = (time.time() - start_time) * 1000
        
        return {
            "success": False,
            "response": "I apologize, but I'm having trouble right now. Please try again.",
            "metadata": {
                "intent": "error",
                "source": "error_handler",
                "confidence": 0.0,
                "response_time_ms": round(response_time, 2),
                "live_data_used": False,
                "cache_hit": False,
                "timestamp": now()
            },
            "quick_replies": ["Try again", "Contact support"],
            "actions": {},
            "error": error_message
        }
    
    def _extract_user_context(self) -> Dict[str, Any]:
        """Extract user context from current session"""
        if not FRAPPE_AVAILABLE:
            return {"user_id": "GUEST", "user_role": "guest"}
        
        try:
            # Extract from frappe session
            user = frappe.session.user if frappe.session else "Guest"
            user_roles = frappe.get_roles(user) if user != "Guest" else ["Guest"]
            
            return {
                "user_id": user,
                "user_role": user_roles[0] if user_roles else "guest",
                "session_id": frappe.session.sid if frappe.session else None
            }
        except:
            return {"user_id": "GUEST", "user_role": "guest"}
    
    def _update_performance_stats(self, start_time: float):
        """Update API performance statistics"""
        response_time = time.time() - start_time
        total_requests = self.api_stats['total_requests']
        
        self.api_stats['average_response_time'] = (
            (self.api_stats['average_response_time'] * (total_requests - 1) + response_time) 
            / total_requests
        )
    
    def get_api_stats(self) -> Dict[str, Any]:
        """Get API performance statistics"""
        return {
            **self.api_stats,
            'success_rate': (
                self.api_stats['successful_responses'] / 
                max(self.api_stats['total_requests'], 1) * 100
            ),
            'average_response_time_ms': self.api_stats['average_response_time'] * 1000
        }

# Global API instance
_master_api = None

def get_master_chat_api() -> MasterChatAPI:
    """Get global master chat API instance"""
    global _master_api
    if _master_api is None:
        _master_api = MasterChatAPI()
    return _master_api

# Frappe API endpoints
if FRAPPE_AVAILABLE:
    @frappe.whitelist(allow_guest=True)
    def send_message(message, user_context=None):
        """Main chat endpoint - processes messages and returns responses"""
        try:
            api = get_master_chat_api()
            
            # Parse user_context if it's a string
            if isinstance(user_context, str):
                user_context = json.loads(user_context)
            
            return api.process_chat_message(message, user_context)
            
        except Exception as e:
            return {
                "success": False,
                "response": "I apologize, but I'm experiencing technical difficulties. Please try again.",
                "error": str(e)
            }
    
    @frappe.whitelist(allow_guest=True)
    def get_performance_stats():
        """Get API performance statistics"""
        try:
            api = get_master_chat_api()
            return api.get_api_stats()
        except Exception as e:
            return {"error": str(e)}
```

### **2.1.2: Frontend Integration Update**

**File:** `assistant_crm/www/anna_integrated.html` (Modifications)

**Location:** Update sendMessage function (around line 350)

```javascript
// Replace existing sendMessage function with optimized version
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message || isProcessing) return;
    
    isProcessing = true;
    input.value = '';
    addMessage('user', message);
    showTyping(true);
    
    try {
        const response = await fetch('/api/method/assistant_crm.api.master_chat_api.send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Frappe-CSRF-Token': frappe.csrf_token || ''
            },
            body: JSON.stringify({
                message: message,
                user_context: getCurrentUserContext()
            })
        });
        
        const data = await response.json();
        showTyping(false);
        isProcessing = false;
        
        if (data.message && data.message.success) {
            const result = data.message;
            
            // Add response message
            addMessage('anna', result.response);
            
            // Show performance indicators (development mode)
            if (result.metadata) {
                console.log('📊 Response Metadata:', result.metadata);
                updatePerformanceIndicators(result.metadata);
            }
            
            // Handle quick replies
            if (result.quick_replies && result.quick_replies.length > 0) {
                showQuickReplies(result.quick_replies);
            }
            
            // Handle special actions
            if (result.actions && Object.keys(result.actions).length > 0) {
                handleSpecialActions(result.actions);
            }
            
        } else {
            const errorMsg = data.message?.error || 'I apologize, but I encountered an error. Please try again.';
            addMessage('anna', errorMsg);
        }
        
    } catch (error) {
        console.error('Error sending message:', error);
        showTyping(false);
        isProcessing = false;
        addMessage('anna', 'I\'m having trouble connecting right now. Please try again.');
    }
}

function getCurrentUserContext() {
    // Extract current user context for API call
    return {
        user_id: window.current_user || 'GUEST',
        user_role: window.user_roles?.[0] || 'guest',
        session_id: window.session_id || null
    };
}

function updatePerformanceIndicators(metadata) {
    // Update performance indicators in development mode
    const indicator = document.getElementById('performanceIndicator');
    if (indicator) {
        indicator.innerHTML = `
            <small>
                ${metadata.response_time_ms}ms | 
                ${metadata.live_data_used ? '🟢 Live' : '🔵 KB'} | 
                ${metadata.cache_hit ? '⚡ Cached' : '🔄 Fresh'}
            </small>
        `;
    }
}

function handleSpecialActions(actions) {
    // Handle special actions from API response
    if (actions.show_file_upload) {
        showFileUpload(true);
    }
    if (actions.redirect_url) {
        window.location.href = actions.redirect_url;
    }
    if (actions.show_authentication) {
        showAuthenticationPrompt();
    }
}
```

## **Implementation Steps**

### **Step 1: Create Master Chat API (4 hours)**
1. Implement unified API endpoint with consistent response format
2. Integrate with optimized services (caching, routing, assembly)
3. Add comprehensive error handling and performance monitoring

### **Step 2: Update Frontend Integration (3 hours)**
1. Modify frontend to use single API endpoint
2. Update response handling for new unified format
3. Add performance indicators and metadata display

### **Step 3: Deprecate Legacy Endpoints (2 hours)**
1. Add deprecation warnings to old endpoints
2. Implement redirect logic for backward compatibility
3. Update documentation and examples

## **Expected Results**
- **API Consistency:** Single response format across all interactions
- **Frontend Simplification:** Single endpoint integration
- **Performance Monitoring:** Real-time performance metrics
- **Maintenance Reduction:** 80% reduction in API maintenance overhead

## **Success Metrics**
- All frontend interactions use single API endpoint
- Response format consistency 100%
- API response time < 300ms average
- Zero breaking changes for existing integrations
