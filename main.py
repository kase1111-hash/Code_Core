#!/usr/bin/env python3
"""
Ollama Automation Harness - Main Entry Point

A CLI application that pairs Claude with Ollama for automated
development workflows with human oversight.
"""

import argparse
import sys
import time

__version__ = "1.0.0"

from core.classifier import Decision, classify
from core.claude import ClaudeError, get_model_info, get_response
from core.executor import ExecutionResult, execute
from core.safety import PermissionManager
from utils.config import (
    LOOP_DELAY,
    MAX_REPLY_LENGTH,
    PERMISSIONS_FILE,
    SANDBOX_DIR,
    ensure_directories,
)
from utils.error_tracking import (
    capture_exception,
    init_error_tracking,
)
from utils.errors import (
    HarnessError,
    format_error_for_user,
    get_recovery_suggestion,
    is_recoverable,
    wrap_exception,
)
from utils.logger import (
    log_action,
    log_error,
    log_shutdown,
    log_startup,
    log_user_decision,
    setup_logger,
)
from utils.secrets import (
    get_secure_config,
    init_secure_config,
)
from utils.validation import (
    ValidationError,
    truncate_response,
    validate_prompt,
    validate_response,
    validate_user_choice,
)


def main() -> None:
    """Main entry point for the automation harness."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="ollama-harness",
        description="Ollama Automation Harness - AI-powered development automation",
        epilog="For more options, use the 'cli.py' entry point with subcommands.",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-p", "--prompt",
        type=str,
        metavar="TEXT",
        help="Initial prompt (if not provided, will prompt interactively)",
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        metavar="PATH",
        help="Read prompt from file",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=PERMISSIONS_FILE,
        metavar="PATH",
        help="Path to permissions config file",
    )
    parser.add_argument(
        "--sandbox",
        type=str,
        default=SANDBOX_DIR,
        metavar="PATH",
        help="Path to sandbox directory",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress non-essential output",
    )
    args = parser.parse_args()

    # Read prompt from file if specified
    if args.file:
        try:
            with open(args.file) as f:
                args.prompt = f.read().strip()
        except OSError as e:
            print(f"Error reading prompt file: {e}", file=sys.stderr)
            sys.exit(1)

    # Initialize
    ensure_directories()
    setup_logger()
    init_secure_config()  # Initialize secure configuration
    init_error_tracking()  # Initialize Sentry/ELK error tracking
    log_startup()
    permissions = PermissionManager(args.config)

    # Display configuration
    model_info = get_model_info()
    secure_config = get_secure_config()
    if not args.quiet:
        print(f"Ollama Automation Harness v{__version__}")
        print(f"Mode: {model_info['mode']} ({model_info['model']})")
        print(f"Environment: {secure_config.environment.value}")
        print(f"Sandbox: {args.sandbox}")
        print("-" * 40)

    # Get initial prompt
    if args.prompt:
        current_prompt = args.prompt
    else:
        try:
            current_prompt = input("Enter your prompt: ").strip()
            if not current_prompt:
                print("No prompt provided. Exiting.")
                return
        except EOFError:
            print("\nNo input provided. Exiting.")
            return

    # Validate the initial prompt
    try:
        current_prompt = validate_prompt(current_prompt)
    except ValidationError as e:
        print(f"Invalid prompt: {e}")
        return

    # Main loop
    try:
        while True:
            next_prompt = process_iteration(
                current_prompt,
                permissions,
                args.sandbox,
                args.verbose,
            )

            if next_prompt is None:
                break

            current_prompt = next_prompt
            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        log_shutdown("keyboard_interrupt")

    except HarnessError as e:
        log_error(e, "main_loop")
        capture_exception(e, context="main_loop")  # Send to Sentry/ELK
        print(f"\n[Fatal Error]: {format_error_for_user(e)}")
        suggestion = get_recovery_suggestion(e)
        if suggestion:
            print(f"[Suggestion]: {suggestion}")
        log_shutdown("error")
        sys.exit(1)

    except Exception as e:
        wrapped = wrap_exception(e, "main_loop")
        log_error(wrapped, "main_loop")
        capture_exception(e, context="main_loop")  # Send to Sentry/ELK
        print(f"\n[Fatal Error]: {format_error_for_user(wrapped)}")
        log_shutdown("error")
        sys.exit(1)

    log_shutdown("normal")
    print("\nGoodbye!")


def process_iteration(
    prompt: str,
    permissions: PermissionManager,
    sandbox_root: str,
    verbose: bool = False,
) -> str | None:
    """
    Process a single iteration of the automation loop.

    Args:
        prompt: User prompt to process
        permissions: Permission manager instance
        sandbox_root: Path to sandbox directory
        verbose: Enable verbose output

    Returns:
        Next prompt or None to exit
    """
    try:
        # Validate prompt before sending
        try:
            prompt = validate_prompt(prompt)
        except ValidationError as e:
            print(f"\n[Error]: Invalid prompt - {e}")
            return get_next_prompt()

        # Get Claude's response
        print(f"\n[Prompt]: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        print("[Thinking...]")

        claude_reply = get_response(prompt)
        claude_reply = validate_response(claude_reply)
        display_response(claude_reply)

        # Classify the action
        decision = classify(claude_reply)
        decision = permissions.enforce(decision)

        print(f"\n[Decision]: {decision.action} ({decision.reason})")
        print(f"[Risk]: {decision.risk_level}")
        if decision.command:
            print(f"[Command]: {decision.command[:100]}")

        if decision.action == "auto":
            # Execute automatically
            if decision.command:
                result = execute(decision.command, sandbox_root)
                log_action("auto_exec", decision, result)

                if result.success:
                    print("\n[Result]: Success")
                    if verbose and result.output:
                        print(result.output[:500])
                else:
                    print(f"\n[Result]: Failed - {result.error}")

                # Build continuation prompt
                return build_continuation_prompt(claude_reply, result)
            else:
                print("\n[Info]: No command to execute")
                return get_next_prompt()

        else:  # "user" action required
            return handle_user_action(decision, permissions, sandbox_root)

    except ClaudeError as e:
        log_error(e, "get_response")
        capture_exception(e, context="get_response")
        print(f"\n[Error]: {format_error_for_user(e)}")
        suggestion = get_recovery_suggestion(wrap_exception(e, "get_response"))
        if suggestion:
            print(f"[Suggestion]: {suggestion}")
        return get_next_prompt()

    except HarnessError as e:
        log_error(e, "process_iteration")
        capture_exception(e, context="process_iteration")
        print(f"\n[Error]: {format_error_for_user(e)}")
        if is_recoverable(e):
            suggestion = get_recovery_suggestion(e)
            if suggestion:
                print(f"[Suggestion]: {suggestion}")
            return get_next_prompt()
        return None

    except Exception as e:
        wrapped = wrap_exception(e, "process_iteration")
        log_error(wrapped, "process_iteration")
        capture_exception(e, context="process_iteration")
        print(f"\n[Error]: {format_error_for_user(wrapped)}")
        return get_next_prompt()


def handle_user_action(
    decision: Decision,
    permissions: PermissionManager,
    sandbox_root: str,
) -> str | None:
    """
    Handle an action that requires user approval.

    Args:
        decision: Decision requiring user input
        permissions: Permission manager instance
        sandbox_root: Path to sandbox directory

    Returns:
        Next prompt, modified prompt, or None to exit
    """
    print(f"\n[!] User action required: {decision.reason}")
    if decision.command:
        print(f"Command: {decision.command}")

    valid_choices = {"y", "m", "s", "q"}
    try:
        user_input = input("\nApprove (y), modify (m), skip (s), quit (q): ").strip().lower()
        user_input = validate_user_choice(user_input, valid_choices)
    except ValidationError:
        print("Invalid choice. Skipping.")
        user_input = "s"
    except EOFError:
        return None

    log_user_decision(decision, user_input)

    if user_input == "q":
        return None

    elif user_input == "y":
        # Execute the command
        if decision.command:
            result = execute(decision.command, sandbox_root)
            log_action("user_approved", decision, result, "y")

            if result.success:
                print("\n[Result]: Success")
                if result.output:
                    print(result.output[:500])
            else:
                print(f"\n[Result]: Failed - {result.error}")

            return build_continuation_prompt("User approved execution", result)
        else:
            print("\n[Info]: No command to execute")
            return get_next_prompt()

    elif user_input == "m":
        # Modify the prompt
        try:
            modification = input("Enter modified prompt: ").strip()
            if modification:
                return modification
        except EOFError:
            pass
        return get_next_prompt()

    else:  # skip or anything else
        return get_next_prompt()


def display_response(response: str) -> None:
    """
    Display Claude's response (truncated if needed).

    Args:
        response: Response text to display
    """
    print("\n[Claude]:")
    print(truncate_response(response, MAX_REPLY_LENGTH))


def build_continuation_prompt(previous_response: str, result: ExecutionResult) -> str:
    """
    Build a continuation prompt based on previous response and result.

    Args:
        previous_response: Previous Claude response
        result: Execution result

    Returns:
        Continuation prompt string
    """
    if result.success:
        return (
            f"The previous command executed successfully.\n"
            f"Output: {result.output[:500] if result.output else 'No output'}\n"
            f"What should we do next?"
        )
    else:
        return (
            f"The previous command failed.\n"
            f"Error: {result.error}\n"
            f"How should we handle this?"
        )


def get_next_prompt(max_attempts: int = 10) -> str | None:
    """
    Get the next prompt from user input.

    Args:
        max_attempts: Maximum number of empty input attempts before giving up

    Returns:
        User's next prompt or None on EOF or max attempts reached
    """
    for _ in range(max_attempts):
        try:
            prompt = input("\nEnter next prompt (or 'q' to quit): ").strip()
            if prompt.lower() == "q":
                return None
            if prompt:
                return prompt
            # Empty input, loop again
        except EOFError:
            return None

    print("Too many empty inputs. Please provide a prompt.")
    return None


if __name__ == "__main__":
    main()
