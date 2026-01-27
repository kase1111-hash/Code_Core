"""
Unit tests for core/executor.py
"""

import os

from core.executor import (
    ExecutionResult,
    _get_safe_env,
    execute,
    execute_sandboxed,
    read_file_sandboxed,
    validate_sandbox_path,
    write_file_sandboxed,
)


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_success_result(self):
        """Test successful execution result."""
        result = ExecutionResult(
            success=True,
            output="test output",
            error="",
            return_code=0,
        )
        assert result.success is True
        assert result.output == "test output"
        assert result.error == ""
        assert result.return_code == 0

    def test_failure_result(self):
        """Test failed execution result."""
        result = ExecutionResult(
            success=False,
            output="",
            error="command failed",
            return_code=1,
        )
        assert result.success is False
        assert result.error == "command failed"
        assert result.return_code == 1


class TestExecute:
    """Tests for execute function."""

    def test_execute_simple_command(self, tmp_path):
        """Test executing a simple command."""
        result = execute("echo hello", str(tmp_path))
        assert result.success is True
        assert "hello" in result.output
        assert result.return_code == 0

    def test_execute_creates_sandbox(self, tmp_path):
        """Test that execute creates sandbox directory."""
        sandbox = tmp_path / "new_sandbox"
        result = execute("echo test", str(sandbox))
        assert sandbox.exists()
        assert result.success is True

    def test_execute_with_invalid_command(self, tmp_path):
        """Test executing an invalid command."""
        result = execute("", str(tmp_path))
        assert result.success is False
        assert "validation failed" in result.error.lower()

    def test_execute_command_with_null_byte(self, tmp_path):
        """Test that command with null byte has it stripped."""
        result = execute("echo \x00test", str(tmp_path))
        # Null byte is removed, command executes
        assert "test" in result.output or result.success is True

    def test_execute_nonexistent_command(self, tmp_path):
        """Test executing a command that doesn't exist."""
        result = execute("nonexistent_command_12345", str(tmp_path))
        assert result.success is False
        assert result.return_code != 0


class TestExecuteSandboxed:
    """Tests for execute_sandboxed function."""

    def test_execute_sandboxed_simple(self, tmp_path):
        """Test sandboxed execution with list command."""
        result = execute_sandboxed(["echo", "hello"], str(tmp_path))
        assert result.success is True
        assert "hello" in result.output

    def test_execute_sandboxed_creates_sandbox(self, tmp_path):
        """Test that sandboxed execution creates sandbox."""
        sandbox = tmp_path / "sandbox"
        result = execute_sandboxed(["echo", "test"], str(sandbox))
        assert sandbox.exists()

    def test_execute_sandboxed_command_not_found(self, tmp_path):
        """Test sandboxed execution with nonexistent command."""
        result = execute_sandboxed(["nonexistent_cmd"], str(tmp_path))
        assert result.success is False
        assert "not found" in result.error.lower()


class TestWriteFileSandboxed:
    """Tests for write_file_sandboxed function."""

    def test_write_file_success(self, tmp_path):
        """Test successful file write."""
        result = write_file_sandboxed("test.txt", "content", str(tmp_path))
        assert result.success is True
        assert (tmp_path / "test.txt").exists()
        assert (tmp_path / "test.txt").read_text() == "content"

    def test_write_file_creates_parent_dirs(self, tmp_path):
        """Test that parent directories are created."""
        result = write_file_sandboxed("subdir/test.txt", "content", str(tmp_path))
        assert result.success is True
        assert (tmp_path / "subdir" / "test.txt").exists()

    def test_write_file_path_traversal_rejected(self, tmp_path):
        """Test that path traversal is rejected."""
        result = write_file_sandboxed("../outside.txt", "content", str(tmp_path))
        assert result.success is False
        assert "validation failed" in result.error.lower()

    def test_write_file_disallowed_extension(self, tmp_path):
        """Test that disallowed extensions are rejected."""
        result = write_file_sandboxed("script.exe", "content", str(tmp_path))
        assert result.success is False
        assert "extension not allowed" in result.error.lower()


class TestReadFileSandboxed:
    """Tests for read_file_sandboxed function."""

    def test_read_file_success(self, tmp_path):
        """Test successful file read."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("file content")

        result = read_file_sandboxed("test.txt", str(tmp_path))
        assert result.success is True
        assert result.output == "file content"

    def test_read_file_not_found(self, tmp_path):
        """Test reading nonexistent file."""
        result = read_file_sandboxed("nonexistent.txt", str(tmp_path))
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_read_file_path_traversal_rejected(self, tmp_path):
        """Test that path traversal is rejected."""
        result = read_file_sandboxed("../etc/passwd", str(tmp_path))
        assert result.success is False
        assert "validation failed" in result.error.lower()


class TestValidateSandboxPath:
    """Tests for validate_sandbox_path function."""

    def test_valid_path(self, tmp_path):
        """Test valid path within sandbox."""
        assert validate_sandbox_path("test.txt", str(tmp_path)) is True

    def test_valid_nested_path(self, tmp_path):
        """Test valid nested path."""
        assert validate_sandbox_path("subdir/file.txt", str(tmp_path)) is True

    def test_path_traversal_rejected(self, tmp_path):
        """Test that path traversal is rejected."""
        assert validate_sandbox_path("../outside.txt", str(tmp_path)) is False

    def test_encoded_traversal_rejected(self, tmp_path):
        """Test that encoded path traversal is rejected."""
        assert validate_sandbox_path("..%2Foutside.txt", str(tmp_path)) is False

    def test_double_dot_in_middle(self, tmp_path):
        """Test path with .. in middle."""
        assert validate_sandbox_path("subdir/../../../etc/passwd", str(tmp_path)) is False


class TestGetSafeEnv:
    """Tests for _get_safe_env function."""

    def test_includes_path(self):
        """Test that PATH is included."""
        env = _get_safe_env()
        if "PATH" in os.environ:
            assert "PATH" in env

    def test_includes_essential_vars(self):
        """Test that essential vars are included if present."""
        essential = ["PATH", "HOME", "USER", "LANG"]
        env = _get_safe_env()
        for var in essential:
            if var in os.environ:
                assert var in env

    def test_sets_pythondontwritebytecode(self):
        """Test that PYTHONDONTWRITEBYTECODE is set."""
        env = _get_safe_env()
        assert env.get("PYTHONDONTWRITEBYTECODE") == "1"

    def test_excludes_sensitive_vars(self):
        """Test that potentially sensitive vars are excluded."""
        # These shouldn't be in the safe env
        excluded = ["AWS_SECRET_KEY", "API_KEY", "PRIVATE_KEY"]
        env = _get_safe_env()
        for var in excluded:
            assert var not in env
