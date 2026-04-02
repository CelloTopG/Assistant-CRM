"""
DDoS Protection Monitoring Dashboard
Frappe page for real-time violation tracking and metrics
"""

import frappe
import json
from datetime import datetime, timedelta
from collections import Counter
import redis


def _get_redis():
    """Get a live Redis connection or return None."""
    try:
        rc = redis.from_url(
            frappe.conf.get("redis_cache", "redis://localhost:6379/1"),
            decode_responses=True
        )
        rc.ping()
        return rc
    except Exception:
        return None

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


# ── IP Management ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_active_rate_limited_ips():
    """Return IPs currently tracked by the Redis sliding-window rate limiter."""
    try:
        rc = _get_redis()
        if not rc:
            return {"status": "error", "message": "Redis unavailable"}

        keys = rc.keys("rl:ip:*:timestamps")
        result = []
        for key in keys:
            ip = key.replace("rl:ip:", "").replace(":timestamps", "")
            count = rc.zcard(key)
            oldest = rc.zrange(key, 0, 0, withscores=True)
            result.append({
                "ip_address": ip,
                "request_count": count,
                "window_start": oldest[0][1] if oldest else None,
            })
        result.sort(key=lambda x: x["request_count"], reverse=True)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def clear_ip_rate_limit(ip_address):
    """Delete Redis rate-limit keys for an IP, immediately lifting any active block."""
    try:
        rc = _get_redis()
        if not rc:
            return {"status": "error", "message": "Redis unavailable"}

        deleted = rc.delete(
            f"rl:ip:{ip_address}:timestamps",
            f"rl:ip:{ip_address}:endpoints",
        )
        return {
            "status": "success",
            "message": f"Rate limit cleared for {ip_address}",
            "keys_deleted": deleted,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def clear_ip_violations(ip_address):
    """Delete all DDoS log entries for a given IP address."""
    try:
        count = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabAssistant CRM DDoS Log` WHERE ip_address = %s",
            ip_address
        )[0][0]
        frappe.db.sql(
            "DELETE FROM `tabAssistant CRM DDoS Log` WHERE ip_address = %s",
            ip_address
        )
        frappe.db.commit()
        return {
            "status": "success",
            "message": f"Cleared {count} violation log(s) for {ip_address}",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def block_ip(ip_address):
    """Add an IP to the permanent Redis blacklist (ddos:blacklist)."""
    try:
        rc = _get_redis()
        if not rc:
            return {"status": "error", "message": "Redis unavailable"}

        rc.sadd("ddos:blacklist", ip_address)
        rc.hset("ddos:blacklist:meta", ip_address, datetime.utcnow().isoformat())
        return {"status": "success", "message": f"IP {ip_address} has been permanently blocked"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def unblock_ip(ip_address):
    """Remove an IP from the permanent Redis blacklist."""
    try:
        rc = _get_redis()
        if not rc:
            return {"status": "error", "message": "Redis unavailable"}

        rc.srem("ddos:blacklist", ip_address)
        rc.hdel("ddos:blacklist:meta", ip_address)
        return {"status": "success", "message": f"IP {ip_address} has been unblocked"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_blocked_ips():
    """Return all IPs currently in the permanent Redis blacklist."""
    try:
        rc = _get_redis()
        if not rc:
            return {"status": "error", "message": "Redis unavailable"}

        ips = rc.smembers("ddos:blacklist")
        meta = rc.hgetall("ddos:blacklist:meta")
        result = [
            {"ip_address": ip, "blocked_at": meta.get(ip, "")}
            for ip in ips
        ]
        result.sort(key=lambda x: x["blocked_at"], reverse=True)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Rate Limit Configuration ───────────────────────────────────────────────────

@frappe.whitelist()
def get_rate_limit_config():
    """Return current rate limits merged with any Redis overrides."""
    try:
        from assistant_crm.ddos_protection import RATE_LIMITS
        import copy

        rc = _get_redis()
        overrides = {}
        if rc:
            raw = rc.get("ddos:rate_limit_overrides")
            if raw:
                overrides = json.loads(raw)

        config = copy.deepcopy(RATE_LIMITS)
        for category, limits in overrides.items():
            if category in config:
                config[category].update(limits)

        return {"status": "success", "data": config, "overrides": overrides}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def update_rate_limit(category, limit_type, value):
    """Persist a rate limit override to Redis. Applies on the next request."""
    try:
        value = int(value)
        if not (1 <= value <= 100000):
            return {"status": "error", "message": "Value must be between 1 and 100,000"}

        rc = _get_redis()
        if not rc:
            return {"status": "error", "message": "Redis unavailable"}

        raw = rc.get("ddos:rate_limit_overrides")
        overrides = json.loads(raw) if raw else {}
        overrides.setdefault(category, {})[limit_type] = value
        rc.set("ddos:rate_limit_overrides", json.dumps(overrides))

        return {
            "status": "success",
            "message": f"Rate limit updated: {category} / {limit_type} = {value} req/min",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
