"""
Unit tests for utils/config.py
"""

from utils.config import (
    ALLOWED_EXTENSIONS,
    DANGEROUS_KEYWORDS,
    get_config_dict,
    is_allowed_extension,
    is_dangerous_keyword,
)


class TestIsDangerousKeyword:
    """Tests for is_dangerous_keyword function."""

    def test_dangerous_keywords_detected(self):
        """Test that dangerous keywords are detected."""
        assert is_dangerous_keyword("sudo rm -rf /") is True
        assert is_dangerous_keyword("deploy to production") is True
        assert is_dangerous_keyword("git push origin main") is True
        assert is_dangerous_keyword("chmod 777 file") is True

    def test_safe_text_allowed(self):
        """Test that safe text passes."""
        assert is_dangerous_keyword("ls -la") is False
        assert is_dangerous_keyword("cat file.txt") is False
        assert is_dangerous_keyword("python script.py") is False

    def test_case_insensitive(self):
        """Test that detection is case-insensitive."""
        assert is_dangerous_keyword("SUDO command") is True
        assert is_dangerous_keyword("Deploy Application") is True

    def test_partial_match(self):
        """Test that partial matches work."""
        assert is_dangerous_keyword("this is production data") is True
        assert is_dangerous_keyword("evaluate expression") is True  # "eval" is in the keyword list

    def test_all_keywords_detected(self):
        """Test that all defined dangerous keywords are detected."""
        for keyword in DANGEROUS_KEYWORDS:
            assert is_dangerous_keyword(keyword) is True, f"Keyword '{keyword}' not detected"


class TestIsAllowedExtension:
    """Tests for is_allowed_extension function."""

    def test_allowed_extensions(self):
        """Test that allowed extensions pass."""
        assert is_allowed_extension("test.py") is True
        assert is_allowed_extension("config.yaml") is True
        assert is_allowed_extension("config.yml") is True
        assert is_allowed_extension("data.json") is True
        assert is_allowed_extension("readme.md") is True
        assert is_allowed_extension("script.sh") is True
        assert is_allowed_extension("notes.txt") is True

    def test_disallowed_extensions(self):
        """Test that disallowed extensions fail."""
        assert is_allowed_extension("program.exe") is False
        assert is_allowed_extension("library.dll") is False
        assert is_allowed_extension("binary.bin") is False

    def test_no_extension_allowed(self):
        """Test that files without extension are allowed."""
        assert is_allowed_extension("Makefile") is True
        assert is_allowed_extension("Dockerfile") is True

    def test_case_insensitive(self):
        """Test that extension checking is case-insensitive."""
        assert is_allowed_extension("test.PY") is True
        assert is_allowed_extension("test.JSON") is True

    def test_all_defined_extensions(self):
        """Test all defined allowed extensions."""
        for ext in ALLOWED_EXTENSIONS:
            filename = f"test{ext}"
            assert is_allowed_extension(filename) is True, f"Extension '{ext}' not allowed"


class TestGetConfigDict:
    """Tests for get_config_dict function."""

    def test_returns_dict(self):
        """Test that config dict is returned."""
        config = get_config_dict()
        assert isinstance(config, dict)

    def test_contains_required_keys(self):
        """Test that config contains required keys."""
        config = get_config_dict()
        required_keys = [
            "sandbox_dir",
            "permissions_file",
            "log_file",
            "ollama_timeout",
            "command_timeout",
            "max_retries",
            "ollama_model",
            "claude_model",
            "dangerous_keywords",
            "allowed_extensions",
        ]
        for key in required_keys:
            assert key in config, f"Missing required key: {key}"

    def test_timeout_values_positive(self):
        """Test that timeout values are positive integers."""
        config = get_config_dict()
        assert config["ollama_timeout"] > 0
        assert config["command_timeout"] > 0

    def test_dangerous_keywords_is_list(self):
        """Test that dangerous_keywords is a list."""
        config = get_config_dict()
        assert isinstance(config["dangerous_keywords"], list)
        assert len(config["dangerous_keywords"]) > 0

    def test_allowed_extensions_is_list(self):
        """Test that allowed_extensions is a list."""
        config = get_config_dict()
        assert isinstance(config["allowed_extensions"], list)
        assert len(config["allowed_extensions"]) > 0
