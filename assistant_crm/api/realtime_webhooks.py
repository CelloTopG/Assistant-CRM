#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Real-Time Webhook Handlers
Enhanced webhook processing with real-time event broadcasting
"""

import frappe
import json
import hmac
import hashlib
from frappe import _
from frappe.utils import now
from assistant_crm.services.omnichannel_router import OmnichannelRouter
from assistant_crm.services.realtime_service import RealtimeService


@frappe.whitelist(allow_guest=True)
def whatsapp_webhook():
    """Enhanced WhatsApp webhook with real-time processing"""
    try:
        # Verify webhook signature
        if not verify_whatsapp_signature():
            frappe.throw(_("Invalid webhook signature"), frappe.AuthenticationError)

        data = json.loads(frappe.request.data)

        # Handle webhook verification
        if frappe.request.method == "GET":
            return handle_whatsapp_verification()

        # Process incoming messages with real-time updates
        if "entry" in data:
            for entry in data["entry"]:
                if "changes" in entry:
                    for change in entry["changes"]:
                        if change.get("field") == "messages":
                            process_whatsapp_message_realtime(change["value"])

        return {"status": "success"}

    except Exception as e:
        frappe.log_error(f"WhatsApp webhook error: {str(e)}", "Real-time Webhooks")
        return {"status": "error", "message": str(e)}


def process_whatsapp_message_realtime(message_data):
    """Process WhatsApp message with real-time broadcasting"""
    try:
        if "messages" not in message_data:
            return

        realtime_service = RealtimeService()

        for message in message_data["messages"]:
            # Extract message details
            from_number = message.get("from")
            message_id = message.get("id")
            message_type = message.get("type", "text")

            # Get message content based on type
            content = ""
            if message_type == "text":
                content = message.get("text", {}).get("body", "")
            elif message_type == "image":
                content = "[Image received]"
            elif message_type == "document":
                content = "[Document received]"
            elif message_type == "audio":
                content = "[Audio message received]"

            # Create message data structure
            message_payload = {
                "channel_type": "WhatsApp",
                "channel_id": from_number,
                "content": content,
                "sender": from_number,
                "message_id": message_id,
                "metadata": {
                    "whatsapp_message_id": message_id,
                    "message_type": message_type,
                    "timestamp": message.get("timestamp"),
                    "raw_data": message,
                },
            }

            # Real-time broadcast of incoming message to agents/UI only.
            # AI responses are produced exclusively via Unified Inbox 
            # SimplifiedChat  EnhancedAIService (Antoine / OpenAI).
            realtime_service.broadcast_message(
                "WhatsApp",
                from_number,
                message_payload,
                target_users=get_available_agents(),
            )

        # Handle status updates
        if "statuses" in message_data:
            process_whatsapp_status_updates(message_data["statuses"])

    except Exception as e:
        frappe.log_error(f"Error processing WhatsApp message: {str(e)}", "Real-time Webhooks")


def process_whatsapp_status_updates(statuses):
    """Process WhatsApp delivery status updates with real-time notifications"""
    try:
        realtime_service = RealtimeService()

        for status in statuses:
            message_id = status.get("id")
            status_type = status.get("status")  # sent, delivered, read, failed
            recipient_id = status.get("recipient_id")
            timestamp = status.get("timestamp")

            # Find the corresponding message in our system
            message_doc = frappe.db.get_value(
                "Omnichannel Message",
                {"metadata": ["like", f"%{message_id}%"]},
                ["name", "conversation_id", "agent_assigned"]
            )

            if message_doc:
                # Update message status in database
                frappe.db.set_value(
                    "Omnichannel Message",
                    message_doc[0],
                    "status",
                    status_type.title()
                )

                # Real-time status update
                frappe.publish_realtime(
                    "message_status_update",
                    {
                        "message_id": message_doc[0],
                        "whatsapp_message_id": message_id,
                        "status": status_type,
                        "recipient_id": recipient_id,
                        "timestamp": timestamp,
                        "channel_type": "WhatsApp"
                    },
                    room=f"conversation_{message_doc[1] or message_doc[0]}"
                )

                # Notify assigned agent if any
                if message_doc[2]:
                    frappe.publish_realtime(
                        "message_delivery_update",
                        {
                            "message_id": message_doc[0],
                            "status": status_type,
                            "timestamp": timestamp
                        },
                        user=message_doc[2]
                    )

    except Exception as e:
        frappe.log_error(f"Error processing WhatsApp status updates: {str(e)}", "Real-time Webhooks")


@frappe.whitelist(allow_guest=True)
def facebook_webhook():
    """Facebook Messenger webhook restored to Unified Inbox pipeline with async AI."""
    try:
        # 1) Handle verification GET first (no signature required)
        if frappe.request.method == "GET":
            return handle_facebook_verification()

        # 2) Verify signature on POST (support both sha1 and sha256 headers)
        if not verify_facebook_signature():
            try:
                # Log failure context for diagnostics
                hdrs = dict(frappe.request.headers)
                body = frappe.request.data or b""
                blen = len(body if isinstance(body, (bytes, bytearray)) else (body.encode("utf-8") if body else b""))
                with open("/workspace/development/frappe-bench/logs/webhook_debug.log", "a") as f:
                    f.write(f"DEBUG: Facebook signature verification FAILED @ {now()} | Headers keys: {list(hdrs.keys())} | BodyLen: {blen}\n")
            except Exception:
                pass
            frappe.throw(_("Invalid webhook signature"), frappe.AuthenticationError)

        data = json.loads(frappe.request.data or "{}")

        # 3) Persist via legacy Unified Inbox pipeline
        from assistant_crm.api.social_media_ports import FacebookIntegration
        FacebookIntegration().process_webhook(data)

        # 4) Enqueue async AI processing for the saved conversation
        try:
            entry = (data.get("entry") or [{}])[0]
            messaging = (entry.get("messaging") or [{}])[0]
            sender_id = (messaging.get("sender") or {}).get("id")

            if sender_id:
                conversation = frappe.db.get_value(
                    "Unified Inbox Conversation",
                    {"platform": "Facebook", "platform_specific_id": sender_id},
                    "name",
                )
                if conversation:
                    frappe.enqueue(
                        "assistant_crm.api.unified_inbox_api.process_conversation_with_ai",
                        conversation_id=conversation,
                        queue="long",
                    )
        except Exception as e:
            frappe.log_error(f"Enqueue AI error: {str(e)}", "Facebook Webhook")

        return {"status": "success"}

    except Exception as e:
        frappe.log_error(f"Facebook webhook error: {str(e)}", "Real-time Webhooks")
        return {"status": "error", "message": str(e)}


def process_facebook_message_realtime(messaging_event):
    """Process Facebook message with real-time broadcasting.

    This helper is now **display-only**: it updates real-time dashboards for
    agents but does not perform any AI routing. All AI responses for Facebook
    are handled via the Unified Inbox  SimplifiedChat 
    EnhancedAIService (Antoine / OpenAI) pipeline in ``facebook_webhook``.
    """
    try:
        if "message" not in messaging_event:
            return

        sender_id = messaging_event["sender"]["id"]
        message = messaging_event["message"]
        message_text = message.get("text", "")

        # Handle attachments
        if "attachments" in message:
            attachment_types = [att.get("type") for att in message["attachments"]]
            message_text = f"[{', '.join(attachment_types)} received]"

        realtime_service = RealtimeService()

        # Create message data
        message_payload = {
            "channel_type": "Facebook",
            "channel_id": sender_id,
            "content": message_text,
            "sender": sender_id,
            "message_id": message.get("mid"),
            "metadata": {
                "facebook_message_id": message.get("mid"),
                "timestamp": messaging_event.get("timestamp"),
                "raw_data": messaging_event,
            },
        }

        # Real-time broadcast only (no omnichannel AI routing here)
        realtime_service.broadcast_message(
            "Facebook",
            sender_id,
            message_payload,
            target_users=get_available_agents(),
        )

    except Exception as e:
        frappe.log_error(f"Error processing Facebook message: {str(e)}", "Real-time Webhooks")


@frappe.whitelist(allow_guest=True)
def telegram_webhook():
    """Enhanced Telegram webhook with real-time processing"""
    try:
        data = json.loads(frappe.request.data)

        # 1) Persist via legacy Unified Inbox pipeline (consistent with Facebook/Instagram)
        try:
            from assistant_crm.api.social_media_ports import TelegramIntegration
            TelegramIntegration().process_webhook(data)
        except Exception as persist_err:
            frappe.log_error(f"Telegram persist error: {str(persist_err)}", "Telegram Webhook")

        # 2) Enqueue async AI processing for the saved conversation (same pattern as Facebook)
        try:
            msg = (data.get("message") or {})
            chat = (msg.get("chat") or {})
            chat_id = str(chat.get("id") or "")

            if chat_id:
                conversation = frappe.db.get_value(
                    "Unified Inbox Conversation",
                    {"platform": "Telegram", "platform_specific_id": chat_id},
                    "name",
                )
                if conversation:
                    frappe.enqueue(
                        "assistant_crm.api.unified_inbox_api.process_conversation_with_ai",
                        conversation_id=conversation,
                        queue="long",
                    )
        except Exception as e_enqueue:
            frappe.log_error(f"Enqueue AI error: {str(e_enqueue)}", "Telegram Webhook")

        # 3) Commit persistence before any optional realtime/broadcasting to avoid rollbacks
        try:
            frappe.db.commit()
        except Exception:
            pass

        # 4) Optional: real-time broadcast to online agents (kept for live UI updates)
        try:
            if "message" in data:
                process_telegram_message_realtime(data["message"])
        except Exception as rt_err:
            # Never fail the webhook just because realtime broadcast failed
            frappe.log_error(f"Telegram realtime broadcast error: {str(rt_err)}", "Telegram Webhook")

        return {"status": "success"}

    except Exception as e:
        frappe.log_error(f"Telegram webhook error: {str(e)}", "Real-time Webhooks")
        return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=True)
def twitter_webhook():
    """Twitter (X) Account Activity webhook with CRC + signature verification."""
    try:
        # Handle CRC verification on GET
        if frappe.request.method == "GET":
            return handle_twitter_crc()

        # Verify signature on POST
        if not verify_twitter_signature():
            frappe.throw(_("Invalid webhook signature"), frappe.AuthenticationError)

        data = json.loads(frappe.request.data or "{}")

        # Persist via Unified Inbox pipeline
        from assistant_crm.api.social_media_ports import TwitterIntegration
        TwitterIntegration().process_webhook(data)

        # Enqueue async AI processing for the saved conversation
        try:
            sender_id = None
            if isinstance(data.get("direct_message_events"), list):
                for ev in data.get("direct_message_events") or []:
                    mc = (ev.get("message_create") or {})
                    sid = str(mc.get("sender_id") or "")
                    if sid and sid != str(data.get("for_user_id") or ""):
                        sender_id = sid
                        break
            elif isinstance(data.get("dm_events"), list):
                for ev in data.get("dm_events") or []:
                    mc = (ev.get("message_create") or {})
                    sid = str(mc.get("sender_id") or "")
                    if sid and sid != str(data.get("for_user_id") or ""):
                        sender_id = sid
                        break

            if sender_id:
                conversation = frappe.db.get_value(
                    "Unified Inbox Conversation",
                    {"platform": "Twitter", "platform_specific_id": sender_id},
                    "name",
                )
                if conversation:
                    frappe.enqueue(
                        "assistant_crm.api.unified_inbox_api.process_conversation_with_ai",
                        conversation_id=conversation,
                        queue="long",
                    )
        except Exception as e:
            frappe.log_error(f"Twitter enqueue AI error: {str(e)}", "Twitter Webhook")

        return {"status": "success"}

    except Exception as e:
        frappe.log_error(f"Twitter webhook error: {str(e)}", "Real-time Webhooks")
        return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=True)
def linkedin_webhook():
    """LinkedIn webhook handler aligned with Unified Inbox pipeline."""
    try:
        # 1) Handle verification GET first
        if frappe.request.method == "GET":
            return handle_linkedin_verification()

        # 2) Verify signature on POST (optional if not configured)
        if not verify_linkedin_signature():
            frappe.throw(_("Invalid webhook signature"), frappe.AuthenticationError)

        data = json.loads(frappe.request.data or "{}")

        # 3) Persist via Unified Inbox pipeline
        from assistant_crm.api.social_media_ports import LinkedInIntegration
        result = LinkedInIntegration().process_webhook(data)

        # 4) Enqueue async AI processing for the saved conversation
        try:
            conversation = (result or {}).get("conversation_id")
            if conversation:
                frappe.enqueue(
                    "assistant_crm.api.unified_inbox_api.process_conversation_with_ai",
                    conversation_id=conversation,
                    queue="long",
                )
        except Exception as e:
            frappe.log_error(f"LinkedIn enqueue AI error: {str(e)}", "LinkedIn Webhook")

        return {"status": "success"}

    except Exception as e:
        frappe.log_error(f"LinkedIn webhook error: {str(e)}", "Real-time Webhooks")
        return {"status": "error", "message": str(e)}


def verify_linkedin_signature():
    """Verify LinkedIn webhook signature.
    LinkedIn typically sends X-LI-Signature as base64(HMAC_SHA256(secret, body)).
    If no secret configured, allow for easier initial testing per project convention.
    """
    try:
        signature = frappe.request.headers.get("X-LI-Signature") or frappe.request.headers.get("x-li-signature")
        # If header missing, allow (we keep verification optional unless configured)
        if not signature:
            return True

        settings = frappe.get_single("Social Media Settings")
        try:
            secret = settings.get_password("linkedin_webhook_secret")
        except Exception:
            secret = settings.get("linkedin_webhook_secret")
        if not secret:
            # Allow if not configured
            return True

        raw_body = frappe.request.data or b""
        if isinstance(raw_body, str):
            raw_body = raw_body.encode("utf-8")

        import hmac, hashlib, base64
        digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
        expected_b64 = base64.b64encode(digest).decode("utf-8")
        # Some implementations might send hex; accept either to be tolerant in dev
        expected_hex = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return signature == expected_b64 or signature == expected_hex
    except Exception:
        return True  # Be tolerant in early setup


def handle_linkedin_verification():
    """Return the challenge param if present, else 'ok'."""
    try:
        challenge = frappe.request.args.get("challenge") or frappe.request.args.get("hub.challenge")
        if challenge:
            return challenge
        return "ok"
    except Exception:
        return "ok"


@frappe.whitelist(allow_guest=True)
def youtube_webhook():
    """YouTube webhook handler for PubSubHubbub and custom integrations.

    Supports:
    - GET: WebSub/PubSubHubbub subscription verification
    - POST: Incoming notifications (new videos, comments via Make.com, etc.)

    Flow: Webhook → YouTubeIntegration.process_webhook() →
          Unified Inbox Conversation → Unified Inbox Message → AI Processing
    """
    try:
        # 1) Handle WebSub verification on GET
        if frappe.request.method == "GET":
            return handle_youtube_verification()

        # 2) Verify signature on POST (optional, depends on configuration)
        if not verify_youtube_signature():
            frappe.throw(_("Invalid webhook signature"), frappe.AuthenticationError)

        # 3) Parse request body - YouTube PubSubHubbub sends Atom XML,
        #    but Make.com/custom integrations send JSON
        raw_body = frappe.request.data or b""
        if isinstance(raw_body, bytes):
            raw_body = raw_body.decode("utf-8")

        data = {}
        content_type = frappe.request.headers.get("Content-Type", "")

        if "application/json" in content_type:
            data = json.loads(raw_body or "{}")
        elif "application/atom+xml" in content_type or "text/xml" in content_type:
            # Parse Atom XML from PubSubHubbub
            data = parse_youtube_atom_feed(raw_body)
        else:
            # Try JSON first, fallback to Atom
            try:
                data = json.loads(raw_body or "{}")
            except json.JSONDecodeError:
                data = parse_youtube_atom_feed(raw_body)

        # 4) Persist via Unified Inbox pipeline
        from assistant_crm.api.social_media_ports import YouTubeIntegration
        result = YouTubeIntegration().process_webhook(data)

        # 5) Enqueue async AI processing for the saved conversation
        try:
            conversation = (result or {}).get("conversation_id")
            if conversation:
                frappe.enqueue(
                    "assistant_crm.api.unified_inbox_api.process_conversation_with_ai",
                    conversation_id=conversation,
                    queue="long",
                )
        except Exception as e:
            frappe.log_error(f"YouTube enqueue AI error: {str(e)}", "YouTube Webhook")

        return {"status": "success"}

    except Exception as e:
        frappe.log_error(f"YouTube webhook error: {str(e)}", "Real-time Webhooks")
        return {"status": "error", "message": str(e)}


def verify_youtube_signature():
    """Verify YouTube webhook signature.

    For PubSubHubbub, YouTube sends X-Hub-Signature header with HMAC-SHA1.
    If no secret configured, allow for easier initial testing.
    """
    try:
        signature = (
            frappe.request.headers.get("X-Hub-Signature") or
            frappe.request.headers.get("x-hub-signature") or
            frappe.request.headers.get("X-YouTube-Signature") or
            frappe.request.headers.get("x-youtube-signature")
        )

        # If header missing, allow (verification optional unless configured)
        if not signature:
            return True

        settings = frappe.get_single("Social Media Settings")
        try:
            secret = settings.get_password("youtube_webhook_secret")
        except Exception:
            secret = settings.get("youtube_webhook_secret")

        if not secret:
            # Allow if not configured
            return True

        raw_body = frappe.request.data or b""
        if isinstance(raw_body, str):
            raw_body = raw_body.encode("utf-8")

        # PubSubHubbub uses SHA1, custom integrations might use SHA256
        if signature.startswith("sha256="):
            expected = "sha256=" + hmac.new(
                secret.encode("utf-8"), raw_body, hashlib.sha256
            ).hexdigest()
        else:
            # Default to SHA1 for PubSubHubbub
            algo_part = signature.split("=")[0] if "=" in signature else "sha1"
            if algo_part == "sha1":
                expected = "sha1=" + hmac.new(
                    secret.encode("utf-8"), raw_body, hashlib.sha1
                ).hexdigest()
            else:
                expected = signature  # Can't verify unknown algo

        return hmac.compare_digest(signature, expected)
    except Exception:
        return True  # Be tolerant in early setup


def handle_youtube_verification():
    """Handle YouTube PubSubHubbub/WebSub subscription verification.

    YouTube sends:
    - hub.mode: 'subscribe' or 'unsubscribe'
    - hub.topic: The feed URL being subscribed to
    - hub.challenge: Random string to echo back
    - hub.lease_seconds: How long the subscription is valid
    - hub.verify_token: Optional verification token (if provided during subscription)
    """
    try:
        hub_mode = frappe.request.args.get("hub.mode")
        hub_challenge = frappe.request.args.get("hub.challenge")
        hub_verify_token = frappe.request.args.get("hub.verify_token")

        if not hub_challenge:
            return {"status": "error", "message": "Missing hub.challenge"}

        # Verify token if configured
        if hub_verify_token:
            settings = frappe.get_single("Social Media Settings")
            expected_token = settings.get("webhook_verify_token") or ""
            if expected_token and hub_verify_token != expected_token:
                frappe.throw(_("Invalid verify token"), frappe.AuthenticationError)

        # Echo back the challenge for subscription confirmation
        # Must return plain text, not JSON
        from werkzeug.wrappers import Response
        return Response(hub_challenge, content_type='text/plain', status=200)

    except Exception as e:
        frappe.log_error(f"YouTube verification error: {str(e)}", "YouTube Webhook")
        from werkzeug.wrappers import Response
        return Response("Verification failed", content_type='text/plain', status=403)


def parse_youtube_atom_feed(xml_content: str) -> dict:
    """Parse YouTube Atom feed XML into a dictionary for processing.

    YouTube PubSubHubbub sends Atom XML with structure:
    <feed>
        <entry>
            <yt:videoId>VIDEO_ID</yt:videoId>
            <yt:channelId>CHANNEL_ID</yt:channelId>
            <title>Video Title</title>
            <author><name>Channel Name</name></author>
            <published>2025-01-15T10:00:00+00:00</published>
            <updated>2025-01-15T10:00:00+00:00</updated>
        </entry>
    </feed>
    """
    try:
        import xml.etree.ElementTree as ET

        # Handle namespace prefixes
        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'yt': 'http://www.youtube.com/xml/schemas/2015',
        }

        root = ET.fromstring(xml_content)

        entries = []

        # Find all entry elements
        for entry in root.findall('.//atom:entry', namespaces) or root.findall('.//entry'):
            entry_data = {}

            # Extract yt:videoId
            video_id_elem = entry.find('.//yt:videoId', namespaces)
            if video_id_elem is not None:
                entry_data['videoId'] = video_id_elem.text
            else:
                # Try without namespace
                for child in entry:
                    if 'videoId' in child.tag:
                        entry_data['videoId'] = child.text
                        break

            # Extract yt:channelId
            channel_id_elem = entry.find('.//yt:channelId', namespaces)
            if channel_id_elem is not None:
                entry_data['channelId'] = channel_id_elem.text
            else:
                for child in entry:
                    if 'channelId' in child.tag:
                        entry_data['channelId'] = child.text
                        break

            # Extract title
            title_elem = entry.find('.//atom:title', namespaces) or entry.find('.//title')
            if title_elem is not None:
                entry_data['title'] = title_elem.text

            # Extract author name
            author_elem = entry.find('.//atom:author/atom:name', namespaces) or entry.find('.//author/name')
            if author_elem is not None:
                entry_data['author'] = {'name': author_elem.text}

            # Extract published/updated timestamps
            published_elem = entry.find('.//atom:published', namespaces) or entry.find('.//published')
            if published_elem is not None:
                entry_data['published'] = published_elem.text

            updated_elem = entry.find('.//atom:updated', namespaces) or entry.find('.//updated')
            if updated_elem is not None:
                entry_data['updated'] = updated_elem.text

            if entry_data:
                entries.append(entry_data)

        return {'feed': True, 'entry': entries}

    except Exception as e:
        frappe.log_error(f"YouTube Atom parse error: {str(e)}", "YouTube Webhook")
        return {}


def verify_twitter_signature():
    """Verify Twitter webhook signature: X-Twitter-Webhooks-Signature = 'sha256=' + base64(HMAC_SHA256(secret, body))."""
    try:
        signature = frappe.request.headers.get("X-Twitter-Webhooks-Signature") or \
                    frappe.request.headers.get("x-twitter-webhooks-signature")
        if not signature:
            return False

        settings = frappe.get_single("Social Media Settings")
        # Prefer dedicated webhook secret; fall back to client/api secret during early setup
        try:
            webhook_secret = settings.get_password("twitter_webhook_secret")
        except Exception:
            webhook_secret = settings.get("twitter_webhook_secret")
        if not webhook_secret:
            try:
                webhook_secret = settings.get_password("twitter_client_secret")
            except Exception:
                webhook_secret = settings.get("twitter_client_secret")
        if not webhook_secret:
            try:
                webhook_secret = settings.get_password("twitter_api_secret")
            except Exception:
                webhook_secret = settings.get("twitter_api_secret")

        if not webhook_secret:
            # Allow if no secret configured to simplify initial testing
            return True

        import hmac, hashlib, base64
        raw_body = frappe.request.data or b""
        if isinstance(raw_body, str):
            raw_body = raw_body.encode("utf-8")
        expected_sig = "sha256=" + base64.b64encode(
            hmac.new(webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
        ).decode("utf-8")
        return hmac.compare_digest(signature, expected_sig)
    except Exception:
        return False


def handle_twitter_crc():
    """Handle Twitter CRC challenge using HMAC-SHA256 of crc_token with webhook secret."""
    try:
        crc_token = frappe.request.args.get("crc_token")
        if not crc_token:
            return {"status": "error", "message": "Missing crc_token"}

        settings = frappe.get_single("Social Media Settings")
        try:
            webhook_secret = settings.get_password("twitter_webhook_secret")
        except Exception:
            webhook_secret = settings.get("twitter_webhook_secret")
        if not webhook_secret:
            try:
                webhook_secret = settings.get_password("twitter_client_secret")
            except Exception:
                webhook_secret = settings.get("twitter_client_secret")

        import hmac, hashlib, base64
        response_token = "sha256=" + base64.b64encode(
            hmac.new(webhook_secret.encode("utf-8"), crc_token.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")
        return {"response_token": response_token}
    except Exception as e:
        frappe.log_error(f"Twitter CRC error: {str(e)}", "Twitter Webhook")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def twitter_register_webhook(webhook_url: str = None):
    """Register Twitter Account Activity webhook for the configured environment.
    Requires API Key/Secret and Access Token/Secret (OAuth 1.0a user context).
    If webhook_url is not provided, falls back to Social Media Settings field
    `twitter_webhook_url` or builds from frappe.utils.get_url.
    """
    try:
        settings = frappe.get_single("Social Media Settings")
        env = (settings.get("twitter_webhook_env") or "").strip()
        if not env:
            return {"status": "error", "message": "Missing twitter_webhook_env in Social Media Settings"}

        # Credentials
        api_key = (settings.get("twitter_api_key") or "").strip()
        try:
            api_secret = (settings.get_password("twitter_api_secret") or "").strip()
        except Exception:
            api_secret = (settings.get("twitter_api_secret") or "").strip()
        try:
            access_token = (settings.get_password("twitter_access_token") or "").strip()
        except Exception:
            access_token = (settings.get("twitter_access_token") or "").strip()
        try:
            access_token_secret = (settings.get_password("twitter_access_token_secret") or "").strip()
        except Exception:
            access_token_secret = (settings.get("twitter_access_token_secret") or "").strip()

        if not (api_key and api_secret and access_token and access_token_secret):
            return {"status": "error", "message": "Missing API key/secret or access token/secret in Social Media Settings"}

        # Determine webhook URL
        if not webhook_url:
            webhook_url = (settings.get("twitter_webhook_url") or "").strip()
        if not webhook_url:
            from frappe.utils import get_url
            webhook_url = f"{get_url()}/api/omnichannel/webhook/twitter"

        # Build OAuth 1.0a header
        import time, uuid, hmac, hashlib, base64, urllib.parse as urlparse
        base_endpoint = f"https://api.twitter.com/1.1/account_activity/all/{env}/webhooks.json"
        oauth_params = {
            "oauth_consumer_key": api_key,
            "oauth_nonce": uuid.uuid4().hex,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": access_token,
            "oauth_version": "1.0",
        }
        def pct_encode(s: str) -> str:
            return urlparse.quote(str(s), safe="~")
        # The request uses query param `url`
        query_params = {"url": webhook_url}
        # Signature base string parameters: include both OAuth and query params
        sig_params = {**oauth_params, **query_params}
        items = [(pct_encode(k), pct_encode(v)) for k, v in sig_params.items()]
        items.sort()
        param_str = "&".join([f"{k}={v}" for k, v in items])
        base_string = "&".join(["POST", pct_encode(base_endpoint), pct_encode(param_str)])
        signing_key = f"{pct_encode(api_secret)}&{pct_encode(access_token_secret)}"
        signature = base64.b64encode(
            hmac.new(signing_key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1).digest()
        ).decode("utf-8")
        header_kv = ", ".join([f'{k}="{pct_encode(v)}"' for k, v in {**oauth_params, "oauth_signature": signature}.items()])
        auth_header = f"OAuth {header_kv}"

        headers = {"Authorization": auth_header}
        resp = requests.post(base_endpoint, params=query_params, headers=headers, timeout=20)
        return {"status": "success" if resp.status_code in (200, 204) else "error", "code": resp.status_code, "body": resp.text}
    except Exception as e:
        frappe.log_error(f"Twitter register webhook error: {str(e)}", "Twitter Webhook Setup")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def twitter_subscribe_account():
    """Create a user subscription for the configured environment so the account receives events."""
    try:
        settings = frappe.get_single("Social Media Settings")
        env = (settings.get("twitter_webhook_env") or "").strip()
        if not env:
            return {"status": "error", "message": "Missing twitter_webhook_env in Social Media Settings"}

        api_key = (settings.get("twitter_api_key") or "").strip()
        try:
            api_secret = (settings.get_password("twitter_api_secret") or "").strip()
        except Exception:
            api_secret = (settings.get("twitter_api_secret") or "").strip()
        try:
            access_token = (settings.get_password("twitter_access_token") or "").strip()
        except Exception:
            access_token = (settings.get("twitter_access_token") or "").strip()
        try:
            access_token_secret = (settings.get_password("twitter_access_token_secret") or "").strip()
        except Exception:
            access_token_secret = (settings.get("twitter_access_token_secret") or "").strip()

        if not (api_key and api_secret and access_token and access_token_secret):
            return {"status": "error", "message": "Missing API key/secret or access token/secret in Social Media Settings"}

        import time, uuid, hmac, hashlib, base64, urllib.parse as urlparse
        endpoint = f"https://api.twitter.com/1.1/account_activity/all/{env}/subscriptions.json"
        oauth_params = {
            "oauth_consumer_key": api_key,
            "oauth_nonce": uuid.uuid4().hex,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": access_token,
            "oauth_version": "1.0",
        }
        def pct_encode(s: str) -> str:
            return urlparse.quote(str(s), safe="~")
        items = [(pct_encode(k), pct_encode(v)) for k, v in oauth_params.items()]
        items.sort()
        param_str = "&".join([f"{k}={v}" for k, v in items])
        base_string = "&".join(["POST", pct_encode(endpoint), pct_encode(param_str)])
        signing_key = f"{pct_encode(api_secret)}&{pct_encode(access_token_secret)}"
        signature = base64.b64encode(
            hmac.new(signing_key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1).digest()
        ).decode("utf-8")
        header_kv = ", ".join([f'{k}="{pct_encode(v)}"' for k, v in {**oauth_params, "oauth_signature": signature}.items()])
        auth_header = f"OAuth {header_kv}"

        headers = {"Authorization": auth_header}
        resp = requests.post(endpoint, headers=headers, timeout=20)
        return {"status": "success" if resp.status_code in (204, 200) else "error", "code": resp.status_code, "body": resp.text}
    except Exception as e:
        frappe.log_error(f"Twitter subscribe error: {str(e)}", "Twitter Webhook Setup")
        return {"status": "error", "message": str(e)}



def process_telegram_message_realtime(message):
    """Process Telegram message with real-time broadcasting"""
    try:
        chat_id = str(message["chat"]["id"])
        message_text = message.get("text", "")
        message_id = message.get("message_id")

        # Handle different message types
        if "photo" in message:
            message_text = "[Photo received]"
        elif "document" in message:
            message_text = "[Document received]"
        elif "voice" in message:
            message_text = "[Voice message received]"

        # Convert Unix timestamp to UTC for accurate timestamps
        import datetime
        unix_timestamp = message.get("date", 0)
        if unix_timestamp:
            # Use UTC conversion to fix timestamp accuracy
            dt = datetime.datetime.utcfromtimestamp(unix_timestamp)
            accurate_timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            from frappe.utils import now
            accurate_timestamp = now()

        realtime_service = RealtimeService()
        router = OmnichannelRouter()

        # Create message data
        message_payload = {
            "channel_type": "Telegram",
            "channel_id": chat_id,
            "content": message_text,
            "sender": message["from"]["first_name"],
            "message_id": str(message_id),
            "metadata": {
                "telegram_message_id": message_id,
                "chat_id": chat_id,
                "from_user": message["from"],
                "timestamp": unix_timestamp,
                "accurate_timestamp": accurate_timestamp
            }
        }

        # Real-time broadcast
        realtime_service.broadcast_message(
            "Telegram",
            chat_id,
            message_payload,
            target_users=get_available_agents()
        )

        # Route message with accurate timestamp
        routing_result = router.route_message(
            "Telegram",
            chat_id,
            message_text,
            {"telegram_message_id": message_id},
            received_at=accurate_timestamp
        )

        # Broadcast routing result
        if routing_result.get("success"):
            realtime_service.broadcast_conversation_update(
                routing_result.get("conversation_id", chat_id),
                "message_processed",
                {"routing_result": routing_result}
            )

    except Exception as e:
        frappe.log_error(f"Error processing Telegram message: {str(e)}", "Real-time Webhooks")


# Utility functions

def get_available_agents():
    """Get list of available agents for message broadcasting"""
    try:
        agents = frappe.db.sql("""
            SELECT user
            FROM `tabAgent Dashboard`
            WHERE status IN ('online', 'available')
            AND active_conversations < max_conversations
        """, as_dict=True)

        return [agent.user for agent in agents]
    except Exception:
        return []


def verify_whatsapp_signature():
    """Verify WhatsApp webhook signature"""
    try:
        signature = frappe.request.headers.get("X-Hub-Signature-256", "")
        if not signature:
            return False

        # Get webhook secret from settings
        settings = frappe.get_single("Assistant CRM Settings")
        webhook_secret = settings.get_password("whatsapp_webhook_secret")

        if not webhook_secret:
            return True  # Skip verification if no secret configured

        expected_signature = "sha256=" + hmac.new(
            webhook_secret.encode(),
            frappe.request.data,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)
    except Exception:
        return False


def verify_facebook_signature():
    """Verify Facebook webhook signature.
    Behavior:
    - If no secret is configured (in either Assistant CRM Settings or Social Media Settings), skip verification (return True)
    - If a secret exists, accept either:
      • X-Hub-Signature-256: sha256 HMAC of request body
      • X-Hub-Signature: sha1 HMAC of request body (legacy)
    """
    try:
        # 1) Resolve secret from settings (Assistant CRM Settings preferred, fallback to Social Media Settings)
        secret = None
        try:
            acs = frappe.get_single("Assistant CRM Settings")
            secret = (acs.get_password("facebook_webhook_secret") or acs.get("facebook_webhook_secret"))
        except Exception:
            secret = None
        if not secret:
            try:
                sms = frappe.get_single("Social Media Settings")
                # Prefer dedicated facebook_webhook_secret, else generic webhook_secret
                secret = (
                    (sms.get_password("facebook_webhook_secret") if hasattr(sms, "get_password") else None)
                    or sms.get("facebook_webhook_secret")
                    or (sms.get_password("webhook_secret") if hasattr(sms, "get_password") else None)
                    or sms.get("webhook_secret")
                )
            except Exception:
                secret = None

        # If no secret configured anywhere, allow (compatibility for initial setup)
        if not secret:
            return True

        headers = frappe.request.headers
        sig256 = headers.get("X-Hub-Signature-256") or headers.get("x-hub-signature-256")
        sig1 = headers.get("X-Hub-Signature") or headers.get("x-hub-signature")

        raw_body = frappe.request.data or b""
        if isinstance(raw_body, str):
            raw_body = raw_body.encode("utf-8")

        if sig256:
            expected256 = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
            return hmac.compare_digest(sig256, expected256)

        if sig1:
            expected1 = "sha1=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha1).hexdigest()
            return hmac.compare_digest(sig1, expected1)

        # No acceptable signature header provided
        return False
    except Exception:
        return False


def handle_whatsapp_verification():
    """Handle WhatsApp webhook verification"""
    verify_token = frappe.request.args.get("hub.verify_token")
    challenge = frappe.request.args.get("hub.challenge")

    settings = frappe.get_single("Assistant CRM Settings")
    expected_token = settings.get("whatsapp_verify_token")

    if verify_token == expected_token:
        return challenge
    else:
        frappe.throw(_("Invalid verify token"), frappe.AuthenticationError)


def handle_facebook_verification():
    """Handle Facebook webhook verification (supports multiple settings sources).
    Accept if hub.verify_token matches any of:
    - Assistant CRM Settings.facebook_verify_token
    - Social Media Settings.facebook_verify_token
    - Social Media Settings.webhook_verify_token
    """
    verify_token = frappe.request.args.get("hub.verify_token")
    challenge = frappe.request.args.get("hub.challenge")

    expected_tokens = []
    try:
        acs = frappe.get_single("Assistant CRM Settings")
        t = (acs.get("facebook_verify_token") or "").strip()
        if t:
            expected_tokens.append(t)
    except Exception:
        pass

    try:
        sms = frappe.get_single("Social Media Settings")
        for key in ("facebook_verify_token", "webhook_verify_token"):
            v = (sms.get(key) or "").strip()
            if v:
                expected_tokens.append(v)
    except Exception:
        pass

    if verify_token and verify_token in expected_tokens:
        return challenge
    else:
        frappe.throw(_("Invalid verify token"), frappe.AuthenticationError)
