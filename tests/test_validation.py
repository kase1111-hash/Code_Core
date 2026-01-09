"""
Unit tests for utils/validation.py
"""

import pytest
from utils.validation import (
    ValidationError,
    validate_prompt,
    sanitize_string,
    validate_command,
    contains_shell_injection,
    get_command_risk_level,
    validate_path,
    contains_path_traversal,
    validate_extension,
    validate_permission_level,
    validate_risk_level,
    validate_response,
    truncate_response,
    validate_user_choice,
    sanitize_log_message,
)


class TestValidatePrompt:
    """Tests for validate_prompt function."""

    def test_valid_prompt(self):
        """Test that valid prompts pass validation."""
        prompt = "Create a Python function to calculate fibonacci"
        result = validate_prompt(prompt)
        assert result == prompt

    def test_empty_prompt_raises(self):
        """Test that empty prompts raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_prompt("")

    def test_whitespace_stripped(self):
        """Test that whitespace is handled correctly."""
        # Leading/trailing whitespace is stripped
        result = validate_prompt("   hello   ")
        assert result == "hello"

    def test_prompt_too_long_raises(self):
        """Test that overly long prompts raise ValidationError."""
        long_prompt = "x" * 100001
        with pytest.raises(ValidationError):
            validate_prompt(long_prompt)

    def test_prompt_stripped(self):
        """Test that prompts are stripped of leading/trailing whitespace."""
        result = validate_prompt("  hello world  ")
        assert result == "hello world"


class TestSanitizeString:
    """Tests for sanitize_string function."""

    def test_removes_null_bytes(self):
        """Test that null bytes are removed."""
        result = sanitize_string("hello\x00world")
        assert "\x00" not in result

    def test_preserves_newlines_by_default(self):
        """Test that newlines are preserved by default."""
        result = sanitize_string("hello\nworld")
        assert "\n" in result

    def test_removes_newlines_when_disabled(self):
        """Test that newlines are removed when allow_newlines=False."""
        result = sanitize_string("hello\nworld", allow_newlines=False)
        assert "\n" not in result

    def test_removes_control_characters(self):
        """Test that control characters are removed."""
        result = sanitize_string("hello\x07world")  # Bell character
        assert "\x07" not in result


class TestValidateCommand:
    """Tests for validate_command function."""

    def test_valid_command(self):
        """Test that valid commands pass validation."""
        result = validate_command("ls -la")
        assert result == "ls -la"

    def test_empty_command_raises(self):
        """Test that empty commands raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_command("")

    def test_command_with_null_byte_sanitized(self):
        """Test that commands with null bytes have them removed."""
        result = validate_command("ls\x00-la")
        assert "\x00" not in result
        assert result == "ls-la"


class TestContainsShellInjection:
    """Tests for contains_shell_injection function."""

    def test_no_injection(self):
        """Test that safe commands return False."""
        assert contains_shell_injection("ls -la") is False

    def test_semicolon_injection(self):
        """Test detection of semicolon injection."""
        assert contains_shell_injection("ls; rm -rf /") is True

    def test_pipe_injection(self):
        """Test detection of pipe injection."""
        assert contains_shell_injection("cat file | bash") is True

    def test_backtick_injection(self):
        """Test detection of backtick injection."""
        assert contains_shell_injection("echo `whoami`") is True

    def test_dollar_paren_injection(self):
        """Test detection of $() injection."""
        assert contains_shell_injection("echo $(whoami)") is True

    def test_eval_injection(self):
        """Test detection of eval injection."""
        assert contains_shell_injection("eval 'rm -rf /'") is True

    def test_redirect_injection(self):
        """Test detection of redirect injection."""
        assert contains_shell_injection("echo test > /etc/passwd") is True


class TestGetCommandRiskLevel:
    """Tests for get_command_risk_level function."""

    def test_low_risk_command(self):
        """Test that safe commands are low risk."""
        assert get_command_risk_level("ls -la") == "low"

    def test_medium_risk_command(self):
        """Test that commands with external access are medium risk."""
        assert get_command_risk_level("git commit -m 'test'") == "medium"
        assert get_command_risk_level("curl http://example.com") == "medium"
        assert get_command_risk_level("rm file.txt") == "medium"

    def test_high_risk_command(self):
        """Test that dangerous commands are high risk."""
        assert get_command_risk_level("sudo rm -rf /") == "high"
        assert get_command_risk_level("chmod 777 file") == "high"


class TestValidatePath:
    """Tests for validate_path function."""

    def test_valid_relative_path(self):
        """Test that valid relative paths pass."""
        result = validate_path("test.py", sandbox_root="/tmp/sandbox")
        assert "test.py" in result

    def test_path_traversal_raises(self):
        """Test that path traversal attempts raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_path("../../../etc/passwd", sandbox_root="/tmp/sandbox")

    def test_empty_path_raises(self):
        """Test that empty paths raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_path("", sandbox_root="/tmp/sandbox")


class TestContainsPathTraversal:
    """Tests for contains_path_traversal function."""

    def test_no_traversal(self):
        """Test that normal paths return False."""
        assert contains_path_traversal("file.txt") is False

    def test_dot_dot_traversal(self):
        """Test detection of .. traversal."""
        assert contains_path_traversal("../file.txt") is True
        assert contains_path_traversal("foo/../bar") is True

    def test_encoded_traversal(self):
        """Test detection of URL-encoded traversal."""
        assert contains_path_traversal("%2e%2e/file.txt") is True


class TestValidateExtension:
    """Tests for validate_extension function."""

    def test_valid_extension(self):
        """Test that allowed extensions pass."""
        assert validate_extension("test.py") is True
        assert validate_extension("test.txt") is True
        assert validate_extension("test.json") is True

    def test_no_extension_allowed(self):
        """Test that files without extension are allowed."""
        assert validate_extension("Makefile") is True

    def test_invalid_extension(self):
        """Test that disallowed extensions fail."""
        assert validate_extension("test.exe") is False


class TestValidatePermissionLevel:
    """Tests for validate_permission_level function."""

    def test_valid_levels(self):
        """Test that valid permission levels pass."""
        assert validate_permission_level("auto") == "auto"
        assert validate_permission_level("ask") == "ask"
        assert validate_permission_level("deny") == "deny"

    def test_invalid_level_raises(self):
        """Test that invalid levels raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_permission_level("invalid")


class TestValidateRiskLevel:
    """Tests for validate_risk_level function."""

    def test_valid_levels(self):
        """Test that valid risk levels pass."""
        assert validate_risk_level("low") == "low"
        assert validate_risk_level("medium") == "medium"
        assert validate_risk_level("high") == "high"

    def test_invalid_level_raises(self):
        """Test that invalid levels raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_risk_level("invalid")

    def test_empty_level_defaults_to_medium(self):
        """Test that empty level returns 'medium'."""
        assert validate_risk_level("") == "medium"


class TestValidateResponse:
    """Tests for validate_response function."""

    def test_valid_response(self):
        """Test that valid responses pass."""
        result = validate_response("This is a response")
        assert result == "This is a response"

    def test_empty_response(self):
        """Test that empty responses return empty string."""
        result = validate_response("")
        assert result == ""


class TestTruncateResponse:
    """Tests for truncate_response function."""

    def test_short_response_unchanged(self):
        """Test that short responses are not truncated."""
        result = truncate_response("hello", max_length=100)
        assert result == "hello"

    def test_long_response_truncated(self):
        """Test that long responses are truncated."""
        long_text = "x" * 100
        result = truncate_response(long_text, max_length=50)
        # Format is: first 50 chars + "\n... (truncated, 100 total)"
        assert len(result) > 50  # Includes truncation notice
        assert result.startswith("x" * 50)
        assert "truncated" in result
        assert "100 total" in result


class TestValidateUserChoice:
    """Tests for validate_user_choice function."""

    def test_valid_choice(self):
        """Test that valid choices pass."""
        result = validate_user_choice("y", {"y", "n"})
        assert result == "y"

    def test_invalid_choice_raises(self):
        """Test that invalid choices raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_user_choice("x", {"y", "n"})

    def test_case_insensitive(self):
        """Test that choices are case-insensitive."""
        result = validate_user_choice("Y", {"y", "n"})
        assert result == "y"


class TestSanitizeLogMessage:
    """Tests for sanitize_log_message function."""

    def test_removes_newlines(self):
        """Test that newlines are removed from log messages."""
        result = sanitize_log_message("hello\nworld")
        assert "\n" not in result

    def test_escapes_quotes(self):
        """Test that quotes are escaped in log messages."""
        result = sanitize_log_message('Hello "world"')
        assert '\\"' in result

    def test_removes_null_bytes(self):
        """Test that null bytes are removed from log messages."""
        result = sanitize_log_message("hello\x00world")
        assert "\x00" not in result
