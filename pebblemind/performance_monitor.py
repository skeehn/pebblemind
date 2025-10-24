"""Performance monitoring and efficiency tracking for PebbleMind"""

import time
from dataclasses import dataclass
from typing import Any, Dict

import psutil


@dataclass
class PerformanceMetrics:
    """Data class to hold performance metrics"""

    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    tokens_per_second: float
    tokens_processed: int
    generation_time: float
    context_switches: int
    model_size: str
    thread_count: int


class PerformanceMonitor:
    """Monitor and track performance metrics for efficiency optimization"""

    def __init__(self):
        self.metrics_history: list[PerformanceMetrics] = []
        self.start_time = time.time()

    async def capture_metrics(
        self,
        tokens_processed: int = 0,
        generation_time: float = 0.0,
        model_size: str = "unknown",
        thread_count: int = 1,
    ) -> PerformanceMetrics:
        """Capture current system and performance metrics"""
        current_time = time.time()

        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        memory_info = psutil.virtual_memory()
        memory_mb = memory_info.used / (1024 * 1024)
        memory_percent = memory_info.percent

        # Calculate tokens per second
        tokens_per_second = (
            tokens_processed / generation_time if generation_time > 0 else 0
        )

        # Create metrics object
        metrics = PerformanceMetrics(
            timestamp=current_time,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_mb=memory_mb,
            tokens_per_second=tokens_per_second,
            tokens_processed=tokens_processed,
            generation_time=generation_time,
            context_switches=len(self.metrics_history) + 1,
            model_size=model_size,
            thread_count=thread_count,
        )

        # Store in history
        self.metrics_history.append(metrics)

        return metrics

    def get_efficiency_report(self) -> Dict[str, Any]:
        """Generate a report on efficiency metrics"""
        if not self.metrics_history:
            return {"message": "No metrics collected yet"}

        # Calculate average metrics
        total_tokens = sum(m.tokens_processed for m in self.metrics_history)
        total_time = sum(m.generation_time for m in self.metrics_history)
        avg_tokens_per_sec = total_tokens / total_time if total_time > 0 else 0

        avg_cpu = sum(m.cpu_percent for m in self.metrics_history) / len(
            self.metrics_history
        )
        avg_memory_mb = sum(m.memory_mb for m in self.metrics_history) / len(
            self.metrics_history
        )
        avg_memory_percent = sum(m.memory_percent for m in self.metrics_history) / len(
            self.metrics_history
        )

        return {
            "total_sessions": len(self.metrics_history),
            "total_tokens_processed": total_tokens,
            "total_time_elapsed": time.time() - self.start_time,
            "average_tokens_per_second": round(avg_tokens_per_sec, 2),
            "average_cpu_percent": round(avg_cpu, 2),
            "average_memory_mb": round(avg_memory_mb, 2),
            "average_memory_percent": round(avg_memory_percent, 2),
            "current_model_size": (
                self.metrics_history[-1].model_size
                if self.metrics_history
                else "unknown"
            ),
            "efficiency_score": self._calculate_efficiency_score(
                avg_tokens_per_sec, avg_cpu, avg_memory_percent
            ),
        }

    def _calculate_efficiency_score(
        self, tokens_per_sec: float, cpu_percent: float, memory_percent: float
    ) -> float:
        """Calculate an overall efficiency score (higher is better)"""
        # Normalize the values to a 0-100 scale
        # Higher tokens/sec = higher efficiency
        # Lower CPU/Memory usage = higher efficiency

        # Tokens per second (normalize to 0-100, assuming 50 tokens/sec is excellent)
        tps_score = min(100, (tokens_per_sec / 50) * 100)

        # CPU usage (lower is better, so invert)
        cpu_score = max(0, 100 - cpu_percent)

        # Memory usage (lower is better, so invert)
        memory_score = max(0, 100 - memory_percent)

        # Weighted average (we prioritize performance and efficiency equally)
        efficiency_score = (tps_score * 0.4) + (cpu_score * 0.3) + (memory_score * 0.3)

        return round(efficiency_score, 2)

    def get_optimization_recommendations(self) -> list[str]:
        """Provide optimization recommendations based on metrics"""
        if not self.metrics_history:
            return ["Run a few generation tasks to collect performance metrics."]

        report = self.get_efficiency_report()
        recommendations = []

        # Check if CPU usage is too high
        if report["average_cpu_percent"] > 85:
            recommendations.append(
                "CPU usage is high. Consider reducing thread count for better thermal performance."
            )

        # Check if memory usage is too high
        if report["average_memory_percent"] > 80:
            recommendations.append(
                "Memory usage is high. Consider using smaller models or reducing context length."
            )

        # Check if efficiency score is low
        if report["efficiency_score"] < 60:
            recommendations.append(
                "Overall efficiency could be improved. "
                "Consider using the 1.5B model for better performance on lightweight devices."
            )

        # Check if tokens per second is low
        if report["average_tokens_per_second"] < 5:
            recommendations.append(
                "Generation speed is slow. Ensure BLAS acceleration is enabled and appropriate thread count is set."
            )

        if not recommendations:
            recommendations.append(
                "Performance looks good! System is running efficiently on lightweight hardware."
            )

        return recommendations
