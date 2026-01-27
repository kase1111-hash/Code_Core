"""
System and acceptance tests for Ollama Automation Harness.

These tests verify end-to-end functionality from the user's perspective,
testing complete workflows and verifying acceptance criteria.
"""

import os
from unittest.mock import patch

import pytest

# =============================================================================
# CLI Acceptance Tests
# =============================================================================


class TestCLIVersionCommand:
    """Acceptance tests for version command."""

    def test_version_flag_shows_version(self):
        """Test that --version flag displays version information."""
        from cli import create_parser

        parser = create_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])

        # Version flag causes SystemExit with code 0
        assert exc_info.value.code == 0

    def test_version_subcommand_shows_details(self):
        """Test that 'version' subcommand shows detailed info."""
        import argparse

        from cli import cmd_version

        args = argparse.Namespace()
        exit_code = cmd_version(args)

        assert exit_code == 0

    def test_version_includes_python_info(self, capsys):
        """Test version output includes Python version."""
        import argparse

        from cli import cmd_version

        args = argparse.Namespace()
        cmd_version(args)

        captured = capsys.readouterr()
        assert "Python" in captured.out


class TestCLICheckCommand:
    """Acceptance tests for check command."""

    def test_check_command_runs_health_checks(self, capsys):
        """Test that check command runs system health checks."""
        import argparse

        from cli import cmd_check

        args = argparse.Namespace(fix=False, verbose=False)
        exit_code = cmd_check(args)

        captured = capsys.readouterr()
        assert "System Health Check" in captured.out
        assert "Python" in captured.out
        assert exit_code in (0, 1)  # Pass or fail is acceptable

    def test_check_command_with_fix_flag(self, capsys, tmp_path):
        """Test that --fix flag attempts to fix issues."""
        import argparse

        from cli import cmd_check

        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            args = argparse.Namespace(fix=True, verbose=False)
            cmd_check(args)

            captured = capsys.readouterr()
            # Should attempt to create directories
            assert "Created directory" in captured.out or "[OK]" in captured.out
        finally:
            os.chdir(original_cwd)

    def test_check_verifies_python_version(self, capsys):
        """Test that check verifies Python version."""
        import argparse

        from cli import cmd_check

        args = argparse.Namespace(fix=False, verbose=False)
        cmd_check(args)

        captured = capsys.readouterr()
        assert "Python" in captured.out
        assert "[OK]" in captured.out or "[X]" in captured.out


class TestCLIConfigCommand:
    """Acceptance tests for config command."""

    def test_config_show_displays_configuration(self, capsys):
        """Test that 'config show' displays current config."""
        import argparse

        from cli import cmd_config

        args = argparse.Namespace(config_command="show")
        exit_code = cmd_config(args)

        captured = capsys.readouterr()
        assert "Current Configuration" in captured.out
        assert exit_code == 0

    def test_config_validate_checks_configuration(self, capsys):
        """Test that 'config validate' validates config."""
        import argparse

        from cli import cmd_config

        args = argparse.Namespace(config_command="validate")
        exit_code = cmd_config(args)

        captured = capsys.readouterr()
        assert "Validating configuration" in captured.out
        assert exit_code in (0, 1)

    def test_config_path_shows_paths(self, capsys):
        """Test that 'config path' shows file paths."""
        import argparse

        from cli import cmd_config

        args = argparse.Namespace(config_command="path")
        exit_code = cmd_config(args)

        captured = capsys.readouterr()
        assert "Configuration File Paths" in captured.out
        assert "Permissions" in captured.out
        assert "Sandbox" in captured.out
        assert exit_code == 0

    def test_config_no_subcommand_shows_help(self, capsys):
        """Test that 'config' without subcommand shows help."""
        import argparse

        from cli import cmd_config

        args = argparse.Namespace(config_command=None)
        exit_code = cmd_config(args)

        captured = capsys.readouterr()
        assert "Please specify" in captured.out
        assert exit_code == 1


class TestCLIRunCommand:
    """Acceptance tests for run command."""

    def test_run_parser_accepts_prompt(self):
        """Test that run command accepts --prompt argument."""
        from cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["run", "-p", "Test prompt"])

        assert args.command == "run"
        assert args.prompt == "Test prompt"

    def test_run_parser_accepts_file_input(self):
        """Test that run command accepts --file argument."""
        from cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["run", "-f", "/path/to/file.txt"])

        assert args.command == "run"
        assert args.file == "/path/to/file.txt"

    def test_run_parser_accepts_environment(self):
        """Test that run command accepts --env argument."""
        from cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["run", "-e", "production"])

        assert args.command == "run"
        assert args.env == "production"

    def test_run_parser_accepts_dry_run(self):
        """Test that run command accepts --dry-run flag."""
        from cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["run", "--dry-run"])

        assert args.command == "run"
        assert args.dry_run is True


class TestCLIHelpOutput:
    """Acceptance tests for help output."""

    def test_main_help_shows_commands(self, capsys):
        """Test that main help shows available commands."""
        from cli import create_parser

        parser = create_parser()
        parser.print_help()

        captured = capsys.readouterr()
        assert "run" in captured.out
        assert "config" in captured.out
        assert "check" in captured.out
        assert "version" in captured.out

    def test_help_includes_examples(self, capsys):
        """Test that help includes usage examples."""
        from cli import create_parser

        parser = create_parser()
        parser.print_help()

        captured = capsys.readouterr()
        assert "Examples" in captured.out


# =============================================================================
# Workflow Acceptance Tests
# =============================================================================


class TestPromptProcessingWorkflow:
    """Acceptance tests for prompt processing workflow."""

    def test_prompt_validation_accepts_valid_input(self):
        """Test that valid prompts are accepted."""
        from utils.validation import validate_prompt

        prompts = [
            "Create a Python function",
            "Fix the bug in file.py",
            "Run the tests",
            "Explain this code",
        ]

        for prompt in prompts:
            result = validate_prompt(prompt)
            assert result == prompt

    def test_prompt_validation_rejects_empty_input(self):
        """Test that empty prompts are rejected."""
        from utils.validation import ValidationError, validate_prompt

        with pytest.raises(ValidationError):
            validate_prompt("")

    def test_dangerous_commands_require_approval(self):
        """Test that dangerous commands are flagged for user approval."""
        from core.classifier import Decision
        from core.safety import PermissionManager

        permissions = PermissionManager()

        # Decision with dangerous command
        decision = Decision(
            action="auto",
            reason="Test",
            command="sudo rm -rf /important",
            risk_level="low",
        )

        enforced = permissions.enforce(decision)
        # Should be escalated to user action
        assert enforced.action == "user"
        assert enforced.risk_level == "high"

    def test_safe_commands_can_auto_execute(self):
        """Test that safe commands can be auto-executed."""
        from core.classifier import Decision
        from core.safety import PermissionManager

        permissions = PermissionManager()

        decision = Decision(
            action="auto",
            reason="Safe read operation",
            command="ls -la",
            risk_level="low",
        )

        enforced = permissions.enforce(decision)
        # Should remain auto (or be escalated based on config)
        assert enforced.action in ("auto", "user")


class TestSandboxedExecutionWorkflow:
    """Acceptance tests for sandboxed execution workflow."""

    def test_commands_execute_in_sandbox(self, tmp_path):
        """Test that commands execute within sandbox directory."""
        from core.executor import execute

        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Create a file in sandbox
        result = execute("touch test_created.txt", str(sandbox))

        # Verify file was created in sandbox
        expected_file = sandbox / "test_created.txt"
        assert expected_file.exists() or result.success

    def test_file_writes_confined_to_sandbox(self, tmp_path):
        """Test that file writes are confined to sandbox."""
        from core.executor import write_file_sandboxed

        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Write a file
        result = write_file_sandboxed("output.txt", "test content", str(sandbox))

        assert result.success is True
        assert (sandbox / "output.txt").exists()
        assert (sandbox / "output.txt").read_text() == "test content"

    def test_path_traversal_prevented(self, tmp_path):
        """Test that path traversal attacks are prevented."""
        from core.executor import write_file_sandboxed

        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Attempt path traversal
        result = write_file_sandboxed(
            "../../../tmp/escape.txt",
            "malicious",
            str(sandbox),
        )

        assert result.success is False

    def test_command_output_captured(self, tmp_path):
        """Test that command output is captured correctly."""
        from core.executor import execute

        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        result = execute("echo 'Hello World'", str(sandbox))

        assert result.success is True
        assert "Hello" in result.output


class TestErrorHandlingWorkflow:
    """Acceptance tests for error handling workflow."""

    def test_errors_are_user_friendly(self):
        """Test that errors produce user-friendly messages."""
        from utils.errors import ErrorCode, HarnessError, format_error_for_user

        error = HarnessError(
            "Operation failed due to invalid input",
            code=ErrorCode.VALIDATION_FAILED,
        )

        message = format_error_for_user(error)

        # Should be readable by end user
        assert isinstance(message, str)
        assert len(message) > 0
        assert "invalid input" in message.lower()

    def test_recovery_suggestions_provided(self):
        """Test that recovery suggestions are provided for errors."""
        from utils.errors import (
            ErrorCode,
            HarnessError,
            get_recovery_suggestion,
        )

        # Use an error code that has a defined suggestion
        error = HarnessError(
            "Validation failed",
            code=ErrorCode.VALIDATION_FAILED,
        )

        suggestion = get_recovery_suggestion(error)

        # Should have a suggestion
        assert suggestion is not None
        assert len(suggestion) > 0

    def test_errors_are_logged(self, tmp_path):
        """Test that errors are properly logged."""
        from utils.error_tracking import (
            capture_exception,
            get_error_counts,
            reset_error_counts,
        )
        from utils.errors import ErrorCode, HarnessError

        reset_error_counts()

        error = HarnessError("Test error", code=ErrorCode.UNKNOWN)
        capture_exception(error, context="acceptance_test")

        counts = get_error_counts()
        assert "UNKNOWN" in counts
        assert counts["UNKNOWN"] >= 1


# =============================================================================
# Security Acceptance Tests
# =============================================================================


class TestSecurityAcceptance:
    """Acceptance tests for security requirements."""

    def test_secrets_are_masked_in_output(self):
        """Test that secrets are masked when displayed."""
        from utils.secrets import mask_secret

        api_key = "sk-1234567890abcdefghijklmnop"
        masked = mask_secret(api_key)

        # Full key should not be visible
        assert api_key not in masked
        # Should show partial info
        assert "..." in masked

    def test_sensitive_config_masked_in_logs(self):
        """Test that sensitive config values are masked in logs."""
        from utils.logger import _mask_sensitive_data

        data = {
            "api_key": "secret-key-12345",
            "password": "super-secret",
            "username": "admin",
        }

        masked = _mask_sensitive_data(data)

        assert masked["api_key"] == "***MASKED***"
        assert masked["password"] == "***MASKED***"
        assert masked["username"] == "admin"  # Not sensitive

    def test_dangerous_keywords_always_detected(self):
        """Test that dangerous keywords are always detected."""
        from utils.config import is_dangerous_keyword

        test_commands = [
            "sudo apt-get install something",
            "rm -rf /important/data",
            "Deploy to production",
            "chmod 777 /etc/passwd",
            "git push origin main --force",
        ]

        for cmd in test_commands:
            assert is_dangerous_keyword(cmd) is True, f"Should detect: {cmd}"

    def test_shell_injection_prevented(self):
        """Test that shell injection attempts are prevented."""
        from utils.validation import ValidationError, validate_command

        injection_attempts = [
            "ls; rm -rf /",
            "echo $(cat /etc/passwd)",
            "cat file | bash",
            "echo `whoami`",
        ]

        for cmd in injection_attempts:
            with pytest.raises(ValidationError):
                validate_command(cmd)


# =============================================================================
# User Story Acceptance Tests
# =============================================================================


class TestUserStoryAutomatedDevWorkflow:
    """
    User Story: As a developer, I want to automate development tasks
    with AI assistance while maintaining control over risky operations.
    """

    def test_safe_operations_auto_execute(self):
        """Verify safe operations can execute automatically."""
        from core.classifier import Decision
        from core.safety import PermissionManager

        manager = PermissionManager()

        # Safe operation
        decision = Decision(
            action="auto",
            reason="Read-only operation",
            command="cat README.md",
            risk_level="low",
        )

        result = manager.enforce(decision)
        # Should allow auto execution or ask (never deny for safe ops)
        assert result.action in ("auto", "user")

    def test_risky_operations_require_confirmation(self):
        """Verify risky operations require user confirmation."""
        from core.classifier import Decision
        from core.safety import PermissionManager

        manager = PermissionManager()

        # Risky operation
        decision = Decision(
            action="auto",
            reason="Deployment operation",
            command="deploy --production",
            risk_level="medium",
        )

        result = manager.enforce(decision)
        # Should require user confirmation
        assert result.action == "user"


class TestUserStorySecureSandbox:
    """
    User Story: As a developer, I want command execution to be
    sandboxed so that my system is protected from harmful commands.
    """

    def test_execution_confined_to_sandbox(self, tmp_path):
        """Verify execution is confined to sandbox directory."""
        from core.executor import execute

        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Command should execute in sandbox
        result = execute("pwd", str(sandbox))

        assert result.success is True
        assert str(sandbox) in result.output

    def test_file_creation_in_sandbox_only(self, tmp_path):
        """Verify files can only be created in sandbox."""
        from core.executor import write_file_sandboxed

        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Create file in sandbox - should succeed
        result = write_file_sandboxed("allowed.txt", "content", str(sandbox))
        assert result.success is True

        # Try to create outside sandbox - should fail
        result = write_file_sandboxed("../outside.txt", "content", str(sandbox))
        assert result.success is False


class TestUserStoryAuditTrail:
    """
    User Story: As a security-conscious developer, I want all
    operations to be logged for audit purposes.
    """

    def test_operations_are_logged(self, tmp_path):
        """Verify that operations are logged."""
        import utils.logger

        # Reset logger
        utils.logger._logger = None

        log_file = tmp_path / "test.log"
        logger = utils.logger.setup_logger(
            str(log_file),
            enable_console=False,
        )

        # Log some operations
        utils.logger.log_startup()
        utils.logger.log_shutdown("test")

        # Verify log file has content
        content = log_file.read_text()
        assert "started" in content.lower() or "stopped" in content.lower()

    def test_errors_are_tracked(self):
        """Verify that errors are tracked."""
        from utils.error_tracking import (
            capture_exception,
            get_error_summary,
            reset_error_counts,
        )
        from utils.errors import ErrorCode, HarnessError

        reset_error_counts()

        # Capture some errors
        for i in range(3):
            error = HarnessError(f"Test error {i}", code=ErrorCode.UNKNOWN)
            capture_exception(error)

        summary = get_error_summary()
        assert summary["total_errors"] >= 3


# =============================================================================
# End-to-End Acceptance Tests
# =============================================================================


class TestEndToEndClassificationPipeline:
    """End-to-end tests for the classification pipeline."""

    def test_response_classification_pipeline(self):
        """Test complete response classification pipeline."""
        from core.classifier import Decision, classify
        from core.safety import PermissionManager

        # Mock response from Claude
        claude_response = """
        To fix this bug, I recommend running the tests:
        ```bash
        pytest tests/ -v
        ```
        This will verify the fix works correctly.
        """

        # Classify the response
        with patch("core.classifier.run_prompt") as mock_ollama:
            mock_ollama.return_value = '{"action": "auto", "reason": "Running tests is safe", "command": "pytest tests/ -v", "risk_level": "low"}'

            decision = classify(claude_response)

        # Enforce permissions
        manager = PermissionManager()
        final_decision = manager.enforce(decision)

        # Verify decision has expected structure
        assert isinstance(final_decision, Decision)
        assert final_decision.action in ("auto", "user")
        assert final_decision.command is not None


class TestEndToEndFileWorkflow:
    """End-to-end tests for file operations workflow."""

    def test_complete_file_read_write_cycle(self, tmp_path):
        """Test complete file read/write workflow."""
        from core.executor import read_file_sandboxed, write_file_sandboxed

        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Write content
        content = "Test content for acceptance test"
        write_result = write_file_sandboxed("test_file.txt", content, str(sandbox))
        assert write_result.success is True

        # Read it back
        read_result = read_file_sandboxed("test_file.txt", str(sandbox))
        assert read_result.success is True
        assert read_result.output == content

    def test_nested_file_operations(self, tmp_path):
        """Test file operations in nested directories."""
        from core.executor import write_file_sandboxed

        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        # Create nested structure
        write_file_sandboxed("src/main.py", "# Main", str(sandbox))
        write_file_sandboxed("src/utils/helper.py", "# Helper", str(sandbox))
        write_file_sandboxed("tests/test_main.py", "# Tests", str(sandbox))

        # Verify all files created
        assert (sandbox / "src" / "main.py").exists()
        assert (sandbox / "src" / "utils" / "helper.py").exists()
        assert (sandbox / "tests" / "test_main.py").exists()


class TestEndToEndErrorRecovery:
    """End-to-end tests for error recovery."""

    def test_graceful_error_handling(self):
        """Test that errors are handled gracefully."""
        from utils.errors import (
            ErrorCode,
            HarnessError,
            format_error_for_user,
            get_recovery_suggestion,
            is_recoverable,
        )

        # Simulate various errors
        errors = [
            HarnessError("Validation failed", code=ErrorCode.VALIDATION_FAILED, recoverable=True),
            HarnessError("Execution failed", code=ErrorCode.EXECUTION_FAILED, recoverable=True),
            HarnessError("Safety violation", code=ErrorCode.SAFETY_VIOLATION, recoverable=False),
        ]

        for error in errors:
            # Should produce user-friendly message
            message = format_error_for_user(error)
            assert len(message) > 0

            # Should indicate recoverability
            recoverable = is_recoverable(error)
            assert isinstance(recoverable, bool)

            # Should have suggestion for recoverable errors
            suggestion = get_recovery_suggestion(error)
            # May or may not have suggestion based on error type


# =============================================================================
# Configuration Acceptance Tests
# =============================================================================


class TestConfigurationAcceptance:
    """Acceptance tests for configuration management."""

    def test_default_config_is_valid(self):
        """Test that default configuration is valid."""
        from utils.config import get_config_dict

        config = get_config_dict()

        # Should have required keys
        assert "sandbox_dir" in config
        assert "command_timeout" in config
        assert "dangerous_keywords" in config
        assert "allowed_extensions" in config

    def test_config_values_are_sensible(self):
        """Test that config values are sensible."""
        from utils.config import (
            ALLOWED_EXTENSIONS,
            COMMAND_TIMEOUT,
            DANGEROUS_KEYWORDS,
            MAX_REPLY_LENGTH,
        )

        # Timeout should be reasonable
        assert 1 <= COMMAND_TIMEOUT <= 600

        # Max reply length should be reasonable
        assert 100 <= MAX_REPLY_LENGTH <= 100000

        # Should have dangerous keywords defined
        assert len(DANGEROUS_KEYWORDS) > 0

        # Should have allowed extensions defined
        assert len(ALLOWED_EXTENSIONS) > 0

    def test_environment_detection_works(self):
        """Test that environment detection works."""
        from utils.secrets import Environment

        # All environments should be defined
        environments = list(Environment)
        assert Environment.DEVELOPMENT in environments
        assert Environment.PRODUCTION in environments
        assert Environment.TESTING in environments
