import frappe


@frappe.whitelist()
def get_post_install_checklist():
    """Return a concise post-install checklist (strings)."""
    return [
        "Open Assistant CRM Settings and confirm provider + API key",
        "Verify roles: WCFCB Agent and WCFCB Assistant Admin",
        "Confirm Contact has social ID fields (Telegram, Facebook, Instagram, LinkedIn)",
        "Run Smoke Test: bench --site <site> execute assistant_crm.smoke_test.run_smoke_test",
        "Test chat status: /api/method/assistant_crm.assistant_crm.api.simplified_chat.get_chat_status",
        "Optionally export settings: export_settings(include_secrets=1) and import on target"
    ]


@frappe.whitelist()
def run_post_install_checks():
    try:
        from assistant_crm.assistant_crm.smoke_test import run_smoke_test
        return run_smoke_test()
    except Exception as e:
        return {"ok": False, "error": str(e)}

