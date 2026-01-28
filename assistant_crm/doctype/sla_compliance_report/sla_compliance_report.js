frappe.ui.form.on('SLA Compliance Report', {
  refresh(frm) {
    if (!frm.doc.__islocal) {
      frm.add_custom_button('Generate Report', () => generate_report(frm), 'Actions');
      frm.add_custom_button('Download PDF', () => download_pdf(frm), 'Actions');
      frm.add_custom_button('Email Report', () => email_report(frm), 'Actions');

      try { render_charts(frm); } catch (e) {}
      try { render_ai_sidebar(frm); } catch (e) {}
    } else {
      frm.set_value('period_type', frm.doc.period_type || 'Monthly');
    }
  }
});

function generate_report(frm) {
  frappe.call({
    method: 'run_generation',
    doc: frm.doc,
    callback: (r) => {
      if (r && r.message) {
        frappe.show_alert({ message: 'Report generated', indicator: 'green' });
        frm.reload_doc();
      }
    }
  });
}

function download_pdf(frm) {
  frappe.call({
    method: 'generate_pdf',
    doc: frm.doc,
    callback: (r) => {
      if (r && r.message && r.message.file_url) {
        window.open(r.message.file_url, '_blank');
      } else {
        frappe.show_alert({ message: 'PDF attached to the document.', indicator: 'blue' });
      }
    }
  });
}

function email_report(frm) {
  frappe.call({
    method: 'email_report',
    doc: frm.doc,
    callback: (r) => {
      if (r && r.message && r.message.ok) {
        frappe.show_alert({ message: 'Email sent to managers.', indicator: 'green' });
      } else {
        frappe.msgprint('Could not send email.');
      }
    }
  });
}

function render_charts(frm) {
  // Overview
  if (frm.doc.chart_overview_json) {
    const data = JSON.parse(frm.doc.chart_overview_json || '{}');
    const el = $('<div style="margin-top:10px"></div>').appendTo(frm.fields_dict.report_html.$wrapper);
    new frappe.Chart(el[0], data);
  }
  // Branch
  if (frm.doc.branch_breakdown_chart_json) {
    const data = JSON.parse(frm.doc.branch_breakdown_chart_json || '{}');
    const el = $('<div style="margin-top:10px"></div>').appendTo(frm.fields_dict.report_html.$wrapper);
    new frappe.Chart(el[0], data);
  }
  // Role
  if (frm.doc.role_breakdown_chart_json) {
    const data = JSON.parse(frm.doc.role_breakdown_chart_json || '{}');
    const el = $('<div style="margin-top:10px"></div>').appendTo(frm.fields_dict.report_html.$wrapper);
    new frappe.Chart(el[0], data);
  }
  // Trend
  if (frm.doc.trend_chart_json) {
    const data = JSON.parse(frm.doc.trend_chart_json || '{}');
    const el = $('<div style="margin-top:10px"></div>').appendTo(frm.fields_dict.report_html.$wrapper);
    new frappe.Chart(el[0], data);
  }
}

function render_ai_sidebar(frm) {
  if (!frm.sidebar || !frm.sidebar.add_user_action) return;
  const wrapper = $(
    '<div class="frappe-control"><div class="control-input-wrapper">' +
    '<div class="control-input flex"><input class="form-control" type="text" ' +
    'placeholder="This is Antoine, how can I help with SLA performance?" />' +
    '<button class="btn btn-default" style="margin-left:6px">Ask</button></div>' +
    '<div class="help-box small text-muted" style="margin-top:6px">Uses current and historical SLA reports for trend and risk analysis.</div>' +
    '<div class="ai-output" style="white-space:pre-wrap; margin-top:8px"></div>' +
    '</div></div>'
  );
  const input = wrapper.find('input');
  const out = wrapper.find('.ai-output');
  const btn = wrapper.find('button');
  btn.on('click', ask);
  input.on('keydown', (e) => { if (e.key === 'Enter') ask(); });
  frm.sidebar.add_user_action(wrapper);

  function ask() {
    const query = (input.val() || '').trim();
    if (!query) return;
    out.text('Thinking...');
    frappe.call({
      method: 'assistant_crm.assistant_crm.doctype.sla_compliance_report.sla_compliance_report.get_ai_insights',
      args: { name: frm.doc.name, query },
      callback: (r) => {
        out.text(r && r.message && r.message.insights ? r.message.insights : 'No insights returned.');
      }
    });
  }
}

