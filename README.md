# WCFCB Assistant CRM

Omnichannel AI Assistant for the Workers' Compensation Fund Control Board (WCFCB) of Zambia.

## Features

- **AI Assistants**: Anna (chat support) and Antoine (reports/analytics)
- **Omnichannel Support**: WhatsApp, Facebook, Instagram, Telegram, Twitter, LinkedIn, USSD, Email
- **Unified Inbox**: Centralized message management across all platforms
- **Live Data Integration**: Real-time claim status, payment info, and account details
- **Multi-language Support**: English, Bemba, Nyanja, Tonga

## Installation

```bash
# From frappe-bench directory
bench get-app https://github.com/CelloTopG/Assistant-CRM.git
bench --site your-site.local install-app assistant_crm
bench --site your-site.local migrate
```

## Configuration

### Required API Keys

Configure API keys via **site_config.json** or the Frappe desk:

#### Option 1: Site Config (Recommended for New Instances)

Add to your `sites/your-site.local/site_config.json`:

```json
{
  "assistant_crm_gemini_api_key": "your-google-gemini-api-key",
  "assistant_crm_openai_api_key": "your-openai-api-key",
  "assistant_crm_openai_model": "gpt-4",
  "assistant_crm_chat_model": "gpt-4",
  "assistant_crm_telegram_bot_token": "your-telegram-bot-token",
  "assistant_crm_facebook_page_access_token": "your-fb-token",
  "assistant_crm_instagram_access_token": "your-instagram-token",
  "assistant_crm_make_com_api_key": "your-make-com-key",
  "assistant_crm_make_com_webhook_secret": "your-webhook-secret",
  "assistant_crm_linkedin_client_secret": "your-linkedin-secret",
  "assistant_crm_linkedin_access_token": "your-linkedin-token",
  "assistant_crm_ussd_api_key": "your-ussd-key"
}
```

Then restart bench and run:
```bash
bench --site your-site.local migrate
```

#### Option 2: Environment File

Create `.env.wcfcb` in your bench directory:

```bash
GEMINI_API_KEY=your-google-gemini-api-key
OPENAI_API_KEY=your-openai-api-key
WHATSAPP_PHONE_NUMBER_ID=your-whatsapp-id
WHATSAPP_ACCESS_TOKEN=your-whatsapp-token
FACEBOOK_PAGE_ACCESS_TOKEN=your-fb-token
TELEGRAM_BOT_TOKEN=your-telegram-token
INSTAGRAM_ACCESS_TOKEN=your-instagram-token
```

#### Option 3: Frappe Desk UI

1. **Assistant CRM Settings**: `/app/assistant-crm-settings`
   - Gemini API Key (for Anna AI)
   - CoreBusiness API Key
   - Claims API Key
   - Telegram Bot Token

2. **Enhanced AI Settings**: `/app/enhanced-ai-settings`
   - OpenAI API Key (for Antoine/Anna)
   - Model selection (gpt-4, etc.)

3. **Social Media Settings**: `/app/social-media-settings`
   - Make.com credentials
   - Facebook, Instagram, Twitter, LinkedIn tokens
   - USSD configuration

### Webhook Configuration

Configure webhooks in your platform dashboards pointing to:

| Platform | Webhook URL |
|----------|-------------|
| Make.com | `https://your-domain/api/omnichannel/webhook/make-com` |
| Telegram | `https://your-domain/api/method/assistant_crm.api.telegram_webhook.telegram_webhook` |
| WhatsApp | `https://your-domain/api/method/assistant_crm.api.whatsapp_webhook.whatsapp_webhook` |
| Facebook | `https://your-domain/api/method/assistant_crm.api.facebook_webhook.facebook_webhook` |

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Social Media   │────▶│   Unified Inbox  │────▶│   AI Service    │
│   Platforms     │     │   (Simplified    │     │  (Antoine/Anna) │
└─────────────────┘     │    Chat API)     │     └─────────────────┘
                        └──────────────────┘              │
                                 │                        ▼
                                 ▼                 ┌─────────────────┐
                        ┌──────────────────┐       │  Live Data      │
                        │   Intent Router  │◀─────▶│  Service        │
                        └──────────────────┘       └─────────────────┘
```

## AI Assistants

### Anna (Chat Support)
- Handles customer inquiries via chat
- Uses Gemini (Google) or OpenAI GPT-4
- Multilingual support

### Antoine (Reports & Analytics)
- Generates reports and analytics
- Uses OpenAI GPT-4
- Professional tone optimization

## Troubleshooting

### API Keys Not Working
1. Check logs: `bench --site your-site.local console` then `frappe.get_single('Enhanced AI Settings').get_password('openai_api_key')`
2. Verify site_config.json has correct key names (prefixed with `assistant_crm_`)
3. Restart bench after config changes

### Webhooks Not Receiving Messages
1. Verify webhook URLs are publicly accessible
2. Check SSL certificate validity
3. Review logs: `tail -f logs/worker.log`

### AI Not Responding
1. Verify API keys are set in Enhanced AI Settings or Assistant CRM Settings
2. Check API quotas (Gemini/OpenAI)
3. Review error logs: `bench --site your-site.local show-logs`

## License

MIT License - See LICENSE file

## Support

- Email: support@wcfcb.com
- Documentation: `/app/assistant-crm-settings`

