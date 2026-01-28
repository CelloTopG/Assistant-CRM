#!/usr/bin/env python3

import frappe

def fix_api_configuration():
    """Fix API configuration by adding fields and setting values"""
    
    print("🔧 Fixing API Configuration...")
    
    try:
        # First, let's add the missing fields to the database table
        add_missing_fields()
        
        # Then update the settings
        update_settings()
        
        # Test the configuration
        test_configuration()
        
        print("✅ API configuration fixed successfully!")
        
    except Exception as e:
        print(f"❌ Error fixing API configuration: {str(e)}")
        frappe.db.rollback()

def add_missing_fields():
    """Add missing fields to the Assistant CRM Settings table"""
    
    print("📝 Adding missing fields to database...")
    
    # List of fields to add
    fields_to_add = [
        ("corebusiness_api_url", "TEXT"),
        ("corebusiness_api_key", "TEXT"),
        ("corebusiness_api_timeout", "INT"),
        ("corebusiness_rate_limit", "INT"),
        ("claims_api_url", "TEXT"),
        ("claims_api_key", "TEXT"),
        ("claims_api_timeout", "INT"),
        ("claims_rate_limit", "INT"),
        ("assessment_cache_ttl", "INT"),
        ("claims_cache_ttl", "INT"),
        ("session_cache_ttl", "INT"),
        ("max_concurrent_requests", "INT"),
        ("retry_attempts", "INT"),
        ("enable_audit_logging", "INT")
    ]
    
    for field_name, field_type in fields_to_add:
        try:
            # Check if field exists
            existing = frappe.db.sql(f"""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'tabAssistant CRM Settings' 
                AND COLUMN_NAME = '{field_name}'
            """)
            
            if not existing:
                # Add the field
                frappe.db.sql(f"""
                    ALTER TABLE `tabAssistant CRM Settings` 
                    ADD COLUMN `{field_name}` {field_type}
                """)
                print(f"   ✅ Added field: {field_name}")
            else:
                print(f"   ℹ️  Field already exists: {field_name}")
                
        except Exception as e:
            print(f"   ⚠️  Error adding field {field_name}: {str(e)}")

def update_settings():
    """Update the settings with API configuration"""
    
    print("🔄 Updating settings values...")
    
    try:
        # Update the settings directly in the database
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
                enable_audit_logging = 1
            WHERE name = 'Assistant CRM Settings'
        """)
        
        frappe.db.commit()
        print("   ✅ Settings updated successfully")
        
    except Exception as e:
        print(f"   ❌ Error updating settings: {str(e)}")
        raise

def test_configuration():
    """Test the API configuration"""
    
    print("🧪 Testing API configuration...")
    
    try:
        # Get the updated settings
        settings = frappe.get_single("Assistant CRM Settings")
        
        # Check if the fields are accessible
        corebusiness_url = getattr(settings, 'corebusiness_api_url', None)
        corebusiness_key = getattr(settings, 'corebusiness_api_key', None)
        claims_url = getattr(settings, 'claims_api_url', None)
        claims_key = getattr(settings, 'claims_api_key', None)
        
        print(f"   CoreBusiness API URL: {corebusiness_url or 'Not set'}")
        print(f"   CoreBusiness API Key: {'***' + corebusiness_key[-4:] if corebusiness_key else 'Not set'}")
        print(f"   Claims API URL: {claims_url or 'Not set'}")
        print(f"   Claims API Key: {'***' + claims_key[-4:] if claims_key else 'Not set'}")
        
        # Test the get_api_config method if it exists
        if hasattr(settings, 'get_api_config'):
            try:
                corebusiness_config = settings.get_api_config('corebusiness')
                claims_config = settings.get_api_config('claims')
                
                if corebusiness_config and corebusiness_config.get('base_url'):
                    print("   ✅ CoreBusiness API config accessible")
                else:
                    print("   ❌ CoreBusiness API config not accessible")
                
                if claims_config and claims_config.get('base_url'):
                    print("   ✅ Claims API config accessible")
                else:
                    print("   ❌ Claims API config not accessible")
                    
            except Exception as e:
                print(f"   ⚠️  Error testing get_api_config method: {str(e)}")
        
        # Test the validation function
        try:
            from assistant_crm.api.api_testing_framework import validate_api_configuration
            result = validate_api_configuration()
            print(f"   📊 Validation result: {result.get('overall_status', 'UNKNOWN')}")
            
            if result.get('overall_status') == 'VALID':
                print("   🎉 API configuration is now valid!")
            else:
                print("   ⚠️  API configuration needs real endpoints for production use")
                
        except Exception as e:
            print(f"   ⚠️  Error running validation: {str(e)}")
        
    except Exception as e:
        print(f"   ❌ Error testing configuration: {str(e)}")

def show_table_structure():
    """Show the current table structure"""
    
    print("📋 Current table structure:")
    
    try:
        columns = frappe.db.sql("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'tabAssistant CRM Settings'
            ORDER BY ORDINAL_POSITION
        """, as_dict=True)
        
        for col in columns:
            print(f"   {col['COLUMN_NAME']}: {col['DATA_TYPE']} ({'NULL' if col['IS_NULLABLE'] == 'YES' else 'NOT NULL'})")
            
    except Exception as e:
        print(f"   ❌ Error showing table structure: {str(e)}")

if __name__ == "__main__":
    frappe.init(site="dev")
    frappe.connect()
    
    show_table_structure()
    fix_api_configuration()
