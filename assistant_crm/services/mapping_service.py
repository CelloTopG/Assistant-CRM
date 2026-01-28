import frappe
import re
from typing import List, Dict, Optional


def _split_candidates(txt: Optional[str]) -> List[str]:
    if not txt:
        return []
    # One per line, trim, drop empties
    return [x.strip() for x in txt.split("\n") if x.strip()]


def doctype_exists(dt: str) -> bool:
    return bool(frappe.db.exists("DocType", dt))


def resolve_doctype(preferred: str, candidates_text: Optional[str]) -> str:
    """Return the DocType to use in this site: prefer existing preferred,
    else first existing from candidates, else return preferred (will be created by migrate if part of this app)."""
    if preferred and doctype_exists(preferred):
        return preferred
    for c in _split_candidates(candidates_text):
        if doctype_exists(c):
            return c
    return preferred


def _field_in_meta(meta, fieldname: str) -> bool:
    return bool(meta.get_field(fieldname))


def _custom_field_exists(dt: str, fieldname: str) -> bool:
    return bool(
        frappe.db.exists(
            "Custom Field", {"dt": dt, "fieldname": fieldname}
        )
    )


def ensure_custom_field(dt: str, mapping_row) -> bool:
    """Ensure a single custom field exists on dt according to mapping_row.
    Returns True if a field was created, False if it already existed.
    mapping_row must have: frappe_field (fieldname), field_type, is_required, transformation_rule (optional)
    """
    fieldname = mapping_row.frappe_field
    if not fieldname:
        return False
    meta = frappe.get_meta(dt)
    if _field_in_meta(meta, fieldname) or _custom_field_exists(dt, fieldname):
        return False

    # Build Custom Field doc
    cf = frappe.new_doc("Custom Field")
    cf.dt = dt
    cf.label = fieldname.replace("_", " ").title()
    cf.fieldname = fieldname
    cf.fieldtype = mapping_row.field_type or "Data"
    cf.reqd = 1 if (mapping_row.is_required or 0) else 0

    # For common link assumptions, allow simple transformation rule hint like: Link:Contact
    if cf.fieldtype == "Link":
        # Try to infer options from transformation_rule, e.g., "Link:Issue" or "Issue"
        rule = (mapping_row.transformation_rule or "").strip()
        if ":" in rule:
            cf.options = rule.split(":", 1)[1].strip()
        elif rule:
            cf.options = rule

    # Allow Select options via transformation_rule; formats supported:
    # "Options: A|B|C" or "A|B|C" or newline/comma separated
    if cf.fieldtype == "Select":
        rule = (mapping_row.transformation_rule or "").strip()
        if rule:
            lower = rule.lower()
            if lower.startswith("options:"):
                rule = rule.split(":", 1)[1].strip()
            parts = re.split(r"[|,\n]+", rule)
            options = [p.strip() for p in parts if p.strip()]
            if options:
                cf.options = "\n".join(options)

    cf.insert(ignore_permissions=True)
    frappe.clear_cache(doctype=dt)
    return True


def apply_profile(profile_doc) -> Dict[str, List[str]]:
    """Apply a Data Mapping Profile - deprecated.
    Returns empty summary dict.
    """
    # Data Mapping Profile functionality has been deprecated
    return {"created_fields": [], "skipped_fields": [], "resolved_doctype": ""}


def apply_all_enabled_profiles_safely() -> Dict[str, Dict[str, List[str]]]:
    """Run across all enabled Data Mapping Profiles - deprecated.
    Returns empty mapping.
    """
    # Data Mapping Profile functionality has been deprecated
    return {}

