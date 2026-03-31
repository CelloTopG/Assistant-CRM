"""
DDoS Protection Email Digest
Generates and sends daily/weekly violation summaries via email
"""

import frappe
from frappe.utils import add_to_date, now_datetime
import json
from datetime import datetime, timedelta

def generate_daily_digest():
    """
    Generate and send daily DDoS violation digest
    Called by scheduled task at 7 AM daily
    """
    generate_digest("daily", "Send Daily DDoS Protection Report")


def generate_weekly_digest():
    """
    Generate and send weekly DDoS violation digest
    Called by scheduled task on Monday mornings
    """
    generate_digest("weekly", "Send Weekly DDoS Protection Report")


def generate_digest(period, subject_prefix):
    """
    Core digest generation logic
    
    Args:
        period: 'daily' or 'weekly'
        subject_prefix: Subject line prefix for email
    """
    
    # Calculate time range
    hours = 24 if period == "daily" else 168  # 7 days
    cutoff_time = add_to_date(None, hours=-hours)
    
    # Fetch summary stats
    try:
        violations = frappe.db.get_list(
            "Assistant CRM DDoS Log",
            filters=[["timestamp", ">=", cutoff_time]],
            fields=["*"],
            order_by="timestamp"
        )
    except:
        # Table doesn't exist yet, skip sending
        return
    
    if not violations:
        # No violations to report
        return
    
    # Build statistics
    stats = build_violation_stats(violations)
    
    # Get system health
    health = get_system_health()
    
    # Generate HTML email body
    email_body = generate_email_html(period, hours, stats, health)
    
    # Send to configured email address
    send_digest_email(period, email_body)
    
    # Log digest was sent
    frappe.log_error(
        title=f"DDoS Digest Sent - {period.title()}",
        message=f"Sent {period} DDoS protection digest to {frappe.conf.get('ddos_alert_email', 'system-alerts@example.com')}\nViolations count: {len(violations)}"
    )


def build_violation_stats(violations):
    """Build statistics from violations list"""
    from collections import Counter
    
    stats = {
        "total_violations": len(violations),
        "by_type": {},
        "top_ips": Counter(),
        "top_endpoints": Counter(),
        "top_users": Counter(),
        "hourly_distribution": {}
    }
    
    for v in violations:
        # By type
        vtype = v.get("violation_type", "unknown")
        stats["by_type"][vtype] = stats["by_type"].get(vtype, 0) + 1
        
        # Top IPs
        stats["top_ips"][v.get("ip_address", "unknown")] += 1
        
        # Top endpoints
        stats["top_endpoints"][v.get("endpoint", "unknown")] += 1
        
        # Top users
        stats["top_users"][v.get("user", "anonymous")] += 1
        
        # Hourly distribution
        try:
            ts = v.get("timestamp")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            hour = ts.strftime("%H:00")
            stats["hourly_distribution"][hour] = stats["hourly_distribution"].get(hour, 0) + 1
        except:
            pass
    
    # Convert counters to lists
    stats["top_ips"] = stats["top_ips"].most_common(10)
    stats["top_endpoints"] = stats["top_endpoints"].most_common(5)
    stats["top_users"] = stats["top_users"].most_common(5)
    
    return stats


def get_system_health():
    """Get system health check status"""
    health = {
        "ddos_enabled": frappe.conf.get("enable_assistant_crm_ddos_protection", True),
        "redis_ok": False,
        "database_ok": False
    }
    
    # Check Redis
    try:
        import redis
        redis_conn = redis.from_url(
            frappe.conf.get("redis_cache", "redis://localhost:6379/1"),
            decode_responses=True
        )
        redis_conn.ping()
        health["redis_ok"] = True
    except:
        pass
    
    # Check database
    try:
        frappe.db.sql("SELECT 1")
        health["database_ok"] = True
    except:
        pass
    
    return health


def generate_email_html(period, hours, stats, health):
    """
    Generate HTML email body for digest
    """
    
    # Time period string
    period_str = "Last 24 Hours" if period == "daily" else "Last 7 Days"
    
    # Build violation details table
    violations_by_type_rows = ""
    for vtype, count in stats["by_type"].items():
        violations_by_type_rows += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">{vtype}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;"><strong>{count}</strong></td>
        </tr>
        """
    
    # Top IPs table
    top_ips_rows = ""
    for ip, count in stats["top_ips"]:
        top_ips_rows += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #eee;"><code>{ip}</code></td>
            <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;"><strong>{count}</strong></td>
        </tr>
        """
    
    # Top endpoints table
    endpoints_rows = ""
    for endpoint, count in stats["top_endpoints"]:
        endpoints_rows += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #eee;"><small>{endpoint}</small></td>
            <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;"><strong>{count}</strong></td>
        </tr>
        """
    
    # Hourly distribution chart (text-based)
    hourly_rows = ""
    for hour in sorted(stats["hourly_distribution"].keys()):
        count = stats["hourly_distribution"][hour]
        bar = "█" * min(count // 5, 40)
        hourly_rows += f"""
        <tr>
            <td style="padding: 4px; border-bottom: 1px solid #eee;">{hour}</td>
            <td style="padding: 4px; border-bottom: 1px solid #eee;"><small>{bar} {count}</small></td>
        </tr>
        """
    
    # System health indicator
    health_indicator = "✅ All Systems Operational" if all(health.values()) else "⚠️ Check Status"
    health_color = "green" if all(health.values()) else "orange"
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; }}
            .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
            .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 4px; }}
            .section-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            .metric {{ font-size: 24px; font-weight: bold; color: #e74c3c; }}
            .metric-label {{ color: #666; font-size: 12px; }}
            .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 15px 0; }}
            .metric-box {{ padding: 15px; background-color: #f5f5f5; border-radius: 4px; text-align: center; }}
            .health-ok {{ color: green; }}
            .health-warning {{ color: orange; }}
            .footer {{ background-color: #ecf0f1; padding: 15px; text-align: center; font-size: 12px; color: #7f8c8d; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🛡️ DDoS Protection {period.title()} Report</h1>
            <p>{period_str} - Assistant CRM</p>
        </div>
        
        <!-- Key Metrics -->
        <div class="section">
            <div class="section-title">📊 Summary Metrics</div>
            <div class="metrics-grid">
                <div class="metric-box">
                    <div class="metric">{stats['total_violations']}</div>
                    <div class="metric-label">Total Violations</div>
                </div>
                <div class="metric-box">
                    <div class="metric">{len(dict(stats['top_ips']))}</div>
                    <div class="metric-label">Unique IPs</div>
                </div>
                <div class="metric-box">
                    <div class="metric">{len(dict(stats['top_endpoints']))}</div>
                    <div class="metric-label">Targeted Endpoints</div>
                </div>
                <div class="metric-box">
                    <div class="metric">{len(dict(stats['top_users']))}</div>
                    <div class="metric-label">Affected Users</div>
                </div>
            </div>
        </div>
        
        <!-- Violations by Type -->
        <div class="section">
            <div class="section-title">📈 Violations by Type</div>
            <table>
                {violations_by_type_rows}
            </table>
        </div>
        
        <!-- Top Attacking IPs -->
        <div class="section">
            <div class="section-title">🚨 Top Attacking IPs</div>
            <table>
                <tr>
                    <th style="padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">IP Address</th>
                    <th style="padding: 8px; text-align: right; border-bottom: 2px solid #ddd;">Violations</th>
                </tr>
                {top_ips_rows}
            </table>
        </div>
        
        <!-- Top Endpoints -->
        <div class="section">
            <div class="section-title">🎯 Most Targeted Endpoints</div>
            <table>
                <tr>
                    <th style="padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">Endpoint</th>
                    <th style="padding: 8px; text-align: right; border-bottom: 2px solid #ddd;">Hits</th>
                </tr>
                {endpoints_rows}
            </table>
        </div>
        
        <!-- Hourly Distribution -->
        <div class="section">
            <div class="section-title">⏱️ Hourly Distribution</div>
            <table>
                <tr>
                    <th style="padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">Hour</th>
                    <th style="padding: 8px; border-bottom: 2px solid #ddd;">Distribution</th>
                </tr>
                {hourly_rows}
            </table>
        </div>
        
        <!-- System Health -->
        <div class="section">
            <div class="section-title">⚙️ System Health</div>
            <p><span class="health-{'ok' if all(health.values()) else 'warning'}">{health_indicator}</span></p>
            <ul>
                <li>DDoS Protection: {'✅ Enabled' if health['ddos_enabled'] else '❌ Disabled'}</li>
                <li>Redis Cache: {'✅ Connected' if health['redis_ok'] else '❌ Disconnected'}</li>
                <li>Database: {'✅ Connected' if health['database_ok'] else '❌ Disconnected'}</li>
            </ul>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <p>
                For detailed analysis, visit:<br>
                <strong>{frappe.conf.get('host_name')}/app/assistant-crm-ddos-monitor</strong>
            </p>
            <p>This is an automated report. Do not reply to this email.</p>
        </div>
    </body>
    </html>
    """
    
    return html_body


def send_digest_email(period, email_body):
    """
    Send email digest to configured recipients
    """
    
    # Get recipient email
    recipient = frappe.conf.get("ddos_alert_email")
    if not recipient:
        # Default to administrator if not configured
        recipient = frappe.db.get_value("Administrator", fieldname="email")
    
    if not recipient:
        frappe.log_error(
            title="DDoS Digest Email Failed",
            message="No recipient configured. Set 'ddos_alert_email' in site_config.json"
        )
        return
    
    period_str = "Daily" if period == "daily" else "Weekly"
    
    try:
        frappe.sendmail(
            recipients=[recipient],
            subject=f"🛡️ Assistant CRM {period_str} DDoS Protection Report",
            message=email_body,
            reference_doctype=None
        )
    except Exception as e:
        frappe.log_error(
            title="DDoS Digest Email Failed",
            message=f"Error sending {period} digest: {str(e)}"
        )
