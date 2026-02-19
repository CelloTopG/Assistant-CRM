import frappe
from frappe import _


def prevent_platform_source_edit(doc, method):
    """
    Prevent users from changing the platform source after an Issue (ticket) has been created.
    - Applies to Issue.custom_platform_source (system-managed by Unified Inbox/AI).
    - Allows initial insert to set the value; blocks any subsequent edits.
    - If field is absent on this site, noop.
    """
    try:
        # If the field doesn't exist on this site, do nothing
        if not hasattr(doc, "custom_platform_source"):
            return

        # Only enforce after the document already exists in the DB
        if not doc.name:
            return

        # Enforce ONLY for AI-created tickets (linked to Unified Inbox Conversation)
        # Detect via presence of custom_conversation_id
        try:
            conv_id = frappe.db.get_value("Issue", doc.name, "custom_conversation_id") or doc.get("custom_conversation_id")
        except Exception:
            conv_id = doc.get("custom_conversation_id")
        if not conv_id:
            # Manually created Issues are not affected
            return

        # Fetch previous value from DB
        old_value = None
        try:
            old_value = frappe.db.get_value("Issue", doc.name, "custom_platform_source")
        except Exception:
            # If table/field lookup fails for any reason, fail safe (don't block)
            return

        # If there was a previous value and user is trying to change it, block
        if old_value and doc.custom_platform_source != old_value:
            # Revert the change for safety and raise a clear validation error
            doc.custom_platform_source = old_value
            frappe.throw(_("Platform Source is system-managed for AI tickets and cannot be changed after creation."))

        # Also prevent clearing the value once set
        if old_value and not doc.custom_platform_source:
            doc.custom_platform_source = old_value
            frappe.throw(_("Platform Source cannot be cleared after ticket creation for AI tickets."))

    except Exception:
        # Fail safe: do not break Issue saving for unrelated reasons
        # Still log for diagnostics
        try:
            frappe.log_error(
                title="Issue Platform Source Guardrail Error",
                message=frappe.get_traceback(),
            )
        except Exception:
            pass


def enqueue_branch_assignment(doc, method):
    """
    Hook to enqueue branch assignment background job after Issue creation.
    Uses the branch_assignment_service to:
    1. Look up beneficiary from Issue data
    2. Parse address to find location
    3. Find closest branch based on distance data
    4. Update the Issue with the assigned branch
    """
    try:
        from assistant_crm.services.branch_assignment_service import enqueue_branch_assignment as _enqueue
        _enqueue(doc.name)
    except Exception:
        # Fail safe: don't break Issue creation if branch assignment fails
        try:
            frappe.log_error(
                title="Branch Assignment Enqueue Error",
                message=frappe.get_traceback(),
            )
        except Exception:
            pass

def sync_escalated_agent_name(doc, method):
    """
    Sync custom_escalated_agent_name with the escalated agent's full name.
    Format: Full Name (user_id)
    """
    try:
        if not hasattr(doc, "custom_escalated_agent") or not doc.custom_escalated_agent:
            if hasattr(doc, "custom_escalated_agent_name"):
                doc.custom_escalated_agent_name = None
            return

        user_name = frappe.db.get_value("User", doc.custom_escalated_agent, "full_name") or doc.custom_escalated_agent
        display_name = f"{user_name} ({doc.custom_escalated_agent})"
        
        if doc.custom_escalated_agent_name != display_name:
            doc.custom_escalated_agent_name = display_name
    except Exception:
        pass


def validate_issue_closure(doc, method):
    """
    Only allow users with Supervisor roles to close or resolve an Issue.
    Specifically restricts WCF Customer Service Assistant & Officer.
    """
    try:
        if doc.status not in ["Closed", "Resolved"]:
            return

        # Check if this is a transition to closed/resolved
        if not doc.name:
            pass
        else:
            old_status = frappe.db.get_value("Issue", doc.name, "status")
            if old_status in ["Closed", "Resolved"]:
                return

        # Define roles
        supervisor_roles = ["System Manager", "Assistant CRM Manager", "Customer Service Manager"]
        agent_roles = ["WCF Customer Service Assistant", "WCF Customer Service Officer"]
        user_roles = frappe.get_roles()

        is_supervisor = any(role in supervisor_roles for role in user_roles)
        is_agent = any(role in agent_roles for role in user_roles)

        if is_agent and not is_supervisor:
            frappe.throw(_("WCF Customer Service Assistants and Officers are not authorized to close or resolve tickets. Please refer this to a Supervisor."))
            
        if not is_supervisor:
            frappe.throw(_("Only Supervisors and Managers are authorized to close or resolve tickets."))
            
    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(f"Error in validate_issue_closure: {str(e)}", "Issue Closure Validation Error")
