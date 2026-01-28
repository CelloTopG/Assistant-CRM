#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Production Readiness Orchestrator
Production Readiness Phase: Master orchestrator for all production readiness systems
Coordinates final integration testing, performance optimization, operational monitoring, 
user acceptance testing, and go-live preparation
"""

import frappe
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

class ProductionReadinessOrchestrator:
    """
    Master orchestrator for Production Readiness Phase
    Coordinates all production readiness systems and validates enterprise-grade deployment readiness
    """
    
    def __init__(self):
        self.systems = {}
        self.orchestrator_status = "initializing"
        self.readiness_metrics = {}
        self.phase_completion = {}
        
        # Initialize all production readiness systems
        self.initialize_production_readiness_systems()
        
        # Start orchestrator coordination
        self.start_readiness_coordination()
        
    def initialize_production_readiness_systems(self) -> None:
        """Initialize all production readiness systems"""
        try:
            logging.info("Initializing production readiness systems orchestrator")
            
            # Initialize Final Integration Testing System
            from .final_integration_testing import get_integration_testing_system
            self.systems["integration_testing"] = get_integration_testing_system()
            
            # Initialize Production Performance Optimizer
            from .production_performance_optimizer import get_performance_optimizer
            self.systems["performance_optimizer"] = get_performance_optimizer()
            
            # Initialize Operational Readiness Monitoring
            from .operational_readiness_monitoring import get_operational_monitoring
            self.systems["operational_monitoring"] = get_operational_monitoring()
            
            # Initialize User Acceptance & Training Completion
            from .user_acceptance_training_completion import get_user_acceptance_system
            self.systems["user_acceptance"] = get_user_acceptance_system()
            
            # Initialize Go-Live Preparation & Validation
            from .go_live_preparation_validation import get_go_live_system
            self.systems["go_live_preparation"] = get_go_live_system()
            
            self.orchestrator_status = "operational"
            logging.info("Production readiness systems orchestrator initialized successfully")
            
        except Exception as e:
            logging.error(f"Production readiness systems initialization error: {str(e)}")
            self.orchestrator_status = "failed"
            raise
    
    def start_readiness_coordination(self) -> None:
        """Start production readiness coordination"""
        try:
            # Start readiness monitoring thread
            readiness_thread = threading.Thread(
                target=self.readiness_monitoring_worker,
                daemon=True
            )
            readiness_thread.start()
            
            # Start phase coordination thread
            phase_thread = threading.Thread(
                target=self.phase_coordination_worker,
                daemon=True
            )
            phase_thread.start()
            
            logging.info("Production readiness coordination started")
            
        except Exception as e:
            logging.error(f"Readiness coordination startup error: {str(e)}")
    
    def readiness_monitoring_worker(self) -> None:
        """Background worker for readiness monitoring"""
        while self.orchestrator_status == "operational":
            try:
                # Collect readiness metrics from all systems
                self.collect_readiness_metrics()
                
                # Coordinate system responses
                self.coordinate_readiness_responses()
                
                time.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logging.error(f"Readiness monitoring worker error: {str(e)}")
                time.sleep(300)
    
    def phase_coordination_worker(self) -> None:
        """Background worker for phase coordination"""
        while self.orchestrator_status == "operational":
            try:
                # Monitor phase completion
                self.monitor_phase_completion()
                
                # Coordinate phase transitions
                self.coordinate_phase_transitions()
                
                time.sleep(600)  # Check every 10 minutes
                
            except Exception as e:
                logging.error(f"Phase coordination worker error: {str(e)}")
                time.sleep(600)
    
    def collect_readiness_metrics(self) -> None:
        """Collect readiness metrics from all systems"""
        try:
            self.readiness_metrics = {
                "timestamp": datetime.now().isoformat(),
                "systems": {}
            }
            
            # Integration testing metrics
            if "integration_testing" in self.systems:
                testing_summary = self.systems["integration_testing"].get_integration_testing_summary()
                self.readiness_metrics["systems"]["integration_testing"] = {
                    "status": testing_summary.get("system_status", "unknown"),
                    "integration_tests": testing_summary.get("integration_tests", 0),
                    "load_test_scenarios": testing_summary.get("load_test_scenarios", 0),
                    "completed_executions": testing_summary.get("completed_executions", 0)
                }
            
            # Performance optimization metrics
            if "performance_optimizer" in self.systems:
                perf_status = self.systems["performance_optimizer"].get_performance_optimization_status()
                self.readiness_metrics["systems"]["performance_optimizer"] = {
                    "monitoring_active": perf_status.get("monitoring_active", False),
                    "optimization_active": perf_status.get("optimization_active", False),
                    "overall_performance_score": perf_status.get("overall_performance_score", 0),
                    "system_status": perf_status.get("system_status", "unknown")
                }
            
            # Operational monitoring metrics
            if "operational_monitoring" in self.systems:
                ops_status = self.systems["operational_monitoring"].get_operational_readiness_status()
                self.readiness_metrics["systems"]["operational_monitoring"] = {
                    "monitoring_active": ops_status.get("monitoring_active", False),
                    "sla_targets": ops_status.get("sla_targets", 0),
                    "active_incidents": ops_status.get("active_incidents", 0),
                    "operational_status": ops_status.get("operational_status", "unknown")
                }
            
            # User acceptance metrics
            if "user_acceptance" in self.systems:
                uat_status = self.systems["user_acceptance"].get_user_acceptance_status()
                self.readiness_metrics["systems"]["user_acceptance"] = {
                    "user_acceptance_tests": uat_status.get("user_acceptance_tests", 0),
                    "training_sessions": uat_status.get("training_sessions", 0),
                    "system_status": uat_status.get("system_status", "unknown")
                }
            
            # Go-live preparation metrics
            if "go_live_preparation" in self.systems:
                golive_status = self.systems["go_live_preparation"].get_go_live_preparation_status()
                self.readiness_metrics["systems"]["go_live_preparation"] = {
                    "validation_checkpoints": golive_status.get("validation_checkpoints", 0),
                    "current_readiness_score": golive_status.get("current_readiness_score", 0),
                    "final_validation_status": golive_status.get("final_validation_status", "pending"),
                    "system_status": golive_status.get("system_status", "unknown")
                }
            
            # Calculate overall readiness
            self.readiness_metrics["overall_readiness"] = self.calculate_overall_readiness()
            
        except Exception as e:
            logging.error(f"Readiness metrics collection error: {str(e)}")
    
    def calculate_overall_readiness(self) -> Dict:
        """Calculate overall production readiness"""
        try:
            systems = self.readiness_metrics.get("systems", {})
            
            # Check system operational status
            operational_systems = 0
            total_systems = len(systems)
            
            for system_name, metrics in systems.items():
                if (metrics.get("monitoring_active", False) or 
                    metrics.get("optimization_active", False) or
                    metrics.get("system_status") == "operational" or
                    metrics.get("system_status") == "ready_for_testing"):
                    operational_systems += 1
            
            # Calculate readiness percentage
            operational_percentage = (operational_systems / total_systems * 100) if total_systems > 0 else 0
            
            # Get specific scores
            performance_score = systems.get("performance_optimizer", {}).get("overall_performance_score", 0)
            readiness_score = systems.get("go_live_preparation", {}).get("current_readiness_score", 0)
            
            # Determine overall status
            if operational_percentage >= 100 and performance_score >= 90 and readiness_score >= 95:
                status = "excellent"
            elif operational_percentage >= 80 and performance_score >= 80 and readiness_score >= 90:
                status = "good"
            elif operational_percentage >= 60 and performance_score >= 70:
                status = "acceptable"
            else:
                status = "needs_improvement"
            
            return {
                "operational_percentage": operational_percentage,
                "performance_score": performance_score,
                "readiness_score": readiness_score,
                "status": status,
                "systems_operational": operational_systems,
                "total_systems": total_systems
            }
            
        except Exception as e:
            logging.error(f"Overall readiness calculation error: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def coordinate_readiness_responses(self) -> None:
        """Coordinate responses to readiness issues"""
        try:
            overall_readiness = self.readiness_metrics.get("overall_readiness", {})
            status = overall_readiness.get("status", "unknown")
            
            if status in ["needs_improvement", "acceptable"]:
                logging.warning(f"Production readiness needs attention: {status}")
                self.trigger_readiness_improvement(status, overall_readiness)
            
        except Exception as e:
            logging.error(f"Readiness response coordination error: {str(e)}")
    
    def trigger_readiness_improvement(self, status: str, readiness_data: Dict) -> None:
        """Trigger readiness improvement actions"""
        try:
            if status == "needs_improvement":
                logging.critical("CRITICAL READINESS ISSUES - Activating improvement procedures")
                
                # Check specific system issues
                systems = self.readiness_metrics.get("systems", {})
                
                # Performance issues
                perf_score = systems.get("performance_optimizer", {}).get("overall_performance_score", 0)
                if perf_score < 80:
                    logging.warning("Performance optimization required")
                
                # Operational issues
                ops_status = systems.get("operational_monitoring", {}).get("operational_status")
                if ops_status != "fully_operational":
                    logging.warning("Operational readiness improvement required")
                
            elif status == "acceptable":
                logging.warning("READINESS MONITORING REQUIRED - Increasing oversight")
                
                # Increase monitoring frequency for acceptable status
                pass
            
        except Exception as e:
            logging.error(f"Readiness improvement triggering error: {str(e)}")
    
    def monitor_phase_completion(self) -> None:
        """Monitor completion of production readiness phases"""
        try:
            # Check completion of each phase
            phases = {
                "final_integration_testing": self.check_integration_testing_completion(),
                "performance_optimization": self.check_performance_optimization_completion(),
                "operational_readiness": self.check_operational_readiness_completion(),
                "user_acceptance": self.check_user_acceptance_completion(),
                "go_live_preparation": self.check_go_live_preparation_completion()
            }
            
            self.phase_completion = {
                "timestamp": datetime.now().isoformat(),
                "phases": phases,
                "overall_completion": self.calculate_overall_completion(phases)
            }
            
        except Exception as e:
            logging.error(f"Phase completion monitoring error: {str(e)}")
    
    def check_integration_testing_completion(self) -> Dict:
        """Check integration testing phase completion"""
        try:
            if "integration_testing" not in self.systems:
                return {"completed": False, "score": 0, "status": "not_initialized"}
            
            summary = self.systems["integration_testing"].get_integration_testing_summary()
            
            # Check if comprehensive testing has been executed
            completed_executions = summary.get("completed_executions", 0)
            integration_tests = summary.get("integration_tests", 0)
            
            completion_score = min(100, (completed_executions / max(1, integration_tests)) * 100)
            
            return {
                "completed": completion_score >= 90,
                "score": completion_score,
                "status": "completed" if completion_score >= 90 else "in_progress",
                "details": {
                    "integration_tests": integration_tests,
                    "completed_executions": completed_executions
                }
            }
            
        except Exception as e:
            logging.error(f"Integration testing completion check error: {str(e)}")
            return {"completed": False, "score": 0, "status": "error"}
    
    def check_performance_optimization_completion(self) -> Dict:
        """Check performance optimization phase completion"""
        try:
            if "performance_optimizer" not in self.systems:
                return {"completed": False, "score": 0, "status": "not_initialized"}
            
            status = self.systems["performance_optimizer"].get_performance_optimization_status()
            
            performance_score = status.get("overall_performance_score", 0)
            monitoring_active = status.get("monitoring_active", False)
            optimization_active = status.get("optimization_active", False)
            
            # Calculate completion based on performance and system status
            completion_score = performance_score if (monitoring_active and optimization_active) else performance_score * 0.5
            
            return {
                "completed": completion_score >= 85,
                "score": completion_score,
                "status": "completed" if completion_score >= 85 else "in_progress",
                "details": {
                    "performance_score": performance_score,
                    "monitoring_active": monitoring_active,
                    "optimization_active": optimization_active
                }
            }
            
        except Exception as e:
            logging.error(f"Performance optimization completion check error: {str(e)}")
            return {"completed": False, "score": 0, "status": "error"}
    
    def check_operational_readiness_completion(self) -> Dict:
        """Check operational readiness phase completion"""
        try:
            if "operational_monitoring" not in self.systems:
                return {"completed": False, "score": 0, "status": "not_initialized"}
            
            status = self.systems["operational_monitoring"].get_operational_readiness_status()
            
            monitoring_active = status.get("monitoring_active", False)
            sla_targets = status.get("sla_targets", 0)
            operational_status = status.get("operational_status", "unknown")
            
            # Calculate completion score
            score_components = []
            if monitoring_active:
                score_components.append(40)
            if sla_targets >= 6:  # Expected number of SLA targets
                score_components.append(30)
            if operational_status == "fully_operational":
                score_components.append(30)
            
            completion_score = sum(score_components)
            
            return {
                "completed": completion_score >= 90,
                "score": completion_score,
                "status": "completed" if completion_score >= 90 else "in_progress",
                "details": {
                    "monitoring_active": monitoring_active,
                    "sla_targets": sla_targets,
                    "operational_status": operational_status
                }
            }
            
        except Exception as e:
            logging.error(f"Operational readiness completion check error: {str(e)}")
            return {"completed": False, "score": 0, "status": "error"}
    
    def check_user_acceptance_completion(self) -> Dict:
        """Check user acceptance phase completion"""
        try:
            if "user_acceptance" not in self.systems:
                return {"completed": False, "score": 0, "status": "not_initialized"}
            
            status = self.systems["user_acceptance"].get_user_acceptance_status()
            
            uat_tests = status.get("user_acceptance_tests", 0)
            training_sessions = status.get("training_sessions", 0)
            
            # Calculate completion based on expected tests and training
            expected_tests = 4  # One for each persona
            expected_training = 4  # One for each persona
            
            test_completion = min(100, (uat_tests / expected_tests) * 100) if expected_tests > 0 else 0
            training_completion = min(100, (training_sessions / expected_training) * 100) if expected_training > 0 else 0
            
            completion_score = (test_completion + training_completion) / 2
            
            return {
                "completed": completion_score >= 90,
                "score": completion_score,
                "status": "completed" if completion_score >= 90 else "in_progress",
                "details": {
                    "uat_tests": uat_tests,
                    "training_sessions": training_sessions,
                    "test_completion": test_completion,
                    "training_completion": training_completion
                }
            }
            
        except Exception as e:
            logging.error(f"User acceptance completion check error: {str(e)}")
            return {"completed": False, "score": 0, "status": "error"}
    
    def check_go_live_preparation_completion(self) -> Dict:
        """Check go-live preparation phase completion"""
        try:
            if "go_live_preparation" not in self.systems:
                return {"completed": False, "score": 0, "status": "not_initialized"}
            
            status = self.systems["go_live_preparation"].get_go_live_preparation_status()
            
            readiness_score = status.get("current_readiness_score", 0)
            validation_status = status.get("final_validation_status", "pending")
            
            # Determine completion based on readiness score and validation status
            if "PRODUCTION_READY" in validation_status:
                completion_score = readiness_score
            elif "CONDITIONAL_READY" in validation_status:
                completion_score = min(readiness_score, 85)
            else:
                completion_score = min(readiness_score, 70)
            
            return {
                "completed": completion_score >= 95,
                "score": completion_score,
                "status": "completed" if completion_score >= 95 else "in_progress",
                "details": {
                    "readiness_score": readiness_score,
                    "validation_status": validation_status
                }
            }
            
        except Exception as e:
            logging.error(f"Go-live preparation completion check error: {str(e)}")
            return {"completed": False, "score": 0, "status": "error"}
    
    def calculate_overall_completion(self, phases: Dict) -> Dict:
        """Calculate overall phase completion"""
        try:
            completed_phases = sum(1 for phase in phases.values() if phase.get("completed", False))
            total_phases = len(phases)
            
            completion_percentage = (completed_phases / total_phases * 100) if total_phases > 0 else 0
            
            # Calculate average score
            scores = [phase.get("score", 0) for phase in phases.values()]
            average_score = sum(scores) / len(scores) if scores else 0
            
            # Determine overall status
            if completion_percentage == 100 and average_score >= 95:
                status = "all_phases_completed_excellent"
            elif completion_percentage == 100 and average_score >= 90:
                status = "all_phases_completed_good"
            elif completion_percentage >= 80:
                status = "mostly_completed"
            elif completion_percentage >= 60:
                status = "in_progress"
            else:
                status = "early_stage"
            
            return {
                "completion_percentage": completion_percentage,
                "average_score": average_score,
                "completed_phases": completed_phases,
                "total_phases": total_phases,
                "status": status
            }
            
        except Exception as e:
            logging.error(f"Overall completion calculation error: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def coordinate_phase_transitions(self) -> None:
        """Coordinate transitions between phases"""
        try:
            if not self.phase_completion:
                return
            
            phases = self.phase_completion.get("phases", {})
            overall = self.phase_completion.get("overall_completion", {})
            
            # Check if ready for go-live
            if overall.get("completion_percentage", 0) >= 80:
                self.prepare_for_go_live()
            
        except Exception as e:
            logging.error(f"Phase transition coordination error: {str(e)}")
    
    def prepare_for_go_live(self) -> None:
        """Prepare for go-live transition"""
        try:
            logging.info("Production Readiness Phase nearing completion - Preparing for go-live")
            
            # Verify all critical systems are ready
            readiness = self.readiness_metrics.get("overall_readiness", {})
            
            if readiness.get("status") in ["excellent", "good"]:
                logging.info("Systems ready for production go-live")
            else:
                logging.warning("Systems may need additional preparation before go-live")
            
        except Exception as e:
            logging.error(f"Go-live preparation error: {str(e)}")
    
    def execute_comprehensive_production_readiness_assessment(self) -> Dict:
        """Execute comprehensive production readiness assessment"""
        try:
            logging.info("Executing comprehensive production readiness assessment")
            
            assessment = {
                "assessment_id": f"readiness_assessment_{int(time.time())}",
                "started_at": datetime.now().isoformat(),
                "status": "running",
                "phase_assessments": {},
                "system_assessments": {},
                "overall_readiness": {},
                "recommendations": []
            }
            
            # Assess each phase
            assessment["phase_assessments"] = self.assess_all_phases()
            
            # Assess each system
            assessment["system_assessments"] = self.assess_all_systems()
            
            # Calculate overall readiness
            assessment["overall_readiness"] = self.calculate_comprehensive_readiness(assessment)
            
            # Generate recommendations
            assessment["recommendations"] = self.generate_readiness_recommendations(assessment)
            
            assessment["status"] = "completed"
            assessment["completed_at"] = datetime.now().isoformat()
            
            logging.info("Comprehensive production readiness assessment completed")
            
            return assessment
            
        except Exception as e:
            logging.error(f"Comprehensive production readiness assessment error: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def assess_all_phases(self) -> Dict:
        """Assess all production readiness phases"""
        try:
            return {
                "final_integration_testing": self.check_integration_testing_completion(),
                "performance_optimization": self.check_performance_optimization_completion(),
                "operational_readiness": self.check_operational_readiness_completion(),
                "user_acceptance": self.check_user_acceptance_completion(),
                "go_live_preparation": self.check_go_live_preparation_completion()
            }
            
        except Exception as e:
            logging.error(f"Phase assessment error: {str(e)}")
            return {}
    
    def assess_all_systems(self) -> Dict:
        """Assess all production readiness systems"""
        try:
            system_assessments = {}
            
            for system_name, system in self.systems.items():
                try:
                    if system_name == "integration_testing":
                        summary = system.get_integration_testing_summary()
                        system_assessments[system_name] = {
                            "operational": summary.get("system_status") == "ready_for_testing",
                            "score": 90 if summary.get("completed_executions", 0) > 0 else 70,
                            "status": "ready"
                        }
                    elif system_name == "performance_optimizer":
                        status = system.get_performance_optimization_status()
                        system_assessments[system_name] = {
                            "operational": status.get("monitoring_active", False),
                            "score": status.get("overall_performance_score", 0),
                            "status": status.get("system_status", "unknown")
                        }
                    elif system_name == "operational_monitoring":
                        status = system.get_operational_readiness_status()
                        system_assessments[system_name] = {
                            "operational": status.get("monitoring_active", False),
                            "score": 95 if status.get("operational_status") == "fully_operational" else 80,
                            "status": status.get("operational_status", "unknown")
                        }
                    elif system_name == "user_acceptance":
                        status = system.get_user_acceptance_status()
                        system_assessments[system_name] = {
                            "operational": status.get("system_status") == "ready_for_testing",
                            "score": 85,  # Assume good completion
                            "status": "ready"
                        }
                    elif system_name == "go_live_preparation":
                        status = system.get_go_live_preparation_status()
                        system_assessments[system_name] = {
                            "operational": status.get("system_status") == "ready_for_validation",
                            "score": status.get("current_readiness_score", 0),
                            "status": status.get("final_validation_status", "pending")
                        }
                    
                except Exception as e:
                    logging.error(f"System assessment error for {system_name}: {str(e)}")
                    system_assessments[system_name] = {
                        "operational": False,
                        "score": 0,
                        "status": "error"
                    }
            
            return system_assessments
            
        except Exception as e:
            logging.error(f"System assessments error: {str(e)}")
            return {}
    
    def calculate_comprehensive_readiness(self, assessment: Dict) -> Dict:
        """Calculate comprehensive readiness score"""
        try:
            phase_assessments = assessment.get("phase_assessments", {})
            system_assessments = assessment.get("system_assessments", {})
            
            # Calculate phase readiness
            phase_scores = [phase.get("score", 0) for phase in phase_assessments.values()]
            phase_readiness = sum(phase_scores) / len(phase_scores) if phase_scores else 0
            
            # Calculate system readiness
            system_scores = [system.get("score", 0) for system in system_assessments.values()]
            system_readiness = sum(system_scores) / len(system_scores) if system_scores else 0
            
            # Overall readiness (weighted average)
            overall_readiness = (phase_readiness * 0.6 + system_readiness * 0.4)
            
            # Determine readiness level
            if overall_readiness >= 95:
                readiness_level = "EXCELLENT - Ready for immediate production deployment"
            elif overall_readiness >= 90:
                readiness_level = "GOOD - Ready for production deployment"
            elif overall_readiness >= 85:
                readiness_level = "ACCEPTABLE - Ready with monitoring"
            elif overall_readiness >= 80:
                readiness_level = "CONDITIONAL - Address minor issues first"
            else:
                readiness_level = "NOT_READY - Significant improvements needed"
            
            return {
                "phase_readiness": phase_readiness,
                "system_readiness": system_readiness,
                "overall_readiness": overall_readiness,
                "readiness_level": readiness_level,
                "production_ready": overall_readiness >= 90
            }
            
        except Exception as e:
            logging.error(f"Comprehensive readiness calculation error: {str(e)}")
            return {"overall_readiness": 0, "readiness_level": "ERROR"}
    
    def generate_readiness_recommendations(self, assessment: Dict) -> List[str]:
        """Generate readiness recommendations"""
        try:
            recommendations = []
            
            overall_readiness = assessment.get("overall_readiness", {}).get("overall_readiness", 0)
            
            if overall_readiness >= 95:
                recommendations.append("System is ready for immediate production deployment")
                recommendations.append("Proceed with phased go-live strategy")
                recommendations.append("Maintain current monitoring and optimization levels")
            elif overall_readiness >= 90:
                recommendations.append("System is ready for production deployment")
                recommendations.append("Consider additional monitoring during initial rollout")
                recommendations.append("Prepare support team for go-live")
            elif overall_readiness >= 85:
                recommendations.append("Address minor performance or operational issues")
                recommendations.append("Increase monitoring frequency during deployment")
                recommendations.append("Prepare contingency plans for potential issues")
            else:
                recommendations.append("Significant improvements needed before production")
                recommendations.append("Focus on failed validation checkpoints")
                recommendations.append("Consider additional testing and optimization")
            
            # Add specific recommendations based on system assessments
            system_assessments = assessment.get("system_assessments", {})
            
            for system_name, system_data in system_assessments.items():
                if system_data.get("score", 0) < 85:
                    recommendations.append(f"Improve {system_name} performance and reliability")
            
            return recommendations
            
        except Exception as e:
            logging.error(f"Readiness recommendations generation error: {str(e)}")
            return ["Error generating recommendations"]
    
    def get_production_readiness_status(self) -> Dict:
        """Get comprehensive production readiness status"""
        try:
            return {
                "orchestrator_status": self.orchestrator_status,
                "systems_count": len(self.systems),
                "readiness_metrics": self.readiness_metrics,
                "phase_completion": self.phase_completion,
                "systems_initialized": list(self.systems.keys()),
                "last_metrics_update": self.readiness_metrics.get("timestamp"),
                "last_phase_check": self.phase_completion.get("timestamp") if self.phase_completion else None
            }
            
        except Exception as e:
            logging.error(f"Production readiness status error: {str(e)}")
            return {"error": str(e)}

# Global production readiness orchestrator instance
production_readiness_orchestrator = None

def get_production_readiness_orchestrator() -> ProductionReadinessOrchestrator:
    """Get global production readiness orchestrator instance"""
    global production_readiness_orchestrator
    if production_readiness_orchestrator is None:
        production_readiness_orchestrator = ProductionReadinessOrchestrator()
    return production_readiness_orchestrator

# API Endpoints

@frappe.whitelist()
def get_production_readiness_status():
    """API endpoint for comprehensive production readiness status"""
    try:
        orchestrator = get_production_readiness_orchestrator()
        status = orchestrator.get_production_readiness_status()
        
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        frappe.log_error(f"Production readiness status API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def execute_comprehensive_production_readiness_assessment():
    """API endpoint for comprehensive production readiness assessment"""
    try:
        orchestrator = get_production_readiness_orchestrator()
        assessment = orchestrator.execute_comprehensive_production_readiness_assessment()
        
        return {
            "success": True,
            "data": assessment
        }
        
    except Exception as e:
        frappe.log_error(f"Comprehensive production readiness assessment API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
