frappe.ui.form.on('Survey Feedback Report', {
  refresh: function(frm) {
    if (!frm.is_new()) {
      frm.add_custom_button('Generate Report', () => run_generate(frm), 'Actions');
      frm.add_custom_button('Download PDF', () => run_pdf(frm), 'Actions');
      frm.add_custom_button('Email Report', () => run_email(frm), 'Actions');
    } else {
      set_default_dates(frm);
      frm.add_custom_button('Generate Report', () => run_generate(frm), 'Actions');
    }

    // Render charts if data present
    setTimeout(() => render_all_charts(frm), 300);
    // Bind drilldown links
    bind_drilldowns(frm);
    // Render AI sidebar
    setTimeout(() => render_ai_sidebar(frm), 300);
  },

  period_type: function(frm) {
    set_default_dates(frm);
  }
});

function set_default_dates(frm) {
  if (!frm.doc.period_type || frm.doc.period_type === 'Monthly') {
    const now = frappe.datetime.now_date();
    const firstThisMonth = frappe.datetime.month_start(now);
    const lastPrevMonth = frappe.datetime.add_days(firstThisMonth, -1);
    frm.set_value('date_to', lastPrevMonth);
    frm.set_value('date_from', frappe.datetime.month_start(lastPrevMonth));
  } else if (frm.doc.period_type === 'Quarterly') {
    const now = frappe.datetime.now_date();
    const m = parseInt(now.split('-')[1], 10);
    const y = parseInt(now.split('-')[0], 10);
    const q = Math.floor((m - 1) / 3); // current quarter index 0..3
    const prev_q = (q + 3) % 4;
    const year = q > 0 ? y : y - 1;
    const start_month = prev_q * 3 + 1;
    const start = `${year}-${('0' + start_month).slice(-2)}-01`;
    const end = frappe.datetime.add_days(frappe.datetime.add_months(start, 3), -1);
    frm.set_value('date_from', start);
    frm.set_value('date_to', end);
  }
}

function run_generate(frm) {
  frm.call({ method: 'run_generation', args: { name: frm.doc.name } }).then(() => {
    frm.reload_doc();
    frappe.show_alert({message: 'Survey Feedback Report generated', indicator: 'green'});
    render_all_charts(frm);
  });
}

function run_pdf(frm) {
  frm.call({ method: 'generate_pdf', args: { name: frm.doc.name } });
}

function run_email(frm) {
  frm.call({ method: 'email_report', args: { name: frm.doc.name } }).then(() => {
    frappe.show_alert({message: 'Report emailed', indicator: 'green'});
  });
}

function render_all_charts(frm) {
  try { render_chart(frm, 'survey_chart_json', 'survey_chart'); } catch(e) {}
  try { render_chart(frm, 'sentiment_chart_json', 'sentiment_chart'); } catch(e) {}
  try { render_chart(frm, 'channel_chart_json', 'channel_chart'); } catch(e) {}
  try { render_chart(frm, 'delivery_chart_json', 'delivery_chart'); } catch(e) {}
  try { render_chart(frm, 'platform_response_rate_json', 'platform_rr_chart'); } catch(e) {}
  try { render_chart(frm, 'trend_chart_json', 'trend_chart'); } catch(e) {}
}

function render_chart(frm, fieldname, wrapper_id) {
  const json = frm.doc[fieldname];
  if (!json) return;
  const data = JSON.parse(json);
  let el = frm.fields_dict.report_html && frm.fields_dict.report_html.$wrapper.find(`#${wrapper_id}`);
  if (!el || !el.length) {
    // create simple container under HTML field
    const c = frm.fields_dict.report_html.$wrapper;
    c.append(`<div class="mt-3"><div id="${wrapper_id}"></div></div>`);
    el = frm.fields_dict.report_html.$wrapper.find(`#${wrapper_id}`);
  }
  el.empty();
  new frappe.Chart(el[0], data);
}

function render_ai_sidebar(frm) {
  const id = 'sf_ai_sidebar';
  if (document.getElementById(id)) return;

  const sidebar = $(`
    <div id="${id}" class="sf-ai p-3" style="border-top:1px solid #eee;">
      <div class="small text-muted">AI Insights</div>
      <div class="frappe-control"><div class="control-input-wrapper">
        <div class="control-input flex">
          <input class="form-control" type="text" placeholder="This is Antoine, how can I help?" />
          <button class="btn btn-default" style="margin-left:6px">Ask</button>
        </div>
        <div class="help-box small text-muted" style="margin-top:6px">
          Uses current and recent reports for trend analysis and forecasting.
        </div>
        <div class="ai-output" style="white-space:pre-wrap; margin-top:8px"></div>
      </div></div>
    </div>`);

  const ai_container = $('<div class="survey-ai-sidebar"></div>').append(sidebar);
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
    method: 'assistant_crm.assistant_crm.doctype.survey_feedback_report.survey_feedback_report.get_ai_insights',
    args: { name: frm.doc.name, query },
    callback: (r) => {
      out.text(r && r.message && r.message.insights ? r.message.insights : 'No insights returned.');
    },
    error: () => out.text('Error retrieving insights.'),
  });
}

function bind_drilldowns(frm) {
  const html = frm.fields_dict.report_html && frm.fields_dict.report_html.$wrapper;
  if (!html || !html.length) return;
  html.off('click.sf-route').on('click.sf-route', 'a.sf-route', function(ev) {
    ev.preventDefault();
    const dt = this.dataset.doctype;
    let filters = {};
    try { filters = JSON.parse(this.dataset.filters || '{}'); } catch(e) {}
    frappe.route_options = filters;
    frappe.set_route('List', dt);
  });
}

