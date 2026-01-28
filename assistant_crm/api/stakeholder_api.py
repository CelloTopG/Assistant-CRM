# Copyright (c) 2024, WCFCB and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from typing import Dict, List, Any, Optional
import json

# NOTE: Employer Profile, Employee Profile, Beneficiary Profile, and Assessment Record
# doctypes have been removed. These data sources now come from ERPNext/Frappe core.
# The functions below have been stubbed out to return appropriate messages.


# ==================== EMPLOYER APIS ====================

@frappe.whitelist()
def get_employer_profile(employer_code: str) -> Dict[str, Any]:
    """Get comprehensive employer profile - Now uses ERPNext Customer doctype"""
    try:
        # Check ERPNext Customer doctype instead
        if not frappe.db.exists("Customer", {"customer_name": employer_code}):
            return {"success": False, "message": "Employer not found. Please use ERPNext Customer doctype."}

        customer = frappe.get_doc("Customer", {"customer_name": employer_code})
        return {
            "success": True,
            "message": "Employer data now sourced from ERPNext Customer doctype",
            "data": {"customer_name": customer.customer_name, "customer_type": customer.customer_type}
        }

    except Exception as e:
        frappe.log_error(f"Error getting employer profile {employer_code}: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def search_employers(query: str = "", filters: str = "{}") -> Dict[str, Any]:
    """Search employers - Now uses ERPNext Customer doctype"""
    try:
        filters_dict = json.loads(filters) if filters else {}

        # Search in ERPNext Customer doctype instead
        search_filters = {"customer_type": "Company"}
        if query:
            search_filters["customer_name"] = ["like", f"%{query}%"]

        customers = frappe.get_all(
            "Customer",
            filters=search_filters,
            fields=["name", "customer_name", "customer_type", "territory"],
            limit=100
        )

        return {
            "success": True,
            "data": customers,
            "count": len(customers),
            "message": "Data sourced from ERPNext Customer doctype"
        }

    except Exception as e:
        frappe.log_error(f"Error searching employers: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def update_employer_profile(employer_code: str, data: str) -> Dict[str, Any]:
    """Update employer profile - Now uses ERPNext Customer doctype"""
    try:
        if not frappe.db.exists("Customer", employer_code):
            return {"success": False, "message": "Employer not found. Please use ERPNext Customer doctype."}

        update_data = json.loads(data)
        customer_doc = frappe.get_doc("Customer", employer_code)

        # Update allowed fields that exist on Customer
        allowed_fields = ["customer_name", "territory"]

        for field in allowed_fields:
            if field in update_data:
                setattr(customer_doc, field, update_data[field])

        customer_doc.save()

        return {"success": True, "message": "Employer profile updated via ERPNext Customer doctype"}

    except Exception as e:
        frappe.log_error(f"Error updating employer profile {employer_code}: {str(e)}")
        return {"success": False, "message": str(e)}


# ==================== EMPLOYEE APIS ====================

@frappe.whitelist()
def get_employee_profile(employee_number: str) -> Dict[str, Any]:
    """Get comprehensive employee profile - Now uses ERPNext Employee doctype"""
    try:
        if not frappe.db.exists("Employee", employee_number):
            return {"success": False, "message": "Employee not found. Please use ERPNext Employee doctype."}

        employee = frappe.get_doc("Employee", employee_number)
        return {
            "success": True,
            "message": "Employee data now sourced from ERPNext Employee doctype",
            "data": {"employee_name": employee.employee_name, "status": employee.status}
        }

    except Exception as e:
        frappe.log_error(f"Error getting employee profile {employee_number}: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def search_employees(query: str = "", filters: str = "{}") -> Dict[str, Any]:
    """Search employees - Now uses ERPNext Employee doctype"""
    try:
        filters_dict = json.loads(filters) if filters else {}

        # Search in ERPNext Employee doctype instead
        search_filters = {}
        if query:
            search_filters["employee_name"] = ["like", f"%{query}%"]

        employees = frappe.get_all(
            "Employee",
            filters=search_filters,
            fields=["name", "employee_name", "status", "company", "department"],
            limit=100
        )

        return {
            "success": True,
            "data": employees,
            "count": len(employees),
            "message": "Data sourced from ERPNext Employee doctype"
        }

    except Exception as e:
        frappe.log_error(f"Error searching employees: {str(e)}")
        return {"success": False, "message": str(e)}


# ==================== BENEFICIARY APIS ====================
# NOTE: Beneficiary Profile doctype has been removed.
# Beneficiary data now comes from ERPNext/Frappe core.

@frappe.whitelist()
def get_beneficiary_profile(beneficiary_number: str) -> Dict[str, Any]:
    """Get comprehensive beneficiary profile - Doctype removed"""
    return {
        "success": False,
        "message": "Beneficiary Profile doctype has been removed. Beneficiary data is now sourced from ERPNext/Frappe."
    }


@frappe.whitelist()
def search_beneficiaries(query: str = "", filters: str = "{}") -> Dict[str, Any]:
    """Search beneficiaries - Doctype removed"""
    return {
        "success": False,
        "message": "Beneficiary Profile doctype has been removed. Beneficiary data is now sourced from ERPNext/Frappe.",
        "data": [],
        "count": 0
    }


# ==================== UNIFIED SEARCH API ====================

@frappe.whitelist()
def unified_search(query: str, entity_types: str = "all") -> Dict[str, Any]:
    """Unified search across all stakeholder types"""
    try:
        entity_types_list = json.loads(entity_types) if entity_types != "all" else ["employers", "employees", "beneficiaries"]
        
        results = {
            "employers": [],
            "employees": [],
            "beneficiaries": [],
            "total_count": 0
        }
        
        if "employers" in entity_types_list:
            employer_result = search_employers(query)
            if employer_result.get("success"):
                results["employers"] = employer_result.get("data", [])
        
        if "employees" in entity_types_list:
            employee_result = search_employees(query)
            if employee_result.get("success"):
                results["employees"] = employee_result.get("data", [])
        
        if "beneficiaries" in entity_types_list:
            beneficiary_result = search_beneficiaries(query)
            if beneficiary_result.get("success"):
                results["beneficiaries"] = beneficiary_result.get("data", [])
        
        results["total_count"] = len(results["employers"]) + len(results["employees"]) + len(results["beneficiaries"])
        
        return {"success": True, "data": results}
        
    except Exception as e:
        frappe.log_error(f"Error in unified search: {str(e)}")
        return {"success": False, "message": str(e)}


# ==================== DASHBOARD APIS ====================

@frappe.whitelist()
def get_unified_dashboard() -> Dict[str, Any]:
    """Get unified stakeholder dashboard - Uses ERPNext doctypes"""
    try:
        # Get counts from ERPNext doctypes
        employer_count = frappe.db.count("Customer", {"customer_type": "Company"})
        employee_count = frappe.db.count("Employee")

        return {
            "success": True,
            "data": {
                "employer_count": employer_count,
                "employee_count": employee_count,
                "message": "Dashboard data sourced from ERPNext Customer and Employee doctypes"
            }
        }

    except Exception as e:
        frappe.log_error(f"Error getting unified dashboard: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_compliance_dashboard() -> Dict[str, Any]:
    """Get compliance-focused dashboard - Uses Compliance Report doctype"""
    try:
        # Get compliance reports instead
        compliance_reports = frappe.get_all(
            "Compliance Report",
            filters={},
            fields=["name", "report_date", "compliance_status", "total_employers", "compliant_count"],
            order_by="report_date desc",
            limit=10
        )

        # Expiring certificates
        expiring_certificates = frappe.get_all(
            "Certificate Status",
            filters={
                "certificate_status": "Valid",
                "expiry_date": ["between", [frappe.utils.today(), frappe.utils.add_days(frappe.utils.today(), 30)]]
            },
            fields=["certificate_number", "certificate_type", "employer_name", "expiry_date"],
            order_by="expiry_date"
        )

        # Use ERPNext Customer for employer counts
        total_employers = frappe.db.count("Customer", {"customer_type": "Company"})

        return {
            "success": True,
            "data": {
                "compliance_metrics": {
                    "total_employers": total_employers,
                    "message": "Detailed compliance data now sourced from Compliance Report doctype"
                },
                "compliance_reports": compliance_reports,
                "expiring_certificates": expiring_certificates
            }
        }

    except Exception as e:
        frappe.log_error(f"Error getting compliance dashboard: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_financial_dashboard() -> Dict[str, Any]:
    """Get financial dashboard - Uses Employer Contributions doctype"""
    try:
        # Use Employer Contributions doctype instead
        contributions = frappe.get_all(
            "Employer Contributions",
            filters={"status": "Paid"},
            fields=["contribution_amount", "outstanding_amount"],
            limit=1000
        )

        total_contributions = sum(c.get("contribution_amount", 0) or 0 for c in contributions)
        outstanding_contributions = sum(c.get("outstanding_amount", 0) or 0 for c in contributions)

        # Get recent contribution trends from Employer Contributions
        monthly_trends = frappe.db.sql("""
            SELECT
                DATE_FORMAT(creation, '%Y-%m') as month,
                COUNT(*) as contribution_records,
                SUM(contribution_amount) as total_contributions
            FROM `tabEmployer Contributions`
            WHERE creation >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(creation, '%Y-%m')
            ORDER BY month
        """, as_dict=True)

        return {
            "success": True,
            "data": {
                "summary": {
                    "total_contributions_collected": float(total_contributions),
                    "outstanding_contributions": float(outstanding_contributions),
                    "message": "Financial data sourced from Employer Contributions doctype"
                },
                "monthly_trends": monthly_trends
            }
        }

    except Exception as e:
        frappe.log_error(f"Error getting financial dashboard: {str(e)}")
        return {"success": False, "message": str(e)}


# ==================== SYNC APIS ====================

@frappe.whitelist()
def trigger_sync(entity_type: str = "all", entity_id: str = "") -> Dict[str, Any]:
    """Trigger manual sync with CoreBusiness system"""
    try:
        from assistant_crm.services.wcfcb_integration_service import WCFCBIntegrationService
        integration_service = WCFCBIntegrationService()

        if entity_id:
            # Sync specific entity
            if entity_type == "employer":
                result = integration_service.sync_employer_from_corebusiness(entity_id)
            elif entity_type == "employee":
                result = integration_service.sync_employee_from_corebusiness(entity_id)
            else:
                return {"success": False, "message": "Invalid entity type"}
        else:
            # Bulk sync
            result = integration_service.bulk_sync_from_corebusiness(entity_type)

        return result

    except Exception as e:
        frappe.log_error(f"Error triggering sync: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_sync_status() -> Dict[str, Any]:
    """Get current sync status"""
    try:
        from assistant_crm.services.wcfcb_integration_service import WCFCBIntegrationService
        integration_service = WCFCBIntegrationService()

        result = integration_service.get_sync_status_dashboard()
        return result

    except Exception as e:
        frappe.log_error(f"Error getting sync status: {str(e)}")
        return {"success": False, "message": str(e)}


# ==================== ANALYTICS APIS ====================

@frappe.whitelist()
def get_stakeholder_analytics(date_range: str = "30") -> Dict[str, Any]:
    """Get comprehensive stakeholder analytics - Uses ERPNext doctypes"""
    try:
        days = int(date_range)
        start_date = frappe.utils.add_days(frappe.utils.today(), -days)

        # New registrations trend from ERPNext Customer (employers)
        new_employers = frappe.db.sql("""
            SELECT DATE(creation) as date, COUNT(*) as count
            FROM `tabCustomer`
            WHERE creation >= %s AND customer_type = 'Company'
            GROUP BY DATE(creation)
            ORDER BY date
        """, [start_date], as_dict=True)

        # New employees from ERPNext Employee
        new_employees = frappe.db.sql("""
            SELECT DATE(creation) as date, COUNT(*) as count
            FROM `tabEmployee`
            WHERE creation >= %s
            GROUP BY DATE(creation)
            ORDER BY date
        """, [start_date], as_dict=True)

        # Geographic distribution from ERPNext Customer
        employer_distribution = frappe.db.sql("""
            SELECT territory as province, COUNT(*) as count
            FROM `tabCustomer`
            WHERE territory IS NOT NULL AND territory != '' AND customer_type = 'Company'
            GROUP BY territory
            ORDER BY count DESC
        """, as_dict=True)

        return {
            "success": True,
            "data": {
                "registration_trends": {
                    "employers": new_employers,
                    "employees": new_employees
                },
                "geographic_distribution": {
                    "employers": employer_distribution
                },
                "date_range": f"{start_date} to {frappe.utils.today()}",
                "message": "Analytics data sourced from ERPNext Customer and Employee doctypes"
            }
        }

    except Exception as e:
        frappe.log_error(f"Error getting stakeholder analytics: {str(e)}")
        return {"success": False, "message": str(e)}
