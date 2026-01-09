"""
Performance test suite for Ollama Automation Harness.

This module contains load and stress tests to verify system performance
under various conditions. These tests help identify bottlenecks and
ensure the application can handle expected workloads.

Run performance tests only:
    pytest -m performance

Run performance tests with timing output:
    pytest -m performance -v --tb=short
"""

import concurrent.futures
import gc
import os
import statistics
import sys
import tempfile
import threading
import time
import tracemalloc
from pathlib import Path
from typing import Callable
from unittest.mock import patch, MagicMock

import pytest

# Mark all tests in this module as performance tests
pytestmark = pytest.mark.performance


# =============================================================================
# Performance Test Configuration
# =============================================================================

# Thresholds for performance tests (in seconds unless otherwise noted)
VALIDATION_MAX_TIME = 0.01  # 10ms per validation
COMMAND_EXECUTION_MAX_TIME = 5.0  # 5 seconds per command
FILE_OPERATION_MAX_TIME = 0.1  # 100ms per file operation
CLASSIFICATION_MAX_TIME = 0.05  # 50ms per classification (mocked)

# Load test parameters
CONCURRENT_OPERATIONS = 10  # Number of concurrent operations
BATCH_SIZE = 100  # Number of operations in batch tests
STRESS_ITERATIONS = 1000  # Number of iterations for stress tests


# =============================================================================
# Performance Testing Utilities
# =============================================================================


def measure_time(func: Callable, *args, **kwargs) -> tuple[float, any]:
    """
    Measure execution time of a function.

    Returns:
        Tuple of (elapsed_time, result)
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return elapsed, result


def measure_memory(func: Callable, *args, **kwargs) -> tuple[int, any]:
    """
    Measure peak memory usage of a function.

    Returns:
        Tuple of (peak_memory_bytes, result)
    """
    gc.collect()
    tracemalloc.start()

    result = func(*args, **kwargs)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return peak, result


def run_concurrent(func: Callable, args_list: list, max_workers: int = 5) -> list:
    """
    Run function concurrently with multiple argument sets.

    Returns:
        List of results
    """
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(func, *args) for args in args_list]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    return results


def calculate_stats(times: list[float]) -> dict:
    """Calculate statistics for a list of timing measurements."""
    return {
        "min": min(times),
        "max": max(times),
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "total": sum(times),
        "count": len(times),
    }


# =============================================================================
# Validation Performance Tests
# =============================================================================


class TestValidationPerformance:
    """Performance tests for input validation functions."""

    def test_prompt_validation_speed(self):
        """Test that prompt validation completes within acceptable time."""
        from utils.validation import validate_prompt

        # Generate various prompts
        prompts = [
            "short prompt",
            "medium " * 100 + " prompt",
            "long " * 500 + " prompt",
            "special chars: !@#$%^&*() test",
            "unicode: 你好世界 test",
        ]

        times = []
        for prompt in prompts:
            elapsed, _ = measure_time(validate_prompt, prompt)
            times.append(elapsed)
            assert elapsed < VALIDATION_MAX_TIME, f"Prompt validation too slow: {elapsed}s"

        stats = calculate_stats(times)
        assert stats["mean"] < VALIDATION_MAX_TIME, f"Mean validation time too high: {stats['mean']}s"

    def test_command_validation_speed(self):
        """Test that command validation completes quickly."""
        from utils.validation import validate_command, ValidationError

        commands = [
            "echo hello",
            "ls -la",
            "python script.py",
            "cat file.txt",
            "grep -r pattern .",
        ]

        times = []
        for cmd in commands:
            elapsed, _ = measure_time(validate_command, cmd)
            times.append(elapsed)
            assert elapsed < VALIDATION_MAX_TIME, f"Command validation too slow: {elapsed}s"

        stats = calculate_stats(times)
        assert stats["mean"] < VALIDATION_MAX_TIME

    def test_path_validation_speed(self, sandbox):
        """Test that path validation completes quickly."""
        from utils.validation import validate_path

        paths = [
            "file.txt",
            "subdir/file.py",
            "deep/nested/path/file.json",
            "another_file.md",
        ]

        times = []
        for path in paths:
            elapsed, _ = measure_time(validate_path, path, str(sandbox))
            times.append(elapsed)
            assert elapsed < VALIDATION_MAX_TIME

        stats = calculate_stats(times)
        assert stats["mean"] < VALIDATION_MAX_TIME

    def test_validation_batch_throughput(self):
        """Test validation throughput with batch operations."""
        from utils.validation import validate_prompt

        prompts = [f"Test prompt number {i}" for i in range(BATCH_SIZE)]

        start = time.perf_counter()
        for prompt in prompts:
            validate_prompt(prompt)
        elapsed = time.perf_counter() - start

        throughput = BATCH_SIZE / elapsed
        # Should process at least 1000 validations per second
        assert throughput > 1000, f"Throughput too low: {throughput} ops/sec"


# =============================================================================
# Execution Performance Tests
# =============================================================================


class TestExecutionPerformance:
    """Performance tests for command execution."""

    def test_simple_command_execution_speed(self, sandbox):
        """Test that simple commands execute quickly."""
        from core.executor import execute

        elapsed, result = measure_time(execute, "echo hello", str(sandbox))

        assert result.success is True
        assert elapsed < COMMAND_EXECUTION_MAX_TIME

    def test_file_write_speed(self, sandbox):
        """Test file write performance."""
        from core.executor import write_file_sandboxed

        content = "Test content\n" * 100

        times = []
        for i in range(10):
            elapsed, result = measure_time(
                write_file_sandboxed,
                f"test_{i}.txt",
                content,
                str(sandbox)
            )
            times.append(elapsed)
            assert result.success is True
            assert elapsed < FILE_OPERATION_MAX_TIME

        stats = calculate_stats(times)
        assert stats["mean"] < FILE_OPERATION_MAX_TIME

    def test_file_read_speed(self, sandbox):
        """Test file read performance."""
        from core.executor import write_file_sandboxed, read_file_sandboxed

        # Create files first
        content = "Test content\n" * 100
        for i in range(10):
            write_file_sandboxed(f"read_test_{i}.txt", content, str(sandbox))

        times = []
        for i in range(10):
            elapsed, result = measure_time(
                read_file_sandboxed,
                f"read_test_{i}.txt",
                str(sandbox)
            )
            times.append(elapsed)
            assert result.success is True
            assert elapsed < FILE_OPERATION_MAX_TIME

        stats = calculate_stats(times)
        assert stats["mean"] < FILE_OPERATION_MAX_TIME

    def test_concurrent_file_operations(self, sandbox):
        """Test concurrent file read/write operations."""
        from core.executor import write_file_sandboxed, read_file_sandboxed

        # Create files
        for i in range(CONCURRENT_OPERATIONS):
            write_file_sandboxed(f"concurrent_{i}.txt", f"content {i}", str(sandbox))

        def read_file(idx):
            return read_file_sandboxed(f"concurrent_{idx}.txt", str(sandbox))

        start = time.perf_counter()
        results = run_concurrent(
            read_file,
            [(i,) for i in range(CONCURRENT_OPERATIONS)],
            max_workers=5
        )
        elapsed = time.perf_counter() - start

        # All operations should succeed
        assert all(r.success for r in results)
        # Concurrent operations should be faster than sequential
        assert elapsed < CONCURRENT_OPERATIONS * FILE_OPERATION_MAX_TIME

    def test_large_file_handling(self, sandbox):
        """Test handling of larger files."""
        from core.executor import write_file_sandboxed, read_file_sandboxed

        # 100KB file
        large_content = "x" * (100 * 1024)

        write_elapsed, write_result = measure_time(
            write_file_sandboxed, "large_file.txt", large_content, str(sandbox)
        )
        assert write_result.success is True
        assert write_elapsed < 1.0  # Should complete within 1 second

        read_elapsed, read_result = measure_time(
            read_file_sandboxed, "large_file.txt", str(sandbox)
        )
        assert read_result.success is True
        assert read_elapsed < 1.0


# =============================================================================
# Classification Performance Tests (Mocked)
# =============================================================================


class TestClassificationPerformance:
    """Performance tests for response classification (with mocked AI)."""

    def test_classification_speed_mocked(self):
        """Test classification speed with mocked AI responses."""
        from core.classifier import classify

        mock_response = {
            "action": "user",
            "reason": "Test reason",
            "command": None,
            "risk_level": "low"
        }

        with patch("core.classifier.run_prompt") as mock:
            mock.return_value = str(mock_response)

            times = []
            for _ in range(50):
                elapsed, _ = measure_time(classify, "test response")
                times.append(elapsed)

            stats = calculate_stats(times)
            # Should be fast since AI is mocked
            assert stats["mean"] < CLASSIFICATION_MAX_TIME

    def test_json_parsing_speed(self):
        """Test JSON parsing performance."""
        from core.classifier import parse_json_response

        json_strings = [
            '{"action": "auto", "reason": "test"}',
            '{"action": "user", "reason": "' + "x" * 500 + '"}',
            '{"action": "skip", "reason": "test", "command": "echo hi"}',
        ]

        times = []
        for json_str in json_strings * 100:
            elapsed, _ = measure_time(parse_json_response, json_str)
            times.append(elapsed)

        stats = calculate_stats(times)
        assert stats["mean"] < 0.001  # Should be very fast

    def test_command_extraction_speed(self):
        """Test command extraction performance."""
        from core.classifier import extract_command

        responses = [
            "Here's the command:\n```bash\necho hello\n```",
            "Execute: `ls -la`",
            "No code here",
            "```python\nprint('hello')\n```",
        ]

        times = []
        for resp in responses * 100:
            elapsed, _ = measure_time(extract_command, resp)
            times.append(elapsed)

        stats = calculate_stats(times)
        assert stats["mean"] < 0.001


# =============================================================================
# Safety Module Performance Tests
# =============================================================================


class TestSafetyPerformance:
    """Performance tests for safety checks."""

    def test_permission_check_speed(self):
        """Test permission checking speed."""
        from core.safety import PermissionManager

        manager = PermissionManager()
        actions = ["run_tests", "read_file", "write_file", "deploy"]

        times = []
        for action in actions * 100:
            elapsed, _ = measure_time(manager.check_permission, action)
            times.append(elapsed)

        stats = calculate_stats(times)
        assert stats["mean"] < 0.001

    def test_decision_enforcement_speed(self):
        """Test decision enforcement speed."""
        from core.classifier import Decision
        from core.safety import PermissionManager

        manager = PermissionManager()
        decision = Decision(
            action="auto",
            reason="Test",
            command="echo hello",
            risk_level="low"
        )

        times = []
        for _ in range(100):
            elapsed, _ = measure_time(manager.enforce, decision)
            times.append(elapsed)

        stats = calculate_stats(times)
        assert stats["mean"] < 0.001


# =============================================================================
# Load Tests
# =============================================================================


class TestLoadHandling:
    """Load tests to verify system behavior under concurrent access."""

    def test_concurrent_validations(self):
        """Test handling of concurrent validation requests."""
        from utils.validation import validate_prompt

        def validate(prompt):
            return validate_prompt(prompt)

        prompts = [(f"Test prompt {i}",) for i in range(CONCURRENT_OPERATIONS * 2)]

        start = time.perf_counter()
        results = run_concurrent(validate, prompts, max_workers=CONCURRENT_OPERATIONS)
        elapsed = time.perf_counter() - start

        # All validations should succeed
        assert len(results) == len(prompts)
        # Should complete in reasonable time
        assert elapsed < 5.0

    def test_concurrent_error_handling(self):
        """Test that error handling works under concurrent load."""
        from utils.errors import HarnessError, ErrorCode, ErrorContext
        from utils.error_tracking import get_error_counts

        def create_error(idx):
            error = HarnessError(
                f"Test error {idx}",
                code=ErrorCode.UNKNOWN,
                context=ErrorContext(operation=f"test_{idx}")
            )
            return error.to_dict()

        args_list = [(i,) for i in range(CONCURRENT_OPERATIONS)]

        start = time.perf_counter()
        results = run_concurrent(create_error, args_list, max_workers=5)
        elapsed = time.perf_counter() - start

        assert len(results) == CONCURRENT_OPERATIONS
        assert all("message" in r for r in results)
        assert elapsed < 2.0

    def test_logging_under_load(self, sandbox):
        """Test that logging works correctly under load."""
        from utils.logger import get_logger, setup_logger
        import logging

        # Setup logger to temp file
        log_file = sandbox / "test.log"
        setup_logger(str(log_file), level=logging.INFO, enable_console=False)
        logger = get_logger()

        def log_message(idx):
            logger.info(f"Test message {idx}")
            return True

        args_list = [(i,) for i in range(BATCH_SIZE)]

        start = time.perf_counter()
        results = run_concurrent(log_message, args_list, max_workers=10)
        elapsed = time.perf_counter() - start

        assert all(results)
        # Logging should be fast even under load
        assert elapsed < 5.0


# =============================================================================
# Stress Tests
# =============================================================================


class TestStressConditions:
    """Stress tests to verify system stability under extreme conditions."""

    def test_validation_stress(self):
        """Stress test validation with many iterations."""
        from utils.validation import validate_prompt

        start = time.perf_counter()
        for i in range(STRESS_ITERATIONS):
            validate_prompt(f"Stress test prompt {i}")
        elapsed = time.perf_counter() - start

        throughput = STRESS_ITERATIONS / elapsed
        # Should handle at least 5000 validations per second
        assert throughput > 5000, f"Throughput too low: {throughput}"

    def test_error_creation_stress(self):
        """Stress test error object creation."""
        from utils.errors import HarnessError, ErrorCode, ErrorContext

        start = time.perf_counter()
        for i in range(STRESS_ITERATIONS):
            error = HarnessError(
                f"Error {i}",
                code=ErrorCode.UNKNOWN,
                context=ErrorContext(operation=f"op_{i}")
            )
            _ = error.to_dict()
        elapsed = time.perf_counter() - start

        throughput = STRESS_ITERATIONS / elapsed
        assert throughput > 1000

    def test_path_validation_stress(self, sandbox):
        """Stress test path validation."""
        from utils.validation import validate_path

        start = time.perf_counter()
        for i in range(STRESS_ITERATIONS):
            try:
                validate_path(f"file_{i % 100}.txt", str(sandbox))
            except Exception:
                pass  # Some validations may fail, that's OK
        elapsed = time.perf_counter() - start

        throughput = STRESS_ITERATIONS / elapsed
        assert throughput > 1000

    def test_long_string_handling(self):
        """Test handling of very long strings."""
        from utils.validation import validate_prompt, ValidationError

        # Test with increasingly large strings
        sizes = [100, 1000, 5000, 9000]  # Stay under MAX_PROMPT_LENGTH

        for size in sizes:
            long_string = "x" * size
            elapsed, _ = measure_time(validate_prompt, long_string)
            # Should handle long strings reasonably fast
            assert elapsed < 0.1, f"Too slow for size {size}: {elapsed}s"

    def test_special_characters_stress(self):
        """Stress test with special characters."""
        from utils.validation import validate_prompt, sanitize_string

        # String with many special characters
        special = "!@#$%^&*()[]{}|\\:\";<>?,./~`" * 100

        times = []
        for _ in range(100):
            elapsed, _ = measure_time(sanitize_string, special)
            times.append(elapsed)

        stats = calculate_stats(times)
        assert stats["mean"] < 0.01


# =============================================================================
# Memory Performance Tests
# =============================================================================


class TestMemoryPerformance:
    """Tests for memory usage and leak detection."""

    def test_validation_memory_usage(self):
        """Test that validation doesn't leak memory."""
        from utils.validation import validate_prompt

        # Measure memory for batch operation
        def batch_validate():
            for i in range(100):
                validate_prompt(f"Test prompt {i}")

        peak_memory, _ = measure_memory(batch_validate)

        # Should use less than 10MB for this operation
        assert peak_memory < 10 * 1024 * 1024

    def test_error_object_memory(self):
        """Test memory usage of error objects."""
        from utils.errors import HarnessError, ErrorCode, ErrorContext

        def create_errors():
            errors = []
            for i in range(100):
                error = HarnessError(
                    f"Error {i}",
                    code=ErrorCode.UNKNOWN,
                    context=ErrorContext(operation=f"op_{i}")
                )
                errors.append(error)
            return errors

        peak_memory, errors = measure_memory(create_errors)

        # 100 error objects should use less than 5MB
        assert peak_memory < 5 * 1024 * 1024
        assert len(errors) == 100

    def test_file_operation_memory(self, sandbox):
        """Test memory usage during file operations."""
        from core.executor import write_file_sandboxed, read_file_sandboxed

        # Create some files
        content = "x" * 10000  # 10KB
        for i in range(10):
            write_file_sandboxed(f"mem_test_{i}.txt", content, str(sandbox))

        def read_all_files():
            results = []
            for i in range(10):
                result = read_file_sandboxed(f"mem_test_{i}.txt", str(sandbox))
                results.append(result)
            return results

        peak_memory, results = measure_memory(read_all_files)

        # Reading 100KB of files should use less than 5MB overhead
        assert peak_memory < 5 * 1024 * 1024
        assert all(r.success for r in results)

    def test_no_memory_leak_repeated_operations(self):
        """Test that repeated operations don't leak memory."""
        from utils.validation import validate_prompt

        # Warm up
        for _ in range(10):
            validate_prompt("warmup")

        gc.collect()
        initial_objects = len(gc.get_objects())

        # Run many iterations
        for _ in range(1000):
            validate_prompt("test prompt")

        gc.collect()
        final_objects = len(gc.get_objects())

        # Object count shouldn't grow significantly
        growth = final_objects - initial_objects
        # Allow some growth but not proportional to iterations
        assert growth < 100, f"Potential memory leak: {growth} new objects"


# =============================================================================
# Throughput Benchmarks
# =============================================================================


class TestThroughputBenchmarks:
    """Benchmark tests to measure system throughput."""

    def test_validation_throughput(self):
        """Benchmark validation throughput."""
        from utils.validation import validate_prompt

        iterations = 10000

        start = time.perf_counter()
        for i in range(iterations):
            validate_prompt(f"Test {i}")
        elapsed = time.perf_counter() - start

        throughput = iterations / elapsed
        print(f"\nValidation throughput: {throughput:.0f} ops/sec")

        # Record but don't fail on throughput
        assert throughput > 0

    def test_sanitization_throughput(self):
        """Benchmark string sanitization throughput."""
        from utils.validation import sanitize_string

        iterations = 10000
        test_string = "Test string with\x00null bytes and special chars: !@#$%"

        start = time.perf_counter()
        for _ in range(iterations):
            sanitize_string(test_string)
        elapsed = time.perf_counter() - start

        throughput = iterations / elapsed
        print(f"\nSanitization throughput: {throughput:.0f} ops/sec")

        assert throughput > 0

    def test_path_traversal_check_throughput(self):
        """Benchmark path traversal detection throughput."""
        from utils.validation import contains_path_traversal

        iterations = 10000
        paths = ["safe/path.txt", "../bad", "also/safe.py", "..%2f/bad"]

        start = time.perf_counter()
        for i in range(iterations):
            contains_path_traversal(paths[i % len(paths)])
        elapsed = time.perf_counter() - start

        throughput = iterations / elapsed
        print(f"\nPath traversal check throughput: {throughput:.0f} ops/sec")

        assert throughput > 0

    def test_error_handling_throughput(self):
        """Benchmark error handling throughput."""
        from utils.errors import HarnessError, ErrorCode, ErrorContext

        iterations = 5000

        start = time.perf_counter()
        for i in range(iterations):
            error = HarnessError(
                f"Error {i}",
                code=ErrorCode.VALIDATION_FAILED,
                context=ErrorContext(operation="test")
            )
            _ = error.to_dict()
        elapsed = time.perf_counter() - start

        throughput = iterations / elapsed
        print(f"\nError handling throughput: {throughput:.0f} ops/sec")

        assert throughput > 0
