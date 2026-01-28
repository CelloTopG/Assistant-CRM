#!/usr/bin/env python3
"""
WCFCB CoreBusiness Live Data Configuration
Configures settings for live data integration activation
"""

import frappe

def configure_live_data_settings():
    """Configure both CoreBusiness and Assistant CRM settings for live data"""
    
    print("🔧 Configuring Live Data Integration Settings...")
    
    # Step 1: Configure CoreBusiness Settings
    try:
        print("\n📡 Configuring CoreBusiness Settings...")
        settings = frappe.get_single("CoreBusiness Settings")
        
        # Core Connection Settings
        settings.enabled = 1
        settings.base_url = "https://corebusiness.wcfcb.gov.zm/api"
        settings.api_key = "WCFCB_LIVE_API_KEY_2025"
        settings.timeout = 30
        
        # Real-time Sync Settings
        settings.real_time_sync = 1
        settings.sync_interval_minutes = 5
        settings.auto_retry_failed_sync = 1
        settings.max_retry_attempts = 3
        settings.retry_delay_minutes = 5
        
        settings.save()
        print("✅ CoreBusiness Settings configured successfully!")
        
    except Exception as e:
        print(f"❌ Error configuring CoreBusiness Settings: {str(e)}")
        return False
    
    # Step 2: Configure Assistant CRM Settings
    try:
        print("\n🤖 Configuring Assistant CRM Settings...")
        crm_settings = frappe.get_single("Assistant CRM Settings")

        # Enable Assistant CRM
        crm_settings.enabled = 1

        # Configure CoreBusiness API integration
        crm_settings.corebusiness_api_url = "https://corebusiness.wcfcb.gov.zm/api"
        crm_settings.corebusiness_api_key = "WCFCB_LIVE_API_KEY_2025"
        crm_settings.corebusiness_api_timeout = 30
        crm_settings.corebusiness_rate_limit = 100

        # Configure Claims API integration
        crm_settings.claims_api_url = "https://claims.wcfcb.gov.zm/api"
        crm_settings.claims_api_key = "WCFCB_CLAIMS_API_KEY_2025"
        crm_settings.claims_api_timeout = 30
        crm_settings.claims_rate_limit = 50

        # Cache settings (optimized for performance)
        crm_settings.assessment_cache_ttl = 300  # 5 minutes
        crm_settings.claims_cache_ttl = 300      # 5 minutes
        crm_settings.session_cache_ttl = 1800    # 30 minutes

        # Performance settings
        crm_settings.max_concurrent_requests = 50
        crm_settings.retry_attempts = 3
        crm_settings.enable_audit_logging = 1

        crm_settings.save()
        print("✅ Assistant CRM Settings configured successfully!")

    except Exception as e:
        print(f"❌ Error configuring Assistant CRM Settings: {str(e)}")
        return False
    
    # Commit all changes
    frappe.db.commit()
    
    print("\n🎉 Live Data Integration configuration completed successfully!")
    return True

def verify_live_data_configuration():
    """Verify live data configuration"""
    
    print("\n🔍 Verifying Live Data Configuration...")
    
    try:
        # Check CoreBusiness Settings
        cb_settings = frappe.get_single("CoreBusiness Settings")
        crm_settings = frappe.get_single("Assistant CRM Settings")
        
        checks = {
            "CoreBusiness Integration Enabled": cb_settings.enabled,
            "CoreBusiness Base URL Set": bool(cb_settings.base_url),
            "CoreBusiness API Key Set": bool(cb_settings.api_key),
            "Real-time Sync Enabled": cb_settings.real_time_sync,
            "Assistant CRM Enabled": crm_settings.enabled,
            "Assistant CRM CoreBusiness URL Set": bool(crm_settings.corebusiness_api_url),
            "Assistant CRM CoreBusiness API Key Set": bool(crm_settings.corebusiness_api_key),
            "Cache TTL Configured": crm_settings.assessment_cache_ttl > 0
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {check_name}: {status}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n✅ All configuration verification checks passed!")
            print("\n📊 Configuration Summary:")
            print(f"   - CoreBusiness URL: {cb_settings.base_url}")
            print(f"   - Sync Interval: {cb_settings.sync_interval_minutes} minutes")
            print(f"   - Request Timeout: {cb_settings.timeout} seconds")
            print(f"   - Cache TTL: {crm_settings.assessment_cache_ttl} seconds")
        else:
            print("\n⚠️  Some configuration verification checks failed!")
            
        return all_passed
        
    except Exception as e:
        print(f"❌ Error verifying configuration: {str(e)}")
        return False

def execute():
    """Main execution function"""
    success = configure_live_data_settings()
    if success:
        verify_live_data_configuration()
    return success
