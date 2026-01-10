"""
Metrics collection for Ollama Automation Harness.

Provides lightweight metrics collection for monitoring application performance,
usage patterns, and operational health.

Features:
- Counter, Gauge, Histogram, and Timer metrics
- In-memory storage with optional file persistence
- Prometheus-compatible export format
- Privacy-respecting (no PII collection)
"""

from __future__ import annotations

import json
import os
import statistics
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


# =============================================================================
# Configuration
# =============================================================================

# Default metrics storage path
METRICS_DIR = Path(os.environ.get("METRICS_DIR", "./logs/metrics"))

# Whether metrics collection is enabled
METRICS_ENABLED = os.environ.get("METRICS_ENABLED", "true").lower() in (
    "true", "1", "yes"
)


class MetricType(Enum):
    """Types of metrics."""

    COUNTER = "counter"      # Monotonically increasing value
    GAUGE = "gauge"          # Value that can go up or down
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"          # Duration measurements


# =============================================================================
# Metric Classes
# =============================================================================

@dataclass
class MetricValue:
    """A single metric value with metadata."""

    name: str
    type: MetricType
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    description: str = ""


@dataclass
class Counter:
    """
    A counter metric that only increases.

    Use for: request counts, error counts, task completions.
    """

    name: str
    description: str = ""
    _value: float = 0.0
    _labels: dict[str, str] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def inc(self, amount: float = 1.0) -> None:
        """Increment the counter."""
        with self._lock:
            self._value += amount

    def get(self) -> float:
        """Get current value."""
        return self._value

    def reset(self) -> None:
        """Reset counter to zero."""
        with self._lock:
            self._value = 0.0


@dataclass
class Gauge:
    """
    A gauge metric that can increase or decrease.

    Use for: current connections, memory usage, queue size.
    """

    name: str
    description: str = ""
    _value: float = 0.0
    _labels: dict[str, str] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def set(self, value: float) -> None:
        """Set gauge to specific value."""
        with self._lock:
            self._value = value

    def inc(self, amount: float = 1.0) -> None:
        """Increment the gauge."""
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        """Decrement the gauge."""
        with self._lock:
            self._value -= amount

    def get(self) -> float:
        """Get current value."""
        return self._value


@dataclass
class Histogram:
    """
    A histogram metric for value distributions.

    Use for: request sizes, response times, batch sizes.
    """

    name: str
    description: str = ""
    buckets: tuple = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    _values: list = field(default_factory=list)
    _labels: dict[str, str] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def observe(self, value: float) -> None:
        """Record an observation."""
        with self._lock:
            self._values.append(value)

    def get_count(self) -> int:
        """Get number of observations."""
        return len(self._values)

    def get_sum(self) -> float:
        """Get sum of all observations."""
        return sum(self._values) if self._values else 0.0

    def get_mean(self) -> float:
        """Get mean of observations."""
        return statistics.mean(self._values) if self._values else 0.0

    def get_percentile(self, p: float) -> float:
        """Get percentile value (0-100)."""
        if not self._values:
            return 0.0
        sorted_values = sorted(self._values)
        idx = int(len(sorted_values) * p / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]

    def get_bucket_counts(self) -> dict[float, int]:
        """Get counts per bucket."""
        counts = {b: 0 for b in self.buckets}
        counts[float("inf")] = 0
        for value in self._values:
            for bucket in self.buckets:
                if value <= bucket:
                    counts[bucket] += 1
                    break
            else:
                counts[float("inf")] += 1
        return counts

    def reset(self) -> None:
        """Clear all observations."""
        with self._lock:
            self._values.clear()


class Timer:
    """
    A timer metric for measuring durations.

    Use as context manager or decorator.
    """

    def __init__(self, histogram: Histogram):
        self.histogram = histogram
        self._start_time: Optional[float] = None

    def __enter__(self) -> "Timer":
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, *args) -> None:
        if self._start_time is not None:
            duration = time.perf_counter() - self._start_time
            self.histogram.observe(duration)

    def __call__(self, func: Callable) -> Callable:
        """Use as decorator."""
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper


# =============================================================================
# Metrics Registry
# =============================================================================

class MetricsRegistry:
    """
    Central registry for all application metrics.

    Thread-safe singleton that manages metric creation and collection.
    """

    _instance: Optional["MetricsRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "MetricsRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._metrics: dict[str, Any] = {}
        self._metric_lock = threading.Lock()
        self._start_time = time.time()
        self._initialized = True

        # Register default metrics
        self._register_default_metrics()

    def _register_default_metrics(self) -> None:
        """Register default application metrics."""
        # Application info
        self.counter(
            "app_info",
            "Application information",
        ).inc()

        # Requests
        self.counter("requests_total", "Total number of requests")
        self.counter("requests_errors_total", "Total number of request errors")

        # Operations
        self.counter("operations_total", "Total operations executed")
        self.histogram("operation_duration_seconds", "Operation duration in seconds")

        # LLM interactions
        self.counter("llm_requests_total", "Total LLM API requests")
        self.counter("llm_tokens_total", "Total tokens processed")
        self.histogram("llm_response_time_seconds", "LLM response time")

        # Commands
        self.counter("commands_executed_total", "Total commands executed")
        self.counter("commands_failed_total", "Total commands failed")

        # System
        self.gauge("uptime_seconds", "Application uptime in seconds")

    def counter(self, name: str, description: str = "") -> Counter:
        """Get or create a counter metric."""
        with self._metric_lock:
            if name not in self._metrics:
                self._metrics[name] = Counter(name=name, description=description)
            return self._metrics[name]

    def gauge(self, name: str, description: str = "") -> Gauge:
        """Get or create a gauge metric."""
        with self._metric_lock:
            if name not in self._metrics:
                self._metrics[name] = Gauge(name=name, description=description)
            return self._metrics[name]

    def histogram(
        self,
        name: str,
        description: str = "",
        buckets: Optional[tuple] = None,
    ) -> Histogram:
        """Get or create a histogram metric."""
        with self._metric_lock:
            if name not in self._metrics:
                kwargs = {"name": name, "description": description}
                if buckets:
                    kwargs["buckets"] = buckets
                self._metrics[name] = Histogram(**kwargs)
            return self._metrics[name]

    def timer(self, name: str, description: str = "") -> Timer:
        """Get a timer for the named histogram."""
        histogram = self.histogram(name, description)
        return Timer(histogram)

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all registered metrics."""
        return dict(self._metrics)

    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self._start_time

    def collect(self) -> list[MetricValue]:
        """Collect all metric values."""
        values = []

        # Update uptime
        self.gauge("uptime_seconds").set(self.get_uptime())

        for name, metric in self._metrics.items():
            if isinstance(metric, Counter):
                values.append(MetricValue(
                    name=name,
                    type=MetricType.COUNTER,
                    value=metric.get(),
                    description=metric.description,
                ))
            elif isinstance(metric, Gauge):
                values.append(MetricValue(
                    name=name,
                    type=MetricType.GAUGE,
                    value=metric.get(),
                    description=metric.description,
                ))
            elif isinstance(metric, Histogram):
                values.append(MetricValue(
                    name=f"{name}_count",
                    type=MetricType.COUNTER,
                    value=metric.get_count(),
                    description=f"{metric.description} (count)",
                ))
                values.append(MetricValue(
                    name=f"{name}_sum",
                    type=MetricType.COUNTER,
                    value=metric.get_sum(),
                    description=f"{metric.description} (sum)",
                ))

        return values

    def to_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        for metric_value in self.collect():
            # Add help and type comments
            if metric_value.description:
                lines.append(f"# HELP {metric_value.name} {metric_value.description}")
            lines.append(f"# TYPE {metric_value.name} {metric_value.type.value}")
            lines.append(f"{metric_value.name} {metric_value.value}")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Export metrics as JSON."""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": self.get_uptime(),
            "metrics": {},
        }

        for metric_value in self.collect():
            data["metrics"][metric_value.name] = {
                "type": metric_value.type.value,
                "value": metric_value.value,
                "description": metric_value.description,
            }

        return json.dumps(data, indent=2)

    def save_to_file(self, path: Optional[Path] = None) -> Path:
        """Save metrics to file."""
        METRICS_DIR.mkdir(parents=True, exist_ok=True)

        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = METRICS_DIR / f"metrics_{timestamp}.json"

        with open(path, "w") as f:
            f.write(self.to_json())

        return path

    def reset_all(self) -> None:
        """Reset all metrics."""
        for metric in self._metrics.values():
            if hasattr(metric, "reset"):
                metric.reset()


# =============================================================================
# Global Functions
# =============================================================================

# Global registry instance
_registry: Optional[MetricsRegistry] = None


def get_registry() -> MetricsRegistry:
    """Get the global metrics registry."""
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry


def counter(name: str, description: str = "") -> Counter:
    """Get or create a counter metric."""
    return get_registry().counter(name, description)


def gauge(name: str, description: str = "") -> Gauge:
    """Get or create a gauge metric."""
    return get_registry().gauge(name, description)


def histogram(name: str, description: str = "", buckets: Optional[tuple] = None) -> Histogram:
    """Get or create a histogram metric."""
    return get_registry().histogram(name, description, buckets)


def timer(name: str, description: str = "") -> Timer:
    """Get a timer for the named histogram."""
    return get_registry().timer(name, description)


@contextmanager
def timed(name: str):
    """Context manager for timing operations."""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        histogram(name).observe(duration)


def increment(name: str, amount: float = 1.0) -> None:
    """Increment a counter."""
    counter(name).inc(amount)


def record(name: str, value: float) -> None:
    """Record a value to a histogram."""
    histogram(name).observe(value)


def set_gauge(name: str, value: float) -> None:
    """Set a gauge value."""
    gauge(name).set(value)


def get_metrics_summary() -> dict[str, Any]:
    """Get a summary of all metrics."""
    registry = get_registry()
    return {
        "uptime_seconds": registry.get_uptime(),
        "total_metrics": len(registry.get_all_metrics()),
        "metrics": {
            name: {
                "type": type(metric).__name__,
                "value": metric.get() if hasattr(metric, "get") else None,
            }
            for name, metric in registry.get_all_metrics().items()
        },
    }
