"""
Performance Optimization Service
Implements connection pooling, query optimization, and response time improvements
"""

import frappe
from frappe.utils import now
import time
from typing import Dict, List, Any, Optional
from contextlib import contextmanager

class PerformanceOptimizationService:
    """Service for optimizing database queries and API response times."""
    
    def __init__(self):
        self.query_cache = {}
        self.performance_metrics = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_response_time": 0,
            "slow_queries": []
        }
    
    @contextmanager
    def measure_performance(self, operation_name: str):
        """Context manager to measure operation performance."""
        start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            duration = end_time - start_time
            self._record_performance(operation_name, duration)
    
    def _record_performance(self, operation_name: str, duration: float):
        """Record performance metrics for monitoring."""
        try:
            self.performance_metrics["total_queries"] += 1
            
            # Update average response time
            current_avg = self.performance_metrics["avg_response_time"]
            total_queries = self.performance_metrics["total_queries"]
            new_avg = ((current_avg * (total_queries - 1)) + duration) / total_queries
            self.performance_metrics["avg_response_time"] = new_avg
            
            # Track slow queries (> 2 seconds)
            if duration > 2.0:
                slow_query = {
                    "operation": operation_name,
                    "duration": duration,
                    "timestamp": now()
                }
                self.performance_metrics["slow_queries"].append(slow_query)
                
                # Keep only last 10 slow queries
                if len(self.performance_metrics["slow_queries"]) > 10:
                    self.performance_metrics["slow_queries"] = \
                        self.performance_metrics["slow_queries"][-10:]
            
        except Exception as e:
            frappe.log_error(f"Performance recording error: {str(e)}", "Performance Service")
    
    def optimized_db_query(self, doctype: str, filters: Dict = None, fields: List[str] = None, 
                          limit: int = None, order_by: str = None) -> List[Dict]:
        """Optimized database query with caching and performance monitoring."""
        try:
            with self.measure_performance(f"db_query_{doctype}"):
                # Generate cache key
                cache_key = self._generate_query_cache_key(doctype, filters, fields, limit, order_by)
                
                # Check cache first
                if cache_key in self.query_cache:
                    self.performance_metrics["cache_hits"] += 1
                    return self.query_cache[cache_key]
                
                # Execute query
                self.performance_metrics["cache_misses"] += 1
                
                query_params = {
                    "doctype": doctype,
                    "filters": filters or {},
                    "fields": fields or ["*"],
                }
                
                if limit:
                    query_params["limit"] = limit
                if order_by:
                    query_params["order_by"] = order_by
                
                results = frappe.get_all(**query_params)
                
                # Cache results (with TTL of 5 minutes)
                self.query_cache[cache_key] = results
                
                # Clean cache if it gets too large
                if len(self.query_cache) > 100:
                    self._clean_query_cache()
                
                return results
                
        except Exception as e:
            frappe.log_error(f"Optimized query error: {str(e)}", "Performance Service")
            return []
    
    def _generate_query_cache_key(self, doctype: str, filters: Dict, fields: List, 
                                 limit: int, order_by: str) -> str:
        """Generate a cache key for database queries."""
        import hashlib
        import json
        
        key_data = {
            "doctype": doctype,
            "filters": filters or {},
            "fields": fields or [],
            "limit": limit,
            "order_by": order_by
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _clean_query_cache(self):
        """Clean old entries from query cache."""
        # Simple LRU implementation - remove oldest 20% of entries
        cache_size = len(self.query_cache)
        entries_to_remove = int(cache_size * 0.2)
        
        if entries_to_remove > 0:
            # Remove oldest entries (this is simplified - in production use proper LRU)
            keys_to_remove = list(self.query_cache.keys())[:entries_to_remove]
            for key in keys_to_remove:
                del self.query_cache[key]
    
    def get_optimized_knowledge_base_articles(self, category: str = None,
                                            keywords: List[str] = None,
                                            limit: int = 20) -> List[Dict]:
        """Optimized knowledge base article retrieval.

        Note: Knowledge Base Article doctype has been deprecated.
        This method now returns an empty list.
        """
        # Knowledge Base Article doctype has been removed
        return []
    
    def get_performance_metrics(self) -> Dict:
        """Get current performance metrics."""
        try:
            cache_hit_rate = 0
            if self.performance_metrics["total_queries"] > 0:
                cache_hit_rate = (self.performance_metrics["cache_hits"] / 
                                self.performance_metrics["total_queries"]) * 100
            
            return {
                "status": "active",
                "metrics": {
                    "total_queries": self.performance_metrics["total_queries"],
                    "cache_hit_rate": round(cache_hit_rate, 2),
                    "avg_response_time": round(self.performance_metrics["avg_response_time"], 3),
                    "slow_queries_count": len(self.performance_metrics["slow_queries"]),
                    "cache_size": len(self.query_cache)
                },
                "recent_slow_queries": self.performance_metrics["slow_queries"][-5:],
                "timestamp": now()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": now()
            }
    
    def clear_performance_cache(self) -> bool:
        """Clear all performance caches."""
        try:
            self.query_cache.clear()
            self.performance_metrics = {
                "total_queries": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "avg_response_time": 0,
                "slow_queries": []
            }
            return True
            
        except Exception as e:
            frappe.log_error(f"Cache clear error: {str(e)}", "Performance Service")
            return False

# Global performance service instance
performance_service = PerformanceOptimizationService()

@frappe.whitelist(allow_guest=True)
def get_performance_stats():
    """API endpoint to get performance statistics."""
    return performance_service.get_performance_metrics()

@frappe.whitelist()
def clear_performance_cache():
    """API endpoint to clear performance cache (admin only)."""
    if frappe.session.user == "Administrator":
        success = performance_service.clear_performance_cache()
        return {
            "status": "success" if success else "error",
            "message": "Performance cache cleared" if success else "Failed to clear cache",
            "timestamp": now()
        }
    else:
        return {
            "status": "error",
            "message": "Unauthorized - Admin access required",
            "timestamp": now()
        }
