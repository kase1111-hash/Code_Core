# Contributing to Ollama Automation Harness

Thank you for your interest in contributing to the Ollama Automation Harness! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Issue Reporting](#issue-reporting)
- [Community Guidelines](#community-guidelines)

---

## Getting Started

### Prerequisites

Before contributing, ensure you have the following installed:

- Python 3.10 or higher
- [Ollama](https://ollama.com) with a model (e.g., `llama3`)
- Git
- Make (optional, but recommended)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ollama-automation-harness.git
   cd ollama-automation-harness
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/kase1111-hash/Code_Core.git
   ```

---

## Development Setup

### Environment Setup

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Or use make
make install-dev

# Install pre-commit hooks
pre-commit install

# Copy environment template
cp .env.example .env
```

### Verify Setup

```bash
# Run tests to verify everything works
make test

# Run linting
make lint

# Run type checking
make typecheck
```

---

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

- **Bug Fixes**: Fix issues reported in the issue tracker
- **Features**: Implement new functionality (please discuss first)
- **Documentation**: Improve or add documentation
- **Tests**: Add or improve test coverage
- **Performance**: Optimize existing code
- **Security**: Report or fix security vulnerabilities (see [SECURITY.md](SECURITY.md))

### Before You Start

1. **Check existing issues**: Look for open issues or discussions related to your contribution
2. **Open an issue first**: For significant changes, open an issue to discuss your proposal
3. **Sync your fork**: Ensure your fork is up to date with upstream

```bash
git fetch upstream
git checkout main
git merge upstream/main
```

---

## Pull Request Process

### Creating a Pull Request

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # Or for bug fixes:
   git checkout -b fix/issue-description
   ```

2. **Make your changes**: Follow the coding standards below

3. **Run quality checks**:
   ```bash
   make check    # Runs lint, format check, and typecheck
   make test     # Runs all tests
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: Add your feature description"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/) format:
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation changes
   - `style:` Code style changes (formatting)
   - `refactor:` Code refactoring
   - `test:` Test additions or changes
   - `chore:` Maintenance tasks

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request**: Go to GitHub and create a PR against the `main` branch

### Pull Request Checklist

Before submitting your PR, ensure:

- [ ] Code follows the project's style guide
- [ ] All tests pass (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make typecheck`)
- [ ] New code has appropriate test coverage
- [ ] Documentation is updated if needed
- [ ] Commit messages follow conventional commits format
- [ ] PR description clearly explains the changes

### Review Process

1. A maintainer will review your PR
2. Address any requested changes
3. Once approved, a maintainer will merge your PR

---

## Coding Standards

### Code Style

We use the following tools for code quality:

- **Black**: Code formatting (line length: 88)
- **Ruff**: Linting and import sorting
- **Mypy**: Static type checking

### Key Requirements

1. **Type Hints**: All functions must have type hints
   ```python
   def classify(response: str) -> Decision:
       ...
   ```

2. **Docstrings**: All public functions need Google-style docstrings
   ```python
   def run_prompt(prompt: str, model: str = "llama3") -> str:
       """
       Execute a prompt using Ollama CLI.

       Args:
           prompt: The prompt to send to Ollama.
           model: Model name to use. Defaults to "llama3".

       Returns:
           Response text from Ollama.

       Raises:
           OllamaError: After MAX_RETRIES failed attempts.
       """
   ```

3. **Naming Conventions**:
   - `snake_case` for functions and variables
   - `PascalCase` for classes
   - `SCREAMING_SNAKE_CASE` for constants

4. **Import Order** (handled by Ruff):
   1. Standard library
   2. Third-party packages
   3. Local modules

For complete details, see [docs/style-guide.md](docs/style-guide.md).

---

## Testing Guidelines

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Run specific test file
pytest tests/test_classifier.py -v

# Run specific test category
pytest -m "security" -v      # Security tests
pytest -m "integration" -v   # Integration tests
pytest -m "not slow" -v      # Skip slow tests
```

### Writing Tests

1. **File naming**: `test_<module>.py`
2. **Function naming**: `test_<function>_<scenario>`
3. **Use AAA pattern**: Arrange, Act, Assert

```python
def test_classify_dangerous_keyword_returns_user():
    # Arrange
    response = '{"action": "deploy", "reason": "Deploy code"}'

    # Act
    result = classify(response)

    # Assert
    assert result.action == "user"
    assert "dangerous" in result.reason.lower()
```

### Test Categories

Use pytest markers for test categorization:

- `@pytest.mark.slow`: Long-running tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.security`: Security-related tests
- `@pytest.mark.regression`: Critical functionality tests

---

## Documentation

### When to Update Documentation

Update documentation when you:

- Add new features
- Change existing functionality
- Modify configuration options
- Update CLI commands
- Fix bugs that users should know about

### Documentation Locations

- **README.md**: Quick start and overview
- **docs/**: Detailed documentation
  - `api-reference.md`: API documentation
  - `FAQ.md`: Common questions
  - `troubleshooting.md`: Issue solutions
- **Docstrings**: In-code documentation

### Documentation Style

- Use clear, concise language
- Include code examples where helpful
- Keep formatting consistent with existing docs

---

## Issue Reporting

### Bug Reports

When reporting bugs, include:

1. **Description**: Clear summary of the issue
2. **Steps to Reproduce**: Detailed steps to recreate the bug
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: OS, Python version, Ollama version
6. **Logs**: Relevant log output (remove sensitive info)

### Feature Requests

For feature requests, describe:

1. **Problem**: The problem you're trying to solve
2. **Proposed Solution**: Your suggested approach
3. **Alternatives**: Other solutions you considered
4. **Additional Context**: Screenshots, examples, etc.

---

## Community Guidelines

### Be Respectful

- Treat all contributors with respect
- Provide constructive feedback
- Be patient with new contributors
- Welcome diverse perspectives

### Communication

- Use clear and professional language
- Stay on topic in discussions
- Ask questions if something is unclear

### Getting Help

If you need help:

1. Check the [FAQ](docs/FAQ.md)
2. Search existing issues
3. Open a new issue with the "question" label

---

## Recognition

Contributors are valued members of our community. Significant contributions may be recognized in:

- The project's contributors list
- Release notes for specific features

Thank you for contributing to the Ollama Automation Harness!
