frappe.ui.form.on('Claims Status Report', {
  refresh(frm) {
    // default dates
    if (!frm.doc.date_from || !frm.doc.date_to) {
      frm.trigger('set_period_defaults');
    }

    // Action buttons
    if (!frm.is_new()) {
      frm.add_custom_button('Generate Report', () => {
        frappe.call({
          method: 'assistant_crm.assistant_crm.doctype.claims_status_report.claims_status_report.generate_report',
          args: { name: frm.doc.name },
          freeze: true,
          callback: () => frm.reload_doc(),
        });
      }).addClass('btn-primary');

      frm.add_custom_button('Download PDF', () => {
        frappe.call({
          method: 'assistant_crm.assistant_crm.doctype.claims_status_report.claims_status_report.generate_pdf',
          args: { name: frm.doc.name },
          freeze: true,
          callback: (r) => {
            const url = r && r.message && r.message.file_url;
            if (url) window.open(url, '_blank');
          }
        });
      });

      frm.add_custom_button('Email Report', () => {
        frappe.call({
          method: 'assistant_crm.assistant_crm.doctype.claims_status_report.claims_status_report.email_report',
          args: { name: frm.doc.name },
          freeze: true,
          callback: (r) => {
            frappe.show_alert({message: 'Report emailed', indicator: 'green'});
          }
        });
      });
    }

    // Sidebar AI
    render_ai_sidebar(frm);

    // Render HTML table and chart if present
    render_report_table(frm);
    render_report_chart(frm);
  },

  set_period_defaults(frm) {
    if (frm.doc.period_type === 'Weekly') {
      const today = frappe.datetime.get_today();
      frm.set_value('date_to', today);
      frm.set_value('date_from', frappe.datetime.add_days(today, -6));
    } else {
      const today = frappe.datetime.get_today();
      frm.set_value('date_from', today);
      frm.set_value('date_to', today);
    }
  }
});

function render_report_table(frm) {
  const wrapper = frm.fields_dict.report_html && frm.fields_dict.report_html.$wrapper;
  if (!wrapper) return;
  wrapper.empty();
  if (frm.doc.report_html) {
    $(wrapper).html(frm.doc.report_html);
  }
}

function render_report_chart(frm) {
  try {
    if (!frm.doc.chart_json) return;
    const data = JSON.parse(frm.doc.chart_json);
    let chart_holder = $(frm.fields_dict.report_html.$wrapper).parent().find('.claims-chart-holder');
    if (!chart_holder.length) {
      chart_holder = $('<div class="claims-chart-holder" style="margin-top:12px"></div>');
      $(frm.fields_dict.report_html.$wrapper).parent().append(chart_holder);
    }
    chart_holder.empty();
    new frappe.Chart(chart_holder.get(0), data);
  } catch (e) {
    // ignore chart errors
  }
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
  const ai_container = $('<div class="claims-ai-sidebar"></div>').append(sidebar);
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
    method: 'assistant_crm.assistant_crm.doctype.claims_status_report.claims_status_report.get_ai_insights',
    args: { name: frm.doc.name, query },
    callback: (r) => {
      out.text(r && r.message && r.message.insights ? r.message.insights : 'No insights returned.');
    },
    error: () => out.text('Error retrieving insights.')
  });
}

