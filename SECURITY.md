# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of Ollama Automation Harness seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of these methods:

1. **GitHub Security Advisories**: Use the [Security tab](../../security/advisories) to privately report a vulnerability
2. **Email**: Contact the maintainers directly (if available in the repository)

### What to Include

When reporting a vulnerability, please include:

- **Description**: A clear description of the vulnerability
- **Impact**: The potential impact and severity
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Affected Versions**: Which versions are affected
- **Potential Fix**: If you have suggestions for fixing the issue

### Response Timeline

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Initial Assessment**: We will provide an initial assessment within 7 days
- **Resolution**: We aim to resolve critical vulnerabilities within 30 days

### Disclosure Policy

- We will work with you to understand and resolve the issue
- We will credit you in the security advisory (unless you prefer to remain anonymous)
- We ask that you give us reasonable time to address the issue before public disclosure

---

## Security Features

The Ollama Automation Harness implements multiple security layers:

### 1. Permission System

YAML-based configuration (`config/permissions.yaml`) controls action authorization:

```yaml
actions:
  read_file: auto      # Safe operations run automatically
  write_file: ask      # Requires user confirmation
  deploy: deny         # Blocked entirely

dangerous_keywords:
  - deploy
  - production
  - sudo
  - rm -rf
```

### 2. Sandbox Enforcement

All file operations are restricted to the `sandbox/` directory:

- Path validation prevents directory traversal (`../`)
- Writes outside the sandbox are blocked
- Configurable sandbox location via `SANDBOX_DIR`

### 3. Input Validation

- All external inputs are validated
- Command injection prevention
- Path sanitization

### 4. Audit Logging

Complete audit trail of all actions:

- All commands logged with full context
- Decision reasoning recorded
- User approvals tracked
- Timestamps for all operations

### 5. Human Oversight

Dangerous operations always require explicit user approval:

- Keyword detection for risky commands
- User confirmation workflow
- Ability to modify or reject commands

---

## Security Best Practices

When using Ollama Automation Harness:

### Configuration

1. **Review permissions**: Customize `config/permissions.yaml` for your security requirements
2. **Restrict sandbox**: Use a dedicated, isolated directory for the sandbox
3. **Protect secrets**: Never commit `.env` files; use environment variables

### Deployment

1. **Run with minimal privileges**: Don't run as root
2. **Isolate the environment**: Consider using containers
3. **Monitor logs**: Regularly review audit logs for suspicious activity

### API Keys

1. **Rotate regularly**: Change API keys periodically
2. **Use environment variables**: Never hardcode keys in source code
3. **Restrict permissions**: Use API keys with minimal necessary permissions

---

## Security Updates

Security updates are released as patch versions (e.g., 1.0.1). We recommend:

1. **Subscribe to releases**: Watch the repository for release notifications
2. **Update promptly**: Apply security patches as soon as possible
3. **Review changelogs**: Check CHANGELOG.md for security-related updates

---

## Security Testing

The project includes comprehensive security testing:

- **Static Analysis**: Ruff with flake8-bandit rules
- **Security Tests**: `tests/test_security.py`, `tests/test_exploits.py`
- **CI/CD Security Scanning**: `.github/workflows/security.yml`

### Running Security Tests

```bash
# Run security test suite
pytest -m "security" -v

# Run exploit tests
pytest -m "exploit" -v

# Run static analysis with security rules
ruff check --select S .
```

---

## Acknowledgments

We thank all security researchers who responsibly disclose vulnerabilities. Contributors who report valid security issues will be acknowledged in the security advisory (unless they prefer to remain anonymous).

---

## Contact

For security concerns that don't fit the vulnerability reporting process, please open a general issue or contact the maintainers.
