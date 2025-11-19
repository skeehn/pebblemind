"""High-performance response caching system with LRU eviction and TTL support"""

import asyncio
import hashlib
import json
import time
from typing import Optional, Any, Dict, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    timestamp: float
    ttl: Optional[float]
    hit_count: int = 0
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

    def touch(self):
        """Update hit count and timestamp"""
        self.hit_count += 1
        self.timestamp = time.time()


class ResponseCache:
    """
    High-performance LRU cache with TTL support, size limits, and statistics.

    Features:
    - LRU eviction policy
    - Per-entry TTL support
    - Memory size tracking
    - Cache statistics
    - Thread-safe async operations
    - Smart key generation
    """

    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 500,
        default_ttl: Optional[float] = 3600,
        enable_stats: bool = True
    ):
        """
        Initialize cache

        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
            default_ttl: Default TTL in seconds (None = no expiration)
            enable_stats: Enable statistics tracking
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.enable_stats = enable_stats

        # LRU cache storage
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()

        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
            "current_size": 0,
            "current_memory_bytes": 0,
        }

        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start background cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Cache cleanup task started")

    async def stop(self):
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Cache cleanup task stopped")

    def _generate_key(self, *args, **kwargs) -> str:
        """
        Generate cache key from arguments

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        # Create deterministic representation
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)

        # Hash for compact key
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes"""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, (list, tuple)):
                return sum(self._estimate_size(v) for v in value)
            elif isinstance(value, dict):
                return sum(
                    self._estimate_size(k) + self._estimate_size(v)
                    for k, v in value.items()
                )
            else:
                # Fallback: use string representation
                return len(str(value).encode('utf-8'))
        except Exception:
            return 100  # Default estimate

    async def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Tuple of (value, hit) where hit indicates cache hit
        """
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                if self.enable_stats:
                    self._stats["misses"] += 1
                return None, False

            # Check expiration
            if entry.is_expired():
                del self._cache[key]
                # Always update size counters (needed for eviction)
                self._stats["current_size"] -= 1
                self._stats["current_memory_bytes"] -= entry.size_bytes
                # Update stats counters only if enabled
                if self.enable_stats:
                    self._stats["misses"] += 1
                    self._stats["expirations"] += 1
                return None, False

            # Update entry (LRU)
            entry.touch()
            self._cache.move_to_end(key)

            if self.enable_stats:
                self._stats["hits"] += 1

            return entry.value, True

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None
    ):
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (None = use default)
        """
        async with self._lock:
            # Calculate size
            size_bytes = self._estimate_size(value)

            # Check if we need to evict
            await self._evict_if_needed(size_bytes)

            # Create entry
            entry = CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl=ttl if ttl is not None else self.default_ttl,
                size_bytes=size_bytes
            )

            # Remove old entry if exists
            if key in self._cache:
                old_entry = self._cache[key]
                self._stats["current_memory_bytes"] -= old_entry.size_bytes
                self._stats["current_size"] -= 1
                del self._cache[key]

            # Add new entry
            self._cache[key] = entry
            # Always update size counters (needed for eviction)
            self._stats["current_size"] += 1
            self._stats["current_memory_bytes"] += size_bytes

    async def _evict_if_needed(self, incoming_size: int):
        """Evict entries if needed to make room"""
        # Evict by size
        while (
            len(self._cache) >= self.max_size or
            self._stats["current_memory_bytes"] + incoming_size > self.max_memory_bytes
        ):
            if not self._cache:
                break

            # Remove oldest (LRU)
            key, entry = self._cache.popitem(last=False)
            # Always update size counters (needed for eviction)
            self._stats["current_size"] -= 1
            self._stats["current_memory_bytes"] -= entry.size_bytes
            # Update stats counter only if enabled
            if self.enable_stats:
                self._stats["evictions"] += 1

    async def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                del self._cache[key]
                # Always update size counters (needed for eviction)
                self._stats["current_size"] -= 1
                self._stats["current_memory_bytes"] -= entry.size_bytes
                return True
            return False

    async def clear(self):
        """Clear entire cache"""
        async with self._lock:
            self._cache.clear()
            # Always update size counters (needed for eviction)
            self._stats["current_size"] = 0
            self._stats["current_memory_bytes"] = 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                self._stats["hits"] / total_requests
                if total_requests > 0
                else 0.0
            )

            return {
                **self._stats,
                "hit_rate": hit_rate,
                "memory_usage_mb": self._stats["current_memory_bytes"] / (1024 * 1024),
                "fill_ratio": len(self._cache) / self.max_size if self.max_size > 0 else 0,
            }

    async def _cleanup_loop(self):
        """Background task to remove expired entries"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")

    async def _cleanup_expired(self):
        """Remove expired entries"""
        async with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)

            for key in expired_keys:
                entry = self._cache[key]
                del self._cache[key]
                # Always update size counters (needed for eviction)
                self._stats["current_size"] -= 1
                self._stats["current_memory_bytes"] -= entry.size_bytes
                # Update stats counter only if enabled
                if self.enable_stats:
                    self._stats["expirations"] += 1

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


# Global cache instance
_global_cache: Optional[ResponseCache] = None


def get_cache() -> ResponseCache:
    """Get global cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = ResponseCache()
    return _global_cache


async def cached(
    func,
    *args,
    ttl: Optional[float] = None,
    cache_instance: Optional[ResponseCache] = None,
    **kwargs
):
    """
    Cache decorator for async functions

    Args:
        func: Function to cache
        *args: Function arguments
        ttl: TTL for this cache entry
        cache_instance: Cache instance to use (default: global)
        **kwargs: Function keyword arguments

    Returns:
        Cached or computed result
    """
    cache = cache_instance or get_cache()

    # Generate key
    key_parts = [func.__name__] + list(args)
    key = cache._generate_key(*key_parts, **kwargs)

    # Try cache
    value, hit = await cache.get(key)
    if hit:
        return value

    # Compute and cache
    if asyncio.iscoroutinefunction(func):
        value = await func(*args, **kwargs)
    else:
        value = func(*args, **kwargs)

    await cache.set(key, value, ttl=ttl)
    return value
