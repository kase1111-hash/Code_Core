"""
Claude API client with Ollama fallback.

This module provides functions to get AI responses from Claude,
with automatic fallback to Ollama when API key is not available.
"""

import os

from core.ollama import OllamaError
from core.ollama import run_prompt as ollama_run_prompt
from utils.config import CLAUDE_MAX_TOKENS, CLAUDE_MODEL, OLLAMA_MODEL
from utils.errors import (
    ErrorCode,
    ErrorContext,
    ServiceError,
)


class ClaudeError(ServiceError):
    """Raised when Claude API call fails."""

    def __init__(self, message: str, code: ErrorCode = ErrorCode.CLAUDE_ERROR):
        super().__init__(
            message,
            code=code,
            context=ErrorContext(operation="claude_api"),
        )


def get_response(prompt: str, use_api: bool | None = None) -> str:
    """
    Get a response from Claude (API or fallback).

    Args:
        prompt: The prompt to send
        use_api: Force API usage (True) or fallback (False).
                 If None, auto-detect based on API key presence.

    Returns:
        Response text from Claude or Ollama fallback
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    # Determine whether to use API
    if use_api is None:
        use_api = bool(api_key)
    elif use_api and not api_key:
        raise ClaudeError(
            "API usage requested but ANTHROPIC_API_KEY not set",
            code=ErrorCode.CLAUDE_AUTH_ERROR,
        )

    if use_api:
        return _call_api(prompt)
    else:
        return _fallback_ollama(prompt)


def _call_api(prompt: str) -> str:
    """
    Call Claude API directly.

    Args:
        prompt: The prompt to send

    Returns:
        Response text from Claude

    Raises:
        ClaudeError: If API call fails
    """
    try:
        from anthropic import Anthropic, APIError

        client = Anthropic()

        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        # Extract text from response
        if message.content and len(message.content) > 0:
            return message.content[0].text

        return ""

    except ImportError:
        raise ClaudeError(
            "anthropic package not installed. Install with: pip install anthropic",
            code=ErrorCode.CONFIGURATION,
        )

    except APIError as e:
        raise ClaudeError(
            f"Claude API error: {e}",
            code=ErrorCode.CLAUDE_API_ERROR,
        )

    except (OSError, ValueError, TypeError) as e:
        raise ClaudeError(
            f"Unexpected error calling Claude: {e}",
            code=ErrorCode.CLAUDE_ERROR,
        )


def _fallback_ollama(prompt: str) -> str:
    """
    Fall back to Ollama when API key is missing.

    Args:
        prompt: The prompt to send

    Returns:
        Response text from Ollama

    Raises:
        ClaudeError: If Ollama fallback fails
    """
    try:
        return ollama_run_prompt(prompt, model=OLLAMA_MODEL)
    except OllamaError as e:
        # Preserve the original error code from OllamaError
        error_code = getattr(e, "code", ErrorCode.OLLAMA_ERROR)
        raise ClaudeError(f"Ollama fallback failed: {e}", code=error_code)


def check_api_available() -> bool:
    """
    Check if Claude API is configured and available.

    Returns:
        True if API key is set, False otherwise
    """
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def get_model_info() -> dict[str, str]:
    """
    Get information about the current configuration.

    Returns:
        Dictionary with model configuration info
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    return {
        "mode": "api" if api_key else "fallback",
        "model": CLAUDE_MODEL if api_key else OLLAMA_MODEL,
        "max_tokens": str(CLAUDE_MAX_TOKENS),
        "api_key_set": "yes" if api_key else "no",
    }
