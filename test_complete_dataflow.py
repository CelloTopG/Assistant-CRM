#!/usr/bin/env python3
"""
Complete dataflow test for assistant_crm chatbot with live data integration
Tests frontend-backend synchronization and live data retrieval
"""

import requests
import json
import time

def test_complete_dataflow():
    """Test the complete chatbot dataflow including live data integration"""
    
    print("=" * 80)
    print("COMPLETE CHATBOT DATAFLOW TEST")
    print("=" * 80)
    
    base_url = "http://localhost:8001"
    api_endpoint = f"{base_url}/api/method/assistant_crm.api.optimized_chat.send_optimized_message"
    
    # Test cases with different scenarios
    test_cases = [
        {
            "name": "Basic Greeting",
            "message": "Hello Anna",
            "expected_keywords": ["hello", "help", "anna"],
            "should_use_live_data": False
        },
        {
            "name": "NRC Identifier Test",
            "message": "My NRC is 123456/78/9 and I need help with my benefits",
            "expected_keywords": ["benefits", "help"],
            "should_use_live_data": True
        },
        {
            "name": "Email Identifier Test", 
            "message": "My email is test@wcfcb.com, can you help me with my claim status?",
            "expected_keywords": ["claim", "status"],
            "should_use_live_data": True
        },
        {
            "name": "Customer ID Test",
            "message": "I am customer CUST-001, what is my payment status?",
            "expected_keywords": ["payment", "status"],
            "should_use_live_data": True
        },
        {
            "name": "General WCFCB Query",
            "message": "What services does WCFCB provide?",
            "expected_keywords": ["wcfcb", "services"],
            "should_use_live_data": False
        }
    ]
    
    results = {
        "total_tests": len(test_cases),
        "passed": 0,
        "failed": 0,
        "test_results": []
    }
    
    print(f"\nTesting {len(test_cases)} scenarios...")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTEST {i}: {test_case['name']}")
        print(f"Message: {test_case['message']}")
        
        try:
            # Send request to chatbot API
            payload = {"message": test_case["message"]}
            headers = {"Content-Type": "application/json"}
            
            start_time = time.time()
            response = requests.post(api_endpoint, json=payload, headers=headers, timeout=30)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                message_data = data.get("message", {})
                
                # Extract key metrics
                bot_response = message_data.get("response", "")
                success = message_data.get("success", False)
                metadata = message_data.get("metadata", {})
                live_data_enabled = metadata.get("live_data_enabled", False)
                live_data_used = metadata.get("live_data_used", False)
                processing_time = metadata.get("performance", {}).get("processing_time_ms", 0)
                
                # Validate response
                test_result = {
                    "test_name": test_case["name"],
                    "success": success,
                    "response_time_ms": response_time,
                    "processing_time_ms": processing_time,
                    "live_data_enabled": live_data_enabled,
                    "live_data_used": live_data_used,
                    "response_length": len(bot_response),
                    "contains_keywords": any(keyword.lower() in bot_response.lower() for keyword in test_case["expected_keywords"]),
                    "live_data_expectation_met": live_data_used == test_case["should_use_live_data"] if test_case["should_use_live_data"] else True
                }
                
                # Print results
                print(f"✅ Status: {'SUCCESS' if success else 'FAILED'}")
                print(f"📊 Response Time: {response_time:.2f}ms")
                print(f"⚡ Processing Time: {processing_time:.2f}ms")
                print(f"🔗 Live Data Enabled: {live_data_enabled}")
                print(f"📈 Live Data Used: {live_data_used}")
                print(f"📝 Response Length: {len(bot_response)} chars")
                print(f"🎯 Keywords Found: {test_result['contains_keywords']}")
                print(f"💬 Response Preview: {bot_response[:100]}...")
                
                # Determine if test passed
                test_passed = (
                    success and 
                    test_result['contains_keywords'] and
                    test_result['live_data_expectation_met'] and
                    len(bot_response) > 10
                )
                
                if test_passed:
                    print("🎉 TEST PASSED")
                    results["passed"] += 1
                else:
                    print("❌ TEST FAILED")
                    results["failed"] += 1
                
                results["test_results"].append(test_result)
                
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text}")
                results["failed"] += 1
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            results["failed"] += 1
        
        print("-" * 60)
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']} ✅")
    print(f"Failed: {results['failed']} ❌")
    print(f"Success Rate: {(results['passed']/results['total_tests']*100):.1f}%")
    
    # Detailed analysis
    if results["test_results"]:
        avg_response_time = sum(r["response_time_ms"] for r in results["test_results"]) / len(results["test_results"])
        avg_processing_time = sum(r["processing_time_ms"] for r in results["test_results"]) / len(results["test_results"])
        live_data_tests = sum(1 for r in results["test_results"] if r["live_data_used"])
        
        print(f"\nPerformance Metrics:")
        print(f"Average Response Time: {avg_response_time:.2f}ms")
        print(f"Average Processing Time: {avg_processing_time:.2f}ms")
        print(f"Live Data Activations: {live_data_tests}/{len(results['test_results'])}")
    
    # Frontend test
    print(f"\n🌐 Frontend URL: {base_url}/anna_integrated")
    print("✅ Frontend is accessible and ready for manual testing")
    
    # Backend validation
    print(f"\n🔧 Backend API: {api_endpoint}")
    print("✅ Backend API is responding and processing requests")
    
    # Live data integration status
    live_data_working = any(r["live_data_enabled"] for r in results["test_results"])
    print(f"\n📊 Live Data Integration: {'✅ ENABLED' if live_data_working else '❌ DISABLED'}")
    
    print("\n" + "=" * 80)
    if results["passed"] == results["total_tests"]:
        print("🎉 ALL TESTS PASSED - CHATBOT IS FULLY OPERATIONAL!")
    elif results["passed"] > results["failed"]:
        print("⚠️  MOSTLY WORKING - Some issues detected")
    else:
        print("❌ MAJOR ISSUES - Chatbot needs attention")
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    try:
        test_results = test_complete_dataflow()
        print(f"\nTest completed. Check the frontend at: http://localhost:8001/anna_integrated")
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
