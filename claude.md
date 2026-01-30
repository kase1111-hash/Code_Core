# Claude.md - Project Context for AI Assistance

## Project Overview

**Ollama Automation Harness** is a human-AI collaboration platform that pairs Claude (Anthropic's LLM) with Ollama (local LLM) for LLM-powered development automation with human oversight. It enables natural language programming for development tasks while maintaining proof-of-human-work through comprehensive audit trails.

### Core Functionality
- **AI-Powered Automation**: Claude generates code via natural language; Ollama provides local LLM inference
- **Human Oversight**: Dangerous operations require user approval (trust enforcement)
- **Sandboxed Execution**: Secure agent orchestration with file operations restricted to sandbox
- **Configurable Permissions**: YAML-based security policy rules for action classification
- **Audit Logging**: Complete reasoning audit trail of all automated actions

## Architecture

```
User Input → Claude API/Ollama → Classify Action →
  Check Permissions → Execute or Prompt User → Log Result → Continue/Exit
```

### Decision Classification
- **Auto**: Safe operations (code generation, tests, reads)
- **User**: Dangerous operations (deploys, git push, system changes)
- **Deny**: Completely blocked operations

## Directory Structure

```
Code_Core/
├── main.py                 # Primary entry point (interactive loop)
├── cli.py                  # Enhanced CLI with subcommands
├── core/                   # Core business logic
│   ├── claude.py           # Claude API client with Ollama fallback
│   ├── ollama.py           # Ollama CLI subprocess wrapper
│   ├── classifier.py       # Action classification (parse & risk assess)
│   ├── executor.py         # Sandboxed command execution
│   └── safety.py           # Permission management & enforcement
├── utils/                  # Utility modules
│   ├── config.py           # Configuration management
│   ├── validation.py       # Input validation & sanitization
│   ├── logger.py           # Audit logging
│   ├── errors.py           # Error definitions & handling
│   ├── secrets.py          # Secure configuration
│   ├── telemetry.py        # Telemetry collection
│   ├── metrics.py          # Metrics registry
│   └── monitoring.py       # Health monitoring
├── config/                 # Configuration files
│   └── permissions.yaml    # Permission rules (auto/ask/deny)
├── tests/                  # Comprehensive test suite (~7600 LOC)
├── docs/                   # Comprehensive documentation
└── sandbox/                # Safe execution directory
```

## Tech Stack

- **Language**: Python 3.10+
- **Runtime Dependencies**: anthropic, PyYAML, python-dotenv, sentry-sdk (optional)
- **Dev Dependencies**: pytest, pytest-cov, mypy, ruff, pre-commit
- **External Services**: Anthropic Claude API, Ollama (local LLM)
- **Infrastructure**: Docker, Docker Compose, GitHub Actions

## Code Conventions

### Style
- **Formatting**: Black (88 char line length)
- **Linting**: Ruff
- **Type Checking**: Mypy (strict mode, Python 3.10+)
- **Docstrings**: Google-style for all public functions

### Naming
- `snake_case` for functions and variables
- `PascalCase` for classes
- `SCREAMING_SNAKE_CASE` for constants

### Testing
- **Framework**: pytest
- **Coverage Target**: 80% minimum
- **Test Markers**:
  - `@pytest.mark.slow` - Long-running tests
  - `@pytest.mark.integration` - Integration tests
  - `@pytest.mark.security` - Security tests
  - `@pytest.mark.regression` - Critical functionality
  - `@pytest.mark.smoke` - Quick sanity checks
  - `@pytest.mark.performance` - Load/stress tests
- **Pattern**: AAA (Arrange, Act, Assert)

### Error Handling
- Custom error hierarchy: `ServiceError`, `ClaudeError`, `OllamaError`, `ValidationError`
- Include operation context for debugging
- Provide recovery suggestions in error messages
- Graceful degradation: Claude API falls back to Ollama

## Common Commands

### Development Setup
```bash
make venv                   # Create virtual environment
source .venv/bin/activate   # Activate venv
make install-dev            # Install all dependencies
cp .env.example .env        # Copy environment template
```

### Running
```bash
python main.py              # Interactive mode
python main.py -p "prompt"  # With initial prompt
python cli.py run           # Enhanced CLI
python cli.py check --fix   # Health checks with auto-fix
```

### Testing
```bash
make test                   # Run all tests
make coverage               # Tests with coverage report
pytest tests/test_X.py -v   # Specific test file
pytest -m "security" -v     # Specific test category
pytest -x --tb=short        # Fail fast
```

### Code Quality
```bash
make check                  # All quality checks
make lint                   # Run linting (ruff)
make format                 # Format code
make typecheck              # Run type checker (mypy)
make security               # Security analysis (bandit)
```

### Docker
```bash
make docker-build           # Build Docker image
make docker-run             # Run Docker container
docker-compose up -d        # Docker Compose
```

## Key Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key | (Ollama fallback) |
| `OLLAMA_MODEL` | Ollama model name | `llama3` |
| `SANDBOX_DIR` | Sandbox directory | `./sandbox` |
| `PERMISSIONS_FILE` | Permissions config | `./config/permissions.yaml` |
| `ENVIRONMENT` | Env (dev/staging/prod) | `development` |
| `DEBUG` | Enable debug mode | `false` |

## Security Considerations

When modifying this codebase:

1. **Input Validation**: All external inputs must be sanitized using `utils/validation.py`
2. **Path Validation**: Prevent directory traversal - use `validate_path()` for all file operations
3. **Sandbox Enforcement**: File operations must be restricted to `sandbox/` directory
4. **Keyword Detection**: Check `config/permissions.yaml` for dangerous operation keywords
5. **Timeout Enforcement**: All subprocess operations must have timeouts
6. **No Hardcoded Secrets**: Use environment variables via `utils/secrets.py`

## Important Files

| File | Purpose |
|------|---------|
| `core/classifier.py` | Action risk classification logic |
| `core/executor.py` | Sandboxed command execution |
| `core/safety.py` | Permission enforcement |
| `config/permissions.yaml` | Permission rules configuration |
| `utils/validation.py` | Input sanitization functions |
| `tests/conftest.py` | Pytest fixtures and configuration |

## Git Workflow

- **Commit Messages**: Use conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`)
- **Quality Checks**: Run `make check && make test` before committing
- **PR Process**: Create feature branch, make changes, submit PR against `main`

## Troubleshooting

- **Ollama not responding**: Check if Ollama is running with `ollama list`
- **Permission denied**: Verify `config/permissions.yaml` rules
- **Sandbox errors**: Ensure `sandbox/` directory exists and is writable
- **API key issues**: Check `ANTHROPIC_API_KEY` in `.env` file

## Documentation

- **[README.md](README.md)** - Quick start guide
- **[docs/architecture.md](docs/architecture.md)** - System design
- **[docs/api-reference.md](docs/api-reference.md)** - API documentation
- **[docs/troubleshooting.md](docs/troubleshooting.md)** - Issue solutions
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
