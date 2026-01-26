"""
Sandboxed command execution module.

This module provides safe command execution within a sandbox
directory with path validation and timeout handling.
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from utils.config import (
    COMMAND_TIMEOUT,
    SANDBOX_DIR,
    is_allowed_extension,
)
from utils.validation import (
    ValidationError,
    contains_path_traversal,
    validate_command,
    validate_path,
)


@dataclass
class ExecutionResult:
    """Represents the result of a command execution."""

    success: bool
    output: str
    error: str
    return_code: int


def execute(command: str, sandbox_root: str = SANDBOX_DIR) -> ExecutionResult:
    """
    Execute a command in the sandbox environment.

    Args:
        command: Shell command to execute
        sandbox_root: Root directory for sandboxed execution

    Returns:
        ExecutionResult with success, output, error, return_code
    """
    # Validate command before execution
    try:
        command = validate_command(command)
    except ValidationError as e:
        return ExecutionResult(
            success=False,
            output="",
            error=f"Command validation failed: {e}",
            return_code=-1,
        )

    # Ensure sandbox exists
    sandbox_path = Path(sandbox_root).resolve()
    sandbox_path.mkdir(parents=True, exist_ok=True)

    try:
        # Execute command with sandbox as working directory
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(sandbox_path),
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
            env=_get_safe_env(),
        )

        return ExecutionResult(
            success=result.returncode == 0,
            output=result.stdout,
            error=result.stderr,
            return_code=result.returncode,
        )

    except subprocess.TimeoutExpired:
        return ExecutionResult(
            success=False,
            output="",
            error=f"Command timed out after {COMMAND_TIMEOUT} seconds",
            return_code=-1,
        )

    except subprocess.SubprocessError as e:
        return ExecutionResult(
            success=False,
            output="",
            error=f"Subprocess error: {e}",
            return_code=-1,
        )


def execute_sandboxed(
    command: list[str],
    sandbox_root: str = SANDBOX_DIR,
) -> ExecutionResult:
    """
    Execute command with cwd set to sandbox (shell=False for safety).

    Args:
        command: Command as list of arguments
        sandbox_root: Root directory for sandboxed execution

    Returns:
        ExecutionResult with success, output, error, return_code
    """
    sandbox_path = Path(sandbox_root).resolve()
    sandbox_path.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            command,
            cwd=str(sandbox_path),
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
            env=_get_safe_env(),
        )

        return ExecutionResult(
            success=result.returncode == 0,
            output=result.stdout,
            error=result.stderr,
            return_code=result.returncode,
        )

    except subprocess.TimeoutExpired:
        return ExecutionResult(
            success=False,
            output="",
            error=f"Command timed out after {COMMAND_TIMEOUT} seconds",
            return_code=-1,
        )

    except FileNotFoundError:
        return ExecutionResult(
            success=False,
            output="",
            error=f"Command not found: {command[0] if command else 'empty'}",
            return_code=-1,
        )

    except subprocess.SubprocessError as e:
        return ExecutionResult(
            success=False,
            output="",
            error=f"Subprocess error: {e}",
            return_code=-1,
        )


def write_file_sandboxed(
    path: str,
    content: str,
    sandbox_root: str = SANDBOX_DIR,
) -> ExecutionResult:
    """
    Write file only if path resolves within sandbox.

    Args:
        path: Relative path within sandbox
        content: Content to write
        sandbox_root: Root directory for sandbox

    Returns:
        ExecutionResult indicating success or failure
    """
    if not validate_sandbox_path(path, sandbox_root):
        return ExecutionResult(
            success=False,
            output="",
            error=f"Path validation failed: {path}",
            return_code=-1,
        )

    if not is_allowed_extension(path):
        return ExecutionResult(
            success=False,
            output="",
            error=f"Extension not allowed: {Path(path).suffix}",
            return_code=-1,
        )

    try:
        sandbox_path = Path(sandbox_root).resolve()
        target_path = (sandbox_path / path).resolve()

        # Create parent directories
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        target_path.write_text(content)

        return ExecutionResult(
            success=True,
            output=f"File written: {target_path}",
            error="",
            return_code=0,
        )

    except OSError as e:
        return ExecutionResult(
            success=False,
            output="",
            error=f"Failed to write file: {e}",
            return_code=-1,
        )


def read_file_sandboxed(
    path: str,
    sandbox_root: str = SANDBOX_DIR,
) -> ExecutionResult:
    """
    Read file only if path resolves within sandbox.

    Args:
        path: Relative path within sandbox
        sandbox_root: Root directory for sandbox

    Returns:
        ExecutionResult with file content in output
    """
    if not validate_sandbox_path(path, sandbox_root):
        return ExecutionResult(
            success=False,
            output="",
            error=f"Path validation failed: {path}",
            return_code=-1,
        )

    try:
        sandbox_path = Path(sandbox_root).resolve()
        target_path = (sandbox_path / path).resolve()

        if not target_path.exists():
            return ExecutionResult(
                success=False,
                output="",
                error=f"File not found: {path}",
                return_code=-1,
            )

        content = target_path.read_text()

        return ExecutionResult(
            success=True,
            output=content,
            error="",
            return_code=0,
        )

    except OSError as e:
        return ExecutionResult(
            success=False,
            output="",
            error=f"Failed to read file: {e}",
            return_code=-1,
        )


def validate_sandbox_path(path: str, sandbox_root: str = SANDBOX_DIR) -> bool:
    """
    Validate that path stays within sandbox.

    Args:
        path: Path to validate
        sandbox_root: Root directory for sandbox

    Returns:
        True if path is valid and within sandbox
    """
    # Quick check for path traversal patterns
    if contains_path_traversal(path):
        return False

    try:
        # Use centralized validation
        validate_path(path, sandbox_root=sandbox_root)
        return True
    except ValidationError:
        return False


def _get_safe_env() -> dict[str, str]:
    """
    Get a safe environment for subprocess execution.

    Returns:
        Environment dictionary with limited variables
    """
    safe_env = {}

    # Only include essential environment variables
    # Note: PYTHONPATH is intentionally excluded to prevent loading
    # malicious modules in sandboxed execution
    for key in ["PATH", "HOME", "USER", "LANG", "LC_ALL"]:
        if key in os.environ:
            safe_env[key] = os.environ[key]

    # Set restrictive defaults
    safe_env["PYTHONDONTWRITEBYTECODE"] = "1"

    return safe_env
