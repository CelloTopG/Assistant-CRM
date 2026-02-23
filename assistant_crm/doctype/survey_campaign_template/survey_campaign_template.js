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
      <i class="fa fa-magic"></i> WorkCom Suggest
    </button>
  `);
  frm.fields_dict.description.$wrapper.find('.clearfix').append(desc_btn);
  desc_btn.on('click', () => suggest_description(frm));

  // Add AI button for Recommended For field
  const rec_btn = $(`
    <button class="btn btn-xs btn-default ai-suggest-btn" style="margin-left: 10px;">
      <i class="fa fa-magic"></i> WorkCom Suggest
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
        <i class="fa fa-magic"></i> Generate WorkCom Questions
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
    __('Customize WorkCom Description'),
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
    freeze_message: __('Generating WorkCom suggestion...'),
    callback: (r) => {
      if (r.message && r.message.success) {
        // Show preview dialog before applying
        show_suggestion_preview(frm, 'description', 'Description', r.message.suggestion);
      } else {
        frappe.msgprint({
          title: __('WorkCom Suggestion Failed'),
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
    __('Customize WorkCom Recommendation'),
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
    freeze_message: __('Generating WorkCom suggestion...'),
    callback: (r) => {
      if (r.message && r.message.success) {
        // Show preview dialog before applying
        show_suggestion_preview(frm, 'recommended_for', 'Recommended For', r.message.suggestion);
      } else {
        frappe.msgprint({
          title: __('WorkCom Suggestion Failed'),
          message: r.message?.error || __('Failed to generate suggestion.'),
          indicator: 'red'
        });
      }
    }
  });
}

// Show preview dialog for text suggestions
function show_suggestion_preview(frm, fieldname, field_label, suggestion) {
  const cleanedSuggestion = suggestion.trim();

  const dialog = new frappe.ui.Dialog({
    title: __('Edit WorkCom Suggestion'),
    size: 'large',
    fields: [
      {
        label: __('Suggested') + ' ' + field_label,
        fieldtype: 'Small Text',
        fieldname: 'edited_suggestion',
        default: cleanedSuggestion,
        description: __('You can edit the AI-generated text before applying it.')
      }
    ],
    primary_action_label: __('Apply Suggestion'),
    primary_action: (values) => {
      frm.set_value(fieldname, values.edited_suggestion);
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
      default: 1,
      description: __('Uncheck to append questions instead of replacing')
    }
  ],
    (values) => {
      generate_ai_questions(frm, values);
    },
    __('Customize WorkCom Questions'),
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
    freeze_message: __('Generating WorkCom questions...'),
    callback: (r) => {
      if (r.message && r.message.success) {
        // Show preview dialog before applying
        show_questions_preview(frm, r.message.questions, preferences.replace_existing);
      } else {
        frappe.msgprint({
          title: __('WorkCom Question Generation Failed'),
          message: r.message?.error || __('Failed to generate questions.'),
          indicator: 'red'
        });
      }
    }
  });
}

// Show preview dialog for questions
function show_questions_preview(frm, questions, replace_existing) {
  // Ensure we unfreeze manually to be safe
  frappe.unfreeze();

  const dialog = new frappe.ui.Dialog({
    title: __('Edit WorkCom Generated Questions'),
    size: 'extra-large',
    fields: [
      {
        fieldname: 'questions_table',
        fieldtype: 'Table',
        label: __('Review & Edit Questions'),
        options: 'Survey Template Question',
        cannot_add_rows: false,
        cannot_delete_rows: false,
        fields: [
          {
            fieldname: 'question_text',
            fieldtype: 'Data',
            label: __('Question'),
            in_list_view: 1,
            reqd: 1,
            columns: 5
          },
          {
            fieldname: 'question_type',
            fieldtype: 'Select',
            label: __('Type'),
            options: 'Rating\nMultiple Choice\nText\nYes/No',
            in_list_view: 1,
            columns: 2
          },
          {
            fieldname: 'is_required',
            fieldtype: 'Check',
            label: __('Required'),
            in_list_view: 1,
            columns: 1
          },
          {
            fieldname: 'options',
            fieldtype: 'Long Text',
            label: __('Options (for Multi Choice)'),
            in_list_view: 0
          }
        ]
      },
      {
        fieldtype: 'Section Break'
      },
      {
        fieldname: 'replace_existing_questions',
        label: __('Replace all existing questions in template'),
        fieldtype: 'Check',
        default: replace_existing ? 1 : 0
      }
    ],
    primary_action_label: __('Apply Questions'),
    primary_action: (values) => {
      const grid = dialog.get_field('questions_table').grid;
      const edited_questions = grid.get_data().filter(q => q && !q.__deleted && q.question_text);

      if (edited_questions.length === 0) {
        frappe.msgprint(__('Please keep at least one question.'));
        return;
      }
      apply_ai_questions(frm, edited_questions, values.replace_existing_questions);
      dialog.hide();
    },
    secondary_action_label: __('Cancel'),
    secondary_action: () => {
      dialog.hide();
    }
  });

  // Populate table data reliably
  const table_field = dialog.get_field('questions_table');
  table_field.df.data = questions.map(q => ({
    question_text: q.question_text,
    question_type: q.question_type,
    is_required: q.is_required ? 1 : 0,
    options: q.options || ''
  }));

  dialog.show();

  // Refresh grid after show to ensure rendering
  table_field.grid.refresh();
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
    message: __('Added {0} WorkCom-generated questions!', [questions.length]),
    indicator: 'green'
  }, 5);
}

