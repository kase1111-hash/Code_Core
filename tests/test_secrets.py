"""
Unit tests for utils/secrets.py
"""

import os
from unittest.mock import patch

from utils.secrets import (
    ConfigValidationError,
    Environment,
    SecureConfig,
    check_environment_security,
    get_api_key,
    get_secure_config,
    has_api_key,
    init_secure_config,
    mask_dict_secrets,
    mask_secret,
    mask_url_credentials,
    validate_config_on_startup,
)


class TestEnvironment:
    """Tests for Environment enum."""

    def test_environment_values(self):
        """Test environment enum values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"
        assert Environment.TESTING.value == "testing"


class TestConfigValidationError:
    """Tests for ConfigValidationError dataclass."""

    def test_error_creation(self):
        """Test error creation with all fields."""
        error = ConfigValidationError(
            key="API_KEY",
            message="Key not set",
            severity="error",
        )
        assert error.key == "API_KEY"
        assert error.message == "Key not set"
        assert error.severity == "error"

    def test_error_default_severity(self):
        """Test default severity is error."""
        error = ConfigValidationError(key="KEY", message="msg")
        assert error.severity == "error"


class TestSecureConfig:
    """Tests for SecureConfig class."""

    def test_default_environment(self):
        """Test default environment is development."""
        config = SecureConfig()
        assert config.environment == Environment.DEVELOPMENT

    def test_load_sets_loaded_flag(self):
        """Test that load sets the loaded flag."""
        config = SecureConfig()
        config.load()
        assert config._loaded is True

    def test_get_nonexistent_secret(self):
        """Test getting nonexistent secret returns None."""
        config = SecureConfig()
        assert config.get("nonexistent") is None

    def test_get_with_default(self):
        """Test getting nonexistent secret with default."""
        config = SecureConfig()
        assert config.get("nonexistent", "default") == "default"

    def test_has_nonexistent_secret(self):
        """Test has returns False for nonexistent secret."""
        config = SecureConfig()
        assert config.has("nonexistent") is False

    def test_get_masked_not_set(self):
        """Test get_masked for unset secret."""
        config = SecureConfig()
        assert config.get_masked("nonexistent") == "<not set>"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key-12345678901234567890"})
    def test_load_from_environment(self):
        """Test loading secret from environment."""
        config = SecureConfig()
        config.load()
        assert config.get("anthropic_api_key") == "sk-ant-test-key-12345678901234567890"

    def test_to_safe_dict(self):
        """Test to_safe_dict returns masked secrets."""
        config = SecureConfig()
        config._secrets["test_key"] = "secret_value"
        safe = config.to_safe_dict()
        assert "environment" in safe
        assert "secrets" in safe
        assert "loaded" in safe

    def test_is_production(self):
        """Test is_production property."""
        config = SecureConfig()
        config.environment = Environment.PRODUCTION
        assert config.is_production is True
        assert config.is_development is False

    def test_is_development(self):
        """Test is_development property."""
        config = SecureConfig()
        config.environment = Environment.DEVELOPMENT
        assert config.is_development is True
        assert config.is_production is False


class TestSecureConfigValidation:
    """Tests for SecureConfig validation."""

    def test_validate_empty_config(self):
        """Test validation of empty config."""
        config = SecureConfig()
        errors = config.validate()
        # No required secrets, so should pass
        assert isinstance(errors, list)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "short"})
    def test_validate_short_key(self):
        """Test validation catches short API key."""
        config = SecureConfig()
        config.load()
        errors = config.validate()
        # Should have error about min length
        assert any("too short" in e.message for e in errors)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "invalid-prefix-12345678901234567890"})
    def test_validate_wrong_pattern(self):
        """Test validation catches wrong pattern."""
        config = SecureConfig()
        config.load()
        errors = config.validate()
        # Should have warning about format
        assert any("format" in e.message.lower() for e in errors)


class TestMaskSecret:
    """Tests for mask_secret function."""

    def test_mask_short_secret(self):
        """Test masking short secret."""
        result = mask_secret("short")
        assert result == "*****"

    def test_mask_long_secret(self):
        """Test masking long secret."""
        result = mask_secret("sk-ant-very-long-api-key-here")
        assert result.startswith("sk-a")
        assert result.endswith("here")
        assert "..." in result

    def test_mask_empty_secret(self):
        """Test masking empty secret."""
        result = mask_secret("")
        assert result == "<empty>"

    def test_mask_none_secret(self):
        """Test masking None secret."""
        result = mask_secret(None)
        assert result == "<empty>"

    def test_mask_custom_visible_chars(self):
        """Test masking with custom visible chars."""
        result = mask_secret("abcdefghijklmnop", visible_chars=2)
        assert result.startswith("ab")
        assert result.endswith("op")


class TestMaskUrlCredentials:
    """Tests for mask_url_credentials function."""

    def test_mask_url_with_credentials(self):
        """Test masking URL with credentials."""
        url = "https://user:password@example.com/path"
        result = mask_url_credentials(url)
        assert "***:***@" in result
        assert "password" not in result

    def test_mask_url_without_credentials(self):
        """Test URL without credentials unchanged."""
        url = "https://example.com/path"
        result = mask_url_credentials(url)
        assert result == url

    def test_mask_http_url(self):
        """Test masking HTTP URL."""
        url = "http://admin:secret@localhost:8080"
        result = mask_url_credentials(url)
        assert "***:***@" in result


class TestMaskDictSecrets:
    """Tests for mask_dict_secrets function."""

    def test_mask_api_key_field(self):
        """Test masking api_key field."""
        data = {"api_key": "sk-ant-secret-key-here"}
        result = mask_dict_secrets(data)
        assert result["api_key"] != "sk-ant-secret-key-here"
        assert "..." in result["api_key"]

    def test_mask_password_field(self):
        """Test masking password field."""
        data = {"password": "mysecretpassword"}
        result = mask_dict_secrets(data)
        assert result["password"] != "mysecretpassword"

    def test_mask_nested_secrets(self):
        """Test masking nested secrets."""
        data = {
            "config": {
                "api_key": "secret-key",
                "name": "test",
            }
        }
        result = mask_dict_secrets(data)
        assert result["config"]["api_key"] != "secret-key"
        assert result["config"]["name"] == "test"

    def test_preserve_non_sensitive(self):
        """Test non-sensitive fields are preserved."""
        data = {"username": "user", "email": "user@example.com"}
        result = mask_dict_secrets(data)
        assert result["username"] == "user"
        assert result["email"] == "user@example.com"

    def test_mask_token_field(self):
        """Test masking token field."""
        data = {"auth_token": "bearer-token-123"}
        result = mask_dict_secrets(data)
        assert "bearer-token-123" not in str(result["auth_token"])


class TestValidateConfigOnStartup:
    """Tests for validate_config_on_startup function."""

    def test_validates_directories(self, tmp_path):
        """Test that required directories are validated."""
        with patch.dict(os.environ, {"SANDBOX_DIR": str(tmp_path / "sandbox")}):
            errors = validate_config_on_startup()
            # Should create directory or report error
            assert isinstance(errors, list)

    @patch.dict(os.environ, {"OLLAMA_TIMEOUT": "-5"})
    def test_validates_negative_timeout(self):
        """Test validation catches negative timeout."""
        errors = validate_config_on_startup()
        assert any("positive" in e.message.lower() for e in errors)

    @patch.dict(os.environ, {"COMMAND_TIMEOUT": "not_a_number"})
    def test_validates_non_integer_timeout(self):
        """Test validation catches non-integer timeout."""
        errors = validate_config_on_startup()
        assert any("integer" in e.message.lower() for e in errors)


class TestCheckEnvironmentSecurity:
    """Tests for check_environment_security function."""

    @patch.dict(os.environ, {"ENVIRONMENT": "production", "DEBUG": "true"})
    def test_warns_debug_in_production(self):
        """Test warning for debug mode in production."""
        warnings = check_environment_security()
        assert any("DEBUG" in w for w in warnings)

    @patch.dict(os.environ, {"ENVIRONMENT": "development", "DEBUG": "true"})
    def test_no_warning_debug_in_development(self):
        """Test no warning for debug in development."""
        warnings = check_environment_security()
        assert not any("DEBUG" in w for w in warnings)


class TestGlobalConfigFunctions:
    """Tests for global configuration functions."""

    def test_init_and_get_secure_config(self):
        """Test init and get secure config."""
        # Reset global
        import utils.secrets
        utils.secrets._config = None

        config = init_secure_config()
        assert config is not None

        retrieved = get_secure_config()
        assert retrieved is config

    def test_get_api_key_not_set(self):
        """Test get_api_key when not set."""
        # Reset global
        import utils.secrets
        utils.secrets._config = None

        key = get_api_key("nonexistent_key")
        assert key is None

    def test_has_api_key_not_set(self):
        """Test has_api_key when not set."""
        # Reset global
        import utils.secrets
        utils.secrets._config = None

        result = has_api_key("nonexistent_key")
        assert result is False
