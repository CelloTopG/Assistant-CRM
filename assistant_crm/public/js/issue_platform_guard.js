frappe.ui.form.on('Issue', {
  onload(frm) {
    enforce_platform_source_read_only(frm);
    update_agent_display_names(frm);
  },
  refresh(frm) {
    enforce_platform_source_read_only(frm);
    update_agent_display_names(frm);
    show_escalation_indicator(frm);
    validate_status_change(frm);
  },
  validate(frm) {
    if (frm.doc.status === 'Closed' || frm.doc.status === 'Resolved') {
      const supervisorRoles = ["System Manager", "Assistant CRM Manager"];
      const isSupervisor = frappe.user_roles.some(role => supervisorRoles.includes(role));

      if (!isSupervisor) {
        // Double check if it was already closed (allow saving other fields)
        if (frm.doc.__onsave && frm.doc.__onsave.status !== 'Closed' && frm.doc.__onsave.status !== 'Resolved') {
          // This is slightly tricky in client script; we rely on the server side mostly
          // but we can warn the user.
        }
      }
    }
  },
  status: function (frm) {
    validate_status_change(frm);
  },
  custom_assigned_agent: function (frm) {
    update_agent_display_names(frm);
  },
  custom_escalated_agent: function (frm) {
    update_agent_display_names(frm);
  }
});

function enforce_platform_source_read_only(frm) {
  try {
    if (!frm || !frm.doc) return;

    // Only lock when AI generated (linked to unified inbox conversation)
    const is_ai_ticket = !!frm.doc.custom_conversation_id;

    // Field API name used by our integration
    const fieldname = 'custom_platform_source';

    // If field doesn't exist on this site, noop
    const field = frm.get_field(fieldname);
    if (!field) return;

    const should_lock = is_ai_ticket && !!frm.doc[fieldname] && !frm.is_new();

    // Toggle read-only state
    frm.set_df_property(fieldname, 'read_only', should_lock ? 1 : 0);

    // Optional: visually indicate lock state
    if (should_lock) {
      field.$wrapper && field.$wrapper.addClass('control-value-like');
    } else {
      field.$wrapper && field.$wrapper.removeClass('control-value-like');
    }

    frm.refresh_field(fieldname);
  } catch (e) {
    if (window && window.console) {
      console.warn('[Issue] platform source guard error:', e);
    }
  }
}

function update_agent_display_names(frm) {
  // Logic to update display name for assigned and escalated agents in Format: Full Name (user_id)
  ['custom_assigned_agent', 'custom_escalated_agent'].forEach(fieldname => {
    let user_id = frm.doc[fieldname];
    if (user_id) {
      frappe.db.get_value('User', user_id, 'full_name', (r) => {
        if (r && r.full_name) {
          let display = `${r.full_name} (${user_id})`;
          if (fieldname === 'custom_escalated_agent') {
            frm.set_value('custom_escalated_agent_name', display);
          }
          // We can't easily change the link field text display without affecting the link itself,
          // but we can set a descriptive label or use a secondary field.
          // For Escalation, we have custom_escalated_agent_name.
        }
      });
    }
  });
}

function show_escalation_indicator(frm) {
  if (frm.doc.custom_escalated_agent) {
    // Add a sidebar indicator using native ERPNext styling
    const user_id = frm.doc.custom_escalated_agent;
    const display = frm.doc.custom_escalated_agent_name || user_id;

    // Use native fonts and colors by avoiding color-specific classes
    // and using a standard agent icon
    frm.sidebar.add_user_action(__('Escalated to: {0}', [display]), () => {
      frappe.set_route('Form', 'User', user_id);
    }, 'fa fa-user');
  }
}

function validate_status_change(frm) {
  if (frm.doc.status === 'Closed' || frm.doc.status === 'Resolved') {
    const supervisorRoles = ["System Manager", "Assistant CRM Manager", "Customer Service Manager"];
    const agentRoles = ["WCF Customer Service Assistant", "WCF Customer Service Officer"];

    // Use frappe.boot.user_roles as the reliable source
    const userRoles = (frappe.boot && frappe.boot.user_roles) ? frappe.boot.user_roles : (frappe.user_roles || []);

    const isSupervisor = userRoles.some(role => supervisorRoles.includes(role));
    const isAgent = userRoles.some(role => agentRoles.includes(role));

    if (isAgent && !isSupervisor) {
      frappe.db.get_value('Issue', frm.doc.name, 'status', (r) => {
        if (r && r.status !== 'Closed' && r.status !== 'Resolved') {
          frappe.msgprint(__('Customer Service Assistants and Officers are not authorized to close or resolve tickets. Please refer this to a Supervisor.'));
          // Only the server-side will truly block it, but we warn here.
        }
      });
    } else if (!isSupervisor) {
      frappe.db.get_value('Issue', frm.doc.name, 'status', (r) => {
        if (r && r.status !== 'Closed' && r.status !== 'Resolved') {
          frappe.msgprint(__('Only Supervisors and Managers are authorized to close or resolve tickets.'));
        }
      });
    }
  }
}
