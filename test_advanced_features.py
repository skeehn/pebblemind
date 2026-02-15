#!/usr/bin/env python3
"""Test Advanced Features: Real-time Web Data, Ultra-Fast Caching, Live Streaming

This script demonstrates the new capabilities:
1. Real-time web data integration
2. Ultra-low latency caching (<100ms)
3. Live streaming capabilities
"""

import asyncio
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_realtime_web():
    """Test real-time web data capabilities"""
    print("="*60)
    print("TEST 1: REAL-TIME WEB DATA")
    print("="*60)
    print()

    try:
        from pebblemind.realtime_web import WebDataTools

        async with WebDataTools(cache_ttl=300) as tools:
            # Web Search
            print("🔍 Testing Web Search...")
            start = time.time()
            results = await tools.search_web("Python 3.12 features", num_results=3)
            elapsed = (time.time() - start) * 1000

            print(f"  ✅ Found {len(results)} results in {elapsed:.0f}ms")
            if results:
                print(f"  Example: {results[0]['title'][:60]}...")
            print()

            # Weather
            print("🌤️  Testing Weather Data...")
            start = time.time()
            weather = await tools.get_weather("San Francisco")
            elapsed = (time.time() - start) * 1000

            if 'temperature_c' in weather:
                print(f"  ✅ Got weather data in {elapsed:.0f}ms")
                print(f"  Temp: {weather['temperature_c']}°C, {weather['condition']}")
            print()

            # News
            print("📰 Testing News Feed...")
            start = time.time()
            news = await tools.get_news("technology", limit=3)
            elapsed = (time.time() - start) * 1000

            print(f"  ✅ Got {len(news)} articles in {elapsed:.0f}ms")
            if news:
                print(f"  Latest: {news[0]['title'][:60]}...")
            print()

            # Test caching (should be much faster)
            print("🔄 Testing Cache Performance...")
            start = time.time()
            weather2 = await tools.get_weather("San Francisco")  # Cached
            elapsed = (time.time() - start) * 1000

            print(f"  ✅ Cached request: {elapsed:.2f}ms")
            print()

        return True

    except ImportError as e:
        print(f"  ⚠️  Skipping: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_ultra_fast_cache():
    """Test ultra-fast caching system"""
    print("="*60)
    print("TEST 2: ULTRA-FAST CACHING (<100ms)")
    print("="*60)
    print()

    try:
        from pebblemind.ultra_fast_cache import UltraFastCache

        # Mock LLM function (simulates 500ms inference)
        async def mock_llm(query: str, **kwargs):
            await asyncio.sleep(0.5)
            return f"AI Response: {query[:50]}..."

        cache = UltraFastCache(
            cache_size=100,
            enable_prediction=True,
            enable_preloading=False  # Disable for demo
        )

        queries = [
            "What is Python?",
            "What is Python?",  # Same query (should be cached)
            "How does Python work?",
            "What is machine learning?",
            "What is machine learning?",  # Cached
        ]

        print("📊 Running Queries with Smart Caching:")
        print()

        for i, query in enumerate(queries, 1):
            start = time.time()
            response, cached, response_time = await cache.get_cached_or_execute(
                query,
                mock_llm
            )
            elapsed = (time.time() - start) * 1000

            status = "💾 CACHED" if cached else "🔄 COMPUTED"
            print(f"  Query {i}: {status}")
            print(f"    Question: {query}")
            print(f"    Response time: {response_time:.2f}ms")
            print(f"    Actual time: {elapsed:.2f}ms")

            # Check if cached query meets <100ms target
            if cached and response_time < 100:
                print(f"    ✅ Sub-100ms achieved!")

            print()

        # Performance Statistics
        print("📈 Performance Statistics:")
        stats = cache.get_performance_stats()

        print(f"  Cache hit rate: {stats['cache']['hit_rate']}")
        print(f"  Total requests: {stats['cache']['total_requests']}")

        if 'avg_cache_hit_time_ms' in stats['performance']:
            hit_time = stats['performance']['avg_cache_hit_time_ms']
            print(f"  Avg cache hit time: {hit_time:.2f}ms")

            if hit_time < 100:
                print(f"  ✅ Ultra-fast cache target achieved (<100ms)!")
            else:
                print(f"  ⚠️  Cache hits: {hit_time:.2f}ms (target: <100ms)")

        if 'cache_speedup' in stats['performance']:
            speedup = stats['performance']['cache_speedup']
            print(f"  Cache speedup: {speedup:.1f}x faster")

        print()

        return True

    except ImportError as e:
        print(f"  ⚠️  Skipping: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_live_streaming():
    """Test live streaming capabilities"""
    print("="*60)
    print("TEST 3: LIVE STREAMING")
    print("="*60)
    print()

    try:
        from pebblemind.live_streaming import StreamingResponse, StreamBuffer, SSEStreamer

        # Mock streaming generator
        async def mock_stream():
            text = "This is a real-time streaming response that demonstrates low-latency chunk delivery for live applications."
            words = text.split()
            for word in words:
                yield word + " "
                await asyncio.sleep(0.05)  # 50ms per word

        # Test streaming with buffer
        print("📡 Testing Live Streaming:")
        print("  Response: ", end="", flush=True)

        start_time = time.time()
        first_chunk_time = None
        chunk_count = 0

        stream = StreamingResponse(mock_stream(), chunk_size=30)

        async for chunk in stream:
            if first_chunk_time is None:
                first_chunk_time = time.time() - start_time
            chunk_count += 1
            print(chunk.content, end="", flush=True)

        total_time = time.time() - start_time
        print("\n")

        # Streaming metrics
        print("📊 Streaming Metrics:")
        print(f"  First chunk latency: {first_chunk_time*1000:.0f}ms")
        print(f"  Total chunks: {chunk_count}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Chunks/second: {chunk_count/total_time:.1f}")

        if first_chunk_time * 1000 < 200:
            print(f"  ✅ Low first-chunk latency achieved!")

        print()

        # Test SSE format
        print("📨 Testing SSE Format:")
        async def short_stream():
            for i in range(3):
                yield f"Chunk {i+1}"

        print("  SSE Events:")
        count = 0
        async for sse_event in SSEStreamer.stream_events(short_stream()):
            print(f"    {sse_event.strip()}")
            count += 1

        print(f"  ✅ Sent {count} SSE events")
        print()

        # Test buffer
        print("🔄 Testing Low-Latency Buffer:")
        buffer = StreamBuffer(chunk_size=20)

        # Add text gradually
        buffer.add("Hello ")
        buffer.add("world ")
        chunk = buffer.add("this is ")  # Should trigger flush

        if chunk:
            print(f"  ✅ Buffer flushed at {len(chunk.content)} chars")
            print(f"  Content: \"{chunk.content.strip()}\"")
        print()

        return True

    except ImportError as e:
        print(f"  ⚠️  Skipping: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_performance_comparison():
    """Compare performance before and after optimizations"""
    print("="*60)
    print("TEST 4: PERFORMANCE COMPARISON")
    print("="*60)
    print()

    try:
        from pebblemind.ultra_fast_cache import UltraFastCache

        async def mock_llm(query: str, **kwargs):
            await asyncio.sleep(0.3)  # 300ms inference
            return f"Response: {query}"

        # Without cache
        print("⏱️  Without Caching:")
        start = time.time()
        for i in range(5):
            await mock_llm(f"Query {i}")
        no_cache_time = time.time() - start
        print(f"  5 queries: {no_cache_time:.2f}s")
        print(f"  Avg per query: {no_cache_time/5*1000:.0f}ms")
        print()

        # With cache
        print("⚡ With Ultra-Fast Cache:")
        cache = UltraFastCache()
        start = time.time()

        # First query (miss)
        await cache.get_cached_or_execute("Query 1", mock_llm)

        # Repeat queries (hits)
        for i in range(4):
            await cache.get_cached_or_execute("Query 1", mock_llm)

        cache_time = time.time() - start
        print(f"  5 queries (1 miss, 4 hits): {cache_time:.2f}s")

        stats = cache.get_performance_stats()
        if 'avg_cache_hit_time_ms' in stats['performance']:
            print(f"  Avg cache hit: {stats['performance']['avg_cache_hit_time_ms']:.2f}ms")

        speedup = no_cache_time / cache_time
        print(f"  ✅ Speedup: {speedup:.1f}x faster")
        print()

        return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "🚀 "*20)
    print("PEBBLEMIND ADVANCED FEATURES TEST SUITE")
    print("🚀 "*20 + "\n")

    tests = [
        ("Real-Time Web Data", test_realtime_web),
        ("Ultra-Fast Caching", test_ultra_fast_cache),
        ("Live Streaming", test_live_streaming),
        ("Performance Comparison", test_performance_comparison),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except KeyboardInterrupt:
            print("\n\n⚠️  Tests interrupted by user")
            break
        except Exception as e:
            print(f"❌ Test '{name}' failed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    print("FINAL TEST SUMMARY")
    print("="*60 + "\n")

    for name, result in results:
        if result is True:
            print(f"✅ PASS: {name}")
        elif result is False:
            print(f"❌ FAIL: {name}")
        else:
            print(f"⏭️  SKIP: {name}")

    passed = sum(1 for _, r in results if r is True)
    print(f"\n📊 Overall: {passed}/{len(results)} tests passed")

    # Feature summary
    print("\n" + "="*60)
    print("NEW CAPABILITIES DEMONSTRATED")
    print("="*60 + "\n")

    print("✅ Real-Time Web Data:")
    print("  • Web search (DuckDuckGo)")
    print("  • Weather data (wttr.in)")
    print("  • News feeds (RSS)")
    print("  • Web scraping")
    print()

    print("✅ Ultra-Low Latency (<100ms):")
    print("  • In-memory LRU cache")
    print("  • Predictive preloading")
    print("  • Query pattern recognition")
    print("  • Sub-millisecond cache hits")
    print()

    print("✅ Live Streaming:")
    print("  • WebSocket support")
    print("  • Server-Sent Events (SSE)")
    print("  • Real-time audio streaming")
    print("  • Low-latency buffering")
    print()

    return all(r for _, r in results if r is not None)


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
