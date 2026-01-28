// Copyright (c) 2025, WCFCB and contributors
// For license information, please see license.txt

frappe.ui.form.on('Chat History', {
	refresh: function(frm) {
		// Add custom buttons or functionality here
		if (frm.doc.status === 'Error') {
			frm.add_custom_button(__('Retry'), function() {
				// Add retry functionality if needed
				frappe.msgprint(__('Retry functionality can be implemented here'));
			});
		}
		
		// Make certain fields read-only after creation
		if (!frm.is_new()) {
			frm.set_df_property('user', 'read_only', 1);
			frm.set_df_property('session_id', 'read_only', 1);
			frm.set_df_property('timestamp', 'read_only', 1);
		}
	},
	
	validate: function(frm) {
		// Add client-side validation if needed
		if (!frm.doc.message && !frm.doc.response) {
			frappe.msgprint(__('Either message or response must be provided'));
			frappe.validated = false;
		}
	}
});
