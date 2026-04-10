#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Social Media Publisher
=============================================

Orchestrates publishing a Social Media Post document to one or more
platforms (Facebook, Instagram, Twitter, LinkedIn) in a single operation.

Responsibilities:
- Scheduled-post dispatch (called by cron every 5 min)
- Per-platform content assembly (shared content + per-platform overrides)
- Calling each platform adapter's publish_post() method
- Writing Social Media Post Result rows back to the document
- Setting the final status (Published / Partially Published / Failed)

Intentionally kept separate from social_media_ports.py which handles the
inbox/messaging side of each platform.

Author: WCFCB Development Team
Created: 2026-04-01
"""

import html
import re
import frappe
from frappe.utils import now_datetime
from typing import Optional


def _html_to_plain_text(content: str) -> str:
    """
    Convert Quill / Text Editor HTML to clean plain text suitable for social posts.
    Handles <br>, <p>, <div> line breaks and decodes HTML entities.
    """
    if not content:
        return ""
    # Replace block-level closing tags with newlines before stripping
    content = re.sub(r"</p>|</div>|</li>|<br\s*/?>", "\n", content, flags=re.IGNORECASE)
    # Strip all remaining HTML tags
    content = re.sub(r"<[^>]+>", "", content)
    # Decode HTML entities (&amp; &lt; &nbsp; etc.)
    content = html.unescape(content)
    # Collapse 3+ consecutive newlines to 2 and strip leading/trailing whitespace
    content = re.sub(r"\n{3,}", "\n\n", content).strip()
    return content


def _resolve_file_path(frappe_url: str) -> Optional[str]:
    """
    Given a Frappe file URL (absolute or relative), return the absolute
    filesystem path if the file is stored locally, otherwise None.

    Handles both relative paths and absolute URLs pointing to this site:
      /private/files/foo.png            → sites/wcfcb/private/files/foo.png
      /files/bar.jpg                    → sites/wcfcb/public/files/bar.jpg
      http://localhost:8000/files/x.png → same as /files/x.png
    """
    try:
        import os
        from urllib.parse import urlparse

        site_path = frappe.get_site_path()

        # Strip query string
        url_no_qs = frappe_url.split("?")[0]

        # If it's an absolute URL, extract just the path component
        from urllib.parse import unquote as _url_unquote
        parsed = urlparse(url_no_qs)
        path = _url_unquote(parsed.path if parsed.scheme else url_no_qs)

        if path.startswith("/private/files/"):
            return os.path.join(site_path, "private", "files", path[len("/private/files/"):])
        if path.startswith("/files/"):
            return os.path.join(site_path, "public", "files", path[len("/files/"):])
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Scheduled entry point (called by Frappe cron via tasks.py)
# ---------------------------------------------------------------------------

def publish_scheduled_posts():
    """Find all posts whose scheduled time has arrived and dispatch them."""
    pending = frappe.get_all(
        "Social Media Post",
        filters={
            "status": "Scheduled",
            "scheduled_datetime": ["<=", now_datetime()]
        },
        pluck="name"
    )
    for post_name in pending:
        frappe.enqueue(
            "assistant_crm.api.social_media_publisher.publish_post_to_platforms",
            post_name=post_name,
            queue="long",
            timeout=300,
            # Deduplicate: don't re-enqueue if already in queue
            job_name=f"social_post_{post_name}"
        )


# ---------------------------------------------------------------------------
# Core publish logic (runs inside a background job)
# ---------------------------------------------------------------------------

def publish_post_to_platforms(post_name: str):
    """
    Publish a Social Media Post to every platform in its target_platforms table.

    Updates the post_results child table and sets the final status.
    Designed to be idempotent: skips platforms that already have a Published result.
    """
    post = frappe.get_doc("Social Media Post", post_name)

    if post.status not in ("Draft", "Scheduled"):
        frappe.log_error(
            title="Social Media Publisher: Skipped",
            message=f"Post '{post_name}' has status '{post.status}' — skipping."
        )
        return

    # Commit immediately so the scheduler won't double-dispatch and the UI
    # shows progress even if the publish step takes a long time.
    post.db_set("status", "Publishing", commit=True, notify=True)

    # Build a lookup of platforms already successfully published (for retries)
    already_done = {
        row.platform
        for row in (post.post_results or [])
        if row.status == "Success"
    }

    # Collect media URLs — convert Frappe relative paths to absolute public URLs
    # so external platforms (Instagram, LinkedIn, etc.) can fetch them.
    #
    # frappe.utils.get_url() returns the internal server address (e.g. :8000) in
    # background-worker context, which external platforms cannot reach.
    # Use assistant_crm_public_base_url from site_config if set, then host_name,
    # then fall back to get_url() as a last resort.
    site_url = (
        frappe.conf.get("assistant_crm_public_base_url")
        or frappe.conf.get("host_name")
        or frappe.utils.get_url()
    ).rstrip("/")

    media_urls = []
    for att in (post.media_attachments or []):
        url = (att.attachment or "").strip()
        if not url:
            continue
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"{site_url}{url}"
        # Encode spaces and other invalid URL characters in the path portion
        # (e.g. filenames like "My Video 2.mp4" → "My%20Video%202.mp4")
        from urllib.parse import urlsplit, urlunsplit, quote as _url_quote
        _parts = urlsplit(url)
        url = urlunsplit(_parts._replace(path=_url_quote(_parts.path, safe="/:@!$&'()*+,;=")))
        media_urls.append(url)

    success_count = 0
    fail_count = 0

    for platform_row in post.target_platforms:
        platform_name = platform_row.platform

        if platform_name in already_done:
            success_count += 1
            continue

        # Assemble content for this platform and strip HTML from Text Editor output
        raw_content = (
            platform_row.custom_content
            if platform_row.override_content and platform_row.custom_content
            else post.content
        )
        content = _html_to_plain_text(raw_content)
        if platform_row.custom_hashtags:
            content = f"{content}\n\n{platform_row.custom_hashtags}"

        result = _publish_to_platform(platform_name, content, media_urls)

        # Persist per-platform result row
        post.append("post_results", {
            "platform": platform_name,
            "status": "Success" if result["success"] else "Failed",
            "post_id": result.get("post_id") or "",
            "post_url": result.get("post_url") or "",
            "published_at": now_datetime() if result["success"] else None,
            "error_message": result.get("error") or ""
        })

        # Update the platform row status inline (visible without expanding results)
        platform_row.post_id = result.get("post_id") or ""
        platform_row.post_url = result.get("post_url") or ""
        platform_row.status = "Published" if result["success"] else "Failed"

        if result["success"]:
            success_count += 1
        else:
            fail_count += 1

    # Determine final status
    if fail_count == 0:
        final_status = "Published"
    elif success_count == 0:
        final_status = "Failed"
    else:
        final_status = "Partially Published"

    post.status = final_status
    try:
        post.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        # If save() fails (e.g. DB lock timeout), at least commit the status
        # directly so the UI reflects the actual outcome.
        frappe.log_error(
            title="Social Media Publisher: save() failed — using db_set fallback",
            message=frappe.get_traceback()
        )
        frappe.db.set_value("Social Media Post", post_name, "status", final_status)
        frappe.db.commit()


# ---------------------------------------------------------------------------
# Whitelisted API — called from the form JS "Publish Now" button
# ---------------------------------------------------------------------------

@frappe.whitelist()
def publish_now(post_name: str) -> dict:
    """Immediately enqueue a publish job for the given post."""
    try:
        if not frappe.db.exists("Social Media Post", post_name):
            return {"success": False, "error": "Post not found."}

        post_status = frappe.db.get_value("Social Media Post", post_name, "status")
        if post_status not in ("Draft", "Scheduled", "Failed", "Partially Published"):
            return {
                "success": False,
                "error": f"Cannot publish a post with status '{post_status}'."
            }

        # Reset per-platform status on retries so fresh results are written
        if post_status in ("Failed", "Partially Published"):
            frappe.db.set_value("Social Media Post", post_name, "status", "Draft")

        frappe.enqueue(
            "assistant_crm.api.social_media_publisher.publish_post_to_platforms",
            post_name=post_name,
            queue="long",
            timeout=300,
            job_name=f"social_post_{post_name}"
        )
        return {"success": True, "message": "Publishing started in the background."}

    except Exception:
        frappe.log_error(title="Social Media Publisher: publish_now Error", message=frappe.get_traceback())
        return {"success": False, "error": "An unexpected error occurred. Check the error log for details."}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _publish_to_platform(platform_name: str, content: str, media_urls: list) -> dict:
    """Instantiate the correct adapter and call publish_post()."""
    try:
        adapter = _get_adapter(platform_name)
        if adapter is None:
            return {"success": False, "error": f"No adapter registered for platform '{platform_name}'."}

        if not adapter.is_configured:
            return {"success": False, "error": f"{platform_name} credentials are not configured in Social Media Settings."}

        return adapter.publish_post(content=content, media_urls=media_urls)

    except NotImplementedError:
        return {
            "success": False,
            "error": f"{platform_name} does not yet implement publish_post(). Add it to the platform adapter."
        }
    except Exception:
        frappe.log_error(
            title=f"Social Media Publisher: {platform_name} Error",
            message=frappe.get_traceback()
        )
        return {"success": False, "error": f"Unhandled exception while publishing to {platform_name}. See error log."}


def _get_adapter(platform_name: str) -> Optional[object]:
    """Return an instantiated platform adapter or None if unrecognised."""
    from assistant_crm.api.social_media_ports import (
        FacebookIntegration,
        InstagramIntegration,
        YouTubeIntegration,
    )

    registry = {
        "Facebook": FacebookIntegration,
        "Instagram": InstagramIntegration,
        "YouTube": YouTubeIntegration,
    }

    cls = registry.get(platform_name)
    return cls() if cls else None
