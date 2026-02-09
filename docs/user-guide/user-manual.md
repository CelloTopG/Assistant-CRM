# User Manual

This manual explains how to use **WCFCB Assistant CRM** in day-to-day operations.

## Personas & access

### Customers & beneficiaries
- Interact primarily with **Anna** via the web chat bubble or messaging channels.
- Ask about claim status, payments, employer services and general WCFCB information.

### Contact center agents
- Work inside the Frappe/ERPNext Desk using the **Assistant CRM** module.
- Use the **Inbox** and related pages to respond to conversations from all channels.

### Supervisors & management
- Monitor performance and service levels using Assistant CRM dashboards and reports.
- Review satisfaction, response times, volumes and branch performance.

### IT & integration teams
- Configure AI providers, CoreBusiness connectivity, channels and security.
- Monitor logs, webhooks and scheduled jobs.

## Accessing Assistant CRM

You can access Assistant CRM in three main ways:

1. **ERPNext Desk**  
   Open the **Assistant CRM** module to access:
   - Unified Inbox for omnichannel conversations
   - Agent performance and satisfaction dashboards
   - Knowledge base, templates and configuration DocTypes

2. **Public website**  
   - Use the Anna chat bubble embedded on WCFCB public pages.
   - Visitors can ask questions, check claim and payment information and request help.

3. **Messaging & social channels**  
- WhatsApp, Telegram, Facebook, Instagram and other channels are connected via webhooks configured for each platform.
- All messages flow back into the unified inbox for agent handling and AI responses.

## Using Anna (chat assistant)

Anna is optimized for customer-facing conversations.

Typical flow:

1. **Start a conversation**
   - From the web chat bubble or a connected messaging channel.
2. **Identify yourself**
   - Provide NRC, full name or employer information when prompted.
3. **Ask your question**
   - Examples: "What is the status of my claim?", "Have my contributions been received?", "How do I submit a new claim?".
4. **Review the response**
   - Anna combines knowledge base content with live data, when available.
5. **Follow-up or escalate**
   - Ask a follow-up question, or request to speak to a human agent for complex cases.

## Using Antoine (reports & analytics)

Antoine focuses on reporting, analytics and more formal outputs.

Typical usage patterns:

- Generate structured summaries of claims, payments or employer activity.
- Produce professional, WCFCB-branded explanations for management or external stakeholders.
- Support decision making with consolidated information from multiple systems.

Reports and analytics are accessible through standard Frappe report views under the **Assistant CRM** module (for example: inbox status, claims status, employer status, payout summaries and survey feedback analysis).

## Typical workflows

### Check claim status
1. Open the Anna chat interface or unified inbox.
2. Provide required identification (NRC and full name).
3. Ask for the status of a specific claim or all active claims.
4. Review the live data returned from CoreBusiness.

### Verify payment information
1. Identify the beneficiary or employer.
2. Ask for recent payments or contribution history.
3. Use the returned data to respond to the citizen or employer.

### Handle an escalation
1. When Anna detects frustration or complex intent, she can suggest escalation.
2. An agent picks up the conversation in the unified inbox.
3. The agent has access to conversation history, intent, and relevant data.
4. After resolving, the conversation is logged for analytics and continuous improvement.

## Best practices for queries

- Be **specific**: include NRC, claim number or employer ID when possible.
- Provide **context**: mention which branch, time period or type of benefit.
- Keep messages **clear and concise**: one question at a time improves AI accuracy.
- Use the **knowledge base** for detailed process explanations and policies.

## Where to go next

- For installation and environment setup, see the [Installation Guide](installation.md).
- For configuration details (AI providers, channels, security), see the [Configuration Guide](configuration.md).
- For operational issues, see the [Troubleshooting Guide](troubleshooting.md) and [FAQ](faq.md).

