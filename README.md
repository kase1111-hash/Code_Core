# Ollama Automation Harness

A **human-AI collaboration** platform that pairs Claude with Ollama for **LLM-powered automation workflows** with human oversight on sensitive operations. This **AI automation harness** enables **natural language programming** for development tasks while preserving **human cognitive labor** and maintaining **proof of human work** through comprehensive audit trails.

## What Problem Does This Solve?

- How do I automate development tasks with AI while keeping human control?
- How can I use LLMs for code generation safely?
- How do I maintain audit trails for AI-assisted development?
- How can I implement human-AI collaboration in my workflow?

## Features

- **AI-Powered Automation**: Claude generates code via **natural language prompts**, Ollama provides **local LLM inference** for action classification
- **Human Oversight**: Implements **AI trust enforcement** ensuring dangerous operations always require user approval
- **Sandboxed Execution**: **Secure agent orchestration** with all file operations restricted to a safe directory
- **Configurable Permissions**: YAML-based **AI security policy** rules for action classification
- **Audit Logging**: Complete **reasoning audit trail** of all automated actions for **intent tracking**

## Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) installed with `llama3` model
- (Optional) Anthropic API key for Claude

### Installation

```bash
# Clone the repository
git clone https://github.com/kase1111-hash/Code_Core.git
cd Code_Core

# Create virtual environment
make setup
# Or manually:
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY (optional)
```

### Running

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the harness
python main.py

# Or use make
make run
```

## Usage

Once running, you'll enter an interactive loop:

```
Enter your prompt: Write a function to calculate fibonacci numbers

[Claude]: Here's a Python function for calculating Fibonacci...

[Decision]: auto (Safe code generation)
Executing...

[Result]: File written to sandbox/fibonacci.py

Enter your prompt: Deploy this to production

[Decision]: user (Dangerous operation: deploy)

⚠️  User action required: Contains dangerous keyword 'deploy'
Approve (y), modify (m), skip (s), quit (q): _
```

### User Actions

| Key | Action |
|-----|--------|
| `y` | Approve and execute |
| `m` | Modify the prompt |
| `s` | Skip and enter new prompt |
| `q` | Quit the application |

## Configuration

### Permissions (`config/permissions.yaml`)

Control which actions require approval:

```yaml
actions:
  # File operations
  read_file: auto      # Execute without asking
  write_file: ask      # Require user confirmation
  delete_file: ask

  # Code operations
  run_tests: auto      # Tests run automatically
  lint_code: auto
  format_code: auto

  # Git operations
  git_status: auto
  git_diff: auto
  git_add: ask
  git_commit: ask
  git_push: ask        # Require user confirmation
  git_pull: ask

  # Dangerous operations
  deploy: deny         # Block entirely
  deploy_production: deny
  system_command: deny
  install_package: ask

default: ask           # Default for unknown actions

dangerous_keywords:    # Always require approval
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
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key | (Ollama fallback) |
| `OLLAMA_MODEL` | Ollama model name | `llama3` |
| `CLAUDE_MODEL` | Claude model name | `claude-sonnet-4-20250514` |
| `CLAUDE_MAX_TOKENS` | Maximum tokens for Claude response | `4096` |
| `SANDBOX_DIR` | Sandbox directory | `./sandbox` |
| `PERMISSIONS_FILE` | Permissions config file path | `./config/permissions.yaml` |
| `LOG_FILE` | Log file path | `./logs/automation.log` |
| `OLLAMA_TIMEOUT` | Ollama timeout (seconds) | `60` |
| `COMMAND_TIMEOUT` | Command timeout (seconds) | `30` |
| `MAX_RETRIES` | Maximum retry attempts for Ollama | `3` |
| `RETRY_DELAY` | Delay between retries (seconds) | `1.0` |
| `LOOP_DELAY` | Delay between automation loop iterations (seconds) | `1.0` |
| `MAX_REPLY_LENGTH` | Maximum characters to display from AI reply | `2000` |
| `ENVIRONMENT` | Environment mode (`development`, `staging`, `production`, `testing`) | `development` |
| `DEBUG` | Enable debug mode | `false` |


### CLI Commands

**Basic usage (`main.py`):**

```bash
# Start interactive mode
python main.py

# Run with initial prompt
python main.py -p "Create a fibonacci function"

# Read prompt from file
python main.py -f prompt.txt

# Use custom config and sandbox
python main.py --config custom-permissions.yaml --sandbox /tmp/safe

# Verbose or quiet mode
python main.py -v          # Verbose output
python main.py -q          # Quiet mode
```

**Enhanced CLI (`cli.py`):**

```bash
# Run harness with all available options
python cli.py run                          # Start interactive mode
python cli.py run -p "Create a test"       # Run with initial prompt
python cli.py run -f prompt.txt            # Read prompt from file
python cli.py run --dry-run                # Show what would be done without executing
python cli.py run --no-confirm             # Auto-approve low-risk actions (use with caution)
python cli.py run --model codellama        # Override the AI model
python cli.py run --timeout 120            # Set command timeout (seconds)
python cli.py run -e production            # Override environment

# Configuration management
python cli.py config show      # Show current configuration
python cli.py config validate  # Validate configuration
python cli.py config init      # Initialize default config files
python cli.py config init --force  # Overwrite existing config files
python cli.py config path      # Show config file paths

# System health checks
python cli.py check            # Run health checks
python cli.py check --fix      # Fix common issues automatically
python cli.py check -v         # Verbose health check output

# Version and monitoring
python cli.py version          # Show version and system info
python cli.py status           # Show application status
```

## Quick Help

### Common Issues

| Issue | Solution |
|-------|----------|
| "Ollama not found" | Install from [ollama.com](https://ollama.com), run `ollama serve` |
| "API key not set" | Add `ANTHROPIC_API_KEY=sk-ant-...` to `.env` (optional) |
| Slow responses | Use `OLLAMA_MODEL=phi` for faster inference |
| Permission denied | Check `config/permissions.yaml` settings |
| Timeout errors | Increase `OLLAMA_TIMEOUT` in `.env` |

### Getting Help

```bash
# Run health check
python cli.py check --verbose

# View logs
tail -f logs/automation.log

# Enable debug mode
DEBUG=true python main.py -v
```

See [Troubleshooting Guide](docs/troubleshooting.md) for detailed solutions.

## Project Structure

```
ollama-automation-harness/
├── main.py                 # Primary entry point
├── cli.py                  # Enhanced CLI with subcommands
├── pyproject.toml          # Project configuration
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── Makefile                # Build automation
├── Dockerfile              # Container image
├── .env.example            # Environment template
│
├── core/                   # Core business logic
│   ├── claude.py           # Claude API client
│   ├── ollama.py           # Ollama CLI wrapper
│   ├── classifier.py       # Action classification
│   ├── executor.py         # Sandboxed execution
│   └── safety.py           # Permission management
│
├── utils/                  # Utility modules
│   ├── config.py           # Configuration management
│   ├── validation.py       # Input validation
│   ├── logger.py           # Audit logging
│   ├── errors.py           # Error definitions
│   ├── secrets.py          # Secure configuration
│   ├── version.py          # Version info
│   ├── error_tracking.py   # Error tracking
│   └── environment.py      # Environment management
│
├── config/                 # Configuration files
│   └── permissions.yaml    # Permission rules
│
├── docs/                   # Documentation
│   ├── FAQ.md              # Frequently asked questions
│   ├── troubleshooting.md  # Troubleshooting guide
│   ├── api-reference.md    # API documentation
│   ├── architecture.md     # System architecture
│   ├── diagrams.md         # Mermaid diagrams
│   └── ...                 # Additional docs
│
├── sandbox/                # Safe execution directory
├── logs/                   # Audit logs
└── tests/                  # Test suite
    ├── unit/               # Unit tests
    ├── integration/        # Integration tests
    └── acceptance/         # Acceptance tests
```

## Development

### Setup Development Environment

```bash
# Install dev dependencies
make install-dev

# Or manually
pip install -r requirements-dev.txt
pre-commit install
```

### Common Commands

```bash
# Code quality
make lint          # Run linter (ruff)
make format        # Format code (ruff)
make typecheck     # Run type checker (mypy)
make security      # Run security analysis (bandit)
make check         # Run all quality checks (lint + typecheck + security)

# Testing
make test          # Run all tests
make test-fast     # Run tests, stop on first failure
make test-unit     # Run unit tests only
make test-integration  # Run integration tests
make test-security     # Run security tests
make test-performance  # Run performance tests
make test-regression   # Run regression tests
make coverage      # Run tests with coverage report

# Build & package
make build         # Build distribution packages
make package-zip   # Create zip distribution
make package-exe   # Create standalone executable
make package-docker  # Build production Docker image
make package-all   # Create all distribution packages
```

### Using Docker

```bash
# Build image
make docker-build

# Run container
make docker-run

# Development container
make docker-dev
```

## Security

The harness implements multiple **AI security monitoring** layers as a **cognitive firewall** for automated operations:

1. **Keyword Detection**: Commands with dangerous keywords (`deploy`, `production`, `push`, `sudo`, `rm -rf`, `chmod`, `chown`, `curl`, `wget`, `eval`, `exec`) always require approval - acting as **cognition boundary control**
2. **Permission System**: YAML configuration provides **AI boundary policy** for action authorization
3. **Sandbox Enforcement**: **Agent trust boundaries** restrict file operations to sandbox directory
4. **Path Validation**: **Cognitive access control** prevents path traversal (`../`) attacks
5. **Audit Logging**: **Security event management** logs all actions with full context for **AI security audit logs**

For security vulnerability reporting, see [SECURITY.md](SECURITY.md).

## Documentation

### User Guides
- [FAQ](docs/FAQ.md) - Frequently Asked Questions
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

### Technical Documentation
- [API Reference](docs/api-reference.md) - Complete API documentation
- [Architecture](docs/architecture.md) - System design and data flow
- [Diagrams](docs/diagrams.md) - Architecture and flow diagrams (Mermaid)
- [Implementation Spec](docs/implementation-spec.md) - Detailed technical specification

### Development Resources
- [User Stories](docs/user-stories.md) - Requirements and acceptance criteria
- [Tech Stack](docs/tech-stack.md) - Technology choices
- [Style Guide](docs/style-guide.md) - Coding conventions

## Testing

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Run specific test file
pytest tests/test_classifier.py -v
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`make check && make test`)
5. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

For detailed contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Anthropic](https://anthropic.com) for Claude
- [Ollama](https://ollama.com) for local LLM inference

---

## Part of the Connected Ecosystem

This project integrates with a broader ecosystem of **digital sovereignty** and **human-AI collaboration** tools:

### NatLangChain Ecosystem
- [NatLangChain](https://github.com/kase1111-hash/NatLangChain) - Prose-first, intent-native blockchain for **natural language smart contracts**
- [IntentLog](https://github.com/kase1111-hash/IntentLog) - **Version control for reasoning** - tracks "why" changes happen via prose commits
- [RRA-Module](https://github.com/kase1111-hash/RRA-Module) - **Autonomous licensing agent** for abandoned repository monetization
- [mediator-node](https://github.com/kase1111-hash/mediator-node) - **LLM mediator** for matching, negotiation, and closure proposals
- [ILR-module](https://github.com/kase1111-hash/ILR-module) - **IP dispute resolution** and licensing reconciliation module
- [Finite-Intent-Executor](https://github.com/kase1111-hash/Finite-Intent-Executor) - **Posthumous smart contracts** for digital estate execution

### Agent-OS Ecosystem
- [Agent-OS](https://github.com/kase1111-hash/Agent-OS) - **Natural language operating system** for AI agents (NLOS)
- [synth-mind](https://github.com/kase1111-hash/synth-mind) - **Psychological AI architecture** with emergent continuity and empathy
- [boundary-daemon](https://github.com/kase1111-hash/boundary-daemon-) - **AI trust enforcement** layer defining cognition boundaries
- [memory-vault](https://github.com/kase1111-hash/memory-vault) - **Sovereign AI memory** storage for cognitive artifacts
- [value-ledger](https://github.com/kase1111-hash/value-ledger) - **Cognitive work accounting** for ideas, effort, and novelty
- [learning-contracts](https://github.com/kase1111-hash/learning-contracts) - **AI learning safety protocols** and data governance

### Security Infrastructure
- [Boundary-SIEM](https://github.com/kase1111-hash/Boundary-SIEM) - **AI security monitoring** and event management system

### Games & Creative Projects
- [Shredsquatch](https://github.com/kase1111-hash/Shredsquatch) - 3D first-person **snowboarding infinite runner** (SkiFree homage)
- [Midnight-pulse](https://github.com/kase1111-hash/Midnight-pulse) - **Procedural night driving** game with synthwave aesthetics
- [Long-Home](https://github.com/kase1111-hash/Long-Home) - Atmospheric indie narrative game built with Godot
