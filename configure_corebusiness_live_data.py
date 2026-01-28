#!/usr/bin/env python3
"""
WCFCB CoreBusiness Live Data Configuration Script
Configures CoreBusiness Settings for live data integration activation
"""

import frappe
from frappe.utils import now

def configure_corebusiness_settings():
    """Configure CoreBusiness Settings for live data integration"""
    
    print("🔧 Configuring CoreBusiness Settings for Live Data Integration...")
    
    try:
        # Get or create CoreBusiness Settings
        settings = frappe.get_single("CoreBusiness Settings")
        
        # Core Connection Settings
        settings.enabled = 1
        settings.base_url = "https://corebusiness.wcfcb.gov.zm/api"
        settings.api_key = "WCFCB_LIVE_API_KEY_2025"  # Production API key placeholder
        settings.timeout = 30
        
        # Real-time Sync Settings (Already optimal defaults)
        settings.real_time_sync = 1
        settings.sync_interval_minutes = 5  # Optimized for performance
        settings.auto_retry_failed_sync = 1
        settings.max_retry_attempts = 3
        settings.retry_delay_minutes = 5
        
        # API Endpoints (Already have optimal defaults)
        # These are already set in the DocType defaults:
        # - auth_endpoint: "/auth/login"
        # - employers_endpoint: "/employers"
        # - beneficiaries_endpoint: "/beneficiaries"
        # - payments_endpoint: "/payments"
        # - claims_endpoint: "/claims"
        # - compliance_endpoint: "/compliance"
        # - customer_lookup_endpoint: "/customers/lookup"
        
        # Data Field Mapping (Already have optimal defaults)
        # These are already set in the DocType defaults:
        # - employer_id_field: "employer_number"
        # - beneficiary_id_field: "beneficiary_id"
        # - customer_phone_field: "phone"
        # - customer_email_field: "email"
        # - payment_status_field: "payment_status"
        # - compliance_status_field: "compliance_status"
        
        # Save settings
        settings.save()
        frappe.db.commit()
        
        print("✅ CoreBusiness Settings configured successfully!")
        print(f"   - Base URL: {settings.base_url}")
        print(f"   - Real-time Sync: {'Enabled' if settings.real_time_sync else 'Disabled'}")
        print(f"   - Sync Interval: {settings.sync_interval_minutes} minutes")
        print(f"   - Timeout: {settings.timeout} seconds")
        print(f"   - Max Retry Attempts: {settings.max_retry_attempts}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error configuring CoreBusiness Settings: {str(e)}")
        frappe.log_error(f"CoreBusiness configuration error: {str(e)}", "Live Data Configuration")
        return False

def verify_corebusiness_configuration():
    """Verify CoreBusiness Settings configuration"""
    
    print("\n🔍 Verifying CoreBusiness Settings configuration...")
    
    try:
        settings = frappe.get_single("CoreBusiness Settings")
        
        # Verification checklist
        checks = {
            "Integration Enabled": settings.enabled,
            "Base URL Set": bool(settings.base_url),
            "API Key Set": bool(settings.api_key),
            "Real-time Sync Enabled": settings.real_time_sync,
            "Timeout Configured": settings.timeout > 0,
            "Retry Settings": settings.max_retry_attempts > 0
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {check_name}: {status}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n✅ All CoreBusiness Settings verification checks passed!")
        else:
            print("\n⚠️  Some CoreBusiness Settings verification checks failed!")
            
        return all_passed
        
    except Exception as e:
        print(f"❌ Error verifying CoreBusiness Settings: {str(e)}")
        return False

def execute_configuration():
    """Main execution function for Frappe context"""
    # Execute configuration
    success = configure_corebusiness_settings()
    if success:
        verify_corebusiness_configuration()
    else:
        print("❌ CoreBusiness Settings configuration failed!")
    return success

if __name__ == "__main__":
    execute_configuration()
