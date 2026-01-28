# Copyright (c) 2024, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SocialMediaSettings(Document):
    """Server-side helpers for Social Media configuration.

    Adds support for exchanging short-lived Facebook/Instagram tokens for long-lived tokens
    via the Graph API and storing them in this settings DocType.
    """
    pass


@frappe.whitelist()
def exchange_facebook_long_lived_token(short_lived_token: str | None = None) -> dict:
    """Exchange a short-lived Facebook User access token for a long-lived token
    and update the configured Page Access Token (and Instagram token if applicable).

    Flow:
    1) Exchange short-lived user token -> long-lived user token
       GET https://graph.facebook.com/v19.0/oauth/access_token
           ?grant_type=fb_exchange_token
           &client_id={app_id}
           &client_secret={app_secret}
           &fb_exchange_token={short_lived_user_token}
    2) If a Facebook Page ID is configured, fetch the Page Access Token using:
       GET https://graph.facebook.com/v19.0/me/accounts?access_token={long_lived_user_token}
       and pick the entry matching the configured page_id.

    Returns a dict: {success: bool, message: str, details?: {...}}
    """
    import requests

    try:
        settings = frappe.get_single("Social Media Settings")
        app_id = settings.get("facebook_app_id")
        app_secret = settings.get_password("facebook_app_secret") if settings.get("facebook_app_secret") else None
        page_id = settings.get("facebook_page_id")

        if not app_id or not app_secret:
            return {"success": False, "message": "Facebook App ID and App Secret are required in Social Media Settings"}

        # Determine the short-lived token source
        token_to_exchange = short_lived_token or (settings.get_password("facebook_page_access_token") if settings.get("facebook_page_access_token") else None)
        if not token_to_exchange:
            return {"success": False, "message": "Provide a short-lived user access token or fill Facebook Page Access Token temporarily and retry"}

        # Step 1: Exchange for long-lived user token
        url = "https://graph.facebook.com/v19.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": token_to_exchange,
        }
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            try:
                err = resp.json()
            except Exception:
                err = {"raw": resp.text}
            return {"success": False, "message": "Failed to exchange long-lived user token", "details": err}

        data = resp.json()
        long_lived_user_token = data.get("access_token")
        expires_in = data.get("expires_in")
        if not long_lived_user_token:
            return {"success": False, "message": "Exchange response missing access_token", "details": data}

        result = {
            "success": True,
            "message": "Obtained long-lived user token",
            "details": {"expires_in": expires_in},
        }

        # Step 2: If page_id configured, fetch the Page Access Token
        page_token_used = False
        if page_id:
            pages_url = "https://graph.facebook.com/v19.0/me/accounts"
            pages_params = {"access_token": long_lived_user_token}
            pages_resp = requests.get(pages_url, params=pages_params, timeout=30)
            if pages_resp.status_code == 200 and pages_resp.content:
                pages_data = pages_resp.json()
                for entry in pages_data.get("data", []):
                    if str(entry.get("id")) == str(page_id):
                        page_access_token = entry.get("access_token")
                        if page_access_token:
                            # Persist tokens
                            settings.set_password("facebook_page_access_token", page_access_token)
                            # Also use the same page token for Instagram DM if set up
                            if settings.get("instagram_business_account_id"):
                                settings.set_password("instagram_access_token", page_access_token)
                            settings.save(ignore_permissions=True)
                            frappe.db.commit()
                            result["message"] = "Exchanged and saved Facebook Page Access Token (also applied to Instagram if configured)"
                            result["details"]["page_id"] = page_id
                            page_token_used = True
                        break
            else:
                # Could not list pages; still save the long-lived user token as page token fallback
                pass

        if not page_token_used:
            # Store the long-lived user token into facebook_page_access_token as a fallback
            settings.set_password("facebook_page_access_token", long_lived_user_token)
            # Optionally mirror to Instagram access token to keep config consistent
            if settings.get("instagram_business_account_id") and not settings.get("instagram_access_token"):
                settings.set_password("instagram_access_token", long_lived_user_token)
            settings.save(ignore_permissions=True)
            frappe.db.commit()
            result["message"] = (
                result["message"] + ", saved user token into Facebook Page Access Token field (no matching page or page listing failed)"
            )

        return result

    except Exception as e:
        frappe.log_error(f"exchange_facebook_long_lived_token error: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def exchange_instagram_long_lived_token(short_lived_token: str | None = None) -> dict:
    """Exchange a short-lived token for Instagram usage.

    For Instagram Business messaging, a Facebook Page Access Token with the
    requisite instagram permissions is typically used. This helper mirrors the
    Facebook exchange flow and saves the resulting Page/User token into the
    Instagram Access Token field as well.
    """
    try:
        # Reuse the Facebook exchange and then mirror to Instagram field
        fb_result = exchange_facebook_long_lived_token(short_lived_token)
        if not fb_result.get("success"):
            return fb_result

        # Ensure instagram_access_token is set (already mirrored in the FB flow when possible)
        settings = frappe.get_single("Social Media Settings")
        if not settings.get("instagram_access_token") and settings.get("facebook_page_access_token"):
            settings.set_password("instagram_access_token", settings.get_password("facebook_page_access_token"))
            settings.save(ignore_permissions=True)
            frappe.db.commit()

        fb_result["message"] = fb_result.get("message", "") + \
            "; Instagram Access Token updated"
        return fb_result

    except Exception as e:
        frappe.log_error(f"exchange_instagram_long_lived_token error: {str(e)}")
        return {"success": False, "message": str(e)}
