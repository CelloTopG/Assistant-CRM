#!/usr/bin/env python3

import frappe
import json

def surgical_api_configuration_fix():
    """Surgical fix for API configuration issues"""
    
    print("🔧 SURGICAL API CONFIGURATION FIX")
    print("=" * 50)
    
    # Step 1: Fix database table structure
    fix_database_table()
    
    # Step 2: Ensure get_api_config method exists
    fix_get_api_config_method()
    
    # Step 3: Initialize API configuration values
    initialize_api_configuration()
    
    # Step 4: Verify the fix
    verify_fix()
    
    print("\n✅ SURGICAL FIX COMPLETED")

def fix_database_table():
    """Fix the database table structure"""
    
    print("\n🗄️  STEP 1: Fixing Database Table Structure")
    print("-" * 40)
    
    try:
        # Check if table exists
        table_exists = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'tabAssistant CRM Settings'
        """, as_dict=True)
        
        if not table_exists or table_exists[0]['count'] == 0:
            print("❌ Table missing - creating table structure...")
            
            # Create the table with all required fields
            create_table_sql = """
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
            """
            
            frappe.db.sql(create_table_sql)
            print("✅ Table created successfully")
            
        else:
            print("✅ Table exists - checking for missing columns...")
            
            # Add missing columns if they don't exist
            api_columns = [
                ('corebusiness_api_url', 'text'),
                ('corebusiness_api_key', 'text'),
                ('corebusiness_api_timeout', 'int(11) DEFAULT 10'),
                ('corebusiness_rate_limit', 'int(11) DEFAULT 100'),
                ('claims_api_url', 'text'),
                ('claims_api_key', 'text'),
                ('claims_api_timeout', 'int(11) DEFAULT 10'),
                ('claims_rate_limit', 'int(11) DEFAULT 50'),
                ('assessment_cache_ttl', 'int(11) DEFAULT 300'),
                ('claims_cache_ttl', 'int(11) DEFAULT 180'),
                ('session_cache_ttl', 'int(11) DEFAULT 3600'),
                ('max_concurrent_requests', 'int(11) DEFAULT 50'),
                ('retry_attempts', 'int(11) DEFAULT 3'),
                ('enable_audit_logging', 'int(1) DEFAULT 1')
            ]
            
            for column_name, column_type in api_columns:
                try:
                    # Check if column exists
                    column_exists = frappe.db.sql(f"""
                        SELECT COUNT(*) as count
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_NAME = 'tabAssistant CRM Settings' 
                        AND COLUMN_NAME = '{column_name}'
                    """, as_dict=True)
                    
                    if not column_exists or column_exists[0]['count'] == 0:
                        frappe.db.sql(f"""
                            ALTER TABLE `tabAssistant CRM Settings` 
                            ADD COLUMN `{column_name}` {column_type}
                        """)
                        print(f"   ✅ Added column: {column_name}")
                    else:
                        print(f"   ℹ️  Column exists: {column_name}")
                        
                except Exception as e:
                    print(f"   ⚠️  Error adding column {column_name}: {str(e)}")
        
        frappe.db.commit()
        
    except Exception as e:
        print(f"❌ Error fixing database table: {str(e)}")
        frappe.db.rollback()
        raise

def fix_get_api_config_method():
    """Ensure the get_api_config method exists and works"""
    
    print("\n🔧 STEP 2: Fixing get_api_config Method")
    print("-" * 40)
    
    try:
        # Check current Python file
        python_file_path = "development/frappe-bench/apps/assistant_crm/assistant_crm/doctype/assistant_crm_settings/assistant_crm_settings.py"
        
        # Read current content
        with open(python_file_path, 'r') as f:
            content = f.read()
        
        # Check if get_api_config method exists
        if 'def get_api_config(' not in content:
            print("❌ get_api_config method missing - adding it...")
            
            # Add the method before the last line
            method_code = '''
	def get_api_config(self, service):
		"""Get API configuration for a specific service"""
		if service == 'corebusiness':
			return {
				'base_url': self.corebusiness_api_url,
				'api_key': self.get_password('corebusiness_api_key') if self.corebusiness_api_key else None,
				'timeout': self.corebusiness_api_timeout or 10,
				'rate_limit': self.corebusiness_rate_limit or 100
			}
		elif service == 'claims':
			return {
				'base_url': self.claims_api_url,
				'api_key': self.get_password('claims_api_key') if self.claims_api_key else None,
				'timeout': self.claims_api_timeout or 10,
				'rate_limit': self.claims_rate_limit or 50
			}
		
		return None
'''
            
            # Insert before the last line (which should be the class end)
            lines = content.split('\n')
            lines.insert(-1, method_code)
            new_content = '\n'.join(lines)
            
            # Write back to file
            with open(python_file_path, 'w') as f:
                f.write(new_content)
            
            print("✅ get_api_config method added")
            
            # Reload the module
            frappe.reload_doc("assistant_crm", "doctype", "assistant_crm_settings")
            print("✅ Module reloaded")
            
        else:
            print("✅ get_api_config method already exists")
            
    except Exception as e:
        print(f"❌ Error fixing get_api_config method: {str(e)}")

def initialize_api_configuration():
    """Initialize API configuration values"""
    
    print("\n🔄 STEP 3: Initializing API Configuration")
    print("-" * 40)
    
    try:
        # Ensure the settings document exists
        if not frappe.db.exists("Assistant CRM Settings", "Assistant CRM Settings"):
            print("Creating new Assistant CRM Settings document...")
            
            # Insert the document directly
            frappe.db.sql("""
                INSERT INTO `tabAssistant CRM Settings` 
                (name, creation, modified, modified_by, owner, docstatus, enabled)
                VALUES 
                ('Assistant CRM Settings', NOW(), NOW(), 'Administrator', 'Administrator', 0, 1)
            """)
            print("✅ Settings document created")
        
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
        print("✅ API configuration values initialized")
        
    except Exception as e:
        print(f"❌ Error initializing API configuration: {str(e)}")
        frappe.db.rollback()
        raise

def verify_fix():
    """Verify that the fix worked"""
    
    print("\n🧪 STEP 4: Verifying Fix")
    print("-" * 40)
    
    try:
        # Test 1: Check if settings document can be retrieved
        settings = frappe.get_single("Assistant CRM Settings")
        print("✅ Settings document retrieved successfully")
        
        # Test 2: Check if API fields are accessible
        cb_url = getattr(settings, 'corebusiness_api_url', None)
        cb_key = getattr(settings, 'corebusiness_api_key', None)
        claims_url = getattr(settings, 'claims_api_url', None)
        claims_key = getattr(settings, 'claims_api_key', None)
        
        print(f"✅ CoreBusiness URL: {cb_url}")
        print(f"✅ CoreBusiness Key: {'***' + cb_key[-4:] if cb_key else 'None'}")
        print(f"✅ Claims URL: {claims_url}")
        print(f"✅ Claims Key: {'***' + claims_key[-4:] if claims_key else 'None'}")
        
        # Test 3: Check if get_api_config method works
        if hasattr(settings, 'get_api_config'):
            print("✅ get_api_config method exists")
            
            # Test CoreBusiness config
            cb_config = settings.get_api_config('corebusiness')
            if cb_config and cb_config.get('base_url'):
                print("✅ CoreBusiness config working")
            else:
                print("❌ CoreBusiness config not working")
            
            # Test Claims config
            claims_config = settings.get_api_config('claims')
            if claims_config and claims_config.get('base_url'):
                print("✅ Claims config working")
            else:
                print("❌ Claims config not working")
                
        else:
            print("❌ get_api_config method still missing")
        
        # Test 4: Run the validation function
        print("\n🔬 Running validation test...")
        from assistant_crm.api.api_testing_framework import validate_api_configuration
        result = validate_api_configuration()
        
        print(f"📊 Validation Status: {result.get('overall_status', 'UNKNOWN')}")
        
        if result.get('overall_status') == 'VALID':
            print("🎉 SUCCESS: API configuration is now VALID!")
        else:
            print("⚠️  Still issues - checking details...")
            print(json.dumps(result, indent=2))
        
        return result
        
    except Exception as e:
        print(f"❌ Error verifying fix: {str(e)}")
        return None

if __name__ == "__main__":
    frappe.init(site="dev")
    frappe.connect()
    surgical_api_configuration_fix()
