#!/usr/bin/env python3
"""PebbleMind Performance Benchmarking Script

Comprehensive benchmarking tool for measuring PebbleMind performance
across different components and configurations.
"""

import asyncio
import time
import statistics
import json
import psutil
import os
from pathlib import Path
from typing import Dict, Any, List
import numpy as np

from pebblemind.core import PebbleMind
from pebblemind.config import Config


class BenchmarkSuite:
    """Comprehensive benchmarking suite for PebbleMind"""

    def __init__(self, config_path: str = None):
        """Initialize benchmark suite"""
        self.config = Config.from_file(config_path) if config_path else Config()
        self.pebblemind: PebbleMind = None
        self.results = {}

    async def setup(self):
        """Setup PebbleMind instance"""
        print("🔧 Setting up PebbleMind...")
        self.pebblemind = PebbleMind(self.config)
        await self.pebblemind.initialize()
        print("✅ Setup complete")

    async def teardown(self):
        """Clean up resources"""
        if self.pebblemind:
            await self.pebblemind.stop()

    def measure_memory_usage(self) -> Dict[str, Any]:
        """Measure current memory usage"""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()

        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent()
        }

    def measure_cpu_usage(self, duration: float = 1.0) -> float:
        """Measure CPU usage over a duration"""
        process = psutil.Process(os.getpid())
        start_time = time.time()
        start_cpu_times = process.cpu_times()

        time.sleep(duration)

        end_cpu_times = process.cpu_times()
        total_time = time.time() - start_time

        user_time = end_cpu_times.user - start_cpu_times.user
        system_time = end_cpu_times.system - start_cpu_times.system

        return ((user_time + system_time) / total_time) * 100

    async def benchmark_llm_inference(self, iterations: int = 5) -> Dict[str, Any]:
        """Benchmark LLM inference performance"""
        print(f"\n🧠 Benchmarking LLM Inference ({iterations} iterations)...")

        test_prompts = [
            "Hello, how are you?",
            "Explain quantum computing in simple terms.",
            "Write a short poem about artificial intelligence.",
            "What are the benefits of renewable energy?",
            "Describe the process of photosynthesis."
        ]

        results = []

        for i, prompt in enumerate(test_prompts):
            print(f"  Testing prompt {i+1}/{len(test_prompts)}: {prompt[:50]}...")

            iteration_results = []

            for j in range(iterations):
                start_time = time.time()
                start_memory = self.measure_memory_usage()

                try:
                    response = await self.pebblemind.query(prompt)
                    end_time = time.time()
                    end_memory = self.measure_memory_usage()

                    latency = end_time - start_time
                    tokens_generated = len(response.split())
                    tokens_per_second = tokens_generated / latency

                    iteration_results.append({
                        "latency": latency,
                        "tokens_generated": tokens_generated,
                        "tokens_per_second": tokens_per_second,
                        "memory_delta_mb": end_memory["rss_mb"] - start_memory["rss_mb"]
                    })

                except Exception as e:
                    print(f"    ❌ Error: {e}")
                    continue

            if iteration_results:
                avg_latency = statistics.mean([r["latency"] for r in iteration_results])
                avg_tokens_per_sec = statistics.mean([r["tokens_per_second"] for r in iteration_results])
                avg_memory_delta = statistics.mean([r["memory_delta_mb"] for r in iteration_results])

                results.append({
                    "prompt": prompt,
                    "avg_latency": avg_latency,
                    "avg_tokens_per_second": avg_tokens_per_sec,
                    "avg_memory_delta_mb": avg_memory_delta,
                    "iterations_completed": len(iteration_results)
                })

        return {
            "component": "llm_inference",
            "overall_avg_tokens_per_second": statistics.mean([r["avg_tokens_per_second"] for r in results]),
            "overall_avg_latency": statistics.mean([r["avg_latency"] for r in results]),
            "results": results
        }

    async def benchmark_rag_search(self, iterations: int = 10) -> Dict[str, Any]:
        """Benchmark RAG search performance"""
        print(f"\n🔍 Benchmarking RAG Search ({iterations} iterations)...")

        # Add some test documents if RAG is empty
        if self.pebblemind.rag_system:
            stats = await self.pebblemind.rag_system.get_stats()
            if stats.get("total_documents", 0) == 0:
                print("  Adding test documents to RAG...")
                test_docs = [
                    {"content": "Artificial intelligence is transforming healthcare.", "metadata": {"topic": "AI"}},
                    {"content": "Machine learning algorithms can predict weather patterns.", "metadata": {"topic": "ML"}},
                    {"content": "Neural networks are inspired by biological brain structures.", "metadata": {"topic": "NN"}},
                    {"content": "Computer vision enables autonomous vehicles.", "metadata": {"topic": "CV"}},
                    {"content": "Natural language processing powers chatbots.", "metadata": {"topic": "NLP"}}
                ]
                await self.pebblemind.add_documents(test_docs)

        test_queries = [
            "What is artificial intelligence?",
            "How does machine learning work?",
            "Tell me about neural networks",
            "What is computer vision?",
            "Explain natural language processing"
        ]

        results = []

        for query in test_queries:
            print(f"  Testing query: {query}")

            iteration_results = []

            for i in range(iterations):
                start_time = time.time()

                try:
                    search_results = await self.pebblemind.rag_system.search(query, k=3)
                    end_time = time.time()

                    latency = end_time - start_time

                    iteration_results.append({
                        "latency": latency,
                        "results_count": len(search_results),
                        "has_results": len(search_results) > 0
                    })

                except Exception as e:
                    print(f"    ❌ Error: {e}")
                    continue

            if iteration_results:
                avg_latency = statistics.mean([r["latency"] for r in iteration_results])

                results.append({
                    "query": query,
                    "avg_latency": avg_latency,
                    "iterations_completed": len(iteration_results)
                })

        return {
            "component": "rag_search",
            "overall_avg_latency": statistics.mean([r["avg_latency"] for r in results]),
            "results": results
        }

    async def benchmark_voice_processing(self) -> Dict[str, Any]:
        """Benchmark voice processing performance"""
        print("\n🎤 Benchmarking Voice Processing...")

        results = {}

        # Test text-to-speech
        test_text = "Hello, this is a test of the text-to-speech system."

        try:
            print("  Testing text-to-speech...")
            start_time = time.time()
            audio_data = await self.pebblemind.voice_processor.text_to_speech(test_text)
            end_time = time.time()

            tts_latency = end_time - start_time
            audio_size = len(audio_data)

            results["text_to_speech"] = {
                "latency": tts_latency,
                "audio_size_bytes": audio_size,
                "text_length": len(test_text),
                "characters_per_second": len(test_text) / tts_latency
            }

        except Exception as e:
            print(f"  ❌ TTS Error: {e}")
            results["text_to_speech"] = {"error": str(e)}

        # Note: STT testing requires audio files, skipping for now
        results["speech_to_text"] = {
            "note": "STT benchmarking requires audio files. Use transcribe command for manual testing."
        }

        return {
            "component": "voice_processing",
            "results": results
        }

    async def benchmark_system_resources(self) -> Dict[str, Any]:
        """Benchmark system resource usage"""
        print("\n💻 Benchmarking System Resources...")

        # Get system information
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        memory = psutil.virtual_memory()

        return {
            "component": "system_info",
            "cpu_count": cpu_count,
            "cpu_freq_mhz": cpu_freq.current if cpu_freq else None,
            "total_memory_gb": memory.total / 1024 / 1024 / 1024,
            "available_memory_gb": memory.available / 1024 / 1024 / 1024,
            "memory_percent_used": memory.percent
        }

    async def run_full_benchmark(self) -> Dict[str, Any]:
        """Run complete benchmark suite"""
        print("🚀 Starting PebbleMind Benchmark Suite")
        print("=" * 50)

        await self.setup()

        try:
            # Run all benchmarks
            benchmarks = [
                self.benchmark_system_resources(),
                self.benchmark_llm_inference(),
                self.benchmark_rag_search(),
                self.benchmark_voice_processing()
            ]

            results = {}
            for benchmark in benchmarks:
                result = await benchmark
                results[result["component"]] = result

            # Add timestamp and metadata
            results["metadata"] = {
                "timestamp": time.time(),
                "config": self.config.model_dump(),
                "benchmark_version": "1.0.0"
            }

            return results

        finally:
            await self.teardown()

    def save_results(self, results: Dict[str, Any], output_file: str = "benchmark_results.json"):
        """Save benchmark results to file"""
        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"📊 Results saved to {output_path}")

    def print_summary(self, results: Dict[str, Any]):
        """Print benchmark summary"""
        print("\n📈 Benchmark Summary")
        print("=" * 30)

        if "system_info" in results:
            sys_info = results["system_info"]
            print("💻 System:")
            print(f"   CPU Cores: {sys_info['cpu_count']}")
            if sys_info['cpu_freq_mhz']:
                print(f"   CPU Freq: {sys_info['cpu_freq_mhz']:.0f} MHz")
            print(f"   Memory: {sys_info['total_memory_gb']:.1f} GB total")

        if "llm_inference" in results:
            llm_info = results["llm_inference"]
            print("🧠 LLM Inference:")
            print(f"   Avg Tokens/Second: {llm_info['overall_avg_tokens_per_second']:.2f}")
            print(f"   Avg Latency: {llm_info['overall_avg_latency']:.2f}s")

        if "rag_search" in results:
            rag_info = results["rag_search"]
            print("🔍 RAG Search:")
            print(f"   Avg Latency: {rag_info['overall_avg_latency']:.4f}s")

        if "voice_processing" in results:
            voice_info = results["voice_processing"]
            if "text_to_speech" in voice_info["results"]:
                tts = voice_info["results"]["text_to_speech"]
                if "latency" in tts:
                    print("🎤 Text-to-Speech:")
                    print(f"   Latency: {tts['latency']:.2f}s")
                    print(f"   Characters/Second: {tts['characters_per_second']:.1f}")


async def main():
    """Main benchmark function"""
    import argparse

    parser = argparse.ArgumentParser(description="PebbleMind Benchmark Suite")
    parser.add_argument("--config", "-c", help="Path to configuration file")
    parser.add_argument("--output", "-o", default="benchmark_results.json", help="Output file for results")
    parser.add_argument("--iterations", "-i", type=int, default=5, help="Number of iterations per test")

    args = parser.parse_args()

    # Run benchmark
    suite = BenchmarkSuite(args.config)

    try:
        results = await suite.run_full_benchmark()

        # Print summary
        suite.print_summary(results)

        # Save results
        suite.save_results(results, args.output)

        print(f"\n✅ Benchmark complete! Results saved to {args.output}")

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
