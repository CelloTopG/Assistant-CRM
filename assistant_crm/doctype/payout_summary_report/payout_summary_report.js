frappe.ui.form.on('Payout Summary Report', {
  refresh(frm) {
    if (!frm.is_new()) {
      frm.add_custom_button('Generate Report', () => {
        frappe.call({
          method: 'assistant_crm.assistant_crm.doctype.payout_summary_report.payout_summary_report.generate_report',
          args: { name: frm.doc.name },
          freeze: true,
          callback: () => frm.reload_doc(),
        });
      }).addClass('btn-primary');

      frm.add_custom_button('Download PDF', () => download_pdf(frm));
      frm.add_custom_button('Email Report', () => email_report(frm));
    }

    // Period field visibility
    toggle_period_fields(frm);

    // Render HTML and chart if present
    render_report_table(frm);
    render_report_chart(frm);

    // AI sidebar
    render_ai_sidebar(frm);
  },

  period_type(frm) {
    toggle_period_fields(frm);
  }
});

function toggle_period_fields(frm) {
  const isMonthly = (frm.doc.period_type || 'Monthly') === 'Monthly';
  frm.toggle_display('month', isMonthly);
  frm.toggle_display('year', isMonthly);
  frm.toggle_display('date_from', !isMonthly);
  frm.toggle_display('date_to', !isMonthly);
}

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
    let chart_holder = $(frm.fields_dict.report_html.$wrapper).parent().find('.payouts-chart-holder');
    if (!chart_holder.length) {
      chart_holder = $('<div class="payouts-chart-holder" style="margin-top:12px"></div>');
      $(frm.fields_dict.report_html.$wrapper).parent().append(chart_holder);
    }
    chart_holder.empty();
    new frappe.Chart(chart_holder.get(0), data);
  } catch (e) {
    // ignore chart errors
  }
}

function download_pdf(frm) {
  frappe.call({
    method: 'assistant_crm.assistant_crm.doctype.payout_summary_report.payout_summary_report.generate_pdf',
    args: { name: frm.doc.name },
    freeze: true,
    callback: (r) => {
      if (r.message && r.message.file_url) {
        const url = r.message.file_url;
        frappe.msgprint({
          title: 'PDF Generated',
          message: `Download: <a href="${url}" target="_blank">${r.message.file_name || 'Payout Summary PDF'}</a>`,
          indicator: 'green'
        });
      }
    }
  });
}

function email_report(frm) {
  frappe.prompt([
    { fieldname: 'extra_emails', label: 'Additional recipients (comma-separated)', fieldtype: 'Small Text', reqd: 0 }
  ], (values) => {
    let recipients = [];
    if (values.extra_emails) {
      recipients = values.extra_emails.split(',').map(s => s.trim()).filter(Boolean);
    }
    frappe.call({
      method: 'assistant_crm.assistant_crm.doctype.payout_summary_report.payout_summary_report.email_report',
      args: { name: frm.doc.name, recipients },
      freeze: true,
      callback: (r) => {
        if (r.message) {
          frappe.show_alert({ message: 'Email sent', indicator: 'green' });
        }
      }
    });
  }, 'Email Report', 'Send');
}

function render_ai_sidebar(frm) {
  if (!frm.sidebar || !frm.sidebar.add_user_action) return;
  if (frm.__payout_ai_rendered) return;
  frm.__payout_ai_rendered = true;

  const sidebar = $(
    '<div class="frappe-control"><div class="control-input-wrapper">' +
    '<div class="control-input flex"><input class="form-control" type="text" placeholder="This is WorkCom, how can I help?" />' +
    '<button class="btn btn-default" style="margin-left:6px">Ask</button></div>' +
    '<div class="help-box small text-muted" style="margin-top:6px">Uses current and recent reports for trend analysis and forecasting.</div>' +
    '<div class="ai-output" style="white-space:pre-wrap; margin-top:8px"></div>' +
    '</div></div>'
  );
  const ai_container = $('<div class="payout-ai-sidebar"></div>').append(sidebar);
  frm.sidebar.add_user_action(ai_container);

  const input = sidebar.find('input');
  const btn = sidebar.find('button');
  const out = sidebar.find('.ai-output');

  function ask() {
    const query = (input.val() || '').trim();
    if (!query) return;
    out.text('Thinking...');
    frappe.call({
      method: 'assistant_crm.assistant_crm.doctype.payout_summary_report.payout_summary_report.get_ai_insights',
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


