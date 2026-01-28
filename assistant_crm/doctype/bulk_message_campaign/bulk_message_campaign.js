// Copyright (c) 2025, WCFCB and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Message Campaign', {
    refresh: function(frm) {
        // Add custom buttons
        if (!frm.is_new()) {
            if (frm.doc.status === 'Draft') {
                frm.add_custom_button(__('Execute Campaign'), function() {
                    execute_campaign(frm);
                }, __('Actions'));
                
                frm.add_custom_button(__('Preview Recipients'), function() {
                    preview_recipients(frm);
                }, __('Actions'));
                
                frm.add_custom_button(__('Test Message'), function() {
                    test_message(frm);
                }, __('Actions'));
            }
            
            if (frm.doc.status === 'Running') {
                frm.add_custom_button(__('Cancel Campaign'), function() {
                    cancel_campaign(frm);
                }, __('Actions'));
            }
            
            frm.add_custom_button(__('View Statistics'), function() {
                view_statistics(frm);
            }, __('Reports'));
        }
        
        // Set indicators based on status
        set_status_indicator(frm);
        
        // Update recipient count
        if (frm.doc.stakeholder_types || frm.doc.dynamic_filters) {
            update_recipient_count(frm);
        }
    },
    
    send_immediately: function(frm) {
        if (frm.doc.send_immediately) {
            frm.set_value('scheduled_time', '');
        }
    },
    
    message_template: function(frm) {
        if (frm.doc.message_template) {
            // Load template content
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Message Template',
                    name: frm.doc.message_template
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('custom_message', r.message.content);
                    }
                }
            });
        }
    },
    
    stakeholder_types_on_form_rendered: function(frm) {
        update_recipient_count(frm);
    },
    
    dynamic_filters_on_form_rendered: function(frm) {
        update_recipient_count(frm);
    }
});

function set_status_indicator(frm) {
    let status = frm.doc.status;
    let indicator_html = '';
    
    switch(status) {
        case 'Draft':
            indicator_html = '<span class="indicator blue">Draft</span>';
            break;
        case 'Scheduled':
            indicator_html = '<span class="indicator orange">Scheduled</span>';
            break;
        case 'Running':
            indicator_html = '<span class="indicator yellow">Running</span>';
            break;
        case 'Completed':
            indicator_html = '<span class="indicator green">Completed</span>';
            break;
        case 'Failed':
            indicator_html = '<span class="indicator red">Failed</span>';
            break;
        case 'Cancelled':
            indicator_html = '<span class="indicator grey">Cancelled</span>';
            break;
    }
    
    if (frm.doc.total_recipients) {
        indicator_html += ` <span class="indicator blue" style="margin-left: 10px;">Recipients: ${frm.doc.total_recipients}</span>`;
    }
    
    if (frm.doc.delivery_rate && frm.doc.status === 'Completed') {
        indicator_html += ` <span class="indicator green" style="margin-left: 10px;">Delivery: ${frm.doc.delivery_rate}%</span>`;
    }
    
    frm.dashboard.set_headline_alert(
        '<div class="row">' +
        '<div class="col-xs-12">' +
        indicator_html +
        '</div>' +
        '</div>'
    );
}

function update_recipient_count(frm) {
    if (frm.is_new()) return;
    
    frappe.call({
        method: 'assistant_crm.api.bulk_messaging.calculate_recipients',
        args: {
            campaign_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frm.set_value('total_recipients', r.message.count);
                set_status_indicator(frm);
            }
        }
    });
}

function execute_campaign(frm) {
    frappe.confirm(
        __('Are you sure you want to execute this campaign? This will send messages to {0} recipients.', [frm.doc.total_recipients]),
        function() {
            frappe.call({
                method: 'assistant_crm.api.bulk_messaging.execute_campaign',
                args: {
                    campaign_name: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert(__('Campaign execution started successfully'));
                        frm.reload_doc();
                    } else {
                        frappe.msgprint(__('Failed to execute campaign: {0}', [r.message.error || 'Unknown error']));
                    }
                }
            });
        }
    );
}

function preview_recipients(frm) {
    frappe.call({
        method: 'assistant_crm.api.bulk_messaging.preview_recipients',
        args: {
            campaign_name: frm.doc.name,
            limit: 50
        },
        callback: function(r) {
            if (r.message) {
                let recipients = r.message.recipients;
                let html = '<table class="table table-bordered"><thead><tr><th>Name</th><th>Email</th><th>Mobile</th><th>Type</th></tr></thead><tbody>';
                
                recipients.forEach(function(recipient) {
                    html += `<tr>
                        <td>${recipient.first_name || ''} ${recipient.last_name || ''}</td>
                        <td>${recipient.email_id || ''}</td>
                        <td>${recipient.mobile_no || ''}</td>
                        <td>${recipient.custom_stakeholder_type || ''}</td>
                    </tr>`;
                });
                
                html += '</tbody></table>';
                
                if (r.message.total > 50) {
                    html += `<p><em>Showing first 50 of ${r.message.total} recipients</em></p>`;
                }
                
                frappe.msgprint({
                    title: __('Campaign Recipients Preview'),
                    message: html,
                    wide: true
                });
            }
        }
    });
}

function test_message(frm) {
    let test_email = prompt(__('Enter email address to send test message:'));
    if (test_email) {
        frappe.call({
            method: 'assistant_crm.api.bulk_messaging.send_test_message',
            args: {
                campaign_name: frm.doc.name,
                test_email: test_email
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    frappe.show_alert(__('Test message sent successfully'));
                } else {
                    frappe.msgprint(__('Failed to send test message: {0}', [r.message.error || 'Unknown error']));
                }
            }
        });
    }
}

function cancel_campaign(frm) {
    frappe.confirm(
        __('Are you sure you want to cancel this campaign?'),
        function() {
            frappe.call({
                method: 'assistant_crm.api.bulk_messaging.cancel_campaign',
                args: {
                    campaign_name: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert(__('Campaign cancelled successfully'));
                        frm.reload_doc();
                    } else {
                        frappe.msgprint(__('Failed to cancel campaign: {0}', [r.message.error || 'Unknown error']));
                    }
                }
            });
        }
    );
}

function view_statistics(frm) {
    frappe.call({
        method: 'assistant_crm.api.bulk_messaging.get_campaign_statistics',
        args: {
            campaign_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                let stats = r.message;
                let html = `
                    <div class="row">
                        <div class="col-md-6">
                            <h5>Campaign Statistics</h5>
                            <table class="table table-bordered">
                                <tr><td>Total Recipients</td><td>${stats.total_recipients}</td></tr>
                                <tr><td>Messages Sent</td><td>${stats.messages_sent}</td></tr>
                                <tr><td>Messages Delivered</td><td>${stats.messages_delivered}</td></tr>
                                <tr><td>Messages Failed</td><td>${stats.messages_failed}</td></tr>
                                <tr><td>Delivery Rate</td><td>${stats.delivery_rate}%</td></tr>
                                <tr><td>Status</td><td>${stats.status}</td></tr>
                            </table>
                        </div>
                    </div>
                `;
                
                frappe.msgprint({
                    title: __('Campaign Statistics'),
                    message: html,
                    wide: true
                });
            }
        }
    });
}
