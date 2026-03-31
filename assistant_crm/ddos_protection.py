"""
Application-level DDoS protection for Assistant CRM
Uses Redis for distributed rate limiting across Gunicorn workers
Logs violations to Frappe error log and database
"""

import frappe
import redis
import time
import logging
from frappe import _, get_request_header
from werkzeug.exceptions import TooManyRequests
import json
from datetime import datetime

logger = logging.getLogger("assistant_crm.ddos_protection")

# Configuration - Rate limits per route category
RATE_LIMITS = {
    "crm_routes": {
        "anonymous": 600,        # 10 req/sec per IP (600 per minute)
        "authenticated": 1800,   # 30 req/sec per user (1800 per minute)
    },
    "auth_routes": {
        "anonymous": 60,         # 1 req/sec per IP for login (60 per minute)
    },
    "report_routes": {
        "authenticated": 120,    # 2 req/sec per user for reports (120 per minute)
    },
}

# CRM endpoints to protect
PROTECTED_ROUTES = {
    "crm_routes": [
        "/api/resource/assistant_crm",
        "/api/method/assistant_crm",
        "/api/resource/conversation",
        "/api/method/conversation",
    ],
    "auth_routes": [
        "/api/method/frappe.auth.login",
        "/api/method/frappe.auth.signup",
    ],
    "report_routes": [
        "/api/method/frappe.client.get_list",
        "/api/method/frappe.report",
    ],
}


class RateLimiterConfig:
    """Centralized rate limit configuration"""

    @staticmethod
    def get_redis_connection():
        """Get Redis connection from Frappe config"""
        try:
            # Try to get from config, fallback to default
            cache_config = frappe.conf.get("redis_cache", "redis://localhost:6379/1")
            rc = redis.from_url(cache_config, decode_responses=True)
            rc.ping()
            return rc
        except Exception as e:
            logger.warning(f"Redis connection failed: {str(e)}")
            return None

    @staticmethod
    def get_route_category(path):
        """Determine which route category a path belongs to"""
        for category, routes in PROTECTED_ROUTES.items():
            for route in routes:
                if route in path:
                    return category
        return None

    @staticmethod
    def get_identifier(is_authenticated, user=None, ip=None):
        """Generate unique identifier for rate limiting"""
        if is_authenticated and user:
            return f"rl:user:{user}"
        return f"rl:ip:{ip}"


class RateLimiter:
    """
    Redis-backed rate limiter using sliding window counter algorithm
    """

    def __init__(self):
        self.redis_conn = RateLimiterConfig.get_redis_connection()
        self.window_size = 60  # 1-minute window

    def is_allowed(self, identifier, limit):
        """
        Check if request is within rate limit.
        Returns: (is_allowed: bool, remaining_requests: int, reset_after_sec: int)
        """
        if not self.redis_conn:
            logger.debug("Redis unavailable, allowing request")
            return True, limit, self.window_size

        try:
            current_time = int(time.time())
            window_start = current_time - self.window_size

            # Get all requests in current window
            timestamps_key = f"{identifier}:timestamps"

            # Remove expired entries (older than window)
            self.redis_conn.zremrangebyscore(timestamps_key, 0, window_start)

            # Count current requests in window
            request_count = self.redis_conn.zcard(timestamps_key)

            if request_count >= limit:
                # Rate limit exceeded
                remaining = 0
                oldest_request = self.redis_conn.zrange(
                    timestamps_key, 0, 0, withscores=True
                )
                reset_after = (
                    int(oldest_request[0][1]) + self.window_size - current_time
                    if oldest_request
                    else self.window_size
                )
                return False, remaining, max(1, reset_after)

            # Add current request timestamp
            self.redis_conn.zadd(timestamps_key, {str(current_time): current_time})
            self.redis_conn.expire(timestamps_key, self.window_size + 10)

            remaining = limit - request_count - 1
            return True, remaining, self.window_size

        except Exception as e:
            logger.error(f"Rate limiter check failed: {str(e)}")
            return True, limit, self.window_size  # Fail open


class BotDetector:
    """
    Detect suspicious bot patterns without external services
    """

    # Suspicious patterns in User-Agent
    SUSPICIOUS_HEADERS = [
        "scrapy",
        "curl",
        "wget",
        "python",
        "java",
        "go-http-client",
        "urlgrabber",
        "libwww",
        "nikto",
        "masscan",
        "nmap",
    ]

    @staticmethod
    def check_headers(request_headers):
        """Analyze request headers for bot patterns"""
        violations = []

        # Check User-Agent
        user_agent = request_headers.get("User-Agent", "").lower()
        if not user_agent:
            violations.append("missing_user_agent")
        else:
            for bot_signature in BotDetector.SUSPICIOUS_HEADERS:
                if bot_signature in user_agent:
                    violations.append(f"bot_signature:{bot_signature}")
                    break

        # Check for missing common browser headers
        if not request_headers.get("Accept-Language"):
            violations.append("missing_accept_language")

        if not request_headers.get("Accept-Encoding"):
            violations.append("missing_accept_encoding")

        # Check for unusual header patterns
        if request_headers.get("X-Forwarded-For") and not request_headers.get(
            "Referer"
        ):
            violations.append("forwarded_no_referer")

        return violations

    @staticmethod
    def check_behavior(identifier, redis_conn):
        """Detect rapid endpoint cycling and other behaviors"""
        if not redis_conn:
            return []

        violations = []

        try:
            # Check for rapid endpoint changes (>5 different endpoints in 10 sec)
            endpoint_key = f"{identifier}:endpoints"
            current_endpoints = redis_conn.smembers(endpoint_key)

            if len(current_endpoints) > 5:
                violations.append("endpoint_cycling")

        except Exception as e:
            logger.debug(f"Behavior check error: {str(e)}")

        return violations


class DDoSProtectionMiddleware:
    """
    Frappe before_request hook for DDoS protection
    """

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.violation_log = []

    def check_request(self):
        """Main entry point for rate limiting and bot detection"""

        # Skip if disabled in config
        if not frappe.conf.get("enable_assistant_crm_ddos_protection", True):
            return

        # Skip database initialization and health check requests
        skip_paths = [
            "/api/setup/check",
            "/api/setup/create",
            "/app/setup",
            "/api/health",
            "/api/method/frappe.client.get_count",  # Health check endpoint
        ]
        if frappe.request.path in skip_paths:
            return

        # Skip non-GET/POST requests
        if frappe.request.method not in ["GET", "POST", "PUT", "DELETE"]:
            return

        # Determine if this is a protected route
        route_category = RateLimiterConfig.get_route_category(frappe.request.path)
        if not route_category:
            return

        # Get request identifiers
        is_authenticated = frappe.session.user != "Guest"
        user = frappe.session.user if is_authenticated else None
        client_ip = (
            get_request_header("X-Forwarded-For")
            or frappe.request.remote_addr
            or "unknown"
        )

        # Extract only the first IP if X-Forwarded-For contains multiple
        if "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()

        identifier = RateLimiterConfig.get_identifier(is_authenticated, user, client_ip)

        # Collect request headers
        request_headers = {}
        for header in frappe.request.headers:
            request_headers[header] = frappe.request.headers.get(header)

        # Bot detection
        bot_violations = BotDetector.check_headers(request_headers)
        bot_violations.extend(
            BotDetector.check_behavior(identifier, self.rate_limiter.redis_conn)
        )

        if bot_violations and len(bot_violations) >= 2:
            # Multiple violations = likely bot
            self._log_violation(
                identifier,
                user,
                client_ip,
                frappe.request.path,
                "bot_detected",
                bot_violations,
            )

        # Rate limiting
        limit = RATE_LIMITS.get(route_category, {}).get(
            "authenticated" if is_authenticated else "anonymous", 600
        )

        is_allowed, remaining, reset_after = self.rate_limiter.is_allowed(
            identifier, limit
        )

        if not is_allowed:
            self._log_violation(
                identifier,
                user,
                client_ip,
                frappe.request.path,
                "rate_limit_exceeded",
                {"limit": limit, "reset_after": reset_after},
            )

            # Return 429 Too Many Requests
            frappe.db.rollback()
            frappe.response["http_status_code"] = 429
            raise TooManyRequests(
                f"Rate limit exceeded. Reset after {reset_after} seconds."
            )

        # Track endpoint for behavior analysis
        if self.rate_limiter.redis_conn:
            try:
                endpoint_key = f"{identifier}:endpoints"
                self.rate_limiter.redis_conn.sadd(endpoint_key, frappe.request.path)
                self.rate_limiter.redis_conn.expire(endpoint_key, 10)
            except Exception as e:
                logger.debug(f"Behavior tracking error: {str(e)}")

    def _log_violation(self, identifier, user, ip, path, violation_type, details):
        """Log DDoS protection violations to Frappe error log and optional database"""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "identifier": identifier,
                "user": user or "anonymous",
                "ip": ip,
                "path": path,
                "violation_type": violation_type,
                "details": details,
            }

            # Log to Frappe's error logger in JSON format (easy to parse)
            logger.warning(f"DDOS_VIOLATION {json.dumps(log_entry)}")

            # Also log to Frappe's error log for UI visibility
            try:
                frappe.log_error(
                    title=f"DDoS: {violation_type}",
                    message=json.dumps(log_entry, indent=2),
                )
            except Exception as e:
                logger.debug(f"Could not log to error log: {str(e)}")

        except Exception as e:
            logger.error(f"Violation logging failed: {str(e)}")


# Global middleware instance
ddos_middleware = None


def initialize_ddos_protection():
    """Initialize middleware on first request"""
    global ddos_middleware
    if not ddos_middleware:
        ddos_middleware = DDoSProtectionMiddleware()


def before_request():
    """Frappe hook: called before every request"""
    initialize_ddos_protection()
    ddos_middleware.check_request()
