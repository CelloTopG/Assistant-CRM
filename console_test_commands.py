"""
Console Testing Commands for WCFCB Assistant CRM
===============================================

Copy and paste these commands into the Frappe console to test various components.

Usage:
    cd /workspace/development/frappe-bench
    bench console
    
Then copy and paste the commands below.
"""

# ============================================================================
# BASIC SETUP AND VERIFICATION
# ============================================================================

def test_basic_setup():
    """Test basic setup and configuration"""
    import frappe
    
    print("🔍 Testing Basic Setup...")
    
    # Test 1: Check if user is set
    print(f"Current User: {frappe.session.user}")
    
    # Test 2: Check Assistant CRM Settings
    if frappe.db.exists("Assistant CRM Settings", "Assistant CRM Settings"):
        settings = frappe.get_doc("Assistant CRM Settings", "Assistant CRM Settings")
        print(f"✅ Settings exist - Enabled: {settings.enabled}")
    else:
        print("❌ Settings missing")
    
    # Test 3: Check DocTypes
    doctypes = ["Chat History", "Conversation Session", "Assistant CRM Settings"]
    for doctype in doctypes:
        if frappe.db.exists("DocType", doctype):
            print(f"✅ {doctype} DocType exists")
        else:
            print(f"❌ {doctype} DocType missing")

# ============================================================================
# SETTINGS SERVICE TESTING
# ============================================================================

def test_settings_service():
    """Test settings service functionality"""
    import frappe
    from assistant_crm.services.settings_service import get_settings_service, validate_access, get_settings
    
    print("🔍 Testing Settings Service...")
    
    # Test 1: Settings service instantiation
    try:
        service = get_settings_service()
        print("✅ Settings service instantiated")
    except Exception as e:
        print(f"❌ Settings service failed: {e}")
        return
    
    # Test 2: Validate access
    try:
        access_result = validate_access()
        print(f"✅ Access validation: {access_result}")
    except Exception as e:
        print(f"❌ Access validation failed: {e}")
    
    # Test 3: Get settings
    try:
        settings_result = get_settings()
        print(f"✅ Settings retrieved: {len(str(settings_result))} chars")
    except Exception as e:
        print(f"❌ Settings retrieval failed: {e}")

# ============================================================================
# GEMINI SERVICE TESTING
# ============================================================================

def test_gemini_service():
    """Test Gemini service functionality"""
    import frappe
    from assistant_crm.services.gemini_service import GeminiService
    
    print("🔍 Testing Gemini Service...")
    
    # Test 1: Service instantiation
    try:
        gemini = GeminiService()
        print(f"✅ Gemini service instantiated - Model: {gemini.model}")
    except Exception as e:
        print(f"❌ Gemini service failed: {e}")
        return
    
    # Test 2: Simple API test
    try:
        result = gemini.process_message("Hello, test message")
        if result.get("response"):
            print(f"✅ Gemini API working: {result['response'][:50]}...")
        else:
            print(f"❌ Gemini API failed: {result}")
    except Exception as e:
        print(f"❌ Gemini API error: {e}")

# ============================================================================
# STREAMLINED REPLY SERVICE TESTING
# ============================================================================

def test_streamlined_reply_service():
    """Test streamlined reply service"""
    import frappe
    from assistant_crm.services.streamlined_reply_service import get_bot_reply
    
    print("🔍 Testing Streamlined Reply Service...")
    
    # Test 1: Basic reply
    try:
        response = get_bot_reply("Hello, I need help with workers compensation")
        if "technical difficulties" not in response.lower():
            print(f"✅ Reply service working: {response[:50]}...")
        else:
            print(f"❌ Still getting fallback response: {response[:50]}...")
    except Exception as e:
        print(f"❌ Reply service error: {e}")

# ============================================================================
# SESSION MANAGEMENT TESTING
# ============================================================================

def test_session_management():
    """Test session management functionality"""
    import frappe
    
    print("🔍 Testing Session Management...")
    
    # Test 1: Create conversation session
    try:
        session_doc = frappe.get_doc({
            "doctype": "Conversation Session",
            "session_id": "console_test_session",
            "user": frappe.session.user,
            "status": "active"
        })
        session_doc.insert(ignore_permissions=True)
        print("✅ Conversation session created")
        
        # Clean up
        frappe.delete_doc("Conversation Session", session_doc.name)
        print("✅ Session cleanup successful")
        
    except Exception as e:
        print(f"❌ Session management error: {e}")

# ============================================================================
# COMPREHENSIVE TEST RUNNER
# ============================================================================

def run_all_console_tests():
    """Run all console tests"""
    import frappe
    
    print("🚀 Running All Console Tests")
    print("=" * 50)
    
    # Set user to Administrator if not already set
    if frappe.session.user == "Guest":
        frappe.set_user("Administrator")
        print("✅ Set user to Administrator")
    
    test_basic_setup()
    print()
    test_settings_service()
    print()
    test_gemini_service()
    print()
    test_streamlined_reply_service()
    print()
    test_session_management()
    
    print("\n" + "=" * 50)
    print("🎉 Console testing complete!")

# ============================================================================
# QUICK TEST COMMANDS
# ============================================================================

# Quick command to test everything:
# run_all_console_tests()

# Quick command to test just the reply service:
# test_streamlined_reply_service()

# Quick command to test just Gemini:
# test_gemini_service()

# Quick command to test settings:
# test_settings_service()
