frappe.ui.form.on('Unified Inbox Conversation', {
    refresh: function (frm) {
        frm.trigger('update_sla_timer');

        // Add Export Menu
        frm.add_custom_button(__('PDF'), () => frm.trigger('export_conv', 'pdf'), __('Export'));
        frm.add_custom_button(__('Excel'), () => frm.trigger('export_conv', 'excel'), __('Export'));
        frm.add_custom_button(__('Word'), () => frm.trigger('export_conv', 'word'), __('Export'));
    },

    export_conv: function (frm, format) {
        // Use the exact same endpoint as Reports for 100% compatibility
        const report_name = "Conversation Export";
        const filters = JSON.stringify({ "conversation_name": frm.doc.name });
        let file_format = "";

        if (format === 'pdf') {
            file_format = "PDF";
        } else if (format === 'excel') {
            file_format = "Excel";
        } else if (format === 'word') {
            // Word is not a standard report export format in Frappe, 
            // but we can still use our custom API for it if it works, 
            // or just tell them to use PDF/Excel if it keeps failing.
            // For now, let's try to stick to native for PDF/Excel.
            const url = `/api/method/assistant_crm.api.unified_inbox_api.export_conversation?conversation_name=${encodeURIComponent(frm.doc.name)}&format=${format}`;
            window.location.href = url;
            return;
        }

        const url = `/api/method/frappe.desk.query_report.export_query?report_name=${encodeURIComponent(report_name)}&filters=${encodeURIComponent(filters)}&file_format=${file_format}`;
        window.location.href = url;
    },

    update_sla_timer: function (frm) {
        // Clear any old interval on this form object
        if (frm.sla_timer_timer) {
            clearInterval(frm.sla_timer_timer);
        }

        if (!frm.doc.resolution_sla_expiry || ['Resolved', 'Closed'].includes(frm.doc.status)) {
            frm.dashboard.clear_headline();
            return;
        }

        const timer_id = `sla-timer-container`;

        const update_ui = () => {
            if (!cur_frm || cur_frm.doc.name !== frm.doc.name || ['Resolved', 'Closed'].includes(frm.doc.status)) {
                clearInterval(frm.sla_timer_timer);
                return;
            }

            const expiry = moment(frm.doc.resolution_sla_expiry);
            const now = moment();
            const diff = expiry.diff(now);

            let text, color;
            if (diff <= 0) {
                text = '<b>SLA EXCEEDED</b>';
                color = 'red';
            } else {
                const duration = moment.duration(diff);
                const hours = Math.floor(duration.asHours());
                const minutes = duration.minutes();
                const seconds = duration.seconds();
                text = `Time to Resolve: <b>${hours}h ${minutes}m ${seconds}s</b>`;
                color = hours < 2 ? 'red' : (hours < 12 ? 'orange' : 'blue');
            }

            let $timer = $(`#${timer_id}`);
            if (!$timer.length) {
                // Completely clear and set once to avoid the "multi-row" look
                frm.dashboard.clear_headline();
                frm.dashboard.set_headline_alert(
                    `<span id="${timer_id}" class="indicator ${color}">${text}</span>`,
                    color
                );
            } else {
                // Update existing text and color for smooth transition
                $timer.attr('class', `indicator ${color}`).html(text);
                // Also update the Frappe alert wrapper class if possible
                $timer.closest('.alert').css('border-left', `4px solid ${color}`);
            }

            if (diff <= 0) {
                clearInterval(frm.sla_timer_timer);
            }
        };

        // Run immediately and then stay active
        update_ui();
        frm.sla_timer_timer = setInterval(update_ui, 1000);
    }
});
