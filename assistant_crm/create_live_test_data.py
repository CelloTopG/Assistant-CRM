#!/usr/bin/env python3
"""
Create Live Test Data for WCFCB Assistant CRM
This script populates the database with realistic test data for live data integration testing.

NOTE: The following doctypes have been removed:
- Beneficiary Profile (no replacement - beneficiary data managed externally)
- Employer Profile (replaced by ERPNext Customer)
- Employee Profile (replaced by ERPNext Employee)
- Assessment Record (replaced by Compliance Report)

The test data creation functions for removed doctypes are now no-ops.
"""

import frappe
from frappe.utils import now, add_days, add_months
from datetime import datetime, timedelta
import random

def create_test_beneficiaries():
    """Create test beneficiary profiles with realistic WCFCB data.

    NOTE: Beneficiary Profile doctype has been removed. This function is now a no-op.
    """
    print("⚠️ Beneficiary Profile doctype has been removed - skipping beneficiary creation")
    return 0

def create_test_payment_status():
    """Create test payment status records."""
    
    test_payments = [
        {
            "title": "Payment for John Mwanza - December 2024",
            "payment_id": "PAY-2024-001234",
            "payment_type": "Benefit Payment",
            "status": "Paid",
            "beneficiary": "123456789",
            "payment_date": add_days(now(), -15),
            "amount": 2150.00,
            "currency": "BWP",
            "payment_method": "Bank Transfer",
            "bank_details": "Zanaco Bank - ACC12345678",
            "reference_number": "REF-2024-001234",
            "transaction_id": "TXN-20241201-001",
            "processing_stage": "Completed",
            "approval_status": "Approved",
            "approved_by": "Finance Manager",
            "approved_date": add_days(now(), -20)
        },
        {
            "title": "Payment for Mary Banda - December 2024",
            "payment_id": "PAY-2024-001235",
            "payment_type": "Benefit Payment",
            "status": "Processing",
            "beneficiary": "987654321",
            "payment_date": add_days(now(), 5),
            "amount": 1750.00,
            "currency": "BWP",
            "payment_method": "Bank Transfer",
            "bank_details": "FNB Bank - ACC98765432",
            "reference_number": "REF-2024-001235",
            "processing_stage": "Approval",
            "expected_completion": add_days(now(), 3),
            "approval_status": "Pending"
        },
        {
            "title": "Payment for Peter Phiri - January 2025",
            "payment_id": "PAY-2025-000001",
            "payment_type": "Benefit Payment",
            "status": "Approved",
            "beneficiary": "555666777",
            "payment_date": add_days(now(), 10),
            "amount": 1950.00,
            "currency": "BWP",
            "payment_method": "Bank Transfer",
            "bank_details": "Standard Bank - ACC55566677",
            "reference_number": "REF-2025-000001",
            "processing_stage": "Processing",
            "expected_completion": add_days(now(), 7),
            "approval_status": "Approved",
            "approved_by": "Finance Manager",
            "approved_date": add_days(now(), -2)
        },
        {
            "title": "Payment for Test User - January 2025",
            "payment_id": "PAY-2025-000168",
            "payment_type": "Benefit Payment",
            "status": "Paid",
            "beneficiary": "228597/62/1",
            "payment_date": add_days(now(), -10),
            "amount": 2500.00,
            "currency": "BWP",
            "payment_method": "Bank Transfer",
            "bank_details": "Zanaco Bank - ACC0005000168",
            "reference_number": "REF-2025-000168",
            "transaction_id": "TXN-20250106-168",
            "processing_stage": "Completed",
            "approval_status": "Approved",
            "approved_by": "Finance Manager",
            "approved_date": add_days(now(), -15)
        }
    ]
    
    created_count = 0
    for payment_data in test_payments:
        try:
            # Check if payment already exists
            existing = frappe.get_all("Payment Status", filters={"payment_id": payment_data["payment_id"]})
            if existing:
                print(f"Payment {payment_data['payment_id']} already exists, skipping...")
                continue
            
            # Create new payment status
            payment = frappe.get_doc({
                "doctype": "Payment Status",
                **payment_data
            })
            payment.insert()
            frappe.db.commit()
            
            print(f"✅ Created payment: {payment_data['payment_id']} for {payment_data['beneficiary']}")
            created_count += 1
            
        except Exception as e:
            print(f"❌ Error creating payment {payment_data['payment_id']}: {str(e)}")
    
    return created_count

def create_test_claims():
    """Create test claims tracking records."""
    
    test_claims = [
        {
            "title": "Medical Claim - John Mwanza",
            "claim_id": "CL-2024-001234",
            "claim_type": "Medical",
            "status": "Under Review",
            "beneficiary": "123456789",
            "submission_date": add_days(now(), -30),
            "description": "Medical treatment for work-related injury",
            "documents_required": "Medical reports, Treatment receipts, Doctor's certificate",
            "current_stage": "Medical Review",
            "next_action": "Awaiting specialist report",
            "estimated_completion": add_days(now(), 15),
            "timeline": "Submitted: 30 days ago\nInitial review: 25 days ago\nMedical assessment: 15 days ago\nSpecialist referral: 10 days ago"
        },
        {
            "title": "Incident Claim - Mary Banda",
            "claim_id": "CL-2024-001235",
            "claim_type": "Incident",
            "status": "Approved",
            "beneficiary": "987654321",
            "submission_date": add_days(now(), -45),
            "description": "Workplace accident resulting in temporary disability",
            "documents_required": "Incident report, Medical certificate, Witness statements",
            "current_stage": "Payment Processing",
            "next_action": "Payment authorization",
            "estimated_completion": add_days(now(), 5),
            "timeline": "Submitted: 45 days ago\nInvestigation: 35 days ago\nApproval: 10 days ago\nPayment processing: 3 days ago"
        },
        {
            "title": "Disability Claim - Peter Phiri",
            "claim_id": "CL-2024-001236",
            "claim_type": "Disability",
            "status": "Pending Documents",
            "beneficiary": "555666777",
            "submission_date": add_days(now(), -20),
            "description": "Permanent disability assessment",
            "documents_required": "Updated medical assessment, Disability certificate, Employment history",
            "current_stage": "Document Collection",
            "next_action": "Submit missing documents",
            "estimated_completion": add_days(now(), 30),
            "timeline": "Submitted: 20 days ago\nInitial review: 15 days ago\nDocument request: 10 days ago"
        }
    ]
    
    created_count = 0
    for claim_data in test_claims:
        try:
            # Check if claim already exists
            existing = frappe.get_all("Claims Tracking", filters={"claim_id": claim_data["claim_id"]})
            if existing:
                print(f"Claim {claim_data['claim_id']} already exists, skipping...")
                continue
            
            # Create new claims tracking
            claim = frappe.get_doc({
                "doctype": "Claims Tracking",
                **claim_data
            })
            claim.insert()
            frappe.db.commit()
            
            print(f"✅ Created claim: {claim_data['claim_id']} for {claim_data['beneficiary']}")
            created_count += 1
            
        except Exception as e:
            print(f"❌ Error creating claim {claim_data['claim_id']}: {str(e)}")
    
    return created_count

def create_test_employers():
    """Create test employers using ERPNext Customer doctype.

    NOTE: Employer Profile doctype has been removed. Using ERPNext Customer instead.
    """
    print("⚠️ Employer Profile doctype has been removed - use ERPNext Customer doctype instead")
    print("   To create test employers, use ERPNext Customer with customer_type='Company'")
    return 0

def create_test_employees():
    """Create test employees using ERPNext Employee doctype.

    NOTE: Employee Profile doctype has been removed. Using ERPNext Employee instead.
    """
    print("⚠️ Employee Profile doctype has been removed - use ERPNext Employee doctype instead")
    print("   To create test employees, use ERPNext Employee with custom_nrc_number field")
    return 0

def main():
    """Main function to create all test data.

    NOTE: Employer Profile, Employee Profile, and Beneficiary Profile doctypes have been removed.
    Use ERPNext Customer, Employee, and standard HR modules instead.
    """

    print("🚀 Creating WCFCB Live Test Data...")
    print("=" * 60)
    print("\n⚠️ DOCTYPE REMOVAL NOTICE:")
    print("   The following doctypes have been removed:")
    print("   - Employer Profile → Use ERPNext Customer (customer_type='Company')")
    print("   - Employee Profile → Use ERPNext Employee (with custom_nrc_number)")
    print("   - Beneficiary Profile → Managed externally")
    print("   - Assessment Record → Use Compliance Report")
    print("=" * 60)

    try:
        # Notify about removed doctype test data
        print("\n1. Employer Profiles (REMOVED)...")
        employer_count = create_test_employers()

        print("\n2. Employee Profiles (REMOVED)...")
        employee_count = create_test_employees()

        print("\n3. Beneficiary Profiles (REMOVED)...")
        beneficiary_count = create_test_beneficiaries()

        # Create test payments (still exists)
        print("\n4. Creating Test Payment Status Records...")
        payment_count = create_test_payment_status()
        print(f"Created {payment_count} payment status records")

        # Create test claims (still exists)
        print("\n5. Creating Test Claims Tracking Records...")
        claims_count = create_test_claims()
        print(f"Created {claims_count} claims tracking records")

        print("\n" + "=" * 60)
        print("🎉 WCFCB Live Test Data Creation Complete!")
        print(f"Total Records Created:")
        print(f"  • Payments: {payment_count}")
        print(f"  • Claims: {claims_count}")
        print("\n⚠️ To create test employers/employees, use ERPNext standard doctypes.")

    except Exception as e:
        print(f"❌ Error creating test data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
