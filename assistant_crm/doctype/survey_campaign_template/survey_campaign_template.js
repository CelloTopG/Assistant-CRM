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

  frappe.call({
    method: 'assistant_crm.assistant_crm.doctype.survey_campaign_template.survey_campaign_template.get_ai_description',
    args: {
      template_name: frm.doc.template_name,
      template_category: frm.doc.template_category || ''
    },
    freeze: true,
    freeze_message: __('Generating AI suggestion...'),
    callback: (r) => {
      if (r.message && r.message.success) {
        frm.set_value('description', r.message.suggestion);
        frappe.show_alert({ message: __('Description generated!'), indicator: 'green' }, 3);
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

  frappe.call({
    method: 'assistant_crm.assistant_crm.doctype.survey_campaign_template.survey_campaign_template.get_ai_recommended_for',
    args: {
      template_name: frm.doc.template_name,
      template_category: frm.doc.template_category || '',
      description: frm.doc.description || ''
    },
    freeze: true,
    freeze_message: __('Generating AI suggestion...'),
    callback: (r) => {
      if (r.message && r.message.success) {
        frm.set_value('recommended_for', r.message.suggestion);
        frappe.show_alert({ message: __('Recommendation generated!'), indicator: 'green' }, 3);
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

function suggest_questions(frm) {
  if (!frm.doc.template_name) {
    frappe.msgprint(__('Please enter a Template Name first.'));
    return;
  }

  // Ask for number of questions
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
      fieldname: 'replace_existing',
      label: __('Replace existing questions'),
      fieldtype: 'Check',
      default: frm.doc.template_questions?.length ? 0 : 1
    }
  ],
  (values) => {
    generate_ai_questions(frm, values.num_questions, values.replace_existing);
  },
  __('Generate AI Questions'),
  __('Generate')
  );
}

function generate_ai_questions(frm, num_questions, replace_existing) {
  frappe.call({
    method: 'assistant_crm.assistant_crm.doctype.survey_campaign_template.survey_campaign_template.get_ai_questions',
    args: {
      template_name: frm.doc.template_name,
      template_category: frm.doc.template_category || '',
      description: frm.doc.description || '',
      num_questions: num_questions
    },
    freeze: true,
    freeze_message: __('Generating AI questions...'),
    callback: (r) => {
      if (r.message && r.message.success) {
        apply_ai_questions(frm, r.message.questions, replace_existing);
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

