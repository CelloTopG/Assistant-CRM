/**
 * WCFCB VoIP Widget - Embedded Softphone for Assistant CRM
 * Provides SIP-based calling functionality directly in the CRM interface
 */

class WCFCBVoIPWidget {
    constructor() {
        this.isInitialized = false;
        this.sipSession = null;
        this.currentCall = null;
        this.userAgent = null;
        this.sipConfig = null;
        this.agentCredentials = null;
        
        this.init();
    }
    
    async init() {
        try {
            // Load SIP.js library if not already loaded
            if (typeof SIP === 'undefined') {
                await this.loadSIPLibrary();
            }
            
            // Get SIP configuration from server
            await this.loadSIPConfiguration();
            
            // Initialize SIP User Agent
            this.initializeSIPAgent();
            
            // Create widget UI
            this.createWidget();
            
            // Set up event listeners
            this.setupEventListeners();
            
            this.isInitialized = true;
            // Verbose initialization logging removed
            
        } catch (error) {
            console.error('Failed to initialize VoIP widget:', error);
            this.showError('Failed to initialize VoIP functionality');
        }
    }
    
    async loadSIPLibrary() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/sip.js@0.21.2/lib/platform/web/sip.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
    
    async loadSIPConfiguration() {
        try {
            const response = await frappe.call({
                method: 'assistant_crm.api.voip_api.get_sip_configuration'
            });
            
            if (response.message.success) {
                this.sipConfig = response.message.sip_config;
                this.agentCredentials = response.message.agent_credentials;
            } else {
                throw new Error(response.message.error || 'Failed to load SIP configuration');
            }
        } catch (error) {
            console.error('Error loading SIP configuration:', error);
            throw error;
        }
    }
    
    initializeSIPAgent() {
        try {
            const uri = SIP.UserAgent.makeURI(`sip:${this.agentCredentials.username}@${this.sipConfig.sip_domain}`);
            
            const userAgentOptions = {
                uri: uri,
                transportOptions: {
                    server: this.sipConfig.websocket_url,
                    connectionTimeout: 30,
                    maxReconnectionAttempts: 5,
                    reconnectionTimeout: 4
                },
                authorizationUsername: this.agentCredentials.username,
                authorizationPassword: this.agentCredentials.password,
                displayName: this.agentCredentials.display_name,
                logBuiltinEnabled: false,
                sessionDescriptionHandlerFactoryOptions: {
                    constraints: {
                        audio: true,
                        video: false
                    },
                    peerConnectionConfiguration: {
                        iceServers: JSON.parse(this.sipConfig.ice_servers || '[{"urls": "stun:stun.l.google.com:19302"}]')
                    }
                }
            };
            
            this.userAgent = new SIP.UserAgent(userAgentOptions);
            
            // Set up User Agent event handlers
            this.userAgent.delegate = {
                onConnect: () => {
                    // Verbose connection logging removed
                    this.updateConnectionStatus('connected');
                },
                onDisconnect: (error) => {
                    // Verbose disconnection logging removed
                    this.updateConnectionStatus('disconnected');
                },
                onInvite: (invitation) => {
                    this.handleIncomingCall(invitation);
                }
            };
            
        } catch (error) {
            console.error('Error initializing SIP agent:', error);
            throw error;
        }
    }
    
    createWidget() {
        // Create widget container
        const widget = $(`
            <div id="wcfcb-voip-widget" class="voip-widget">
                <div class="voip-header">
                    <span class="voip-title">WCFCB Phone</span>
                    <span class="voip-status" id="voip-status">Disconnected</span>
                    <button class="voip-minimize" id="voip-minimize">−</button>
                </div>
                <div class="voip-content" id="voip-content">
                    <div class="voip-dialer" id="voip-dialer">
                        <input type="text" id="phone-input" placeholder="Enter phone number" class="form-control">
                        <div class="voip-buttons">
                            <button class="btn btn-success" id="call-button">📞 Call</button>
                            <button class="btn btn-secondary" id="search-button">🔍 Search</button>
                        </div>
                        <div class="voip-keypad">
                            <div class="keypad-row">
                                <button class="keypad-btn" data-digit="1">1</button>
                                <button class="keypad-btn" data-digit="2">2</button>
                                <button class="keypad-btn" data-digit="3">3</button>
                            </div>
                            <div class="keypad-row">
                                <button class="keypad-btn" data-digit="4">4</button>
                                <button class="keypad-btn" data-digit="5">5</button>
                                <button class="keypad-btn" data-digit="6">6</button>
                            </div>
                            <div class="keypad-row">
                                <button class="keypad-btn" data-digit="7">7</button>
                                <button class="keypad-btn" data-digit="8">8</button>
                                <button class="keypad-btn" data-digit="9">9</button>
                            </div>
                            <div class="keypad-row">
                                <button class="keypad-btn" data-digit="*">*</button>
                                <button class="keypad-btn" data-digit="0">0</button>
                                <button class="keypad-btn" data-digit="#">#</button>
                            </div>
                        </div>
                    </div>
                    <div class="voip-call-controls" id="voip-call-controls" style="display: none;">
                        <div class="call-info">
                            <div class="caller-name" id="caller-name">Unknown</div>
                            <div class="caller-number" id="caller-number">+260...</div>
                            <div class="call-duration" id="call-duration">00:00</div>
                        </div>
                        <div class="call-buttons">
                            <button class="btn btn-warning" id="hold-button">⏸️ Hold</button>
                            <button class="btn btn-danger" id="hangup-button">📞 Hang Up</button>
                            <button class="btn btn-secondary" id="mute-button">🔇 Mute</button>
                        </div>
                    </div>
                    <div class="voip-customer-info" id="voip-customer-info" style="display: none;">
                        <div class="customer-details">
                            <h6>Customer Information</h6>
                            <div id="customer-data"></div>
                        </div>
                    </div>
                </div>
            </div>
        `);
        
        // Add widget to page
        $('body').append(widget);
        
        // Add CSS styles
        this.addWidgetStyles();
    }
    
    addWidgetStyles() {
        const styles = `
            <style>
                .voip-widget {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    width: 300px;
                    background: white;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    z-index: 9999;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                
                .voip-header {
                    background: #2196F3;
                    color: white;
                    padding: 10px 15px;
                    border-radius: 8px 8px 0 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    cursor: move;
                }
                
                .voip-title {
                    font-weight: 600;
                    font-size: 14px;
                }
                
                .voip-status {
                    font-size: 12px;
                    opacity: 0.9;
                }
                
                .voip-minimize {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 18px;
                    cursor: pointer;
                    padding: 0;
                    width: 20px;
                    height: 20px;
                }
                
                .voip-content {
                    padding: 15px;
                }
                
                .voip-dialer #phone-input {
                    margin-bottom: 10px;
                }
                
                .voip-buttons {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 15px;
                }
                
                .voip-buttons button {
                    flex: 1;
                    font-size: 12px;
                }
                
                .voip-keypad {
                    display: grid;
                    gap: 5px;
                }
                
                .keypad-row {
                    display: flex;
                    gap: 5px;
                }
                
                .keypad-btn {
                    flex: 1;
                    padding: 10px;
                    border: 1px solid #ddd;
                    background: #f8f9fa;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 16px;
                    font-weight: 600;
                }
                
                .keypad-btn:hover {
                    background: #e9ecef;
                }
                
                .call-info {
                    text-align: center;
                    margin-bottom: 15px;
                }
                
                .caller-name {
                    font-size: 16px;
                    font-weight: 600;
                    margin-bottom: 5px;
                }
                
                .caller-number {
                    font-size: 14px;
                    color: #666;
                    margin-bottom: 5px;
                }
                
                .call-duration {
                    font-size: 18px;
                    font-weight: 600;
                    color: #2196F3;
                }
                
                .call-buttons {
                    display: flex;
                    gap: 8px;
                }
                
                .call-buttons button {
                    flex: 1;
                    font-size: 11px;
                    padding: 8px 4px;
                }
                
                .customer-details {
                    background: #f8f9fa;
                    padding: 10px;
                    border-radius: 4px;
                    margin-top: 10px;
                }
                
                .customer-details h6 {
                    margin: 0 0 8px 0;
                    font-size: 12px;
                    color: #666;
                }
                
                .voip-widget.minimized .voip-content {
                    display: none;
                }
                
                .voip-widget.calling .voip-dialer {
                    display: none;
                }
                
                .voip-widget.calling .voip-call-controls {
                    display: block !important;
                }
            </style>
        `;
        
        $('head').append(styles);
    }
    
    setupEventListeners() {
        // Minimize/maximize widget
        $('#voip-minimize').on('click', () => {
            $('#wcfcb-voip-widget').toggleClass('minimized');
        });
        
        // Keypad input
        $('.keypad-btn').on('click', (e) => {
            const digit = $(e.target).data('digit');
            const input = $('#phone-input');
            input.val(input.val() + digit);
        });
        
        // Call button
        $('#call-button').on('click', () => {
            const phoneNumber = $('#phone-input').val().trim();
            if (phoneNumber) {
                this.initiateCall(phoneNumber);
            }
        });
        
        // Search button
        $('#search-button').on('click', () => {
            const query = $('#phone-input').val().trim();
            if (query) {
                this.searchCustomers(query);
            }
        });
        
        // Call control buttons
        $('#hangup-button').on('click', () => this.hangupCall());
        $('#hold-button').on('click', () => this.toggleHold());
        $('#mute-button').on('click', () => this.toggleMute());
        
        // Make widget draggable
        this.makeWidgetDraggable();
        
        // Listen for incoming call notifications
        frappe.realtime.on('incoming_call', (data) => {
            this.handleIncomingCallNotification(data);
        });
    }

    async connect() {
        try {
            if (this.userAgent && this.userAgent.state === SIP.UserAgentState.Stopped) {
                await this.userAgent.start();
                this.updateConnectionStatus('connecting');
            }
        } catch (error) {
            console.error('Error connecting SIP agent:', error);
            this.showError('Failed to connect to phone system');
        }
    }

    async disconnect() {
        try {
            if (this.userAgent && this.userAgent.state === SIP.UserAgentState.Started) {
                await this.userAgent.stop();
                this.updateConnectionStatus('disconnected');
            }
        } catch (error) {
            console.error('Error disconnecting SIP agent:', error);
        }
    }

    async initiateCall(phoneNumber) {
        try {
            if (!this.isInitialized) {
                throw new Error('VoIP widget not initialized');
            }

            // Ensure we're connected
            if (this.userAgent.state !== SIP.UserAgentState.Started) {
                await this.connect();
            }

            // Call server API to initiate call
            const response = await frappe.call({
                method: 'assistant_crm.api.voip_api.initiate_call',
                args: {
                    customer_phone: phoneNumber
                }
            });

            if (!response.message.success) {
                throw new Error(response.message.error || 'Failed to initiate call');
            }

            // Create SIP invitation
            const target = SIP.UserAgent.makeURI(`sip:${phoneNumber}@${this.sipConfig.sip_domain}`);
            const inviter = new SIP.Inviter(this.userAgent, target);

            // Set up session event handlers
            this.setupSessionEventHandlers(inviter, response.message.call_session_id);

            // Send invitation
            await inviter.invite();

            this.currentCall = {
                session: inviter,
                callSessionId: response.message.call_session_id,
                phoneNumber: phoneNumber,
                direction: 'outbound',
                startTime: new Date()
            };

            this.showCallInterface(phoneNumber, 'Calling...');

        } catch (error) {
            console.error('Error initiating call:', error);
            this.showError('Failed to initiate call: ' + error.message);
        }
    }

    handleIncomingCall(invitation) {
        try {
            // Extract caller information
            const fromHeader = invitation.request.from;
            const callerNumber = this.extractPhoneNumber(fromHeader.uri.user);

            // Show incoming call interface
            this.showIncomingCallInterface(callerNumber, invitation);

        } catch (error) {
            console.error('Error handling incoming call:', error);
            invitation.reject();
        }
    }

    handleIncomingCallNotification(data) {
        try {
            // Show browser notification
            if (Notification.permission === 'granted') {
                new Notification('Incoming Call', {
                    body: `Call from ${data.customer_phone}`,
                    icon: '/assets/assistant_crm/images/phone-icon.png'
                });
            }

            // Show visual notification in widget
            this.showIncomingCallAlert(data);

        } catch (error) {
            console.error('Error handling incoming call notification:', error);
        }
    }

    showIncomingCallInterface(callerNumber, invitation) {
        const widget = $('#wcfcb-voip-widget');
        widget.removeClass('minimized');

        // Update widget content for incoming call
        $('#voip-content').html(`
            <div class="incoming-call">
                <div class="call-info">
                    <div class="caller-name">Incoming Call</div>
                    <div class="caller-number">${callerNumber}</div>
                </div>
                <div class="incoming-call-buttons">
                    <button class="btn btn-success" id="answer-button">📞 Answer</button>
                    <button class="btn btn-danger" id="reject-button">❌ Reject</button>
                </div>
                <div class="customer-lookup" id="customer-lookup">
                    <small>Looking up customer...</small>
                </div>
            </div>
        `);

        // Set up answer/reject handlers
        $('#answer-button').on('click', () => this.answerCall(invitation));
        $('#reject-button').on('click', () => this.rejectCall(invitation));

        // Look up customer information
        this.lookupCustomerByPhone(callerNumber);
    }

    async answerCall(invitation) {
        try {
            await invitation.accept();

            this.currentCall = {
                session: invitation,
                callSessionId: null, // Will be set by server
                phoneNumber: this.extractPhoneNumber(invitation.request.from.uri.user),
                direction: 'inbound',
                startTime: new Date()
            };

            this.setupSessionEventHandlers(invitation);
            this.showCallInterface(this.currentCall.phoneNumber, 'Connected');

        } catch (error) {
            console.error('Error answering call:', error);
            this.showError('Failed to answer call');
        }
    }

    async rejectCall(invitation) {
        try {
            await invitation.reject();
            this.resetWidget();
        } catch (error) {
            console.error('Error rejecting call:', error);
        }
    }

    async hangupCall() {
        try {
            if (this.currentCall && this.currentCall.session) {
                if (this.currentCall.session.state === SIP.SessionState.Established) {
                    await this.currentCall.session.bye();
                } else {
                    await this.currentCall.session.cancel();
                }

                // Update call status on server
                if (this.currentCall.callSessionId) {
                    await frappe.call({
                        method: 'assistant_crm.api.voip_api.update_call_status',
                        args: {
                            call_session_id: this.currentCall.callSessionId,
                            status: 'ended'
                        }
                    });
                }
            }

            this.currentCall = null;
            this.resetWidget();

        } catch (error) {
            console.error('Error hanging up call:', error);
            this.resetWidget();
        }
    }

    setupSessionEventHandlers(session, callSessionId = null) {
        session.delegate = {
            onBye: () => {
                // Verbose call end logging removed
                this.currentCall = null;
                this.resetWidget();
            },
            onSessionDescriptionHandler: (sdh) => {
                // Set up media event handlers
                sdh.peerConnection.addEventListener('track', (event) => {
                    const remoteAudio = document.getElementById('remote-audio') || document.createElement('audio');
                    remoteAudio.id = 'remote-audio';
                    remoteAudio.autoplay = true;
                    remoteAudio.srcObject = event.streams[0];
                    document.body.appendChild(remoteAudio);
                });
            }
        };

        // Update call session ID if provided
        if (callSessionId && this.currentCall) {
            this.currentCall.callSessionId = callSessionId;
        }
    }

    showCallInterface(phoneNumber, status) {
        const widget = $('#wcfcb-voip-widget');
        widget.addClass('calling');

        $('#caller-number').text(phoneNumber);
        $('#caller-name').text(status);

        // Start call timer
        this.startCallTimer();
    }

    startCallTimer() {
        if (this.callTimer) {
            clearInterval(this.callTimer);
        }

        this.callTimer = setInterval(() => {
            if (this.currentCall) {
                const duration = Math.floor((new Date() - this.currentCall.startTime) / 1000);
                const minutes = Math.floor(duration / 60);
                const seconds = duration % 60;
                $('#call-duration').text(`${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`);
            }
        }, 1000);
    }

    resetWidget() {
        const widget = $('#wcfcb-voip-widget');
        widget.removeClass('calling');

        $('#voip-content').html($('#voip-dialer').parent().html());
        this.setupEventListeners();

        if (this.callTimer) {
            clearInterval(this.callTimer);
            this.callTimer = null;
        }

        // Remove remote audio element
        const remoteAudio = document.getElementById('remote-audio');
        if (remoteAudio) {
            remoteAudio.remove();
        }
    }

    async searchCustomers(query) {
        try {
            const response = await frappe.call({
                method: 'assistant_crm.api.voip_api.search_customers_by_phone',
                args: {
                    phone_query: query
                }
            });

            if (response.message.success) {
                this.showCustomerSearchResults(response.message.customers);
            } else {
                this.showError('Customer search failed');
            }

        } catch (error) {
            console.error('Error searching customers:', error);
            this.showError('Customer search failed');
        }
    }

    showCustomerSearchResults(customers) {
        if (customers.length === 0) {
            frappe.show_alert('No customers found', 3);
            return;
        }

        // Create customer selection dialog
        const dialog = new frappe.ui.Dialog({
            title: 'Select Customer',
            fields: [
                {
                    fieldtype: 'HTML',
                    fieldname: 'customer_list',
                    options: this.generateCustomerListHTML(customers)
                }
            ]
        });

        dialog.show();

        // Set up customer selection handlers
        dialog.$wrapper.find('.customer-item').on('click', (e) => {
            const customerId = $(e.currentTarget).data('customer-id');
            const phone = $(e.currentTarget).data('phone');
            $('#phone-input').val(phone);
            dialog.hide();
        });
    }

    generateCustomerListHTML(customers) {
        return customers.map(customer => `
            <div class="customer-item" data-customer-id="${customer.customer_id}" data-phone="${customer.primary_phone}" style="padding: 10px; border-bottom: 1px solid #eee; cursor: pointer;">
                <div style="font-weight: 600;">${customer.customer_name}</div>
                <div style="color: #666; font-size: 12px;">${customer.primary_phone}</div>
                <div style="color: #888; font-size: 11px;">${customer.customer_group || 'Standard'}</div>
            </div>
        `).join('');
    }

    updateConnectionStatus(status) {
        const statusElement = $('#voip-status');
        const statusMap = {
            'connected': { text: 'Connected', color: '#4CAF50' },
            'connecting': { text: 'Connecting...', color: '#FF9800' },
            'disconnected': { text: 'Disconnected', color: '#F44336' }
        };

        const statusInfo = statusMap[status] || statusMap['disconnected'];
        statusElement.text(statusInfo.text).css('color', statusInfo.color);
    }

    showError(message) {
        frappe.show_alert({
            message: message,
            indicator: 'red'
        }, 5);
    }

    extractPhoneNumber(sipUser) {
        // Extract phone number from SIP user part
        return sipUser.replace(/[^0-9+]/g, '');
    }

    makeWidgetDraggable() {
        let isDragging = false;
        let currentX;
        let currentY;
        let initialX;
        let initialY;
        let xOffset = 0;
        let yOffset = 0;

        const widget = document.getElementById('wcfcb-voip-widget');
        const header = widget.querySelector('.voip-header');

        header.addEventListener('mousedown', dragStart);
        document.addEventListener('mousemove', drag);
        document.addEventListener('mouseup', dragEnd);

        function dragStart(e) {
            initialX = e.clientX - xOffset;
            initialY = e.clientY - yOffset;

            if (e.target === header || header.contains(e.target)) {
                isDragging = true;
            }
        }

        function drag(e) {
            if (isDragging) {
                e.preventDefault();
                currentX = e.clientX - initialX;
                currentY = e.clientY - initialY;

                xOffset = currentX;
                yOffset = currentY;

                widget.style.transform = `translate3d(${currentX}px, ${currentY}px, 0)`;
            }
        }

        function dragEnd() {
            initialX = currentX;
            initialY = currentY;
            isDragging = false;
        }
    }
}

// Initialize VoIP widget when page loads
$(document).ready(() => {
    // Only initialize on pages where VoIP is needed
    if (frappe.user.has_role(['Assistant CRM Agent', 'Assistant CRM Manager', 'System Manager'])) {
        window.wcfcbVoIP = new WCFCBVoIPWidget();

        // Auto-connect when widget is initialized
        setTimeout(() => {
            if (window.wcfcbVoIP.isInitialized) {
                window.wcfcbVoIP.connect();
            }
        }, 2000);
    }
});
