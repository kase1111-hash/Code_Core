# Frequently Asked Questions (FAQ)

This document answers common questions about the Ollama Automation Harness.

---

## Table of Contents

1. [General Questions](#general-questions)
2. [Installation & Setup](#installation--setup)
3. [Usage Questions](#usage-questions)
4. [Configuration](#configuration)
5. [Security](#security)
6. [Troubleshooting](#troubleshooting)
7. [Development](#development)

---

## General Questions

### What is the Ollama Automation Harness?

The Ollama Automation Harness is a CLI application that enables AI-powered development automation with human oversight. It pairs Claude (Anthropic's AI) for code generation with Ollama (local LLM) for action classification, ensuring dangerous operations always require user approval.

### Why use this instead of just using Claude directly?

The harness adds several critical features:
- **Safety controls**: Dangerous operations are detected and require approval
- **Sandboxed execution**: File operations are restricted to a safe directory
- **Audit logging**: All actions are logged for accountability
- **Local classification**: Ollama runs locally, reducing API costs for classification
- **Configurable permissions**: Fine-grained control over what actions are allowed

### Do I need an Anthropic API key?

No, the API key is optional. If not provided, the harness will use Ollama for both code generation and classification. However, Claude typically provides better code generation quality.

### Is my data sent to external servers?

- **With API key**: Prompts are sent to Anthropic's Claude API
- **Without API key**: Everything runs locally via Ollama
- **Classification**: Always uses local Ollama (no external API calls)
- **Execution**: All command execution is local

### What models are supported?

**Claude (via API):**
- `claude-sonnet-4-20250514` (default)
- Other Claude models can be configured

**Ollama (local):**
- `llama3` (default)
- Any model available via `ollama list`

---

## Installation & Setup

### What are the system requirements?

- **Python**: 3.10 or higher
- **Ollama**: Latest version with at least one model installed
- **Memory**: 8GB+ recommended (depends on Ollama model)
- **Disk**: 5GB+ for Ollama models
- **OS**: Linux, macOS, or Windows with WSL

### How do I install Ollama?

Visit [ollama.com](https://ollama.com) and follow the installation instructions for your OS.

After installation, pull the default model:
```bash
ollama pull llama3
```

### Why is Ollama not found?

Ensure Ollama is:
1. Installed: `which ollama` (Linux/Mac) or `where ollama` (Windows)
2. In your PATH
3. Running: `ollama serve` (may run automatically on some systems)

### How do I get an Anthropic API key?

1. Visit [console.anthropic.com](https://console.anthropic.com)
2. Create an account
3. Navigate to API Keys
4. Create a new key
5. Add to your `.env` file: `ANTHROPIC_API_KEY=sk-ant-...`

### Can I use a virtual environment?

Yes, and it's recommended:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### Docker installation fails, what do I do?

Common fixes:
1. Ensure Docker is installed and running
2. Check disk space (images need ~2GB)
3. On Linux, ensure your user is in the `docker` group
4. Try: `docker build --no-cache -t ollama-harness .`

---

## Usage Questions

### How do I start the harness?

**Interactive mode:**
```bash
python main.py
# or
make run
```

**With initial prompt:**
```bash
python main.py -p "Create a fibonacci function"
```

**From file:**
```bash
python main.py -f prompt.txt
```

### What do the decision types mean?

| Decision | Meaning |
|----------|---------|
| `auto` | Safe operation, executes automatically |
| `user` | Requires your approval before executing |

### What do the risk levels mean?

| Level | Description | Examples |
|-------|-------------|----------|
| `low` | Read-only operations | Reading files, listing directories |
| `medium` | Safe writes | Writing to sandbox, running tests |
| `high` | Dangerous operations | Git push, deploy, system commands |

### How do I approve/reject actions?

When prompted:
- `y` - Approve and execute the command
- `m` - Modify the prompt and try again
- `s` - Skip this action and enter a new prompt
- `q` - Quit the application

### Can I run commands automatically without approval?

Yes, but use with caution:
1. Set actions to `auto` in `config/permissions.yaml`
2. Use `--no-confirm` flag for low-risk actions only
3. Never set dangerous operations to `auto`

### Where are generated files saved?

All files are written to the `sandbox/` directory (configurable via `SANDBOX_DIR`). This prevents the harness from modifying files outside the safe zone.

### How do I view the audit log?

```bash
# View recent logs
tail -f logs/automation.log

# Search for specific actions
grep "git_push" logs/automation.log

# JSON formatted logs (if enabled)
cat logs/automation.json | jq
```

---

## Configuration

### How do I change the default model?

Edit `.env`:
```bash
# For Claude
CLAUDE_MODEL=claude-sonnet-4-20250514

# For Ollama
OLLAMA_MODEL=codellama
```

### How do I add custom dangerous keywords?

Edit `config/permissions.yaml`:
```yaml
dangerous_keywords:
  - deploy
  - production
  - push
  - sudo
  - rm -rf
  - chmod
  - chown
  - curl
  - wget
  - eval
  - exec
  - your_custom_keyword  # Add your own keywords here
```

### How do I allow specific actions without approval?

Edit `config/permissions.yaml`:
```yaml
actions:
  run_tests: auto      # No approval needed
  lint_code: auto
  read_file: auto
  write_file: ask      # Still requires approval
```

### Can I use different configurations for different environments?

Yes, use the `--config` flag:
```bash
python main.py --config config/permissions-dev.yaml
```

Or use environment-specific files in `config/environments/`.

### How do I increase timeouts?

Edit `.env`:
```bash
OLLAMA_TIMEOUT=120      # Ollama timeout in seconds
COMMAND_TIMEOUT=60      # Command execution timeout
```

---

## Security

### Is this safe to use in production?

The harness is designed for development automation. For production use:
1. Never set dangerous operations to `auto`
2. Review all audit logs
3. Use environment-specific configurations
4. Consider running in a container with limited permissions

### What operations are blocked by default?

- `deploy` - All deployment operations
- `deploy_production` - Production deployments
- `system_command` - Direct system commands
- Commands containing: `sudo`, `rm -rf`, `chmod`, `chown`, `curl`, `wget`, `eval`, `exec`, `push`, `production`

### Can the AI bypass security controls?

No. The security layers are enforced at the application level:
1. Keyword detection scans all responses
2. Permission checks are mandatory
3. Sandbox paths are validated
4. All actions are logged

### How do I audit AI actions?

All actions are logged to `logs/automation.log`:
```
[2024-01-15T10:30:00] ACTION=execute DECISION=auto RISK=low COMMAND="pytest tests/" RESULT=success
```

For detailed auditing, enable JSON logging:
```bash
# In .env
LOG_JSON=true
```

### Is my API key secure?

- Store in `.env` file (git-ignored by default)
- Never commit API keys to version control
- Use environment variables in production
- The key is never logged or exposed

---

## Troubleshooting

### "Ollama not found" error

See the [Troubleshooting Guide](./troubleshooting.md#ollama-not-found).

### "ANTHROPIC_API_KEY not set" warning

This is informational, not an error. The harness will use Ollama as a fallback. To use Claude, add your API key to `.env`.

### Commands timeout frequently

1. Increase timeout: `OLLAMA_TIMEOUT=120` in `.env`
2. Use a smaller model: `OLLAMA_MODEL=phi`
3. Check system resources (RAM, CPU)

### Permission denied errors

1. Check sandbox directory permissions
2. Ensure you own the sandbox directory
3. On Docker, check volume mount permissions

### Classification seems wrong

1. Use a more capable model for classification
2. Check if keywords are triggering false positives
3. Review the classification prompt in `core/classifier.py`

For more issues, see the [Troubleshooting Guide](./troubleshooting.md).

---

## Development

### How do I run tests?

```bash
# All tests
make test

# With coverage
make coverage

# Specific test
pytest tests/test_classifier.py -v
```

### How do I add a new action type?

1. Add to `config/permissions.yaml`:
   ```yaml
   actions:
     my_new_action: ask
   ```

2. Update `_infer_action_type()` in `core/safety.py`

3. Add tests in `tests/`

### How do I contribute?

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run `make check && make test`
5. Submit a Pull Request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.

### Where can I get help?

- [GitHub Issues](https://github.com/kase1111-hash/Code_Core/issues)
- [Documentation](./README.md)
- [Architecture Guide](./architecture.md)
- [API Reference](./api-reference.md)

---

## Still have questions?

If your question isn't answered here:
1. Check the [Troubleshooting Guide](./troubleshooting.md)
2. Search [existing issues](https://github.com/kase1111-hash/Code_Core/issues)
3. Open a new issue with:
   - Your environment (OS, Python version)
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant log output

---

*Last updated: 2025-02-12*
