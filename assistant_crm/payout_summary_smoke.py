from __future__ import annotations

from typing import Any, Dict

import frappe
from frappe.utils import add_months, getdate

from assistant_crm.assistant_crm.doctype.payout_summary_report.payout_summary_report import (
    MONTHS,
    create_and_generate,
)


def _smoke_month_date() -> str:
    """Return a date string that falls in the previous month (used for payments)."""
    today = getdate()
    prev = add_months(today, -1)
    # Middle of previous month is safely inside the reporting window
    return f"{prev.year}-{prev.month:02d}-15"


def _ensure_employer(code: str, name: str) -> str:
    """Ensure employer exists using ERPNext Customer (Employer Profile removed)."""
    if frappe.db.exists("Customer", code):
        return code
    doc = frappe.get_doc(
        {
            "doctype": "Customer",
            "customer_name": name,
            "customer_type": "Company",
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_employee(emp_no: str, employer_code: str, first_name: str, last_name: str) -> str:
    """Ensure employee exists using ERPNext Employee (Employee Profile removed)."""
    if frappe.db.exists("Employee", emp_no):
        return emp_no
    doc = frappe.get_doc(
        {
            "doctype": "Employee",
            "name": emp_no,
            "employee_name": f"{first_name} {last_name}",
            "first_name": first_name,
            "last_name": last_name,
            "company": employer_code,
            "custom_nrc_number": f"{emp_no}-NRC",
            "status": "Active",
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_beneficiary(
    benef_no: str,
    employee_no: str,
    relationship: str,
    gender: str,
    first_name: str,
    last_name: str,
    monthly_amount: float,
) -> str:
    """Beneficiary Profile doctype has been removed - skipping creation."""
    # NOTE: Beneficiary Profile doctype has been removed
    # Return the benef_no as placeholder for test purposes
    frappe.log_error("Beneficiary Profile doctype removed - _ensure_beneficiary is a no-op", "Smoke Test")
    return benef_no


def _ensure_payment(title: str, beneficiary_key: str, amount: float, posting_date: str) -> str:
    if frappe.db.exists("Payment Status", title):
        return title
    doc = frappe.get_doc(
        {
            "doctype": "Payment Status",
            "title": title,
            "payment_id": title,
            "payment_type": "Benefit Payment",
            "status": "Paid",
            # We deliberately use beneficiary_number as the key here so that
            # payout_summary_report can resolve it via beneficiary_key.
            "beneficiary": beneficiary_key,
            "payment_date": posting_date,
            "amount": amount,
            "currency": "BWP",  # default currency in Payment Status
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


@frappe.whitelist()
def create_payout_smoke_data() -> Dict[str, Any]:
    """Create a small representative dataset for payout summary smoke testing.

    The dataset covers all dependant relations: Husband, Wife, Son, Daughter.
    """
    posting_date = _smoke_month_date()

    employer = _ensure_employer("EMP-SMOKE", "Smoke Test Employer")

    emp1 = _ensure_employee("EMP-SMOKE-001", employer, "John", "Tester")
    emp2 = _ensure_employee("EMP-SMOKE-002", employer, "Jane", "Tester")

    ben_husband = _ensure_beneficiary(
        "BEN-HUSBAND", emp2, "Spouse", "Male", "Husband", "Test", 1200.0
    )
    ben_wife = _ensure_beneficiary(
        "BEN-WIFE", emp1, "Spouse", "Female", "Wife", "Test", 1300.0
    )
    ben_son = _ensure_beneficiary(
        "BEN-SON", emp1, "Child", "Male", "Son", "Test", 800.0
    )
    ben_daughter = _ensure_beneficiary(
        "BEN-DAUGHTER", emp1, "Child", "Female", "Daughter", "Test", 900.0
    )

    _ensure_payment("PS-HUSBAND-1", ben_husband, 1200.0, posting_date)
    _ensure_payment("PS-WIFE-1", ben_wife, 1300.0, posting_date)
    _ensure_payment("PS-SON-1", ben_son, 800.0, posting_date)
    _ensure_payment("PS-DAUGHTER-1", ben_daughter, 900.0, posting_date)

    return {
        "employer": employer,
        "employees": [emp1, emp2],
        "beneficiaries": [ben_husband, ben_wife, ben_son, ben_daughter],
    }


@frappe.whitelist()
def run_payout_smoke_test() -> Dict[str, Any]:
    """Populate data and generate a payout summary report as a smoke test."""
    create_payout_smoke_data()

    # create_and_generate already defaults to previous month when period_type is Monthly
    result = create_and_generate(period_type="Monthly", title="SMOKE Payout Summary")
    doc = frappe.get_doc("Payout Summary Report", result.get("name"))

    dependant_summary = [
        {
            "dependant_relation": r.dependant_relation,
            "total_count": r.total_count,
            "total_amount": float(r.total_amount or 0),
        }
        for r in doc.dependant_summary
    ]

    ok = bool(doc.beneficiaries_count) and bool(dependant_summary)

    return {
        "ok": ok,
        "report_name": doc.name,
        "beneficiaries_count": doc.beneficiaries_count,
        "payroll_month": doc.payroll_month,
        "total_paid": float(doc.total_paid or 0),
        "dependant_summary": dependant_summary,
    }

