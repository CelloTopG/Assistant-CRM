frappe.ui.form.on('Issue', {
  onload(frm) {
    enforce_platform_source_read_only(frm);
    update_agent_display_names(frm);
  },
  refresh(frm) {
    enforce_platform_source_read_only(frm);
    update_agent_display_names(frm);
    show_escalation_indicator(frm);
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
    // Add a prominent sidebar indicator
    let user_id = frm.doc.custom_escalated_agent;
    frappe.db.get_value('User', user_id, 'full_name', (r) => {
      let name = r ? r.full_name : user_id;
      let display = `${name} (${user_id})`;

      frm.sidebar.add_user_action(__('Escalated to: {0}', [display]), () => {
        frappe.set_route('Form', 'User', user_id);
      }, 'fa fa-arrow-circle-up text-danger');

      // Also show a dashboard alert if escalated
      frm.dashboard.add_comment(__('This issue has been escalated to {0}.', [`<b>${display}</b>`]), 'red', true);
    });
  }
}

