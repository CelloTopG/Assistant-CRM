import frappe
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import hmac
from dataclasses import dataclass
from enum import Enum


class ComplianceStandard(Enum):
    GDPR = "gdpr"
    ZAMBIAN_DATA_PROTECTION = "zambian_data_protection"
    WCFCB_INTERNAL = "wcfcb_internal"
    ISO_27001 = "iso_27001"
    ACCESSIBILITY_WCAG = "accessibility_wcag"
    AUDIT_REQUIREMENTS = "audit_requirements"


class ComplianceLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


@dataclass
class ComplianceRule:
    id: str
    name: str
    description: str
    standard: ComplianceStandard
    level: ComplianceLevel
    check_function: str
    remediation_actions: List[str]
    enabled: bool
    last_checked: Optional[datetime] = None
    compliance_status: bool = False
    findings: List[str] = None


class RegulatoryComplianceService:
    """
    Regulatory Compliance Service for WCFCB Assistant CRM
    Phase C: Comprehensive compliance monitoring and enforcement
    Compliance Target: 99/100 score
    """
    
    def __init__(self):
        self.config = self.get_compliance_configuration()
        self.compliance_rules = self.load_compliance_rules()
        self.audit_logger = self.initialize_audit_logger()
        
    def get_compliance_configuration(self) -> Dict[str, Any]:
        """Get regulatory compliance configuration"""
        try:
            settings = frappe.get_single("Regulatory Compliance Settings")
            return {
                "enabled": settings.get("enabled", 1),
                "gdpr_compliance_enabled": settings.get("gdpr_compliance_enabled", 1),
                "data_protection_enabled": settings.get("data_protection_enabled", 1),
                "audit_logging_enabled": settings.get("audit_logging_enabled", 1),
                "accessibility_compliance_enabled": settings.get("accessibility_compliance_enabled", 1),
                "security_compliance_enabled": settings.get("security_compliance_enabled", 1),
                "automated_remediation_enabled": settings.get("automated_remediation_enabled", 1),
                "compliance_reporting_enabled": settings.get("compliance_reporting_enabled", 1),
                "real_time_monitoring_enabled": settings.get("real_time_monitoring_enabled", 1),
                "data_retention_days": settings.get("data_retention_days", 2555),  # 7 years
                "audit_retention_days": settings.get("audit_retention_days", 3650),  # 10 years
                "compliance_check_interval_hours": settings.get("compliance_check_interval_hours", 24)
            }
        except Exception:
            return {
                "enabled": 1,
                "gdpr_compliance_enabled": 1,
                "data_protection_enabled": 1,
                "audit_logging_enabled": 1,
                "accessibility_compliance_enabled": 1,
                "security_compliance_enabled": 1,
                "automated_remediation_enabled": 1,
                "compliance_reporting_enabled": 1,
                "real_time_monitoring_enabled": 1,
                "data_retention_days": 2555,
                "audit_retention_days": 3650,
                "compliance_check_interval_hours": 24
            }
    
    def load_compliance_rules(self) -> List[ComplianceRule]:
        """Load compliance rules from configuration"""
        rules = [
            # GDPR Compliance Rules
            ComplianceRule(
                id="gdpr_data_retention",
                name="GDPR Data Retention Compliance",
                description="Ensure personal data is not retained beyond necessary period",
                standard=ComplianceStandard.GDPR,
                level=ComplianceLevel.CRITICAL,
                check_function="check_gdpr_data_retention",
                remediation_actions=["archive_old_data", "anonymize_personal_data"],
                enabled=self.config["gdpr_compliance_enabled"]
            ),
            ComplianceRule(
                id="gdpr_consent_tracking",
                name="GDPR Consent Tracking",
                description="Verify consent is properly tracked and documented",
                standard=ComplianceStandard.GDPR,
                level=ComplianceLevel.HIGH,
                check_function="check_gdpr_consent_tracking",
                remediation_actions=["update_consent_records", "request_new_consent"],
                enabled=self.config["gdpr_compliance_enabled"]
            ),
            
            # Zambian Data Protection Rules
            ComplianceRule(
                id="zambian_data_localization",
                name="Zambian Data Localization",
                description="Ensure sensitive data is stored within Zambian jurisdiction",
                standard=ComplianceStandard.ZAMBIAN_DATA_PROTECTION,
                level=ComplianceLevel.CRITICAL,
                check_function="check_data_localization",
                remediation_actions=["migrate_data_to_local_servers"],
                enabled=self.config["data_protection_enabled"]
            ),
            
            # WCFCB Internal Compliance Rules
            ComplianceRule(
                id="wcfcb_response_time",
                name="WCFCB Response Time Compliance",
                description="Ensure customer inquiries are responded to within SLA",
                standard=ComplianceStandard.WCFCB_INTERNAL,
                level=ComplianceLevel.HIGH,
                check_function="check_response_time_sla",
                remediation_actions=["escalate_overdue_conversations", "assign_additional_agents"],
                enabled=True
            ),
            
            # Security Compliance Rules
            ComplianceRule(
                id="iso27001_access_control",
                name="ISO 27001 Access Control",
                description="Verify proper access controls are in place",
                standard=ComplianceStandard.ISO_27001,
                level=ComplianceLevel.HIGH,
                check_function="check_access_controls",
                remediation_actions=["review_user_permissions", "update_access_policies"],
                enabled=self.config["security_compliance_enabled"]
            ),
            
            # Accessibility Compliance Rules
            ComplianceRule(
                id="wcag_accessibility",
                name="WCAG 2.1 AA Accessibility",
                description="Ensure system meets accessibility standards",
                standard=ComplianceStandard.ACCESSIBILITY_WCAG,
                level=ComplianceLevel.MEDIUM,
                check_function="check_accessibility_compliance",
                remediation_actions=["fix_accessibility_issues", "update_ui_components"],
                enabled=self.config["accessibility_compliance_enabled"]
            ),
            
            # Audit Requirements
            ComplianceRule(
                id="audit_trail_completeness",
                name="Audit Trail Completeness",
                description="Verify all required actions are logged in audit trail",
                standard=ComplianceStandard.AUDIT_REQUIREMENTS,
                level=ComplianceLevel.CRITICAL,
                check_function="check_audit_trail_completeness",
                remediation_actions=["enable_missing_audit_logs", "repair_audit_gaps"],
                enabled=self.config["audit_logging_enabled"]
            )
        ]
        
        return [rule for rule in rules if rule.enabled]
    
    def initialize_audit_logger(self):
        """Initialize comprehensive audit logging system"""
        return {
            "enabled": self.config["audit_logging_enabled"],
            "retention_days": self.config["audit_retention_days"],
            "log_levels": ["INFO", "WARNING", "ERROR", "CRITICAL"],
            "audit_categories": [
                "user_access", "data_access", "data_modification", 
                "system_configuration", "compliance_check", "security_event"
            ]
        }
    
    def run_comprehensive_compliance_check(self) -> Dict[str, Any]:
        """Run comprehensive compliance check across all standards"""
        try:
            if not self.config["enabled"]:
                return {"success": False, "error": "Regulatory compliance monitoring disabled"}
            
            compliance_results = []
            overall_score = 0
            critical_violations = 0
            high_violations = 0
            
            for rule in self.compliance_rules:
                try:
                    # Execute compliance check
                    check_result = self.execute_compliance_check(rule)
                    
                    # Update rule status
                    rule.last_checked = datetime.now()
                    rule.compliance_status = check_result["compliant"]
                    rule.findings = check_result.get("findings", [])
                    
                    # Add to results
                    compliance_results.append({
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "standard": rule.standard.value,
                        "level": rule.level.value,
                        "compliant": check_result["compliant"],
                        "score": check_result.get("score", 0),
                        "findings": check_result.get("findings", []),
                        "remediation_required": not check_result["compliant"],
                        "remediation_actions": rule.remediation_actions if not check_result["compliant"] else []
                    })
                    
                    # Update overall metrics
                    overall_score += check_result.get("score", 0)
                    
                    if not check_result["compliant"]:
                        if rule.level == ComplianceLevel.CRITICAL:
                            critical_violations += 1
                        elif rule.level == ComplianceLevel.HIGH:
                            high_violations += 1
                    
                except Exception as e:
                    frappe.log_error(f"Error checking compliance rule {rule.id}: {str(e)}")
                    compliance_results.append({
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "standard": rule.standard.value,
                        "level": rule.level.value,
                        "compliant": False,
                        "error": str(e),
                        "remediation_required": True
                    })
            
            # Calculate overall compliance score
            total_rules = len(self.compliance_rules)
            overall_compliance_score = (overall_score / max(1, total_rules * 100)) * 100
            
            # Generate compliance report
            compliance_report = {
                "timestamp": datetime.now().isoformat(),
                "overall_compliance_score": overall_compliance_score,
                "total_rules_checked": total_rules,
                "compliant_rules": sum(1 for result in compliance_results if result.get("compliant")),
                "non_compliant_rules": sum(1 for result in compliance_results if not result.get("compliant")),
                "critical_violations": critical_violations,
                "high_violations": high_violations,
                "detailed_results": compliance_results,
                "remediation_summary": self.generate_remediation_summary(compliance_results),
                "next_check_due": (datetime.now() + timedelta(hours=self.config["compliance_check_interval_hours"])).isoformat()
            }
            
            # Store compliance report
            self.store_compliance_report(compliance_report)
            
            # Execute automated remediation if enabled
            if self.config["automated_remediation_enabled"]:
                remediation_results = self.execute_automated_remediation(compliance_results)
                compliance_report["automated_remediation"] = remediation_results
            
            # Send alerts for critical violations
            if critical_violations > 0:
                self.send_critical_compliance_alerts(compliance_results)
            
            # Log compliance check completion
            self.log_audit_event(
                category="compliance_check",
                action="comprehensive_compliance_check_completed",
                details={
                    "overall_score": overall_compliance_score,
                    "critical_violations": critical_violations,
                    "high_violations": high_violations
                }
            )
            
            return {
                "success": True,
                "compliance_score": overall_compliance_score,
                "critical_violations": critical_violations,
                "high_violations": high_violations,
                "report": compliance_report
            }
            
        except Exception as e:
            frappe.log_error(f"Error in comprehensive compliance check: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_compliance_check(self, rule: ComplianceRule) -> Dict[str, Any]:
        """Execute a specific compliance check"""
        try:
            # Get the check function
            check_function = getattr(self, rule.check_function, None)
            
            if not check_function:
                return {
                    "compliant": False,
                    "score": 0,
                    "findings": [f"Check function {rule.check_function} not implemented"],
                    "error": f"Check function {rule.check_function} not found"
                }
            
            # Execute the check
            result = check_function()
            
            # Ensure result has required fields
            if not isinstance(result, dict):
                result = {"compliant": False, "score": 0, "findings": ["Invalid check result"]}
            
            result.setdefault("compliant", False)
            result.setdefault("score", 0)
            result.setdefault("findings", [])
            
            return result
            
        except Exception as e:
            return {
                "compliant": False,
                "score": 0,
                "findings": [f"Error executing compliance check: {str(e)}"],
                "error": str(e)
            }
    
    def check_gdpr_data_retention(self) -> Dict[str, Any]:
        """Check GDPR data retention compliance"""
        try:
            findings = []
            score = 100
            
            # Check for data older than retention period
            retention_cutoff = datetime.now() - timedelta(days=self.config["data_retention_days"])
            
            old_conversations = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabOmnichannel Conversation`
                WHERE start_time < %s AND conversation_status = 'Closed'
            """, (retention_cutoff,), as_dict=True)[0]["count"]
            
            if old_conversations > 0:
                findings.append(f"{old_conversations} conversations exceed data retention period")
                score -= 20
            
            # Check for personal data without consent
            conversations_without_consent = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabOmnichannel Conversation`
                WHERE (consent_status IS NULL OR consent_status = '') 
                AND customer_name IS NOT NULL
            """, as_dict=True)[0]["count"]
            
            if conversations_without_consent > 0:
                findings.append(f"{conversations_without_consent} conversations lack proper consent documentation")
                score -= 30
            
            return {
                "compliant": score >= 80,
                "score": max(0, score),
                "findings": findings
            }
            
        except Exception as e:
            return {
                "compliant": False,
                "score": 0,
                "findings": [f"Error checking GDPR data retention: {str(e)}"]
            }

    def check_response_time_sla(self) -> Dict[str, Any]:
        """Check WCFCB response time SLA compliance"""
        try:
            findings = []
            score = 100

            # Check conversations with delayed first response (>2 hours)
            two_hours_ago = datetime.now() - timedelta(hours=2)

            delayed_responses = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabOmnichannel Conversation` oc
                LEFT JOIN `tabOmnichannel Message` om ON oc.name = om.conversation_id
                    AND om.is_inbound = 0
                WHERE oc.start_time < %s
                AND oc.conversation_status = 'Open'
                AND om.name IS NULL
            """, (two_hours_ago,), as_dict=True)[0]["count"]

            if delayed_responses > 0:
                findings.append(f"{delayed_responses} conversations exceed 2-hour response SLA")
                score -= 40

            # Check conversations open for more than 24 hours
            twenty_four_hours_ago = datetime.now() - timedelta(hours=24)

            overdue_conversations = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabOmnichannel Conversation`
                WHERE start_time < %s AND conversation_status = 'Open'
            """, (twenty_four_hours_ago,), as_dict=True)[0]["count"]

            if overdue_conversations > 0:
                findings.append(f"{overdue_conversations} conversations open for more than 24 hours")
                score -= 30

            return {
                "compliant": score >= 80,
                "score": max(0, score),
                "findings": findings
            }

        except Exception as e:
            return {
                "compliant": False,
                "score": 0,
                "findings": [f"Error checking response time SLA: {str(e)}"]
            }

    def check_audit_trail_completeness(self) -> Dict[str, Any]:
        """Check audit trail completeness"""
        try:
            findings = []
            score = 100

            # Check for missing audit logs in the last 24 hours
            yesterday = datetime.now() - timedelta(days=1)

            # Check if all user logins are logged
            user_sessions = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabSessions`
                WHERE creation >= %s
            """, (yesterday,), as_dict=True)[0]["count"]

            audit_login_logs = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabAudit Log`
                WHERE creation >= %s AND action_type = 'user_login'
            """, (yesterday,), as_dict=True)

            if audit_login_logs and user_sessions > audit_login_logs[0]["count"]:
                findings.append("Missing audit logs for user login events")
                score -= 25

            # Check for data modification logs
            recent_conversations = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabOmnichannel Conversation`
                WHERE modified >= %s
            """, (yesterday,), as_dict=True)[0]["count"]

            if recent_conversations > 0:
                audit_modification_logs = frappe.db.sql("""
                    SELECT COUNT(*) as count
                    FROM `tabAudit Log`
                    WHERE creation >= %s AND action_type = 'data_modification'
                """, (yesterday,), as_dict=True)

                if not audit_modification_logs or audit_modification_logs[0]["count"] == 0:
                    findings.append("Missing audit logs for data modification events")
                    score -= 30

            return {
                "compliant": score >= 80,
                "score": max(0, score),
                "findings": findings
            }

        except Exception as e:
            return {
                "compliant": False,
                "score": 0,
                "findings": [f"Error checking audit trail completeness: {str(e)}"]
            }

    def check_data_localization(self) -> Dict[str, Any]:
        """Check Zambian data localization compliance"""
        try:
            findings = []
            score = 100

            # This would typically check server locations, database locations, etc.
            # For this implementation, we'll check configuration settings

            # Check if data backup locations are configured for Zambia
            backup_settings = frappe.get_single("System Settings")
            backup_location = getattr(backup_settings, 'backup_location', '')

            if not backup_location or 'zambia' not in backup_location.lower():
                findings.append("Backup location not configured for Zambian jurisdiction")
                score -= 50

            # Check for any external integrations that might store data outside Zambia
            external_integrations = frappe.get_all("Integration Request",
                                                 filters={"status": "Completed"},
                                                 limit=10)

            if len(external_integrations) > 0:
                findings.append("External integrations detected - verify data localization compliance")
                score -= 20

            return {
                "compliant": score >= 80,
                "score": max(0, score),
                "findings": findings
            }

        except Exception as e:
            return {
                "compliant": False,
                "score": 0,
                "findings": [f"Error checking data localization: {str(e)}"]
            }

    def check_access_controls(self) -> Dict[str, Any]:
        """Check ISO 27001 access control compliance"""
        try:
            findings = []
            score = 100

            # Check for users without proper role assignments
            users_without_roles = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabUser` u
                LEFT JOIN `tabHas Role` hr ON u.name = hr.parent
                WHERE u.enabled = 1 AND u.user_type = 'System User'
                AND hr.role IS NULL
            """, as_dict=True)[0]["count"]

            if users_without_roles > 0:
                findings.append(f"{users_without_roles} users without proper role assignments")
                score -= 30

            # Check for inactive users that are still enabled
            ninety_days_ago = datetime.now() - timedelta(days=90)

            inactive_users = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabUser`
                WHERE enabled = 1 AND user_type = 'System User'
                AND (last_login IS NULL OR last_login < %s)
            """, (ninety_days_ago,), as_dict=True)[0]["count"]

            if inactive_users > 0:
                findings.append(f"{inactive_users} inactive users still have system access")
                score -= 25

            # Check for shared accounts (users with generic names)
            generic_accounts = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabUser`
                WHERE enabled = 1 AND user_type = 'System User'
                AND (email LIKE '%admin%' OR email LIKE '%shared%' OR email LIKE '%generic%')
            """, as_dict=True)[0]["count"]

            if generic_accounts > 0:
                findings.append(f"{generic_accounts} potentially shared/generic accounts detected")
                score -= 20

            return {
                "compliant": score >= 80,
                "score": max(0, score),
                "findings": findings
            }

        except Exception as e:
            return {
                "compliant": False,
                "score": 0,
                "findings": [f"Error checking access controls: {str(e)}"]
            }

    def check_accessibility_compliance(self) -> Dict[str, Any]:
        """Check WCAG 2.1 AA accessibility compliance"""
        try:
            findings = []
            score = 100

            # This would typically involve automated accessibility testing
            # For this implementation, we'll check basic configuration

            # Check if accessibility features are enabled
            system_settings = frappe.get_single("System Settings")

            # Check for alt text requirements
            if not getattr(system_settings, 'require_alt_text', False):
                findings.append("Alt text requirements not enforced")
                score -= 20

            # Check for keyboard navigation support
            if not getattr(system_settings, 'keyboard_navigation_enabled', False):
                findings.append("Keyboard navigation support not enabled")
                score -= 25

            # Check for high contrast mode availability
            if not getattr(system_settings, 'high_contrast_mode', False):
                findings.append("High contrast mode not available")
                score -= 15

            return {
                "compliant": score >= 80,
                "score": max(0, score),
                "findings": findings
            }

        except Exception as e:
            return {
                "compliant": False,
                "score": 0,
                "findings": [f"Error checking accessibility compliance: {str(e)}"]
            }

    def check_gdpr_consent_tracking(self) -> Dict[str, Any]:
        """Check GDPR consent tracking compliance"""
        try:
            findings = []
            score = 100

            # Check for customers without consent records
            customers_without_consent = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabCustomer` c
                LEFT JOIN `tabConsent Record` cr ON c.name = cr.customer
                WHERE cr.name IS NULL
            """, as_dict=True)

            if customers_without_consent and customers_without_consent[0]["count"] > 0:
                findings.append(f"{customers_without_consent[0]['count']} customers without consent records")
                score -= 40

            # Check for expired consents
            expired_consents = frappe.db.sql("""
                SELECT COUNT(*) as count
                FROM `tabConsent Record`
                WHERE consent_expiry < %s AND consent_status = 'Active'
            """, (datetime.now(),), as_dict=True)

            if expired_consents and expired_consents[0]["count"] > 0:
                findings.append(f"{expired_consents[0]['count']} expired consents still marked as active")
                score -= 30

            return {
                "compliant": score >= 80,
                "score": max(0, score),
                "findings": findings
            }

        except Exception as e:
            return {
                "compliant": False,
                "score": 0,
                "findings": [f"Error checking GDPR consent tracking: {str(e)}"]
            }

    def log_audit_event(self, category: str, action: str, details: Dict[str, Any] = None,
                       user: str = None, ip_address: str = None):
        """Log audit event for compliance tracking"""
        try:
            if not self.config["audit_logging_enabled"]:
                return

            audit_log = frappe.get_doc({
                "doctype": "Audit Log",
                "category": category,
                "action_type": action,
                "user": user or frappe.session.user,
                "ip_address": ip_address or frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else None,
                "timestamp": datetime.now(),
                "details": json.dumps(details) if details else None,
                "compliance_relevant": 1
            })
            audit_log.insert()
            frappe.db.commit()

        except Exception as e:
            frappe.log_error(f"Error logging audit event: {str(e)}")

    def store_compliance_report(self, report: Dict[str, Any]):
        """Store compliance report for historical tracking"""
        try:
            compliance_report = frappe.get_doc({
                "doctype": "Compliance Report",
                "report_date": datetime.now(),
                "overall_compliance_score": report["overall_compliance_score"],
                "total_rules_checked": report["total_rules_checked"],
                "compliant_rules": report["compliant_rules"],
                "non_compliant_rules": report["non_compliant_rules"],
                "critical_violations": report["critical_violations"],
                "high_violations": report["high_violations"],
                "detailed_results": json.dumps(report["detailed_results"]),
                "remediation_summary": json.dumps(report["remediation_summary"]),
                "next_check_due": report["next_check_due"]
            })
            compliance_report.insert()
            frappe.db.commit()

        except Exception as e:
            frappe.log_error(f"Error storing compliance report: {str(e)}")

    def generate_remediation_summary(self, compliance_results: List[Dict]) -> Dict[str, Any]:
        """Generate summary of required remediation actions"""
        try:
            remediation_actions = {}
            priority_actions = []

            for result in compliance_results:
                if not result.get("compliant") and result.get("remediation_actions"):
                    for action in result["remediation_actions"]:
                        if action not in remediation_actions:
                            remediation_actions[action] = {
                                "action": action,
                                "affected_rules": [],
                                "priority": "medium"
                            }

                        remediation_actions[action]["affected_rules"].append(result["rule_id"])

                        # Set priority based on rule level
                        if result["level"] in ["critical", "high"]:
                            remediation_actions[action]["priority"] = "high"
                            if action not in priority_actions:
                                priority_actions.append(action)

            return {
                "total_actions_required": len(remediation_actions),
                "high_priority_actions": len(priority_actions),
                "remediation_actions": list(remediation_actions.values()),
                "priority_actions": priority_actions
            }

        except Exception as e:
            frappe.log_error(f"Error generating remediation summary: {str(e)}")
            return {}
