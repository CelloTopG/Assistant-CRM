#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Monitoring & Analytics System
Production Deployment Phase: Real-time performance dashboards and analytics
Implements comprehensive monitoring, alerting, and user interaction analytics
"""

import frappe
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import statistics
import redis
import logging
from collections import defaultdict, deque

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    timestamp: datetime
    metric_type: str
    value: float
    component: str
    user_type: str
    session_id: str
    additional_data: Dict

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    metric_type: str
    threshold: float
    comparison: str  # 'gt', 'lt', 'eq'
    duration: int  # seconds
    severity: str  # 'critical', 'warning', 'info'
    enabled: bool

class MonitoringAnalyticsSystem:
    """
    Comprehensive monitoring and analytics system for production deployment
    Provides real-time dashboards, alerting, and user interaction analytics
    """
    
    def __init__(self):
        self.metrics_buffer = deque(maxlen=10000)  # In-memory buffer
        self.alert_rules = self.load_alert_rules()
        self.active_alerts = {}
        self.analytics_cache = {}
        self.monitoring_active = False
        
        # Performance tracking
        self.response_times = defaultdict(list)
        self.cache_stats = defaultdict(int)
        self.user_interactions = defaultdict(list)
        self.error_counts = defaultdict(int)
        
        # SLA tracking
        self.sla_targets = self.load_sla_targets()
        self.sla_metrics = defaultdict(list)
        
        # Start monitoring workers
        self.start_monitoring_workers()
    
    def start_monitoring_workers(self) -> None:
        """Start background monitoring workers"""
        try:
            self.monitoring_active = True
            
            # Start metrics processing worker
            metrics_worker = threading.Thread(
                target=self.metrics_processing_worker,
                daemon=True
            )
            metrics_worker.start()
            
            # Start alerting worker
            alerting_worker = threading.Thread(
                target=self.alerting_worker,
                daemon=True
            )
            alerting_worker.start()
            
            # Start analytics worker
            analytics_worker = threading.Thread(
                target=self.analytics_worker,
                daemon=True
            )
            analytics_worker.start()
            
            logging.info("Monitoring and analytics workers started")
            
        except Exception as e:
            logging.error(f"Monitoring workers startup error: {str(e)}")
            raise
    
    def record_performance_metric(self, metric_type: str, value: float, 
                                component: str, user_type: str = "unknown",
                                session_id: str = "", additional_data: Dict = None) -> None:
        """Record a performance metric"""
        try:
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                metric_type=metric_type,
                value=value,
                component=component,
                user_type=user_type,
                session_id=session_id,
                additional_data=additional_data or {}
            )
            
            # Add to buffer for processing
            self.metrics_buffer.append(metric)
            
            # Update real-time tracking
            self.update_realtime_tracking(metric)
            
        except Exception as e:
            logging.error(f"Metric recording error: {str(e)}")
    
    def update_realtime_tracking(self, metric: PerformanceMetric) -> None:
        """Update real-time tracking data structures"""
        try:
            # Track response times
            if metric.metric_type == "response_time":
                self.response_times[metric.component].append(metric.value)
                # Keep only last 1000 measurements per component
                if len(self.response_times[metric.component]) > 1000:
                    self.response_times[metric.component] = self.response_times[metric.component][-1000:]
            
            # Track cache statistics
            elif metric.metric_type == "cache_hit":
                self.cache_stats["hits"] += 1
            elif metric.metric_type == "cache_miss":
                self.cache_stats["misses"] += 1
            
            # Track user interactions
            elif metric.metric_type == "user_interaction":
                self.user_interactions[metric.user_type].append({
                    "timestamp": metric.timestamp,
                    "component": metric.component,
                    "data": metric.additional_data
                })
                # Keep only last 24 hours per user type
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.user_interactions[metric.user_type] = [
                    interaction for interaction in self.user_interactions[metric.user_type]
                    if interaction["timestamp"] > cutoff_time
                ]
            
            # Track errors
            elif metric.metric_type == "error":
                error_key = f"{metric.component}_{metric.additional_data.get('error_type', 'unknown')}"
                self.error_counts[error_key] += 1
            
        except Exception as e:
            logging.error(f"Real-time tracking update error: {str(e)}")
    
    def metrics_processing_worker(self) -> None:
        """Background worker for processing metrics"""
        while self.monitoring_active:
            try:
                # Process metrics batch
                if self.metrics_buffer:
                    batch_size = min(100, len(self.metrics_buffer))
                    batch = [self.metrics_buffer.popleft() for _ in range(batch_size)]
                    self.process_metrics_batch(batch)
                
                time.sleep(5)  # Process every 5 seconds
                
            except Exception as e:
                logging.error(f"Metrics processing worker error: {str(e)}")
                time.sleep(30)
    
    def process_metrics_batch(self, batch: List[PerformanceMetric]) -> None:
        """Process a batch of metrics"""
        try:
            # Store metrics in Redis for real-time dashboard
            self.store_metrics_in_redis(batch)
            
            # Update SLA tracking
            self.update_sla_tracking(batch)
            
            # Generate analytics insights
            self.generate_analytics_insights(batch)
            
        except Exception as e:
            logging.error(f"Metrics batch processing error: {str(e)}")
    
    def store_metrics_in_redis(self, batch: List[PerformanceMetric]) -> None:
        """Store metrics in Redis for real-time access"""
        try:
            from .production_environment_manager import get_production_environment_manager
            
            manager = get_production_environment_manager()
            if "redis_primary" in manager.connection_pools:
                redis_client = redis.Redis(
                    connection_pool=manager.connection_pools["redis_primary"]["pool"]
                )
                
                for metric in batch:
                    # Store individual metric
                    metric_key = f"wcfcb:metrics:{metric.metric_type}:{metric.component}"
                    metric_data = {
                        "timestamp": metric.timestamp.isoformat(),
                        "value": metric.value,
                        "user_type": metric.user_type,
                        "session_id": metric.session_id,
                        "additional_data": json.dumps(metric.additional_data)
                    }
                    
                    # Store in time series (sorted set)
                    redis_client.zadd(
                        metric_key,
                        {json.dumps(metric_data): time.mktime(metric.timestamp.timetuple())}
                    )
                    
                    # Keep only last 24 hours
                    cutoff_time = time.time() - (24 * 60 * 60)
                    redis_client.zremrangebyscore(metric_key, 0, cutoff_time)
                
                # Update aggregated metrics
                self.update_aggregated_metrics(redis_client, batch)
            
        except Exception as e:
            logging.error(f"Redis metrics storage error: {str(e)}")
    
    def update_aggregated_metrics(self, redis_client, batch: List[PerformanceMetric]) -> None:
        """Update aggregated metrics in Redis"""
        try:
            # Group metrics by type and component
            grouped_metrics = defaultdict(list)
            for metric in batch:
                key = f"{metric.metric_type}:{metric.component}"
                grouped_metrics[key].append(metric.value)
            
            # Calculate and store aggregations
            for key, values in grouped_metrics.items():
                metric_type, component = key.split(":", 1)
                
                aggregations = {
                    "count": len(values),
                    "avg": statistics.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "median": statistics.median(values)
                }
                
                if len(values) > 1:
                    aggregations["stddev"] = statistics.stdev(values)
                
                # Store aggregations
                agg_key = f"wcfcb:aggregated:{metric_type}:{component}"
                redis_client.hmset(agg_key, aggregations)
                redis_client.expire(agg_key, 3600)  # 1 hour TTL
            
        except Exception as e:
            logging.error(f"Aggregated metrics update error: {str(e)}")
    
    def update_sla_tracking(self, batch: List[PerformanceMetric]) -> None:
        """Update SLA tracking metrics"""
        try:
            for metric in batch:
                if metric.metric_type in self.sla_targets:
                    target = self.sla_targets[metric.metric_type]
                    
                    # Check if metric meets SLA
                    meets_sla = self.check_sla_compliance(metric.value, target)
                    
                    # Record SLA metric
                    sla_metric = {
                        "timestamp": metric.timestamp,
                        "metric_type": metric.metric_type,
                        "component": metric.component,
                        "value": metric.value,
                        "target": target["target"],
                        "meets_sla": meets_sla
                    }
                    
                    self.sla_metrics[metric.metric_type].append(sla_metric)
                    
                    # Keep only last 24 hours
                    cutoff_time = datetime.now() - timedelta(hours=24)
                    self.sla_metrics[metric.metric_type] = [
                        m for m in self.sla_metrics[metric.metric_type]
                        if m["timestamp"] > cutoff_time
                    ]
            
        except Exception as e:
            logging.error(f"SLA tracking update error: {str(e)}")
    
    def check_sla_compliance(self, value: float, target: Dict) -> bool:
        """Check if metric value meets SLA target"""
        try:
            target_value = target["target"]
            comparison = target["comparison"]
            
            if comparison == "lt":
                return value < target_value
            elif comparison == "gt":
                return value > target_value
            elif comparison == "eq":
                return abs(value - target_value) < 0.01
            else:
                return False
                
        except Exception as e:
            logging.error(f"SLA compliance check error: {str(e)}")
            return False
    
    def alerting_worker(self) -> None:
        """Background worker for processing alerts"""
        while self.monitoring_active:
            try:
                self.process_alert_rules()
                time.sleep(30)  # Check alerts every 30 seconds
                
            except Exception as e:
                logging.error(f"Alerting worker error: {str(e)}")
                time.sleep(60)
    
    def process_alert_rules(self) -> None:
        """Process alert rules and trigger alerts"""
        try:
            for rule in self.alert_rules:
                if not rule.enabled:
                    continue
                
                # Get recent metrics for this rule
                recent_metrics = self.get_recent_metrics(rule.metric_type, rule.duration)
                
                if recent_metrics:
                    # Check if alert condition is met
                    if self.evaluate_alert_condition(recent_metrics, rule):
                        self.trigger_alert(rule, recent_metrics)
                    else:
                        # Clear alert if it was previously active
                        self.clear_alert(rule.name)
            
        except Exception as e:
            logging.error(f"Alert rules processing error: {str(e)}")
    
    def get_recent_metrics(self, metric_type: str, duration: int) -> List[PerformanceMetric]:
        """Get recent metrics for alert evaluation"""
        try:
            cutoff_time = datetime.now() - timedelta(seconds=duration)
            
            recent_metrics = [
                metric for metric in self.metrics_buffer
                if metric.metric_type == metric_type and metric.timestamp > cutoff_time
            ]
            
            return recent_metrics
            
        except Exception as e:
            logging.error(f"Recent metrics retrieval error: {str(e)}")
            return []
    
    def evaluate_alert_condition(self, metrics: List[PerformanceMetric], rule: AlertRule) -> bool:
        """Evaluate if alert condition is met"""
        try:
            if not metrics:
                return False
            
            # Calculate metric value based on rule
            values = [metric.value for metric in metrics]
            
            if rule.comparison == "avg":
                metric_value = statistics.mean(values)
            elif rule.comparison == "max":
                metric_value = max(values)
            elif rule.comparison == "min":
                metric_value = min(values)
            else:
                metric_value = values[-1]  # Latest value
            
            # Check threshold
            if rule.comparison in ["gt", "avg", "max", "min"]:
                return metric_value > rule.threshold
            elif rule.comparison == "lt":
                return metric_value < rule.threshold
            elif rule.comparison == "eq":
                return abs(metric_value - rule.threshold) < 0.01
            
            return False
            
        except Exception as e:
            logging.error(f"Alert condition evaluation error: {str(e)}")
            return False
    
    def trigger_alert(self, rule: AlertRule, metrics: List[PerformanceMetric]) -> None:
        """Trigger an alert"""
        try:
            alert_id = f"alert_{rule.name}_{int(time.time())}"
            
            alert_data = {
                "id": alert_id,
                "rule_name": rule.name,
                "severity": rule.severity,
                "metric_type": rule.metric_type,
                "threshold": rule.threshold,
                "current_value": statistics.mean([m.value for m in metrics]),
                "triggered_at": datetime.now().isoformat(),
                "metrics_count": len(metrics),
                "status": "active"
            }
            
            # Store active alert
            self.active_alerts[rule.name] = alert_data
            
            # Log alert
            logging.warning(f"Alert triggered: {alert_data}")
            
            # Send alert notification
            self.send_alert_notification(alert_data)
            
        except Exception as e:
            logging.error(f"Alert triggering error: {str(e)}")
    
    def clear_alert(self, rule_name: str) -> None:
        """Clear an active alert"""
        try:
            if rule_name in self.active_alerts:
                alert_data = self.active_alerts[rule_name]
                alert_data["status"] = "cleared"
                alert_data["cleared_at"] = datetime.now().isoformat()
                
                # Log alert clearance
                logging.info(f"Alert cleared: {rule_name}")
                
                # Remove from active alerts
                del self.active_alerts[rule_name]
            
        except Exception as e:
            logging.error(f"Alert clearing error: {str(e)}")
    
    def send_alert_notification(self, alert_data: Dict) -> None:
        """Send alert notification"""
        try:
            # In production, integrate with notification systems
            # (email, SMS, Slack, PagerDuty, etc.)
            
            notification_message = f"""
WCFCB Assistant CRM Alert

Severity: {alert_data['severity'].upper()}
Rule: {alert_data['rule_name']}
Metric: {alert_data['metric_type']}
Threshold: {alert_data['threshold']}
Current Value: {alert_data['current_value']:.2f}
Triggered: {alert_data['triggered_at']}

Please investigate immediately.
            """
            
            logging.warning(f"Alert notification: {notification_message}")
            
        except Exception as e:
            logging.error(f"Alert notification error: {str(e)}")
    
    def analytics_worker(self) -> None:
        """Background worker for analytics processing"""
        while self.monitoring_active:
            try:
                self.generate_analytics_reports()
                time.sleep(300)  # Generate reports every 5 minutes
                
            except Exception as e:
                logging.error(f"Analytics worker error: {str(e)}")
                time.sleep(300)
    
    def generate_analytics_insights(self, batch: List[PerformanceMetric]) -> None:
        """Generate analytics insights from metrics batch"""
        try:
            # User interaction patterns
            user_patterns = self.analyze_user_patterns(batch)
            
            # Performance trends
            performance_trends = self.analyze_performance_trends(batch)
            
            # Component usage analytics
            component_usage = self.analyze_component_usage(batch)
            
            # Store insights in cache
            self.analytics_cache.update({
                "user_patterns": user_patterns,
                "performance_trends": performance_trends,
                "component_usage": component_usage,
                "last_updated": datetime.now().isoformat()
            })
            
        except Exception as e:
            logging.error(f"Analytics insights generation error: {str(e)}")
    
    def analyze_user_patterns(self, batch: List[PerformanceMetric]) -> Dict:
        """Analyze user interaction patterns"""
        try:
            user_metrics = [m for m in batch if m.metric_type == "user_interaction"]
            
            if not user_metrics:
                return {}
            
            # Group by user type
            user_type_counts = defaultdict(int)
            component_usage = defaultdict(int)
            
            for metric in user_metrics:
                user_type_counts[metric.user_type] += 1
                component_usage[metric.component] += 1
            
            return {
                "user_type_distribution": dict(user_type_counts),
                "component_usage": dict(component_usage),
                "total_interactions": len(user_metrics)
            }
            
        except Exception as e:
            logging.error(f"User patterns analysis error: {str(e)}")
            return {}
    
    def analyze_performance_trends(self, batch: List[PerformanceMetric]) -> Dict:
        """Analyze performance trends"""
        try:
            response_time_metrics = [m for m in batch if m.metric_type == "response_time"]
            
            if not response_time_metrics:
                return {}
            
            # Calculate trends by component
            component_trends = {}
            
            for component in set(m.component for m in response_time_metrics):
                component_metrics = [m for m in response_time_metrics if m.component == component]
                values = [m.value for m in component_metrics]
                
                if values:
                    component_trends[component] = {
                        "avg_response_time": statistics.mean(values),
                        "min_response_time": min(values),
                        "max_response_time": max(values),
                        "sample_count": len(values)
                    }
            
            return component_trends
            
        except Exception as e:
            logging.error(f"Performance trends analysis error: {str(e)}")
            return {}
    
    def analyze_component_usage(self, batch: List[PerformanceMetric]) -> Dict:
        """Analyze component usage patterns"""
        try:
            component_counts = defaultdict(int)
            component_errors = defaultdict(int)
            
            for metric in batch:
                component_counts[metric.component] += 1
                
                if metric.metric_type == "error":
                    component_errors[metric.component] += 1
            
            # Calculate error rates
            component_error_rates = {}
            for component, count in component_counts.items():
                error_count = component_errors.get(component, 0)
                component_error_rates[component] = (error_count / count) * 100 if count > 0 else 0
            
            return {
                "usage_counts": dict(component_counts),
                "error_rates": component_error_rates,
                "most_used_component": max(component_counts.items(), key=lambda x: x[1])[0] if component_counts else None
            }
            
        except Exception as e:
            logging.error(f"Component usage analysis error: {str(e)}")
            return {}
    
    def generate_analytics_reports(self) -> None:
        """Generate comprehensive analytics reports"""
        try:
            # Generate real-time dashboard data
            dashboard_data = self.generate_dashboard_data()
            
            # Generate SLA report
            sla_report = self.generate_sla_report()
            
            # Generate user satisfaction metrics
            satisfaction_metrics = self.generate_satisfaction_metrics()
            
            # Store reports
            self.store_analytics_reports({
                "dashboard": dashboard_data,
                "sla": sla_report,
                "satisfaction": satisfaction_metrics,
                "generated_at": datetime.now().isoformat()
            })
            
        except Exception as e:
            logging.error(f"Analytics reports generation error: {str(e)}")
    
    def generate_dashboard_data(self) -> Dict:
        """Generate real-time dashboard data"""
        try:
            # Calculate current metrics
            current_metrics = {
                "response_times": self.calculate_current_response_times(),
                "cache_performance": self.calculate_cache_performance(),
                "user_activity": self.calculate_user_activity(),
                "error_rates": self.calculate_error_rates(),
                "system_health": self.calculate_system_health()
            }
            
            return current_metrics
            
        except Exception as e:
            logging.error(f"Dashboard data generation error: {str(e)}")
            return {}
    
    def calculate_current_response_times(self) -> Dict:
        """Calculate current response time metrics"""
        try:
            response_time_data = {}
            
            for component, times in self.response_times.items():
                if times:
                    response_time_data[component] = {
                        "avg": statistics.mean(times),
                        "p95": self.calculate_percentile(times, 95),
                        "p99": self.calculate_percentile(times, 99),
                        "count": len(times)
                    }
            
            return response_time_data
            
        except Exception as e:
            logging.error(f"Response times calculation error: {str(e)}")
            return {}
    
    def calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        try:
            if not values:
                return 0.0
            
            sorted_values = sorted(values)
            index = int((percentile / 100) * len(sorted_values))
            return sorted_values[min(index, len(sorted_values) - 1)]
            
        except Exception as e:
            logging.error(f"Percentile calculation error: {str(e)}")
            return 0.0
    
    def calculate_cache_performance(self) -> Dict:
        """Calculate cache performance metrics"""
        try:
            total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
            hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "hit_rate": hit_rate,
                "total_hits": self.cache_stats["hits"],
                "total_misses": self.cache_stats["misses"],
                "total_requests": total_requests
            }
            
        except Exception as e:
            logging.error(f"Cache performance calculation error: {str(e)}")
            return {}
    
    def calculate_user_activity(self) -> Dict:
        """Calculate user activity metrics"""
        try:
            total_interactions = sum(len(interactions) for interactions in self.user_interactions.values())
            
            user_type_distribution = {
                user_type: len(interactions)
                for user_type, interactions in self.user_interactions.items()
            }
            
            return {
                "total_interactions": total_interactions,
                "user_type_distribution": user_type_distribution,
                "active_user_types": len(user_type_distribution)
            }
            
        except Exception as e:
            logging.error(f"User activity calculation error: {str(e)}")
            return {}
    
    def calculate_error_rates(self) -> Dict:
        """Calculate error rate metrics"""
        try:
            total_errors = sum(self.error_counts.values())
            
            error_breakdown = dict(self.error_counts)
            
            return {
                "total_errors": total_errors,
                "error_breakdown": error_breakdown,
                "error_types": len(error_breakdown)
            }
            
        except Exception as e:
            logging.error(f"Error rates calculation error: {str(e)}")
            return {}
    
    def calculate_system_health(self) -> Dict:
        """Calculate overall system health score"""
        try:
            # Calculate health score based on various factors
            health_factors = {
                "response_time": self.calculate_response_time_health(),
                "error_rate": self.calculate_error_rate_health(),
                "cache_performance": self.calculate_cache_health(),
                "user_satisfaction": self.calculate_user_satisfaction_health()
            }
            
            # Overall health score (0-100)
            overall_health = statistics.mean(health_factors.values())
            
            return {
                "overall_score": overall_health,
                "factors": health_factors,
                "status": self.get_health_status(overall_health)
            }
            
        except Exception as e:
            logging.error(f"System health calculation error: {str(e)}")
            return {"overall_score": 0, "status": "unknown"}
    
    def calculate_response_time_health(self) -> float:
        """Calculate response time health score"""
        try:
            all_times = []
            for times in self.response_times.values():
                all_times.extend(times)
            
            if not all_times:
                return 100.0
            
            avg_time = statistics.mean(all_times)
            
            # Score based on SLA target (2 seconds)
            if avg_time <= 1.0:
                return 100.0
            elif avg_time <= 2.0:
                return 80.0
            elif avg_time <= 3.0:
                return 60.0
            else:
                return 40.0
                
        except Exception as e:
            logging.error(f"Response time health calculation error: {str(e)}")
            return 50.0
    
    def calculate_error_rate_health(self) -> float:
        """Calculate error rate health score"""
        try:
            total_errors = sum(self.error_counts.values())
            
            # Assume 1000 total requests for calculation
            error_rate = (total_errors / 1000) * 100
            
            if error_rate <= 1.0:
                return 100.0
            elif error_rate <= 5.0:
                return 80.0
            elif error_rate <= 10.0:
                return 60.0
            else:
                return 40.0
                
        except Exception as e:
            logging.error(f"Error rate health calculation error: {str(e)}")
            return 50.0
    
    def calculate_cache_health(self) -> float:
        """Calculate cache performance health score"""
        try:
            cache_perf = self.calculate_cache_performance()
            hit_rate = cache_perf.get("hit_rate", 0)
            
            if hit_rate >= 80:
                return 100.0
            elif hit_rate >= 60:
                return 80.0
            elif hit_rate >= 40:
                return 60.0
            else:
                return 40.0
                
        except Exception as e:
            logging.error(f"Cache health calculation error: {str(e)}")
            return 50.0
    
    def calculate_user_satisfaction_health(self) -> float:
        """Calculate user satisfaction health score"""
        try:
            # Placeholder for user satisfaction calculation
            # In production, this would be based on user feedback, ratings, etc.
            return 85.0
            
        except Exception as e:
            logging.error(f"User satisfaction health calculation error: {str(e)}")
            return 50.0
    
    def get_health_status(self, score: float) -> str:
        """Get health status based on score"""
        if score >= 90:
            return "excellent"
        elif score >= 80:
            return "good"
        elif score >= 70:
            return "fair"
        elif score >= 60:
            return "poor"
        else:
            return "critical"
    
    def generate_sla_report(self) -> Dict:
        """Generate SLA compliance report"""
        try:
            sla_report = {}
            
            for metric_type, metrics in self.sla_metrics.items():
                if metrics:
                    total_metrics = len(metrics)
                    compliant_metrics = len([m for m in metrics if m["meets_sla"]])
                    compliance_rate = (compliant_metrics / total_metrics) * 100
                    
                    sla_report[metric_type] = {
                        "compliance_rate": compliance_rate,
                        "total_measurements": total_metrics,
                        "compliant_measurements": compliant_metrics,
                        "target": self.sla_targets[metric_type]["target"],
                        "status": "compliant" if compliance_rate >= 95 else "non_compliant"
                    }
            
            return sla_report
            
        except Exception as e:
            logging.error(f"SLA report generation error: {str(e)}")
            return {}
    
    def generate_satisfaction_metrics(self) -> Dict:
        """Generate user satisfaction metrics"""
        try:
            # Placeholder for satisfaction metrics
            # In production, integrate with user feedback systems
            return {
                "overall_satisfaction": 4.2,
                "response_quality": 4.3,
                "response_speed": 4.1,
                "ease_of_use": 4.4,
                "total_feedback": 150,
                "feedback_trend": "improving"
            }
            
        except Exception as e:
            logging.error(f"Satisfaction metrics generation error: {str(e)}")
            return {}
    
    def store_analytics_reports(self, reports: Dict) -> None:
        """Store analytics reports"""
        try:
            from .production_environment_manager import get_production_environment_manager
            
            manager = get_production_environment_manager()
            if "redis_primary" in manager.connection_pools:
                redis_client = redis.Redis(
                    connection_pool=manager.connection_pools["redis_primary"]["pool"]
                )
                
                # Store latest reports
                redis_client.setex(
                    "wcfcb:analytics:reports",
                    3600,  # 1 hour TTL
                    json.dumps(reports)
                )
                
                # Store in historical data
                redis_client.zadd(
                    "wcfcb:analytics:history",
                    {json.dumps(reports): time.time()}
                )
                
                # Keep only last 7 days
                cutoff_time = time.time() - (7 * 24 * 60 * 60)
                redis_client.zremrangebyscore("wcfcb:analytics:history", 0, cutoff_time)
            
        except Exception as e:
            logging.error(f"Analytics reports storage error: {str(e)}")
    
    def load_alert_rules(self) -> List[AlertRule]:
        """Load alert rules configuration"""
        return [
            AlertRule(
                name="high_response_time",
                metric_type="response_time",
                threshold=2.0,
                comparison="gt",
                duration=300,  # 5 minutes
                severity="warning",
                enabled=True
            ),
            AlertRule(
                name="critical_response_time",
                metric_type="response_time",
                threshold=5.0,
                comparison="gt",
                duration=60,  # 1 minute
                severity="critical",
                enabled=True
            ),
            AlertRule(
                name="high_error_rate",
                metric_type="error",
                threshold=10.0,
                comparison="gt",
                duration=300,  # 5 minutes
                severity="warning",
                enabled=True
            ),
            AlertRule(
                name="low_cache_hit_rate",
                metric_type="cache_hit_rate",
                threshold=50.0,
                comparison="lt",
                duration=600,  # 10 minutes
                severity="warning",
                enabled=True
            )
        ]
    
    def load_sla_targets(self) -> Dict:
        """Load SLA targets configuration"""
        return {
            "response_time": {
                "target": 2.0,
                "comparison": "lt",
                "description": "Response time should be less than 2 seconds"
            },
            "availability": {
                "target": 99.9,
                "comparison": "gt",
                "description": "System availability should be greater than 99.9%"
            },
            "cache_hit_rate": {
                "target": 60.0,
                "comparison": "gt",
                "description": "Cache hit rate should be greater than 60%"
            }
        }
    
    def get_monitoring_status(self) -> Dict:
        """Get comprehensive monitoring status"""
        try:
            return {
                "monitoring_active": self.monitoring_active,
                "metrics_buffer_size": len(self.metrics_buffer),
                "active_alerts": len(self.active_alerts),
                "alert_rules": len(self.alert_rules),
                "analytics_cache_size": len(self.analytics_cache),
                "last_analytics_update": self.analytics_cache.get("last_updated"),
                "sla_metrics_tracked": len(self.sla_metrics),
                "performance_tracking": {
                    "components_tracked": len(self.response_times),
                    "cache_requests": self.cache_stats["hits"] + self.cache_stats["misses"],
                    "user_interactions": sum(len(interactions) for interactions in self.user_interactions.values()),
                    "error_count": sum(self.error_counts.values())
                }
            }
            
        except Exception as e:
            logging.error(f"Monitoring status error: {str(e)}")
            return {"error": str(e)}

# Global monitoring system instance
monitoring_system = None

def get_monitoring_system() -> MonitoringAnalyticsSystem:
    """Get global monitoring system instance"""
    global monitoring_system
    if monitoring_system is None:
        monitoring_system = MonitoringAnalyticsSystem()
    return monitoring_system

# API Endpoints

@frappe.whitelist()
def get_performance_dashboard():
    """API endpoint for performance dashboard data"""
    try:
        system = get_monitoring_system()
        dashboard_data = system.generate_dashboard_data()
        
        return {
            "success": True,
            "data": dashboard_data
        }
        
    except Exception as e:
        frappe.log_error(f"Performance dashboard API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_analytics_reports():
    """API endpoint for analytics reports"""
    try:
        system = get_monitoring_system()
        
        reports = {
            "dashboard": system.generate_dashboard_data(),
            "sla": system.generate_sla_report(),
            "satisfaction": system.generate_satisfaction_metrics(),
            "system_health": system.calculate_system_health()
        }
        
        return {
            "success": True,
            "data": reports
        }
        
    except Exception as e:
        frappe.log_error(f"Analytics reports API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_active_alerts():
    """API endpoint for active alerts"""
    try:
        system = get_monitoring_system()
        
        return {
            "success": True,
            "data": {
                "active_alerts": list(system.active_alerts.values()),
                "alert_count": len(system.active_alerts)
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Active alerts API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
