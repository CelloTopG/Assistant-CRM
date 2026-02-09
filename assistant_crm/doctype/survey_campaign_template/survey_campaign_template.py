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
def get_ai_description(template_name, template_category, preferences=None):
    """Generate AI suggestion for template description.

    Args:
        template_name: Name of the template
        template_category: Category of the template
        preferences: User preferences for the suggestion (tone, length, focus, etc.)

    Returns:
        dict with success status and suggestion
    """
    if not template_name:
        return {"success": False, "error": "Template name is required"}

    # Parse preferences if provided as string
    if preferences and isinstance(preferences, str):
        preferences = json.loads(preferences)

    # Build preference instructions
    pref_instructions = ""
    if preferences:
        tone = preferences.get('tone', 'Professional')
        length = preferences.get('length', 'Medium (2-3 sentences)')
        focus = preferences.get('focus', 'Purpose & Goals')
        additional = preferences.get('additional_instructions', '')

        # Map length to sentence count
        length_map = {
            'Short (1-2 sentences)': '1-2 sentences, under 100 characters',
            'Medium (2-3 sentences)': '2-3 sentences, under 200 characters',
            'Detailed (3-4 sentences)': '3-4 sentences, under 300 characters'
        }
        length_instruction = length_map.get(length, '2-3 sentences, under 200 characters')

        pref_instructions = f"""
Tone: {tone}
Length: {length_instruction}
Focus: {focus}"""

        if additional:
            pref_instructions += f"\nAdditional Requirements: {additional}"

    prompt = f"""Generate a description for a survey template with the following details:

Template Name: {template_name}
Category: {template_category or 'General Survey'}
{pref_instructions}

The description should explain what the survey measures and its purpose."""

    suggestion = _call_openai(prompt, max_tokens=200)

    if suggestion:
        return {"success": True, "suggestion": suggestion}
    else:
        return {"success": False, "error": "Failed to generate suggestion. Please try again."}


@frappe.whitelist()
def get_ai_recommended_for(template_name, template_category, description=None, preferences=None):
    """Generate AI suggestion for recommended audience.

    Args:
        template_name: Name of the template
        template_category: Category of the template
        description: Optional description for context
        preferences: User preferences for the suggestion

    Returns:
        dict with success status and suggestion
    """
    if not template_name:
        return {"success": False, "error": "Template name is required"}

    # Parse preferences if provided as string
    if preferences and isinstance(preferences, str):
        preferences = json.loads(preferences)

    context = f"Description: {description}" if description else ""

    # Build preference instructions
    pref_instructions = ""
    if preferences:
        audience_type = preferences.get('audience_type', 'Customers')
        detail_level = preferences.get('detail_level', 'Moderate Detail')
        include_timing = preferences.get('include_timing', True)
        include_criteria = preferences.get('include_criteria', True)
        additional = preferences.get('additional_instructions', '')

        # Map detail level
        detail_map = {
            'Brief Overview': '1-2 sentences',
            'Moderate Detail': '2-3 sentences',
            'Comprehensive': '3-4 sentences with specific criteria'
        }
        detail_instruction = detail_map.get(detail_level, '2-3 sentences')

        pref_instructions = f"""
Primary Audience Type: {audience_type}
Detail Level: {detail_instruction}"""

        if include_timing:
            pref_instructions += "\nInclude: Best timing/occasions to send this survey"
        if include_criteria:
            pref_instructions += "\nInclude: Selection criteria for recipients"
        if additional:
            pref_instructions += f"\nAdditional Requirements: {additional}"

    prompt = f"""Suggest who this survey template is best suited for (target audience recommendation):

Template Name: {template_name}
Category: {template_category or 'General Survey'}
{context}
{pref_instructions}

Provide a recommendation describing who should receive this survey."""

    suggestion = _call_openai(prompt, max_tokens=250)

    if suggestion:
        return {"success": True, "suggestion": suggestion}
    else:
        return {"success": False, "error": "Failed to generate suggestion. Please try again."}


@frappe.whitelist()
def get_ai_questions(template_name, template_category, description=None, num_questions=5, preferences=None):
    """Generate AI suggestions for survey questions.

    Args:
        template_name: Name of the template
        template_category: Category of the template
        description: Optional description for context
        num_questions: Number of questions to generate (default 5)
        preferences: User preferences for question style, complexity, focus area

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

    # Parse preferences if provided as string
    if preferences and isinstance(preferences, str):
        preferences = json.loads(preferences)

    context = f"Description: {description}" if description else ""

    # Build preference instructions
    pref_instructions = ""
    if preferences:
        question_style = preferences.get('question_style', 'Mixed (Variety of types)')
        complexity = preferences.get('complexity', 'Moderate')
        focus_area = preferences.get('focus_area', 'Overall Satisfaction')
        additional = preferences.get('additional_instructions', '')

        # Map question style to instructions
        style_map = {
            'Mixed (Variety of types)': 'Use a variety of question types (Rating, Multiple Choice, Text, Yes/No)',
            'Mostly Rating Questions': 'Primarily use Rating type questions (at least 70%)',
            'Mostly Multiple Choice': 'Primarily use Multiple Choice questions (at least 70%)',
            'Mostly Open-ended Text': 'Primarily use Text type questions (at least 70%)',
            'Mostly Yes/No': 'Primarily use Yes/No questions (at least 70%)'
        }
        style_instruction = style_map.get(question_style, 'Use a variety of question types')

        # Map complexity
        complexity_map = {
            'Simple & Direct': 'Keep questions simple, direct, and easy to understand',
            'Moderate': 'Use moderately detailed questions that are clear but comprehensive',
            'Detailed & Comprehensive': 'Create detailed, comprehensive questions that cover all aspects'
        }
        complexity_instruction = complexity_map.get(complexity, 'Use moderately detailed questions')

        pref_instructions = f"""
Question Style: {style_instruction}
Complexity: {complexity_instruction}
Focus Area: {focus_area}"""

        if additional:
            pref_instructions += f"\nAdditional Requirements: {additional}"

    prompt = f"""Generate {num_questions} professional survey questions for:

Template Name: {template_name}
Category: {template_category or 'General Survey'}
{context}
{pref_instructions}

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

