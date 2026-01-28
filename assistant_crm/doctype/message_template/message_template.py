# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import re


class MessageTemplate(Document):
    def validate(self):
        """Validate the message template"""
        self.validate_variables()
        self.extract_variables_from_content()
    
    def validate_variables(self):
        """Validate that all variables in content are defined"""
        if not self.content:
            return
        
        # Extract variables from content using regex
        content_variables = re.findall(r'\{\{(\w+)\}\}', self.content)
        
        # Get defined variables
        defined_variables = [var.variable_name for var in self.variables]
        
        # Check for undefined variables
        undefined_variables = set(content_variables) - set(defined_variables)
        
        if undefined_variables:
            frappe.msgprint(_("Warning: The following variables are used in content but not defined: {0}").format(
                ", ".join(undefined_variables)), alert=True)
    
    def extract_variables_from_content(self):
        """Auto-extract variables from content if none defined"""
        if not self.content or self.variables:
            return
        
        # Extract variables from content
        content_variables = re.findall(r'\{\{(\w+)\}\}', self.content)
        
        # Add unique variables
        for var in set(content_variables):
            self.append("variables", {
                "variable_name": var,
                "description": f"Auto-extracted variable: {var}",
                "default_value": ""
            })
    
    def render_template(self, context_data):
        """Render template with provided context data"""
        if not self.content:
            return ""
        
        rendered_content = self.content
        
        # Replace variables with context data
        for var in self.variables:
            variable_name = var.variable_name
            placeholder = f"{{{{{variable_name}}}}}"
            
            # Get value from context or use default
            value = context_data.get(variable_name, var.default_value or "")
            
            rendered_content = rendered_content.replace(placeholder, str(value))
        
        return rendered_content
    
    def get_template_variables(self):
        """Get list of template variables"""
        return [{"name": var.variable_name, "description": var.description, "default": var.default_value} 
                for var in self.variables]
