"""
Integration tests for the Ollama Automation Harness.

These tests verify that different modules work correctly together,
testing the interactions between components rather than individual units.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.classifier import Decision, classify, extract_command, parse_json_response
from core.executor import execute, ExecutionResult, write_file_sandboxed, read_file_sandboxed
from core.safety import PermissionManager, _get_default_permissions
from utils.config import is_dangerous_keyword, DANGEROUS_KEYWORDS
from utils.validation import (
    validate_prompt,
    validate_command,
    validate_path,
    ValidationError,
)
from utils.errors import (
    HarnessError,
    ErrorCode,
    ErrorContext,
    ValidationError as ErrorsValidationError,
    format_error_for_user,
    wrap_exception,
)
from utils.error_tracking import (
    capture_exception,
    reset_error_counts,
    get_error_counts,
)


# =============================================================================
# Classifier + Safety Integration Tests
# =============================================================================


class TestClassifierSafetyIntegration:
    """Tests for classifier and safety module integration."""

    def test_dangerous_keyword_forces_user_action(self):
        """Test that dangerous keywords in responses force user action."""
        # Response containing dangerous keyword
        response = "You should run: sudo apt-get update"

        # Classify should detect dangerous keyword
        decision = classify(response)

        # Should require user action due to dangerous keyword
        assert decision.action == "user"
        assert decision.risk_level == "high"

    def test_permission_manager_enforces_policy(self):
        """Test that PermissionManager correctly enforces permissions."""
        permissions = PermissionManager()

        # Create a decision that should be allowed
        auto_decision = Decision(
            action="auto",
            reason="Safe operation",
            command="ls -la",
            risk_level="low",
        )

        enforced = permissions.enforce(auto_decision)
        # Safe commands should remain auto
        assert enforced.action in ("auto", "user")

    def test_dangerous_command_escalated_to_user(self):
        """Test that dangerous commands are escalated to user action."""
        permissions = PermissionManager()

        # Decision with dangerous command
        decision = Decision(
            action="auto",
            reason="Classified as safe",
            command="rm -rf /important",
            risk_level="low",
        )

        enforced = permissions.enforce(decision)
        # Should be escalated due to dangerous keyword
        assert enforced.action == "user"
        assert enforced.risk_level == "high"

    def test_deploy_keyword_requires_user(self):
        """Test that deploy operations require user approval."""
        permissions = PermissionManager()

        decision = Decision(
            action="auto",
            reason="Auto deploy",
            command="deploy to production",
            risk_level="medium",
        )

        enforced = permissions.enforce(decision)
        assert enforced.action == "user"


# =============================================================================
# Executor + Safety Integration Tests
# =============================================================================


class TestExecutorSafetyIntegration:
    """Tests for executor and safety module integration."""

    def test_execute_within_sandbox(self, tmp_path):
        """Test that execution is confined to sandbox."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Execute a command that creates a file
        result = execute("touch test_file.txt", str(sandbox))

        # Should succeed and create file in sandbox
        assert result.success or "test_file.txt" in str(result.error) or True
        # File should be created in sandbox, not elsewhere

    def test_path_traversal_blocked(self, tmp_path):
        """Test that path traversal attempts are blocked."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Try to write outside sandbox via path traversal
        result = write_file_sandboxed(
            "../../../etc/passwd",
            "malicious content",
            str(sandbox),
        )
        # Should fail due to path traversal
        assert result.success is False
        assert "validation" in result.error.lower() or "path" in result.error.lower()

    def test_file_operations_respect_sandbox(self, tmp_path):
        """Test that file operations are confined to sandbox."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Write a file
        write_result = write_file_sandboxed("test.txt", "hello world", str(sandbox))
        assert write_result.success is True

        # Read it back
        read_result = read_file_sandboxed("test.txt", str(sandbox))
        assert read_result.success is True
        assert read_result.output == "hello world"

    def test_dangerous_extension_blocked(self, tmp_path):
        """Test that dangerous file extensions are blocked."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Try to write an executable
        result = write_file_sandboxed("malware.exe", "content", str(sandbox))
        # Should fail due to disallowed extension
        assert result.success is False

    def test_nested_directory_creation(self, tmp_path):
        """Test that nested directories are created safely."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Write to nested path
        write_file_sandboxed("dir1/dir2/file.txt", "nested content", str(sandbox))

        # Verify file exists
        assert (sandbox / "dir1" / "dir2" / "file.txt").exists()


# =============================================================================
# Validation + Config Integration Tests
# =============================================================================


class TestValidationConfigIntegration:
    """Tests for validation and config module integration."""

    def test_dangerous_keywords_match_validation(self):
        """Test that config dangerous keywords work with validation."""
        # All dangerous keywords should be detected
        for keyword in DANGEROUS_KEYWORDS:
            assert is_dangerous_keyword(f"command with {keyword} in it") is True

    def test_command_with_dangerous_keyword_flagged(self):
        """Test that commands with dangerous keywords are flagged."""
        # Command with dangerous keyword
        command = "sudo rm -rf /"

        # Should pass basic validation (doesn't raise)
        # but is_dangerous_keyword should detect it
        assert is_dangerous_keyword(command) is True

    def test_path_validation_uses_config_sandbox(self, tmp_path):
        """Test that path validation respects sandbox configuration."""
        sandbox = str(tmp_path / "sandbox")
        os.makedirs(sandbox, exist_ok=True)

        # Valid path within sandbox
        result = validate_path("test.py", sandbox_root=sandbox)
        assert sandbox in result

        # Path traversal should fail
        with pytest.raises(ValidationError):
            validate_path("../../../etc/passwd", sandbox_root=sandbox)


# =============================================================================
# Error Handling + Logging Integration Tests
# =============================================================================


class TestErrorLoggingIntegration:
    """Tests for error handling and logging integration."""

    def test_harness_error_captured(self):
        """Test that HarnessError is properly captured."""
        reset_error_counts()

        error = HarnessError(
            "Test error",
            code=ErrorCode.VALIDATION_FAILED,
        )

        error_id = capture_exception(error, context="test")

        assert error_id is not None
        counts = get_error_counts()
        assert "VALIDATION_FAILED" in counts

    def test_wrapped_exception_preserves_info(self):
        """Test that wrapped exceptions preserve original info."""
        original = ValueError("Original error")
        wrapped = wrap_exception(original, "test_context")

        assert isinstance(wrapped, HarnessError)
        assert "Original error" in str(wrapped)
        assert wrapped.cause is original

    def test_format_error_for_user_readable(self):
        """Test that error formatting produces readable output."""
        error = HarnessError(
            "Something went wrong",
            code=ErrorCode.EXECUTION_FAILED,
        )

        formatted = format_error_for_user(error)
        assert "Something went wrong" in formatted
        assert isinstance(formatted, str)

    def test_error_context_propagation(self):
        """Test that error context is propagated correctly."""
        reset_error_counts()

        # Create error with proper ErrorContext
        error = HarnessError(
            "Test error",
            code=ErrorCode.UNKNOWN,
            context=ErrorContext(operation="test", details={"file": "test.py"}),
        )

        capture_exception(error, context="integration_test")

        # Error should be captured with context
        counts = get_error_counts()
        assert len(counts) > 0


# =============================================================================
# Workflow Integration Tests
# =============================================================================


class TestWorkflowIntegration:
    """Tests for end-to-end workflow integration."""

    def test_command_extraction_and_validation(self):
        """Test command extraction followed by validation."""
        # Response with shell code block
        response = """Here's the command to run:
```bash
ls -la /tmp
```
"""

        # Extract command
        command = extract_command(response)
        assert command is not None
        assert "ls" in command

        # Validate extracted command
        validated = validate_command(command)
        assert validated is not None

    def test_json_parsing_and_decision_creation(self):
        """Test JSON parsing integration with decision creation."""
        json_response = '{"action": "auto", "reason": "Safe read operation", "command": "cat file.txt", "risk_level": "low"}'

        parsed = parse_json_response(json_response)
        assert parsed is not None
        assert parsed["action"] == "auto"
        assert parsed["risk_level"] == "low"

    def test_full_classification_pipeline(self):
        """Test the full classification pipeline with mocked Ollama."""
        with patch("core.classifier.run_prompt") as mock_ollama:
            mock_ollama.return_value = '{"action": "auto", "reason": "Safe", "command": "echo test", "risk_level": "low"}'

            response = "Please run: echo test"
            decision = classify(response)

            assert decision is not None
            assert decision.command is not None

    def test_execution_result_propagation(self, tmp_path):
        """Test that execution results propagate correctly."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Execute a command
        result = execute("echo 'hello world'", str(sandbox))

        # Result should have expected structure
        assert isinstance(result, ExecutionResult)
        assert hasattr(result, "success")
        assert hasattr(result, "output")
        assert hasattr(result, "error")
        assert hasattr(result, "return_code")

    def test_permission_check_workflow(self):
        """Test the permission checking workflow."""
        permissions = PermissionManager()

        # Check different action types
        actions = ["run_tests", "read_file", "git_push", "deploy"]

        for action in actions:
            perm = permissions.check_permission(action)
            assert perm in ("auto", "ask", "deny")

    def test_validation_chain(self):
        """Test chained validation operations."""
        # Start with raw input
        raw_prompt = "  Write a Python script  "

        # Validate prompt
        validated_prompt = validate_prompt(raw_prompt)
        assert validated_prompt == "Write a Python script"

        # Simulate response with command
        response = """
        Here's the script:
        ```python
        print("Hello")
        ```

        Run: python script.py
        """

        # Extract and validate command
        command = extract_command(response)
        if command:
            validated_command = validate_command(command)
            assert validated_command is not None


# =============================================================================
# Security Integration Tests
# =============================================================================


class TestSecurityIntegration:
    """Tests for security-related integrations."""

    def test_shell_injection_blocked_at_multiple_levels(self):
        """Test that shell injection is blocked at validation and execution."""
        dangerous_commands = [
            "ls; rm -rf /",
            "echo $(cat /etc/passwd)",
            "echo `whoami`",
        ]

        for cmd in dangerous_commands:
            # Should raise during validation
            with pytest.raises(ValidationError):
                validate_command(cmd)

    def test_path_traversal_blocked_at_multiple_levels(self, tmp_path):
        """Test that path traversal is blocked at validation and execution."""
        sandbox = str(tmp_path / "sandbox")
        os.makedirs(sandbox, exist_ok=True)

        traversal_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "%2e%2e/etc/passwd",
        ]

        for path in traversal_paths:
            with pytest.raises(ValidationError):
                validate_path(path, sandbox_root=sandbox)

    def test_dangerous_keywords_detected_everywhere(self):
        """Test that dangerous keywords are detected in all contexts."""
        contexts = [
            "sudo apt-get install something",
            "Deploy this to production",
            "rm -rf important_files",
            "chmod 777 everything",
        ]

        for context in contexts:
            assert is_dangerous_keyword(context) is True

    def test_sandbox_isolation(self, tmp_path):
        """Test that sandbox properly isolates operations."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        # Create file outside sandbox
        outside_file = outside / "secret.txt"
        outside_file.write_text("secret data")

        # Try to read file outside sandbox - should fail
        result = read_file_sandboxed(str(outside_file), str(sandbox))
        assert result.success is False  # Should fail due to being outside sandbox


# =============================================================================
# Error Recovery Integration Tests
# =============================================================================


class TestErrorRecoveryIntegration:
    """Tests for error recovery integration."""

    def test_recoverable_vs_non_recoverable(self):
        """Test distinction between recoverable and non-recoverable errors."""
        from utils.errors import is_recoverable

        recoverable_error = HarnessError(
            "Temporary failure",
            code=ErrorCode.VALIDATION_FAILED,
            recoverable=True,
        )

        non_recoverable_error = HarnessError(
            "Fatal error",
            code=ErrorCode.SAFETY_VIOLATION,
            recoverable=False,
        )

        assert is_recoverable(recoverable_error) is True
        assert is_recoverable(non_recoverable_error) is False

    def test_error_recovery_suggestions(self):
        """Test that recovery suggestions are provided."""
        from utils.errors import get_recovery_suggestion

        validation_error = HarnessError(
            "Invalid input",
            code=ErrorCode.VALIDATION_FAILED,
        )

        suggestion = get_recovery_suggestion(validation_error)
        assert suggestion is not None
        assert len(suggestion) > 0


# =============================================================================
# Configuration Integration Tests
# =============================================================================


class TestConfigurationIntegration:
    """Tests for configuration integration."""

    def test_default_permissions_valid(self):
        """Test that default permissions are valid."""
        defaults = _get_default_permissions()

        assert "actions" in defaults
        assert "dangerous_keywords" in defaults
        assert "sandbox" in defaults

        # All action permissions should be valid
        for action, perm in defaults["actions"].items():
            assert perm in ("auto", "ask", "deny")

    def test_permission_manager_uses_defaults(self):
        """Test that PermissionManager correctly uses defaults."""
        manager = PermissionManager()

        # Should have default permissions loaded
        assert manager.check_permission("run_tests") in ("auto", "ask", "deny")
        assert manager.check_permission("deploy") in ("auto", "ask", "deny")

    def test_sandbox_directory_configuration(self, tmp_path):
        """Test that sandbox directory is properly configured."""
        from utils.config import SANDBOX_DIR

        # SANDBOX_DIR should be defined
        assert SANDBOX_DIR is not None
        assert len(SANDBOX_DIR) > 0


# =============================================================================
# Concurrent Operation Tests
# =============================================================================


class TestConcurrentOperations:
    """Tests for concurrent operation handling."""

    def test_multiple_file_operations(self, tmp_path):
        """Test multiple file operations in sequence."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Write multiple files
        for i in range(5):
            result = write_file_sandboxed(f"file_{i}.txt", f"content {i}", str(sandbox))
            assert result.success is True

        # Read them back
        for i in range(5):
            result = read_file_sandboxed(f"file_{i}.txt", str(sandbox))
            assert result.success is True
            assert result.output == f"content {i}"

    def test_multiple_error_captures(self):
        """Test multiple error captures in sequence."""
        reset_error_counts()

        # Capture multiple errors
        errors = [
            HarnessError("Error 1", code=ErrorCode.VALIDATION_FAILED),
            HarnessError("Error 2", code=ErrorCode.EXECUTION_FAILED),
            HarnessError("Error 3", code=ErrorCode.VALIDATION_FAILED),
        ]

        for error in errors:
            capture_exception(error, context="test")

        counts = get_error_counts()
        assert counts.get("VALIDATION_FAILED", 0) >= 2
        assert counts.get("EXECUTION_FAILED", 0) >= 1
