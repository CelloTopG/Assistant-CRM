# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now

class ChatHistory(Document):
    """Chat History DocType for storing conversation data"""

    def update_response(self, response=None, status=None, context_data=None, error_message=None):
        """Update chat history with AI response and status"""
        try:
            # Reload to get latest version and avoid timestamp conflicts
            self.reload()

            if response is not None:
                self.response = response

            if status is not None:
                self.status = status

            if context_data is not None:
                # Store context data as JSON string if it's a dict
                if isinstance(context_data, dict):
                    import json
                    self.context_data = json.dumps(context_data)
                else:
                    self.context_data = context_data

            if error_message is not None:
                self.error_message = error_message

            # Save the document with ignore_version to avoid timestamp conflicts
            self.save(ignore_version=True)
            frappe.db.commit()

        except Exception as e:
            frappe.log_error(f"Error updating chat response: {str(e)}", "Chat History Update")
            raise

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
            "status": "Received"  # Now valid since we added it to the options
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
