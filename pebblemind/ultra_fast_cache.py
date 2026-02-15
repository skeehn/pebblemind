"""Ultra-Fast Caching System for Sub-100ms Response Times

Multi-layer caching strategy:
1. In-memory cache (< 1ms access)
2. Response prediction and preloading
3. Query pattern recognition
4. Streaming for perceived low latency
5. Lightweight response mode
"""

import asyncio
import hashlib
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from collections import OrderedDict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
import pickle

logger = logging.getLogger(__name__)


@dataclass
class CachedResponse:
    """Cached response with metadata"""
    response: str
    timestamp: float
    hit_count: int
    avg_response_time: float
    tags: List[str]


class LRUCache:
    """Ultra-fast LRU cache with O(1) operations"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, CachedResponse] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[str]:
        """Get from cache (O(1))"""
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            cached = self.cache[key]
            cached.hit_count += 1
            self.hits += 1
            return cached.response

        self.misses += 1
        return None

    def put(self, key: str, response: str, response_time: float, tags: List[str] = None):
        """Store in cache (O(1))"""
        if key in self.cache:
            # Update existing
            self.cache.move_to_end(key)
            cached = self.cache[key]
            # Running average
            cached.avg_response_time = (cached.avg_response_time * cached.hit_count + response_time) / (cached.hit_count + 1)
        else:
            # Add new
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                self.cache.popitem(last=False)

            self.cache[key] = CachedResponse(
                response=response,
                timestamp=time.time(),
                hit_count=0,
                avg_response_time=response_time,
                tags=tags or []
            )

    def invalidate_by_tag(self, tag: str):
        """Invalidate all entries with a specific tag"""
        keys_to_delete = [k for k, v in self.cache.items() if tag in v.tags]
        for key in keys_to_delete:
            del self.cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.2f}%",
            'total_requests': total
        }


class QueryPredictor:
    """Predicts next likely queries based on patterns"""

    def __init__(self, history_size: int = 100):
        self.history: deque = deque(maxlen=history_size)
        self.patterns: Dict[str, List[str]] = {}  # Current query -> likely next queries
        self.preload_queue: asyncio.Queue = asyncio.Queue(maxsize=10)

    def record_query(self, query: str):
        """Record a query to learn patterns"""
        if len(self.history) > 0:
            prev_query = self.history[-1]

            if prev_query not in self.patterns:
                self.patterns[prev_query] = []

            # Add to pattern if not already there
            if query not in self.patterns[prev_query]:
                self.patterns[prev_query].append(query)

        self.history.append(query)

    def predict_next(self, current_query: str, n: int = 3) -> List[str]:
        """Predict next n most likely queries"""
        if current_query in self.patterns:
            predictions = self.patterns[current_query][:n]
            return predictions
        return []

    async def add_to_preload(self, query: str):
        """Add query to preload queue"""
        try:
            await self.preload_queue.put(query)
        except asyncio.QueueFull:
            pass  # Queue full, skip preloading

    async def get_preload_query(self) -> Optional[str]:
        """Get next query to preload"""
        try:
            return await asyncio.wait_for(self.preload_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None


class UltraFastCache:
    """
    Ultra-fast caching system with:
    - Sub-ms in-memory cache
    - Predictive preloading
    - Pattern recognition
    - Response streaming
    """

    def __init__(
        self,
        cache_size: int = 1000,
        enable_prediction: bool = True,
        enable_preloading: bool = True
    ):
        self.lru_cache = LRUCache(max_size=cache_size)
        self.predictor = QueryPredictor() if enable_prediction else None
        self.enable_preloading = enable_preloading

        # Performance tracking
        self.query_times: deque = deque(maxlen=100)
        self.cache_hit_times: deque = deque(maxlen=100)

        # Preloading task
        self.preload_task: Optional[asyncio.Task] = None

    def _make_cache_key(self, query: str, **kwargs) -> str:
        """Generate cache key from query and parameters"""
        # Include relevant parameters in key
        key_parts = [query]
        for k, v in sorted(kwargs.items()):
            if k in ['temperature', 'max_tokens', 'system_prompt']:
                key_parts.append(f"{k}={v}")

        key_str = "|".join(str(p) for p in key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    async def get_cached_or_execute(
        self,
        query: str,
        execute_func: Callable,
        **kwargs
    ) -> tuple[str, bool, float]:
        """
        Get cached response or execute function

        Returns:
            (response, was_cached, response_time_ms)
        """
        start_time = time.time()
        cache_key = self._make_cache_key(query, **kwargs)

        # Try cache first
        cached_response = self.lru_cache.get(cache_key)
        if cached_response:
            response_time = (time.time() - start_time) * 1000  # ms
            self.cache_hit_times.append(response_time)

            # Record for prediction
            if self.predictor:
                self.predictor.record_query(query)

                # Predict and preload next queries
                if self.enable_preloading:
                    next_queries = self.predictor.predict_next(query)
                    for next_q in next_queries:
                        await self.predictor.add_to_preload(next_q)

            return cached_response, True, response_time

        # Execute function
        try:
            response = await execute_func(query, **kwargs)
            execution_time = (time.time() - start_time) * 1000  # ms

            # Cache the response
            self.lru_cache.put(cache_key, response, execution_time)
            self.query_times.append(execution_time)

            # Record for prediction
            if self.predictor:
                self.predictor.record_query(query)

            return response, False, execution_time

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    async def stream_response(
        self,
        query: str,
        execute_func: Callable,
        chunk_size: int = 50,
        **kwargs
    ):
        """
        Stream response for perceived low latency

        Yields chunks of the response as they're generated
        """
        cache_key = self._make_cache_key(query, **kwargs)

        # Check cache first
        cached_response = self.lru_cache.get(cache_key)
        if cached_response:
            # Stream cached response in chunks for consistency
            for i in range(0, len(cached_response), chunk_size):
                chunk = cached_response[i:i + chunk_size]
                yield chunk
                await asyncio.sleep(0.01)  # Small delay for smooth streaming
            return

        # Execute and stream
        response_parts = []
        async for chunk in execute_func(query, **kwargs):
            response_parts.append(chunk)
            yield chunk

        # Cache complete response
        full_response = "".join(response_parts)
        self.lru_cache.put(cache_key, full_response, 0.0)  # Streaming time not measured

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        cache_stats = self.lru_cache.get_stats()

        stats = {
            'cache': cache_stats,
            'performance': {}
        }

        if self.query_times:
            stats['performance']['avg_query_time_ms'] = sum(self.query_times) / len(self.query_times)
            stats['performance']['p95_query_time_ms'] = sorted(self.query_times)[int(len(self.query_times) * 0.95)]
            stats['performance']['p99_query_time_ms'] = sorted(self.query_times)[int(len(self.query_times) * 0.99)]

        if self.cache_hit_times:
            stats['performance']['avg_cache_hit_time_ms'] = sum(self.cache_hit_times) / len(self.cache_hit_times)
            stats['performance']['cache_speedup'] = (
                stats['performance'].get('avg_query_time_ms', 0) /
                stats['performance']['avg_cache_hit_time_ms']
            ) if stats['performance'].get('avg_cache_hit_time_ms') else 0

        if self.predictor:
            stats['prediction'] = {
                'patterns_learned': len(self.predictor.patterns),
                'history_size': len(self.predictor.history)
            }

        return stats

    async def preload_worker(self, execute_func: Callable):
        """Background worker for preloading predicted queries"""
        while True:
            try:
                if self.predictor:
                    query = await self.predictor.get_preload_query()
                    if query:
                        # Preload in background
                        cache_key = self._make_cache_key(query)
                        if not self.lru_cache.get(cache_key):
                            try:
                                response = await execute_func(query)
                                self.lru_cache.put(cache_key, response, 0.0)
                                logger.debug(f"Preloaded: {query[:50]}...")
                            except Exception as e:
                                logger.error(f"Preload failed: {e}")
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Preload worker error: {e}")
                await asyncio.sleep(1)

    def start_preloading(self, execute_func: Callable):
        """Start background preloading"""
        if self.enable_preloading and not self.preload_task:
            self.preload_task = asyncio.create_task(self.preload_worker(execute_func))

    async def stop_preloading(self):
        """Stop background preloading"""
        if self.preload_task:
            self.preload_task.cancel()
            try:
                await self.preload_task
            except asyncio.CancelledError:
                pass
            self.preload_task = None


# Example usage
async def demo():
    """Demo ultra-fast cache"""
    print("="*60)
    print("ULTRA-FAST CACHE DEMO")
    print("="*60 + "\n")

    # Mock LLM function
    async def mock_llm(query: str, **kwargs):
        await asyncio.sleep(0.5)  # Simulate 500ms LLM response
        return f"Response to: {query}"

    cache = UltraFastCache(cache_size=100, enable_prediction=True)

    # First query (miss)
    print("Query 1 (cache miss)...")
    start = time.time()
    response, cached, response_time = await cache.get_cached_or_execute(
        "What is Python?",
        mock_llm
    )
    print(f"  Response time: {response_time:.2f}ms")
    print(f"  Cached: {cached}")
    print()

    # Same query (hit)
    print("Query 2 (cache hit - same question)...")
    response, cached, response_time = await cache.get_cached_or_execute(
        "What is Python?",
        mock_llm
    )
    print(f"  Response time: {response_time:.2f}ms")
    print(f"  Cached: {cached}")
    print()

    # Performance stats
    print("Performance Statistics:")
    stats = cache.get_performance_stats()
    print(f"  Cache hit rate: {stats['cache']['hit_rate']}")
    if 'avg_cache_hit_time_ms' in stats['performance']:
        print(f"  Avg cache hit time: {stats['performance']['avg_cache_hit_time_ms']:.2f}ms")
        print(f"  Cache speedup: {stats['performance']['cache_speedup']:.1f}x")


if __name__ == "__main__":
    asyncio.run(demo())
