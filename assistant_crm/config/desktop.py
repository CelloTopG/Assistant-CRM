from frappe import _

def get_data():
    return [
        {
            "module_name": "Assistant CRM",
            "color": "blue",
            "icon": "octicon octicon-comment-discussion",
            "type": "module",
            "label": _("Assistant CRM")
        },
        {
            "module_name": "Inbox",
            "color": "green",
            "icon": "octicon octicon-inbox",
            "type": "page",
            "link": "inbox",
            "label": _("Inbox"),
            "description": _("Manage customer conversations across all platforms")
        }
    ]
