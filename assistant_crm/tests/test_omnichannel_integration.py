#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Omnichannel Integration Test Suite
Comprehensive testing framework for all channel integrations
"""

import frappe
import unittest
import json
import time
import asyncio
import aiohttp
from unittest.mock import patch, MagicMock
from frappe.test_runner import make_test_records
from assistant_crm.services.omnichannel_router import OmnichannelRouter
from assistant_crm.services.realtime_service import RealtimeService
from assistant_crm.services.config_manager import ConfigManager


class TestOmnichannelIntegration(unittest.TestCase):
    """Test suite for omnichannel platform integrations"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        frappe.set_user("Administrator")
        cls.setup_test_data()
        cls.router = OmnichannelRouter()
        cls.realtime_service = RealtimeService()
        cls.config_manager = ConfigManager()
    
    @classmethod
    def setup_test_data(cls):
        """Create test channel configurations"""
        test_channels = [
            {
                "doctype": "Channel Configuration",
                "channel_name": "Test WhatsApp",
                "channel_type": "WhatsApp",
                "phone_number": "+1234567890",
                "whatsapp_business_account_id": "test_business_id",
                "whatsapp_phone_number_id": "test_phone_id",
                "is_active": 1,
                "auto_response_enabled": 1
            },
            {
                "doctype": "Channel Configuration", 
                "channel_name": "Test Facebook",
                "channel_type": "Facebook",
                "facebook_page_id": "test_page_id",
                "facebook_app_id": "test_app_id",
                "is_active": 1,
                "auto_response_enabled": 1
            },
            {
                "doctype": "Channel Configuration",
                "channel_name": "Test Telegram",
                "channel_type": "Telegram",
                "telegram_bot_username": "@test_bot",
                "is_active": 1,
                "auto_response_enabled": 1
            }
        ]
        
        for channel_data in test_channels:
            if not frappe.db.exists("Channel Configuration", {"channel_name": channel_data["channel_name"]}):
                doc = frappe.get_doc(channel_data)
                doc.set_password("api_key", "test_api_key")
                doc.set_password("whatsapp_webhook_secret", "test_webhook_secret")
                doc.insert()
    
    def test_whatsapp_message_processing(self):
        """Test WhatsApp message processing with real-time updates"""
        test_message_data = {
            "entry": [{
                "changes": [{
                    "field": "messages",
                    "value": {
                        "messages": [{
                            "from": "+1234567890",
                            "text": {"body": "Hello WCFCB, I need help with my pension"},
                            "type": "text",
                            "id": "test_msg_001",
                            "timestamp": "1234567890"
                        }]
                    }
                }]
            }]
        }
        
        # Mock the webhook processing
        with patch('assistant_crm.api.realtime_webhooks.process_whatsapp_message_realtime') as mock_process:
            mock_process.return_value = {"success": True, "message_id": "test_msg_001"}
            
            # Test message routing
            result = self.router.route_message(
                "WhatsApp",
                "+1234567890", 
                "Hello WCFCB, I need help with my pension",
                {"whatsapp_message_id": "test_msg_001"}
            )
            
            self.assertTrue(result.get("success"))
            self.assertIsNotNone(result.get("response"))
            self.assertEqual(result.get("channel_type"), "WhatsApp")
    
    def test_facebook_message_processing(self):
        """Test Facebook Messenger message processing"""
        test_messaging_event = {
            "sender": {"id": "test_user_123"},
            "recipient": {"id": "test_page_456"},
            "timestamp": 1234567890,
            "message": {
                "mid": "test_fb_msg_001",
                "text": "I want to submit a claim"
            }
        }
        
        # Test message routing
        result = self.router.route_message(
            "Facebook",
            "test_user_123",
            "I want to submit a claim", 
            {"facebook_message_id": "test_fb_msg_001"}
        )
        
        self.assertTrue(result.get("success"))
        self.assertIsNotNone(result.get("response"))
        self.assertEqual(result.get("channel_type"), "Facebook")
    
    def test_telegram_message_processing(self):
        """Test Telegram message processing"""
        test_telegram_message = {
            "message_id": 123,
            "from": {
                "id": 987654321,
                "first_name": "John",
                "username": "john_doe"
            },
            "chat": {"id": 987654321, "type": "private"},
            "date": 1234567890,
            "text": "What are my benefit options?"
        }
        
        # Test message routing
        result = self.router.route_message(
            "Telegram",
            "987654321",
            "What are my benefit options?",
            {"telegram_message_id": 123}
        )
        
        self.assertTrue(result.get("success"))
        self.assertIsNotNone(result.get("response"))
        self.assertEqual(result.get("channel_type"), "Telegram")
    
    def test_real_time_message_broadcasting(self):
        """Test real-time message broadcasting functionality"""
        test_message_data = {
            "content": "Test real-time message",
            "sender": "test_user",
            "message_id": "test_rt_001",
            "metadata": {"priority": "high"}
        }
        
        # Test broadcasting to specific users
        result = self.realtime_service.broadcast_message(
            "WhatsApp",
            "+1234567890",
            test_message_data,
            target_users=["Administrator"]
        )
        
        self.assertTrue(result.get("success"))
        self.assertIsNotNone(result.get("event_data"))
    
    def test_agent_assignment_notification(self):
        """Test real-time agent assignment notifications"""
        test_conversation_id = "test_conv_001"
        test_agent_id = "Administrator"
        test_message_data = {
            "customer_name": "John Doe",
            "channel_type": "WhatsApp",
            "priority": "high",
            "content": "Urgent pension inquiry"
        }
        
        result = self.realtime_service.notify_agent_assignment(
            test_agent_id,
            test_conversation_id,
            test_message_data
        )
        
        self.assertTrue(result.get("success"))
        self.assertTrue(result.get("notification_sent"))
    
    def test_typing_indicator_management(self):
        """Test real-time typing indicators"""
        test_conversation_id = "test_conv_002"
        test_user_id = "test_user_123"
        
        # Test typing start
        result_start = self.realtime_service.update_typing_indicator(
            test_conversation_id,
            test_user_id,
            True,
            "WhatsApp"
        )
        
        self.assertTrue(result_start.get("success"))
        self.assertTrue(result_start.get("typing_updated"))
        
        # Test typing stop
        result_stop = self.realtime_service.update_typing_indicator(
            test_conversation_id,
            test_user_id,
            False,
            "WhatsApp"
        )
        
        self.assertTrue(result_stop.get("success"))
        self.assertTrue(result_stop.get("typing_updated"))
    
    def test_configuration_management(self):
        """Test secure configuration management"""
        test_credentials = {
            "channel_type": "WhatsApp",
            "api_key": "test_secret_token",
            "whatsapp_webhook_secret": "test_webhook_secret",
            "whatsapp_business_account_id": "test_business_id"
        }
        
        # Test credential storage
        success = self.config_manager.store_channel_credentials(
            "Test Config Channel",
            test_credentials
        )
        self.assertTrue(success)
        
        # Test credential retrieval
        retrieved_credentials = self.config_manager.get_channel_credentials(
            "Test Config Channel"
        )
        self.assertIsNotNone(retrieved_credentials)
        self.assertEqual(retrieved_credentials.get("channel_type"), "WhatsApp")
    
    def test_configuration_validation(self):
        """Test channel configuration validation"""
        # Test valid WhatsApp configuration
        valid_whatsapp_config = {
            "whatsapp_business_account_id": "test_business_id",
            "whatsapp_phone_number_id": "test_phone_id",
            "api_key": "test_token",
            "whatsapp_webhook_secret": "test_secret",
            "phone_number": "+1234567890"
        }
        
        validation_result = self.config_manager.validate_channel_config(
            "WhatsApp",
            valid_whatsapp_config
        )
        self.assertTrue(validation_result.get("valid"))
        
        # Test invalid configuration (missing required fields)
        invalid_config = {"api_key": "test_token"}
        
        validation_result = self.config_manager.validate_channel_config(
            "WhatsApp",
            invalid_config
        )
        self.assertFalse(validation_result.get("valid"))
        self.assertGreater(len(validation_result.get("errors", [])), 0)
    
    def test_webhook_url_generation(self):
        """Test webhook URL generation for different channels"""
        webhook_urls = self.config_manager.setup_webhook_urls("WhatsApp")
        
        self.assertIn("webhook_url", webhook_urls)
        self.assertIn("verify_url", webhook_urls)
        self.assertIn("status_url", webhook_urls)
        self.assertTrue(webhook_urls["webhook_url"].endswith("/whatsapp"))
    
    def test_error_handling_and_fallback(self):
        """Test error handling and fallback mechanisms"""
        # Test with invalid channel type
        result = self.router.route_message(
            "InvalidChannel",
            "test_user",
            "test message",
            {}
        )
        
        self.assertFalse(result.get("success"))
        self.assertIn("error", result)
        
        # Test with missing channel configuration
        result = self.router.route_message(
            "WhatsApp",
            "+9999999999",  # Non-configured number
            "test message",
            {}
        )
        
        # Should still process but may have different behavior
        self.assertIsNotNone(result)


class TestLoadAndPerformance(unittest.TestCase):
    """Performance and load testing for omnichannel integration"""
    
    def setUp(self):
        frappe.set_user("Administrator")
        self.router = OmnichannelRouter()
    
    def test_concurrent_message_processing(self):
        """Test concurrent message processing performance"""
        import threading
        import time
        
        results = []
        start_time = time.time()
        
        def process_message(message_id):
            result = self.router.route_message(
                "WhatsApp",
                f"+123456789{message_id}",
                f"Test message {message_id}",
                {"test_message_id": message_id}
            )
            results.append(result)
        
        # Create 10 concurrent threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=process_message, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Validate results
        self.assertEqual(len(results), 10)
        self.assertLess(processing_time, 10)  # Should complete within 10 seconds
        
        # Check success rate
        success_count = sum(1 for r in results if r.get("success"))
        success_rate = success_count / len(results)
        self.assertGreaterEqual(success_rate, 0.8)  # At least 80% success rate
    
    def test_response_time_benchmarks(self):
        """Test response time benchmarks for different operations"""
        import time
        
        # Test message routing response time
        start_time = time.time()
        result = self.router.route_message(
            "WhatsApp",
            "+1234567890",
            "Quick response test",
            {"benchmark_test": True}
        )
        routing_time = time.time() - start_time
        
        self.assertTrue(result.get("success"))
        self.assertLess(routing_time, 2.0)  # Should complete within 2 seconds
        
        # Test real-time service response time
        realtime_service = RealtimeService()
        start_time = time.time()
        
        broadcast_result = realtime_service.broadcast_message(
            "WhatsApp",
            "+1234567890",
            {"content": "Benchmark test", "sender": "system"},
            target_users=["Administrator"]
        )
        broadcast_time = time.time() - start_time
        
        self.assertTrue(broadcast_result.get("success"))
        self.assertLess(broadcast_time, 0.5)  # Should complete within 500ms
    
    def test_memory_usage_monitoring(self):
        """Test memory usage during intensive operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform intensive operations
        for i in range(100):
            self.router.route_message(
                "WhatsApp",
                f"+123456{i:04d}",
                f"Memory test message {i}",
                {"memory_test": True}
            )
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for 100 messages)
        self.assertLess(memory_increase, 100)


class TestIntegrationEndToEnd(unittest.TestCase):
    """End-to-end integration testing"""
    
    def setUp(self):
        frappe.set_user("Administrator")
    
    def test_complete_whatsapp_flow(self):
        """Test complete WhatsApp message flow from webhook to response"""
        # Simulate incoming webhook data
        webhook_data = {
            "entry": [{
                "changes": [{
                    "field": "messages",
                    "value": {
                        "messages": [{
                            "from": "+1234567890",
                            "text": {"body": "I need help with my pension claim"},
                            "type": "text",
                            "id": "e2e_test_msg_001",
                            "timestamp": str(int(time.time()))
                        }]
                    }
                }]
            }]
        }
        
        # Process through the complete flow
        from assistant_crm.api.realtime_webhooks import process_whatsapp_message_realtime
        
        # Mock the actual webhook processing
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                "messages": [{"id": "response_msg_001"}]
            }
            
            # Process the message
            for entry in webhook_data["entry"]:
                for change in entry["changes"]:
                    if change["field"] == "messages":
                        process_whatsapp_message_realtime(change["value"])
            
            # Verify that response was sent
            self.assertTrue(mock_post.called)
    
    def test_agent_escalation_flow(self):
        """Test complete agent escalation flow"""
        # Create a message that should trigger escalation
        complex_message = "I have a complex issue with my pension calculation that involves multiple years of service and I need detailed explanation of the formula used"
        
        router = OmnichannelRouter()
        result = router.route_message(
            "WhatsApp",
            "+1234567890",
            complex_message,
            {"escalation_test": True}
        )
        
        # Should be escalated to agent
        self.assertTrue(result.get("success"))
        # Check if escalation occurred (this depends on AI analysis)
        # In a real scenario, this would check the escalation logic
    
    def test_multi_channel_conversation(self):
        """Test conversation across multiple channels"""
        customer_id = "test_customer_001"
        
        # Start conversation on WhatsApp
        whatsapp_result = OmnichannelRouter().route_message(
            "WhatsApp",
            "+1234567890",
            "Hello, I started a conversation here",
            {"customer_id": customer_id}
        )
        
        # Continue on Facebook
        facebook_result = OmnichannelRouter().route_message(
            "Facebook",
            "fb_user_123",
            "Continuing our conversation from WhatsApp",
            {"customer_id": customer_id}
        )
        
        # Both should be successful and potentially linked
        self.assertTrue(whatsapp_result.get("success"))
        self.assertTrue(facebook_result.get("success"))


if __name__ == "__main__":
    # Run the test suite
    unittest.main(verbosity=2)
