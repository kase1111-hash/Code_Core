#!/usr/bin/env python3
"""
Version bump script for Ollama Automation Harness.

Automates version bumping across all project files that contain version info.

Usage:
    python scripts/bump_version.py major    # 1.0.0 -> 2.0.0
    python scripts/bump_version.py minor    # 1.0.0 -> 1.1.0
    python scripts/bump_version.py patch    # 1.0.0 -> 1.0.1
    python scripts/bump_version.py set 2.0.0  # Set specific version
    python scripts/bump_version.py show     # Show current version
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Files that contain version information
VERSION_FILES = {
    "utils/version.py": [
        (r'__version__\s*=\s*["\']([^"\']+)["\']', '__version__ = "{version}"'),
        (r"VERSION_MAJOR\s*=\s*(\d+)", "VERSION_MAJOR = {major}"),
        (r"VERSION_MINOR\s*=\s*(\d+)", "VERSION_MINOR = {minor}"),
        (r"VERSION_PATCH\s*=\s*(\d+)", "VERSION_PATCH = {patch}"),
    ],
    "pyproject.toml": [
        (r'version\s*=\s*["\']([^"\']+)["\']', 'version = "{version}"'),
    ],
}


class Version:
    """Simple version class for bumping."""

    def __init__(self, major: int, minor: int, patch: int):
        self.major = major
        self.minor = minor
        self.patch = patch

    @classmethod
    def parse(cls, version_string: str) -> "Version":
        """Parse version string."""
        # Remove 'v' prefix if present
        if version_string.startswith("v"):
            version_string = version_string[1:]

        # Handle pre-release suffix
        version_string = version_string.split("-")[0].split("+")[0]

        parts = version_string.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {version_string}")

        return cls(int(parts[0]), int(parts[1]), int(parts[2]))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def bump_major(self) -> "Version":
        return Version(self.major + 1, 0, 0)

    def bump_minor(self) -> "Version":
        return Version(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "Version":
        return Version(self.major, self.minor, self.patch + 1)


def get_current_version() -> Version:
    """Read current version from utils/version.py."""
    version_file = PROJECT_ROOT / "utils" / "version.py"

    if not version_file.exists():
        raise FileNotFoundError("utils/version.py not found")

    content = version_file.read_text()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)

    if not match:
        raise ValueError("Could not find __version__ in utils/version.py")

    return Version.parse(match.group(1))


def update_file(file_path: Path, version: Version, patterns: list) -> bool:
    """Update version in a single file."""
    if not file_path.exists():
        print(f"  Warning: {file_path} not found, skipping")
        return False

    content = file_path.read_text()
    original_content = content

    for pattern, replacement in patterns:
        # Format replacement with version info
        formatted_replacement = replacement.format(
            version=str(version),
            major=version.major,
            minor=version.minor,
            patch=version.patch,
        )

        # Replace in content
        content = re.sub(pattern, formatted_replacement, content)

    if content != original_content:
        file_path.write_text(content)
        return True
    return False


def update_all_files(version: Version) -> list[str]:
    """Update version in all project files."""
    updated = []

    for rel_path, patterns in VERSION_FILES.items():
        file_path = PROJECT_ROOT / rel_path
        if update_file(file_path, version, patterns):
            updated.append(rel_path)
            print(f"  Updated: {rel_path}")

    return updated


def create_git_tag(version: Version, push: bool = False) -> bool:
    """Create and optionally push a git tag."""
    tag_name = f"v{version}"

    try:
        # Check if tag exists
        result = subprocess.run(
            ["git", "tag", "-l", tag_name],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

        if tag_name in result.stdout:
            print(f"  Warning: Tag {tag_name} already exists")
            return False

        # Create tag
        subprocess.run(
            ["git", "tag", "-a", tag_name, "-m", f"Release {version}"],
            check=True,
            cwd=PROJECT_ROOT,
        )
        print(f"  Created tag: {tag_name}")

        if push:
            subprocess.run(
                ["git", "push", "origin", tag_name],
                check=True,
                cwd=PROJECT_ROOT,
            )
            print(f"  Pushed tag: {tag_name}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"  Error creating tag: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Bump version for Ollama Automation Harness"
    )
    parser.add_argument(
        "action",
        choices=["major", "minor", "patch", "set", "show"],
        help="Version bump action",
    )
    parser.add_argument(
        "version",
        nargs="?",
        help="Version string (only for 'set' action)",
    )
    parser.add_argument(
        "--tag",
        action="store_true",
        help="Create git tag after bump",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push git tag to origin (implies --tag)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    # Get current version
    try:
        current = get_current_version()
    except Exception as e:
        print(f"Error reading current version: {e}")
        return 1

    print(f"Current version: {current}")

    # Handle show action
    if args.action == "show":
        return 0

    # Calculate new version
    if args.action == "major":
        new_version = current.bump_major()
    elif args.action == "minor":
        new_version = current.bump_minor()
    elif args.action == "patch":
        new_version = current.bump_patch()
    elif args.action == "set":
        if not args.version:
            print("Error: 'set' action requires a version argument")
            return 1
        try:
            new_version = Version.parse(args.version)
        except ValueError as e:
            print(f"Error: {e}")
            return 1
    else:
        print(f"Unknown action: {args.action}")
        return 1

    print(f"New version: {new_version}")

    if args.dry_run:
        print("\nDry run - no changes made")
        print("Files that would be updated:")
        for rel_path in VERSION_FILES:
            file_path = PROJECT_ROOT / rel_path
            if file_path.exists():
                print(f"  - {rel_path}")
        return 0

    # Update files
    print("\nUpdating files...")
    updated = update_all_files(new_version)

    if not updated:
        print("No files were updated")
        return 1

    print(f"\nUpdated {len(updated)} file(s)")

    # Create tag if requested
    if args.tag or args.push:
        print("\nCreating git tag...")
        create_git_tag(new_version, push=args.push)

    print(f"\nVersion bumped to {new_version}")
    print("\nNext steps:")
    print("  1. Review changes: git diff")
    print(f"  2. Commit changes: git commit -am 'Bump version to {new_version}'")
    if not (args.tag or args.push):
        print(f"  3. Create tag: git tag -a v{new_version} -m 'Release {new_version}'")
        print("  4. Push: git push && git push --tags")

    return 0


if __name__ == "__main__":
    sys.exit(main())
