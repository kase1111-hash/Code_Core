#!/usr/bin/env python3
"""
Package builder for Ollama Automation Harness.

Creates distributable packages in various formats:
- zip: Source distribution for direct Python execution
- wheel: Python wheel package for pip installation
- exe: Standalone executable via PyInstaller (Windows/Linux/Mac)
- docker: Docker image

Usage:
    python scripts/package.py zip          # Create zip archive
    python scripts/package.py wheel        # Create wheel package
    python scripts/package.py exe          # Create standalone executable
    python scripts/package.py docker       # Build Docker image
    python scripts/package.py all          # Create all packages
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"

# Files and directories to include in distributions
INCLUDE_FILES = [
    "cli.py",
    "main.py",
    "requirements.txt",
    "README.md",
    "LICENSE",
    ".env.example",
    "pyproject.toml",
]

INCLUDE_DIRS = [
    "core",
    "utils",
    "config",
]

# Files and patterns to exclude
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "*.egg-info",
    ".env",
    "*.log",
]


def get_version() -> str:
    """Get version from pyproject.toml or use date-based version."""
    try:
        import tomllib
        with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {}).get("version", "0.0.0")
    except Exception:
        # Fallback to date-based version
        return datetime.now().strftime("%Y.%m.%d")


def clean_dist():
    """Remove existing dist and build directories."""
    print("Cleaning previous builds...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)


def should_exclude(path: Path) -> bool:
    """Check if path should be excluded from package."""
    path_str = str(path)
    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*"):
            if path_str.endswith(pattern[1:]):
                return True
        elif pattern in path_str:
            return True
    return False


def build_zip() -> Path:
    """Create a zip archive of the source distribution."""
    version = get_version()
    zip_name = f"ollama-harness-{version}.zip"
    zip_path = DIST_DIR / zip_name

    print(f"Building zip archive: {zip_name}")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add individual files
        for file_name in INCLUDE_FILES:
            file_path = PROJECT_ROOT / file_name
            if file_path.exists():
                zf.write(file_path, f"ollama-harness/{file_name}")
                print(f"  Added: {file_name}")

        # Add directories
        for dir_name in INCLUDE_DIRS:
            dir_path = PROJECT_ROOT / dir_name
            if dir_path.exists():
                for root, dirs, files in os.walk(dir_path):
                    # Filter out excluded directories
                    dirs[:] = [d for d in dirs if not should_exclude(Path(root) / d)]

                    for file in files:
                        file_path = Path(root) / file
                        if not should_exclude(file_path):
                            arcname = f"ollama-harness/{file_path.relative_to(PROJECT_ROOT)}"
                            zf.write(file_path, arcname)

        # Add install script
        install_script = '''#!/bin/bash
# Installation script for Ollama Automation Harness

echo "Installing Ollama Automation Harness..."

# Check Python version
python3 --version || { echo "Python 3 is required"; exit 1; }

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy example environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file - please configure your settings"
fi

echo "Installation complete!"
echo "Run: source venv/bin/activate && python main.py --help"
'''
        zf.writestr("ollama-harness/install.sh", install_script)

        # Add Windows install script
        install_bat = '''@echo off
REM Installation script for Ollama Automation Harness

echo Installing Ollama Automation Harness...

REM Check Python
python --version || (echo Python 3 is required && exit /b 1)

REM Create virtual environment
python -m venv venv
call venv\\Scripts\\activate.bat

REM Install dependencies
pip install -r requirements.txt

REM Copy example environment file
if not exist .env copy .env.example .env

echo Installation complete!
echo Run: venv\\Scripts\\activate.bat ^&^& python main.py --help
'''
        zf.writestr("ollama-harness/install.bat", install_bat)

    print(f"Created: {zip_path}")
    print(f"Size: {zip_path.stat().st_size / 1024:.1f} KB")
    return zip_path


def build_wheel() -> Path:
    """Build Python wheel package."""
    version = get_version()
    print(f"Building wheel package (version {version})...")

    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(DIST_DIR)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Wheel build failed: {result.stderr}")
        # Try with pip instead
        result = subprocess.run(
            [sys.executable, "-m", "pip", "wheel", ".", "--wheel-dir", str(DIST_DIR), "--no-deps"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"Wheel build failed: {result.stderr}")
            return None

    # Find the created wheel
    wheels = list(DIST_DIR.glob("*.whl"))
    if wheels:
        wheel_path = wheels[0]
        print(f"Created: {wheel_path}")
        return wheel_path
    return None


def build_exe() -> Path:
    """Build standalone executable with PyInstaller."""
    version = get_version()
    exe_name = "ollama-harness"

    print(f"Building standalone executable: {exe_name}")

    # Check if PyInstaller is available
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", exe_name,
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR / "pyinstaller"),
        "--specpath", str(BUILD_DIR),
        "--clean",
        "--noconfirm",
        # Add data files
        "--add-data", f"{PROJECT_ROOT / 'config'}:config",
        "--add-data", f"{PROJECT_ROOT / '.env.example'}:.",
        # Hidden imports
        "--hidden-import", "dotenv",
        "--hidden-import", "yaml",
        "--hidden-import", "anthropic",
        "--hidden-import", "sentry_sdk",
        # Entry point
        str(PROJECT_ROOT / "main.py"),
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"PyInstaller failed: {result.stderr}")
        return None

    # Find the created executable
    if sys.platform == "win32":
        exe_path = DIST_DIR / f"{exe_name}.exe"
    else:
        exe_path = DIST_DIR / exe_name

    if exe_path.exists():
        print(f"Created: {exe_path}")
        print(f"Size: {exe_path.stat().st_size / (1024*1024):.1f} MB")
        return exe_path
    return None


def build_docker(tag: str = None) -> bool:
    """Build Docker image."""
    version = get_version()
    tag = tag or f"ollama-harness:{version}"

    print(f"Building Docker image: {tag}")

    cmd = [
        "docker", "build",
        "-f", "Dockerfile.prod",
        "-t", tag,
        "-t", "ollama-harness:latest",
        ".",
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        print(f"Created Docker image: {tag}")

        # Optionally save to tar
        tar_path = DIST_DIR / f"ollama-harness-{version}-docker.tar"
        save_cmd = ["docker", "save", "-o", str(tar_path), tag]
        save_result = subprocess.run(save_cmd, capture_output=True)

        if save_result.returncode == 0:
            print(f"Saved to: {tar_path}")
            print(f"Size: {tar_path.stat().st_size / (1024*1024):.1f} MB")

        return True
    return False


def build_all():
    """Build all package formats."""
    results = {}

    results["zip"] = build_zip()
    results["wheel"] = build_wheel()
    results["exe"] = build_exe()
    results["docker"] = build_docker()

    print("\n" + "=" * 60)
    print("Build Summary")
    print("=" * 60)

    for fmt, result in results.items():
        status = "OK" if result else "FAILED"
        print(f"  {fmt:12} {status}")

    return all(results.values())


def main():
    parser = argparse.ArgumentParser(
        description="Build distributable packages for Ollama Automation Harness"
    )
    parser.add_argument(
        "format",
        choices=["zip", "wheel", "exe", "docker", "all", "clean"],
        help="Package format to build",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Skip cleaning previous builds",
    )
    parser.add_argument(
        "--docker-tag",
        help="Custom Docker tag (for docker format)",
    )

    args = parser.parse_args()

    # Change to project root
    os.chdir(PROJECT_ROOT)

    # Clean unless skipped
    if args.format == "clean":
        clean_dist()
        print("Cleaned dist and build directories")
        return 0

    if not args.no_clean:
        clean_dist()
    else:
        DIST_DIR.mkdir(parents=True, exist_ok=True)
        BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # Build requested format
    success = False

    if args.format == "zip":
        success = build_zip() is not None
    elif args.format == "wheel":
        success = build_wheel() is not None
    elif args.format == "exe":
        success = build_exe() is not None
    elif args.format == "docker":
        success = build_docker(args.docker_tag)
    elif args.format == "all":
        success = build_all()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
