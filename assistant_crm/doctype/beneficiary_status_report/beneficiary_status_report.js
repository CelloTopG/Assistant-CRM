frappe.ui.form.on('Beneficiary Status Report', {
  refresh: function(frm) {
    // Generate button
    if (!frm.is_new()) {
      frm.add_custom_button('Generate', () => frm.call('run_generation').then(() => frm.reload_doc()));
      frm.add_custom_button('Download Excel', () => frm.call('generate_excel'));
      frm.add_custom_button('Email Report', () => frm.call('email_report'));
    }

    // Render charts if present
    const charts = [
      { field: 'status_chart_json', title: 'Status Distribution' },
      { field: 'province_chart_json', title: 'Province Breakdown' },
      { field: 'benefit_type_chart_json', title: 'Benefit Type Breakdown' },
      { field: 'trend_chart_json', title: 'Trend' }
    ];

    charts.forEach(cfg => {
      try {
        const raw = frm.doc[cfg.field];
        if (!raw) return;
        const data = JSON.parse(raw);
        const wrapper = frm.get_field('report_html').$wrapper;
        const id = 'chart_' + cfg.field;
        if (!document.getElementById(id)) {
          wrapper.append(`<div style="margin-top:10px"><h5>${cfg.title}</h5><div id="${id}"></div></div>`);
        }
        new frappe.Chart('#' + id, data);
      } catch (e) {
        // ignore chart errors gracefully
      }
    });

    // Antoine AI sidebar (match SLA/Complaints positioning)
    if (!frm.custom_ai_sidebar_rendered && frm.sidebar && frm.sidebar.add_user_action) {
      const wrapper = $(
        '<div class="frappe-control"><div class="control-input-wrapper">' +
        '<div class="control-input flex"><input class="form-control" type="text" ' +
        'placeholder="This is Antoine, how can I help with beneficiary status?" />' +
        '<button class="btn btn-default" style="margin-left:6px">Ask</button></div>' +
        '<div class="help-box small text-muted" style="margin-top:6px">Uses current and historical beneficiary reports for trend and risk analysis.</div>' +
        '<div class="ai-output" style="white-space:pre-wrap; margin-top:8px"></div>' +
        '</div></div>'
      );

      const input = wrapper.find('input');
      const out = wrapper.find('.ai-output');
      const btn = wrapper.find('button');

      function ask() {
        const query = (input.val() || '').trim();
        if (!query) return;
        out.text('Thinking...');
        frappe.call({
          method: 'assistant_crm.assistant_crm.doctype.beneficiary_status_report.beneficiary_status_report.get_ai_insights',
          args: { name: frm.doc.name, query },
        }).then(r => {
          const ans = (r && r.message && r.message.insights) || 'No answer';
          out.text(ans);
        });
      }

      btn.on('click', ask);
      input.on('keydown', (e) => { if (e.key === 'Enter') ask(); });

      frm.sidebar.add_user_action(wrapper);
      frm.custom_ai_sidebar_rendered = true;
    }
  }
});

