"""
Tests for utils/metrics.py module.

Comprehensive tests for metrics collection including:
- Counter, Gauge, Histogram, Timer metrics
- MetricsRegistry singleton
- Prometheus export format
- JSON export format
"""

import threading
import time
from unittest.mock import patch

import pytest


class TestCounter:
    """Tests for Counter metric."""

    def test_counter_initial_value(self):
        """Test counter starts at zero."""
        from utils.metrics import Counter
        c = Counter(name="test_counter")
        assert c.get() == 0.0

    def test_counter_increment(self):
        """Test counter increment."""
        from utils.metrics import Counter
        c = Counter(name="test_counter")
        c.inc()
        assert c.get() == 1.0

    def test_counter_increment_by_amount(self):
        """Test counter increment by specific amount."""
        from utils.metrics import Counter
        c = Counter(name="test_counter")
        c.inc(5.0)
        assert c.get() == 5.0

    def test_counter_multiple_increments(self):
        """Test multiple increments accumulate."""
        from utils.metrics import Counter
        c = Counter(name="test_counter")
        c.inc(1)
        c.inc(2)
        c.inc(3)
        assert c.get() == 6.0

    def test_counter_reset(self):
        """Test counter reset."""
        from utils.metrics import Counter
        c = Counter(name="test_counter")
        c.inc(10)
        c.reset()
        assert c.get() == 0.0

    def test_counter_thread_safety(self):
        """Test counter is thread-safe."""
        from utils.metrics import Counter
        c = Counter(name="test_counter")

        def increment_many():
            for _ in range(100):
                c.inc()

        threads = [threading.Thread(target=increment_many) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert c.get() == 1000.0


class TestGauge:
    """Tests for Gauge metric."""

    def test_gauge_initial_value(self):
        """Test gauge starts at zero."""
        from utils.metrics import Gauge
        g = Gauge(name="test_gauge")
        assert g.get() == 0.0

    def test_gauge_set(self):
        """Test gauge set value."""
        from utils.metrics import Gauge
        g = Gauge(name="test_gauge")
        g.set(42.0)
        assert g.get() == 42.0

    def test_gauge_increment(self):
        """Test gauge increment."""
        from utils.metrics import Gauge
        g = Gauge(name="test_gauge")
        g.set(10)
        g.inc(5)
        assert g.get() == 15.0

    def test_gauge_decrement(self):
        """Test gauge decrement."""
        from utils.metrics import Gauge
        g = Gauge(name="test_gauge")
        g.set(10)
        g.dec(3)
        assert g.get() == 7.0

    def test_gauge_can_go_negative(self):
        """Test gauge can go below zero."""
        from utils.metrics import Gauge
        g = Gauge(name="test_gauge")
        g.dec(5)
        assert g.get() == -5.0


class TestHistogram:
    """Tests for Histogram metric."""

    def test_histogram_initial_state(self):
        """Test histogram starts empty."""
        from utils.metrics import Histogram
        h = Histogram(name="test_histogram")
        assert h.get_count() == 0
        assert h.get_sum() == 0.0

    def test_histogram_observe(self):
        """Test histogram observation."""
        from utils.metrics import Histogram
        h = Histogram(name="test_histogram")
        h.observe(1.5)
        assert h.get_count() == 1
        assert h.get_sum() == 1.5

    def test_histogram_multiple_observations(self):
        """Test multiple observations."""
        from utils.metrics import Histogram
        h = Histogram(name="test_histogram")
        h.observe(1.0)
        h.observe(2.0)
        h.observe(3.0)
        assert h.get_count() == 3
        assert h.get_sum() == 6.0

    def test_histogram_mean(self):
        """Test histogram mean calculation."""
        from utils.metrics import Histogram
        h = Histogram(name="test_histogram")
        h.observe(2.0)
        h.observe(4.0)
        h.observe(6.0)
        assert h.get_mean() == 4.0

    def test_histogram_mean_empty(self):
        """Test histogram mean when empty."""
        from utils.metrics import Histogram
        h = Histogram(name="test_histogram")
        assert h.get_mean() == 0.0

    def test_histogram_percentile(self):
        """Test histogram percentile calculation."""
        from utils.metrics import Histogram
        h = Histogram(name="test_histogram")
        for i in range(1, 101):
            h.observe(float(i))
        # 50th percentile should be around 50
        assert 45 <= h.get_percentile(50) <= 55

    def test_histogram_percentile_empty(self):
        """Test histogram percentile when empty."""
        from utils.metrics import Histogram
        h = Histogram(name="test_histogram")
        assert h.get_percentile(50) == 0.0

    def test_histogram_bucket_counts(self):
        """Test histogram bucket counts."""
        from utils.metrics import Histogram
        h = Histogram(name="test_histogram", buckets=(1.0, 5.0, 10.0))
        h.observe(0.5)  # <= 1.0
        h.observe(3.0)  # <= 5.0
        h.observe(7.0)  # <= 10.0
        h.observe(15.0)  # > 10.0 (inf bucket)

        counts = h.get_bucket_counts()
        assert counts[1.0] == 1
        assert counts[5.0] == 1
        assert counts[10.0] == 1
        assert counts[float("inf")] == 1

    def test_histogram_reset(self):
        """Test histogram reset."""
        from utils.metrics import Histogram
        h = Histogram(name="test_histogram")
        h.observe(1.0)
        h.observe(2.0)
        h.reset()
        assert h.get_count() == 0
        assert h.get_sum() == 0.0


class TestTimer:
    """Tests for Timer metric."""

    def test_timer_context_manager(self):
        """Test timer as context manager."""
        from utils.metrics import Histogram, Timer
        h = Histogram(name="test_histogram")
        t = Timer(h)

        with t:
            time.sleep(0.01)  # 10ms

        assert h.get_count() == 1
        assert h.get_sum() >= 0.01  # At least 10ms

    def test_timer_decorator(self):
        """Test timer as decorator."""
        from utils.metrics import Histogram, Timer
        h = Histogram(name="test_histogram")
        t = Timer(h)

        @t
        def slow_function():
            time.sleep(0.01)
            return "done"

        result = slow_function()
        assert result == "done"
        assert h.get_count() == 1


class TestMetricType:
    """Tests for MetricType enum."""

    def test_metric_types(self):
        """Test metric type values."""
        from utils.metrics import MetricType
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.TIMER.value == "timer"


class TestMetricValue:
    """Tests for MetricValue dataclass."""

    def test_metric_value_creation(self):
        """Test MetricValue creation."""
        from utils.metrics import MetricType, MetricValue
        mv = MetricValue(
            name="test_metric",
            type=MetricType.COUNTER,
            value=42.0,
            description="Test metric"
        )
        assert mv.name == "test_metric"
        assert mv.type == MetricType.COUNTER
        assert mv.value == 42.0

    def test_metric_value_default_labels(self):
        """Test MetricValue default labels."""
        from utils.metrics import MetricType, MetricValue
        mv = MetricValue(
            name="test_metric",
            type=MetricType.GAUGE,
            value=0
        )
        assert mv.labels == {}


class TestMetricsRegistry:
    """Tests for MetricsRegistry singleton."""

    def test_registry_singleton(self):
        """Test registry is singleton."""
        from utils.metrics import MetricsRegistry
        r1 = MetricsRegistry()
        r2 = MetricsRegistry()
        assert r1 is r2

    def test_registry_counter(self):
        """Test registry counter creation."""
        from utils.metrics import get_registry
        registry = get_registry()
        c = registry.counter("test_registry_counter", "Test counter")
        assert c.get() == 0.0
        c.inc()
        # Same counter returned
        c2 = registry.counter("test_registry_counter")
        assert c2.get() == 1.0

    def test_registry_gauge(self):
        """Test registry gauge creation."""
        from utils.metrics import get_registry
        registry = get_registry()
        g = registry.gauge("test_registry_gauge", "Test gauge")
        g.set(100)
        g2 = registry.gauge("test_registry_gauge")
        assert g2.get() == 100.0

    def test_registry_histogram(self):
        """Test registry histogram creation."""
        from utils.metrics import get_registry
        registry = get_registry()
        h = registry.histogram("test_registry_histogram", "Test histogram")
        h.observe(5.0)
        h2 = registry.histogram("test_registry_histogram")
        assert h2.get_count() == 1

    def test_registry_timer(self):
        """Test registry timer creation."""
        from utils.metrics import get_registry
        registry = get_registry()
        t = registry.timer("test_timer_metric", "Test timer")
        with t:
            pass
        h = registry.histogram("test_timer_metric")
        assert h.get_count() >= 1

    def test_registry_get_all_metrics(self):
        """Test getting all metrics."""
        from utils.metrics import get_registry
        registry = get_registry()
        metrics = registry.get_all_metrics()
        assert isinstance(metrics, dict)

    def test_registry_uptime(self):
        """Test registry uptime."""
        from utils.metrics import get_registry
        registry = get_registry()
        uptime = registry.get_uptime()
        assert uptime >= 0

    def test_registry_collect(self):
        """Test collecting all metric values."""
        from utils.metrics import get_registry
        registry = get_registry()
        values = registry.collect()
        assert isinstance(values, list)

    def test_registry_to_prometheus(self):
        """Test Prometheus export format."""
        from utils.metrics import get_registry
        registry = get_registry()
        prometheus_output = registry.to_prometheus()
        assert isinstance(prometheus_output, str)
        assert "# TYPE" in prometheus_output

    def test_registry_to_json(self):
        """Test JSON export format."""
        import json
        from utils.metrics import get_registry
        registry = get_registry()
        json_output = registry.to_json()
        data = json.loads(json_output)
        assert "timestamp" in data
        assert "metrics" in data
        assert "uptime_seconds" in data

    def test_registry_save_to_file(self, tmp_path):
        """Test saving metrics to file."""
        from utils.metrics import get_registry
        registry = get_registry()
        filepath = tmp_path / "metrics.json"
        with patch("utils.metrics.METRICS_DIR", tmp_path):
            result_path = registry.save_to_file(filepath)
        assert result_path.exists()

    def test_registry_reset_all(self):
        """Test resetting all metrics."""
        from utils.metrics import get_registry
        registry = get_registry()
        c = registry.counter("reset_test_counter")
        c.inc(10)
        registry.reset_all()
        # Counter should be reset
        assert c.get() == 0.0


class TestGlobalFunctions:
    """Tests for module-level convenience functions."""

    def test_counter_function(self):
        """Test counter convenience function."""
        from utils.metrics import counter
        c = counter("global_test_counter", "Test")
        c.inc()
        assert c.get() >= 1

    def test_gauge_function(self):
        """Test gauge convenience function."""
        from utils.metrics import gauge
        g = gauge("global_test_gauge", "Test")
        g.set(50)
        assert g.get() == 50

    def test_histogram_function(self):
        """Test histogram convenience function."""
        from utils.metrics import histogram
        h = histogram("global_test_histogram", "Test")
        h.observe(1.0)
        assert h.get_count() >= 1

    def test_timer_function(self):
        """Test timer convenience function."""
        from utils.metrics import timer
        t = timer("global_test_timer", "Test")
        with t:
            pass

    def test_timed_context_manager(self):
        """Test timed context manager."""
        from utils.metrics import histogram, timed
        with timed("timed_test_operation"):
            time.sleep(0.001)
        h = histogram("timed_test_operation")
        assert h.get_count() >= 1

    def test_increment_function(self):
        """Test increment convenience function."""
        from utils.metrics import counter, increment
        increment("increment_test_counter")
        c = counter("increment_test_counter")
        assert c.get() >= 1

    def test_record_function(self):
        """Test record convenience function."""
        from utils.metrics import histogram, record
        record("record_test_histogram", 5.0)
        h = histogram("record_test_histogram")
        assert h.get_count() >= 1

    def test_set_gauge_function(self):
        """Test set_gauge convenience function."""
        from utils.metrics import gauge, set_gauge
        set_gauge("set_gauge_test", 100)
        g = gauge("set_gauge_test")
        assert g.get() == 100

    def test_get_metrics_summary(self):
        """Test get_metrics_summary function."""
        from utils.metrics import get_metrics_summary
        summary = get_metrics_summary()
        assert "uptime_seconds" in summary
        assert "total_metrics" in summary
        assert "metrics" in summary


class TestMetricsEnabled:
    """Tests for metrics enabled/disabled behavior."""

    def test_metrics_enabled_default(self):
        """Test METRICS_ENABLED default value."""
        from utils.metrics import METRICS_ENABLED
        assert isinstance(METRICS_ENABLED, bool)
