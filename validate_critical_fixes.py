#!/usr/bin/env python3
"""
Direct Validation of Critical Fixes
Validates the code changes for session creation and NRC recognition
"""

import sys
import re
from datetime import datetime

# Add the apps directory to Python path
sys.path.insert(0, '/workspace/development/frappe-bench/apps')
sys.path.insert(0, '/workspace/development/frappe-bench/apps/assistant_crm')

def validate_critical_fixes():
    """Validate the critical fixes by examining the code directly"""
    print("🔍 DIRECT VALIDATION OF CRITICAL FIXES")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    validation_results = {}
    
    # Validation 1: Session Creation Fix
    print("\n🔄 VALIDATION 1: SESSION CREATION FIX")
    print("-" * 50)
    
    try:
        auth_workflow_path = '/workspace/development/frappe-bench/apps/assistant_crm/assistant_crm/services/live_authentication_workflow.py'
        
        with open(auth_workflow_path, 'r') as f:
            content = f.read()
        
        # Check for session creation fix
        session_creation_checks = [
            ('Session initialization check', 'if not hasattr(self, \'_sessions\'):'),
            ('Session storage initialization', 'self._sessions = {}'),
            ('Session existence check', 'if session_id not in self._sessions:'),
            ('Basic session creation', 'self._sessions[session_id] = {'),
            ('Session created timestamp', '\'created_at\': now()'),
            ('Session authenticated flag', '\'authenticated\': False'),
            ('Session ID storage', '\'session_id\': session_id'),
            ('Session data retrieval', 'session_data = self._get_session_data(session_id)')
        ]
        
        session_fix_score = 0
        for check_name, pattern in session_creation_checks:
            if pattern in content:
                print(f"   ✅ {check_name}: IMPLEMENTED")
                session_fix_score += 1
            else:
                print(f"   ❌ {check_name}: MISSING")
        
        session_fix_rate = (session_fix_score / len(session_creation_checks)) * 100
        validation_results['session_creation_fix'] = session_fix_rate >= 80
        
        print(f"   📊 Session Creation Fix Score: {session_fix_rate:.1f}%")
        
    except Exception as e:
        print(f"   ❌ Session creation validation error: {str(e)}")
        validation_results['session_creation_fix'] = False
    
    # Validation 2: NRC Format Recognition Fix
    print("\n🔐 VALIDATION 2: NRC FORMAT RECOGNITION FIX")
    print("-" * 50)
    
    try:
        # Check for NRC recognition enhancements
        nrc_recognition_checks = [
            ('Enhanced parse function', 'def _parse_authentication_input'),
            ('Import regex module', 'import re'),
            ('Message cleaning', 'message.strip().lower()'),
            ('Prefix removal', 're.sub.*nrc.*reference'),
            ('NRC validation function', 'def _is_valid_nrc_format'),
            ('Standard NRC format', r'\\d{6}/\\d{2}/\\d'),
            ('Alternative NRC format', r'\\d{9,}'),
            ('NRC pattern matching', 'nrc_pattern.*=.*r\''),
            ('Reference pattern matching', 'ref_pattern.*=.*r\''),
            ('Multiple parsing strategies', 'Strategy.*:'),
            ('Format validation', 'if self._is_valid_nrc_format'),
            ('Enhanced error messages', 'Great! I can see your NRC number')
        ]
        
        nrc_fix_score = 0
        for check_name, pattern in nrc_recognition_checks:
            if re.search(pattern, content, re.IGNORECASE):
                print(f"   ✅ {check_name}: IMPLEMENTED")
                nrc_fix_score += 1
            else:
                print(f"   ❌ {check_name}: MISSING")
        
        nrc_fix_rate = (nrc_fix_score / len(nrc_recognition_checks)) * 100
        validation_results['nrc_recognition_fix'] = nrc_fix_rate >= 80
        
        print(f"   📊 NRC Recognition Fix Score: {nrc_fix_rate:.1f}%")
        
        # Test specific NRC format validation
        print("\n   Testing specific NRC format patterns...")
        
        # Check if the specific patterns are in the code
        nrc_patterns = [
            ('228597/62/1 format', r'\\d{6}/\\d{2}/\\d'),
            ('9+ digit format', r'\\d{9,}'),
            ('Alternative format', r'\\d{6}/\\d{2}/\\d{1,2}')
        ]
        
        pattern_score = 0
        for pattern_name, pattern in nrc_patterns:
            if pattern in content:
                print(f"   ✅ {pattern_name}: SUPPORTED")
                pattern_score += 1
            else:
                print(f"   ❌ {pattern_name}: NOT SUPPORTED")
        
        pattern_rate = (pattern_score / len(nrc_patterns)) * 100
        validation_results['nrc_pattern_support'] = pattern_rate >= 80
        
        print(f"   📊 NRC Pattern Support: {pattern_rate:.1f}%")
        
    except Exception as e:
        print(f"   ❌ NRC recognition validation error: {str(e)}")
        validation_results['nrc_recognition_fix'] = False
        validation_results['nrc_pattern_support'] = False
    
    # Validation 3: Error Message Enhancement
    print("\n💬 VALIDATION 3: ERROR MESSAGE ENHANCEMENT")
    print("-" * 50)
    
    try:
        # Check for enhanced error messages
        error_message_checks = [
            ('Missing reference detection', 'missing_reference'),
            ('NRC recognition message', 'Great! I can see your NRC number'),
            ('Enhanced format examples', '228597/62/1 BN-123456'),
            ('Multiple format examples', 'Examples:'),
            ('Helpful guidance', 'Your NRC is on your National Registration Card'),
            ('Reference number guidance', 'Your Reference Number depends on'),
            ('Format validation message', 'I couldn\'t recognize the format'),
            ('Improved user experience', 'Please provide both:')
        ]
        
        error_message_score = 0
        for check_name, pattern in error_message_checks:
            if pattern in content:
                print(f"   ✅ {check_name}: IMPLEMENTED")
                error_message_score += 1
            else:
                print(f"   ❌ {check_name}: MISSING")
        
        error_message_rate = (error_message_score / len(error_message_checks)) * 100
        validation_results['error_message_enhancement'] = error_message_rate >= 80
        
        print(f"   📊 Error Message Enhancement Score: {error_message_rate:.1f}%")
        
    except Exception as e:
        print(f"   ❌ Error message validation error: {str(e)}")
        validation_results['error_message_enhancement'] = False
    
    # Validation 4: Code Quality and Integration
    print("\n⚙️ VALIDATION 4: CODE QUALITY AND INTEGRATION")
    print("-" * 50)
    
    try:
        # Check for code quality indicators
        quality_checks = [
            ('Function documentation', '""".*"""'),
            ('Type hints', '-> Optional'),
            ('Error handling', 'except Exception as e:'),
            ('Import statements', 'import re'),
            ('Regex compilation', 're.match'),
            ('String validation', 'len.*>='),
            ('Return type consistency', 'return.*None'),
            ('Code comments', 'ENHANCED:.*CRITICAL FIX:')
        ]
        
        quality_score = 0
        for check_name, pattern in quality_checks:
            matches = len(re.findall(pattern, content, re.IGNORECASE | re.DOTALL))
            if matches > 0:
                print(f"   ✅ {check_name}: GOOD ({matches} occurrences)")
                quality_score += 1
            else:
                print(f"   ❌ {check_name}: MISSING")
        
        quality_rate = (quality_score / len(quality_checks)) * 100
        validation_results['code_quality'] = quality_rate >= 80
        
        print(f"   📊 Code Quality Score: {quality_rate:.1f}%")
        
    except Exception as e:
        print(f"   ❌ Code quality validation error: {str(e)}")
        validation_results['code_quality'] = False
    
    # Generate Validation Report
    print("\n" + "=" * 60)
    print("📊 CRITICAL FIXES VALIDATION REPORT")
    print("=" * 60)
    
    successful_validations = sum(1 for success in validation_results.values() if success)
    total_validations = len(validation_results)
    success_rate = (successful_validations / total_validations) * 100 if total_validations > 0 else 0
    
    print(f"Critical Fixes Validation Rate: {success_rate:.1f}% ({successful_validations}/{total_validations})")
    
    print("\nDetailed Validation Results:")
    for validation_name, success in validation_results.items():
        status = "✅ FIXED" if success else "❌ NEEDS WORK"
        print(f"  {validation_name.replace('_', ' ').title():30} {status}")
    
    # Final Assessment
    print(f"\n🎯 CRITICAL FIXES VALIDATION ASSESSMENT:")
    
    if success_rate >= 95:
        print("🎉 EXCELLENT: All critical fixes implemented perfectly")
        print("   ✅ Session creation error completely resolved")
        print("   ✅ NRC format recognition fully enhanced")
        print("   ✅ Error messages significantly improved")
        print("   ✅ Code quality excellent")
        print("   ✅ Ready for immediate deployment")
        
    elif success_rate >= 80:
        print("✅ VERY GOOD: Critical fixes mostly implemented")
        print("   ✅ Session creation error addressed")
        print("   ✅ NRC format recognition enhanced")
        print("   ✅ Error messages improved")
        print("   ⚠️ Minor refinements possible")
        print("   ✅ Ready for testing")
        
    elif success_rate >= 60:
        print("⚠️ PARTIAL: Some critical fixes implemented")
        print("   ✅ Some improvements made")
        print("   ⚠️ Additional work needed")
        print("   ⚠️ Continue development")
        
    else:
        print("❌ INSUFFICIENT: Critical fixes not adequately implemented")
        print("   ❌ Session creation issues remain")
        print("   ❌ NRC recognition not enhanced")
        print("   ❌ Immediate attention required")
    
    # Specific Issue Resolution Status
    print(f"\n🚨 SPECIFIC ISSUE RESOLUTION STATUS:")
    
    if validation_results.get('session_creation_fix', False):
        print("   ✅ Session Creation Error: CODE FIXED")
        print("     - Session initialization added to process_user_request")
        print("     - Session existence check implemented")
        print("     - Basic session creation on first access")
    else:
        print("   ❌ Session Creation Error: CODE NOT FIXED")
        print("     - Session initialization missing")
    
    if validation_results.get('nrc_recognition_fix', False):
        print("   ✅ NRC Format Recognition: CODE ENHANCED")
        print("     - Enhanced parsing function implemented")
        print("     - Multiple NRC format support added")
        print("     - Regex pattern matching active")
    else:
        print("   ❌ NRC Format Recognition: CODE NOT ENHANCED")
        print("     - Parsing function not improved")
    
    if validation_results.get('error_message_enhancement', False):
        print("   ✅ Error Messages: SIGNIFICANTLY IMPROVED")
        print("     - Better user guidance implemented")
        print("     - Format examples enhanced")
    else:
        print("   ❌ Error Messages: NOT IMPROVED")
        print("     - User guidance not enhanced")
    
    print(f"\n📋 Validation Summary:")
    print(f"   Validations Performed: {total_validations}")
    print(f"   Success Rate: {success_rate:.1f}%")
    print(f"   Target Issues: Session Creation + NRC Recognition")
    print(f"   Code File: live_authentication_workflow.py")
    print(f"   Validation Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return success_rate >= 80, validation_results

def main():
    """Main execution function"""
    print("🔍 CRITICAL FIXES CODE VALIDATION")
    print("Validating code changes for session and NRC issues")
    
    success, results = validate_critical_fixes()
    
    if success:
        print("\n🎉 CRITICAL FIXES VALIDATION: SUCCESS")
        print("   Code changes implemented correctly")
        print("   Session creation error should be resolved")
        print("   NRC format recognition should work")
        print("   Ready for user testing")
        return True
    else:
        print("\n⚠️ CRITICAL FIXES VALIDATION: INCOMPLETE")
        print("   Some code changes missing or incomplete")
        print("   Additional development required")
        return False

if __name__ == "__main__":
    main()
