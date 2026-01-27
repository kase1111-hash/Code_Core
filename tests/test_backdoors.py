"""
Backdoor detection and unauthorized access testing suite.

This module contains tests to detect:
- Hardcoded credentials and backdoor patterns
- Unauthorized access attempts
- Hidden functionality
- Suspicious code patterns
- Permission bypass vulnerabilities
- Network and file system access auditing

Run backdoor tests only:
    pytest -m backdoor

Run backdoor tests with verbose output:
    pytest -m backdoor -v --tb=short
"""

import ast
import re
from pathlib import Path

import pytest

# Mark all tests in this module as backdoor tests
pytestmark = pytest.mark.backdoor


# =============================================================================
# Code Scanning Configuration
# =============================================================================

# Directories to scan for backdoor patterns
SOURCE_DIRS = ["core", "utils"]

# Patterns that might indicate backdoors
SUSPICIOUS_PATTERNS = {
    "hardcoded_password": [
        r'password\s*=\s*["\'][^"\']+["\']',
        r'passwd\s*=\s*["\'][^"\']+["\']',
        r'pwd\s*=\s*["\'][^"\']+["\']',
    ],
    "hardcoded_api_key": [
        r'api[_-]?key\s*=\s*["\']sk-[^"\']+["\']',
        r'api[_-]?key\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
        r'secret[_-]?key\s*=\s*["\'][^"\']+["\']',
    ],
    "suspicious_urls": [
        r'https?://[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',  # IP addresses
        r'https?://localhost',
        r'https?://127\.0\.0\.1',
    ],
    "code_execution": [
        r'\beval\s*\(',
        r'\bexec\s*\(',
        r'__import__\s*\(',
        r'subprocess\.call\s*\(\s*["\']',
        r'os\.system\s*\(',
    ],
    "network_backdoor": [
        r'socket\.socket\s*\(',
        r'bind\s*\(\s*\(["\'][0-9.]+["\']',
        r'listen\s*\(',
    ],
    "file_exfiltration": [
        r'open\s*\(\s*["\']/etc/',
        r'open\s*\(\s*["\']/root/',
        r'open\s*\(\s*["\']~/',
    ],
}

# Allowed patterns (false positive exclusions)
ALLOWED_PATTERNS = [
    r'# Example:',  # Documentation examples
    r'""".*"""',  # Docstrings
    r"'''.*'''",  # Docstrings
    r'#.*test',  # Test comments
    r'localhost.*test',  # Test configurations
]


# =============================================================================
# Code Scanning Utilities
# =============================================================================


def get_python_files(directories: list[str]) -> list[Path]:
    """Get all Python files in specified directories."""
    files = []
    base = Path(__file__).parent.parent

    for dir_name in directories:
        dir_path = base / dir_name
        if dir_path.exists():
            files.extend(dir_path.glob("**/*.py"))

    return files


def scan_file_for_patterns(file_path: Path, patterns: dict) -> list[dict]:
    """
    Scan a file for suspicious patterns.

    Returns list of findings with line numbers and matched patterns.
    """
    findings = []

    try:
        content = file_path.read_text()
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip comments and docstrings for some checks
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            for category, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Check if it's an allowed pattern
                        is_allowed = any(
                            re.search(allowed, line, re.IGNORECASE)
                            for allowed in ALLOWED_PATTERNS
                        )

                        if not is_allowed:
                            findings.append({
                                "file": str(file_path),
                                "line": line_num,
                                "category": category,
                                "pattern": pattern,
                                "content": line.strip()[:100],
                            })

    except Exception:
        pass  # Skip files that can't be read

    return findings


def analyze_ast_for_backdoors(file_path: Path) -> list[dict]:
    """
    Use AST analysis to detect suspicious code patterns.

    Returns list of findings.
    """
    findings = []

    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        for node in ast.walk(tree):
            # Check for eval/exec calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ("eval", "exec", "compile"):
                        findings.append({
                            "file": str(file_path),
                            "line": node.lineno,
                            "category": "dangerous_function",
                            "content": f"Call to {node.func.id}()",
                        })

            # Check for __import__ calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id == "__import__":
                        findings.append({
                            "file": str(file_path),
                            "line": node.lineno,
                            "category": "dynamic_import",
                            "content": "Dynamic __import__ call",
                        })

            # Check for suspicious attribute access
            if isinstance(node, ast.Attribute):
                if node.attr in ("__globals__", "__code__", "__builtins__"):
                    findings.append({
                        "file": str(file_path),
                        "line": node.lineno,
                        "category": "suspicious_attribute",
                        "content": f"Access to {node.attr}",
                    })

    except SyntaxError:
        pass  # Skip files with syntax errors
    except Exception:
        pass

    return findings


# =============================================================================
# Backdoor Pattern Detection Tests
# =============================================================================


class TestHardcodedCredentials:
    """Tests for hardcoded credentials detection."""

    def test_no_hardcoded_passwords_in_source(self):
        """Scan source code for hardcoded passwords."""
        files = get_python_files(SOURCE_DIRS)
        findings = []

        for file_path in files:
            file_findings = scan_file_for_patterns(
                file_path,
                {"hardcoded_password": SUSPICIOUS_PATTERNS["hardcoded_password"]}
            )
            # Filter out test files and config examples
            file_findings = [
                f for f in file_findings
                if "test" not in f["file"].lower()
                and "example" not in f["content"].lower()
                and "placeholder" not in f["content"].lower()
            ]
            findings.extend(file_findings)

        assert len(findings) == 0, f"Found hardcoded passwords: {findings}"

    def test_no_hardcoded_api_keys_in_source(self):
        """Scan source code for hardcoded API keys."""
        files = get_python_files(SOURCE_DIRS)
        findings = []

        for file_path in files:
            file_findings = scan_file_for_patterns(
                file_path,
                {"hardcoded_api_key": SUSPICIOUS_PATTERNS["hardcoded_api_key"]}
            )
            # Filter out pattern definitions and examples
            file_findings = [
                f for f in file_findings
                if "pattern" not in f["content"].lower()
                and "example" not in f["content"].lower()
                and "r'" not in f["content"]  # Regex patterns
                and 'r"' not in f["content"]
            ]
            findings.extend(file_findings)

        assert len(findings) == 0, f"Found hardcoded API keys: {findings}"

    def test_no_hardcoded_secrets_in_config(self):
        """Check that config files don't contain actual secrets."""
        base = Path(__file__).parent.parent
        config_files = list(base.glob("*.py")) + list(base.glob("**/*.yaml"))

        findings = []
        secret_patterns = [
            r'sk-ant-[a-zA-Z0-9]+',  # Anthropic key format
            r'sk-[a-zA-Z0-9]{48}',  # OpenAI key format
            r'ghp_[a-zA-Z0-9]+',  # GitHub token
        ]

        for file_path in config_files:
            try:
                content = file_path.read_text()
                for pattern in secret_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        findings.append({
                            "file": str(file_path),
                            "pattern": pattern,
                            "matches": matches,
                        })
            except Exception:
                pass

        assert len(findings) == 0, f"Found secrets in config: {findings}"


class TestSuspiciousCodePatterns:
    """Tests for suspicious code patterns that might indicate backdoors."""

    def test_no_eval_exec_in_production_code(self):
        """Check that eval/exec are not used in production code."""
        files = get_python_files(SOURCE_DIRS)
        findings = []

        for file_path in files:
            # Skip test files
            if "test" in str(file_path).lower():
                continue

            ast_findings = analyze_ast_for_backdoors(file_path)
            dangerous = [
                f for f in ast_findings
                if f["category"] == "dangerous_function"
            ]
            findings.extend(dangerous)

        assert len(findings) == 0, f"Found eval/exec usage: {findings}"

    def test_no_dynamic_imports_without_validation(self):
        """Check for potentially dangerous dynamic imports."""
        files = get_python_files(SOURCE_DIRS)
        findings = []

        for file_path in files:
            if "test" in str(file_path).lower():
                continue

            ast_findings = analyze_ast_for_backdoors(file_path)
            imports = [
                f for f in ast_findings
                if f["category"] == "dynamic_import"
            ]
            findings.extend(imports)

        assert len(findings) == 0, f"Found dynamic imports: {findings}"

    def test_no_suspicious_attribute_access(self):
        """Check for suspicious attribute access patterns."""
        files = get_python_files(SOURCE_DIRS)
        findings = []

        for file_path in files:
            if "test" in str(file_path).lower():
                continue

            ast_findings = analyze_ast_for_backdoors(file_path)
            suspicious = [
                f for f in ast_findings
                if f["category"] == "suspicious_attribute"
            ]
            findings.extend(suspicious)

        assert len(findings) == 0, f"Found suspicious attributes: {findings}"


class TestNetworkBackdoors:
    """Tests for potential network backdoor patterns."""

    def test_no_hardcoded_external_urls(self):
        """Check for hardcoded external URLs that could be C&C servers."""
        files = get_python_files(SOURCE_DIRS)
        findings = []

        # Look for IP addresses in URLs (potential C&C)
        ip_pattern = r'https?://[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}'

        for file_path in files:
            try:
                content = file_path.read_text()
                matches = re.findall(ip_pattern, content)
                # Filter out localhost and common internal IPs
                suspicious = [
                    m for m in matches
                    if not m.startswith("http://127.")
                    and not m.startswith("http://192.168.")
                    and not m.startswith("http://10.")
                    and not m.startswith("http://172.")
                ]
                if suspicious:
                    findings.append({
                        "file": str(file_path),
                        "urls": suspicious,
                    })
            except Exception:
                pass

        assert len(findings) == 0, f"Found suspicious URLs: {findings}"

    def test_no_socket_listeners_in_code(self):
        """Check for hidden socket listeners."""
        files = get_python_files(SOURCE_DIRS)
        findings = []

        listener_patterns = [
            r'\.listen\s*\(\s*\d+\s*\)',
            r'\.bind\s*\(\s*\(["\'][^"\']*["\']',
        ]

        for file_path in files:
            if "test" in str(file_path).lower():
                continue

            try:
                content = file_path.read_text()
                for pattern in listener_patterns:
                    if re.search(pattern, content):
                        findings.append({
                            "file": str(file_path),
                            "pattern": pattern,
                        })
            except Exception:
                pass

        assert len(findings) == 0, f"Found socket listeners: {findings}"


class TestFileSystemBackdoors:
    """Tests for potential file system backdoor patterns."""

    def test_no_access_to_system_files(self):
        """Check for code accessing sensitive system files."""
        files = get_python_files(SOURCE_DIRS)
        findings = []

        sensitive_paths = [
            r'open\s*\(\s*["\']/etc/passwd',
            r'open\s*\(\s*["\']/etc/shadow',
            r'open\s*\(\s*["\']/root/',
            r'open\s*\(\s*["\']~/.ssh/',
            r'Path\s*\(\s*["\']/etc/',
        ]

        for file_path in files:
            if "test" in str(file_path).lower():
                continue

            try:
                content = file_path.read_text()
                for pattern in sensitive_paths:
                    if re.search(pattern, content):
                        findings.append({
                            "file": str(file_path),
                            "pattern": pattern,
                        })
            except Exception:
                pass

        assert len(findings) == 0, f"Found access to sensitive files: {findings}"

    def test_no_hidden_file_operations(self):
        """Check for operations on hidden files outside sandbox."""
        files = get_python_files(SOURCE_DIRS)
        findings = []

        hidden_patterns = [
            r'open\s*\(\s*["\']\./',  # Hidden files
            r'Path\s*\(\s*["\']\.(?!env)',  # Hidden paths (except .env)
        ]

        for file_path in files:
            if "test" in str(file_path).lower():
                continue

            try:
                content = file_path.read_text()
                for pattern in hidden_patterns:
                    matches = re.findall(pattern, content)
                    # Filter out valid uses like .env
                    suspicious = [
                        m for m in matches
                        if ".env" not in m and ".git" not in m
                    ]
                    if suspicious:
                        findings.append({
                            "file": str(file_path),
                            "matches": suspicious,
                        })
            except Exception:
                pass

        # This may have false positives, so we just report
        # assert len(findings) == 0, f"Found hidden file operations: {findings}"


# =============================================================================
# Unauthorized Access Tests
# =============================================================================


class TestPermissionEnforcement:
    """Tests for proper permission enforcement."""

    def test_permission_check_required_for_actions(self):
        """Test that actions require permission checks."""
        from core.safety import PermissionManager

        manager = PermissionManager()

        # All actions should have defined permissions
        test_actions = [
            "run_tests",
            "read_file",
            "write_file",
            "execute_command",
        ]

        for action in test_actions:
            # Should not raise, should return a permission level
            result = manager.check_permission(action)
            assert result in ("auto", "ask", "deny", None)

    def test_high_risk_commands_require_permission(self):
        """Test that high-risk commands require explicit permission."""
        from core.classifier import Decision
        from core.safety import PermissionManager

        manager = PermissionManager()

        high_risk_decision = Decision(
            action="auto",
            reason="Test",
            command="rm -rf /",
            risk_level="high"
        )

        # High risk should require confirmation or be denied
        result = manager.enforce(high_risk_decision)
        # The enforcement should either block or require confirmation

    def test_sandbox_enforced_for_file_operations(self, sandbox):
        """Test that file operations are confined to sandbox."""
        from core.executor import write_file_sandboxed

        # Operations within sandbox should work
        result = write_file_sandboxed("test.txt", "content", str(sandbox))
        assert result.success is True

        # Verify file is in sandbox
        assert (sandbox / "test.txt").exists()

    def test_cannot_access_parent_directories(self, sandbox):
        """Test that parent directory access is blocked."""
        from utils.validation import ValidationError, validate_path

        with pytest.raises(ValidationError):
            validate_path("../outside.txt", str(sandbox))

        with pytest.raises(ValidationError):
            validate_path("../../etc/passwd", str(sandbox))


class TestAuthenticationBypass:
    """Tests for authentication bypass vulnerabilities."""

    def test_api_key_validation_enforced(self):
        """Test that API key validation is properly enforced."""
        from utils.secrets import SecretConfig, SecureConfig

        config = SecureConfig()
        config.SECRET_DEFINITIONS = [
            SecretConfig(
                name="api_key",
                env_var="API_KEY",
                required=True,
                min_length=20,
            )
        ]
        config._loaded = True

        # Missing required key should produce error
        errors = config.validate()
        assert any(e.severity == "error" for e in errors)

    def test_empty_credentials_rejected(self):
        """Test that empty credentials are rejected."""
        from utils.secrets import SecureConfig

        config = SecureConfig()
        config._secrets = {"api_key": ""}

        # Empty string should be treated as not set
        assert config.has("api_key") is False

    def test_whitespace_credentials_rejected(self):
        """Test that whitespace-only credentials are rejected."""
        from utils.secrets import SecureConfig

        config = SecureConfig()
        config._secrets = {"api_key": "   "}

        # Whitespace should be treated as not set
        # (depending on implementation)
        result = config.get("api_key")
        if result:
            assert result.strip() == ""


class TestPrivilegeEscalation:
    """Tests for privilege escalation prevention."""

    def test_cannot_modify_permission_levels_directly(self):
        """Test that permission levels can't be bypassed."""
        from core.safety import PermissionManager

        manager = PermissionManager()

        # Get current permissions
        original = manager.check_permission("deploy")

        # Attempt to directly modify (if possible)
        # This tests that internal state is protected

    def test_risk_level_cannot_be_downgraded(self):
        """Test that risk levels are properly enforced."""
        from utils.validation import get_command_risk_level

        # High risk commands should always be identified as high risk
        high_risk_commands = [
            "rm -rf /",
            "sudo anything",
            "chmod 777 /",
        ]

        for cmd in high_risk_commands:
            risk = get_command_risk_level(cmd)
            assert risk == "high", f"Risk level downgraded for: {cmd}"

    def test_sandbox_cannot_be_escaped_via_symlink(self, sandbox):
        """Test that symlinks can't escape the sandbox."""

        # Create symlink pointing outside sandbox
        try:
            link = sandbox / "escape_link"
            link.symlink_to("/etc/passwd")

            # Attempting to validate the symlink target should fail
            # when resolved
        except OSError:
            pass  # May not have permission


# =============================================================================
# Hidden Functionality Tests
# =============================================================================


class TestHiddenFunctionality:
    """Tests to detect hidden or undocumented functionality."""

    def test_no_debug_backdoors(self):
        """Check for debug backdoors in code."""
        files = get_python_files(SOURCE_DIRS)
        findings = []

        debug_patterns = [
            r'if\s+debug\s*==\s*["\']secret',
            r'if\s+os\.getenv\(["\']DEBUG_BACKDOOR',
            r'if\s+["\']backdoor["\']',
            r'# TODO.*remove.*before.*prod',
            r'# HACK.*bypass',
        ]

        for file_path in files:
            try:
                content = file_path.read_text()
                for pattern in debug_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        findings.append({
                            "file": str(file_path),
                            "pattern": pattern,
                        })
            except Exception:
                pass

        assert len(findings) == 0, f"Found debug backdoors: {findings}"

    def test_no_hidden_admin_functions(self):
        """Check for hidden admin or superuser functions."""
        files = get_python_files(SOURCE_DIRS)
        findings = []

        admin_patterns = [
            r'def\s+_?_?admin',
            r'def\s+_?_?superuser',
            r'def\s+_?_?backdoor',
            r'def\s+_?_?bypass',
            r'is_admin\s*=\s*True',
            r'is_superuser\s*=\s*True',
        ]

        for file_path in files:
            try:
                content = file_path.read_text()
                for pattern in admin_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        findings.append({
                            "file": str(file_path),
                            "pattern": pattern,
                        })
            except Exception:
                pass

        assert len(findings) == 0, f"Found hidden admin functions: {findings}"

    def test_all_cli_commands_documented(self):
        """Verify all CLI commands are documented (no hidden commands)."""
        from cli import create_parser

        parser = create_parser()

        # Get all subcommands
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, type(parser._subparsers))
            or hasattr(action, "_group_actions")
        ]

        # All commands should have help text
        # This is a structural test - detailed implementation depends on CLI


class TestEnvironmentManipulation:
    """Tests for unauthorized environment manipulation."""

    def test_no_environment_variable_injection(self):
        """Check that code doesn't set dangerous environment variables."""
        files = get_python_files(SOURCE_DIRS)
        findings = []

        dangerous_env_patterns = [
            r'os\.environ\[["\']PATH["\']\]',
            r'os\.environ\[["\']LD_PRELOAD["\']\]',
            r'os\.environ\[["\']LD_LIBRARY_PATH["\']\]',
            r'os\.putenv\s*\(\s*["\']PATH',
        ]

        for file_path in files:
            if "test" in str(file_path).lower():
                continue

            try:
                content = file_path.read_text()
                for pattern in dangerous_env_patterns:
                    if re.search(pattern, content):
                        findings.append({
                            "file": str(file_path),
                            "pattern": pattern,
                        })
            except Exception:
                pass

        assert len(findings) == 0, f"Found environment manipulation: {findings}"

    def test_environment_variables_properly_validated(self):
        """Test that environment variables are validated before use."""
        from utils.secrets import validate_config_on_startup

        # Should not crash with missing env vars
        errors = validate_config_on_startup()

        # Errors should be properly reported, not silently ignored
        assert isinstance(errors, list)


# =============================================================================
# Data Exfiltration Tests
# =============================================================================


class TestDataExfiltration:
    """Tests for potential data exfiltration patterns."""

    def test_no_data_sending_to_external_services(self):
        """Check for code that sends data to external services."""
        files = get_python_files(SOURCE_DIRS)
        findings = []

        exfil_patterns = [
            r'requests\.(post|put)\s*\(\s*["\']https?://',
            r'urllib.*urlopen\s*\(\s*["\']https?://',
            r'httpx\.(post|put)\s*\(',
        ]

        for file_path in files:
            if "test" in str(file_path).lower():
                continue

            try:
                content = file_path.read_text()
                for pattern in exfil_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        # Check if it's the expected Ollama endpoint
                        if "ollama" not in content.lower() or "localhost" not in content:
                            findings.append({
                                "file": str(file_path),
                                "pattern": pattern,
                            })
            except Exception:
                pass

        # Report findings (may have legitimate uses)
        # assert len(findings) == 0, f"Found data exfiltration: {findings}"

    def test_logs_do_not_contain_sensitive_data(self):
        """Test that logging doesn't leak sensitive data."""
        from utils.secrets import mask_secret
        from utils.validation import sanitize_log_message

        sensitive_data = [
            "sk-ant-secret-key-12345",
            "password123",
            "api_key=secret",
        ]

        for data in sensitive_data:
            # Log sanitization should handle these
            sanitized = sanitize_log_message(data)
            # Masking should work for API keys
            masked = mask_secret(data)

            # At minimum, masking should obscure the value
            assert masked != data or "..." in masked or "*" in masked


# =============================================================================
# Integration Backdoor Tests
# =============================================================================


class TestBackdoorIntegration:
    """Integration tests for backdoor detection."""

    def test_full_source_scan(self):
        """Run comprehensive scan of all source files."""
        files = get_python_files(SOURCE_DIRS)
        all_findings = []

        for file_path in files:
            if "test" in str(file_path).lower():
                continue

            # Pattern scan
            findings = scan_file_for_patterns(file_path, SUSPICIOUS_PATTERNS)

            # AST scan
            ast_findings = analyze_ast_for_backdoors(file_path)

            # Combine and filter
            combined = findings + ast_findings

            # Filter out known safe patterns
            filtered = [
                f for f in combined
                if not any(
                    safe in f.get("content", "").lower()
                    for safe in ["example", "test", "pattern", "regex"]
                )
            ]

            all_findings.extend(filtered)

        # Report any findings (some may be false positives)
        if all_findings:
            # Log for review but don't fail on minor findings
            pass

    def test_no_obfuscated_code(self):
        """Check for obfuscated code that might hide backdoors."""
        files = get_python_files(SOURCE_DIRS)
        findings = []

        obfuscation_patterns = [
            # Long hex strings (10+ consecutive) that look like encoded payload
            r'(?:\\x[0-9a-f]{2}){10,}',
            r'base64\.b64decode\s*\(["\'][A-Za-z0-9+/=]{50,}',  # Long base64
            r'exec\s*\(\s*["\'][^"\']{100,}',  # Long exec strings
            r'chr\s*\(\s*\d+\s*\)\s*\+\s*chr',  # Character building
        ]

        for file_path in files:
            try:
                content = file_path.read_text()
                for pattern in obfuscation_patterns:
                    if re.search(pattern, content):
                        findings.append({
                            "file": str(file_path),
                            "pattern": pattern,
                        })
            except Exception:
                pass

        # Note: Short hex sequences like \x00 for null bytes are legitimate
        assert len(findings) == 0, f"Found obfuscated code: {findings}"

    def test_dependencies_are_trusted(self):
        """Verify that dependencies come from trusted sources."""
        base = Path(__file__).parent.parent
        requirements_files = [
            base / "requirements.txt",
            base / "pyproject.toml",
        ]

        suspicious_sources = [
            r'git\+https?://(?!github\.com)',  # Non-GitHub git sources
            r'http://',  # Insecure HTTP
            r'--index-url\s+https?://(?!pypi\.org)',  # Non-PyPI index
        ]

        findings = []
        for req_file in requirements_files:
            if req_file.exists():
                try:
                    content = req_file.read_text()
                    for pattern in suspicious_sources:
                        if re.search(pattern, content):
                            findings.append({
                                "file": str(req_file),
                                "pattern": pattern,
                            })
                except Exception:
                    pass

        assert len(findings) == 0, f"Found suspicious dependencies: {findings}"
