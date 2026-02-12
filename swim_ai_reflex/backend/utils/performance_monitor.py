"""
Performance Monitoring and Metrics Collection

Tracks API performance, optimization times, cache hit rates, and system health.
"""

import inspect
import logging
import statistics
import time
from collections import deque
from collections.abc import Callable
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitors and tracks system performance metrics"""

    def __init__(self, max_samples: int = 1000):
        self.metrics: dict[str, deque] = {}
        self.max_samples = max_samples
        self.start_time = datetime.now()

    def record_metric(self, metric_name: str, value: float):
        """Record a performance metric"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = deque(maxlen=self.max_samples)

        self.metrics[metric_name].append(
            {"value": value, "timestamp": datetime.now().isoformat()}
        )

    def get_stats(self, metric_name: str) -> dict:
        """Get statistics for a metric"""
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return {}

        values = [m["value"] for m in self.metrics[metric_name]]

        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
        }

    def _percentile(self, values: list[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]

    def get_all_stats(self) -> dict:
        """Get all performance stats"""
        return {metric: self.get_stats(metric) for metric in self.metrics.keys()}

    def get_health_status(self) -> dict:
        """Get overall system health"""
        opt_stats = self.get_stats("optimization_time")
        cache_stats = self.get_stats("cache_hit")

        health: dict = {
            "status": "healthy",
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "metrics_tracked": len(self.metrics),
            "total_requests": sum(len(m) for m in self.metrics.values()),
        }

        if opt_stats:
            health["avg_optimization_time"] = opt_stats["mean"]
            health["p95_optimization_time"] = opt_stats["p95"]

            if opt_stats["p95"] > 60:
                health["status"] = "degraded"

        if cache_stats:
            cache_values = [m["value"] for m in self.metrics.get("cache_hit", [])]
            hit_rate = (
                (sum(cache_values) / len(cache_values)) * 100 if cache_values else 0
            )
            health["cache_hit_rate"] = hit_rate

            if hit_rate < 50:
                health["status"] = "degraded"

        return health


# Global monitor instance
monitor = PerformanceMonitor()


def track_performance(metric_name: str):
    """
    Decorator to track function execution time.

    Usage:
        @track_performance('optimization_time')
        async def optimize_lineup():
            # ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                monitor.record_metric(metric_name, duration)
                logger.info(f"{metric_name}: {duration:.2f}s")

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                monitor.record_metric(metric_name, duration)
                logger.info(f"{metric_name}: {duration:.2f}s")

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
