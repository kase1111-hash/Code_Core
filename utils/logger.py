"""
Logging utilities for audit trail and general application logging.

This module provides structured logging for all automation actions
with timestamps, decision details, execution results, and performance metrics.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator, Optional

if TYPE_CHECKING:
    from core.classifier import Decision
    from core.executor import ExecutionResult

# Default configuration
LOG_DIR = "logs"
LOG_FILE = "logs/automation.log"
DEBUG_LOG_FILE = "logs/debug.log"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

# Log format templates
LOG_FORMAT = "[{timestamp}] ACTION={action_type} DECISION={decision} RISK={risk} COMMAND=\"{command}\" RESULT={result}"
CONSOLE_FORMAT = "%(levelname)s: %(message)s"
FILE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
JSON_FORMAT = True  # Enable JSON structured logging

# Module-level logger instances
_logger: Optional[logging.Logger] = None
_debug_logger: Optional[logging.Logger] = None


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logger(
    log_file: str = LOG_FILE,
    level: int = logging.INFO,
    enable_console: bool = True,
    enable_json: bool = False,
    enable_rotation: bool = True,
) -> logging.Logger:
    """
    Set up and configure the automation logger.

    Args:
        log_file: Path to log file
        level: Logging level
        enable_console: Enable console output
        enable_json: Enable JSON structured logging
        enable_rotation: Enable log file rotation

    Returns:
        Configured logger instance
    """
    global _logger

    if _logger is not None:
        return _logger

    # Create logger
    logger = logging.getLogger("ollama-harness")
    logger.setLevel(level)

    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # File handler with optional rotation
    if enable_rotation:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
        )
    else:
        file_handler = logging.FileHandler(log_path)

    file_handler.setLevel(level)

    if enable_json:
        file_handler.setFormatter(JsonFormatter())
    else:
        file_handler.setFormatter(logging.Formatter(
            FILE_FORMAT,
            datefmt="%Y-%m-%dT%H:%M:%S",
        ))

    logger.addHandler(file_handler)

    # Console handler for immediate feedback
    if enable_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
        logger.addHandler(console_handler)

    _logger = logger
    return logger


def setup_debug_logger(
    log_file: str = DEBUG_LOG_FILE,
) -> logging.Logger:
    """
    Set up a separate debug logger for detailed debugging.

    Args:
        log_file: Path to debug log file

    Returns:
        Configured debug logger instance
    """
    global _debug_logger

    if _debug_logger is not None:
        return _debug_logger

    logger = logging.getLogger("ollama-harness.debug")
    logger.setLevel(logging.DEBUG)

    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Rotating file handler for debug logs
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    logger.addHandler(file_handler)

    _debug_logger = logger
    return logger


def get_logger() -> logging.Logger:
    """
    Get the current logger instance.

    Returns:
        Logger instance (creates one if not exists)
    """
    if _logger is None:
        return setup_logger()
    return _logger


def get_debug_logger() -> logging.Logger:
    """
    Get the debug logger instance.

    Returns:
        Debug logger instance (creates one if not exists)
    """
    if _debug_logger is None:
        return setup_debug_logger()
    return _debug_logger


# =============================================================================
# Core logging functions
# =============================================================================


def log_action(
    action_type: str,
    decision: Decision,
    result: ExecutionResult,
    user_input: Optional[str] = None,
) -> None:
    """
    Log an automation action with full context.

    Args:
        action_type: Type of action performed
        decision: Decision object from classifier
        result: ExecutionResult from executor
        user_input: Optional user input for user-approved actions
    """
    logger = get_logger()

    # Format the log message
    timestamp = datetime.now().isoformat()
    command = (decision.command or "").replace('"', '\\"')
    result_status = "success" if result.success else "failure"

    message = LOG_FORMAT.format(
        timestamp=timestamp,
        action_type=action_type,
        decision=decision.action,
        risk=decision.risk_level,
        command=command[:100],  # Truncate long commands
        result=result_status,
    )

    # Add user input if present
    if user_input:
        message += f" USER_INPUT=\"{user_input}\""

    # Add error details if present
    if result.error:
        message += f" ERROR=\"{result.error[:200]}\""

    logger.info(message)


def log_error(error: Exception, context: str) -> None:
    """
    Log an error with context information.

    Args:
        error: Exception that occurred
        context: Description of what was happening
    """
    logger = get_logger()

    timestamp = datetime.now().isoformat()
    error_type = type(error).__name__
    error_msg = str(error).replace('"', '\\"')[:500]

    message = (
        f"[{timestamp}] ERROR type={error_type} "
        f"context=\"{context}\" message=\"{error_msg}\""
    )

    logger.error(message, exc_info=True)


# =============================================================================
# Application lifecycle logging
# =============================================================================


def log_startup() -> None:
    """Log application startup."""
    logger = get_logger()
    logger.info(
        f"[{datetime.now().isoformat()}] "
        "Ollama Automation Harness started"
    )


def log_shutdown(reason: str = "normal") -> None:
    """
    Log application shutdown.

    Args:
        reason: Reason for shutdown
    """
    logger = get_logger()
    logger.info(
        f"[{datetime.now().isoformat()}] "
        f"Ollama Automation Harness stopped reason=\"{reason}\""
    )


def log_config_loaded(config_path: str, config_data: dict[str, Any]) -> None:
    """
    Log configuration loading.

    Args:
        config_path: Path to configuration file
        config_data: Configuration data (sensitive values will be masked)
    """
    logger = get_logger()

    # Mask sensitive values
    safe_config = _mask_sensitive_data(config_data)

    logger.info(
        f"[{datetime.now().isoformat()}] "
        f"CONFIG_LOADED path=\"{config_path}\" "
        f"keys={list(safe_config.keys())}"
    )


# =============================================================================
# User interaction logging
# =============================================================================


def log_user_decision(decision: Decision, user_choice: str) -> None:
    """
    Log user's decision on a prompted action.

    Args:
        decision: Decision that was presented to user
        user_choice: User's choice (y/m/s/q)
    """
    logger = get_logger()

    choice_map = {
        "y": "approved",
        "m": "modified",
        "s": "skipped",
        "q": "quit",
    }
    choice_text = choice_map.get(user_choice.lower(), user_choice)

    command = (decision.command or "").replace('"', '\\"')[:100]

    logger.info(
        f"[{datetime.now().isoformat()}] "
        f"USER_DECISION choice={choice_text} "
        f"risk={decision.risk_level} "
        f"command=\"{command}\""
    )


def log_prompt_received(prompt: str) -> None:
    """
    Log receipt of a user prompt.

    Args:
        prompt: User's prompt text
    """
    logger = get_logger()
    truncated = prompt[:100] + "..." if len(prompt) > 100 else prompt
    truncated = truncated.replace('"', '\\"').replace("\n", "\\n")

    logger.info(
        f"[{datetime.now().isoformat()}] "
        f"PROMPT_RECEIVED length={len(prompt)} "
        f"preview=\"{truncated}\""
    )


# =============================================================================
# API and service logging
# =============================================================================


def log_api_call(
    service: str,
    operation: str,
    success: bool,
    duration_ms: float,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """
    Log an API call to an external service.

    Args:
        service: Service name (e.g., "claude", "ollama")
        operation: Operation performed
        success: Whether the call succeeded
        duration_ms: Duration in milliseconds
        details: Optional additional details
    """
    logger = get_logger()

    status = "success" if success else "failure"

    message = (
        f"[{datetime.now().isoformat()}] "
        f"API_CALL service={service} "
        f"operation={operation} "
        f"status={status} "
        f"duration_ms={duration_ms:.2f}"
    )

    if details:
        safe_details = _mask_sensitive_data(details)
        message += f" details={json.dumps(safe_details)}"

    logger.info(message)


def log_ollama_call(
    model: str,
    prompt_length: int,
    response_length: int,
    duration_ms: float,
    success: bool,
) -> None:
    """
    Log an Ollama API call.

    Args:
        model: Model name
        prompt_length: Length of prompt
        response_length: Length of response
        duration_ms: Duration in milliseconds
        success: Whether the call succeeded
    """
    log_api_call(
        service="ollama",
        operation="run_prompt",
        success=success,
        duration_ms=duration_ms,
        details={
            "model": model,
            "prompt_length": prompt_length,
            "response_length": response_length,
        },
    )


def log_claude_call(
    model: str,
    prompt_length: int,
    response_length: int,
    duration_ms: float,
    success: bool,
    tokens_used: Optional[int] = None,
) -> None:
    """
    Log a Claude API call.

    Args:
        model: Model name
        prompt_length: Length of prompt
        response_length: Length of response
        duration_ms: Duration in milliseconds
        success: Whether the call succeeded
        tokens_used: Optional token count
    """
    details: dict[str, Any] = {
        "model": model,
        "prompt_length": prompt_length,
        "response_length": response_length,
    }
    if tokens_used is not None:
        details["tokens_used"] = tokens_used

    log_api_call(
        service="claude",
        operation="messages_create",
        success=success,
        duration_ms=duration_ms,
        details=details,
    )


# =============================================================================
# Execution logging
# =============================================================================


def log_command_execution(
    command: str,
    sandbox_root: str,
    success: bool,
    return_code: int,
    duration_ms: float,
    output_length: int = 0,
) -> None:
    """
    Log command execution details.

    Args:
        command: Command that was executed
        sandbox_root: Sandbox directory
        success: Whether execution succeeded
        return_code: Command return code
        duration_ms: Duration in milliseconds
        output_length: Length of output
    """
    logger = get_logger()

    safe_command = command.replace('"', '\\"')[:100]
    status = "success" if success else "failure"

    logger.info(
        f"[{datetime.now().isoformat()}] "
        f"COMMAND_EXEC command=\"{safe_command}\" "
        f"sandbox=\"{sandbox_root}\" "
        f"status={status} "
        f"return_code={return_code} "
        f"duration_ms={duration_ms:.2f} "
        f"output_length={output_length}"
    )


def log_file_operation(
    operation: str,
    path: str,
    success: bool,
    size: Optional[int] = None,
) -> None:
    """
    Log a file operation.

    Args:
        operation: Operation type (read, write, delete)
        path: File path
        success: Whether operation succeeded
        size: Optional file size
    """
    logger = get_logger()

    status = "success" if success else "failure"
    message = (
        f"[{datetime.now().isoformat()}] "
        f"FILE_OP operation={operation} "
        f"path=\"{path}\" "
        f"status={status}"
    )

    if size is not None:
        message += f" size={size}"

    logger.info(message)


# =============================================================================
# Security logging
# =============================================================================


def log_security_event(
    event_type: str,
    severity: str,
    description: str,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """
    Log a security-related event.

    Args:
        event_type: Type of security event
        severity: Severity level (low, medium, high, critical)
        description: Description of the event
        details: Optional additional details
    """
    logger = get_logger()

    message = (
        f"[{datetime.now().isoformat()}] "
        f"SECURITY event={event_type} "
        f"severity={severity} "
        f"description=\"{description}\""
    )

    if details:
        safe_details = _mask_sensitive_data(details)
        message += f" details={json.dumps(safe_details)}"

    # Use appropriate log level based on severity
    if severity == "critical":
        logger.critical(message)
    elif severity == "high":
        logger.error(message)
    elif severity == "medium":
        logger.warning(message)
    else:
        logger.info(message)


def log_permission_check(
    action_type: str,
    permission: str,
    command: Optional[str] = None,
) -> None:
    """
    Log a permission check result.

    Args:
        action_type: Type of action being checked
        permission: Permission result (auto, ask, deny)
        command: Optional command being checked
    """
    logger = get_logger()

    message = (
        f"[{datetime.now().isoformat()}] "
        f"PERMISSION_CHECK action={action_type} "
        f"permission={permission}"
    )

    if command:
        safe_command = command.replace('"', '\\"')[:50]
        message += f" command=\"{safe_command}\""

    logger.debug(message)


def log_dangerous_keyword_detected(keyword: str, context: str) -> None:
    """
    Log detection of a dangerous keyword.

    Args:
        keyword: The dangerous keyword detected
        context: Context where it was detected
    """
    log_security_event(
        event_type="dangerous_keyword",
        severity="high",
        description=f"Dangerous keyword '{keyword}' detected",
        details={"keyword": keyword, "context": context[:100]},
    )


# =============================================================================
# Performance logging
# =============================================================================


@contextmanager
def log_operation_timing(
    operation: str,
    details: Optional[dict[str, Any]] = None,
) -> Generator[None, None, None]:
    """
    Context manager for timing and logging operations.

    Args:
        operation: Name of the operation being timed
        details: Optional additional details

    Usage:
        with log_operation_timing("classify_response"):
            result = classify(response)
    """
    logger = get_logger()
    start_time = time.perf_counter()

    try:
        yield
        success = True
    except Exception:
        success = False
        raise
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        status = "success" if success else "failure"

        message = (
            f"[{datetime.now().isoformat()}] "
            f"TIMING operation={operation} "
            f"status={status} "
            f"duration_ms={duration_ms:.2f}"
        )

        if details:
            message += f" details={json.dumps(details)}"

        logger.debug(message)


def log_performance_metric(
    metric_name: str,
    value: float,
    unit: str = "ms",
    tags: Optional[dict[str, str]] = None,
) -> None:
    """
    Log a performance metric.

    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        tags: Optional tags for categorization
    """
    logger = get_logger()

    message = (
        f"[{datetime.now().isoformat()}] "
        f"METRIC name={metric_name} "
        f"value={value:.2f} "
        f"unit={unit}"
    )

    if tags:
        message += f" tags={json.dumps(tags)}"

    logger.debug(message)


# =============================================================================
# Debug logging
# =============================================================================


def log_debug(message: str, data: Optional[dict[str, Any]] = None) -> None:
    """
    Log a debug message with optional structured data.

    Args:
        message: Debug message
        data: Optional structured data
    """
    logger = get_debug_logger()

    if data:
        safe_data = _mask_sensitive_data(data)
        logger.debug(f"{message} | data={json.dumps(safe_data)}")
    else:
        logger.debug(message)


def log_trace(operation: str, step: str, data: Optional[dict[str, Any]] = None) -> None:
    """
    Log a trace message for detailed debugging.

    Args:
        operation: Operation being traced
        step: Current step in the operation
        data: Optional data at this step
    """
    logger = get_debug_logger()

    message = f"TRACE [{operation}] {step}"
    if data:
        safe_data = _mask_sensitive_data(data)
        message += f" | {json.dumps(safe_data)}"

    logger.debug(message)


# =============================================================================
# Helper functions
# =============================================================================


def _mask_sensitive_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Mask sensitive values in a dictionary.

    Args:
        data: Dictionary to mask

    Returns:
        Dictionary with sensitive values masked
    """
    sensitive_keys = {
        "api_key", "apikey", "api-key",
        "password", "passwd", "pwd",
        "secret", "token", "key",
        "authorization", "auth",
        "credential", "credentials",
    }

    masked = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            masked[key] = "***MASKED***"
        elif isinstance(value, dict):
            masked[key] = _mask_sensitive_data(value)
        else:
            masked[key] = value

    return masked


def set_log_level(level: int) -> None:
    """
    Set the logging level for all handlers.

    Args:
        level: Logging level (e.g., logging.DEBUG)
    """
    logger = get_logger()
    logger.setLevel(level)
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.setLevel(level)


def enable_verbose_logging() -> None:
    """Enable verbose (DEBUG level) logging."""
    set_log_level(logging.DEBUG)
    setup_debug_logger()


def get_log_file_path() -> str:
    """
    Get the path to the main log file.

    Returns:
        Path to log file
    """
    return str(Path(LOG_FILE).resolve())
