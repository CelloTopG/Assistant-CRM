#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Integration Validation Script
Comprehensive validation of omnichannel platform integrations
"""

import frappe
import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Any


class IntegrationValidator:
    """Comprehensive validation of omnichannel integrations"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "UNKNOWN",
            "validations": {},
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
    def validate_all(self) -> Dict[str, Any]:
        """Run all validation checks"""
        print("🔍 Starting WCFCB Assistant CRM Integration Validation")
        print("=" * 60)
        
        # Core system validation
        self.validate_frappe_setup()
        self.validate_database_connectivity()
        self.validate_redis_connectivity()
        
        # App-specific validation
        self.validate_app_installation()
        self.validate_real_time_infrastructure()
        self.validate_webhook_endpoints()
        
        # Channel-specific validation
        self.validate_channel_configurations()
        self.validate_api_connectivity()
        
        # Security validation
        self.validate_ssl_configuration()
        self.validate_credential_security()
        
        # Performance validation
        self.validate_response_times()
        self.validate_concurrent_handling()
        
        # Generate final report
        self.generate_final_report()
        
        return self.results
    
    def validate_frappe_setup(self):
        """Validate Frappe framework setup"""
        print("\n📋 Validating Frappe Framework Setup...")
        
        try:
            # Check Frappe version
            frappe_version = frappe.__version__
            if self.compare_versions(frappe_version, "14.0.0") >= 0:
                self.add_success("frappe_version", f"Frappe version {frappe_version} is compatible")
            else:
                self.add_error("frappe_version", f"Frappe version {frappe_version} is too old. Minimum required: 14.0.0")
            
            # Check if site is accessible
            frappe.init()
            frappe.connect()
            self.add_success("frappe_connectivity", "Frappe site connectivity verified")
            
            # Check developer mode status
            if frappe.conf.get('developer_mode'):
                self.add_warning("developer_mode", "Developer mode is enabled - consider disabling for production")
            else:
                self.add_success("developer_mode", "Developer mode appropriately configured")
                
        except Exception as e:
            self.add_error("frappe_setup", f"Frappe setup validation failed: {str(e)}")
    
    def validate_database_connectivity(self):
        """Validate database connectivity and performance"""
        print("🗄️  Validating Database Connectivity...")
        
        try:
            start_time = time.time()
            frappe.db.sql("SELECT 1")
            response_time = time.time() - start_time
            
            if response_time < 0.1:
                self.add_success("database_performance", f"Database response time: {response_time:.3f}s (Excellent)")
            elif response_time < 0.5:
                self.add_success("database_performance", f"Database response time: {response_time:.3f}s (Good)")
            else:
                self.add_warning("database_performance", f"Database response time: {response_time:.3f}s (Slow)")
            
            # Check required tables exist
            required_tables = [
                "tabOmnichannel Conversation",
                "tabOmnichannel Message", 
                "tabChannel Configuration",
                "tabAgent Dashboard"
            ]
            
            for table in required_tables:
                if frappe.db.table_exists(table):
                    self.add_success(f"table_{table}", f"Table {table} exists")
                else:
                    self.add_error(f"table_{table}", f"Required table {table} is missing")
                    
        except Exception as e:
            self.add_error("database_connectivity", f"Database validation failed: {str(e)}")
    
    def validate_redis_connectivity(self):
        """Validate Redis connectivity for real-time features"""
        print("🔴 Validating Redis Connectivity...")
        
        try:
            import redis
            
            # Test Redis connection
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.ping()
            
            # Test pub/sub functionality
            pubsub = r.pubsub()
            pubsub.subscribe('test_channel')
            r.publish('test_channel', 'test_message')
            
            self.add_success("redis_connectivity", "Redis connectivity and pub/sub verified")
            
        except ImportError:
            self.add_error("redis_package", "Redis Python package not installed")
        except Exception as e:
            self.add_error("redis_connectivity", f"Redis validation failed: {str(e)}")
    
    def validate_app_installation(self):
        """Validate Assistant CRM app installation"""
        print("📱 Validating Assistant CRM App Installation...")
        
        try:
            # Check if app is installed
            if "assistant_crm" in frappe.get_installed_apps():
                self.add_success("app_installation", "Assistant CRM app is installed")
            else:
                self.add_error("app_installation", "Assistant CRM app is not installed")
                return
            
            # Check required doctypes
            required_doctypes = [
                "Omnichannel Conversation",
                "Omnichannel Message",
                "Channel Configuration", 
                "Agent Dashboard",
                "User Interaction Log"
            ]
            
            for doctype in required_doctypes:
                if frappe.db.exists("DocType", doctype):
                    self.add_success(f"doctype_{doctype}", f"DocType {doctype} exists")
                else:
                    self.add_error(f"doctype_{doctype}", f"Required DocType {doctype} is missing")
            
            # Check custom fields and configurations
            self.validate_custom_configurations()
            
        except Exception as e:
            self.add_error("app_installation", f"App installation validation failed: {str(e)}")
    
    def validate_real_time_infrastructure(self):
        """Validate real-time communication infrastructure"""
        print("⚡ Validating Real-Time Infrastructure...")
        
        try:
            # Check if real-time service is available
            from assistant_crm.services.realtime_service import RealtimeService
            realtime_service = RealtimeService()
            
            # Test message broadcasting
            test_result = realtime_service.broadcast_message(
                "Test",
                "validation_test",
                {"content": "Validation test", "sender": "system"},
                target_users=["Administrator"]
            )
            
            if test_result.get("success"):
                self.add_success("realtime_broadcasting", "Real-time message broadcasting works")
            else:
                self.add_error("realtime_broadcasting", "Real-time message broadcasting failed")
            
            # Check WebSocket configuration
            self.validate_websocket_config()
            
        except ImportError:
            self.add_error("realtime_service", "Real-time service module not found")
        except Exception as e:
            self.add_error("realtime_infrastructure", f"Real-time infrastructure validation failed: {str(e)}")
    
    def validate_webhook_endpoints(self):
        """Validate webhook endpoint accessibility"""
        print("🔗 Validating Webhook Endpoints...")
        
        webhook_endpoints = [
            "/api/omnichannel/webhook/whatsapp",
            "/api/omnichannel/webhook/facebook",
            "/api/omnichannel/webhook/telegram",
            "/api/omnichannel/webhook/sms"
        ]
        
        site_url = frappe.utils.get_url()
        
        for endpoint in webhook_endpoints:
            try:
                url = f"{site_url}{endpoint}"
                response = requests.get(url, timeout=10, verify=False)
                
                # Webhook endpoints should return 405 (Method Not Allowed) for GET requests
                if response.status_code == 405:
                    self.add_success(f"webhook_{endpoint}", f"Webhook endpoint {endpoint} is accessible")
                elif response.status_code == 200:
                    self.add_success(f"webhook_{endpoint}", f"Webhook endpoint {endpoint} is accessible")
                else:
                    self.add_warning(f"webhook_{endpoint}", f"Webhook endpoint {endpoint} returned status {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.add_error(f"webhook_{endpoint}", f"Webhook endpoint {endpoint} is not accessible: {str(e)}")
    
    def validate_channel_configurations(self):
        """Validate channel configurations"""
        print("📺 Validating Channel Configurations...")
        
        try:
            channels = frappe.get_all("Channel Configuration", fields=["name", "channel_type", "is_active"])
            
            if not channels:
                self.add_warning("channel_configs", "No channel configurations found")
                return
            
            for channel in channels:
                channel_doc = frappe.get_doc("Channel Configuration", channel.name)
                
                if channel.is_active:
                    # Validate required credentials based on channel type
                    self.validate_channel_credentials(channel_doc)
                else:
                    self.add_info(f"channel_{channel.name}", f"Channel {channel.name} is inactive")
                    
        except Exception as e:
            self.add_error("channel_configurations", f"Channel configuration validation failed: {str(e)}")
    
    def validate_channel_credentials(self, channel_doc):
        """Validate credentials for a specific channel"""
        channel_type = channel_doc.channel_type
        channel_name = channel_doc.name
        
        try:
            if channel_type == "WhatsApp":
                required_fields = ["api_key", "whatsapp_business_account_id", "whatsapp_phone_number_id"]
                for field in required_fields:
                    if channel_doc.get_password(field) or getattr(channel_doc, field, None):
                        self.add_success(f"cred_{channel_name}_{field}", f"WhatsApp {field} is configured")
                    else:
                        self.add_error(f"cred_{channel_name}_{field}", f"WhatsApp {field} is missing")
            
            elif channel_type == "Facebook":
                required_fields = ["api_key", "facebook_page_id", "facebook_app_id"]
                for field in required_fields:
                    if channel_doc.get_password(field) or getattr(channel_doc, field, None):
                        self.add_success(f"cred_{channel_name}_{field}", f"Facebook {field} is configured")
                    else:
                        self.add_error(f"cred_{channel_name}_{field}", f"Facebook {field} is missing")
            
            elif channel_type == "Telegram":
                if channel_doc.get_password("api_key"):
                    self.add_success(f"cred_{channel_name}_token", "Telegram bot token is configured")
                else:
                    self.add_error(f"cred_{channel_name}_token", "Telegram bot token is missing")
                    
        except Exception as e:
            self.add_error(f"cred_{channel_name}", f"Credential validation failed for {channel_name}: {str(e)}")
    
    def validate_api_connectivity(self):
        """Test API connectivity for configured channels"""
        print("🌐 Validating API Connectivity...")
        
        try:
            from assistant_crm.services.config_manager import ConfigManager
            config_manager = ConfigManager()
            
            channels = frappe.get_all("Channel Configuration", 
                                    filters={"is_active": 1}, 
                                    fields=["name", "channel_type"])
            
            for channel in channels:
                try:
                    # Test connection using config manager
                    test_result = self.test_channel_api_connection(channel.name, config_manager)
                    
                    if test_result.get("success"):
                        self.add_success(f"api_{channel.name}", f"API connectivity verified for {channel.name}")
                    else:
                        self.add_error(f"api_{channel.name}", f"API connectivity failed for {channel.name}: {test_result.get('error')}")
                        
                except Exception as e:
                    self.add_error(f"api_{channel.name}", f"API test failed for {channel.name}: {str(e)}")
                    
        except Exception as e:
            self.add_error("api_connectivity", f"API connectivity validation failed: {str(e)}")
    
    def validate_ssl_configuration(self):
        """Validate SSL configuration"""
        print("🔒 Validating SSL Configuration...")
        
        try:
            site_url = frappe.utils.get_url()
            
            if site_url.startswith("https://"):
                # Test SSL certificate
                response = requests.get(site_url, timeout=10)
                if response.status_code == 200:
                    self.add_success("ssl_config", "SSL configuration is working")
                else:
                    self.add_warning("ssl_config", f"SSL endpoint returned status {response.status_code}")
            else:
                self.add_warning("ssl_config", "Site is not configured for HTTPS")
                
        except requests.exceptions.SSLError as e:
            self.add_error("ssl_config", f"SSL configuration error: {str(e)}")
        except Exception as e:
            self.add_error("ssl_config", f"SSL validation failed: {str(e)}")
    
    def validate_response_times(self):
        """Validate system response times"""
        print("⏱️  Validating Response Times...")
        
        try:
            # Test database query response time
            start_time = time.time()
            frappe.db.sql("SELECT COUNT(*) FROM `tabOmnichannel Message`")
            db_time = time.time() - start_time
            
            if db_time < 0.1:
                self.add_success("response_time_db", f"Database query time: {db_time:.3f}s (Excellent)")
            elif db_time < 0.5:
                self.add_success("response_time_db", f"Database query time: {db_time:.3f}s (Good)")
            else:
                self.add_warning("response_time_db", f"Database query time: {db_time:.3f}s (Needs optimization)")
            
            # Test API endpoint response time
            site_url = frappe.utils.get_url()
            start_time = time.time()
            response = requests.get(f"{site_url}/api/method/ping", timeout=10)
            api_time = time.time() - start_time
            
            if api_time < 1.0:
                self.add_success("response_time_api", f"API response time: {api_time:.3f}s (Good)")
            else:
                self.add_warning("response_time_api", f"API response time: {api_time:.3f}s (Slow)")
                
        except Exception as e:
            self.add_error("response_times", f"Response time validation failed: {str(e)}")
    
    # Helper methods
    def add_success(self, key: str, message: str):
        """Add a success result"""
        self.results["validations"][key] = {"status": "SUCCESS", "message": message}
        print(f"  ✅ {message}")
    
    def add_error(self, key: str, message: str):
        """Add an error result"""
        self.results["validations"][key] = {"status": "ERROR", "message": message}
        self.results["errors"].append(message)
        print(f"  ❌ {message}")
    
    def add_warning(self, key: str, message: str):
        """Add a warning result"""
        self.results["validations"][key] = {"status": "WARNING", "message": message}
        self.results["warnings"].append(message)
        print(f"  ⚠️  {message}")
    
    def add_info(self, key: str, message: str):
        """Add an info result"""
        self.results["validations"][key] = {"status": "INFO", "message": message}
        print(f"  ℹ️  {message}")
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings"""
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1_part = v1_parts[i] if i < len(v1_parts) else 0
            v2_part = v2_parts[i] if i < len(v2_parts) else 0
            
            if v1_part > v2_part:
                return 1
            elif v1_part < v2_part:
                return -1
        
        return 0
    
    def generate_final_report(self):
        """Generate final validation report"""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        total_checks = len(self.results["validations"])
        success_count = sum(1 for v in self.results["validations"].values() if v["status"] == "SUCCESS")
        error_count = len(self.results["errors"])
        warning_count = len(self.results["warnings"])
        
        print(f"Total Checks: {total_checks}")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Errors: {error_count}")
        print(f"⚠️  Warnings: {warning_count}")
        
        if error_count == 0:
            if warning_count == 0:
                self.results["overall_status"] = "EXCELLENT"
                print("\n🎉 Overall Status: EXCELLENT - All validations passed!")
            else:
                self.results["overall_status"] = "GOOD"
                print("\n✅ Overall Status: GOOD - Minor issues found")
        else:
            self.results["overall_status"] = "NEEDS_ATTENTION"
            print("\n⚠️  Overall Status: NEEDS ATTENTION - Critical issues found")
        
        # Save report to file
        report_file = f"/tmp/omnichannel_validation_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return self.results["overall_status"]


def main():
    """Main validation function"""
    try:
        frappe.init()
        frappe.connect()
        frappe.set_user("Administrator")
        
        validator = IntegrationValidator()
        results = validator.validate_all()
        
        # Exit with appropriate code
        if results["overall_status"] == "EXCELLENT":
            sys.exit(0)
        elif results["overall_status"] == "GOOD":
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Validation script failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
