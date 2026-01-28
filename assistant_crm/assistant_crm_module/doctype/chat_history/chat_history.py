# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now

class ChatHistory(Document):
    """Chat History DocType for storing conversation data"""

    @staticmethod
    def create_chat_entry(message, session_id=None, user=None):
        """Create a new chat history entry"""
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())

        if not user:
            user = frappe.session.user

        doc = frappe.get_doc({
            "doctype": "Chat History",
            "user": user,
            "session_id": session_id,
            "message": message,
            "timestamp": now(),
            "status": "Received"
        })
        doc.insert()
        return doc

    @staticmethod
    def get_user_chat_history(session_id, limit=10, user=None):
        """Get chat history for a session"""
        if not user:
            user = frappe.session.user

        return frappe.get_all(
            "Chat History",
            filters={
                "session_id": session_id,
                "user": user
            },
            fields=["name", "message", "response", "timestamp", "status"],
            order_by="timestamp desc",
            limit=limit
        )
