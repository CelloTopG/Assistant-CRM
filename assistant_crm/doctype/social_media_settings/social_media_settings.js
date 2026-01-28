frappe.ui.form.on('Social Media Settings', {
  refresh: function(frm) {
    if (frm.doc.facebook_enabled) {
      frm.add_custom_button('Exchange FB Long-Lived Token', function() {
        frappe.prompt([
          {
            fieldname: 'short_lived_token',
            label: 'Short-Lived User Access Token',
            fieldtype: 'Password',
            description: 'Optional. If left blank, the value from Facebook Page Access Token will be used.'
          }
        ], function(values) {
          frappe.call({
            method: 'assistant_crm.assistant_crm.doctype.social_media_settings.social_media_settings.exchange_facebook_long_lived_token',
            args: { short_lived_token: values.short_lived_token || null },
            freeze: true,
            freeze_message: 'Exchanging token with Facebook Graph API...'
          }).then(r => {
            const res = r && r.message ? r.message : r;
            if (res && res.success) {
              frappe.show_alert({ message: res.message || 'Success', indicator: 'green' });
              frm.reload_doc();
            } else {
              frappe.msgprint({ title: 'Token Exchange Failed', message: (res && res.message) || 'Unknown error', indicator: 'red' });
            }
          }).catch(e => {
            frappe.msgprint({ title: 'Error', message: e.message || e, indicator: 'red' });
          });
        }, 'Exchange Long-Lived Token (Facebook)', 'Exchange');
      }, __('Facebook'));
    }

    if (frm.doc.instagram_enabled) {
      frm.add_custom_button('Exchange IG Long-Lived Token', function() {
        frappe.prompt([
          {
            fieldname: 'short_lived_token',
            label: 'Short-Lived User Access Token',
            fieldtype: 'Password',
            description: 'Optional. If left blank, the system will use configured tokens.'
          }
        ], function(values) {
          frappe.call({
            method: 'assistant_crm.assistant_crm.doctype.social_media_settings.social_media_settings.exchange_instagram_long_lived_token',
            args: { short_lived_token: values.short_lived_token || null },
            freeze: true,
            freeze_message: 'Exchanging token with Facebook Graph API (Instagram)...'
          }).then(r => {
            const res = r && r.message ? r.message : r;
            if (res && res.success) {
              frappe.show_alert({ message: res.message || 'Success', indicator: 'green' });
              frm.reload_doc();
            } else {
              frappe.msgprint({ title: 'Token Exchange Failed', message: (res && res.message) || 'Unknown error', indicator: 'red' });
            }
          }).catch(e => {
            frappe.msgprint({ title: 'Error', message: e.message || e, indicator: 'red' });
          });
        }, 'Exchange Long-Lived Token (Instagram)', 'Exchange');
      }, __('Instagram'));
    }
  }
});

