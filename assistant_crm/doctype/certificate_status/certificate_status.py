# Copyright (c) 2024, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_months


class CertificateStatus(Document):
    """Certificate Status DocType

    NOTE: Employer Profile and Employee Profile doctypes have been removed.
    Now uses ERPNext Customer and Employee doctypes.
    WCFCBIntegrationService has also been removed.
    """

    def before_save(self):
        """Update calculated fields and sync status"""
        # Get employer name from ERPNext Customer (replaces Employer Profile)
        if self.employer_code:
            customer = frappe.db.get_value("Customer", self.employer_code, "customer_name")
            if customer:
                self.employer_name = customer

        # Get employee name from ERPNext Employee (replaces Employee Profile)
        if self.employee_number:
            employee_name = frappe.db.get_value("Employee", self.employee_number, "employee_name")
            if employee_name:
                self.employee_name = employee_name

        # Calculate expiry date if not set
        if self.issue_date and self.validity_period_months and not self.expiry_date:
            self.expiry_date = add_months(self.issue_date, self.validity_period_months)

        # Set renewal due date
        if self.expiry_date and self.renewal_required:
            self.renewal_due_date = add_months(self.expiry_date, -1)  # 1 month before expiry

        # Update certificate status based on dates
        self.update_certificate_status()

        # Update sync status when document is modified
        if self.has_value_changed():
            self.sync_status = "Pending"

    def after_insert(self):
        """Trigger sync after new certificate is created"""
        self.sync_to_corebusiness()

    def after_save(self):
        """Trigger sync after certificate is updated"""
        if self.sync_status == "Pending":
            self.sync_to_corebusiness()

    def sync_to_corebusiness(self):
        """Sync certificate data to CoreBusiness system

        NOTE: WCFCBIntegrationService has been removed.
        """
        try:
            # WCFCBIntegrationService has been removed - mark as synced locally
            self.db_set("sync_status", "Synced")
            self.db_set("last_sync_datetime", frappe.utils.now())

        except Exception as e:
            frappe.log_error(f"Error syncing certificate {self.certificate_number}: {str(e)}")
            self.db_set("sync_status", "Failed")
    
    def update_certificate_status(self):
        """Update certificate status based on current date"""
        today = getdate()
        
        if self.expiry_date:
            if today > self.expiry_date:
                self.certificate_status = "Expired"
            elif self.renewal_required and self.renewal_due_date and today >= self.renewal_due_date:
                self.certificate_status = "Pending Renewal"
            else:
                self.certificate_status = "Valid"
    
    def is_valid(self):
        """Check if certificate is currently valid"""
        return self.certificate_status == "Valid"
    
    def days_until_expiry(self):
        """Calculate days until certificate expires"""
        if self.expiry_date:
            today = getdate()
            return (self.expiry_date - today).days
        return None
