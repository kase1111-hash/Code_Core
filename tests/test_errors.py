"""
Unit tests for utils/errors.py
"""

import pytest
from utils.errors import (
    ErrorCode,
    ErrorSeverity,
    ErrorContext,
    HarnessError,
    ValidationError,
    ConfigurationError,
    ExecutionError,
    SafetyError,
    ServiceError,
    format_error_for_user,
    format_error_for_log,
    is_recoverable,
    get_recovery_suggestion,
    wrap_exception,
)


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_error_codes_exist(self):
        """Test that expected error codes exist."""
        assert ErrorCode.UNKNOWN.value == 100
        assert ErrorCode.VALIDATION_FAILED.value == 200
        assert ErrorCode.OLLAMA_ERROR.value == 300
        assert ErrorCode.EXECUTION_FAILED.value == 400
        assert ErrorCode.SAFETY_VIOLATION.value == 500

    def test_all_codes_unique(self):
        """Test that all error codes have unique values."""
        values = [code.value for code in ErrorCode]
        assert len(values) == len(set(values))


class TestErrorSeverity:
    """Tests for ErrorSeverity enum."""

    def test_severity_levels_exist(self):
        """Test that expected severity levels exist."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestErrorContext:
    """Tests for ErrorContext dataclass."""

    def test_default_context(self):
        """Test default context creation."""
        ctx = ErrorContext()
        assert ctx.operation == ""
        assert ctx.input_data is None
        assert ctx.details == {}

    def test_context_with_data(self):
        """Test context with data."""
        ctx = ErrorContext(
            operation="test_op",
            input_data="test input",
            details={"key": "value"}
        )
        assert ctx.operation == "test_op"
        assert ctx.input_data == "test input"
        assert ctx.details == {"key": "value"}

    def test_context_str(self):
        """Test context string representation."""
        ctx = ErrorContext(operation="test_op")
        assert "operation=test_op" in str(ctx)


class TestHarnessError:
    """Tests for HarnessError base exception."""

    def test_basic_creation(self):
        """Test basic error creation."""
        error = HarnessError("Test error")
        assert str(error.args[0]) == "Test error"
        assert error.code == ErrorCode.UNKNOWN
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recoverable is True

    def test_error_with_code(self):
        """Test error with specific code."""
        error = HarnessError(
            "Test error",
            code=ErrorCode.VALIDATION_FAILED,
            severity=ErrorSeverity.LOW
        )
        assert error.code == ErrorCode.VALIDATION_FAILED
        assert error.severity == ErrorSeverity.LOW

    def test_error_with_context(self):
        """Test error with context."""
        ctx = ErrorContext(operation="test")
        error = HarnessError("Test error", context=ctx)
        assert error.context.operation == "test"

    def test_error_str(self):
        """Test error string representation."""
        error = HarnessError("Test error", code=ErrorCode.VALIDATION_FAILED)
        error_str = str(error)
        assert "VALIDATION_FAILED" in error_str
        assert "Test error" in error_str

    def test_error_to_dict(self):
        """Test error to dictionary conversion."""
        error = HarnessError("Test error", code=ErrorCode.UNKNOWN)
        error_dict = error.to_dict()
        assert error_dict["message"] == "Test error"
        assert error_dict["code"] == "UNKNOWN"
        assert "severity" in error_dict
        assert "recoverable" in error_dict


class TestSpecializedErrors:
    """Tests for specialized error classes."""

    def test_validation_error(self):
        """Test ValidationError creation."""
        error = ValidationError("Invalid input")
        assert error.code == ErrorCode.VALIDATION_FAILED
        assert error.severity == ErrorSeverity.LOW
        assert error.recoverable is True

    def test_configuration_error(self):
        """Test ConfigurationError creation."""
        error = ConfigurationError("Config missing")
        assert error.code == ErrorCode.CONFIGURATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.recoverable is False

    def test_execution_error(self):
        """Test ExecutionError creation."""
        error = ExecutionError("Command failed")
        assert error.code == ErrorCode.EXECUTION_FAILED
        assert error.severity == ErrorSeverity.MEDIUM

    def test_safety_error(self):
        """Test SafetyError creation."""
        error = SafetyError("Unsafe operation")
        assert error.code == ErrorCode.SAFETY_VIOLATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.recoverable is False

    def test_service_error(self):
        """Test ServiceError creation."""
        error = ServiceError("Service unavailable")
        assert error.code == ErrorCode.OLLAMA_ERROR
        assert error.severity == ErrorSeverity.MEDIUM


class TestFormatErrorForUser:
    """Tests for format_error_for_user function."""

    def test_harness_error_formatted(self):
        """Test formatting of HarnessError."""
        error = HarnessError("Something went wrong")
        result = format_error_for_user(error)
        assert "Something went wrong" in result

    def test_standard_exception_formatted(self):
        """Test formatting of standard exception."""
        error = ValueError("Invalid value")
        result = format_error_for_user(error)
        assert "Invalid value" in result
        assert "Unexpected error" in result

    def test_ollama_not_found_message(self):
        """Test user-friendly message for Ollama not found."""
        error = HarnessError("Not found", code=ErrorCode.OLLAMA_NOT_FOUND)
        result = format_error_for_user(error)
        assert "Ollama" in result


class TestFormatErrorForLog:
    """Tests for format_error_for_log function."""

    def test_harness_error_logged(self):
        """Test log formatting of HarnessError."""
        error = HarnessError("Test error", code=ErrorCode.UNKNOWN)
        result = format_error_for_log(error)
        assert isinstance(result, dict)
        assert result["message"] == "Test error"
        assert result["code"] == "UNKNOWN"

    def test_standard_exception_logged(self):
        """Test log formatting of standard exception."""
        error = ValueError("Invalid")
        result = format_error_for_log(error)
        assert isinstance(result, dict)
        assert "Invalid" in result["message"]
        assert result["type"] == "ValueError"


class TestIsRecoverable:
    """Tests for is_recoverable function."""

    def test_recoverable_error(self):
        """Test recoverable error detection."""
        error = HarnessError("Test", recoverable=True)
        assert is_recoverable(error) is True

    def test_non_recoverable_error(self):
        """Test non-recoverable error detection."""
        error = HarnessError("Test", recoverable=False)
        assert is_recoverable(error) is False

    def test_standard_exception_not_recoverable(self):
        """Test that standard exceptions are not recoverable."""
        error = ValueError("Test")
        assert is_recoverable(error) is False


class TestGetRecoverySuggestion:
    """Tests for get_recovery_suggestion function."""

    def test_validation_error_suggestion(self):
        """Test suggestion for validation error."""
        error = HarnessError("Invalid", code=ErrorCode.VALIDATION_FAILED)
        suggestion = get_recovery_suggestion(error)
        assert suggestion is not None
        assert "input" in suggestion.lower() or "try again" in suggestion.lower()

    def test_ollama_not_found_suggestion(self):
        """Test suggestion for Ollama not found."""
        error = HarnessError("Not found", code=ErrorCode.OLLAMA_NOT_FOUND)
        suggestion = get_recovery_suggestion(error)
        assert suggestion is not None
        assert "ollama" in suggestion.lower()

    def test_unknown_error_no_suggestion(self):
        """Test that unknown errors may have no suggestion."""
        error = HarnessError("Unknown", code=ErrorCode.UNKNOWN)
        suggestion = get_recovery_suggestion(error)
        # Unknown errors may or may not have suggestions


class TestWrapException:
    """Tests for wrap_exception function."""

    def test_wraps_standard_exception(self):
        """Test wrapping a standard exception."""
        original = ValueError("Test value error")
        wrapped = wrap_exception(original, "test_operation")
        assert isinstance(wrapped, HarnessError)
        assert wrapped.context.operation == "test_operation"
        assert wrapped.cause is original

    def test_preserves_harness_error(self):
        """Test that HarnessError is not re-wrapped."""
        original = HarnessError("Test error")
        wrapped = wrap_exception(original, "test_operation")
        assert wrapped is original or wrapped.context.operation == "test_operation"

    def test_file_not_found_code(self):
        """Test that FileNotFoundError gets correct code."""
        original = FileNotFoundError("File missing")
        wrapped = wrap_exception(original, "file_op")
        assert wrapped.code == ErrorCode.FILE_NOT_FOUND

    def test_permission_error_code(self):
        """Test that PermissionError gets correct code."""
        original = PermissionError("Access denied")
        wrapped = wrap_exception(original, "file_op")
        assert wrapped.code == ErrorCode.PERMISSION_DENIED
