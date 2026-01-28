# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from frappe.utils import now_datetime, add_to_date, get_datetime
from assistant_crm.assistant_crm.services.cache_service import get_cache_service
from assistant_crm.assistant_crm.services.error_handler import get_error_handler


class MonitoringService:
    """Comprehensive monitoring service for Assistant CRM system health"""
    
    def __init__(self):
        self.metrics_key = "assistant_crm_metrics"
        self.alerts_key = "assistant_crm_alerts"
        
    def record_api_call(self, service: str, endpoint: str, response_time: float, 
                       status: str, error_message: str = None):
        """Record API call metrics"""
        try:
            timestamp = now_datetime()
            metric_data = {
                "timestamp": timestamp.isoformat(),
                "service": service,
                "endpoint": endpoint,
                "response_time": response_time,
                "status": status,  # success, error, timeout, rate_limit
                "error_message": error_message
            }
            
            # Store individual metric
            metric_key = f"{self.metrics_key}:api_calls:{timestamp.strftime('%Y%m%d%H')}"
            existing_metrics = frappe.cache().get_value(metric_key) or []
            existing_metrics.append(metric_data)
            
            # Keep only last 100 entries per hour to manage memory
            if len(existing_metrics) > 100:
                existing_metrics = existing_metrics[-100:]
            
            frappe.cache().set_value(metric_key, existing_metrics, expires_in_sec=86400)
            
            # Update aggregated stats
            self._update_aggregated_stats(service, status, response_time)
            
        except Exception as e:
            frappe.log_error(f"Error recording API call metric: {str(e)}", "Monitoring Service")
    
    def _update_aggregated_stats(self, service: str, status: str, response_time: float):
        """Update aggregated statistics"""
        try:
            stats_key = f"{self.metrics_key}:aggregated:{service}"
            stats = frappe.cache().get_value(stats_key) or {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "avg_response_time": 0,
                "max_response_time": 0,
                "min_response_time": float('inf'),
                "last_updated": now_datetime().isoformat()
            }
            
            stats["total_calls"] += 1
            stats["last_updated"] = now_datetime().isoformat()
            
            if status == "success":
                stats["successful_calls"] += 1
            else:
                stats["failed_calls"] += 1
            
            # Update response time stats
            if response_time > stats["max_response_time"]:
                stats["max_response_time"] = response_time
            
            if response_time < stats["min_response_time"]:
                stats["min_response_time"] = response_time
            
            # Calculate rolling average
            current_avg = stats["avg_response_time"]
            stats["avg_response_time"] = (current_avg * (stats["total_calls"] - 1) + response_time) / stats["total_calls"]
            
            # Calculate success rate
            stats["success_rate"] = (stats["successful_calls"] / stats["total_calls"]) * 100
            
            frappe.cache().set_value(stats_key, stats, expires_in_sec=86400)
            
        except Exception as e:
            frappe.log_error(f"Error updating aggregated stats: {str(e)}", "Monitoring Service")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        try:
            health_data = {
                "timestamp": now_datetime().isoformat(),
                "overall_status": "healthy",
                "services": {},
                "alerts": [],
                "performance_metrics": {}
            }
            
            # Check Gemini API health
            gemini_health = self._check_gemini_health()
            health_data["services"]["gemini_api"] = gemini_health
            
            # Check cache health
            cache_health = self._check_cache_health()
            health_data["services"]["cache"] = cache_health
            
            # Check database health
            db_health = self._check_database_health()
            health_data["services"]["database"] = db_health
            
            # Determine overall status
            service_statuses = [service["status"] for service in health_data["services"].values()]
            if "critical" in service_statuses:
                health_data["overall_status"] = "critical"
            elif "warning" in service_statuses:
                health_data["overall_status"] = "warning"
            
            # Get active alerts
            health_data["alerts"] = self.get_active_alerts()
            
            # Get performance metrics
            health_data["performance_metrics"] = self.get_performance_metrics()
            
            return health_data
            
        except Exception as e:
            frappe.log_error(f"Error getting system health: {str(e)}", "Monitoring Service")
            return {
                "timestamp": now_datetime().isoformat(),
                "overall_status": "unknown",
                "error": str(e)
            }
    
    def _check_gemini_health(self) -> Dict[str, Any]:
        """Check Gemini API service health"""
        try:
            error_handler = get_error_handler("gemini_api")
            error_stats = error_handler.get_error_stats()
            circuit_state = error_handler.get_circuit_state()
            
            status = "healthy"
            if circuit_state["state"] == "open":
                status = "critical"
            elif error_stats.get("success_rate", 100) < 80:
                status = "warning"
            
            return {
                "status": status,
                "circuit_state": circuit_state["state"],
                "success_rate": error_stats.get("success_rate", 0),
                "total_requests": error_stats.get("total_requests", 0),
                "last_error": error_stats.get("last_error"),
                "last_error_time": error_stats.get("last_error_time")
            }
            
        except Exception as e:
            return {
                "status": "unknown",
                "error": str(e)
            }
    
    def _check_cache_health(self) -> Dict[str, Any]:
        """Check cache service health"""
        try:
            cache_service = get_cache_service()
            cache_stats = cache_service.get_cache_stats()
            
            hit_rate = cache_stats.get("hit_rate", 0)
            status = "healthy"
            
            if hit_rate < 30:
                status = "warning"
            elif hit_rate < 10:
                status = "critical"
            
            return {
                "status": status,
                "hit_rate": hit_rate,
                "total_requests": cache_stats.get("total_requests", 0),
                "cache_hits": cache_stats.get("cache_hits", 0),
                "cache_misses": cache_stats.get("cache_misses", 0)
            }
            
        except Exception as e:
            return {
                "status": "unknown",
                "error": str(e)
            }
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            # Simple database connectivity test
            start_time = datetime.now()
            frappe.db.sql("SELECT 1")
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            status = "healthy"
            if response_time > 1000:  # 1 second
                status = "warning"
            elif response_time > 5000:  # 5 seconds
                status = "critical"
            
            return {
                "status": status,
                "response_time_ms": response_time,
                "connection": "active"
            }
            
        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "connection": "failed"
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the last 24 hours"""
        try:
            metrics = {
                "api_calls_24h": 0,
                "avg_response_time_24h": 0,
                "error_rate_24h": 0,
                "cache_hit_rate_24h": 0,
                "peak_usage_hour": None
            }
            
            # Get API call metrics for last 24 hours
            now = datetime.now()
            hourly_stats = {}
            
            for i in range(24):
                hour_key = (now - timedelta(hours=i)).strftime('%Y%m%d%H')
                metric_key = f"{self.metrics_key}:api_calls:{hour_key}"
                hour_metrics = frappe.cache().get_value(metric_key) or []
                
                hourly_stats[hour_key] = {
                    "total_calls": len(hour_metrics),
                    "successful_calls": len([m for m in hour_metrics if m["status"] == "success"]),
                    "avg_response_time": sum([m["response_time"] for m in hour_metrics]) / len(hour_metrics) if hour_metrics else 0
                }
                
                metrics["api_calls_24h"] += len(hour_metrics)
            
            # Calculate overall metrics
            if metrics["api_calls_24h"] > 0:
                total_successful = sum([h["successful_calls"] for h in hourly_stats.values()])
                metrics["error_rate_24h"] = ((metrics["api_calls_24h"] - total_successful) / metrics["api_calls_24h"]) * 100
                
                total_response_time = sum([h["avg_response_time"] * h["total_calls"] for h in hourly_stats.values()])
                metrics["avg_response_time_24h"] = total_response_time / metrics["api_calls_24h"]
            
            # Find peak usage hour
            if hourly_stats:
                peak_hour = max(hourly_stats.items(), key=lambda x: x[1]["total_calls"])
                metrics["peak_usage_hour"] = {
                    "hour": peak_hour[0],
                    "calls": peak_hour[1]["total_calls"]
                }
            
            # Get cache metrics
            cache_service = get_cache_service()
            cache_stats = cache_service.get_cache_stats()
            metrics["cache_hit_rate_24h"] = cache_stats.get("hit_rate", 0)
            
            return metrics
            
        except Exception as e:
            frappe.log_error(f"Error getting performance metrics: {str(e)}", "Monitoring Service")
            return {}
    
    def create_alert(self, alert_type: str, severity: str, message: str, 
                    service: str = None, metadata: Dict[str, Any] = None):
        """Create a system alert"""
        try:
            alert = {
                "id": frappe.generate_hash(length=10),
                "timestamp": now_datetime().isoformat(),
                "type": alert_type,  # rate_limit, circuit_open, high_error_rate, etc.
                "severity": severity,  # info, warning, critical
                "message": message,
                "service": service,
                "metadata": metadata or {},
                "acknowledged": False,
                "resolved": False
            }
            
            alerts_key = f"{self.alerts_key}:active"
            active_alerts = frappe.cache().get_value(alerts_key) or []
            active_alerts.append(alert)
            
            # Keep only last 50 alerts
            if len(active_alerts) > 50:
                active_alerts = active_alerts[-50:]
            
            frappe.cache().set_value(alerts_key, active_alerts, expires_in_sec=86400)
            
            # Log critical alerts
            if severity == "critical":
                frappe.log_error(f"CRITICAL ALERT: {message}", "Monitoring Service")
            
            return alert["id"]
            
        except Exception as e:
            frappe.log_error(f"Error creating alert: {str(e)}", "Monitoring Service")
            return None
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        try:
            alerts_key = f"{self.alerts_key}:active"
            active_alerts = frappe.cache().get_value(alerts_key) or []
            
            # Filter out resolved alerts
            active_alerts = [alert for alert in active_alerts if not alert.get("resolved", False)]
            
            return active_alerts
            
        except Exception as e:
            frappe.log_error(f"Error getting active alerts: {str(e)}", "Monitoring Service")
            return []
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        try:
            alerts_key = f"{self.alerts_key}:active"
            active_alerts = frappe.cache().get_value(alerts_key) or []
            
            for alert in active_alerts:
                if alert["id"] == alert_id:
                    alert["acknowledged"] = True
                    alert["acknowledged_at"] = now_datetime().isoformat()
                    break
            
            frappe.cache().set_value(alerts_key, active_alerts, expires_in_sec=86400)
            return True
            
        except Exception as e:
            frappe.log_error(f"Error acknowledging alert: {str(e)}", "Monitoring Service")
            return False


# Global monitoring service instance
_monitoring_service = None

def get_monitoring_service():
    """Get global monitoring service instance"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service
