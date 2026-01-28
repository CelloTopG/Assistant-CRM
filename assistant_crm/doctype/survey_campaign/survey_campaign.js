// ===================================================================
// SURVEY CAMPAIGN CLIENT SCRIPT - SIMPLIFIED VERSION
// ===================================================================

// Configuration constants
const CHANNELS = ['Email', 'WhatsApp', 'SMS', 'Facebook', 'Instagram', 'Telegram'];

let SHOW_ALERTS = false;

// ===================================================================
// MAIN FORM EVENTS
// ===================================================================

frappe.ui.form.on('Survey Campaign', {
  refresh(frm) {
    if (frm.doc.docstatus === 0) {
      // Preview Recipients Button
      frm.add_custom_button(__('Preview Recipients'), () => {
        show_preview_dialog(frm);
      });
      
      // Validate Filters Button
      frm.add_custom_button(__('Validate Filters'), async () => {
        await validate_all_filters(frm);
      }, __('Actions'));
      
      // Set filter type options for the grid
      set_filter_type_options_for_grid(frm);
    }
  },
  
  onload(frm) {
    // Initialize when form loads
    if (frm.doc.docstatus === 0) {
      set_filter_type_options_for_grid(frm);
    }
  }
});

// ===================================================================
// CHILD TABLE EVENTS
// ===================================================================

frappe.ui.form.on('Survey Target Audience', {
  target_audience_add(frm, cdt, cdn) {
    set_filter_type_options_for_grid(frm);
  },
  
  filter_type(frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    const filter_type = (row.filter_type || '').trim();
    
    // Clear field/operator/value when type changes
    frappe.model.set_value(cdt, cdn, 'filter_field', '');
    frappe.model.set_value(cdt, cdn, 'filter_operator', '');
    frappe.model.set_value(cdt, cdn, 'filter_value', '');
    
    // Show helpful alerts
    if (filter_type === 'Channel') {
      frappe.show_alert({
        message: __('Channel filter: Set Filter Value to one of: {0}', [CHANNELS.join(', ')]),
        indicator: 'blue'
      }, 5);
    } else if (filter_type === 'Beneficiary') {
      frappe.show_alert({
        message: __('Beneficiary filter: Use field names like full_name, first_name, last_name, email, mobile, beneficiary_number, nrc_number, benefit_type, benefit_status'),
        indicator: 'blue'
      }, 5);
    } else if (filter_type === 'Employer') {
      frappe.show_alert({
        message: __('Employer filter: Use field names like employer_name, employer_code, email, mobile, phone'),
        indicator: 'blue'
      }, 5);
    } else if (filter_type === 'Date Range') {
      frappe.model.set_value(cdt, cdn, 'filter_field', 'creation');
      frappe.show_alert({
        message: __('Date Range: Use creation, modified, or any date field from Contact'),
        indicator: 'blue'
      }, 5);
    }
  },
  
  filter_value(frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    
    // Validate Channel value in real-time
    if (row.filter_type === 'Channel') {
      const value = (row.filter_value || '').trim();
      if (value && !CHANNELS.includes(value)) {
        frappe.show_alert({
          message: __('Invalid channel. Must be one of: {0}', [CHANNELS.join(', ')]),
          indicator: 'orange'
        }, 5);
      }
    }
  }
});

// ===================================================================
// PREVIEW RECIPIENTS DIALOG
// ===================================================================

function show_preview_dialog(frm) {
  const d = new frappe.ui.Dialog({
    title: __('Preview Recipients'),
    fields: [
      { 
        label: __('Sample Size'), 
        fieldname: 'limit', 
        fieldtype: 'Int', 
        default: 20, 
        reqd: 1, 
        description: __('Number of recipients to list (preview only)') 
      }
    ],
    primary_action_label: __('Run Preview'),
    primary_action: (values) => {
      d.set_message(__('Running preview...'));
      
      frappe.call({
        method: 'assistant_crm.assistant_crm.doctype.survey_campaign.survey_campaign.preview_recipients_from_doc',
        args: { 
          doc: frm.doc, 
          limit: values.limit || 20 
        },
        callback: (r) => {
          display_preview_results(d, r);
        },
        error: (err) => {
          d.set_message(`<span class="text-danger">${__('Failed to run preview')}</span>`);
          console.error('Preview error:', err);
        }
      });
    }
  });
  
  d.show();
}

function display_preview_results(dialog, response) {
  const res = (response && response.message) || {};
  const count = res.count || 0;
  const safe_max = res.safe_max_target || 100;
  const channels = res.active_channels || [];
  const lines = [];
  
  lines.push(`<b>${__('Targeted')}:</b> ${count}`);
  lines.push(`<b>${__('Active Channels')}:</b> ${channels.join(', ') || __('None')}`);
  
  // Display warnings
  if (Array.isArray(res.warnings) && res.warnings.length) {
    lines.push(`<br/><span class="text-warning"><b>${__('Warnings')}:</b></span>`);
    res.warnings.forEach(w => {
      lines.push(`<span class="text-warning">⚠ ${frappe.utils.escape_html(w)}</span>`);
    });
  }
  
  // Safety threshold warning
  if (count > safe_max) {
    lines.push(`<br/><span class="text-danger"><b>${__('Warning')}:</b> Count exceeds safety threshold of ${safe_max}. Submission will be blocked.</span>`);
  }
  
  // Display sample recipients
  const recs = res.recipients || [];
  if (recs.length) {
    lines.push('<hr/>');
    lines.push(`<b>${__('Sample Recipients')}:</b>`);
    lines.push('<table class="table table-bordered table-sm" style="margin-top: 10px;">');
    lines.push(`<thead><tr><th>${__('Name')}</th><th>${__('Contact Info')}</th><th>${__('Ready Status')}</th></tr></thead><tbody>`);
    
    recs.forEach(r => {
      const name_display = frappe.utils.escape_html([r.first_name, r.last_name].filter(Boolean).join(' ') || r.name);
      
      // Build contact info
      const contact_bits = [];
      if (r.email_id) contact_bits.push(`📧 ${frappe.utils.escape_html(r.email_id)}`);
      if (r.mobile_no) contact_bits.push(`📱 ${frappe.utils.escape_html(r.mobile_no)}`);
      if (r.telegram_chat_id) contact_bits.push(`✈️ ${frappe.utils.escape_html(r.telegram_chat_id)}`);
      if (r.facebook_psid) contact_bits.push(`📘 ${frappe.utils.escape_html(r.facebook_psid)}`);
      if (r.instagram_user_id) contact_bits.push(`📷 ${frappe.utils.escape_html(r.instagram_user_id)}`);
      
      // Build ready status
      const ready = r.ready || {};
      const ready_badges = channels.map(ch => {
        const is_ready = ready[ch];
        const color = is_ready ? 'green' : 'red';
        return `<span class="badge" style="background-color: ${color}; color: white; margin-right: 3px;">${ch}: ${is_ready ? '✓' : '✗'}</span>`;
      }).join('');
      
      lines.push(`<tr><td>${name_display}</td><td>${contact_bits.join('<br/>') || '-'}</td><td>${ready_badges || '-'}</td></tr>`);
    });
    
    lines.push('</tbody></table>');
  } else {
    lines.push(`<br/><span class="text-muted">${__('No recipients found')}</span>`);
  }
  
  dialog.set_message(lines.join(''));
}

// ===================================================================
// VALIDATION FUNCTIONS
// ===================================================================

async function validate_all_filters(frm) {
  SHOW_ALERTS = true;
  
  try {
    const rows = frm.doc.target_audience || [];
    
    if (!rows.length) {
      frappe.msgprint({
        title: __('No Filters'),
        message: __('Please add at least one filter to the Target Audience table.'),
        indicator: 'orange'
      });
      return;
    }
    
    let error_count = 0;
    
    for (const row of rows) {
      const has_error = await validate_row(frm, row);
      if (has_error) error_count++;
    }
    
    if (error_count === 0) {
      frappe.show_alert({ 
        message: __('All filters validated successfully'), 
        indicator: 'green' 
      }, 5);
    } else {
      frappe.msgprint({
        title: __('Validation Complete'),
        message: __('Found {0} filter(s) with potential issues. Please review.', [error_count]),
        indicator: 'orange'
      });
    }
    
  } finally {
    SHOW_ALERTS = false;
  }
}

async function validate_row(frm, row) {
  const ftype = (row.filter_type || '').trim();
  const ffield = (row.filter_field || '').trim();
  const fvalue = (row.filter_value || '').trim();
  const foperator = (row.filter_operator || '').trim();
  let has_error = false;

  // Validate filter type is set
  if (!ftype) {
    if (SHOW_ALERTS) {
      frappe.show_alert({
        message: __('Row {0}: Filter Type is required', [row.idx]),
        indicator: 'orange'
      }, 5);
    }
    return true;
  }

  // Channel validation
  if (ftype === 'Channel') {
    if (!fvalue) {
      if (SHOW_ALERTS) {
        frappe.show_alert({
          message: __('Row {0}: Channel Filter Value is required', [row.idx]),
          indicator: 'orange'
        }, 5);
      }
      return true;
    }

    if (!CHANNELS.includes(fvalue)) {
      if (SHOW_ALERTS) {
        frappe.msgprint({
          title: __('Invalid Channel'),
          message: __('Row {0}: Filter Value must be one of: {1}', [row.idx, CHANNELS.join(', ')]),
          indicator: 'orange'
        });
      }
      return true;
    }

    return false;
  }

  // Validate required fields
  if (!ffield) {
    if (SHOW_ALERTS) {
      frappe.show_alert({
        message: __('Row {0}: Filter Field is required', [row.idx]),
        indicator: 'orange'
      }, 5);
    }
    return true;
  }

  if (!foperator) {
    if (SHOW_ALERTS) {
      frappe.show_alert({
        message: __('Row {0}: Filter Operator is required', [row.idx]),
        indicator: 'orange'
      }, 5);
    }
    return true;
  }

  if (!fvalue && foperator !== 'is_set' && foperator !== 'is_not_set') {
    if (SHOW_ALERTS) {
      frappe.show_alert({
        message: __('Row {0}: Filter Value is required', [row.idx]),
        indicator: 'orange'
      }, 5);
    }
    return true;
  }

  // Validate Beneficiary/Employer field names
  if (ftype === 'Beneficiary') {
    const valid_fields = ['beneficiary_number', 'nrc_number', 'first_name', 'last_name', 'full_name',
                         'email', 'phone', 'mobile', 'benefit_type', 'benefit_status', 'employee_number',
                         'date_of_birth', 'gender', 'marital_status', 'nationality', 'physical_address',
                         'postal_address', 'city', 'province', 'bank_name', 'bank_account_number', 'bank_branch'];
    const normalized_field = ffield.toLowerCase().replace(/\s+/g, '_').replace(/-/g, '_');

    if (!valid_fields.includes(normalized_field)) {
      if (SHOW_ALERTS) {
        frappe.msgprint({
          title: __('Invalid Beneficiary Field'),
          message: __('Row {0}: Field "{1}" is not valid. Use one of: {2}',
                     [row.idx, ffield, valid_fields.join(', ')]),
          indicator: 'orange'
        });
      }
      return true;
    }
  }

  if (ftype === 'Employer') {
    const valid_fields = ['employer_code', 'employer_name', 'email', 'phone', 'mobile',
                         'physical_address', 'postal_address', 'city', 'province'];
    const normalized_field = ffield.toLowerCase().replace(/\s+/g, '_').replace(/-/g, '_');

    if (!valid_fields.includes(normalized_field)) {
      if (SHOW_ALERTS) {
        frappe.msgprint({
          title: __('Invalid Employer Field'),
          message: __('Row {0}: Field "{1}" is not valid. Use one of: {2}',
                     [row.idx, ffield, valid_fields.join(', ')]),
          indicator: 'orange'
        });
      }
      return true;
    }
  }

  return false;
}

// ===================================================================
// HELPER FUNCTIONS
// ===================================================================

function set_filter_type_options_for_grid(frm) {
  try {
    const grid = frm.fields_dict['target_audience'];
    if (!grid || !grid.grid) return;
    
    const options = ['Beneficiary', 'Employer', 'Channel', 'Date Range', 'Custom Field'].join('\n');
    grid.grid.update_docfield_property('filter_type', 'options', options);
  } catch (e) {
    console.warn('set_filter_type_options_for_grid failed', e);
  }
}