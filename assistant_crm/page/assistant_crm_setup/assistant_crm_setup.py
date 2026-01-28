import frappe


def _require_admin():
    roles = set(frappe.get_roles(frappe.session.user))
    if not ({"System Manager", "WCFCB Assistant Admin"} & roles):
        frappe.throw("Not permitted", frappe.PermissionError)


@frappe.whitelist()
def get_doctypes():
    """Return available DocTypes to help the admin pick targets"""
    _require_admin()
    names = frappe.get_all("DocType", pluck="name")
    return names


@frappe.whitelist()
def create_profile(title: str, target_doctype: str, candidate_doctypes: str = "", enabled: int = 1, rows: list | None = None):
    """Data Mapping Profile has been deprecated"""
    _require_admin()
    frappe.throw("Data Mapping Profile functionality has been deprecated")


@frappe.whitelist()
def apply_profile(name: str):
    """Data Mapping Profile has been deprecated"""
    _require_admin()
    frappe.throw("Data Mapping Profile functionality has been deprecated")


@frappe.whitelist()
def apply_all():
    """Data Mapping Profile has been deprecated"""
    _require_admin()
    frappe.throw("Data Mapping Profile functionality has been deprecated")

