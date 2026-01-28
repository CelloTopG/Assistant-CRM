# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime
import json


class BulkMessageCampaign(Document):
    def validate(self):
        """Validate the bulk message campaign"""
        self.validate_channels()
        self.validate_scheduling()
        self.validate_message_content()
        self.calculate_recipients()
    
    def validate_channels(self):
        """Validate that at least one channel is selected"""
        if not self.channels:
            frappe.throw(_("At least one channel must be selected"))
        
        enabled_channels = [ch for ch in self.channels if ch.is_enabled]
        if not enabled_channels:
            frappe.throw(_("At least one channel must be enabled"))
    
    def validate_scheduling(self):
        """Validate scheduling configuration"""
        if not self.send_immediately and not self.scheduled_time:
            frappe.throw(_("Scheduled time is required when 'Send Immediately' is not checked"))
        
        if self.scheduled_time and self.scheduled_time <= datetime.now():
            frappe.throw(_("Scheduled time must be in the future"))
    
    def validate_message_content(self):
        """Validate message content"""
        if not self.message_template and not self.custom_message:
            frappe.throw(_("Either Message Template or Custom Message must be provided"))
    
    def calculate_recipients(self):
        """Calculate and update total recipients"""
        try:
            recipients = self.get_target_recipients()
            self.total_recipients = len(recipients)
        except Exception as e:
            frappe.log_error(f"Error calculating recipients: {str(e)}", "Bulk Message Campaign")
            self.total_recipients = 0
    
    def get_target_recipients(self):
        """Get target recipients based on filters"""
        conditions = []
        values = {}
        
        # Base query for contacts
        base_query = """
            SELECT name, email_id, mobile_no, first_name, last_name, 
                   company, custom_stakeholder_type, custom_employer_number, custom_pensioner_id
            FROM `tabContact`
            WHERE is_primary_contact = 1
        """
        
        # Stakeholder type filters
        if self.stakeholder_types:
            stakeholder_conditions = []
            for i, stakeholder in enumerate(self.stakeholder_types):
                param_name = f'stakeholder_{i}'
                stakeholder_conditions.append(f'custom_stakeholder_type = %({param_name})s')
                values[param_name] = stakeholder.stakeholder_type
            
            if stakeholder_conditions:
                conditions.append(f"({' OR '.join(stakeholder_conditions)})")
        
        # Dynamic filters
        if self.dynamic_filters:
            for i, filter_item in enumerate(self.dynamic_filters):
                param_name = f'filter_{i}'
                field_name = filter_item.field
                operator = filter_item.operator
                filter_value = filter_item.value
                
                if operator == 'equals':
                    conditions.append(f'{field_name} = %({param_name})s')
                    values[param_name] = filter_value
                elif operator == 'contains':
                    conditions.append(f'{field_name} LIKE %({param_name})s')
                    values[param_name] = f'%{filter_value}%'
                elif operator == 'starts_with':
                    conditions.append(f'{field_name} LIKE %({param_name})s')
                    values[param_name] = f'{filter_value}%'
                elif operator == 'ends_with':
                    conditions.append(f'{field_name} LIKE %({param_name})s')
                    values[param_name] = f'%{filter_value}'
                elif operator == 'in':
                    values_list = [v.strip() for v in filter_value.split(',')]
                    placeholders = [f'%({param_name}_{j})s' for j in range(len(values_list))]
                    conditions.append(f'{field_name} IN ({",".join(placeholders)})')
                    for j, val in enumerate(values_list):
                        values[f'{param_name}_{j}'] = val
                elif operator == 'not_in':
                    values_list = [v.strip() for v in filter_value.split(',')]
                    placeholders = [f'%({param_name}_{j})s' for j in range(len(values_list))]
                    conditions.append(f'{field_name} NOT IN ({",".join(placeholders)})')
                    for j, val in enumerate(values_list):
                        values[f'{param_name}_{j}'] = val
        
        # Build final query
        if conditions:
            query = f"{base_query} AND {' AND '.join(conditions)}"
        else:
            query = base_query
        
        recipients = frappe.db.sql(query, values, as_dict=True)
        return recipients
    
    def get_message_content(self):
        """Get the message content to send"""
        if self.message_template:
            template_doc = frappe.get_doc("Message Template", self.message_template)
            return template_doc.content
        else:
            return self.custom_message
    
    def personalize_message(self, content, recipient):
        """Personalize message for specific recipient"""
        personalized = content
        
        # Standard personalizations
        replacements = {
            '{{first_name}}': recipient.get('first_name', ''),
            '{{last_name}}': recipient.get('last_name', ''),
            '{{full_name}}': f"{recipient.get('first_name', '')} {recipient.get('last_name', '')}".strip(),
            '{{email}}': recipient.get('email_id', ''),
            '{{mobile}}': recipient.get('mobile_no', ''),
            '{{company}}': recipient.get('company', ''),
            '{{employer_number}}': recipient.get('custom_employer_number', ''),
            '{{pensioner_id}}': recipient.get('custom_pensioner_id', '')
        }
        
        # Custom personalizations from campaign
        for personalization in self.personalization:
            field_value = recipient.get(personalization.field_name, '')
            replacements[personalization.placeholder] = str(field_value)
        
        # Apply replacements
        for placeholder, value in replacements.items():
            personalized = personalized.replace(placeholder, value)
        
        return personalized
    
    def execute_campaign(self):
        """Execute the bulk message campaign"""
        if self.status != 'Draft':
            frappe.throw(_('Campaign must be in Draft status to execute'))
        
        # Update status
        self.status = 'Running'
        self.save()
        
        try:
            # Import bulk messaging service
            from assistant_crm.services.bulk_messaging_service import BulkMessagingService
            
            bulk_service = BulkMessagingService()
            result = bulk_service.execute_campaign(self.name)
            
            if result.get('success'):
                self.status = 'Completed'
            else:
                self.status = 'Failed'
                frappe.log_error(f"Campaign execution failed: {result.get('error')}", "Bulk Message Campaign")
            
            self.save()
            return result
            
        except Exception as e:
            self.status = 'Failed'
            self.save()
            frappe.log_error(f"Campaign execution error: {str(e)}", "Bulk Message Campaign")
            frappe.throw(_("Campaign execution failed: {0}").format(str(e)))
    
    def get_campaign_statistics(self):
        """Get campaign statistics"""
        return {
            'total_recipients': self.total_recipients,
            'messages_sent': self.messages_sent,
            'messages_delivered': self.messages_delivered,
            'messages_failed': self.messages_failed,
            'delivery_rate': self.delivery_rate,
            'status': self.status
        }
