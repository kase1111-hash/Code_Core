"""
Tests for utils/version.py module.

Comprehensive tests for version management including:
- SemanticVersion parsing and comparison
- Version bumping
- Version formatting
- Compatibility checking
"""

import pytest


class TestVersionConstants:
    """Tests for version constants."""

    def test_version_exists(self):
        """Test __version__ is defined."""
        from utils.version import __version__
        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_version_components(self):
        """Test version components are defined."""
        from utils.version import VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH
        assert isinstance(VERSION_MAJOR, int)
        assert isinstance(VERSION_MINOR, int)
        assert isinstance(VERSION_PATCH, int)

    def test_app_metadata(self):
        """Test app metadata is defined."""
        from utils.version import APP_AUTHOR, APP_LICENSE, APP_NAME
        assert APP_NAME is not None
        assert APP_AUTHOR is not None
        assert APP_LICENSE is not None


class TestSemanticVersion:
    """Tests for SemanticVersion class."""

    def test_semantic_version_creation(self):
        """Test SemanticVersion creation."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 2, 3)
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_semantic_version_with_prerelease(self):
        """Test SemanticVersion with prerelease."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 0, 0, prerelease="beta.1")
        assert v.prerelease == "beta.1"
        assert v.is_prerelease is True

    def test_semantic_version_with_build(self):
        """Test SemanticVersion with build metadata."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 0, 0, build="build.123")
        assert v.build == "build.123"

    def test_semantic_version_str(self):
        """Test SemanticVersion string representation."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 2, 3)
        assert str(v) == "1.2.3"

    def test_semantic_version_str_with_prerelease(self):
        """Test SemanticVersion string with prerelease."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 0, 0, prerelease="alpha")
        assert str(v) == "1.0.0-alpha"

    def test_semantic_version_str_with_build(self):
        """Test SemanticVersion string with build."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 0, 0, build="123")
        assert str(v) == "1.0.0+123"

    def test_semantic_version_str_full(self):
        """Test SemanticVersion string with all components."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 0, 0, prerelease="rc.1", build="456")
        assert str(v) == "1.0.0-rc.1+456"

    def test_semantic_version_repr(self):
        """Test SemanticVersion repr."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 2, 3)
        repr_str = repr(v)
        assert "SemanticVersion" in repr_str
        assert "major=1" in repr_str

    def test_semantic_version_negative_raises(self):
        """Test negative version components raise error."""
        from utils.version import SemanticVersion
        with pytest.raises(ValueError):
            SemanticVersion(-1, 0, 0)

    def test_semantic_version_parse(self):
        """Test SemanticVersion parsing."""
        from utils.version import SemanticVersion
        v = SemanticVersion.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_semantic_version_parse_with_v_prefix(self):
        """Test parsing with v prefix."""
        from utils.version import SemanticVersion
        v = SemanticVersion.parse("v1.2.3")
        assert v.major == 1

    def test_semantic_version_parse_with_prerelease(self):
        """Test parsing with prerelease."""
        from utils.version import SemanticVersion
        v = SemanticVersion.parse("1.0.0-beta.1")
        assert v.prerelease == "beta.1"

    def test_semantic_version_parse_with_build(self):
        """Test parsing with build metadata."""
        from utils.version import SemanticVersion
        v = SemanticVersion.parse("1.0.0+build.123")
        assert v.build == "build.123"

    def test_semantic_version_parse_invalid(self):
        """Test parsing invalid version raises error."""
        from utils.version import SemanticVersion
        with pytest.raises(ValueError):
            SemanticVersion.parse("invalid")

    def test_semantic_version_equality(self):
        """Test SemanticVersion equality."""
        from utils.version import SemanticVersion
        v1 = SemanticVersion(1, 2, 3)
        v2 = SemanticVersion(1, 2, 3)
        assert v1 == v2

    def test_semantic_version_equality_ignores_build(self):
        """Test equality ignores build metadata."""
        from utils.version import SemanticVersion
        v1 = SemanticVersion(1, 0, 0, build="111")
        v2 = SemanticVersion(1, 0, 0, build="222")
        assert v1 == v2

    def test_semantic_version_inequality(self):
        """Test SemanticVersion inequality."""
        from utils.version import SemanticVersion
        v1 = SemanticVersion(1, 0, 0)
        v2 = SemanticVersion(2, 0, 0)
        assert v1 != v2

    def test_semantic_version_less_than(self):
        """Test SemanticVersion less than comparison."""
        from utils.version import SemanticVersion
        v1 = SemanticVersion(1, 0, 0)
        v2 = SemanticVersion(2, 0, 0)
        assert v1 < v2

    def test_semantic_version_prerelease_precedence(self):
        """Test prerelease has lower precedence."""
        from utils.version import SemanticVersion
        v1 = SemanticVersion(1, 0, 0, prerelease="alpha")
        v2 = SemanticVersion(1, 0, 0)
        assert v1 < v2

    def test_semantic_version_prerelease_comparison(self):
        """Test prerelease version comparison."""
        from utils.version import SemanticVersion
        v1 = SemanticVersion(1, 0, 0, prerelease="alpha")
        v2 = SemanticVersion(1, 0, 0, prerelease="beta")
        assert v1 < v2

    def test_semantic_version_prerelease_numeric(self):
        """Test numeric prerelease comparison."""
        from utils.version import SemanticVersion
        v1 = SemanticVersion(1, 0, 0, prerelease="rc.1")
        v2 = SemanticVersion(1, 0, 0, prerelease="rc.2")
        assert v1 < v2

    def test_semantic_version_hash(self):
        """Test SemanticVersion is hashable."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 0, 0)
        version_set = {v}
        assert v in version_set

    def test_semantic_version_bump_major(self):
        """Test bumping major version."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 2, 3)
        bumped = v.bump_major()
        assert bumped.major == 2
        assert bumped.minor == 0
        assert bumped.patch == 0

    def test_semantic_version_bump_minor(self):
        """Test bumping minor version."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 2, 3)
        bumped = v.bump_minor()
        assert bumped.major == 1
        assert bumped.minor == 3
        assert bumped.patch == 0

    def test_semantic_version_bump_patch(self):
        """Test bumping patch version."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 2, 3)
        bumped = v.bump_patch()
        assert bumped.major == 1
        assert bumped.minor == 2
        assert bumped.patch == 4

    def test_semantic_version_with_prerelease_method(self):
        """Test with_prerelease method."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 0, 0)
        v_pre = v.with_prerelease("beta")
        assert v_pre.prerelease == "beta"

    def test_semantic_version_with_build_method(self):
        """Test with_build method."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 0, 0)
        v_build = v.with_build("123")
        assert v_build.build == "123"

    def test_semantic_version_is_stable(self):
        """Test is_stable property."""
        from utils.version import SemanticVersion
        v_stable = SemanticVersion(1, 0, 0)
        v_prerelease = SemanticVersion(1, 0, 0, prerelease="beta")
        v_zero = SemanticVersion(0, 1, 0)

        assert v_stable.is_stable is True
        assert v_prerelease.is_stable is False
        assert v_zero.is_stable is False

    def test_semantic_version_to_tuple(self):
        """Test to_tuple method."""
        from utils.version import SemanticVersion
        v = SemanticVersion(1, 2, 3)
        assert v.to_tuple() == (1, 2, 3, "")


class TestHelperFunctions:
    """Tests for version helper functions."""

    def test_get_version(self):
        """Test get_version function."""
        from utils.version import __version__, get_version
        assert get_version() == __version__

    def test_get_version_info(self):
        """Test get_version_info function."""
        from utils.version import get_version_info
        info = get_version_info()
        assert "version" in info
        assert "major" in info
        assert "minor" in info
        assert "patch" in info
        assert "app_name" in info

    def test_get_semantic_version(self):
        """Test get_semantic_version function."""
        from utils.version import SemanticVersion, get_semantic_version
        v = get_semantic_version()
        assert isinstance(v, SemanticVersion)

    def test_parse_version(self):
        """Test parse_version function."""
        from utils.version import SemanticVersion, parse_version
        v = parse_version("2.1.0")
        assert isinstance(v, SemanticVersion)
        assert v.major == 2

    def test_compare_versions_less(self):
        """Test compare_versions returns -1."""
        from utils.version import compare_versions
        result = compare_versions("1.0.0", "2.0.0")
        assert result == -1

    def test_compare_versions_greater(self):
        """Test compare_versions returns 1."""
        from utils.version import compare_versions
        result = compare_versions("2.0.0", "1.0.0")
        assert result == 1

    def test_compare_versions_equal(self):
        """Test compare_versions returns 0."""
        from utils.version import compare_versions
        result = compare_versions("1.0.0", "1.0.0")
        assert result == 0

    def test_is_compatible_same_major(self):
        """Test is_compatible with same major version."""
        from utils.version import is_compatible
        assert is_compatible("1.0.0", "1.2.0") is True

    def test_is_compatible_different_major(self):
        """Test is_compatible with different major version."""
        from utils.version import is_compatible
        assert is_compatible("1.0.0", "2.0.0") is False

    def test_is_compatible_lower_current(self):
        """Test is_compatible when current is lower."""
        from utils.version import is_compatible
        assert is_compatible("1.5.0", "1.2.0") is False

    def test_format_version_string(self):
        """Test format_version_string function."""
        from utils.version import format_version_string
        result = format_version_string(1, 2, 3)
        assert result == "1.2.3"

    def test_format_version_string_with_prerelease(self):
        """Test format_version_string with prerelease."""
        from utils.version import format_version_string
        result = format_version_string(1, 0, 0, prerelease="alpha")
        assert result == "1.0.0-alpha"

    def test_format_version_string_with_build(self):
        """Test format_version_string with build."""
        from utils.version import format_version_string
        result = format_version_string(1, 0, 0, build="123")
        assert result == "1.0.0+123"
