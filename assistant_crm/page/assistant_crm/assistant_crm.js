frappe.pages['assistant-crm'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Assistant CRM',
        single_column: true
    });

    // Initialize the page
    new AssistantCRMIntegration(page);
};

class AssistantCRMIntegration {
    constructor(page) {
        this.page = page;
        this.wrapper = page.main;
        this.init();
    }

    init() {
        // Assets are already loaded globally via hooks.py, no need for frappe.require()
        console.log("🔍 Assistant CRM page init - checking asset availability");
        console.log("WcfcbChatBubble class available:", typeof WcfcbChatBubble !== 'undefined');

        // Load the HTML content directly
        this.setupHTML();

        // Bind events
        this.bindEvents();

        // Load current settings
        this.loadSettings();

        // Initialize chat bubble if available
        setTimeout(() => {
            console.log("🔍 Assistant CRM page: Initializing chat bubble");
            console.log("WcfcbChatBubble class available:", typeof WcfcbChatBubble !== 'undefined');
            console.log("window.wcfcbChatBubble exists:", typeof window.wcfcbChatBubble !== 'undefined');
            console.log("Manual init function available:", typeof window.initializeWcfcbChatBubble !== 'undefined');

            if (window.wcfcbChatBubble) {
                console.log("✅ Chat bubble exists, triggering auto-launch");
                // Chat bubble already exists, trigger auto-launch
                window.wcfcbChatBubble.autoLaunchCenterScreen();
            } else if (typeof WcfcbChatBubble !== 'undefined') {
                console.log("✅ Creating new chat bubble instance");
                // Create new chat bubble instance
                window.wcfcbChatBubble = new WcfcbChatBubble();
                // Auto-launch after creation
                setTimeout(() => {
                    if (window.wcfcbChatBubble && window.wcfcbChatBubble.autoLaunchCenterScreen) {
                        window.wcfcbChatBubble.autoLaunchCenterScreen();
                    }
                }, 500);
            } else if (typeof window.initializeWcfcbChatBubble !== 'undefined') {
                console.log("✅ Using manual initialization function");
                window.initializeWcfcbChatBubble();
                setTimeout(() => {
                    if (window.wcfcbChatBubble && window.wcfcbChatBubble.autoLaunchCenterScreen) {
                        window.wcfcbChatBubble.autoLaunchCenterScreen();
                    }
                }, 500);
            } else {
                console.log("❌ Cannot initialize chat bubble - class not available");
            }
        }, 1000);
    }

    setupHTML() {
        // Create HTML content without template issues
        const html = `
            <div class="assistant-crm-integration">
                <div class="page-header">
                    <div class="WorkCom-avatar">
                        <div class="WorkCom-image">👩‍💼</div>
                    </div>
                    <h1>Hi this is WorkCom!</h1>
                    <p class="WorkCom-greeting">How can I help?</p>
                    <p class="text-muted">Your WCFCB AI assistant for customer service and CRM support</p>
                </div>

                <!-- WorkCom's Services Section -->
                <div class="WorkCom-services-section">
                    <h3>I specialize in helping you with:</h3>
                    <div class="services-grid">
                        <div class="service-card">
                            <div class="service-icon">📋</div>
                            <h4>Claims Processing</h4>
                            <p>Assistance with workers' compensation claims and documentation</p>
                        </div>
                        <div class="service-card">
                            <div class="service-icon">🏢</div>
                            <h4>Employer Registration</h4>
                            <p>Help with company registration and compliance requirements</p>
                        </div>
                        <div class="service-card">
                            <div class="service-icon">💰</div>
                            <h4>Payment Services</h4>
                            <p>Support with online payments and declaration submissions</p>
                        </div>
                        <div class="service-card">
                            <div class="service-icon">📊</div>
                            <h4>Reports & Analytics</h4>
                            <p>Access to reports, statistics, and business insights</p>
                        </div>
                        <div class="service-card">
                            <div class="service-icon">🛡️</div>
                            <h4>Safety & Health</h4>
                            <p>Workplace safety guidelines and health compliance</p>
                        </div>
                        <div class="service-card">
                            <div class="service-icon">📞</div>
                            <h4>General Support</h4>
                            <p>Any questions about WCFCB services and procedures</p>
                        </div>
                    </div>
                </div>

                <div class="integration-content">
                    <!-- Enable/Disable Section -->
                    <div class="form-group">
                        <div class="checkbox">
                            <label>
                                <input type="checkbox" id="assistant-enabled" />
                                <span class="label-area">Enable WorkCom Assistant</span>
                            </label>
                        </div>
                        <p class="help-text text-muted">
                            Enable WorkCom to provide AI-powered assistance across your WCFCB system
                        </p>
                    </div>

                    <!-- Settings Form (hidden by default) -->
                    <div id="assistant-settings-form" style="display: none;">
                        <hr>
                        
                        <!-- AI Provider Section -->
                        <div class="form-group">
                            <label class="control-label">AI Provider</label>
                            <select class="form-control" id="ai-provider">
                                <option value="Google Gemini">Google Gemini</option>
                                <option value="OpenAI GPT">OpenAI GPT</option>
                                <option value="Anthropic Claude">Anthropic Claude</option>
                                <option value="Custom API">Custom API</option>
                            </select>
                        </div>

                        <!-- API Key Section -->
                        <div class="form-group">
                            <label class="control-label">API Key</label>
                            <input type="password" class="form-control" id="api-key" placeholder="Enter your AI provider API key">
                            <p class="help-text text-muted">
                                Your API key will be encrypted and stored securely
                            </p>
                        </div>

                        <!-- Model Name Section -->
                        <div class="form-group">
                            <label class="control-label">Model Name</label>
                            <input type="text" class="form-control" id="model-name" placeholder="e.g., gemini-1.5-pro">
                            <p class="help-text text-muted">
                                Specify the AI model to use (e.g., gemini-1.5-pro, gpt-4, claude-3-sonnet-20240229)
                            </p>
                        </div>

                        <!-- Advanced Settings -->
                        <div class="form-group">
                            <label class="control-label">Response Timeout (seconds)</label>
                            <input type="number" class="form-control" id="response-timeout" value="30" min="5" max="120">
                        </div>

                        <div class="form-group">
                            <label class="control-label">Welcome Message</label>
                            <textarea class="form-control" id="welcome-message" rows="2" placeholder="Hi! I'm WorkCom, your WCFCB assistant. How can I help you today? 😊"></textarea>
                        </div>

                        <div class="form-group">
                            <label class="control-label">Chat Bubble Position</label>
                            <select class="form-control" id="chat-position">
                                <option value="Bottom Right">Bottom Right</option>
                                <option value="Bottom Left">Bottom Left</option>
                                <option value="Top Right">Top Right</option>
                                <option value="Top Left">Top Left</option>
                            </select>
                        </div>

                        <!-- Action Buttons -->
                        <div class="form-group">
                            <button class="btn btn-primary" id="save-settings">Save Settings</button>
                            <button class="btn btn-default" id="test-connection" style="margin-left: 10px;">Test Connection</button>
                        </div>

                        <!-- Status Messages -->
                        <div id="status-message" style="margin-top: 15px;"></div>
                    </div>

                    <!-- Help Section -->
                    <div class="help-section" style="margin-top: 30px;">
                        <h4>Getting Started</h4>
                        <ol>
                            <li><strong>Get an API Key:</strong> Sign up for your preferred AI provider (Google AI Studio, OpenAI, Anthropic)</li>
                            <li><strong>Enable Integration:</strong> Check the "Enable Assistant CRM" checkbox above</li>
                            <li><strong>Configure Settings:</strong> Enter your API key and configure preferences</li>
                            <li><strong>Test Connection:</strong> Use the "Test Connection" button to verify your setup</li>
                            <li><strong>Start Using:</strong> The chat bubble will appear on all desk pages when properly configured</li>
                        </ol>

                        <h4>Features</h4>
                        <ul>
                            <li>🌐 <strong>Omnichannel Support:</strong> WhatsApp, Telegram, Facebook Messenger integration</li>
                            <li>🎯 <strong>CRM Integration:</strong> Direct access to customer data, leads, and opportunities</li>
                            <li>🤖 <strong>WorkCom Persona:</strong> Professional, patient, and solution-focused assistant</li>
                            <li>🔍 <strong>Context-Aware:</strong> Understands customer history and preferences</li>
                            <li>🛡️ <strong>Secure:</strong> Role-based access with encrypted API key storage</li>
                            <li>📊 <strong>Analytics:</strong> Sentiment analysis and conversation monitoring</li>
                        </ul>

                        <h4>Support</h4>
                        <p>For help and documentation, visit: <a href="https://github.com/QuantumSolver/assistant_crm" target="_blank">Assistant CRM GitHub</a></p>
                    </div>
                </div>
            </div>
        `;

        $(this.wrapper).html(html);

        // Add debug controls
        this.addDebugControls();
    }

    addDebugControls() {
        // Add debug buttons to the page
        const debugHTML = `
            <div class="debug-controls" style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; border: 1px solid #dee2e6;">
                <h5 style="margin-bottom: 10px;">🔧 Debug Controls</h5>
                <button class="btn btn-primary btn-sm" onclick="window.testChatBubble()">Test Chat Bubble</button>
                <button class="btn btn-secondary btn-sm" onclick="window.checkAssets()">Check Assets</button>
                <button class="btn btn-info btn-sm" onclick="window.manualInit()">Manual Init</button>
                <button class="btn btn-warning btn-sm" onclick="window.forceAutoLaunch()">Force Auto Launch</button>
            </div>
        `;

        $(this.wrapper).prepend(debugHTML);

        // Add debug functions to window
        window.testChatBubble = () => {
            console.log("🧪 Testing chat bubble...");
            console.log("WcfcbChatBubble available:", typeof WcfcbChatBubble !== 'undefined');
            console.log("window.wcfcbChatBubble exists:", typeof window.wcfcbChatBubble !== 'undefined');
            if (window.wcfcbChatBubble) {
                console.log("Chat bubble methods:", Object.getOwnPropertyNames(Object.getPrototypeOf(window.wcfcbChatBubble)));
            }
        };

        window.checkAssets = () => {
            console.log("🔍 Checking assets...");
            console.log("jQuery available:", typeof $ !== 'undefined');
            console.log("Frappe available:", typeof frappe !== 'undefined');
            console.log("Frappe boot available:", frappe && typeof frappe.boot !== 'undefined');
            console.log("WcfcbChatBubble class:", typeof WcfcbChatBubble !== 'undefined');
        };

        window.manualInit = () => {
            console.log("🔧 Manual initialization...");
            if (typeof WcfcbChatBubble !== 'undefined') {
                window.wcfcbChatBubble = new WcfcbChatBubble();
                console.log("✅ Chat bubble created manually");
            } else {
                console.log("❌ WcfcbChatBubble class not available");
            }
        };

        window.forceAutoLaunch = () => {
            console.log("🚀 Force auto launch...");
            if (window.wcfcbChatBubble && window.wcfcbChatBubble.autoLaunchCenterScreen) {
                window.wcfcbChatBubble.autoLaunchCenterScreen();
                console.log("✅ Auto launch triggered");
            } else {
                console.log("❌ Chat bubble or auto launch method not available");
            }
        };
    }

    bindEvents() {
        const self = this;

        // Toggle settings form when enabled checkbox changes
        $(this.wrapper).on('change', '#assistant-enabled', function() {
            if ($(this).is(':checked')) {
                $('#assistant-settings-form').slideDown();
            } else {
                $('#assistant-settings-form').slideUp();
            }
        });

        // Save settings button
        $(this.wrapper).on('click', '#save-settings', function() {
            self.saveSettings();
        });

        // Test connection button
        $(this.wrapper).on('click', '#test-connection', function() {
            self.testConnection();
        });
    }

    loadSettings() {
        frappe.call({
            method: 'assistant_crm.page.assistant_crm.assistant_crm.get_settings',
            callback: (r) => {
                if (r.message) {
                    this.populateForm(r.message);
                }
            }
        });
    }

    populateForm(settings) {
        $('#assistant-enabled').prop('checked', settings.enabled);
        $('#ai-provider').val(settings.ai_provider);
        $('#model-name').val(settings.model_name);
        $('#api-key').val(settings.has_api_key ? '***' : '');
        $('#response-timeout').val(settings.response_timeout);
        $('#welcome-message').val(settings.welcome_message);
        $('#chat-position').val(settings.chat_bubble_position);

        // Show/hide settings form based on enabled state
        if (settings.enabled) {
            $('#assistant-settings-form').show();
        }

        // Show status if there's an error
        if (settings.error) {
            this.showMessage('Error loading settings: ' + settings.error, 'red');
        }
    }

    saveSettings() {
        const settings = {
            enabled: $('#assistant-enabled').is(':checked'),
            ai_provider: $('#ai-provider').val(),
            model_name: $('#model-name').val(),
            api_key: $('#api-key').val(),
            response_timeout: parseInt($('#response-timeout').val()),
            welcome_message: $('#welcome-message').val(),
            chat_bubble_position: $('#chat-position').val()
        };

        // Validate required fields
        if (settings.enabled) {
            if (!settings.api_key || settings.api_key === '***') {
                this.showMessage('API Key is required when Assistant CRM is enabled', 'red');
                return;
            }
            if (!settings.model_name) {
                this.showMessage('Model Name is required', 'red');
                return;
            }
        }

        // Show loading
        this.showMessage('Saving settings...', 'blue');

        frappe.call({
            method: 'assistant_crm.page.assistant_crm.assistant_crm.save_settings',
            args: {
                settings: settings
            },
            callback: (r) => {
                if (r.message && r.message.success) {
                    this.showMessage('Settings saved successfully! Chat bubble will appear when enabled.', 'green');

                    // Refresh the page to update chat bubble
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    this.showMessage('Error saving settings: ' + (r.message.error || 'Unknown error'), 'red');
                }
            }
        });
    }

    testConnection() {
        // Check if API key is provided
        const apiKey = $('#api-key').val();
        if (!apiKey || apiKey === '***') {
            this.showMessage('Please enter an API key before testing connection', 'red');
            return;
        }

        // Save settings first, then test
        this.showMessage('Testing connection...', 'blue');

        frappe.call({
            method: 'assistant_crm.page.assistant_crm.assistant_crm.test_connection',
            callback: (r) => {
                if (r.message && r.message.success) {
                    this.showMessage(
                        `✅ Connection successful!<br>
                        <strong>Model:</strong> ${r.message.model}<br>
                        <strong>Response Preview:</strong> ${r.message.response_preview}`,
                        'green'
                    );
                } else {
                    this.showMessage(
                        `❌ Connection failed: ${r.message.message}<br>
                        <small>Please check your API key and model settings.</small>`,
                        'red'
                    );
                }
            }
        });
    }

    showMessage(message, color) {
        const alertClass = {
            'green': 'alert-success',
            'red': 'alert-danger',
            'blue': 'alert-info',
            'orange': 'alert-warning'
        }[color] || 'alert-info';

        $('#status-message').html(`
            <div class="alert ${alertClass}" role="alert">
                ${message}
            </div>
        `);

        // Auto-hide success messages after 5 seconds
        if (color === 'green') {
            setTimeout(() => {
                $('#status-message').fadeOut();
            }, 5000);
        }
    }
}

