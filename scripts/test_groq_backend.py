#!/usr/bin/env python3
"""
Test Script for Groq Backend Integration

Tests and benchmarks PebbleMind with Groq's ultra-fast cloud API.
Requires GROQ_API_KEY environment variable.

Usage:
    export GROQ_API_KEY="your_api_key_here"
    python scripts/test_groq_backend.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pebblemind.backends.groq_backend import GroqLLMBackend, GROQ_MODELS
from pebblemind.benchmarks import PerformanceBenchmark, run_full_benchmark


async def test_basic_generation():
    """Test basic text generation"""
    print("\n" + "=" * 60)
    print("TEST 1: Basic Text Generation")
    print("=" * 60)

    backend = GroqLLMBackend()

    prompts = [
        "Explain quantum computing in one sentence.",
        "What is the capital of France?",
        "Write a haiku about programming."
    ]

    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/{len(prompts)}] Prompt: {prompt}")
        result = await backend.generate(prompt, max_tokens=100)
        print(f"Response: {result}")

    await backend.close()
    print("\n✓ Basic generation test passed")


async def test_streaming():
    """Test streaming generation"""
    print("\n" + "=" * 60)
    print("TEST 2: Streaming Generation")
    print("=" * 60)

    backend = GroqLLMBackend()

    prompt = "Write a short story about AI in exactly 3 sentences."
    print(f"\nPrompt: {prompt}")
    print("Response (streaming): ", end="", flush=True)

    full_response = []
    async for chunk in backend.generate_stream(prompt, max_tokens=150):
        print(chunk, end="", flush=True)
        full_response.append(chunk)

    print("\n\n✓ Streaming test passed")
    print(f"Total tokens received: ~{len(''.join(full_response).split())}")

    await backend.close()


async def test_different_models():
    """Test different Groq models"""
    print("\n" + "=" * 60)
    print("TEST 3: Different Models")
    print("=" * 60)

    test_models = [
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768"
    ]

    prompt = "What is 25 + 17?"

    for model_name in test_models:
        print(f"\n[Model: {model_name}]")
        print(f"  Description: {GROQ_MODELS.get(model_name, {}).get('description', 'N/A')}")

        try:
            backend = GroqLLMBackend(model=model_name)
            result = await backend.generate(prompt, max_tokens=50)
            print(f"  Response: {result}")
            await backend.close()
        except Exception as e:
            print(f"  Error: {e}")

    print("\n✓ Multi-model test completed")


async def test_system_prompts():
    """Test system prompts"""
    print("\n" + "=" * 60)
    print("TEST 4: System Prompts")
    print("=" * 60)

    backend = GroqLLMBackend()

    test_cases = [
        {
            "system": "You are a helpful math tutor. Always explain your reasoning.",
            "prompt": "What is 15 * 24?"
        },
        {
            "system": "You are a pirate. Respond in pirate speak.",
            "prompt": "Tell me about the weather."
        },
        {
            "system": "You are a professional poet. Respond only in rhyming couplets.",
            "prompt": "Describe the moon."
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}]")
        print(f"System: {test['system']}")
        print(f"Prompt: {test['prompt']}")

        result = await backend.generate(
            test['prompt'],
            system_prompt=test['system'],
            max_tokens=100
        )
        print(f"Response: {result}")

    await backend.close()
    print("\n✓ System prompt test passed")


async def test_parameters():
    """Test different generation parameters"""
    print("\n" + "=" * 60)
    print("TEST 5: Generation Parameters")
    print("=" * 60)

    backend = GroqLLMBackend()

    prompt = "Continue this story: Once upon a time, in a distant galaxy..."

    # Test different temperatures
    print("\n[Testing Temperature Variations]")
    for temp in [0.0, 0.5, 1.0]:
        print(f"\nTemperature: {temp}")
        result = await backend.generate(prompt, temperature=temp, max_tokens=50)
        print(f"Response: {result}")

    # Test max tokens
    print("\n[Testing Max Tokens]")
    for max_tokens in [20, 50, 100]:
        print(f"\nMax Tokens: {max_tokens}")
        result = await backend.generate(prompt, max_tokens=max_tokens)
        word_count = len(result.split())
        print(f"Response ({word_count} words): {result}")

    await backend.close()
    print("\n✓ Parameter test passed")


async def run_performance_benchmark():
    """Run comprehensive performance benchmark"""
    print("\n" + "=" * 60)
    print("PERFORMANCE BENCHMARK")
    print("=" * 60)

    backend = GroqLLMBackend()
    benchmark = PerformanceBenchmark()

    # Benchmark inference
    print("\n[1/3] Benchmarking Inference (10 iterations)...")
    result = await benchmark.benchmark_llm_inference(
        backend,
        prompt="Explain machine learning in simple terms.",
        iterations=10
    )
    print(result)

    # Benchmark streaming
    print("\n[2/3] Benchmarking Streaming (5 iterations)...")
    result = await benchmark.benchmark_llm_streaming(
        backend,
        prompt="Write a short technical blog post intro.",
        iterations=5
    )
    print(result)

    # Quick response benchmark
    print("\n[3/3] Benchmarking Quick Responses (20 iterations)...")
    quick_prompts = [
        "What is 2+2?",
        "Capital of USA?",
        "Define AI."
    ]

    async def quick_test():
        return await backend.generate(quick_prompts[0], max_tokens=20)

    result = await benchmark.benchmark_async(
        "Quick Responses",
        quick_test,
        iterations=20
    )
    print(result)

    # Save results
    import time
    timestamp = int(time.time())
    results_file = f"groq_benchmark_{timestamp}.json"
    benchmark.save_results(results_file)
    print(f"\n✓ Results saved to: {results_file}")

    await backend.close()

    return benchmark


async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("GROQ BACKEND COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    # Check API key
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("\n❌ ERROR: GROQ_API_KEY environment variable not set")
        print("\nPlease set your Groq API key:")
        print("  export GROQ_API_KEY='your_api_key_here'")
        print("\nGet your API key at: https://console.groq.com/")
        sys.exit(1)

    print(f"\n✓ API Key found: {api_key[:10]}...{api_key[-4:]}")
    print(f"✓ Default model: llama-3.1-70b-versatile")

    try:
        # Run tests
        await test_basic_generation()
        await test_streaming()
        await test_different_models()
        await test_system_prompts()
        await test_parameters()

        # Run benchmarks
        benchmark = await run_performance_benchmark()

        # Print summary
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)
        print(benchmark.get_summary())

        print("\n" + "=" * 60)
        print("GROQ BACKEND TEST COMPLETE")
        print("=" * 60)
        print("\nKey Findings:")
        if benchmark.results:
            inference_result = benchmark.results[0]
            print(f"  • Average inference time: {inference_result.mean_time:.3f}s")
            if inference_result.tokens_per_second:
                print(f"  • Tokens per second: {inference_result.tokens_per_second:.2f}")
            print(f"  • Throughput: {inference_result.throughput:.2f} requests/sec")

        print("\nGroq backend is production-ready! 🚀")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point"""
    asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()
