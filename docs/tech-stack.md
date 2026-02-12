# Tech Stack & Dependencies

## Overview

This document outlines the technology choices and dependencies for the Ollama Automation Harness project.

---

## Core Technology

### Language: Python 3.10+

**Justification:**
- Native subprocess support for Ollama CLI integration
- Rich ecosystem for API clients and YAML parsing
- Type hints for better code quality and IDE support
- Cross-platform compatibility (macOS, Linux, Windows/WSL)

---

## Runtime Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `anthropic` | ^0.40.0 | Official Claude API client |
| `pyyaml` | ^6.0 | YAML config file parsing |
| `python-dotenv` | ^1.0.0 | Environment variable management |

### anthropic
- Official Anthropic SDK for Claude API integration
- Handles authentication, rate limiting, and response parsing
- Required for `core/claude.py` module

### pyyaml
- Parse `config/permissions.yaml` for action classification
- Load configuration files
- Required for `core/safety.py` module

### python-dotenv
- Load `.env` files for `ANTHROPIC_API_KEY`
- Secure configuration management
- Keep secrets out of version control

---

## Standard Library (No Install Required)

| Module | Purpose |
|--------|---------|
| `subprocess` | Execute Ollama CLI commands |
| `json` | Parse Claude/Ollama responses |
| `pathlib` | Safe path manipulation for sandbox |
| `logging` | Audit trail and error logging |
| `dataclasses` | Decision and ExecutionResult structures |
| `typing` | Type annotations |
| `argparse` | CLI argument parsing |
| `datetime` | Timestamps for logging |
| `os` | Environment variables, file operations |
| `sys` | Exit codes, stdin/stdout |

---

## Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | ^8.0.0 | Unit and integration testing |
| `pytest-cov` | ^4.1.0 | Test coverage reporting |
| `mypy` | ^1.8.0 | Static type checking |
| `ruff` | ^0.2.0 | Fast linting and formatting |
| `black` | ^24.0.0 | Code formatting (alternative) |
| `pre-commit` | ^3.6.0 | Git hooks for quality checks |

### Testing
- `pytest`: Test framework with fixtures and parameterization
- `pytest-cov`: Coverage reports for CI/CD

### Code Quality
- `mypy`: Catch type errors before runtime
- `ruff`: All-in-one linter (replaces flake8, isort, etc.)
- `black`: Consistent code formatting

### Automation
- `pre-commit`: Run checks before commits

---

## External Services

### Ollama (Local)
- **Purpose:** Local LLM inference for decision classification
- **Model:** `llama3` (default)
- **Installation:** https://ollama.com
- **Requirement:** Must be running locally on default port

### Claude API (Remote)
- **Purpose:** Code generation and suggestions
- **Model:** `claude-sonnet-4-20250514`
- **Authentication:** `ANTHROPIC_API_KEY` environment variable
- **Fallback:** Ollama simulation when API key missing

---

## Project Structure

```
ollama-automation-harness/
├── core/
│   ├── __init__.py
│   ├── ollama.py      # Ollama subprocess wrapper
│   ├── claude.py      # Claude API client
│   ├── classifier.py  # Decision classification
│   ├── executor.py    # Sandboxed execution
│   └── safety.py      # Permission management
├── utils/
│   ├── __init__.py
│   └── logger.py      # Logging utilities
├── config/
│   └── permissions.yaml
├── tests/
│   ├── __init__.py
│   ├── test_ollama.py
│   ├── test_claude.py
│   ├── test_classifier.py
│   ├── test_executor.py
│   └── test_safety.py
├── logs/
│   └── .gitkeep
├── sandbox/
│   └── .gitkeep
├── docs/
│   ├── user-stories.md
│   └── tech-stack.md
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

---

## Version Constraints

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.10 | 3.11+ |
| Ollama | 0.1.0 | Latest |
| pip | 23.0 | Latest |

---

## Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| macOS | ✅ Full | Native Ollama support |
| Linux | ✅ Full | Native Ollama support |
| Windows | ⚠️ WSL | Requires WSL2 for Ollama |

---

## Security Considerations

- `ANTHROPIC_API_KEY` stored in `.env` (not committed)
- Sandbox directory for all file operations
- No root/sudo access required
- Audit logging for compliance
