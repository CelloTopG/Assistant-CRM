frappe.ui.form.on('Assistant CRM SMS Log', {
    refresh: function (frm) {
        if (frm.doc.status === 'Sent') {
            frm.set_df_property('status', 'description', 'Successfully delivered to gateway');
        } else if (frm.doc.status === 'Failed') {
            frm.set_df_property('status', 'description', frm.doc.error_message || 'Unknown failure');
        }
    }
});

frappe.ui.form.on('Assistant CRM SMS Log', {
    onload: function (frm) {
        frm.set_indicator_formatter('status', function (doc) {
            if (doc.status === 'Sent') return 'green';
            if (doc.status === 'Failed') return 'red';
            return 'orange';
        });
    }
});
