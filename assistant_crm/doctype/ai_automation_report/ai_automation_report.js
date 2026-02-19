frappe.ui.form.on('AI Automation Report', {
  refresh(frm) {
    if (!frm.doc.__islocal) {
      add_report_buttons(frm);
      render_ai_sidebar(frm);
      render_charts(frm);
    }
  },
});

function add_report_buttons(frm) {
  frm.add_custom_button(__('Generate Report'), () => {
    frappe.call({
      method: 'assistant_crm.assistant_crm.doctype.ai_automation_report.ai_automation_report.generate_ai_automation_report',
      args: { name: frm.doc.name },
      freeze: true,
      freeze_message: __('Generating AI Automation metrics...'),
      callback: () => frm.reload_doc(),
    });
  });

  frm.add_custom_button(__('Download PDF'), () => {
    frappe.call({
      method: 'assistant_crm.assistant_crm.doctype.ai_automation_report.ai_automation_report.generate_pdf',
      args: { name: frm.doc.name },
      freeze: true,
      freeze_message: __('Generating PDF...'),
      callback: () => {
        frappe.show_alert({ message: __('PDF attached to the document'), indicator: 'green' });
      },
    });
  });

  frm.add_custom_button(__('Email Report'), () => {
    frappe.call({
      method: 'assistant_crm.assistant_crm.doctype.ai_automation_report.ai_automation_report.email_report',
      args: { name: frm.doc.name },
      freeze: true,
      freeze_message: __('Emailing report to CRM Admin & ICT...'),
      callback: (r) => {
        if (r && r.message && r.message.status === 'sent') {
          frappe.msgprint(__('Email sent successfully'));
        }
      },
    });
  });
}

function render_charts(frm) {
  const charts = [
    { field: 'automation_chart_json', parent: 'automation-summary-chart' },
    { field: 'after_hours_chart_json', parent: 'after-hours-chart' },
    { field: 'document_validation_chart_json', parent: 'document-validation-chart' },
    { field: 'data_quality_chart_json', parent: 'data-quality-chart' },
    { field: 'ai_failure_chart_json', parent: 'ai-failure-chart' },
    { field: 'system_health_chart_json', parent: 'system-health-chart' },
  ];

  charts.forEach(cfg => {
    const data = frm.doc[cfg.field];
    if (!data) return;
    let parsed;
    try {
      parsed = JSON.parse(data);
    } catch (e) {
      return;
    }
    const container = frm.get_field('report_html')?.$wrapper;
    if (!container) return;
    let target = container.find(`.${cfg.parent}`);
    if (!target.length) {
      target = $(`<div class="${cfg.parent}" style="margin-top: 16px"></div>`);
      container.append(target);
    }
    target.empty();
    new frappe.Chart(target[0], parsed);
  });
}

function render_ai_sidebar(frm) {
  const sidebar = $(
    '<div class="frappe-control"><div class="control-input-wrapper">' +
    '<div class="control-input flex"><input class="form-control" type="text" ' +
    'placeholder="This is WorkCom, how can I help?" />' +
    '<button class="btn btn-default" style="margin-left:6px">Ask</button></div>' +
    '<div class="help-box small text-muted" style="margin-top:6px">' +
    'Uses current and recent reports for trend analysis and forecasting.</div>' +
    '<div class="ai-output" style="white-space:pre-wrap; margin-top:8px"></div>' +
    '</div></div>'
  );
  const ai_container = $('<div class="ai-automation-sidebar"></div>').append(sidebar);

  if (frm.sidebar && frm.sidebar.add_user_action) {
    frm.sidebar.add_user_action(ai_container);
  } else {
    $(frm.wrapper).find('.form-sidebar').append(ai_container);
  }

  const input = sidebar.find('input');
  const btn = sidebar.find('button');
  const out = sidebar.find('.ai-output');

  const ask = () => {
    const q = (input.val() || '').trim();
    if (!q) return;
    out.text('Thinking...');
    frappe.call({
      method: 'assistant_crm.assistant_crm.doctype.ai_automation_report.ai_automation_report.get_ai_insights',
      args: { name: frm.doc.name, query: q },
      callback: (r) => {
        out.text(r && r.message && r.message.insights ? r.message.insights : 'No insights returned.');
      },
      error: () => {
        out.text('Error retrieving insights.');
      },
    });
  };

  btn.on('click', ask);
  input.on('keypress', (e) => {
    if (e.which === 13) ask();
  });
}


