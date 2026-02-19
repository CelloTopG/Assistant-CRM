frappe.ui.form.on('Inbox Status Report', {
  refresh(frm) {
    if (!frm.doc.__islocal) {
      frm.add_custom_button('Generate Report', () => generate_report(frm), 'Actions');
      frm.add_custom_button('Download PDF', () => download_pdf(frm), 'Actions');
      frm.add_custom_button('Email Report', () => email_report(frm), 'Actions');
      try { render_charts(frm); } catch (e) {}
      try { render_ai_sidebar(frm); } catch (e) {}
    }
  }
});

function generate_report(frm) {
  frappe.call({ method: 'run_generation', doc: frm.doc, callback: () => { frm.reload_doc(); frappe.msgprint('Report generated'); } });
}
function download_pdf(frm) {
  frappe.call({ method: 'generate_pdf', doc: frm.doc, callback: () => frappe.show_alert({message: 'PDF attached', indicator: 'green'}) });
}
function email_report(frm) {
  frappe.call({ method: 'email_report', doc: frm.doc, callback: (r) => { if (r && r.message === 'no-recipients') frappe.msgprint('No recipients for Customer Service / ICT.'); else frappe.msgprint('Email sent'); } });
}

function render_charts(frm) {
  const wrap = $(frm.fields_dict.report_html.wrapper); if (!wrap || !wrap.length) return;
  function add(cfg){ try{ const el=$('<div style="margin-top:10px"></div>').get(0); wrap.append(el); new frappe.Chart(el, JSON.parse(cfg)); }catch(e){} }
  if (frm.doc.platform_chart_json) add(frm.doc.platform_chart_json);
  if (frm.doc.direction_chart_json) add(frm.doc.direction_chart_json);
  if (frm.doc.status_chart_json) add(frm.doc.status_chart_json);
  if (frm.doc.priority_chart_json) add(frm.doc.priority_chart_json);
  if (frm.doc.platform_direction_stacked_json) add(frm.doc.platform_direction_stacked_json);
  if (frm.doc.trend_chart_json) add(frm.doc.trend_chart_json);
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
  const ai_container = $('<div class="inbox-ai-sidebar"></div>').append(sidebar);
  if (frm.sidebar && frm.sidebar.add_user_action) {
    frm.sidebar.add_user_action(ai_container);
  } else {
    $(frm.wrapper).find('.form-sidebar').append(ai_container);
  }

  const input = sidebar.find('input');
  const btn = sidebar.find('button');
  const out = sidebar.find('.ai-output');

  btn.on('click', () => ask_ai(frm, input, out));
  input.on('keypress', (e) => { if (e.which === 13) ask_ai(frm, input, out); });
}

function ask_ai(frm, input, out) {
  const query = (input.val() || '').trim();
  if (!query) return;
  out.text('Thinking...');
  frappe.call({
    method: 'assistant_crm.assistant_crm.doctype.inbox_status_report.inbox_status_report.get_ai_insights',
    args: { name: frm.doc.name, query },
    callback: (r) => {
      out.text(r && r.message && r.message.insights ? r.message.insights : 'No insights returned.');
    },
    error: () => out.text('Error retrieving insights.'),
  });
}


