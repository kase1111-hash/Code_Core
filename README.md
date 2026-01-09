# Ollama Automation Harness

A Python CLI that pairs Claude with Ollama for automated development workflows with human oversight on sensitive operations.

## Features

- **AI-Powered Automation**: Claude generates code and suggestions, Ollama classifies actions
- **Human Oversight**: Dangerous operations always require user approval
- **Sandboxed Execution**: All file operations restricted to a safe directory
- **Configurable Permissions**: YAML-based rules for action classification
- **Audit Logging**: Complete trail of all automated actions

## Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai) installed with `llama3` model
- (Optional) Anthropic API key for Claude

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ollama-automation-harness.git
cd ollama-automation-harness

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
  read_file: auto      # Execute without asking
  write_file: ask      # Require user confirmation
  git_push: ask        # Require user confirmation
  deploy: deny         # Block entirely

default: ask           # Default for unknown actions
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key | (Ollama fallback) |
| `OLLAMA_MODEL` | Ollama model name | `llama3` |
| `SANDBOX_DIR` | Sandbox directory | `./sandbox` |
| `LOG_FILE` | Log file path | `./logs/automation.log` |

## Project Structure

```
ollama-automation-harness/
├── main.py              # Entry point
├── core/                # Core modules
│   ├── ollama.py        # Ollama CLI wrapper
│   ├── claude.py        # Claude API client
│   ├── classifier.py    # Action classification
│   ├── executor.py      # Sandboxed execution
│   └── safety.py        # Permission management
├── utils/
│   └── logger.py        # Audit logging
├── config/
│   └── permissions.yaml # Permission rules
├── sandbox/             # Safe execution directory
├── logs/                # Audit logs
└── tests/               # Test suite
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
make lint        # Run linter
make format      # Format code
make typecheck   # Run type checker
make test        # Run tests
make coverage    # Run tests with coverage
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

The harness implements multiple security layers:

1. **Keyword Detection**: Commands with dangerous keywords (`deploy`, `sudo`, `rm -rf`, etc.) always require approval
2. **Permission System**: YAML configuration controls action authorization
3. **Sandbox Enforcement**: File operations restricted to sandbox directory
4. **Path Validation**: No path traversal (`../`) allowed
5. **Audit Logging**: All actions logged with full context

## Documentation

- [Implementation Spec](docs/implementation-spec.md) - Detailed technical specification
- [Architecture](docs/architecture.md) - System design and data flow
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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Anthropic](https://anthropic.com) for Claude
- [Ollama](https://ollama.ai) for local LLM inference
