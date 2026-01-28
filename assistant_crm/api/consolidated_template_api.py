"""
Consolidated Template API - Updated for Enhanced Message Template DocType
Surgical precision updates to work with consolidated template system
"""

import frappe
import json
from frappe.utils import now

# Safe import of translation function
try:
    from frappe import _
except ImportError:
    def _(text):
        return text


class ConsolidatedTemplateService:
    """Service class for handling consolidated template operations"""
    
    def create_template_consolidated(self, template_data):
        """
        Create a new message template with consolidated features
        
        Args:
            template_data (dict): Template data including personalization, channels, filters
            
        Returns:
            dict: Created template document
        """
        try:
            # Prepare template document
            template_doc_data = {
                "doctype": "Message Template",
                "template_name": template_data.get("template_name"),
                "template_type": template_data.get("template_type", "General"),
                "language": template_data.get("language", "en"),
                "category": template_data.get("category"),
                "priority": template_data.get("priority", "Medium"),
                "subject": template_data.get("subject"),
                "content": template_data.get("content"),
                "is_active": template_data.get("is_active", 1),
                "created_by_migration": template_data.get("created_by_migration", 0)
            }
            
            # Add consolidated features
            if template_data.get("personalization_rules"):
                template_doc_data["personalization_rules"] = json.dumps(template_data["personalization_rules"])
            
            if template_data.get("target_channels"):
                template_doc_data["target_channels"] = template_data["target_channels"]
            
            if template_data.get("channel_specific_content"):
                template_doc_data["channel_specific_content"] = json.dumps(template_data["channel_specific_content"])
            
            if template_data.get("filter_conditions"):
                template_doc_data["filter_conditions"] = json.dumps(template_data["filter_conditions"])
            
            # Create template document
            template_doc = frappe.get_doc(template_doc_data)
            template_doc.insert(ignore_permissions=True)
            
            # Add variables if provided
            if template_data.get("variables"):
                self._add_template_variables(template_doc, template_data["variables"])
            
            return {
                "success": True,
                "template": template_doc,
                "message": "Template created successfully"
            }
            
        except Exception as e:
            frappe.log_error(f"Error creating consolidated template: {str(e)}", "Consolidated Template Error")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_template_consolidated(self, template_name, update_data):
        """
        Update an existing message template with consolidated features
        
        Args:
            template_name (str): Template name to update
            update_data (dict): Data to update
            
        Returns:
            dict: Updated template document
        """
        try:
            template_doc = frappe.get_doc("Message Template", template_name)
            
            # Update basic fields
            for field in ["template_type", "language", "category", "priority", "subject", "content", "is_active"]:
                if field in update_data:
                    setattr(template_doc, field, update_data[field])
            
            # Update consolidated features
            if "personalization_rules" in update_data:
                template_doc.personalization_rules = json.dumps(update_data["personalization_rules"])
            
            if "target_channels" in update_data:
                template_doc.target_channels = update_data["target_channels"]
            
            if "channel_specific_content" in update_data:
                template_doc.channel_specific_content = json.dumps(update_data["channel_specific_content"])
            
            if "filter_conditions" in update_data:
                template_doc.filter_conditions = json.dumps(update_data["filter_conditions"])
            
            # Update usage analytics
            template_doc.last_used = now()
            template_doc.usage_count = (template_doc.usage_count or 0) + 1
            
            template_doc.save(ignore_permissions=True)
            
            return {
                "success": True,
                "template": template_doc,
                "message": "Template updated successfully"
            }
            
        except Exception as e:
            frappe.log_error(f"Error updating consolidated template: {str(e)}", "Consolidated Template Error")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_template_consolidated(self, template_name, persona=None, channel=None):
        """
        Get a template with personalization and channel-specific content
        
        Args:
            template_name (str): Template name
            persona (str): User persona for personalization
            channel (str): Channel for channel-specific content
            
        Returns:
            dict: Template with personalized content
        """
        try:
            template_doc = frappe.get_doc("Message Template", template_name)
            
            # Base template data
            template_data = {
                "name": template_doc.name,
                "template_name": template_doc.template_name,
                "template_type": template_doc.template_type,
                "language": template_doc.language,
                "category": template_doc.category,
                "priority": template_doc.priority,
                "subject": template_doc.subject,
                "content": template_doc.content,
                "is_active": template_doc.is_active,
                "usage_count": template_doc.usage_count,
                "success_rate": template_doc.success_rate,
                "last_used": template_doc.last_used
            }
            
            # Apply personalization if available
            if persona and template_doc.personalization_rules:
                try:
                    personalization_rules = json.loads(template_doc.personalization_rules)
                    if persona in personalization_rules:
                        persona_content = personalization_rules[persona]
                        template_data["content"] = persona_content.get("content", template_data["content"])
                        template_data["subject"] = persona_content.get("subject", template_data["subject"])
                except:
                    pass
            
            # Apply channel-specific content if available
            if channel and template_doc.channel_specific_content:
                try:
                    channel_content = json.loads(template_doc.channel_specific_content)
                    if channel in channel_content:
                        channel_data = channel_content[channel]
                        template_data["content"] = channel_data.get("content", template_data["content"])
                        template_data["subject"] = channel_data.get("subject", template_data["subject"])
                except:
                    pass
            
            # Add variables
            template_data["variables"] = self._get_template_variables(template_doc)
            
            # Add filter conditions
            if template_doc.filter_conditions:
                try:
                    template_data["filter_conditions"] = json.loads(template_doc.filter_conditions)
                except:
                    template_data["filter_conditions"] = {}
            
            return {
                "success": True,
                "template": template_data
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting consolidated template: {str(e)}", "Consolidated Template Error")
            return {
                "success": False,
                "error": str(e)
            }
    
    def search_templates_consolidated(self, filters=None, persona=None, channel=None, limit=50):
        """
        Search templates with consolidated filtering
        
        Args:
            filters (dict): Search filters
            persona (str): User persona
            channel (str): Channel
            limit (int): Maximum results
            
        Returns:
            dict: Search results
        """
        try:
            # Build base filters
            base_filters = {"is_active": 1}
            if filters:
                base_filters.update(filters)
            
            # Get templates
            templates = frappe.get_all(
                "Message Template",
                filters=base_filters,
                fields=[
                    "name", "template_name", "template_type", "language", "category",
                    "priority", "subject", "content", "usage_count", "success_rate",
                    "last_used", "personalization_rules", "target_channels",
                    "channel_specific_content", "filter_conditions"
                ],
                order_by="usage_count desc, success_rate desc",
                limit=limit
            )
            
            # Filter by persona and channel
            filtered_templates = []
            for template in templates:
                # Check if template is suitable for persona
                if persona and template.get("personalization_rules"):
                    try:
                        personalization_rules = json.loads(template["personalization_rules"])
                        if persona not in personalization_rules:
                            continue
                    except:
                        pass
                
                # Check if template supports channel
                if channel and template.get("target_channels"):
                    # This would need proper channel checking logic
                    pass
                
                # Check filter conditions
                if template.get("filter_conditions"):
                    try:
                        filter_conditions = json.loads(template["filter_conditions"])
                        # Apply filter logic here
                        if not self._check_filter_conditions(filter_conditions, persona, channel):
                            continue
                    except:
                        pass
                
                filtered_templates.append(template)
            
            return {
                "success": True,
                "templates": filtered_templates,
                "count": len(filtered_templates)
            }
            
        except Exception as e:
            frappe.log_error(f"Error searching consolidated templates: {str(e)}", "Consolidated Template Error")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _add_template_variables(self, template_doc, variables):
        """Add variables to template"""
        for variable in variables:
            variable_doc = frappe.get_doc({
                "doctype": "Template Variable",
                "parent": template_doc.name,
                "parenttype": "Message Template",
                "parentfield": "variables",
                "variable_name": variable.get("name"),
                "variable_type": variable.get("type", "text"),
                "default_value": variable.get("default_value"),
                "description": variable.get("description")
            })
            variable_doc.insert(ignore_permissions=True)
    
    def _get_template_variables(self, template_doc):
        """Get template variables"""
        return frappe.get_all(
            "Template Variable",
            filters={"parent": template_doc.name},
            fields=["variable_name", "variable_type", "default_value", "description"]
        )
    
    def _check_filter_conditions(self, filter_conditions, persona, channel):
        """Check if template matches filter conditions"""
        # Simplified filter checking - would implement proper logic
        if "persona" in filter_conditions:
            if filter_conditions["persona"] != persona:
                return False
        
        if "channel" in filter_conditions:
            if filter_conditions["channel"] != channel:
                return False
        
        return True
    
    def update_template_analytics(self, template_name, success=True):
        """Update template usage analytics"""
        try:
            template_doc = frappe.get_doc("Message Template", template_name)
            
            # Update usage count
            template_doc.usage_count = (template_doc.usage_count or 0) + 1
            template_doc.last_used = now()
            
            # Update success rate
            if template_doc.success_rate is None:
                template_doc.success_rate = 100 if success else 0
            else:
                current_success_count = (template_doc.usage_count - 1) * (template_doc.success_rate / 100)
                if success:
                    current_success_count += 1
                template_doc.success_rate = (current_success_count / template_doc.usage_count) * 100
            
            template_doc.save(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(f"Error updating template analytics: {str(e)}", "Consolidated Template Error")


# Initialize service
consolidated_template_service = ConsolidatedTemplateService()


# ============================================================================
# CONSOLIDATED TEMPLATE API ENDPOINTS
# ============================================================================

@frappe.whitelist()
def create_template_consolidated():
    """Create a new message template with consolidated features"""
    try:
        data = frappe.local.form_dict
        result = consolidated_template_service.create_template_consolidated(data)
        return result

    except Exception as e:
        frappe.log_error(f"Template creation API error: {str(e)}", "Consolidated Template API Error")
        return {"success": False, "error": "Failed to create template"}


@frappe.whitelist()
def update_template_consolidated(template_name):
    """Update an existing message template"""
    try:
        data = frappe.local.form_dict
        result = consolidated_template_service.update_template_consolidated(template_name, data)
        return result

    except Exception as e:
        frappe.log_error(f"Template update API error: {str(e)}", "Consolidated Template API Error")
        return {"success": False, "error": "Failed to update template"}


@frappe.whitelist()
def get_template_consolidated(template_name, persona=None, channel=None):
    """Get a template with personalization and channel-specific content"""
    try:
        result = consolidated_template_service.get_template_consolidated(template_name, persona, channel)
        return result

    except Exception as e:
        frappe.log_error(f"Template get API error: {str(e)}", "Consolidated Template API Error")
        return {"success": False, "error": "Failed to get template"}


@frappe.whitelist()
def search_templates_consolidated(filters=None, persona=None, channel=None, limit=50):
    """Search templates with consolidated filtering"""
    try:
        if filters and isinstance(filters, str):
            filters = json.loads(filters)

        result = consolidated_template_service.search_templates_consolidated(filters, persona, channel, int(limit))
        return result

    except Exception as e:
        frappe.log_error(f"Template search API error: {str(e)}", "Consolidated Template API Error")
        return {"success": False, "error": "Failed to search templates"}


@frappe.whitelist()
def update_template_analytics_consolidated(template_name, success=True):
    """Update template usage analytics"""
    try:
        consolidated_template_service.update_template_analytics(template_name, success)
        return {"success": True, "message": "Analytics updated"}

    except Exception as e:
        frappe.log_error(f"Template analytics API error: {str(e)}", "Consolidated Template API Error")
        return {"success": False, "error": "Failed to update analytics"}
