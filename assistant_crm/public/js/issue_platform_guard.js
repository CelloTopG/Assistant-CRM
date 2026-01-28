frappe.ui.form.on('Issue', {
  onload(frm) {
    enforce_platform_source_read_only(frm);
  },
  refresh(frm) {
    enforce_platform_source_read_only(frm);
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
    // Do not break the form; log to console for debugging
    if (window && window.console) {
      console.warn('[Issue] platform source guard error:', e);
    }
  }
}

