"""
Ollama CLI subprocess wrapper.

This module provides functions to execute prompts using the Ollama CLI
with retry logic and timeout handling.
"""

import subprocess
import time
from typing import Optional

DEFAULT_MODEL = "llama3"
TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds between retries


class OllamaError(Exception):
    """Raised when Ollama command fails after all retries."""

    pass


def run_prompt(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Execute a prompt using Ollama CLI.

    Args:
        prompt: The prompt to send to Ollama
        model: Model name (default: "llama3")

    Returns:
        Response text from Ollama

    Raises:
        OllamaError: After MAX_RETRIES failed attempts
    """
    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES):
        try:
            result = subprocess.run(
                ["ollama", "run", model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
            )

            if result.returncode == 0:
                return result.stdout.strip()

            # Non-zero return code
            last_error = OllamaError(
                f"Ollama returned non-zero exit code: {result.returncode}. "
                f"stderr: {result.stderr}"
            )

        except subprocess.TimeoutExpired:
            last_error = OllamaError(f"Ollama timed out after {TIMEOUT} seconds")

        except FileNotFoundError:
            raise OllamaError(
                "Ollama not found. Please install Ollama: https://ollama.ai"
            )

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
            timeout=10,
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
            timeout=10,
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

    except FileNotFoundError:
        raise OllamaError(
            "Ollama not found. Please install Ollama: https://ollama.ai"
        )
