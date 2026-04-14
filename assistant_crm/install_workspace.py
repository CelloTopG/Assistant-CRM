# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import json
import os

import frappe

WORKSPACE_NAME = "CRM"

# Child tables that belong to a Workspace record.
# Listed exhaustively so the delete step is complete across all Frappe versions.
_CHILD_TABLES = [
    "tabWorkspace Link",
    "tabWorkspace Shortcut",
    "tabWorkspace Chart",
    "tabWorkspace Number Card",
]


def create_crm_workspace():
    """Create or override the 'CRM' workspace.

    If a workspace named 'CRM' already exists in the instance, its content is
    fully replaced with the app's built-in definition (workspace/crm/crm.json).
    The function is idempotent: running it multiple times always leaves the
    workspace in the canonical state shipped with the app.
    """
    try:
        print(f"Setting up '{WORKSPACE_NAME}' workspace...")

        definition = _load_workspace_definition()

        if frappe.db.exists("Workspace", WORKSPACE_NAME):
            print(f"  Existing '{WORKSPACE_NAME}' workspace found — overriding content...")
            _drop_workspace(WORKSPACE_NAME)
        else:
            print(f"  '{WORKSPACE_NAME}' workspace not found — creating fresh...")

        _insert_workspace(definition)

        frappe.db.commit()
        print(f"✅ '{WORKSPACE_NAME}' workspace ready.")
        print(f"🔗 Access via: Desk → {WORKSPACE_NAME}")

    except Exception as exc:
        frappe.log_error(
            f"Error setting up CRM workspace: {exc}", "CRM Workspace Setup"
        )
        print(f"❌ CRM workspace setup failed: {exc}")
        raise


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_workspace_definition() -> dict:
    """Return the workspace definition from the bundled JSON file."""
    json_path = os.path.join(
        os.path.dirname(__file__), "workspace", "crm", "crm.json"
    )
    with open(json_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _drop_workspace(name: str) -> None:
    """Delete a workspace record and all of its child-table rows."""
    for table in _CHILD_TABLES:
        try:
            frappe.db.sql(f"DELETE FROM `{table}` WHERE parent = %s", name)
        except Exception:
            # Table may not exist in every Frappe version — skip silently.
            pass
    frappe.db.sql("DELETE FROM `tabWorkspace` WHERE name = %s", name)


def _insert_workspace(definition: dict) -> None:
    """Insert the main workspace record followed by all child-table rows."""
    content_str = json.dumps(definition.get("content", []))

    frappe.db.sql(
        """
        INSERT INTO `tabWorkspace`
            (name, title, icon, indicator_color, is_hidden,
             module, public, content, sequence_id,
             creation, modified, modified_by, owner)
        VALUES
            (%(name)s, %(title)s, %(icon)s, %(indicator_color)s, %(is_hidden)s,
             %(module)s, %(public)s, %(content)s, %(sequence_id)s,
             NOW(), NOW(), 'Administrator', 'Administrator')
        """,
        {
            "name": definition["name"],
            "title": definition["title"],
            "icon": definition.get("icon", ""),
            "indicator_color": definition.get("indicator_color", "Blue"),
            "is_hidden": definition.get("is_hidden", 0),
            "module": definition.get("module", ""),
            "public": definition.get("public", 1),
            "content": content_str,
            "sequence_id": definition.get("sequence_id", 1.0),
        },
    )

    for idx, shortcut in enumerate(definition.get("shortcuts", []), start=1):
        _insert_shortcut(definition["name"], shortcut, idx)

    for idx, link in enumerate(definition.get("links", []), start=1):
        _insert_link(definition["name"], link, idx)


def _insert_shortcut(workspace_name: str, shortcut: dict, idx: int) -> None:
    """Insert one row into tabWorkspace Shortcut."""
    frappe.db.sql(
        """
        INSERT INTO `tabWorkspace Shortcut`
            (name, parent, parenttype, parentfield,
             label, link_to, type, color, icon, idx,
             creation, modified, modified_by, owner)
        VALUES
            (%(name)s, %(parent)s, 'Workspace', 'shortcuts',
             %(label)s, %(link_to)s, %(type)s, %(color)s, %(icon)s, %(idx)s,
             NOW(), NOW(), 'Administrator', 'Administrator')
        """,
        {
            "name": frappe.generate_hash(length=10),
            "parent": workspace_name,
            "label": shortcut.get("label", ""),
            "link_to": shortcut.get("link_to", ""),
            "type": shortcut.get("type", "DocType"),
            "color": shortcut.get("color", "#4BCB97"),
            "icon": shortcut.get("icon", ""),
            "idx": idx,
        },
    )


def _insert_link(workspace_name: str, link: dict, idx: int) -> None:
    """Insert one row into tabWorkspace Link (either a Card Break or a Link)."""
    frappe.db.sql(
        """
        INSERT INTO `tabWorkspace Link`
            (name, parent, parenttype, parentfield,
             label, link_to, link_type, type, icon, description,
             is_query_report, only_for, dependencies, idx,
             creation, modified, modified_by, owner)
        VALUES
            (%(name)s, %(parent)s, 'Workspace', 'links',
             %(label)s, %(link_to)s, %(link_type)s, %(type)s,
             %(icon)s, %(description)s,
             %(is_query_report)s, %(only_for)s, %(dependencies)s, %(idx)s,
             NOW(), NOW(), 'Administrator', 'Administrator')
        """,
        {
            "name": frappe.generate_hash(length=10),
            "parent": workspace_name,
            "label": link.get("label", ""),
            "link_to": link.get("link_to", ""),
            "link_type": link.get("link_type", ""),
            "type": link.get("type", "Link"),
            "icon": link.get("icon", ""),
            "description": link.get("description", ""),
            "is_query_report": link.get("is_query_report", 0),
            "only_for": link.get("only_for", ""),
            "dependencies": link.get("dependencies", ""),
            "idx": idx,
        },
    )


# ---------------------------------------------------------------------------
# Backwards-compatibility shim
# ---------------------------------------------------------------------------

def install_workspace():
    """Alias kept for backward compatibility — delegates to create_crm_workspace()."""
    create_crm_workspace()


if __name__ == "__main__":
    create_crm_workspace()
