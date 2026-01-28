#!/usr/bin/env python3

import frappe

def final_api_configuration_fix():
    """Final fix for API configuration"""
    
    print("🔧 FINAL API CONFIGURATION FIX")
    print("=" * 40)
    
    # Step 1: Ensure database table and document exist
    ensure_database_setup()
    
    # Step 2: Initialize API configuration
    initialize_api_values()
    
    # Step 3: Test the fix
    test_final_fix()
    
    print("\n✅ FINAL FIX COMPLETED")

def ensure_database_setup():
    """Ensure database table and document exist"""
    
    print("\n🗄️  Step 1: Ensuring Database Setup")
    print("-" * 30)
    
    try:
        # Check if table exists
        table_exists = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'tabAssistant CRM Settings'
        """, as_dict=True)
        
        if not table_exists or table_exists[0]['count'] == 0:
            print("❌ Table missing - running migration...")
            # Force migration
            frappe.db.sql("""
                CREATE TABLE IF NOT EXISTS `tabAssistant CRM Settings` (
                    `name` varchar(140) NOT NULL,
                    `creation` datetime(6) DEFAULT NULL,
                    `modified` datetime(6) DEFAULT NULL,
                    `modified_by` varchar(140) DEFAULT NULL,
                    `owner` varchar(140) DEFAULT NULL,
                    `docstatus` int(1) NOT NULL DEFAULT 0,
                    `idx` int(8) NOT NULL DEFAULT 0,
                    `enabled` int(1) DEFAULT 1,
                    `ai_provider` varchar(140) DEFAULT NULL,
                    `api_key` text DEFAULT NULL,
                    `model_name` varchar(140) DEFAULT NULL,
                    `response_timeout` int(11) DEFAULT 30,
                    `max_tokens` int(11) DEFAULT 1000,
                    `temperature` decimal(3,2) DEFAULT 0.70,
                    `corebusiness_api_url` text DEFAULT NULL,
                    `corebusiness_api_key` text DEFAULT NULL,
                    `corebusiness_api_timeout` int(11) DEFAULT 10,
                    `corebusiness_rate_limit` int(11) DEFAULT 100,
                    `claims_api_url` text DEFAULT NULL,
                    `claims_api_key` text DEFAULT NULL,
                    `claims_api_timeout` int(11) DEFAULT 10,
                    `claims_rate_limit` int(11) DEFAULT 50,
                    `assessment_cache_ttl` int(11) DEFAULT 300,
                    `claims_cache_ttl` int(11) DEFAULT 180,
                    `session_cache_ttl` int(11) DEFAULT 3600,
                    `max_concurrent_requests` int(11) DEFAULT 50,
                    `retry_attempts` int(11) DEFAULT 3,
                    `enable_audit_logging` int(1) DEFAULT 1,
                    `wcfcb_contact_phone` varchar(140) DEFAULT NULL,
                    `wcfcb_contact_email` varchar(140) DEFAULT NULL,
                    `wcfcb_office_address` text DEFAULT NULL,
                    `business_hours_start` time DEFAULT NULL,
                    `business_hours_end` time DEFAULT NULL,
                    `default_language` varchar(140) DEFAULT 'en',
                    `enable_multilingual` int(1) DEFAULT 0,
                    `supported_languages` text DEFAULT NULL,
                    `enable_sentiment_analysis` int(1) DEFAULT 0,
                    `auto_escalation_enabled` int(1) DEFAULT 1,
                    `escalation_threshold` decimal(3,2) DEFAULT 0.80,
                    `enable_conversation_logging` int(1) DEFAULT 1,
                    `max_conversation_history` int(11) DEFAULT 100,
                    PRIMARY KEY (`name`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ Table created")
        else:
            print("✅ Table exists")
        
        # Ensure the document exists
        if not frappe.db.exists("Assistant CRM Settings", "Assistant CRM Settings"):
            print("Creating settings document...")
            frappe.db.sql("""
                INSERT INTO `tabAssistant CRM Settings` 
                (name, creation, modified, modified_by, owner, docstatus, enabled)
                VALUES 
                ('Assistant CRM Settings', NOW(), NOW(), 'Administrator', 'Administrator', 0, 1)
            """)
            print("✅ Settings document created")
        else:
            print("✅ Settings document exists")
        
        frappe.db.commit()
        
    except Exception as e:
        print(f"❌ Error ensuring database setup: {str(e)}")
        frappe.db.rollback()
        raise

def initialize_api_values():
    """Initialize API configuration values"""
    
    print("\n🔄 Step 2: Initializing API Values")
    print("-" * 30)
    
    try:
        # Update with API configuration values
        frappe.db.sql("""
            UPDATE `tabAssistant CRM Settings` 
            SET 
                corebusiness_api_url = 'https://api-demo.corebusiness.wcfcb.gov.zm/v1',
                corebusiness_api_key = 'demo_corebusiness_api_key_12345',
                corebusiness_api_timeout = 10,
                corebusiness_rate_limit = 100,
                claims_api_url = 'https://api-demo.claims.wcfcb.gov.zm/v1',
                claims_api_key = 'demo_claims_api_key_67890',
                claims_api_timeout = 10,
                claims_rate_limit = 50,
                assessment_cache_ttl = 300,
                claims_cache_ttl = 180,
                session_cache_ttl = 3600,
                max_concurrent_requests = 50,
                retry_attempts = 3,
                enable_audit_logging = 1,
                modified = NOW()
            WHERE name = 'Assistant CRM Settings'
        """)
        
        frappe.db.commit()
        print("✅ API values initialized")
        
    except Exception as e:
        print(f"❌ Error initializing API values: {str(e)}")
        frappe.db.rollback()
        raise

def test_final_fix():
    """Test the final fix"""
    
    print("\n🧪 Step 3: Testing Final Fix")
    print("-" * 30)
    
    try:
        # Test 1: Get settings document
        settings = frappe.get_single("Assistant CRM Settings")
        print("✅ Settings document retrieved")
        
        # Test 2: Check API fields
        cb_url = getattr(settings, 'corebusiness_api_url', None)
        cb_key = getattr(settings, 'corebusiness_api_key', None)
        claims_url = getattr(settings, 'claims_api_url', None)
        claims_key = getattr(settings, 'claims_api_key', None)
        
        print(f"CoreBusiness URL: {cb_url or 'None'}")
        print(f"CoreBusiness Key: {'***' + cb_key[-4:] if cb_key else 'None'}")
        print(f"Claims URL: {claims_url or 'None'}")
        print(f"Claims Key: {'***' + claims_key[-4:] if claims_key else 'None'}")
        
        # Test 3: Test get_api_config method
        if hasattr(settings, 'get_api_config'):
            print("✅ get_api_config method exists")
            
            # Test CoreBusiness
            cb_config = settings.get_api_config('corebusiness')
            if cb_config and cb_config.get('base_url'):
                print("✅ CoreBusiness config working")
            else:
                print("❌ CoreBusiness config not working")
            
            # Test Claims
            claims_config = settings.get_api_config('claims')
            if claims_config and claims_config.get('base_url'):
                print("✅ Claims config working")
            else:
                print("❌ Claims config not working")
        else:
            print("❌ get_api_config method missing")
        
        # Test 4: Run validation
        print("\n🔬 Running API validation...")
        try:
            from assistant_crm.api.api_testing_framework import validate_api_configuration
            result = validate_api_configuration()
            
            print(f"📊 Overall Status: {result.get('overall_status', 'UNKNOWN')}")
            
            if result.get('overall_status') == 'VALID':
                print("🎉 SUCCESS: API configuration is now VALID!")
                return True
            else:
                print("⚠️  Issues remain:")
                if 'corebusiness_api' in result:
                    print(f"   CoreBusiness: {result['corebusiness_api'].get('status')} - {result['corebusiness_api'].get('error', '')}")
                if 'claims_api' in result:
                    print(f"   Claims: {result['claims_api'].get('status')} - {result['claims_api'].get('error', '')}")
                return False
                
        except Exception as e:
            print(f"❌ Error running validation: {str(e)}")
            return False
        
    except Exception as e:
        print(f"❌ Error testing fix: {str(e)}")
        return False

if __name__ == "__main__":
    frappe.init(site="dev")
    frappe.connect()
    final_api_configuration_fix()
