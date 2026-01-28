# Copyright (c) 2025, WCFCB and contributors
# For license information, please see license.txt

import frappe
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from frappe.utils import now_datetime
from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit breaker is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is back


class ErrorHandler:
    """Comprehensive error handling with circuit breaker and exponential backoff"""
    
    def __init__(self, service_name: str = "gemini_api"):
        self.service_name = service_name
        self.circuit_key = f"circuit_breaker:{service_name}"
        self.error_key = f"error_stats:{service_name}"
        
        # Circuit breaker configuration
        self.failure_threshold = 5  # Number of failures before opening circuit
        self.recovery_timeout = 300  # 5 minutes before trying half-open
        self.success_threshold = 3  # Successes needed to close circuit
        
        # Exponential backoff configuration
        self.base_delay = 1  # Base delay in seconds
        self.max_delay = 60  # Maximum delay in seconds
        self.max_retries = 3  # Maximum number of retries
        
    def get_circuit_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        try:
            circuit_data = frappe.cache().get_value(self.circuit_key) or {
                "state": CircuitState.CLOSED.value,
                "failure_count": 0,
                "last_failure_time": None,
                "success_count": 0,
                "last_success_time": None
            }
            
            # Check if we should transition from OPEN to HALF_OPEN
            if (circuit_data["state"] == CircuitState.OPEN.value and 
                circuit_data["last_failure_time"]):
                
                last_failure = datetime.fromisoformat(circuit_data["last_failure_time"])
                if now_datetime() - last_failure > timedelta(seconds=self.recovery_timeout):
                    circuit_data["state"] = CircuitState.HALF_OPEN.value
                    circuit_data["success_count"] = 0
                    self._save_circuit_state(circuit_data)
            
            return circuit_data
            
        except Exception as e:
            frappe.log_error(f"Error getting circuit state: {str(e)}", "Error Handler")
            return {
                "state": CircuitState.CLOSED.value,
                "failure_count": 0,
                "last_failure_time": None,
                "success_count": 0,
                "last_success_time": None
            }
    
    def _save_circuit_state(self, circuit_data: Dict[str, Any]):
        """Save circuit breaker state"""
        try:
            frappe.cache().set_value(self.circuit_key, circuit_data, expires_in_sec=3600)
        except Exception as e:
            frappe.log_error(f"Error saving circuit state: {str(e)}", "Error Handler")
    
    def can_execute(self) -> bool:
        """Check if request can be executed based on circuit state"""
        circuit_data = self.get_circuit_state()
        return circuit_data["state"] != CircuitState.OPEN.value
    
    def record_success(self):
        """Record a successful operation"""
        try:
            circuit_data = self.get_circuit_state()
            circuit_data["last_success_time"] = now_datetime().isoformat()
            
            if circuit_data["state"] == CircuitState.HALF_OPEN.value:
                circuit_data["success_count"] += 1
                if circuit_data["success_count"] >= self.success_threshold:
                    # Close the circuit
                    circuit_data["state"] = CircuitState.CLOSED.value
                    circuit_data["failure_count"] = 0
                    circuit_data["success_count"] = 0
            elif circuit_data["state"] == CircuitState.CLOSED.value:
                # Reset failure count on success
                circuit_data["failure_count"] = 0
            
            self._save_circuit_state(circuit_data)
            self._update_error_stats("success")
            
        except Exception as e:
            frappe.log_error(f"Error recording success: {str(e)}", "Error Handler")
    
    def record_failure(self, error: Exception):
        """Record a failed operation"""
        try:
            circuit_data = self.get_circuit_state()
            circuit_data["last_failure_time"] = now_datetime().isoformat()
            circuit_data["failure_count"] += 1
            
            # Check if we should open the circuit
            if (circuit_data["state"] == CircuitState.CLOSED.value and 
                circuit_data["failure_count"] >= self.failure_threshold):
                circuit_data["state"] = CircuitState.OPEN.value
            elif circuit_data["state"] == CircuitState.HALF_OPEN.value:
                # Go back to open state
                circuit_data["state"] = CircuitState.OPEN.value
                circuit_data["success_count"] = 0
            
            self._save_circuit_state(circuit_data)
            self._update_error_stats("failure", str(error))
            
        except Exception as e:
            frappe.log_error(f"Error recording failure: {str(e)}", "Error Handler")
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with exponential backoff retry logic"""
        if not self.can_execute():
            raise Exception(f"Circuit breaker is OPEN for {self.service_name}")
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
                
            except Exception as e:
                last_exception = e
                self.record_failure(e)
                
                # Don't retry on the last attempt
                if attempt == self.max_retries:
                    break
                
                # Calculate delay with exponential backoff and jitter
                delay = min(
                    self.base_delay * (2 ** attempt) + random.uniform(0, 1),
                    self.max_delay
                )
                
                frappe.log_error(
                    f"Attempt {attempt + 1} failed for {self.service_name}: {str(e)}. "
                    f"Retrying in {delay:.2f} seconds...",
                    "Error Handler"
                )
                
                time.sleep(delay)
        
        # All retries exhausted
        raise last_exception
    
    def _update_error_stats(self, operation: str, error_message: str = None):
        """Update error statistics"""
        try:
            stats_key = f"{self.error_key}:stats"
            stats = frappe.cache().get_value(stats_key) or {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "last_error": None,
                "last_error_time": None,
                "error_types": {}
            }
            
            stats["total_requests"] += 1
            
            if operation == "success":
                stats["successful_requests"] += 1
            elif operation == "failure":
                stats["failed_requests"] += 1
                stats["last_error"] = error_message
                stats["last_error_time"] = now_datetime().isoformat()
                
                # Track error types
                error_type = type(Exception).__name__
                if error_message:
                    if "429" in error_message:
                        error_type = "RateLimitError"
                    elif "timeout" in error_message.lower():
                        error_type = "TimeoutError"
                    elif "connection" in error_message.lower():
                        error_type = "ConnectionError"
                
                stats["error_types"][error_type] = stats["error_types"].get(error_type, 0) + 1
            
            # Calculate success rate
            if stats["total_requests"] > 0:
                stats["success_rate"] = (stats["successful_requests"] / stats["total_requests"]) * 100
            
            frappe.cache().set_value(stats_key, stats, expires_in_sec=86400)  # 24 hours
            
        except Exception as e:
            frappe.log_error(f"Error updating error stats: {str(e)}", "Error Handler")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        try:
            stats_key = f"{self.error_key}:stats"
            stats = frappe.cache().get_value(stats_key) or {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "success_rate": 0,
                "last_error": None,
                "last_error_time": None,
                "error_types": {}
            }
            
            # Add circuit breaker state
            circuit_data = self.get_circuit_state()
            stats["circuit_state"] = circuit_data["state"]
            stats["failure_count"] = circuit_data["failure_count"]
            
            return stats
            
        except Exception as e:
            frappe.log_error(f"Error getting error stats: {str(e)}", "Error Handler")
            return {}
    
    def reset_circuit(self):
        """Manually reset circuit breaker"""
        try:
            circuit_data = {
                "state": CircuitState.CLOSED.value,
                "failure_count": 0,
                "last_failure_time": None,
                "success_count": 0,
                "last_success_time": None
            }
            self._save_circuit_state(circuit_data)
            
        except Exception as e:
            frappe.log_error(f"Error resetting circuit: {str(e)}", "Error Handler")
    
    def get_fallback_response(self, error: Exception) -> Dict[str, Any]:
        """Get appropriate fallback response based on error type"""
        error_message = str(error)
        
        if "429" in error_message:
            return {
                "response": "I'm currently experiencing high demand. Please try again in a few minutes, or contact WCFCB directly at +260-211-123456 for immediate assistance.",
                "context_data": {
                    "error_type": "rate_limit",
                    "fallback": True,
                    "suggested_action": "retry_later"
                }
            }
        elif "timeout" in error_message.lower():
            return {
                "response": "The request is taking longer than expected. Please try again, or contact WCFCB at info@wcfcb.gov.zm if the issue persists.",
                "context_data": {
                    "error_type": "timeout",
                    "fallback": True,
                    "suggested_action": "retry"
                }
            }
        elif "connection" in error_message.lower():
            return {
                "response": "I'm having trouble connecting to our services. Please check your internet connection and try again, or contact WCFCB directly.",
                "context_data": {
                    "error_type": "connection",
                    "fallback": True,
                    "suggested_action": "check_connection"
                }
            }
        else:
            return {
                "response": "I encountered an unexpected issue. Please try again or contact WCFCB at +260-211-123456 for assistance.",
                "context_data": {
                    "error_type": "unknown",
                    "fallback": True,
                    "suggested_action": "contact_support"
                }
            }


# Global error handler instance
_error_handler = None

def get_error_handler(service_name: str = "gemini_api"):
    """Get global error handler instance"""
    global _error_handler
    if _error_handler is None or _error_handler.service_name != service_name:
        _error_handler = ErrorHandler(service_name)
    return _error_handler
