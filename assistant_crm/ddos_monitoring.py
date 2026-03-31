"""
DDoS Protection Monitoring Dashboard
Frappe page for real-time violation tracking and metrics
"""

import frappe
import json
from datetime import datetime, timedelta
from collections import Counter
import redis

@frappe.whitelist()
def get_ddos_violations(hours=24, limit=100):
    """
    Fetch DDoS violations from the last N hours
    Used by dashboard to display recent violations
    """
    try:
        cutoff_time = frappe.utils.add_to_date(None, hours=-hours)
        
        violations = frappe.db.get_list(
            "Assistant CRM DDoS Log",
            filters=[["timestamp", ">=", cutoff_time]],
            fields=["name", "timestamp", "user", "ip_address", "endpoint", "violation_type", "details"],
            order_by="timestamp desc",
            limit_page_length=limit
        )
        
        return {
            "status": "success",
            "count": len(violations),
            "data": violations
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist()
def get_violations_summary(hours=24):
    """
    Get summary statistics for dashboard
    """
    try:
        cutoff_time = frappe.utils.add_to_date(None, hours=-hours)
        
        # Total violations
        total = frappe.db.get_value(
            "Assistant CRM DDoS Log",
            filters=[["timestamp", ">=", cutoff_time]],
            fieldname="COUNT(*) as count"
        )
        total = total[0] if total else 0
        
        # By violation type
        violations_by_type = frappe.db.get_list(
            "Assistant CRM DDoS Log",
            filters=[["timestamp", ">=", cutoff_time]],
            fields=["violation_type", "COUNT(*) as count"],
            group_by="violation_type"
        )
        
        # Top attacking IPs
        top_ips = frappe.db.get_list(
            "Assistant CRM DDoS Log",
            filters=[["timestamp", ">=", cutoff_time]],
            fields=["ip_address", "COUNT(*) as count"],
            group_by="ip_address",
            order_by="count desc",
            limit_page_length=10
        )
        
        # Most targeted endpoints
        top_endpoints = frappe.db.get_list(
            "Assistant CRM DDoS Log",
            filters=[["timestamp", ">=", cutoff_time]],
            fields=["endpoint", "COUNT(*) as count"],
            group_by="endpoint",
            order_by="count desc",
            limit_page_length=5
        )
        
        # Unique IPs
        unique_ips = frappe.db.get_value(
            "Assistant CRM DDoS Log",
            filters=[["timestamp", ">=", cutoff_time]],
            fieldname="COUNT(DISTINCT ip_address) as count"
        )
        unique_ips = unique_ips[0] if unique_ips else 0
        
        # Unique users affected
        unique_users = frappe.db.get_value(
            "Assistant CRM DDoS Log",
            filters=[["timestamp", ">=", cutoff_time]],
            fieldname="COUNT(DISTINCT user) as count"
        )
        unique_users = unique_users[0] if unique_users else 0
        
        return {
            "status": "success",
            "summary": {
                "total_violations": total,
                "unique_ips": unique_ips,
                "unique_users": unique_users,
                "time_period_hours": hours
            },
            "by_type": violations_by_type,
            "top_ips": top_ips,
            "top_endpoints": top_endpoints
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist()
def get_violation_timeline(hours=24, interval_minutes=60):
    """
    Get violations over time for chart
    """
    try:
        cutoff_time = frappe.utils.add_to_date(None, hours=-hours)
        
        # Raw violations
        violations = frappe.db.get_list(
            "Assistant CRM DDoS Log",
            filters=[["timestamp", ">=", cutoff_time]],
            fields=["timestamp"],
            order_by="timestamp"
        )
        
        # Group by time interval
        timeline = {}
        for v in violations:
            ts = v.timestamp
            # Round to interval
            interval_key = (ts.replace(minute=0, second=0, microsecond=0) + 
                          timedelta(minutes=interval_minutes * (ts.minute // interval_minutes)))
            key = interval_key.isoformat()
            timeline[key] = timeline.get(key, 0) + 1
        
        # Sort and format
        sorted_timeline = sorted(timeline.items())
        
        return {
            "status": "success",
            "data": [{"timestamp": k, "count": v} for k, v in sorted_timeline]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist()
def get_redis_metrics():
    """
    Get rate limiter metrics from Redis
    """
    try:
        redis_conn = redis.from_url(
            frappe.conf.get("redis_cache", "redis://localhost:6379/1"),
            decode_responses=True
        )
        
        # Get all rate limit keys
        keys = redis_conn.keys("rl:*:timestamps")
        
        metrics = {
            "active_rate_limiters": len(keys),
            "rate_limited_ips": len([k for k in keys if k.startswith("rl:ip:")]),
            "rate_limited_users": len([k for k in keys if k.startswith("rl:user:")])
        }
        
        return {
            "status": "success",
            "data": metrics
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist()
def get_health_check():
    """
    Health check for monitoring
    """
    try:
        # Check DDoS protection is enabled
        ddos_enabled = frappe.conf.get("enable_assistant_crm_ddos_protection", True)
        
        # Check Redis
        redis_ok = False
        try:
            redis_conn = redis.from_url(
                frappe.conf.get("redis_cache", "redis://localhost:6379/1"),
                decode_responses=True
            )
            redis_conn.ping()
            redis_ok = True
        except:
            pass
        
        # Check database
        db_ok = False
        try:
            frappe.db.sql("SELECT 1")
            db_ok = True
        except:
            pass
        
        status = "healthy" if (ddos_enabled and redis_ok and db_ok) else "degraded"
        
        return {
            "status": status,
            "checks": {
                "ddos_enabled": ddos_enabled,
                "redis_available": redis_ok,
                "database_available": db_ok
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist()
def export_violation_report(hours=24, format="json"):
    """
    Export violations for analysis
    """
    try:
        cutoff_time = frappe.utils.add_to_date(None, hours=-hours)
        
        violations = frappe.db.get_list(
            "Assistant CRM DDoS Log",
            filters=[["timestamp", ">=", cutoff_time]],
            fields=["*"],
            order_by="timestamp desc"
        )
        
        if format == "csv":
            # CSV format
            import csv
            from io import StringIO
            
            output = StringIO()
            if violations:
                writer = csv.DictWriter(output, fieldnames=violations[0].keys())
                writer.writeheader()
                writer.writerows(violations)
            
            return {
                "status": "success",
                "data": output.getvalue(),
                "filename": f"ddos_violations_{hours}h.csv"
            }
        else:
            # JSON format
            return {
                "status": "success",
                "data": violations,
                "filename": f"ddos_violations_{hours}h.json"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
