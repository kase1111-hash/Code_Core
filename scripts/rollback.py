#!/usr/bin/env python3
"""
Rollback and recovery utilities for Ollama Automation Harness.

Provides mechanisms for:
- Creating deployment snapshots/backups
- Rolling back to previous versions
- Recovery from failed deployments
- State management and versioning

Usage:
    python scripts/rollback.py backup           # Create backup
    python scripts/rollback.py list             # List available backups
    python scripts/rollback.py restore <id>     # Restore specific backup
    python scripts/rollback.py rollback         # Rollback to previous version
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# =============================================================================
# Configuration
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
BACKUP_DIR = PROJECT_ROOT / ".backups"
STATE_FILE = BACKUP_DIR / "state.json"
MAX_BACKUPS = int(os.environ.get("MAX_BACKUPS", "10"))

# Directories and files to backup
BACKUP_INCLUDES = [
    "core",
    "utils",
    "config",
    "cli.py",
    "main.py",
    "requirements.txt",
    "pyproject.toml",
]

# Files/patterns to exclude from backup
BACKUP_EXCLUDES = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".git",
    ".env",
    "*.log",
]


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class BackupMetadata:
    """Metadata for a backup."""

    backup_id: str
    timestamp: str
    version: str
    git_commit: str
    git_branch: str
    description: str
    file_count: int
    size_bytes: int
    checksum: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BackupMetadata":
        return cls(**data)


@dataclass
class RollbackState:
    """Tracks rollback state and history."""

    current_backup_id: str | None = None
    previous_backup_id: str | None = None
    backups: list[dict] = field(default_factory=list)
    last_action: str = ""
    last_action_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RollbackState":
        return cls(**data)


# =============================================================================
# Utility Functions
# =============================================================================

def get_version() -> str:
    """Get current application version."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from utils.version import get_version
        return get_version()
    except ImportError:
        return "unknown"


def get_git_info() -> tuple[str, str]:
    """Get current git commit and branch."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        ).stdout.strip()
        return commit or "unknown", branch or "unknown"
    except Exception:
        return "unknown", "unknown"


def generate_backup_id() -> str:
    """Generate unique backup ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"backup_{timestamp}"


def calculate_checksum(path: Path) -> str:
    """Calculate checksum of a file or directory."""
    hasher = hashlib.sha256()

    if path.is_file():
        hasher.update(path.read_bytes())
    elif path.is_dir():
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file():
                rel_path = file_path.relative_to(path)
                hasher.update(str(rel_path).encode())
                hasher.update(file_path.read_bytes())

    return hasher.hexdigest()[:16]


def should_exclude(path: Path) -> bool:
    """Check if path should be excluded from backup."""
    path_str = str(path)
    for pattern in BACKUP_EXCLUDES:
        if pattern.startswith("*"):
            if path_str.endswith(pattern[1:]):
                return True
        elif pattern in path_str:
            return True
    return False


def load_state() -> RollbackState:
    """Load rollback state from file."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return RollbackState.from_dict(json.load(f))
    return RollbackState()


def save_state(state: RollbackState) -> None:
    """Save rollback state to file."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state.to_dict(), f, indent=2)


# =============================================================================
# Backup Operations
# =============================================================================

def create_backup(description: str = "") -> BackupMetadata:
    """Create a new backup of the current state."""
    print("Creating backup...")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    backup_id = generate_backup_id()
    backup_path = BACKUP_DIR / backup_id

    backup_path.mkdir(parents=True, exist_ok=True)

    # Copy files
    file_count = 0
    total_size = 0

    for item in BACKUP_INCLUDES:
        src = PROJECT_ROOT / item
        if not src.exists():
            continue

        dst = backup_path / item

        if src.is_file():
            shutil.copy2(src, dst)
            file_count += 1
            total_size += src.stat().st_size
        elif src.is_dir():
            shutil.copytree(
                src, dst,
                ignore=lambda d, files: [f for f in files if should_exclude(Path(d) / f)]
            )
            for f in dst.rglob("*"):
                if f.is_file():
                    file_count += 1
                    total_size += f.stat().st_size

    # Calculate checksum
    checksum = calculate_checksum(backup_path)

    # Get metadata
    git_commit, git_branch = get_git_info()

    metadata = BackupMetadata(
        backup_id=backup_id,
        timestamp=datetime.now().isoformat(),
        version=get_version(),
        git_commit=git_commit,
        git_branch=git_branch,
        description=description or f"Backup created at {datetime.now()}",
        file_count=file_count,
        size_bytes=total_size,
        checksum=checksum,
    )

    # Save metadata
    with open(backup_path / "metadata.json", "w") as f:
        json.dump(metadata.to_dict(), f, indent=2)

    # Update state
    state = load_state()
    state.backups.insert(0, metadata.to_dict())
    state.previous_backup_id = state.current_backup_id
    state.current_backup_id = backup_id
    state.last_action = "backup"
    state.last_action_time = datetime.now().isoformat()

    # Prune old backups
    while len(state.backups) > MAX_BACKUPS:
        old_backup = state.backups.pop()
        old_path = BACKUP_DIR / old_backup["backup_id"]
        if old_path.exists():
            shutil.rmtree(old_path)

    save_state(state)

    print(f"Backup created: {backup_id}")
    print(f"  Files: {file_count}")
    print(f"  Size: {total_size / 1024:.1f} KB")
    print(f"  Checksum: {checksum}")

    return metadata


def list_backups() -> list[BackupMetadata]:
    """List all available backups."""
    state = load_state()
    backups = []

    for backup_data in state.backups:
        backup_id = backup_data.get("backup_id")
        backup_path = BACKUP_DIR / backup_id

        if backup_path.exists():
            backups.append(BackupMetadata.from_dict(backup_data))

    return backups


def get_backup(backup_id: str) -> BackupMetadata | None:
    """Get metadata for a specific backup."""
    backup_path = BACKUP_DIR / backup_id / "metadata.json"
    if backup_path.exists():
        with open(backup_path) as f:
            return BackupMetadata.from_dict(json.load(f))
    return None


def restore_backup(backup_id: str, force: bool = False) -> bool:
    """Restore from a specific backup."""
    backup_path = BACKUP_DIR / backup_id

    if not backup_path.exists():
        print(f"Backup not found: {backup_id}")
        return False

    metadata = get_backup(backup_id)
    if not metadata:
        print("Backup metadata not found")
        return False

    # Verify checksum
    current_checksum = calculate_checksum(backup_path)
    if current_checksum != metadata.checksum and not force:
        print(f"Checksum mismatch! Expected {metadata.checksum}, got {current_checksum}")
        print("Use --force to restore anyway")
        return False

    print(f"Restoring backup: {backup_id}")
    print(f"  Version: {metadata.version}")
    print(f"  Created: {metadata.timestamp}")

    # Create pre-restore backup
    pre_restore = create_backup(f"Pre-restore backup before restoring {backup_id}")

    # Restore files
    for item in BACKUP_INCLUDES:
        src = backup_path / item
        dst = PROJECT_ROOT / item

        if not src.exists():
            continue

        # Remove existing
        if dst.exists():
            if dst.is_file():
                dst.unlink()
            else:
                shutil.rmtree(dst)

        # Copy from backup
        if src.is_file():
            shutil.copy2(src, dst)
        else:
            shutil.copytree(src, dst)

    # Update state
    state = load_state()
    state.previous_backup_id = state.current_backup_id
    state.current_backup_id = backup_id
    state.last_action = "restore"
    state.last_action_time = datetime.now().isoformat()
    save_state(state)

    print(f"Restored successfully from {backup_id}")
    print(f"Pre-restore backup saved as: {pre_restore.backup_id}")

    return True


def rollback() -> bool:
    """Rollback to the previous backup."""
    state = load_state()

    if not state.previous_backup_id:
        print("No previous backup available for rollback")
        return False

    print(f"Rolling back to: {state.previous_backup_id}")
    return restore_backup(state.previous_backup_id)


def delete_backup(backup_id: str) -> bool:
    """Delete a specific backup."""
    backup_path = BACKUP_DIR / backup_id

    if not backup_path.exists():
        print(f"Backup not found: {backup_id}")
        return False

    state = load_state()

    # Don't allow deleting current backup
    if state.current_backup_id == backup_id:
        print("Cannot delete current backup")
        return False

    # Remove from state
    state.backups = [b for b in state.backups if b.get("backup_id") != backup_id]

    if state.previous_backup_id == backup_id:
        state.previous_backup_id = None

    save_state(state)

    # Remove directory
    shutil.rmtree(backup_path)
    print(f"Deleted backup: {backup_id}")

    return True


def cleanup_old_backups(keep: int = MAX_BACKUPS) -> int:
    """Remove old backups, keeping only the most recent ones."""
    state = load_state()
    removed = 0

    while len(state.backups) > keep:
        old_backup = state.backups.pop()
        backup_id = old_backup.get("backup_id")
        backup_path = BACKUP_DIR / backup_id

        if backup_path.exists():
            shutil.rmtree(backup_path)
            removed += 1
            print(f"Removed old backup: {backup_id}")

    save_state(state)
    return removed


# =============================================================================
# Recovery Operations
# =============================================================================

def verify_installation() -> dict[str, Any]:
    """Verify the current installation is intact."""
    issues = []
    checks = []

    # Check required files
    required_files = ["cli.py", "main.py", "requirements.txt"]
    for file in required_files:
        path = PROJECT_ROOT / file
        if path.exists():
            checks.append({"file": file, "status": "ok"})
        else:
            checks.append({"file": file, "status": "missing"})
            issues.append(f"Missing required file: {file}")

    # Check required directories
    required_dirs = ["core", "utils", "config"]
    for directory in required_dirs:
        path = PROJECT_ROOT / directory
        if path.exists() and path.is_dir():
            checks.append({"directory": directory, "status": "ok"})
        else:
            checks.append({"directory": directory, "status": "missing"})
            issues.append(f"Missing required directory: {directory}")

    # Check Python imports
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from utils.config import get_config_dict
        checks.append({"import": "utils.config", "status": "ok"})
    except ImportError as e:
        checks.append({"import": "utils.config", "status": "failed"})
        issues.append(f"Import error: {e}")

    return {
        "valid": len(issues) == 0,
        "checks": checks,
        "issues": issues,
    }


def attempt_recovery() -> bool:
    """Attempt automatic recovery from the most recent backup."""
    print("Attempting automatic recovery...")

    # Verify current state
    result = verify_installation()
    if result["valid"]:
        print("Installation appears valid, no recovery needed")
        return True

    print(f"Found {len(result['issues'])} issues:")
    for issue in result["issues"]:
        print(f"  - {issue}")

    # Find most recent valid backup
    backups = list_backups()
    if not backups:
        print("No backups available for recovery")
        return False

    # Try to restore from most recent backup
    for backup in backups:
        print(f"Attempting restore from: {backup.backup_id}")
        if restore_backup(backup.backup_id, force=True):
            # Verify after restore
            result = verify_installation()
            if result["valid"]:
                print("Recovery successful!")
                return True
            print("Restore completed but issues remain, trying next backup...")

    print("Recovery failed - no valid backups found")
    return False


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Rollback and recovery utilities"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a backup")
    backup_parser.add_argument(
        "-d", "--description",
        help="Backup description",
    )

    # List command
    subparsers.add_parser("list", help="List available backups")

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_id", help="Backup ID to restore")
    restore_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force restore even if checksum mismatch",
    )

    # Rollback command
    subparsers.add_parser("rollback", help="Rollback to previous version")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a backup")
    delete_parser.add_argument("backup_id", help="Backup ID to delete")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove old backups")
    cleanup_parser.add_argument(
        "--keep", "-k",
        type=int,
        default=MAX_BACKUPS,
        help=f"Number of backups to keep (default: {MAX_BACKUPS})",
    )

    # Verify command
    subparsers.add_parser("verify", help="Verify installation integrity")

    # Recover command
    subparsers.add_parser("recover", help="Attempt automatic recovery")

    # Status command
    subparsers.add_parser("status", help="Show rollback status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "backup":
        create_backup(args.description or "")
        return 0

    elif args.command == "list":
        backups = list_backups()
        if not backups:
            print("No backups found")
            return 0

        print(f"Available backups ({len(backups)}):\n")
        for b in backups:
            print(f"  {b.backup_id}")
            print(f"    Version: {b.version}")
            print(f"    Created: {b.timestamp}")
            print(f"    Git: {b.git_branch}@{b.git_commit}")
            print(f"    Size: {b.size_bytes / 1024:.1f} KB")
            print()
        return 0

    elif args.command == "restore":
        return 0 if restore_backup(args.backup_id, args.force) else 1

    elif args.command == "rollback":
        return 0 if rollback() else 1

    elif args.command == "delete":
        return 0 if delete_backup(args.backup_id) else 1

    elif args.command == "cleanup":
        removed = cleanup_old_backups(args.keep)
        print(f"Removed {removed} old backup(s)")
        return 0

    elif args.command == "verify":
        result = verify_installation()
        print("Installation verification:")
        for check in result["checks"]:
            status = "✓" if check.get("status") == "ok" else "✗"
            item = check.get("file") or check.get("directory") or check.get("import")
            print(f"  [{status}] {item}")

        if result["valid"]:
            print("\nInstallation is valid")
            return 0
        else:
            print(f"\nFound {len(result['issues'])} issue(s)")
            return 1

    elif args.command == "recover":
        return 0 if attempt_recovery() else 1

    elif args.command == "status":
        state = load_state()
        print("Rollback Status:")
        print(f"  Current backup: {state.current_backup_id or 'None'}")
        print(f"  Previous backup: {state.previous_backup_id or 'None'}")
        print(f"  Total backups: {len(state.backups)}")
        print(f"  Last action: {state.last_action or 'None'}")
        print(f"  Last action time: {state.last_action_time or 'Never'}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
