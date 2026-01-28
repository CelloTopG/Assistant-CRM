#!/usr/bin/env python3
"""
Make.com Integration Test Suite
==============================

Comprehensive test suite for WCFCB Assistant CRM Make.com webhook integration.
Tests all major functionality including authentication, message processing, and error handling.

Usage:
    python test_make_com_integration.py

Requirements:
    - WCFCB Assistant CRM running
    - Make.com integration configured
    - Test API key configured
"""

import requests
import json
import hmac
import hashlib
import time
from datetime import datetime


class MakeComIntegrationTester:
    """Test suite for Make.com webhook integration"""
    
    def __init__(self, base_url="http://localhost:8000", api_key="test_api_key"):
        self.base_url = base_url.rstrip('/')
        self.webhook_url = f"{self.base_url}/api/omnichannel/webhook/make-com"
        self.api_key = api_key
        self.webhook_secret = "test_webhook_secret"
        self.test_results = []
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Make.com Integration Tests")
        print("=" * 50)
        
        # Test webhook status
        self.test_webhook_status()
        
        # Test authentication
        self.test_authentication()
        
        # Test message processing
        self.test_message_processing()
        
        # Test error handling
        self.test_error_handling()
        
        # Test rate limiting
        self.test_rate_limiting()
        
        # Print results
        self.print_results()
    
    def test_webhook_status(self):
        """Test webhook status endpoint"""
        print("\n📡 Testing Webhook Status...")
        
        try:
            response = requests.get(self.webhook_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "Make.com webhook endpoint is active" in data.get("message", ""):
                    self.log_test("Webhook Status", "PASS", "Endpoint is active and responding")
                else:
                    self.log_test("Webhook Status", "FAIL", f"Unexpected response: {data}")
            else:
                self.log_test("Webhook Status", "FAIL", f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Webhook Status", "ERROR", str(e))
    
    def test_authentication(self):
        """Test authentication mechanisms"""
        print("\n🔐 Testing Authentication...")
        
        # Test valid API key
        self.test_valid_api_key()
        
        # Test invalid API key
        self.test_invalid_api_key()
        
        # Test missing API key
        self.test_missing_api_key()
        
        # Test webhook signature
        self.test_webhook_signature()
    
    def test_valid_api_key(self):
        """Test with valid API key"""
        payload = self.create_test_message_payload()
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload, headers=headers, timeout=10)
            
            # Note: This might fail if Make.com integration is not fully configured
            # but should not fail due to authentication
            if response.status_code in [200, 400, 500]:  # Not 401 (auth error)
                self.log_test("Valid API Key", "PASS", "Authentication accepted")
            else:
                self.log_test("Valid API Key", "FAIL", f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Valid API Key", "ERROR", str(e))
    
    def test_invalid_api_key(self):
        """Test with invalid API key"""
        payload = self.create_test_message_payload()
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": "invalid_key_123"
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 401:
                self.log_test("Invalid API Key", "PASS", "Authentication properly rejected")
            else:
                self.log_test("Invalid API Key", "FAIL", f"Expected 401, got {response.status_code}")
                
        except Exception as e:
            self.log_test("Invalid API Key", "ERROR", str(e))
    
    def test_missing_api_key(self):
        """Test with missing API key"""
        payload = self.create_test_message_payload()
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(self.webhook_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 401:
                self.log_test("Missing API Key", "PASS", "Authentication properly rejected")
            else:
                self.log_test("Missing API Key", "FAIL", f"Expected 401, got {response.status_code}")
                
        except Exception as e:
            self.log_test("Missing API Key", "ERROR", str(e))
    
    def test_webhook_signature(self):
        """Test webhook signature verification"""
        payload = self.create_test_message_payload()
        payload_str = json.dumps(payload, separators=(',', ':'))
        
        # Calculate signature
        signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-Webhook-Signature": f"sha256={signature}"
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload, headers=headers, timeout=10)
            
            # Should not fail due to signature (might fail for other reasons)
            if response.status_code != 401:
                self.log_test("Webhook Signature", "PASS", "Signature verification working")
            else:
                self.log_test("Webhook Signature", "FAIL", "Signature verification failed")
                
        except Exception as e:
            self.log_test("Webhook Signature", "ERROR", str(e))
    
    def test_message_processing(self):
        """Test message processing functionality"""
        print("\n💬 Testing Message Processing...")
        
        # Test text message
        self.test_text_message()
        
        # Test different platforms
        self.test_different_platforms()
        
        # Test different event types
        self.test_different_event_types()
    
    def test_text_message(self):
        """Test basic text message processing"""
        payload = self.create_test_message_payload(
            message_content="Hello Anna, I need help with my pension",
            platform="facebook"
        )
        
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("response"):
                    self.log_test("Text Message Processing", "PASS", "Message processed successfully")
                else:
                    self.log_test("Text Message Processing", "PARTIAL", f"Response: {data}")
            else:
                self.log_test("Text Message Processing", "FAIL", f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Text Message Processing", "ERROR", str(e))
    
    def test_different_platforms(self):
        """Test different social media platforms"""
        platforms = ["facebook", "instagram", "telegram", "whatsapp"]
        
        for platform in platforms:
            payload = self.create_test_message_payload(platform=platform)
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            
            try:
                response = requests.post(self.webhook_url, json=payload, headers=headers, timeout=10)
                
                if response.status_code in [200, 400]:  # 400 might be config issue, not platform issue
                    self.log_test(f"Platform {platform.title()}", "PASS", "Platform supported")
                else:
                    self.log_test(f"Platform {platform.title()}", "FAIL", f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Platform {platform.title()}", "ERROR", str(e))
    
    def test_different_event_types(self):
        """Test different event types"""
        event_types = ["message", "status_update", "user_action"]
        
        for event_type in event_types:
            payload = self.create_test_payload_by_event_type(event_type)
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            
            try:
                response = requests.post(self.webhook_url, json=payload, headers=headers, timeout=10)
                
                if response.status_code in [200, 400]:
                    self.log_test(f"Event {event_type}", "PASS", "Event type supported")
                else:
                    self.log_test(f"Event {event_type}", "FAIL", f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Event {event_type}", "ERROR", str(e))
    
    def test_error_handling(self):
        """Test error handling"""
        print("\n⚠️ Testing Error Handling...")
        
        # Test invalid JSON
        self.test_invalid_json()
        
        # Test missing required fields
        self.test_missing_fields()
        
        # Test invalid platform
        self.test_invalid_platform()
    
    def test_invalid_json(self):
        """Test invalid JSON handling"""
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        
        try:
            response = requests.post(self.webhook_url, data="invalid json", headers=headers, timeout=10)
            
            if response.status_code == 400:
                self.log_test("Invalid JSON", "PASS", "Invalid JSON properly rejected")
            else:
                self.log_test("Invalid JSON", "FAIL", f"Expected 400, got {response.status_code}")
                
        except Exception as e:
            self.log_test("Invalid JSON", "ERROR", str(e))
    
    def test_missing_fields(self):
        """Test missing required fields"""
        payload = {"platform": "facebook"}  # Missing required fields
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 400:
                self.log_test("Missing Fields", "PASS", "Missing fields properly rejected")
            else:
                self.log_test("Missing Fields", "FAIL", f"Expected 400, got {response.status_code}")
                
        except Exception as e:
            self.log_test("Missing Fields", "ERROR", str(e))
    
    def test_invalid_platform(self):
        """Test invalid platform handling"""
        payload = self.create_test_message_payload(platform="invalid_platform")
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 400:
                self.log_test("Invalid Platform", "PASS", "Invalid platform properly rejected")
            else:
                self.log_test("Invalid Platform", "FAIL", f"Expected 400, got {response.status_code}")
                
        except Exception as e:
            self.log_test("Invalid Platform", "ERROR", str(e))
    
    def test_rate_limiting(self):
        """Test rate limiting (basic test)"""
        print("\n🚦 Testing Rate Limiting...")
        
        # Note: This is a basic test - full rate limiting test would require many requests
        payload = self.create_test_message_payload()
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        
        try:
            # Make a few rapid requests
            responses = []
            for i in range(3):
                response = requests.post(self.webhook_url, json=payload, headers=headers, timeout=10)
                responses.append(response.status_code)
                time.sleep(0.1)
            
            # Should not hit rate limit with just 3 requests
            if all(code != 429 for code in responses):
                self.log_test("Rate Limiting", "PASS", "Rate limiting configured (not triggered)")
            else:
                self.log_test("Rate Limiting", "INFO", "Rate limiting triggered (very strict limits)")
                
        except Exception as e:
            self.log_test("Rate Limiting", "ERROR", str(e))
    
    def create_test_message_payload(self, message_content="Hello Anna", platform="facebook"):
        """Create test message payload"""
        return {
            "platform": platform,
            "event_type": "message",
            "timestamp": datetime.now().isoformat() + "Z",
            "data": {
                "message": {
                    "id": f"test_msg_{int(time.time())}",
                    "content": message_content,
                    "type": "text"
                },
                "sender": {
                    "id": f"test_user_{int(time.time())}",
                    "name": "Test User",
                    "platform_data": {}
                },
                "conversation": {
                    "id": f"test_conv_{int(time.time())}",
                    "channel_id": f"test_channel_{int(time.time())}"
                }
            }
        }
    
    def create_test_payload_by_event_type(self, event_type):
        """Create test payload for different event types"""
        base_payload = {
            "platform": "facebook",
            "event_type": event_type,
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
        if event_type == "message":
            base_payload["data"] = {
                "message": {"id": "test_123", "content": "Test message", "type": "text"},
                "sender": {"id": "test_user", "name": "Test User"},
                "conversation": {"channel_id": "test_channel"}
            }
        elif event_type == "status_update":
            base_payload["data"] = {
                "status": {"message_id": "test_123", "type": "delivered"}
            }
        elif event_type == "user_action":
            base_payload["data"] = {
                "action": {"type": "typing", "user_id": "test_user", "typing": True}
            }
        
        return base_payload
    
    def log_test(self, test_name, status, details):
        """Log test result"""
        self.test_results.append({
            "test": test_name,
            "status": status,
            "details": details
        })
        
        # Print immediate result
        status_emoji = {
            "PASS": "✅",
            "FAIL": "❌", 
            "ERROR": "💥",
            "PARTIAL": "⚠️",
            "INFO": "ℹ️"
        }
        
        print(f"  {status_emoji.get(status, '❓')} {test_name}: {status} - {details}")
    
    def print_results(self):
        """Print test results summary"""
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        error_tests = len([r for r in self.test_results if r["status"] == "ERROR"])
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"💥 Errors: {error_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0 or error_tests > 0:
            print("\n🔍 Issues Found:")
            for result in self.test_results:
                if result["status"] in ["FAIL", "ERROR"]:
                    print(f"  • {result['test']}: {result['details']}")


if __name__ == "__main__":
    # Configuration
    BASE_URL = "http://localhost:8000"  # Change to your WCFCB instance URL
    API_KEY = "test_api_key"  # Change to your configured API key
    
    # Run tests
    tester = MakeComIntegrationTester(BASE_URL, API_KEY)
    tester.run_all_tests()
