# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Ollama Automation Harness.

Build command:
    pyinstaller ollama-harness.spec

This creates a standalone executable that includes all dependencies.
"""

import sys
from pathlib import Path

# Project root directory
project_root = Path(SPECPATH)

# Analysis configuration
a = Analysis(
    # Entry point script
    [str(project_root / 'main.py')],

    # Additional paths to search for imports
    pathex=[str(project_root)],

    # Binary files to include (none needed for pure Python)
    binaries=[],

    # Data files to bundle with the executable
    datas=[
        # Configuration files
        (str(project_root / 'config'), 'config'),
        # Environment example
        (str(project_root / '.env.example'), '.'),
    ],

    # Hidden imports that PyInstaller might miss
    hiddenimports=[
        # Core dependencies
        'dotenv',
        'yaml',
        'anthropic',
        'sentry_sdk',
        'sentry_sdk.integrations',
        'sentry_sdk.integrations.logging',
        # Standard library modules that might be missed
        'argparse',
        'logging',
        'logging.handlers',
        'json',
        'subprocess',
        'pathlib',
        'typing',
        'enum',
        'dataclasses',
        'functools',
        'contextlib',
        # Utils modules
        'utils.config',
        'utils.environment',
        'utils.logger',
        'utils.validation',
        'utils.secrets',
        # Core modules
        'core.ollama',
        'core.claude',
        'core.executor',
        'core.safety',
    ],

    # Packages to include
    hookspath=[],

    # Runtime hooks
    runtime_hooks=[],

    # Modules to exclude (reduce size)
    excludes=[
        # Testing frameworks
        'pytest',
        'pytest_cov',
        'hypothesis',
        # Development tools
        'black',
        'ruff',
        'mypy',
        'pre_commit',
        # Unused standard library
        'tkinter',
        'unittest',
        # Documentation
        'sphinx',
        'docutils',
    ],

    # No cipher for code (not using --key)
    cipher=None,

    # Don't fail on missing hidden imports
    noarchive=False,
)

# PYZ archive (compressed Python modules)
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

# Executable configuration
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],

    # Executable name
    name='ollama-harness',

    # Debug mode (set to True for troubleshooting)
    debug=False,

    # Boot loader ignore signals
    bootloader_ignore_signals=False,

    # Strip symbols (smaller binary, harder to debug)
    strip=False,

    # UPX compression (if available)
    upx=True,
    upx_exclude=[],

    # Console application (not windowed)
    console=True,

    # Disable windowed mode traceback
    disable_windowed_traceback=False,

    # Target architecture (None = current)
    target_arch=None,

    # Code signing (None = unsigned)
    codesign_identity=None,

    # Entitlements file (macOS)
    entitlements_file=None,

    # Version info (Windows)
    version=None,

    # Icon file (optional)
    # icon='assets/icon.ico',
)

# For macOS .app bundle (optional)
# app = BUNDLE(
#     exe,
#     name='Ollama Harness.app',
#     icon='assets/icon.icns',
#     bundle_identifier='com.ollama.harness',
#     info_plist={
#         'CFBundleShortVersionString': '1.0.0',
#         'CFBundleVersion': '1.0.0',
#     },
# )
