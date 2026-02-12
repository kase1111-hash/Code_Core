"""
Centralized configuration for Ollama Automation Harness.

This module provides a single source of truth for all configuration
constants and settings used across the application.
"""

import os
from pathlib import Path
from typing import Any

from utils.environment import (
    get_current_environment,
    is_debug_enabled,
    load_environment,
)

# Load environment-specific configuration
# This loads .env first, then overlays environment-specific settings
load_environment()


# =============================================================================
# Path Configuration
# =============================================================================

# Project root (where main.py is located)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Sandbox directory for safe file operations
SANDBOX_DIR = os.getenv("SANDBOX_DIR", str(PROJECT_ROOT / "sandbox"))

# Configuration file paths
CONFIG_DIR = PROJECT_ROOT / "config"
PERMISSIONS_FILE = os.getenv("PERMISSIONS_FILE", str(CONFIG_DIR / "permissions.yaml"))

# Log file path
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = os.getenv("LOG_FILE", str(LOG_DIR / "automation.log"))


# =============================================================================
# Timeout Configuration
# =============================================================================

# Ollama subprocess timeout (seconds)
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))

# Command execution timeout (seconds)
COMMAND_TIMEOUT = int(os.getenv("COMMAND_TIMEOUT", "30"))

# Ollama availability check timeout (seconds)
OLLAMA_CHECK_TIMEOUT = 10


# =============================================================================
# Retry Configuration
# =============================================================================

# Maximum retry attempts for Ollama
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# Delay between retries (seconds)
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))


# =============================================================================
# Model Configuration
# =============================================================================

# Default Ollama model
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Claude model for API mode
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# Maximum tokens for Claude response
CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "4096"))


# =============================================================================
# Security Configuration
# =============================================================================

# Keywords that always require user approval
DANGEROUS_KEYWORDS = [
    "deploy",
    "production",
    "push",
    "sudo",
    "rm -rf",
    "chmod",
    "chown",
    "curl",
    "wget",
    "eval",
    "exec",
]

# Allowed file extensions for sandbox operations
ALLOWED_EXTENSIONS = [
    ".py",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".sh",
]


# =============================================================================
# Display Configuration
# =============================================================================

# Main loop delay between iterations (seconds)
LOOP_DELAY = float(os.getenv("LOOP_DELAY", "1.0"))

# Maximum characters to display from Claude's reply
MAX_REPLY_LENGTH = int(os.getenv("MAX_REPLY_LENGTH", "2000"))


# =============================================================================
# Environment Configuration
# =============================================================================

# Current environment (development, staging, production, testing)
CURRENT_ENVIRONMENT = get_current_environment()

# Debug mode flag
DEBUG = is_debug_enabled()

# Log level
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Log format (verbose or json)
LOG_FORMAT = os.getenv("LOG_FORMAT", "verbose")

# Feature flags based on environment
RATE_LIMITING = os.getenv("RATE_LIMITING", "true").lower() in ("true", "1", "yes")
TEST_MODE = os.getenv("TEST_MODE", "false").lower() in ("true", "1", "yes")
DETAILED_ERRORS = os.getenv("DETAILED_ERRORS", "false").lower() in ("true", "1", "yes")


# =============================================================================
# Helper Functions
# =============================================================================

def get_config_dict() -> dict[str, Any]:
    """
    Get all configuration as a dictionary.

    Returns:
        Dictionary of all configuration values
    """
    return {
        # Paths
        "sandbox_dir": SANDBOX_DIR,
        "permissions_file": PERMISSIONS_FILE,
        "log_file": LOG_FILE,
        # Timeouts
        "ollama_timeout": OLLAMA_TIMEOUT,
        "command_timeout": COMMAND_TIMEOUT,
        # Retry
        "max_retries": MAX_RETRIES,
        "retry_delay": RETRY_DELAY,
        # Models
        "ollama_model": OLLAMA_MODEL,
        "claude_model": CLAUDE_MODEL,
        "claude_max_tokens": CLAUDE_MAX_TOKENS,
        # Display
        "loop_delay": LOOP_DELAY,
        "max_reply_length": MAX_REPLY_LENGTH,
        # Security
        "dangerous_keywords": DANGEROUS_KEYWORDS,
        "allowed_extensions": ALLOWED_EXTENSIONS,
        # Environment
        "environment": CURRENT_ENVIRONMENT.value,
        "debug": DEBUG,
        "log_level": LOG_LEVEL,
        "log_format": LOG_FORMAT,
        # Feature flags
        "rate_limiting": RATE_LIMITING,
        "test_mode": TEST_MODE,
        "detailed_errors": DETAILED_ERRORS,
    }


def is_dangerous_keyword(text: str) -> bool:
    """
    Check if text contains any dangerous keywords.

    Args:
        text: Text to check

    Returns:
        True if dangerous keyword found
    """
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in DANGEROUS_KEYWORDS)


def is_allowed_extension(path: str) -> bool:
    """
    Check if file extension is allowed.

    Args:
        path: File path to check

    Returns:
        True if extension is allowed
    """
    suffix = Path(path).suffix.lower()
    # Allow files without extension (like Makefile)
    if not suffix:
        return True
    return suffix in ALLOWED_EXTENSIONS


def ensure_directories() -> None:
    """Ensure required directories exist."""
    Path(SANDBOX_DIR).mkdir(parents=True, exist_ok=True)
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    Path(CONFIG_DIR).mkdir(parents=True, exist_ok=True)
