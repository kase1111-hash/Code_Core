"""
Logging utilities for audit trail and error logging.

This module provides structured logging for all automation actions
with timestamps, decision details, and execution results.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.classifier import Decision
    from core.executor import ExecutionResult

LOG_FILE = "logs/automation.log"
LOG_FORMAT = "[{timestamp}] ACTION={action_type} DECISION={decision} RISK={risk} COMMAND=\"{command}\" RESULT={result}"

# Module-level logger instance
_logger: Optional[logging.Logger] = None


def setup_logger(
    log_file: str = LOG_FILE,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Set up and configure the automation logger.

    Args:
        log_file: Path to log file
        level: Logging level

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

    # File handler for audit trail
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler for immediate feedback
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    _logger = logger
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
