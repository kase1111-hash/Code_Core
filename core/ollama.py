"""
Ollama CLI subprocess wrapper.

This module provides functions to execute prompts using the Ollama CLI
with retry logic and timeout handling.
"""

import subprocess
from typing import Optional

DEFAULT_MODEL = "llama3"
TIMEOUT = 60
MAX_RETRIES = 3


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
    # TODO: Implement in Core Implementation phase
    raise NotImplementedError("Implementation pending")
