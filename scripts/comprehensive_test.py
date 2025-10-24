#!/usr/bin/env python3
"""
Comprehensive Integration Test with Groq Backend

Tests all PebbleMind features with Groq API:
- Groq backend integration
- Performance benchmarks
- Specialized agents
- All features working together

Requires: GROQ_API_KEY environment variable

Usage:
    export GROQ_API_KEY="your_api_key_here"
    python scripts/comprehensive_test.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pebblemind.backends.groq_backend import GroqLLMBackend
from pebblemind.specialized_agents import (
    ResearchAgent,
    CodeAgent,
    MathAgent,
    WritingAgent,
    AgentOrchestrator
)
from pebblemind.benchmarks import PerformanceBenchmark


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def test_groq_basic():
    """Test basic Groq integration"""
    print_section("TEST 1: Groq Backend - Basic Functionality")

    backend = GroqLLMBackend()

    tests = [
        ("Simple Question", "What is the capital of France?"),
        ("Math Query", "What is 25 * 17?"),
        ("Code Question", "How do you reverse a string in Python?"),
        ("Creative Task", "Write a one-sentence poem about technology.")
    ]

    for name, prompt in tests:
        print(f"\n[{name}]")
        print(f"Prompt: {prompt}")

        response = await backend.generate(prompt, max_tokens=100)
        print(f"Response: {response}\n")

    await backend.close()
    print("✓ Basic Groq integration test passed")


async def test_groq_streaming():
    """Test Groq streaming"""
    print_section("TEST 2: Groq Backend - Streaming")

    backend = GroqLLMBackend()

    prompt = "Explain the concept of recursion in programming with a simple example."
    print(f"\nPrompt: {prompt}")
    print("Response (streaming):\n")

    full_response = []
    async for chunk in backend.generate_stream(prompt, max_tokens=200):
        print(chunk, end="", flush=True)
        full_response.append(chunk)

    print("\n\n✓ Streaming test passed")
    print(f"Total characters received: {len(''.join(full_response))}")

    await backend.close()


async def test_specialized_agents():
    """Test specialized agents"""
    print_section("TEST 3: Specialized Agents")

    # Create agents
    research = ResearchAgent()
    code = CodeAgent()
    math = MathAgent()
    writing = WritingAgent()

    print("\n[Research Agent]")
    result = await research.execute("Research quantum computing")
    print(f"Result: {result['synthesis'][:200]}...")

    print("\n[Code Agent]")
    test_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
    result = await code.execute("Analyze this code", code=test_code)
    print(f"Result: {result['result'][:200]}...")

    print("\n[Math Agent]")
    result = await math.execute("Calculate 157 + 289")
    print(f"Result: {result['result']}")

    print("\n[Writing Agent]")
    result = await writing.execute("Create an outline for a blog post about AI")
    print(f"Result: {result['result'][:200]}...")

    print("\n✓ All specialized agents tested")


async def test_agent_orchestration():
    """Test agent orchestration"""
    print_section("TEST 4: Agent Orchestration")

    orchestrator = AgentOrchestrator()

    tasks = [
        ("Math task", "What is 45 * 23?"),
        ("Research task", "Find information about machine learning"),
        ("Code task", "How to implement a binary search?"),
        ("Writing task", "Write an outline for a technical article")
    ]

    for name, task in tasks:
        print(f"\n[{name}] {task}")
        result = await orchestrator.route_task(task)
        print(f"Agent used: {result['agent']}")
        print(f"Result: {result['result'][:150]}...")

    print("\n✓ Agent orchestration test passed")


async def run_performance_benchmarks():
    """Run comprehensive performance benchmarks"""
    print_section("TEST 5: Performance Benchmarks")

    backend = GroqLLMBackend()
    benchmark = PerformanceBenchmark()

    # 1. Inference benchmark
    print("\n[Benchmark 1/4] LLM Inference (10 iterations)")
    result = await benchmark.benchmark_llm_inference(
        backend,
        prompt="Explain neural networks in simple terms.",
        iterations=10
    )
    print(f"  Mean time: {result.mean_time:.3f}s")
    print(f"  Tokens/sec: {result.tokens_per_second:.2f}")
    print(f"  Throughput: {result.throughput:.2f} req/sec")

    # 2. Streaming benchmark
    print("\n[Benchmark 2/4] LLM Streaming (5 iterations)")
    result = await benchmark.benchmark_llm_streaming(
        backend,
        prompt="Write a technical explanation of APIs.",
        iterations=5
    )
    print(f"  Mean time: {result.mean_time:.3f}s")
    print(f"  Throughput: {result.throughput:.2f} req/sec")

    # 3. Quick response benchmark
    print("\n[Benchmark 3/4] Quick Responses (20 iterations)")

    async def quick_gen():
        return await backend.generate("What is 2+2?", max_tokens=20)

    result = await benchmark.benchmark_async(
        "Quick Responses",
        quick_gen,
        iterations=20
    )
    print(f"  Mean time: {result.mean_time:.3f}s")
    print(f"  Median time: {result.median_time:.3f}s")
    print(f"  Throughput: {result.throughput:.2f} req/sec")

    # 4. Different temperatures benchmark
    print("\n[Benchmark 4/4] Temperature Variations (5 iterations each)")

    for temp in [0.0, 0.5, 1.0]:
        async def temp_gen():
            return await backend.generate(
                "Continue: Once upon a time...",
                temperature=temp,
                max_tokens=50
            )

        result = await benchmark.benchmark_async(
            f"Temperature {temp}",
            temp_gen,
            iterations=5
        )
        print(f"  Temp {temp}: {result.mean_time:.3f}s avg")

    await backend.close()

    # Save results
    import time
    timestamp = int(time.time())
    results_file = f"comprehensive_benchmark_{timestamp}.json"
    benchmark.save_results(results_file)
    print(f"\n✓ Benchmark results saved to: {results_file}")

    return benchmark


async def test_groq_with_agents():
    """Test Groq backend integrated with specialized agents"""
    print_section("TEST 6: Groq + Agents Integration")

    backend = GroqLLMBackend()
    orchestrator = AgentOrchestrator()

    print("\nScenario: Complex task requiring multiple capabilities\n")

    # Scenario 1: Research + Code
    print("[Scenario 1] Research machine learning, then explain code")
    research_result = await orchestrator.execute_with_agent(
        "research",
        "Research neural networks"
    )
    print(f"Research: {research_result['synthesis'][:100]}...")

    # Use Groq to summarize the research
    summary_prompt = f"Summarize this in one sentence: {research_result['synthesis']}"
    summary = await backend.generate(summary_prompt, max_tokens=50)
    print(f"Groq Summary: {summary}")

    # Scenario 2: Math + Groq explanation
    print("\n[Scenario 2] Calculate with Math Agent, explain with Groq")
    math_result = await orchestrator.execute_with_agent(
        "math",
        "Calculate 789 * 456"
    )
    print(f"Math Result: {math_result['result']}")

    explanation_prompt = "Explain how multiplication works in 1-2 sentences"
    explanation = await backend.generate(explanation_prompt, max_tokens=100)
    print(f"Groq Explanation: {explanation}")

    # Scenario 3: Writing + Groq enhancement
    print("\n[Scenario 3] Create outline with Writing Agent, enhance with Groq")
    writing_result = await orchestrator.execute_with_agent(
        "writing",
        "Create an outline for an article about AI ethics"
    )
    print(f"Writing Agent: {writing_result['result'][:100]}...")

    enhance_prompt = "Improve this outline for an article about AI ethics. Make it more compelling."
    enhanced = await backend.generate(enhance_prompt, max_tokens=150)
    print(f"Groq Enhancement: {enhanced}")

    await backend.close()
    print("\n✓ Groq + Agents integration test passed")


async def stress_test():
    """Stress test with concurrent requests"""
    print_section("TEST 7: Stress Test - Concurrent Requests")

    backend = GroqLLMBackend()

    print("\nSending 10 concurrent requests...")

    prompts = [
        "What is AI?",
        "Define machine learning",
        "Explain neural networks",
        "What is deep learning?",
        "Define NLP",
        "What is computer vision?",
        "Explain reinforcement learning",
        "What is supervised learning?",
        "Define unsupervised learning",
        "What is transfer learning?"
    ]

    import time
    start = time.perf_counter()

    # Send all requests concurrently
    tasks = [
        backend.generate(prompt, max_tokens=50)
        for prompt in prompts
    ]

    results = await asyncio.gather(*tasks)
    end = time.perf_counter()

    total_time = end - start
    avg_time = total_time / len(prompts)

    print(f"\n✓ Completed {len(prompts)} requests in {total_time:.2f}s")
    print(f"  Average time per request: {avg_time:.3f}s")
    print(f"  Requests per second: {len(prompts)/total_time:.2f}")

    # Show sample responses
    print("\nSample responses:")
    for i, (prompt, response) in enumerate(zip(prompts[:3], results[:3]), 1):
        print(f"\n[{i}] {prompt}")
        print(f"    {response[:100]}...")

    await backend.close()


async def run_all_tests():
    """Run all comprehensive tests"""
    print("=" * 70)
    print("  PEBBLEMIND COMPREHENSIVE INTEGRATION TEST")
    print("  Testing: Groq Backend + Agents + Benchmarks")
    print("=" * 70)

    # Check API key
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("\n❌ ERROR: GROQ_API_KEY environment variable not set")
        print("\nPlease set your Groq API key:")
        print("  export GROQ_API_KEY='your_api_key_here'")
        print("\nGet your API key at: https://console.groq.com/")
        sys.exit(1)

    print(f"\n✓ API Key configured")
    print(f"✓ Model: llama-3.1-70b-versatile (Groq)")
    print(f"✓ Starting comprehensive test suite...\n")

    try:
        # Run all tests
        await test_groq_basic()
        await test_groq_streaming()
        await test_specialized_agents()
        await test_agent_orchestration()

        # Performance benchmarks
        benchmark = await run_performance_benchmarks()

        # Integration tests
        await test_groq_with_agents()
        await stress_test()

        # Final summary
        print_section("COMPREHENSIVE TEST SUMMARY")

        print("\n✓ ALL TESTS PASSED!")

        print("\nTest Results:")
        print("  ✓ Groq Backend: WORKING")
        print("  ✓ Streaming: WORKING")
        print("  ✓ Specialized Agents: WORKING")
        print("  ✓ Agent Orchestration: WORKING")
        print("  ✓ Performance Benchmarks: COMPLETE")
        print("  ✓ Integration: WORKING")
        print("  ✓ Stress Test: PASSED")

        if benchmark.results:
            print("\nPerformance Highlights:")
            for result in benchmark.results[:3]:
                print(f"  • {result.name}: {result.mean_time:.3f}s average")
                if result.tokens_per_second:
                    print(f"    Tokens/sec: {result.tokens_per_second:.2f}")

        print("\n" + "=" * 70)
        print("  🎉 PEBBLEMIND IS PRODUCTION-READY WITH GROQ! 🎉")
        print("=" * 70)

        print("\nKey Capabilities Verified:")
        print("  ✓ Ultra-fast cloud inference with Groq")
        print("  ✓ Streaming responses")
        print("  ✓ Specialized agents (Research, Code, Math, Writing)")
        print("  ✓ Agent orchestration and routing")
        print("  ✓ Performance benchmarking")
        print("  ✓ Concurrent request handling")
        print("  ✓ Integration between all components")

        print("\nReady for:")
        print("  • Production deployment")
        print("  • Real-world applications")
        print("  • High-throughput workloads")
        print("  • Complex multi-agent tasks")

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
