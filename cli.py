#!/usr/bin/env python3
"""
Enhanced command-line interface for Ollama Automation Harness.

Provides subcommands for running, configuration, and diagnostics.
"""

import argparse
import sys

from utils.version import __version__

# Description for CLI
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

    # Metrics subcommand
    _add_metrics_parser(subparsers)

    # Status/monitoring subcommand
    _add_status_parser(subparsers)

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


def _add_metrics_parser(subparsers) -> None:
    """Add the 'metrics' subcommand parser."""
    metrics_parser = subparsers.add_parser(
        "metrics",
        help="Show application metrics and telemetry",
        description="Display collected metrics and telemetry data.",
    )
    metrics_parser.add_argument(
        "--format", "-f",
        choices=["text", "json", "prometheus"],
        default="text",
        help="Output format (default: text)",
    )
    metrics_parser.add_argument(
        "--save",
        type=str,
        metavar="FILE",
        help="Save metrics to file",
    )


def _add_status_parser(subparsers) -> None:
    """Add the 'status' subcommand parser."""
    status_parser = subparsers.add_parser(
        "status",
        help="Show application health and monitoring status",
        description="Display health checks, errors, and performance metrics.",
    )
    status_parser.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    status_parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Continuously watch status (refresh every 5s)",
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

    from utils.version import get_version_info

    info = get_version_info()

    print(f"{info['app_name']} v{info['version']}")
    print("=" * 50)
    print(f"Version:  {info['major']}.{info['minor']}.{info['patch']}")
    print(f"License:  {info['license']}")
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


def cmd_metrics(args: argparse.Namespace) -> int:
    """
    Execute the 'metrics' command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    from pathlib import Path

    from utils.metrics import get_registry
    from utils.telemetry import get_telemetry_summary

    registry = get_registry()
    output_format = getattr(args, "format", "text")
    save_path = getattr(args, "save", None)

    if output_format == "json":
        output = registry.to_json()
    elif output_format == "prometheus":
        output = registry.to_prometheus()
    else:
        # Text format
        summary = get_telemetry_summary()
        lines = [
            "Ollama Automation Harness - Metrics",
            "=" * 50,
            "",
            f"Uptime: {summary['metrics']['uptime_seconds']:.1f} seconds",
            f"Total Metrics: {summary['metrics']['total_metrics']}",
            "",
            "Telemetry:",
            f"  Session ID: {summary['telemetry']['session_id']}",
            f"  Enabled: {summary['telemetry']['enabled']}",
            f"  Buffered Events: {summary['telemetry']['buffered_events']}",
            "",
            "Metrics:",
        ]

        for metric_value in registry.collect():
            lines.append(f"  {metric_value.name}: {metric_value.value}")

        output = "\n".join(lines)

    # Save or print
    if save_path:
        Path(save_path).write_text(output)
        print(f"Metrics saved to: {save_path}")
    else:
        print(output)

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """
    Execute the 'status' command.

    Args:
        args: Parsed arguments

    Returns:
        Exit code
    """
    import json as json_module
    import time as time_module

    from utils.monitoring import get_status

    output_format = getattr(args, "format", "text")
    watch_mode = getattr(args, "watch", False)

    def print_status():
        status = get_status()

        if output_format == "json":
            print(json_module.dumps(status, indent=2))
        else:
            # Text format
            status_symbol = {
                "healthy": "\033[92m●\033[0m",    # Green
                "degraded": "\033[93m●\033[0m",   # Yellow
                "unhealthy": "\033[91m●\033[0m",  # Red
                "unknown": "\033[90m●\033[0m",    # Gray
            }.get(status["status"], "●")

            print("\nOllama Automation Harness - Status")
            print("=" * 50)
            print(f"Status:  {status_symbol} {status['status'].upper()}")
            print(f"Uptime:  {status['uptime']}")
            print(f"Time:    {status['timestamp']}")

            # Health checks
            print("\nHealth Checks:")
            for name, check in status["health"]["checks"].items():
                check_symbol = {
                    "healthy": "✓",
                    "degraded": "!",
                    "unhealthy": "✗",
                }.get(check["status"], "?")
                print(f"  [{check_symbol}] {name}: {check['message']}")

            # Performance
            perf = status["performance"]
            print("\nPerformance:")
            print(f"  Requests:     {perf['requests']}")
            print(f"  Throughput:   {perf['throughput_rps']} req/s")
            print(f"  Avg Response: {perf['avg_response_ms']} ms")
            print(f"  P95 Response: {perf['p95_response_ms']} ms")

            # Errors
            errors = status["errors"]
            print(f"\nErrors (last {errors['window_seconds']}s):")
            print(f"  Count:     {errors['total_errors']}")
            print(f"  Rate:      {errors['error_rate']:.2f}/s")
            print(f"  Threshold: {errors['threshold']}")

            # Alerts
            if status["alerts"]:
                print("\nActive Alerts:")
                for alert in status["alerts"]:
                    print(f"  [{alert['severity']}] {alert['title']}: {alert['message']}")

    if watch_mode:
        try:
            while True:
                print("\033[2J\033[H")  # Clear screen
                print_status()
                print("\nPress Ctrl+C to exit...")
                time_module.sleep(5)
        except KeyboardInterrupt:
            print("\nStopped watching.")
    else:
        print_status()

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
        "metrics": cmd_metrics,
        "status": cmd_status,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
