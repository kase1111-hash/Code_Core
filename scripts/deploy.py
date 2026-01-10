#!/usr/bin/env python3
"""
Deployment automation script for Ollama Automation Harness.

Supports multiple deployment targets and strategies:
- Local installation
- Remote server deployment via SSH
- Docker container deployment
- PyPI package publishing

Usage:
    python scripts/deploy.py local              # Install locally
    python scripts/deploy.py remote             # Deploy to remote server
    python scripts/deploy.py docker             # Deploy as Docker container
    python scripts/deploy.py pypi               # Publish to PyPI
    python scripts/deploy.py --env production   # Use production config
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


# =============================================================================
# Configuration
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEPLOY_CONFIG_FILE = PROJECT_ROOT / "config" / "deploy.json"
DIST_DIR = PROJECT_ROOT / "dist"
BACKUP_DIR = PROJECT_ROOT / ".deploy_backups"


@dataclass
class DeploymentConfig:
    """Deployment configuration."""

    environment: str = "development"
    target: str = "local"

    # Remote deployment
    remote_host: Optional[str] = None
    remote_user: Optional[str] = None
    remote_path: Optional[str] = None
    ssh_key: Optional[str] = None

    # Docker deployment
    docker_registry: Optional[str] = None
    docker_image: str = "ollama-harness"
    docker_tag: str = "latest"

    # PyPI deployment
    pypi_repository: str = "pypi"
    pypi_token: Optional[str] = None

    # General options
    backup_before_deploy: bool = True
    run_tests_before_deploy: bool = True
    notify_on_complete: bool = False


# =============================================================================
# Utilities
# =============================================================================

class Colors:
    """Terminal colors."""

    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"


def log_info(msg: str):
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")


def log_success(msg: str):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {msg}")


def log_warning(msg: str):
    print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {msg}")


def log_error(msg: str):
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")


def log_step(step: int, total: int, msg: str):
    print(f"\n{Colors.BOLD}[{step}/{total}] {msg}{Colors.RESET}")


def run_command(
    cmd: list[str],
    cwd: Optional[Path] = None,
    capture: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a shell command."""
    log_info(f"Running: {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        cwd=cwd or PROJECT_ROOT,
        capture_output=capture,
        text=True,
        check=check,
    )


def load_config(env: str) -> DeploymentConfig:
    """Load deployment configuration for environment."""
    config = DeploymentConfig(environment=env)

    if DEPLOY_CONFIG_FILE.exists():
        with open(DEPLOY_CONFIG_FILE) as f:
            data = json.load(f)

        # Load environment-specific config
        env_config = data.get(env, data.get("default", {}))
        for key, value in env_config.items():
            if hasattr(config, key):
                setattr(config, key, value)

    # Override with environment variables
    if os.environ.get("DEPLOY_REMOTE_HOST"):
        config.remote_host = os.environ["DEPLOY_REMOTE_HOST"]
    if os.environ.get("DEPLOY_REMOTE_USER"):
        config.remote_user = os.environ["DEPLOY_REMOTE_USER"]
    if os.environ.get("DEPLOY_REMOTE_PATH"):
        config.remote_path = os.environ["DEPLOY_REMOTE_PATH"]
    if os.environ.get("DOCKER_REGISTRY"):
        config.docker_registry = os.environ["DOCKER_REGISTRY"]
    if os.environ.get("PYPI_TOKEN"):
        config.pypi_token = os.environ["PYPI_TOKEN"]

    return config


# =============================================================================
# Pre-deployment Checks
# =============================================================================

def check_prerequisites(config: DeploymentConfig) -> bool:
    """Check deployment prerequisites."""
    log_info("Checking prerequisites...")
    checks_passed = True

    # Check Python version
    if sys.version_info < (3, 10):
        log_error("Python 3.10+ required")
        checks_passed = False

    # Check git status (warn if dirty)
    result = run_command(["git", "status", "--porcelain"], capture=True, check=False)
    if result.stdout.strip():
        log_warning("Working directory has uncommitted changes")

    return checks_passed


def run_tests(config: DeploymentConfig) -> bool:
    """Run test suite before deployment."""
    if not config.run_tests_before_deploy:
        log_info("Skipping tests (disabled in config)")
        return True

    log_info("Running test suite...")
    result = run_command(
        [sys.executable, "-m", "pytest", "tests/", "-x", "--tb=short", "-q"],
        check=False,
    )
    return result.returncode == 0


def create_backup(config: DeploymentConfig) -> Optional[Path]:
    """Create backup before deployment."""
    if not config.backup_before_deploy:
        return None

    log_info("Creating backup...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{config.environment}_{timestamp}"
    backup_path = BACKUP_DIR / backup_name

    # Create backup manifest
    manifest = {
        "timestamp": timestamp,
        "environment": config.environment,
        "git_commit": get_git_commit(),
        "version": get_version(),
    }

    backup_path.mkdir(parents=True, exist_ok=True)
    with open(backup_path / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    log_success(f"Backup created: {backup_path}")
    return backup_path


def get_git_commit() -> str:
    """Get current git commit hash."""
    result = run_command(
        ["git", "rev-parse", "--short", "HEAD"],
        capture=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def get_version() -> str:
    """Get current version."""
    try:
        from utils.version import get_version
        return get_version()
    except ImportError:
        return "unknown"


# =============================================================================
# Deployment Targets
# =============================================================================

def deploy_local(config: DeploymentConfig) -> bool:
    """Deploy locally (install in development mode)."""
    log_step(1, 3, "Building package")
    run_command([sys.executable, "-m", "build"])

    log_step(2, 3, "Installing package")
    wheels = list(DIST_DIR.glob("*.whl"))
    if not wheels:
        log_error("No wheel found in dist/")
        return False

    run_command([sys.executable, "-m", "pip", "install", str(wheels[0]), "--force-reinstall"])

    log_step(3, 3, "Verifying installation")
    result = run_command(
        [sys.executable, "-c", "from utils.version import get_version; print(get_version())"],
        capture=True,
    )
    log_success(f"Installed version: {result.stdout.strip()}")

    return True


def deploy_remote(config: DeploymentConfig) -> bool:
    """Deploy to remote server via SSH."""
    if not config.remote_host or not config.remote_user:
        log_error("Remote host and user must be configured")
        return False

    remote_path = config.remote_path or "/opt/ollama-harness"
    ssh_target = f"{config.remote_user}@{config.remote_host}"

    ssh_opts = []
    if config.ssh_key:
        ssh_opts.extend(["-i", config.ssh_key])

    log_step(1, 4, "Building package")
    run_command([sys.executable, "scripts/package.py", "zip"])

    # Find the zip file
    zips = list(DIST_DIR.glob("*.zip"))
    if not zips:
        log_error("No zip package found")
        return False
    zip_file = zips[0]

    log_step(2, 4, "Copying package to remote")
    run_command([
        "scp", *ssh_opts,
        str(zip_file),
        f"{ssh_target}:/tmp/{zip_file.name}",
    ])

    log_step(3, 4, "Installing on remote")
    install_script = f"""
        set -e
        cd /tmp
        rm -rf ollama-harness-deploy
        unzip -o {zip_file.name} -d ollama-harness-deploy
        cd ollama-harness-deploy/ollama-harness
        sudo mkdir -p {remote_path}
        sudo cp -r . {remote_path}/
        cd {remote_path}
        python3 -m venv venv || true
        source venv/bin/activate
        pip install -r requirements.txt
        echo "Deployment complete"
    """
    run_command([
        "ssh", *ssh_opts,
        ssh_target,
        install_script,
    ])

    log_step(4, 4, "Verifying remote installation")
    run_command([
        "ssh", *ssh_opts,
        ssh_target,
        f"cd {remote_path} && source venv/bin/activate && python -c 'from utils.version import get_version; print(get_version())'",
    ])

    return True


def deploy_docker(config: DeploymentConfig) -> bool:
    """Deploy as Docker container."""
    image_name = config.docker_image
    tag = config.docker_tag

    if config.docker_registry:
        full_image = f"{config.docker_registry}/{image_name}:{tag}"
    else:
        full_image = f"{image_name}:{tag}"

    log_step(1, 4, "Building Docker image")
    run_command([
        "docker", "build",
        "-f", "Dockerfile.prod",
        "-t", full_image,
        ".",
    ])

    log_step(2, 4, "Tagging image")
    # Also tag as latest if not already
    if tag != "latest":
        latest_image = full_image.replace(f":{tag}", ":latest")
        run_command(["docker", "tag", full_image, latest_image])

    log_step(3, 4, "Pushing to registry")
    if config.docker_registry:
        run_command(["docker", "push", full_image])
        if tag != "latest":
            run_command(["docker", "push", latest_image])
        log_success(f"Pushed: {full_image}")
    else:
        log_warning("No registry configured, skipping push")

    log_step(4, 4, "Verifying image")
    run_command([
        "docker", "run", "--rm", full_image,
        "python", "-c", "from utils.version import get_version; print(get_version())",
    ])

    return True


def deploy_pypi(config: DeploymentConfig) -> bool:
    """Publish to PyPI."""
    log_step(1, 4, "Cleaning previous builds")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    log_step(2, 4, "Building distribution packages")
    run_command([sys.executable, "-m", "build"])

    log_step(3, 4, "Checking package")
    run_command([sys.executable, "-m", "twine", "check", "dist/*"])

    log_step(4, 4, "Uploading to PyPI")
    upload_cmd = [sys.executable, "-m", "twine", "upload"]

    if config.pypi_repository == "testpypi":
        upload_cmd.extend(["--repository", "testpypi"])

    if config.pypi_token:
        upload_cmd.extend(["-u", "__token__", "-p", config.pypi_token])

    upload_cmd.append("dist/*")
    run_command(upload_cmd)

    log_success("Published to PyPI")
    return True


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Deploy Ollama Automation Harness"
    )
    parser.add_argument(
        "target",
        choices=["local", "remote", "docker", "pypi"],
        help="Deployment target",
    )
    parser.add_argument(
        "--env", "-e",
        default="development",
        choices=["development", "staging", "production"],
        help="Deployment environment",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests before deployment",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip creating backup",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )

    args = parser.parse_args()

    print(f"\n{Colors.BOLD}Ollama Automation Harness - Deployment{Colors.RESET}")
    print("=" * 50)
    print(f"Target:      {args.target}")
    print(f"Environment: {args.env}")
    print()

    # Load configuration
    config = load_config(args.env)
    config.target = args.target

    if args.skip_tests:
        config.run_tests_before_deploy = False
    if args.skip_backup:
        config.backup_before_deploy = False

    if args.dry_run:
        print("Dry run mode - no changes will be made")
        print(f"\nConfiguration:")
        for key, value in vars(config).items():
            if not key.startswith("_"):
                print(f"  {key}: {value}")
        return 0

    # Pre-deployment checks
    if not check_prerequisites(config):
        log_error("Prerequisites check failed")
        return 1

    # Run tests
    if not run_tests(config):
        log_error("Tests failed - aborting deployment")
        return 1

    # Create backup
    create_backup(config)

    # Deploy
    deploy_func = {
        "local": deploy_local,
        "remote": deploy_remote,
        "docker": deploy_docker,
        "pypi": deploy_pypi,
    }.get(args.target)

    try:
        success = deploy_func(config)
    except subprocess.CalledProcessError as e:
        log_error(f"Deployment failed: {e}")
        return 1
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        return 1

    if success:
        print()
        log_success(f"Deployment to {args.target} ({args.env}) completed!")
        return 0
    else:
        log_error("Deployment failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
