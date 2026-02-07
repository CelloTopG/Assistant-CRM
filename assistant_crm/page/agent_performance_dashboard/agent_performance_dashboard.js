// Agent Performance Dashboard - Professional Enterprise UI
// Real-time agent performance monitoring with live updates

frappe.pages['agent-performance-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Agent Performance Dashboard',
        single_column: true
    });

    // Initialize dashboard
    new AgentPerformanceDashboard(page);
};

class AgentPerformanceDashboard {
    constructor(page) {
        this.page = page;
        this.refreshInterval = null;
        this.charts = {};
        
        // Default date range (last 30 days)
        this.dateFrom = frappe.datetime.add_days(frappe.datetime.get_today(), -30);
        this.dateTo = frappe.datetime.get_today();
        
        this.init();
    }

    init() {
        this.renderLayout();
        this.bindEvents();
        this.loadDashboard();
        this.startLiveUpdates();
    }

    renderLayout() {
        this.page.main.html(`
            <div class="agent-dashboard-container">
                <!-- Header -->
                <div class="dashboard-header">
                    <h1 class="dashboard-title">
                        <i class="fa fa-users"></i> Agent Performance Dashboard
                    </h1>
                    <div class="dashboard-controls">
                        <div class="live-indicator">
                            <span class="live-dot"></span>
                            <span>Live</span>
                        </div>
                        <div class="date-filter">
                            <input type="date" id="date-from" value="${this.dateFrom}">
                            <span>to</span>
                            <input type="date" id="date-to" value="${this.dateTo}">
                        </div>
                        <button class="btn-refresh" id="refresh-btn">
                            <i class="fa fa-refresh"></i> Refresh
                        </button>
                    </div>
                </div>

                <!-- Summary Cards -->
                <div class="summary-cards" id="summary-cards">
                    <div class="loading-spinner">
                        <i class="fa fa-spinner fa-spin"></i>
                    </div>
                </div>

                <!-- Main Grid -->
                <div class="dashboard-grid">
                    <!-- Agent Performance Table -->
                    <div class="dashboard-card" style="grid-column: span 2;">
                        <div class="card-header">
                            <h3 class="card-title">
                                <i class="fa fa-user-circle"></i> Agent Performance
                            </h3>
                        </div>
                        <div class="card-body" id="agent-table-container">
                            <div class="loading-spinner">
                                <i class="fa fa-spinner fa-spin"></i>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Charts Row -->
                <div class="dashboard-grid">
                    <!-- Trend Chart -->
                    <div class="dashboard-card">
                        <div class="card-header">
                            <h3 class="card-title">
                                <i class="fa fa-line-chart"></i> Performance Trend
                            </h3>
                        </div>
                        <div class="card-body">
                            <div class="chart-container" id="trend-chart"></div>
                        </div>
                    </div>

                    <!-- Platform Distribution -->
                    <div class="dashboard-card">
                        <div class="card-header">
                            <h3 class="card-title">
                                <i class="fa fa-pie-chart"></i> Platform Distribution
                            </h3>
                        </div>
                        <div class="card-body">
                            <div class="chart-container" id="platform-chart"></div>
                        </div>
                    </div>
                </div>

                <!-- Live Activity -->
                <div class="dashboard-card" style="margin-top: 24px;">
                    <div class="card-header">
                        <h3 class="card-title">
                            <i class="fa fa-bolt"></i> Recent Activity
                            <span class="live-indicator" style="margin-left: 8px;">
                                <span class="live-dot"></span>
                            </span>
                        </h3>
                    </div>
                    <div class="card-body">
                        <div class="activity-feed" id="activity-feed">
                            <div class="loading-spinner">
                                <i class="fa fa-spinner fa-spin"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `);
    }

    bindEvents() {
        const self = this;

        // Refresh button
        $('#refresh-btn').on('click', function() {
            $(this).addClass('loading');
            self.loadDashboard().then(() => {
                $(this).removeClass('loading');
            });
        });

        // Date filter changes
        $('#date-from, #date-to').on('change', function() {
            self.dateFrom = $('#date-from').val();
            self.dateTo = $('#date-to').val();
            self.loadDashboard();
        });
    }

    async loadDashboard() {
        await Promise.all([
            this.loadSummary(),
            this.loadAgentDetails(),
            this.loadTrendChart(),
            this.loadPlatformChart(),
            this.loadLiveActivity()
        ]);
    }

    async loadSummary() {
        try {
            const data = await frappe.call({
                method: 'assistant_crm.assistant_crm.page.agent_performance_dashboard.agent_performance_dashboard.get_dashboard_summary',
                args: { date_from: this.dateFrom, date_to: this.dateTo }
            });

            const summary = data.message;
            $('#summary-cards').html(`
                <div class="summary-card">
                    <div class="card-icon primary"><i class="fa fa-users"></i></div>
                    <div class="card-value">${summary.total_agents}</div>
                    <div class="card-label">Total Agents</div>
                </div>
                <div class="summary-card">
                    <div class="card-icon primary"><i class="fa fa-comments"></i></div>
                    <div class="card-value">${summary.total_conversations}</div>
                    <div class="card-label">Total Conversations</div>
                </div>
                <div class="summary-card">
                    <div class="card-icon success"><i class="fa fa-check-circle"></i></div>
                    <div class="card-value">${summary.resolved_conversations}</div>
                    <div class="card-label">Resolved</div>
                </div>
                <div class="summary-card">
                    <div class="card-icon ${summary.resolution_rate >= 80 ? 'success' : summary.resolution_rate >= 50 ? 'warning' : 'danger'}">
                        <i class="fa fa-percent"></i>
                    </div>
                    <div class="card-value">${summary.resolution_rate}%</div>
                    <div class="card-label">Resolution Rate</div>
                </div>
                <div class="summary-card">
                    <div class="card-icon warning"><i class="fa fa-clock-o"></i></div>
                    <div class="card-value">${this.formatResponseTime(summary.avg_response_time)}</div>
                    <div class="card-label">Avg Response Time</div>
                </div>
                <div class="summary-card">
                    <div class="card-icon danger"><i class="fa fa-spinner"></i></div>
                    <div class="card-value">${summary.active_conversations}</div>
                    <div class="card-label">Active Now</div>
                </div>
            `);
        } catch (e) {
            console.error('Error loading summary:', e);
        }
    }

    async loadAgentDetails() {
        try {
            const data = await frappe.call({
                method: 'assistant_crm.assistant_crm.page.agent_performance_dashboard.agent_performance_dashboard.get_agent_details',
                args: { date_from: this.dateFrom, date_to: this.dateTo }
            });

            const agents = data.message || [];

            if (agents.length === 0) {
                $('#agent-table-container').html(`
                    <div class="text-center text-muted py-4">
                        <i class="fa fa-users fa-2x mb-2"></i>
                        <p>No agents with Customer Service roles found</p>
                    </div>
                `);
                return;
            }

            let tableHtml = `
                <table class="agent-table">
                    <thead>
                        <tr>
                            <th>Agent</th>
                            <th>Assigned</th>
                            <th>Resolved</th>
                            <th>Active</th>
                            <th>Resolution Rate</th>
                            <th>Avg Response</th>
                            <th>Top Platform</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            agents.forEach(agent => {
                const initials = this.getInitials(agent.full_name);
                const topPlatform = this.getTopPlatform(agent.platform_breakdown);
                const rateClass = agent.resolution_rate >= 80 ? 'success' : agent.resolution_rate >= 50 ? 'warning' : 'danger';

                tableHtml += `
                    <tr>
                        <td>
                            <div class="agent-info">
                                <div class="agent-avatar">
                                    ${agent.user_image ? `<img src="${agent.user_image}" alt="${agent.full_name}">` : initials}
                                </div>
                                <div>
                                    <div class="agent-name">${agent.full_name}</div>
                                    <div class="agent-role">${agent.roles.join(', ')}</div>
                                </div>
                            </div>
                        </td>
                        <td><span class="metric-value">${agent.total_assigned}</span></td>
                        <td><span class="metric-value">${agent.resolved}</span></td>
                        <td><span class="metric-badge primary">${agent.active}</span></td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <div class="progress-bar-container" style="width: 80px;">
                                    <div class="progress-bar-fill ${rateClass}" style="width: ${agent.resolution_rate}%;"></div>
                                </div>
                                <span class="metric-badge ${rateClass}">${agent.resolution_rate}%</span>
                            </div>
                        </td>
                        <td><span class="metric-value">${this.formatResponseTime(agent.avg_response_time)}</span></td>
                        <td>${topPlatform ? `<span class="platform-badge ${topPlatform.toLowerCase()}">${topPlatform}</span>` : '-'}</td>
                    </tr>
                `;
            });

            tableHtml += '</tbody></table>';
            $('#agent-table-container').html(tableHtml);
        } catch (e) {
            console.error('Error loading agent details:', e);
        }
    }

    async loadTrendChart() {
        try {
            const data = await frappe.call({
                method: 'assistant_crm.assistant_crm.page.agent_performance_dashboard.agent_performance_dashboard.get_performance_trends',
                args: { date_from: this.dateFrom, date_to: this.dateTo }
            });

            const trends = data.message || [];

            if (trends.length === 0) {
                $('#trend-chart').html('<div class="text-center text-muted py-4">No data available</div>');
                return;
            }

            const chartData = {
                labels: trends.map(t => frappe.datetime.str_to_user(t.date)),
                datasets: [
                    { name: 'Total', values: trends.map(t => t.total) },
                    { name: 'Resolved', values: trends.map(t => t.resolved) }
                ]
            };

            if (this.charts.trend) {
                this.charts.trend.update(chartData);
            } else {
                this.charts.trend = new frappe.Chart('#trend-chart', {
                    data: chartData,
                    type: 'line',
                    height: 280,
                    colors: ['#0289f7', '#30a66d'],
                    lineOptions: { regionFill: 1 }
                });
            }
        } catch (e) {
            console.error('Error loading trend chart:', e);
        }
    }

    async loadPlatformChart() {
        try {
            const data = await frappe.call({
                method: 'assistant_crm.assistant_crm.page.agent_performance_dashboard.agent_performance_dashboard.get_platform_distribution',
                args: { date_from: this.dateFrom, date_to: this.dateTo }
            });

            const platforms = data.message || [];

            if (platforms.length === 0) {
                $('#platform-chart').html('<div class="text-center text-muted py-4">No data available</div>');
                return;
            }

            const chartData = {
                labels: platforms.map(p => p.platform || 'Unknown'),
                datasets: [{ values: platforms.map(p => p.count) }]
            };

            const colors = platforms.map(p => this.getPlatformColor(p.platform));

            if (this.charts.platform) {
                this.charts.platform.update(chartData);
            } else {
                this.charts.platform = new frappe.Chart('#platform-chart', {
                    data: chartData,
                    type: 'pie',
                    height: 280,
                    colors: colors
                });
            }
        } catch (e) {
            console.error('Error loading platform chart:', e);
        }
    }

    async loadLiveActivity() {
        try {
            const data = await frappe.call({
                method: 'assistant_crm.assistant_crm.page.agent_performance_dashboard.agent_performance_dashboard.get_live_activity'
            });

            const activity = data.message;
            const recent = activity.recent_assignments || [];

            if (recent.length === 0) {
                $('#activity-feed').html(`
                    <div class="text-center text-muted py-4">
                        <i class="fa fa-inbox fa-2x mb-2"></i>
                        <p>No recent activity</p>
                    </div>
                `);
                return;
            }

            let feedHtml = '';
            recent.forEach(item => {
                const timeAgo = frappe.datetime.prettyDate(item.agent_assigned_at);
                const platformClass = (item.platform || '').toLowerCase().replace('.', '');

                feedHtml += `
                    <div class="activity-item">
                        <div class="activity-icon" style="background: var(--apd-primary-light); color: var(--apd-primary);">
                            <i class="fa fa-user-plus"></i>
                        </div>
                        <div class="activity-content">
                            <div class="activity-title">
                                <strong>${item.agent_name}</strong> assigned to
                                <a href="/app/unified-inbox-conversation/${item.name}">${item.customer_name || 'Customer'}</a>
                            </div>
                            <div class="activity-meta">
                                <span class="platform-badge ${platformClass}">${item.platform}</span>
                                <span style="margin-left: 8px;">${timeAgo}</span>
                            </div>
                        </div>
                    </div>
                `;
            });

            $('#activity-feed').html(feedHtml);
        } catch (e) {
            console.error('Error loading live activity:', e);
        }
    }

    startLiveUpdates() {
        // Refresh live activity every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.loadLiveActivity();
            this.loadSummary();
        }, 30000);
    }

    stopLiveUpdates() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }

    // Helper methods
    formatResponseTime(minutes) {
        if (!minutes || minutes === 0) return '-';
        if (minutes < 1) return `${Math.round(minutes * 60)}s`;
        if (minutes < 60) return `${Math.round(minutes)}m`;
        const hours = Math.floor(minutes / 60);
        const mins = Math.round(minutes % 60);
        return `${hours}h ${mins}m`;
    }

    getInitials(name) {
        if (!name) return '?';
        return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
    }

    getTopPlatform(breakdown) {
        if (!breakdown || Object.keys(breakdown).length === 0) return null;
        return Object.entries(breakdown).sort((a, b) => b[1] - a[1])[0][0];
    }

    getPlatformColor(platform) {
        const colors = {
            'WhatsApp': '#25D366',
            'Facebook': '#1877F2',
            'Instagram': '#E4405F',
            'Telegram': '#0088cc',
            'Twitter': '#1DA1F2',
            'LinkedIn': '#0A66C2',
            'Tawk.to': '#03a84e',
            'YouTube': '#FF0000'
        };
        return colors[platform] || '#7c7c7c';
    }
}

// Cleanup on page unload
frappe.pages['agent-performance-dashboard'].on_page_hide = function() {
    if (window.agentDashboard) {
        window.agentDashboard.stopLiveUpdates();
    }
};
