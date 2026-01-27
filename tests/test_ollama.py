"""
Tests for core/ollama.py module.

Comprehensive tests for Ollama CLI wrapper including:
- Prompt execution
- Retry logic
- Error handling
- Model listing
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest


class TestOllamaError:
    """Tests for OllamaError exception."""

    def test_ollama_error_creation(self):
        """Test OllamaError creation."""
        from core.ollama import OllamaError
        error = OllamaError("Test error")
        assert "Test error" in str(error)

    def test_ollama_error_with_code(self):
        """Test OllamaError with error code."""
        from core.ollama import OllamaError
        from utils.errors import ErrorCode
        error = OllamaError("Test", code=ErrorCode.OLLAMA_TIMEOUT)
        assert error.code == ErrorCode.OLLAMA_TIMEOUT


class TestRunPrompt:
    """Tests for run_prompt function."""

    def test_run_prompt_success(self):
        """Test successful prompt execution."""
        from core.ollama import run_prompt

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Test response\n"

        with patch("subprocess.run", return_value=mock_result):
            result = run_prompt("test prompt")
            assert result == "Test response"

    def test_run_prompt_non_zero_exit_retries(self):
        """Test retry on non-zero exit code."""
        from core.ollama import OllamaError, run_prompt

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error output"

        with patch("subprocess.run", return_value=mock_result):
            with patch("time.sleep"):  # Skip delays
                with pytest.raises(OllamaError) as exc_info:
                    run_prompt("test")
                assert "Failed after" in str(exc_info.value)

    def test_run_prompt_timeout(self):
        """Test timeout handling."""
        from core.ollama import OllamaError, run_prompt

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)):
            with patch("time.sleep"):
                with pytest.raises(OllamaError) as exc_info:
                    run_prompt("test")
                assert "Failed after" in str(exc_info.value)

    def test_run_prompt_file_not_found(self):
        """Test Ollama not installed."""
        from core.ollama import OllamaError, run_prompt

        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(OllamaError) as exc_info:
                run_prompt("test")
            assert "not found" in str(exc_info.value).lower()

    def test_run_prompt_subprocess_error(self):
        """Test subprocess error handling."""
        from core.ollama import OllamaError, run_prompt

        with patch("subprocess.run", side_effect=subprocess.SubprocessError("Error")):
            with patch("time.sleep"):
                with pytest.raises(OllamaError):
                    run_prompt("test")

    def test_run_prompt_custom_model(self):
        """Test custom model specification."""
        from core.ollama import run_prompt

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Response"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            run_prompt("test", model="custom-model")
            call_args = mock_run.call_args
            assert "custom-model" in call_args[0][0]


class TestCheckOllamaAvailable:
    """Tests for check_ollama_available function."""

    def test_check_ollama_available_success(self):
        """Test Ollama is available."""
        from core.ollama import check_ollama_available

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            assert check_ollama_available() is True

    def test_check_ollama_available_not_installed(self):
        """Test Ollama not installed."""
        from core.ollama import check_ollama_available

        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert check_ollama_available() is False

    def test_check_ollama_available_error(self):
        """Test Ollama command error."""
        from core.ollama import check_ollama_available

        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            assert check_ollama_available() is False

    def test_check_ollama_available_subprocess_error(self):
        """Test subprocess error."""
        from core.ollama import check_ollama_available

        with patch("subprocess.run", side_effect=subprocess.SubprocessError):
            assert check_ollama_available() is False


class TestListModels:
    """Tests for list_models function."""

    def test_list_models_success(self):
        """Test successful model listing."""
        from core.ollama import list_models

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "NAME\nllama3:latest\nmistral:latest\n"

        with patch("subprocess.run", return_value=mock_result):
            models = list_models()
            assert "llama3:latest" in models
            assert "mistral:latest" in models

    def test_list_models_empty(self):
        """Test empty model list."""
        from core.ollama import list_models

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "NAME\n"

        with patch("subprocess.run", return_value=mock_result):
            models = list_models()
            assert models == []

    def test_list_models_error(self):
        """Test model listing error."""
        from core.ollama import OllamaError, list_models

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(OllamaError):
                list_models()

    def test_list_models_not_installed(self):
        """Test Ollama not installed."""
        from core.ollama import OllamaError, list_models

        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(OllamaError) as exc_info:
                list_models()
            assert "not found" in str(exc_info.value).lower()
