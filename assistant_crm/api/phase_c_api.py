import frappe
from frappe import _
import json
from datetime import datetime


@frappe.whitelist(allow_guest=False)
def start_automation_engine():
    """
    Start the advanced automation engine
    
    Returns:
        Dict containing start result
    """
    try:
        from assistant_crm.services.advanced_automation_service import AdvancedAutomationService
        
        automation_service = AdvancedAutomationService()
        automation_service.start_automation_engine()
        
        return {
            "success": True,
            "message": "Advanced automation engine started successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        frappe.log_error(f"Error in start_automation_engine API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def stop_automation_engine():
    """
    Stop the advanced automation engine
    
    Returns:
        Dict containing stop result
    """
    try:
        from assistant_crm.services.advanced_automation_service import AdvancedAutomationService
        
        automation_service = AdvancedAutomationService()
        automation_service.stop_automation_engine()
        
        return {
            "success": True,
            "message": "Advanced automation engine stopped successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        frappe.log_error(f"Error in stop_automation_engine API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def intelligent_conversation_routing(conversation_id):
    """
    Apply intelligent routing to a conversation
    
    Args:
        conversation_id: Conversation identifier
        
    Returns:
        Dict containing routing result
    """
    try:
        from assistant_crm.services.advanced_automation_service import AdvancedAutomationService
        
        automation_service = AdvancedAutomationService()
        result = automation_service.intelligent_conversation_routing(conversation_id)
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error in intelligent_conversation_routing API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def auto_escalation_check(conversation_id):
    """
    Check if conversation should be escalated
    
    Args:
        conversation_id: Conversation identifier
        
    Returns:
        Dict containing escalation result
    """
    try:
        from assistant_crm.services.advanced_automation_service import AdvancedAutomationService
        
        automation_service = AdvancedAutomationService()
        result = automation_service.auto_escalation_system(conversation_id)
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error in auto_escalation_check API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def run_compliance_check():
    """
    Run comprehensive regulatory compliance check
    
    Returns:
        Dict containing compliance check results
    """
    try:
        from assistant_crm.services.regulatory_compliance_service import RegulatoryComplianceService
        
        compliance_service = RegulatoryComplianceService()
        result = compliance_service.run_comprehensive_compliance_check()
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error in run_compliance_check API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def get_compliance_dashboard():
    """
    Get regulatory compliance dashboard data
    
    Returns:
        Dict containing compliance dashboard data
    """
    try:
        from assistant_crm.services.regulatory_compliance_service import RegulatoryComplianceService
        
        compliance_service = RegulatoryComplianceService()
        
        # Get latest compliance report
        latest_report = frappe.get_all(
            "Compliance Report",
            fields=["*"],
            order_by="report_date desc",
            limit=1
        )
        
        if latest_report:
            report_data = latest_report[0]
            detailed_results = json.loads(report_data.get("detailed_results", "[]"))
            remediation_summary = json.loads(report_data.get("remediation_summary", "{}"))
            
            dashboard_data = {
                "overall_compliance_score": report_data.get("overall_compliance_score", 0),
                "total_rules_checked": report_data.get("total_rules_checked", 0),
                "compliant_rules": report_data.get("compliant_rules", 0),
                "non_compliant_rules": report_data.get("non_compliant_rules", 0),
                "critical_violations": report_data.get("critical_violations", 0),
                "high_violations": report_data.get("high_violations", 0),
                "report_date": report_data.get("report_date"),
                "next_check_due": report_data.get("next_check_due"),
                "detailed_results": detailed_results,
                "remediation_summary": remediation_summary
            }
        else:
            dashboard_data = {
                "overall_compliance_score": 0,
                "message": "No compliance reports available. Run compliance check first."
            }
        
        return {
            "success": True,
            "dashboard": dashboard_data
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_compliance_dashboard API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def get_automation_status():
    """
    Get current automation engine status and statistics
    
    Returns:
        Dict containing automation status
    """
    try:
        # Get automation execution logs from the last 24 hours
        yesterday = datetime.now() - timedelta(days=1)
        
        execution_logs = frappe.get_all(
            "Automation Execution Log",
            filters={"execution_timestamp": [">=", yesterday]},
            fields=["rule_id", "execution_status", "success_rate", "execution_timestamp"],
            order_by="execution_timestamp desc"
        )
        
        # Get automation rules statistics
        automation_rules = frappe.get_all(
            "Automation Rule",
            filters={"enabled": 1},
            fields=["name", "rule_name", "trigger_type", "execution_count", "success_rate", "last_executed"]
        )
        
        # Calculate statistics
        total_executions = len(execution_logs)
        successful_executions = len([log for log in execution_logs if log.execution_status == "completed"])
        failed_executions = len([log for log in execution_logs if log.execution_status == "failed"])
        
        success_rate = (successful_executions / max(1, total_executions)) * 100
        
        status_data = {
            "automation_engine_status": "running",  # This would be determined by checking the actual engine status
            "total_automation_rules": len(automation_rules),
            "active_rules": len([rule for rule in automation_rules if rule.last_executed]),
            "executions_last_24h": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "overall_success_rate": success_rate,
            "recent_executions": execution_logs[:10],  # Last 10 executions
            "automation_rules": automation_rules
        }
        
        return {
            "success": True,
            "status": status_data
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_automation_status API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def log_audit_event(category, action, details=None):
    """
    Log an audit event for compliance tracking
    
    Args:
        category: Audit category
        action: Action performed
        details: Optional additional details (JSON string)
        
    Returns:
        Dict containing logging result
    """
    try:
        from assistant_crm.services.regulatory_compliance_service import RegulatoryComplianceService
        
        compliance_service = RegulatoryComplianceService()
        
        # Parse details if provided as string
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except:
                details = {"raw_details": details}
        
        compliance_service.log_audit_event(
            category=category,
            action=action,
            details=details,
            user=frappe.session.user,
            ip_address=frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else None
        )
        
        return {
            "success": True,
            "message": "Audit event logged successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        frappe.log_error(f"Error in log_audit_event API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def get_phase_c_system_status():
    """
    Get comprehensive Phase C system status
    
    Returns:
        Dict containing Phase C system status
    """
    try:
        # Check automation service status
        try:
            from assistant_crm.services.advanced_automation_service import AdvancedAutomationService
            automation_service = AdvancedAutomationService()
            automation_status = "available"
        except Exception:
            automation_status = "unavailable"
        
        # Check compliance service status
        try:
            from assistant_crm.services.regulatory_compliance_service import RegulatoryComplianceService
            compliance_service = RegulatoryComplianceService()
            compliance_status = "available"
        except Exception:
            compliance_status = "unavailable"

        # Get recent system activity
        recent_activity = {
            "automation_executions": frappe.db.count("Automation Execution Log", {"creation": [">=", datetime.now() - timedelta(hours=24)]}),
            "compliance_checks": frappe.db.count("Compliance Report", {"report_date": [">=", datetime.now() - timedelta(days=7)]})
        }

        system_status = {
            "timestamp": datetime.now().isoformat(),
            "phase_c_components": {
                "advanced_automation": automation_status,
                "regulatory_compliance": compliance_status
            },
            "recent_activity": recent_activity,
            "overall_health": "healthy" if all(status == "available" for status in [automation_status, compliance_status]) else "degraded"
        }
        
        return {
            "success": True,
            "system_status": system_status
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_phase_c_system_status API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
