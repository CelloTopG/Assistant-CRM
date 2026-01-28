# Installation Guide

This guide provides step-by-step instructions for installing WCFCB Assistant CRM on your Frappe/ERPNext environment.

## Prerequisites

### System Requirements
- **Frappe Framework**: v14.0 or higher
- **Python**: 3.8+
- **Node.js**: 16.0+
- **Database**: MariaDB 10.6+ or PostgreSQL 13+
- **Memory**: 4GB RAM minimum (8GB recommended)
- **Storage**: 20GB available space

### Required API Keys
- **Google Gemini API Key**: For AI functionality
- **Make.com Account**: For omnichannel integrations (optional)
- **Ngrok Account**: For webhook testing (development only)

## Installation Steps

### 1. Install the App

```bash
# Navigate to your Frappe bench directory
cd /path/to/your/frappe-bench

# Get the app from repository
bench get-app https://github.com/your-org/assistant_crm.git

# Install the app on your site
bench --site your-site install-app assistant_crm

# Run database migrations to create DocTypes
bench --site your-site migrate
```

### 2. Build Assets

```bash
# Build frontend assets
bench build --app assistant_crm

# Restart the bench to load new assets
bench restart
```

### 3. Configure API Keys

#### Option A: Through Web Interface (Recommended)
1. Navigate to **Setup → Integrations → Assistant CRM Settings**
2. Enable the system by checking "Enable Assistant CRM"
3. Configure your AI provider:
   - **AI Provider**: Select "Google Gemini"
   - **API Key**: Enter your Gemini API key
   - **Model**: `gemini-1.5-pro` (recommended)
4. Test the connection using the "Test Connection" button

#### Option B: Environment Variables (Legacy)
Create a `.env.ai` file in your bench directory:

```bash
# .env.ai
google_gemini_api_key=your_gemini_api_key_here
gemini_model=gemini-1.5-pro
```

### 4. Initial Data Setup

```bash
# Create initial knowledge base articles
bench --site your-site execute assistant_crm.setup_knowledge_base.create_initial_articles

# Set up default personas and templates
bench --site your-site execute assistant_crm.fixtures.persona_sample_data.create_sample_personas

# Configure default settings
bench --site your-site execute assistant_crm.install.setup_default_configuration
```

### 5. Verify Installation

```bash
# Run comprehensive system test
bench --site your-site execute assistant_crm.comprehensive_test.run_all_tests

# Test chat functionality
bench --site your-site execute assistant_crm.test_api.test_chat_endpoint
```

## Post-Installation Configuration

### 1. User Permissions

Create and assign the following roles:
- **Assistant CRM Admin**: Full system administration
- **Assistant CRM Agent**: Agent dashboard access
- **Assistant CRM User**: Basic chat access

```bash
# Create roles and permissions
bench --site your-site execute assistant_crm.install.setup_roles_and_permissions
```

### 2. Knowledge Base Setup

1. Navigate to **Assistant CRM → Knowledge Base Articles**
2. Review and customize the default articles
3. Add organization-specific content
4. Configure article keywords for better intent matching

### 3. Omnichannel Configuration (Optional)

#### WhatsApp Integration
1. Set up a WhatsApp Business API account
2. Configure webhook URL: `https://your-domain.com/api/omnichannel/webhook/whatsapp`
3. Update settings in **Assistant CRM → Social Media Settings**

#### Telegram Integration
1. Create a Telegram bot via @BotFather
2. Configure webhook URL: `https://your-domain.com/api/omnichannel/webhook/telegram`
3. Update bot token in **Assistant CRM → Social Media Settings**

#### Make.com Integration (Recommended)
1. Create Make.com scenarios for each platform
2. Configure centralized webhook: `https://your-domain.com/api/omnichannel/webhook/make-com`
3. Update Make.com settings in **Assistant CRM → Advanced Social Media Settings**

## Troubleshooting

### Common Issues

#### 1. Chat Bubble Not Appearing
- Verify assets are built: `bench build --app assistant_crm`
- Check if Assistant CRM is enabled in settings
- Ensure user has proper permissions

#### 2. API Connection Errors
- Verify API key is correct and active
- Check internet connectivity
- Test API connection in settings

#### 3. Database Migration Errors
```bash
# Force migration
bench --site your-site migrate --skip-failing

# Check migration status
bench --site your-site migrate-status
```

#### 4. Permission Errors
```bash
# Reset permissions
bench --site your-site execute assistant_crm.install.reset_permissions

# Reload DocTypes
bench --site your-site reload-doctype
```

### Log Files

Check these log files for debugging:
- **Frappe Logs**: `logs/frappe.log`
- **Assistant CRM Logs**: `logs/assistant_crm.log`
- **Error Logs**: `logs/error.log`

### Performance Optimization

#### 1. Enable Caching
```bash
# Enable Redis caching
bench --site your-site set-config enable_redis_cache 1

# Configure cache settings
bench --site your-site execute assistant_crm.services.cache_service.configure_cache
```

#### 2. Database Optimization
```bash
# Optimize database tables
bench --site your-site execute assistant_crm.utils.optimize_database_tables

# Clean up old logs
bench --site your-site execute assistant_crm.utils.cleanup_old_logs
```

## Next Steps

After successful installation:

1. **Configure System Settings**: Review [Configuration Guide](configuration.md)
2. **Set Up Users**: Create user accounts and assign appropriate roles
3. **Customize Knowledge Base**: Add organization-specific content
4. **Test Functionality**: Perform end-to-end testing
5. **Deploy to Production**: Follow [Production Deployment Guide](../deployment/production.md)

## Support

If you encounter issues during installation:

1. Check the [Troubleshooting Section](#troubleshooting) above
2. Review the [FAQ](../user-guide/faq.md)
3. Create an issue on [GitHub](https://github.com/your-org/assistant_crm/issues)
4. Contact technical support: support@wcfcb.com

---

**Next**: [Configuration Guide](configuration.md)
