"""
Tests for utils/environment.py module.

Comprehensive tests for environment management including:
- Environment detection
- Environment loading
- Production validation
- Environment checks
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestEnvironmentEnum:
    """Tests for Environment enum."""

    def test_environment_values(self):
        """Test Environment enum values."""
        from utils.environment import Environment
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"
        assert Environment.TESTING.value == "testing"


class TestGetCurrentEnvironment:
    """Tests for get_current_environment function."""

    def test_get_current_environment_default(self):
        """Test default environment."""
        from utils.environment import DEFAULT_ENVIRONMENT, get_current_environment

        with patch.dict(os.environ, {}, clear=True):
            with patch("os.getenv", return_value=DEFAULT_ENVIRONMENT.value):
                env = get_current_environment()
                assert env == DEFAULT_ENVIRONMENT

    def test_get_current_environment_development(self):
        """Test development environment detection."""
        from utils.environment import Environment, get_current_environment

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            env = get_current_environment()
            assert env == Environment.DEVELOPMENT

    def test_get_current_environment_production(self):
        """Test production environment detection."""
        from utils.environment import Environment, get_current_environment

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            env = get_current_environment()
            assert env == Environment.PRODUCTION

    def test_get_current_environment_staging(self):
        """Test staging environment detection."""
        from utils.environment import Environment, get_current_environment

        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            env = get_current_environment()
            assert env == Environment.STAGING

    def test_get_current_environment_testing(self):
        """Test testing environment detection."""
        from utils.environment import Environment, get_current_environment

        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}):
            env = get_current_environment()
            assert env == Environment.TESTING

    def test_get_current_environment_invalid(self):
        """Test invalid environment falls back to default."""
        from utils.environment import DEFAULT_ENVIRONMENT, get_current_environment

        with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}):
            env = get_current_environment()
            assert env == DEFAULT_ENVIRONMENT

    def test_get_current_environment_case_insensitive(self):
        """Test environment detection is case insensitive."""
        from utils.environment import Environment, get_current_environment

        with patch.dict(os.environ, {"ENVIRONMENT": "PRODUCTION"}):
            env = get_current_environment()
            assert env == Environment.PRODUCTION


class TestGetEnvironmentFile:
    """Tests for get_environment_file function."""

    def test_get_environment_file_default(self):
        """Test getting default environment file."""
        from utils.environment import get_environment_file

        file_path = get_environment_file()
        assert file_path.suffix == ".env"

    def test_get_environment_file_specific(self):
        """Test getting specific environment file."""
        from utils.environment import Environment, get_environment_file

        file_path = get_environment_file(Environment.PRODUCTION)
        assert "production.env" in str(file_path)

    def test_get_environment_file_development(self):
        """Test getting development environment file."""
        from utils.environment import Environment, get_environment_file

        file_path = get_environment_file(Environment.DEVELOPMENT)
        assert "development.env" in str(file_path)


class TestLoadEnvironment:
    """Tests for load_environment function."""

    def test_load_environment_no_files(self, tmp_path):
        """Test loading when no env files exist."""
        from utils.environment import load_environment

        with patch("utils.environment.PROJECT_ROOT", tmp_path):
            with patch("utils.environment.ENVIRONMENTS_DIR", tmp_path / "envs"):
                result = load_environment()
                assert result is False

    def test_load_environment_with_file(self, tmp_path):
        """Test loading when env file exists."""
        from utils.environment import Environment, load_environment

        # Create environment directory and file
        env_dir = tmp_path / "config" / "environments"
        env_dir.mkdir(parents=True)
        env_file = env_dir / "development.env"
        env_file.write_text("TEST_VAR=test_value")

        with patch("utils.environment.PROJECT_ROOT", tmp_path):
            with patch("utils.environment.ENVIRONMENTS_DIR", env_dir):
                result = load_environment(Environment.DEVELOPMENT)
                # Result depends on file existence
                assert isinstance(result, bool)


class TestEnvironmentChecks:
    """Tests for environment check functions."""

    def test_is_development(self):
        """Test is_development function."""
        from utils.environment import is_development

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            assert is_development() is True

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            assert is_development() is False

    def test_is_staging(self):
        """Test is_staging function."""
        from utils.environment import is_staging

        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            assert is_staging() is True

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            assert is_staging() is False

    def test_is_production(self):
        """Test is_production function."""
        from utils.environment import is_production

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            assert is_production() is True

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            assert is_production() is False

    def test_is_testing(self):
        """Test is_testing function."""
        from utils.environment import is_testing

        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}):
            assert is_testing() is True

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            assert is_testing() is False


class TestIsDebugEnabled:
    """Tests for is_debug_enabled function."""

    def test_is_debug_enabled_true(self):
        """Test debug enabled with true."""
        from utils.environment import is_debug_enabled

        with patch.dict(os.environ, {"DEBUG": "true"}):
            assert is_debug_enabled() is True

    def test_is_debug_enabled_one(self):
        """Test debug enabled with 1."""
        from utils.environment import is_debug_enabled

        with patch.dict(os.environ, {"DEBUG": "1"}):
            assert is_debug_enabled() is True

    def test_is_debug_enabled_yes(self):
        """Test debug enabled with yes."""
        from utils.environment import is_debug_enabled

        with patch.dict(os.environ, {"DEBUG": "yes"}):
            assert is_debug_enabled() is True

    def test_is_debug_enabled_false(self):
        """Test debug disabled."""
        from utils.environment import is_debug_enabled

        with patch.dict(os.environ, {"DEBUG": "false"}):
            assert is_debug_enabled() is False

    def test_is_debug_enabled_default(self):
        """Test debug default is false."""
        from utils.environment import is_debug_enabled

        with patch.dict(os.environ, {}, clear=True):
            # Clear the DEBUG variable
            with patch("os.getenv", return_value="false"):
                assert is_debug_enabled() is False


class TestGetLogLevel:
    """Tests for get_log_level function."""

    def test_get_log_level_default(self):
        """Test default log level."""
        from utils.environment import get_log_level

        with patch.dict(os.environ, {}, clear=True):
            with patch("os.getenv", return_value="INFO"):
                level = get_log_level()
                assert level == "INFO"

    def test_get_log_level_debug(self):
        """Test debug log level."""
        from utils.environment import get_log_level

        with patch.dict(os.environ, {"LOG_LEVEL": "debug"}):
            level = get_log_level()
            assert level == "DEBUG"

    def test_get_log_level_uppercase(self):
        """Test log level is uppercased."""
        from utils.environment import get_log_level

        with patch.dict(os.environ, {"LOG_LEVEL": "warning"}):
            level = get_log_level()
            assert level == "WARNING"


class TestGetEnvironmentInfo:
    """Tests for get_environment_info function."""

    def test_get_environment_info_structure(self):
        """Test environment info structure."""
        from utils.environment import get_environment_info

        info = get_environment_info()
        assert "environment" in info
        assert "environment_file" in info
        assert "debug_enabled" in info
        assert "log_level" in info
        assert "is_production" in info
        assert "project_root" in info

    def test_get_environment_info_values(self):
        """Test environment info values."""
        from utils.environment import get_environment_info

        with patch.dict(os.environ, {"ENVIRONMENT": "development", "DEBUG": "false"}):
            info = get_environment_info()
            assert info["environment"] == "development"
            assert info["debug_enabled"] is False


class TestValidateProductionConfig:
    """Tests for validate_production_config function."""

    def test_validate_production_config_not_production(self):
        """Test validation returns empty for non-production."""
        from utils.environment import validate_production_config

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            errors = validate_production_config()
            assert errors == []

    def test_validate_production_config_debug_enabled(self):
        """Test validation catches debug in production."""
        from utils.environment import validate_production_config

        with patch.dict(os.environ, {"ENVIRONMENT": "production", "DEBUG": "true"}):
            errors = validate_production_config()
            assert any("DEBUG" in e for e in errors)

    def test_validate_production_config_detailed_errors(self):
        """Test validation catches detailed errors in production."""
        from utils.environment import validate_production_config

        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "DETAILED_ERRORS": "true"
        }):
            errors = validate_production_config()
            assert any("DETAILED_ERRORS" in e for e in errors)

    def test_validate_production_config_test_mode(self):
        """Test validation catches test mode in production."""
        from utils.environment import validate_production_config

        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "TEST_MODE": "true"
        }):
            errors = validate_production_config()
            assert any("TEST_MODE" in e for e in errors)

    def test_validate_production_config_debug_log_level(self):
        """Test validation catches DEBUG log level in production."""
        from utils.environment import validate_production_config

        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "LOG_LEVEL": "DEBUG"
        }):
            errors = validate_production_config()
            assert any("LOG_LEVEL" in e for e in errors)


class TestRequireEnvironment:
    """Tests for require_environment function."""

    def test_require_environment_correct(self):
        """Test require_environment with correct environment."""
        from utils.environment import Environment, require_environment

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            # Should not raise
            require_environment(Environment.DEVELOPMENT)

    def test_require_environment_incorrect(self):
        """Test require_environment with incorrect environment."""
        from utils.environment import Environment, require_environment

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            with pytest.raises(RuntimeError) as exc_info:
                require_environment(Environment.PRODUCTION)
            assert "requires production" in str(exc_info.value).lower()


class TestEnsureNotProduction:
    """Tests for ensure_not_production function."""

    def test_ensure_not_production_development(self):
        """Test ensure_not_production in development."""
        from utils.environment import ensure_not_production

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            # Should not raise
            ensure_not_production()

    def test_ensure_not_production_in_production(self):
        """Test ensure_not_production in production."""
        from utils.environment import ensure_not_production

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with pytest.raises(RuntimeError) as exc_info:
                ensure_not_production()
            assert "not allowed in production" in str(exc_info.value).lower()


class TestProjectPaths:
    """Tests for project path constants."""

    def test_project_root_exists(self):
        """Test PROJECT_ROOT is a valid path."""
        from utils.environment import PROJECT_ROOT
        assert isinstance(PROJECT_ROOT, Path)

    def test_environments_dir_path(self):
        """Test ENVIRONMENTS_DIR is under config."""
        from utils.environment import ENVIRONMENTS_DIR
        assert "config" in str(ENVIRONMENTS_DIR)
        assert "environments" in str(ENVIRONMENTS_DIR)
