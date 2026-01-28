/**
 * WCFCB Assistant CRM Chat Bubble
 * Floating chat interface for AI assistant
 */

class WcfcbChatBubble {
    constructor() {
        this.isOpen = false;
        this.sessionId = this.generateSessionId();
        this.messages = [];
        this.isTyping = false;
        this.isConfigured = false;
        this.configError = null;
        this.conversationId = null;
        this.agentAssigned = false;
        this.agentName = null;
        this.typingTimeout = null;
        this.realtimeEvents = {};

        // PHASE 2.1: Initialize testing mode for development
        this.enableTestingMode();

        this.init();
    }
    
    init() {
        // Check configuration before initializing
        this.checkConfiguration().then(() => {
            if (this.isConfigured) {
                this.createChatBubble();
                this.bindEvents();
                this.setupRealtimeEvents();
                this.loadChatHistory();

                // Auto-launch behavior for assistant-crm page
                if (window.location.pathname.includes('/app/assistant-crm')) {
                    setTimeout(() => {
                        this.autoLaunchCenterScreen();
                    }, 1000); // Delay to ensure page is fully loaded
                }
            } else {
                // Don't show anything when not configured - more professional
                // Verbose logging removed
            }
        }).catch((error) => {
            console.error('Anna Assistant configuration check failed:', error);
            // Don't show anything on error - more professional
            // Verbose logging removed
        });
    }
    
    generateSessionId() {
        return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    async checkConfiguration() {
        try {
            console.log("🔍 Chat bubble: Checking configuration...");
            const response = await frappe.call({
                method: 'assistant_crm.services.settings_service.validate_access',
                type: 'GET'
            });

            console.log("🔍 Configuration response:", response);

            if (response.message) {
                console.log("🔍 Response message:", response.message);
                console.log("🔍 has_access:", response.message.has_access);
                console.log("🔍 enabled:", response.message.enabled);

                this.isConfigured = response.message.has_access && response.message.enabled;
                console.log("🔍 isConfigured result:", this.isConfigured);

                if (!response.message.enabled) {
                    this.configError = 'WCFCB Assistant CRM is disabled in settings';
                    console.log("❌ Configuration error: disabled");
                } else if (!response.message.has_access) {
                    this.configError = 'You do not have permission to use WCFCB Assistant CRM';
                    console.log("❌ Configuration error: no access");
                } else {
                    console.log("✅ Configuration check passed");
                    // Additional check for API key configuration
                    const settingsResponse = await frappe.call({
                        method: 'assistant_crm.services.settings_service.get_settings',
                        type: 'GET'
                    });

                    if (settingsResponse.message && settingsResponse.message.ai_config) {
                        const aiConfig = settingsResponse.message.ai_config;
                        if (!aiConfig.api_key) {
                            this.isConfigured = false;
                            this.configError = 'AI API key not configured. Please configure in Assistant CRM Settings.';
                        }
                    }
                }
            } else {
                this.isConfigured = false;
                this.configError = 'Unable to check Assistant CRM configuration';
            }
        } catch (error) {
            console.error('❌ Configuration check error:', error);
            console.error('❌ Error details:', {
                message: error.message,
                exc_type: error.exc_type,
                stack: error.stack
            });
            this.isConfigured = false;

            // Provide more specific error messages
            if (error.exc_type === 'PermissionError') {
                this.configError = 'Authentication required. Please log in to use the chatbot.';
                console.log("❌ Permission error detected");
            } else if (error.message && error.message.includes('network')) {
                this.configError = 'Network connection error. Please check your internet connection.';
                console.log("❌ Network error detected");
            } else {
                this.configError = `Configuration check failed: ${error.message || 'Unknown error'}`;
                console.log("❌ Generic error detected");
            }
        }
    }

    // Removed disabled bubble methods - chat is completely hidden when not configured
    
    createChatBubble() {
        const chatBubbleHTML = `
            <div class="exn-chat-bubble" id="exnChatBubble">
                <!-- Chat Bubble Button -->
                <button class="exn-chat-bubble-btn" id="exnChatBubbleBtn">
                    <svg class="exn-chat-icon" viewBox="0 0 24 24">
                        <path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h4l4 4 4-4h4c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/>
                    </svg>
                    <div class="exn-chat-badge" id="exnChatBadge">1</div>
                </button>
                
                <!-- Chat Window -->
                <div class="exn-chat-window" id="exnChatWindow">
                    <!-- Chat Header -->
                    <div class="exn-chat-header">
                        <div>
                            <h4 class="exn-chat-title">This is Anna, how can I help? 😊</h4>
                            <p class="exn-chat-subtitle">Your WCFCB AI assistant</p>
                        </div>
                        <button class="exn-chat-close" id="exnChatClose">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                            </svg>
                        </button>
                    </div>
                    
                    <!-- Chat Messages -->
                    <div class="exn-chat-messages" id="exnChatMessages">
                        <div class="exn-welcome-message">
                            <div class="anna-welcome-avatar">👩‍💼</div>
                            <h4>Hi! I'm Anna, your WCFCB assistant!</h4>
                            <p>I'm here to help you with all your WCFCB needs. Ask me about:</p>
                            <ul style="text-align: left; margin: 10px 0;">
                                <li>Workers' compensation claims and benefits</li>
                                <li>Employer registration and compliance</li>
                                <li>Online payments and declarations</li>
                                <li>Safety and health guidelines</li>
                                <li>Reports and business insights</li>
                                <li>Any other WCFCB services</li>
                            </ul>
                        </div>
                    </div>
                    
                    <!-- Typing Indicator -->
                    <div class="exn-typing-indicator" id="exnTypingIndicator">
                        <span>Assistant is typing</span>
                        <div class="exn-typing-dots">
                            <div class="exn-typing-dot"></div>
                            <div class="exn-typing-dot"></div>
                            <div class="exn-typing-dot"></div>
                        </div>
                    </div>
                    
                    <!-- Chat Input -->
                    <div class="exn-chat-input-area">
                        <div class="exn-chat-input-container">
                            <textarea 
                                class="exn-chat-input" 
                                id="exnChatInput" 
                                placeholder="Type your message..."
                                rows="1"
                            ></textarea>
                            <button class="exn-chat-send-btn" id="exnChatSendBtn">
                                <svg class="exn-send-icon" viewBox="0 0 24 24">
                                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add to body
        document.body.insertAdjacentHTML('beforeend', chatBubbleHTML);
        
        // Get references
        this.bubbleBtn = document.getElementById('exnChatBubbleBtn');
        this.chatWindow = document.getElementById('exnChatWindow');
        this.chatMessages = document.getElementById('exnChatMessages');
        this.chatInput = document.getElementById('exnChatInput');
        this.sendBtn = document.getElementById('exnChatSendBtn');
        this.closeBtn = document.getElementById('exnChatClose');
        this.typingIndicator = document.getElementById('exnTypingIndicator');
        this.badge = document.getElementById('exnChatBadge');
    }
    
    bindEvents() {
        // Toggle chat window
        this.bubbleBtn.addEventListener('click', () => this.toggleChat());
        this.closeBtn.addEventListener('click', () => this.closeChat());

        // Send message
        this.sendBtn.addEventListener('click', () => this.sendMessage());

        // Enter key to send
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea
        this.chatInput.addEventListener('input', () => {
            this.autoResizeTextarea();
            this.handleTypingIndicator();
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (this.isOpen && !document.getElementById('exnChatBubble').contains(e.target)) {
                this.closeChat();
            }
        });
    }

    setupRealtimeEvents() {
        // Setup real-time event listeners for live communication
        if (window.frappe && frappe.realtime) {
            // Listen for incoming messages
            frappe.realtime.on('omnichannel_message', (data) => {
                if (data.channel_id === this.sessionId) {
                    this.handleIncomingMessage(data);
                }
            });

            // Listen for agent assignment
            frappe.realtime.on('agent_assigned_notification', (data) => {
                if (data.conversation_id === this.conversationId) {
                    this.handleAgentAssignment(data);
                }
            });

            // Listen for typing indicators
            frappe.realtime.on('typing_indicator', (data) => {
                if (data.conversation_id === this.conversationId && data.user_id !== frappe.session.user) {
                    this.handleTypingIndicator(data);
                }
            });

            // Listen for conversation updates
            frappe.realtime.on('conversation_update', (data) => {
                if (data.conversation_id === this.conversationId) {
                    this.handleConversationUpdate(data);
                }
            });

            // Join conversation room when chat opens
            this.realtimeEvents.joinRoom = () => {
                if (this.conversationId) {
                    frappe.call({
                        method: 'assistant_crm.services.realtime_service.join_conversation_room',
                        args: { conversation_id: this.conversationId }
                    });
                }
            };
        }
    }
    
    toggleChat() {
        if (this.isOpen) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }
    
    openChat() {
        this.isOpen = true;
        this.chatWindow.classList.add('show');
        this.bubbleBtn.classList.add('active');
        this.badge.classList.remove('show');
        this.chatInput.focus();
    }
    
    closeChat() {
        this.isOpen = false;
        this.chatWindow.classList.remove('show');
        this.chatWindow.classList.remove('center-screen');
        this.bubbleBtn.classList.remove('active');
    }

    autoLaunchCenterScreen() {
        // Auto-launch chat in center of screen for assistant-crm page
        this.isOpen = true;
        this.chatWindow.classList.add('show');
        this.chatWindow.classList.add('center-screen');
        this.bubbleBtn.classList.add('active');
        this.badge.classList.remove('show');
        this.chatInput.focus();
    }
    
    autoResizeTextarea() {
        this.chatInput.style.height = 'auto';
        this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 100) + 'px';
    }
    
    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || this.isTyping) return;
        
        // Add user message to UI
        this.addMessage(message, 'user');
        this.chatInput.value = '';
        this.autoResizeTextarea();
        
        // Show typing indicator
        this.showTyping();
        
        try {
            // Send to API
            const response = await this.callChatAPI(message);
            
            if (response.success) {
                this.addMessage(response.response, 'assistant');
            } else {
                // Handle configuration errors specially
                if (response.config_error) {
                    this.addMessage(response.error, 'assistant', true);
                    this.showConfigurationMessage();
                } else {
                    this.addMessage(response.error || 'Sorry, I encountered an error. Please try again.', 'assistant', true);
                }
            }
        } catch (error) {
            console.error('Chat error:', error);
            this.addMessage('Sorry, I\'m having trouble connecting. Please try again later.', 'assistant', true);
        } finally {
            this.hideTyping();
        }
    }
    
    async callChatAPI(message) {
        // PHASE 2.1: Frontend API Migration with A/B Testing and Fallback
        const useOptimizedAPI = this.shouldUseOptimizedAPI();

        // Verbose API selection logging removed

        if (useOptimizedAPI) {
            // Try optimized API first
            const optimizedResult = await this.callOptimizedChatAPI(message);

            if (optimizedResult.success) {
                // Verbose success logging removed
                return optimizedResult;
            } else {
                // Verbose fallback logging removed
                // Fallback to legacy API
                return await this.callLegacyChatAPI(message, 'optimized_fallback');
            }
        } else {
            // Use legacy API directly
            return await this.callLegacyChatAPI(message, 'legacy_direct');
        }
    }

    shouldUseOptimizedAPI() {
        // PHASE 2.1: A/B Testing Logic - Start with 10% traffic

        // Check for feature flag override
        const urlParams = new URLSearchParams(window.location.search);
        const forceOptimized = urlParams.get('force_optimized');
        const forceLegacy = urlParams.get('force_legacy');

        if (forceOptimized === 'true') {
            // Verbose URL parameter logging removed
            return true;
        }

        if (forceLegacy === 'true') {
            // Verbose URL parameter logging removed
            return false;
        }

        // Check localStorage for user preference (for testing)
        const userPreference = localStorage.getItem('assistant_crm_api_preference');
        if (userPreference === 'optimized') {
            // Verbose user preference logging removed
            return true;
        }
        if (userPreference === 'legacy') {
            // Verbose user preference logging removed
            return false;
        }

        // PHASE 3.1 COMPLETE: 100% traffic to optimized API
        // All traffic now uses optimized system with legacy fallback
        const useOptimized = true; // 100% traffic - PHASE 3 SCALING COMPLETE

        // Verbose phase completion logging removed
        return useOptimized;
    }

    hashCode(str) {
        // Simple hash function for consistent A/B testing
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return hash;
    }

    async callOptimizedChatAPI(message) {
        const startTime = Date.now();

        try {
            // Verbose API call logging removed

            const response = await frappe.call({
                method: 'assistant_crm.api.simplified_chat.send_message',
                args: {
                    message: message,
                    session_id: this.sessionId,
                    user_context: {
                        user_name: frappe.session.user_fullname || frappe.session.user,
                        interaction_frequency: 'returning',
                        frontend_version: 'phase2_migration'
                    }
                }
            });

            const responseTime = Date.now() - startTime;

            if (response.message && response.message.success) {
                // Log successful optimized response
                this.logAPIUsage('optimized', 'success', responseTime, {
                    wordCount: response.message.response ? response.message.response.split(' ').length : 0,
                    model: response.message.context_data?.model
                });

                return {
                    ...response.message,
                    responseTime: responseTime
                };
            } else {
                // Log optimized API failure
                this.logAPIUsage('optimized', 'failure', responseTime, {
                    error: response.message?.error || 'Unknown error'
                });

                return {
                    success: false,
                    error: response.message?.error || 'Optimized API returned unsuccessful response',
                    responseTime: responseTime
                };
            }
        } catch (error) {
            const responseTime = Date.now() - startTime;
            console.error('[PHASE 2] Optimized Chat API Error:', error);

            // Log optimized API error
            this.logAPIUsage('optimized', 'error', responseTime, {
                error: error.message || error.toString()
            });

            return {
                success: false,
                error: 'Failed to connect to the optimized assistant. Falling back to standard service.',
                responseTime: responseTime
            };
        }
    }

    async callLegacyChatAPI(message, reason = 'direct') {
        const startTime = Date.now();

        try {
            // Verbose API call logging removed

            const response = await frappe.call({
                method: 'assistant_crm.api.simplified_chat.send_message',
                args: {
                    message: message,
                    session_id: this.sessionId
                }
            });

            const responseTime = Date.now() - startTime;

            // Log legacy API usage
            this.logAPIUsage('legacy', 'success', responseTime, {
                reason: reason,
                wordCount: response.message?.response ? response.message.response.split(' ').length : 0
            });

            return {
                ...response.message,
                responseTime: responseTime
            };
        } catch (error) {
            const responseTime = Date.now() - startTime;
            console.error('[PHASE 2] Legacy Chat API Error:', error);

            // Log legacy API error
            this.logAPIUsage('legacy', 'error', responseTime, {
                reason: reason,
                error: error.message || error.toString()
            });

            return {
                success: false,
                error: 'Failed to connect to the assistant. Please try again.',
                responseTime: responseTime
            };
        }
    }

    logAPIUsage(apiType, status, responseTime, metadata = {}) {
        // PHASE 2.1: Comprehensive logging for monitoring
        const logData = {
            timestamp: new Date().toISOString(),
            apiType: apiType, // 'optimized' or 'legacy'
            status: status, // 'success', 'failure', 'error'
            responseTime: responseTime,
            sessionId: this.sessionId,
            userAgent: navigator.userAgent,
            ...metadata
        };

        // Verbose API usage logging removed

        // Store in localStorage for analysis (keep last 100 entries)
        try {
            const logs = JSON.parse(localStorage.getItem('assistant_crm_api_logs') || '[]');
            logs.push(logData);

            // Keep only last 100 entries
            if (logs.length > 100) {
                logs.splice(0, logs.length - 100);
            }

            localStorage.setItem('assistant_crm_api_logs', JSON.stringify(logs));
        } catch (e) {
            // Verbose log storage warning removed
        }

        // Send to server for monitoring (non-blocking)
        this.sendAPILogToServer(logData);
    }

    async sendAPILogToServer(logData) {
        // PHASE 2.1: Send usage data to server for monitoring
        try {
            // Non-blocking server logging
            setTimeout(async () => {
                try {
                    await frappe.call({
                        method: 'assistant_crm.api.simplified_chat.get_chat_status',
                        args: { log_data: logData },
                        no_spinner: true
                    });
                } catch (e) {
                    // Silently fail - don't disrupt user experience
                    // Verbose server logging debug removed
                }
            }, 100);
        } catch (e) {
            // Silently fail
            // Verbose server logging schedule debug removed
        }
    }

    // PHASE 2.1: Utility functions for testing and monitoring
    getAPIUsageLogs() {
        // Get stored API usage logs for analysis
        try {
            const logs = JSON.parse(localStorage.getItem('assistant_crm_api_logs') || '[]');
            return logs;
        } catch (e) {
            console.error('[PHASE 2] Failed to retrieve API logs:', e);
            return [];
        }
    }

    getAPIUsageStats() {
        // Calculate usage statistics from stored logs
        const logs = this.getAPIUsageLogs();

        if (logs.length === 0) {
            return {
                totalRequests: 0,
                optimizedRequests: 0,
                legacyRequests: 0,
                averageResponseTime: 0,
                successRate: 0
            };
        }

        const optimizedLogs = logs.filter(log => log.apiType === 'optimized');
        const legacyLogs = logs.filter(log => log.apiType === 'legacy');
        const successfulLogs = logs.filter(log => log.status === 'success');

        const totalResponseTime = logs.reduce((sum, log) => sum + (log.responseTime || 0), 0);
        const averageResponseTime = totalResponseTime / logs.length;

        return {
            totalRequests: logs.length,
            optimizedRequests: optimizedLogs.length,
            legacyRequests: legacyLogs.length,
            optimizedPercentage: ((optimizedLogs.length / logs.length) * 100).toFixed(1),
            averageResponseTime: Math.round(averageResponseTime),
            successRate: ((successfulLogs.length / logs.length) * 100).toFixed(1),
            lastUpdated: new Date().toISOString()
        };
    }

    clearAPIUsageLogs() {
        // Clear stored API usage logs
        try {
            localStorage.removeItem('assistant_crm_api_logs');
            // Verbose log clearing notification removed
            return true;
        } catch (e) {
            console.error('[PHASE 2] Failed to clear API logs:', e);
            return false;
        }
    }

    setAPIPreference(preference) {
        // Set user preference for API (for testing)
        // preference: 'optimized', 'legacy', or null (remove preference)
        try {
            if (preference === null || preference === 'auto') {
                localStorage.removeItem('assistant_crm_api_preference');
                // Verbose preference clearing notification removed
            } else if (preference === 'optimized' || preference === 'legacy') {
                localStorage.setItem('assistant_crm_api_preference', preference);
                // Verbose preference setting notification removed
            } else {
                console.error('[PHASE 2] Invalid API preference:', preference);
                return false;
            }
            return true;
        } catch (e) {
            console.error('[PHASE 2] Failed to set API preference:', e);
            return false;
        }
    }

    getAPIPreference() {
        // Get current API preference
        try {
            return localStorage.getItem('assistant_crm_api_preference') || 'auto';
        } catch (e) {
            console.error('[PHASE 2] Failed to get API preference:', e);
            return 'auto';
        }
    }

    // PHASE 2.1: Testing utilities (available in browser console)
    enableTestingMode() {
        // Enable testing mode with additional logging
        window.assistantCRMTesting = {
            getStats: () => this.getAPIUsageStats(),
            getLogs: () => this.getAPIUsageLogs(),
            clearLogs: () => this.clearAPIUsageLogs(),
            setPreference: (pref) => this.setAPIPreference(pref),
            getPreference: () => this.getAPIPreference(),
            forceOptimized: () => this.setAPIPreference('optimized'),
            forceLegacy: () => this.setAPIPreference('legacy'),
            enableAB: () => this.setAPIPreference('auto'),
            testMessage: async (msg) => {
                // Verbose test message logging removed
                return await this.callChatAPI(msg || 'Hello, this is a test message');
            }
        };

        // Verbose testing mode instructions removed
    }
    
    addMessage(text, sender, isError = false, data = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `exn-chat-message ${sender}`;

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = `exn-message-bubble ${sender}${isError ? ' error' : ''}`;

        // Check if this is a financial/budget response with structured data
        if (sender === 'assistant' && data && this.isFinancialData(data)) {
            bubbleDiv.innerHTML = this.formatFinancialResponse(text, data);
        } else if (sender === 'assistant' && this.containsMarkdown(text)) {
            // Parse and render markdown for assistant responses
            bubbleDiv.innerHTML = this.parseMarkdown(text);
        } else {
            bubbleDiv.textContent = text;
        }

        const timeDiv = document.createElement('div');
        timeDiv.className = 'exn-message-time';
        timeDiv.textContent = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

        messageDiv.appendChild(bubbleDiv);
        messageDiv.appendChild(timeDiv);

        // Remove welcome message if it exists
        const welcomeMsg = this.chatMessages.querySelector('.exn-welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();

        // Store message
        this.messages.push({
            text: text,
            sender: sender,
            timestamp: new Date(),
            isError: isError,
            data: data
        });
    }
    
    showTyping() {
        this.isTyping = true;
        this.typingIndicator.classList.add('show');
        this.sendBtn.disabled = true;
        this.scrollToBottom();
    }
    
    hideTyping() {
        this.isTyping = false;
        this.typingIndicator.classList.remove('show');
        this.sendBtn.disabled = false;
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }

    // Real-time event handlers
    handleIncomingMessage(data) {
        if (data.sender !== 'user') {
            this.addMessage(data.message, 'assistant', false, data.metadata);
            this.hideTyping();
        }
    }

    handleAgentAssignment(data) {
        this.agentAssigned = true;
        this.agentName = data.agent_name;
        this.conversationId = data.conversation_id;

        // Update chat header to show agent name
        const chatTitle = document.querySelector('.exn-chat-title');
        if (chatTitle) {
            chatTitle.textContent = `${data.agent_name} - WCFCB Assistant`;
        }

        // Add agent assignment message
        this.addMessage(data.message, 'assistant');

        // Join conversation room for real-time updates
        if (this.realtimeEvents.joinRoom) {
            this.realtimeEvents.joinRoom();
        }
    }

    handleTypingIndicator(data) {
        if (data && data.is_typing) {
            this.showAgentTyping(data.user_id);
        } else {
            this.hideAgentTyping();
        }
    }

    handleConversationUpdate(data) {
        // Handle conversation status changes, escalations, etc.
        if (data.update_type === 'status_change') {
            this.updateConversationStatus(data.data.new_status);
        } else if (data.update_type === 'escalation') {
            this.handleEscalation(data.data);
        }
    }

    // Typing indicator management
    handleTypingIndicator() {
        // Clear existing timeout
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }

        // Send typing start
        this.sendTypingStatus(true);

        // Set timeout to send typing stop
        this.typingTimeout = setTimeout(() => {
            this.sendTypingStatus(false);
        }, 3000);
    }

    sendTypingStatus(isTyping) {
        if (this.conversationId && window.frappe) {
            frappe.call({
                method: 'assistant_crm.services.realtime_service.update_typing_status',
                args: {
                    conversation_id: this.conversationId,
                    is_typing: isTyping
                }
            });
        }
    }

    showAgentTyping(agentId) {
        const existingIndicator = this.chatMessages.querySelector('.agent-typing-indicator');
        if (!existingIndicator) {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'exn-chat-message assistant agent-typing-indicator';
            typingDiv.innerHTML = `
                <div class="exn-message-bubble assistant">
                    <div class="typing-animation">
                        <span></span><span></span><span></span>
                    </div>
                    <small>${this.agentName || 'Agent'} is typing...</small>
                </div>
            `;
            this.chatMessages.appendChild(typingDiv);
            this.scrollToBottom();
        }
    }

    hideAgentTyping() {
        const typingIndicator = this.chatMessages.querySelector('.agent-typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    updateConversationStatus(status) {
        // Update UI based on conversation status
        const statusIndicator = document.querySelector('.conversation-status');
        if (statusIndicator) {
            statusIndicator.textContent = status;
        }
    }

    handleEscalation(escalationData) {
        // Show escalation notification
        this.addMessage(
            `Your conversation has been escalated to ${escalationData.escalated_to || 'a supervisor'} for specialized assistance.`,
            'assistant'
        );
    }
    
    async loadChatHistory() {
        try {
            const response = await frappe.call({
                method: 'assistant_crm.api.simplified_chat.get_chat_status',
                args: {
                    session_id: this.sessionId,
                    limit: 20
                }
            });
            
            if (response.message.success && response.message.history.length > 0) {
                // Clear welcome message
                const welcomeMsg = this.chatMessages.querySelector('.exn-welcome-message');
                if (welcomeMsg) {
                    welcomeMsg.remove();
                }
                
                // Add historical messages
                response.message.history.reverse().forEach(chat => {
                    if (chat.message) {
                        this.addMessage(chat.message, 'user');
                    }
                    if (chat.response) {
                        this.addMessage(chat.response, 'assistant');
                    }
                });
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }

    isFinancialData(data) {
        // Check if data contains financial/budget information
        return data && (
            data.budgets ||
            data.budget_vs_actual ||
            data.financial_kpis ||
            data.accounts ||
            data.summary ||
            data.alerts
        );
    }

    formatFinancialResponse(text, data) {
        let html = `<div class="exn-financial-response">`;
        html += `<p>${text}</p>`;

        // Add budget cards if available
        if (data.budgets && data.budgets.length > 0) {
            html += this.createBudgetCards(data.budgets.slice(0, 3)); // Show top 3
        }

        // Add budget vs actual comparison
        if (data.budget_vs_actual) {
            html += this.createBudgetComparison(data.budget_vs_actual);
        }

        // Add financial KPIs
        if (data.financial_kpis) {
            html += this.createKPICards(data.financial_kpis);
        }

        // Add account spending table
        if (data.accounts && data.accounts.length > 0) {
            html += this.createSpendingTable(data.accounts.slice(0, 5)); // Show top 5
        }

        // Add budget alerts
        if (data.alerts && data.alerts.length > 0) {
            html += this.createBudgetAlerts(data.alerts);
        }

        html += `</div>`;
        return html;
    }

    createBudgetCards(budgets) {
        let html = '<div class="exn-budget-cards">';

        budgets.forEach(budget => {
            const utilization = budget.utilization_percent || 0;
            const statusClass = this.getBudgetStatusClass(utilization);

            html += `
                <div class="exn-budget-card">
                    <div class="exn-budget-header">
                        <h4 class="exn-budget-title">${budget.cost_center || budget.budget_name || 'Budget'}</h4>
                        <span class="exn-budget-amount">${this.formatCurrency(budget.total_budget || 0)}</span>
                    </div>
                    <div class="exn-budget-progress">
                        <div class="exn-budget-progress-bar ${statusClass}" style="width: ${Math.min(utilization, 100)}%"></div>
                    </div>
                    <div class="exn-budget-stats">
                        <div class="exn-budget-stat">
                            <span class="exn-budget-stat-value">${this.formatCurrency(budget.total_actual || 0)}</span>
                            <span class="exn-budget-stat-label">Spent</span>
                        </div>
                        <div class="exn-budget-stat">
                            <span class="exn-budget-stat-value">${utilization.toFixed(1)}%</span>
                            <span class="exn-budget-stat-label">Used</span>
                        </div>
                        <div class="exn-budget-stat">
                            <span class="exn-budget-stat-value">${this.formatCurrency(budget.remaining_budget || 0)}</span>
                            <span class="exn-budget-stat-label">Remaining</span>
                        </div>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        return html;
    }

    createBudgetComparison(comparison) {
        const utilization = comparison.utilization_percent || 0;
        const variance = comparison.variance || 0;

        return `
            <div class="exn-budget-comparison">
                <h4>Budget vs Actual</h4>
                <div class="exn-kpi-grid">
                    <div class="exn-kpi-card">
                        <div class="exn-kpi-value">${this.formatCurrency(comparison.total_budget || 0)}</div>
                        <div class="exn-kpi-label">Total Budget</div>
                    </div>
                    <div class="exn-kpi-card">
                        <div class="exn-kpi-value">${this.formatCurrency(comparison.total_actual || 0)}</div>
                        <div class="exn-kpi-label">Actual Spent</div>
                    </div>
                    <div class="exn-kpi-card">
                        <div class="exn-kpi-value ${variance >= 0 ? 'positive' : 'negative'}">${this.formatCurrency(variance)}</div>
                        <div class="exn-kpi-label">Variance</div>
                    </div>
                    <div class="exn-kpi-card">
                        <div class="exn-kpi-value">${utilization.toFixed(1)}%</div>
                        <div class="exn-kpi-label">Utilization</div>
                    </div>
                </div>
            </div>
        `;
    }

    createKPICards(kpis) {
        return `
            <div class="exn-kpi-section">
                <h4>Financial KPIs</h4>
                <div class="exn-kpi-grid">
                    <div class="exn-kpi-card">
                        <div class="exn-kpi-value">${kpis.total_budget_lines || 0}</div>
                        <div class="exn-kpi-label">Budget Lines</div>
                    </div>
                    <div class="exn-kpi-card">
                        <div class="exn-kpi-value">${(kpis.overall_utilization_percent || 0).toFixed(1)}%</div>
                        <div class="exn-kpi-label">Overall Utilization</div>
                    </div>
                    <div class="exn-kpi-card">
                        <div class="exn-kpi-value positive">${this.formatCurrency(kpis.savings_achieved || 0)}</div>
                        <div class="exn-kpi-label">Savings</div>
                    </div>
                    <div class="exn-kpi-card">
                        <div class="exn-kpi-value ${(kpis.overspend_amount || 0) > 0 ? 'negative' : ''}">${this.formatCurrency(kpis.overspend_amount || 0)}</div>
                        <div class="exn-kpi-label">Overspend</div>
                    </div>
                </div>
            </div>
        `;
    }

    createSpendingTable(accounts) {
        let html = `
            <div class="exn-spending-table">
                <h4>Top Spending Accounts</h4>
                <table class="exn-financial-table">
                    <thead>
                        <tr>
                            <th>Account</th>
                            <th class="amount">Budget</th>
                            <th class="amount">Actual</th>
                            <th class="amount">Variance</th>
                            <th class="amount">Utilization</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        accounts.forEach(account => {
            const variance = account.variance || 0;
            const utilization = account.utilization_percent || 0;
            const varianceClass = variance >= 0 ? 'positive' : 'negative';
            const utilizationClass = utilization > 100 ? 'negative' : utilization > 90 ? 'warning' : 'positive';

            html += `
                <tr>
                    <td>${account.account_name || account.account || 'Unknown'}</td>
                    <td class="amount">${this.formatCurrency(account.budget_amount || 0)}</td>
                    <td class="amount">${this.formatCurrency(account.actual_spending || 0)}</td>
                    <td class="amount ${varianceClass}">${this.formatCurrency(variance)}</td>
                    <td class="amount ${utilizationClass}">${utilization.toFixed(1)}%</td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        return html;
    }

    createBudgetAlerts(alerts) {
        let html = '<div class="exn-budget-alerts"><h4>Budget Alerts</h4>';

        alerts.forEach(alert => {
            const alertClass = alert.type || 'info';
            html += `
                <div class="exn-budget-alert ${alertClass}">
                    <div class="exn-budget-alert-icon">⚠️</div>
                    <div>
                        <strong>${alert.account || 'Budget Alert'}</strong><br>
                        ${alert.message || 'No details available'}
                    </div>
                </div>
            `;
        });

        html += '</div>';
        return html;
    }

    getBudgetStatusClass(utilization) {
        if (utilization > 100) return 'over-budget';
        if (utilization > 90) return 'near-limit';
        return 'on-track';
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount || 0);
    }

    containsMarkdown(text) {
        // Check if text contains markdown patterns
        const markdownPatterns = [
            /\*\*.*?\*\*/,           // Bold text
            /\*.*?\*/,               // Italic text
            /^#{1,6}\s/m,            // Headers
            /^\s*[-*+]\s/m,          // Unordered lists
            /^\s*\d+\.\s/m,          // Ordered lists
            /^\|.*\|$/m,             // Tables
            /```[\s\S]*?```/,        // Code blocks
            /`.*?`/,                 // Inline code
            /^\s*>\s/m,              // Blockquotes
            /---+/,                  // Horizontal rules
            /\[.*?\]\(.*?\)/         // Links
        ];

        return markdownPatterns.some(pattern => pattern.test(text));
    }

    parseMarkdown(text) {
        // Simple markdown parser for chat messages
        let html = text;

        // Headers (h1-h6)
        html = html.replace(/^### (.*$)/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gm, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gm, '<h1>$1</h1>');

        // Bold text
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Italic text
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

        // Inline code
        html = html.replace(/`(.*?)`/g, '<code>$1</code>');

        // Links
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

        // Horizontal rules
        html = html.replace(/^---+$/gm, '<hr>');

        // Parse tables
        html = this.parseTables(html);

        // Parse lists
        html = this.parseLists(html);

        // Parse blockquotes
        html = html.replace(/^>\s(.*)$/gm, '<blockquote>$1</blockquote>');

        // Convert line breaks
        html = html.replace(/\n/g, '<br>');

        // Clean up multiple <br> tags
        html = html.replace(/(<br>\s*){3,}/g, '<br><br>');

        return html;
    }

    parseTables(html) {
        // Parse markdown tables
        const tableRegex = /^(\|.*\|)\n(\|[-\s|:]+\|)\n((?:\|.*\|\n?)*)/gm;

        return html.replace(tableRegex, (match, header, separator, rows) => {
            let tableHtml = '<table class="exn-markdown-table">';

            // Parse header
            const headerCells = header.split('|').slice(1, -1).map(cell => cell.trim());
            tableHtml += '<thead><tr>';
            headerCells.forEach(cell => {
                tableHtml += `<th>${cell}</th>`;
            });
            tableHtml += '</tr></thead>';

            // Parse rows
            tableHtml += '<tbody>';
            const rowLines = rows.trim().split('\n');
            rowLines.forEach(row => {
                if (row.trim()) {
                    const cells = row.split('|').slice(1, -1).map(cell => cell.trim());
                    tableHtml += '<tr>';
                    cells.forEach(cell => {
                        tableHtml += `<td>${cell}</td>`;
                    });
                    tableHtml += '</tr>';
                }
            });
            tableHtml += '</tbody></table>';

            return tableHtml;
        });
    }

    parseLists(html) {
        // Parse unordered lists
        html = html.replace(/^(\s*[-*+]\s.*(?:\n\s*[-*+]\s.*)*)/gm, (match) => {
            const items = match.split('\n').map(line => {
                const trimmed = line.trim();
                if (trimmed.match(/^[-*+]\s/)) {
                    return `<li>${trimmed.substring(2)}</li>`;
                }
                return '';
            }).filter(item => item);

            return `<ul class="exn-markdown-list">${items.join('')}</ul>`;
        });

        // Parse ordered lists
        html = html.replace(/^(\s*\d+\.\s.*(?:\n\s*\d+\.\s.*)*)/gm, (match) => {
            const items = match.split('\n').map(line => {
                const trimmed = line.trim();
                if (trimmed.match(/^\d+\.\s/)) {
                    return `<li>${trimmed.replace(/^\d+\.\s/, '')}</li>`;
                }
                return '';
            }).filter(item => item);

            return `<ol class="exn-markdown-list">${items.join('')}</ol>`;
        });

        return html;
    }

    // Enhanced progress bar parsing
    parseProgressBars(html) {
        // Convert █ and ░ characters to visual progress bars
        const progressRegex = /([█░]+)\s*(\d+\.?\d*%)/g;

        return html.replace(progressRegex, (match, bar, percentage) => {
            const filled = (bar.match(/█/g) || []).length;
            const total = bar.length;
            const percent = (filled / total) * 100;

            return `<div class="exn-progress-container">
                <div class="exn-progress-bar-visual" style="width: 100%; height: 8px; background: #f1f3f4; border-radius: 4px; overflow: hidden;">
                    <div class="exn-progress-fill" style="width: ${percent}%; height: 100%; background: linear-gradient(90deg, #4caf50 0%, #ff9800 70%, #f44336 90%); transition: width 0.3s ease;"></div>
                </div>
                <span class="exn-progress-text" style="font-size: 12px; color: #666; margin-left: 8px;">${percentage}</span>
            </div>`;
        });
    }

    // Enhanced status indicator parsing
    parseStatusIndicators(html) {
        // Convert emoji status indicators to styled elements
        const statusMap = {
            '🔴': '<span class="exn-status-indicator red"></span>',
            '🟡': '<span class="exn-status-indicator yellow"></span>',
            '🟢': '<span class="exn-status-indicator green"></span>',
            '🔵': '<span class="exn-status-indicator blue"></span>',
            '✅': '<span class="exn-status-check">✅</span>',
            '❌': '<span class="exn-status-error">❌</span>',
            '⚠️': '<span class="exn-status-warning">⚠️</span>'
        };

        for (const [emoji, replacement] of Object.entries(statusMap)) {
            html = html.replace(new RegExp(emoji, 'g'), replacement);
        }

        return html;
    }
}

// Global table sorting function
function sortTable(columnIndex, tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;

    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const header = table.querySelectorAll('th')[columnIndex];

    // Determine sort direction
    const isAscending = !header.classList.contains('sort-asc');

    // Clear all sort classes
    table.querySelectorAll('th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });

    // Add appropriate sort class
    header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');

    // Sort rows
    rows.sort((a, b) => {
        const aText = a.cells[columnIndex].textContent.trim();
        const bText = b.cells[columnIndex].textContent.trim();

        // Try to parse as numbers
        const aNum = parseFloat(aText.replace(/[^0-9.-]/g, ''));
        const bNum = parseFloat(bText.replace(/[^0-9.-]/g, ''));

        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAscending ? aNum - bNum : bNum - aNum;
        } else {
            return isAscending ? aText.localeCompare(bText) : bText.localeCompare(aText);
        }
    });

    // Reorder rows in DOM
    rows.forEach(row => tbody.appendChild(row));
}

// Initialize chat bubble when DOM is ready
$(document).ready(function() {
    console.log("🔍 Chat bubble DOM ready - checking initialization conditions");
    console.log("window.frappe available:", typeof window.frappe !== 'undefined');
    console.log("frappe.boot available:", window.frappe && typeof frappe.boot !== 'undefined');
    console.log("Current path:", window.location.pathname);

    // Initialize on desk pages for both authenticated and guest users
    if (window.frappe && frappe.boot) {
        console.log("✅ Creating WcfcbChatBubble instance");
        // Always initialize - the chat bubble will handle authentication internally
        window.wcfcbChatBubble = new WcfcbChatBubble();
        console.log("✅ WcfcbChatBubble created:", typeof window.wcfcbChatBubble);
    } else {
        console.log("❌ Cannot create chat bubble - frappe not ready");
    }
});

// Also provide a manual initialization function
window.initializeWcfcbChatBubble = function() {
    console.log("🔧 Manual chat bubble initialization called");
    if (!window.wcfcbChatBubble) {
        console.log("Creating new chat bubble instance");
        window.wcfcbChatBubble = new WcfcbChatBubble();
    } else {
        console.log("Chat bubble already exists");
    }
    return window.wcfcbChatBubble;
};
