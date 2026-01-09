#!/usr/bin/env python3
"""
Ollama Automation Harness - Main Entry Point

A CLI application that pairs Claude with Ollama for automated
development workflows with human oversight.
"""

import argparse
import sys
import time
from typing import Optional

from core.claude import get_response, ClaudeError, get_model_info
from core.classifier import classify, Decision
from core.executor import execute, ExecutionResult
from core.safety import PermissionManager
from utils.logger import (
    setup_logger,
    log_action,
    log_error,
    log_startup,
    log_shutdown,
    log_user_decision,
)

LOOP_DELAY = 1.0  # seconds
MAX_REPLY_LENGTH = 2000
SANDBOX_ROOT = "./sandbox"


def main() -> None:
    """Main entry point for the automation harness."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Ollama Automation Harness - AI-powered development automation"
    )
    parser.add_argument(
        "-p", "--prompt",
        type=str,
        help="Initial prompt (if not provided, will prompt interactively)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/permissions.yaml",
        help="Path to permissions config file",
    )
    parser.add_argument(
        "--sandbox",
        type=str,
        default=SANDBOX_ROOT,
        help="Path to sandbox directory",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    args = parser.parse_args()

    # Initialize
    setup_logger()
    log_startup()
    permissions = PermissionManager(args.config)

    # Display configuration
    model_info = get_model_info()
    print(f"Ollama Automation Harness")
    print(f"Mode: {model_info['mode']} ({model_info['model']})")
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

    except Exception as e:
        log_error(e, "main_loop")
        print(f"\nUnexpected error: {e}")
        log_shutdown("error")
        sys.exit(1)

    log_shutdown("normal")
    print("\nGoodbye!")


def process_iteration(
    prompt: str,
    permissions: PermissionManager,
    sandbox_root: str,
    verbose: bool = False,
) -> Optional[str]:
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
        # Get Claude's response
        print(f"\n[Prompt]: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        print("[Thinking...]")

        claude_reply = get_response(prompt)
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
                    print(f"\n[Result]: Success")
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
        print(f"\n[Error]: {e}")
        return get_next_prompt()

    except Exception as e:
        log_error(e, "process_iteration")
        print(f"\n[Error]: {e}")
        return get_next_prompt()


def handle_user_action(
    decision: Decision,
    permissions: PermissionManager,
    sandbox_root: str,
) -> Optional[str]:
    """
    Handle an action that requires user approval.

    Args:
        decision: Decision requiring user input
        permissions: Permission manager instance
        sandbox_root: Path to sandbox directory

    Returns:
        Next prompt, modified prompt, or None to exit
    """
    print(f"\n⚠️  User action required: {decision.reason}")
    if decision.command:
        print(f"Command: {decision.command}")

    try:
        user_input = input("\nApprove (y), modify (m), skip (s), quit (q): ").strip().lower()
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
                print(f"\n[Result]: Success")
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
    if len(response) > MAX_REPLY_LENGTH:
        print(response[:MAX_REPLY_LENGTH])
        print(f"\n... (truncated, {len(response)} total characters)")
    else:
        print(response)


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


def get_next_prompt() -> Optional[str]:
    """
    Get the next prompt from user input.

    Returns:
        User's next prompt or None on EOF
    """
    try:
        prompt = input("\nEnter next prompt (or 'q' to quit): ").strip()
        if prompt.lower() == "q":
            return None
        return prompt if prompt else get_next_prompt()
    except EOFError:
        return None


if __name__ == "__main__":
    main()
