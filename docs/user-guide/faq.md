# Frequently Asked Questions (FAQ)

## What is WCFCB Assistant CRM?

WCFCB Assistant CRM is an omnichannel AI assistant app for the Workers' Compensation Fund Control Board (WCFCB) of Zambia. It combines AI assistants, a unified inbox, live CoreBusiness data and analytics on top of the Frappe/ERPNext platform.

## Which channels are supported?

Out of the box, Assistant CRM can integrate with:

- Web chat (embedded chat bubble)
- WhatsApp Business API
- Telegram
- Facebook Messenger
- Instagram
- Email
- USSD (via integration)
 

## Which AI providers are supported?

The app supports multiple AI backends:

- **Google Gemini** (recommended)
- **OpenAI GPT**
- **Anthropic Claude**
- Custom HTTP APIs

You can select the provider and model in **Assistant CRM Settings** and **Enhanced AI Settings**.

## Does Assistant CRM store personal data?

Yes. Conversation history, claims-related data and user identifiers are stored in the Frappe database to enable live data lookups, auditability and analytics.

Data protection features include:

- Role-based access control (RBAC) for sensitive DocTypes
- Configurable data retention and anonymization policies
- Audit logs and access tracking
- Support for encryption of sensitive fields

Your organization remains responsible for configuring retention, consent and compliance settings according to local regulations.

## How do I install the app?

See the [Installation Guide](installation.md) for step-by-step instructions, including prerequisites, bench commands and initial data setup.

## How do I configure AI and channels?

Use the [Configuration Guide](configuration.md) to:

- Select and configure your AI provider (Gemini, OpenAI, Claude, custom)
- Set timeouts, caching and rate limits
- Configure WhatsApp, Telegram, Facebook and other channels
- Set up CoreBusiness and other live data integrations

## How do agents work with the system?

Agents primarily use:

- The **Unified Inbox** to handle conversations from all channels
- Dashboards and reports to monitor workload and service levels
- Knowledge base and templates to deliver consistent, high-quality responses

See the [User Manual](user-manual.md) for typical workflows.

## What environments are recommended?

For production deployments:

- Run on a dedicated Frappe/ERPNext bench with adequate CPU, RAM and storage
- Use HTTPS with valid TLS certificates
- Enable Redis caching and background workers
- Configure regular backups and monitoring

See the production section of your infrastructure documentation and the [System Architecture](../technical/architecture.md) guide for more details.

## Where can I find help?

If you encounter issues:

1. Start with the [Troubleshooting Guide](troubleshooting.md).
2. Review relevant server logs.
3. Collect error messages, stack traces and steps to reproduce.
4. Escalate to your internal IT/support team with this information.

