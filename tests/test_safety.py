"""
Unit tests for core/safety.py
"""

from unittest.mock import MagicMock, patch

from core.safety import (
    PermissionManager,
    _get_default_permissions,
    get_permission,
    load_permissions,
)


# Mock Decision class for testing
class MockDecision:
    """Mock Decision class for testing."""
    def __init__(self, action="auto", reason="test", command=None, risk_level="low"):
        self.action = action
        self.reason = reason
        self.command = command
        self.risk_level = risk_level


class TestPermissionManager:
    """Tests for PermissionManager class."""

    def test_init_with_default_permissions(self, tmp_path):
        """Test initialization without config file uses defaults."""
        config_path = tmp_path / "nonexistent.yaml"
        manager = PermissionManager(str(config_path))
        assert manager.permissions is not None
        assert "actions" in manager.permissions

    def test_check_permission_default(self, tmp_path):
        """Test check_permission returns default when action not found."""
        config_path = tmp_path / "nonexistent.yaml"
        manager = PermissionManager(str(config_path))
        permission = manager.check_permission("unknown_action")
        assert permission == "ask"

    def test_check_permission_read_file(self, tmp_path):
        """Test check_permission for read_file action."""
        config_path = tmp_path / "nonexistent.yaml"
        manager = PermissionManager(str(config_path))
        permission = manager.check_permission("read_file")
        assert permission == "auto"

    def test_check_permission_git_push(self, tmp_path):
        """Test check_permission for git_push action."""
        config_path = tmp_path / "nonexistent.yaml"
        manager = PermissionManager(str(config_path))
        permission = manager.check_permission("git_push")
        assert permission == "ask"

    def test_check_permission_deploy(self, tmp_path):
        """Test check_permission for deploy action."""
        config_path = tmp_path / "nonexistent.yaml"
        manager = PermissionManager(str(config_path))
        permission = manager.check_permission("deploy")
        assert permission == "deny"


class TestPermissionManagerEnforce:
    """Tests for PermissionManager.enforce method."""

    @patch("core.safety.PermissionManager._contains_dangerous_keyword")
    def test_enforce_dangerous_keyword(self, mock_dangerous, tmp_path):
        """Test enforce detects dangerous keywords."""
        mock_dangerous.return_value = True

        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))

        with patch("core.classifier.Decision") as mock_decision_class:
            mock_decision_class.return_value = MagicMock(action="user")
            decision = MockDecision(action="auto", command="rm -rf /")
            result = manager.enforce(decision)
            # Should return a decision requiring user approval
            assert result.action == "user"

    def test_contains_dangerous_keyword_deploy(self, tmp_path):
        """Test dangerous keyword detection - deploy."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        assert manager._contains_dangerous_keyword("deploy to production") is True

    def test_contains_dangerous_keyword_sudo(self, tmp_path):
        """Test dangerous keyword detection - sudo."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        assert manager._contains_dangerous_keyword("sudo rm file") is True

    def test_contains_dangerous_keyword_rm_rf(self, tmp_path):
        """Test dangerous keyword detection - rm -rf."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        assert manager._contains_dangerous_keyword("rm -rf folder") is True

    def test_no_dangerous_keyword(self, tmp_path):
        """Test safe command detection."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        assert manager._contains_dangerous_keyword("echo hello") is False


class TestPermissionManagerValidatePath:
    """Tests for PermissionManager.validate_path method."""

    def test_validate_path_within_sandbox(self, tmp_path):
        """Test path validation within sandbox."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        target = sandbox / "test.py"
        target.touch()

        result = manager.validate_path(str(target), str(sandbox))
        assert result is True

    def test_validate_path_outside_sandbox(self, tmp_path):
        """Test path validation outside sandbox."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        result = manager.validate_path("/etc/passwd", str(sandbox))
        assert result is False

    def test_validate_path_disallowed_extension(self, tmp_path):
        """Test path validation with disallowed extension."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        target = sandbox / "script.exe"
        target.touch()

        result = manager.validate_path(str(target), str(sandbox))
        assert result is False

    def test_validate_path_allowed_extension(self, tmp_path):
        """Test path validation with allowed extension."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        target = sandbox / "script.py"
        target.touch()

        result = manager.validate_path(str(target), str(sandbox))
        assert result is True


class TestPermissionManagerInferActionType:
    """Tests for PermissionManager._infer_action_type method."""

    def test_infer_git_push(self, tmp_path):
        """Test inferring git push action type."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        decision = MockDecision(command="git push origin main")
        assert manager._infer_action_type(decision) == "git_push"

    def test_infer_git_commit(self, tmp_path):
        """Test inferring git commit action type."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        decision = MockDecision(command="git commit -m 'test'")
        assert manager._infer_action_type(decision) == "git_commit"

    def test_infer_delete_file(self, tmp_path):
        """Test inferring delete file action type."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        decision = MockDecision(command="rm file.txt")
        assert manager._infer_action_type(decision) == "delete_file"

    def test_infer_read_file(self, tmp_path):
        """Test inferring read file action type."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        decision = MockDecision(command="cat file.txt")
        assert manager._infer_action_type(decision) == "read_file"

    def test_infer_run_tests(self, tmp_path):
        """Test inferring run tests action type."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        decision = MockDecision(command="pytest tests/")
        assert manager._infer_action_type(decision) == "run_tests"

    def test_infer_default(self, tmp_path):
        """Test inferring default action type."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        decision = MockDecision(command="some random command")
        assert manager._infer_action_type(decision) == "default"

    def test_infer_install_package(self, tmp_path):
        """Test inferring install_package action type."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        decision = MockDecision(command="pip install requests")
        assert manager._infer_action_type(decision) == "install_package"

    def test_infer_system_command(self, tmp_path):
        """Test inferring system_command for docker."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        decision = MockDecision(command="docker run nginx")
        assert manager._infer_action_type(decision) == "system_command"

    def test_infer_remote_command(self, tmp_path):
        """Test inferring remote_command for ssh."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        decision = MockDecision(command="ssh user@host")
        assert manager._infer_action_type(decision) == "remote_command"

    def test_infer_lint_code(self, tmp_path):
        """Test inferring lint_code for linters."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        decision = MockDecision(command="ruff check .")
        assert manager._infer_action_type(decision) == "lint_code"

    def test_infer_format_code(self, tmp_path):
        """Test inferring format_code for formatters."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        decision = MockDecision(command="ruff format .")
        assert manager._infer_action_type(decision) == "format_code"

    def test_infer_git_add(self, tmp_path):
        """Test inferring git_add action type."""
        manager = PermissionManager(str(tmp_path / "nonexistent.yaml"))
        decision = MockDecision(command="git add file.py")
        assert manager._infer_action_type(decision) == "git_add"


class TestLoadPermissions:
    """Tests for load_permissions function."""

    def test_load_permissions_file_not_found(self, tmp_path):
        """Test loading permissions when file doesn't exist."""
        permissions = load_permissions(str(tmp_path / "nonexistent.yaml"))
        assert permissions is not None
        assert "actions" in permissions

    def test_load_permissions_from_valid_yaml(self, tmp_path):
        """Test loading permissions from valid YAML file."""
        config_file = tmp_path / "permissions.yaml"
        config_file.write_text("""
actions:
  read_file: auto
  write_file: deny
default: ask
""")
        # Clear cache
        import core.safety
        core.safety._permissions_cache = None

        permissions = load_permissions(str(config_file))
        assert permissions["actions"]["read_file"] == "auto"
        assert permissions["actions"]["write_file"] == "deny"
        assert permissions["default"] == "ask"

    def test_load_permissions_invalid_yaml(self, tmp_path):
        """Test loading permissions from invalid YAML returns defaults."""
        config_file = tmp_path / "permissions.yaml"
        config_file.write_text("invalid: yaml: content: [")

        # Clear cache
        import core.safety
        core.safety._permissions_cache = None

        permissions = load_permissions(str(config_file))
        # Should return defaults on parse error
        assert "actions" in permissions


class TestGetPermission:
    """Tests for get_permission function."""

    def test_get_permission_existing_action(self):
        """Test getting permission for existing action."""
        # Clear cache first
        import core.safety
        core.safety._permissions_cache = None

        permission = get_permission("read_file")
        assert permission == "auto"

    def test_get_permission_nonexistent_action(self):
        """Test getting permission for nonexistent action."""
        # Clear cache first
        import core.safety
        core.safety._permissions_cache = None

        permission = get_permission("unknown_action")
        assert permission == "ask"


class TestGetDefaultPermissions:
    """Tests for _get_default_permissions function."""

    def test_default_permissions_structure(self):
        """Test default permissions have correct structure."""
        defaults = _get_default_permissions()
        assert "actions" in defaults
        assert "default" in defaults
        assert "dangerous_keywords" in defaults
        assert "sandbox" in defaults

    def test_default_permissions_actions(self):
        """Test default permissions have expected actions."""
        defaults = _get_default_permissions()
        assert defaults["actions"]["read_file"] == "auto"
        assert defaults["actions"]["deploy"] == "deny"
        assert defaults["actions"]["git_push"] == "ask"

    def test_default_permissions_dangerous_keywords(self):
        """Test default dangerous keywords."""
        defaults = _get_default_permissions()
        keywords = defaults["dangerous_keywords"]
        assert "deploy" in keywords
        assert "sudo" in keywords
        assert "rm -rf" in keywords

    def test_default_permissions_sandbox(self):
        """Test default sandbox settings."""
        defaults = _get_default_permissions()
        sandbox = defaults["sandbox"]
        assert "root" in sandbox
        assert "allowed_extensions" in sandbox
        assert ".py" in sandbox["allowed_extensions"]
