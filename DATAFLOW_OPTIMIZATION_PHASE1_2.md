# **PHASE 1.2: REQUEST BATCHING AND CONNECTION POOLING**

## **Objective**
Implement request batching and database connection pooling to reduce overhead and improve concurrent user handling.

## **Technical Specifications**

### **1.2.1: Database Connection Pool Manager**

**File:** `assistant_crm/services/connection_pool_manager.py`

```python
#!/usr/bin/env python3
"""
Database Connection Pool Manager for Assistant CRM
Optimizes database connections and reduces connection overhead
"""

import time
import threading
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

class ConnectionPoolManager:
    """
    Manages database connection pooling for optimal performance
    """
    
    def __init__(self, max_connections: int = 10, timeout: int = 30):
        self.max_connections = max_connections
        self.timeout = timeout
        self.active_connections = 0
        self.connection_queue = []
        self.lock = threading.Lock()
        self.stats = {
            'total_requests': 0,
            'active_connections': 0,
            'max_concurrent': 0,
            'average_wait_time': 0
        }
    
    @contextmanager
    def get_connection(self):
        """Get database connection from pool"""
        start_time = time.time()
        
        with self.lock:
            self.stats['total_requests'] += 1
            
            # Wait for available connection
            while self.active_connections >= self.max_connections:
                if time.time() - start_time > self.timeout:
                    raise TimeoutError("Connection pool timeout")
                time.sleep(0.1)
            
            self.active_connections += 1
            self.stats['active_connections'] = self.active_connections
            self.stats['max_concurrent'] = max(self.stats['max_concurrent'], self.active_connections)
        
        try:
            # Simulate connection (in real implementation, this would be actual DB connection)
            yield {"connection": f"conn_{self.active_connections}"}
        finally:
            with self.lock:
                self.active_connections -= 1
                wait_time = time.time() - start_time
                self.stats['average_wait_time'] = (
                    (self.stats['average_wait_time'] * (self.stats['total_requests'] - 1) + wait_time) 
                    / self.stats['total_requests']
                )

# Global connection pool
_connection_pool = None

def get_connection_pool() -> ConnectionPoolManager:
    """Get global connection pool instance"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPoolManager()
    return _connection_pool
```

### **1.2.2: Request Batching Service**

**File:** `assistant_crm/services/request_batching_service.py`

```python
#!/usr/bin/env python3
"""
Request Batching Service for Assistant CRM
Batches similar requests to reduce database load and improve performance
"""

import time
import asyncio
from typing import Dict, Any, List, Callable
from collections import defaultdict

class RequestBatchingService:
    """
    Batches similar requests for optimal database utilization
    """
    
    def __init__(self, batch_size: int = 5, batch_timeout: float = 0.1):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_batches = defaultdict(list)
        self.batch_processors = {}
        self.stats = {
            'total_requests': 0,
            'batched_requests': 0,
            'batch_efficiency': 0
        }
    
    def register_batch_processor(self, intent_type: str, processor: Callable):
        """Register batch processor for specific intent type"""
        self.batch_processors[intent_type] = processor
    
    async def add_request(self, intent_type: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add request to batch queue"""
        self.stats['total_requests'] += 1
        
        # Add to pending batch
        batch_key = f"{intent_type}_{request_data.get('user_role', 'default')}"
        self.pending_batches[batch_key].append(request_data)
        
        # Process batch if size reached or timeout
        if len(self.pending_batches[batch_key]) >= self.batch_size:
            return await self._process_batch(batch_key)
        else:
            # Wait for timeout or more requests
            await asyncio.sleep(self.batch_timeout)
            if self.pending_batches[batch_key]:
                return await self._process_batch(batch_key)
    
    async def _process_batch(self, batch_key: str) -> List[Dict[str, Any]]:
        """Process batch of requests"""
        if batch_key not in self.pending_batches:
            return []
        
        batch = self.pending_batches[batch_key]
        del self.pending_batches[batch_key]
        
        if not batch:
            return []
        
        self.stats['batched_requests'] += len(batch)
        self.stats['batch_efficiency'] = (
            self.stats['batched_requests'] / self.stats['total_requests'] * 100
        )
        
        # Process batch using registered processor
        intent_type = batch_key.split('_')[0]
        if intent_type in self.batch_processors:
            return await self.batch_processors[intent_type](batch)
        else:
            # Fallback to individual processing
            return [await self._process_individual(request) for request in batch]
    
    async def _process_individual(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback individual request processing"""
        return {"processed": True, "data": request_data}

# Global batching service
_batching_service = None

def get_batching_service() -> RequestBatchingService:
    """Get global batching service instance"""
    global _batching_service
    if _batching_service is None:
        _batching_service = RequestBatchingService()
    return _batching_service
```

### **1.2.3: LiveDataOrchestrator Optimization**

**File:** `assistant_crm/services/live_data_orchestrator.py` (Modifications)

**Location:** Add imports at top of file

```python
from assistant_crm.services.connection_pool_manager import get_connection_pool
from assistant_crm.services.request_batching_service import get_batching_service
```

**Location:** Modify __init__ method

```python
def __init__(self):
    # Existing initialization...
    self.connection_pool = get_connection_pool()
    self.batching_service = get_batching_service()
    
    # Register batch processors
    self._register_batch_processors()

def _register_batch_processors(self):
    """Register batch processors for different intent types"""
    self.batching_service.register_batch_processor('claim_status', self._batch_process_claims)
    self.batching_service.register_batch_processor('payment_status', self._batch_process_payments)
    self.batching_service.register_batch_processor('pension_inquiry', self._batch_process_pensions)

async def _batch_process_claims(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Batch process claim status requests"""
    with self.connection_pool.get_connection() as conn:
        # Process multiple claims in single database query
        user_ids = [req['user_context']['user_id'] for req in batch]
        # Simulate batch database query
        results = []
        for user_id in user_ids:
            results.append({
                'type': 'claim_data',
                'claim_number': f'CLM-{user_id}-2025',
                'status': 'Under Review',
                'submitted_date': '2025-01-15',
                'retrieved_at': '2025-08-12T23:20:00'
            })
        return results
```

## **Implementation Steps**

### **Step 1: Create Connection Pool Manager (3 hours)**
1. Implement connection pooling with configurable limits
2. Add connection timeout and retry logic
3. Implement performance monitoring

### **Step 2: Implement Request Batching (3 hours)**
1. Create batching service with configurable batch sizes
2. Implement batch processors for common intent types
3. Add async processing capabilities

### **Step 3: Integrate with LiveDataOrchestrator (2 hours)**
1. Modify orchestrator to use connection pooling
2. Integrate batch processing for similar requests
3. Add performance metrics collection

## **Expected Results**
- **Concurrent User Capacity:** 300% increase
- **Database Connection Efficiency:** 80% reduction in connection overhead
- **Batch Processing Efficiency:** 60% reduction in database queries for similar requests
- **Response Time Consistency:** More predictable response times under load

## **Success Metrics**
- Support 100+ concurrent users without degradation
- Database connection utilization < 70%
- Batch efficiency > 75% for similar requests
- Zero functional regressions
