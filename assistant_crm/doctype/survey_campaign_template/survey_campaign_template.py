# Copyright (c) 2026, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SurveyCampaignTemplate(Document):
    """Survey Campaign Template for auto-populating survey campaigns with predefined questions and settings"""

    def validate(self):
        """Validate template data"""
        self.validate_questions()

    def validate_questions(self):
        """Ensure at least one question exists and normalize order"""
        if not self.template_questions:
            frappe.throw("At least one survey question is required in the template")

        # Auto-normalize question order
        for i, q in enumerate(self.template_questions, start=1):
            if not q.order:
                q.order = i

    def on_update(self):
        """Track usage when template is accessed"""
        pass

    def increment_usage(self):
        """Increment usage count when template is applied"""
        frappe.db.set_value(
            'Survey Campaign Template',
            self.name,
            'usage_count',
            (self.usage_count or 0) + 1
        )


@frappe.whitelist()
def get_template_data(template_name):
    """Get template data for auto-populating a Survey Campaign.
    
    Args:
        template_name: Name of the Survey Campaign Template
        
    Returns:
        dict with template fields, questions, audience filters, and channels
    """
    if not template_name:
        return {'success': False, 'error': 'Template name is required'}

    if not frappe.db.exists('Survey Campaign Template', template_name):
        return {'success': False, 'error': 'Template not found'}

    template = frappe.get_doc('Survey Campaign Template', template_name)

    # Increment usage count
    template.increment_usage()

    # Build response data
    data = {
        'success': True,
        'template_name': template.template_name,
        'template_category': template.template_category,
        'description': template.description,
        'recommended_for': template.recommended_for,
        'suggested_campaign_name': template.suggested_campaign_name,
        'default_survey_type': template.default_survey_type,
        'questions': [],
        'target_audience': [],
        'distribution_channels': []
    }

    # Add questions
    for q in sorted(template.template_questions or [], key=lambda x: x.order or 0):
        data['questions'].append({
            'question_text': q.question_text,
            'question_type': q.question_type,
            'options': q.options,
            'is_required': q.is_required,
            'order': q.order
        })

    # Add target audience filters
    for a in template.template_audience or []:
        data['target_audience'].append({
            'filter_type': a.filter_type,
            'filter_field': a.filter_field,
            'filter_operator': a.filter_operator,
            'filter_value': a.filter_value
        })

    # Add distribution channels
    for c in template.template_channels or []:
        data['distribution_channels'].append({
            'channel': c.channel,
            'is_active': c.is_active
        })

    return data

