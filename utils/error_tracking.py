"""
Error tracking and reporting module.

Provides structured error logging with optional Sentry integration.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from utils.errors import (
    HarnessError,
    format_error_for_log,
)

# Configuration
ERROR_LOG_FILE = "logs/errors.json"
MAX_ERROR_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
ERROR_LOG_BACKUP_COUNT = 10

# Module state
_sentry_initialized = False
_error_logger: logging.Logger | None = None
_error_counts: dict[str, int] = defaultdict(int)
_error_callbacks: list[Callable[[dict[str, Any]], None]] = []


def init_error_tracking(
    sentry_dsn: str | None = None,
    environment: str = "development",
    release: str | None = None,
) -> bool:
    """
    Initialize error tracking systems.

    Args:
        sentry_dsn: Sentry DSN for error reporting (or set SENTRY_DSN env var)
        environment: Environment name (development, staging, production)
        release: Application release/version

    Returns:
        True if initialization succeeded
    """
    global _sentry_initialized

    # Initialize JSON error logger
    _setup_error_logger()

    # Try to initialize Sentry if DSN provided
    dsn = sentry_dsn or os.getenv("SENTRY_DSN")
    if dsn:
        _sentry_initialized = _init_sentry(dsn, environment, release)

    return True


def _setup_error_logger() -> logging.Logger:
    """Set up the JSON error logger for ELK-compatible output."""
    global _error_logger

    if _error_logger is not None:
        return _error_logger

    logger = logging.getLogger("ollama-harness.errors")
    logger.setLevel(logging.ERROR)

    # Ensure log directory exists
    log_path = Path(ERROR_LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Rotating file handler for error logs
    handler = RotatingFileHandler(
        log_path,
        maxBytes=MAX_ERROR_LOG_SIZE,
        backupCount=ERROR_LOG_BACKUP_COUNT,
    )
    handler.setLevel(logging.ERROR)

    # Use a simple formatter - we'll format JSON ourselves
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    _error_logger = logger
    return logger


def _init_sentry(
    dsn: str,
    environment: str,
    release: str | None,
) -> bool:
    """
    Initialize Sentry SDK if available.

    Args:
        dsn: Sentry DSN
        environment: Environment name
        release: Application release

    Returns:
        True if Sentry was initialized successfully
    """
    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR,
        )

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            integrations=[sentry_logging],
            traces_sample_rate=0.1,
            send_default_pii=False,
        )

        return True

    except ImportError:
        # Sentry SDK not installed - that's okay
        return False
    except Exception:
        # Sentry initialization failed
        return False


def capture_exception(
    error: Exception,
    context: str | None = None,
    extra: dict[str, Any] | None = None,
    tags: dict[str, str] | None = None,
) -> str:
    """
    Capture and log an exception.

    Args:
        error: The exception to capture
        context: Context description (what was happening)
        extra: Additional data to include
        tags: Optional tags for categorization

    Returns:
        Error ID for reference
    """
    # Generate error ID
    error_id = _generate_error_id()

    # Build error record
    error_record = _build_error_record(
        error=error,
        error_id=error_id,
        context=context,
        extra=extra,
        tags=tags,
    )

    # Log to JSON file (ELK-compatible)
    _log_error_json(error_record)

    # Update error counts
    error_code = error_record.get("error_code", "UNKNOWN")
    _error_counts[error_code] += 1

    # Send to Sentry if available
    if _sentry_initialized:
        _send_to_sentry(error, error_record)

    # Call registered callbacks
    for callback in _error_callbacks:
        try:
            callback(error_record)
        except Exception:
            pass  # Don't let callbacks break error handling

    return error_id


def capture_message(
    message: str,
    level: str = "error",
    context: str | None = None,
    extra: dict[str, Any] | None = None,
    tags: dict[str, str] | None = None,
) -> str:
    """
    Capture and log an error message (without exception).

    Args:
        message: Error message
        level: Severity level (error, warning, info)
        context: Context description
        extra: Additional data
        tags: Optional tags

    Returns:
        Error ID for reference
    """
    error_id = _generate_error_id()

    record = {
        "@timestamp": datetime.utcnow().isoformat() + "Z",
        "error_id": error_id,
        "level": level,
        "message": message,
        "context": context,
        "extra": extra or {},
        "tags": tags or {},
        "environment": os.getenv("ENVIRONMENT", "development"),
    }

    _log_error_json(record)

    if _sentry_initialized:
        try:
            import sentry_sdk
            sentry_sdk.capture_message(message, level=level)
        except Exception:
            pass

    return error_id


def _build_error_record(
    error: Exception,
    error_id: str,
    context: str | None = None,
    extra: dict[str, Any] | None = None,
    tags: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a structured error record for logging."""

    # Get error details
    if isinstance(error, HarnessError):
        error_data = format_error_for_log(error)
        error_code = error.code.name
        severity = error.severity.value
    else:
        error_data = {
            "message": str(error),
            "type": type(error).__name__,
        }
        error_code = "UNKNOWN"
        severity = "medium"

    # Build stack trace
    tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
    stack_trace = "".join(tb_lines)

    # Extract frame info
    frames = _extract_stack_frames(error)

    record = {
        "@timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "ERROR",
        "logger": "ollama-harness",
        "error_id": error_id,
        "error_code": error_code,
        "error_type": type(error).__name__,
        "error_message": str(error)[:1000],
        "severity": severity,
        "tags": tags or {},
        "context": context,
        "extra": _sanitize_extra(extra or {}),
        "stack_trace": stack_trace,
        "frames": frames,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "python_version": sys.version,
        "error_data": error_data,
    }

    return record


def _extract_stack_frames(error: Exception) -> list[dict[str, Any]]:
    """Extract structured stack frame information."""
    frames = []

    tb = error.__traceback__
    while tb is not None:
        frame = tb.tb_frame
        frames.append({
            "filename": frame.f_code.co_filename,
            "function": frame.f_code.co_name,
            "lineno": tb.tb_lineno,
            "locals": _safe_locals(frame.f_locals),
        })
        tb = tb.tb_next

    return frames


def _safe_locals(local_vars: dict[str, Any]) -> dict[str, str]:
    """Safely convert local variables to strings."""
    safe = {}
    for key, value in local_vars.items():
        if key.startswith("_"):
            continue
        try:
            str_val = repr(value)[:200]
            safe[key] = str_val
        except Exception:
            safe[key] = "<unrepresentable>"
    return safe


def _sanitize_extra(extra: dict[str, Any]) -> dict[str, Any]:
    """Sanitize extra data, removing sensitive information."""
    sensitive_keys = {
        "password", "passwd", "pwd", "secret", "token", "key",
        "api_key", "apikey", "authorization", "auth", "credential",
    }

    sanitized = {}
    for key, value in extra.items():
        key_lower = key.lower()
        if any(s in key_lower for s in sensitive_keys):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_extra(value)
        else:
            try:
                sanitized[key] = str(value)[:500]
            except Exception:
                sanitized[key] = "<unserializable>"

    return sanitized


def _log_error_json(record: dict[str, Any]) -> None:
    """Log error record as JSON line."""
    logger = _setup_error_logger()

    try:
        json_line = json.dumps(record, default=str)
        logger.error(json_line)
    except Exception:
        # Fallback to basic logging
        logger.error(f"Error logging failed: {record.get('error_message', 'unknown')}")


def _send_to_sentry(error: Exception, record: dict[str, Any]) -> None:
    """Send error to Sentry."""
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            # Add tags
            for key, value in record.get("tags", {}).items():
                scope.set_tag(key, value)

            # Add context
            scope.set_context("error_details", {
                "error_id": record.get("error_id"),
                "error_code": record.get("error_code"),
                "context": record.get("context"),
            })

            # Add extra data
            for key, value in record.get("extra", {}).items():
                scope.set_extra(key, value)

            sentry_sdk.capture_exception(error)

    except Exception:
        pass  # Don't break on Sentry errors


def _generate_error_id() -> str:
    """Generate a unique error ID."""
    import uuid
    return f"err_{uuid.uuid4().hex[:12]}"


# =============================================================================
# Error statistics and aggregation
# =============================================================================


def get_error_counts() -> dict[str, int]:
    """
    Get error counts by error code.

    Returns:
        Dictionary mapping error codes to counts
    """
    return dict(_error_counts)


def get_error_summary() -> dict[str, Any]:
    """
    Get a summary of errors.

    Returns:
        Summary dictionary with counts and top errors
    """
    total = sum(_error_counts.values())
    top_errors = sorted(
        _error_counts.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    return {
        "total_errors": total,
        "unique_error_codes": len(_error_counts),
        "top_errors": dict(top_errors),
        "sentry_enabled": _sentry_initialized,
    }


def reset_error_counts() -> None:
    """Reset error counters."""
    global _error_counts
    _error_counts = defaultdict(int)


# =============================================================================
# Callback registration
# =============================================================================


def register_error_callback(callback: Callable[[dict[str, Any]], None]) -> None:
    """
    Register a callback to be called on each error.

    Args:
        callback: Function that receives error record dict
    """
    _error_callbacks.append(callback)


def unregister_error_callback(callback: Callable[[dict[str, Any]], None]) -> None:
    """
    Unregister an error callback.

    Args:
        callback: Previously registered callback
    """
    if callback in _error_callbacks:
        _error_callbacks.remove(callback)


# =============================================================================
# Context manager for error tracking
# =============================================================================


class error_context:
    """
    Context manager for capturing errors in a block.

    Usage:
        with error_context("processing_prompt", extra={"prompt_id": "123"}):
            process_prompt(prompt)
    """

    def __init__(
        self,
        context: str,
        extra: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
        reraise: bool = True,
    ):
        self.context = context
        self.extra = extra
        self.tags = tags
        self.reraise = reraise
        self.error_id: str | None = None

    def __enter__(self) -> error_context:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_val is not None:
            self.error_id = capture_exception(
                exc_val,
                context=self.context,
                extra=self.extra,
                tags=self.tags,
            )
            return not self.reraise
        return False


# =============================================================================
# Decorator for automatic error capture
# =============================================================================


def capture_errors(
    context: str | None = None,
    reraise: bool = True,
):
    """
    Decorator to automatically capture errors from a function.

    Args:
        context: Context description (defaults to function name)
        reraise: Whether to re-raise the exception after capturing

    Usage:
        @capture_errors(context="user_authentication")
        def authenticate_user(username, password):
            ...
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            ctx = context or func.__name__
            try:
                return func(*args, **kwargs)
            except Exception as e:
                capture_exception(e, context=ctx)
                if reraise:
                    raise
                return None
        return wrapper
    return decorator
