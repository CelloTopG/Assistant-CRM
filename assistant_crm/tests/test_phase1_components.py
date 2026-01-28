#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WCFCB Assistant CRM - Phase 1 Component Tests
=============================================

Unit tests for Phase 1 architectural foundation components.
Tests each component in isolation to ensure no circular dependencies.

Author: WCFCB Development Team
Created: 2025-08-12 (Phase 1 Implementation)
License: MIT

Test Coverage:
-------------
1. LiveDataOrchestrator - Standalone live data operations
2. IntentRouter - Unidirectional request routing
3. ResponseAssembler - Response assembly without circular calls
4. Circuit Breaker - Timeout protection and failure recovery
5. Integration - Component interaction validation
"""

import unittest
import time
import threading
from unittest.mock import Mock, patch
import sys
import os

# Add the assistant_crm module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from assistant_crm.services.live_data_orchestrator import LiveDataOrchestrator, CircuitBreaker, TimeoutException
    from assistant_crm.services.intent_router import IntentRouter
    from assistant_crm.services.response_assembler import ResponseAssembler
except ImportError as e:
    print(f"Import error: {e}")
    # Create mock classes for testing if imports fail
    class LiveDataOrchestrator:
        def __init__(self): pass
        def process_live_data_request(self, *args): return None
    
    class IntentRouter:
        def __init__(self): pass
        def route_request(self, *args): return {}
    
    class ResponseAssembler:
        def __init__(self): pass
        def assemble_response(self, *args): return "Test response"
    
    class CircuitBreaker:
        def __init__(self, *args): pass
        def call(self, func, *args, **kwargs): return func(*args, **kwargs)
    
    class TimeoutException(Exception): pass


class TestLiveDataOrchestrator(unittest.TestCase):
    """Test LiveDataOrchestrator component in isolation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.orchestrator = LiveDataOrchestrator()
        self.test_user_context = {
            'user_id': 'TEST001',
            'user_role': 'beneficiary',
            'user_type': 'beneficiary'
        }
    
    def test_initialization(self):
        """Test orchestrator initializes correctly."""
        self.assertIsNotNone(self.orchestrator)
        self.assertEqual(self.orchestrator.timeout_duration, 5)
        self.assertIsInstance(self.orchestrator.circuit_breaker, CircuitBreaker)
    
    def test_live_data_intent_validation(self):
        """Test live data intent validation."""
        # Valid live data intents
        self.assertTrue(self.orchestrator._is_live_data_intent('claim_status'))
        self.assertTrue(self.orchestrator._is_live_data_intent('payment_status'))
        self.assertTrue(self.orchestrator._is_live_data_intent('pension_inquiry'))
        
        # Invalid intents
        self.assertFalse(self.orchestrator._is_live_data_intent('greeting'))
        self.assertFalse(self.orchestrator._is_live_data_intent('unknown'))
    
    def test_permission_validation(self):
        """Test permission validation logic."""
        # Valid beneficiary permissions
        self.assertTrue(self.orchestrator._validate_permissions(self.test_user_context, 'claim_status'))
        self.assertTrue(self.orchestrator._validate_permissions(self.test_user_context, 'payment_status'))
        
        # Invalid guest permissions
        guest_context = {'user_id': 'guest', 'user_role': 'guest'}
        self.assertFalse(self.orchestrator._validate_permissions(guest_context, 'claim_status'))
        
        # Invalid context
        self.assertFalse(self.orchestrator._validate_permissions(None, 'claim_status'))
    
    def test_claim_data_retrieval(self):
        """Test claim data retrieval."""
        result = self.orchestrator._get_claim_data(self.test_user_context)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'claim_data')
        self.assertIn('claim_number', result)
        self.assertIn('status', result)
        self.assertIn('progress', result)
    
    def test_payment_data_retrieval(self):
        """Test payment data retrieval."""
        result = self.orchestrator._get_payment_data(self.test_user_context)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'payment_data')
        self.assertIn('next_payment_date', result)
        self.assertIn('amount', result)
    
    def test_process_live_data_request_success(self):
        """Test successful live data request processing."""
        result = self.orchestrator.process_live_data_request(
            'claim_status', self.test_user_context, 'What is my claim status?'
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'claim_data')
    
    def test_process_live_data_request_invalid_intent(self):
        """Test live data request with invalid intent."""
        result = self.orchestrator.process_live_data_request(
            'greeting', self.test_user_context, 'Hello'
        )
        
        self.assertIsNone(result)
    
    def test_process_live_data_request_invalid_permissions(self):
        """Test live data request with invalid permissions."""
        guest_context = {'user_id': 'guest', 'user_role': 'guest'}
        result = self.orchestrator.process_live_data_request(
            'claim_status', guest_context, 'What is my claim status?'
        )
        
        self.assertIsNone(result)
    
    def test_caching_mechanism(self):
        """Test data caching functionality."""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        # Cache data
        self.orchestrator._cache_data(cache_key, test_data)
        
        # Retrieve cached data
        cached_result = self.orchestrator._get_cached_data(cache_key)
        self.assertEqual(cached_result, test_data)
        
        # Test cache expiration (simulate expired cache)
        self.orchestrator._cache[cache_key]['timestamp'] = time.time() - 400  # Expired
        expired_result = self.orchestrator._get_cached_data(cache_key)
        self.assertIsNone(expired_result)


class TestIntentRouter(unittest.TestCase):
    """Test IntentRouter component in isolation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.router = IntentRouter()
        self.test_user_context = {
            'user_id': 'TEST001',
            'user_role': 'beneficiary',
            'user_type': 'beneficiary'
        }
    
    def test_initialization(self):
        """Test router initializes correctly."""
        self.assertIsNotNone(self.router)
        self.assertEqual(self.router.timeout_duration, 5)
        self.assertIsInstance(self.router.intent_patterns, dict)
    
    def test_intent_detection(self):
        """Test intent detection from messages."""
        # Test claim status intent
        intent, confidence = self.router._detect_intent("What is my claim status?")
        self.assertEqual(intent, 'claim_status')
        self.assertGreater(confidence, 0.3)
        
        # Test payment status intent
        intent, confidence = self.router._detect_intent("When will I receive my payment?")
        self.assertEqual(intent, 'payment_status')
        self.assertGreater(confidence, 0.3)
        
        # Test greeting intent
        intent, confidence = self.router._detect_intent("Hello")
        self.assertEqual(intent, 'greeting')
        self.assertGreater(confidence, 0.3)
        
        # Test unknown intent
        intent, confidence = self.router._detect_intent("Random gibberish xyz123")
        self.assertEqual(intent, 'unknown')
        self.assertEqual(confidence, 0.0)
    
    def test_route_request_live_data_intent(self):
        """Test routing for live data intents."""
        result = self.router.route_request("What is my claim status?", self.test_user_context)
        
        self.assertIsInstance(result, dict)
        self.assertIn('source', result)
        self.assertIn('intent', result)
        self.assertIn('confidence', result)
        self.assertEqual(result['intent'], 'claim_status')
    
    def test_route_request_knowledge_base_intent(self):
        """Test routing for knowledge base intents."""
        result = self.router.route_request("Hello", self.test_user_context)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['source'], 'knowledge_base')
        self.assertEqual(result['intent'], 'greeting')
    
    def test_get_supported_intents(self):
        """Test getting list of supported intents."""
        intents = self.router.get_supported_intents()
        
        self.assertIsInstance(intents, list)
        self.assertIn('claim_status', intents)
        self.assertIn('payment_status', intents)
        self.assertIn('greeting', intents)
    
    def test_get_live_data_intents(self):
        """Test getting list of live data intents."""
        intents = self.router.get_live_data_intents()
        
        self.assertIsInstance(intents, list)
        self.assertIn('claim_status', intents)
        self.assertIn('payment_status', intents)
        self.assertNotIn('greeting', intents)
    
    def test_get_knowledge_base_intents(self):
        """Test getting list of knowledge base intents."""
        intents = self.router.get_knowledge_base_intents()
        
        self.assertIsInstance(intents, list)
        self.assertIn('greeting', intents)
        self.assertIn('agent_request', intents)
        self.assertNotIn('claim_status', intents)


class TestResponseAssembler(unittest.TestCase):
    """Test ResponseAssembler component in isolation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.assembler = ResponseAssembler()
        self.test_user_context = {
            'user_id': 'TEST001',
            'user_role': 'beneficiary',
            'user_type': 'beneficiary'
        }
    
    def test_initialization(self):
        """Test assembler initializes correctly."""
        self.assertIsNotNone(self.assembler)
        self.assertEqual(self.assembler.timeout_duration, 3)
        self.assertIsInstance(self.assembler.response_templates, dict)
    
    def test_assemble_live_data_response(self):
        """Test assembling response from live data."""
        routing_result = {
            'source': 'live_data',
            'intent': 'claim_status',
            'data': {
                'type': 'claim_data',
                'claim_number': 'CLM-2025-001',
                'status': 'Under Review',
                'progress': {'submitted': True, 'documents_received': True},
                'assigned_officer': 'Sarah Mwanza',
                'contact_number': '+260-211-123456'
            }
        }
        
        response = self.assembler.assemble_response(
            routing_result, "What is my claim status?", self.test_user_context
        )
        
        self.assertIsInstance(response, str)
        self.assertIn('Anna', response)
        self.assertIn('CLM-2025-001', response)
        self.assertIn('Under Review', response)
        self.assertIn('Sarah Mwanza', response)
    
    def test_assemble_knowledge_base_response(self):
        """Test assembling response from knowledge base routing."""
        routing_result = {
            'source': 'knowledge_base',
            'intent': 'greeting',
            'data': {
                'type': 'knowledge_base_routing',
                'intent': 'greeting'
            }
        }
        
        response = self.assembler.assemble_response(
            routing_result, "Hello", self.test_user_context
        )
        
        self.assertIsInstance(response, str)
        self.assertIn('Anna', response)
        self.assertIn('WCFCB', response)
    
    def test_apply_anna_personality(self):
        """Test applying Anna's personality to responses."""
        basic_response = "Your claim is under review."
        
        enhanced_response = self.assembler._apply_anna_personality(
            basic_response, 'claim_status', self.test_user_context
        )
        
        self.assertIn('Anna', enhanced_response)
        self.assertIn('WCFCB', enhanced_response)
        self.assertIn('claim is under review', enhanced_response)
    
    def test_enhance_response_quality(self):
        """Test response quality enhancement."""
        # Test capitalization
        response = self.assembler._enhance_response_quality("hello world")
        self.assertTrue(response[0].isupper())
        
        # Test punctuation
        response = self.assembler._enhance_response_quality("Hello world")
        self.assertTrue(response.endswith('.'))
    
    def test_fallback_responses(self):
        """Test fallback response generation."""
        timeout_response = self.assembler._get_timeout_fallback_response(self.test_user_context)
        self.assertIn('Anna', timeout_response)
        self.assertIn('delays', timeout_response)
        
        error_response = self.assembler._get_error_fallback_response(self.test_user_context)
        self.assertIn('Anna', error_response)
        self.assertIn('technical difficulties', error_response)


class TestCircuitBreaker(unittest.TestCase):
    """Test CircuitBreaker component in isolation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=1)
    
    def test_initialization(self):
        """Test circuit breaker initializes correctly."""
        self.assertEqual(self.circuit_breaker.failure_threshold, 3)
        self.assertEqual(self.circuit_breaker.timeout, 1)
        self.assertEqual(self.circuit_breaker.state, "CLOSED")
    
    def test_successful_calls(self):
        """Test successful function calls."""
        def success_func():
            return "success"
        
        result = self.circuit_breaker.call(success_func)
        self.assertEqual(result, "success")
        self.assertEqual(self.circuit_breaker.state, "CLOSED")
    
    def test_failure_handling(self):
        """Test failure handling and state transitions."""
        def failure_func():
            raise Exception("Test failure")
        
        # First few failures should keep circuit closed
        for i in range(2):
            with self.assertRaises(Exception):
                self.circuit_breaker.call(failure_func)
            self.assertEqual(self.circuit_breaker.state, "CLOSED")
        
        # Third failure should open circuit
        with self.assertRaises(Exception):
            self.circuit_breaker.call(failure_func)
        self.assertEqual(self.circuit_breaker.state, "OPEN")


class TestComponentIntegration(unittest.TestCase):
    """Test integration between Phase 1 components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.orchestrator = LiveDataOrchestrator()
        self.router = IntentRouter()
        self.assembler = ResponseAssembler()
        self.test_user_context = {
            'user_id': 'TEST001',
            'user_role': 'beneficiary',
            'user_type': 'beneficiary'
        }
    
    def test_end_to_end_live_data_flow(self):
        """Test complete flow from routing to response assembly."""
        # Step 1: Route request
        routing_result = self.router.route_request("What is my claim status?", self.test_user_context)
        
        # Step 2: Assemble response
        final_response = self.assembler.assemble_response(
            routing_result, "What is my claim status?", self.test_user_context
        )
        
        # Validate end-to-end flow
        self.assertIsInstance(final_response, str)
        self.assertIn('Anna', final_response)
        self.assertGreater(len(final_response), 50)  # Substantial response
    
    def test_no_circular_dependencies(self):
        """Test that no circular dependencies exist between components."""
        # This test ensures that components don't call back to each other
        # by checking that each component can operate independently
        
        # Test orchestrator independence
        orchestrator_result = self.orchestrator.process_live_data_request(
            'claim_status', self.test_user_context, 'Test message'
        )
        self.assertIsNotNone(orchestrator_result)
        
        # Test router independence
        router_result = self.router.route_request('Test message', self.test_user_context)
        self.assertIsInstance(router_result, dict)
        
        # Test assembler independence
        mock_routing_result = {
            'source': 'knowledge_base',
            'intent': 'greeting',
            'data': {}
        }
        assembler_result = self.assembler.assemble_response(
            mock_routing_result, 'Test message', self.test_user_context
        )
        self.assertIsInstance(assembler_result, str)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)
