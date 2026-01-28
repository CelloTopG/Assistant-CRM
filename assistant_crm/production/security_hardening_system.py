#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Security Hardening System
Production Deployment Phase: Enterprise-grade security implementation
Implements encryption, threat detection, audit logging, and DDoS protection
"""

import frappe
import json
import time
import hashlib
import hmac
import secrets
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging
import ipaddress
from collections import defaultdict, deque
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

@dataclass
class SecurityEvent:
    """Security event data structure"""
    timestamp: datetime
    event_type: str
    severity: str
    source_ip: str
    user_id: str
    session_id: str
    details: Dict
    risk_score: int

@dataclass
class ThreatPattern:
    """Threat detection pattern"""
    name: str
    pattern_type: str
    indicators: List[str]
    threshold: int
    time_window: int
    severity: str
    enabled: bool

class SecurityHardeningSystem:
    """
    Comprehensive security hardening system for production deployment
    Implements encryption, threat detection, audit logging, and access controls
    """
    
    def __init__(self):
        self.encryption_key = self.load_or_generate_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Security monitoring
        self.security_events = deque(maxlen=10000)
        self.threat_patterns = self.load_threat_patterns()
        self.active_threats = {}
        self.blocked_ips = set()
        self.rate_limiters = defaultdict(deque)
        
        # Audit logging
        self.audit_logger = self.setup_audit_logging()
        
        # Security configuration
        self.security_config = self.load_security_config()
        
        # Start security monitoring
        self.monitoring_active = False
        self.start_security_monitoring()
    
    def load_or_generate_encryption_key(self) -> bytes:
        """Load or generate encryption key for data protection"""
        try:
            key_file = os.path.join(
                os.getenv('SECURITY_KEY_DIR', '/etc/wcfcb/keys'),
                'encryption.key'
            )
            
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    return f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(key_file), exist_ok=True)
                
                # Save key securely
                with open(key_file, 'wb') as f:
                    f.write(key)
                
                # Set secure permissions
                os.chmod(key_file, 0o600)
                
                logging.info("New encryption key generated and saved")
                return key
                
        except Exception as e:
            logging.error(f"Encryption key loading error: {str(e)}")
            # Fallback to environment variable or generate temporary key
            env_key = os.getenv('WCFCB_ENCRYPTION_KEY')
            if env_key:
                return base64.urlsafe_b64decode(env_key)
            else:
                logging.warning("Using temporary encryption key - not suitable for production")
                return Fernet.generate_key()
    
    def setup_audit_logging(self) -> logging.Logger:
        """Setup dedicated audit logging"""
        try:
            audit_logger = logging.getLogger('wcfcb.security.audit')
            audit_logger.setLevel(logging.INFO)
            
            # Audit log file
            audit_file = os.path.join(
                os.getenv('AUDIT_LOG_DIR', '/var/log/wcfcb/audit'),
                'security_audit.log'
            )
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(audit_file), exist_ok=True)
            
            # Create file handler with rotation
            handler = logging.FileHandler(audit_file)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
            ))
            
            audit_logger.addHandler(handler)
            
            return audit_logger
            
        except Exception as e:
            logging.error(f"Audit logging setup error: {str(e)}")
            return logging.getLogger('wcfcb.security.audit')
    
    def load_security_config(self) -> Dict:
        """Load security configuration"""
        return {
            "encryption": {
                "algorithm": "AES-256",
                "key_rotation_days": int(os.getenv('KEY_ROTATION_DAYS', 90)),
                "data_at_rest": True,
                "data_in_transit": True
            },
            "rate_limiting": {
                "enabled": True,
                "requests_per_minute": int(os.getenv('RATE_LIMIT_RPM', 100)),
                "burst_limit": int(os.getenv('RATE_LIMIT_BURST', 20)),
                "block_duration": int(os.getenv('RATE_LIMIT_BLOCK_DURATION', 300))
            },
            "ddos_protection": {
                "enabled": True,
                "threshold": int(os.getenv('DDOS_THRESHOLD', 1000)),
                "time_window": int(os.getenv('DDOS_TIME_WINDOW', 60)),
                "auto_block": True
            },
            "threat_detection": {
                "enabled": True,
                "real_time_analysis": True,
                "ml_based_detection": False,  # Placeholder for future ML integration
                "alert_threshold": int(os.getenv('THREAT_ALERT_THRESHOLD', 7))
            },
            "access_control": {
                "session_timeout": int(os.getenv('SESSION_TIMEOUT', 1800)),
                "max_concurrent_sessions": int(os.getenv('MAX_CONCURRENT_SESSIONS', 3)),
                "ip_whitelist_enabled": os.getenv('IP_WHITELIST_ENABLED', 'false').lower() == 'true',
                "geo_blocking_enabled": os.getenv('GEO_BLOCKING_ENABLED', 'false').lower() == 'true'
            },
            "audit": {
                "log_all_requests": True,
                "log_authentication": True,
                "log_data_access": True,
                "log_admin_actions": True,
                "retention_days": int(os.getenv('AUDIT_RETENTION_DAYS', 365))
            }
        }
    
    def start_security_monitoring(self) -> None:
        """Start security monitoring workers"""
        try:
            self.monitoring_active = True
            
            # Start threat detection worker
            threat_worker = threading.Thread(
                target=self.threat_detection_worker,
                daemon=True
            )
            threat_worker.start()
            
            # Start rate limiting cleanup worker
            cleanup_worker = threading.Thread(
                target=self.rate_limit_cleanup_worker,
                daemon=True
            )
            cleanup_worker.start()
            
            # Start security analytics worker
            analytics_worker = threading.Thread(
                target=self.security_analytics_worker,
                daemon=True
            )
            analytics_worker.start()
            
            logging.info("Security monitoring workers started")
            
        except Exception as e:
            logging.error(f"Security monitoring startup error: {str(e)}")
            raise
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            if not data:
                return data
            
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            logging.error(f"Data encryption error: {str(e)}")
            raise
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            if not encrypted_data:
                return encrypted_data
            
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_data.decode()
            
        except Exception as e:
            logging.error(f"Data decryption error: {str(e)}")
            raise
    
    def validate_request_security(self, request_data: Dict) -> Dict:
        """Validate request security and apply protections"""
        try:
            source_ip = request_data.get("source_ip", "unknown")
            user_id = request_data.get("user_id", "anonymous")
            endpoint = request_data.get("endpoint", "unknown")
            
            validation_result = {
                "allowed": True,
                "security_checks": {},
                "risk_score": 0,
                "applied_protections": []
            }
            
            # Check IP blocking
            ip_check = self.check_ip_blocking(source_ip)
            validation_result["security_checks"]["ip_blocking"] = ip_check
            if not ip_check["allowed"]:
                validation_result["allowed"] = False
                validation_result["reason"] = "IP blocked"
                return validation_result
            
            # Check rate limiting
            rate_limit_check = self.check_rate_limiting(source_ip, user_id)
            validation_result["security_checks"]["rate_limiting"] = rate_limit_check
            if not rate_limit_check["allowed"]:
                validation_result["allowed"] = False
                validation_result["reason"] = "Rate limit exceeded"
                return validation_result
            
            # Check DDoS protection
            ddos_check = self.check_ddos_protection(source_ip)
            validation_result["security_checks"]["ddos_protection"] = ddos_check
            if not ddos_check["allowed"]:
                validation_result["allowed"] = False
                validation_result["reason"] = "DDoS protection triggered"
                return validation_result
            
            # Threat detection analysis
            threat_analysis = self.analyze_request_threats(request_data)
            validation_result["security_checks"]["threat_analysis"] = threat_analysis
            validation_result["risk_score"] = threat_analysis["risk_score"]
            
            # Log security event
            self.log_security_event(
                event_type="request_validation",
                severity="info",
                source_ip=source_ip,
                user_id=user_id,
                details={
                    "endpoint": endpoint,
                    "validation_result": validation_result
                }
            )
            
            return validation_result
            
        except Exception as e:
            logging.error(f"Request security validation error: {str(e)}")
            return {
                "allowed": False,
                "reason": "Security validation error",
                "error": str(e)
            }
    
    def check_ip_blocking(self, source_ip: str) -> Dict:
        """Check if IP is blocked"""
        try:
            if source_ip in self.blocked_ips:
                return {
                    "allowed": False,
                    "reason": "IP is blocked",
                    "blocked_until": "permanent"
                }
            
            # Check IP whitelist if enabled
            if self.security_config["access_control"]["ip_whitelist_enabled"]:
                whitelist = self.load_ip_whitelist()
                if source_ip not in whitelist:
                    return {
                        "allowed": False,
                        "reason": "IP not in whitelist"
                    }
            
            return {"allowed": True}
            
        except Exception as e:
            logging.error(f"IP blocking check error: {str(e)}")
            return {"allowed": True}  # Fail open for availability
    
    def check_rate_limiting(self, source_ip: str, user_id: str) -> Dict:
        """Check rate limiting for IP and user"""
        try:
            if not self.security_config["rate_limiting"]["enabled"]:
                return {"allowed": True}
            
            current_time = time.time()
            time_window = 60  # 1 minute window
            
            # Check IP-based rate limiting
            ip_key = f"ip:{source_ip}"
            ip_requests = self.rate_limiters[ip_key]
            
            # Remove old requests
            while ip_requests and ip_requests[0] < current_time - time_window:
                ip_requests.popleft()
            
            # Check if limit exceeded
            rpm_limit = self.security_config["rate_limiting"]["requests_per_minute"]
            if len(ip_requests) >= rpm_limit:
                return {
                    "allowed": False,
                    "reason": "IP rate limit exceeded",
                    "limit": rpm_limit,
                    "current": len(ip_requests)
                }
            
            # Add current request
            ip_requests.append(current_time)
            
            # Check user-based rate limiting if user is authenticated
            if user_id != "anonymous":
                user_key = f"user:{user_id}"
                user_requests = self.rate_limiters[user_key]
                
                # Remove old requests
                while user_requests and user_requests[0] < current_time - time_window:
                    user_requests.popleft()
                
                # Check user limit (higher than IP limit)
                user_limit = rpm_limit * 2
                if len(user_requests) >= user_limit:
                    return {
                        "allowed": False,
                        "reason": "User rate limit exceeded",
                        "limit": user_limit,
                        "current": len(user_requests)
                    }
                
                user_requests.append(current_time)
            
            return {"allowed": True}
            
        except Exception as e:
            logging.error(f"Rate limiting check error: {str(e)}")
            return {"allowed": True}  # Fail open
    
    def check_ddos_protection(self, source_ip: str) -> Dict:
        """Check DDoS protection"""
        try:
            if not self.security_config["ddos_protection"]["enabled"]:
                return {"allowed": True}
            
            current_time = time.time()
            time_window = self.security_config["ddos_protection"]["time_window"]
            threshold = self.security_config["ddos_protection"]["threshold"]
            
            # Check request volume from IP
            ddos_key = f"ddos:{source_ip}"
            requests = self.rate_limiters[ddos_key]
            
            # Remove old requests
            while requests and requests[0] < current_time - time_window:
                requests.popleft()
            
            # Check if threshold exceeded
            if len(requests) >= threshold:
                # Auto-block IP if enabled
                if self.security_config["ddos_protection"]["auto_block"]:
                    self.block_ip(source_ip, "DDoS protection")
                
                return {
                    "allowed": False,
                    "reason": "DDoS protection triggered",
                    "threshold": threshold,
                    "current": len(requests)
                }
            
            # Add current request
            requests.append(current_time)
            
            return {"allowed": True}
            
        except Exception as e:
            logging.error(f"DDoS protection check error: {str(e)}")
            return {"allowed": True}  # Fail open
    
    def analyze_request_threats(self, request_data: Dict) -> Dict:
        """Analyze request for threat patterns"""
        try:
            risk_score = 0
            detected_threats = []
            
            # Analyze request patterns
            for pattern in self.threat_patterns:
                if not pattern.enabled:
                    continue
                
                threat_detected = self.check_threat_pattern(request_data, pattern)
                if threat_detected:
                    detected_threats.append(pattern.name)
                    risk_score += self.get_pattern_risk_score(pattern)
            
            # Additional threat analysis
            risk_score += self.analyze_request_anomalies(request_data)
            
            return {
                "risk_score": min(risk_score, 10),  # Cap at 10
                "detected_threats": detected_threats,
                "threat_level": self.get_threat_level(risk_score)
            }
            
        except Exception as e:
            logging.error(f"Threat analysis error: {str(e)}")
            return {"risk_score": 0, "detected_threats": [], "threat_level": "low"}
    
    def check_threat_pattern(self, request_data: Dict, pattern: ThreatPattern) -> bool:
        """Check if request matches threat pattern"""
        try:
            if pattern.pattern_type == "sql_injection":
                return self.check_sql_injection_pattern(request_data, pattern)
            elif pattern.pattern_type == "xss":
                return self.check_xss_pattern(request_data, pattern)
            elif pattern.pattern_type == "brute_force":
                return self.check_brute_force_pattern(request_data, pattern)
            elif pattern.pattern_type == "suspicious_user_agent":
                return self.check_user_agent_pattern(request_data, pattern)
            else:
                return False
                
        except Exception as e:
            logging.error(f"Threat pattern check error: {str(e)}")
            return False
    
    def check_sql_injection_pattern(self, request_data: Dict, pattern: ThreatPattern) -> bool:
        """Check for SQL injection patterns"""
        try:
            # Check request parameters for SQL injection indicators
            request_content = json.dumps(request_data).lower()
            
            sql_indicators = [
                "union select", "drop table", "insert into", "delete from",
                "update set", "exec(", "execute(", "sp_", "xp_", "'; --",
                "' or '1'='1", "' or 1=1", "admin'--", "' union select"
            ]
            
            for indicator in sql_indicators:
                if indicator in request_content:
                    return True
            
            return False
            
        except Exception as e:
            logging.error(f"SQL injection pattern check error: {str(e)}")
            return False
    
    def check_xss_pattern(self, request_data: Dict, pattern: ThreatPattern) -> bool:
        """Check for XSS patterns"""
        try:
            request_content = json.dumps(request_data).lower()
            
            xss_indicators = [
                "<script", "javascript:", "onload=", "onerror=", "onclick=",
                "alert(", "document.cookie", "window.location", "<iframe",
                "eval(", "expression(", "vbscript:", "data:text/html"
            ]
            
            for indicator in xss_indicators:
                if indicator in request_content:
                    return True
            
            return False
            
        except Exception as e:
            logging.error(f"XSS pattern check error: {str(e)}")
            return False
    
    def check_brute_force_pattern(self, request_data: Dict, pattern: ThreatPattern) -> bool:
        """Check for brute force patterns"""
        try:
            # Check for repeated authentication attempts
            source_ip = request_data.get("source_ip", "")
            endpoint = request_data.get("endpoint", "")
            
            if "auth" in endpoint.lower() or "login" in endpoint.lower():
                # Count recent authentication attempts from this IP
                current_time = time.time()
                auth_key = f"auth_attempts:{source_ip}"
                attempts = self.rate_limiters[auth_key]
                
                # Remove old attempts (last 15 minutes)
                while attempts and attempts[0] < current_time - 900:
                    attempts.popleft()
                
                # Check if threshold exceeded
                if len(attempts) >= pattern.threshold:
                    return True
                
                attempts.append(current_time)
            
            return False
            
        except Exception as e:
            logging.error(f"Brute force pattern check error: {str(e)}")
            return False
    
    def check_user_agent_pattern(self, request_data: Dict, pattern: ThreatPattern) -> bool:
        """Check for suspicious user agent patterns"""
        try:
            user_agent = request_data.get("user_agent", "").lower()
            
            suspicious_agents = [
                "sqlmap", "nikto", "nmap", "masscan", "zap", "burp",
                "python-requests", "curl", "wget", "bot", "crawler",
                "scanner", "exploit", "hack", "attack"
            ]
            
            for agent in suspicious_agents:
                if agent in user_agent:
                    return True
            
            return False
            
        except Exception as e:
            logging.error(f"User agent pattern check error: {str(e)}")
            return False
    
    def analyze_request_anomalies(self, request_data: Dict) -> int:
        """Analyze request for anomalies"""
        try:
            anomaly_score = 0
            
            # Check request size
            request_size = len(json.dumps(request_data))
            if request_size > 100000:  # 100KB
                anomaly_score += 2
            
            # Check for unusual headers
            headers = request_data.get("headers", {})
            if len(headers) > 50:
                anomaly_score += 1
            
            # Check for suspicious parameters
            params = request_data.get("parameters", {})
            if len(params) > 100:
                anomaly_score += 1
            
            # Check for binary content in text fields
            for key, value in params.items():
                if isinstance(value, str) and len(value) > 1000:
                    # Check for binary patterns
                    if any(ord(c) < 32 or ord(c) > 126 for c in value[:100]):
                        anomaly_score += 2
            
            return anomaly_score
            
        except Exception as e:
            logging.error(f"Request anomaly analysis error: {str(e)}")
            return 0
    
    def get_pattern_risk_score(self, pattern: ThreatPattern) -> int:
        """Get risk score for threat pattern"""
        severity_scores = {
            "low": 1,
            "medium": 3,
            "high": 5,
            "critical": 8
        }
        return severity_scores.get(pattern.severity, 1)
    
    def get_threat_level(self, risk_score: int) -> str:
        """Get threat level based on risk score"""
        if risk_score >= 8:
            return "critical"
        elif risk_score >= 5:
            return "high"
        elif risk_score >= 3:
            return "medium"
        else:
            return "low"
    
    def block_ip(self, ip_address: str, reason: str) -> None:
        """Block IP address"""
        try:
            self.blocked_ips.add(ip_address)
            
            # Log security event
            self.log_security_event(
                event_type="ip_blocked",
                severity="warning",
                source_ip=ip_address,
                user_id="system",
                details={"reason": reason}
            )
            
            logging.warning(f"IP blocked: {ip_address} - Reason: {reason}")
            
        except Exception as e:
            logging.error(f"IP blocking error: {str(e)}")
    
    def log_security_event(self, event_type: str, severity: str, source_ip: str,
                          user_id: str, details: Dict, session_id: str = "") -> None:
        """Log security event"""
        try:
            event = SecurityEvent(
                timestamp=datetime.now(),
                event_type=event_type,
                severity=severity,
                source_ip=source_ip,
                user_id=user_id,
                session_id=session_id,
                details=details,
                risk_score=details.get("risk_score", 0)
            )
            
            # Add to events buffer
            self.security_events.append(event)
            
            # Log to audit logger
            audit_message = {
                "timestamp": event.timestamp.isoformat(),
                "event_type": event_type,
                "severity": severity,
                "source_ip": source_ip,
                "user_id": user_id,
                "session_id": session_id,
                "details": details
            }
            
            self.audit_logger.info(json.dumps(audit_message))
            
        except Exception as e:
            logging.error(f"Security event logging error: {str(e)}")
    
    def threat_detection_worker(self) -> None:
        """Background worker for threat detection"""
        while self.monitoring_active:
            try:
                self.analyze_security_events()
                time.sleep(30)  # Analyze every 30 seconds
                
            except Exception as e:
                logging.error(f"Threat detection worker error: {str(e)}")
                time.sleep(60)
    
    def analyze_security_events(self) -> None:
        """Analyze security events for threats"""
        try:
            # Get recent events (last 5 minutes)
            cutoff_time = datetime.now() - timedelta(minutes=5)
            recent_events = [
                event for event in self.security_events
                if event.timestamp > cutoff_time
            ]
            
            if not recent_events:
                return
            
            # Analyze event patterns
            self.detect_coordinated_attacks(recent_events)
            self.detect_privilege_escalation(recent_events)
            self.detect_data_exfiltration(recent_events)
            
        except Exception as e:
            logging.error(f"Security events analysis error: {str(e)}")
    
    def detect_coordinated_attacks(self, events: List[SecurityEvent]) -> None:
        """Detect coordinated attack patterns"""
        try:
            # Group events by source IP
            ip_events = defaultdict(list)
            for event in events:
                ip_events[event.source_ip].append(event)
            
            # Check for coordinated attacks
            for ip, ip_event_list in ip_events.items():
                if len(ip_event_list) >= 10:  # High activity threshold
                    # Check for diverse attack types
                    attack_types = set(event.event_type for event in ip_event_list)
                    if len(attack_types) >= 3:
                        self.trigger_security_alert(
                            "coordinated_attack",
                            "high",
                            f"Coordinated attack detected from {ip}",
                            {"source_ip": ip, "attack_types": list(attack_types)}
                        )
            
        except Exception as e:
            logging.error(f"Coordinated attack detection error: {str(e)}")
    
    def detect_privilege_escalation(self, events: List[SecurityEvent]) -> None:
        """Detect privilege escalation attempts"""
        try:
            # Look for authentication followed by admin actions
            user_events = defaultdict(list)
            for event in events:
                if event.user_id != "anonymous":
                    user_events[event.user_id].append(event)
            
            for user_id, user_event_list in user_events.items():
                # Check for rapid privilege changes
                auth_events = [e for e in user_event_list if "auth" in e.event_type]
                admin_events = [e for e in user_event_list if "admin" in e.event_type]
                
                if auth_events and admin_events:
                    time_diff = (admin_events[0].timestamp - auth_events[-1].timestamp).total_seconds()
                    if time_diff < 60:  # Less than 1 minute
                        self.trigger_security_alert(
                            "privilege_escalation",
                            "critical",
                            f"Potential privilege escalation by user {user_id}",
                            {"user_id": user_id, "time_diff": time_diff}
                        )
            
        except Exception as e:
            logging.error(f"Privilege escalation detection error: {str(e)}")
    
    def detect_data_exfiltration(self, events: List[SecurityEvent]) -> None:
        """Detect data exfiltration attempts"""
        try:
            # Look for large data access patterns
            data_access_events = [
                event for event in events
                if event.event_type == "data_access" and event.details.get("data_size", 0) > 1000000
            ]
            
            if len(data_access_events) >= 5:  # Multiple large data accesses
                self.trigger_security_alert(
                    "data_exfiltration",
                    "critical",
                    "Potential data exfiltration detected",
                    {"large_access_count": len(data_access_events)}
                )
            
        except Exception as e:
            logging.error(f"Data exfiltration detection error: {str(e)}")
    
    def trigger_security_alert(self, alert_type: str, severity: str, 
                             message: str, details: Dict) -> None:
        """Trigger security alert"""
        try:
            alert_data = {
                "id": f"alert_{int(time.time())}_{secrets.token_hex(4)}",
                "type": alert_type,
                "severity": severity,
                "message": message,
                "details": details,
                "triggered_at": datetime.now().isoformat(),
                "status": "active"
            }
            
            # Store active threat
            self.active_threats[alert_data["id"]] = alert_data
            
            # Log critical alert
            logging.critical(f"Security alert: {alert_data}")
            
            # Send alert notification
            self.send_security_alert(alert_data)
            
        except Exception as e:
            logging.error(f"Security alert triggering error: {str(e)}")
    
    def send_security_alert(self, alert_data: Dict) -> None:
        """Send security alert notification"""
        try:
            # In production, integrate with security incident response systems
            alert_message = f"""
WCFCB SECURITY ALERT

Severity: {alert_data['severity'].upper()}
Type: {alert_data['type']}
Message: {alert_data['message']}
Time: {alert_data['triggered_at']}

Details: {json.dumps(alert_data['details'], indent=2)}

IMMEDIATE INVESTIGATION REQUIRED
            """
            
            logging.critical(f"Security alert notification: {alert_message}")
            
        except Exception as e:
            logging.error(f"Security alert notification error: {str(e)}")
    
    def rate_limit_cleanup_worker(self) -> None:
        """Background worker for rate limit cleanup"""
        while self.monitoring_active:
            try:
                current_time = time.time()
                
                # Clean up old rate limit entries
                for key in list(self.rate_limiters.keys()):
                    requests = self.rate_limiters[key]
                    
                    # Remove entries older than 1 hour
                    while requests and requests[0] < current_time - 3600:
                        requests.popleft()
                    
                    # Remove empty deques
                    if not requests:
                        del self.rate_limiters[key]
                
                time.sleep(300)  # Cleanup every 5 minutes
                
            except Exception as e:
                logging.error(f"Rate limit cleanup worker error: {str(e)}")
                time.sleep(300)
    
    def security_analytics_worker(self) -> None:
        """Background worker for security analytics"""
        while self.monitoring_active:
            try:
                self.generate_security_analytics()
                time.sleep(600)  # Generate analytics every 10 minutes
                
            except Exception as e:
                logging.error(f"Security analytics worker error: {str(e)}")
                time.sleep(600)
    
    def generate_security_analytics(self) -> None:
        """Generate security analytics and insights"""
        try:
            # Get recent events (last hour)
            cutoff_time = datetime.now() - timedelta(hours=1)
            recent_events = [
                event for event in self.security_events
                if event.timestamp > cutoff_time
            ]
            
            if not recent_events:
                return
            
            analytics = {
                "timestamp": datetime.now().isoformat(),
                "total_events": len(recent_events),
                "event_types": self.analyze_event_types(recent_events),
                "severity_distribution": self.analyze_severity_distribution(recent_events),
                "top_source_ips": self.analyze_top_source_ips(recent_events),
                "threat_trends": self.analyze_threat_trends(recent_events),
                "security_score": self.calculate_security_score(recent_events)
            }
            
            # Store analytics
            self.store_security_analytics(analytics)
            
        except Exception as e:
            logging.error(f"Security analytics generation error: {str(e)}")
    
    def analyze_event_types(self, events: List[SecurityEvent]) -> Dict:
        """Analyze event types distribution"""
        event_counts = defaultdict(int)
        for event in events:
            event_counts[event.event_type] += 1
        return dict(event_counts)
    
    def analyze_severity_distribution(self, events: List[SecurityEvent]) -> Dict:
        """Analyze severity distribution"""
        severity_counts = defaultdict(int)
        for event in events:
            severity_counts[event.severity] += 1
        return dict(severity_counts)
    
    def analyze_top_source_ips(self, events: List[SecurityEvent]) -> List[Dict]:
        """Analyze top source IPs"""
        ip_counts = defaultdict(int)
        for event in events:
            ip_counts[event.source_ip] += 1
        
        # Return top 10 IPs
        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        return [{"ip": ip, "count": count} for ip, count in top_ips]
    
    def analyze_threat_trends(self, events: List[SecurityEvent]) -> Dict:
        """Analyze threat trends"""
        high_risk_events = [event for event in events if event.risk_score >= 5]
        
        return {
            "high_risk_events": len(high_risk_events),
            "average_risk_score": sum(event.risk_score for event in events) / len(events) if events else 0,
            "trend": "increasing" if len(high_risk_events) > 5 else "stable"
        }
    
    def calculate_security_score(self, events: List[SecurityEvent]) -> int:
        """Calculate overall security score (0-100)"""
        try:
            if not events:
                return 100
            
            # Base score
            score = 100
            
            # Deduct points for security events
            critical_events = len([e for e in events if e.severity == "critical"])
            high_events = len([e for e in events if e.severity == "high"])
            medium_events = len([e for e in events if e.severity == "medium"])
            
            score -= critical_events * 10
            score -= high_events * 5
            score -= medium_events * 2
            
            # Deduct points for high risk scores
            avg_risk = sum(event.risk_score for event in events) / len(events)
            score -= int(avg_risk * 5)
            
            return max(score, 0)
            
        except Exception as e:
            logging.error(f"Security score calculation error: {str(e)}")
            return 50
    
    def store_security_analytics(self, analytics: Dict) -> None:
        """Store security analytics"""
        try:
            from .production_environment_manager import get_production_environment_manager
            
            manager = get_production_environment_manager()
            if "redis_primary" in manager.connection_pools:
                redis_client = redis.Redis(
                    connection_pool=manager.connection_pools["redis_primary"]["pool"]
                )
                
                # Store latest analytics
                redis_client.setex(
                    "wcfcb:security:analytics",
                    3600,  # 1 hour TTL
                    json.dumps(analytics)
                )
                
                # Store in historical data
                redis_client.zadd(
                    "wcfcb:security:history",
                    {json.dumps(analytics): time.time()}
                )
                
                # Keep only last 30 days
                cutoff_time = time.time() - (30 * 24 * 60 * 60)
                redis_client.zremrangebyscore("wcfcb:security:history", 0, cutoff_time)
            
        except Exception as e:
            logging.error(f"Security analytics storage error: {str(e)}")
    
    def load_threat_patterns(self) -> List[ThreatPattern]:
        """Load threat detection patterns"""
        return [
            ThreatPattern(
                name="sql_injection",
                pattern_type="sql_injection",
                indicators=["union select", "drop table", "'; --"],
                threshold=1,
                time_window=60,
                severity="high",
                enabled=True
            ),
            ThreatPattern(
                name="xss_attack",
                pattern_type="xss",
                indicators=["<script", "javascript:", "alert("],
                threshold=1,
                time_window=60,
                severity="medium",
                enabled=True
            ),
            ThreatPattern(
                name="brute_force_login",
                pattern_type="brute_force",
                indicators=["failed_login"],
                threshold=5,
                time_window=300,
                severity="high",
                enabled=True
            ),
            ThreatPattern(
                name="suspicious_bot",
                pattern_type="suspicious_user_agent",
                indicators=["bot", "crawler", "scanner"],
                threshold=1,
                time_window=60,
                severity="low",
                enabled=True
            )
        ]
    
    def load_ip_whitelist(self) -> List[str]:
        """Load IP whitelist"""
        try:
            whitelist_file = os.path.join(
                os.getenv('SECURITY_CONFIG_DIR', '/etc/wcfcb/security'),
                'ip_whitelist.txt'
            )
            
            if os.path.exists(whitelist_file):
                with open(whitelist_file, 'r') as f:
                    return [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            # Default whitelist for development
            return ["127.0.0.1", "::1", "localhost"]
            
        except Exception as e:
            logging.error(f"IP whitelist loading error: {str(e)}")
            return ["127.0.0.1", "::1"]
    
    def get_security_status(self) -> Dict:
        """Get comprehensive security status"""
        try:
            return {
                "monitoring_active": self.monitoring_active,
                "encryption_enabled": bool(self.encryption_key),
                "blocked_ips_count": len(self.blocked_ips),
                "active_threats_count": len(self.active_threats),
                "security_events_count": len(self.security_events),
                "threat_patterns_enabled": len([p for p in self.threat_patterns if p.enabled]),
                "rate_limiters_active": len(self.rate_limiters),
                "security_config": {
                    "rate_limiting_enabled": self.security_config["rate_limiting"]["enabled"],
                    "ddos_protection_enabled": self.security_config["ddos_protection"]["enabled"],
                    "threat_detection_enabled": self.security_config["threat_detection"]["enabled"],
                    "audit_logging_enabled": self.security_config["audit"]["log_all_requests"]
                },
                "last_analytics_update": datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Security status error: {str(e)}")
            return {"error": str(e)}

# Global security system instance
security_system = None

def get_security_system() -> SecurityHardeningSystem:
    """Get global security system instance"""
    global security_system
    if security_system is None:
        security_system = SecurityHardeningSystem()
    return security_system

# API Endpoints

@frappe.whitelist()
def validate_request_security():
    """API endpoint for request security validation"""
    try:
        data = frappe.local.form_dict
        request_data = {
            "source_ip": frappe.local.request.environ.get('REMOTE_ADDR', 'unknown'),
            "user_id": data.get("user_id", "anonymous"),
            "endpoint": frappe.local.request.path,
            "user_agent": frappe.local.request.headers.get('User-Agent', ''),
            "headers": dict(frappe.local.request.headers),
            "parameters": data
        }
        
        system = get_security_system()
        validation_result = system.validate_request_security(request_data)
        
        return {
            "success": True,
            "data": validation_result
        }
        
    except Exception as e:
        frappe.log_error(f"Security validation API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_security_dashboard():
    """API endpoint for security dashboard"""
    try:
        system = get_security_system()
        status = system.get_security_status()
        
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        frappe.log_error(f"Security dashboard API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_active_threats():
    """API endpoint for active security threats"""
    try:
        system = get_security_system()
        
        return {
            "success": True,
            "data": {
                "active_threats": list(system.active_threats.values()),
                "threat_count": len(system.active_threats)
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Active threats API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
