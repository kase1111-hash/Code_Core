"""
Permission management module.

This module handles loading and checking permissions from YAML
configuration, with support for overriding classifier decisions.
"""

from __future__ import annotations

import logging
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
        """Check if command contains dangerous keywords."""
        dangerous = self.permissions.get("dangerous_keywords", [
            "deploy", "production", "push", "sudo", "rm -rf",
            "chmod", "chown", "curl", "wget", "eval", "exec",
        ])
        command_lower = command.lower()
        return any(keyword.lower() in command_lower for keyword in dangerous)

    def _infer_action_type(self, decision: Decision) -> str:
        """Infer action type from decision command."""
        command = (decision.command or "").lower()

        if "git push" in command:
            return "git_push"
        elif "git commit" in command:
            return "git_commit"
        elif "git pull" in command:
            return "git_pull"
        elif "deploy" in command:
            return "deploy"
        elif "rm " in command or "delete" in command:
            return "delete_file"
        elif any(cmd in command for cmd in ["cat ", "read", "less ", "head ", "tail "]):
            return "read_file"
        elif any(cmd in command for cmd in ["write", "echo ", ">", "touch "]):
            return "write_file"
        elif "test" in command or "pytest" in command:
            return "run_tests"

        return "default"


def load_permissions(path: str = CONFIG_PATH) -> dict[str, Any]:
    """
    Load permissions from YAML configuration file.

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
        # Return default permissions if file doesn't exist
        _permissions_cache = _get_default_permissions()
        return _permissions_cache

    try:
        with open(config_file) as f:
            _permissions_cache = yaml.safe_load(f) or {}
            return _permissions_cache
    except yaml.YAMLError as e:
        # Log the error and return defaults on parse error
        logger.error("Failed to parse permissions YAML file '%s': %s", path, e)
        logger.warning("Using default permissions due to YAML parse error")
        _permissions_cache = _get_default_permissions()
        return _permissions_cache


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
            "rm -rf",
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
