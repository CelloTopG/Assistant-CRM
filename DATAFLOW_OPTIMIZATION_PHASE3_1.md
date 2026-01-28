# **PHASE 3.1: MONITORING AND PERFORMANCE METRICS**

## **Objective**
Implement comprehensive monitoring, logging, and performance metrics to ensure production readiness and maintain the 100% success rate achieved in live data integration.

## **Technical Specifications**

### **3.1.1: Performance Monitoring Service**

**File:** `assistant_crm/services/performance_monitoring_service.py`

```python
#!/usr/bin/env python3
"""
Performance Monitoring Service for Assistant CRM
Comprehensive monitoring and metrics collection for production deployment
"""

import time
import json
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque

class PerformanceMonitoringService:
    """
    Comprehensive performance monitoring with real-time metrics and alerting
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics = {
            'response_times': deque(maxlen=max_history),
            'intent_distribution': defaultdict(int),
            'error_rates': defaultdict(int),
            'cache_performance': defaultdict(int),
            'user_activity': defaultdict(int),
            'system_health': defaultdict(list)
        }
        self.alerts = []
        self.thresholds = {
            'response_time_warning': 1000,  # 1 second
            'response_time_critical': 3000,  # 3 seconds
            'error_rate_warning': 5,        # 5%
            'error_rate_critical': 10,      # 10%
            'cache_hit_rate_warning': 70,   # 70%
            'cache_hit_rate_critical': 50   # 50%
        }
        self.lock = threading.Lock()
    
    def record_request(self, intent: str, response_time: float, success: bool, 
                      cache_hit: bool = False, user_id: str = "unknown") -> None:
        """Record request metrics"""
        with self.lock:
            # Record response time
            self.metrics['response_times'].append({
                'timestamp': time.time(),
                'response_time': response_time,
                'intent': intent,
                'success': success
            })
            
            # Record intent distribution
            self.metrics['intent_distribution'][intent] += 1
            
            # Record error rates
            if not success:
                self.metrics['error_rates'][intent] += 1
            
            # Record cache performance
            cache_key = 'hit' if cache_hit else 'miss'
            self.metrics['cache_performance'][cache_key] += 1
            
            # Record user activity
            self.metrics['user_activity'][user_id] += 1
            
            # Check thresholds and generate alerts
            self._check_thresholds(intent, response_time, success)
    
    def record_system_metric(self, metric_name: str, value: float) -> None:
        """Record system-level metrics"""
        with self.lock:
            self.metrics['system_health'][metric_name].append({
                'timestamp': time.time(),
                'value': value
            })
            
            # Keep only recent metrics
            if len(self.metrics['system_health'][metric_name]) > self.max_history:
                self.metrics['system_health'][metric_name] = \
                    self.metrics['system_health'][metric_name][-self.max_history:]
    
    def get_performance_summary(self, time_window: int = 3600) -> Dict[str, Any]:
        """Get performance summary for specified time window (seconds)"""
        current_time = time.time()
        cutoff_time = current_time - time_window
        
        with self.lock:
            # Filter recent response times
            recent_responses = [
                r for r in self.metrics['response_times'] 
                if r['timestamp'] > cutoff_time
            ]
            
            if not recent_responses:
                return self._empty_summary()
            
            # Calculate metrics
            response_times = [r['response_time'] for r in recent_responses]
            successful_requests = [r for r in recent_responses if r['success']]
            
            # Cache performance
            total_cache_requests = (
                self.metrics['cache_performance']['hit'] + 
                self.metrics['cache_performance']['miss']
            )
            cache_hit_rate = (
                (self.metrics['cache_performance']['hit'] / max(total_cache_requests, 1)) * 100
            )
            
            return {
                'time_window_hours': time_window / 3600,
                'total_requests': len(recent_responses),
                'successful_requests': len(successful_requests),
                'success_rate': (len(successful_requests) / len(recent_responses)) * 100,
                'response_times': {
                    'average': sum(response_times) / len(response_times),
                    'min': min(response_times),
                    'max': max(response_times),
                    'p95': self._percentile(response_times, 95),
                    'p99': self._percentile(response_times, 99)
                },
                'cache_performance': {
                    'hit_rate': round(cache_hit_rate, 2),
                    'total_hits': self.metrics['cache_performance']['hit'],
                    'total_misses': self.metrics['cache_performance']['miss']
                },
                'intent_distribution': dict(self.metrics['intent_distribution']),
                'active_alerts': len(self.alerts),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics for dashboard"""
        recent_window = 300  # 5 minutes
        current_time = time.time()
        cutoff_time = current_time - recent_window
        
        with self.lock:
            recent_responses = [
                r for r in self.metrics['response_times'] 
                if r['timestamp'] > cutoff_time
            ]
            
            if not recent_responses:
                return {'status': 'no_recent_activity'}
            
            avg_response_time = sum(r['response_time'] for r in recent_responses) / len(recent_responses)
            success_rate = (
                sum(1 for r in recent_responses if r['success']) / len(recent_responses) * 100
            )
            
            return {
                'status': 'active',
                'requests_per_minute': len(recent_responses) / 5,
                'average_response_time': round(avg_response_time, 2),
                'success_rate': round(success_rate, 2),
                'active_alerts': len(self.alerts),
                'timestamp': datetime.now().isoformat()
            }
    
    def _check_thresholds(self, intent: str, response_time: float, success: bool) -> None:
        """Check performance thresholds and generate alerts"""
        # Response time alerts
        if response_time > self.thresholds['response_time_critical']:
            self._create_alert('critical', f'Response time critical: {response_time:.2f}ms for {intent}')
        elif response_time > self.thresholds['response_time_warning']:
            self._create_alert('warning', f'Response time warning: {response_time:.2f}ms for {intent}')
        
        # Error rate alerts (check recent error rate)
        recent_requests = list(self.metrics['response_times'])[-100:]  # Last 100 requests
        if recent_requests:
            error_rate = (
                sum(1 for r in recent_requests if not r['success']) / len(recent_requests) * 100
            )
            
            if error_rate > self.thresholds['error_rate_critical']:
                self._create_alert('critical', f'Error rate critical: {error_rate:.1f}%')
            elif error_rate > self.thresholds['error_rate_warning']:
                self._create_alert('warning', f'Error rate warning: {error_rate:.1f}%')
    
    def _create_alert(self, severity: str, message: str) -> None:
        """Create performance alert"""
        alert = {
            'severity': severity,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'id': f"{severity}_{int(time.time())}"
        }
        
        self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0
        
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary when no data available"""
        return {
            'time_window_hours': 0,
            'total_requests': 0,
            'successful_requests': 0,
            'success_rate': 0,
            'response_times': {'average': 0, 'min': 0, 'max': 0, 'p95': 0, 'p99': 0},
            'cache_performance': {'hit_rate': 0, 'total_hits': 0, 'total_misses': 0},
            'intent_distribution': {},
            'active_alerts': 0,
            'timestamp': datetime.now().isoformat()
        }

# Global monitoring service
_monitoring_service = None

def get_monitoring_service() -> PerformanceMonitoringService:
    """Get global monitoring service instance"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = PerformanceMonitoringService()
    return _monitoring_service
```

### **3.1.2: Monitoring API Endpoints**

**File:** `assistant_crm/api/monitoring_api.py`

```python
#!/usr/bin/env python3
"""
Monitoring API for Assistant CRM
Provides performance metrics and health check endpoints
"""

try:
    import frappe
    from frappe import _
    FRAPPE_AVAILABLE = True
except ImportError:
    frappe = None
    _ = lambda x: x
    FRAPPE_AVAILABLE = False

from assistant_crm.services.performance_monitoring_service import get_monitoring_service
from assistant_crm.services.enhanced_cache_service import get_cache_service
from assistant_crm.api.master_chat_api import get_master_chat_api

if FRAPPE_AVAILABLE:
    @frappe.whitelist()
    def get_performance_dashboard():
        """Get comprehensive performance dashboard data"""
        try:
            monitoring = get_monitoring_service()
            cache_service = get_cache_service()
            chat_api = get_master_chat_api()
            
            return {
                'performance_summary': monitoring.get_performance_summary(),
                'real_time_metrics': monitoring.get_real_time_metrics(),
                'cache_stats': cache_service.get_performance_stats(),
                'api_stats': chat_api.get_api_stats(),
                'system_status': 'operational'
            }
        except Exception as e:
            return {'error': str(e), 'system_status': 'error'}
    
    @frappe.whitelist()
    def health_check():
        """Simple health check endpoint"""
        try:
            monitoring = get_monitoring_service()
            real_time = monitoring.get_real_time_metrics()
            
            # Determine health status
            if real_time.get('status') == 'no_recent_activity':
                status = 'idle'
            elif real_time.get('success_rate', 0) > 95 and real_time.get('average_response_time', 0) < 1000:
                status = 'healthy'
            elif real_time.get('success_rate', 0) > 90:
                status = 'warning'
            else:
                status = 'critical'
            
            return {
                'status': status,
                'timestamp': real_time.get('timestamp'),
                'metrics': real_time
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
```

## **Implementation Steps**

### **Step 1: Create Performance Monitoring Service (4 hours)**
1. Implement comprehensive metrics collection
2. Add real-time performance tracking
3. Implement alerting system with configurable thresholds

### **Step 2: Create Monitoring API Endpoints (2 hours)**
1. Implement performance dashboard API
2. Add health check endpoint
3. Integrate with existing services

### **Step 3: Integrate with Existing Services (2 hours)**
1. Add monitoring calls to master chat API
2. Integrate with intent router and cache service
3. Add performance tracking to all critical paths

## **Expected Results**
- **Real-time Monitoring:** Live performance metrics and alerting
- **Production Visibility:** Comprehensive dashboard for system health
- **Proactive Alerting:** Early warning system for performance issues
- **Performance Optimization:** Data-driven optimization opportunities

## **Success Metrics**
- 100% uptime monitoring coverage
- Alert response time < 30 seconds
- Performance dashboard load time < 2 seconds
- Zero monitoring overhead impact on chat performance
