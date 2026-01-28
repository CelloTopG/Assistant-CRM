frappe.ui.form.on('Employer Status Report', {
  refresh(frm) {
    if (!frm.doc.__islocal) {
      frm.add_custom_button('Generate Report', () => generate_report(frm), 'Actions');
      frm.add_custom_button('Download PDF', () => download_pdf(frm), 'Actions');
      frm.add_custom_button('Email Report', () => email_report(frm), 'Actions');

      try { render_charts(frm); } catch (e) { /* no-op */ }
      try { render_ai_sidebar(frm); } catch (e) { /* no-op */ }
      try { render_top_claims(frm); } catch (e) { /* no-op */ }
    }
  }
});

function generate_report(frm) {
  frappe.call({
    method: 'run_generation',
    doc: frm.doc,
    callback: () => {
      frm.reload_doc();
      frappe.msgprint('Report generated');
    }
  });
}

function download_pdf(frm) {
  frappe.call({
    method: 'assistant_crm.assistant_crm.doctype.employer_status_report.employer_status_report.generate_pdf',
    args: { name: frm.doc.name },
    callback: () => {
      frappe.show_alert({message: 'PDF attached to the document', indicator: 'green'});
    }
  });
}

function email_report(frm) {
  frappe.call({
    method: 'assistant_crm.assistant_crm.doctype.employer_status_report.employer_status_report.email_report',
    args: { name: frm.doc.name },
    callback: (r) => {
      if (r && r.message && r.message.message === 'no-recipients') {
        frappe.msgprint('No recipients found for Finance / Claims.');
      } else {
        frappe.msgprint('Email sent');
      }
    }
  });
}

function render_charts(frm) {
  const fld = frm.fields_dict.report_html;
  if (!fld || !fld.wrapper) {
    // No wrapper found; nothing to render into
    return;
  }
  const wrap = $(fld.wrapper);
  if (!wrap || !wrap.length) return;

  // Debug placeholder so we can visually confirm this block ran
  wrap.append('<div style="margin-top:10px;color:#888">Employer Dashboard Charts Section</div>');

  function add_chart(json) {
    if (!json) return;
    try {
      const cfg = JSON.parse(json);
      const el = $('<div style="margin-top:10px"></div>').get(0);
      wrap.append(el);
      if (frappe.Chart) {
        new frappe.Chart(el, cfg);
      } else if (frappe.chart && frappe.chart.Chart) {
        // Fallback for older Frappe chart API
        new frappe.chart.Chart(el, cfg);
      }
    } catch (e) {
      // Swallow JSON/Chart errors so the form still loads
    }
  }

  add_chart(frm.doc.status_chart_json);
  add_chart(frm.doc.compliance_chart_json);
  add_chart(frm.doc.contributions_chart_json);
  add_chart(frm.doc.trend_chart_json);
}

function render_ai_sidebar(frm) {
  const sidebar = $(
    '<div class="frappe-control"><div class="control-input-wrapper">' +
    '<div class="control-input flex"><input class="form-control" type="text" placeholder="This is Antoine, how can I help?" />' +
    '<button class="btn btn-default" style="margin-left:6px">Ask</button></div>' +
    '<div class="help-box small text-muted" style="margin-top:6px">Uses current and recent reports for trend analysis and forecasting.</div>' +
    '<div class="ai-output" style="white-space:pre-wrap; margin-top:8px"></div>' +
    '</div></div>'
  );
  const ai_container = $('<div class="employer-ai-sidebar"></div>').append(sidebar);
  frm.sidebar && frm.sidebar.add_user_action && frm.sidebar.add_user_action(ai_container);

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
    method: 'assistant_crm.assistant_crm.doctype.employer_status_report.employer_status_report.get_ai_insights',
    args: { name: frm.doc.name, query },
    callback: (r) => {
      out.text(r && r.message && r.message.insights ? r.message.insights : 'No insights returned.');
    },
    error: () => out.text('Error retrieving insights.')
  });
}

function render_top_claims(frm) {
  const wrap = $(frm.fields_dict.report_html.wrapper);
  if (!wrap || !wrap.length) return;
  if (!frm.doc.top_claims_json) return;
  let rows = [];
  try { rows = JSON.parse(frm.doc.top_claims_json || '[]'); } catch (e) { rows = []; }
  if (!rows || !rows.length) return;
  const container = $('<div style="margin-top:14px"></div>');
  container.append('<h5>Top Employers by Claims</h5>');
  const tbl = $('<table class="table table-bordered table-condensed"></table>');
  const thead = $('<thead><tr><th>Employer</th><th>Claims</th><th>Amount</th></tr></thead>');
  const tbody = $('<tbody></tbody>');
  (rows.slice(0, 20)).forEach((r) => {
    const tr = $('<tr></tr>');
    tr.append($('<td></td>').text(r.employer || ''));
    tr.append($('<td></td>').text(String(r.claims || 0)));
    tr.append($('<td></td>').text((r.amount || 0).toLocaleString()))
    tbody.append(tr);
  });
  tbl.append(thead).append(tbody);
  container.append(tbl);
  wrap.append(container);
}
