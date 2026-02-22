
import frappe
from frappe import _

def create_conversation_print_format():
    if not frappe.db.exists("Print Format", "Conversation Export"):
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        .header { margin-bottom: 30px; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        .conversation-meta { margin-bottom: 20px; color: #555; }
        .message { margin-bottom: 15px; padding: 10px; border-radius: 5px; page-break-inside: avoid; }
        .inbound { background-color: #f1f1f1; border-left: 4px solid #007bff; margin-right: 40px; }
        .outbound { background-color: #e3f2fd; border-right: 4px solid #28a745; margin-left: 40px; text-align: right; }
        .sender { font-weight: bold; font-size: 0.9em; margin-bottom: 5px; }
        .timestamp { font-size: 0.8em; color: #888; }
        .content { margin-top: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ doc.customer_name or "Guest" }}</h1>
        <div class="conversation-meta">
            <p><strong>Platform:</strong> {{ doc.platform }}</p>
            <p><strong>Conversation ID:</strong> {{ doc.name }}</p>
            <p><strong>Status:</strong> {{ doc.status }}</p>
            <p><strong>Date:</strong> {{ doc.creation }}</p>
        </div>
    </div>

    <div class="messages">
        {% set messages = frappe.get_all("Unified Inbox Message", 
            filters={"conversation": doc.name},
            fields=["direction", "sender_name", "message_content", "timestamp"],
            order_by="timestamp asc") %}
        {% for m in messages %}
            <div class="message {{ 'inbound' if m.direction == 'Inbound' else 'outbound' }}">
                <div class="sender">{{ m.sender_name or ("Customer" if m.direction == "Inbound" else "Agent") }}</div>
                <div class="content">{{ m.message_content }}</div>
                <div class="timestamp">{{ m.timestamp }}</div>
            </div>
        {% endfor %}
    </div>
</body>
</html>
"""
        doc = frappe.get_doc({
            "doctype": "Print Format",
            "doc_type": "Unified Inbox Conversation",
            "name": "Conversation Export",
            "print_format_type": "Jinja",
            "html": html,
            "standard": "No",
            "custom_format": 1
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return "Created 'Conversation Export' Print Format"
    return "Print Format 'Conversation Export' already exists"

if __name__ == "__main__":
    print(create_conversation_print_format())
