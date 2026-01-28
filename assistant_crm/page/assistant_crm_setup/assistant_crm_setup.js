frappe.pages['assistant_crm_setup'] = {
  on_page_load: function (wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: 'Assistant CRM Setup',
      single_column: true
    });

    const $body = $(wrapper).find('.layout-main-section');
    $body.html(`
      <div class="assistant-setup">
        <div class="form-grid" style="max-width: 920px">
          <div class="frappe-control" style="margin-bottom: 10px">
            <label class="control-label">Target DocType</label>
            <select class="form-control" id="target_dt"></select>
          </div>
          <div class="frappe-control" style="margin-bottom: 10px">
            <label class="control-label">Candidate DocTypes (one per line)</label>
            <textarea class="form-control" id="candidates" rows="3" placeholder="Issue\nTicket\nTask"></textarea>
          </div>
          <div class="frappe-control" style="margin-bottom: 6px">
            <label class="control-label">Mapping Rows</label>
            <small class="text-muted">One per line: fieldname | fieldtype | transformation_rule (optional). Example: custom_platform_source | Select | Options:WhatsApp|Facebook|Instagram</small>
            <textarea class="form-control" id="rows" rows="6" placeholder="custom_conversation_id | Data\ncustom_platform_source | Select | Options:WhatsApp|Facebook|Instagram\ncustom_customer_phone | Data\ncustom_customer_nrc | Data"></textarea>
          </div>
          <div class="form-check" style="margin: 8px 0 16px 2px">
            <input class="form-check-input" type="checkbox" id="enabled" checked>
            <label class="form-check-label" for="enabled">Enable profile</label>
          </div>
          <div>
            <button class="btn btn-primary" id="save_profile">Save Profile</button>
            <button class="btn btn-default" id="apply_profile" style="margin-left: 8px">Apply Profile</button>
            <button class="btn btn-default" id="apply_all" style="margin-left: 8px">Apply All Enabled</button>
          </div>
          <div id="result" style="margin-top: 16px"></div>
        </div>
      </div>
    `);

    let last_profile_name = null;

    function load_doctypes() {
      frappe.call({
        method: 'assistant_crm.assistant_crm.page.assistant_crm_setup.assistant_crm_setup.get_doctypes',
        callback: (r) => {
          const list = (r.message || []).sort();
          const $sel = $body.find('#target_dt');
          $sel.empty();
          list.forEach(dt => $sel.append(`<option value="${frappe.utils.escape_html(dt)}">${frappe.utils.escape_html(dt)}</option>`));
          // Pre-select common doctypes if present
          const preferred = ['Issue', 'Ticket', 'Communication'];
          for (const p of preferred) {
            if (list.includes(p)) { $sel.val(p); break; }
          }
        }
      });
    }

    function parse_rows(text) {
      const rows = [];
      (text || '').split(/\n+/).forEach(line => {
        const t = line.trim();
        if (!t) return;
        const parts = t.split('|').map(x => x.trim());
        const frappe_field = parts[0] || '';
        const field_type = parts[1] || 'Data';
        const transformation_rule = parts[2] || '';
        if (frappe_field) rows.push({ frappe_field, field_type, is_required: 0, transformation_rule });
      });
      return rows;
    }

    $body.on('click', '#save_profile', function () {
      const payload = {
        title: `Setup Profile - ${$body.find('#target_dt').val()}`,
        target_doctype: $body.find('#target_dt').val(),
        candidate_doctypes: $body.find('#candidates').val(),
        enabled: $body.find('#enabled').is(':checked') ? 1 : 0,
        rows: parse_rows($body.find('#rows').val())
      };
      frappe.call({
        method: 'assistant_crm.assistant_crm.page.assistant_crm_setup.assistant_crm_setup.create_profile',
        args: payload,
        freeze: true,
        callback: (r) => {
          if (r.message && r.message.name) {
            last_profile_name = r.message.name;
            frappe.show_alert({message: __('Profile saved: {0}', [last_profile_name]), indicator: 'green'});
          } else {
            frappe.msgprint(__('Failed to save profile'));
          }
        }
      });
    });

    $body.on('click', '#apply_profile', function () {
      if (!last_profile_name) {
        frappe.msgprint(__('Please save a profile first.'));
        return;
      }
      frappe.call({
        method: 'assistant_crm.assistant_crm.page.assistant_crm_setup.assistant_crm_setup.apply_profile',
        args: { name: last_profile_name },
        freeze: true,
        callback: (r) => {
          const res = r.message || {};
          $body.find('#result').html(
            `<pre style="white-space: pre-wrap">${frappe.utils.escape_html(JSON.stringify(res, null, 2))}</pre>`
          );
          frappe.show_alert({message: __('Applied to {0}', [res.resolved_doctype || 'DocType']), indicator: 'green'});
        }
      });
    });

    $body.on('click', '#apply_all', function () {
      frappe.call({
        method: 'assistant_crm.assistant_crm.page.assistant_crm_setup.assistant_crm_setup.apply_all',
        freeze: true,
        callback: (r) => {
          const res = r.message || {};
          $body.find('#result').html(
            `<pre style="white-space: pre-wrap">${frappe.utils.escape_html(JSON.stringify(res, null, 2))}</pre>`
          );
        }
      });
    });

    load_doctypes();
  }
};

