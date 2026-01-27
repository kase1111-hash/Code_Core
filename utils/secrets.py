"""
Secure configuration and secrets management module.

Provides:
- Secure loading and validation of secrets
- Environment-specific configuration
- API key masking for logs
- Configuration validation on startup
"""

from __future__ import annotations

import os
import re
import warnings
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class Environment(Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class SecretConfig:
    """Configuration for a secret value."""
    name: str
    env_var: str
    required: bool = False
    default: str | None = None
    min_length: int | None = None
    pattern: str | None = None
    description: str = ""


@dataclass
class ConfigValidationError:
    """Represents a configuration validation error."""
    key: str
    message: str
    severity: str = "error"  # error, warning


@dataclass
class SecureConfig:
    """
    Secure configuration container.

    Provides secure access to secrets with validation and masking.
    """
    environment: Environment = Environment.DEVELOPMENT
    _secrets: dict[str, str] = field(default_factory=dict)
    _loaded: bool = False
    _validation_errors: list[ConfigValidationError] = field(default_factory=list)

    # Secret definitions
    SECRET_DEFINITIONS: list[SecretConfig] = field(default_factory=lambda: [
        SecretConfig(
            name="anthropic_api_key",
            env_var="ANTHROPIC_API_KEY",
            required=False,  # Optional - falls back to Ollama
            min_length=20,
            pattern=r"^sk-ant-.*",
            description="Anthropic API key for Claude access",
        ),
        SecretConfig(
            name="sentry_dsn",
            env_var="SENTRY_DSN",
            required=False,
            pattern=r"^https://.*@.*\.ingest\.sentry\.io/.*",
            description="Sentry DSN for error tracking",
        ),
        SecretConfig(
            name="ollama_api_key",
            env_var="OLLAMA_API_KEY",
            required=False,
            description="Optional Ollama API key for remote instances",
        ),
    ])

    def load(self, env_file: str | None = None) -> SecureConfig:
        """
        Load secrets from environment.

        Args:
            env_file: Optional path to .env file

        Returns:
            Self for chaining
        """
        # Load from .env file if specified or exists
        if env_file:
            load_dotenv(env_file)
        else:
            # Try environment-specific .env files
            env_name = os.getenv("ENVIRONMENT", "development").lower()
            env_specific = Path(f".env.{env_name}")
            if env_specific.exists():
                load_dotenv(env_specific)
            load_dotenv()  # Load default .env

        # Set environment
        self.environment = self._detect_environment()

        # Load secrets
        for secret_def in self.SECRET_DEFINITIONS:
            value = os.getenv(secret_def.env_var)
            if value:
                self._secrets[secret_def.name] = value

        self._loaded = True
        return self

    def validate(self) -> list[ConfigValidationError]:
        """
        Validate all configuration.

        Returns:
            List of validation errors
        """
        self._validation_errors = []

        for secret_def in self.SECRET_DEFINITIONS:
            value = self._secrets.get(secret_def.name)

            # Check required
            if secret_def.required and not value:
                self._validation_errors.append(ConfigValidationError(
                    key=secret_def.env_var,
                    message=f"Required secret {secret_def.env_var} is not set",
                    severity="error",
                ))
                continue

            if value:
                # Check minimum length
                if secret_def.min_length and len(value) < secret_def.min_length:
                    self._validation_errors.append(ConfigValidationError(
                        key=secret_def.env_var,
                        message=f"{secret_def.env_var} is too short (min {secret_def.min_length} chars)",
                        severity="error",
                    ))

                # Check pattern
                if secret_def.pattern and not re.match(secret_def.pattern, value):
                    self._validation_errors.append(ConfigValidationError(
                        key=secret_def.env_var,
                        message=f"{secret_def.env_var} does not match expected format",
                        severity="warning",
                    ))

        # Environment-specific validation
        if self.environment == Environment.PRODUCTION:
            # Production should have API key
            if not self.get("anthropic_api_key"):
                self._validation_errors.append(ConfigValidationError(
                    key="ANTHROPIC_API_KEY",
                    message="Production environment should have ANTHROPIC_API_KEY set",
                    severity="warning",
                ))

        return self._validation_errors

    def get(self, name: str, default: str | None = None) -> str | None:
        """
        Get a secret value.

        Args:
            name: Secret name
            default: Default value if not set

        Returns:
            Secret value or default
        """
        return self._secrets.get(name, default)

    def has(self, name: str) -> bool:
        """
        Check if a secret is set.

        Args:
            name: Secret name

        Returns:
            True if secret is set and non-empty
        """
        return bool(self._secrets.get(name))

    def get_masked(self, name: str) -> str:
        """
        Get a masked version of a secret for logging.

        Args:
            name: Secret name

        Returns:
            Masked value (e.g., "sk-ant-***...***")
        """
        value = self._secrets.get(name)
        if not value:
            return "<not set>"
        return mask_secret(value)

    def _detect_environment(self) -> Environment:
        """Detect environment from env vars."""
        env_str = os.getenv("ENVIRONMENT", "development").lower()
        try:
            return Environment(env_str)
        except ValueError:
            return Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == Environment.DEVELOPMENT

    def to_safe_dict(self) -> dict[str, Any]:
        """
        Get configuration as dictionary with masked secrets.

        Returns:
            Safe dictionary for logging
        """
        return {
            "environment": self.environment.value,
            "secrets": {
                name: self.get_masked(name)
                for name in self._secrets
            },
            "loaded": self._loaded,
        }


# =============================================================================
# Secret masking utilities
# =============================================================================


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """
    Mask a secret value for safe logging.

    Args:
        value: Secret value to mask
        visible_chars: Number of characters to show at start and end

    Returns:
        Masked string (e.g., "sk-a...xyz")
    """
    if not value:
        return "<empty>"

    if len(value) <= visible_chars * 2:
        return "*" * len(value)

    start = value[:visible_chars]
    end = value[-visible_chars:]
    return f"{start}...{end}"


def mask_url_credentials(url: str) -> str:
    """
    Mask credentials in a URL.

    Args:
        url: URL that may contain credentials

    Returns:
        URL with credentials masked
    """
    # Match URLs with credentials: scheme://user:pass@host
    pattern = r"(https?://)([^:]+):([^@]+)@"
    return re.sub(pattern, r"\1***:***@", url)


def mask_dict_secrets(data: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively mask secrets in a dictionary.

    Args:
        data: Dictionary to process

    Returns:
        Dictionary with secrets masked
    """
    sensitive_patterns = [
        r".*api[_-]?key.*",
        r".*secret.*",
        r".*password.*",
        r".*token.*",
        r".*credential.*",
        r".*auth.*",
        r".*dsn.*",
    ]

    def is_sensitive(key: str) -> bool:
        key_lower = key.lower()
        return any(re.match(p, key_lower) for p in sensitive_patterns)

    masked = {}
    for key, value in data.items():
        if isinstance(value, dict):
            masked[key] = mask_dict_secrets(value)
        elif is_sensitive(key) and isinstance(value, str):
            masked[key] = mask_secret(value)
        else:
            masked[key] = value

    return masked


# =============================================================================
# Configuration validation
# =============================================================================


def validate_config_on_startup() -> list[ConfigValidationError]:
    """
    Validate all configuration on startup.

    Returns:
        List of validation errors
    """
    errors = []

    # Validate required directories exist or can be created
    required_dirs = [
        os.getenv("SANDBOX_DIR", "./sandbox"),
        os.getenv("LOG_DIR", "./logs"),
    ]

    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                errors.append(ConfigValidationError(
                    key=dir_path,
                    message=f"Cannot create directory {dir_path}: {e}",
                    severity="error",
                ))

    # Validate timeout values are positive
    timeout_vars = [
        ("OLLAMA_TIMEOUT", 60),
        ("COMMAND_TIMEOUT", 30),
    ]

    for var_name, default in timeout_vars:
        try:
            value = int(os.getenv(var_name, str(default)))
            if value <= 0:
                errors.append(ConfigValidationError(
                    key=var_name,
                    message=f"{var_name} must be positive (got {value})",
                    severity="error",
                ))
        except ValueError:
            errors.append(ConfigValidationError(
                key=var_name,
                message=f"{var_name} must be an integer",
                severity="error",
            ))

    return errors


def check_environment_security() -> list[str]:
    """
    Check for security issues in the current environment.

    Returns:
        List of security warnings
    """
    warnings_list = []

    # Check if running as root
    if os.geteuid() == 0:
        warnings_list.append(
            "Running as root is not recommended for security reasons"
        )

    # Check for debug mode in production
    env = os.getenv("ENVIRONMENT", "development").lower()
    debug = os.getenv("DEBUG", "false").lower() == "true"

    if env == "production" and debug:
        warnings_list.append(
            "DEBUG mode is enabled in production environment"
        )

    # Check for insecure .env file permissions
    env_file = Path(".env")
    if env_file.exists():
        mode = env_file.stat().st_mode & 0o777
        if mode & 0o077:  # Group or others can read
            warnings_list.append(
                f".env file has insecure permissions ({oct(mode)}), "
                "should be 600 or 400"
            )

    return warnings_list


# =============================================================================
# Global configuration instance
# =============================================================================


_config: SecureConfig | None = None


def get_secure_config() -> SecureConfig:
    """
    Get the global secure configuration instance.

    Returns:
        SecureConfig instance
    """
    global _config
    if _config is None:
        _config = SecureConfig()
        _config.load()
    return _config


def init_secure_config(env_file: str | None = None) -> SecureConfig:
    """
    Initialize secure configuration.

    Args:
        env_file: Optional path to .env file

    Returns:
        Initialized SecureConfig
    """
    global _config
    _config = SecureConfig()
    _config.load(env_file)

    # Validate
    errors = _config.validate()
    errors.extend(validate_config_on_startup())

    # Log warnings
    for error in errors:
        if error.severity == "warning":
            warnings.warn(f"Config warning: {error.message}", stacklevel=2)
        else:
            warnings.warn(f"Config error: {error.message}", stacklevel=2)

    # Check security
    security_warnings = check_environment_security()
    for warning in security_warnings:
        warnings.warn(f"Security: {warning}", stacklevel=2)

    return _config


def get_api_key(name: str = "anthropic_api_key") -> str | None:
    """
    Get an API key securely.

    Args:
        name: Key name

    Returns:
        API key value or None
    """
    config = get_secure_config()
    return config.get(name)


def has_api_key(name: str = "anthropic_api_key") -> bool:
    """
    Check if an API key is configured.

    Args:
        name: Key name

    Returns:
        True if key is set
    """
    config = get_secure_config()
    return config.has(name)
