# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from frappe.utils import now_datetime, add_to_date


class CacheService:
    """Intelligent caching service for API responses and chatbot interactions"""
    
    def __init__(self):
        self.cache_prefix = "assistant_crm_cache"
        self.default_ttl = 3600  # 1 hour default TTL
        self.max_cache_size = 1000  # Maximum number of cached items
        
    def _generate_cache_key(self, message: str, context: Dict[str, Any] = None) -> str:
        """Generate a unique cache key for the message and context"""
        # Normalize message for better cache hits
        normalized_message = message.lower().strip()
        
        # Include relevant context in cache key
        context_str = ""
        if context:
            # Only include stable context elements
            stable_context = {
                "language": context.get("language", "en"),
                "channel_type": context.get("channel_type", "web"),
                "user_type": context.get("user_type", "guest")
            }
            context_str = json.dumps(stable_context, sort_keys=True)
        
        # Create hash of message + context
        cache_input = f"{normalized_message}|{context_str}"
        cache_hash = hashlib.md5(cache_input.encode()).hexdigest()
        
        return f"{self.cache_prefix}:response:{cache_hash}"
    
    def get_cached_response(self, message: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Get cached response for a message"""
        try:
            cache_key = self._generate_cache_key(message, context)
            cached_data = frappe.cache().get_value(cache_key)
            
            if cached_data:
                # Check if cache is still valid
                if self._is_cache_valid(cached_data):
                    # Update access time for LRU
                    cached_data["last_accessed"] = now_datetime().isoformat()
                    frappe.cache().set_value(cache_key, cached_data, expires_in_sec=self.default_ttl)
                    
                    return {
                        "response": cached_data["response"],
                        "context_data": cached_data.get("context_data", {}),
                        "cached": True,
                        "cache_timestamp": cached_data["timestamp"]
                    }
                else:
                    # Remove expired cache
                    frappe.cache().delete_value(cache_key)
            
            return None
            
        except Exception as e:
            frappe.log_error(f"Error retrieving cached response: {str(e)}", "Cache Service")
            return None
    
    def cache_response(self, message: str, response: Dict[str, Any], context: Dict[str, Any] = None, ttl: int = None) -> bool:
        """Cache a response for future use"""
        try:
            cache_key = self._generate_cache_key(message, context)
            ttl = ttl or self.default_ttl
            
            # Prepare cache data
            cache_data = {
                "response": response.get("response", ""),
                "context_data": response.get("context_data", {}),
                "timestamp": now_datetime().isoformat(),
                "last_accessed": now_datetime().isoformat(),
                "message_hash": hashlib.md5(message.encode()).hexdigest(),
                "ttl": ttl
            }
            
            # Store in cache
            frappe.cache().set_value(cache_key, cache_data, expires_in_sec=ttl)
            
            # Update cache statistics
            self._update_cache_stats("cache_set")
            
            return True
            
        except Exception as e:
            frappe.log_error(f"Error caching response: {str(e)}", "Cache Service")
            return False
    
    def _is_cache_valid(self, cached_data: Dict[str, Any]) -> bool:
        """Check if cached data is still valid"""
        try:
            timestamp = datetime.fromisoformat(cached_data["timestamp"])
            ttl = cached_data.get("ttl", self.default_ttl)
            expiry_time = timestamp + timedelta(seconds=ttl)
            
            return now_datetime() < expiry_time
            
        except Exception:
            return False
    
    def clear_cache(self, pattern: str = None) -> int:
        """Clear cache entries matching pattern"""
        try:
            if pattern:
                # Clear specific pattern
                cache_key = f"{self.cache_prefix}:{pattern}:*"
            else:
                # Clear all assistant_crm cache
                cache_key = f"{self.cache_prefix}:*"
            
            # Note: Frappe cache doesn't support pattern deletion
            # This is a simplified implementation
            frappe.cache().delete_value(cache_key)
            
            self._update_cache_stats("cache_clear")
            return 1
            
        except Exception as e:
            frappe.log_error(f"Error clearing cache: {str(e)}", "Cache Service")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache usage statistics"""
        try:
            stats_key = f"{self.cache_prefix}:stats"
            stats = frappe.cache().get_value(stats_key) or {
                "cache_hits": 0,
                "cache_misses": 0,
                "cache_sets": 0,
                "cache_clears": 0,
                "last_reset": now_datetime().isoformat()
            }
            
            # Calculate hit rate
            total_requests = stats["cache_hits"] + stats["cache_misses"]
            hit_rate = (stats["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
            
            stats["hit_rate"] = round(hit_rate, 2)
            stats["total_requests"] = total_requests
            
            return stats
            
        except Exception as e:
            frappe.log_error(f"Error getting cache stats: {str(e)}", "Cache Service")
            return {}
    
    def _update_cache_stats(self, operation: str):
        """Update cache statistics"""
        try:
            stats_key = f"{self.cache_prefix}:stats"
            stats = frappe.cache().get_value(stats_key) or {
                "cache_hits": 0,
                "cache_misses": 0,
                "cache_sets": 0,
                "cache_clears": 0,
                "last_reset": now_datetime().isoformat()
            }
            
            if operation in stats:
                stats[operation] += 1
            
            # Store updated stats (24 hour expiry)
            frappe.cache().set_value(stats_key, stats, expires_in_sec=86400)
            
        except Exception as e:
            frappe.log_error(f"Error updating cache stats: {str(e)}", "Cache Service")
    
    def get_similar_responses(self, message: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get similar cached responses for fallback purposes"""
        # This is a simplified implementation
        # In a production system, you might use vector similarity or fuzzy matching
        try:
            # For now, return empty list as this requires more complex implementation
            return []
            
        except Exception as e:
            frappe.log_error(f"Error getting similar responses: {str(e)}", "Cache Service")
            return []
    
    def warm_cache(self, common_queries: List[str]):
        """Pre-warm cache with common queries"""
        try:
            for query in common_queries:
                # Check if already cached
                if not self.get_cached_response(query):
                    # This would typically trigger a background job to generate responses
                    frappe.enqueue(
                        "assistant_crm.services.cache_service.generate_and_cache_response",
                        query=query,
                        queue="default",
                        timeout=300
                    )
            
        except Exception as e:
            frappe.log_error(f"Error warming cache: {str(e)}", "Cache Service")


def generate_and_cache_response(query: str):
    """Background job to generate and cache responses"""
    try:
        from assistant_crm.services.gemini_service import GeminiService
        
        gemini = GeminiService()
        response = gemini.process_message(
            message=query,
            user_context={},
            chat_history=[]
        )
        
        if response and "error" not in response.get("context_data", {}):
            cache_service = CacheService()
            cache_service.cache_response(query, response, ttl=7200)  # 2 hour TTL for pre-warmed cache
            
    except Exception as e:
        frappe.log_error(f"Error in background cache generation: {str(e)}", "Cache Service")


# Global cache service instance
_cache_service = None

def get_cache_service():
    """Get global cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
