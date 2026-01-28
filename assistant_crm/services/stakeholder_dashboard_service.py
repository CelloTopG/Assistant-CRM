# Copyright (c) 2024, WCFCB and contributors
# For license information, please see license.txt

import frappe
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json


class StakeholderDashboardService:
    """
    Service for creating unified 360-degree stakeholder views and 
    comprehensive dashboard analytics
    """
    
    def __init__(self):
        self.current_user = frappe.session.user
    
    # ==================== 360-DEGREE STAKEHOLDER VIEWS ====================
    
    def get_employer_360_view(self, employer_code: str) -> Dict[str, Any]:
        """Get comprehensive 360-degree view of an employer.

        NOTE: Employer Profile doctype has been removed - using ERPNext Customer.
        """
        try:
            # Get employer profile from ERPNext Customer (Employer Profile removed)
            employer = frappe.get_doc("Customer", employer_code)
            
            # Get related data
            employees = self._get_employer_employees(employer_code)
            assessments = self._get_employer_assessments(employer_code)
            certificates = self._get_employer_certificates(employer_code)
            compliance_history = self._get_employer_compliance_history(employer_code)
            communication_history = self._get_employer_communication_history(employer_code)
            
            # Calculate key metrics
            metrics = self._calculate_employer_metrics(employer_code)
            
            return {
                "success": True,
                "data": {
                    "profile": employer.as_dict(),
                    "employees": employees,
                    "assessments": assessments,
                    "certificates": certificates,
                    "compliance_history": compliance_history,
                    "communication_history": communication_history,
                    "metrics": metrics,
                    "last_updated": frappe.utils.now()
                }
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting employer 360 view for {employer_code}: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def get_employee_360_view(self, employee_number: str) -> Dict[str, Any]:
        """Get comprehensive 360-degree view of an employee.

        NOTE: Employee Profile doctype has been removed - using ERPNext Employee.
        """
        try:
            # Get employee profile from ERPNext Employee (Employee Profile removed)
            employee = frappe.get_doc("Employee", employee_number)
            
            # Get related data
            employer_info = self._get_employee_employer_info(employee.employer_code)
            contribution_history = self._get_employee_contribution_history(employee_number)
            benefit_claims = self._get_employee_benefit_claims(employee_number)
            certificates = self._get_employee_certificates(employee_number)
            beneficiaries = self._get_employee_beneficiaries(employee_number)
            communication_history = self._get_employee_communication_history(employee_number)
            
            # Calculate key metrics
            metrics = self._calculate_employee_metrics(employee_number)
            
            return {
                "success": True,
                "data": {
                    "profile": employee.as_dict(),
                    "employer_info": employer_info,
                    "contribution_history": contribution_history,
                    "benefit_claims": benefit_claims,
                    "certificates": certificates,
                    "beneficiaries": beneficiaries,
                    "communication_history": communication_history,
                    "metrics": metrics,
                    "last_updated": frappe.utils.now()
                }
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting employee 360 view for {employee_number}: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def get_beneficiary_360_view(self, beneficiary_number: str) -> Dict[str, Any]:
        """Get comprehensive 360-degree view of a beneficiary.

        NOTE: Beneficiary Profile doctype has been removed - beneficiary data managed externally.
        """
        # NOTE: Beneficiary Profile doctype has been removed
        return {
            "success": False,
            "message": "Beneficiary Profile doctype has been removed - beneficiary data is managed externally"
        }
    
    # ==================== UNIFIED DASHBOARD ====================
    
    def get_unified_dashboard(self) -> Dict[str, Any]:
        """Get unified dashboard with all stakeholder information"""
        try:
            dashboard_data = {
                "overview_metrics": self._get_overview_metrics(),
                "recent_activities": self._get_recent_activities(),
                "compliance_alerts": self._get_compliance_alerts(),
                "pending_actions": self._get_pending_actions(),
                "communication_summary": self._get_communication_summary(),
                "financial_summary": self._get_financial_summary(),
                "system_status": self._get_system_status()
            }
            
            return {"success": True, "data": dashboard_data}
            
        except Exception as e:
            frappe.log_error(f"Error getting unified dashboard: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def _get_overview_metrics(self) -> Dict[str, Any]:
        """Get high-level overview metrics.

        NOTE: Using ERPNext doctypes - Employer/Employee/Beneficiary Profile and Assessment Record removed.
        """
        return {
            # Using ERPNext Customer (replaces Employer Profile)
            "total_employers": frappe.db.count("Customer", {"customer_type": "Company"}),
            "active_employers": frappe.db.count("Customer", {"customer_type": "Company", "disabled": 0}),
            # Using ERPNext Employee (replaces Employee Profile)
            "total_employees": frappe.db.count("Employee"),
            "active_employees": frappe.db.count("Employee", {"status": "Active"}),
            # Beneficiary Profile removed - return 0
            "total_beneficiaries": 0,
            "active_beneficiaries": 0,
            # Using Compliance Report (replaces Assessment Record)
            "pending_assessments": frappe.db.count("Compliance Report", {"status": "Draft"}),
            "overdue_payments": frappe.db.count("Compliance Report", {"payment_status": "Overdue"}),
            "expiring_certificates": self._count_expiring_certificates()
        }
    
    def _get_recent_activities(self) -> List[Dict[str, Any]]:
        """Get recent activities across all stakeholder types.

        NOTE: Using ERPNext Customer and Employee (Employer/Employee Profile removed).
        """
        activities = []

        # Recent employer registrations - using ERPNext Customer
        recent_employers = frappe.get_all(
            "Customer",
            filters={"customer_type": "Company"},
            fields=["name", "customer_name", "creation"],
            order_by="creation desc",
            limit=5
        )

        for employer in recent_employers:
            activities.append({
                "type": "employer_registration",
                "title": f"New employer registered: {employer.customer_name}",
                "timestamp": employer.creation,
                "entity_id": employer.name
            })

        # Recent employee additions - using ERPNext Employee
        recent_employees = frappe.get_all(
            "Employee",
            fields=["name", "employee_name", "creation"],
            order_by="creation desc",
            limit=5
        )

        for employee in recent_employees:
            activities.append({
                "type": "employee_addition",
                "title": f"New employee added: {employee.employee_name}",
                "timestamp": employee.creation,
                "entity_id": employee.name
            })

        # Sort by timestamp
        activities.sort(key=lambda x: x["timestamp"], reverse=True)

        return activities[:10]
    
    def _get_compliance_alerts(self) -> List[Dict[str, Any]]:
        """Get compliance alerts and warnings.

        NOTE: Using Compliance Report (Assessment Record removed) and ERPNext Customer (Employer Profile removed).
        """
        alerts = []

        # Non-compliant employers - using Compliance Report instead of Employer Profile
        non_compliant_reports = frappe.get_all(
            "Compliance Report",
            filters={"status": "Non-Compliant"},
            fields=["name", "employer_code", "total_outstanding"]
        )

        for report in non_compliant_reports:
            employer_name = frappe.db.get_value("Customer", report.employer_code, "customer_name") or report.employer_code
            alerts.append({
                "type": "compliance_violation",
                "severity": "high",
                "title": f"Non-compliant employer: {employer_name}",
                "description": f"Outstanding contributions: ZMW {(report.total_outstanding or 0):,.2f}",
                "entity_id": report.employer_code
            })
        
        # Expiring certificates
        expiring_certificates = frappe.get_all(
            "Certificate Status",
            filters={
                "certificate_status": "Valid",
                "expiry_date": ["between", [frappe.utils.today(), frappe.utils.add_days(frappe.utils.today(), 30)]]
            },
            fields=["certificate_number", "certificate_type", "expiry_date", "employer_code"]
        )
        
        for cert in expiring_certificates:
            alerts.append({
                "type": "certificate_expiry",
                "severity": "medium",
                "title": f"Certificate expiring: {cert.certificate_type}",
                "description": f"Expires on {cert.expiry_date}",
                "entity_id": cert.certificate_number
            })
        
        return alerts
    
    def _get_pending_actions(self) -> List[Dict[str, Any]]:
        """Get pending actions requiring attention.

        NOTE: Using Compliance Report (replaces Assessment Record).
        """
        actions = []

        # Pending compliance reports - using Compliance Report instead of Assessment Record
        pending_reports = frappe.get_all(
            "Compliance Report",
            filters={"status": "Draft"},
            fields=["name", "employer_code", "reporting_period_end"],
            limit=10
        )

        for report in pending_reports:
            employer_name = frappe.db.get_value("Customer", report.employer_code, "customer_name") or report.employer_code
            actions.append({
                "type": "assessment_pending",
                "title": f"Complete compliance report for {employer_name}",
                "due_date": report.reporting_period_end,
                "entity_id": report.name
            })

        return actions
    
    def _get_communication_summary(self) -> Dict[str, Any]:
        """Get communication summary across all channels"""
        # This would integrate with the existing communication modules
        return {
            "total_conversations": 0,
            "active_conversations": 0,
            "pending_responses": 0,
            "channels": {
                "email": 0,
                "sms": 0,
                "whatsapp": 0,
                "facebook": 0,
                "phone": 0
            }
        }
    
    def _get_financial_summary(self) -> Dict[str, Any]:
        """Get financial summary.

        NOTE: Using Employer Contributions and Compliance Report (removed doctypes replaced).
        """
        # Get contributions from Employer Contributions doctype
        total_contributions = frappe.db.sql("""
            SELECT SUM(total_contributions) as total
            FROM `tabEmployer Contributions`
            WHERE docstatus = 1
        """)[0][0] or 0

        # Get outstanding from Compliance Report (replaces Employer Profile)
        outstanding_contributions = frappe.db.sql("""
            SELECT SUM(total_outstanding) as total
            FROM `tabCompliance Report`
            WHERE status = 'Non-Compliant'
        """)[0][0] or 0

        # Beneficiary Profile removed - benefits data not available locally
        total_benefits_paid = 0

        return {
            "total_contributions_collected": float(total_contributions),
            "outstanding_contributions": float(outstanding_contributions),
            "total_benefits_paid": float(total_benefits_paid),
            "collection_rate": 85.5,  # This would be calculated based on actual data
            "currency": "ZMW"
        }
    
    def _get_system_status(self) -> Dict[str, Any]:
        """Get system status information"""
        from assistant_crm.services.wcfcb_integration_service import WCFCBIntegrationService
        
        integration_service = WCFCBIntegrationService()
        sync_status = integration_service.get_sync_status_dashboard()
        
        return {
            "sync_status": sync_status.get("data", {}) if sync_status.get("success") else {},
            "last_updated": frappe.utils.now()
        }

    # ==================== HELPER METHODS ====================

    def _get_employer_employees(self, employer_code: str) -> List[Dict[str, Any]]:
        """Get all employees for an employer.

        NOTE: Using ERPNext Employee (Employee Profile removed).
        """
        return frappe.get_all(
            "Employee",
            filters={"company": employer_code},
            fields=["name", "employee_name", "status", "designation", "ctc"],
            order_by="date_of_joining desc"
        )

    def _get_employer_assessments(self, employer_code: str) -> List[Dict[str, Any]]:
        """Get all compliance reports for an employer.

        NOTE: Using Compliance Report (Assessment Record removed).
        """
        return frappe.get_all(
            "Compliance Report",
            filters={"employer_code": employer_code},
            fields=["name", "reporting_period_end", "report_type", "status", "total_contributions", "payment_status"],
            order_by="reporting_period_end desc"
        )

    def _get_employer_certificates(self, employer_code: str) -> List[Dict[str, Any]]:
        """Get all certificates for an employer"""
        return frappe.get_all(
            "Certificate Status",
            filters={"employer_code": employer_code},
            fields=["certificate_number", "certificate_type", "certificate_status", "issue_date", "expiry_date"],
            order_by="issue_date desc"
        )

    def _get_employer_compliance_history(self, employer_code: str) -> List[Dict[str, Any]]:
        """Get compliance history for an employer"""
        # This would track compliance status changes over time
        return []

    def _get_employer_communication_history(self, employer_code: str) -> List[Dict[str, Any]]:
        """Get communication history for an employer"""
        # This would integrate with the communication modules
        return []

    def _calculate_employer_metrics(self, employer_code: str) -> Dict[str, Any]:
        """Calculate key metrics for an employer.

        NOTE: Using ERPNext Customer and Compliance Report (Employer/Employee Profile removed).
        """
        employer = frappe.get_doc("Customer", employer_code)

        # Get compliance data from Compliance Report
        latest_report = frappe.get_all(
            "Compliance Report",
            filters={"employer_code": employer_code},
            fields=["status", "total_outstanding", "reporting_period_end"],
            order_by="reporting_period_end desc",
            limit=1
        )

        # Calculate compliance score
        compliance_score = 100
        outstanding = 0
        compliance_status = "Compliant"
        if latest_report:
            outstanding = latest_report[0].get("total_outstanding") or 0
            compliance_status = latest_report[0].get("status") or "Unknown"
            if outstanding > 0:
                compliance_score -= 30
            if compliance_status == "Non-Compliant":
                compliance_score -= 50

        # Calculate employee growth using ERPNext Employee
        current_employees = frappe.db.count("Employee", {"company": employer_code, "status": "Active"})
        last_month_employees = frappe.db.count("Employee", {
            "company": employer_code,
            "status": "Active",
            "date_of_joining": ["<", frappe.utils.add_months(frappe.utils.today(), -1)]
        })

        employee_growth = ((current_employees - last_month_employees) / max(1, last_month_employees)) * 100

        return {
            "compliance_score": max(0, compliance_score),
            "employee_count": current_employees,
            "employee_growth_rate": employee_growth,
            "outstanding_amount": float(outstanding),
            "last_assessment_date": latest_report[0].get("reporting_period_end") if latest_report else None,
            "next_due_date": None  # Would need to calculate based on reporting frequency
        }

    def _get_employee_employer_info(self, employer_code: str) -> Dict[str, Any]:
        """Get employer information for an employee.

        NOTE: Using ERPNext Customer (Employer Profile removed).
        """
        if employer_code:
            employer = frappe.get_doc("Customer", employer_code)
            # Get compliance status from latest report
            latest_report = frappe.get_all(
                "Compliance Report",
                filters={"employer_code": employer_code},
                fields=["status"],
                order_by="reporting_period_end desc",
                limit=1
            )
            compliance_status = latest_report[0].get("status") if latest_report else "Unknown"
            return {
                "employer_code": employer.name,
                "employer_name": employer.customer_name,
                "compliance_status": compliance_status,
                "industry_sector": employer.get("industry") or ""
            }
        return {}

    def _get_employee_contribution_history(self, employee_number: str) -> List[Dict[str, Any]]:
        """Get contribution history for an employee"""
        # This would come from a contribution records table
        return []

    def _get_employee_benefit_claims(self, employee_number: str) -> List[Dict[str, Any]]:
        """Get benefit claims for an employee"""
        # This would come from a benefit claims table
        return []

    def _get_employee_certificates(self, employee_number: str) -> List[Dict[str, Any]]:
        """Get certificates for an employee"""
        return frappe.get_all(
            "Certificate Status",
            filters={"employee_number": employee_number},
            fields=["certificate_number", "certificate_type", "certificate_status", "issue_date", "expiry_date"],
            order_by="issue_date desc"
        )

    def _get_employee_beneficiaries(self, employee_number: str) -> List[Dict[str, Any]]:
        """Get beneficiaries for an employee.

        NOTE: Beneficiary Profile doctype removed - returns empty list.
        """
        # NOTE: Beneficiary Profile doctype has been removed - beneficiary data managed externally
        _ = employee_number  # Unused
        return []

    def _get_employee_communication_history(self, employee_number: str) -> List[Dict[str, Any]]:
        """Get communication history for an employee"""
        # This would integrate with the communication modules
        _ = employee_number  # Unused
        return []

    def _calculate_employee_metrics(self, employee_number: str) -> Dict[str, Any]:
        """Calculate key metrics for an employee.

        NOTE: Using ERPNext Employee (Employee Profile removed).
        """
        employee = frappe.get_doc("Employee", employee_number)

        # Calculate years of service
        if employee.date_of_joining:
            years_of_service = (frappe.utils.getdate() - employee.date_of_joining).days / 365.25
        else:
            years_of_service = 0

        return {
            "years_of_service": round(years_of_service, 1),
            "monthly_contribution": 0,  # Would come from Employer Contributions
            "total_contributions": 0,  # Would need custom field or calculation
            "benefit_eligibility": employee.status,
            "employment_status": employee.status
        }

    def _get_beneficiary_employee_info(self, employee_number: str) -> Dict[str, Any]:
        """Get employee information for a beneficiary.

        NOTE: Using ERPNext Employee (Employee Profile removed).
        """
        if employee_number:
            try:
                employee = frappe.get_doc("Employee", employee_number)
                return {
                    "employee_number": employee.name,
                    "employee_name": employee.employee_name,
                    "employment_status": employee.status,
                    "total_contributions": 0  # Would need custom field or calculation
                }
            except frappe.DoesNotExistError:
                return {}
        return {}

    def _get_beneficiary_payment_history(self, beneficiary_number: str) -> List[Dict[str, Any]]:
        """Get payment history for a beneficiary.

        NOTE: Beneficiary Profile removed - returns empty list.
        """
        _ = beneficiary_number  # Unused
        return []

    def _get_beneficiary_benefit_calculations(self, beneficiary_number: str) -> Dict[str, Any]:
        """Get benefit calculations for a beneficiary.

        NOTE: Beneficiary Profile doctype removed.
        """
        _ = beneficiary_number  # Unused
        # NOTE: Beneficiary Profile doctype has been removed
        return {
            "monthly_benefit": 0,
            "annual_benefit": 0,
            "total_received": 0,
            "eligibility_status": "Unknown - doctype removed"
        }

    def _get_beneficiary_communication_history(self, beneficiary_number: str) -> List[Dict[str, Any]]:
        """Get communication history for a beneficiary"""
        # This would integrate with the communication modules
        _ = beneficiary_number  # Unused
        return []

    def _calculate_beneficiary_metrics(self, beneficiary_number: str) -> Dict[str, Any]:
        """Calculate key metrics for a beneficiary.

        NOTE: Beneficiary Profile doctype removed.
        """
        _ = beneficiary_number  # Unused
        # NOTE: Beneficiary Profile doctype has been removed
        return {
            "benefit_duration_years": 0,
            "monthly_benefit": 0,
            "total_received": 0,
            "benefit_status": "Unknown - doctype removed",
            "next_payment_due": None
        }

    def _count_expiring_certificates(self) -> int:
        """Count certificates expiring in the next 30 days"""
        return frappe.db.count(
            "Certificate Status",
            {
                "certificate_status": "Valid",
                "expiry_date": ["between", [frappe.utils.today(), frappe.utils.add_days(frappe.utils.today(), 30)]]
            }
        )
