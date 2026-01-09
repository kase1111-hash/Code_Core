"""
Claude API client with Ollama fallback.

This module provides functions to get AI responses from Claude,
with automatic fallback to Ollama when API key is not available.
"""

import os
from typing import Optional

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096


def get_response(prompt: str) -> str:
    """
    Get a response from Claude (API or fallback).

    Args:
        prompt: The prompt to send

    Returns:
        Response text from Claude or Ollama fallback
    """
    # TODO: Implement in Core Implementation phase
    raise NotImplementedError("Implementation pending")


def _call_api(prompt: str) -> str:
    """Call Claude API directly."""
    # TODO: Implement in Core Implementation phase
    raise NotImplementedError("Implementation pending")


def _fallback_ollama(prompt: str) -> str:
    """Fall back to Ollama when API key is missing."""
    # TODO: Implement in Core Implementation phase
    raise NotImplementedError("Implementation pending")
