# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import json
from datetime import datetime


@frappe.whitelist()
def create_campaign(campaign_data):
    """Create a new bulk message campaign"""
    try:
        if isinstance(campaign_data, str):
            campaign_data = json.loads(campaign_data)
        
        # Create campaign document
        campaign = frappe.get_doc({
            "doctype": "Bulk Message Campaign",
            "campaign_name": campaign_data.get("campaign_name"),
            "campaign_type": campaign_data.get("campaign_type", "Broadcast"),
            "status": "Draft",
            "send_immediately": campaign_data.get("send_immediately", 1),
            "scheduled_time": campaign_data.get("scheduled_time"),
            "timezone": campaign_data.get("timezone", "Africa/Lusaka"),
            "custom_message": campaign_data.get("custom_message"),
            "message_template": campaign_data.get("message_template")
        })
        
        # Add channels
        if campaign_data.get("channels"):
            for channel in campaign_data["channels"]:
                campaign.append("channels", {
                    "channel_type": channel.get("channel_type"),
                    "is_enabled": channel.get("is_enabled", 1)
                })
        
        # Add stakeholder types
        if campaign_data.get("stakeholder_types"):
            for stakeholder_type in campaign_data["stakeholder_types"]:
                campaign.append("stakeholder_types", {
                    "stakeholder_type": stakeholder_type
                })
        
        # Add dynamic filters
        if campaign_data.get("dynamic_filters"):
            for filter_item in campaign_data["dynamic_filters"]:
                campaign.append("dynamic_filters", {
                    "field": filter_item.get("field"),
                    "operator": filter_item.get("operator"),
                    "value": filter_item.get("value")
                })
        
        # Add personalization
        if campaign_data.get("personalization"):
            for personalization in campaign_data["personalization"]:
                campaign.append("personalization", {
                    "field_name": personalization.get("field_name"),
                    "placeholder": personalization.get("placeholder"),
                    "is_required": personalization.get("is_required", 0)
                })
        
        campaign.insert()
        frappe.db.commit()
        
        return {
            "success": True,
            "campaign_name": campaign.name,
            "message": "Campaign created successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating campaign: {str(e)}", "Bulk Messaging API")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def execute_campaign(campaign_name):
    """Execute a bulk message campaign"""
    try:
        # Import bulk messaging service
        from assistant_crm.services.bulk_messaging_service import BulkMessagingService
        
        bulk_service = BulkMessagingService()
        result = bulk_service.execute_campaign(campaign_name)
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error executing campaign: {str(e)}", "Bulk Messaging API")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def cancel_campaign(campaign_name):
    """Cancel a running campaign"""
    try:
        campaign = frappe.get_doc("Bulk Message Campaign", campaign_name)
        
        if campaign.status not in ["Running", "Scheduled"]:
            return {
                "success": False,
                "error": "Campaign can only be cancelled if it's running or scheduled"
            }
        
        campaign.status = "Cancelled"
        campaign.save()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Campaign cancelled successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error cancelling campaign: {str(e)}", "Bulk Messaging API")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def get_campaign_statistics(campaign_name):
    """Get campaign statistics"""
    try:
        campaign = frappe.get_doc("Bulk Message Campaign", campaign_name)
        return campaign.get_campaign_statistics()
        
    except Exception as e:
        frappe.log_error(f"Error getting campaign statistics: {str(e)}", "Bulk Messaging API")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def calculate_recipients(campaign_name):
    """Calculate number of recipients for campaign"""
    try:
        campaign = frappe.get_doc("Bulk Message Campaign", campaign_name)
        recipients = campaign.get_target_recipients()
        
        return {
            "success": True,
            "count": len(recipients)
        }
        
    except Exception as e:
        frappe.log_error(f"Error calculating recipients: {str(e)}", "Bulk Messaging API")
        return {
            "success": False,
            "error": str(e),
            "count": 0
        }


@frappe.whitelist()
def preview_recipients(campaign_name, limit=50):
    """Preview recipients for campaign"""
    try:
        campaign = frappe.get_doc("Bulk Message Campaign", campaign_name)
        recipients = campaign.get_target_recipients()
        
        # Limit results for preview
        preview_recipients = recipients[:int(limit)]
        
        return {
            "success": True,
            "recipients": preview_recipients,
            "total": len(recipients),
            "preview_count": len(preview_recipients)
        }
        
    except Exception as e:
        frappe.log_error(f"Error previewing recipients: {str(e)}", "Bulk Messaging API")
        return {
            "success": False,
            "error": str(e),
            "recipients": [],
            "total": 0
        }


@frappe.whitelist()
def send_test_message(campaign_name, test_email):
    """Send test message"""
    try:
        from assistant_crm.services.bulk_messaging_service import BulkMessagingService
        
        bulk_service = BulkMessagingService()
        result = bulk_service.send_test_message(campaign_name, test_email)
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error sending test message: {str(e)}", "Bulk Messaging API")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def get_campaign_list(filters=None):
    """Get list of campaigns with optional filters"""
    try:
        if isinstance(filters, str):
            filters = json.loads(filters)
        
        if not filters:
            filters = {}
        
        campaigns = frappe.get_all(
            "Bulk Message Campaign",
            filters=filters,
            fields=[
                "name", "campaign_name", "campaign_type", "status", 
                "total_recipients", "messages_sent", "messages_delivered", 
                "delivery_rate", "creation", "modified"
            ],
            order_by="modified desc"
        )
        
        return {
            "success": True,
            "campaigns": campaigns
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting campaign list: {str(e)}", "Bulk Messaging API")
        return {
            "success": False,
            "error": str(e),
            "campaigns": []
        }


@frappe.whitelist()
def get_message_templates(language=None):
    """Get available message templates"""
    try:
        filters = {"is_active": 1}
        if language:
            filters["language"] = language
        
        templates = frappe.get_all(
            "Message Template",
            filters=filters,
            fields=["name", "template_name", "template_type", "language", "subject", "content"],
            order_by="template_name"
        )
        
        return {
            "success": True,
            "templates": templates
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting message templates: {str(e)}", "Bulk Messaging API")
        return {
            "success": False,
            "error": str(e),
            "templates": []
        }


@frappe.whitelist()
def get_stakeholder_types():
    """Get available stakeholder types"""
    try:
        # Get unique stakeholder types from contacts
        stakeholder_types = frappe.db.sql("""
            SELECT DISTINCT custom_stakeholder_type as stakeholder_type
            FROM `tabContact`
            WHERE custom_stakeholder_type IS NOT NULL
            AND custom_stakeholder_type != ''
            ORDER BY custom_stakeholder_type
        """, as_dict=True)
        
        return {
            "success": True,
            "stakeholder_types": [st["stakeholder_type"] for st in stakeholder_types]
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting stakeholder types: {str(e)}", "Bulk Messaging API")
        return {
            "success": False,
            "error": str(e),
            "stakeholder_types": []
        }


@frappe.whitelist()
def update_campaign(campaign_name, campaign_data):
    """Update an existing campaign"""
    try:
        if isinstance(campaign_data, str):
            campaign_data = json.loads(campaign_data)
        
        campaign = frappe.get_doc("Bulk Message Campaign", campaign_name)
        
        if campaign.status not in ["Draft", "Scheduled"]:
            return {
                "success": False,
                "error": "Campaign can only be updated if it's in Draft or Scheduled status"
            }
        
        # Update basic fields
        for field in ["campaign_name", "campaign_type", "send_immediately", "scheduled_time", 
                     "timezone", "custom_message", "message_template"]:
            if field in campaign_data:
                setattr(campaign, field, campaign_data[field])
        
        # Update child tables if provided
        if "channels" in campaign_data:
            campaign.channels = []
            for channel in campaign_data["channels"]:
                campaign.append("channels", {
                    "channel_type": channel.get("channel_type"),
                    "is_enabled": channel.get("is_enabled", 1)
                })
        
        if "stakeholder_types" in campaign_data:
            campaign.stakeholder_types = []
            for stakeholder_type in campaign_data["stakeholder_types"]:
                campaign.append("stakeholder_types", {
                    "stakeholder_type": stakeholder_type
                })
        
        campaign.save()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Campaign updated successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error updating campaign: {str(e)}", "Bulk Messaging API")
        return {
            "success": False,
            "error": str(e)
        }
