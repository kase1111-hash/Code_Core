"""
Unit tests for utils/error_tracking.py
"""

import json
import os
from unittest.mock import patch

import pytest

from utils.error_tracking import (
    capture_errors,
    capture_exception,
    capture_message,
    error_context,
    format_for_elk,
    get_elk_index_template,
    get_error_counts,
    get_error_summary,
    init_error_tracking,
    register_error_callback,
    reset_error_counts,
    unregister_error_callback,
)
from utils.errors import ErrorCode, HarnessError


class TestInitErrorTracking:
    """Tests for init_error_tracking function."""

    def test_init_without_sentry(self):
        """Test initialization without Sentry DSN."""
        result = init_error_tracking()
        assert result is True

    @patch.dict(os.environ, {"SENTRY_DSN": ""})
    def test_init_with_empty_dsn(self):
        """Test initialization with empty Sentry DSN."""
        result = init_error_tracking()
        assert result is True


class TestCaptureException:
    """Tests for capture_exception function."""

    def test_capture_standard_exception(self):
        """Test capturing a standard exception."""
        reset_error_counts()
        error = ValueError("test error")
        error_id = capture_exception(error, context="test_context")

        assert error_id.startswith("err_")
        assert len(error_id) > 4

    def test_capture_harness_error(self):
        """Test capturing a HarnessError."""
        reset_error_counts()
        error = HarnessError("test error", code=ErrorCode.VALIDATION_FAILED)
        error_id = capture_exception(error, context="test_context")

        assert error_id.startswith("err_")
        counts = get_error_counts()
        assert "VALIDATION_FAILED" in counts

    def test_capture_with_extra(self):
        """Test capturing exception with extra data."""
        reset_error_counts()
        error = ValueError("test")
        error_id = capture_exception(
            error,
            context="test",
            extra={"key": "value"},
        )
        assert error_id is not None

    def test_capture_with_tags(self):
        """Test capturing exception with tags."""
        reset_error_counts()
        error = ValueError("test")
        error_id = capture_exception(
            error,
            context="test",
            tags={"environment": "test"},
        )
        assert error_id is not None

    def test_capture_with_user_id(self):
        """Test capturing exception with user ID."""
        reset_error_counts()
        error = ValueError("test")
        error_id = capture_exception(
            error,
            context="test",
            user_id="user123",
        )
        assert error_id is not None


class TestCaptureMessage:
    """Tests for capture_message function."""

    def test_capture_error_message(self):
        """Test capturing an error message."""
        error_id = capture_message("Test error message", level="error")
        assert error_id.startswith("err_")

    def test_capture_warning_message(self):
        """Test capturing a warning message."""
        error_id = capture_message("Test warning", level="warning")
        assert error_id is not None

    def test_capture_message_with_context(self):
        """Test capturing message with context."""
        error_id = capture_message(
            "Test message",
            context="test_operation",
            extra={"detail": "value"},
        )
        assert error_id is not None


class TestErrorCounts:
    """Tests for error counting functions."""

    def test_error_counts_initial(self):
        """Test initial error counts are empty or reset."""
        reset_error_counts()
        counts = get_error_counts()
        assert isinstance(counts, dict)

    def test_error_counts_increment(self):
        """Test error counts increment."""
        reset_error_counts()
        error = HarnessError("test", code=ErrorCode.UNKNOWN)
        capture_exception(error)

        counts = get_error_counts()
        assert "UNKNOWN" in counts
        assert counts["UNKNOWN"] >= 1

    def test_reset_error_counts(self):
        """Test resetting error counts."""
        error = ValueError("test")
        capture_exception(error)
        reset_error_counts()

        counts = get_error_counts()
        assert sum(counts.values()) == 0


class TestErrorSummary:
    """Tests for get_error_summary function."""

    def test_error_summary_structure(self):
        """Test error summary has correct structure."""
        reset_error_counts()
        summary = get_error_summary()

        assert "total_errors" in summary
        assert "unique_error_codes" in summary
        assert "top_errors" in summary
        assert "sentry_enabled" in summary

    def test_error_summary_counts(self):
        """Test error summary counts correctly."""
        reset_error_counts()
        error1 = HarnessError("test1", code=ErrorCode.UNKNOWN)
        error2 = HarnessError("test2", code=ErrorCode.VALIDATION_FAILED)
        capture_exception(error1)
        capture_exception(error2)

        summary = get_error_summary()
        assert summary["total_errors"] >= 2
        assert summary["unique_error_codes"] >= 2


class TestErrorCallbacks:
    """Tests for error callback functions."""

    def test_register_callback(self):
        """Test registering an error callback."""
        reset_error_counts()
        callback_called = []

        def test_callback(record):
            callback_called.append(record)

        register_error_callback(test_callback)

        error = ValueError("test")
        capture_exception(error)

        assert len(callback_called) >= 1
        unregister_error_callback(test_callback)

    def test_unregister_callback(self):
        """Test unregistering an error callback."""
        callback_called = []

        def test_callback(record):
            callback_called.append(record)

        register_error_callback(test_callback)
        unregister_error_callback(test_callback)

        reset_error_counts()
        error = ValueError("test")
        capture_exception(error)

        # Callback should not have been called
        assert len(callback_called) == 0

    def test_callback_exception_ignored(self):
        """Test that callback exceptions are ignored."""
        def bad_callback(record):
            raise Exception("callback error")

        register_error_callback(bad_callback)

        # Should not raise
        error = ValueError("test")
        error_id = capture_exception(error)
        assert error_id is not None

        unregister_error_callback(bad_callback)


class TestErrorContext:
    """Tests for error_context context manager."""

    def test_error_context_captures_exception(self):
        """Test error_context captures exceptions."""
        reset_error_counts()

        with pytest.raises(ValueError), error_context("test_operation") as ctx:
            raise ValueError("test error")

        assert ctx.error_id is not None
        assert ctx.error_id.startswith("err_")

    def test_error_context_no_exception(self):
        """Test error_context with no exception."""
        with error_context("test_operation") as ctx:
            pass  # No exception

        assert ctx.error_id is None

    def test_error_context_reraise_false(self):
        """Test error_context with reraise=False."""
        with error_context("test_operation", reraise=False) as ctx:
            raise ValueError("test error")

        assert ctx.error_id is not None

    def test_error_context_with_extra(self):
        """Test error_context with extra data."""
        reset_error_counts()

        with pytest.raises(ValueError):
            with error_context("test", extra={"key": "value"}) as ctx:
                raise ValueError("test")

        assert ctx.error_id is not None


class TestCaptureErrorsDecorator:
    """Tests for capture_errors decorator."""

    def test_decorator_captures_exception(self):
        """Test decorator captures exceptions."""
        reset_error_counts()

        @capture_errors(context="decorated_function")
        def failing_function():
            raise ValueError("decorated error")

        with pytest.raises(ValueError):
            failing_function()

        counts = get_error_counts()
        assert "UNKNOWN" in counts

    def test_decorator_reraise_false(self):
        """Test decorator with reraise=False."""
        @capture_errors(context="test", reraise=False)
        def failing_function():
            raise ValueError("error")

        result = failing_function()
        assert result is None

    def test_decorator_success(self):
        """Test decorator with successful function."""
        @capture_errors(context="test")
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_decorator_default_context(self):
        """Test decorator uses function name as default context."""
        @capture_errors()
        def my_function():
            raise ValueError("error")

        with pytest.raises(ValueError):
            my_function()


class TestFormatForElk:
    """Tests for format_for_elk function."""

    def test_format_standard_exception(self):
        """Test formatting standard exception for ELK."""
        error = ValueError("test error")
        result = format_for_elk(error, context="test")

        parsed = json.loads(result)
        assert "@timestamp" in parsed
        assert "error_id" in parsed
        assert "error_type" in parsed
        assert parsed["error_type"] == "ValueError"

    def test_format_harness_error(self):
        """Test formatting HarnessError for ELK."""
        error = HarnessError("test", code=ErrorCode.VALIDATION_FAILED)
        result = format_for_elk(error)

        parsed = json.loads(result)
        assert parsed["error_code"] == "VALIDATION_FAILED"

    def test_format_includes_context(self):
        """Test format includes context."""
        error = ValueError("test")
        result = format_for_elk(error, context="my_context")

        parsed = json.loads(result)
        assert parsed["context"] == "my_context"


class TestGetElkIndexTemplate:
    """Tests for get_elk_index_template function."""

    def test_template_structure(self):
        """Test ELK index template structure."""
        template = get_elk_index_template()

        assert "index_patterns" in template
        assert "settings" in template
        assert "mappings" in template

    def test_template_mappings(self):
        """Test ELK index template mappings."""
        template = get_elk_index_template()
        properties = template["mappings"]["properties"]

        assert "@timestamp" in properties
        assert "error_id" in properties
        assert "error_code" in properties
        assert "error_type" in properties
        assert "error_message" in properties
        assert "severity" in properties

    def test_template_timestamp_type(self):
        """Test timestamp field type."""
        template = get_elk_index_template()
        props = template["mappings"]["properties"]
        assert props["@timestamp"]["type"] == "date"

    def test_template_keyword_fields(self):
        """Test keyword field types."""
        template = get_elk_index_template()
        props = template["mappings"]["properties"]

        keyword_fields = ["level", "error_id", "error_code", "error_type", "severity"]
        for field in keyword_fields:
            assert props[field]["type"] == "keyword"
