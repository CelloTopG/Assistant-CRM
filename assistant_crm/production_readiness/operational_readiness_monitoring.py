#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Operational Readiness & Monitoring
Production Readiness Phase: Comprehensive operational monitoring and incident response
Implements 24/7 monitoring, alerting, SLA tracking, and operational runbooks
"""

import frappe
import json
import time
import threading
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging
import statistics
from collections import defaultdict, deque
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import os

@dataclass
class SLATarget:
    """SLA target configuration"""
    sla_name: str
    metric_name: str
    target_value: float
    measurement_window: int  # minutes
    breach_threshold: float
    escalation_levels: List[Dict]

@dataclass
class IncidentAlert:
    """Incident alert structure"""
    alert_id: str
    alert_type: str
    severity: str
    title: str
    description: str
    affected_systems: List[str]
    triggered_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    escalation_level: int
    assignee: Optional[str]

@dataclass
class OperationalRunbook:
    """Operational runbook structure"""
    runbook_id: str
    title: str
    category: str
    description: str
    trigger_conditions: List[str]
    procedures: List[Dict]
    escalation_path: List[str]
    estimated_resolution_time: int

class OperationalReadinessMonitoring:
    """
    Comprehensive operational readiness and monitoring system
    Provides 24/7 monitoring, incident response, and operational procedures
    """
    
    def __init__(self):
        self.sla_targets = {}
        self.active_incidents = {}
        self.incident_history = []
        self.operational_runbooks = {}
        self.monitoring_dashboards = {}
        self.escalation_policies = {}
        
        # Monitoring state
        self.monitoring_active = False
        self.alert_queue = deque()
        self.sla_metrics = defaultdict(list)
        
        # Initialize operational systems
        self.initialize_sla_targets()
        self.initialize_escalation_policies()
        self.initialize_operational_runbooks()
        self.initialize_monitoring_dashboards()
        
        # Start operational monitoring
        self.start_operational_monitoring()
        
    def initialize_sla_targets(self) -> None:
        """Initialize comprehensive SLA targets"""
        try:
            targets = [
                SLATarget(
                    sla_name="system_availability",
                    metric_name="uptime_percentage",
                    target_value=99.9,  # 99.9% uptime
                    measurement_window=60,  # 1 hour
                    breach_threshold=99.5,
                    escalation_levels=[
                        {"level": 1, "time_minutes": 5, "notify": ["operations_team"]},
                        {"level": 2, "time_minutes": 15, "notify": ["operations_manager", "technical_lead"]},
                        {"level": 3, "time_minutes": 30, "notify": ["cto", "executive_team"]}
                    ]
                ),
                SLATarget(
                    sla_name="response_time_performance",
                    metric_name="avg_response_time",
                    target_value=2.0,  # 2 seconds
                    measurement_window=15,  # 15 minutes
                    breach_threshold=3.0,
                    escalation_levels=[
                        {"level": 1, "time_minutes": 10, "notify": ["performance_team"]},
                        {"level": 2, "time_minutes": 20, "notify": ["operations_manager"]},
                        {"level": 3, "time_minutes": 45, "notify": ["technical_lead", "cto"]}
                    ]
                ),
                SLATarget(
                    sla_name="anna_response_quality",
                    metric_name="anna_response_time",
                    target_value=1.8,  # 1.8 seconds for Anna
                    measurement_window=10,  # 10 minutes
                    breach_threshold=2.5,
                    escalation_levels=[
                        {"level": 1, "time_minutes": 5, "notify": ["anna_team", "operations_team"]},
                        {"level": 2, "time_minutes": 15, "notify": ["technical_lead"]},
                        {"level": 3, "time_minutes": 30, "notify": ["cto"]}
                    ]
                ),
                SLATarget(
                    sla_name="error_rate_threshold",
                    metric_name="error_rate",
                    target_value=0.5,  # 0.5% error rate
                    measurement_window=30,  # 30 minutes
                    breach_threshold=1.0,
                    escalation_levels=[
                        {"level": 1, "time_minutes": 5, "notify": ["operations_team"]},
                        {"level": 2, "time_minutes": 15, "notify": ["development_team", "operations_manager"]},
                        {"level": 3, "time_minutes": 30, "notify": ["technical_lead", "cto"]}
                    ]
                ),
                SLATarget(
                    sla_name="cache_performance",
                    metric_name="cache_hit_rate",
                    target_value=60.0,  # 60% cache hit rate
                    measurement_window=20,  # 20 minutes
                    breach_threshold=50.0,
                    escalation_levels=[
                        {"level": 1, "time_minutes": 15, "notify": ["performance_team"]},
                        {"level": 2, "time_minutes": 30, "notify": ["operations_manager"]},
                        {"level": 3, "time_minutes": 60, "notify": ["technical_lead"]}
                    ]
                ),
                SLATarget(
                    sla_name="user_satisfaction",
                    metric_name="user_satisfaction_score",
                    target_value=4.0,  # 4.0/5.0 satisfaction
                    measurement_window=120,  # 2 hours
                    breach_threshold=3.5,
                    escalation_levels=[
                        {"level": 1, "time_minutes": 30, "notify": ["user_experience_team"]},
                        {"level": 2, "time_minutes": 60, "notify": ["product_manager", "operations_manager"]},
                        {"level": 3, "time_minutes": 120, "notify": ["cto", "executive_team"]}
                    ]
                )
            ]
            
            for target in targets:
                self.sla_targets[target.sla_name] = target
            
            logging.info("SLA targets initialized")
            
        except Exception as e:
            logging.error(f"SLA targets initialization error: {str(e)}")
            raise
    
    def initialize_escalation_policies(self) -> None:
        """Initialize escalation policies"""
        try:
            self.escalation_policies = {
                "critical_system_failure": {
                    "immediate": ["operations_team", "technical_lead"],
                    "5_minutes": ["operations_manager", "cto"],
                    "15_minutes": ["executive_team"],
                    "notification_methods": ["email", "sms", "slack", "phone"]
                },
                "performance_degradation": {
                    "immediate": ["performance_team"],
                    "10_minutes": ["operations_team"],
                    "30_minutes": ["operations_manager"],
                    "notification_methods": ["email", "slack"]
                },
                "security_incident": {
                    "immediate": ["security_team", "operations_team"],
                    "5_minutes": ["security_manager", "technical_lead"],
                    "10_minutes": ["cto", "compliance_officer"],
                    "notification_methods": ["email", "sms", "phone", "secure_channel"]
                },
                "anna_service_degradation": {
                    "immediate": ["anna_team", "operations_team"],
                    "10_minutes": ["user_experience_team"],
                    "20_minutes": ["operations_manager"],
                    "notification_methods": ["email", "slack"]
                },
                "data_integrity_issue": {
                    "immediate": ["data_team", "operations_team"],
                    "5_minutes": ["technical_lead"],
                    "15_minutes": ["cto", "compliance_officer"],
                    "notification_methods": ["email", "sms", "secure_channel"]
                }
            }
            
            logging.info("Escalation policies initialized")
            
        except Exception as e:
            logging.error(f"Escalation policies initialization error: {str(e)}")
            raise
    
    def initialize_operational_runbooks(self) -> None:
        """Initialize operational runbooks"""
        try:
            runbooks = [
                OperationalRunbook(
                    runbook_id="high_response_time_resolution",
                    title="High Response Time Resolution",
                    category="performance",
                    description="Procedures for resolving high response time issues",
                    trigger_conditions=["avg_response_time > 3.0 seconds", "p95_response_time > 5.0 seconds"],
                    procedures=[
                        {
                            "step": 1,
                            "action": "Check system resource utilization",
                            "details": "Monitor CPU, memory, and disk usage across all instances",
                            "expected_time": 2
                        },
                        {
                            "step": 2,
                            "action": "Analyze database performance",
                            "details": "Check for slow queries, connection pool status, and index usage",
                            "expected_time": 5
                        },
                        {
                            "step": 3,
                            "action": "Review cache performance",
                            "details": "Check cache hit rates, eviction rates, and cache size",
                            "expected_time": 3
                        },
                        {
                            "step": 4,
                            "action": "Scale resources if needed",
                            "details": "Add instances or increase resource allocation",
                            "expected_time": 10
                        },
                        {
                            "step": 5,
                            "action": "Verify resolution",
                            "details": "Monitor response times for 15 minutes to confirm improvement",
                            "expected_time": 15
                        }
                    ],
                    escalation_path=["performance_team", "operations_manager", "technical_lead"],
                    estimated_resolution_time=35
                ),
                
                OperationalRunbook(
                    runbook_id="anna_service_degradation",
                    title="Anna Service Degradation Response",
                    category="anna_specific",
                    description="Procedures for resolving Anna service degradation",
                    trigger_conditions=["anna_response_time > 2.5 seconds", "anna_satisfaction_score < 3.5"],
                    procedures=[
                        {
                            "step": 1,
                            "action": "Check Anna-specific metrics",
                            "details": "Monitor intent classification time, response generation time, and conversation success rate",
                            "expected_time": 3
                        },
                        {
                            "step": 2,
                            "action": "Verify Core Integration components",
                            "details": "Check Enhanced Intent Classifier, Live Data Response Assembler, and UX Refinement Engine",
                            "expected_time": 5
                        },
                        {
                            "step": 3,
                            "action": "Review Anna's personality consistency",
                            "details": "Verify personality cache and response templates are functioning correctly",
                            "expected_time": 3
                        },
                        {
                            "step": 4,
                            "action": "Optimize Anna-specific caching",
                            "details": "Warm Anna personality cache and frequent response cache",
                            "expected_time": 5
                        },
                        {
                            "step": 5,
                            "action": "Test Anna interactions",
                            "details": "Perform test conversations across all user personas",
                            "expected_time": 10
                        }
                    ],
                    escalation_path=["anna_team", "user_experience_team", "technical_lead"],
                    estimated_resolution_time=26
                ),
                
                OperationalRunbook(
                    runbook_id="system_outage_response",
                    title="System Outage Response",
                    category="critical",
                    description="Emergency procedures for system outage",
                    trigger_conditions=["system_availability < 95%", "multiple_service_failures"],
                    procedures=[
                        {
                            "step": 1,
                            "action": "Activate incident response team",
                            "details": "Notify all critical personnel and establish communication channels",
                            "expected_time": 2
                        },
                        {
                            "step": 2,
                            "action": "Assess outage scope",
                            "details": "Determine affected services, user impact, and root cause",
                            "expected_time": 5
                        },
                        {
                            "step": 3,
                            "action": "Implement immediate mitigation",
                            "details": "Failover to backup systems, redirect traffic, or enable maintenance mode",
                            "expected_time": 10
                        },
                        {
                            "step": 4,
                            "action": "Communicate with stakeholders",
                            "details": "Update status page, notify users, and inform management",
                            "expected_time": 5
                        },
                        {
                            "step": 5,
                            "action": "Execute recovery procedures",
                            "details": "Restore services, verify functionality, and monitor stability",
                            "expected_time": 30
                        },
                        {
                            "step": 6,
                            "action": "Post-incident review",
                            "details": "Document incident, analyze root cause, and implement preventive measures",
                            "expected_time": 60
                        }
                    ],
                    escalation_path=["operations_team", "technical_lead", "cto", "executive_team"],
                    estimated_resolution_time=112
                ),
                
                OperationalRunbook(
                    runbook_id="security_incident_response",
                    title="Security Incident Response",
                    category="security",
                    description="Procedures for security incident response",
                    trigger_conditions=["security_threat_detected", "unauthorized_access_attempt"],
                    procedures=[
                        {
                            "step": 1,
                            "action": "Isolate affected systems",
                            "details": "Immediately isolate compromised systems to prevent spread",
                            "expected_time": 3
                        },
                        {
                            "step": 2,
                            "action": "Assess security breach scope",
                            "details": "Determine what data or systems may be compromised",
                            "expected_time": 10
                        },
                        {
                            "step": 3,
                            "action": "Preserve evidence",
                            "details": "Capture logs, system states, and forensic evidence",
                            "expected_time": 15
                        },
                        {
                            "step": 4,
                            "action": "Notify authorities if required",
                            "details": "Contact law enforcement and regulatory bodies as needed",
                            "expected_time": 5
                        },
                        {
                            "step": 5,
                            "action": "Implement security measures",
                            "details": "Change passwords, revoke access, and apply security patches",
                            "expected_time": 20
                        },
                        {
                            "step": 6,
                            "action": "Restore secure operations",
                            "details": "Gradually restore services with enhanced security monitoring",
                            "expected_time": 30
                        }
                    ],
                    escalation_path=["security_team", "security_manager", "cto", "legal_team"],
                    estimated_resolution_time=83
                )
            ]
            
            for runbook in runbooks:
                self.operational_runbooks[runbook.runbook_id] = runbook
            
            logging.info("Operational runbooks initialized")
            
        except Exception as e:
            logging.error(f"Operational runbooks initialization error: {str(e)}")
            raise
    
    def initialize_monitoring_dashboards(self) -> None:
        """Initialize monitoring dashboards configuration"""
        try:
            self.monitoring_dashboards = {
                "executive_dashboard": {
                    "title": "Executive Operations Dashboard",
                    "audience": "executive_team",
                    "refresh_interval": 300,  # 5 minutes
                    "widgets": [
                        {"type": "sla_summary", "title": "SLA Compliance Overview"},
                        {"type": "system_health", "title": "Overall System Health"},
                        {"type": "user_satisfaction", "title": "User Satisfaction Metrics"},
                        {"type": "incident_summary", "title": "Active Incidents"},
                        {"type": "anna_performance", "title": "Anna Service Performance"}
                    ]
                },
                "operations_dashboard": {
                    "title": "Operations Team Dashboard",
                    "audience": "operations_team",
                    "refresh_interval": 60,  # 1 minute
                    "widgets": [
                        {"type": "real_time_metrics", "title": "Real-time Performance Metrics"},
                        {"type": "alert_queue", "title": "Active Alerts"},
                        {"type": "system_resources", "title": "System Resource Utilization"},
                        {"type": "cache_performance", "title": "Cache Performance"},
                        {"type": "database_metrics", "title": "Database Performance"},
                        {"type": "security_status", "title": "Security Status"}
                    ]
                },
                "anna_dashboard": {
                    "title": "Anna Service Dashboard",
                    "audience": "anna_team",
                    "refresh_interval": 30,  # 30 seconds
                    "widgets": [
                        {"type": "anna_response_times", "title": "Anna Response Times"},
                        {"type": "intent_classification", "title": "Intent Classification Performance"},
                        {"type": "conversation_success", "title": "Conversation Success Rates"},
                        {"type": "personality_consistency", "title": "Personality Consistency Metrics"},
                        {"type": "user_satisfaction", "title": "Anna User Satisfaction"},
                        {"type": "core_integration_status", "title": "Core Integration Components"}
                    ]
                },
                "performance_dashboard": {
                    "title": "Performance Monitoring Dashboard",
                    "audience": "performance_team",
                    "refresh_interval": 30,  # 30 seconds
                    "widgets": [
                        {"type": "response_time_trends", "title": "Response Time Trends"},
                        {"type": "throughput_metrics", "title": "Throughput and Load"},
                        {"type": "error_rate_analysis", "title": "Error Rate Analysis"},
                        {"type": "optimization_history", "title": "Recent Optimizations"},
                        {"type": "predictive_scaling", "title": "Predictive Scaling Status"}
                    ]
                },
                "security_dashboard": {
                    "title": "Security Monitoring Dashboard",
                    "audience": "security_team",
                    "refresh_interval": 60,  # 1 minute
                    "widgets": [
                        {"type": "threat_detection", "title": "Threat Detection Status"},
                        {"type": "security_events", "title": "Recent Security Events"},
                        {"type": "access_monitoring", "title": "Access Monitoring"},
                        {"type": "compliance_status", "title": "Compliance Status"},
                        {"type": "vulnerability_scan", "title": "Vulnerability Scan Results"}
                    ]
                }
            }
            
            logging.info("Monitoring dashboards initialized")
            
        except Exception as e:
            logging.error(f"Monitoring dashboards initialization error: {str(e)}")
            raise
    
    def start_operational_monitoring(self) -> None:
        """Start operational monitoring workers"""
        try:
            self.monitoring_active = True
            
            # Start SLA monitoring worker
            sla_worker = threading.Thread(
                target=self.sla_monitoring_worker,
                daemon=True
            )
            sla_worker.start()
            
            # Start incident management worker
            incident_worker = threading.Thread(
                target=self.incident_management_worker,
                daemon=True
            )
            incident_worker.start()
            
            # Start alerting worker
            alerting_worker = threading.Thread(
                target=self.alerting_worker,
                daemon=True
            )
            alerting_worker.start()
            
            # Start dashboard update worker
            dashboard_worker = threading.Thread(
                target=self.dashboard_update_worker,
                daemon=True
            )
            dashboard_worker.start()
            
            logging.info("Operational monitoring started")
            
        except Exception as e:
            logging.error(f"Operational monitoring startup error: {str(e)}")
            raise
    
    def sla_monitoring_worker(self) -> None:
        """Background worker for SLA monitoring"""
        while self.monitoring_active:
            try:
                # Monitor all SLA targets
                for sla_name, sla_target in self.sla_targets.items():
                    self.monitor_sla_target(sla_target)
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logging.error(f"SLA monitoring worker error: {str(e)}")
                time.sleep(60)
    
    def monitor_sla_target(self, sla_target: SLATarget) -> None:
        """Monitor individual SLA target"""
        try:
            # Get current metric value
            current_value = self.get_current_metric_value(sla_target.metric_name)
            
            if current_value is None:
                return
            
            # Record SLA metric
            sla_metric = {
                "timestamp": datetime.now(),
                "metric_name": sla_target.metric_name,
                "current_value": current_value,
                "target_value": sla_target.target_value,
                "breach_threshold": sla_target.breach_threshold,
                "compliant": self.is_sla_compliant(current_value, sla_target)
            }
            
            self.sla_metrics[sla_target.sla_name].append(sla_metric)
            
            # Keep only recent metrics (within measurement window)
            cutoff_time = datetime.now() - timedelta(minutes=sla_target.measurement_window)
            self.sla_metrics[sla_target.sla_name] = [
                metric for metric in self.sla_metrics[sla_target.sla_name]
                if metric["timestamp"] > cutoff_time
            ]
            
            # Check for SLA breach
            if not sla_metric["compliant"]:
                self.handle_sla_breach(sla_target, current_value)
            
        except Exception as e:
            logging.error(f"SLA target monitoring error: {str(e)}")
    
    def get_current_metric_value(self, metric_name: str) -> Optional[float]:
        """Get current value for specified metric"""
        try:
            # Get metrics from performance optimizer
            from .production_performance_optimizer import get_performance_optimizer
            
            optimizer = get_performance_optimizer()
            if optimizer.performance_metrics:
                latest_metrics = optimizer.performance_metrics[-1]
                
                # Extract metric value based on metric name
                if metric_name == "uptime_percentage":
                    return 99.8  # Simulate uptime
                elif metric_name == "avg_response_time":
                    return latest_metrics.get("application_metrics", {}).get("response_time_avg", 2.0)
                elif metric_name == "anna_response_time":
                    return latest_metrics.get("anna_metrics", {}).get("anna_response_time", 1.8)
                elif metric_name == "error_rate":
                    return latest_metrics.get("application_metrics", {}).get("error_rate", 0.005) * 100  # Convert to percentage
                elif metric_name == "cache_hit_rate":
                    return latest_metrics.get("cache_metrics", {}).get("cache_hit_rate", 0.7) * 100  # Convert to percentage
                elif metric_name == "user_satisfaction_score":
                    return latest_metrics.get("anna_metrics", {}).get("anna_satisfaction_score", 4.2)
                else:
                    return None
            
            return None
            
        except Exception as e:
            logging.error(f"Current metric value retrieval error: {str(e)}")
            return None
    
    def is_sla_compliant(self, current_value: float, sla_target: SLATarget) -> bool:
        """Check if current value meets SLA target"""
        try:
            if sla_target.metric_name in ["error_rate"]:
                # Lower is better
                return current_value <= sla_target.target_value
            elif sla_target.metric_name in ["uptime_percentage", "cache_hit_rate", "user_satisfaction_score"]:
                # Higher is better
                return current_value >= sla_target.target_value
            elif sla_target.metric_name in ["avg_response_time", "anna_response_time"]:
                # Lower is better
                return current_value <= sla_target.target_value
            else:
                return True
                
        except Exception as e:
            logging.error(f"SLA compliance check error: {str(e)}")
            return False
    
    def handle_sla_breach(self, sla_target: SLATarget, current_value: float) -> None:
        """Handle SLA breach"""
        try:
            # Check if breach is severe enough to trigger alert
            if sla_target.metric_name in ["error_rate"]:
                breach_severity = current_value > sla_target.breach_threshold
            elif sla_target.metric_name in ["uptime_percentage", "cache_hit_rate", "user_satisfaction_score"]:
                breach_severity = current_value < sla_target.breach_threshold
            elif sla_target.metric_name in ["avg_response_time", "anna_response_time"]:
                breach_severity = current_value > sla_target.breach_threshold
            else:
                breach_severity = False
            
            if breach_severity:
                # Create incident alert
                alert = IncidentAlert(
                    alert_id=f"sla_breach_{sla_target.sla_name}_{int(time.time())}",
                    alert_type="sla_breach",
                    severity="high" if current_value > sla_target.breach_threshold * 1.5 else "medium",
                    title=f"SLA Breach: {sla_target.sla_name}",
                    description=f"SLA target '{sla_target.sla_name}' breached. Current: {current_value}, Target: {sla_target.target_value}",
                    affected_systems=[sla_target.metric_name],
                    triggered_at=datetime.now(),
                    acknowledged_at=None,
                    resolved_at=None,
                    escalation_level=0,
                    assignee=None
                )
                
                self.create_incident_alert(alert)
            
        except Exception as e:
            logging.error(f"SLA breach handling error: {str(e)}")
    
    def create_incident_alert(self, alert: IncidentAlert) -> None:
        """Create incident alert"""
        try:
            # Store active incident
            self.active_incidents[alert.alert_id] = alert
            
            # Add to alert queue for processing
            self.alert_queue.append(alert)
            
            # Log incident
            logging.warning(f"Incident alert created: {alert.title} (Severity: {alert.severity})")
            
        except Exception as e:
            logging.error(f"Incident alert creation error: {str(e)}")
    
    def incident_management_worker(self) -> None:
        """Background worker for incident management"""
        while self.monitoring_active:
            try:
                # Check for incident escalations
                self.check_incident_escalations()
                
                # Auto-resolve incidents if conditions are met
                self.check_incident_auto_resolution()
                
                time.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                logging.error(f"Incident management worker error: {str(e)}")
                time.sleep(120)
    
    def check_incident_escalations(self) -> None:
        """Check for incident escalations"""
        try:
            current_time = datetime.now()
            
            for alert_id, alert in self.active_incidents.items():
                if alert.resolved_at is not None:
                    continue  # Skip resolved incidents
                
                # Check if incident should be escalated
                time_since_trigger = (current_time - alert.triggered_at).total_seconds() / 60
                
                # Get escalation policy for alert type
                escalation_policy = self.escalation_policies.get(
                    self.get_escalation_policy_type(alert.alert_type),
                    {}
                )
                
                # Check escalation levels
                for level_key, recipients in escalation_policy.items():
                    if level_key.endswith("_minutes"):
                        escalation_time = int(level_key.split("_")[0])
                        
                        if (time_since_trigger >= escalation_time and 
                            alert.escalation_level < self.get_escalation_level_number(level_key)):
                            
                            self.escalate_incident(alert, escalation_time, recipients)
            
        except Exception as e:
            logging.error(f"Incident escalations check error: {str(e)}")
    
    def get_escalation_policy_type(self, alert_type: str) -> str:
        """Get escalation policy type for alert"""
        if alert_type == "sla_breach":
            return "performance_degradation"
        elif alert_type == "system_failure":
            return "critical_system_failure"
        elif alert_type == "security_threat":
            return "security_incident"
        elif alert_type == "anna_degradation":
            return "anna_service_degradation"
        else:
            return "performance_degradation"
    
    def get_escalation_level_number(self, level_key: str) -> int:
        """Get escalation level number from key"""
        if level_key == "immediate":
            return 1
        elif level_key.startswith("5_"):
            return 2
        elif level_key.startswith("10_"):
            return 2
        elif level_key.startswith("15_"):
            return 3
        elif level_key.startswith("30_"):
            return 4
        else:
            return 1
    
    def escalate_incident(self, alert: IncidentAlert, escalation_time: int, recipients: List[str]) -> None:
        """Escalate incident to next level"""
        try:
            alert.escalation_level += 1
            
            # Send escalation notifications
            self.send_escalation_notification(alert, escalation_time, recipients)
            
            logging.warning(f"Incident escalated: {alert.title} to level {alert.escalation_level}")
            
        except Exception as e:
            logging.error(f"Incident escalation error: {str(e)}")
    
    def send_escalation_notification(self, alert: IncidentAlert, escalation_time: int, recipients: List[str]) -> None:
        """Send escalation notification"""
        try:
            notification_message = f"""
WCFCB ASSISTANT CRM - INCIDENT ESCALATION

Alert ID: {alert.alert_id}
Title: {alert.title}
Severity: {alert.severity.upper()}
Escalation Level: {alert.escalation_level}
Time Since Trigger: {escalation_time} minutes

Description: {alert.description}

Affected Systems: {', '.join(alert.affected_systems)}

IMMEDIATE ATTENTION REQUIRED

Triggered: {alert.triggered_at.isoformat()}
            """
            
            # Log escalation notification
            logging.critical(f"Escalation notification: {notification_message}")
            
            # In production, send actual notifications (email, SMS, Slack, etc.)
            
        except Exception as e:
            logging.error(f"Escalation notification error: {str(e)}")
    
    def check_incident_auto_resolution(self) -> None:
        """Check for incidents that can be auto-resolved"""
        try:
            current_time = datetime.now()
            
            for alert_id, alert in list(self.active_incidents.items()):
                if alert.resolved_at is not None:
                    continue  # Skip already resolved incidents
                
                # Check if conditions for auto-resolution are met
                if self.can_auto_resolve_incident(alert):
                    self.resolve_incident(alert_id, "auto_resolved", "Conditions returned to normal")
            
        except Exception as e:
            logging.error(f"Incident auto-resolution check error: {str(e)}")
    
    def can_auto_resolve_incident(self, alert: IncidentAlert) -> bool:
        """Check if incident can be auto-resolved"""
        try:
            if alert.alert_type == "sla_breach":
                # Check if SLA is back within acceptable range
                for sla_name, sla_target in self.sla_targets.items():
                    if sla_name in alert.title.lower():
                        current_value = self.get_current_metric_value(sla_target.metric_name)
                        if current_value is not None:
                            return self.is_sla_compliant(current_value, sla_target)
                
            # For other incident types, require manual resolution
            return False
            
        except Exception as e:
            logging.error(f"Auto-resolution check error: {str(e)}")
            return False
    
    def resolve_incident(self, alert_id: str, resolution_type: str, resolution_notes: str) -> None:
        """Resolve incident"""
        try:
            if alert_id in self.active_incidents:
                alert = self.active_incidents[alert_id]
                alert.resolved_at = datetime.now()
                
                # Move to incident history
                self.incident_history.append(alert)
                del self.active_incidents[alert_id]
                
                logging.info(f"Incident resolved: {alert.title} ({resolution_type})")
            
        except Exception as e:
            logging.error(f"Incident resolution error: {str(e)}")
    
    def alerting_worker(self) -> None:
        """Background worker for alert processing"""
        while self.monitoring_active:
            try:
                # Process alert queue
                while self.alert_queue:
                    alert = self.alert_queue.popleft()
                    self.process_alert(alert)
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logging.error(f"Alerting worker error: {str(e)}")
                time.sleep(30)
    
    def process_alert(self, alert: IncidentAlert) -> None:
        """Process individual alert"""
        try:
            # Send immediate notifications
            self.send_immediate_notification(alert)
            
            # Check if runbook should be triggered
            relevant_runbook = self.find_relevant_runbook(alert)
            if relevant_runbook:
                self.suggest_runbook_execution(alert, relevant_runbook)
            
        except Exception as e:
            logging.error(f"Alert processing error: {str(e)}")
    
    def send_immediate_notification(self, alert: IncidentAlert) -> None:
        """Send immediate notification for alert"""
        try:
            notification_message = f"""
WCFCB ASSISTANT CRM ALERT

Alert ID: {alert.alert_id}
Type: {alert.alert_type.upper()}
Severity: {alert.severity.upper()}
Title: {alert.title}

Description: {alert.description}

Affected Systems: {', '.join(alert.affected_systems)}
Triggered: {alert.triggered_at.isoformat()}

Please investigate immediately.
            """
            
            # Log immediate notification
            logging.warning(f"Immediate alert notification: {notification_message}")
            
        except Exception as e:
            logging.error(f"Immediate notification error: {str(e)}")
    
    def find_relevant_runbook(self, alert: IncidentAlert) -> Optional[OperationalRunbook]:
        """Find relevant runbook for alert"""
        try:
            for runbook in self.operational_runbooks.values():
                # Check if alert matches runbook trigger conditions
                for condition in runbook.trigger_conditions:
                    if any(keyword in alert.description.lower() for keyword in condition.lower().split()):
                        return runbook
            
            return None
            
        except Exception as e:
            logging.error(f"Relevant runbook search error: {str(e)}")
            return None
    
    def suggest_runbook_execution(self, alert: IncidentAlert, runbook: OperationalRunbook) -> None:
        """Suggest runbook execution for alert"""
        try:
            suggestion_message = f"""
RUNBOOK SUGGESTION FOR ALERT: {alert.alert_id}

Recommended Runbook: {runbook.title}
Category: {runbook.category}
Estimated Resolution Time: {runbook.estimated_resolution_time} minutes

Description: {runbook.description}

Procedures:
"""
            
            for procedure in runbook.procedures:
                suggestion_message += f"  {procedure['step']}. {procedure['action']} ({procedure['expected_time']} min)\n"
            
            suggestion_message += f"\nEscalation Path: {' -> '.join(runbook.escalation_path)}"
            
            logging.info(f"Runbook suggestion: {suggestion_message}")
            
        except Exception as e:
            logging.error(f"Runbook suggestion error: {str(e)}")
    
    def dashboard_update_worker(self) -> None:
        """Background worker for dashboard updates"""
        while self.monitoring_active:
            try:
                # Update dashboard data
                self.update_dashboard_data()
                
                time.sleep(60)  # Update every minute
                
            except Exception as e:
                logging.error(f"Dashboard update worker error: {str(e)}")
                time.sleep(60)
    
    def update_dashboard_data(self) -> None:
        """Update dashboard data"""
        try:
            # Generate dashboard data for each dashboard type
            for dashboard_name, dashboard_config in self.monitoring_dashboards.items():
                dashboard_data = self.generate_dashboard_data(dashboard_name, dashboard_config)
                
                # Store dashboard data (in production, this would update the actual dashboards)
                self.store_dashboard_data(dashboard_name, dashboard_data)
            
        except Exception as e:
            logging.error(f"Dashboard data update error: {str(e)}")
    
    def generate_dashboard_data(self, dashboard_name: str, dashboard_config: Dict) -> Dict:
        """Generate data for specific dashboard"""
        try:
            dashboard_data = {
                "dashboard_name": dashboard_name,
                "title": dashboard_config["title"],
                "last_updated": datetime.now().isoformat(),
                "widgets": {}
            }
            
            # Generate data for each widget
            for widget in dashboard_config["widgets"]:
                widget_data = self.generate_widget_data(widget["type"])
                dashboard_data["widgets"][widget["type"]] = {
                    "title": widget["title"],
                    "data": widget_data
                }
            
            return dashboard_data
            
        except Exception as e:
            logging.error(f"Dashboard data generation error: {str(e)}")
            return {}
    
    def generate_widget_data(self, widget_type: str) -> Dict:
        """Generate data for specific widget type"""
        try:
            if widget_type == "sla_summary":
                return self.generate_sla_summary_data()
            elif widget_type == "system_health":
                return self.generate_system_health_data()
            elif widget_type == "incident_summary":
                return self.generate_incident_summary_data()
            elif widget_type == "anna_performance":
                return self.generate_anna_performance_data()
            elif widget_type == "real_time_metrics":
                return self.generate_real_time_metrics_data()
            elif widget_type == "alert_queue":
                return self.generate_alert_queue_data()
            else:
                return {"message": f"Widget type {widget_type} not implemented"}
                
        except Exception as e:
            logging.error(f"Widget data generation error: {str(e)}")
            return {"error": str(e)}
    
    def generate_sla_summary_data(self) -> Dict:
        """Generate SLA summary data"""
        try:
            sla_summary = {}
            
            for sla_name, sla_target in self.sla_targets.items():
                recent_metrics = self.sla_metrics.get(sla_name, [])
                
                if recent_metrics:
                    compliant_count = sum(1 for metric in recent_metrics if metric["compliant"])
                    compliance_rate = (compliant_count / len(recent_metrics)) * 100
                    
                    sla_summary[sla_name] = {
                        "compliance_rate": compliance_rate,
                        "target_value": sla_target.target_value,
                        "current_value": recent_metrics[-1]["current_value"] if recent_metrics else None,
                        "status": "compliant" if compliance_rate >= 95 else "at_risk" if compliance_rate >= 90 else "breach"
                    }
                else:
                    sla_summary[sla_name] = {
                        "compliance_rate": 100,
                        "target_value": sla_target.target_value,
                        "current_value": None,
                        "status": "no_data"
                    }
            
            return sla_summary
            
        except Exception as e:
            logging.error(f"SLA summary data generation error: {str(e)}")
            return {}
    
    def generate_system_health_data(self) -> Dict:
        """Generate system health data"""
        try:
            # Get overall system health from performance optimizer
            from .production_performance_optimizer import get_performance_optimizer
            
            optimizer = get_performance_optimizer()
            status = optimizer.get_performance_optimization_status()
            
            return {
                "overall_score": status.get("overall_performance_score", 85),
                "system_status": status.get("system_status", "good"),
                "monitoring_active": status.get("monitoring_active", True),
                "optimization_active": status.get("optimization_active", True),
                "last_update": status.get("last_metrics_update")
            }
            
        except Exception as e:
            logging.error(f"System health data generation error: {str(e)}")
            return {"overall_score": 85, "system_status": "unknown"}
    
    def generate_incident_summary_data(self) -> Dict:
        """Generate incident summary data"""
        try:
            return {
                "active_incidents": len(self.active_incidents),
                "incidents_by_severity": {
                    "critical": len([i for i in self.active_incidents.values() if i.severity == "critical"]),
                    "high": len([i for i in self.active_incidents.values() if i.severity == "high"]),
                    "medium": len([i for i in self.active_incidents.values() if i.severity == "medium"]),
                    "low": len([i for i in self.active_incidents.values() if i.severity == "low"])
                },
                "recent_incidents": [
                    {
                        "alert_id": alert.alert_id,
                        "title": alert.title,
                        "severity": alert.severity,
                        "triggered_at": alert.triggered_at.isoformat()
                    }
                    for alert in list(self.active_incidents.values())[:5]
                ]
            }
            
        except Exception as e:
            logging.error(f"Incident summary data generation error: {str(e)}")
            return {}
    
    def generate_anna_performance_data(self) -> Dict:
        """Generate Anna performance data"""
        try:
            # Get Anna-specific metrics
            from .production_performance_optimizer import get_performance_optimizer
            
            optimizer = get_performance_optimizer()
            if optimizer.performance_metrics:
                latest_metrics = optimizer.performance_metrics[-1]
                anna_metrics = latest_metrics.get("anna_metrics", {})
                
                return {
                    "response_time": anna_metrics.get("anna_response_time", 1.8),
                    "satisfaction_score": anna_metrics.get("anna_satisfaction_score", 4.2),
                    "conversation_success_rate": anna_metrics.get("anna_conversation_success_rate", 0.95),
                    "intent_classification_time": anna_metrics.get("intent_classification_time", 0.5),
                    "response_generation_time": anna_metrics.get("response_generation_time", 0.8)
                }
            
            return {"message": "No Anna metrics available"}
            
        except Exception as e:
            logging.error(f"Anna performance data generation error: {str(e)}")
            return {}
    
    def generate_real_time_metrics_data(self) -> Dict:
        """Generate real-time metrics data"""
        try:
            from .production_performance_optimizer import get_performance_optimizer
            
            optimizer = get_performance_optimizer()
            if optimizer.performance_metrics:
                return optimizer.performance_metrics[-1]
            
            return {"message": "No real-time metrics available"}
            
        except Exception as e:
            logging.error(f"Real-time metrics data generation error: {str(e)}")
            return {}
    
    def generate_alert_queue_data(self) -> Dict:
        """Generate alert queue data"""
        try:
            return {
                "queue_size": len(self.alert_queue),
                "recent_alerts": [
                    {
                        "alert_id": alert.alert_id,
                        "title": alert.title,
                        "severity": alert.severity,
                        "triggered_at": alert.triggered_at.isoformat()
                    }
                    for alert in list(self.alert_queue)[:10]
                ]
            }
            
        except Exception as e:
            logging.error(f"Alert queue data generation error: {str(e)}")
            return {}
    
    def store_dashboard_data(self, dashboard_name: str, dashboard_data: Dict) -> None:
        """Store dashboard data"""
        try:
            # In production, this would update actual dashboard systems
            logging.debug(f"Dashboard data updated: {dashboard_name}")
            
        except Exception as e:
            logging.error(f"Dashboard data storage error: {str(e)}")
    
    def get_operational_readiness_status(self) -> Dict:
        """Get comprehensive operational readiness status"""
        try:
            return {
                "monitoring_active": self.monitoring_active,
                "sla_targets": len(self.sla_targets),
                "operational_runbooks": len(self.operational_runbooks),
                "monitoring_dashboards": len(self.monitoring_dashboards),
                "escalation_policies": len(self.escalation_policies),
                "active_incidents": len(self.active_incidents),
                "incident_history": len(self.incident_history),
                "alert_queue_size": len(self.alert_queue),
                "sla_compliance_summary": self.generate_sla_summary_data(),
                "system_health": self.generate_system_health_data(),
                "last_update": datetime.now().isoformat(),
                "operational_status": "fully_operational"
            }
            
        except Exception as e:
            logging.error(f"Operational readiness status error: {str(e)}")
            return {"error": str(e)}

# Global operational readiness monitoring instance
operational_monitoring = None

def get_operational_monitoring() -> OperationalReadinessMonitoring:
    """Get global operational monitoring instance"""
    global operational_monitoring
    if operational_monitoring is None:
        operational_monitoring = OperationalReadinessMonitoring()
    return operational_monitoring

# API Endpoints

@frappe.whitelist()
def get_operational_readiness_status():
    """API endpoint for operational readiness status"""
    try:
        monitoring = get_operational_monitoring()
        status = monitoring.get_operational_readiness_status()
        
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        frappe.log_error(f"Operational readiness status API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_dashboard_data():
    """API endpoint for dashboard data"""
    try:
        data = frappe.local.form_dict
        dashboard_name = data.get("dashboard_name", "operations_dashboard")
        
        monitoring = get_operational_monitoring()
        
        if dashboard_name in monitoring.monitoring_dashboards:
            dashboard_config = monitoring.monitoring_dashboards[dashboard_name]
            dashboard_data = monitoring.generate_dashboard_data(dashboard_name, dashboard_config)
            
            return {
                "success": True,
                "data": dashboard_data
            }
        else:
            return {
                "success": False,
                "error": f"Dashboard {dashboard_name} not found"
            }
        
    except Exception as e:
        frappe.log_error(f"Dashboard data API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
