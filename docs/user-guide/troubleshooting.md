# Troubleshooting Guide

This guide helps you diagnose and fix common issues with **WCFCB Assistant CRM**.

Before you begin:

- Confirm your Frappe/ERPNext environment is healthy.
- Ensure you are testing on the correct site (e.g. `your-site` or `your-site.local`).
- Have access to server logs and the Frappe bench commands.

## 1. Installation & migration issues

### 1.1 Database migration errors

Symptoms:
- `migrate` fails or stops on Assistant CRM DocTypes.

Steps:

```bash
# From your bench directory
bench --site your-site migrate --skip-failing
bench --site your-site migrate-status
```

If errors persist:
- Check **error logs** under `logs/error.log`.
- Verify database permissions and storage space.

### 1.2 App not visible in Desk

- Confirm installation completed:
  - `bench --site your-site list-apps | grep assistant_crm`
- Restart bench:

```bash
bench restart
```

If the app is still missing, verify that the site you are logging into is the same site where the app was installed.

## 2. Chat bubble & UI issues

### 2.1 Chat bubble not appearing

- Ensure assets are built for the app:

```bash
bench build --app assistant_crm
bench restart
```

- Confirm **Enable Assistant CRM** is checked in **Assistant CRM Settings**.
- Verify the user has the required roles (e.g. Assistant CRM User / Agent).
- Clear browser cache or test in an incognito window.

### 2.2 Errors on public chat pages

- Open browser developer tools and check for JavaScript errors.
- Review `logs/frappe.log` and `logs/error.log` for stack traces.
- Confirm that your site URL and CSRF settings are correctly configured.

## 3. AI integration issues

### 3.1 AI not responding or timing out

- Verify API keys in **Assistant CRM Settings** and **Enhanced AI Settings**.
- Check that the selected model (e.g. `gemini-1.5-pro`, `gpt-4`) is available on your account.
- Confirm outbound internet access from the server.

From the bench console you can quickly verify stored keys:

```bash
bench --site your-site.local console
```

Then in the Python console:

```python
frappe.get_single("Enhanced AI Settings").get_password("openai_api_key")
```

- Review API provider dashboards for quota or permission issues.

### 3.2 Responses are poor or inconsistent

- Review and expand your knowledge base articles.
- Ensure intents and keywords are configured for common questions.
- Adjust AI temperature and related settings in configuration (e.g. more deterministic responses for official communication).

## 4. Omnichannel & webhook issues

### 4.1 Webhooks not receiving messages

- Verify webhook URLs are publicly reachable over HTTPS.
- Check SSL certificate validity.
- Confirm webhook configuration on each platform (WhatsApp, Telegram, Facebook, etc.).

Key endpoints (examples):

- Telegram: `https://your-domain/api/method/assistant_crm.api.telegram_webhook.telegram_webhook`
- WhatsApp: `https://your-domain/api/method/assistant_crm.api.whatsapp_webhook.whatsapp_webhook`
- Facebook: `https://your-domain/api/method/assistant_crm.api.facebook_webhook.facebook_webhook`

Monitor worker logs during tests:

```bash
tail -f logs/worker.log
```

### 4.2 Messages delayed or duplicated

- Check for retries or duplicate deliveries from the channel provider.
- Review Assistant CRM webhook handlers for error responses.
- Confirm only one webhook is configured per channel to avoid duplicate deliveries.

## 5. Performance & stability

### 5.1 Slow responses

- Monitor system resources (CPU, RAM, disk I/O).
- Verify Redis is enabled and configured for caching.
- Review database slow queries and add indexes where needed.

Example commands:

```bash
bench --site your-site set-config enable_redis_cache 1
bench --site your-site execute assistant_crm.services.cache_service.configure_cache
```

### 5.2 Large logs or database size

- Clean up old logs and optimize tables:

```bash
bench --site your-site execute assistant_crm.utils.cleanup_old_logs
bench --site your-site execute assistant_crm.utils.optimize_database_tables
```

## 6. Getting help

If issues persist:

1. Review this guide and the [Configuration Guide](configuration.md).
2. Check logs (`logs/frappe.log`, `logs/error.log`, `logs/assistant_crm.log`).
3. Run targeted tests from `assistant_crm.comprehensive_test` or other built-in scripts in a safe environment.
4. Escalate with detailed error messages, steps to reproduce and environment information.

