"""
Input validation and sanitation utilities.

This module provides functions to validate and sanitize all user inputs
and external data to prevent security issues and ensure data integrity.
"""

import re
from pathlib import Path

from utils.config import (
    ALLOWED_EXTENSIONS,
    MAX_REPLY_LENGTH,
    SANDBOX_DIR,
)

# Maximum lengths for various inputs
MAX_PROMPT_LENGTH = 10000
MAX_COMMAND_LENGTH = 1000
MAX_PATH_LENGTH = 500
MAX_CONFIG_VALUE_LENGTH = 1000


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


# =============================================================================
# Prompt Validation
# =============================================================================

def validate_prompt(prompt: str) -> str:
    """
    Validate and sanitize user prompt.

    Args:
        prompt: User input prompt

    Returns:
        Sanitized prompt string

    Raises:
        ValidationError: If prompt is invalid
    """
    if not prompt:
        raise ValidationError("Prompt cannot be empty")

    if not isinstance(prompt, str):
        raise ValidationError("Prompt must be a string")

    # Strip whitespace
    prompt = prompt.strip()

    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ValidationError(
            f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters"
        )

    # Remove null bytes and other control characters (except newlines/tabs)
    prompt = sanitize_string(prompt)

    return prompt


def sanitize_string(text: str, allow_newlines: bool = True) -> str:
    """
    Remove potentially dangerous characters from string.

    Args:
        text: Input string
        allow_newlines: Whether to allow newlines and tabs

    Returns:
        Sanitized string
    """
    if not text:
        return ""

    # Remove null bytes
    text = text.replace("\x00", "")

    # Remove other control characters
    if allow_newlines:
        # Keep newlines, tabs, but remove other control chars
        text = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    else:
        # Remove all control characters
        text = re.sub(r'[\x00-\x1f\x7f]', '', text)

    return text


# =============================================================================
# Command Validation
# =============================================================================

def validate_command(command: str) -> str:
    """
    Validate and sanitize command string.

    Args:
        command: Command to validate

    Returns:
        Validated command string

    Raises:
        ValidationError: If command is invalid
    """
    if not command:
        raise ValidationError("Command cannot be empty")

    if not isinstance(command, str):
        raise ValidationError("Command must be a string")

    command = command.strip()

    if len(command) > MAX_COMMAND_LENGTH:
        raise ValidationError(
            f"Command exceeds maximum length of {MAX_COMMAND_LENGTH} characters"
        )

    # Remove null bytes
    command = command.replace("\x00", "")

    # Check for shell injection patterns
    if contains_shell_injection(command):
        raise ValidationError("Command contains potentially dangerous patterns")

    return command


def contains_shell_injection(command: str) -> bool:
    """
    Check if command contains shell injection patterns.

    Args:
        command: Command string to check

    Returns:
        True if dangerous patterns found
    """
    # Patterns that might indicate shell injection
    dangerous_patterns = [
        r'\$\([^)]+\)',      # Command substitution $(...)
        r'`[^`]+`',          # Backtick command substitution
        r';\s*rm\s',         # Semicolon followed by rm
        r'\|\s*sh\b',        # Pipe to shell
        r'\|\s*bash\b',      # Pipe to bash
        r'>\s*/etc/',        # Redirect to /etc
        r'>\s*/dev/',        # Redirect to /dev
        r'\beval\b',         # eval command
        r'\bexec\b',         # exec command
    ]

    command_lower = command.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, command_lower):
            return True

    return False


def get_command_risk_level(command: str) -> str:
    """
    Assess risk level of a command.

    Args:
        command: Command to assess

    Returns:
        Risk level: "low", "medium", or "high"
    """
    command_lower = command.lower()

    # High risk commands
    high_risk_patterns = [
        r'\brm\s+(-rf?|--recursive)',
        r'\bsudo\b',
        r'\bchmod\b',
        r'\bchown\b',
        r'\bdd\b',
        r'\bmkfs\b',
        r'\bformat\b',
        r'>\s*/dev/',
        r'\bdeploy\b',
        r'\bpush\b.*\b(main|master|prod)',
    ]

    for pattern in high_risk_patterns:
        if re.search(pattern, command_lower):
            return "high"

    # Medium risk commands
    medium_risk_patterns = [
        r'\bgit\s+(push|commit|merge)',
        r'\bnpm\s+publish',
        r'\bpip\s+install',
        r'\bapt\s+install',
        r'\bcurl\b',
        r'\bwget\b',
        r'\brm\b',
        r'\bmv\b',
    ]

    for pattern in medium_risk_patterns:
        if re.search(pattern, command_lower):
            return "medium"

    return "low"


# =============================================================================
# Path Validation
# =============================================================================

def validate_path(
    path: str,
    sandbox_root: str = SANDBOX_DIR,
    must_exist: bool = False,
) -> str:
    """
    Validate and sanitize file path.

    Args:
        path: Path to validate
        sandbox_root: Root directory for sandbox
        must_exist: Whether path must exist

    Returns:
        Validated path string

    Raises:
        ValidationError: If path is invalid
    """
    if not path:
        raise ValidationError("Path cannot be empty")

    if not isinstance(path, str):
        raise ValidationError("Path must be a string")

    path = path.strip()

    if len(path) > MAX_PATH_LENGTH:
        raise ValidationError(
            f"Path exceeds maximum length of {MAX_PATH_LENGTH} characters"
        )

    # Remove null bytes
    path = path.replace("\x00", "")

    # Check for path traversal
    if contains_path_traversal(path):
        raise ValidationError("Path contains traversal patterns")

    # Resolve and validate within sandbox
    try:
        sandbox = Path(sandbox_root).resolve()
        if Path(path).is_absolute():
            target = Path(path).resolve()
        else:
            target = (sandbox / path).resolve()

        # Ensure path is within sandbox
        if not str(target).startswith(str(sandbox)):
            raise ValidationError("Path is outside sandbox directory")

        # Check existence if required
        if must_exist and not target.exists():
            raise ValidationError(f"Path does not exist: {path}")

        return str(target)

    except (ValueError, OSError) as e:
        raise ValidationError(f"Invalid path: {e}") from e


def contains_path_traversal(path: str) -> bool:
    """
    Check if path contains traversal patterns.

    Args:
        path: Path to check

    Returns:
        True if traversal patterns found
    """
    # Normalize path separators
    normalized = path.replace("\\", "/")

    # Check for various traversal patterns
    traversal_patterns = [
        "..",
        "..%2f",
        "..%5c",
        "%2e%2e",
        "....//",
        "..;/",
    ]

    for pattern in traversal_patterns:
        if pattern in normalized.lower():
            return True

    return False


def validate_extension(path: str) -> bool:
    """
    Validate file extension is allowed.

    Args:
        path: File path to check

    Returns:
        True if extension is allowed
    """
    suffix = Path(path).suffix.lower()

    # Allow files without extension
    if not suffix:
        return True

    return suffix in ALLOWED_EXTENSIONS


# =============================================================================
# Configuration Validation
# =============================================================================

def validate_config_value(key: str, value: str) -> str:
    """
    Validate configuration value.

    Args:
        key: Configuration key
        value: Configuration value

    Returns:
        Validated value

    Raises:
        ValidationError: If value is invalid
    """
    if not isinstance(value, str):
        value = str(value)

    value = value.strip()

    if len(value) > MAX_CONFIG_VALUE_LENGTH:
        raise ValidationError(
            f"Config value for '{key}' exceeds maximum length"
        )

    # Remove null bytes
    value = value.replace("\x00", "")

    return value


def validate_permission_level(level: str) -> str:
    """
    Validate permission level string.

    Args:
        level: Permission level

    Returns:
        Validated permission level

    Raises:
        ValidationError: If level is invalid
    """
    valid_levels = {"auto", "ask", "deny"}

    if not level:
        raise ValidationError("Permission level cannot be empty")

    level = level.lower().strip()

    if level not in valid_levels:
        raise ValidationError(
            f"Invalid permission level '{level}'. "
            f"Must be one of: {', '.join(valid_levels)}"
        )

    return level


def validate_risk_level(level: str) -> str:
    """
    Validate risk level string.

    Args:
        level: Risk level

    Returns:
        Validated risk level

    Raises:
        ValidationError: If level is invalid
    """
    valid_levels = {"low", "medium", "high"}

    if not level:
        return "medium"  # Default

    level = level.lower().strip()

    if level not in valid_levels:
        raise ValidationError(
            f"Invalid risk level '{level}'. "
            f"Must be one of: {', '.join(valid_levels)}"
        )

    return level


# =============================================================================
# Response Validation
# =============================================================================

def validate_response(response: str) -> str:
    """
    Validate and sanitize AI response.

    Args:
        response: Response from AI

    Returns:
        Validated response string

    Raises:
        ValidationError: If response is invalid
    """
    if response is None:
        raise ValidationError("Response cannot be None")

    if not isinstance(response, str):
        response = str(response)

    # Remove null bytes
    response = response.replace("\x00", "")

    return response


def truncate_response(response: str, max_length: int = MAX_REPLY_LENGTH) -> str:
    """
    Truncate response to maximum length.

    Args:
        response: Response string
        max_length: Maximum allowed length

    Returns:
        Truncated response
    """
    if len(response) <= max_length:
        return response

    return response[:max_length] + f"\n... (truncated, {len(response)} total)"


# =============================================================================
# User Input Validation
# =============================================================================

def validate_user_choice(choice: str, valid_choices: set[str]) -> str:
    """
    Validate user menu choice.

    Args:
        choice: User's choice
        valid_choices: Set of valid choice strings

    Returns:
        Validated choice

    Raises:
        ValidationError: If choice is invalid
    """
    if not choice:
        raise ValidationError("Choice cannot be empty")

    choice = choice.strip().lower()

    if choice not in valid_choices:
        raise ValidationError(
            f"Invalid choice '{choice}'. "
            f"Must be one of: {', '.join(sorted(valid_choices))}"
        )

    return choice


def sanitize_log_message(message: str) -> str:
    """
    Sanitize message for logging (prevent log injection).

    Args:
        message: Log message

    Returns:
        Sanitized message
    """
    if not message:
        return ""

    # Replace newlines to prevent log injection
    message = message.replace("\n", "\\n")
    message = message.replace("\r", "\\r")

    # Remove null bytes
    message = message.replace("\x00", "")

    # Escape quotes
    message = message.replace('"', '\\"')

    return message
