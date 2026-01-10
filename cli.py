#!/usr/bin/env python3
"""
Enhanced command-line interface for Ollama Automation Harness.

Provides subcommands for running, configuration, and diagnostics.
"""

import argparse
import sys

# Version information
__version__ = "0.1.0"
__description__ = "AI-powered development automation with human oversight"


def create_parser() -> argparse.ArgumentParser:
    """
    Create the main argument parser with subcommands.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="ollama-harness",
        description=f"Ollama Automation Harness v{__version__} - {__description__}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s run                      Start interactive mode
  %(prog)s run -p "Create a test"   Run with initial prompt
  %(prog)s config show              Show current configuration
  %(prog)s config validate          Validate configuration
  %(prog)s check                    Run system health checks
  %(prog)s version                  Show version information

For more information, visit: https://github.com/example/ollama-harness
        """,
    )

    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # Create subparsers
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        help="Available commands",
    )

    # Run subcommand
    _add_run_parser(subparsers)

    # Config subcommand
    _add_config_parser(subparsers)

    # Check subcommand
    _add_check_parser(subparsers)

    # Version subcommand (detailed)
    _add_version_parser(subparsers)

    return parser


def _add_run_parser(subparsers) -> None:
    """Add the 'run' subcommand parser."""
    run_parser = subparsers.add_parser(
        "run",
        help="Run the automation harness",
        description="Start the automation harness in interactive or single-prompt mode.",
    )

    run_parser.add_argument(
        "-p", "--prompt",
        type=str,
        metavar="TEXT",
        help="Initial prompt to process (interactive if not provided)",
    )

    run_parser.add_argument(
        "-f", "--file",
        type=str,
        metavar="PATH",
        help="Read prompt from file",
    )

    run_parser.add_argument(
        "--config",
        type=str,
        metavar="PATH",
        help="Path to permissions config file",
    )

    run_parser.add_argument(
        "--sandbox",
        type=str,
        metavar="PATH",
        help="Path to sandbox directory",
    )

    run_parser.add_argument(
        "-e", "--env",
        type=str,
        choices=["development", "staging", "production", "testing"],
        metavar="ENV",
        help="Override environment (development, staging, production, testing)",
    )

    run_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    run_parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress non-essential output",
    )

    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )

    run_parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="Auto-approve low-risk actions (use with caution)",
    )

    run_parser.add_argument(
        "--model",
        type=str,
        metavar="NAME",
        help="Override the AI model to use",
    )

    run_parser.add_argument(
        "--timeout",
        type=int,
        metavar="SECONDS",
        help="Command execution timeout in seconds",
    )


def _add_config_parser(subparsers) -> None:
    """Add the 'config' subcommand parser."""
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management",
        description="View and validate configuration settings.",
    )

    config_subparsers = config_parser.add_subparsers(
        title="config commands",
        dest="config_command",
    )

    # config show
    config_subparsers.add_parser(
        "show",
        help="Show current configuration",
        description="Display all current configuration values (secrets are masked).",
    )

    # config validate
    config_subparsers.add_parser(
        "validate",
        help="Validate configuration",
        description="Check configuration for errors and warnings.",
    )

    # config init
    init_parser = config_subparsers.add_parser(
        "init",
        help="Initialize configuration files",
        description="Create default configuration files if they don't exist.",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )

    # config path
    config_subparsers.add_parser(
        "path",
        help="Show configuration file paths",
        description="Display paths to all configuration files.",
    )


def _add_check_parser(subparsers) -> None:
    """Add the 'check' subcommand parser."""
    check_parser = subparsers.add_parser(
        "check",
        help="Run system health checks",
        description="Verify system dependencies and configuration.",
    )

    check_parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix issues automatically",
    )

    check_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed check results",
    )


def _add_version_parser(subparsers) -> None:
    """Add the 'version' subcommand parser."""
    subparsers.add_parser(
        "version",
        help="Show detailed version information",
        description="Display version and system information.",
    )


def cmd_run(args: argparse.Namespace) -> int:
    """
    Execute the 'run' command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    import os

    # Override environment if specified
    if args.env:
        os.environ["ENVIRONMENT"] = args.env

    # Read prompt from file if specified
    prompt = args.prompt
    if args.file:
        try:
            with open(args.file) as f:
                prompt = f.read().strip()
        except OSError as e:
            print(f"Error reading prompt file: {e}", file=sys.stderr)
            return 1

    # Import and run main
    from main import main as run_main

    # Modify sys.argv for main's argparse
    sys.argv = ["ollama-harness"]
    if prompt:
        sys.argv.extend(["-p", prompt])
    if args.config:
        sys.argv.extend(["--config", args.config])
    if args.sandbox:
        sys.argv.extend(["--sandbox", args.sandbox])
    if args.verbose:
        sys.argv.append("-v")

    try:
        run_main()
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


def cmd_config(args: argparse.Namespace) -> int:
    """
    Execute the 'config' command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    from utils.config import get_config_dict
    from utils.secrets import (
        check_environment_security,
        get_secure_config,
        init_secure_config,
        validate_config_on_startup,
    )

    config_command = args.config_command

    if config_command == "show":
        # Show configuration
        init_secure_config()
        config = get_config_dict()
        secure_config = get_secure_config()

        print("Current Configuration")
        print("=" * 50)
        print(f"\nEnvironment: {secure_config.environment.value}")
        print("\nGeneral Settings:")
        for key, value in config.items():
            if key not in ("dangerous_keywords", "allowed_extensions"):
                print(f"  {key}: {value}")

        print("\nSecrets (masked):")
        safe_dict = secure_config.to_safe_dict()
        for name, masked in safe_dict.get("secrets", {}).items():
            print(f"  {name}: {masked}")

        print("\nDangerous Keywords:")
        for kw in config.get("dangerous_keywords", []):
            print(f"  - {kw}")

        print("\nAllowed Extensions:")
        print(f"  {', '.join(config.get('allowed_extensions', []))}")

        return 0

    elif config_command == "validate":
        # Validate configuration
        print("Validating configuration...")
        print("-" * 40)

        init_secure_config()
        errors = validate_config_on_startup()
        secure_config = get_secure_config()
        config_errors = secure_config.validate()
        security_warnings = check_environment_security()

        all_errors = errors + config_errors
        has_errors = False

        for error in all_errors:
            symbol = "[X]" if error.severity == "error" else "[!]"
            print(f"{symbol} {error.key}: {error.message}")
            if error.severity == "error":
                has_errors = True

        for warning in security_warnings:
            print(f"[!] Security: {warning}")

        if not all_errors and not security_warnings:
            print("[OK] All configuration checks passed")
            return 0

        return 1 if has_errors else 0

    elif config_command == "init":
        # Initialize configuration files
        from pathlib import Path
        from shutil import copy2

        files_to_create = [
            (".env.example", ".env"),
            ("config/permissions.yaml", "config/permissions.yaml"),
        ]

        for src, dest in files_to_create:
            dest_path = Path(dest)
            if dest_path.exists() and not args.force:
                print(f"[SKIP] {dest} already exists (use --force to overwrite)")
            else:
                src_path = Path(src)
                if src_path.exists():
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    copy2(src_path, dest_path)
                    print(f"[OK] Created {dest}")
                else:
                    print(f"[SKIP] Source {src} not found")

        return 0

    elif config_command == "path":
        # Show configuration paths
        from pathlib import Path

        from utils.config import LOG_FILE, PERMISSIONS_FILE, SANDBOX_DIR

        print("Configuration File Paths")
        print("=" * 50)
        print(f"Permissions: {PERMISSIONS_FILE}")
        print(f"Sandbox:     {SANDBOX_DIR}")
        print(f"Log file:    {LOG_FILE}")
        print(f".env file:   {Path('.env').resolve()}")

        return 0

    else:
        print("Please specify a config command: show, validate, init, or path")
        return 1


def cmd_check(args: argparse.Namespace) -> int:
    """
    Execute the 'check' command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    import shutil
    from pathlib import Path

    print("System Health Check")
    print("=" * 50)

    checks_passed = 0
    checks_failed = 0

    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 10):
        print(f"[OK] Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        checks_passed += 1
    else:
        print(f"[X] Python {python_version.major}.{python_version.minor} (requires 3.10+)")
        checks_failed += 1

    # Check Ollama installation
    ollama_path = shutil.which("ollama")
    if ollama_path:
        print(f"[OK] Ollama found: {ollama_path}")
        checks_passed += 1
    else:
        print("[X] Ollama not found in PATH")
        checks_failed += 1
        if args.fix:
            print("    Install from: https://ollama.ai")

    # Check required directories
    dirs_to_check = ["sandbox", "logs", "config"]
    for dir_name in dirs_to_check:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"[OK] Directory exists: {dir_name}/")
            checks_passed += 1
        else:
            if args.fix:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"[OK] Created directory: {dir_name}/")
                checks_passed += 1
            else:
                print(f"[X] Directory missing: {dir_name}/")
                checks_failed += 1

    # Check .env file
    env_file = Path(".env")
    if env_file.exists():
        print("[OK] .env file exists")
        checks_passed += 1
    else:
        print("[!] .env file not found (optional)")

    # Check permissions file
    perm_file = Path("config/permissions.yaml")
    if perm_file.exists():
        print("[OK] Permissions file exists")
        checks_passed += 1
    else:
        print("[!] Permissions file not found (will use defaults)")

    # Check required packages
    required_packages = [
        ("anthropic", "anthropic"),
        ("yaml", "PyYAML"),
        ("dotenv", "python-dotenv"),
    ]

    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
            print(f"[OK] Package installed: {package_name}")
            checks_passed += 1
        except ImportError:
            print(f"[X] Package missing: {package_name}")
            checks_failed += 1
            if args.fix:
                print(f"    Install with: pip install {package_name}")

    # Summary
    print("-" * 50)
    print(f"Passed: {checks_passed}, Failed: {checks_failed}")

    return 0 if checks_failed == 0 else 1


def cmd_version(args: argparse.Namespace) -> int:
    """
    Execute the 'version' command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    import platform

    print(f"Ollama Automation Harness v{__version__}")
    print("=" * 50)
    print(f"Python:   {platform.python_version()}")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Machine:  {platform.machine()}")

    # Check model availability
    try:
        from core.claude import get_model_info
        model_info = get_model_info()
        print(f"\nAI Mode:  {model_info['mode']}")
        print(f"Model:    {model_info['model']}")
    except Exception:
        print("\nAI Mode:  Not configured")

    return 0


def main() -> int:
    """
    Main entry point for CLI.

    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args()

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        return 0

    # Dispatch to command handler
    commands = {
        "run": cmd_run,
        "config": cmd_config,
        "check": cmd_check,
        "version": cmd_version,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
