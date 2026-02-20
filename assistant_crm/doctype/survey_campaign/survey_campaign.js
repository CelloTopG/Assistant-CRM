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

    // Close Survey button - show for submitted campaigns that are not already completed/cancelled
    if (frm.doc.docstatus === 1 && !['Completed', 'Cancelled'].includes(frm.doc.status)) {
      frm.add_custom_button(__('Close Survey'), () => {
        show_close_survey_dialog(frm);
      }, __('Actions'));
    }
  },

  onload(frm) {
    // Initialize when form loads
    if (frm.doc.docstatus === 0) {
      set_filter_type_options_for_grid(frm);
    }
  },

  // Handle template selection for auto-population
  campaign_template(frm) {
    if (!frm.doc.campaign_template) {
      return;
    }

    // Confirm if form has existing data
    const has_questions = frm.doc.survey_questions && frm.doc.survey_questions.length > 0;
    const has_audience = frm.doc.target_audience && frm.doc.target_audience.length > 0;
    const has_channels = frm.doc.distribution_channels && frm.doc.distribution_channels.length > 0;

    if (has_questions || has_audience || has_channels) {
      frappe.confirm(
        __('Applying this template will replace existing questions, target audience, and distribution channels. Continue?'),
        () => apply_template(frm),
        () => {
          // User cancelled - reset template field
          frm.set_value('campaign_template', '');
        }
      );
    } else {
      apply_template(frm);
    }
  }
});

// ===================================================================
// CLOSE SURVEY DIALOG
// ===================================================================

function show_close_survey_dialog(frm) {
  frappe.confirm(
    __('Are you sure you want to close this survey? This will invalidate all pending survey links and recipients will no longer be able to respond.'),
    () => {
      // On confirm
      frappe.call({
        method: 'assistant_crm.assistant_crm.doctype.survey_campaign.survey_campaign.close_survey',
        args: {
          campaign_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Closing survey...'),
        callback: (r) => {
          if (r.message && r.message.success) {
            frappe.show_alert({
              message: r.message.message,
              indicator: 'green'
            }, 5);
            frm.reload_doc();
          } else {
            frappe.show_alert({
              message: __('Failed to close survey: ') + (r.message?.error || 'Unknown error'),
              indicator: 'red'
            }, 5);
          }
        }
      });
    }
  );
}

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
        message: __('Beneficiary filter: Use Contact/Customer (Individual) fields like first_name, last_name, email, mobile, beneficiary_number, territory, customer_group'),
        indicator: 'blue'
      }, 5);
    } else if (filter_type === 'Employer') {
      frappe.show_alert({
        message: __('Employer filter: Use Customer (Company) fields like employer_name, email, mobile, territory, customer_group, industry'),
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
        description: __('Number of recipients to preview')
      },
      {
        fieldname: 'results_section',
        fieldtype: 'Section Break'
      },
      {
        fieldname: 'results_html',
        fieldtype: 'HTML'
      }
    ],
    primary_action_label: __('Run Preview'),
    primary_action: (values) => {
      d.fields_dict.results_html.$wrapper.html(`
        <div style="text-align: center; padding: 20px; color: #888;">
          <i class="fa fa-spinner fa-spin"></i> ${__('Loading...')}
        </div>
      `);

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
          d.fields_dict.results_html.$wrapper.html(`
            <div style="padding: 15px; color: #e74c3c;">
              <i class="fa fa-exclamation-circle"></i> ${__('Failed to run preview')}
            </div>
          `);
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
  const recs = res.recipients || [];

  let html = '';

  if (recs.length) {
    // Header with count
    html += `
      <div style="padding: 15px 0; border-bottom: 1px solid #eee; margin-bottom: 10px;">
        <span style="font-size: 24px; font-weight: 600; color: #333;">${count}</span>
        <span style="color: #666; margin-left: 8px;">${count === 1 ? __('recipient') : __('recipients')}</span>
      </div>
    `;

    // List of names
    html += `<div style="max-height: 300px; overflow-y: auto;">`;
    recs.forEach((r, idx) => {
      const name = [r.first_name, r.last_name].filter(Boolean).join(' ') || r.name || 'Unknown';
      html += `
        <div style="padding: 8px 0; border-bottom: 1px solid #f5f5f5; color: #333;">
          ${frappe.utils.escape_html(name)}
        </div>
      `;
    });
    html += `</div>`;

    // Show "and X more" if truncated
    if (count > recs.length) {
      html += `
        <div style="padding: 10px 0; color: #888; font-size: 13px; text-align: center;">
          ${__('and')} ${count - recs.length} ${__('more')}...
        </div>
      `;
    }
  } else {
    html = `
      <div style="padding: 30px; text-align: center; color: #888;">
        <i class="fa fa-users" style="font-size: 32px; margin-bottom: 10px; display: block;"></i>
        ${__('No recipients found')}
      </div>
    `;
  }

  dialog.fields_dict.results_html.$wrapper.html(html);
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
  // Beneficiary filters map to ERPNext Contact doctype and Customer (type Individual)
  if (ftype === 'Beneficiary') {
    const valid_fields = [
      // Contact fields
      'first_name', 'last_name', 'full_name', 'email', 'email_id', 'phone', 'mobile', 'mobile_no',
      // Customer (Individual) fields via Dynamic Link
      'beneficiary_number', 'customer_name', 'nrc_number', 'tax_id',
      'territory', 'customer_group', 'gender'
    ];
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

  // Employer filters map to ERPNext Customer doctype (type Company) via Dynamic Link
  if (ftype === 'Employer') {
    const valid_fields = [
      // Customer (Company) fields
      'employer_name', 'employer_code', 'customer_name', 'name',
      'email', 'email_id', 'phone', 'mobile', 'mobile_no',
      'territory', 'customer_group', 'industry', 'tax_id'
    ];
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

// ===================================================================
// TEMPLATE AUTO-POPULATION
// ===================================================================

function apply_template(frm) {
  frappe.call({
    method: 'assistant_crm.assistant_crm.doctype.survey_campaign_template.survey_campaign_template.get_template_data',
    args: {
      template_name: frm.doc.campaign_template
    },
    freeze: true,
    freeze_message: __('Applying template...'),
    callback: (r) => {
      if (!r.message || !r.message.success) {
        frappe.msgprint({
          title: __('Error'),
          message: r.message?.error || __('Failed to load template'),
          indicator: 'red'
        });
        frm.set_value('campaign_template', '');
        return;
      }

      const data = r.message;

      // Set suggested campaign name if not already set
      if (data.suggested_campaign_name && !frm.doc.campaign_name) {
        frm.set_value('campaign_name', data.suggested_campaign_name);
      }

      // Set survey type from template
      if (data.default_survey_type) {
        frm.set_value('survey_type', data.default_survey_type);
      }

      // Set invitation message from template
      if (data.invitation_message) {
        frm.set_value('invitation_message', data.invitation_message);
      }

      // Clear and populate survey questions
      frm.clear_table('survey_questions');
      (data.questions || []).forEach((q) => {
        const row = frm.add_child('survey_questions');
        row.question_text = q.question_text;
        row.question_type = q.question_type;
        row.options = q.options;
        row.is_required = q.is_required;
        row.order = q.order;
      });

      // Clear and populate target audience
      frm.clear_table('target_audience');
      (data.target_audience || []).forEach((a) => {
        const row = frm.add_child('target_audience');
        row.filter_type = a.filter_type;
        row.filter_field = a.filter_field;
        row.filter_operator = a.filter_operator;
        row.filter_value = a.filter_value;
      });

      // Clear and populate distribution channels
      frm.clear_table('distribution_channels');
      (data.distribution_channels || []).forEach((c) => {
        const row = frm.add_child('distribution_channels');
        row.channel = c.channel;
        row.is_active = c.is_active;
      });

      // Refresh all child tables
      frm.refresh_field('survey_questions');
      frm.refresh_field('target_audience');
      frm.refresh_field('distribution_channels');

      // Show success message with template info
      let msg = __('Template "{0}" applied successfully.', [data.template_name]);
      if (data.recommended_for) {
        msg += '<br><br><b>' + __('Recommended for:') + '</b> ' + data.recommended_for;
      }

      frappe.msgprint({
        title: __('Template Applied'),
        message: msg,
        indicator: 'green'
      });
    },
    error: (err) => {
      console.error('Template application error:', err);
      frappe.msgprint({
        title: __('Error'),
        message: __('Failed to apply template. Please try again.'),
        indicator: 'red'
      });
      frm.set_value('campaign_template', '');
    }
  });
}