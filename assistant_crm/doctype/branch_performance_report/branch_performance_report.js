frappe.ui.form.on('Branch Performance Report', {
  refresh(frm) {
    // Set default dates based on period type
    if (!frm.doc.date_from || !frm.doc.date_to) {
      frm.trigger('set_period_defaults');
    }

    if (!frm.is_new()) {
      frm.add_custom_button('Generate', () => {
        frm.call('run_generation').then(() => frm.reload_doc());
      }).addClass('btn-primary');

      frm.add_custom_button('Download Excel', () => {
        frappe.call({
          method: 'assistant_crm.assistant_crm.doctype.branch_performance_report.branch_performance_report.generate_excel_file',
          args: { name: frm.doc.name },
          freeze: true,
          callback: (r) => {
            const url = r && r.message && r.message.file_url;
            if (url) window.open(url, '_blank');
          }
        });
      });

      frm.add_custom_button('Download PDF', () => {
        frappe.call({
          method: 'assistant_crm.assistant_crm.doctype.branch_performance_report.branch_performance_report.generate_pdf_file',
          args: { name: frm.doc.name },
          freeze: true,
          callback: (r) => {
            const url = r && r.message && r.message.file_url;
            if (url) window.open(url, '_blank');
          }
        });
      });

      // Add View Tickets buttons (open in new tab)
      if (frm.doc.generated_at) {
        add_view_tickets_buttons(frm);
      }
    }

    render_charts(frm);
    render_ai_sidebar(frm);
  },

  set_period_defaults(frm) {
    const today = frappe.datetime.get_today();
    if (frm.doc.period_type === 'Quarterly') {
      // Last full quarter as a simple default: previous 90 days
      frm.set_value('date_to', today);
      frm.set_value('date_from', frappe.datetime.add_days(today, -89));
    } else if (frm.doc.period_type === 'Monthly') {
      const firstDay = frappe.datetime.month_start();
      const lastDay = frappe.datetime.month_end();
      frm.set_value('date_from', firstDay);
      frm.set_value('date_to', lastDay);
    } else {
      // Custom: last 30 days
      frm.set_value('date_to', today);
      frm.set_value('date_from', frappe.datetime.add_days(today, -29));
    }
  }
});

function render_charts(frm) {
  const charts = [
    { field: 'branch_overview_chart_json', title: 'Branch Overview' },
    { field: 'sla_branch_chart_json', title: 'SLA by Branch' },
    { field: 'regional_comparison_chart_json', title: 'Regional Comparison' },
    { field: 'trend_chart_json', title: 'Trends' }
  ];

  const wrapper = frm.get_field('report_html') && frm.get_field('report_html').$wrapper;
  if (!wrapper) return;

  // Clear existing chart containers to allow re-rendering
  wrapper.find('.br-chart-container').remove();

  charts.forEach(cfg => {
    try {
      const raw = frm.doc[cfg.field];
      if (!raw) return;
      const data = JSON.parse(raw);
      if (!data || !data.data) return; // Skip empty chart data

      const id = 'chart_' + cfg.field + '_' + frm.doc.name;
      wrapper.append(`<div class="br-chart-container" style="margin-top:16px"><h5>${cfg.title}</h5><div id="${id}" style="height:250px"></div></div>`);
      new frappe.Chart('#' + id, data);
    } catch (e) {
      console.log('Chart render error:', cfg.field, e);
    }
  });
}

function render_ai_sidebar(frm) {
  if (frm.custom_ai_sidebar_rendered) return;

  const sidebar = $(
    '<div class="frappe-control"><div class="control-input-wrapper">' +
    '<div class="control-input flex"><input class="form-control" type="text" ' +
    'placeholder="This is Antoine, how can I help with branch performance?" />' +
    '<button class="btn btn-default" style="margin-left:6px">Ask</button></div>' +
    '<div class="help-box small text-muted" style="margin-top:6px">' +
    'Uses current and recent branch performance reports for trend and SLA risk analysis.' +
    '</div><div class="ai-output" style="white-space:pre-wrap; margin-top:8px"></div>' +
    '</div></div>'
  );
  const ai_container = $('<div class="branch-ai-sidebar"></div>').append(sidebar);

  if (frm.sidebar && frm.sidebar.add_user_action) {
    frm.sidebar.add_user_action(ai_container);
  } else if (frm.page && frm.page.sidebar) {
    $(frm.page.sidebar).append(ai_container);
  }

  const input = sidebar.find('input');
  const btn = sidebar.find('button');
  const out = sidebar.find('.ai-output');

  const ask = () => {
    const query = (input.val() || '').trim();
    if (!query) return;
    out.text('Thinking...');
    frappe.call({
      method: 'assistant_crm.assistant_crm.doctype.branch_performance_report.branch_performance_report.get_ai_insights',
      args: { name: frm.doc.name, query },
      callback: (r) => {
        out.text(r && r.message && r.message.insights ? r.message.insights : 'No answer');
      },
      error: () => out.text('Error retrieving insights.'),
    });
  };

  btn.on('click', ask);
  input.on('keypress', (e) => { if (e.which === 13) ask(); });

  frm.custom_ai_sidebar_rendered = true;
}

function add_view_tickets_buttons(frm) {
  const dateFrom = frm.doc.date_from;
  const dateTo = frm.doc.date_to;
  const branch = (frm.doc.branch_filter || '').trim();

  // Build filter strings for URL
  const dateFilter = `["${dateFrom}","${dateTo}","[]"]`;

  // View Issues button
  frm.add_custom_button(__('View Issues'), () => {
    let filters = { creation: ['between', [dateFrom, dateTo]] };
    if (branch) filters.custom_branch = ['like', `%${branch}%`];
    const url = `/app/issue?${$.param(filters)}`;
    window.open(url, '_blank');
  }, __('View Tickets'));

  // View Claims button
  frm.add_custom_button(__('View Claims'), () => {
    let filters = { submitted_date: ['between', [dateFrom, dateTo]] };
    if (branch) filters.branch = ['like', `%${branch}%`];
    const url = `/app/claim?${$.param(filters)}`;
    window.open(url, '_blank');
  }, __('View Tickets'));

  // View Conversations button
  frm.add_custom_button(__('View Conversations'), () => {
    let filters = { creation: ['between', [dateFrom, dateTo]] };
    const channel = frm.doc.channel_filter;
    if (channel && channel !== 'All') filters.platform = channel;
    const url = `/app/unified-inbox-conversation?${$.param(filters)}`;
    window.open(url, '_blank');
  }, __('View Tickets'));
}

