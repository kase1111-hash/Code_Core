"""
Environment management for Ollama Automation Harness.

This module provides environment-specific configuration loading,
supporting development, staging, production, and testing environments.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class Environment(Enum):
    """Supported environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


# Default environment if not specified
DEFAULT_ENVIRONMENT = Environment.DEVELOPMENT

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
ENVIRONMENTS_DIR = PROJECT_ROOT / "config" / "environments"


def get_current_environment() -> Environment:
    """
    Get the current environment from ENVIRONMENT variable.

    Returns:
        Current Environment enum value
    """
    env_name = os.getenv("ENVIRONMENT", DEFAULT_ENVIRONMENT.value).lower()

    try:
        return Environment(env_name)
    except ValueError:
        # Fall back to default if invalid environment specified
        return DEFAULT_ENVIRONMENT


def get_environment_file(env: Environment | None = None) -> Path:
    """
    Get the path to the environment-specific config file.

    Args:
        env: Environment to get config for (defaults to current)

    Returns:
        Path to the environment config file
    """
    if env is None:
        env = get_current_environment()

    return ENVIRONMENTS_DIR / f"{env.value}.env"


def load_environment(env: Environment | None = None, override: bool = True) -> bool:
    """
    Load environment-specific configuration.

    This loads the base .env file first, then overlays environment-specific
    settings from the config/environments/ directory.

    Args:
        env: Environment to load (defaults to current from ENVIRONMENT var)
        override: Whether to override existing environment variables

    Returns:
        True if environment was loaded successfully
    """
    # Load base .env file first (if exists)
    base_env_file = PROJECT_ROOT / ".env"
    if base_env_file.exists():
        load_dotenv(base_env_file, override=override)

    # Load environment-specific config
    env_file = get_environment_file(env)
    if env_file.exists():
        load_dotenv(env_file, override=override)
        return True

    return False


def is_development() -> bool:
    """Check if running in development environment."""
    return get_current_environment() == Environment.DEVELOPMENT


def is_staging() -> bool:
    """Check if running in staging environment."""
    return get_current_environment() == Environment.STAGING


def is_production() -> bool:
    """Check if running in production environment."""
    return get_current_environment() == Environment.PRODUCTION


def is_testing() -> bool:
    """Check if running in testing environment."""
    return get_current_environment() == Environment.TESTING


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled."""
    return os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")


def get_log_level() -> str:
    """Get the configured log level."""
    return os.getenv("LOG_LEVEL", "INFO").upper()


def get_environment_info() -> dict[str, Any]:
    """
    Get information about the current environment configuration.

    Returns:
        Dictionary with environment details
    """
    env = get_current_environment()
    env_file = get_environment_file(env)

    return {
        "environment": env.value,
        "environment_file": str(env_file),
        "environment_file_exists": env_file.exists(),
        "debug_enabled": is_debug_enabled(),
        "log_level": get_log_level(),
        "is_production": is_production(),
        "project_root": str(PROJECT_ROOT),
    }


def validate_production_config() -> list[str]:
    """
    Validate configuration for production environment.

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if not is_production():
        return errors

    # Check debug is disabled
    if is_debug_enabled():
        errors.append("DEBUG must be disabled in production")

    # Check detailed errors are disabled
    if os.getenv("DETAILED_ERRORS", "false").lower() in ("true", "1", "yes"):
        errors.append("DETAILED_ERRORS should be disabled in production")

    # Check test mode is disabled
    if os.getenv("TEST_MODE", "false").lower() in ("true", "1", "yes"):
        errors.append("TEST_MODE must be disabled in production")

    # Check logging level
    log_level = get_log_level()
    if log_level == "DEBUG":
        errors.append("LOG_LEVEL should not be DEBUG in production")

    return errors


def require_environment(required: Environment) -> None:
    """
    Raise an error if not running in the required environment.

    Args:
        required: The required environment

    Raises:
        RuntimeError: If not in the required environment
    """
    current = get_current_environment()
    if current != required:
        raise RuntimeError(
            f"This operation requires {required.value} environment, "
            f"but running in {current.value}"
        )


def ensure_not_production() -> None:
    """
    Raise an error if running in production.

    Use this to protect dangerous operations.

    Raises:
        RuntimeError: If running in production
    """
    if is_production():
        raise RuntimeError(
            "This operation is not allowed in production environment"
        )
