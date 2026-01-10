"""
Monitoring utilities for Ollama Automation Harness.

Provides comprehensive monitoring for:
- Application uptime and availability
- Error tracking and alerting
- Performance metrics and thresholds
- Health checks and status reporting

Features:
- Real-time health status
- Configurable alert thresholds
- Historical error tracking
- Performance degradation detection
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from utils.metrics import counter, gauge, histogram, get_registry


# =============================================================================
# Configuration
# =============================================================================

# Health check configuration
HEALTH_CHECK_INTERVAL = int(os.environ.get("HEALTH_CHECK_INTERVAL", "30"))
ERROR_THRESHOLD = int(os.environ.get("ERROR_THRESHOLD", "10"))
ERROR_WINDOW_SECONDS = int(os.environ.get("ERROR_WINDOW_SECONDS", "300"))

# Performance thresholds
RESPONSE_TIME_WARNING_MS = float(os.environ.get("RESPONSE_TIME_WARNING_MS", "1000"))
RESPONSE_TIME_CRITICAL_MS = float(os.environ.get("RESPONSE_TIME_CRITICAL_MS", "5000"))


class HealthStatus(Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class HealthCheckResult:
    """Result of a health check."""

    name: str
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""

    error_type: str
    message: str
    timestamp: float = field(default_factory=time.time)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics."""

    timestamp: str
    uptime_seconds: float
    request_count: int
    error_count: int
    error_rate: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    status: HealthStatus


@dataclass
class Alert:
    """An alert notification."""

    severity: AlertSeverity
    title: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = ""
    resolved: bool = False


# =============================================================================
# Health Checks
# =============================================================================

class HealthChecker:
    """
    Manages health checks for application components.

    Supports registering custom health checks and aggregating results.
    """

    def __init__(self):
        self._checks: dict[str, Callable[[], HealthCheckResult]] = {}
        self._last_results: dict[str, HealthCheckResult] = {}
        self._lock = threading.Lock()

        # Register default checks
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """Register default health checks."""
        self.register("system", self._check_system)
        self.register("dependencies", self._check_dependencies)
        self.register("configuration", self._check_configuration)

    def register(self, name: str, check_func: Callable[[], HealthCheckResult]) -> None:
        """Register a health check."""
        with self._lock:
            self._checks[name] = check_func

    def unregister(self, name: str) -> None:
        """Unregister a health check."""
        with self._lock:
            self._checks.pop(name, None)

    def _check_system(self) -> HealthCheckResult:
        """Check system resources."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)

            status = HealthStatus.HEALTHY
            message = "System resources OK"

            if memory.percent > 90 or cpu_percent > 90:
                status = HealthStatus.DEGRADED
                message = f"High resource usage: Memory {memory.percent}%, CPU {cpu_percent}%"

            return HealthCheckResult(
                name="system",
                status=status,
                message=message,
                details={
                    "memory_percent": memory.percent,
                    "cpu_percent": cpu_percent,
                },
            )
        except ImportError:
            # psutil not available
            return HealthCheckResult(
                name="system",
                status=HealthStatus.HEALTHY,
                message="System check (basic)",
            )

    def _check_dependencies(self) -> HealthCheckResult:
        """Check required dependencies."""
        missing = []
        available = []

        deps = [
            ("anthropic", "Anthropic SDK"),
            ("yaml", "PyYAML"),
            ("dotenv", "python-dotenv"),
        ]

        import importlib

        for module, name in deps:
            try:
                importlib.import_module(module)
                available.append(name)
            except ImportError:
                missing.append(name)

        if missing:
            return HealthCheckResult(
                name="dependencies",
                status=HealthStatus.DEGRADED,
                message=f"Missing: {', '.join(missing)}",
                details={"missing": missing, "available": available},
            )

        return HealthCheckResult(
            name="dependencies",
            status=HealthStatus.HEALTHY,
            message="All dependencies available",
            details={"available": available},
        )

    def _check_configuration(self) -> HealthCheckResult:
        """Check application configuration."""
        issues = []

        # Check for API key
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            issues.append("ANTHROPIC_API_KEY not set")

        # Check environment
        env = os.environ.get("ENVIRONMENT", "")
        if not env:
            issues.append("ENVIRONMENT not set")

        if issues:
            return HealthCheckResult(
                name="configuration",
                status=HealthStatus.DEGRADED,
                message=f"Config issues: {'; '.join(issues)}",
                details={"issues": issues},
            )

        return HealthCheckResult(
            name="configuration",
            status=HealthStatus.HEALTHY,
            message="Configuration OK",
        )

    def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        check_func = self._checks.get(name)
        if not check_func:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Unknown check: {name}",
            )

        start = time.perf_counter()
        try:
            result = check_func()
            result.duration_ms = (time.perf_counter() - start) * 1000
            with self._lock:
                self._last_results[name] = result
            return result
        except Exception as e:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

    def run_all_checks(self) -> list[HealthCheckResult]:
        """Run all registered health checks."""
        results = []
        for name in self._checks:
            results.append(self.run_check(name))
        return results

    def get_overall_status(self) -> HealthStatus:
        """Get overall health status from all checks."""
        results = self.run_all_checks()

        if any(r.status == HealthStatus.UNHEALTHY for r in results):
            return HealthStatus.UNHEALTHY
        if any(r.status == HealthStatus.DEGRADED for r in results):
            return HealthStatus.DEGRADED
        if all(r.status == HealthStatus.HEALTHY for r in results):
            return HealthStatus.HEALTHY
        return HealthStatus.UNKNOWN

    def get_health_report(self) -> dict[str, Any]:
        """Get comprehensive health report."""
        results = self.run_all_checks()
        overall = self.get_overall_status()

        return {
            "status": overall.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {r.name: {
                "status": r.status.value,
                "message": r.message,
                "duration_ms": r.duration_ms,
                "details": r.details,
            } for r in results},
        }


# =============================================================================
# Error Tracker
# =============================================================================

class ErrorTracker:
    """
    Tracks errors and provides alerting based on thresholds.

    Maintains a sliding window of errors for rate calculation.
    """

    def __init__(
        self,
        threshold: int = ERROR_THRESHOLD,
        window_seconds: int = ERROR_WINDOW_SECONDS,
    ):
        self._errors: deque[ErrorRecord] = deque()
        self._threshold = threshold
        self._window_seconds = window_seconds
        self._lock = threading.Lock()
        self._alerts: list[Alert] = []
        self._alert_callbacks: list[Callable[[Alert], None]] = []

    def record_error(
        self,
        error_type: str,
        message: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record an error occurrence."""
        error = ErrorRecord(
            error_type=error_type,
            message=message[:500],  # Limit message length
            context=context or {},
        )

        with self._lock:
            self._errors.append(error)
            self._cleanup_old_errors()

            # Update metrics
            counter("requests_errors_total").inc()

            # Check threshold
            if self.get_error_count() >= self._threshold:
                self._trigger_alert(
                    AlertSeverity.ERROR,
                    "Error threshold exceeded",
                    f"{self.get_error_count()} errors in last {self._window_seconds}s",
                )

    def _cleanup_old_errors(self) -> None:
        """Remove errors outside the sliding window."""
        cutoff = time.time() - self._window_seconds
        while self._errors and self._errors[0].timestamp < cutoff:
            self._errors.popleft()

    def get_error_count(self) -> int:
        """Get number of errors in the window."""
        with self._lock:
            self._cleanup_old_errors()
            return len(self._errors)

    def get_error_rate(self) -> float:
        """Get errors per second in the window."""
        count = self.get_error_count()
        return count / self._window_seconds if self._window_seconds > 0 else 0

    def get_recent_errors(self, limit: int = 10) -> list[ErrorRecord]:
        """Get most recent errors."""
        with self._lock:
            self._cleanup_old_errors()
            return list(self._errors)[-limit:]

    def get_error_summary(self) -> dict[str, Any]:
        """Get summary of error statistics."""
        with self._lock:
            self._cleanup_old_errors()
            by_type: dict[str, int] = {}
            for error in self._errors:
                by_type[error.error_type] = by_type.get(error.error_type, 0) + 1

        return {
            "total_errors": self.get_error_count(),
            "error_rate": self.get_error_rate(),
            "window_seconds": self._window_seconds,
            "threshold": self._threshold,
            "by_type": by_type,
        }

    def _trigger_alert(self, severity: AlertSeverity, title: str, message: str) -> None:
        """Trigger an alert."""
        alert = Alert(
            severity=severity,
            title=title,
            message=message,
            source="error_tracker",
        )
        self._alerts.append(alert)

        # Notify callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception:
                pass  # Don't let callback errors affect tracking

    def register_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register a callback for alerts."""
        self._alert_callbacks.append(callback)

    def get_alerts(self, include_resolved: bool = False) -> list[Alert]:
        """Get active alerts."""
        if include_resolved:
            return list(self._alerts)
        return [a for a in self._alerts if not a.resolved]


# =============================================================================
# Performance Monitor
# =============================================================================

class PerformanceMonitor:
    """
    Monitors application performance and detects degradation.

    Tracks response times, throughput, and resource usage.
    """

    def __init__(self):
        self._start_time = time.time()
        self._request_count = 0
        self._response_times: deque[float] = deque(maxlen=1000)
        self._lock = threading.Lock()

    def record_request(self, duration_ms: float) -> None:
        """Record a request with its duration."""
        with self._lock:
            self._request_count += 1
            self._response_times.append(duration_ms)

            # Update metrics
            counter("requests_total").inc()
            histogram("operation_duration_seconds").observe(duration_ms / 1000)

            # Check for slow requests
            if duration_ms > RESPONSE_TIME_CRITICAL_MS:
                counter("slow_requests_critical_total").inc()
            elif duration_ms > RESPONSE_TIME_WARNING_MS:
                counter("slow_requests_warning_total").inc()

    def get_uptime_seconds(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self._start_time

    def get_uptime_formatted(self) -> str:
        """Get formatted uptime string."""
        seconds = self.get_uptime_seconds()
        delta = timedelta(seconds=int(seconds))
        return str(delta)

    def get_request_count(self) -> int:
        """Get total request count."""
        return self._request_count

    def get_avg_response_time(self) -> float:
        """Get average response time in ms."""
        with self._lock:
            if not self._response_times:
                return 0.0
            return sum(self._response_times) / len(self._response_times)

    def get_percentile_response_time(self, percentile: float) -> float:
        """Get response time at given percentile."""
        with self._lock:
            if not self._response_times:
                return 0.0
            sorted_times = sorted(self._response_times)
            idx = int(len(sorted_times) * percentile / 100)
            return sorted_times[min(idx, len(sorted_times) - 1)]

    def get_throughput(self) -> float:
        """Get requests per second."""
        uptime = self.get_uptime_seconds()
        return self._request_count / uptime if uptime > 0 else 0

    def get_performance_status(self) -> HealthStatus:
        """Get performance health status."""
        avg_time = self.get_avg_response_time()

        if avg_time > RESPONSE_TIME_CRITICAL_MS:
            return HealthStatus.UNHEALTHY
        if avg_time > RESPONSE_TIME_WARNING_MS:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def get_snapshot(self) -> PerformanceSnapshot:
        """Get current performance snapshot."""
        registry = get_registry()
        error_count = int(counter("requests_errors_total").get())
        request_count = self.get_request_count()

        return PerformanceSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            uptime_seconds=self.get_uptime_seconds(),
            request_count=request_count,
            error_count=error_count,
            error_rate=error_count / request_count if request_count > 0 else 0,
            avg_response_time_ms=self.get_avg_response_time(),
            p95_response_time_ms=self.get_percentile_response_time(95),
            status=self.get_performance_status(),
        )


# =============================================================================
# Monitor Manager
# =============================================================================

class MonitorManager:
    """
    Central manager for all monitoring components.

    Singleton that provides unified access to health, errors, and performance.
    """

    _instance: Optional["MonitorManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "MonitorManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.health = HealthChecker()
        self.errors = ErrorTracker()
        self.performance = PerformanceMonitor()
        self._initialized = True

    def get_status(self) -> dict[str, Any]:
        """Get comprehensive monitoring status."""
        health_status = self.health.get_overall_status()
        perf_status = self.performance.get_performance_status()

        # Determine overall status
        if health_status == HealthStatus.UNHEALTHY or perf_status == HealthStatus.UNHEALTHY:
            overall = HealthStatus.UNHEALTHY
        elif health_status == HealthStatus.DEGRADED or perf_status == HealthStatus.DEGRADED:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return {
            "status": overall.value,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": self.performance.get_uptime_formatted(),
            "uptime_seconds": self.performance.get_uptime_seconds(),
            "health": self.health.get_health_report(),
            "errors": self.errors.get_error_summary(),
            "performance": {
                "status": perf_status.value,
                "requests": self.performance.get_request_count(),
                "throughput_rps": round(self.performance.get_throughput(), 2),
                "avg_response_ms": round(self.performance.get_avg_response_time(), 2),
                "p95_response_ms": round(self.performance.get_percentile_response_time(95), 2),
            },
            "alerts": [
                {
                    "severity": a.severity.value,
                    "title": a.title,
                    "message": a.message,
                    "timestamp": a.timestamp,
                }
                for a in self.errors.get_alerts()
            ],
        }


# =============================================================================
# Global Functions
# =============================================================================

_monitor: Optional[MonitorManager] = None


def get_monitor() -> MonitorManager:
    """Get the global monitor manager."""
    global _monitor
    if _monitor is None:
        _monitor = MonitorManager()
    return _monitor


def check_health() -> dict[str, Any]:
    """Run health checks and return report."""
    return get_monitor().health.get_health_report()


def get_status() -> dict[str, Any]:
    """Get comprehensive monitoring status."""
    return get_monitor().get_status()


def record_error(error_type: str, message: str, context: Optional[dict[str, Any]] = None) -> None:
    """Record an error."""
    get_monitor().errors.record_error(error_type, message, context)


def record_request(duration_ms: float) -> None:
    """Record a request with duration."""
    get_monitor().performance.record_request(duration_ms)


def get_uptime() -> str:
    """Get formatted uptime."""
    return get_monitor().performance.get_uptime_formatted()


def is_healthy() -> bool:
    """Quick check if application is healthy."""
    return get_monitor().health.get_overall_status() == HealthStatus.HEALTHY
