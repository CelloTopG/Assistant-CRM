// CRM Inbox - Professional Enterprise UI
// Unified messaging hub for customer conversations

frappe.pages['inbox'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Inbox',
        single_column: true
    });

    // Set the page content with professional, clean design
    page.main.html(`
        <div class="inbox-container">
            <!-- Platform Filters with Refresh -->
            <div class="platform-filters d-flex justify-content-between align-items-center">
                <div class="btn-group flex-wrap" role="group" aria-label="Platform filters">
                    <button type="button" class="btn active" id="filter-all" data-platform="all">
                        All Channels
                    </button>
                    <button type="button" class="btn" id="filter-whatsapp" data-platform="WhatsApp">
                        <i class="fa fa-whatsapp me-1"></i>WhatsApp
                    </button>
                    <button type="button" class="btn" id="filter-facebook" data-platform="Facebook">
                        <i class="fa fa-facebook me-1"></i>Facebook
                    </button>
                    <button type="button" class="btn" id="filter-instagram" data-platform="Instagram">
                        <i class="fa fa-instagram me-1"></i>Instagram
                    </button>
                    <button type="button" class="btn" id="filter-telegram" data-platform="Telegram">
                        <i class="fa fa-telegram me-1"></i>Telegram
                    </button>
                    <button type="button" class="btn" id="filter-twitter" data-platform="Twitter">
                        <i class="fa fa-twitter me-1"></i>Twitter
                    </button>
                    <button type="button" class="btn" id="filter-linkedin" data-platform="LinkedIn">
                        <i class="fa fa-linkedin me-1"></i>LinkedIn
                    </button>
                    <button type="button" class="btn" id="filter-tawk" data-platform="Tawk.to">
                        <i class="fa fa-headphones me-1"></i>Tawk.to
                    </button>
                    <button type="button" class="btn" id="filter-youtube" data-platform="YouTube">
                        <i class="fa fa-youtube me-1"></i>YouTube
                    </button>
                </div>
                <button class="btn btn-sm btn-default" id="refresh-btn" title="Refresh conversations">
                    <i class="fa fa-refresh"></i>
                </button>
            </div>

            <!-- Main Content Grid -->
            <div class="row g-3 mt-0">
                <!-- Conversations List -->
                <div class="col-md-4">
                    <div class="card h-100">
                        <div class="card-header">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span class="d-flex align-items-center">
                                    <i class="fa fa-comments me-2"></i>Conversations
                                </span>
                                <span id="conversation-count">0</span>
                            </div>
                            <div class="d-flex align-items-center gap-2">
                                <div class="btn-group btn-group-sm" role="group">
                                    <button type="button" class="btn btn-outline-secondary active" id="conv-filter-non-survey" data-convfilter="non_survey">
                                        Chats
                                    </button>
                                    <button type="button" class="btn btn-outline-secondary" id="conv-filter-survey" data-convfilter="survey_only">
                                        Surveys
                                    </button>
                                </div>
                                <div class="input-group input-group-sm flex-grow-1">
                                    <span class="input-group-text border-0 bg-transparent"><i class="fa fa-search text-muted"></i></span>
                                    <input type="text" class="form-control" id="conversation-search" placeholder="Search..." autocomplete="off" autocorrect="off" autocapitalize="none" spellcheck="false"/>
                                </div>
                            </div>
                        </div>
                        <div class="card-body p-0">
                            <div class="conversation-list" id="conversation-list">
                                <div class="text-center p-4">
                                    <i class="fa fa-spinner fa-spin mb-2"></i>
                                    <p class="mb-0 small">Loading...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Message Area -->
                <div class="col-md-8">
                    <div class="card h-100">
                        <!-- Conversation Header - Clean layout -->
                        <div class="card-header" id="conversation-header" style="display: none;">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <div class="d-flex align-items-center gap-2 mb-1">
                                        <strong id="customer-name">Customer Name</strong>
                                        <span class="platform-badge badge" id="platform-badge">Platform</span>
                                        <span class="status-badge badge" id="status-badge">Status</span>
                                    </div>
                                    <div class="d-flex align-items-center gap-2">
                                        <span class="badge bg-info" id="assigned-badge" style="display: none;">
                                            <i class="fa fa-user me-1"></i><span id="assigned-agent-name">Unassigned</span>
                                        </span>
                                        <span class="badge bg-success" id="data-source-badge" style="display: none;">
                                            <i class="fa fa-database me-1"></i>Live
                                        </span>
                                        <span class="badge bg-success" id="survey-badge" style="display: none;">
                                            Survey
                                        </span>
                                    </div>
                                </div>
                                <div class="btn-group btn-group-sm action-buttons">
                                    <button class="btn btn-default icon-btn" id="customer-data-btn" style="display: none;" title="View customer data">
                                        <i class="fa fa-user-circle-o"></i>
                                    </button>
                                    <button class="btn btn-default icon-btn" id="issue-btn" style="display: none;" title="View ticket">
                                        <i class="fa fa-ticket"></i>
                                    </button>
                                    <button class="btn btn-default icon-btn" id="assign-btn" title="Assign to agent">
                                        <i class="fa fa-user-plus"></i>
                                    </button>
                                    <button class="btn btn-default icon-btn" id="ai-control-btn" title="AI settings">
                                        <i class="fa fa-cog"></i>
                                    </button>
                                    <button class="btn btn-default icon-btn" id="escalate-btn" title="Escalate issue">
                                        <i class="fa fa-arrow-up"></i>
                                    </button>
                                    <button class="btn btn-default icon-btn" id="close-btn" title="Close conversation">
                                        <i class="fa fa-check"></i>
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- Messages Container -->
                        <div class="card-body p-0">
                            <div class="messages-container" id="messages-container">
                                <div class="no-conversation text-center">
                                    <i class="fa fa-inbox fa-3x mb-3"></i>
                                    <h6>Select a conversation</h6>
                                    <p class="small mb-0">Choose from the list to view and respond</p>
                                </div>
                            </div>
                        </div>

                        <!-- Message Input - Clean -->
                        <div class="card-footer" id="message-input-area" style="display: none;">
                            <div class="input-group">
                                <input type="text" class="form-control" id="message-input" placeholder="Type a message...">
                                <select id="twitter-reply-mode" class="form-select" style="max-width: 100px; display: none;">
                                    <option value="dm" selected>DM</option>
                                    <option value="public">Public</option>
                                </select>
                                <button class="btn btn-primary" type="button" id="send-btn">
                                    <i class="fa fa-paper-plane"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `);

    // Custom CSS is now in inbox.css - no inline styles needed for professional design
    // The external stylesheet provides all styling with CSS variables for theming

    // Initialize the inbox functionality with a small delay to ensure DOM is ready
    setTimeout(() => {
        new InboxManager(page);
    }, 500);
};

class InboxManager {
    constructor(page) {
        this.page = page;
        this.conversations = [];
        this.messages = [];
        this.currentConversation = null;
        this.currentPlatformFilter = 'all';
        this.currentConversationFilter = 'non_survey'; // default: exclude surveys
        this.surveyLabels = {};
        // Search state
        this.searchQuery = '';
        this._searchTimer = null;

        this.setup_events();
        this.initialize();
    }

    initialize() {
        console.log('Initializing Inbox...');
        // Ensure search is cleared on load (avoid browser autofill carrying over)
        try {
            const $search = $('#conversation-search');
            if ($search && $search.length) {
                $search.val('');
            }
            this.searchQuery = '';
        } catch (e) {
            console.warn('Search reset skipped:', e);
        }


        // Initialize empty conversations and load from API
        this.conversations = [];

        // Load conversations from API
        this.loadConversations();

        // Set up periodic refresh with live message fetching
        setInterval(() => {
            Promise.all([
                this.fetchTelegramMessages(),
                this.fetchTawkToMessages(),
                this.fetchInstagramMessages()
            ]).then(() => {
                this.loadConversations();
            });
        }, 30000);

        // Initial message fetch from all platforms
        Promise.all([
            this.fetchTelegramMessages(),
            this.fetchTawkToMessages(),
            this.fetchInstagramMessages()
        ]).then(() => {
            console.log('DEBUG: Initial message fetch completed for all platforms');
        });
    }

    setup_events() {
        console.log('DEBUG: Setting up event listeners');

        // Set up event listeners with comprehensive logging
        $(document).on('click', '#refresh-btn', () => {
            console.log('DEBUG: Refresh button clicked');
            this.refreshInbox();
        });
        $(document).on('click', '#send-btn', () => {
            console.log('DEBUG: Send button clicked');
            this.sendMessage();
        });
        $(document).on('click', '#assign-btn', () => {
            console.log('DEBUG: Assign button clicked - Event triggered');
            console.log('DEBUG: this context:', this);
            console.log('DEBUG: assignToAgent function exists:', typeof this.assignToAgent);
            this.assignToAgent();
        });
        $(document).on('click', '#escalate-btn', () => {
            console.log('DEBUG: Escalate button clicked - Event triggered');
            console.log('DEBUG: escalateConversation function exists:', typeof this.escalateConversation);
            this.escalateConversation();
        });
        $(document).on('click', '#close-btn', () => {
            console.log('DEBUG: Close button clicked');
            this.closeConversation();
        });
        $(document).on('click', '#ai-control-btn', () => {
            console.log('DEBUG: AI Control button clicked');
            this.openAiControlDialog();
        });
        $(document).on('click', '#customer-data-btn', () => {
            console.log('DEBUG: Customer data button clicked');
            this.showCustomerData();
        });
        $(document).on('click', '#issue-btn', () => {
            console.log('DEBUG: Issue/Ticket button clicked - Event triggered');
            console.log('DEBUG: openIssue function exists:', typeof this.openIssue);
            this.openIssue();
        });

        // Platform filter buttons
        $(document).on('click', '.platform-filters .btn', (e) => {
            const platform = $(e.currentTarget).data('platform');
            this.filterByPlatform(platform);
        });

        // Conversation type filter buttons (in Conversations header)
        $(document).on('click', 'button[data-convfilter]', (e) => {
            const filter = $(e.currentTarget).data('convfilter');
            this.currentConversationFilter = filter;
            // Toggle active classes
            $('#conv-filter-non-survey').removeClass('active');
            $('#conv-filter-survey').removeClass('active');
            if (filter === 'non_survey') {
                $('#conv-filter-non-survey').addClass('active');
            } else if (filter === 'survey_only') {
                $('#conv-filter-survey').addClass('active');
            }
            this.renderConversations();
        });

        // Handle Enter key in message input
        $(document).on('keypress', '#message-input', (e) => {
            if (e.which === 13 && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Search input for conversations
        $(document).on('input', '#conversation-search', (e) => {
            const q = (e.currentTarget.value || '').trim();
            this.handleSearchInput(q);
        });

    }

    loadConversations() {
        // Sync with DOM input and route to search only if non-empty
        const el = document.getElementById('conversation-search');
        const domQ = el ? ((el.value || '').trim()) : '';
        this.searchQuery = domQ;
        if (domQ.length > 0) {
            return this.searchConversations(domQ);
        }
        try {
            frappe.call({
                method: 'assistant_crm.api.unified_inbox_api.get_conversations',
                callback: (response) => {
                    if (response.message && response.message.status === 'success') {
                        const data = response.message.data || response.message.conversations || [];
                        this.conversations = data;
                        console.log('Loaded conversations from API:', this.conversations.length);
                    } else {
                        console.log('No API data; keeping current conversations');
                    }
                    this.renderConversations();
                },
                error: (error) => {
                    console.error('Error loading conversations:', error);
                    this.renderConversations();
                }
            });
        } catch (error) {
            console.error('Error calling API:', error);
            this.renderConversations();
        }
    }


    handleSearchInput(query) {
        this.searchQuery = (query || '').trim();
        if (this._searchTimer) {
            clearTimeout(this._searchTimer);
        }
        // Debounce to avoid excessive calls while typing
        this._searchTimer = setTimeout(() => {
            if (!this.searchQuery) {
                // If cleared, reload full list
                this.loadConversations();
            } else {
                this.searchConversations(this.searchQuery);
            }
        }, 300);
    }

    searchConversations(query) {
        const q = (query || '').trim();
        if (!q) {
            return this.loadConversations();
        }
        try {
            frappe.call({
                method: 'assistant_crm.api.unified_inbox_api.search_conversations',
                args: { q: q, limit: 100 },
                callback: (response) => {
                    if (response.message && response.message.status === 'success') {
                        const data = response.message.data || response.message.conversations || [];
                        this.conversations = data;
                    } else {
                        console.warn('Search returned no results or error; retaining existing conversation list');
                    }
                    this.renderConversations();
                },
                error: (error) => {
                    console.error('Error searching conversations:', error);
                    this.renderConversations();
                }
            });
        } catch (e) {
            console.error('Exception during search:', e);
            this.renderConversations();
        }
    }

    renderConversations() {
        console.log('Rendering conversations, total:', this.conversations.length);
        const conversationList = document.getElementById('conversation-list');
        const conversationCount = document.getElementById('conversation-count');

        if (!conversationList) {
            console.log('Conversation list element not found, waiting...');
            setTimeout(() => this.renderConversations(), 1000);
            return;
        }

        // Filter by platform
        let filteredConversations = this.conversations;
        if (this.currentPlatformFilter !== 'all') {
            filteredConversations = this.conversations.filter(conv => conv.platform === this.currentPlatformFilter);
        }

        // Apply conversation type filter (default: exclude surveys)
        filteredConversations = filteredConversations.filter(conv => {
            const tags = String(conv.tags || '').toLowerCase();
            const subject = String(conv.subject || '').toLowerCase();
            const status = String(conv.status || '').toLowerCase();
            const isSurvey = tags.includes('survey') || subject.startsWith('survey') || status.includes('survey');
            if (this.currentConversationFilter === 'survey_only') return isSurvey;
            if (this.currentConversationFilter === 'non_survey') return !isSurvey;
            return true; // fallback to all
        });

        console.log('Filtered conversations:', filteredConversations.length);
        conversationCount.textContent = filteredConversations.length;

        const html = filteredConversations.map(conv => {
            const isActive = this.currentConversation === conv.name ? 'active' : '';
            const unreadBadge = conv.unread_count > 0 ? `<span class="badge bg-danger ms-2">${conv.unread_count}</span>` : '';
            const tagHasSurvey = String(conv.tags || '').toLowerCase().includes('survey');
            const subjHasSurvey = String(conv.subject || '').toLowerCase().startsWith('survey');
            const statusHasSurvey = String(conv.status || '').toLowerCase().includes('survey');

            return `
                <div class="conversation-item ${isActive}" data-conversation="${conv.name}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="d-flex align-items-center mb-1">
                                <strong class="me-2">${conv.customer_name}</strong>
                                ${unreadBadge}
                            </div>
                            <div class="mb-2">
                                <span class="platform-badge badge ${conv.platform} me-1">${conv.platform}</span>
                                <span class="status-badge badge ${(conv.status || '').replace(' ', '.')}">${conv.status || ''}</span>
                                ${(tagHasSurvey || subjHasSurvey || statusHasSurvey) ? '<span class="badge bg-success ms-1"><i class="fa fa-bar-chart me-1"></i>Survey</span>' : ''}
                                ${conv.priority === 'Urgent' ? '<span class="badge bg-danger ms-1">🚨 URGENT</span>' : ''}
                                ${conv.priority === 'High' ? '<span class="badge bg-warning ms-1">⚠️ HIGH</span>' : ''}
                            </div>
                            <small class="text-muted d-block">${conv.last_message_preview}</small>
                            <small class="text-muted">${this.formatTime(conv.last_message_time)}</small>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        conversationList.innerHTML = html;

        // Add click event listeners to conversation items
        $(document).off('click', '.conversation-item').on('click', '.conversation-item', (e) => {
            const conversationName = $(e.currentTarget).data('conversation');
            this.selectConversation(conversationName);
        });
    }

    filterByPlatform(platform) {
        this.currentPlatformFilter = platform;

        // Update button states
        $('.platform-filters .btn').removeClass('active');
        $(`.platform-filters .btn[data-platform="${platform}"]`).addClass('active');

        // Re-render conversations with filter
        this.renderConversations();
    }

    selectConversation(conversationName) {
        console.log('Selecting conversation:', conversationName);
        this.currentConversation = conversationName;
        this.renderConversations(); // Re-render to show active state
        this.loadMessages(conversationName);

        // Show message input area and conversation header
        console.log('Showing conversation header and input area');
        $('#message-input-area').show();
        $('#conversation-header').show();

        // Update conversation header
        this.updateConversationHeader(conversationName);

        // Check if customer has CoreBusiness data
        this.checkCustomerData(conversationName);
    }

    updateConversationHeader(conversationName) {
        const conversation = this.conversations.find(c => c.name === conversationName);
        if (!conversation) return;

        $('#customer-name').text(conversation.customer_name);
        $('#platform-badge').text(conversation.platform).attr('class', `platform-badge badge ${conversation.platform}`);
        $('#status-badge').text(conversation.status || '').attr('class', `status-badge badge ${(conversation.status || '').replace(' ', '.')}`);
        const mode = conversation.ai_mode || 'Auto';
        $('#ai-control-btn').html(`<i class=\"fa fa-cog\"></i> AI: ${mode}`);

        // Reset survey badge; will be set during message render if applicable
        $('#survey-badge').hide();

        // Toggle Twitter reply mode selector visibility
        if (conversation.platform === 'Twitter') {
            $('#twitter-reply-mode').show();
            $('#twitter-reply-mode').val('dm');
        } else {
            $('#twitter-reply-mode').hide();
        }

        // Assigned agent badge
        const assignedLabel = conversation.assigned_agent_name || conversation.assigned_agent || null;
        if (assignedLabel) {
            $('#assigned-agent-name').text(assignedLabel);
            $('#assigned-badge').show();
        } else {
            $('#assigned-badge').hide();
        }

        // Show Issue button if conversation has a real ERPNext Issue ID
        if (conversation.issue_id) {
            $('#issue-btn').show();
        } else {
            $('#issue-btn').hide();
        }
    }

    checkCustomerData(conversationName) {
        const conversation = this.conversations.find(c => c.name === conversationName);

        // Show data button for conversations with phone numbers
        if (conversation && conversation.customer_phone) {
            $('#data-source-badge').show();
            $('#customer-data-btn').show();
        } else {
            $('#data-source-badge').hide();
            $('#customer-data-btn').hide();
        }
    }

    formatTime(timestamp) {
        if (!timestamp) return '';

        try {
            let date;

            // Parse our standard 'YYYY-MM-DD HH:MM:SS' as UTC to avoid local shifts
            if (typeof timestamp === 'string') {
                const m = timestamp.match(/^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$/);
                if (m) {
                    const Y = parseInt(m[1], 10);
                    const Mo = parseInt(m[2], 10) - 1;
                    const D = parseInt(m[3], 10);
                    const H = parseInt(m[4], 10);
                    const Mi = parseInt(m[5], 10);
                    const S = parseInt(m[6], 10);
                    date = new Date(Date.UTC(Y, Mo, D, H, Mi, S));
                }
            }

            if (!date) {
                date = new Date(timestamp);
            }

            if (isNaN(date.getTime())) {
                return String(timestamp);
            }

            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);

            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffDays < 7) return `${diffDays}d ago`;

            return date.toLocaleDateString();
        } catch (e) {
            return String(timestamp);
        }
    }

    refreshInbox() {
        console.log('DEBUG: Refreshing inbox with live messages...');

        // Fetch live messages from all platforms
        Promise.all([
            this.fetchTelegramMessages(),
            this.fetchTawkToMessages(),
            this.fetchInstagramMessages()
        ]).then(() => {
            // Then load all conversations (including new ones)
            this.loadConversations();
            if (this.currentConversation) {
                this.loadMessages(this.currentConversation);
            }
            frappe.show_alert({ message: 'Inbox refreshed', indicator: 'blue' });
        });
    }


    openAiControlDialog() {
        if (!this.currentConversation) {
            frappe.show_alert({ message: 'Please select a conversation first', indicator: 'orange' });
            return;
        }
        const conversation = this.conversations.find(c => c.name === this.currentConversation) || {};
        const currentMode = conversation.ai_mode || 'Auto';

        const dialog = new frappe.ui.Dialog({
            title: 'AI Control',
            fields: [
                {
                    fieldtype: 'Select',
                    fieldname: 'mode',
                    label: 'AI Mode',
                    options: ['Auto', 'On', 'Off'],
                    default: currentMode,
                    reqd: 1,
                    description: 'Auto: AI responds when unassigned, pauses when assigned. On: Force AI responses. Off: Disable AI responses.'
                }
            ],
            primary_action_label: 'Save',
            primary_action: (values) => {
                frappe.call({
                    method: 'assistant_crm.api.unified_inbox_api.set_conversation_ai_mode',
                    args: {
                        conversation_name: this.currentConversation,
                        mode: values.mode
                    },
                    callback: (r) => {
                        if (r.message && r.message.status === 'success') {
                            const mode = r.message.mode;
                            const conv = this.conversations.find(c => c.name === this.currentConversation);
                            if (conv) conv.ai_mode = mode;
                            $('#ai-control-btn').html(`<i class=\"fa fa-cog\"></i> AI: ${mode}`);
                            dialog.hide();
                            frappe.show_alert({ message: `AI mode set to ${mode}`, indicator: 'green' });
                        } else {
                            frappe.show_alert({
                                message: 'Failed to set AI mode: ' + (r.message?.message || 'Unknown error'),
                                indicator: 'red'
                            });
                        }
                    },
                    error: (error) => {
                        console.error('Error setting AI mode:', error);
                        frappe.show_alert({ message: 'Error setting AI mode', indicator: 'red' });
                    }
                });
            }
        });

        dialog.show();
    }

    fetchTelegramMessages() {
        console.log('DEBUG: Fetching live Telegram messages...');

        return new Promise((resolve) => {
            frappe.call({
                method: 'assistant_crm.api.unified_inbox_api.fetch_telegram_messages',
                callback: (response) => {
                    try {
                        if (response.message && response.message.status === 'success') {
                            console.log('DEBUG: Telegram fetch result:', response.message);

                            if (response.message.new_conversations > 0) {
                                frappe.show_alert({
                                    message: `${response.message.new_conversations} new Telegram conversation(s) received`,
                                    indicator: 'green'
                                });
                            }

                            if (response.message.processed_messages > 0) {
                                console.log(`DEBUG: Processed ${response.message.processed_messages} new Telegram messages`);
                            }
                        } else if (response.message && response.message.status === 'error') {
                            console.error('DEBUG: Telegram fetch failed:', response.message.message);
                            // Don't show error alerts for Telegram fetch failures to avoid spam
                        } else {
                            console.error('DEBUG: Unexpected Telegram response:', response.message);
                        }
                    } catch (e) {
                        console.error('DEBUG: Error processing Telegram response:', e);
                    }
                    resolve();
                },
                error: (error) => {
                    console.error('DEBUG: Telegram fetch network error:', error);
                    // Don't show error alerts for network failures to avoid spam
                    resolve();
                }
            });
        });
    }

    fetchTawkToMessages() {
        console.log('DEBUG: Fetching live Tawk.to messages...');

        return new Promise((resolve) => {
            frappe.call({
                method: 'assistant_crm.api.unified_inbox_api.fetch_tawkto_messages',
                callback: (response) => {
                    try {
                        if (response.message && response.message.status === 'success') {
                            console.log('DEBUG: Tawk.to fetch result:', response.message);

                            if (response.message.new_conversations > 0) {
                                frappe.show_alert({
                                    message: `${response.message.new_conversations} new Tawk.to conversation(s) received`,
                                    indicator: 'green'
                                });
                            }

                            if (response.message.processed_messages > 0) {
                                console.log(`DEBUG: Processed ${response.message.processed_messages} new Tawk.to messages`);
                            }
                        } else if (response.message && response.message.status === 'info') {
                            console.log('DEBUG: Tawk.to info:', response.message.message);
                            // Don't show alerts for info messages (webhook-based integration)
                        } else if (response.message && response.message.status === 'error') {
                            console.error('DEBUG: Tawk.to fetch failed:', response.message.message);
                            // Don't show error alerts for Tawk.to fetch failures to avoid spam
                        } else {
                            console.error('DEBUG: Unexpected Tawk.to response:', response.message);
                        }
                    } catch (e) {
                        console.error('DEBUG: Error processing Tawk.to response:', e);
                    }
                    resolve();
                },
                error: (error) => {
                    console.error('DEBUG: Tawk.to fetch network error:', error);
                    // Don't show error alerts for network failures to avoid spam
                    resolve();
                }
            });
        });
    }

    fetchInstagramMessages() {
        console.log('DEBUG: Fetching live Instagram messages...');

        return new Promise((resolve) => {
            frappe.call({
                method: 'assistant_crm.api.unified_inbox_api.fetch_instagram_messages',
                callback: (response) => {
                    try {
                        if (response.message && response.message.status === 'success') {
                            console.log('DEBUG: Instagram fetch result:', response.message);

                            if (response.message.new_conversations > 0) {
                                frappe.show_alert({
                                    message: `${response.message.new_conversations} new Instagram conversation(s) received`,
                                    indicator: 'green'
                                });
                            }

                            if (response.message.processed_messages > 0) {
                                console.log(`DEBUG: Processed ${response.message.processed_messages} new Instagram messages`);
                            }
                        } else if (response.message && response.message.status === 'error') {
                            console.error('DEBUG: Instagram fetch failed:', response.message.message);
                            // Don't show error alerts for Instagram fetch failures to avoid spam
                        } else {
                            console.error('DEBUG: Unexpected Instagram response:', response.message);
                        }
                    } catch (e) {
                        console.error('DEBUG: Error processing Instagram response:', e);
                    }
                    resolve();
                },
                error: (error) => {
                    console.error('DEBUG: Instagram fetch network error:', error);
                    // Don't show error alerts for network failures to avoid spam
                    resolve();
                }
            });
        });
    }

    // Load messages for a conversation
    loadMessages(conversationName) {
        if (!conversationName) return;

        // Show loading state
        $('#messages-container').html(`
            <div class="text-center p-4">
                <i class="fa fa-spinner fa-spin fa-2x mb-3"></i>
                <p>Loading messages...</p>
            </div>
        `);

        // Load messages from API
        frappe.call({
            method: 'assistant_crm.api.unified_inbox_api.get_messages',
            args: {
                conversation_name: conversationName,
                limit: 500
            },
            callback: (response) => {
                if (response.message && response.message.status === 'success') {
                    this.messages = response.message.data;

                    // Generate ticket immediately when messages are loaded (before rendering)
                    this.generateTicketForConversation(conversationName, () => {
                        this.renderMessages();
                    });
                } else {
                    $('#messages-container').html(`
                        <div class="text-center p-4 text-muted">
                            <i class="fa fa-comments fa-3x mb-3"></i>
                            <h5>No messages yet</h5>
                            <p>Start the conversation by sending a message</p>
                        </div>
                    `);
                }
            },
            error: (error) => {
                console.error('Error loading messages:', error);
                $('#messages-container').html(`
                    <div class="text-center p-4 text-danger">
                        <i class="fa fa-exclamation-triangle fa-2x mb-3"></i>
                        <p>Error loading messages</p>
                    </div>
                `);
            }
        });
    }

    renderMessages() {
        console.log('DEBUG: renderMessages called, messages count:', this.messages ? this.messages.length : 'undefined');
        const messagesContainer = document.getElementById('messages-container');
        if (!messagesContainer) {
            console.error('DEBUG: messagesContainer not found!');
            return;
        }

        if (!this.messages || this.messages.length === 0) {
            console.log('DEBUG: No messages to render');
            messagesContainer.innerHTML = `
                <div class="no-conversation text-center">
                    <i class="fa fa-comments fa-3x text-muted mb-3"></i>
                    <h5 class="text-muted">No messages yet</h5>
                    <p class="text-muted">Start the conversation by sending a message</p>
                </div>
            `;
            return;
        }

        // Get ticket number for this conversation
        const conversation = this.conversations.find(c => c.name === this.currentConversation);
        const ticketNumber = conversation && conversation.issue_id ? conversation.issue_id : null;

        // Ensure messages are interleaved strictly by timestamp (ascending)
        const parseToMillis = (ts) => {
            if (!ts) return 0;
            if (typeof ts === 'string') {
                const m = ts.match(/^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$/);
                if (m) {
                    return Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]);
                }
            }
            const d = new Date(ts);
            return isNaN(d.getTime()) ? 0 : d.getTime();
        };

        const sorted = [...this.messages].sort((a, b) => {
            const at = parseToMillis(a.timestamp);
            const bt = parseToMillis(b.timestamp);
            if (at !== bt) return at - bt;
            // If same second, show inbound before outbound so reply follows prompt
            const da = (a.direction || '').toLowerCase();
            const db = (b.direction || '').toLowerCase();
            if (da !== db) return da === 'inbound' ? -1 : 1;
            // Final tie-breaker: fall back to name to keep stable order
            return (a.name || '').localeCompare(b.name || '');
        });

        // Survey header badge + label extraction
        const convStatus = String((conversation && conversation.status) || '').toLowerCase();
        const surveyActive = convStatus.includes('survey');
        let surveyLabel = this.surveyLabels[this.currentConversation] || '';
        if (surveyActive && !surveyLabel) {
            const intro = sorted.find(m => (m.direction === 'Outbound') && m.sender_name === 'Survey Bot' && typeof m.message_content === 'string' && m.message_content.includes('WCFCB Survey:'));
            if (intro) {
                const marker = 'WCFCB Survey:';
                const idx = intro.message_content.indexOf(marker);
                if (idx >= 0) {
                    let rest = intro.message_content.slice(idx + marker.length).trim();
                    const nl = rest.indexOf('\n');
                    surveyLabel = (nl >= 0 ? rest.slice(0, nl) : rest).trim();
                    this.surveyLabels[this.currentConversation] = surveyLabel;
                }
            }
        }
        // Update conversation header survey badge
        const $sb = $('#survey-badge');
        if ($sb && $sb.length) {
            if (surveyActive) {
                const txt = `Survey${surveyLabel ? ': ' + surveyLabel : ''}`;
                $sb.text(txt).show();
            } else {
                $sb.hide();
            }
        }


        console.log('DEBUG: Sorted messages count:', sorted.length);

        const html = sorted.map(msg => {
            // Uniform outbound color - no distinction between AI/agent/manual
            const messageClass = msg.direction === 'Inbound' ? 'inbound' : 'outbound';
            const isAI = msg.sender_name === 'Anna AI Assistant';

            return `
                ${ticketNumber ? `
                    <div class="ticket-number-display mb-2">
                        <small class="badge bg-secondary">
                            <i class="fa fa-ticket me-1"></i>
                            Ticket: ${ticketNumber}
                        </small>
                    </div>
                ` : ''}
                <div class="message ${messageClass}">
                    <div class="message-content">
                        ${isAI ? `<div class="mb-1 text-end"><small class="text-white-50"><i class="fas fa-robot me-1"></i>Anna AI Assistant</small></div>` : ''}
                        ${(surveyActive && (msg.direction === 'Inbound' || msg.sender_name === 'Survey Bot')) ? `<div class="mb-1"><small class="badge bg-success">Survey · ${surveyLabel || ''}</small></div>` : ''}
                        ${msg.message_content}
                    </div>
                    <small class="text-muted d-block mt-1">
                        <i class="fa fa-user me-1"></i>
                        ${msg.sender_name || 'Unknown'} • ${this.formatTime(msg.timestamp)}
                    </small>
                </div>
            `;
        }).join('');

        console.log('DEBUG: Generated HTML length:', html.length);
        messagesContainer.innerHTML = html;
        this.scrollToBottom();
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('messages-container');
        if (messagesContainer) {
            setTimeout(() => {
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }, 100);
        }
    }

    sendMessage() {
        const input = document.getElementById('message-input');
        const sendButton = document.querySelector('#send-btn');
        const message = input.value.trim();

        if (!message) {
            frappe.show_alert({ message: 'Please enter a message', indicator: 'orange' });
            return;
        }

        if (!this.currentConversation) {
            frappe.show_alert({ message: 'Please select a conversation first', indicator: 'orange' });
            return;
        }

        // Show loading state
        const originalButtonText = sendButton.innerHTML;
        sendButton.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Sending...';
        sendButton.disabled = true;
        input.disabled = true;

        // Send via API
        const convo = this.conversations.find(c => c.name === this.currentConversation);
        const twitter_reply_mode = (convo && convo.platform === 'Twitter') ? ($('#twitter-reply-mode').val() || 'dm') : null;
        frappe.call({
            method: 'assistant_crm.api.unified_inbox_api.send_message',
            args: {
                conversation_name: this.currentConversation,
                message: message,
                send_via_platform: true,
                twitter_reply_mode: twitter_reply_mode
            },
            callback: (response) => {
                if (response.message && response.message.status === 'success') {
                    // Add message to Issue as comment
                    this.addMessageToIssue(
                        this.currentConversation,
                        message,
                        frappe.session.user_fullname || frappe.session.user,
                        'Agent'
                    );

                    // Clear input and reload messages
                    input.value = '';
                    this.loadMessages(this.currentConversation);
                    this.loadConversations(); // Refresh conversation list

                    frappe.show_alert({ message: 'Message sent successfully!', indicator: 'green' });
                } else {
                    // Surface platform error details if present
                    const ps = response.message?.data?.platform_send;
                    let extra = '';
                    try {
                        if (ps && ps.error_details) {
                            const code = ps.error_details.status_code ? `status ${ps.error_details.status_code}` : '';
                            const reason = ps.error_details.response_text || ps.message || '';
                            const payload = ps.error_details.request_payload ? JSON.stringify(ps.error_details.request_payload) : '';
                            const parts = [];
                            if (code) parts.push(code);
                            if (reason) parts.push(reason);
                            if (payload) parts.push(`payload ${payload}`);
                            extra = parts.length ? ' (' + parts.join(' | ') + ')' : '';
                            console.warn('Platform send failed:', ps);
                        }
                    } catch (e) {
                        console.warn('Error parsing platform_send details', e);
                    }

                    frappe.show_alert({
                        message: 'Failed to send message: ' + (response.message?.message || 'Unknown error') + extra,
                        indicator: 'red'
                    });
                }
            },
            error: (error) => {
                console.error('Error sending message:', error);
                frappe.show_alert({ message: 'Error sending message. Please try again.', indicator: 'red' });
            },
            always: () => {
                // Restore button and input state
                sendButton.innerHTML = originalButtonText;
                sendButton.disabled = false;
                input.disabled = false;
                input.focus();
            }
        });
    }

    assignToAgent() {
        console.log('DEBUG: assignToAgent() function called');
        console.log('DEBUG: this.currentConversation:', this.currentConversation);

        if (!this.currentConversation) {
            console.log('DEBUG: No conversation selected, showing alert');
            frappe.show_alert({ message: 'Please select a conversation first', indicator: 'orange' });
            return;
        }

        console.log('DEBUG: Starting assignment for conversation:', this.currentConversation);

        // Always use a reliable custom assignment dialog for consistent UX
        // This avoids dependency on ERPNext's AssignToDialog loading in Desk pages
        console.log('DEBUG: Using custom assignment dialog for assignment');
        this.createCustomAssignmentDialog();
    }

    testAssignmentButton() {
        console.log('DEBUG: Testing assignment button');
        console.log('DEBUG: Button exists:', $('#assign-btn').length > 0);
        console.log('DEBUG: Button visible:', $('#assign-btn').is(':visible'));
        console.log('DEBUG: Button disabled:', $('#assign-btn').prop('disabled'));
        console.log('DEBUG: Current conversation:', this.currentConversation);

        // Test click programmatically
        if ($('#assign-btn').length > 0) {
            console.log('DEBUG: Triggering click programmatically');
            $('#assign-btn').trigger('click');
        }
    }

    // Demo assignment dialog removed - using ERPNext native assignment for all conversations

    escalateConversation() {
        console.log('DEBUG: escalateConversation() function called');
        console.log('DEBUG: this.currentConversation:', this.currentConversation);

        if (!this.currentConversation) {
            console.log('DEBUG: No conversation selected for escalation');
            frappe.show_alert({ message: 'Please select a conversation first', indicator: 'orange' });
            return;
        }

        const conversation = this.conversations.find(c => c.name === this.currentConversation);
        console.log('DEBUG: Found conversation for escalation:', conversation);

        if (!conversation) {
            console.log('DEBUG: Conversation not found in conversations array');
            frappe.show_alert({ message: 'Conversation not found', indicator: 'red' });
            return;
        }

        // Check if conversation has an associated ERPNext Issue
        if (!conversation.issue_id) {
            frappe.show_alert({ message: 'No ERPNext Issue found for this conversation', indicator: 'orange' });
            return;
        }

        // Fetch supervisors from API to filter the escalation target list
        frappe.call({
            method: 'assistant_crm.api.unified_inbox_api.get_supervisors',
            callback: (res) => {
                const supervisors = (res.message && res.message.status === 'success') ? res.message.data : [];
                const supervisor_names = supervisors.map(s => s.name);

                // Use ERPNext's native escalation through Issue priority and assignment
                const dialog = new frappe.ui.Dialog({
                    title: 'Escalate to ERPNext Issue',
                    fields: [
                        {
                            fieldtype: 'Select',
                            fieldname: 'priority',
                            label: 'Escalate Priority To',
                            options: ['Medium', 'High', 'Urgent'],
                            default: 'High',
                            reqd: 1
                        },
                        {
                            fieldtype: 'Link',
                            fieldname: 'assign_to',
                            label: 'Escalate to User',
                            options: 'User',
                            description: supervisors.length > 0 ? 'Showing supervisors by default' : 'Assign the ERPNext Issue to a specific user'
                        },
                        {
                            fieldtype: 'Small Text',
                            fieldname: 'escalation_reason',
                            label: 'Escalation Reason',
                            reqd: 1,
                            description: 'Reason for escalating this conversation'
                        }
                    ],
                    primary_action_label: 'Escalate Issue',
                    primary_action: (values) => {
                        console.log('DEBUG: Escalating to ERPNext Issue:', conversation.issue_id);

                        frappe.call({
                            method: 'assistant_crm.api.unified_inbox_api.escalate_to_erpnext_issue',
                            args: {
                                conversation_name: this.currentConversation,
                                issue_id: conversation.issue_id,
                                new_priority: values.priority,
                                assign_to: values.assign_to,
                                escalation_reason: values.escalation_reason
                            },
                            callback: (response) => {
                                if (response.message && response.message.status === 'success') {
                                    // Update conversation status
                                    conversation.status = 'Escalated';
                                    conversation.priority = values.priority;
                                    if (values.assign_to) {
                                        conversation.assigned_agent = values.assign_to;
                                    }

                                    this.renderConversations();
                                    this.updateConversationHeader(this.currentConversation);
                                    dialog.hide();

                                    frappe.show_alert({
                                        message: `Issue ${conversation.issue_id} escalated successfully!`,
                                        indicator: 'green'
                                    });
                                } else {
                                    frappe.show_alert({
                                        message: 'Failed to escalate: ' + (response.message?.message || 'Unknown error'),
                                        indicator: 'red'
                                    });
                                }
                            },
                            error: (error) => {
                                console.error('Error escalating to ERPNext Issue:', error);
                                frappe.show_alert({ message: 'Error escalating Issue', indicator: 'red' });
                            }
                        });
                    }
                });

                // Apply supervisor filter to the assign_to field if supervisors found
                if (supervisor_names.length > 0) {
                    dialog.fields_dict.assign_to.get_query = () => {
                        return {
                            filters: {
                                "name": ["in", supervisor_names]
                            }
                        };
                    };
                }

                dialog.show();
            }
        });
    }

    closeConversation() {
        if (!this.currentConversation) {
            frappe.show_alert({ message: 'Please select a conversation first', indicator: 'orange' });
            return;
        }

        frappe.confirm('Are you sure you want to close this conversation?', () => {
            // Update conversation status
            const conversation = this.conversations.find(c => c.name === this.currentConversation);
            if (conversation) {
                conversation.status = 'Closed';
            }

            // Sync with ERPNext Issue
            this.syncConversationStatus(this.currentConversation, 'Closed');

            this.renderConversations();
            this.updateConversationHeader(this.currentConversation);
            frappe.show_alert({ message: 'Conversation closed', indicator: 'blue' });
        });
    }

    showCustomerData() {
        if (!this.currentConversation) {
            frappe.show_alert({ message: 'Please select a conversation first', indicator: 'orange' });
            return;
        }

        // Create customer data dialog
        const dialog = new frappe.ui.Dialog({
            title: 'Customer Information',
            size: 'large',
            fields: [
                {
                    fieldtype: 'HTML',
                    fieldname: 'customer_data',
                    label: 'Customer Data'
                }
            ]
        });

        // Load customer data
        frappe.call({
            method: 'assistant_crm.api.unified_inbox_api.get_customer_summary',
            args: {
                conversation_name: this.currentConversation
            },
            callback: (response) => {
                if (response.message && response.message.status === 'success') {
                    const data = response.message.data;
                    let html = this.generateCustomerDataHTML(data);
                    dialog.fields_dict.customer_data.$wrapper.html(html);
                } else {
                    dialog.fields_dict.customer_data.$wrapper.html('<div class="alert alert-warning">No customer data available</div>');
                }
            },
            error: (error) => {
                console.error('Error loading customer data:', error);
                dialog.fields_dict.customer_data.$wrapper.html('<div class="alert alert-danger">Error loading customer data</div>');
            }
        });

        dialog.show();
    }

    generateCustomerDataHTML(data) {
        const conversation = this.conversations.find(c => c.name === this.currentConversation);

        let html = `
            <div class="card mb-3">
                <div class="card-header">
                    <h6 class="mb-0"><i class="fa fa-comments me-2"></i>Conversation Information</h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>Customer:</strong> ${conversation?.customer_name || 'Unknown'}</p>
                            <p><strong>Platform:</strong> ${conversation?.platform}</p>
                            <p><strong>Status:</strong> <span class="badge bg-primary">${conversation?.status}</span></p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>Priority:</strong> ${conversation?.priority || 'Normal'}</p>
                            <p><strong>Phone:</strong> ${conversation?.customer_phone || 'N/A'}</p>
                            <p><strong>Agent:</strong> ${conversation?.assigned_agent || 'Unassigned'}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        if (data && data.corebusiness_data && data.corebusiness_data.has_data) {
            const customerInfo = data.corebusiness_data.customer_info;

            html += `
                <div class="card mb-3">
                    <div class="card-header bg-success text-white">
                        <h6 class="mb-0"><i class="fa fa-database me-2"></i>CoreBusiness Customer Data</h6>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>Beneficiary ID:</strong> ${customerInfo.BENEFICIARY_ID || 'N/A'}</p>
                                <p><strong>NRC Number:</strong> ${customerInfo.NRC_NUMBER || 'N/A'}</p>
                                <p><strong>Full Name:</strong> ${customerInfo.FIRST_NAME || ''} ${customerInfo.LAST_NAME || ''}</p>
                                <p><strong>Phone:</strong> ${customerInfo.PHONE_NUMBER || 'N/A'}</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Email:</strong> ${customerInfo.EMAIL_ADDRESS || 'N/A'}</p>
                                <p><strong>Employer:</strong> ${customerInfo.EMPLOYER_NAME || 'N/A'}</p>
                                <p><strong>Status:</strong> <span class="badge bg-success">${customerInfo.STATUS || 'N/A'}</span></p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else {
            html += `
                <div class="alert alert-info">
                    <i class="fa fa-info-circle me-2"></i>
                    No CoreBusiness data available for this customer.
                </div>
            `;
        }

        return html;
    }

    openIssue() {
        console.log('DEBUG: openIssue() function called');
        console.log('DEBUG: this.currentConversation:', this.currentConversation);

        if (!this.currentConversation) {
            console.log('DEBUG: No conversation selected for opening issue');
            frappe.show_alert({ message: 'Please select a conversation first', indicator: 'orange' });
            return;
        }

        const conversation = this.conversations.find(c => c.name === this.currentConversation);
        console.log('DEBUG: Found conversation for issue:', conversation);
        console.log('DEBUG: Conversation issue_id:', conversation?.issue_id);
        console.log('DEBUG: Conversation custom_issue_id:', conversation?.custom_issue_id);

        if (!conversation || (!conversation.issue_id && !conversation.custom_issue_id)) {
            console.log('DEBUG: No Issue ID found for conversation');
            console.log('DEBUG: Available conversation fields:', Object.keys(conversation || {}));
            frappe.show_alert({ message: 'No ERPNext Issue found for this conversation', indicator: 'orange' });
            return;
        }

        // Open Issue in new tab
        const issueUrl = `/app/issue/${conversation.issue_id}`;
        window.open(issueUrl, '_blank');

        frappe.show_alert({ message: `Opening ERPNext Issue ${conversation.issue_id}`, indicator: 'blue' });
    }

    comprehensiveSystemDiagnostic() {
        console.log('=== COMPREHENSIVE SYSTEM DIAGNOSTIC ===');

        // 1. Check DOM Elements
        console.log('1. DOM ELEMENTS CHECK:');
        console.log('   - Assign button exists:', $('#assign-btn').length > 0);
        console.log('   - Assign button visible:', $('#assign-btn').is(':visible'));
        console.log('   - Escalate button exists:', $('#escalate-btn').length > 0);
        console.log('   - Escalate button visible:', $('#escalate-btn').is(':visible'));
        console.log('   - Issue button exists:', $('#issue-btn').length > 0);
        console.log('   - Issue button visible:', $('#issue-btn').is(':visible'));

        // 2. Check Function Availability
        console.log('2. FUNCTION AVAILABILITY:');
        console.log('   - assignToAgent function:', typeof this.assignToAgent);
        console.log('   - escalateConversation function:', typeof this.escalateConversation);
        console.log('   - openIssue function:', typeof this.openIssue);

        // 3. DEEP ERPNext Framework Analysis
        console.log('3. DEEP ERPNEXT FRAMEWORK ANALYSIS:');
        console.log('   - frappe object:', typeof frappe);
        console.log('   - frappe.ui:', typeof frappe.ui);
        console.log('   - frappe.ui.form:', typeof frappe.ui.form);
        console.log('   - frappe.ui.Dialog:', typeof frappe.ui.Dialog);
        console.log('   - AssignToDialog:', typeof frappe.ui.form?.AssignToDialog);

        // Check if form scripts are loaded
        console.log('   - frappe.ui.form.AssignToDialog constructor:', frappe.ui.form?.AssignToDialog?.toString?.()?.substring(0, 100));

        // Check loaded scripts
        console.log('   - Loaded script tags count:', $('script').length);
        console.log('   - Scripts with "form" in src:', $('script[src*="form"]').length);
        console.log('   - Scripts with "assign" in src:', $('script[src*="assign"]').length);

        // Check frappe.require functionality
        console.log('   - frappe.require function:', typeof frappe.require);
        console.log('   - frappe.ready function:', typeof frappe.ready);

        // 4. Test ERPNext UI Components
        console.log('4. ERPNEXT UI COMPONENTS TEST:');
        try {
            // Test basic Dialog
            const testDialog = new frappe.ui.Dialog({
                title: 'Test Dialog',
                fields: [{ fieldtype: 'Data', fieldname: 'test', label: 'Test' }]
            });
            console.log('   - Basic Dialog creation: SUCCESS');
            testDialog.$wrapper.remove(); // Clean up
        } catch (dialogError) {
            console.log('   - Basic Dialog creation: FAILED -', dialogError.message);
        }

        // Test AssignToDialog specifically
        try {
            if (frappe.ui.form?.AssignToDialog) {
                console.log('   - AssignToDialog constructor exists: YES');
                // Try to create without showing
                const testAssignDialog = new frappe.ui.form.AssignToDialog({
                    obj: {}, // Minimal object
                    method: 'test_method',
                    doctype: 'Test',
                    docname: 'test'
                });
                console.log('   - AssignToDialog instantiation: SUCCESS');
            } else {
                console.log('   - AssignToDialog constructor exists: NO');
            }
        } catch (assignError) {
            console.log('   - AssignToDialog instantiation: FAILED -', assignError.message);
        }

        // 5. Check Current State
        console.log('5. CURRENT STATE:');
        console.log('   - currentConversation:', this.currentConversation);
        console.log('   - conversations array length:', this.conversations?.length || 0);

        if (this.currentConversation) {
            const conversation = this.conversations.find(c => c.name === this.currentConversation);
            console.log('   - selected conversation:', conversation);
            console.log('   - conversation issue_id:', conversation?.issue_id);
            console.log('   - conversation custom_issue_id:', conversation?.custom_issue_id);
            console.log('   - conversation status:', conversation?.status);
            console.log('   - conversation assigned_agent:', conversation?.assigned_agent);
        }

        // 6. Test API Connectivity
        console.log('6. TESTING API CONNECTIVITY:');
        this.testAPIConnectivity();

        console.log('=== END DIAGNOSTIC ===');
    }

    testAPIConnectivity() {
        // Test get_available_agents API
        frappe.call({
            method: 'assistant_crm.api.unified_inbox_api.get_available_agents',
            callback: (response) => {
                console.log('   - get_available_agents API response:', response);
            },
            error: (error) => {
                console.error('   - get_available_agents API error:', error);
            }
        });

        // Test conversations API
        frappe.call({
            method: 'assistant_crm.api.unified_inbox_api.get_conversations',
            callback: (response) => {
                console.log('   - get_conversations API response status:', response?.message?.status);
                console.log('   - get_conversations API data count:', response?.message?.data?.length || 0);
            },
            error: (error) => {
                console.error('   - get_conversations API error:', error);
            }
        });
    }

    testERPNextDependencyLoading() {
        console.log('=== TESTING ERPNEXT DEPENDENCY LOADING ===');

        // Test if we can load ERPNext form dependencies
        const requiredDependencies = [
            '/assets/frappe/js/frappe/form/form.js',
            '/assets/frappe/js/frappe/form/assign_to.js',
            '/assets/frappe/js/frappe/ui/dialog.js'
        ];

        console.log('1. CHECKING REQUIRED DEPENDENCIES:');
        requiredDependencies.forEach(dep => {
            const scriptExists = $(`script[src*="${dep.split('/').pop()}"]`).length > 0;
            console.log(`   - ${dep}: ${scriptExists ? 'LOADED' : 'MISSING'}`);
        });

        // Test frappe.require functionality
        console.log('2. TESTING FRAPPE.REQUIRE:');
        if (typeof frappe.require === 'function') {
            console.log('   - frappe.require available: YES');

            // Try to require form dependencies
            try {
                frappe.require([
                    'assets/frappe/js/frappe/form/assign_to.js'
                ], () => {
                    console.log('   - assign_to.js loaded successfully');
                    console.log('   - AssignToDialog after require:', typeof frappe.ui.form?.AssignToDialog);
                    this.testAssignmentDialogAfterLoad();
                });
            } catch (requireError) {
                console.log('   - frappe.require failed:', requireError.message);
            }
        } else {
            console.log('   - frappe.require available: NO');
        }

        // Test alternative loading methods
        console.log('3. TESTING ALTERNATIVE LOADING:');
        this.loadERPNextFormDependencies();

        console.log('=== END DEPENDENCY LOADING TEST ===');
    }

    loadERPNextFormDependencies() {
        console.log('   - Attempting to load ERPNext form dependencies...');

        // Method 1: Try to load assign_to.js directly
        const assignToScript = document.createElement('script');
        assignToScript.src = '/assets/frappe/js/frappe/form/assign_to.js';
        assignToScript.onload = () => {
            console.log('   - assign_to.js loaded via script tag');
            console.log('   - AssignToDialog now available:', typeof frappe.ui.form?.AssignToDialog);
        };
        assignToScript.onerror = () => {
            console.log('   - Failed to load assign_to.js via script tag');
        };

        // Only add if not already present
        if (!$('script[src*="assign_to.js"]').length) {
            document.head.appendChild(assignToScript);
        }
    }

    testAssignmentDialogAfterLoad() {
        console.log('4. TESTING ASSIGNMENT DIALOG AFTER DEPENDENCY LOAD:');

        setTimeout(() => {
            try {
                if (frappe.ui.form?.AssignToDialog) {
                    console.log('   - AssignToDialog now available: YES');

                    // Test actual instantiation
                    const testDialog = new frappe.ui.form.AssignToDialog({
                        obj: this,
                        method: 'assistant_crm.api.unified_inbox_api.assign_conversation_to_user',
                        doctype: 'Unified Inbox Conversation',
                        docname: 'test-conversation'
                    });

                    console.log('   - AssignToDialog instantiation: SUCCESS');
                    console.log('   - Dialog object:', testDialog);

                    // Clean up test dialog
                    if (testDialog.dialog) {
                        testDialog.dialog.hide();
                    }

                } else {
                    console.log('   - AssignToDialog still not available after load attempt');
                }
            } catch (error) {
                console.log('   - AssignToDialog test failed:', error.message);
                console.log('   - Error stack:', error.stack);
            }
        }, 1000); // Wait 1 second for loading
    }

    createCustomAssignmentDialog() {
        console.log('DEBUG: Creating custom assignment dialog as fallback');

        // Load available agents first
        frappe.call({
            method: 'assistant_crm.api.unified_inbox_api.get_available_agents',
            callback: (response) => {
                console.log('DEBUG: Agents API response for custom dialog:', response);

                if (response.message && response.message.status === 'success' && response.message.data) {
                    const agents = response.message.data;

                    // Create agent options for select field
                    const agentOptions = agents.map(agent => ({
                        label: `${agent.full_name} (${agent.email})`,
                        value: agent.email
                    }));

                    // Create custom assignment dialog using frappe.ui.Dialog
                    const assignmentDialog = new frappe.ui.Dialog({
                        title: 'Assign Conversation',
                        fields: [
                            {
                                fieldtype: 'Select',
                                fieldname: 'assigned_to',
                                label: 'Assign To',
                                options: agentOptions,
                                reqd: 1
                            },
                            {
                                fieldtype: 'Small Text',
                                fieldname: 'description',
                                label: 'Assignment Notes'
                            }
                        ],
                        primary_action_label: 'Assign',
                        primary_action: (values) => {
                            console.log('DEBUG: Custom assignment dialog values:', values);

                            if (!values.assigned_to) {
                                frappe.show_alert({ message: 'Please select an agent', indicator: 'orange' });
                                return;
                            }

                            // Call the assignment API
                            frappe.call({
                                method: 'assistant_crm.api.unified_inbox_api.assign_conversation_to_user',
                                args: {
                                    doctype: 'Unified Inbox Conversation',
                                    docname: this.currentConversation,
                                    assign_to: values.assigned_to,
                                    description: values.description || 'Assigned via Unified Inbox'
                                },
                                callback: (r) => {
                                    console.log('DEBUG: Custom assignment API response:', r);

                                    if (r && r.message) {
                                        if (r.message.status === 'success') {
                                            // Update conversation status
                                            const conversation = this.conversations.find(c => c.name === this.currentConversation);
                                            if (conversation) {
                                                conversation.status = 'Agent Assigned';
                                                conversation.assigned_agent = r.message.assigned_to;
                                                conversation.assigned_agent_name = r.message.assigned_to_name;
                                            }

                                            this.renderConversations();
                                            this.updateConversationHeader(this.currentConversation);
                                            this.syncConversationStatus(this.currentConversation, 'Agent Assigned', r.message.assigned_to);

                                            frappe.show_alert({
                                                message: `Conversation assigned to ${r.message.assigned_to_name || r.message.assigned_to}`,
                                                indicator: 'green'
                                            });

                                            assignmentDialog.hide();
                                        } else if (r.message.status === 'error') {
                                            frappe.show_alert({
                                                message: r.message.error || 'Assignment failed',
                                                indicator: 'red'
                                            });
                                        }
                                    } else {
                                        frappe.show_alert({
                                            message: 'Assignment failed - invalid response',
                                            indicator: 'red'
                                        });
                                    }
                                },
                                error: (error) => {
                                    console.error('DEBUG: Assignment API error:', error);
                                    frappe.show_alert({
                                        message: 'Assignment failed - API error',
                                        indicator: 'red'
                                    });
                                }
                            });
                        }
                    });

                    assignmentDialog.show();

                } else {
                    console.error('DEBUG: Failed to load agents for custom dialog');
                    frappe.show_alert({
                        message: 'Failed to load available agents',
                        indicator: 'red'
                    });
                }
            },
            error: (error) => {
                console.error('DEBUG: Error loading agents for custom dialog:', error);
                frappe.show_alert({
                    message: 'Error loading available agents',
                    indicator: 'red'
                });
            }
        });
    }

    generateTicketForConversation(conversationName, callback) {
        // Get conversation details
        const conversation = this.conversations.find(c => c.name === conversationName);
        if (!conversation) {
            if (callback) callback();
            return;
        }

        // Check if conversation already has an Issue ID
        if (conversation.issue_id) {
            console.log('Conversation already has Issue:', conversation.issue_id);
            // Update conversation header to show ticket button
            this.updateConversationHeader(conversationName);
            if (callback) callback();
            return;
        }

        // Get the first message to use as initial message for ticket
        let initialMessage = 'Customer inquiry';
        if (this.messages && this.messages.length > 0) {
            const firstMessage = this.messages.find(m => m.direction === 'Inbound');
            if (firstMessage) {
                initialMessage = firstMessage.message_content;
            }
        }

        console.log('DEBUG: Generating ticket immediately for conversation:', conversationName);
        console.log('DEBUG: Initial message:', initialMessage);
        console.log('DEBUG: Customer name:', conversation.customer_name);
        console.log('DEBUG: Platform:', conversation.platform);

        // Map conversation priority to Issue priority
        const priorityMapping = {
            'Normal': 'Medium',
            'High': 'High',
            'Urgent': 'High'
        };

        // Remember if conversation already had an Issue ID before API call
        const hadExistingIssue = !!conversation.issue_id;

        console.log('DEBUG: Making API call to create_issue_for_conversation');
        frappe.call({
            method: 'assistant_crm.api.unified_inbox_api.create_issue_for_conversation',
            args: {
                conversation_name: conversationName,
                customer_name: conversation.customer_name,
                platform: conversation.platform,
                initial_message: initialMessage,
                customer_phone: conversation.customer_phone,
                customer_nrc: conversation.customer_nrc,
                priority: priorityMapping[conversation.priority] || 'Medium'
            },
            callback: (response) => {
                console.log('DEBUG: API response received:', response);
                if (response.message && response.message.status === 'success') {
                    console.log('DEBUG: Issue response for conversation:', response.message.issue_id);

                    // Update conversation with real ERPNext Issue ID
                    conversation.issue_id = response.message.issue_id;

                    // Update conversation header to show ticket button
                    this.updateConversationHeader(conversationName);

                    // Only show notification for newly created Issues (not existing ones)
                    // Double check: don't show if conversation already had an Issue OR if API says it's existing
                    if (!response.message.existing && !hadExistingIssue) {
                        console.log('DEBUG: New ERPNext Issue created:', response.message.issue_id);
                        frappe.show_alert({
                            message: `ERPNext Issue ${response.message.issue_id} created`,
                            indicator: 'green'
                        });
                    } else {
                        console.log('DEBUG: Using existing Issue:', response.message.issue_id,
                            'hadExisting:', hadExistingIssue, 'apiExisting:', response.message.existing);
                    }
                } else {
                    console.error('DEBUG: Failed to generate ticket:', response.message);
                    console.error('DEBUG: Full response:', response);
                }

                // Always call callback to continue with rendering
                if (callback) callback();
            },
            error: (error) => {
                console.error('Error generating ticket:', error);
                // Always call callback to continue with rendering
                if (callback) callback();
            }
        });
    }

    syncConversationStatus(conversationName, status, assignedAgent = null) {
        // Sync conversation status with ERPNext Issue
        frappe.call({
            method: 'assistant_crm.api.unified_inbox_api.sync_conversation_issue_status',
            args: {
                conversation_name: conversationName,
                conversation_status: status,
                assigned_agent: assignedAgent
            },
            callback: (response) => {
                if (response.message && response.message.status === 'success') {
                    console.log('Issue status synced successfully:', response.message.issue_id);
                } else {
                    console.log('Issue sync response:', response.message);
                }
            },
            error: (error) => {
                console.error('Error syncing Issue status:', error);
            }
        });
    }

    addMessageToIssue(conversationName, messageContent, senderName, messageType = 'Customer') {
        // Add conversation message as comment to ERPNext Issue
        frappe.call({
            method: 'assistant_crm.api.unified_inbox_api.add_conversation_comment_to_issue',
            args: {
                conversation_name: conversationName,
                message_content: messageContent,
                sender_name: senderName,
                message_type: messageType
            },
            callback: (response) => {
                if (response.message && response.message.status === 'success') {
                    console.log('Message added to Issue successfully');
                } else {
                    console.log('Message addition response:', response.message);
                }
            },
            error: (error) => {
                console.error('Error adding message to Issue:', error);
            }
        });
    }
}
