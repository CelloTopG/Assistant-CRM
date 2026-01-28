#!/usr/bin/env python3

import frappe
from frappe import _
import json
import time
from datetime import datetime
from .dynamic_data_integration import get_dynamic_response
from .escalation_manager import trigger_escalation

@frappe.whitelist()
def test_dynamic_data_integration():
    """Comprehensive test suite for dynamic data integration"""
    
    print("🧪 Starting Dynamic Data Integration Test Suite...")
    
    test_results = {
        'test_suite': 'Dynamic Data Integration',
        'start_time': datetime.now().isoformat(),
        'tests': [],
        'summary': {}
    }
    
    # Test scenarios
    test_scenarios = [
        {
            'name': 'Payment Status Query - Authenticated Employer',
            'intent': 'payment_status_inquiry',
            'user_context': {
                'user_id': 'EMP001',
                'session_token': 'test_session_123',
                'role': 'Employer',
                'employer_number': 'EMP-2024-00001'
            },
            'expected_success': True
        },
        {
            'name': 'Payment Status Query - Unauthenticated User',
            'intent': 'payment_status_inquiry',
            'user_context': {},
            'expected_success': False,
            'expected_action': 'redirect_to_login'
        },
        {
            'name': 'Due Date Query - Valid Employer',
            'intent': 'due_date_inquiry',
            'user_context': {
                'user_id': 'EMP002',
                'session_token': 'test_session_456',
                'role': 'Employer',
                'employer_number': 'EMP-2024-00002'
            },
            'query_params': {'period': 'current_quarter'},
            'expected_success': True
        },
        {
            'name': 'Claim Status Query - Authenticated Beneficiary',
            'intent': 'claim_status_inquiry',
            'user_context': {
                'user_id': 'BEN001',
                'session_token': 'test_session_789',
                'role': 'Beneficiary',
                'beneficiary_number': 'BEN-2024-00001',
                'claim_number': 'CLM-2024-00001'
            },
            'expected_success': True
        },
        {
            'name': 'Invalid Intent Test',
            'intent': 'invalid_intent',
            'user_context': {'user_id': 'TEST001'},
            'expected_success': False,
            'expected_fallback': True
        },
        {
            'name': 'API Timeout Simulation',
            'intent': 'payment_status_inquiry',
            'user_context': {
                'user_id': 'TIMEOUT_TEST',
                'session_token': 'timeout_session',
                'role': 'Employer',
                'employer_number': 'TIMEOUT-TEST'
            },
            'simulate_timeout': True,
            'expected_success': False,
            'expected_escalation': True
        }
    ]
    
    # Run tests
    for scenario in test_scenarios:
        test_result = run_test_scenario(scenario)
        test_results['tests'].append(test_result)
    
    # Generate summary
    test_results['summary'] = generate_test_summary(test_results['tests'])
    test_results['end_time'] = datetime.now().isoformat()
    
    # Save test results
    save_test_results(test_results)
    
    print(f"\n📊 Test Suite Completed!")
    print(f"Total Tests: {test_results['summary']['total_tests']}")
    print(f"Passed: {test_results['summary']['passed']}")
    print(f"Failed: {test_results['summary']['failed']}")
    print(f"Success Rate: {test_results['summary']['success_rate']:.1f}%")
    
    return test_results

def run_test_scenario(scenario):
    """Run a single test scenario"""
    
    test_start = time.time()
    test_result = {
        'name': scenario['name'],
        'start_time': datetime.now().isoformat(),
        'status': 'RUNNING'
    }
    
    try:
        print(f"\n🔍 Running: {scenario['name']}")
        
        # Prepare test data
        intent = scenario['intent']
        user_context = json.dumps(scenario.get('user_context', {}))
        query_params = json.dumps(scenario.get('query_params', {}))
        
        # Simulate API timeout if requested
        if scenario.get('simulate_timeout'):
            # Mock timeout scenario
            response = {
                'success': False,
                'message': 'API request timeout',
                'escalate': True,
                'error': 'Simulated timeout'
            }
        else:
            # Call actual function
            response = get_dynamic_response(intent, user_context, query_params)
        
        # Validate response
        validation_result = validate_test_response(response, scenario)
        
        test_result.update({
            'status': 'PASSED' if validation_result['valid'] else 'FAILED',
            'response': response,
            'validation': validation_result,
            'execution_time': time.time() - test_start
        })
        
        # Test escalation if expected
        if scenario.get('expected_escalation') and response.get('escalate'):
            escalation_result = test_escalation_trigger(scenario, response)
            test_result['escalation_test'] = escalation_result
        
        print(f"✅ {scenario['name']}: {test_result['status']}")
        
    except Exception as e:
        test_result.update({
            'status': 'ERROR',
            'error': str(e),
            'execution_time': time.time() - test_start
        })
        print(f"❌ {scenario['name']}: ERROR - {str(e)}")
    
    test_result['end_time'] = datetime.now().isoformat()
    return test_result

def validate_test_response(response, scenario):
    """Validate test response against expected outcomes"""
    
    validation = {
        'valid': True,
        'checks': [],
        'errors': []
    }
    
    # Check success expectation
    expected_success = scenario.get('expected_success', True)
    actual_success = response.get('success', False)
    
    if expected_success != actual_success:
        validation['valid'] = False
        validation['errors'].append(f"Expected success: {expected_success}, got: {actual_success}")
    else:
        validation['checks'].append(f"Success status correct: {actual_success}")
    
    # Check expected action
    if scenario.get('expected_action'):
        expected_action = scenario['expected_action']
        actual_action = response.get('action')
        
        if expected_action != actual_action:
            validation['valid'] = False
            validation['errors'].append(f"Expected action: {expected_action}, got: {actual_action}")
        else:
            validation['checks'].append(f"Action correct: {actual_action}")
    
    # Check fallback expectation
    if scenario.get('expected_fallback'):
        if not response.get('fallback_to_static'):
            validation['valid'] = False
            validation['errors'].append("Expected fallback to static content")
        else:
            validation['checks'].append("Fallback to static content correct")
    
    # Check escalation expectation
    if scenario.get('expected_escalation'):
        if not response.get('escalate'):
            validation['valid'] = False
            validation['errors'].append("Expected escalation trigger")
        else:
            validation['checks'].append("Escalation trigger correct")
    
    # Check response structure for successful responses
    if actual_success:
        required_fields = ['data_type']
        for field in required_fields:
            if field not in response:
                validation['valid'] = False
                validation['errors'].append(f"Missing required field: {field}")
            else:
                validation['checks'].append(f"Required field present: {field}")
    
    return validation

def test_escalation_trigger(scenario, response):
    """Test escalation trigger functionality"""
    
    try:
        escalation_result = trigger_escalation(
            escalation_type='api_failure',
            user_context=json.dumps(scenario.get('user_context', {})),
            conversation_data=json.dumps({
                'intent': scenario['intent'],
                'response': response,
                'test_scenario': True
            }),
            priority='normal'
        )
        
        return {
            'status': 'PASSED' if escalation_result.get('success') else 'FAILED',
            'escalation_id': escalation_result.get('escalation_id'),
            'routing': escalation_result.get('routing'),
            'response_time': escalation_result.get('estimated_response_time')
        }
        
    except Exception as e:
        return {
            'status': 'ERROR',
            'error': str(e)
        }

def generate_test_summary(test_results):
    """Generate test summary statistics"""
    
    total_tests = len(test_results)
    passed_tests = len([t for t in test_results if t['status'] == 'PASSED'])
    failed_tests = len([t for t in test_results if t['status'] == 'FAILED'])
    error_tests = len([t for t in test_results if t['status'] == 'ERROR'])
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    avg_execution_time = sum([t.get('execution_time', 0) for t in test_results]) / total_tests if total_tests > 0 else 0
    
    return {
        'total_tests': total_tests,
        'passed': passed_tests,
        'failed': failed_tests,
        'errors': error_tests,
        'success_rate': success_rate,
        'average_execution_time': avg_execution_time
    }

def save_test_results(test_results):
    """Save test results to database"""
    
    try:
        test_run = frappe.new_doc("API Test Run")
        test_run.test_suite = test_results['test_suite']
        test_run.start_time = test_results['start_time']
        test_run.end_time = test_results['end_time']
        test_run.total_tests = test_results['summary']['total_tests']
        test_run.passed_tests = test_results['summary']['passed']
        test_run.failed_tests = test_results['summary']['failed']
        test_run.success_rate = test_results['summary']['success_rate']
        test_run.test_results = json.dumps(test_results)
        test_run.insert()
        frappe.db.commit()
        
        print(f"📝 Test results saved: {test_run.name}")
        
    except Exception as e:
        print(f"❌ Failed to save test results: {str(e)}")

@frappe.whitelist()
def validate_api_configuration():
    """Validate API configuration and connectivity"""
    
    print("🔧 Validating API Configuration...")
    
    from .dynamic_data_integration import get_api_config
    
    validation_results = {
        'corebusiness_api': validate_api_config('corebusiness'),
        'claims_api': validate_api_config('claims'),
        'overall_status': 'UNKNOWN'
    }
    
    # Determine overall status
    if all(result['status'] == 'VALID' for result in validation_results.values() if isinstance(result, dict)):
        validation_results['overall_status'] = 'VALID'
    elif any(result['status'] == 'VALID' for result in validation_results.values() if isinstance(result, dict)):
        validation_results['overall_status'] = 'PARTIAL'
    else:
        validation_results['overall_status'] = 'INVALID'
    
    print(f"📊 API Configuration Status: {validation_results['overall_status']}")
    
    return validation_results

def validate_api_config(service):
    """Validate individual API configuration"""

    try:
        from .dynamic_data_integration import get_api_config

        config = get_api_config(service)

        # Check if we're in development mode (allow missing config)
        development_mode = frappe.conf.get('developer_mode', False) or frappe.conf.get('allow_empty_api_config', False)

        if not config:
            if development_mode:
                return {
                    'status': 'VALID',
                    'note': 'Development mode - API configuration not required'
                }
            else:
                return {
                    'status': 'INVALID',
                    'error': 'Configuration not found'
                }

        # Check required fields
        required_fields = ['base_url', 'api_key']
        missing_fields = [field for field in required_fields if not config.get(field)]

        if missing_fields:
            if development_mode:
                return {
                    'status': 'VALID',
                    'note': f'Development mode - Missing fields allowed: {", ".join(missing_fields)}'
                }
            else:
                return {
                    'status': 'INVALID',
                    'error': f'Missing fields: {", ".join(missing_fields)}'
                }
        
        # Validate URL format
        base_url = config['base_url']
        if not (base_url.startswith('http://') or base_url.startswith('https://')):
            return {
                'status': 'INVALID',
                'error': 'Invalid URL format'
            }
        
        return {
            'status': 'VALID',
            'base_url': base_url,
            'api_key_present': bool(config['api_key'])
        }
        
    except Exception as e:
        return {
            'status': 'ERROR',
            'error': str(e)
        }

if __name__ == "__main__":
    frappe.init(site="dev")
    frappe.connect()
    test_dynamic_data_integration()
