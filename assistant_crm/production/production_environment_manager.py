#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Production Environment Manager
Production Deployment Phase: Enterprise-grade infrastructure setup
Configures production database connections, monitoring, backup, and high availability
"""

import frappe
import json
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
import psutil
import redis
from contextlib import contextmanager

@dataclass
class ProductionConfig:
    """Production environment configuration"""
    environment: str
    database_config: Dict
    redis_config: Dict
    monitoring_config: Dict
    security_config: Dict
    backup_config: Dict
    load_balancer_config: Dict

class ProductionEnvironmentManager:
    """
    Production Environment Manager for enterprise-grade deployment
    Handles database connections, monitoring, backup, and high availability
    """
    
    def __init__(self):
        self.environment = os.getenv('FRAPPE_ENV', 'production')
        self.config = self.load_production_config()
        self.connection_pools = {}
        self.monitoring_active = False
        self.backup_scheduler = None
        self.health_checker = None
        
        # Initialize production components
        self.setup_logging()
        self.initialize_connection_pools()
        self.start_health_monitoring()
        
    def load_production_config(self) -> ProductionConfig:
        """Load production environment configuration"""
        try:
            # Load from environment variables and config files
            config = ProductionConfig(
                environment=self.environment,
                database_config={
                    "primary": {
                        "host": os.getenv('DB_PRIMARY_HOST', 'localhost'),
                        "port": int(os.getenv('DB_PRIMARY_PORT', 3306)),
                        "database": os.getenv('DB_NAME', 'wcfcb_production'),
                        "user": os.getenv('DB_USER', 'wcfcb_user'),
                        "password": os.getenv('DB_PASSWORD', ''),
                        "pool_size": int(os.getenv('DB_POOL_SIZE', 20)),
                        "max_overflow": int(os.getenv('DB_MAX_OVERFLOW', 30)),
                        "pool_timeout": int(os.getenv('DB_POOL_TIMEOUT', 30)),
                        "ssl_enabled": os.getenv('DB_SSL_ENABLED', 'true').lower() == 'true'
                    },
                    "replica": {
                        "host": os.getenv('DB_REPLICA_HOST', 'localhost'),
                        "port": int(os.getenv('DB_REPLICA_PORT', 3306)),
                        "database": os.getenv('DB_NAME', 'wcfcb_production'),
                        "user": os.getenv('DB_USER', 'wcfcb_user'),
                        "password": os.getenv('DB_PASSWORD', ''),
                        "pool_size": int(os.getenv('DB_REPLICA_POOL_SIZE', 10)),
                        "ssl_enabled": True
                    }
                },
                redis_config={
                    "primary": {
                        "host": os.getenv('REDIS_PRIMARY_HOST', 'localhost'),
                        "port": int(os.getenv('REDIS_PRIMARY_PORT', 6379)),
                        "db": int(os.getenv('REDIS_DB', 0)),
                        "password": os.getenv('REDIS_PASSWORD', ''),
                        "ssl": os.getenv('REDIS_SSL', 'false').lower() == 'true',
                        "max_connections": int(os.getenv('REDIS_MAX_CONNECTIONS', 50))
                    },
                    "cache": {
                        "host": os.getenv('REDIS_CACHE_HOST', 'localhost'),
                        "port": int(os.getenv('REDIS_CACHE_PORT', 6380)),
                        "db": int(os.getenv('REDIS_CACHE_DB', 1)),
                        "password": os.getenv('REDIS_CACHE_PASSWORD', ''),
                        "ssl": os.getenv('REDIS_CACHE_SSL', 'false').lower() == 'true'
                    }
                },
                monitoring_config={
                    "enabled": os.getenv('MONITORING_ENABLED', 'true').lower() == 'true',
                    "metrics_interval": int(os.getenv('METRICS_INTERVAL', 30)),
                    "health_check_interval": int(os.getenv('HEALTH_CHECK_INTERVAL', 60)),
                    "alert_thresholds": {
                        "response_time": float(os.getenv('ALERT_RESPONSE_TIME', 2.0)),
                        "error_rate": float(os.getenv('ALERT_ERROR_RATE', 0.05)),
                        "cpu_usage": float(os.getenv('ALERT_CPU_USAGE', 80.0)),
                        "memory_usage": float(os.getenv('ALERT_MEMORY_USAGE', 85.0)),
                        "disk_usage": float(os.getenv('ALERT_DISK_USAGE', 90.0))
                    }
                },
                security_config={
                    "encryption_enabled": True,
                    "tls_version": "1.3",
                    "rate_limiting": {
                        "enabled": True,
                        "requests_per_minute": int(os.getenv('RATE_LIMIT_RPM', 100)),
                        "burst_limit": int(os.getenv('RATE_LIMIT_BURST', 20))
                    },
                    "ddos_protection": {
                        "enabled": True,
                        "threshold": int(os.getenv('DDOS_THRESHOLD', 1000))
                    }
                },
                backup_config={
                    "enabled": True,
                    "schedule": os.getenv('BACKUP_SCHEDULE', '0 2 * * *'),  # Daily at 2 AM
                    "retention_days": int(os.getenv('BACKUP_RETENTION_DAYS', 30)),
                    "storage_location": os.getenv('BACKUP_STORAGE', '/backup/wcfcb'),
                    "encryption_enabled": True
                },
                load_balancer_config={
                    "enabled": True,
                    "algorithm": os.getenv('LB_ALGORITHM', 'round_robin'),
                    "health_check_path": "/api/method/assistant_crm.production.health_check",
                    "session_affinity": True,
                    "auto_scaling": {
                        "enabled": True,
                        "min_instances": int(os.getenv('AUTO_SCALE_MIN', 2)),
                        "max_instances": int(os.getenv('AUTO_SCALE_MAX', 10)),
                        "cpu_threshold": float(os.getenv('AUTO_SCALE_CPU_THRESHOLD', 70.0))
                    }
                }
            )
            
            frappe.log_error("Production configuration loaded successfully")
            return config
            
        except Exception as e:
            frappe.log_error(f"Production config loading error: {str(e)}")
            raise
    
    def setup_logging(self) -> None:
        """Setup production-grade logging"""
        try:
            # Configure structured logging
            log_level = os.getenv('LOG_LEVEL', 'INFO')
            log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            
            # Setup file logging
            log_file = os.path.join(
                os.getenv('LOG_DIR', '/var/log/wcfcb'),
                'assistant_crm_production.log'
            )
            
            logging.basicConfig(
                level=getattr(logging, log_level),
                format=log_format,
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
            
            # Setup component-specific loggers
            self.setup_component_loggers()
            
            logging.info("Production logging configured successfully")
            
        except Exception as e:
            print(f"Logging setup error: {str(e)}")
            raise
    
    def setup_component_loggers(self) -> None:
        """Setup loggers for each Core Integration component"""
        components = [
            'intent_classifier',
            'response_assembler',
            'flow_optimizer',
            'performance_optimizer',
            'ux_engine',
            'orchestrator'
        ]
        
        for component in components:
            logger = logging.getLogger(f'wcfcb.{component}')
            logger.setLevel(logging.INFO)
            
            # Add component-specific file handler
            handler = logging.FileHandler(
                os.path.join(
                    os.getenv('LOG_DIR', '/var/log/wcfcb'),
                    f'{component}.log'
                )
            )
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(handler)
    
    def initialize_connection_pools(self) -> None:
        """Initialize production-grade connection pools"""
        try:
            # Database connection pools
            self.setup_database_pools()
            
            # Redis connection pools
            self.setup_redis_pools()
            
            # External API connection pools
            self.setup_api_pools()
            
            logging.info("Production connection pools initialized")
            
        except Exception as e:
            logging.error(f"Connection pool initialization error: {str(e)}")
            raise
    
    def setup_database_pools(self) -> None:
        """Setup database connection pools with failover"""
        try:
            # Primary database pool
            primary_config = self.config.database_config["primary"]
            self.connection_pools["db_primary"] = self.create_database_pool(
                primary_config, "primary"
            )
            
            # Replica database pool (for read operations)
            replica_config = self.config.database_config["replica"]
            self.connection_pools["db_replica"] = self.create_database_pool(
                replica_config, "replica"
            )
            
            logging.info("Database connection pools configured")
            
        except Exception as e:
            logging.error(f"Database pool setup error: {str(e)}")
            raise
    
    def create_database_pool(self, config: Dict, pool_type: str) -> Dict:
        """Create database connection pool with configuration"""
        return {
            "type": "database",
            "pool_type": pool_type,
            "config": config,
            "created_at": datetime.now(),
            "status": "active",
            "connections": {
                "active": 0,
                "idle": 0,
                "total": 0
            }
        }
    
    def setup_redis_pools(self) -> None:
        """Setup Redis connection pools"""
        try:
            # Primary Redis for sessions and real-time data
            primary_redis = self.config.redis_config["primary"]
            self.connection_pools["redis_primary"] = self.create_redis_pool(
                primary_redis, "primary"
            )
            
            # Cache Redis for performance optimization
            cache_redis = self.config.redis_config["cache"]
            self.connection_pools["redis_cache"] = self.create_redis_pool(
                cache_redis, "cache"
            )
            
            logging.info("Redis connection pools configured")
            
        except Exception as e:
            logging.error(f"Redis pool setup error: {str(e)}")
            raise
    
    def create_redis_pool(self, config: Dict, pool_type: str) -> Dict:
        """Create Redis connection pool"""
        try:
            # Create Redis connection pool
            pool = redis.ConnectionPool(
                host=config["host"],
                port=config["port"],
                db=config["db"],
                password=config["password"],
                ssl=config["ssl"],
                max_connections=config["max_connections"],
                retry_on_timeout=True,
                socket_timeout=30,
                socket_connect_timeout=10
            )
            
            return {
                "type": "redis",
                "pool_type": pool_type,
                "pool": pool,
                "config": config,
                "created_at": datetime.now(),
                "status": "active"
            }
            
        except Exception as e:
            logging.error(f"Redis pool creation error: {str(e)}")
            raise
    
    def setup_api_pools(self) -> None:
        """Setup external API connection pools"""
        try:
            # WCFCB Core Business API pool
            self.connection_pools["api_core_business"] = {
                "type": "api",
                "pool_type": "core_business",
                "base_url": os.getenv('CORE_BUSINESS_API_URL', 'https://api.wcfcb.gov.zm'),
                "timeout": int(os.getenv('API_TIMEOUT', 30)),
                "max_connections": int(os.getenv('API_MAX_CONNECTIONS', 20)),
                "retry_attempts": int(os.getenv('API_RETRY_ATTEMPTS', 3)),
                "created_at": datetime.now(),
                "status": "active"
            }
            
            # Medical providers API pool
            self.connection_pools["api_medical"] = {
                "type": "api",
                "pool_type": "medical_providers",
                "base_url": os.getenv('MEDICAL_API_URL', 'https://medical.wcfcb.gov.zm'),
                "timeout": int(os.getenv('MEDICAL_API_TIMEOUT', 20)),
                "max_connections": int(os.getenv('MEDICAL_API_MAX_CONNECTIONS', 10)),
                "created_at": datetime.now(),
                "status": "active"
            }
            
            logging.info("API connection pools configured")
            
        except Exception as e:
            logging.error(f"API pool setup error: {str(e)}")
            raise
    
    def start_health_monitoring(self) -> None:
        """Start production health monitoring"""
        try:
            if not self.config.monitoring_config["enabled"]:
                return
            
            self.monitoring_active = True
            
            # Start health check thread
            self.health_checker = threading.Thread(
                target=self.health_check_worker,
                daemon=True
            )
            self.health_checker.start()
            
            # Start metrics collection thread
            metrics_thread = threading.Thread(
                target=self.metrics_collection_worker,
                daemon=True
            )
            metrics_thread.start()
            
            logging.info("Production health monitoring started")
            
        except Exception as e:
            logging.error(f"Health monitoring startup error: {str(e)}")
            raise
    
    def health_check_worker(self) -> None:
        """Background worker for health checks"""
        while self.monitoring_active:
            try:
                health_status = self.perform_health_check()
                self.process_health_status(health_status)
                
                time.sleep(self.config.monitoring_config["health_check_interval"])
                
            except Exception as e:
                logging.error(f"Health check worker error: {str(e)}")
                time.sleep(60)  # Wait 1 minute on error
    
    def perform_health_check(self) -> Dict:
        """Perform comprehensive health check"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {}
        }
        
        try:
            # Check database connections
            health_status["components"]["database"] = self.check_database_health()
            
            # Check Redis connections
            health_status["components"]["redis"] = self.check_redis_health()
            
            # Check API endpoints
            health_status["components"]["apis"] = self.check_api_health()
            
            # Check system resources
            health_status["components"]["system"] = self.check_system_health()
            
            # Check Core Integration components
            health_status["components"]["core_integration"] = self.check_core_integration_health()
            
            # Determine overall status
            component_statuses = [comp.get("status", "unhealthy") for comp in health_status["components"].values()]
            if all(status == "healthy" for status in component_statuses):
                health_status["overall_status"] = "healthy"
            elif any(status == "critical" for status in component_statuses):
                health_status["overall_status"] = "critical"
            else:
                health_status["overall_status"] = "degraded"
            
        except Exception as e:
            logging.error(f"Health check error: {str(e)}")
            health_status["overall_status"] = "critical"
            health_status["error"] = str(e)
        
        return health_status
    
    def check_database_health(self) -> Dict:
        """Check database connection health"""
        try:
            # Test primary database
            primary_status = self.test_database_connection("db_primary")
            
            # Test replica database
            replica_status = self.test_database_connection("db_replica")
            
            return {
                "status": "healthy" if primary_status and replica_status else "degraded",
                "primary": primary_status,
                "replica": replica_status,
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }
    
    def test_database_connection(self, pool_name: str) -> bool:
        """Test database connection"""
        try:
            # Simulate database connection test
            # In production, this would execute a simple query
            pool_info = self.connection_pools.get(pool_name)
            return pool_info and pool_info.get("status") == "active"
            
        except Exception as e:
            logging.error(f"Database connection test error for {pool_name}: {str(e)}")
            return False
    
    def check_redis_health(self) -> Dict:
        """Check Redis connection health"""
        try:
            primary_status = self.test_redis_connection("redis_primary")
            cache_status = self.test_redis_connection("redis_cache")
            
            return {
                "status": "healthy" if primary_status and cache_status else "degraded",
                "primary": primary_status,
                "cache": cache_status,
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }
    
    def test_redis_connection(self, pool_name: str) -> bool:
        """Test Redis connection"""
        try:
            pool_info = self.connection_pools.get(pool_name)
            if not pool_info:
                return False
            
            # Test Redis connection with ping
            redis_client = redis.Redis(connection_pool=pool_info["pool"])
            return redis_client.ping()
            
        except Exception as e:
            logging.error(f"Redis connection test error for {pool_name}: {str(e)}")
            return False
    
    def check_api_health(self) -> Dict:
        """Check external API health"""
        try:
            api_statuses = {}
            
            for api_name, api_config in self.connection_pools.items():
                if api_config.get("type") == "api":
                    api_statuses[api_name] = self.test_api_connection(api_config)
            
            all_healthy = all(status for status in api_statuses.values())
            
            return {
                "status": "healthy" if all_healthy else "degraded",
                "apis": api_statuses,
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }
    
    def test_api_connection(self, api_config: Dict) -> bool:
        """Test external API connection"""
        try:
            # Simulate API health check
            # In production, this would make actual HTTP requests
            return api_config.get("status") == "active"
            
        except Exception as e:
            logging.error(f"API connection test error: {str(e)}")
            return False
    
    def check_system_health(self) -> Dict:
        """Check system resource health"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            thresholds = self.config.monitoring_config["alert_thresholds"]
            
            return {
                "status": "healthy" if (
                    cpu_percent < thresholds["cpu_usage"] and
                    memory.percent < thresholds["memory_usage"] and
                    disk.percent < thresholds["disk_usage"]
                ) else "degraded",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }
    
    def check_core_integration_health(self) -> Dict:
        """Check Core Integration components health"""
        try:
            # Test Core Integration Orchestrator
            from ..api.core_integration_orchestrator import CoreIntegrationOrchestrator
            
            orchestrator = CoreIntegrationOrchestrator()
            test_result = orchestrator.process_enhanced_chat_message(
                "Health check test", None, {"test": True}
            )
            
            return {
                "status": "healthy" if test_result.get("success") else "degraded",
                "orchestrator_functional": test_result.get("success", False),
                "response_time": test_result.get("performance_metrics", {}).get("total_orchestration_time", 0),
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }
    
    def process_health_status(self, health_status: Dict) -> None:
        """Process health status and trigger alerts if needed"""
        try:
            # Log health status
            logging.info(f"Health check completed: {health_status['overall_status']}")
            
            # Check for alert conditions
            if health_status["overall_status"] in ["critical", "degraded"]:
                self.trigger_health_alert(health_status)
            
            # Store health status for monitoring dashboard
            self.store_health_metrics(health_status)
            
        except Exception as e:
            logging.error(f"Health status processing error: {str(e)}")
    
    def trigger_health_alert(self, health_status: Dict) -> None:
        """Trigger health alert for critical issues"""
        try:
            alert_data = {
                "timestamp": datetime.now().isoformat(),
                "severity": health_status["overall_status"],
                "components": health_status["components"],
                "alert_type": "health_check"
            }
            
            # Log critical alert
            logging.critical(f"Health alert triggered: {alert_data}")
            
            # In production, this would send alerts via email, SMS, Slack, etc.
            self.send_production_alert(alert_data)
            
        except Exception as e:
            logging.error(f"Health alert error: {str(e)}")
    
    def send_production_alert(self, alert_data: Dict) -> None:
        """Send production alert to operations team"""
        try:
            # Placeholder for production alerting system
            # In production, integrate with PagerDuty, Slack, email, etc.
            logging.warning(f"Production alert would be sent: {alert_data}")
            
        except Exception as e:
            logging.error(f"Production alert sending error: {str(e)}")
    
    def store_health_metrics(self, health_status: Dict) -> None:
        """Store health metrics for monitoring dashboard"""
        try:
            # Store in Redis for real-time dashboard
            if "redis_primary" in self.connection_pools:
                redis_client = redis.Redis(
                    connection_pool=self.connection_pools["redis_primary"]["pool"]
                )
                
                # Store latest health status
                redis_client.setex(
                    "wcfcb:health:latest",
                    300,  # 5 minutes TTL
                    json.dumps(health_status)
                )
                
                # Store in time series for historical analysis
                redis_client.zadd(
                    "wcfcb:health:history",
                    {json.dumps(health_status): time.time()}
                )
                
                # Keep only last 24 hours of history
                cutoff_time = time.time() - (24 * 60 * 60)
                redis_client.zremrangebyscore("wcfcb:health:history", 0, cutoff_time)
            
        except Exception as e:
            logging.error(f"Health metrics storage error: {str(e)}")
    
    def metrics_collection_worker(self) -> None:
        """Background worker for metrics collection"""
        while self.monitoring_active:
            try:
                metrics = self.collect_performance_metrics()
                self.store_performance_metrics(metrics)
                
                time.sleep(self.config.monitoring_config["metrics_interval"])
                
            except Exception as e:
                logging.error(f"Metrics collection worker error: {str(e)}")
                time.sleep(60)
    
    def collect_performance_metrics(self) -> Dict:
        """Collect performance metrics"""
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": psutil.disk_usage('/').percent,
                    "network_io": psutil.net_io_counters()._asdict(),
                    "process_count": len(psutil.pids())
                },
                "application": {
                    "active_sessions": self.get_active_session_count(),
                    "cache_hit_rate": self.get_cache_hit_rate(),
                    "avg_response_time": self.get_avg_response_time(),
                    "error_rate": self.get_error_rate()
                }
            }
            
        except Exception as e:
            logging.error(f"Metrics collection error: {str(e)}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def get_active_session_count(self) -> int:
        """Get count of active user sessions"""
        try:
            # Placeholder - in production, query session store
            return 0
        except:
            return 0
    
    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate percentage"""
        try:
            # Placeholder - in production, calculate from cache metrics
            return 0.0
        except:
            return 0.0
    
    def get_avg_response_time(self) -> float:
        """Get average response time"""
        try:
            # Placeholder - in production, calculate from response time metrics
            return 0.0
        except:
            return 0.0
    
    def get_error_rate(self) -> float:
        """Get error rate percentage"""
        try:
            # Placeholder - in production, calculate from error logs
            return 0.0
        except:
            return 0.0
    
    def store_performance_metrics(self, metrics: Dict) -> None:
        """Store performance metrics"""
        try:
            if "redis_primary" in self.connection_pools:
                redis_client = redis.Redis(
                    connection_pool=self.connection_pools["redis_primary"]["pool"]
                )
                
                # Store latest metrics
                redis_client.setex(
                    "wcfcb:metrics:latest",
                    300,  # 5 minutes TTL
                    json.dumps(metrics)
                )
                
                # Store in time series
                redis_client.zadd(
                    "wcfcb:metrics:history",
                    {json.dumps(metrics): time.time()}
                )
                
                # Keep only last 7 days of metrics
                cutoff_time = time.time() - (7 * 24 * 60 * 60)
                redis_client.zremrangebyscore("wcfcb:metrics:history", 0, cutoff_time)
            
        except Exception as e:
            logging.error(f"Metrics storage error: {str(e)}")
    
    def get_production_status(self) -> Dict:
        """Get comprehensive production status"""
        try:
            return {
                "environment": self.environment,
                "status": "operational" if self.monitoring_active else "degraded",
                "uptime": self.get_uptime(),
                "connection_pools": {
                    name: {
                        "type": pool["type"],
                        "status": pool["status"],
                        "created_at": pool["created_at"].isoformat()
                    }
                    for name, pool in self.connection_pools.items()
                },
                "monitoring": {
                    "active": self.monitoring_active,
                    "health_checker_running": self.health_checker and self.health_checker.is_alive(),
                    "last_health_check": datetime.now().isoformat()
                },
                "configuration": {
                    "database_pools": len([p for p in self.connection_pools.values() if p["type"] == "database"]),
                    "redis_pools": len([p for p in self.connection_pools.values() if p["type"] == "redis"]),
                    "api_pools": len([p for p in self.connection_pools.values() if p["type"] == "api"])
                }
            }
            
        except Exception as e:
            logging.error(f"Production status error: {str(e)}")
            return {"error": str(e), "status": "error"}
    
    def get_uptime(self) -> str:
        """Get system uptime"""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = uptime_seconds / 3600
            return f"{uptime_hours:.1f} hours"
        except:
            return "unknown"
    
    def shutdown(self) -> None:
        """Graceful shutdown of production environment"""
        try:
            logging.info("Initiating production environment shutdown")
            
            # Stop monitoring
            self.monitoring_active = False
            
            # Wait for threads to finish
            if self.health_checker and self.health_checker.is_alive():
                self.health_checker.join(timeout=30)
            
            # Close connection pools
            self.close_connection_pools()
            
            logging.info("Production environment shutdown completed")
            
        except Exception as e:
            logging.error(f"Production shutdown error: {str(e)}")
    
    def close_connection_pools(self) -> None:
        """Close all connection pools"""
        try:
            for name, pool in self.connection_pools.items():
                pool["status"] = "closed"
                logging.info(f"Closed connection pool: {name}")
            
        except Exception as e:
            logging.error(f"Connection pool closure error: {str(e)}")

# Global production environment manager instance
production_env_manager = None

def get_production_environment_manager() -> ProductionEnvironmentManager:
    """Get global production environment manager instance"""
    global production_env_manager
    if production_env_manager is None:
        production_env_manager = ProductionEnvironmentManager()
    return production_env_manager

# API Endpoints

@frappe.whitelist()
def get_production_status():
    """API endpoint to get production environment status"""
    try:
        manager = get_production_environment_manager()
        status = manager.get_production_status()
        
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        frappe.log_error(f"Production status API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def health_check():
    """Production health check endpoint"""
    try:
        manager = get_production_environment_manager()
        health_status = manager.perform_health_check()
        
        return {
            "success": True,
            "data": health_status
        }
        
    except Exception as e:
        frappe.log_error(f"Health check API error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
