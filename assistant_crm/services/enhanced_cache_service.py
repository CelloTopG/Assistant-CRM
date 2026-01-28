#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Cache Service for Assistant CRM
Provides intelligent caching with TTL, invalidation, and performance monitoring
Designed for future single dataflow architecture integration
"""

import time
import json
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

class EnhancedCacheService:
    """
    Intelligent caching service with performance optimization
    Designed to support future unified dataflow architecture
    """
    
    def __init__(self):
        self.cache_store = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'total_requests': 0,
            'dataflow_optimization_enabled': True
        }
        # TTL configuration optimized for single dataflow
        self.ttl_config = {
            'live_data': 300,      # 5 minutes for live data
            'knowledge_base': 3600, # 1 hour for knowledge base
            'user_context': 1800,   # 30 minutes for user context
            'intent_routing': 600,  # 10 minutes for intent routing
            'unified_response': 180 # 3 minutes for unified responses (future)
        }
        self.performance_metrics = {
            'cache_efficiency': 0.0,
            'memory_usage': 0,
            'avg_retrieval_time': 0.0
        }
    
    def get_cache_key(self, intent: str, user_context: Dict[str, Any], message: str = "") -> str:
        """
        Generate unique cache key for request
        Optimized for future single dataflow architecture
        """
        # Simplified key generation for unified dataflow
        key_data = {
            'intent': intent,
            'user_id': user_context.get('user_id', 'guest'),
            'user_role': user_context.get('user_role', 'guest'),
            'message_hash': hashlib.md5(message.encode()).hexdigest()[:8] if message else ''
        }
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def get(self, cache_key: str, cache_type: str = 'live_data') -> Optional[Dict[str, Any]]:
        """
        Retrieve cached data with TTL validation
        Supports future unified dataflow patterns
        """
        start_time = time.time()
        self.cache_stats['total_requests'] += 1
        
        if cache_key not in self.cache_store:
            self.cache_stats['misses'] += 1
            self._update_performance_metrics(start_time, False)
            return None
        
        cached_item = self.cache_store[cache_key]
        ttl = self.ttl_config.get(cache_type, 300)
        
        # Check if cache is expired
        if time.time() - cached_item['timestamp'] > ttl:
            del self.cache_store[cache_key]
            self.cache_stats['misses'] += 1
            self._update_performance_metrics(start_time, False)
            return None
        
        self.cache_stats['hits'] += 1
        self._update_performance_metrics(start_time, True)
        return cached_item['data']
    
    def set(self, cache_key: str, data: Dict[str, Any], cache_type: str = 'live_data') -> None:
        """
        Store data in cache with timestamp
        Prepared for unified dataflow integration
        """
        self.cache_store[cache_key] = {
            'data': data,
            'timestamp': time.time(),
            'cache_type': cache_type,
            'dataflow_version': '1.0'  # For future compatibility
        }
        
        # Update memory usage estimate
        self.performance_metrics['memory_usage'] = len(self.cache_store)
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern
        Supports future bulk invalidation for unified dataflow
        """
        invalidated = 0
        keys_to_remove = []
        
        for key in self.cache_store.keys():
            if pattern in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache_store[key]
            invalidated += 1
        
        self.cache_stats['invalidations'] += invalidated
        self.performance_metrics['memory_usage'] = len(self.cache_store)
        return invalidated
    
    def invalidate_user_cache(self, user_id: str) -> int:
        """
        Invalidate all cache entries for specific user
        Useful for authentication bypass scenarios
        """
        return self.invalidate_pattern(user_id)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics
        Enhanced for dataflow optimization monitoring
        """
        total = self.cache_stats['total_requests']
        if total == 0:
            hit_rate = 0
        else:
            hit_rate = (self.cache_stats['hits'] / total) * 100
        
        # Calculate cache efficiency
        self.performance_metrics['cache_efficiency'] = hit_rate
        
        return {
            'hit_rate': round(hit_rate, 2),
            'cache_stats': self.cache_stats,
            'cache_size': len(self.cache_store),
            'performance_metrics': self.performance_metrics,
            'ttl_config': self.ttl_config,
            'dataflow_optimization_ready': True
        }
    
    def _update_performance_metrics(self, start_time: float, cache_hit: bool) -> None:
        """Update performance metrics for monitoring"""
        retrieval_time = time.time() - start_time
        
        # Update average retrieval time
        total_requests = self.cache_stats['total_requests']
        if total_requests > 0:
            current_avg = self.performance_metrics['avg_retrieval_time']
            self.performance_metrics['avg_retrieval_time'] = (
                (current_avg * (total_requests - 1) + retrieval_time) / total_requests
            )
    
    def prepare_for_unified_dataflow(self) -> Dict[str, Any]:
        """
        Prepare cache service for future unified dataflow integration
        Returns configuration and dependencies
        """
        return {
            'cache_ready': True,
            'unified_dataflow_support': True,
            'dependencies': {
                'response_assembler_removal': 'pending',
                'session_management_removal': 'pending',
                'authentication_bypass': 'pending',
                'single_api_endpoint': 'pending'
            },
            'migration_notes': [
                'Cache keys optimized for unified dataflow',
                'TTL configuration supports direct AI integration',
                'Performance metrics ready for single dataflow monitoring',
                'User cache invalidation prepared for auth bypass'
            ]
        }
    
    def clear_all_cache(self) -> int:
        """Clear all cache entries (for testing and rollback)"""
        cache_size = len(self.cache_store)
        self.cache_store.clear()
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'total_requests': 0,
            'dataflow_optimization_enabled': True
        }
        self.performance_metrics['memory_usage'] = 0
        return cache_size

# Global cache instance
_cache_service = None

def get_cache_service() -> EnhancedCacheService:
    """Get global cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = EnhancedCacheService()
    return _cache_service

def reset_cache_service() -> None:
    """Reset cache service (for testing and rollback)"""
    global _cache_service
    _cache_service = None
