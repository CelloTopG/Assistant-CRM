import json
import os

filepath = r"C:\Users\march\.gemini\antigravity\scratch\assistant-crm\assistant_crm\doctype\enhanced_ai_settings\enhanced_ai_settings.json"

with open(filepath, 'r', encoding='utf-8') as f:
    doctype = json.load(f)

# The new fields to insert
new_fields = [
    {
        "fieldname": "anna_agent_section",
        "fieldtype": "Section Break",
        "label": "Anna (Unified Inbox Chat Agent)"
    },
    {
        "fieldname": "anna_api_key",
        "fieldtype": "Password",
        "label": "Anna API Key / Bearer Token"
    },
    {
        "fieldname": "anna_endpoint_url",
        "fieldtype": "Data",
        "label": "Anna Endpoint URL",
        "description": "Full URL to Anna's specific API endpoint (e.g., https://api.openai.com/v1/chat/completions or your custom webhook)"
    },
    {
        "fieldname": "anna_model_id",
        "fieldtype": "Data",
        "label": "Anna Model ID / Assistant ID",
        "description": "The specific Assistant ID (asst_xyz) or Model ID"
    },
    {
        "fieldname": "antoine_agent_section",
        "fieldtype": "Section Break",
        "label": "Antoine (Reporting & Analytics Agent)"
    },
    {
        "fieldname": "antoine_api_key",
        "fieldtype": "Password",
        "label": "Antoine API Key / Bearer Token"
    },
    {
        "fieldname": "antoine_endpoint_url",
        "fieldtype": "Data",
        "label": "Antoine Endpoint URL"
    },
    {
        "fieldname": "antoine_model_id",
        "fieldtype": "Data",
        "label": "Antoine Model ID / Assistant ID"
    },
    {
        "fieldname": "enhancement_agent_section",
        "fieldtype": "Section Break",
        "label": "Enhancement Agent (Tone & Grammar)"
    },
    {
        "fieldname": "enhancement_api_key",
        "fieldtype": "Password",
        "label": "Enhancement Agent API Key"
    },
    {
        "fieldname": "enhancement_endpoint_url",
        "fieldtype": "Data",
        "label": "Enhancement Agent Endpoint URL"
    },
    {
        "fieldname": "enhancement_model_id",
        "fieldtype": "Data",
        "label": "Enhancement Agent Model ID"
    }
]

# We want to replace the old AI configuration fields but keep max_tokens etc.
# Old fields to remove from field_order and fields:
fields_to_remove = ["ai_configuration_section", "openai_api_key", "openai_model", "chat_model"]

new_field_list = []
new_field_order = []

# Filter out old fields
for f in doctype.get('fields', []):
    if f.get('fieldname') not in fields_to_remove:
        new_field_list.append(f)

for fn in doctype.get('field_order', []):
    if fn not in fields_to_remove:
        new_field_order.append(fn)

# Prepend new fields
doctype['fields'] = new_fields + new_field_list
doctype['field_order'] = [f['fieldname'] for f in new_fields] + new_field_order

with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(doctype, f, indent=1)

print("DocType JSON updated successfully!")
