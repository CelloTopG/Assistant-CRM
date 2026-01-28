#!/usr/bin/env python3
"""
Phase 5: Comprehensive Testing and Validation Suite
==================================================

Systematic testing framework for WCFCB Assistant CRM chatbot system.
Validates all user types, API integrations, performance, security, and regression testing.

Test Categories:
1. User Type Testing (4 roles)
2. API Integration Testing
3. Performance Validation
4. Security Testing (RBAC)
5. Regression Testing
6. Error Handling Testing
7. Anna Personality & WCFCB Branding Testing
"""

import sys
import time
import json
import threading
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Any, Tuple
sys.path.append('/workspace/development/frappe-bench/apps/assistant_crm')

class Phase5TestSuite:
    """Comprehensive testing suite for Phase 5 validation"""
    
    def __init__(self):
        self.test_results = {
            'user_type_testing': {},
            'api_integration_testing': {},
            'performance_validation': {},
            'security_testing': {},
            'regression_testing': {},
            'error_handling_testing': {},
            'anna_branding_testing': {}
        }
        
        self.performance_metrics = {
            'response_times': [],
            'success_rates': [],
            'error_rates': [],
            'load_test_results': []
        }
        
        self.user_roles = ['beneficiary', 'employer', 'supplier', 'wcfcb_staff']
        self.test_messages = [
            'Hello Anna',
            'What services do you offer?',
            'Can you help me with my claim?',
            'I need to submit a payment',
            'What documents do I need?',
            'Can you check my account status?',
            'I have a complaint',
            'What are your office hours?',
            'How do I contact support?',
            'I need help with my benefits'
        ]
        
        self.start_time = None
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

    def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Execute complete Phase 5 test suite"""
        print("🚀 PHASE 5: COMPREHENSIVE TESTING AND VALIDATION")
        print("=" * 60)
        
        self.start_time = time.time()
        
        # Test Category 1: User Type Testing
        print("\n📋 TEST CATEGORY 1: USER TYPE TESTING")
        self.test_user_types()
        
        # Test Category 2: API Integration Testing
        print("\n📋 TEST CATEGORY 2: API INTEGRATION TESTING")
        self.test_api_integrations()
        
        # Test Category 3: Performance Validation
        print("\n📋 TEST CATEGORY 3: PERFORMANCE VALIDATION")
        self.test_performance_validation()
        
        # Test Category 4: Security Testing (RBAC)
        print("\n📋 TEST CATEGORY 4: SECURITY TESTING (RBAC)")
        self.test_security_rbac()
        
        # Test Category 5: Regression Testing
        print("\n📋 TEST CATEGORY 5: REGRESSION TESTING")
        self.test_regression_validation()
        
        # Test Category 6: Error Handling Testing
        print("\n📋 TEST CATEGORY 6: ERROR HANDLING TESTING")
        self.test_error_handling()
        
        # Test Category 7: Anna Personality & WCFCB Branding
        print("\n📋 TEST CATEGORY 7: ANNA PERSONALITY & WCFCB BRANDING")
        self.test_anna_branding()
        
        # Generate comprehensive report
        return self.generate_test_report()

    def test_user_types(self):
        """Test Category 1: User Type Testing for all four roles"""
        print("Testing all user roles with role-specific scenarios...")
        
        for role in self.user_roles:
            print(f"\n  Testing {role} role:")
            role_results = self.test_single_user_role(role)
            self.test_results['user_type_testing'][role] = role_results
            
            # Display results
            passed = sum(1 for r in role_results.values() if r.get('passed', False))
            total = len(role_results)
            print(f"    ✅ {role}: {passed}/{total} tests passed")

    def test_single_user_role(self, role: str) -> Dict[str, Any]:
        """Test specific user role with role-appropriate scenarios"""
        role_results = {}
        
        try:
            # Import APIs
            from assistant_crm.api.unified_chat_api import process_message
            from assistant_crm.api.chatbot import ask_bot
            
            user_context = {
                'user_id': f'{role.upper()}001',
                'user_role': role,
                'user_type': role
            }
            
            # Test role-specific scenarios
            role_scenarios = self.get_role_specific_scenarios(role)
            
            for scenario_name, message in role_scenarios.items():
                try:
                    # Test unified API
                    start_time = time.time()
                    unified_result = process_message(message, user_context=user_context)
                    unified_time = time.time() - start_time
                    
                    # Test chatbot API
                    start_time = time.time()
                    chatbot_result = ask_bot(message, user_context=user_context)
                    chatbot_time = time.time() - start_time
                    
                    # Validate results
                    role_results[scenario_name] = {
                        'passed': (unified_result.get('success') and chatbot_result.get('success')),
                        'unified_api': {
                            'success': unified_result.get('success'),
                            'response_time': unified_time,
                            'has_user_profile': 'user_profile' in unified_result,
                            'user_role_correct': unified_result.get('user_profile', {}).get('user_role') == role if 'user_profile' in unified_result else False
                        },
                        'chatbot_api': {
                            'success': chatbot_result.get('success'),
                            'response_time': chatbot_time,
                            'has_reply': bool(chatbot_result.get('reply'))
                        },
                        'anna_present': 'Anna' in (unified_result.get('reply', '') + chatbot_result.get('reply', '')),
                        'wcfcb_present': 'WCFCB' in (unified_result.get('reply', '') + chatbot_result.get('reply', ''))
                    }
                    
                    self.total_tests += 1
                    if role_results[scenario_name]['passed']:
                        self.passed_tests += 1
                    else:
                        self.failed_tests += 1
                        
                except Exception as e:
                    role_results[scenario_name] = {
                        'passed': False,
                        'error': str(e)
                    }
                    self.total_tests += 1
                    self.failed_tests += 1
                    
        except Exception as e:
            role_results['import_error'] = {
                'passed': False,
                'error': f"Failed to import APIs: {str(e)}"
            }
            
        return role_results

    def get_role_specific_scenarios(self, role: str) -> Dict[str, str]:
        """Get role-specific test scenarios"""
        scenarios = {
            'beneficiary': {
                'greeting': 'Hello Anna',
                'claim_inquiry': 'Can you help me with my claim?',
                'payment_status': 'What is my payment status?',
                'benefit_info': 'What benefits am I entitled to?',
                'document_request': 'What documents do I need to submit?'
            },
            'employer': {
                'greeting': 'Hello Anna',
                'contribution_inquiry': 'How do I submit contributions?',
                'employee_management': 'How do I add new employees?',
                'compliance_check': 'What are my compliance requirements?',
                'return_submission': 'How do I submit my returns?'
            },
            'supplier': {
                'greeting': 'Hello Anna',
                'contract_inquiry': 'Can you help me with my contract?',
                'invoice_submission': 'How do I submit an invoice?',
                'payment_inquiry': 'When will I receive payment?',
                'tender_information': 'Are there any new tenders?'
            },
            'wcfcb_staff': {
                'greeting': 'Hello Anna',
                'claim_management': 'I need to process a claim',
                'report_generation': 'How do I generate reports?',
                'system_administration': 'I need admin access',
                'data_inquiry': 'Can you show me system statistics?'
            }
        }
        
        return scenarios.get(role, {'greeting': 'Hello Anna'})

    def test_api_integrations(self):
        """Test Category 2: API Integration Testing"""
        print("Testing API integrations with various contexts...")
        
        api_tests = {
            'unified_api_basic': self.test_unified_api_basic,
            'unified_api_with_context': self.test_unified_api_with_context,
            'chatbot_api_basic': self.test_chatbot_api_basic,
            'chatbot_api_with_context': self.test_chatbot_api_with_context,
            'api_consistency': self.test_api_consistency,
            'edge_cases': self.test_api_edge_cases
        }
        
        for test_name, test_func in api_tests.items():
            try:
                result = test_func()
                self.test_results['api_integration_testing'][test_name] = result
                status = "✅ PASSED" if result.get('passed') else "❌ FAILED"
                print(f"  {test_name}: {status}")
                
                self.total_tests += 1
                if result.get('passed'):
                    self.passed_tests += 1
                else:
                    self.failed_tests += 1
                    
            except Exception as e:
                self.test_results['api_integration_testing'][test_name] = {
                    'passed': False,
                    'error': str(e)
                }
                print(f"  {test_name}: ❌ FAILED - {str(e)}")
                self.total_tests += 1
                self.failed_tests += 1

    def test_unified_api_basic(self) -> Dict[str, Any]:
        """Test unified API basic functionality"""
        try:
            from assistant_crm.api.unified_chat_api import process_message
            
            start_time = time.time()
            result = process_message("Hello Anna")
            response_time = time.time() - start_time
            
            return {
                'passed': result.get('success', False),
                'response_time': response_time,
                'has_reply': bool(result.get('reply')),
                'anna_personality': result.get('anna_personality', False),
                'wcfcb_branding': result.get('wcfcb_branding', False),
                'performance_target_met': response_time < 2.0
            }
            
        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_unified_api_with_context(self) -> Dict[str, Any]:
        """Test unified API with user context"""
        try:
            from assistant_crm.api.unified_chat_api import process_message
            
            user_context = {'user_id': 'TEST001', 'user_role': 'beneficiary'}
            start_time = time.time()
            result = process_message("Can you check my claim status?", user_context=user_context)
            response_time = time.time() - start_time
            
            return {
                'passed': result.get('success', False),
                'response_time': response_time,
                'has_user_profile': 'user_profile' in result,
                'user_context_processed': result.get('user_profile', {}).get('user_role') == 'beneficiary' if 'user_profile' in result else False,
                'performance_target_met': response_time < 2.0
            }
            
        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_performance_validation(self):
        """Test Category 3: Performance Validation"""
        print("Testing performance under various conditions...")

        performance_tests = {
            'single_request_performance': self.test_single_request_performance,
            'concurrent_requests': self.test_concurrent_requests,
            'load_testing': self.test_load_testing,
            'memory_usage': self.test_memory_usage,
            'response_time_consistency': self.test_response_time_consistency
        }

        for test_name, test_func in performance_tests.items():
            try:
                result = test_func()
                self.test_results['performance_validation'][test_name] = result
                status = "✅ PASSED" if result.get('passed') else "❌ FAILED"
                print(f"  {test_name}: {status}")

                self.total_tests += 1
                if result.get('passed'):
                    self.passed_tests += 1
                else:
                    self.failed_tests += 1

            except Exception as e:
                self.test_results['performance_validation'][test_name] = {
                    'passed': False,
                    'error': str(e)
                }
                print(f"  {test_name}: ❌ FAILED - {str(e)}")
                self.total_tests += 1
                self.failed_tests += 1

    def test_single_request_performance(self) -> Dict[str, Any]:
        """Test single request performance"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            response_times = []
            success_count = 0

            for message in self.test_messages[:5]:  # Test with 5 messages
                start_time = time.time()
                result = process_message(message)
                response_time = time.time() - start_time

                response_times.append(response_time)
                if result.get('success'):
                    success_count += 1

            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)

            return {
                'passed': avg_response_time < 2.0 and max_response_time < 2.0,
                'average_response_time': avg_response_time,
                'max_response_time': max_response_time,
                'success_rate': success_count / len(response_times),
                'target_met': avg_response_time < 2.0,
                'all_under_target': max_response_time < 2.0
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_concurrent_requests(self) -> Dict[str, Any]:
        """Test concurrent request handling"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            def make_request(message):
                start_time = time.time()
                result = process_message(message)
                response_time = time.time() - start_time
                return {
                    'success': result.get('success'),
                    'response_time': response_time,
                    'message': message
                }

            # Test with 10 concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request, f"Test message {i}") for i in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

            success_count = sum(1 for r in results if r['success'])
            response_times = [r['response_time'] for r in results]
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)

            return {
                'passed': success_count >= 8 and avg_response_time < 2.0,  # Allow 2 failures out of 10
                'concurrent_requests': len(results),
                'successful_requests': success_count,
                'success_rate': success_count / len(results),
                'average_response_time': avg_response_time,
                'max_response_time': max_response_time,
                'performance_target_met': avg_response_time < 2.0
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_load_testing(self) -> Dict[str, Any]:
        """Test system under load"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            # Simulate load with 50 requests
            total_requests = 50
            successful_requests = 0
            response_times = []

            start_load_test = time.time()

            for i in range(total_requests):
                message = self.test_messages[i % len(self.test_messages)]

                start_time = time.time()
                result = process_message(message)
                response_time = time.time() - start_time

                response_times.append(response_time)
                if result.get('success'):
                    successful_requests += 1

            total_load_test_time = time.time() - start_load_test

            avg_response_time = sum(response_times) / len(response_times)
            success_rate = successful_requests / total_requests
            requests_per_second = total_requests / total_load_test_time

            return {
                'passed': success_rate >= 0.95 and avg_response_time < 2.0,
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'success_rate': success_rate,
                'average_response_time': avg_response_time,
                'max_response_time': max(response_times),
                'min_response_time': min(response_times),
                'requests_per_second': requests_per_second,
                'total_test_time': total_load_test_time,
                'performance_target_met': avg_response_time < 2.0
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_memory_usage(self) -> Dict[str, Any]:
        """Test memory usage during operations"""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Perform multiple operations
            from assistant_crm.api.unified_chat_api import process_message

            for i in range(20):
                process_message(f"Test message {i}")

            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            return {
                'passed': memory_increase < 50,  # Less than 50MB increase
                'initial_memory_mb': initial_memory,
                'final_memory_mb': final_memory,
                'memory_increase_mb': memory_increase,
                'memory_target_met': memory_increase < 50
            }

        except ImportError:
            return {
                'passed': True,  # Skip if psutil not available
                'skipped': True,
                'reason': 'psutil not available'
            }
        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_response_time_consistency(self) -> Dict[str, Any]:
        """Test response time consistency"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            response_times = []

            # Test same message multiple times
            for i in range(10):
                start_time = time.time()
                result = process_message("Hello Anna")
                response_time = time.time() - start_time
                response_times.append(response_time)

            avg_time = sum(response_times) / len(response_times)
            variance = sum((t - avg_time) ** 2 for t in response_times) / len(response_times)
            std_deviation = variance ** 0.5

            # Check consistency (low standard deviation)
            consistent = std_deviation < 0.1  # Less than 100ms standard deviation

            return {
                'passed': consistent and avg_time < 2.0,
                'average_response_time': avg_time,
                'standard_deviation': std_deviation,
                'min_time': min(response_times),
                'max_time': max(response_times),
                'consistency_target_met': consistent,
                'performance_target_met': avg_time < 2.0,
                'response_times': response_times
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_security_rbac(self):
        """Test Category 4: Security Testing (RBAC)"""
        print("Testing role-based access control and security...")

        security_tests = {
            'role_permission_validation': self.test_role_permissions,
            'data_access_control': self.test_data_access_control,
            'unauthorized_access_prevention': self.test_unauthorized_access,
            'session_security': self.test_session_security,
            'data_filtering': self.test_data_filtering
        }

        for test_name, test_func in security_tests.items():
            try:
                result = test_func()
                self.test_results['security_testing'][test_name] = result
                status = "✅ PASSED" if result.get('passed') else "❌ FAILED"
                print(f"  {test_name}: {status}")

                self.total_tests += 1
                if result.get('passed'):
                    self.passed_tests += 1
                else:
                    self.failed_tests += 1

            except Exception as e:
                self.test_results['security_testing'][test_name] = {
                    'passed': False,
                    'error': str(e)
                }
                print(f"  {test_name}: ❌ FAILED - {str(e)}")
                self.total_tests += 1
                self.failed_tests += 1

    def test_role_permissions(self) -> Dict[str, Any]:
        """Test role-based permission validation"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            role_permission_tests = {}
            all_roles_valid = True

            for role in self.user_roles:
                user_context = {'user_id': f'{role.upper()}001', 'user_role': role}
                result = process_message("What can I access?", user_context=user_context)

                if result.get('success') and 'user_profile' in result:
                    profile = result['user_profile']
                    has_permissions = bool(profile.get('permissions'))
                    correct_role = profile.get('user_role') == role
                    has_session_permissions = bool(profile.get('session_permissions'))

                    role_permission_tests[role] = {
                        'has_permissions': has_permissions,
                        'correct_role': correct_role,
                        'has_session_permissions': has_session_permissions,
                        'valid': has_permissions and correct_role and has_session_permissions
                    }

                    if not (has_permissions and correct_role and has_session_permissions):
                        all_roles_valid = False
                else:
                    role_permission_tests[role] = {'valid': False, 'error': 'No user profile or failed request'}
                    all_roles_valid = False

            return {
                'passed': all_roles_valid,
                'role_tests': role_permission_tests,
                'total_roles': len(self.user_roles),
                'valid_roles': sum(1 for r in role_permission_tests.values() if r.get('valid', False))
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_data_access_control(self) -> Dict[str, Any]:
        """Test data access control based on roles"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            # Test different roles accessing sensitive data
            sensitive_queries = [
                "Show me all user data",
                "Give me admin access",
                "Show me financial reports",
                "Access system configuration"
            ]

            access_control_results = {}

            for role in ['beneficiary', 'employer', 'wcfcb_staff']:
                user_context = {'user_id': f'{role.upper()}001', 'user_role': role}
                role_results = {}

                for query in sensitive_queries:
                    result = process_message(query, user_context=user_context)

                    # Staff should have broader access, others should be restricted
                    if role == 'wcfcb_staff':
                        # Staff should get helpful responses
                        appropriate_response = result.get('success', False)
                    else:
                        # Non-staff should get general responses, not sensitive data
                        reply = result.get('reply', '').lower()
                        appropriate_response = not any(sensitive in reply for sensitive in ['admin', 'system', 'configuration', 'all users'])

                    role_results[query] = {
                        'appropriate_response': appropriate_response,
                        'success': result.get('success', False)
                    }

                access_control_results[role] = role_results

            # Check if access control is working
            all_appropriate = True
            for role_data in access_control_results.values():
                for query_result in role_data.values():
                    if not query_result['appropriate_response']:
                        all_appropriate = False
                        break

            return {
                'passed': all_appropriate,
                'access_control_results': access_control_results,
                'total_queries_tested': len(sensitive_queries) * 3,
                'appropriate_responses': sum(
                    sum(1 for q in role_data.values() if q['appropriate_response'])
                    for role_data in access_control_results.values()
                )
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_unauthorized_access(self) -> Dict[str, Any]:
        """Test prevention of unauthorized access"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            # Test with invalid/malicious contexts
            unauthorized_contexts = [
                {'user_id': 'ADMIN', 'user_role': 'admin'},  # Invalid role
                {'user_id': '../../../etc/passwd', 'user_role': 'beneficiary'},  # Path injection
                {'user_id': 'DROP TABLE users;', 'user_role': 'beneficiary'},  # SQL injection attempt
                {'user_id': '<script>alert("xss")</script>', 'user_role': 'beneficiary'},  # XSS attempt
                None  # No context
            ]

            unauthorized_results = {}
            all_handled_safely = True

            for i, context in enumerate(unauthorized_contexts):
                try:
                    result = process_message("Give me admin access", user_context=context)

                    # Should handle gracefully without giving admin access
                    handled_safely = (
                        result.get('success') is not None and  # Should not crash
                        'admin' not in result.get('reply', '').lower() and  # Should not grant admin
                        'error' not in result.get('reply', '').lower()  # Should not expose errors
                    )

                    unauthorized_results[f'test_{i}'] = {
                        'handled_safely': handled_safely,
                        'success': result.get('success'),
                        'context': str(context)[:50] if context else 'None'
                    }

                    if not handled_safely:
                        all_handled_safely = False

                except Exception as e:
                    unauthorized_results[f'test_{i}'] = {
                        'handled_safely': False,
                        'error': str(e),
                        'context': str(context)[:50] if context else 'None'
                    }
                    all_handled_safely = False

            return {
                'passed': all_handled_safely,
                'unauthorized_tests': unauthorized_results,
                'total_tests': len(unauthorized_contexts),
                'safely_handled': sum(1 for r in unauthorized_results.values() if r.get('handled_safely', False))
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_session_security(self) -> Dict[str, Any]:
        """Test session security and management"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            # Test session generation and consistency
            result1 = process_message("Hello", user_context={'user_id': 'TEST001', 'user_role': 'beneficiary'})
            result2 = process_message("Hello again", session_id=result1.get('session_id'), user_context={'user_id': 'TEST001', 'user_role': 'beneficiary'})

            session1 = result1.get('session_id')
            session2 = result2.get('session_id')

            # Sessions should be consistent when provided
            session_consistency = session1 == session2 if session1 and session2 else False

            # Test session without user context
            result3 = process_message("Hello anonymous")
            session3 = result3.get('session_id')

            return {
                'passed': bool(session1) and bool(session3) and session_consistency,
                'session_generated_with_context': bool(session1),
                'session_generated_without_context': bool(session3),
                'session_consistency': session_consistency,
                'different_sessions': session1 != session3 if session1 and session3 else False
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_data_filtering(self) -> Dict[str, Any]:
        """Test data filtering based on user permissions"""
        try:
            from assistant_crm.services.user_identification_service import UserIdentificationService

            if not UserIdentificationService:
                return {'passed': True, 'skipped': True, 'reason': 'UserIdentificationService not available'}

            service = UserIdentificationService()

            # Test data filtering for different roles
            test_data = {
                'personal_info': 'John Doe personal data',
                'company_info': 'Company ABC data',
                'payment_history': 'Payment records',
                'admin_data': 'Administrative information',
                'public_info': 'Public information'
            }

            filtering_results = {}

            for role in self.user_roles:
                user_profile = {
                    'user_role': role,
                    'data_access': service.get_user_role_config(role)['data_access']
                }

                filtered_data = service.filter_data_by_permissions(user_profile, test_data)

                # Check if filtering is appropriate
                if role == 'wcfcb_staff':
                    # Staff should see all data
                    appropriate_filtering = len(filtered_data) >= len(test_data) * 0.8  # At least 80%
                else:
                    # Others should see limited data
                    appropriate_filtering = len(filtered_data) <= len(test_data) * 0.6  # At most 60%

                filtering_results[role] = {
                    'original_data_count': len(test_data),
                    'filtered_data_count': len(filtered_data),
                    'appropriate_filtering': appropriate_filtering,
                    'filtered_keys': list(filtered_data.keys())
                }

            all_appropriate = all(r['appropriate_filtering'] for r in filtering_results.values())

            return {
                'passed': all_appropriate,
                'filtering_results': filtering_results,
                'total_roles_tested': len(self.user_roles)
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_regression_validation(self):
        """Test Category 5: Regression Testing"""
        print("Testing for regressions from previous phases...")

        regression_tests = {
            'phase1_streamlined_service': self.test_phase1_regression,
            'phase2_knowledge_base': self.test_phase2_regression,
            'phase3_frontend_backend': self.test_phase3_regression,
            'phase4_user_identification': self.test_phase4_regression,
            'existing_functionality': self.test_existing_functionality
        }

        for test_name, test_func in regression_tests.items():
            try:
                result = test_func()
                self.test_results['regression_testing'][test_name] = result
                status = "✅ PASSED" if result.get('passed') else "❌ FAILED"
                print(f"  {test_name}: {status}")

                self.total_tests += 1
                if result.get('passed'):
                    self.passed_tests += 1
                else:
                    self.failed_tests += 1

            except Exception as e:
                self.test_results['regression_testing'][test_name] = {
                    'passed': False,
                    'error': str(e)
                }
                print(f"  {test_name}: ❌ FAILED - {str(e)}")
                self.total_tests += 1
                self.failed_tests += 1

    def test_phase1_regression(self) -> Dict[str, Any]:
        """Test Phase 1 (Streamlined Service) functionality"""
        try:
            from assistant_crm.api.unified_chat_api import process_message
            from assistant_crm.api.chatbot import ask_bot

            # Test basic chatbot functionality
            basic_messages = ['Hello', 'Help', 'What services do you offer?']

            unified_results = []
            chatbot_results = []

            for message in basic_messages:
                unified_result = process_message(message)
                chatbot_result = ask_bot(message)

                unified_results.append(unified_result.get('success', False))
                chatbot_results.append(chatbot_result.get('success', False))

            unified_success_rate = sum(unified_results) / len(unified_results)
            chatbot_success_rate = sum(chatbot_results) / len(chatbot_results)

            return {
                'passed': unified_success_rate >= 0.9 and chatbot_success_rate >= 0.9,
                'unified_success_rate': unified_success_rate,
                'chatbot_success_rate': chatbot_success_rate,
                'total_messages_tested': len(basic_messages)
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_phase2_regression(self) -> Dict[str, Any]:
        """Test Phase 2 (Knowledge Base) functionality"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            # Test knowledge base queries
            kb_queries = [
                'What documents do I need?',
                'How do I submit a claim?',
                'What are your office hours?',
                'How do I contact support?'
            ]

            kb_results = []
            response_quality = []

            for query in kb_queries:
                result = process_message(query)
                kb_results.append(result.get('success', False))

                # Check response quality (should have substantive content)
                reply = result.get('reply', '')
                quality = len(reply) > 20 and ('WCFCB' in reply or 'Anna' in reply)
                response_quality.append(quality)

            success_rate = sum(kb_results) / len(kb_results)
            quality_rate = sum(response_quality) / len(response_quality)

            return {
                'passed': success_rate >= 0.9 and quality_rate >= 0.8,
                'success_rate': success_rate,
                'quality_rate': quality_rate,
                'total_queries_tested': len(kb_queries)
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_phase3_regression(self) -> Dict[str, Any]:
        """Test Phase 3 (Frontend-Backend Alignment) functionality"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            # Test unified API functionality
            result = process_message('Hello Anna')

            # Check standardized response format
            required_fields = ['success', 'reply', 'session_id', 'timestamp', 'user',
                             'live_data_used', 'data_sources', 'anna_personality',
                             'wcfcb_branding', 'response_time']

            has_all_fields = all(field in result for field in required_fields)

            # Check performance
            response_time = result.get('response_time', 999)
            performance_ok = response_time < 2.0

            return {
                'passed': result.get('success', False) and has_all_fields and performance_ok,
                'has_standardized_format': has_all_fields,
                'performance_target_met': performance_ok,
                'response_time': response_time,
                'missing_fields': [f for f in required_fields if f not in result]
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_phase4_regression(self) -> Dict[str, Any]:
        """Test Phase 4 (User Identification) functionality"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            # Test user identification functionality
            user_context = {'user_id': 'TEST001', 'user_role': 'beneficiary'}
            result = process_message('Hello Anna', user_context=user_context)

            # Check user profile integration
            has_user_profile = 'user_profile' in result
            user_profile = result.get('user_profile', {})

            profile_complete = (
                user_profile.get('user_id') == 'TEST001' and
                user_profile.get('user_role') == 'beneficiary' and
                bool(user_profile.get('permissions')) and
                bool(user_profile.get('session_permissions'))
            ) if has_user_profile else False

            return {
                'passed': result.get('success', False) and has_user_profile and profile_complete,
                'has_user_profile': has_user_profile,
                'profile_complete': profile_complete,
                'user_identification_working': has_user_profile and profile_complete
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_existing_functionality(self) -> Dict[str, Any]:
        """Test that all existing functionality still works"""
        try:
            from assistant_crm.api.unified_chat_api import process_message
            from assistant_crm.api.chatbot import ask_bot

            # Test core functionality that should always work
            core_tests = {
                'basic_greeting': 'Hello',
                'service_inquiry': 'What services do you offer?',
                'help_request': 'I need help',
                'contact_info': 'How do I contact you?'
            }

            functionality_results = {}

            for test_name, message in core_tests.items():
                # Test both APIs
                unified_result = process_message(message)
                chatbot_result = ask_bot(message)

                functionality_results[test_name] = {
                    'unified_success': unified_result.get('success', False),
                    'chatbot_success': chatbot_result.get('success', False),
                    'both_successful': unified_result.get('success', False) and chatbot_result.get('success', False),
                    'unified_has_reply': bool(unified_result.get('reply')),
                    'chatbot_has_reply': bool(chatbot_result.get('reply'))
                }

            all_working = all(r['both_successful'] for r in functionality_results.values())

            return {
                'passed': all_working,
                'functionality_results': functionality_results,
                'total_tests': len(core_tests),
                'working_tests': sum(1 for r in functionality_results.values() if r['both_successful'])
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_error_handling(self):
        """Test Category 6: Error Handling Testing"""
        print("Testing error handling and system resilience...")

        error_tests = {
            'graceful_fallbacks': self.test_graceful_fallbacks,
            'service_unavailability': self.test_service_unavailability,
            'invalid_inputs': self.test_invalid_inputs,
            'system_resilience': self.test_system_resilience
        }

        for test_name, test_func in error_tests.items():
            try:
                result = test_func()
                self.test_results['error_handling_testing'][test_name] = result
                status = "✅ PASSED" if result.get('passed') else "❌ FAILED"
                print(f"  {test_name}: {status}")

                self.total_tests += 1
                if result.get('passed'):
                    self.passed_tests += 1
                else:
                    self.failed_tests += 1

            except Exception as e:
                self.test_results['error_handling_testing'][test_name] = {
                    'passed': False,
                    'error': str(e)
                }
                print(f"  {test_name}: ❌ FAILED - {str(e)}")
                self.total_tests += 1
                self.failed_tests += 1

    def test_graceful_fallbacks(self) -> Dict[str, Any]:
        """Test graceful fallback mechanisms"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            # Test various scenarios that should fallback gracefully
            fallback_scenarios = [
                ('empty_message', ''),
                ('whitespace_only', '   '),
                ('very_long_message', 'help ' * 200),
                ('special_characters', '!@#$%^&*()'),
                ('numbers_only', '12345'),
                ('mixed_content', 'Hello 123 !@# test')
            ]

            fallback_results = {}
            all_graceful = True

            for scenario_name, message in fallback_scenarios:
                result = process_message(message)

                # Should handle gracefully (not crash) and provide some response
                graceful = (
                    result is not None and
                    'success' in result and
                    (result.get('success') or bool(result.get('reply')))  # Either success or error message
                )

                fallback_results[scenario_name] = {
                    'graceful': graceful,
                    'success': result.get('success') if result else False,
                    'has_reply': bool(result.get('reply')) if result else False
                }

                if not graceful:
                    all_graceful = False

            return {
                'passed': all_graceful,
                'fallback_results': fallback_results,
                'total_scenarios': len(fallback_scenarios),
                'graceful_scenarios': sum(1 for r in fallback_results.values() if r['graceful'])
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_service_unavailability(self) -> Dict[str, Any]:
        """Test behavior when services are unavailable"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            # Test with various user contexts that might cause service issues
            test_contexts = [
                None,
                {},
                {'user_id': None},
                {'user_role': 'invalid_role'},
                {'user_id': 'NONEXISTENT', 'user_role': 'beneficiary'}
            ]

            unavailability_results = {}
            all_handled = True

            for i, context in enumerate(test_contexts):
                try:
                    result = process_message("Hello Anna", user_context=context)

                    # Should handle gracefully even if services are unavailable
                    handled = (
                        result is not None and
                        result.get('success') is not None and
                        bool(result.get('reply'))
                    )

                    unavailability_results[f'context_{i}'] = {
                        'handled': handled,
                        'success': result.get('success') if result else False,
                        'context': str(context)[:50] if context else 'None'
                    }

                    if not handled:
                        all_handled = False

                except Exception as e:
                    unavailability_results[f'context_{i}'] = {
                        'handled': False,
                        'error': str(e),
                        'context': str(context)[:50] if context else 'None'
                    }
                    all_handled = False

            return {
                'passed': all_handled,
                'unavailability_results': unavailability_results,
                'total_contexts': len(test_contexts),
                'handled_contexts': sum(1 for r in unavailability_results.values() if r.get('handled', False))
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_invalid_inputs(self) -> Dict[str, Any]:
        """Test handling of invalid inputs"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            # Test various invalid inputs
            invalid_inputs = [
                (None, None),
                (123, {'user_id': 'TEST'}),
                (['list', 'input'], {'user_role': 'beneficiary'}),
                ('valid message', 'invalid_context_string'),
                ('', {'user_id': '', 'user_role': ''}),
            ]

            invalid_results = {}
            all_handled_safely = True

            for i, (message, context) in enumerate(invalid_inputs):
                try:
                    result = process_message(message, user_context=context)

                    # Should handle invalid inputs safely
                    safe = (
                        result is not None and
                        isinstance(result, dict) and
                        'success' in result
                    )

                    invalid_results[f'invalid_{i}'] = {
                        'safe': safe,
                        'success': result.get('success') if result else False,
                        'input_type': f"{type(message).__name__}, {type(context).__name__}"
                    }

                    if not safe:
                        all_handled_safely = False

                except Exception as e:
                    invalid_results[f'invalid_{i}'] = {
                        'safe': False,
                        'error': str(e),
                        'input_type': f"{type(message).__name__}, {type(context).__name__}"
                    }
                    all_handled_safely = False

            return {
                'passed': all_handled_safely,
                'invalid_results': invalid_results,
                'total_invalid_inputs': len(invalid_inputs),
                'safely_handled': sum(1 for r in invalid_results.values() if r.get('safe', False))
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_system_resilience(self) -> Dict[str, Any]:
        """Test overall system resilience"""
        try:
            from assistant_crm.api.unified_chat_api import process_message
            from assistant_crm.api.chatbot import ask_bot

            # Test rapid successive requests
            rapid_requests = []
            for i in range(20):
                start_time = time.time()
                result = process_message(f"Test {i}")
                response_time = time.time() - start_time

                rapid_requests.append({
                    'success': result.get('success', False),
                    'response_time': response_time,
                    'has_reply': bool(result.get('reply'))
                })

            # Test alternating API calls
            alternating_results = []
            for i in range(10):
                if i % 2 == 0:
                    result = process_message(f"Unified {i}")
                else:
                    result = ask_bot(f"Chatbot {i}")

                alternating_results.append(result.get('success', False))

            # Calculate resilience metrics
            rapid_success_rate = sum(1 for r in rapid_requests if r['success']) / len(rapid_requests)
            rapid_avg_time = sum(r['response_time'] for r in rapid_requests) / len(rapid_requests)
            alternating_success_rate = sum(alternating_results) / len(alternating_results)

            resilient = (
                rapid_success_rate >= 0.9 and
                rapid_avg_time < 2.0 and
                alternating_success_rate >= 0.9
            )

            return {
                'passed': resilient,
                'rapid_success_rate': rapid_success_rate,
                'rapid_avg_response_time': rapid_avg_time,
                'alternating_success_rate': alternating_success_rate,
                'total_rapid_requests': len(rapid_requests),
                'total_alternating_requests': len(alternating_results)
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_anna_branding(self):
        """Test Category 7: Anna Personality & WCFCB Branding"""
        print("Testing Anna personality and WCFCB branding consistency...")

        branding_tests = {
            'anna_personality_consistency': self.test_anna_personality,
            'wcfcb_branding_consistency': self.test_wcfcb_branding,
            'professional_tone': self.test_professional_tone,
            'empathy_patterns': self.test_empathy_patterns,
            'brand_alignment': self.test_brand_alignment
        }

        for test_name, test_func in branding_tests.items():
            try:
                result = test_func()
                self.test_results['anna_branding_testing'][test_name] = result
                status = "✅ PASSED" if result.get('passed') else "❌ FAILED"
                print(f"  {test_name}: {status}")

                self.total_tests += 1
                if result.get('passed'):
                    self.passed_tests += 1
                else:
                    self.failed_tests += 1

            except Exception as e:
                self.test_results['anna_branding_testing'][test_name] = {
                    'passed': False,
                    'error': str(e)
                }
                print(f"  {test_name}: ❌ FAILED - {str(e)}")
                self.total_tests += 1
                self.failed_tests += 1

    def test_anna_personality(self) -> Dict[str, Any]:
        """Test Anna personality consistency"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            personality_scenarios = [
                'Hello',
                'I need help',
                'Can you assist me?',
                'What can you do for me?',
                'I have a question'
            ]

            anna_results = {}
            anna_count = 0
            total_responses = 0

            for scenario in personality_scenarios:
                result = process_message(scenario)
                reply = result.get('reply', '')

                # Check for Anna's presence and personality indicators
                has_anna = 'Anna' in reply
                has_greeting = any(greeting in reply.lower() for greeting in ['hi', 'hello', 'good'])
                has_helpfulness = any(help_word in reply.lower() for help_word in ['help', 'assist', 'support'])

                anna_results[scenario] = {
                    'has_anna': has_anna,
                    'has_greeting': has_greeting,
                    'has_helpfulness': has_helpfulness,
                    'anna_personality_score': sum([has_anna, has_greeting, has_helpfulness])
                }

                if has_anna:
                    anna_count += 1
                total_responses += 1

            anna_percentage = (anna_count / total_responses) * 100 if total_responses > 0 else 0
            avg_personality_score = sum(r['anna_personality_score'] for r in anna_results.values()) / len(anna_results)

            return {
                'passed': anna_percentage >= 75 and avg_personality_score >= 2.0,
                'anna_percentage': anna_percentage,
                'average_personality_score': avg_personality_score,
                'anna_results': anna_results,
                'total_scenarios': len(personality_scenarios)
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_wcfcb_branding(self) -> Dict[str, Any]:
        """Test WCFCB branding consistency"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            branding_scenarios = [
                'Who are you?',
                'What organization do you work for?',
                'Tell me about your company',
                'What services do you offer?',
                'How can I contact you?'
            ]

            wcfcb_results = {}
            wcfcb_count = 0
            professional_count = 0

            for scenario in branding_scenarios:
                result = process_message(scenario)
                reply = result.get('reply', '')

                # Check for WCFCB branding
                has_wcfcb = 'WCFCB' in reply
                has_professional_tone = len(reply) > 20 and not any(casual in reply.lower() for casual in ['lol', 'haha', 'cool', 'awesome'])
                has_contact_info = any(contact in reply.lower() for contact in ['contact', 'phone', 'email', 'office'])

                wcfcb_results[scenario] = {
                    'has_wcfcb': has_wcfcb,
                    'has_professional_tone': has_professional_tone,
                    'has_contact_info': has_contact_info,
                    'branding_score': sum([has_wcfcb, has_professional_tone, has_contact_info])
                }

                if has_wcfcb:
                    wcfcb_count += 1
                if has_professional_tone:
                    professional_count += 1

            wcfcb_percentage = (wcfcb_count / len(branding_scenarios)) * 100
            professional_percentage = (professional_count / len(branding_scenarios)) * 100

            return {
                'passed': wcfcb_percentage >= 60 and professional_percentage >= 90,
                'wcfcb_percentage': wcfcb_percentage,
                'professional_percentage': professional_percentage,
                'wcfcb_results': wcfcb_results,
                'total_scenarios': len(branding_scenarios)
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_professional_tone(self) -> Dict[str, Any]:
        """Test professional tone consistency"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            tone_scenarios = [
                'I have a complaint',
                'This is urgent',
                'I am frustrated',
                'I need immediate help',
                'This is not working'
            ]

            tone_results = {}
            professional_responses = 0

            for scenario in tone_scenarios:
                result = process_message(scenario)
                reply = result.get('reply', '')

                # Check for professional tone indicators
                has_empathy = any(empathy in reply.lower() for empathy in ['understand', 'sorry', 'apologize', 'help'])
                avoids_casual = not any(casual in reply.lower() for casual in ['whatever', 'no problem', 'sure thing'])
                appropriate_length = len(reply) > 30  # Substantive response

                is_professional = has_empathy and avoids_casual and appropriate_length

                tone_results[scenario] = {
                    'has_empathy': has_empathy,
                    'avoids_casual': avoids_casual,
                    'appropriate_length': appropriate_length,
                    'is_professional': is_professional
                }

                if is_professional:
                    professional_responses += 1

            professional_percentage = (professional_responses / len(tone_scenarios)) * 100

            return {
                'passed': professional_percentage >= 80,
                'professional_percentage': professional_percentage,
                'tone_results': tone_results,
                'total_scenarios': len(tone_scenarios)
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_empathy_patterns(self) -> Dict[str, Any]:
        """Test empathy patterns in responses"""
        try:
            from assistant_crm.api.unified_chat_api import process_message

            empathy_scenarios = [
                'I lost my job',
                'I am having financial difficulties',
                'I need help with my benefits',
                'I am confused about the process',
                'I have been waiting for a long time'
            ]

            empathy_results = {}
            empathetic_responses = 0

            for scenario in empathy_scenarios:
                result = process_message(scenario)
                reply = result.get('reply', '')

                # Check for empathy indicators
                empathy_words = ['understand', 'sorry', 'help', 'support', 'assist', 'here for you']
                has_empathy = any(word in reply.lower() for word in empathy_words)

                # Check for helpful guidance
                guidance_words = ['can', 'will', 'let me', 'I\'ll', 'we can']
                offers_help = any(word in reply.lower() for word in guidance_words)

                is_empathetic = has_empathy and offers_help

                empathy_results[scenario] = {
                    'has_empathy': has_empathy,
                    'offers_help': offers_help,
                    'is_empathetic': is_empathetic,
                    'reply_length': len(reply)
                }

                if is_empathetic:
                    empathetic_responses += 1

            empathy_percentage = (empathetic_responses / len(empathy_scenarios)) * 100

            return {
                'passed': empathy_percentage >= 70,
                'empathy_percentage': empathy_percentage,
                'empathy_results': empathy_results,
                'total_scenarios': len(empathy_scenarios)
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def test_brand_alignment(self) -> Dict[str, Any]:
        """Test overall brand alignment"""
        try:
            from assistant_crm.api.unified_chat_api import process_message
            from assistant_crm.api.chatbot import ask_bot

            # Test brand consistency across both APIs
            brand_message = "Tell me about your organization"

            unified_result = process_message(brand_message)
            chatbot_result = ask_bot(brand_message)

            unified_reply = unified_result.get('reply', '')
            chatbot_reply = chatbot_result.get('reply', '')

            # Check brand elements in both responses
            unified_brand = {
                'has_anna': 'Anna' in unified_reply,
                'has_wcfcb': 'WCFCB' in unified_reply,
                'professional': len(unified_reply) > 20,
                'helpful': any(word in unified_reply.lower() for word in ['help', 'assist', 'support'])
            }

            chatbot_brand = {
                'has_anna': 'Anna' in chatbot_reply,
                'has_wcfcb': 'WCFCB' in chatbot_reply,
                'professional': len(chatbot_reply) > 20,
                'helpful': any(word in chatbot_reply.lower() for word in ['help', 'assist', 'support'])
            }

            # Calculate brand alignment scores
            unified_score = sum(unified_brand.values())
            chatbot_score = sum(chatbot_brand.values())

            brand_consistency = abs(unified_score - chatbot_score) <= 1  # Scores should be similar

            return {
                'passed': unified_score >= 3 and chatbot_score >= 3 and brand_consistency,
                'unified_brand_score': unified_score,
                'chatbot_brand_score': chatbot_score,
                'brand_consistency': brand_consistency,
                'unified_brand_elements': unified_brand,
                'chatbot_brand_elements': chatbot_brand
            }

        except Exception as e:
            return {'passed': False, 'error': str(e)}

    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        end_time = time.time()
        total_test_time = end_time - self.start_time if self.start_time else 0

        # Calculate overall statistics
        overall_pass_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0

        # Calculate category pass rates
        category_stats = {}
        for category, results in self.test_results.items():
            if results:
                category_passed = sum(1 for r in results.values() if r.get('passed', False))
                category_total = len(results)
                category_pass_rate = (category_passed / category_total) * 100 if category_total > 0 else 0

                category_stats[category] = {
                    'passed': category_passed,
                    'total': category_total,
                    'pass_rate': category_pass_rate,
                    'status': 'PASSED' if category_pass_rate >= 90 else 'FAILED'
                }

        # Determine overall status
        overall_status = 'PASSED' if overall_pass_rate >= 95 else 'FAILED'

        # Generate performance summary
        performance_summary = {
            'average_response_time': sum(self.performance_metrics['response_times']) / len(self.performance_metrics['response_times']) if self.performance_metrics['response_times'] else 0,
            'success_rate': sum(self.performance_metrics['success_rates']) / len(self.performance_metrics['success_rates']) if self.performance_metrics['success_rates'] else 0,
            'error_rate': sum(self.performance_metrics['error_rates']) / len(self.performance_metrics['error_rates']) if self.performance_metrics['error_rates'] else 0
        }

        # Generate recommendations
        recommendations = self.generate_recommendations()

        report = {
            'test_summary': {
                'total_tests': self.total_tests,
                'passed_tests': self.passed_tests,
                'failed_tests': self.failed_tests,
                'overall_pass_rate': overall_pass_rate,
                'overall_status': overall_status,
                'test_duration': total_test_time
            },
            'category_results': category_stats,
            'detailed_results': self.test_results,
            'performance_summary': performance_summary,
            'recommendations': recommendations,
            'production_readiness': self.assess_production_readiness(overall_pass_rate, category_stats),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        # Print summary
        self.print_test_summary(report)

        return report

    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []

        # Check each category for specific recommendations
        for category, results in self.test_results.items():
            if results:
                category_passed = sum(1 for r in results.values() if r.get('passed', False))
                category_total = len(results)
                category_pass_rate = (category_passed / category_total) * 100 if category_total > 0 else 0

                if category_pass_rate < 90:
                    if category == 'user_type_testing':
                        recommendations.append("Review user role configurations and permissions")
                    elif category == 'api_integration_testing':
                        recommendations.append("Investigate API integration issues and response consistency")
                    elif category == 'performance_validation':
                        recommendations.append("Optimize system performance and response times")
                    elif category == 'security_testing':
                        recommendations.append("Strengthen role-based access control and security measures")
                    elif category == 'regression_testing':
                        recommendations.append("Address regression issues from previous phases")
                    elif category == 'error_handling_testing':
                        recommendations.append("Improve error handling and system resilience")
                    elif category == 'anna_branding_testing':
                        recommendations.append("Enhance Anna personality consistency and WCFCB branding")

        # Add general recommendations
        if self.passed_tests / self.total_tests < 0.95:
            recommendations.append("Conduct additional testing before production deployment")

        if not recommendations:
            recommendations.append("System is ready for production deployment")
            recommendations.append("Consider implementing monitoring and alerting for production")
            recommendations.append("Prepare user training and documentation")

        return recommendations

    def assess_production_readiness(self, overall_pass_rate: float, category_stats: Dict) -> Dict[str, Any]:
        """Assess production readiness based on test results"""

        # Critical categories that must pass for production
        critical_categories = ['api_integration_testing', 'security_testing', 'regression_testing']
        critical_passed = all(
            category_stats.get(cat, {}).get('pass_rate', 0) >= 90
            for cat in critical_categories
        )

        # Performance requirements
        performance_ok = category_stats.get('performance_validation', {}).get('pass_rate', 0) >= 80

        # Overall readiness assessment
        ready_for_production = (
            overall_pass_rate >= 95 and
            critical_passed and
            performance_ok
        )

        readiness_level = "PRODUCTION READY" if ready_for_production else "NEEDS IMPROVEMENT"

        return {
            'ready_for_production': ready_for_production,
            'readiness_level': readiness_level,
            'overall_pass_rate': overall_pass_rate,
            'critical_categories_passed': critical_passed,
            'performance_acceptable': performance_ok,
            'deployment_recommendation': (
                "System is ready for production deployment" if ready_for_production
                else "Address failing tests before production deployment"
            )
        }

    def print_test_summary(self, report: Dict[str, Any]):
        """Print comprehensive test summary"""
        print("\n" + "=" * 60)
        print("🏆 PHASE 5 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)

        summary = report['test_summary']
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']}")
        print(f"   Failed: {summary['failed_tests']}")
        print(f"   Pass Rate: {summary['overall_pass_rate']:.1f}%")
        print(f"   Status: {summary['overall_status']}")
        print(f"   Duration: {summary['test_duration']:.2f} seconds")

        print(f"\n📋 CATEGORY RESULTS:")
        for category, stats in report['category_results'].items():
            status_icon = "✅" if stats['status'] == 'PASSED' else "❌"
            print(f"   {status_icon} {category}: {stats['passed']}/{stats['total']} ({stats['pass_rate']:.1f}%)")

        print(f"\n🎯 PRODUCTION READINESS:")
        readiness = report['production_readiness']
        readiness_icon = "✅" if readiness['ready_for_production'] else "⚠️"
        print(f"   {readiness_icon} {readiness['readiness_level']}")
        print(f"   Recommendation: {readiness['deployment_recommendation']}")

        if report['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"   {i}. {rec}")

        print("\n" + "=" * 60)


# Main execution function
def run_phase5_comprehensive_tests():
    """Run Phase 5 comprehensive testing suite"""
    test_suite = Phase5TestSuite()
    return test_suite.run_comprehensive_test_suite()


if __name__ == "__main__":
    results = run_phase5_comprehensive_tests()

    # Save results to file
    with open('/workspace/development/frappe-bench/apps/assistant_crm/phase5_test_results.json', 'w') as f:
        import json
        json.dump(results, f, indent=2, default=str)

    print(f"\n📄 Detailed results saved to: phase5_test_results.json")
