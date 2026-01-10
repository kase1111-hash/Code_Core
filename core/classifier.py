"""
Decision classification module.

This module parses Claude responses and classifies them into
actionable decisions with risk assessment.
"""

import json
import re
from dataclasses import dataclass

from core.ollama import OllamaError, run_prompt
from utils.config import MAX_REPLY_LENGTH, is_dangerous_keyword
from utils.validation import sanitize_string, validate_risk_level

CLASSIFICATION_PROMPT = '''Analyze this AI response and classify the required action.

Response to analyze:
"""
{claude_reply}
"""

Output ONLY valid JSON (no markdown, no explanation):
{{"action": "auto" or "user", "reason": "brief explanation", "command": "extracted command or null", "risk_level": "low" or "medium" or "high"}}

Rules:
- "auto": Safe operations (run tests, generate code, read files, write to sandbox)
- "user": Dangerous operations (git push, deploy, delete, modify system files)
- Always "user" for: deploy, production, push, sudo, rm -rf, chmod
- risk_level: "low" for read-only, "medium" for sandbox writes, "high" for system changes
'''


@dataclass
class Decision:
    """Represents a classified action decision."""

    action: str  # "auto" | "user"
    reason: str  # Explanation for the decision
    command: str | None  # Command to execute
    risk_level: str  # "low" | "medium" | "high"


def classify(response: str) -> Decision:
    """
    Classify a Claude response into an action decision.

    Args:
        response: Raw response from Claude

    Returns:
        Decision object with action, reason, command, risk_level
    """
    # Sanitize the response first
    response = sanitize_string(response)

    # First, try to extract any command from the response
    extracted_command = extract_command(response)

    # Check for dangerous keywords in the response
    if is_dangerous_keyword(response):
        return Decision(
            action="user",
            reason="Contains dangerous keyword",
            command=extracted_command,
            risk_level="high",
        )

    # Try to classify using Ollama
    try:
        prompt = CLASSIFICATION_PROMPT.format(claude_reply=response[:MAX_REPLY_LENGTH])
        ollama_response = run_prompt(prompt)
        parsed = parse_json_response(ollama_response)

        if parsed:
            # Validate and extract fields
            action = parsed.get("action", "user")
            if action not in ("auto", "user"):
                action = "user"

            reason = parsed.get("reason", "Classified by Ollama")
            command = parsed.get("command") or extracted_command
            risk_level = validate_risk_level(parsed.get("risk_level", "medium"))

            # Double-check for dangerous keywords in command
            if command and is_dangerous_keyword(command):
                action = "user"
                risk_level = "high"

            return Decision(
                action=action,
                reason=reason,
                command=command,
                risk_level=risk_level,
            )

    except OllamaError:
        # Fall back to conservative classification
        pass

    # Default: require user action (safe fallback)
    return Decision(
        action="user",
        reason="Unable to classify automatically",
        command=extracted_command,
        risk_level="medium",
    )


def parse_json_response(response: str) -> dict | None:
    """
    Parse JSON from Claude/Ollama response.

    Args:
        response: Response text that may contain JSON

    Returns:
        Parsed dictionary or None if parsing fails
    """
    # Try direct parse first
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass

    # Try to find JSON in the response
    # Look for {...} pattern
    json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Try to find JSON in code blocks
    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass

    return None


def extract_command(response: str) -> str | None:
    """
    Extract command from Claude response.

    Args:
        response: Claude's response text

    Returns:
        Extracted command or None
    """
    # Look for shell code blocks
    shell_match = re.search(r'```(?:bash|sh|shell|zsh)?\s*\n(.*?)\n```', response, re.DOTALL)
    if shell_match:
        return shell_match.group(1).strip()

    # Look for inline commands with $ prefix
    cmd_match = re.search(r'\$\s*(.+?)(?:\n|$)', response)
    if cmd_match:
        return cmd_match.group(1).strip()

    # Look for "run:" or "execute:" patterns
    run_match = re.search(r'(?:run|execute|command):\s*[`"]?(.+?)[`"]?(?:\n|$)', response, re.IGNORECASE)
    if run_match:
        return run_match.group(1).strip()

    return None
