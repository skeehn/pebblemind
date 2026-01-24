"""
Reliable Edge AI Example
Demonstrates production-grade error handling for edge devices
"""

import asyncio
import random
from pebblemind.config import get_config
from pebblemind.core.llm import LLMEngine
from pebblemind.utils.error_handler import ErrorHandler, with_retry


async def main():
    """Demonstrate robust error handling for edge AI"""
    print("\n🛡️  PebbleMind Reliable Edge AI Demo")
    print("=" * 60)
    print("This example shows production-grade error handling")
    print("crucial for edge devices with unstable conditions\n")

    # Load configuration
    try:
        config = get_config()
    except FileNotFoundError:
        print("❌ Config file not found. Run: python install.py")
        return

    # Initialize error handler with exponential backoff
    error_handler = ErrorHandler(
        max_retries=3,
        base_delay=0.5,
        exponential_base=2,
        jitter=True,
        enable_logging=True
    )

    # Initialize LLM
    print("⏳ Loading model...")
    engine = LLMEngine(config.llm)

    try:
        await engine.initialize()
        print(f"✅ Ready ({config.llm.model_size.upper()} model)\n")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return

    # Example 1: Simulate unreliable API
    print("=" * 60)
    print("Example 1: Automatic Retry with Exponential Backoff")
    print("-" * 60)

    attempt_count = [0]

    async def unreliable_generation(query: str) -> str:
        """Simulates unreliable API that may fail"""
        attempt_count[0] += 1

        # Simulate 50% failure rate
        if random.random() < 0.5:
            print(f"  ⚠️  Attempt {attempt_count[0]}: Connection error")
            raise ConnectionError("Network timeout")

        print(f"  ✅ Attempt {attempt_count[0]}: Success!")
        return await engine.generate(query, max_tokens=50)

    print("\nTrying query with automatic retry...")
    try:
        result = await error_handler.handle_async(
            unreliable_generation,
            "What is Python?",
            retryable_exceptions=(ConnectionError,)
        )
        print(f"\n💬 Final result: {result[:100]}...")
    except Exception as e:
        print(f"\n❌ Failed after {error_handler.max_retries} retries: {e}")

    # Example 2: Fallback mechanism
    print(f"\n" + "=" * 60)
    print("Example 2: Fallback for Edge Device Failures")
    print("-" * 60)

    async def primary_service(query: str) -> str:
        """Primary (complex) response"""
        print("  🎯 Trying primary service...")
        # Simulate occasional failure
        if random.random() < 0.3:
            raise RuntimeError("Out of memory")
        return await engine.generate(query, max_tokens=100)

    async def fallback_service(query: str) -> str:
        """Fallback (simpler) response"""
        print("  🔄 Using fallback service...")
        return await engine.generate(query, max_tokens=30)

    print("\nQuerying with fallback protection...")
    try:
        result = await error_handler.handle_async(
            primary_service,
            "Explain machine learning",
            fallback=fallback_service,
            retryable_exceptions=(RuntimeError,)
        )
        print(f"\n💬 Result: {result[:150]}...")
    except Exception as e:
        print(f"\n❌ Both primary and fallback failed: {e}")

    # Example 3: Decorator pattern
    print(f"\n" + "=" * 60)
    print("Example 3: Retry Decorator (Clean API)")
    print("-" * 60)

    failure_count = [0]

    @with_retry(max_retries=3, retryable_exceptions=(TimeoutError,))
    async def flaky_function():
        """Simulates flaky operation"""
        failure_count[0] += 1

        if failure_count[0] < 3:
            print(f"  ⏱️  Attempt {failure_count[0]}: Timeout...")
            raise TimeoutError("Operation timed out")

        print(f"  ✅ Attempt {failure_count[0]}: Success!")
        return "Success after retries!"

    print("\nCalling flaky function with decorator...")
    result = await flaky_function()
    print(f"\n💬 Result: {result}")

    # Example 4: Graceful degradation
    print(f"\n" + "=" * 60)
    print("Example 4: Graceful Degradation Under Stress")
    print("-" * 60)

    async def adaptive_generation(query: str, max_retries: int = 2):
        """
        Progressively reduce quality if under stress
        Critical for edge devices with limited resources
        """
        quality_levels = [
            {'max_tokens': 200, 'desc': 'Full quality'},
            {'max_tokens': 100, 'desc': 'Medium quality'},
            {'max_tokens': 50, 'desc': 'Low quality'},
        ]

        for i, quality in enumerate(quality_levels):
            try:
                print(f"  🎯 Trying {quality['desc']}...")

                # Simulate stress conditions
                if i < 2 and random.random() < 0.5:
                    raise MemoryError("Insufficient memory")

                response = await engine.generate(
                    query,
                    max_tokens=quality['max_tokens']
                )

                print(f"  ✅ Success with {quality['desc']}")
                return response

            except MemoryError:
                if i < len(quality_levels) - 1:
                    print(f"  ⚠️  Failed, trying lower quality...")
                    await asyncio.sleep(0.5)
                else:
                    return "System under stress. Please try again later."

    print("\nAdaptive quality under stress...")
    result = await adaptive_generation("What is AI?")
    print(f"\n💬 Result: {result[:100]}...")

    # Show error statistics
    print(f"\n" + "=" * 60)
    print("Error Handling Statistics")
    print("-" * 60)

    stats = error_handler.get_stats()
    print(f"\n📊 Handler Stats:")
    print(f"   Total errors: {stats['total_errors']}")
    print(f"   Retried operations: {stats['retried_operations']}")
    print(f"   Successful retries: {stats['successful_retries']}")
    print(f"   Failed retries: {stats['failed_retries']}")
    print(f"   Fallbacks used: {stats['fallbacks_used']}")

    if stats['retried_operations'] > 0:
        print(f"   Success rate: {stats['retry_success_rate']:.1%}")

    # Production best practices
    print(f"\n" + "=" * 60)
    print("💡 Edge AI Error Handling Best Practices")
    print("-" * 60)
    print("""
1. ⚡ Exponential Backoff
   - Prevents overwhelming stressed devices
   - Add jitter to avoid thundering herd
   - Cap maximum delay (don't wait forever)

2. 🔄 Fallback Mechanisms
   - Simple fallback for complex operations
   - Degrade gracefully under stress
   - Always have a "last resort" response

3. 🎯 Retry Strategy
   - Only retry transient errors (network, memory)
   - Don't retry permanent errors (invalid input)
   - Set reasonable retry limits

4. 📊 Monitoring
   - Track error rates and patterns
   - Alert on sustained high error rates
   - Use metrics for capacity planning

5. 🛡️  Circuit Breaker
   - Stop retrying after repeated failures
   - Allow system time to recover
   - Prevent cascading failures

6. 💾 State Management
   - Save state before risky operations
   - Allow resume after failures
   - Implement idempotency where possible
    """)

    print("🎯 Why This Matters for Edge AI:")
    print("-" * 60)
    print("""
Edge devices face unique challenges:
- 📱 Limited resources (CPU, memory, battery)
- 🌐 Unreliable connectivity
- 🔋 Power constraints
- 🌡️  Thermal throttling
- 📶 Variable network conditions

Robust error handling is CRITICAL for production edge AI!
    """)

    # Cleanup
    await engine.cleanup()
    print("\n👋 Demo complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
