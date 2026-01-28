// Copyright (c) 2025, WCFCB and contributors
// For license information, please see license.txt

frappe.ui.form.on('Assistant CRM Settings', {
	refresh: function(frm) {
		// Add custom buttons for settings management
		if (!frm.is_new()) {
			frm.add_custom_button(__('Test Connection'), function() {
				// Test API connection functionality
				frappe.call({
					method: 'assistant_crm.doctype.assistant_crm_settings.assistant_crm_settings.test_connection',
					args: {
						doc: frm.doc
					},
					callback: function(r) {
						if (r.message && r.message.success) {
							frappe.msgprint(__('Connection test successful!'));
						} else {
							frappe.msgprint(__('Connection test failed. Please check your settings.'));
						}
					}
				});
			});
			
			frm.add_custom_button(__('Reset to Defaults'), function() {
				frappe.confirm(__('Are you sure you want to reset all settings to default values?'), function() {
					frappe.call({
						method: 'assistant_crm.doctype.assistant_crm_settings.assistant_crm_settings.reset_to_defaults',
						args: {
							doc: frm.doc
						},
						callback: function(r) {
							if (r.message && r.message.success) {
								frm.reload_doc();
								frappe.msgprint(__('Settings reset to defaults successfully!'));
							}
						}
					});
				});
			});
		}
		
		// Make certain system fields read-only
		if (!frm.is_new()) {
			frm.set_df_property('creation', 'read_only', 1);
			frm.set_df_property('modified', 'read_only', 1);
		}
	},
	
	validate: function(frm) {
		// Client-side validation for settings
		if (frm.doc.api_key && frm.doc.api_key.length < 10) {
			frappe.msgprint(__('API Key must be at least 10 characters long'));
			frappe.validated = false;
		}
		
		if (frm.doc.webhook_url && !frm.doc.webhook_url.startsWith('http')) {
			frappe.msgprint(__('Webhook URL must start with http:// or https://'));
			frappe.validated = false;
		}
	},
	
	api_key: function(frm) {
		// Mask API key for security
		if (frm.doc.api_key && frm.doc.api_key.length > 4) {
			let masked = frm.doc.api_key.substring(0, 4) + '*'.repeat(frm.doc.api_key.length - 4);
			frm.set_value('api_key_display', masked);
		}
	}
});
