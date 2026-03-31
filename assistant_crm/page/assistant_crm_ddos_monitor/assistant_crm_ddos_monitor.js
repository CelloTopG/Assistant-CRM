frappe.pages['assistant-crm-ddos-monitor'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Assistant CRM DDoS Monitor',
        single_column: true
    });

    page.set_primary_action('Refresh', function() {
        document.getElementById('ddos-monitor-iframe').contentWindow.location.reload();
    });

    page.main.html(`
        <div class="ddos-monitor-inner" style="height: calc(100vh - 120px);">
            <iframe id="ddos-monitor-iframe" src="/ddos_monitor" style="width: 100%; height: 100%; border: 0;" sandbox="allow-same-origin allow-scripts allow-forms allow-popups"></iframe>
        </div>
    `);
};