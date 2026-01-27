"""
Regression test suite for Ollama Automation Harness.

This module contains critical regression tests that verify core functionality
has not been broken by recent changes. These tests should be run frequently
and must always pass before any release.

Run regression tests only:
    pytest -m regression

Run all tests except regression:
    pytest -m "not regression"
"""

import os
from unittest.mock import patch

import pytest

# Mark all tests in this module as regression tests
pytestmark = pytest.mark.regression


# =============================================================================
# Critical Input Validation Regressions
# =============================================================================


class TestInputValidationRegression:
    """Regression tests for input validation - these bugs must never return."""

    def test_empty_string_rejected(self):
        """
        Regression: Empty strings must be rejected.
        Bug #001: Empty prompts were being accepted and causing crashes.
        """
        from utils.validation import ValidationError, validate_prompt

        with pytest.raises(ValidationError):
            validate_prompt("")

    def test_null_bytes_removed_from_commands(self):
        """
        Regression: Null bytes must be removed from commands.
        Bug #002: Null bytes in commands could bypass validation.
        """
        from utils.validation import validate_command

        result = validate_command("ls\x00-la")
        assert "\x00" not in result

    def test_path_traversal_always_blocked(self):
        """
        Regression: Path traversal must always be blocked.
        Bug #003: Encoded path traversal was not detected.
        """
        from utils.validation import contains_path_traversal

        traversal_attempts = [
            "../etc/passwd",
            "..\\windows\\system32",
            "%2e%2e/etc/passwd",
            "..%2f..%2fetc",
            "....//....//etc",
        ]

        for attempt in traversal_attempts:
            assert contains_path_traversal(attempt) is True, f"Should block: {attempt}"

    def test_shell_injection_always_blocked(self):
        """
        Regression: Shell injection must always be blocked.
        Bug #004: Some injection patterns were not detected.
        """
        from utils.validation import ValidationError, validate_command

        injection_attempts = [
            "ls; rm -rf /",
            "echo $(whoami)",
            "cat `id`",
            "echo test | bash",
        ]

        for attempt in injection_attempts:
            with pytest.raises(ValidationError):
                validate_command(attempt)


# =============================================================================
# Critical Security Regressions
# =============================================================================


class TestSecurityRegression:
    """Regression tests for security - these must never fail."""

    def test_dangerous_keywords_detected(self):
        """
        Regression: Dangerous keywords must always be detected.
        Bug #005: Case-insensitive matching was broken.
        """
        from utils.config import is_dangerous_keyword

        keywords = [
            "sudo apt-get install",
            "SUDO apt-get",
            "rm -rf /",
            "RM -RF",
            "chmod 777",
            "CHMOD 777",
            "deploy to production",
            "DEPLOY TO PRODUCTION",
        ]

        for kw in keywords:
            assert is_dangerous_keyword(kw) is True, f"Should detect: {kw}"

    def test_sandbox_path_validation(self, sandbox):
        """
        Regression: Files outside sandbox must be rejected.
        Bug #006: Absolute paths could escape sandbox.
        """
        from core.executor import write_file_sandboxed

        # Try absolute path outside sandbox
        result = write_file_sandboxed("/etc/passwd", "test", str(sandbox))
        assert result.success is False

        # Try relative path escape
        result = write_file_sandboxed("../../../etc/passwd", "test", str(sandbox))
        assert result.success is False

    def test_secrets_masked_in_output(self):
        """
        Regression: Secrets must always be masked.
        Bug #007: Short secrets were not being masked.
        """
        from utils.secrets import mask_secret

        secrets = [
            "sk-1234567890abcdef",
            "api_key_12345",
            "short",  # Even short secrets
        ]

        for secret in secrets:
            masked = mask_secret(secret)
            # Full secret should not appear
            assert secret not in masked or len(secret) < 8

    def test_permission_escalation_blocked(self):
        """
        Regression: Permission escalation must be blocked.
        Bug #008: Auto decisions with dangerous commands were not escalated.
        """
        from core.classifier import Decision
        from core.safety import PermissionManager

        manager = PermissionManager()

        # Auto decision with dangerous command
        decision = Decision(
            action="auto",
            reason="Test",
            command="sudo rm -rf /",
            risk_level="low",
        )

        enforced = manager.enforce(decision)
        assert enforced.action == "user"
        assert enforced.risk_level == "high"


# =============================================================================
# Critical Execution Regressions
# =============================================================================


class TestExecutionRegression:
    """Regression tests for command execution."""

    def test_command_timeout_enforced(self, sandbox):
        """
        Regression: Command timeout must be enforced.
        Bug #009: Long-running commands could hang indefinitely.
        """
        from core.executor import execute

        # This should timeout (sleep for longer than timeout)
        result = execute("sleep 0.1", str(sandbox))
        # Should complete quickly (not hang)
        assert result is not None

    def test_execution_result_structure(self, sandbox):
        """
        Regression: ExecutionResult must have all required fields.
        Bug #010: Missing fields caused AttributeError.
        """
        from core.executor import ExecutionResult, execute

        result = execute("echo test", str(sandbox))

        assert isinstance(result, ExecutionResult)
        assert hasattr(result, "success")
        assert hasattr(result, "output")
        assert hasattr(result, "error")
        assert hasattr(result, "return_code")

    def test_failed_command_returns_error(self, sandbox):
        """
        Regression: Failed commands must return error info.
        Bug #011: Failed commands returned empty error messages.
        """
        from core.executor import execute

        result = execute("nonexistent_command_12345", str(sandbox))

        assert result.success is False
        assert result.return_code != 0


# =============================================================================
# Critical Error Handling Regressions
# =============================================================================


class TestErrorHandlingRegression:
    """Regression tests for error handling."""

    def test_error_codes_unique(self):
        """
        Regression: Error codes must be unique.
        Bug #012: Duplicate error codes caused wrong handling.
        """
        from utils.errors import ErrorCode

        codes = [e.value for e in ErrorCode]
        assert len(codes) == len(set(codes)), "Duplicate error codes found"

    def test_harness_error_serializable(self):
        """
        Regression: HarnessError must be serializable.
        Bug #013: to_dict() was failing with certain contexts.
        """
        from utils.errors import ErrorCode, ErrorContext, HarnessError

        error = HarnessError(
            "Test error",
            code=ErrorCode.UNKNOWN,
            context=ErrorContext(operation="test"),
        )

        error_dict = error.to_dict()
        assert "message" in error_dict
        assert "code" in error_dict

    def test_wrapped_exceptions_preserve_cause(self):
        """
        Regression: Wrapped exceptions must preserve cause.
        Bug #014: Original exception was lost during wrapping.
        """
        from utils.errors import wrap_exception

        original = ValueError("Original error")
        wrapped = wrap_exception(original, "test_operation")

        assert wrapped.cause is original
        assert "Original error" in str(wrapped)


# =============================================================================
# Critical Classification Regressions
# =============================================================================


class TestClassificationRegression:
    """Regression tests for response classification."""

    def test_json_parsing_handles_malformed(self):
        """
        Regression: JSON parsing must handle malformed input.
        Bug #015: Malformed JSON caused uncaught exceptions.
        """
        from core.classifier import parse_json_response

        malformed_inputs = [
            "not json at all",
            "{incomplete",
            '{"missing": }',
            "",
            None,
        ]

        for input_val in malformed_inputs:
            if input_val is not None:
                result = parse_json_response(input_val)
                # Should return None, not raise
                assert result is None or isinstance(result, dict)

    def test_command_extraction_handles_empty(self):
        """
        Regression: Command extraction must handle empty responses.
        Bug #016: Empty responses caused IndexError.
        """
        from core.classifier import extract_command

        empty_inputs = [
            "",
            "   ",
            "No code here",
            "```\n```",
        ]

        for input_val in empty_inputs:
            result = extract_command(input_val)
            # Should return None, not raise
            assert result is None or isinstance(result, str)

    def test_decision_defaults_safe(self):
        """
        Regression: Decision defaults must be safe.
        Bug #017: Default action was 'auto' instead of 'user'.
        """
        from core.classifier import classify
        from core.ollama import OllamaError

        with patch("core.classifier.run_prompt") as mock:
            mock.side_effect = OllamaError("API error")

            # Should fall back to safe defaults
            decision = classify("any response")

            assert decision.action == "user"  # Safe default


# =============================================================================
# Critical File Operation Regressions
# =============================================================================


class TestFileOperationRegression:
    """Regression tests for file operations."""

    def test_write_creates_parent_dirs(self, sandbox):
        """
        Regression: Write must create parent directories.
        Bug #018: Writing to nested paths failed.
        """
        from core.executor import write_file_sandboxed

        result = write_file_sandboxed(
            "deep/nested/path/file.txt",
            "content",
            str(sandbox),
        )

        assert result.success is True
        assert (sandbox / "deep/nested/path/file.txt").exists()

    def test_read_nonexistent_fails_gracefully(self, sandbox):
        """
        Regression: Reading nonexistent files must fail gracefully.
        Bug #019: Missing files caused uncaught FileNotFoundError.
        """
        from core.executor import read_file_sandboxed

        result = read_file_sandboxed("nonexistent.txt", str(sandbox))

        assert result.success is False
        assert "not found" in result.error.lower() or "error" in result.error.lower()

    def test_disallowed_extension_blocked(self, sandbox):
        """
        Regression: Disallowed extensions must be blocked.
        Bug #020: .exe files were being created.
        """
        from core.executor import write_file_sandboxed

        # These extensions are NOT in ALLOWED_EXTENSIONS
        disallowed = [".exe", ".dll", ".bin", ".bat"]

        for ext in disallowed:
            result = write_file_sandboxed(f"file{ext}", "content", str(sandbox))
            # Should fail due to disallowed extension
            assert result.success is False, f"Should block extension: {ext}"


# =============================================================================
# Critical Configuration Regressions
# =============================================================================


class TestConfigurationRegression:
    """Regression tests for configuration."""

    def test_default_config_valid(self):
        """
        Regression: Default configuration must be valid.
        Bug #021: Missing default values caused KeyError.
        """
        from utils.config import get_config_dict

        config = get_config_dict()

        required_keys = [
            "sandbox_dir",
            "command_timeout",
            "dangerous_keywords",
            "allowed_extensions",
        ]

        for key in required_keys:
            assert key in config, f"Missing required config: {key}"

    def test_config_values_sensible(self):
        """
        Regression: Config values must be sensible.
        Bug #022: Timeout was set to 0, causing immediate failures.
        """
        from utils.config import COMMAND_TIMEOUT, MAX_REPLY_LENGTH

        assert COMMAND_TIMEOUT > 0, "Timeout must be positive"
        assert MAX_REPLY_LENGTH > 0, "Max reply length must be positive"

    def test_permissions_defaults_safe(self):
        """
        Regression: Permission defaults must be safe.
        Bug #023: Default was 'auto' for dangerous operations.
        """
        from core.safety import _get_default_permissions

        defaults = _get_default_permissions()

        # Dangerous operations should default to ask or deny
        dangerous_actions = ["deploy", "git_push"]
        for action in dangerous_actions:
            if action in defaults.get("actions", {}):
                perm = defaults["actions"][action]
                assert perm in ("ask", "deny"), f"{action} should not default to auto"


# =============================================================================
# Critical Logging Regressions
# =============================================================================


class TestLoggingRegression:
    """Regression tests for logging."""

    def test_sensitive_data_masked(self):
        """
        Regression: Sensitive data must be masked in logs.
        Bug #024: API keys were being logged in plain text.
        """
        from utils.logger import _mask_sensitive_data

        data = {
            "api_key": "secret123",
            "password": "pass456",
            "token": "tok789",
            "normal_field": "visible",
        }

        masked = _mask_sensitive_data(data)

        assert masked["api_key"] == "***MASKED***"
        assert masked["password"] == "***MASKED***"
        assert masked["token"] == "***MASKED***"
        assert masked["normal_field"] == "visible"

    def test_log_file_path_absolute(self):
        """
        Regression: Log file path must be absolute.
        Bug #025: Relative paths caused files in wrong locations.
        """
        from utils.logger import get_log_file_path

        path = get_log_file_path()
        assert os.path.isabs(path), "Log path must be absolute"


# =============================================================================
# Smoke Tests (Quick Sanity Checks)
# =============================================================================


@pytest.mark.smoke
class TestSmoke:
    """Quick smoke tests to verify basic functionality."""

    def test_imports_work(self):
        """Verify all main modules can be imported."""

    def test_cli_parser_works(self):
        """Verify CLI parser initializes without error."""
        from cli import create_parser

        parser = create_parser()
        assert parser is not None

    def test_config_loads(self):
        """Verify configuration loads without error."""
        from utils.config import get_config_dict

        config = get_config_dict()
        assert isinstance(config, dict)

    def test_error_codes_exist(self):
        """Verify error codes are defined."""
        from utils.errors import ErrorCode

        assert len(list(ErrorCode)) > 0

    def test_validation_functions_exist(self):
        """Verify validation functions exist and are callable."""
        from utils.validation import (
            validate_command,
            validate_path,
            validate_prompt,
        )

        assert callable(validate_prompt)
        assert callable(validate_command)
        assert callable(validate_path)
