frappe.ui.form.on('Social Media Settings', {
  refresh: function(frm) {
    // Auto-populate the redirect URI with a sensible default if it's empty
    if (!frm.doc.youtube_redirect_uri) {
      const defaultUri = window.location.origin + '/api/method/assistant_crm.api.social_media_ports.google_oauth_callback';
      frm.set_value('youtube_redirect_uri', defaultUri);
    }

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
    if (frm.doc.youtube_enabled || frm.doc.youtube_client_id) {
      frm.add_custom_button('Authorize YouTube API', function() {
        const clientId = frm.doc.youtube_client_id ? frm.doc.youtube_client_id.trim() : '';
        if (!clientId) {
          frappe.msgprint({ title: 'Missing Client ID', message: 'Please enter the YouTube OAuth Client ID before authorizing.', indicator: 'orange' });
          return;
        }

        // Use the saved redirect URI field, falling back to the current origin
        const redirectUri = (frm.doc.youtube_redirect_uri || '').trim() ||
          (window.location.origin + '/api/method/assistant_crm.api.social_media_ports.google_oauth_callback');

        const scope = 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl';
        const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=${encodeURIComponent(scope)}&access_type=offline&prompt=consent`;

        window.open(authUrl, '_blank');
      }, __('YouTube'));
    }
  }
});
