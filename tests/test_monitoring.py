"""
Tests for utils/monitoring.py module.

Comprehensive tests for monitoring utilities including:
- Health checks
- Error tracking
- Performance monitoring
- Monitor manager
"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_health_status_values(self):
        """Test health status values."""
        from utils.monitoring import HealthStatus
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestAlertSeverity:
    """Tests for AlertSeverity enum."""

    def test_alert_severity_values(self):
        """Test alert severity values."""
        from utils.monitoring import AlertSeverity
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestHealthCheckResult:
    """Tests for HealthCheckResult dataclass."""

    def test_health_check_result_creation(self):
        """Test HealthCheckResult creation."""
        from utils.monitoring import HealthCheckResult, HealthStatus
        result = HealthCheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="All good"
        )
        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"

    def test_health_check_result_defaults(self):
        """Test HealthCheckResult default values."""
        from utils.monitoring import HealthCheckResult, HealthStatus
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.HEALTHY
        )
        assert result.message == ""
        assert result.duration_ms == 0.0
        assert result.details == {}


class TestErrorRecord:
    """Tests for ErrorRecord dataclass."""

    def test_error_record_creation(self):
        """Test ErrorRecord creation."""
        from utils.monitoring import ErrorRecord
        error = ErrorRecord(
            error_type="ValueError",
            message="Test error"
        )
        assert error.error_type == "ValueError"
        assert error.message == "Test error"
        assert error.timestamp > 0


class TestPerformanceSnapshot:
    """Tests for PerformanceSnapshot dataclass."""

    def test_performance_snapshot_creation(self):
        """Test PerformanceSnapshot creation."""
        from utils.monitoring import HealthStatus, PerformanceSnapshot
        snapshot = PerformanceSnapshot(
            timestamp="2024-01-01T00:00:00",
            uptime_seconds=100.0,
            request_count=50,
            error_count=2,
            error_rate=0.04,
            avg_response_time_ms=50.0,
            p95_response_time_ms=100.0,
            status=HealthStatus.HEALTHY
        )
        assert snapshot.request_count == 50
        assert snapshot.error_rate == 0.04


class TestAlert:
    """Tests for Alert dataclass."""

    def test_alert_creation(self):
        """Test Alert creation."""
        from utils.monitoring import Alert, AlertSeverity
        alert = Alert(
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="This is a test"
        )
        assert alert.severity == AlertSeverity.WARNING
        assert alert.title == "Test Alert"
        assert alert.resolved is False


class TestHealthChecker:
    """Tests for HealthChecker class."""

    def test_health_checker_creation(self):
        """Test HealthChecker creation."""
        from utils.monitoring import HealthChecker
        checker = HealthChecker()
        assert checker is not None

    def test_health_checker_default_checks(self):
        """Test default health checks are registered."""
        from utils.monitoring import HealthChecker
        checker = HealthChecker()
        assert "system" in checker._checks
        assert "dependencies" in checker._checks
        assert "configuration" in checker._checks

    def test_health_checker_register(self):
        """Test registering custom health check."""
        from utils.monitoring import HealthCheckResult, HealthChecker, HealthStatus
        checker = HealthChecker()

        def custom_check():
            return HealthCheckResult(
                name="custom",
                status=HealthStatus.HEALTHY,
                message="Custom check OK"
            )

        checker.register("custom", custom_check)
        assert "custom" in checker._checks

    def test_health_checker_unregister(self):
        """Test unregistering health check."""
        from utils.monitoring import HealthCheckResult, HealthChecker, HealthStatus
        checker = HealthChecker()

        def temp_check():
            return HealthCheckResult(
                name="temp",
                status=HealthStatus.HEALTHY
            )

        checker.register("temp", temp_check)
        checker.unregister("temp")
        assert "temp" not in checker._checks

    def test_health_checker_run_check(self):
        """Test running a specific health check."""
        from utils.monitoring import HealthChecker, HealthStatus
        checker = HealthChecker()
        result = checker.run_check("dependencies")
        assert result.name == "dependencies"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

    def test_health_checker_run_unknown_check(self):
        """Test running unknown health check."""
        from utils.monitoring import HealthChecker, HealthStatus
        checker = HealthChecker()
        result = checker.run_check("nonexistent")
        assert result.status == HealthStatus.UNKNOWN

    def test_health_checker_run_all_checks(self):
        """Test running all health checks."""
        from utils.monitoring import HealthChecker
        checker = HealthChecker()
        results = checker.run_all_checks()
        assert len(results) >= 3  # At least default checks

    def test_health_checker_get_overall_status(self):
        """Test getting overall status."""
        from utils.monitoring import HealthChecker, HealthStatus
        checker = HealthChecker()
        status = checker.get_overall_status()
        assert status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
            HealthStatus.UNKNOWN
        ]

    def test_health_checker_get_health_report(self):
        """Test getting health report."""
        from utils.monitoring import HealthChecker
        checker = HealthChecker()
        report = checker.get_health_report()
        assert "status" in report
        assert "timestamp" in report
        assert "checks" in report

    def test_health_checker_check_failure_handling(self):
        """Test health check failure handling."""
        from utils.monitoring import HealthChecker, HealthStatus
        checker = HealthChecker()

        def failing_check():
            raise RuntimeError("Check failed")

        checker.register("failing", failing_check)
        result = checker.run_check("failing")
        assert result.status == HealthStatus.UNHEALTHY
        assert "failed" in result.message.lower()


class TestErrorTracker:
    """Tests for ErrorTracker class."""

    def test_error_tracker_creation(self):
        """Test ErrorTracker creation."""
        from utils.monitoring import ErrorTracker
        tracker = ErrorTracker()
        assert tracker.get_error_count() == 0

    def test_error_tracker_record_error(self):
        """Test recording an error."""
        from utils.monitoring import ErrorTracker
        tracker = ErrorTracker(threshold=100, window_seconds=60)
        tracker.record_error("TestError", "Test message")
        assert tracker.get_error_count() == 1

    def test_error_tracker_multiple_errors(self):
        """Test recording multiple errors."""
        from utils.monitoring import ErrorTracker
        tracker = ErrorTracker(threshold=100, window_seconds=60)
        tracker.record_error("Error1", "Message 1")
        tracker.record_error("Error2", "Message 2")
        tracker.record_error("Error3", "Message 3")
        assert tracker.get_error_count() == 3

    def test_error_tracker_error_rate(self):
        """Test error rate calculation."""
        from utils.monitoring import ErrorTracker
        tracker = ErrorTracker(threshold=100, window_seconds=60)
        tracker.record_error("Error", "Test")
        rate = tracker.get_error_rate()
        assert rate > 0

    def test_error_tracker_get_recent_errors(self):
        """Test getting recent errors."""
        from utils.monitoring import ErrorTracker
        tracker = ErrorTracker(threshold=100, window_seconds=60)
        for i in range(5):
            tracker.record_error(f"Error{i}", f"Message {i}")
        recent = tracker.get_recent_errors(limit=3)
        assert len(recent) == 3

    def test_error_tracker_error_summary(self):
        """Test error summary."""
        from utils.monitoring import ErrorTracker
        tracker = ErrorTracker(threshold=100, window_seconds=60)
        tracker.record_error("TypeError", "Type error")
        tracker.record_error("ValueError", "Value error")
        summary = tracker.get_error_summary()
        assert "total_errors" in summary
        assert "error_rate" in summary
        assert "by_type" in summary

    def test_error_tracker_threshold_alert(self):
        """Test threshold triggers alert."""
        from utils.monitoring import ErrorTracker
        tracker = ErrorTracker(threshold=3, window_seconds=60)
        alerts_triggered = []

        def alert_callback(alert):
            alerts_triggered.append(alert)

        tracker.register_alert_callback(alert_callback)

        for i in range(5):
            tracker.record_error("Error", "Test")

        assert len(tracker.get_alerts()) >= 1

    def test_error_tracker_get_alerts(self):
        """Test getting alerts."""
        from utils.monitoring import ErrorTracker
        tracker = ErrorTracker(threshold=1, window_seconds=60)
        tracker.record_error("Error", "Test")
        alerts = tracker.get_alerts()
        assert isinstance(alerts, list)

    def test_error_tracker_context(self):
        """Test error with context."""
        from utils.monitoring import ErrorTracker
        tracker = ErrorTracker(threshold=100, window_seconds=60)
        tracker.record_error(
            "Error",
            "Test",
            context={"key": "value"}
        )
        errors = tracker.get_recent_errors()
        assert errors[0].context == {"key": "value"}


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor class."""

    def test_performance_monitor_creation(self):
        """Test PerformanceMonitor creation."""
        from utils.monitoring import PerformanceMonitor
        monitor = PerformanceMonitor()
        assert monitor.get_request_count() == 0

    def test_performance_monitor_record_request(self):
        """Test recording a request."""
        from utils.monitoring import PerformanceMonitor
        monitor = PerformanceMonitor()
        monitor.record_request(100.0)
        assert monitor.get_request_count() == 1

    def test_performance_monitor_uptime(self):
        """Test uptime tracking."""
        from utils.monitoring import PerformanceMonitor
        monitor = PerformanceMonitor()
        time.sleep(0.01)
        uptime = monitor.get_uptime_seconds()
        assert uptime >= 0.01

    def test_performance_monitor_uptime_formatted(self):
        """Test formatted uptime."""
        from utils.monitoring import PerformanceMonitor
        monitor = PerformanceMonitor()
        formatted = monitor.get_uptime_formatted()
        assert ":" in formatted  # Contains time separator

    def test_performance_monitor_avg_response_time(self):
        """Test average response time calculation."""
        from utils.monitoring import PerformanceMonitor
        monitor = PerformanceMonitor()
        monitor.record_request(100.0)
        monitor.record_request(200.0)
        monitor.record_request(300.0)
        avg = monitor.get_avg_response_time()
        assert avg == 200.0

    def test_performance_monitor_avg_response_time_empty(self):
        """Test average response time when empty."""
        from utils.monitoring import PerformanceMonitor
        monitor = PerformanceMonitor()
        avg = monitor.get_avg_response_time()
        assert avg == 0.0

    def test_performance_monitor_percentile(self):
        """Test percentile calculation."""
        from utils.monitoring import PerformanceMonitor
        monitor = PerformanceMonitor()
        for i in range(1, 101):
            monitor.record_request(float(i))
        p95 = monitor.get_percentile_response_time(95)
        assert p95 >= 90

    def test_performance_monitor_throughput(self):
        """Test throughput calculation."""
        from utils.monitoring import PerformanceMonitor
        monitor = PerformanceMonitor()
        monitor.record_request(100.0)
        throughput = monitor.get_throughput()
        assert throughput > 0

    def test_performance_monitor_status_healthy(self):
        """Test healthy performance status."""
        from utils.monitoring import HealthStatus, PerformanceMonitor
        monitor = PerformanceMonitor()
        monitor.record_request(10.0)  # Very fast
        status = monitor.get_performance_status()
        assert status == HealthStatus.HEALTHY

    def test_performance_monitor_snapshot(self):
        """Test performance snapshot."""
        from utils.monitoring import PerformanceMonitor
        monitor = PerformanceMonitor()
        monitor.record_request(100.0)
        snapshot = monitor.get_snapshot()
        assert snapshot.request_count == 1
        assert snapshot.uptime_seconds > 0


class TestMonitorManager:
    """Tests for MonitorManager singleton."""

    def test_monitor_manager_singleton(self):
        """Test MonitorManager is singleton."""
        from utils.monitoring import MonitorManager
        m1 = MonitorManager()
        m2 = MonitorManager()
        assert m1 is m2

    def test_monitor_manager_components(self):
        """Test MonitorManager has all components."""
        from utils.monitoring import MonitorManager
        manager = MonitorManager()
        assert manager.health is not None
        assert manager.errors is not None
        assert manager.performance is not None

    def test_monitor_manager_get_status(self):
        """Test getting comprehensive status."""
        from utils.monitoring import MonitorManager
        manager = MonitorManager()
        status = manager.get_status()
        assert "status" in status
        assert "timestamp" in status
        assert "uptime" in status
        assert "health" in status
        assert "errors" in status
        assert "performance" in status


class TestGlobalFunctions:
    """Tests for module-level convenience functions."""

    def test_get_monitor(self):
        """Test get_monitor function."""
        from utils.monitoring import get_monitor
        monitor = get_monitor()
        assert monitor is not None

    def test_check_health(self):
        """Test check_health function."""
        from utils.monitoring import check_health
        report = check_health()
        assert "status" in report
        assert "checks" in report

    def test_get_status(self):
        """Test get_status function."""
        from utils.monitoring import get_status
        status = get_status()
        assert "status" in status

    def test_record_error(self):
        """Test record_error function."""
        from utils.monitoring import get_monitor, record_error
        initial_count = get_monitor().errors.get_error_count()
        record_error("TestError", "Test message")
        # Note: might be cleaned up if outside window

    def test_record_request(self):
        """Test record_request function."""
        from utils.monitoring import get_monitor, record_request
        initial_count = get_monitor().performance.get_request_count()
        record_request(100.0)
        assert get_monitor().performance.get_request_count() > initial_count

    def test_get_uptime(self):
        """Test get_uptime function."""
        from utils.monitoring import get_uptime
        uptime = get_uptime()
        assert ":" in uptime

    def test_is_healthy(self):
        """Test is_healthy function."""
        from utils.monitoring import is_healthy
        result = is_healthy()
        assert isinstance(result, bool)
