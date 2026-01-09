"""
Pytest configuration and fixtures for the test suite.

This module provides shared fixtures and configuration for all tests.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator

import pytest


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    """
    Provide a clean sandbox directory for testing.

    Returns:
        Path to temporary sandbox directory
    """
    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    return sandbox_dir


@pytest.fixture
def clean_sandbox(sandbox: Path) -> Generator[Path, None, None]:
    """
    Provide a sandbox that is cleaned up after test.

    Yields:
        Path to sandbox directory
    """
    yield sandbox
    # Cleanup
    if sandbox.exists():
        shutil.rmtree(sandbox)


@pytest.fixture
def sample_files(sandbox: Path) -> dict[str, Path]:
    """
    Create sample files for testing.

    Returns:
        Dictionary mapping file names to their paths
    """
    files = {}

    # Create sample Python file
    py_file = sandbox / "sample.py"
    py_file.write_text('print("Hello, World!")\n')
    files["python"] = py_file

    # Create sample text file
    txt_file = sandbox / "readme.txt"
    txt_file.write_text("Sample readme content\n")
    files["text"] = txt_file

    # Create sample JSON file
    json_file = sandbox / "config.json"
    json_file.write_text('{"key": "value"}\n')
    files["json"] = json_file

    return files


@pytest.fixture
def mock_env_vars() -> Generator[dict[str, str], None, None]:
    """
    Provide mock environment variables that are restored after test.

    Yields:
        Original environment variables
    """
    original = os.environ.copy()
    yield original
    os.environ.clear()
    os.environ.update(original)


@pytest.fixture
def isolated_config(tmp_path: Path, mock_env_vars) -> Path:
    """
    Provide isolated configuration for testing.

    Returns:
        Path to temporary config directory
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create minimal permissions file
    permissions_file = config_dir / "permissions.yaml"
    permissions_file.write_text("""
actions:
  run_tests: auto
  read_file: auto
  write_file: ask
  deploy: deny
dangerous_keywords:
  - sudo
  - rm -rf
sandbox:
  root: ./sandbox
""")

    return config_dir


@pytest.fixture(autouse=True)
def reset_loggers():
    """Reset loggers between tests to prevent state leakage."""
    yield
    # Reset logger state
    import utils.logger
    utils.logger._logger = None
    utils.logger._debug_logger = None


@pytest.fixture(autouse=True)
def reset_error_tracking():
    """Reset error tracking between tests."""
    yield
    # Reset error counts
    from utils.error_tracking import reset_error_counts
    reset_error_counts()


# =============================================================================
# Pytest Hooks
# =============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    # Markers are defined in pyproject.toml
    pass


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add regression marker to tests in test_regression.py
        if "test_regression" in str(item.fspath):
            item.add_marker(pytest.mark.regression)

        # Add integration marker to tests in test_integration.py
        if "test_integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add performance marker to tests in test_performance.py
        if "test_performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)

        # Add security marker to tests in test_security.py
        if "test_security" in str(item.fspath):
            item.add_marker(pytest.mark.security)


# =============================================================================
# Helper Functions
# =============================================================================


def create_test_file(path: Path, content: str = "") -> Path:
    """
    Helper to create a test file.

    Args:
        path: Path for the file
        content: Content to write

    Returns:
        Path to created file
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def assert_file_contains(path: Path, text: str) -> None:
    """
    Assert that a file contains specific text.

    Args:
        path: Path to file
        text: Text to search for
    """
    content = path.read_text()
    assert text in content, f"Expected '{text}' in file {path}"
