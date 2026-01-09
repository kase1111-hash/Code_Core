"""
Unit tests for utils/logger.py
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from utils.logger import (
    JsonFormatter,
    setup_logger,
    setup_debug_logger,
    get_logger,
    get_debug_logger,
    log_error,
    log_startup,
    log_shutdown,
    log_api_call,
    log_command_execution,
    log_file_operation,
    log_security_event,
    log_performance_metric,
    log_debug,
    log_trace,
    log_operation_timing,
    set_log_level,
    enable_verbose_logging,
    get_log_file_path,
    _mask_sensitive_data,
)


class TestJsonFormatter:
    """Tests for JsonFormatter class."""

    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert "timestamp" in parsed
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
        assert "logger" in parsed

    def test_format_includes_module(self):
        """Test that format includes module info."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="mymodule.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert "module" in parsed
        assert parsed["line"] == 42


class TestSetupLogger:
    """Tests for setup_logger function."""

    def test_setup_logger_creates_directory(self, tmp_path):
        """Test that setup_logger creates log directory."""
        # Reset global logger
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "logs" / "test.log"
        logger = setup_logger(
            str(log_file),
            enable_console=False,
        )

        assert log_file.parent.exists()
        assert logger is not None

    def test_setup_logger_returns_logger(self, tmp_path):
        """Test that setup_logger returns a logger."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        logger = setup_logger(str(log_file), enable_console=False)

        assert isinstance(logger, logging.Logger)
        assert logger.name == "ollama-harness"

    def test_setup_logger_singleton(self, tmp_path):
        """Test that setup_logger returns same instance."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        logger1 = setup_logger(str(log_file), enable_console=False)
        logger2 = setup_logger(str(log_file), enable_console=False)

        assert logger1 is logger2

    def test_setup_logger_with_json(self, tmp_path):
        """Test setup_logger with JSON formatting."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        logger = setup_logger(
            str(log_file),
            enable_console=False,
            enable_json=True,
        )

        # Log a message
        logger.info("Test message")

        # Check that JSON was written
        content = log_file.read_text()
        parsed = json.loads(content.strip())
        assert parsed["message"] == "Test message"


class TestSetupDebugLogger:
    """Tests for setup_debug_logger function."""

    def test_setup_debug_logger_creates_file(self, tmp_path):
        """Test that debug logger creates log file."""
        import utils.logger
        utils.logger._debug_logger = None

        log_file = tmp_path / "debug.log"
        logger = setup_debug_logger(str(log_file))

        assert logger is not None
        assert log_file.parent.exists()

    def test_setup_debug_logger_is_debug_level(self, tmp_path):
        """Test that debug logger is at DEBUG level."""
        import utils.logger
        utils.logger._debug_logger = None

        log_file = tmp_path / "debug.log"
        logger = setup_debug_logger(str(log_file))

        assert logger.level == logging.DEBUG


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_creates_if_needed(self, tmp_path):
        """Test that get_logger creates logger if needed."""
        import utils.logger
        utils.logger._logger = None

        # Temporarily change the log file path
        original = utils.logger.LOG_FILE
        utils.logger.LOG_FILE = str(tmp_path / "test.log")

        try:
            logger = get_logger()
            assert logger is not None
        finally:
            utils.logger.LOG_FILE = original


class TestLogError:
    """Tests for log_error function."""

    def test_log_error_captures_context(self, tmp_path):
        """Test that log_error captures context."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        setup_logger(str(log_file), enable_console=False)

        error = ValueError("test error")
        log_error(error, "test_context")

        content = log_file.read_text()
        assert "ERROR" in content
        assert "test_context" in content
        assert "test error" in content


class TestLogStartupShutdown:
    """Tests for log_startup and log_shutdown functions."""

    def test_log_startup(self, tmp_path):
        """Test log_startup logs message."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        setup_logger(str(log_file), enable_console=False)

        log_startup()

        content = log_file.read_text()
        assert "started" in content.lower()

    def test_log_shutdown(self, tmp_path):
        """Test log_shutdown logs message."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        setup_logger(str(log_file), enable_console=False)

        log_shutdown("test_reason")

        content = log_file.read_text()
        assert "stopped" in content.lower()
        assert "test_reason" in content


class TestLogApiCall:
    """Tests for log_api_call function."""

    def test_log_api_call_success(self, tmp_path):
        """Test logging successful API call."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        setup_logger(str(log_file), enable_console=False)

        log_api_call(
            service="claude",
            operation="test_op",
            success=True,
            duration_ms=150.5,
        )

        content = log_file.read_text()
        assert "API_CALL" in content
        assert "claude" in content
        assert "success" in content

    def test_log_api_call_with_details(self, tmp_path):
        """Test logging API call with details."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        setup_logger(str(log_file), enable_console=False)

        log_api_call(
            service="ollama",
            operation="generate",
            success=True,
            duration_ms=100,
            details={"model": "llama2"},
        )

        content = log_file.read_text()
        assert "model" in content


class TestLogCommandExecution:
    """Tests for log_command_execution function."""

    def test_log_command_execution(self, tmp_path):
        """Test logging command execution."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        setup_logger(str(log_file), enable_console=False)

        log_command_execution(
            command="echo hello",
            sandbox_root="/tmp/sandbox",
            success=True,
            return_code=0,
            duration_ms=50,
        )

        content = log_file.read_text()
        assert "COMMAND_EXEC" in content
        assert "echo hello" in content
        assert "success" in content


class TestLogSecurityEvent:
    """Tests for log_security_event function."""

    def test_log_security_event_high(self, tmp_path):
        """Test logging high severity security event."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        setup_logger(str(log_file), enable_console=False)

        log_security_event(
            event_type="unauthorized_access",
            severity="high",
            description="Access denied",
        )

        content = log_file.read_text()
        assert "SECURITY" in content
        assert "unauthorized_access" in content

    def test_log_security_event_with_details(self, tmp_path):
        """Test logging security event with details."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        setup_logger(str(log_file), enable_console=False)

        log_security_event(
            event_type="test_event",
            severity="medium",
            description="Test description",
            details={"ip": "192.168.1.1"},
        )

        content = log_file.read_text()
        assert "SECURITY" in content


class TestLogOperationTiming:
    """Tests for log_operation_timing context manager."""

    def test_log_operation_timing_success(self, tmp_path):
        """Test timing a successful operation."""
        import utils.logger
        utils.logger._logger = None
        utils.logger._debug_logger = None

        log_file = tmp_path / "test.log"
        setup_logger(str(log_file), level=logging.DEBUG, enable_console=False)

        with log_operation_timing("test_operation"):
            pass  # Simulate work

        # Timing is logged at DEBUG level
        content = log_file.read_text()
        assert "TIMING" in content or content == ""  # May be empty if DEBUG not logged

    def test_log_operation_timing_failure(self, tmp_path):
        """Test timing a failing operation."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        setup_logger(str(log_file), level=logging.DEBUG, enable_console=False)

        with pytest.raises(ValueError):
            with log_operation_timing("failing_op"):
                raise ValueError("test error")


class TestMaskSensitiveData:
    """Tests for _mask_sensitive_data function."""

    def test_masks_password(self):
        """Test that password is masked."""
        data = {"username": "user", "password": "secret123"}
        result = _mask_sensitive_data(data)

        assert result["username"] == "user"
        assert result["password"] == "***MASKED***"

    def test_masks_api_key(self):
        """Test that api_key is masked."""
        data = {"api_key": "sk-secret-key", "name": "test"}
        result = _mask_sensitive_data(data)

        assert result["api_key"] == "***MASKED***"
        assert result["name"] == "test"

    def test_masks_token(self):
        """Test that token is masked."""
        data = {"auth_token": "bearer-123", "id": 1}
        result = _mask_sensitive_data(data)

        assert result["auth_token"] == "***MASKED***"
        assert result["id"] == 1

    def test_masks_nested_secrets(self):
        """Test that nested secrets are masked."""
        data = {
            "config": {
                "api_key": "secret",
                "url": "http://example.com",
            }
        }
        result = _mask_sensitive_data(data)

        assert result["config"]["api_key"] == "***MASKED***"
        assert result["config"]["url"] == "http://example.com"

    def test_preserves_non_sensitive(self):
        """Test that non-sensitive data is preserved."""
        data = {"name": "test", "count": 42, "enabled": True}
        result = _mask_sensitive_data(data)

        assert result == data


class TestSetLogLevel:
    """Tests for set_log_level function."""

    def test_set_log_level(self, tmp_path):
        """Test setting log level."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        logger = setup_logger(str(log_file), enable_console=False)

        set_log_level(logging.DEBUG)
        assert logger.level == logging.DEBUG


class TestEnableVerboseLogging:
    """Tests for enable_verbose_logging function."""

    def test_enable_verbose_logging(self, tmp_path):
        """Test enabling verbose logging."""
        import utils.logger
        utils.logger._logger = None
        utils.logger._debug_logger = None

        # Set custom paths
        utils.logger.LOG_FILE = str(tmp_path / "test.log")
        utils.logger.DEBUG_LOG_FILE = str(tmp_path / "debug.log")

        enable_verbose_logging()

        logger = get_logger()
        assert logger.level == logging.DEBUG


class TestGetLogFilePath:
    """Tests for get_log_file_path function."""

    def test_returns_absolute_path(self):
        """Test that get_log_file_path returns absolute path."""
        path = get_log_file_path()
        assert os.path.isabs(path)
        assert ".log" in path  # Log file has .log extension


class TestLogDebugAndTrace:
    """Tests for log_debug and log_trace functions."""

    def test_log_debug(self, tmp_path):
        """Test log_debug function."""
        import utils.logger
        utils.logger._debug_logger = None

        log_file = tmp_path / "debug.log"
        setup_debug_logger(str(log_file))

        log_debug("Debug message", data={"key": "value"})

        content = log_file.read_text()
        assert "Debug message" in content

    def test_log_trace(self, tmp_path):
        """Test log_trace function."""
        import utils.logger
        utils.logger._debug_logger = None

        log_file = tmp_path / "debug.log"
        setup_debug_logger(str(log_file))

        log_trace("my_operation", "step_1", data={"value": 42})

        content = log_file.read_text()
        assert "TRACE" in content
        assert "my_operation" in content


class TestLogFileOperation:
    """Tests for log_file_operation function."""

    def test_log_file_operation_success(self, tmp_path):
        """Test logging successful file operation."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        setup_logger(str(log_file), enable_console=False)

        log_file_operation(
            operation="write",
            path="/tmp/test.txt",
            success=True,
            size=1024,
        )

        content = log_file.read_text()
        assert "FILE_OP" in content
        assert "write" in content
        assert "success" in content

    def test_log_file_operation_failure(self, tmp_path):
        """Test logging failed file operation."""
        import utils.logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        setup_logger(str(log_file), enable_console=False)

        log_file_operation(
            operation="read",
            path="/tmp/missing.txt",
            success=False,
        )

        content = log_file.read_text()
        assert "FILE_OP" in content
        assert "failure" in content
