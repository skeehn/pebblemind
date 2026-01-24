"""
Smart Caching Example
Demonstrates how caching dramatically improves performance in local edge AI
"""

import asyncio
import time
from pebblemind.config import Config, get_config
from pebblemind.core.llm import LLMEngine
from pebblemind.cache import ResponseCache, cached


async def main():
    """Demonstrate smart caching for edge AI optimization"""
    print("\n⚡ PebbleMind Smart Caching Demo")
    print("=" * 60)
    print("This example shows how caching saves computation in edge AI")
    print("CRITICAL for local deployments where every token counts!\n")

    # Load configuration
    try:
        config = get_config()
    except FileNotFoundError:
        print("❌ Config file not found. Run: python install.py")
        return

    # Initialize LLM
    print("⏳ Loading model...")
    engine = LLMEngine(config.llm)

    try:
        await engine.initialize()
        print(f"✅ Ready ({config.llm.model_size.upper()} model)\n")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return

    # Create cache
    cache = ResponseCache(
        max_size=100,      # Store up to 100 responses
        default_ttl=300,   # 5-minute expiration
        max_memory_mb=50   # Limit to 50MB
    )
    await cache.start()
    print("✅ Cache initialized\n")

    # Define some common queries
    queries = [
        "What is Python?",
        "Explain machine learning",
        "What is Python?",  # Duplicate - will use cache
        "What is quantum computing?",
        "Explain machine learning",  # Duplicate - will use cache
        "What is Python?",  # Duplicate again
    ]

    print("📊 Performance Comparison:")
    print("-" * 60)
    print(f"{'Query':<40} {'Method':<12} {'Time (s)':<10}")
    print("-" * 60)

    total_without_cache = 0
    total_with_cache = 0

    for query in queries:
        query_short = query[:35] + "..." if len(query) > 35 else query

        # Method 1: Without cache (always compute)
        start = time.time()
        response_no_cache = await engine.generate(query, max_tokens=50)
        time_no_cache = time.time() - start
        total_without_cache += time_no_cache

        print(f"{query_short:<40} {'No Cache':<12} {time_no_cache:>8.2f}")

        # Method 2: With cache (smart)
        start = time.time()

        # Check cache first
        cached_response, hit = await cache.get(query)

        if hit:
            response_cached = cached_response
            time_cached = time.time() - start
        else:
            # Not in cache, generate and store
            response_cached = await engine.generate(query, max_tokens=50)
            await cache.set(query, response_cached, ttl=300)
            time_cached = time.time() - start

        total_with_cache += time_cached

        cache_status = "CACHED ✨" if hit else "Computed  "
        print(f"{query_short:<40} {cache_status:<12} {time_cached:>8.2f}")
        print()

    # Show statistics
    print("-" * 60)
    print(f"\n{'Total time without cache:':<40} {total_without_cache:>8.2f}s")
    print(f"{'Total time with cache:':<40} {total_with_cache:>8.2f}s")

    speedup = (total_without_cache / total_with_cache) if total_with_cache > 0 else 0
    savings = total_without_cache - total_with_cache

    print(f"\n⚡ Speedup: {speedup:.1f}x faster")
    print(f"⏱️  Time saved: {savings:.1f} seconds")

    # Cache statistics
    stats = cache.get_stats()
    print(f"\n📊 Cache Statistics:")
    print(f"   Hits: {stats['hits']}")
    print(f"   Misses: {stats['misses']}")
    print(f"   Hit rate: {stats['hit_rate']:.1%}")
    print(f"   Total items: {stats['total_items']}")
    print(f"   Memory used: {stats['memory_mb']:.2f} MB")

    # Demonstrate the cached decorator
    print(f"\n" + "=" * 60)
    print("🎨 Decorator Pattern Example:")
    print("-" * 60)

    @cached(cache=cache, ttl=60)
    async def smart_answer(question: str) -> str:
        """This function automatically caches results"""
        return await engine.generate(question, max_tokens=50)

    # First call - will compute
    print("\nFirst call to smart_answer()...")
    start = time.time()
    answer1 = await smart_answer("What is AI?")
    time1 = time.time() - start
    print(f"⏱️  Time: {time1:.2f}s (computed)")

    # Second call - will use cache
    print("\nSecond call with same question...")
    start = time.time()
    answer2 = await smart_answer("What is AI?")
    time2 = time.time() - start
    print(f"⏱️  Time: {time2:.4f}s (cached - {time1/time2:.0f}x faster!)")

    # Show why this matters for edge AI
    print(f"\n" + "=" * 60)
    print("💡 Why Caching Matters for Edge AI:")
    print("-" * 60)
    print("1. ⚡ Speed: Instant responses for repeated queries")
    print("2. 🔋 Energy: Saves CPU cycles, extends battery life")
    print("3. 💰 Cost: Reduces compute requirements")
    print("4. 🌡️  Heat: Less computation = cooler devices")
    print("5. 📱 UX: Better user experience with faster responses")
    print("\nIn production: Can improve performance by 50-90%")
    print("on workloads with repeated patterns!\n")

    # Cleanup
    await cache.stop()
    await engine.cleanup()
    print("👋 Demo complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
