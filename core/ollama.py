"""
Ollama CLI subprocess wrapper.

This module provides functions to execute prompts using the Ollama CLI
with retry logic and timeout handling.
"""

import subprocess
import time

from utils.config import (
    MAX_RETRIES,
    OLLAMA_CHECK_TIMEOUT,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    RETRY_DELAY,
)
from utils.errors import (
    ErrorCode,
    ErrorContext,
    ServiceError,
)


class OllamaError(ServiceError):
    """Raised when Ollama command fails after all retries."""

    def __init__(self, message: str, code: ErrorCode = ErrorCode.OLLAMA_ERROR):
        super().__init__(
            message,
            code=code,
            context=ErrorContext(operation="ollama_run"),
        )


def run_prompt(prompt: str, model: str = OLLAMA_MODEL) -> str:
    """
    Execute a prompt using Ollama CLI.

    Args:
        prompt: The prompt to send to Ollama
        model: Model name (default from config)

    Returns:
        Response text from Ollama

    Raises:
        OllamaError: After MAX_RETRIES failed attempts
    """
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            result = subprocess.run(
                ["ollama", "run", model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=OLLAMA_TIMEOUT,
            )

            if result.returncode == 0:
                return result.stdout.strip()

            # Non-zero return code
            last_error = OllamaError(
                f"Ollama returned non-zero exit code: {result.returncode}. "
                f"stderr: {result.stderr}"
            )

        except subprocess.TimeoutExpired:
            last_error = OllamaError(
                f"Ollama timed out after {OLLAMA_TIMEOUT} seconds",
                code=ErrorCode.OLLAMA_TIMEOUT,
            )

        except FileNotFoundError as e:
            raise OllamaError(
                "Ollama not found. Please install Ollama: https://ollama.com",
                code=ErrorCode.OLLAMA_NOT_FOUND,
            ) from e

        except subprocess.SubprocessError as e:
            last_error = OllamaError(f"Subprocess error: {e}")

        # Wait before retry (except on last attempt)
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)

    # All retries exhausted
    raise OllamaError(
        f"Failed after {MAX_RETRIES} attempts. Last error: {last_error}"
    )


def check_ollama_available() -> bool:
    """
    Check if Ollama is installed and running.

    Returns:
        True if Ollama is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=OLLAMA_CHECK_TIMEOUT,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def list_models() -> list[str]:
    """
    List available Ollama models.

    Returns:
        List of model names

    Raises:
        OllamaError: If unable to list models
    """
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=OLLAMA_CHECK_TIMEOUT,
        )

        if result.returncode != 0:
            raise OllamaError(f"Failed to list models: {result.stderr}")

        # Parse output (skip header line)
        lines = result.stdout.strip().split("\n")[1:]
        models = []
        for line in lines:
            if line.strip():
                # First column is model name
                model_name = line.split()[0]
                models.append(model_name)

        return models

    except FileNotFoundError as e:
        raise OllamaError(
            "Ollama not found. Please install Ollama: https://ollama.com",
            code=ErrorCode.OLLAMA_NOT_FOUND,
        ) from e
