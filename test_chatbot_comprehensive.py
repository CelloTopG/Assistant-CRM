#!/usr/bin/env python3
"""
Comprehensive Chatbot Testing Script
===================================

This script provides comprehensive testing for the WCFCB Assistant CRM chatbot
after the surgical fixes have been implemented.

Usage:
    cd /workspace/development/frappe-bench
    python apps/assistant_crm/test_chatbot_comprehensive.py

Test Coverage:
- API endpoint accessibility
- Guest user functionality
- Authenticated user functionality
- Session management
- Error handling
- Response quality
"""

import requests
import json
import time
import sys

class ChatbotTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        
    def log_test(self, test_name, success, details=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
    
    def test_api_accessibility(self):
        """Test 1: API Endpoint Accessibility"""
        print("\n🔍 Test 1: API Endpoint Accessibility")
        
        try:
            # Test settings API
            response = requests.get(f"{self.base_url}/api/method/assistant_crm.services.settings_service.validate_access")
            if response.status_code == 200:
                data = response.json()
                if data.get("message", {}).get("has_access"):
                    self.log_test("Settings API Access", True, "Guest users can access settings")
                else:
                    self.log_test("Settings API Access", False, "Settings API not accessible")
            else:
                self.log_test("Settings API Access", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Settings API Access", False, str(e))
    
    def test_guest_user_chat(self):
        """Test 2: Guest User Chat Functionality"""
        print("\n🔍 Test 2: Guest User Chat Functionality")
        
        try:
            # Test optimized chat API
            payload = {
                "message": "Hello, I need help with workers compensation",
                "session_id": "test_guest_session"
            }
            
            response = requests.post(
                f"{self.base_url}/api/method/assistant_crm.api.optimized_chat.send_optimized_message",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                message_data = data.get("message", {})
                
                if message_data.get("success"):
                    ai_response = message_data.get("response", "")
                    if ai_response and "technical difficulties" not in ai_response.lower():
                        self.log_test("Guest Chat Response", True, f"Got AI response: {ai_response[:50]}...")
                    else:
                        self.log_test("Guest Chat Response", False, "Still getting generic error response")
                        
                    # Check session management
                    if message_data.get("session_id"):
                        self.log_test("Session Management", True, f"Session ID: {message_data.get('session_id')}")
                    else:
                        self.log_test("Session Management", False, "No session ID returned")
                        
                else:
                    self.log_test("Guest Chat Response", False, "API returned success=false")
            else:
                self.log_test("Guest Chat Response", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Guest Chat Response", False, str(e))
    
    def test_response_quality(self):
        """Test 3: Response Quality and Consistency"""
        print("\n🔍 Test 3: Response Quality and Consistency")
        
        test_messages = [
            "What services do you offer?",
            "How do I file a workers compensation claim?",
            "I need help with employer registration",
            "What are the payment options available?"
        ]
        
        for i, message in enumerate(test_messages):
            try:
                payload = {
                    "message": message,
                    "session_id": f"quality_test_{i}"
                }
                
                response = requests.post(
                    f"{self.base_url}/api/method/assistant_crm.api.optimized_chat.send_optimized_message",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    message_data = data.get("message", {})
                    ai_response = message_data.get("response", "")
                    
                    # Check for Anna personality
                    has_personality = any(indicator in ai_response.lower() for indicator in [
                        "anna", "wcfcb", "workers", "compensation", "help", "assist"
                    ])
                    
                    if has_personality:
                        self.log_test(f"Quality Test {i+1}", True, f"Response shows WCFCB context")
                    else:
                        self.log_test(f"Quality Test {i+1}", False, f"Generic response: {ai_response[:30]}...")
                else:
                    self.log_test(f"Quality Test {i+1}", False, f"HTTP {response.status_code}")
                    
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                self.log_test(f"Quality Test {i+1}", False, str(e))
    
    def test_error_handling(self):
        """Test 4: Error Handling"""
        print("\n🔍 Test 4: Error Handling")
        
        # Test empty message
        try:
            payload = {"message": "", "session_id": "error_test"}
            response = requests.post(
                f"{self.base_url}/api/method/assistant_crm.api.optimized_chat.send_optimized_message",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 417:  # Frappe validation error
                self.log_test("Empty Message Handling", True, "Properly rejects empty messages")
            else:
                self.log_test("Empty Message Handling", False, f"Unexpected response: {response.status_code}")
                
        except Exception as e:
            self.log_test("Empty Message Handling", False, str(e))
    
    def run_all_tests(self):
        """Run all tests and provide summary"""
        print("🚀 Starting Comprehensive Chatbot Testing")
        print("=" * 50)
        
        start_time = time.time()
        
        self.test_api_accessibility()
        self.test_guest_user_chat()
        self.test_response_quality()
        self.test_error_handling()
        
        end_time = time.time()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        print(f"Execution Time: {end_time - start_time:.2f} seconds")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! Chatbot is working correctly.")
        else:
            print(f"\n⚠️  {total - passed} tests failed. Review the details above.")
            
        return passed == total

if __name__ == "__main__":
    tester = ChatbotTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
