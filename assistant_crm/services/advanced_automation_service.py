import frappe
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import asyncio
import schedule
import threading
from dataclasses import dataclass
from enum import Enum


class AutomationTriggerType(Enum):
    TIME_BASED = "time_based"
    EVENT_BASED = "event_based"
    CONDITION_BASED = "condition_based"
    ML_PREDICTION = "ml_prediction"


class AutomationActionType(Enum):
    SEND_MESSAGE = "send_message"
    ASSIGN_AGENT = "assign_agent"
    UPDATE_STATUS = "update_status"
    CREATE_TASK = "create_task"
    ESCALATE = "escalate"
    GENERATE_REPORT = "generate_report"
    SYNC_DATA = "sync_data"
    COMPLIANCE_CHECK = "compliance_check"


@dataclass
class AutomationRule:
    id: str
    name: str
    description: str
    trigger_type: AutomationTriggerType
    trigger_conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    enabled: bool
    priority: int
    created_by: str
    created_at: datetime
    last_executed: Optional[datetime] = None
    execution_count: int = 0
    success_rate: float = 0.0


class AdvancedAutomationService:
    """
    Advanced Automation Service for WCFCB Assistant CRM
    Phase C: Intelligent workflow automation and regulatory compliance
    Compliance Target: 99/100 score
    """
    
    def __init__(self):
        self.config = self.get_automation_configuration()
        self.automation_rules = self.load_automation_rules()
        self.scheduler = schedule
        self.is_running = False
        self.automation_thread = None
        
    def get_automation_configuration(self) -> Dict[str, Any]:
        """Get automation service configuration"""
        try:
            settings = frappe.get_single("Advanced Automation Settings")
            return {
                "enabled": settings.get("enabled", 1),
                "intelligent_routing_enabled": settings.get("intelligent_routing_enabled", 1),
                "auto_escalation_enabled": settings.get("auto_escalation_enabled", 1),
                "predictive_assignment_enabled": settings.get("predictive_assignment_enabled", 1),
                "compliance_monitoring_enabled": settings.get("compliance_monitoring_enabled", 1),
                "workflow_optimization_enabled": settings.get("workflow_optimization_enabled", 1),
                "max_concurrent_automations": settings.get("max_concurrent_automations", 10),
                "automation_retry_attempts": settings.get("automation_retry_attempts", 3),
                "execution_timeout_seconds": settings.get("execution_timeout_seconds", 300),
                "performance_monitoring_enabled": settings.get("performance_monitoring_enabled", 1)
            }
        except Exception:
            return {
                "enabled": 1,
                "intelligent_routing_enabled": 1,
                "auto_escalation_enabled": 1,
                "predictive_assignment_enabled": 1,
                "compliance_monitoring_enabled": 1,
                "workflow_optimization_enabled": 1,
                "max_concurrent_automations": 10,
                "automation_retry_attempts": 3,
                "execution_timeout_seconds": 300,
                "performance_monitoring_enabled": 1
            }
    
    def load_automation_rules(self) -> List[AutomationRule]:
        """Load automation rules from database"""
        try:
            rules_data = frappe.get_all(
                "Automation Rule",
                filters={"enabled": 1},
                fields=["*"]
            )
            
            rules = []
            for rule_data in rules_data:
                rule = AutomationRule(
                    id=rule_data.name,
                    name=rule_data.rule_name,
                    description=rule_data.description,
                    trigger_type=AutomationTriggerType(rule_data.trigger_type),
                    trigger_conditions=json.loads(rule_data.trigger_conditions or "{}"),
                    actions=json.loads(rule_data.actions or "[]"),
                    enabled=rule_data.enabled,
                    priority=rule_data.priority or 0,
                    created_by=rule_data.created_by,
                    created_at=rule_data.creation,
                    last_executed=rule_data.last_executed,
                    execution_count=rule_data.execution_count or 0,
                    success_rate=rule_data.success_rate or 0.0
                )
                rules.append(rule)
            
            # Sort by priority (higher priority first)
            rules.sort(key=lambda x: x.priority, reverse=True)
            return rules
            
        except Exception as e:
            frappe.log_error(f"Error loading automation rules: {str(e)}")
            return []
    
    def start_automation_engine(self):
        """Start the automation engine in a separate thread"""
        try:
            if not self.config["enabled"] or self.is_running:
                return
            
            self.is_running = True
            
            # Schedule time-based automations
            self.schedule_time_based_automations()
            
            # Start automation thread
            self.automation_thread = threading.Thread(target=self.automation_worker, daemon=True)
            self.automation_thread.start()
            
            frappe.log_error("Advanced Automation Engine started successfully")
            
        except Exception as e:
            frappe.log_error(f"Error starting automation engine: {str(e)}")
            self.is_running = False
    
    def stop_automation_engine(self):
        """Stop the automation engine"""
        try:
            self.is_running = False
            if self.automation_thread and self.automation_thread.is_alive():
                self.automation_thread.join(timeout=5)
            
            frappe.log_error("Advanced Automation Engine stopped")
            
        except Exception as e:
            frappe.log_error(f"Error stopping automation engine: {str(e)}")
    
    def automation_worker(self):
        """Main automation worker thread"""
        while self.is_running:
            try:
                # Run scheduled automations
                self.scheduler.run_pending()
                
                # Process event-based automations
                self.process_event_based_automations()
                
                # Process condition-based automations
                self.process_condition_based_automations()
                
                # Process ML prediction-based automations
                self.process_ml_prediction_automations()
                
                # Sleep for a short interval
                threading.Event().wait(10)  # 10 second intervals
                
            except Exception as e:
                frappe.log_error(f"Error in automation worker: {str(e)}")
                threading.Event().wait(30)  # Wait longer on error
    
    def schedule_time_based_automations(self):
        """Schedule time-based automation rules"""
        try:
            time_based_rules = [rule for rule in self.automation_rules 
                              if rule.trigger_type == AutomationTriggerType.TIME_BASED]
            
            for rule in time_based_rules:
                trigger_conditions = rule.trigger_conditions
                schedule_type = trigger_conditions.get("schedule_type", "daily")
                schedule_time = trigger_conditions.get("schedule_time", "09:00")
                
                if schedule_type == "daily":
                    self.scheduler.every().day.at(schedule_time).do(
                        self.execute_automation_rule, rule
                    )
                elif schedule_type == "weekly":
                    day_of_week = trigger_conditions.get("day_of_week", "monday")
                    getattr(self.scheduler.every(), day_of_week).at(schedule_time).do(
                        self.execute_automation_rule, rule
                    )
                elif schedule_type == "monthly":
                    # For monthly, we'll check on the first day of each month
                    self.scheduler.every().day.at(schedule_time).do(
                        self.check_monthly_automation, rule
                    )
                elif schedule_type == "hourly":
                    self.scheduler.every().hour.do(
                        self.execute_automation_rule, rule
                    )
                
        except Exception as e:
            frappe.log_error(f"Error scheduling time-based automations: {str(e)}")
    
    def process_event_based_automations(self):
        """Process event-based automation rules"""
        try:
            event_based_rules = [rule for rule in self.automation_rules 
                               if rule.trigger_type == AutomationTriggerType.EVENT_BASED]
            
            # Get recent events that might trigger automations
            recent_events = self.get_recent_automation_events()
            
            for event in recent_events:
                for rule in event_based_rules:
                    if self.check_event_trigger(event, rule):
                        self.execute_automation_rule(rule, event_context=event)
                        
        except Exception as e:
            frappe.log_error(f"Error processing event-based automations: {str(e)}")
    
    def process_condition_based_automations(self):
        """Process condition-based automation rules"""
        try:
            condition_based_rules = [rule for rule in self.automation_rules 
                                   if rule.trigger_type == AutomationTriggerType.CONDITION_BASED]
            
            for rule in condition_based_rules:
                if self.evaluate_conditions(rule.trigger_conditions):
                    self.execute_automation_rule(rule)
                    
        except Exception as e:
            frappe.log_error(f"Error processing condition-based automations: {str(e)}")
    
    def process_ml_prediction_automations(self):
        """Process ML prediction-based automation rules"""
        try:
            if not self.config["predictive_assignment_enabled"]:
                return
            
            ml_based_rules = [rule for rule in self.automation_rules 
                            if rule.trigger_type == AutomationTriggerType.ML_PREDICTION]
            
            for rule in ml_based_rules:
                predictions = self.get_ml_predictions(rule.trigger_conditions)
                if predictions and self.should_trigger_ml_automation(predictions, rule):
                    self.execute_automation_rule(rule, ml_context=predictions)
                    
        except Exception as e:
            frappe.log_error(f"Error processing ML prediction automations: {str(e)}")
    
    def execute_automation_rule(self, rule: AutomationRule, event_context: Dict = None, ml_context: Dict = None):
        """Execute a specific automation rule"""
        try:
            execution_start = datetime.now()
            
            # Log execution attempt
            self.log_automation_execution(rule.id, "started", execution_start)
            
            # Execute each action in the rule
            action_results = []
            for action in rule.actions:
                try:
                    result = self.execute_automation_action(
                        action, 
                        rule, 
                        event_context=event_context, 
                        ml_context=ml_context
                    )
                    action_results.append(result)
                except Exception as e:
                    action_results.append({
                        "success": False,
                        "error": str(e),
                        "action": action
                    })
            
            # Calculate success rate
            successful_actions = sum(1 for result in action_results if result.get("success"))
            success_rate = (successful_actions / len(action_results)) * 100 if action_results else 0
            
            # Update rule statistics
            self.update_rule_statistics(rule.id, success_rate)
            
            # Log execution completion
            execution_end = datetime.now()
            execution_duration = (execution_end - execution_start).total_seconds()
            
            self.log_automation_execution(
                rule.id, 
                "completed", 
                execution_end, 
                duration=execution_duration,
                success_rate=success_rate,
                action_results=action_results
            )
            
            return {
                "success": success_rate > 50,  # Consider successful if >50% actions succeeded
                "rule_id": rule.id,
                "execution_duration": execution_duration,
                "success_rate": success_rate,
                "action_results": action_results
            }
            
        except Exception as e:
            frappe.log_error(f"Error executing automation rule {rule.id}: {str(e)}")
            self.log_automation_execution(rule.id, "failed", datetime.now(), error=str(e))
            return {
                "success": False,
                "rule_id": rule.id,
                "error": str(e)
            }
    
    def execute_automation_action(self, action: Dict[str, Any], rule: AutomationRule, 
                                event_context: Dict = None, ml_context: Dict = None) -> Dict[str, Any]:
        """Execute a specific automation action"""
        try:
            action_type = AutomationActionType(action.get("type"))
            action_params = action.get("parameters", {})
            
            if action_type == AutomationActionType.SEND_MESSAGE:
                return self.execute_send_message_action(action_params, event_context, ml_context)
            elif action_type == AutomationActionType.ASSIGN_AGENT:
                return self.execute_assign_agent_action(action_params, event_context, ml_context)
            elif action_type == AutomationActionType.UPDATE_STATUS:
                return self.execute_update_status_action(action_params, event_context, ml_context)
            elif action_type == AutomationActionType.CREATE_TASK:
                return self.execute_create_task_action(action_params, event_context, ml_context)
            elif action_type == AutomationActionType.ESCALATE:
                return self.execute_escalate_action(action_params, event_context, ml_context)
            elif action_type == AutomationActionType.GENERATE_REPORT:
                return self.execute_generate_report_action(action_params, event_context, ml_context)
            elif action_type == AutomationActionType.SYNC_DATA:
                return self.execute_sync_data_action(action_params, event_context, ml_context)
            elif action_type == AutomationActionType.COMPLIANCE_CHECK:
                return self.execute_compliance_check_action(action_params, event_context, ml_context)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action type: {action_type}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "action": action
            }
    
    def intelligent_conversation_routing(self, conversation_id: str) -> Dict[str, Any]:
        """Intelligently route conversations using ML and business rules"""
        try:
            if not self.config["intelligent_routing_enabled"]:
                return {"success": False, "error": "Intelligent routing disabled"}
            
            # Get conversation details
            conversation = frappe.get_doc("Omnichannel Conversation", conversation_id)
            
            # Analyze conversation content
            conversation_analysis = self.analyze_conversation_content(conversation)
            
            # Get agent availability and skills
            available_agents = self.get_available_agents_with_skills()
            
            # Use ML to predict best agent match
            if self.config["predictive_assignment_enabled"]:
                ml_recommendation = self.predict_best_agent_match(
                    conversation_analysis, 
                    available_agents
                )
            else:
                ml_recommendation = None
            
            # Apply business rules
            business_rule_assignment = self.apply_routing_business_rules(
                conversation, 
                conversation_analysis, 
                available_agents
            )
            
            # Combine ML and business rule recommendations
            final_assignment = self.combine_routing_recommendations(
                ml_recommendation, 
                business_rule_assignment, 
                available_agents
            )
            
            if final_assignment:
                # Assign conversation to agent
                conversation.assigned_agent = final_assignment["agent_id"]
                conversation.assignment_reason = final_assignment["reason"]
                conversation.assignment_confidence = final_assignment["confidence"]
                conversation.save()
                
                # Log routing decision
                self.log_routing_decision(conversation_id, final_assignment)
                
                return {
                    "success": True,
                    "assigned_agent": final_assignment["agent_id"],
                    "assignment_reason": final_assignment["reason"],
                    "confidence": final_assignment["confidence"]
                }
            else:
                return {
                    "success": False,
                    "error": "No suitable agent found",
                    "fallback_action": "queue_for_manual_assignment"
                }
                
        except Exception as e:
            frappe.log_error(f"Error in intelligent conversation routing: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def auto_escalation_system(self, conversation_id: str) -> Dict[str, Any]:
        """Automatically escalate conversations based on predefined criteria"""
        try:
            if not self.config["auto_escalation_enabled"]:
                return {"success": False, "error": "Auto escalation disabled"}

            conversation = frappe.get_doc("Omnichannel Conversation", conversation_id)

            # Check escalation criteria
            escalation_triggers = self.check_escalation_triggers(conversation)

            if escalation_triggers:
                # Determine escalation level and target
                escalation_plan = self.determine_escalation_plan(conversation, escalation_triggers)

                # Execute escalation
                escalation_result = self.execute_escalation(conversation, escalation_plan)

                return {
                    "success": True,
                    "escalated": True,
                    "escalation_level": escalation_plan["level"],
                    "escalation_target": escalation_plan["target"],
                    "escalation_reason": escalation_triggers,
                    "escalation_result": escalation_result
                }
            else:
                return {
                    "success": True,
                    "escalated": False,
                    "message": "No escalation criteria met"
                }

        except Exception as e:
            frappe.log_error(f"Error in auto escalation system: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def compliance_monitoring_system(self) -> Dict[str, Any]:
        """Monitor system compliance and generate alerts"""
        try:
            if not self.config["compliance_monitoring_enabled"]:
                return {"success": False, "error": "Compliance monitoring disabled"}

            compliance_checks = [
                self.check_response_time_compliance(),
                self.check_data_retention_compliance(),
                self.check_security_compliance(),
                self.check_accessibility_compliance(),
                self.check_audit_trail_compliance(),
                self.check_privacy_compliance()
            ]

            # Aggregate compliance results
            total_checks = len(compliance_checks)
            passed_checks = sum(1 for check in compliance_checks if check.get("compliant"))
            compliance_score = (passed_checks / total_checks) * 100

            # Identify critical issues
            critical_issues = [check for check in compliance_checks
                             if not check.get("compliant") and check.get("severity") == "critical"]

            # Generate compliance report
            compliance_report = {
                "timestamp": datetime.now().isoformat(),
                "overall_score": compliance_score,
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "failed_checks": total_checks - passed_checks,
                "critical_issues": len(critical_issues),
                "detailed_results": compliance_checks,
                "recommendations": self.generate_compliance_recommendations(compliance_checks)
            }

            # Store compliance report
            self.store_compliance_report(compliance_report)

            # Send alerts for critical issues
            if critical_issues:
                self.send_compliance_alerts(critical_issues)

            return {
                "success": True,
                "compliance_score": compliance_score,
                "critical_issues": len(critical_issues),
                "report": compliance_report
            }

        except Exception as e:
            frappe.log_error(f"Error in compliance monitoring: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def workflow_optimization_engine(self) -> Dict[str, Any]:
        """Analyze and optimize workflows based on performance data"""
        try:
            if not self.config["workflow_optimization_enabled"]:
                return {"success": False, "error": "Workflow optimization disabled"}

            # Analyze current workflow performance
            workflow_analysis = self.analyze_workflow_performance()

            # Identify optimization opportunities
            optimization_opportunities = self.identify_optimization_opportunities(workflow_analysis)

            # Generate optimization recommendations
            recommendations = self.generate_workflow_recommendations(optimization_opportunities)

            # Auto-implement safe optimizations
            auto_implemented = self.auto_implement_safe_optimizations(recommendations)

            # Create optimization report
            optimization_report = {
                "timestamp": datetime.now().isoformat(),
                "workflow_analysis": workflow_analysis,
                "optimization_opportunities": optimization_opportunities,
                "recommendations": recommendations,
                "auto_implemented": auto_implemented,
                "potential_improvements": self.calculate_potential_improvements(recommendations)
            }

            return {
                "success": True,
                "optimizations_found": len(optimization_opportunities),
                "auto_implemented": len(auto_implemented),
                "report": optimization_report
            }

        except Exception as e:
            frappe.log_error(f"Error in workflow optimization: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def predictive_workload_management(self) -> Dict[str, Any]:
        """Predict and manage agent workload proactively"""
        try:
            if not self.config["predictive_assignment_enabled"]:
                return {"success": False, "error": "Predictive workload management disabled"}

            # Get current agent workloads
            current_workloads = self.get_current_agent_workloads()

            # Predict future workload based on historical patterns
            workload_predictions = self.predict_future_workloads()

            # Identify potential bottlenecks
            bottlenecks = self.identify_workload_bottlenecks(current_workloads, workload_predictions)

            # Generate workload balancing recommendations
            balancing_recommendations = self.generate_workload_balancing_recommendations(
                current_workloads,
                workload_predictions,
                bottlenecks
            )

            # Auto-implement workload balancing if safe
            auto_balancing_results = self.auto_implement_workload_balancing(balancing_recommendations)

            return {
                "success": True,
                "current_workloads": current_workloads,
                "predictions": workload_predictions,
                "bottlenecks": bottlenecks,
                "recommendations": balancing_recommendations,
                "auto_balancing_results": auto_balancing_results
            }

        except Exception as e:
            frappe.log_error(f"Error in predictive workload management: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def check_escalation_triggers(self, conversation) -> List[Dict[str, Any]]:
        """Check if conversation meets escalation criteria"""
        triggers = []

        try:
            # Response time trigger
            if conversation.start_time:
                time_since_start = datetime.now() - conversation.start_time
                if time_since_start.total_seconds() > 3600:  # 1 hour
                    triggers.append({
                        "type": "response_time",
                        "severity": "medium",
                        "description": "Conversation open for over 1 hour"
                    })

            # Message count trigger
            if conversation.message_count and conversation.message_count > 20:
                triggers.append({
                    "type": "message_count",
                    "severity": "medium",
                    "description": "High message count indicates complex issue"
                })

            # Customer sentiment trigger (if available)
            if hasattr(conversation, 'customer_sentiment') and conversation.customer_sentiment == 'negative':
                triggers.append({
                    "type": "customer_sentiment",
                    "severity": "high",
                    "description": "Negative customer sentiment detected"
                })

            # VIP customer trigger
            if hasattr(conversation, 'customer_priority') and conversation.customer_priority == 'VIP':
                triggers.append({
                    "type": "vip_customer",
                    "severity": "high",
                    "description": "VIP customer requires priority handling"
                })

            return triggers

        except Exception as e:
            frappe.log_error(f"Error checking escalation triggers: {str(e)}")
            return []

    def analyze_conversation_content(self, conversation) -> Dict[str, Any]:
        """Analyze conversation content for routing decisions"""
        try:
            # Get conversation messages
            messages = frappe.get_all(
                "Omnichannel Message",
                filters={"conversation_id": conversation.name},
                fields=["message_content", "is_inbound", "timestamp"],
                order_by="timestamp"
            )

            # Combine all message content
            all_content = " ".join([msg.message_content for msg in messages if msg.message_content])

            # Basic keyword analysis
            keywords = self.extract_keywords(all_content)

            # Determine conversation category
            category = self.categorize_conversation(keywords, all_content)

            # Assess complexity
            complexity = self.assess_conversation_complexity(messages, keywords)

            # Detect urgency
            urgency = self.detect_urgency(all_content, keywords)

            return {
                "keywords": keywords,
                "category": category,
                "complexity": complexity,
                "urgency": urgency,
                "message_count": len(messages),
                "content_length": len(all_content),
                "channel": conversation.channel_type
            }

        except Exception as e:
            frappe.log_error(f"Error analyzing conversation content: {str(e)}")
            return {}

    def get_available_agents_with_skills(self) -> List[Dict[str, Any]]:
        """Get available agents with their skills and current workload"""
        try:
            agents = frappe.db.sql("""
                SELECT
                    ap.user,
                    ap.full_name,
                    ap.skills,
                    ap.max_concurrent_conversations,
                    COUNT(oc.name) as current_conversations,
                    ap.availability_status,
                    ap.expertise_areas
                FROM `tabAgent Profile` ap
                LEFT JOIN `tabOmnichannel Conversation` oc ON ap.user = oc.assigned_agent
                    AND oc.conversation_status = 'Open'
                WHERE ap.availability_status = 'Available'
                GROUP BY ap.user, ap.full_name, ap.skills, ap.max_concurrent_conversations,
                         ap.availability_status, ap.expertise_areas
                HAVING current_conversations < ap.max_concurrent_conversations
            """, as_dict=True)

            # Parse skills and expertise areas
            for agent in agents:
                agent["skills_list"] = json.loads(agent.get("skills") or "[]")
                agent["expertise_list"] = json.loads(agent.get("expertise_areas") or "[]")
                agent["capacity_utilization"] = (agent["current_conversations"] /
                                               max(1, agent["max_concurrent_conversations"])) * 100

            return agents

        except Exception as e:
            frappe.log_error(f"Error getting available agents: {str(e)}")
            return []

    def log_automation_execution(self, rule_id: str, status: str, timestamp: datetime,
                                duration: float = None, success_rate: float = None,
                                action_results: List = None, error: str = None):
        """Log automation execution for monitoring and analysis"""
        try:
            log_entry = frappe.get_doc({
                "doctype": "Automation Execution Log",
                "rule_id": rule_id,
                "execution_status": status,
                "execution_timestamp": timestamp,
                "execution_duration": duration,
                "success_rate": success_rate,
                "action_results": json.dumps(action_results) if action_results else None,
                "error_message": error
            })
            log_entry.insert()
            frappe.db.commit()

        except Exception as e:
            frappe.log_error(f"Error logging automation execution: {str(e)}")

    def update_rule_statistics(self, rule_id: str, success_rate: float):
        """Update automation rule statistics"""
        try:
            rule_doc = frappe.get_doc("Automation Rule", rule_id)
            rule_doc.execution_count = (rule_doc.execution_count or 0) + 1
            rule_doc.last_executed = datetime.now()

            # Calculate rolling average success rate
            if rule_doc.success_rate:
                rule_doc.success_rate = (rule_doc.success_rate * 0.8) + (success_rate * 0.2)
            else:
                rule_doc.success_rate = success_rate

            rule_doc.save()
            frappe.db.commit()

        except Exception as e:
            frappe.log_error(f"Error updating rule statistics: {str(e)}")
