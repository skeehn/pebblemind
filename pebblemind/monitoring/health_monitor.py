"""Comprehensive health monitoring and metrics system"""

import asyncio
import psutil
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """System health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: float
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """Health check definition"""
    name: str
    check_func: Callable
    interval: float = 30.0  # seconds
    timeout: float = 5.0
    critical: bool = False


class MetricsCollector:
    """
    Collect and track system metrics.

    Features:
    - CPU, memory, disk usage
    - Request latency tracking
    - Token generation rate
    - Error rates
    - Custom metrics
    - Time-series data
    """

    def __init__(self, retention_minutes: int = 60):
        """
        Initialize metrics collector

        Args:
            retention_minutes: How long to retain metrics
        """
        self.retention_seconds = retention_minutes * 60
        self._metrics: Dict[str, deque] = {}
        self._counters: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def record_metric(
        self,
        name: str,
        value: float,
        tags: Dict[str, str] = None
    ):
        """
        Record metric value

        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags
        """
        async with self._lock:
            if name not in self._metrics:
                self._metrics[name] = deque()

            point = MetricPoint(
                timestamp=time.time(),
                value=value,
                tags=tags or {}
            )
            self._metrics[name].append(point)

            # Clean old metrics
            await self._clean_old_metrics(name)

    async def increment_counter(self, name: str, amount: int = 1):
        """Increment counter"""
        async with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

    async def get_metric_stats(
        self,
        name: str,
        window_seconds: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Get statistics for metric

        Args:
            name: Metric name
            window_seconds: Time window for stats

        Returns:
            Statistics dictionary
        """
        async with self._lock:
            if name not in self._metrics or not self._metrics[name]:
                return {}

            # Filter by time window
            now = time.time()
            points = self._metrics[name]

            if window_seconds:
                cutoff = now - window_seconds
                points = [p for p in points if p.timestamp >= cutoff]
            else:
                points = list(points)

            if not points:
                return {}

            values = [p.value for p in points]

            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1],
                "total": sum(values)
            }

    async def _clean_old_metrics(self, name: str):
        """Remove metrics older than retention period"""
        if name not in self._metrics:
            return

        cutoff = time.time() - self.retention_seconds
        metrics = self._metrics[name]

        while metrics and metrics[0].timestamp < cutoff:
            metrics.popleft()

    async def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        async with self._lock:
            return {
                "metrics": {
                    name: await self.get_metric_stats(name)
                    for name in self._metrics.keys()
                },
                "counters": dict(self._counters)
            }


class HealthMonitor:
    """
    System health monitoring with alerts.

    Features:
    - System resource monitoring
    - Component health checks
    - Automatic alerting
    - Health history
    - Performance benchmarking
    """

    def __init__(self):
        """Initialize health monitor"""
        self._health_checks: Dict[str, HealthCheck] = {}
        self._health_status: Dict[str, HealthStatus] = {}
        self._metrics = MetricsCollector()
        self._alert_handlers: List[Callable] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False

    def register_health_check(self, check: HealthCheck):
        """
        Register health check

        Args:
            check: Health check to register
        """
        self._health_checks[check.name] = check
        logger.info(f"Registered health check: {check.name}")

    def register_alert_handler(self, handler: Callable):
        """Register alert handler function"""
        self._alert_handlers.append(handler)

    async def start(self):
        """Start monitoring"""
        if self._running:
            return

        self._running = True

        # Register default system checks
        self._register_default_checks()

        # Start monitoring loop
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Health monitoring started")

    async def stop(self):
        """Stop monitoring"""
        self._running = False

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None

        logger.info("Health monitoring stopped")

    def _register_default_checks(self):
        """Register default system health checks"""
        # CPU check
        self.register_health_check(HealthCheck(
            name="cpu_usage",
            check_func=self._check_cpu,
            interval=10.0
        ))

        # Memory check
        self.register_health_check(HealthCheck(
            name="memory_usage",
            check_func=self._check_memory,
            interval=10.0,
            critical=True
        ))

        # Disk check
        self.register_health_check(HealthCheck(
            name="disk_usage",
            check_func=self._check_disk,
            interval=30.0
        ))

    async def _check_cpu(self) -> Dict[str, Any]:
        """Check CPU usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        await self._metrics.record_metric("cpu_percent", cpu_percent)

        if cpu_percent > 90:
            return {"status": HealthStatus.CRITICAL, "cpu_percent": cpu_percent}
        elif cpu_percent > 70:
            return {"status": HealthStatus.DEGRADED, "cpu_percent": cpu_percent}
        else:
            return {"status": HealthStatus.HEALTHY, "cpu_percent": cpu_percent}

    async def _check_memory(self) -> Dict[str, Any]:
        """Check memory usage"""
        memory = psutil.virtual_memory()
        await self._metrics.record_metric("memory_percent", memory.percent)
        await self._metrics.record_metric("memory_available_mb", memory.available / 1024 / 1024)

        if memory.percent > 95:
            return {"status": HealthStatus.CRITICAL, "memory_percent": memory.percent}
        elif memory.percent > 85:
            return {"status": HealthStatus.DEGRADED, "memory_percent": memory.percent}
        else:
            return {"status": HealthStatus.HEALTHY, "memory_percent": memory.percent}

    async def _check_disk(self) -> Dict[str, Any]:
        """Check disk usage"""
        disk = psutil.disk_usage('/')
        await self._metrics.record_metric("disk_percent", disk.percent)

        if disk.percent > 95:
            return {"status": HealthStatus.CRITICAL, "disk_percent": disk.percent}
        elif disk.percent > 85:
            return {"status": HealthStatus.DEGRADED, "disk_percent": disk.percent}
        else:
            return {"status": HealthStatus.HEALTHY, "disk_percent": disk.percent}

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                # Run all health checks
                for name, check in self._health_checks.items():
                    asyncio.create_task(self._run_health_check(name, check))

                # Wait before next iteration
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)

    async def _run_health_check(self, name: str, check: HealthCheck):
        """Run individual health check"""
        try:
            # Run check with timeout
            result = await asyncio.wait_for(
                check.check_func(),
                timeout=check.timeout
            )

            status = result.get("status", HealthStatus.HEALTHY)
            previous_status = self._health_status.get(name)

            # Update status
            self._health_status[name] = status

            # Alert if status changed to degraded/unhealthy
            if previous_status != status and status != HealthStatus.HEALTHY:
                await self._trigger_alert(name, status, result, check.critical)

        except asyncio.TimeoutError:
            logger.warning(f"Health check timed out: {name}")
            self._health_status[name] = HealthStatus.UNHEALTHY
            await self._trigger_alert(name, HealthStatus.UNHEALTHY, {"error": "timeout"}, check.critical)

        except Exception as e:
            logger.error(f"Health check failed: {name}: {e}")
            self._health_status[name] = HealthStatus.UNHEALTHY
            await self._trigger_alert(name, HealthStatus.UNHEALTHY, {"error": str(e)}, check.critical)

    async def _trigger_alert(
        self,
        check_name: str,
        status: HealthStatus,
        details: Dict[str, Any],
        critical: bool
    ):
        """Trigger alert for health check failure"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "check_name": check_name,
            "status": status.value,
            "details": details,
            "critical": critical
        }

        logger.warning(f"Health alert: {alert}")

        # Call alert handlers
        for handler in self._alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")

    async def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        # Determine overall status
        if not self._health_status:
            overall_status = HealthStatus.HEALTHY
        elif any(s == HealthStatus.CRITICAL for s in self._health_status.values()):
            overall_status = HealthStatus.CRITICAL
        elif any(s == HealthStatus.UNHEALTHY for s in self._health_status.values()):
            overall_status = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in self._health_status.values()):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return {
            "overall_status": overall_status.value,
            "checks": {
                name: status.value
                for name, status in self._health_status.items()
            },
            "timestamp": datetime.now().isoformat()
        }

    async def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        return await self._metrics.get_all_metrics()

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for health dashboard"""
        return {
            "health": await self.get_health_status(),
            "metrics": await self.get_metrics(),
            "system": {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
                "disk_total_gb": psutil.disk_usage('/').total / 1024 / 1024 / 1024,
            }
        }


# Global monitor instance
_monitor: Optional[HealthMonitor] = None


def get_monitor() -> HealthMonitor:
    """Get global health monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = HealthMonitor()
    return _monitor
