// Copyright (c) 2026, WCFCB and contributors
// For license information, please see license.txt

frappe.ui.form.on("Social Media Post", {

    refresh(frm) {
        frm.trigger("toggle_schedule_field");
        frm.trigger("add_action_buttons");

        // If the job is already running when the form loads, keep polling
        if (frm.doc.status === "Publishing") {
            frm.trigger("start_status_poll");
        }
    },

    after_save(frm) {
        // After saving with Publish Immediately, the background job takes a moment.
        // Poll until the status leaves Draft/Publishing so the form shows the real outcome.
        if (frm.doc.send_immediately && ["Draft", "Publishing"].includes(frm.doc.status)) {
            frm.trigger("start_status_poll");
        }
    },

    start_status_poll(frm) {
        // Avoid duplicate intervals
        if (frm._status_poll_interval) return;

        frappe.show_alert({ message: __("Publishing in progress…"), indicator: "blue" });

        let attempts = 0;
        frm._status_poll_interval = setInterval(() => {
            attempts++;
            frappe.db.get_value("Social Media Post", frm.doc.name, "status").then(r => {
                const status = r.message && r.message.status;
                const done = status && !["Draft", "Publishing"].includes(status);
                if (done || attempts >= 30) {
                    clearInterval(frm._status_poll_interval);
                    frm._status_poll_interval = null;
                    frm.reload_doc();
                }
            });
        }, 3000);
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
