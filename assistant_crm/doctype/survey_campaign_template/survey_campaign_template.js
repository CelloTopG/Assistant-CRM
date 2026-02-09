// Copyright (c) 2026, WCFCB and contributors
// For license information, please see license.txt

frappe.ui.form.on('Survey Campaign Template', {
  refresh(frm) {
    // Add AI suggestion buttons
    add_ai_buttons(frm);
  },

  template_name(frm) {
    // Clear AI buttons when template name changes
    if (frm.ai_buttons_added) {
      add_ai_buttons(frm);
    }
  }
});

function add_ai_buttons(frm) {
  // Remove existing AI buttons first
  frm.fields_dict.description.$wrapper.find('.ai-suggest-btn').remove();
  frm.fields_dict.recommended_for.$wrapper.find('.ai-suggest-btn').remove();
  frm.fields_dict.template_questions.$wrapper.find('.ai-suggest-btn').remove();

  // Add AI button for Description field
  const desc_btn = $(`
    <button class="btn btn-xs btn-default ai-suggest-btn" style="margin-left: 10px;">
      <i class="fa fa-magic"></i> AI Suggest
    </button>
  `);
  frm.fields_dict.description.$wrapper.find('.clearfix').append(desc_btn);
  desc_btn.on('click', () => suggest_description(frm));

  // Add AI button for Recommended For field
  const rec_btn = $(`
    <button class="btn btn-xs btn-default ai-suggest-btn" style="margin-left: 10px;">
      <i class="fa fa-magic"></i> AI Suggest
    </button>
  `);
  frm.fields_dict.recommended_for.$wrapper.find('.clearfix').append(rec_btn);
  rec_btn.on('click', () => suggest_recommended_for(frm));

  // Add AI button for Questions section
  const questions_section = frm.fields_dict.template_questions.$wrapper;
  const existing_q_btn = questions_section.find('.ai-suggest-btn');
  if (existing_q_btn.length === 0) {
    const q_btn = $(`
      <button class="btn btn-xs btn-primary ai-suggest-btn" style="margin-bottom: 10px;">
        <i class="fa fa-magic"></i> Generate AI Questions
      </button>
    `);
    questions_section.prepend(q_btn);
    q_btn.on('click', () => suggest_questions(frm));
  }

  frm.ai_buttons_added = true;
}

function suggest_description(frm) {
  if (!frm.doc.template_name) {
    frappe.msgprint(__('Please enter a Template Name first.'));
    return;
  }

  // Ask user for preferences before generating
  frappe.prompt([
    {
      fieldname: 'tone',
      label: __('Tone'),
      fieldtype: 'Select',
      options: 'Professional\nFriendly\nFormal\nCasual\nTechnical',
      default: 'Professional',
      reqd: 1
    },
    {
      fieldname: 'length',
      label: __('Length'),
      fieldtype: 'Select',
      options: 'Short (1-2 sentences)\nMedium (2-3 sentences)\nDetailed (3-4 sentences)',
      default: 'Medium (2-3 sentences)',
      reqd: 1
    },
    {
      fieldname: 'focus',
      label: __('Focus Area'),
      fieldtype: 'Select',
      options: 'Purpose & Goals\nBenefits & Value\nProcess & Methodology\nTarget Outcomes',
      default: 'Purpose & Goals',
      reqd: 1
    },
    {
      fieldname: 'additional_instructions',
      label: __('Additional Instructions (Optional)'),
      fieldtype: 'Small Text',
      description: __('Any specific requirements or keywords to include')
    }
  ],
  (values) => {
    generate_description(frm, values);
  },
  __('Customize AI Description'),
  __('Generate')
  );
}

function generate_description(frm, preferences) {
  frappe.call({
    method: 'assistant_crm.assistant_crm.doctype.survey_campaign_template.survey_campaign_template.get_ai_description',
    args: {
      template_name: frm.doc.template_name,
      template_category: frm.doc.template_category || '',
      preferences: preferences
    },
    freeze: true,
    freeze_message: __('Generating AI suggestion...'),
    callback: (r) => {
      if (r.message && r.message.success) {
        // Show preview dialog before applying
        show_suggestion_preview(frm, 'description', 'Description', r.message.suggestion);
      } else {
        frappe.msgprint({
          title: __('AI Suggestion Failed'),
          message: r.message?.error || __('Failed to generate suggestion.'),
          indicator: 'red'
        });
      }
    }
  });
}

function suggest_recommended_for(frm) {
  if (!frm.doc.template_name) {
    frappe.msgprint(__('Please enter a Template Name first.'));
    return;
  }

  // Ask user for preferences before generating
  frappe.prompt([
    {
      fieldname: 'audience_type',
      label: __('Primary Audience Type'),
      fieldtype: 'Select',
      options: 'Customers\nEmployees\nBeneficiaries\nStakeholders\nGeneral Public\nAll',
      default: 'Customers',
      reqd: 1
    },
    {
      fieldname: 'detail_level',
      label: __('Detail Level'),
      fieldtype: 'Select',
      options: 'Brief Overview\nModerate Detail\nComprehensive',
      default: 'Moderate Detail',
      reqd: 1
    },
    {
      fieldname: 'include_timing',
      label: __('Include Best Timing Suggestions'),
      fieldtype: 'Check',
      default: 1
    },
    {
      fieldname: 'include_criteria',
      label: __('Include Selection Criteria'),
      fieldtype: 'Check',
      default: 1
    },
    {
      fieldname: 'additional_instructions',
      label: __('Additional Instructions (Optional)'),
      fieldtype: 'Small Text',
      description: __('Any specific audience segments or criteria to consider')
    }
  ],
  (values) => {
    generate_recommended_for(frm, values);
  },
  __('Customize AI Recommendation'),
  __('Generate')
  );
}

function generate_recommended_for(frm, preferences) {
  frappe.call({
    method: 'assistant_crm.assistant_crm.doctype.survey_campaign_template.survey_campaign_template.get_ai_recommended_for',
    args: {
      template_name: frm.doc.template_name,
      template_category: frm.doc.template_category || '',
      description: frm.doc.description || '',
      preferences: preferences
    },
    freeze: true,
    freeze_message: __('Generating AI suggestion...'),
    callback: (r) => {
      if (r.message && r.message.success) {
        // Show preview dialog before applying
        show_suggestion_preview(frm, 'recommended_for', 'Recommended For', r.message.suggestion);
      } else {
        frappe.msgprint({
          title: __('AI Suggestion Failed'),
          message: r.message?.error || __('Failed to generate suggestion.'),
          indicator: 'red'
        });
      }
    }
  });
}

// Show preview dialog for text suggestions
function show_suggestion_preview(frm, fieldname, field_label, suggestion) {
  // Trim and normalize whitespace in the suggestion
  const cleanedSuggestion = suggestion.trim().replace(/\s+/g, ' ');

  const dialog = new frappe.ui.Dialog({
    title: __('AI Suggestion Preview'),
    size: 'large',
    fields: [
      {
        fieldtype: 'HTML',
        fieldname: 'preview_html',
        options: `
          <div style="margin-bottom: 15px;">
            <label class="control-label" style="font-weight: bold;">${__('Suggested')} ${field_label}:</label>
            <div style="background: #f5f7fa; border: 1px solid #d1d8dd; border-radius: 4px; padding: 15px; margin-top: 8px; text-align: left; line-height: 1.5;">
              ${frappe.utils.escape_html(cleanedSuggestion)}
            </div>
          </div>
        `
      }
    ],
    primary_action_label: __('Apply Suggestion'),
    primary_action: () => {
      frm.set_value(fieldname, cleanedSuggestion);
      frappe.show_alert({ message: __(`${field_label} applied!`), indicator: 'green' }, 3);
      dialog.hide();
    },
    secondary_action_label: __('Cancel'),
    secondary_action: () => {
      dialog.hide();
    }
  });

  dialog.show();
}

function suggest_questions(frm) {
  if (!frm.doc.template_name) {
    frappe.msgprint(__('Please enter a Template Name first.'));
    return;
  }

  // Ask for question preferences
  frappe.prompt([
    {
      fieldname: 'num_questions',
      label: __('Number of Questions'),
      fieldtype: 'Int',
      default: 5,
      reqd: 1,
      description: __('How many questions should AI generate? (1-10)')
    },
    {
      fieldname: 'question_style',
      label: __('Question Style'),
      fieldtype: 'Select',
      options: 'Mixed (Variety of types)\nMostly Rating Questions\nMostly Multiple Choice\nMostly Open-ended Text\nMostly Yes/No',
      default: 'Mixed (Variety of types)',
      reqd: 1
    },
    {
      fieldname: 'complexity',
      label: __('Question Complexity'),
      fieldtype: 'Select',
      options: 'Simple & Direct\nModerate\nDetailed & Comprehensive',
      default: 'Moderate',
      reqd: 1
    },
    {
      fieldname: 'focus_area',
      label: __('Focus Area'),
      fieldtype: 'Select',
      options: 'Overall Satisfaction\nService Quality\nProduct Feedback\nEmployee Experience\nProcess Improvement\nGeneral Feedback',
      default: 'Overall Satisfaction',
      reqd: 1
    },
    {
      fieldname: 'additional_instructions',
      label: __('Additional Instructions (Optional)'),
      fieldtype: 'Small Text',
      description: __('Specific topics or aspects to cover in questions')
    },
    {
      fieldtype: 'Section Break',
      label: __('Options')
    },
    {
      fieldname: 'replace_existing',
      label: __('Replace existing questions'),
      fieldtype: 'Check',
      default: frm.doc.template_questions?.length ? 0 : 1
    }
  ],
  (values) => {
    generate_ai_questions(frm, values);
  },
  __('Customize AI Questions'),
  __('Generate')
  );
}

function generate_ai_questions(frm, preferences) {
  frappe.call({
    method: 'assistant_crm.assistant_crm.doctype.survey_campaign_template.survey_campaign_template.get_ai_questions',
    args: {
      template_name: frm.doc.template_name,
      template_category: frm.doc.template_category || '',
      description: frm.doc.description || '',
      num_questions: preferences.num_questions,
      preferences: preferences
    },
    freeze: true,
    freeze_message: __('Generating AI questions...'),
    callback: (r) => {
      if (r.message && r.message.success) {
        // Show preview dialog before applying
        show_questions_preview(frm, r.message.questions, preferences.replace_existing);
      } else {
        frappe.msgprint({
          title: __('AI Question Generation Failed'),
          message: r.message?.error || __('Failed to generate questions.'),
          indicator: 'red'
        });
      }
    }
  });
}

// Show preview dialog for questions
function show_questions_preview(frm, questions, replace_existing) {
  // Build HTML table for questions preview
  let questions_html = `
    <div style="margin-bottom: 15px;">
      <label class="control-label" style="font-weight: bold;">${__('AI Generated Questions')}:</label>
      <table class="table table-bordered" style="margin-top: 10px;">
        <thead>
          <tr style="background: #f5f7fa;">
            <th style="width: 5%;">#</th>
            <th style="width: 50%;">${__('Question')}</th>
            <th style="width: 20%;">${__('Type')}</th>
            <th style="width: 15%;">${__('Required')}</th>
          </tr>
        </thead>
        <tbody>
  `;

  questions.forEach((q, idx) => {
    questions_html += `
      <tr>
        <td>${idx + 1}</td>
        <td>${frappe.utils.escape_html(q.question_text)}</td>
        <td><span class="badge">${q.question_type}</span></td>
        <td>${q.is_required ? '<i class="fa fa-check text-success"></i> Yes' : '<i class="fa fa-times text-muted"></i> No'}</td>
      </tr>
    `;
  });

  questions_html += `
        </tbody>
      </table>
      <p class="text-muted" style="margin-top: 10px;">
        <i class="fa fa-info-circle"></i>
        ${replace_existing ? __('This will replace all existing questions.') : __('These questions will be added to existing ones.')}
      </p>
    </div>
  `;

  const dialog = new frappe.ui.Dialog({
    title: __('AI Questions Preview'),
    size: 'extra-large',
    fields: [
      {
        fieldtype: 'HTML',
        fieldname: 'questions_preview_html',
        options: questions_html
      }
    ],
    primary_action_label: __('Apply Questions'),
    primary_action: () => {
      apply_ai_questions(frm, questions, replace_existing);
      dialog.hide();
    },
    secondary_action_label: __('Cancel'),
    secondary_action: () => {
      dialog.hide();
    }
  });

  dialog.show();
}

function apply_ai_questions(frm, questions, replace_existing) {
  if (replace_existing) {
    frm.clear_table('template_questions');
  }

  // Calculate starting order
  let start_order = 1;
  if (!replace_existing && frm.doc.template_questions?.length) {
    const max_order = Math.max(...frm.doc.template_questions.map(q => q.order || 0));
    start_order = max_order + 1;
  }

  // Add questions to the table
  questions.forEach((q, idx) => {
    const row = frm.add_child('template_questions');
    row.question_text = q.question_text;
    row.question_type = q.question_type;
    row.options = q.options || '';
    row.is_required = q.is_required;
    row.order = start_order + idx;
  });

  frm.refresh_field('template_questions');

  frappe.show_alert({
    message: __('Added {0} AI-generated questions!', [questions.length]),
    indicator: 'green'
  }, 5);
}

