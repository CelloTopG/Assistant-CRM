# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class SurveyAccessToken(Document):
    def before_insert(self):
        if not self.token:
            self.token = frappe.generate_hash(length=32)
        if not self.watermark_id:
            self.watermark_id = frappe.generate_hash(length=8).upper()
