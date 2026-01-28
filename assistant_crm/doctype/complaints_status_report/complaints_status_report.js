frappe.ui.form.on('Complaints Status Report', {
  refresh(frm) {
    if (!frm.doc.__islocal) {
      frm.add_custom_button('Generate Report', () => generate_report(frm), 'Actions');
      frm.add_custom_button('Download PDF', () => download_pdf(frm), 'Actions');
      frm.add_custom_button('Email Report', () => email_report(frm), 'Actions');

      // Render charts, AI, and overrides panel if present
      try { render_charts(frm); } catch (e) { /* no-op */ }
      try { render_ai_sidebar(frm); } catch (e) { /* no-op */ }
      try { render_rows_panel(frm); } catch (e) { /* no-op */ }
    }
  }
});

function generate_report(frm) {
  frappe.call({
    method: 'run_generation',
    doc: frm.doc,
    callback: (r) => {
      frm.reload_doc();
      frappe.msgprint('Report generated');
    }
  });
}

function download_pdf(frm) {
  frappe.call({
    method: 'generate_pdf',
    doc: frm.doc,
    callback: (r) => {
      frappe.show_alert({message: 'PDF attached to the document', indicator: 'green'});
    }
  });
}

function email_report(frm) {
  // First fetch default recipients from the server, then show a preview dialog
  frappe.call({
    method: 'get_recipients',
    doc: frm.doc,
    callback: (r) => {
      const payload = r && r.message ? r.message : {};
      const defaults = payload.recipients || [];

      const d = new frappe.ui.Dialog({
        title: 'Email Complaints Status Report',
        fields: [
          {
            label: 'Recipients',
            fieldname: 'recipients',
            fieldtype: 'Small Text',
            description: 'One email per line or separated by commas/semicolons. Default is Customer Service & Corporate Affairs.'
          }
        ],
        primary_action_label: 'Send',
        primary_action(values) {
          let txt = values.recipients || '';
          let recips = txt
            .split(/[\n,;]+/)
            .map(v => v.trim())
            .filter(Boolean);

          frappe.call({
            method: 'email_report',
            doc: frm.doc,
            args: recips.length ? { recipients: recips } : {},
            callback: (res) => {
              const msg = res && res.message ? res.message : null;
              const status = msg && msg.message ? msg.message : msg;

              if (status === 'no-recipients') {
                frappe.msgprint('No recipients found for Customer Service / Corporate Affairs.');
              } else {
                const sent_to = msg && Array.isArray(msg.recipients) ? msg.recipients.join(', ') : '';
                frappe.msgprint(sent_to
                  ? `Email sent to: ${sent_to}`
                  : 'Email sent');
              }
            }
          });

          d.hide();
        }
      });

      d.set_values({ recipients: (defaults || []).join('\n') });
      d.show();
    }
  });
}

function render_charts(frm) {
  const wrap = $(frm.fields_dict.report_html.wrapper);
  if (!wrap || !wrap.length) return;

  // Category chart
  if (frm.doc.chart_json) {
    try {
      const cfg = JSON.parse(frm.doc.chart_json);
      const chart1 = $('<div style="margin-top:10px"></div>').get(0);
      wrap.append(chart1);
      new frappe.Chart(chart1, cfg);
    } catch (e) { /* ignore */ }
  }

  // Status chart
  if (frm.doc.status_chart_json) {
    try {
      const cfg2 = JSON.parse(frm.doc.status_chart_json);
      const chart2 = $('<div style="margin-top:10px"></div>').get(0);
      wrap.append(chart2);
      new frappe.Chart(chart2, cfg2);
    } catch (e) { /* ignore */ }
  }

  // Platform-by-Category stacked bar
  if (frm.doc.stacked_chart_json) {
    try {
      const cfg3 = JSON.parse(frm.doc.stacked_chart_json);
      const chart3 = $('<div style="margin-top:10px"></div>').get(0);
      wrap.append(chart3);
      new frappe.Chart(chart3, cfg3);
    } catch (e) { /* ignore */ }
  }

  // Trend chart
  if (frm.doc.trend_chart_json) {
    try {
      const cfg4 = JSON.parse(frm.doc.trend_chart_json);
      const chart4 = $('<div style="margin-top:10px"></div>').get(0);
      wrap.append(chart4);
      new frappe.Chart(chart4, cfg4);
    } catch (e) { /* ignore */ }
  }
}

function render_ai_sidebar(frm) {
  const sidebar = $(
    '<div class="frappe-control"><div class="control-input-wrapper">' +
    '<div class="control-input flex"><input class="form-control" type="text" ' +
    'placeholder="This is Antoine, how can I help with complaints performance?" />' +
    '<button class="btn btn-default" style="margin-left:6px">Ask</button></div>' +
    '<div class="help-box small text-muted" style="margin-top:6px">Uses current and recent complaints reports for trend and risk analysis.</div>' +
    '<div class="ai-output" style="white-space:pre-wrap; margin-top:8px"></div>' +
    '</div></div>'
  );
  const ai_container = $('<div class="complaints-ai-sidebar"></div>').append(sidebar);
  if (frm.sidebar && frm.sidebar.add_user_action) {
    frm.sidebar.add_user_action(ai_container);
  } else {
    // Fallback: append into form wrapper
    $(frm.wrapper).find('.form-sidebar').append(ai_container);
  }

  const input = sidebar.find('input');
  const btn = sidebar.find('button');
  const out = sidebar.find('.ai-output');

  function ask() {
    const query = (input.val() || '').trim();
    if (!query) return;
    out.text('Thinking...');
    frappe.call({
      method: 'assistant_crm.assistant_crm.doctype.complaints_status_report.complaints_status_report.get_ai_insights',
      args: { name: frm.doc.name, query },
      callback: (r) => {
        out.text(r && r.message && r.message.insights ? r.message.insights : 'No insights returned.');
      },
      error: () => out.text('Error retrieving insights.')
    });
  }

  btn.on('click', ask);
  input.on('keypress', (e) => { if (e.which === 13) ask(); });
}



function render_rows_panel(frm) {
  const wrap = $(frm.fields_dict.report_html.wrapper);
  if (!wrap || !wrap.length) return;
  if (!frm.doc.rows_json) return;

  let rows;
  try { rows = JSON.parse(frm.doc.rows_json || '[]'); } catch (e) { rows = []; }
  if (!rows || !rows.length) return;

  const container = $('<div style="margin-top:14px"></div>');
  container.append('<h5>Complaints (sample)</h5>');

  const tbl = $('<table class="table table-bordered table-condensed"></table>');
  const thead = $('<thead><tr>' +
    '<th>Source</th><th>ID</th><th>Platform</th><th>Status</th>' +
    '<th>Auto</th><th>Override</th><th>Final</th><th></th>' +
    '</tr></thead>');
  const tbody = $('<tbody></tbody>');

  const CATS = ['Claims', 'Compliance', 'General'];

  (rows.slice(0, 50)).forEach((r) => {
    const tr = $('<tr></tr>');
    const link = $('<a></a>')
      .attr('href', `/app/${r.doctype.toLowerCase().replace(/ /g,'-')}/${r.name}`)
      .attr('target', '_blank')
      .text(r.name);

    const sel = $('<select class="input-xs form-control"></select>');
    sel.append('<option value="">(none)</option>');
    CATS.forEach((c) => sel.append(`<option value="${c}">${c}</option>`));
    if (r.override_category) sel.val(r.override_category);

    const save = $('<button class="btn btn-sm btn-default">Save</button>');

    save.on('click', () => {
      const newCat = sel.val();
      frappe.call({
        method: 'assistant_crm.assistant_crm.doctype.complaints_status_report.complaints_status_report.set_category_override',
        args: { source_doctype: r.doctype, source_name: r.name, category: newCat },
        callback: () => {
          frappe.show_alert({ message: 'Override saved', indicator: 'green' });
          // reflect locally
          r.override_category = newCat || null;
          r.final_category = newCat || r.auto_category;
          tr.find('.final-cell').text(r.final_category || '');
        }
      });
    });

    tr.append(`<td>${frappe.utils.escape_html(r.doctype || '')}</td>`);
    tr.append($('<td></td>').append(link));
    tr.append(`<td>${frappe.utils.escape_html(r.platform || '')}</td>`);
    tr.append(`<td>${frappe.utils.escape_html(r.status || '')}</td>`);
    tr.append(`<td>${frappe.utils.escape_html(r.auto_category || '')}</td>`);
    tr.append($('<td></td>').append(sel));
    tr.append($('<td class=\"final-cell\"></td>').text(r.final_category || ''));
    tr.append($('<td></td>').append(save));
    tbody.append(tr);
  });

  tbl.append(thead).append(tbody);
  container.append(tbl);
  wrap.append(container);
}
