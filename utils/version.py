"""
Version management for Ollama Automation Harness.

This module implements Semantic Versioning 2.0.0 (https://semver.org/)
and provides utilities for version management.

Version format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
  - MAJOR: Incompatible API changes
  - MINOR: Backwards-compatible functionality additions
  - PATCH: Backwards-compatible bug fixes
  - PRERELEASE: Optional pre-release identifier (e.g., alpha, beta, rc.1)
  - BUILD: Optional build metadata (e.g., build.123, 20240101)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import Optional


# =============================================================================
# Version Constants
# =============================================================================

# Current version - Single source of truth
__version__ = "1.0.0"

# Version components
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0
VERSION_PRERELEASE: Optional[str] = None
VERSION_BUILD: Optional[str] = None

# Application metadata
APP_NAME = "Ollama Automation Harness"
APP_AUTHOR = "Ollama Harness Team"
APP_LICENSE = "MIT"


# =============================================================================
# Semantic Version Class
# =============================================================================

@total_ordering
@dataclass
class SemanticVersion:
    """
    Represents a semantic version following SemVer 2.0.0 specification.

    Examples:
        >>> v = SemanticVersion(1, 2, 3)
        >>> str(v)
        '1.2.3'

        >>> v = SemanticVersion(1, 0, 0, prerelease='beta.1')
        >>> str(v)
        '1.0.0-beta.1'

        >>> v1 = SemanticVersion.parse('1.0.0')
        >>> v2 = SemanticVersion.parse('2.0.0')
        >>> v1 < v2
        True
    """

    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    # Regex pattern for parsing semantic versions
    SEMVER_PATTERN = re.compile(
        r"^(?P<major>0|[1-9]\d*)"
        r"\.(?P<minor>0|[1-9]\d*)"
        r"\.(?P<patch>0|[1-9]\d*)"
        r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
        r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    def __post_init__(self):
        """Validate version components."""
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError("Version components must be non-negative integers")

    @classmethod
    def parse(cls, version_string: str) -> "SemanticVersion":
        """
        Parse a version string into a SemanticVersion object.

        Args:
            version_string: Version string to parse (e.g., "1.2.3-beta+build")

        Returns:
            SemanticVersion object

        Raises:
            ValueError: If version string is invalid
        """
        # Strip 'v' prefix if present
        if version_string.startswith("v"):
            version_string = version_string[1:]

        match = cls.SEMVER_PATTERN.match(version_string)
        if not match:
            raise ValueError(f"Invalid semantic version: {version_string}")

        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("prerelease"),
            build=match.group("build"),
        )

    def __str__(self) -> str:
        """Return version string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"SemanticVersion(major={self.major}, minor={self.minor}, "
            f"patch={self.patch}, prerelease={self.prerelease!r}, "
            f"build={self.build!r})"
        )

    def __eq__(self, other: object) -> bool:
        """Check equality (build metadata is ignored per SemVer spec)."""
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __lt__(self, other: "SemanticVersion") -> bool:
        """
        Compare versions (build metadata is ignored per SemVer spec).

        Pre-release versions have lower precedence than normal versions.
        """
        if not isinstance(other, SemanticVersion):
            return NotImplemented

        # Compare major.minor.patch
        if (self.major, self.minor, self.patch) != (
            other.major,
            other.minor,
            other.patch,
        ):
            return (self.major, self.minor, self.patch) < (
                other.major,
                other.minor,
                other.patch,
            )

        # Pre-release has lower precedence than no pre-release
        if self.prerelease is None and other.prerelease is not None:
            return False
        if self.prerelease is not None and other.prerelease is None:
            return True
        if self.prerelease is None and other.prerelease is None:
            return False

        # Compare pre-release identifiers
        self_parts = self.prerelease.split(".")
        other_parts = other.prerelease.split(".")

        for self_part, other_part in zip(self_parts, other_parts):
            # Numeric identifiers have lower precedence than alphanumeric
            self_is_num = self_part.isdigit()
            other_is_num = other_part.isdigit()

            if self_is_num and other_is_num:
                if int(self_part) != int(other_part):
                    return int(self_part) < int(other_part)
            elif self_is_num:
                return True  # Numeric < alphanumeric
            elif other_is_num:
                return False
            elif self_part != other_part:
                return self_part < other_part

        # Shorter pre-release has lower precedence
        return len(self_parts) < len(other_parts)

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash((self.major, self.minor, self.patch, self.prerelease))

    def bump_major(self) -> "SemanticVersion":
        """Return new version with bumped major number."""
        return SemanticVersion(self.major + 1, 0, 0)

    def bump_minor(self) -> "SemanticVersion":
        """Return new version with bumped minor number."""
        return SemanticVersion(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "SemanticVersion":
        """Return new version with bumped patch number."""
        return SemanticVersion(self.major, self.minor, self.patch + 1)

    def with_prerelease(self, prerelease: str) -> "SemanticVersion":
        """Return new version with pre-release identifier."""
        return SemanticVersion(
            self.major, self.minor, self.patch, prerelease=prerelease
        )

    def with_build(self, build: str) -> "SemanticVersion":
        """Return new version with build metadata."""
        return SemanticVersion(
            self.major, self.minor, self.patch, self.prerelease, build=build
        )

    @property
    def is_prerelease(self) -> bool:
        """Check if this is a pre-release version."""
        return self.prerelease is not None

    @property
    def is_stable(self) -> bool:
        """Check if this is a stable release (major > 0, no prerelease)."""
        return self.major > 0 and not self.is_prerelease

    def to_tuple(self) -> tuple:
        """Return version as tuple for comparison."""
        return (self.major, self.minor, self.patch, self.prerelease or "")


# =============================================================================
# Helper Functions
# =============================================================================

def get_version() -> str:
    """Get the current version string."""
    return __version__


def get_version_info() -> dict:
    """Get detailed version information."""
    return {
        "version": __version__,
        "major": VERSION_MAJOR,
        "minor": VERSION_MINOR,
        "patch": VERSION_PATCH,
        "prerelease": VERSION_PRERELEASE,
        "build": VERSION_BUILD,
        "app_name": APP_NAME,
        "author": APP_AUTHOR,
        "license": APP_LICENSE,
    }


def get_semantic_version() -> SemanticVersion:
    """Get the current version as a SemanticVersion object."""
    return SemanticVersion(
        major=VERSION_MAJOR,
        minor=VERSION_MINOR,
        patch=VERSION_PATCH,
        prerelease=VERSION_PRERELEASE,
        build=VERSION_BUILD,
    )


def parse_version(version_string: str) -> SemanticVersion:
    """Parse a version string into a SemanticVersion object."""
    return SemanticVersion.parse(version_string)


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.

    Returns:
        -1 if v1 < v2
         0 if v1 == v2
         1 if v1 > v2
    """
    sv1 = SemanticVersion.parse(v1)
    sv2 = SemanticVersion.parse(v2)

    if sv1 < sv2:
        return -1
    elif sv1 > sv2:
        return 1
    return 0


def is_compatible(required: str, current: str) -> bool:
    """
    Check if current version is compatible with required version.

    Uses caret (^) compatibility: same major version, >= minor.patch.
    """
    req = SemanticVersion.parse(required)
    cur = SemanticVersion.parse(current)

    # Same major version required
    if req.major != cur.major:
        return False

    # Current must be >= required
    return cur >= req


def format_version_string(
    major: int,
    minor: int,
    patch: int,
    prerelease: Optional[str] = None,
    build: Optional[str] = None,
) -> str:
    """Format version components into a version string."""
    version = f"{major}.{minor}.{patch}"
    if prerelease:
        version += f"-{prerelease}"
    if build:
        version += f"+{build}"
    return version
