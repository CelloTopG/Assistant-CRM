
import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    return [
        {"fieldname": "direction", "label": _("Direction"), "fieldtype": "Data", "width": 100},
        {"fieldname": "sender_name", "label": _("Sender"), "fieldtype": "Data", "width": 150},
        {"fieldname": "message_content", "label": _("Message"), "fieldtype": "Data", "width": 400},
        {"fieldname": "timestamp", "label": _("Timestamp"), "fieldtype": "Datetime", "width": 160}
    ]

def get_data(filters):
    conversation_name = filters.get("conversation_name")
    if not conversation_name:
        return []
        
    messages = frappe.get_all(
        "Unified Inbox Message",
        filters={"conversation": conversation_name},
        fields=["direction", "sender_name", "message_content", "timestamp"],
        order_by="timestamp asc"
    )
    
    return messages
