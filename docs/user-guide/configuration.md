# Configuration Guide

This guide covers the complete configuration of WCFCB Assistant CRM after installation, including system settings, AI configuration, omnichannel setup, and user management.

## Initial System Configuration

### 1. Access Assistant CRM Settings

Navigate to **Setup → Integrations → Assistant CRM Settings** or go directly to:
```
https://your-domain.com/app/assistant-crm-settings
```

### 2. Enable the System

1. Check **"Enable Assistant CRM"** to activate the system
2. The chat bubble will appear once properly configured
3. All configuration options become available after enabling

## AI Configuration

### 1. Google Gemini Setup (Recommended)

#### Obtain API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key for configuration

#### Configure in System
1. **AI Provider**: Select "Google Gemini"
2. **API Key**: Paste your Gemini API key
3. **Model**: Choose from:
   - `gemini-1.5-pro` (Recommended for production)
   - `gemini-1.5-flash` (Faster responses, lower cost)
   - `gemini-pro` (Legacy model)
4. **Test Connection**: Click to verify the configuration

#### Advanced Gemini Settings
```json
{
  "temperature": 0.7,
  "max_output_tokens": 2048,
  "top_p": 0.8,
  "top_k": 40,
  "safety_settings": {
    "harassment": "BLOCK_MEDIUM_AND_ABOVE",
    "hate_speech": "BLOCK_MEDIUM_AND_ABOVE",
    "sexually_explicit": "BLOCK_MEDIUM_AND_ABOVE",
    "dangerous_content": "BLOCK_MEDIUM_AND_ABOVE"
  }
}
```

### 2. Alternative AI Providers

#### OpenAI GPT Configuration
1. **AI Provider**: Select "OpenAI GPT"
2. **API Key**: Your OpenAI API key
3. **Model**: `gpt-4` or `gpt-3.5-turbo`
4. **Custom Endpoint**: Leave blank for default

#### Anthropic Claude Configuration
1. **AI Provider**: Select "Anthropic Claude"
2. **API Key**: Your Anthropic API key
3. **Model**: `claude-3-sonnet-20240229`
4. **Custom Endpoint**: Leave blank for default

#### Custom API Configuration
1. **AI Provider**: Select "Custom API"
2. **Custom Endpoint**: Your API endpoint URL
3. **API Key**: Your custom API key
4. **Model**: Your model identifier

## Performance Settings

### 1. Response Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| **Response Timeout** | 30 seconds | Maximum time to wait for AI response |
| **Cache Duration** | 300 seconds | How long to cache responses |
| **Max Concurrent Requests** | 5 | Maximum simultaneous AI requests |
| **Debug Logging** | Disabled | Enable for troubleshooting |

### 2. Rate Limiting

Configure rate limits to prevent abuse:

```json
{
  "guest_users": {
    "requests_per_minute": 10,
    "burst_limit": 5
  },
  "authenticated_users": {
    "requests_per_minute": 60,
    "burst_limit": 20
  },
  "admin_users": {
    "requests_per_minute": 300,
    "burst_limit": 50
  }
}
```

## User Experience Configuration

### 1. Chat Interface Settings

#### Chat Bubble Configuration
- **Position**: Bottom Right, Bottom Left, Top Right, Top Left
- **Size**: Small, Medium, Large
- **Color Scheme**: WCFCB Blue, Custom colors
- **Animation**: Enable/disable entrance animations

#### Welcome Message
Customize Anna's greeting message:
```
Hi! I'm Anna, your WCFCB assistant. How can I help you today? 😊

I can help you with:
• Claim status and submissions
• Payment inquiries
• Employer services
• General information
```

#### Response Format Options
- **Professional**: Formal business language
- **Casual**: Friendly, conversational tone
- **Technical**: Detailed technical responses
- **Brief**: Concise, to-the-point answers

### 2. Multi-language Support

#### Supported Languages
- **English** (Primary)
- **Afrikaans**
- **Zulu**
- **Xhosa**
- **Other regional languages**

#### Language Detection
- **Automatic**: Detect language from user input
- **Manual**: User selects preferred language
- **Browser**: Use browser language settings

## Omnichannel Configuration

### 1. WhatsApp Business Integration

#### Prerequisites
- WhatsApp Business API account
- Verified business phone number
- Meta Business Manager access

#### Configuration Steps
1. Navigate to **Assistant CRM → Social Media Settings**
2. Enable **WhatsApp Integration**
3. Configure settings:

```json
{
  "phone_number_id": "your_phone_number_id",
  "access_token": "your_whatsapp_access_token",
  "webhook_verify_token": "your_webhook_verify_token",
  "webhook_url": "https://your-domain.com/api/omnichannel/webhook/whatsapp"
}
```

#### Webhook Setup
1. In Meta Business Manager, set webhook URL:
   ```
   https://your-domain.com/api/omnichannel/webhook/whatsapp
   ```
2. Subscribe to events: `messages`, `message_deliveries`, `message_reads`
3. Verify webhook with your verify token

### 2. Telegram Bot Integration

#### Create Telegram Bot
1. Message @BotFather on Telegram
2. Use `/newbot` command
3. Follow instructions to create bot
4. Save the bot token

#### Configure in System
1. Navigate to **Assistant CRM → Social Media Settings**
2. Enable **Telegram Integration**
3. Enter bot token and configure webhook:

```json
{
  "bot_token": "your_telegram_bot_token",
  "webhook_url": "https://your-domain.com/api/omnichannel/webhook/telegram",
  "allowed_updates": ["message", "callback_query"]
}
```

### 3. Facebook Messenger Integration

#### Prerequisites
- Facebook Page
- Facebook App with Messenger permissions
- Page access token

#### Configuration
1. Enable **Facebook Messenger Integration**
2. Configure settings:

```json
{
  "page_access_token": "your_page_access_token",
  "verify_token": "your_verify_token",
  "app_secret": "your_app_secret",
  "webhook_url": "https://your-domain.com/api/omnichannel/webhook/facebook"
}
```

### 4. Make.com Integration (Recommended)

Make.com provides centralized management of all social media integrations.

#### Setup Process
1. Create Make.com account
2. Create scenarios for each platform
3. Configure centralized webhook:
   ```
   https://your-domain.com/api/omnichannel/webhook/make-com
   ```
4. Update **Advanced Social Media Settings** with Make.com configuration

#### Benefits
- Simplified configuration
- Enhanced reliability
- Unified message processing
- Easier maintenance

## Knowledge Base Configuration

### 1. Article Management

#### Create Knowledge Base Articles
1. Navigate to **Assistant CRM → Knowledge Base Articles**
2. Click **New** to create an article
3. Fill in required fields:
   - **Title**: Clear, descriptive title
   - **Category**: Organize by topic
   - **Content**: Detailed article content
   - **Keywords**: Search terms (minimum 30 recommended)
   - **Status**: Published/Draft

#### Article Categories
- **Claims Management**
- **Payment Services**
- **Employer Services**
- **General Information**
- **Technical Support**

#### Keyword Optimization
Add comprehensive keywords for better intent matching:
```
Keywords: claim, status, check, track, progress, update, inquiry, 
submission, medical, certificate, injury, accident, workplace, 
compensation, benefits, payment, reimbursement
```

### 2. Response Templates

#### Create Persona-Specific Templates
1. Navigate to **Assistant CRM → Persona Response Templates**
2. Create templates for each user type:
   - **Employer/HR Manager**
   - **Beneficiary/Pensioner**
   - **Supplier**
   - **WCFCB Staff**

#### Template Structure
```markdown
## Greeting
Hi! I'm Anna, your WCFCB assistant.

## Clarification
To help you with [specific request], I'll need some information.

## Confirmation
Let me confirm your request: [summary]

## Response
Based on your inquiry, here's what I found: [information]

## Next Steps
Would you like me to help you with anything else?
```

## Live Data Integration

### 1. CoreBusiness API Configuration

#### API Settings
1. Navigate to **Assistant CRM → CoreBusiness Settings**
2. Configure API connection:

```json
{
  "api_base_url": "https://api.corebusiness.wcfcb.com",
  "api_key": "your_corebusiness_api_key",
  "timeout": 30,
  "retry_attempts": 3,
  "cache_duration": 120
}
```

#### Supported Data Types
- **Claims**: Status, history, documents
- **Payments**: Status, history, amounts
- **Employers**: Contributions, compliance
- **Beneficiaries**: Personal information, benefits

### 2. Authentication Workflow

#### National ID Verification
Configure the authentication process:

```json
{
  "require_nrc": true,
  "require_full_name": true,
  "verification_timeout": 300,
  "max_attempts": 3,
  "lockout_duration": 900
}
```

#### Session Management
- **Session Timeout**: 30 minutes of inactivity
- **Intent Locking**: Maintain context during authentication
- **Multi-session Support**: Allow multiple concurrent sessions

## Security Configuration

### 1. Role-Based Access Control

#### Create User Roles
1. Navigate to **Setup → Users and Permissions → Role**
2. Create these roles:
   - **Assistant CRM Admin**: Full system access
   - **Assistant CRM Agent**: Agent dashboard access
   - **Assistant CRM User**: Basic chat access
   - **Assistant CRM Manager**: Management reports

#### Assign Permissions
Configure permissions for each DocType:
- **Read**: View records
- **Write**: Create/modify records
- **Create**: Create new records
- **Delete**: Remove records
- **Submit**: Submit documents
- **Cancel**: Cancel documents

### 2. Data Protection Settings

#### Privacy Controls
```json
{
  "data_retention_days": 365,
  "anonymize_after_days": 730,
  "encrypt_sensitive_data": true,
  "audit_all_access": true,
  "gdpr_compliance": true
}
```

#### Access Logging
- **Log All Interactions**: Track all user interactions
- **IP Address Logging**: Record user IP addresses
- **Session Tracking**: Monitor user sessions
- **Failed Attempts**: Log authentication failures

## Monitoring and Analytics

### 1. Performance Monitoring

#### Key Metrics
- **Response Time**: Target <2 seconds for live data
- **Success Rate**: Target >95% successful responses
- **User Satisfaction**: Track user feedback
- **System Uptime**: Monitor service availability

#### Alerting Configuration
```json
{
  "response_time_threshold": 5.0,
  "error_rate_threshold": 0.05,
  "uptime_threshold": 0.99,
  "notification_channels": ["email", "slack", "sms"]
}
```

### 2. Analytics Dashboard

#### Available Reports
- **Conversation Analytics**: Message volume, response times
- **User Engagement**: Active users, session duration
- **Intent Analysis**: Most common user requests
- **Performance Metrics**: System performance indicators

#### Custom Dashboards
Create custom dashboards for different stakeholders:
- **Executive Dashboard**: High-level metrics
- **Operations Dashboard**: Detailed performance data
- **Agent Dashboard**: Real-time conversation management

## Backup and Maintenance

### 1. Automated Backups

#### Backup Configuration
```bash
# Daily database backup
0 2 * * * /home/frappe/backup_script.sh

# Weekly full system backup
0 3 * * 0 /home/frappe/full_backup_script.sh
```

#### Backup Retention
- **Daily Backups**: Keep for 30 days
- **Weekly Backups**: Keep for 12 weeks
- **Monthly Backups**: Keep for 12 months

### 2. Maintenance Tasks

#### Regular Maintenance
- **Log Cleanup**: Remove old log files
- **Cache Optimization**: Clear expired cache entries
- **Database Optimization**: Optimize database tables
- **Security Updates**: Apply security patches

#### Scheduled Tasks
```python
# Clean up old chat history
scheduler_events = {
    "daily": [
        "assistant_crm.tasks.cleanup_old_chat_history"
    ],
    "weekly": [
        "assistant_crm.tasks.optimize_database_tables"
    ],
    "monthly": [
        "assistant_crm.tasks.generate_analytics_reports"
    ]
}
```

## Troubleshooting Configuration Issues

### Common Configuration Problems

#### 1. Chat Bubble Not Appearing
- Verify Assistant CRM is enabled
- Check user permissions
- Ensure assets are built: `bench build --app assistant_crm`
- Clear browser cache

#### 2. AI Service Connection Errors
- Verify API key is correct
- Check internet connectivity
- Test API connection in settings
- Review error logs

#### 3. Omnichannel Integration Issues
- Verify webhook URLs are accessible
- Check webhook verification tokens
- Review webhook activity logs
- Test individual platform connections

#### 4. Performance Issues
- Check database performance
- Review cache hit rates
- Monitor system resources
- Optimize database queries

### Getting Help

If you encounter configuration issues:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review system logs in **Setup → System Console**
3. Test individual components using built-in test functions
4. Contact support with specific error messages

---

**Next**: [User Manual](user-manual.md) | [Troubleshooting Guide](troubleshooting.md)
