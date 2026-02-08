# Copyright (c) 2026, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json

# OpenAI API configuration - API key should be set in site_config.json as "openai_api_key"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


def get_openai_api_key():
    """Get OpenAI API key from site configuration.

    The API key should be set in site_config.json:
    bench --site <sitename> set-config openai_api_key "your-api-key-here"
    """
    api_key = frappe.conf.get("openai_api_key")
    if not api_key:
        frappe.throw("OpenAI API key not configured. Please set 'openai_api_key' in site_config.json")
    return api_key


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


def _call_openai(prompt, max_tokens=500):
    """Internal function to call OpenAI API.

    Args:
        prompt: The prompt to send to OpenAI
        max_tokens: Maximum tokens in response

    Returns:
        str: The AI response text or None on error
    """
    import requests

    try:
        api_key = get_openai_api_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates professional survey content for a CRM system. Be concise and professional."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"].strip()

    except requests.exceptions.RequestException as e:
        frappe.log_error(f"OpenAI API Error: {str(e)}", "AI Suggestion Error")
        return None
    except (KeyError, IndexError) as e:
        frappe.log_error(f"OpenAI Response Parse Error: {str(e)}", "AI Suggestion Error")
        return None


@frappe.whitelist()
def get_ai_description(template_name, template_category):
    """Generate AI suggestion for template description.

    Args:
        template_name: Name of the template
        template_category: Category of the template

    Returns:
        dict with success status and suggestion
    """
    if not template_name:
        return {"success": False, "error": "Template name is required"}

    prompt = f"""Generate a professional, concise description (2-3 sentences) for a survey template with the following details:

Template Name: {template_name}
Category: {template_category or 'General Survey'}

The description should explain what the survey measures and its purpose. Keep it under 200 characters."""

    suggestion = _call_openai(prompt, max_tokens=150)

    if suggestion:
        return {"success": True, "suggestion": suggestion}
    else:
        return {"success": False, "error": "Failed to generate suggestion. Please try again."}


@frappe.whitelist()
def get_ai_recommended_for(template_name, template_category, description=None):
    """Generate AI suggestion for recommended audience.

    Args:
        template_name: Name of the template
        template_category: Category of the template
        description: Optional description for context

    Returns:
        dict with success status and suggestion
    """
    if not template_name:
        return {"success": False, "error": "Template name is required"}

    context = f"Description: {description}" if description else ""

    prompt = f"""Suggest who this survey template is best suited for (target audience recommendation):

Template Name: {template_name}
Category: {template_category or 'General Survey'}
{context}

Provide a concise recommendation (2-3 sentences) describing:
1. Who should receive this survey
2. When is the best time to send it
Keep it under 250 characters."""

    suggestion = _call_openai(prompt, max_tokens=150)

    if suggestion:
        return {"success": True, "suggestion": suggestion}
    else:
        return {"success": False, "error": "Failed to generate suggestion. Please try again."}


@frappe.whitelist()
def get_ai_questions(template_name, template_category, description=None, num_questions=5):
    """Generate AI suggestions for survey questions.

    Args:
        template_name: Name of the template
        template_category: Category of the template
        description: Optional description for context
        num_questions: Number of questions to generate (default 5)

    Returns:
        dict with success status and list of question suggestions
    """
    if not template_name:
        return {"success": False, "error": "Template name is required"}

    try:
        num_questions = int(num_questions)
        num_questions = min(max(num_questions, 1), 10)  # Limit between 1-10
    except (ValueError, TypeError):
        num_questions = 5

    context = f"Description: {description}" if description else ""

    prompt = f"""Generate {num_questions} professional survey questions for:

Template Name: {template_name}
Category: {template_category or 'General Survey'}
{context}

Return a JSON array with exactly {num_questions} questions. Each question should have:
- "question_text": The question text
- "question_type": One of "Rating", "Multiple Choice", "Text", or "Yes/No"
- "options": For Multiple Choice only, provide newline-separated options (e.g., "Option 1\\nOption 2\\nOption 3"). Leave empty for other types.
- "is_required": 1 for required, 0 for optional

Example format:
[
  {{"question_text": "How satisfied are you?", "question_type": "Rating", "options": "", "is_required": 1}},
  {{"question_text": "Would you recommend us?", "question_type": "Yes/No", "options": "", "is_required": 1}}
]

Return ONLY the JSON array, no other text."""

    suggestion = _call_openai(prompt, max_tokens=800)

    if not suggestion:
        return {"success": False, "error": "Failed to generate questions. Please try again."}

    try:
        # Clean up the response - remove markdown code blocks if present
        cleaned = suggestion.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        questions = json.loads(cleaned)

        if not isinstance(questions, list):
            raise ValueError("Response is not a list")

        # Validate and normalize questions
        valid_types = ["Rating", "Multiple Choice", "Text", "Yes/No"]
        normalized = []
        for i, q in enumerate(questions):
            if not isinstance(q, dict) or "question_text" not in q:
                continue

            q_type = q.get("question_type", "Text")
            if q_type not in valid_types:
                q_type = "Text"

            normalized.append({
                "question_text": str(q.get("question_text", "")),
                "question_type": q_type,
                "options": str(q.get("options", "")) if q_type == "Multiple Choice" else "",
                "is_required": 1 if q.get("is_required", 1) else 0,
                "order": i + 1
            })

        if not normalized:
            return {"success": False, "error": "No valid questions generated. Please try again."}

        return {"success": True, "questions": normalized}

    except (json.JSONDecodeError, ValueError) as e:
        frappe.log_error(f"Failed to parse AI questions: {suggestion}\nError: {str(e)}", "AI Question Parse Error")
        return {"success": False, "error": "Failed to parse AI response. Please try again."}

