"""
Permission management module.

This module handles loading and checking permissions from YAML
configuration, with support for overriding classifier decisions.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from core.classifier import Decision

logger = logging.getLogger(__name__)

CONFIG_PATH = "config/permissions.yaml"

# Module-level cache for permissions
_permissions_cache: dict[str, Any] | None = None


class PermissionManager:
    """Manages permission rules loaded from YAML configuration."""

    def __init__(self, config_path: str = CONFIG_PATH) -> None:
        """
        Initialize the permission manager.

        Args:
            config_path: Path to permissions YAML file
        """
        self.config_path = config_path
        self.permissions = load_permissions(config_path)

    def check_permission(self, action_type: str) -> str:
        """
        Check permission level for an action type.

        Args:
            action_type: Type of action (e.g., "read_file", "git_push")

        Returns:
            Permission level: "auto", "ask", or "deny"
        """
        actions = self.permissions.get("actions", {})
        return actions.get(action_type, self.permissions.get("default", "ask"))

    def enforce(self, decision: Decision) -> Decision:
        """
        Override decision based on permission rules.

        If YAML says "ask" but classifier said "auto",
        return modified Decision with action="user".

        Args:
            decision: Decision object from classifier

        Returns:
            Modified Decision based on permissions
        """
        from core.classifier import Decision as DecisionClass

        # Check for dangerous keywords first
        if self._contains_dangerous_keyword(decision.command or ""):
            return DecisionClass(
                action="user",
                reason=f"Contains dangerous keyword (original: {decision.reason})",
                command=decision.command,
                risk_level="high",
            )

        # Get permission for this type of action
        permission = self.check_permission(self._infer_action_type(decision))

        if permission == "deny":
            return DecisionClass(
                action="user",
                reason=f"Action denied by policy (original: {decision.reason})",
                command=decision.command,
                risk_level="high",
            )

        if permission == "ask" and decision.action == "auto":
            return DecisionClass(
                action="user",
                reason=f"Requires approval per policy (original: {decision.reason})",
                command=decision.command,
                risk_level=decision.risk_level,
            )

        return decision

    def validate_path(self, path: str, sandbox_root: str = "./sandbox") -> bool:
        """
        Ensure path is within sandbox and has allowed extension.

        Args:
            path: Path to validate
            sandbox_root: Root of sandbox directory

        Returns:
            True if path is valid, False otherwise
        """
        try:
            # Resolve paths to absolute
            sandbox = Path(sandbox_root).resolve()
            target = Path(path).resolve()

            # Check if target is within sandbox
            if not str(target).startswith(str(sandbox)):
                return False

            # Check extension
            allowed = self.permissions.get("sandbox", {}).get(
                "allowed_extensions", [".py", ".txt", ".json", ".yaml", ".md", ".sh"]
            )
            if target.suffix and target.suffix not in allowed:
                return False

            return True

        except (ValueError, OSError):
            return False

    def _contains_dangerous_keyword(self, command: str) -> bool:
        """Check if command contains dangerous keywords.

        Keywords that start and end with / are treated as regex patterns
        (e.g. "/rm\\s+-r/" matches rm -r, rm -rf, rm -ri). Plain strings
        are matched as literal substrings.
        """
        dangerous = self.permissions.get("dangerous_keywords", [
            "deploy", "production", "push", "sudo", "rm -rf",
            "chmod", "chown", "curl", "wget", "eval", "exec",
        ])
        command_lower = command.lower()
        for keyword in dangerous:
            kw = str(keyword)
            if kw.startswith("/") and kw.endswith("/") and len(kw) > 2:
                # Regex pattern
                try:
                    if re.search(kw[1:-1], command_lower):
                        return True
                except re.error:
                    # Fall back to literal match on bad regex
                    if kw[1:-1] in command_lower:
                        return True
            else:
                if kw.lower() in command_lower:
                    return True
        return False

    # Regex-based action type inference rules.
    # Order matters: first match wins. Each entry is (pattern, action_type).
    _ACTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
        # Git operations (most specific first)
        (re.compile(r"\bgit\s+push\b"), "git_push"),
        (re.compile(r"\bgit\s+pull\b"), "git_pull"),
        (re.compile(r"\bgit\s+commit\b"), "git_commit"),
        (re.compile(r"\bgit\s+add\b"), "git_add"),
        (re.compile(r"\bgit\s+(status|diff|log|show)\b"), "git_status"),
        # Package installation
        (re.compile(r"\b(pip|pip3)\s+install\b"), "install_package"),
        (re.compile(r"\bnpm\s+(install|i|ci)\b"), "install_package"),
        (re.compile(r"\b(apt-get|apt|yum|dnf|brew|pacman)\s+(install|update|upgrade)\b"), "install_package"),
        # Remote / container commands
        (re.compile(r"\b(ssh|scp|rsync)\b"), "remote_command"),
        (re.compile(r"\b(docker|kubectl|podman)\b"), "system_command"),
        # Deploy
        (re.compile(r"\bdeploy\b"), "deploy"),
        # Linting and formatting
        (re.compile(r"\b(ruff|flake8|pylint|eslint|black|isort|prettier)\s+(check|--check)\b"), "lint_code"),
        (re.compile(r"\b(ruff|black|isort|prettier|autopep8)\s+(format|--fix)\b"), "format_code"),
        (re.compile(r"\b(ruff|flake8|pylint|eslint|mypy)\b"), "lint_code"),
        # Testing
        (re.compile(r"\b(pytest|unittest|nose2|tox)\b"), "run_tests"),
        (re.compile(r"\btest\b"), "run_tests"),
        # File operations
        (re.compile(r"\brm\s"), "delete_file"),
        (re.compile(r"\bdelete\b"), "delete_file"),
        (re.compile(r"\b(cat|less|head|tail|more)\s"), "read_file"),
        (re.compile(r"\bread\b"), "read_file"),
        (re.compile(r"\b(echo|tee)\s.*>"), "write_file"),
        (re.compile(r"\btouch\s"), "write_file"),
        (re.compile(r"\bwrite\b"), "write_file"),
    ]

    def _infer_action_type(self, decision: Decision) -> str:
        """Infer action type from decision command using regex patterns."""
        command = (decision.command or "").lower()
        for pattern, action_type in self._ACTION_PATTERNS:
            if pattern.search(command):
                return action_type
        return "default"


PROJECT_CONFIG = ".ollama-harness.yaml"


def load_permissions(path: str = CONFIG_PATH) -> dict[str, Any]:
    """
    Load permissions from YAML configuration file.

    If a project-scoped `.ollama-harness.yaml` exists in the current
    directory, its values are merged on top of the global config
    (project overrides global).

    Args:
        path: Path to permissions YAML file

    Returns:
        Dictionary of permission settings
    """
    global _permissions_cache

    if _permissions_cache is not None:
        return _permissions_cache

    config_file = Path(path)

    if not config_file.exists():
        base = _get_default_permissions()
    else:
        try:
            with open(config_file) as f:
                base = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.error("Failed to parse permissions YAML file '%s': %s", path, e)
            logger.warning("Using default permissions due to YAML parse error")
            base = _get_default_permissions()

    # Merge project-scoped overrides if present
    project_file = Path(PROJECT_CONFIG)
    if project_file.exists():
        try:
            with open(project_file) as f:
                project = yaml.safe_load(f) or {}
            base = _merge_permissions(base, project)
            logger.info("Loaded project-scoped permissions from %s", PROJECT_CONFIG)
        except yaml.YAMLError as e:
            logger.warning("Ignoring invalid project config %s: %s", PROJECT_CONFIG, e)

    _permissions_cache = base
    return _permissions_cache


def _merge_permissions(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Shallow-merge override onto base (one level deep for dict values)."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def get_permission(action_type: str) -> str:
    """
    Get permission level for an action type.

    Args:
        action_type: Type of action (e.g., "read_file", "git_push")

    Returns:
        Permission level: "auto", "ask", or "deny"
    """
    permissions = load_permissions()
    actions = permissions.get("actions", {})
    return actions.get(action_type, permissions.get("default", "ask"))


def check_action(decision: Decision) -> str:
    """
    Check permission level for a classified action.

    Args:
        decision: Decision object from classifier

    Returns:
        Permission level: "auto", "ask", or "deny"
    """
    manager = PermissionManager()
    enforced = manager.enforce(decision)
    return "auto" if enforced.action == "auto" else "ask"


def _get_default_permissions() -> dict[str, Any]:
    """Return default permission settings."""
    return {
        "actions": {
            "read_file": "auto",
            "write_file": "ask",
            "delete_file": "ask",
            "run_tests": "auto",
            "git_commit": "ask",
            "git_push": "ask",
            "deploy": "deny",
        },
        "default": "ask",
        "dangerous_keywords": [
            "deploy",
            "production",
            "push",
            "sudo",
            r"/rm\s+-r/",
            "chmod",
            "chown",
            "curl",
            "wget",
            "eval",
            "exec",
        ],
        "sandbox": {
            "root": "./sandbox",
            "allowed_extensions": [".py", ".txt", ".json", ".yaml", ".md", ".sh"],
        },
    }
