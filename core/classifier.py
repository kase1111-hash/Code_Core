"""
Decision classification module.

This module parses Claude responses and classifies them into
actionable decisions with risk assessment.
"""

import json
import logging
import re
from dataclasses import dataclass

from core.ollama import OllamaError, run_prompt
from utils.config import MAX_REPLY_LENGTH, is_dangerous_keyword
from utils.validation import sanitize_string, validate_risk_level

logger = logging.getLogger(__name__)

# noqa: E501 - Classification prompt template
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
- Always "user" for: deploy, production, push, sudo, rm -rf, chmod, chown, curl, wget, eval, exec
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
        sanitized = _sanitize_for_classification(response[:MAX_REPLY_LENGTH])
        prompt = CLASSIFICATION_PROMPT.format(claude_reply=sanitized)
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

            # Double-check for dangerous keywords in command and response
            if command and is_dangerous_keyword(command):
                action = "user"
                risk_level = "high"
            if is_dangerous_keyword(response):
                action = "user"
                risk_level = "high"

            return Decision(
                action=action,
                reason=reason,
                command=command,
                risk_level=risk_level,
            )

    except OllamaError as e:
        # Fall back to conservative classification
        logger.warning("Ollama classification failed: %s. Falling back to conservative mode.", e)

    # Default: require user action (safe fallback)
    logger.debug("Using conservative fallback classification for response")
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
    except json.JSONDecodeError as e:
        logger.debug("Direct JSON parse failed: %s", e)

    # Try to find JSON in the response
    # Look for {...} pattern
    json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.debug("JSON extraction from pattern failed: %s", e)

    # Try to find JSON in code blocks
    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError as e:
            logger.debug("JSON extraction from code block failed: %s", e)

    logger.warning("Failed to parse JSON from response (length=%d)", len(response))
    return None


def _sanitize_for_classification(text: str) -> str:
    """
    Sanitize text before embedding in the classification prompt.

    Prevents prompt injection by:
    - Escaping triple-quote delimiters that could break out of the prompt
    - Removing lines with common prompt injection phrases
    - Stripping embedded JSON that could fake classification output

    Args:
        text: Raw LLM response text

    Returns:
        Sanitized text safe for embedding in classification prompt
    """
    # Escape triple-quote sequences to prevent breaking out of delimiters
    text = text.replace('"""', r'\"\"\"')

    # Remove lines that look like prompt injection attempts
    injection_patterns = [
        r'(?i)^\s*ignore\s+(all\s+)?previous',
        r'(?i)^\s*you\s+are\s+now\b',
        r'(?i)^\s*system\s*:',
        r'(?i)^\s*output\s+only\b',
        r'(?i)^\s*new\s+instructions?\s*:',
        r'(?i)^\s*disregard\s+(all\s+)?above',
    ]
    lines = text.split('\n')
    filtered_lines = []
    for line in lines:
        if not any(re.search(p, line) for p in injection_patterns):
            filtered_lines.append(line)
    text = '\n'.join(filtered_lines)

    # Strip standalone JSON objects that could fake classification output
    # (only strip top-level JSON blocks that look like classification results)
    text = re.sub(
        r'\{\s*"action"\s*:', '{ "action":', text
    )

    return text


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
