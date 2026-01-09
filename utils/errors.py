"""
Centralized error handling module.

Provides a consistent exception hierarchy, error codes, and
recovery helpers for the Ollama Automation Harness.
"""

from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field


class ErrorCode(Enum):
    """Error codes for categorizing exceptions."""

    # General errors (1xx)
    UNKNOWN = 100
    CONFIGURATION = 101
    INITIALIZATION = 102

    # Validation errors (2xx)
    VALIDATION_FAILED = 200
    INVALID_INPUT = 201
    INVALID_PATH = 202
    INVALID_COMMAND = 203
    PATH_TRAVERSAL = 204
    SHELL_INJECTION = 205

    # External service errors (3xx)
    OLLAMA_ERROR = 300
    OLLAMA_TIMEOUT = 301
    OLLAMA_NOT_FOUND = 302
    CLAUDE_ERROR = 310
    CLAUDE_API_ERROR = 311
    CLAUDE_AUTH_ERROR = 312

    # Execution errors (4xx)
    EXECUTION_FAILED = 400
    COMMAND_TIMEOUT = 401
    PERMISSION_DENIED = 402
    FILE_NOT_FOUND = 403
    SANDBOX_VIOLATION = 404

    # Safety errors (5xx)
    SAFETY_VIOLATION = 500
    DANGEROUS_OPERATION = 501
    PERMISSION_REJECTED = 502


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Additional context for an error."""

    operation: str = ""
    input_data: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        parts = []
        if self.operation:
            parts.append(f"operation={self.operation}")
        if self.input_data:
            # Truncate input data for display
            truncated = self.input_data[:100]
            if len(self.input_data) > 100:
                truncated += "..."
            parts.append(f"input={truncated}")
        if self.details:
            parts.append(f"details={self.details}")
        return ", ".join(parts) if parts else "no context"


class HarnessError(Exception):
    """
    Base exception for all Ollama Automation Harness errors.

    Attributes:
        code: Error code for categorization
        severity: Severity level of the error
        context: Additional context about the error
        recoverable: Whether the error can potentially be recovered from
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        recoverable: bool = True,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.code = code
        self.severity = severity
        self.context = context or ErrorContext()
        self.recoverable = recoverable
        self.cause = cause

    def __str__(self) -> str:
        parts = [f"[{self.code.name}] {super().__str__()}"]
        if self.context.operation:
            parts.append(f" (during: {self.context.operation})")
        return "".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            "message": str(self.args[0]),
            "code": self.code.name,
            "code_value": self.code.value,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "context": str(self.context),
            "cause": str(self.cause) if self.cause else None,
        }


class ValidationError(HarnessError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.VALIDATION_FAILED,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(
            message,
            code=code,
            severity=ErrorSeverity.LOW,
            context=context,
            recoverable=True,
        )


class ConfigurationError(HarnessError):
    """Raised when configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(
            message,
            code=ErrorCode.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            context=context,
            recoverable=False,
        )


class ExecutionError(HarnessError):
    """Raised when command execution fails."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.EXECUTION_FAILED,
        context: Optional[ErrorContext] = None,
        recoverable: bool = True,
    ):
        super().__init__(
            message,
            code=code,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            recoverable=recoverable,
        )


class SafetyError(HarnessError):
    """Raised when a safety check fails."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.SAFETY_VIOLATION,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(
            message,
            code=code,
            severity=ErrorSeverity.HIGH,
            context=context,
            recoverable=False,
        )


class ServiceError(HarnessError):
    """Raised when an external service (Ollama, Claude) fails."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.OLLAMA_ERROR,
        context: Optional[ErrorContext] = None,
        recoverable: bool = True,
    ):
        super().__init__(
            message,
            code=code,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            recoverable=recoverable,
        )


def format_error_for_user(error: Exception) -> str:
    """
    Format an error for user-friendly display.

    Args:
        error: The exception to format

    Returns:
        User-friendly error message
    """
    if isinstance(error, HarnessError):
        base_msg = str(error.args[0])

        if error.code == ErrorCode.VALIDATION_FAILED:
            return f"Input error: {base_msg}"
        elif error.code == ErrorCode.OLLAMA_NOT_FOUND:
            return "Ollama is not installed. Please install from https://ollama.ai"
        elif error.code == ErrorCode.CLAUDE_AUTH_ERROR:
            return "Claude API authentication failed. Check your ANTHROPIC_API_KEY."
        elif error.code == ErrorCode.COMMAND_TIMEOUT:
            return f"Command timed out: {base_msg}"
        elif error.code == ErrorCode.SANDBOX_VIOLATION:
            return f"Security error: {base_msg}"
        elif error.code == ErrorCode.DANGEROUS_OPERATION:
            return f"Blocked: {base_msg}"
        else:
            return base_msg

    return f"Unexpected error: {error}"


def format_error_for_log(error: Exception) -> dict[str, Any]:
    """
    Format an error for structured logging.

    Args:
        error: The exception to format

    Returns:
        Dictionary suitable for structured logging
    """
    if isinstance(error, HarnessError):
        return error.to_dict()

    return {
        "message": str(error),
        "type": type(error).__name__,
        "code": ErrorCode.UNKNOWN.name,
        "code_value": ErrorCode.UNKNOWN.value,
        "severity": ErrorSeverity.MEDIUM.value,
        "recoverable": False,
    }


def is_recoverable(error: Exception) -> bool:
    """
    Check if an error is recoverable.

    Args:
        error: The exception to check

    Returns:
        True if the error can potentially be recovered from
    """
    if isinstance(error, HarnessError):
        return error.recoverable

    # Default: assume standard exceptions are not recoverable
    return False


def get_recovery_suggestion(error: Exception) -> Optional[str]:
    """
    Get a suggested recovery action for an error.

    Args:
        error: The exception to get suggestion for

    Returns:
        Suggested recovery action or None
    """
    if isinstance(error, HarnessError):
        code = error.code

        suggestions = {
            ErrorCode.VALIDATION_FAILED: "Check your input and try again.",
            ErrorCode.INVALID_PATH: "Ensure the path exists and is accessible.",
            ErrorCode.SHELL_INJECTION: "Remove shell special characters from input.",
            ErrorCode.OLLAMA_NOT_FOUND: "Install Ollama: https://ollama.ai",
            ErrorCode.OLLAMA_TIMEOUT: "Check if Ollama service is running.",
            ErrorCode.CLAUDE_AUTH_ERROR: "Set ANTHROPIC_API_KEY environment variable.",
            ErrorCode.COMMAND_TIMEOUT: "Increase timeout or simplify the command.",
            ErrorCode.PERMISSION_DENIED: "Check file/directory permissions.",
            ErrorCode.SANDBOX_VIOLATION: "Ensure all paths are within the sandbox.",
            ErrorCode.DANGEROUS_OPERATION: "This operation requires user approval.",
        }

        return suggestions.get(code)

    return None


def wrap_exception(
    error: Exception,
    operation: str,
    code: Optional[ErrorCode] = None,
) -> HarnessError:
    """
    Wrap a standard exception in a HarnessError.

    Args:
        error: The original exception
        operation: Description of the operation that failed
        code: Optional error code override

    Returns:
        HarnessError wrapping the original exception
    """
    if isinstance(error, HarnessError):
        # Already a HarnessError, just add context
        if not error.context.operation:
            error.context.operation = operation
        return error

    # Determine appropriate error code
    if code is None:
        if isinstance(error, FileNotFoundError):
            code = ErrorCode.FILE_NOT_FOUND
        elif isinstance(error, PermissionError):
            code = ErrorCode.PERMISSION_DENIED
        elif isinstance(error, TimeoutError):
            code = ErrorCode.COMMAND_TIMEOUT
        elif isinstance(error, ValueError):
            code = ErrorCode.INVALID_INPUT
        else:
            code = ErrorCode.UNKNOWN

    return HarnessError(
        str(error),
        code=code,
        context=ErrorContext(operation=operation),
        cause=error,
    )
