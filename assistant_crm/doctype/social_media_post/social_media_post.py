# Copyright (c) 2026, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class SocialMediaPost(Document):

    def validate(self):
        self._validate_platforms_unique()
        self._validate_schedule()

    def _validate_platforms_unique(self):
        """Each platform should appear at most once in the target list."""
        seen = set()
        for row in self.target_platforms or []:
            if row.platform in seen:
                frappe.throw(
                    f"Platform <b>{row.platform}</b> is listed more than once. "
                    "Each platform can only be selected once per post."
                )
            seen.add(row.platform)

    def _validate_schedule(self):
        """If not publishing immediately, a future datetime is required."""
        if not self.send_immediately:
            if not self.scheduled_datetime:
                frappe.throw("Please set a <b>Scheduled Date & Time</b> or enable <b>Publish Immediately</b>.")
            if frappe.utils.get_datetime(self.scheduled_datetime) <= now_datetime():
                frappe.throw("Scheduled Date & Time must be in the future.")

    def on_update(self):
        # Reload status directly from DB to avoid stale in-memory value
        current_status = frappe.db.get_value("Social Media Post", self.name, "status") or "Draft"

        if self.send_immediately and current_status == "Draft":
            self._enqueue_publish()
        elif not self.send_immediately and current_status == "Draft" and self.scheduled_datetime:
            # Mark as Scheduled so the cron job picks it up; commit immediately
            self.db_set("status", "Scheduled", commit=True, notify=True)

    def _enqueue_publish(self):
        # job_name deduplicates: if a job for this post is already queued/running,
        # the second enqueue is a no-op.
        frappe.enqueue(
            "assistant_crm.api.social_media_publisher.publish_post_to_platforms",
            post_name=self.name,
            queue="long",
            timeout=300,
            job_name=f"social_post_{self.name}"
        )
