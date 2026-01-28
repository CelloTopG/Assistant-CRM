# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import os
import frappe
from frappe.utils import get_site_path


def load_environment_variables(bootinfo):
    """Load environment variables from .env.wcfcb file on boot

    Args:
        bootinfo (dict): Boot information dictionary passed by Frappe
    """
    # Call the internal function to do the actual work
    _load_environment_variables_internal()


def load_env_file(file_path):
    """Load environment variables from a file"""
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Set environment variable if not already set
                    if key and not os.getenv(key):
                        os.environ[key] = value
                        
    except Exception as e:
        frappe.logger().error(f"Error reading environment file {file_path}: {str(e)}")


def get_environment_status():
    """Get status of environment variables for monitoring"""
    try:
        required_vars = [
            "GEMINI_API_KEY",
            "WHATSAPP_PHONE_NUMBER_ID", 
            "WHATSAPP_ACCESS_TOKEN",
            "WHATSAPP_VERIFY_TOKEN",
            "FACEBOOK_PAGE_ACCESS_TOKEN",
            "FACEBOOK_VERIFY_TOKEN",
            "TELEGRAM_BOT_TOKEN",
            "INSTAGRAM_ACCESS_TOKEN"
        ]
        
        status = {
            "loaded_vars": {},
            "missing_vars": [],
            "total_env_vars": len(os.environ)
        }
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                # Mask sensitive values for security
                if len(value) > 10:
                    masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:]
                else:
                    masked_value = "*" * len(value)
                status["loaded_vars"][var] = masked_value
            else:
                status["missing_vars"].append(var)
        
        return status
        
    except Exception as e:
        frappe.logger().error(f"Error getting environment status: {str(e)}")
        return {
            "error": str(e),
            "loaded_vars": {},
            "missing_vars": [],
            "total_env_vars": 0
        }


def validate_critical_environment_variables():
    """Validate that critical environment variables are set"""
    try:
        critical_vars = ["GEMINI_API_KEY"]
        missing_critical = []
        
        for var in critical_vars:
            if not os.getenv(var):
                missing_critical.append(var)
        
        if missing_critical:
            frappe.logger().warning(
                f"Critical environment variables missing: {', '.join(missing_critical)}"
            )
            return False, missing_critical
        
        return True, []
        
    except Exception as e:
        frappe.logger().error(f"Error validating environment variables: {str(e)}")
        return False, [str(e)]


def _load_environment_variables_internal():
    """Internal function to load environment variables without bootinfo parameter"""
    try:
        # Get the site path
        site_path = get_site_path()
        bench_path = os.path.dirname(os.path.dirname(site_path))

        # Look for .env.wcfcb file in bench directory
        env_file_path = os.path.join(bench_path, ".env.wcfcb")

        if os.path.exists(env_file_path):
            load_env_file(env_file_path)
            frappe.logger().info(f"Loaded environment variables from {env_file_path}")
        else:
            frappe.logger().info(f"Environment file not found at {env_file_path}")

        # Also check for .env file as fallback
        fallback_env_path = os.path.join(bench_path, ".env")
        if os.path.exists(fallback_env_path):
            load_env_file(fallback_env_path)
            frappe.logger().info(f"Loaded fallback environment variables from {fallback_env_path}")

    except Exception as e:
        frappe.logger().error(f"Error loading environment variables: {str(e)}")


def refresh_environment_variables():
    """Refresh environment variables (useful for development)"""
    try:
        _load_environment_variables_internal()

        # Clear any cached settings to force reload
        frappe.cache().delete_value("assistant_crm_settings")

        return True, "Environment variables refreshed successfully"

    except Exception as e:
        frappe.logger().error(f"Error refreshing environment variables: {str(e)}")
        return False, str(e)


# Auto-load environment variables when module is imported
if not frappe.flags.in_test:
    try:
        _load_environment_variables_internal()
    except Exception as e:
        frappe.logger().error(f"Error auto-loading environment variables: {str(e)}")
