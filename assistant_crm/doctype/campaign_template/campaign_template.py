# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CampaignTemplate(Document):
    """Pre-built campaign templates for bulk messaging"""
    
    def validate(self):
        """Validate campaign template"""
        self.validate_unique_template_name()
    
    def validate_unique_template_name(self):
        """Ensure template name is unique"""
        if self.template_name:
            existing = frappe.db.get_value(
                "Campaign Template", 
                {"template_name": self.template_name, "name": ["!=", self.name]}, 
                "name"
            )
            if existing:
                frappe.throw(f"Template name '{self.template_name}' already exists")
    
    def create_campaign_from_template(self, campaign_name, custom_settings=None):
        """Create a new bulk message campaign from this template"""
        try:
            # Create new campaign
            campaign = frappe.get_doc({
                "doctype": "Bulk Message Campaign",
                "campaign_name": campaign_name,
                "campaign_type": "Targeted",
                "message_template": self.message_template,
                "timezone": self.default_timezone,
                "status": "Draft"
            })
            
            # Add default channels
            for channel in self.default_channels:
                campaign.append("channels", {
                    "channel_type": channel.channel_type,
                    "is_active": channel.is_active
                })
            
            # Add default filters
            for filter_item in self.default_filters:
                campaign.append("dynamic_filters", {
                    "field": filter_item.field,
                    "operator": filter_item.operator,
                    "value": filter_item.value
                })
            
            # Add personalization fields
            for pers_field in self.personalization_fields:
                campaign.append("personalization", {
                    "field_name": pers_field.field_name,
                    "field_value": pers_field.field_value
                })
            
            # Apply custom settings if provided
            if custom_settings:
                for key, value in custom_settings.items():
                    if hasattr(campaign, key):
                        setattr(campaign, key, value)
            
            campaign.insert()
            
            # Update template usage statistics
            self.usage_count = (self.usage_count or 0) + 1
            self.save(ignore_permissions=True)
            
            return campaign.name
            
        except Exception as e:
            frappe.log_error(f"Error creating campaign from template: {str(e)}", "Campaign Template")
            frappe.throw(f"Failed to create campaign: {str(e)}")
    
    def update_success_rate(self, campaign_success):
        """Update template success rate based on campaign performance"""
        try:
            if self.usage_count == 1:
                self.success_rate = 100.0 if campaign_success else 0.0
            else:
                current_successes = (self.success_rate / 100.0) * (self.usage_count - 1)
                if campaign_success:
                    current_successes += 1
                self.success_rate = (current_successes / self.usage_count) * 100.0
            
            self.save(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(f"Error updating template success rate: {str(e)}", "Campaign Template")


@frappe.whitelist()
def get_templates_by_category(category):
    """Get campaign templates by category"""
    return frappe.get_all(
        "Campaign Template",
        filters={"template_category": category, "is_active": 1},
        fields=["name", "template_name", "description", "target_audience", "recommended_frequency"],
        order_by="usage_count desc"
    )


@frappe.whitelist()
def create_campaign_from_template(template_name, campaign_name, custom_settings=None):
    """API endpoint to create campaign from template"""
    try:
        template = frappe.get_doc("Campaign Template", template_name)
        
        # Parse custom settings if provided as JSON string
        if custom_settings and isinstance(custom_settings, str):
            import json
            custom_settings = json.loads(custom_settings)
        
        campaign_id = template.create_campaign_from_template(campaign_name, custom_settings)
        
        return {
            "success": True,
            "campaign_id": campaign_id,
            "message": f"Campaign '{campaign_name}' created successfully from template"
        }
        
    except Exception as e:
        frappe.log_error(f"Error in create_campaign_from_template API: {str(e)}", "Campaign Template API")
        return {
            "success": False,
            "error": str(e)
        }
