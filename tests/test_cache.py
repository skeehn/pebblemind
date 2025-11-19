"""Tests for response cache system"""

import pytest
import asyncio
from pebblemind.cache import ResponseCache, get_cache, cached


@pytest.mark.asyncio
async def test_cache_set_and_get():
    """Test basic cache set and get operations"""
    cache = ResponseCache(max_size=100, default_ttl=10)
    await cache.start()

    # Set value
    await cache.set("test_key", "test_value")

    # Get value
    value, hit = await cache.get("test_key")
    assert hit is True
    assert value == "test_value"

    await cache.stop()


@pytest.mark.asyncio
async def test_cache_miss():
    """Test cache miss"""
    cache = ResponseCache(max_size=100)
    await cache.start()

    # Get non-existent key
    value, hit = await cache.get("nonexistent")
    assert hit is False
    assert value is None

    await cache.stop()


@pytest.mark.asyncio
async def test_cache_expiration():
    """Test TTL expiration"""
    cache = ResponseCache(max_size=100, default_ttl=1)
    await cache.start()

    # Set value with short TTL
    await cache.set("test_key", "test_value", ttl=1)

    # Should be available immediately
    value, hit = await cache.get("test_key")
    assert hit is True

    # Wait for expiration
    await asyncio.sleep(1.5)

    # Should be expired
    value, hit = await cache.get("test_key")
    assert hit is False

    await cache.stop()


@pytest.mark.asyncio
async def test_cache_lru_eviction():
    """Test LRU eviction policy"""
    cache = ResponseCache(max_size=3)
    await cache.start()

    # Fill cache
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    await cache.set("key3", "value3")

    # Add one more (should evict key1)
    await cache.set("key4", "value4")

    # key1 should be evicted
    value, hit = await cache.get("key1")
    assert hit is False

    # Others should exist
    _, hit = await cache.get("key2")
    assert hit is True

    await cache.stop()


@pytest.mark.asyncio
async def test_cache_stats():
    """Test cache statistics"""
    cache = ResponseCache(max_size=100)
    await cache.start()

    # Generate some hits and misses
    await cache.set("key1", "value1")
    await cache.get("key1")  # Hit
    await cache.get("key2")  # Miss

    stats = await cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["current_size"] == 1

    await cache.stop()


@pytest.mark.asyncio
async def test_cached_decorator():
    """Test cached decorator"""
    cache = ResponseCache(max_size=100)
    await cache.start()

    call_count = 0

    async def expensive_function(x):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)
        return x * 2

    # First call - should execute function
    result1 = await cached(expensive_function, 5, cache_instance=cache)
    assert result1 == 10
    assert call_count == 1

    # Second call - should use cache
    result2 = await cached(expensive_function, 5, cache_instance=cache)
    assert result2 == 10
    assert call_count == 1  # Should not increment

    await cache.stop()


@pytest.mark.asyncio
async def test_cache_clear():
    """Test cache clear operation"""
    cache = ResponseCache(max_size=100)
    await cache.start()

    # Add items
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")

    # Clear cache
    await cache.clear()

    # Check items are gone
    _, hit1 = await cache.get("key1")
    _, hit2 = await cache.get("key2")
    assert hit1 is False
    assert hit2 is False

    stats = await cache.get_stats()
    assert stats["current_size"] == 0

    await cache.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
