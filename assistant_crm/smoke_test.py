import frappe


def _cf_exists(dt: str, fieldname: str) -> bool:
    try:
        meta = frappe.get_meta(dt)
        if meta.get_field(fieldname):
            return True
    except Exception:
        pass
    try:
        return bool(frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname}))
    except Exception:
        return False


@frappe.whitelist()
def run_smoke_test():
    """Minimal smoke test for Assistant CRM install health."""
    results = {}
    try:
        results["settings_exists"] = bool(frappe.db.exists("Assistant CRM Settings", "Assistant CRM Settings"))
        results["role_wcfcb_agent"] = bool(frappe.db.exists("Role", "WCFCB Agent"))
        results["role_wcfcb_admin"] = bool(frappe.db.exists("Role", "WCFCB Assistant Admin"))

        # Contact channel fields
        channel_fields = [
            "telegram_chat_id",
            "facebook_psid",
            "instagram_user_id",
            "linkedin_chat_id",
        ]
        results["contact_fields"] = {f: _cf_exists("Contact", f) for f in channel_fields}

        # Chat status endpoint
        try:
            from assistant_crm.assistant_crm.api.simplified_chat import get_chat_status
            status = get_chat_status()
            results["chat_status_ok"] = bool(status and status.get("success"))
        except Exception:
            results["chat_status_ok"] = False

        # Overall
        results["ok"] = (
            results.get("settings_exists")
            and results.get("role_wcfcb_agent")
            and results.get("role_wcfcb_admin")
            and all(results.get("contact_fields", {}).values())
            and results.get("chat_status_ok")
        )
    except Exception as e:
        results["ok"] = False
        results["error"] = str(e)

    return results

