"""
Performance Benchmarking Suite for PebbleMind

Measures actual performance of LLM inference, RAG, and other components
with real-world workloads.
"""

import logging
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Results from a single benchmark"""

    name: str
    total_time: float
    iterations: int
    mean_time: float
    median_time: float
    std_dev: float
    min_time: float
    max_time: float
    tokens_per_second: Optional[float] = None
    throughput: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "total_time": self.total_time,
            "iterations": self.iterations,
            "mean_time": self.mean_time,
            "median_time": self.median_time,
            "std_dev": self.std_dev,
            "min_time": self.min_time,
            "max_time": self.max_time,
            "tokens_per_second": self.tokens_per_second,
            "throughput": self.throughput,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """Human-readable representation"""
        lines = [
            f"Benchmark: {self.name}",
            f"  Iterations: {self.iterations}",
            f"  Total Time: {self.total_time:.2f}s",
            f"  Mean: {self.mean_time:.3f}s",
            f"  Median: {self.median_time:.3f}s",
            f"  Std Dev: {self.std_dev:.3f}s",
            f"  Min: {self.min_time:.3f}s",
            f"  Max: {self.max_time:.3f}s",
        ]

        if self.tokens_per_second:
            lines.append(f"  Tokens/sec: {self.tokens_per_second:.2f}")

        if self.throughput:
            lines.append(f"  Throughput: {self.throughput:.2f} ops/sec")

        if self.metadata:
            lines.append("  Metadata:")
            for key, value in self.metadata.items():
                lines.append(f"    {key}: {value}")

        return "\n".join(lines)


class PerformanceBenchmark:
    """Performance benchmarking utility"""

    def __init__(self):
        """Initialize benchmark"""
        self.results: List[BenchmarkResult] = []

    async def benchmark_async(
        self, name: str, func: Callable, iterations: int = 10, warmup: int = 2, **kwargs
    ) -> BenchmarkResult:
        """
        Benchmark an async function

        Args:
            name: Benchmark name
            func: Async function to benchmark
            iterations: Number of iterations
            warmup: Number of warmup iterations
            **kwargs: Arguments to pass to function

        Returns:
            BenchmarkResult
        """
        logger.info(f"Running benchmark: {name} ({iterations} iterations)")

        # Warmup
        for _ in range(warmup):
            await func(**kwargs)

        # Benchmark
        times = []
        start_total = time.perf_counter()

        for i in range(iterations):
            start = time.perf_counter()
            await func(**kwargs)
            end = time.perf_counter()
            times.append(end - start)

            if (i + 1) % 10 == 0:
                logger.info(f"  Completed {i + 1}/{iterations} iterations")

        end_total = time.perf_counter()
        total_time = end_total - start_total

        result = BenchmarkResult(
            name=name,
            total_time=total_time,
            iterations=iterations,
            mean_time=statistics.mean(times),
            median_time=statistics.median(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0.0,
            min_time=min(times),
            max_time=max(times),
            throughput=iterations / total_time,
        )

        self.results.append(result)
        return result

    def benchmark_sync(
        self, name: str, func: Callable, iterations: int = 10, warmup: int = 2, **kwargs
    ) -> BenchmarkResult:
        """
        Benchmark a synchronous function

        Args:
            name: Benchmark name
            func: Function to benchmark
            iterations: Number of iterations
            warmup: Number of warmup iterations
            **kwargs: Arguments to pass to function

        Returns:
            BenchmarkResult
        """
        logger.info(f"Running benchmark: {name} ({iterations} iterations)")

        # Warmup
        for _ in range(warmup):
            func(**kwargs)

        # Benchmark
        times = []
        start_total = time.perf_counter()

        for i in range(iterations):
            start = time.perf_counter()
            func(**kwargs)
            end = time.perf_counter()
            times.append(end - start)

            if (i + 1) % 10 == 0:
                logger.info(f"  Completed {i + 1}/{iterations} iterations")

        end_total = time.perf_counter()
        total_time = end_total - start_total

        result = BenchmarkResult(
            name=name,
            total_time=total_time,
            iterations=iterations,
            mean_time=statistics.mean(times),
            median_time=statistics.median(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0.0,
            min_time=min(times),
            max_time=max(times),
            throughput=iterations / total_time,
        )

        self.results.append(result)
        return result

    async def benchmark_llm_inference(
        self,
        llm_backend,
        prompt: str = "Explain quantum computing in simple terms.",
        iterations: int = 5,
    ) -> BenchmarkResult:
        """
        Benchmark LLM inference

        Args:
            llm_backend: LLM backend to benchmark
            prompt: Test prompt
            iterations: Number of iterations

        Returns:
            BenchmarkResult
        """

        async def run_inference():
            return await llm_backend.generate(prompt=prompt, max_tokens=100)

        result = await self.benchmark_async(
            name="LLM Inference", func=run_inference, iterations=iterations
        )

        # Calculate tokens per second (estimate)
        # Assuming ~100 tokens generated per run
        tokens_generated = 100 * iterations
        result.tokens_per_second = tokens_generated / result.total_time
        result.metadata = {
            "prompt": prompt[:50] + "...",
            "max_tokens": 100,
            "backend": type(llm_backend).__name__,
        }

        return result

    async def benchmark_llm_streaming(
        self,
        llm_backend,
        prompt: str = "Write a short story about AI.",
        iterations: int = 3,
    ) -> BenchmarkResult:
        """
        Benchmark LLM streaming

        Args:
            llm_backend: LLM backend to benchmark
            prompt: Test prompt
            iterations: Number of iterations

        Returns:
            BenchmarkResult
        """

        async def run_streaming():
            chunks = []
            async for chunk in llm_backend.generate_stream(
                prompt=prompt, max_tokens=100
            ):
                chunks.append(chunk)
            return "".join(chunks)

        result = await self.benchmark_async(
            name="LLM Streaming", func=run_streaming, iterations=iterations
        )

        result.metadata = {
            "prompt": prompt[:50] + "...",
            "max_tokens": 100,
            "backend": type(llm_backend).__name__,
        }

        return result

    async def benchmark_rag_search(
        self, rag_system, queries: List[str] = None, iterations: int = 10
    ) -> BenchmarkResult:
        """
        Benchmark RAG search

        Args:
            rag_system: RAG system to benchmark
            queries: Test queries
            iterations: Number of iterations

        Returns:
            BenchmarkResult
        """
        if queries is None:
            queries = [
                "What is machine learning?",
                "Explain neural networks",
                "How does Python work?",
                "Tell me about databases",
            ]

        async def run_search():
            query = queries[0]  # Use first query for consistency
            return await rag_system.search(query, k=5)

        result = await self.benchmark_async(
            name="RAG Search", func=run_search, iterations=iterations
        )

        result.metadata = {"queries": len(queries), "k": 5}

        return result

    async def benchmark_rag_indexing(
        self, rag_system, documents: List[Dict[str, Any]], iterations: int = 3
    ) -> BenchmarkResult:
        """
        Benchmark RAG document indexing

        Args:
            rag_system: RAG system to benchmark
            documents: Test documents
            iterations: Number of iterations

        Returns:
            BenchmarkResult
        """

        async def run_indexing():
            await rag_system.add_documents(documents)

        result = await self.benchmark_async(
            name="RAG Indexing", func=run_indexing, iterations=iterations
        )

        result.metadata = {
            "documents": len(documents),
            "total_chars": sum(len(d.get("content", "")) for d in documents),
        }

        return result

    def get_summary(self) -> str:
        """Get summary of all benchmarks"""
        if not self.results:
            return "No benchmarks run"

        lines = ["=" * 60, "BENCHMARK SUMMARY", "=" * 60, ""]

        for result in self.results:
            lines.append(str(result))
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def save_results(self, filepath: str):
        """Save results to JSON file"""
        import json
        from pathlib import Path

        data = {
            "timestamp": time.time(),
            "results": [r.to_dict() for r in self.results],
        }

        Path(filepath).write_text(json.dumps(data, indent=2))
        logger.info(f"Saved benchmark results to: {filepath}")


async def run_full_benchmark(llm_backend, rag_system=None) -> PerformanceBenchmark:
    """
    Run a comprehensive benchmark suite

    Args:
        llm_backend: LLM backend to benchmark
        rag_system: RAG system to benchmark (optional)

    Returns:
        PerformanceBenchmark with results
    """
    benchmark = PerformanceBenchmark()

    print("Starting comprehensive performance benchmark...")
    print("=" * 60)

    # Benchmark LLM inference
    print("\n[1/4] Benchmarking LLM Inference...")
    result = await benchmark.benchmark_llm_inference(llm_backend, iterations=5)
    print(result)

    # Benchmark LLM streaming
    print("\n[2/4] Benchmarking LLM Streaming...")
    result = await benchmark.benchmark_llm_streaming(llm_backend, iterations=3)
    print(result)

    if rag_system:
        # Benchmark RAG search
        print("\n[3/4] Benchmarking RAG Search...")
        result = await benchmark.benchmark_rag_search(rag_system, iterations=10)
        print(result)

        # Benchmark RAG indexing
        print("\n[4/4] Benchmarking RAG Indexing...")
        test_docs = [
            {"content": f"This is test document {i} with some sample content." * 10}
            for i in range(5)
        ]
        result = await benchmark.benchmark_rag_indexing(
            rag_system, test_docs, iterations=3
        )
        print(result)
    else:
        print("\n[3/4] Skipping RAG benchmarks (no RAG system provided)")
        print("[4/4] Skipping RAG benchmarks (no RAG system provided)")

    print("\n" + "=" * 60)
    print("Benchmark complete!")

    return benchmark
