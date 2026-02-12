#!/usr/bin/env python3
"""
Ollama Automation Harness - Interactive Setup Wizard

A cross-platform setup wizard that guides users through the initial
configuration of the Ollama Automation Harness.

Usage:
    python scripts/setup_wizard.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"
SANDBOX_DIR = PROJECT_ROOT / "sandbox"


# =============================================================================
# Terminal Utilities
# =============================================================================

class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"

    @classmethod
    def disable(cls):
        """Disable colors for non-supporting terminals."""
        cls.RESET = ""
        cls.BOLD = ""
        cls.RED = ""
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.BLUE = ""
        cls.CYAN = ""


# Disable colors on Windows without proper terminal support
if sys.platform == "win32" and not os.environ.get("TERM"):
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        Colors.disable()


def clear_screen():
    """Clear the terminal screen."""
    os.system("cls" if sys.platform == "win32" else "clear")


def print_banner():
    """Print the setup wizard banner."""
    print(f"{Colors.CYAN}")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║                                                                   ║")
    print("║           Ollama Automation Harness - Setup Wizard                ║")
    print("║                                                                   ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")


def print_step(step_num: int, total: int, title: str):
    """Print a step header."""
    print(f"\n{Colors.BOLD}Step {step_num}/{total}: {title}{Colors.RESET}")
    print("─" * 50)


def print_success(message: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_error(message: str):
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message: str):
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")


def prompt(question: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    if default:
        result = input(f"{question} [{default}]: ").strip()
        return result if result else default
    return input(f"{question}: ").strip()


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Prompt user for yes/no answer."""
    suffix = "[Y/n]" if default else "[y/N]"
    result = input(f"{question} {suffix}: ").strip().lower()

    if not result:
        return default
    return result in ("y", "yes", "true", "1")


def prompt_choice(question: str, choices: list[str], default: int = 0) -> str:
    """Prompt user to choose from a list."""
    print(f"\n{question}")
    for i, choice in enumerate(choices):
        marker = ">" if i == default else " "
        print(f"  {marker} {i + 1}. {choice}")

    while True:
        result = input(f"\nEnter choice [1-{len(choices)}] (default: {default + 1}): ").strip()
        if not result:
            return choices[default]
        try:
            idx = int(result) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass
        print_error("Invalid choice. Please try again.")


def prompt_secret(question: str) -> str:
    """Prompt for a secret (hidden input)."""
    import getpass
    return getpass.getpass(f"{question}: ")


# =============================================================================
# System Checks
# =============================================================================

def check_python_version() -> bool:
    """Check if Python version is sufficient."""
    version = sys.version_info
    if version >= (3, 10):
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    print_error(f"Python {version.major}.{version.minor} is too old. Need 3.10+")
    return False


def check_ollama() -> bool:
    """Check if Ollama is installed."""
    if shutil.which("ollama"):
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version = result.stdout.strip() or result.stderr.strip()
            print_success(f"Ollama: {version}")
            return True
        except Exception:
            print_success("Ollama installed")
            return True
    print_warning("Ollama not found (optional for local LLM)")
    return False


def check_dependencies() -> bool:
    """Check if required packages are installed."""
    required = ["dotenv", "yaml", "anthropic"]
    missing = []

    for package in required:
        try:
            __import__(package)
        except ImportError:
            # Handle package name differences
            if package == "dotenv":
                try:
                    from dotenv import load_dotenv
                    continue
                except ImportError:
                    missing.append("python-dotenv")
            elif package == "yaml":
                try:
                    import yaml
                    continue
                except ImportError:
                    missing.append("pyyaml")
            else:
                missing.append(package)

    if missing:
        print_warning(f"Missing packages: {', '.join(missing)}")
        return False
    print_success("All required packages installed")
    return True


# =============================================================================
# Configuration
# =============================================================================

def create_directories() -> bool:
    """Create required directories."""
    directories = [LOGS_DIR, SANDBOX_DIR, CONFIG_DIR]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    print_success("Created required directories")
    return True


def setup_environment_file(config: dict) -> bool:
    """Create or update the .env file."""
    # Read template if exists
    template_lines = []
    if ENV_EXAMPLE.exists():
        template_lines = ENV_EXAMPLE.read_text().splitlines()

    # Build new content
    new_lines = []
    for line in template_lines:
        # Check if this line sets a value we have
        for key, value in config.items():
            if line.startswith(f"{key}="):
                line = f"{key}={value}"
                break
        new_lines.append(line)

    # Write to .env
    ENV_FILE.write_text("\n".join(new_lines) + "\n")
    print_success(f"Configuration saved to {ENV_FILE}")
    return True


def configure_api_keys() -> dict:
    """Configure API keys."""
    config = {}

    print("\nAPI Key Configuration")
    print("─" * 30)

    # Anthropic API Key
    print_info("Get your Anthropic API key at: https://console.anthropic.com/")
    api_key = prompt_secret("Enter Anthropic API key (leave blank to skip)")
    if api_key:
        config["ANTHROPIC_API_KEY"] = api_key

    return config


def configure_environment() -> dict:
    """Configure environment settings."""
    config = {}

    print("\nEnvironment Configuration")
    print("─" * 30)

    # Environment type
    env_type = prompt_choice(
        "Select environment:",
        ["development", "staging", "production"],
        default=0,
    )
    config["ENVIRONMENT"] = env_type

    # Debug mode
    if env_type == "development":
        config["DEBUG"] = "true"
    else:
        debug = prompt_yes_no("Enable debug mode?", default=False)
        config["DEBUG"] = "true" if debug else "false"

    return config


def configure_models() -> dict:
    """Configure LLM model settings."""
    config = {}

    print("\nModel Configuration")
    print("─" * 30)

    # Ollama model
    ollama_model = prompt("Ollama model name", default="llama3")
    config["OLLAMA_MODEL"] = ollama_model

    # Claude model
    claude_model = prompt_choice(
        "Select Claude model:",
        ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
        default=0,
    )
    config["CLAUDE_MODEL"] = claude_model

    return config


def configure_paths() -> dict:
    """Configure file paths."""
    config = {}

    print("\nPath Configuration")
    print("─" * 30)

    # Use defaults for most paths
    print_info("Using default paths (can be changed in .env later)")
    config["SANDBOX_DIR"] = "./sandbox"
    config["LOG_FILE"] = "./logs/automation.log"

    return config


# =============================================================================
# Main Wizard
# =============================================================================

def run_wizard():
    """Run the interactive setup wizard."""
    clear_screen()
    print_banner()

    print("Welcome to the Ollama Automation Harness setup wizard!")
    print("This wizard will help you configure the application.\n")

    if not prompt_yes_no("Ready to begin?"):
        print("\nSetup cancelled. Run this wizard again when ready.")
        return False

    total_steps = 5
    config = {}

    # Step 1: System Check
    print_step(1, total_steps, "System Check")
    all_ok = True
    all_ok &= check_python_version()
    check_ollama()  # Optional, don't fail
    check_dependencies()
    create_directories()

    if not all_ok:
        print_error("\nSome requirements not met. Please fix issues and try again.")
        return False

    # Step 2: Environment
    print_step(2, total_steps, "Environment Configuration")
    config.update(configure_environment())

    # Step 3: API Keys
    print_step(3, total_steps, "API Keys")
    config.update(configure_api_keys())

    # Step 4: Model Settings
    print_step(4, total_steps, "Model Settings")
    config.update(configure_models())

    # Step 5: Paths
    print_step(5, total_steps, "Path Configuration")
    config.update(configure_paths())

    # Save configuration
    print(f"\n{Colors.BOLD}Saving Configuration{Colors.RESET}")
    print("─" * 50)
    setup_environment_file(config)

    # Summary
    print(f"\n{Colors.GREEN}╔═══════════════════════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.GREEN}║                     Setup Complete!                               ║{Colors.RESET}")
    print(f"{Colors.GREEN}╚═══════════════════════════════════════════════════════════════════╝{Colors.RESET}")

    print("\nConfiguration Summary:")
    print(f"  Environment: {config.get('ENVIRONMENT', 'development')}")
    print(f"  Debug Mode:  {config.get('DEBUG', 'false')}")
    print(f"  Ollama Model: {config.get('OLLAMA_MODEL', 'llama3')}")
    print(f"  Claude Model: {config.get('CLAUDE_MODEL', 'claude-sonnet-4-20250514')}")
    print(f"  API Key:     {'configured' if config.get('ANTHROPIC_API_KEY') else 'not set'}")

    print("\nNext Steps:")
    print("  1. Review your configuration: cat .env")
    print("  2. Start the application: python main.py --help")
    print("  3. Run with Ollama: python main.py run")
    print("  4. Run with Claude API: python main.py run --mode api")

    return True


def main():
    """Main entry point."""
    try:
        success = run_wizard()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
