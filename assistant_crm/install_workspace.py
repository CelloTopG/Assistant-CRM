# Copyright (c) 2025, ExN and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def install_workspace():
    """Install ExN Assistant integration link and setup"""
    try:
        # Add ExN Assistant to Integrations workspace
        print("Adding ExN Assistant to Integrations...")

        # Check if Integrations workspace exists
        if not frappe.db.exists("Workspace", "Integrations"):
            print("⚠️ Integrations workspace not found, creating ExN Assistant workspace...")

            # Create workspace using SQL to avoid validation issues
            frappe.db.sql("""
                INSERT INTO `tabWorkspace` (
                    name, title, icon, indicator_color, is_hidden,
                    module, public, content, creation, modified, modified_by, owner
                ) VALUES (
                    'ExN Assistant', 'ExN Assistant', '🤖', 'Blue', 0,
                    'Integrations', 1, '[]', NOW(), NOW(), 'Administrator', 'Administrator'
                )
            """)

        else:
            # Add ExN Assistant link to existing Integrations workspace
            print("Adding ExN Assistant link to Integrations workspace...")

            # Check if link already exists
            existing_link = frappe.db.sql("""
                SELECT name FROM `tabWorkspace Link`
                WHERE parent = 'Integrations' AND link_to = 'exn-assistant'
            """)

            if not existing_link:
                # Add the integration link
                frappe.get_doc({
                    "doctype": "Workspace Link",
                    "parent": "Integrations",
                    "parenttype": "Workspace",
                    "parentfield": "links",
                    "label": "ExN Assistant",
                    "link_to": "exn-assistant",
                    "link_type": "Page",
                    "icon": "🤖",
                    "description": "AI-powered assistant for intelligent business process guidance",
                    "idx": 25  # Place in Settings section (around idx 20-30)
                }).insert(ignore_permissions=True)

                print("✅ ExN Assistant link added to Integrations")
            else:
                print("✅ ExN Assistant link already exists in Integrations")

        print("✅ ExN Assistant integration setup completed")
        
        # Settings will be created automatically when user accesses the integration page
        print("📝 Settings will be created when you first access the integration page")
        
        # Create ExN Assistant Admin role if not exists
        if not frappe.db.exists("Role", "ExN Assistant Admin"):
            print("Creating ExN Assistant Admin role...")

            try:
                role = frappe.get_doc({
                    "doctype": "Role",
                    "name": "ExN Assistant Admin",
                    "role_name": "ExN Assistant Admin",
                    "desk_access": 1,
                    "is_custom": 1,
                    "disabled": 0
                })

                role.insert(ignore_permissions=True)
                print("✅ ExN Assistant Admin role created")
            except Exception as e:
                print(f"⚠️ Role creation failed: {str(e)}")
                print("   Role will be created automatically when needed")
        else:
            print("✅ ExN Assistant Admin role already exists")
        
        frappe.db.commit()
        print("\n🎉 ExN Assistant installation completed successfully!")
        print("📍 Access: Integrations → ExN Assistant")
        print("🔗 URL: /app/exn-assistant")
        
    except Exception as e:
        frappe.log_error(f"Error installing ExN Assistant workspace: {str(e)}", "ExN Assistant Installation")
        print(f"❌ Installation failed: {str(e)}")


if __name__ == "__main__":
    install_workspace()
