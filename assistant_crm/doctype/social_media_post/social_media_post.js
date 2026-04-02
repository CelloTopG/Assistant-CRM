// Copyright (c) 2026, WCFCB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Social Media Post", {

    refresh(frm) {
        frm.trigger("toggle_schedule_field");
        frm.trigger("add_action_buttons");
    },

    send_immediately(frm) {
        frm.trigger("toggle_schedule_field");
    },

    toggle_schedule_field(frm) {
        frm.toggle_reqd("scheduled_datetime", !frm.doc.send_immediately);
    },

    add_action_buttons(frm) {
        // Only show action buttons on saved, non-terminal records
        const actionable = ["Draft", "Scheduled", "Failed", "Partially Published"];
        if (frm.is_new() || !actionable.includes(frm.doc.status)) return;

        if (frm.doc.status === "Publishing") return;

        frm.add_custom_button(__("Publish Now"), () => {
            frappe.confirm(
                __("Publish this post to all selected platforms right now?"),
                () => {
                    frappe.call({
                        method: "assistant_crm.api.social_media_publisher.publish_now",
                        args: { post_name: frm.doc.name },
                        freeze: true,
                        freeze_message: __("Publishing..."),
                        callback(r) {
                            if (r.message && r.message.success) {
                                frappe.show_alert({
                                    message: __("Publishing started. Refresh in a moment to see results."),
                                    indicator: "green"
                                });
                                frm.reload_doc();
                            } else {
                                frappe.msgprint({
                                    title: __("Publish Failed"),
                                    message: (r.message && r.message.error) || __("An unexpected error occurred."),
                                    indicator: "red"
                                });
                            }
                        }
                    });
                }
            );
        }, __("Actions"));

        // Allow re-scheduling a failed post
        if (["Failed", "Partially Published"].includes(frm.doc.status)) {
            frm.add_custom_button(__("Reset to Draft"), () => {
                frappe.call({
                    method: "frappe.client.set_value",
                    args: {
                        doctype: "Social Media Post",
                        name: frm.doc.name,
                        fieldname: "status",
                        value: "Draft"
                    },
                    callback() {
                        frm.reload_doc();
                    }
                });
            }, __("Actions"));
        }
    }
});
