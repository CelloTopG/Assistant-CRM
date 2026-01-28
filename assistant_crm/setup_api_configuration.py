#!/usr/bin/env python3

import frappe

def setup_api_configuration():
    """Setup API configuration for WCFCB Assistant CRM"""
    
    print("🔧 Setting up API Configuration for WCFCB Assistant CRM...")
    
    try:
        # Get or create Assistant CRM Settings
        settings = get_or_create_settings()
        
        # Configure API endpoints with demo/test values
        configure_api_endpoints(settings)
        
        # Configure performance and caching settings
        configure_performance_settings(settings)
        
        # Save the settings
        settings.save()
        frappe.db.commit()
        
        print("✅ API Configuration setup completed successfully!")
        
        # Test the configuration
        test_configuration(settings)
        
        return settings
        
    except Exception as e:
        print(f"❌ Error setting up API configuration: {str(e)}")
        frappe.db.rollback()
        raise

def get_or_create_settings():
    """Get existing settings or create new ones"""
    
    try:
        # Try to get existing settings
        settings = frappe.get_single("Assistant CRM Settings")
        print("📋 Found existing Assistant CRM Settings")
        return settings
        
    except frappe.DoesNotExistError:
        # Create new settings document
        print("📝 Creating new Assistant CRM Settings")
        settings = frappe.new_doc("Assistant CRM Settings")
        
        # Set basic configuration
        settings.enabled = 1
        settings.ai_provider = "OpenAI"
        settings.model_name = "gpt-3.5-turbo"
        settings.response_timeout = 30
        settings.max_tokens = 1000
        settings.temperature = 0.7
        
        return settings

def configure_api_endpoints(settings):
    """Configure API endpoints with demo/development values"""
    
    print("🔗 Configuring API endpoints...")
    
    # CoreBusiness API Configuration
    if not settings.corebusiness_api_url:
        settings.corebusiness_api_url = "https://api-demo.corebusiness.wcfcb.gov.zm/v1"
        print("   Set CoreBusiness API URL to demo endpoint")
    
    if not settings.corebusiness_api_key:
        settings.corebusiness_api_key = "demo_corebusiness_api_key_12345"
        print("   Set CoreBusiness API Key to demo value")
    
    if not settings.corebusiness_api_timeout:
        settings.corebusiness_api_timeout = 10
    
    if not settings.corebusiness_rate_limit:
        settings.corebusiness_rate_limit = 100
    
    # Claims API Configuration
    if not settings.claims_api_url:
        settings.claims_api_url = "https://api-demo.claims.wcfcb.gov.zm/v1"
        print("   Set Claims API URL to demo endpoint")
    
    if not settings.claims_api_key:
        settings.claims_api_key = "demo_claims_api_key_67890"
        print("   Set Claims API Key to demo value")
    
    if not settings.claims_api_timeout:
        settings.claims_api_timeout = 10
    
    if not settings.claims_rate_limit:
        settings.claims_rate_limit = 50

def configure_performance_settings(settings):
    """Configure performance and caching settings"""
    
    print("⚡ Configuring performance settings...")
    
    # Cache settings
    if not settings.assessment_cache_ttl:
        settings.assessment_cache_ttl = 300  # 5 minutes
    
    if not settings.claims_cache_ttl:
        settings.claims_cache_ttl = 180  # 3 minutes
    
    if not settings.session_cache_ttl:
        settings.session_cache_ttl = 3600  # 1 hour
    
    # Performance settings
    if not settings.max_concurrent_requests:
        settings.max_concurrent_requests = 50
    
    if not settings.retry_attempts:
        settings.retry_attempts = 3
    
    if not settings.enable_audit_logging:
        settings.enable_audit_logging = 1
    
    print("   Configured cache TTL and performance limits")

def test_configuration(settings):
    """Test the API configuration"""
    
    print("\n🧪 Testing API Configuration...")
    
    try:
        # Test CoreBusiness API config
        corebusiness_config = settings.get_api_config('corebusiness')
        if corebusiness_config and corebusiness_config.get('base_url') and corebusiness_config.get('api_key'):
            print("✅ CoreBusiness API configuration valid")
            print(f"   URL: {corebusiness_config['base_url']}")
            print(f"   API Key: {'*' * (len(corebusiness_config['api_key']) - 4) + corebusiness_config['api_key'][-4:]}")
        else:
            print("❌ CoreBusiness API configuration invalid")
        
        # Test Claims API config
        claims_config = settings.get_api_config('claims')
        if claims_config and claims_config.get('base_url') and claims_config.get('api_key'):
            print("✅ Claims API configuration valid")
            print(f"   URL: {claims_config['base_url']}")
            print(f"   API Key: {'*' * (len(claims_config['api_key']) - 4) + claims_config['api_key'][-4:]}")
        else:
            print("❌ Claims API configuration invalid")
        
        # Test the validation function
        from .api.api_testing_framework import validate_api_configuration
        validation_result = validate_api_configuration()
        
        print(f"\n📊 Overall API Status: {validation_result.get('overall_status', 'UNKNOWN')}")
        
        if validation_result.get('overall_status') == 'VALID':
            print("🎉 All API configurations are valid and ready for use!")
        elif validation_result.get('overall_status') == 'PARTIAL':
            print("⚠️  Some API configurations are valid, others need attention")
        else:
            print("❌ API configurations need to be updated with real values")
            print("\n📝 Next Steps:")
            print("1. Update CoreBusiness API URL and key with real values")
            print("2. Update Claims API URL and key with real values")
            print("3. Test connectivity to actual API endpoints")
        
        return validation_result
        
    except Exception as e:
        print(f"❌ Error testing configuration: {str(e)}")
        return None

def update_api_credentials(corebusiness_url=None, corebusiness_key=None, claims_url=None, claims_key=None):
    """Update API credentials with real values"""
    
    print("🔑 Updating API credentials...")
    
    try:
        settings = frappe.get_single("Assistant CRM Settings")
        
        if corebusiness_url:
            settings.corebusiness_api_url = corebusiness_url
            print(f"✅ Updated CoreBusiness API URL")
        
        if corebusiness_key:
            settings.corebusiness_api_key = corebusiness_key
            print(f"✅ Updated CoreBusiness API Key")
        
        if claims_url:
            settings.claims_api_url = claims_url
            print(f"✅ Updated Claims API URL")
        
        if claims_key:
            settings.claims_api_key = claims_key
            print(f"✅ Updated Claims API Key")
        
        settings.save()
        frappe.db.commit()
        
        print("✅ API credentials updated successfully!")
        
        # Test the updated configuration
        test_configuration(settings)
        
        return settings
        
    except Exception as e:
        print(f"❌ Error updating credentials: {str(e)}")
        frappe.db.rollback()
        raise

def show_configuration_status():
    """Show current configuration status"""
    
    print("📊 Current API Configuration Status")
    print("=" * 50)
    
    try:
        settings = frappe.get_single("Assistant CRM Settings")
        
        print(f"System Enabled: {'✅ Yes' if settings.enabled else '❌ No'}")
        print(f"Audit Logging: {'✅ Enabled' if settings.enable_audit_logging else '❌ Disabled'}")
        
        print(f"\n🔗 API Endpoints:")
        print(f"CoreBusiness API: {settings.corebusiness_api_url or '❌ Not configured'}")
        print(f"Claims API: {settings.claims_api_url or '❌ Not configured'}")
        
        print(f"\n⚡ Performance Settings:")
        print(f"Assessment Cache TTL: {settings.assessment_cache_ttl or 300} seconds")
        print(f"Claims Cache TTL: {settings.claims_cache_ttl or 180} seconds")
        print(f"Max Concurrent Requests: {settings.max_concurrent_requests or 50}")
        print(f"Retry Attempts: {settings.retry_attempts or 3}")
        
        print(f"\n🔒 Security:")
        print(f"CoreBusiness API Key: {'✅ Configured' if settings.corebusiness_api_key else '❌ Missing'}")
        print(f"Claims API Key: {'✅ Configured' if settings.claims_api_key else '❌ Missing'}")
        
        # Test current configuration
        from .api.api_testing_framework import validate_api_configuration
        validation_result = validate_api_configuration()
        print(f"\n📊 Validation Status: {validation_result.get('overall_status', 'UNKNOWN')}")
        
    except Exception as e:
        print(f"❌ Error retrieving configuration: {str(e)}")

def reset_to_demo_configuration():
    """Reset configuration to demo values"""
    
    print("🔄 Resetting to demo configuration...")
    
    try:
        settings = frappe.get_single("Assistant CRM Settings")
        
        # Reset to demo values
        settings.corebusiness_api_url = "https://api-demo.corebusiness.wcfcb.gov.zm/v1"
        settings.corebusiness_api_key = "demo_corebusiness_api_key_12345"
        settings.claims_api_url = "https://api-demo.claims.wcfcb.gov.zm/v1"
        settings.claims_api_key = "demo_claims_api_key_67890"
        
        settings.save()
        frappe.db.commit()
        
        print("✅ Configuration reset to demo values")
        
        # Test the demo configuration
        test_configuration(settings)
        
        return settings
        
    except Exception as e:
        print(f"❌ Error resetting configuration: {str(e)}")
        frappe.db.rollback()
        raise

if __name__ == "__main__":
    frappe.init(site="dev")
    frappe.connect()
    setup_api_configuration()
