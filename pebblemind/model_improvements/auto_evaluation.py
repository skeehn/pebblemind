"""
Automatic evaluation framework for testing model improvements.

Provides benchmarks and metrics to measure model quality objectively.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class EvaluationMetric(Enum):
    """Evaluation metrics"""
    ACCURACY = "accuracy"
    BLEU = "bleu"
    ROUGE = "rouge"
    PERPLEXITY = "perplexity"
    LATENCY = "latency"
    EXACT_MATCH = "exact_match"
    F1 = "f1"


@dataclass
class EvaluationExample:
    """Single evaluation example"""
    input: str
    expected_output: str
    category: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EvaluationResult:
    """Result of evaluation"""
    metric_scores: Dict[str, float]
    latency_ms: float
    examples_tested: int
    passed: int
    failed: int
    details: List[Dict[str, Any]]


class AutoEvaluator:
    """
    Automatic evaluation framework for model testing.

    Features:
    - Multiple evaluation metrics
    - Benchmark datasets
    - Performance tracking
    - Comparative analysis
    """

    def __init__(self):
        """Initialize evaluator"""
        self.benchmarks = self._load_benchmarks()

    def _load_benchmarks(self) -> Dict[str, List[EvaluationExample]]:
        """Load built-in benchmark datasets"""
        return {
            "math": [
                EvaluationExample(
                    input="What is 15 + 27?",
                    expected_output="42",
                    category="arithmetic"
                ),
                EvaluationExample(
                    input="If a train travels 120 km in 2 hours, what is its speed in km/h?",
                    expected_output="60",
                    category="word_problem"
                ),
            ],
            "reasoning": [
                EvaluationExample(
                    input="If all roses are flowers and some flowers fade quickly, can we conclude that some roses fade quickly?",
                    expected_output="no",
                    category="logic"
                ),
            ],
            "code": [
                EvaluationExample(
                    input="Write a Python function to check if a number is even",
                    expected_output="def is_even(n): return n % 2 == 0",
                    category="code_generation"
                ),
            ]
        }

    async def evaluate(
        self,
        generate_func: Callable,
        benchmark_name: str = "math",
        metrics: Optional[List[EvaluationMetric]] = None,
        **kwargs
    ) -> EvaluationResult:
        """
        Evaluate model on benchmark

        Args:
            generate_func: Async function to generate responses
            benchmark_name: Name of benchmark dataset
            metrics: Metrics to compute
            **kwargs: Additional arguments for generate_func

        Returns:
            Evaluation results
        """
        if benchmark_name not in self.benchmarks:
            raise ValueError(f"Unknown benchmark: {benchmark_name}")

        examples = self.benchmarks[benchmark_name]
        metrics = metrics or [EvaluationMetric.EXACT_MATCH, EvaluationMetric.LATENCY]

        logger.info(f"Evaluating on {benchmark_name} ({len(examples)} examples)")

        start_time = time.time()
        results = []
        passed = 0
        failed = 0

        for example in examples:
            # Generate response
            gen_start = time.time()
            try:
                response = await generate_func(example.input, **kwargs)
                latency = (time.time() - gen_start) * 1000  # ms

                # Evaluate
                is_correct = self._check_correctness(
                    response,
                    example.expected_output,
                    example.category
                )

                if is_correct:
                    passed += 1
                else:
                    failed += 1

                results.append({
                    "input": example.input,
                    "expected": example.expected_output,
                    "generated": response,
                    "correct": is_correct,
                    "latency_ms": latency,
                    "category": example.category
                })

            except Exception as e:
                logger.error(f"Evaluation error: {e}")
                failed += 1
                results.append({
                    "input": example.input,
                    "error": str(e),
                    "correct": False
                })

        total_time = (time.time() - start_time) * 1000

        # Calculate metrics
        metric_scores = {}

        if EvaluationMetric.ACCURACY in metrics:
            metric_scores["accuracy"] = passed / len(examples) if examples else 0.0

        if EvaluationMetric.EXACT_MATCH in metrics:
            metric_scores["exact_match"] = passed / len(examples) if examples else 0.0

        if EvaluationMetric.LATENCY in metrics:
            latencies = [r.get("latency_ms", 0) for r in results if "latency_ms" in r]
            metric_scores["avg_latency_ms"] = sum(latencies) / len(latencies) if latencies else 0

        logger.info(
            f"Evaluation complete: {passed}/{len(examples)} passed "
            f"({metric_scores.get('accuracy', 0):.1%})"
        )

        return EvaluationResult(
            metric_scores=metric_scores,
            latency_ms=total_time,
            examples_tested=len(examples),
            passed=passed,
            failed=failed,
            details=results
        )

    def _check_correctness(
        self,
        generated: str,
        expected: str,
        category: Optional[str]
    ) -> bool:
        """
        Check if generated output is correct

        Args:
            generated: Generated output
            expected: Expected output
            category: Category of example

        Returns:
            True if correct
        """
        # Normalize strings
        gen_norm = generated.lower().strip()
        exp_norm = expected.lower().strip()

        # Exact match
        if gen_norm == exp_norm:
            return True

        # For numeric answers, extract number
        if category in ["arithmetic", "word_problem"]:
            gen_num = self._extract_number(generated)
            exp_num = self._extract_number(expected)
            if gen_num is not None and exp_num is not None:
                return abs(gen_num - exp_num) < 0.01

        # For code, check if expected is substring
        if category == "code_generation":
            # Simple check: does generated contain expected logic
            if exp_norm in gen_norm:
                return True

        # For yes/no questions
        if exp_norm in ["yes", "no", "true", "false"]:
            return exp_norm in gen_norm

        # Partial match (contains expected)
        return exp_norm in gen_norm

    def _extract_number(self, text: str) -> Optional[float]:
        """Extract first number from text"""
        import re
        match = re.search(r'-?\d+\.?\d*', text)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None

    async def compare_models(
        self,
        generate_funcs: Dict[str, Callable],
        benchmark_name: str = "math",
        **kwargs
    ) -> Dict[str, EvaluationResult]:
        """
        Compare multiple models on same benchmark

        Args:
            generate_funcs: Dict mapping model names to generate functions
            benchmark_name: Benchmark to use
            **kwargs: Generation parameters

        Returns:
            Results for each model
        """
        logger.info(f"Comparing {len(generate_funcs)} models on {benchmark_name}")

        results = {}
        for model_name, generate_func in generate_funcs.items():
            logger.info(f"Evaluating {model_name}...")
            result = await self.evaluate(generate_func, benchmark_name, **kwargs)
            results[model_name] = result

        # Print comparison
        logger.info("\n=== Model Comparison ===")
        for model_name, result in results.items():
            accuracy = result.metric_scores.get("accuracy", 0)
            latency = result.metric_scores.get("avg_latency_ms", 0)
            logger.info(
                f"{model_name}: {accuracy:.1%} accuracy, {latency:.0f}ms avg latency"
            )

        return results

    def add_benchmark(
        self,
        name: str,
        examples: List[EvaluationExample]
    ):
        """
        Add custom benchmark

        Args:
            name: Benchmark name
            examples: Evaluation examples
        """
        self.benchmarks[name] = examples
        logger.info(f"Added benchmark '{name}' with {len(examples)} examples")

    def get_benchmark_names(self) -> List[str]:
        """Get list of available benchmarks"""
        return list(self.benchmarks.keys())


# Global evaluator
_evaluator: Optional[AutoEvaluator] = None


def get_evaluator() -> AutoEvaluator:
    """Get global evaluator instance"""
    global _evaluator
    if _evaluator is None:
        _evaluator = AutoEvaluator()
    return _evaluator
