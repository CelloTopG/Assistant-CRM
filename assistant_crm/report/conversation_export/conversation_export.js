
frappe.query_reports["Conversation Export"] = {
    "filters": [
        {
            "fieldname": "conversation_name",
            "label": __("Conversation"),
            "fieldtype": "Link",
            "options": "Unified Inbox Conversation",
            "reqd": 1,
            "default": frappe.route_options ? frappe.route_options.conversation_name : ""
        }
    ]
};
