frappe.ui.form.on('Unified Inbox Conversation', {
    refresh: function (frm) {
        frm.trigger('update_sla_timer');
    },

    update_sla_timer: function (frm) {
        if (!frm.doc.resolution_sla_expiry || ['Resolved', 'Closed'].includes(frm.doc.status)) {
            frm.dashboard.clear_headline();
            return;
        }

        const update_countdown = () => {
            if (['Resolved', 'Closed'].includes(frm.doc.status)) {
                frm.dashboard.clear_headline();
                return;
            }

            const expiry = moment(frm.doc.resolution_sla_expiry);
            const now = moment();
            const diff = expiry.diff(now);

            if (diff <= 0) {
                frm.dashboard.set_headline_alert(
                    '<span class="indicator red"><b>SLA EXCEEDED</b></span>',
                    'red'
                );
                return;
            }

            const duration = moment.duration(diff);
            const hours = Math.floor(duration.asHours());
            const minutes = duration.minutes();
            const seconds = duration.seconds();

            const time_str = `${hours}h ${minutes}m ${seconds}s`;
            const color = hours < 2 ? 'red' : (hours < 12 ? 'orange' : 'blue');

            frm.dashboard.set_headline_alert(
                `<span class="indicator ${color}">Time to Resolve: <b>${time_str}</b></span>`,
                color
            );

            // Re-run every second if the form is still open
            if (cur_frm && cur_frm.doc.name === frm.doc.name) {
                setTimeout(update_countdown, 1000);
            }
        };

        update_countdown();
    }
});
