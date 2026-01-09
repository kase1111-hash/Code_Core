# Coding Conventions & Style Guide

## Overview

This document defines the coding standards for the Ollama Automation Harness project. All contributors must follow these conventions to maintain code consistency and quality.

---

## Code Formatting

### Formatter: Black

- **Line length:** 88 characters (Black default)
- **Quote style:** Double quotes `"string"`
- **Trailing commas:** Yes, for multi-line structures

```python
# Good
result = {
    "action": "auto",
    "reason": "Safe operation",
    "command": "pytest tests/",
}

# Bad
result = {'action': 'auto', 'reason': 'Safe operation', 'command': 'pytest tests/'}
```

### Indentation

- **Spaces:** 4 spaces per level (no tabs)
- **Continuation:** Align with opening delimiter or use hanging indent

```python
# Good - aligned with delimiter
def long_function(argument_one, argument_two,
                  argument_three, argument_four):
    pass

# Good - hanging indent
def long_function(
    argument_one,
    argument_two,
    argument_three,
):
    pass
```

---

## Linting: Ruff

### Enabled Rules

```toml
[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # Pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "S",    # flake8-bandit (security)
]
```

### Import Order (isort)

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Standard library
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Third-party
import yaml
from anthropic import Anthropic

# Local
from core.classifier import Decision
from utils.logger import log_action
```

---

## Type Hints

### Requirements

- **All functions** must have type hints for parameters and return values
- **All class attributes** must be typed
- **Use `Optional[T]`** for nullable values
- **Use `Union[A, B]`** sparingly; prefer specific types

```python
# Good
def run_prompt(prompt: str, model: str = "llama3") -> str:
    ...

def classify(response: str) -> Decision:
    ...

def execute(command: str) -> Optional[ExecutionResult]:
    ...

# Bad - missing type hints
def run_prompt(prompt, model="llama3"):
    ...
```

### Common Type Patterns

```python
from typing import Dict, List, Optional, Tuple, Union

# Dictionaries
config: Dict[str, str]
permissions: Dict[str, Dict[str, str]]

# Lists
commands: List[str]
results: List[ExecutionResult]

# Optional (can be None)
error: Optional[str] = None

# Tuples
coordinates: Tuple[int, int]
```

---

## Naming Conventions

### Variables and Functions

- **snake_case** for variables and functions
- **Descriptive names** that indicate purpose

```python
# Good
user_prompt = "Write tests"
execution_result = execute(command)
is_dangerous = check_dangerous_keywords(cmd)

# Bad
up = "Write tests"
er = execute(command)
x = check_dangerous_keywords(cmd)
```

### Classes

- **PascalCase** for class names
- **Noun phrases** describing the entity

```python
# Good
class Decision:
    pass

class ExecutionResult:
    pass

class OllamaError(Exception):
    pass

# Bad
class decision:
    pass

class execution_result:
    pass
```

### Constants

- **SCREAMING_SNAKE_CASE** for constants
- Define at module level

```python
# Good
DEFAULT_MODEL = "llama3"
MAX_RETRIES = 3
TIMEOUT = 60
DANGEROUS_KEYWORDS = ["deploy", "sudo", "rm -rf"]

# Bad
defaultModel = "llama3"
max_retries = 3
```

### Private Members

- **Single underscore prefix** for internal use
- **Double underscore** only for name mangling (rare)

```python
# Good
def _parse_json(response: str) -> dict:
    """Internal helper function."""
    pass

def _validate_path(path: str) -> bool:
    """Internal validation."""
    pass

# Public API
def classify(response: str) -> Decision:
    """Public function."""
    pass
```

---

## Documentation

### Docstrings

- **All public functions** must have docstrings
- **Google style** format
- Include: description, Args, Returns, Raises

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
    pass
```

### Comments

- **Explain why**, not what
- Keep comments up-to-date with code
- Use `# TODO:` for planned work

```python
# Good - explains why
# Retry on timeout because Ollama may be loading the model
for attempt in range(MAX_RETRIES):
    ...

# Bad - explains what (obvious from code)
# Loop three times
for attempt in range(3):
    ...
```

---

## Error Handling

### Custom Exceptions

- Inherit from appropriate base class
- Use descriptive names ending in `Error`

```python
class OllamaError(Exception):
    """Raised when Ollama command fails after all retries."""
    pass

class SandboxError(Exception):
    """Raised when sandbox validation fails."""
    pass
```

### Exception Handling

- Catch specific exceptions, not bare `except:`
- Log errors with context
- Re-raise or handle appropriately

```python
# Good
try:
    result = subprocess.run(cmd, timeout=TIMEOUT)
except subprocess.TimeoutExpired:
    log_error(e, "Command timed out")
    return ExecutionResult(success=False, error="Timeout")
except subprocess.SubprocessError as e:
    log_error(e, "Subprocess failed")
    raise OllamaError(f"Command failed: {e}")

# Bad
try:
    result = subprocess.run(cmd, timeout=TIMEOUT)
except:
    pass
```

---

## Dataclasses

### Use for Data Structures

```python
from dataclasses import dataclass

@dataclass
class Decision:
    """Represents a classified action decision."""

    action: str      # "auto" | "user"
    reason: str      # Explanation
    command: str     # Command to execute
    risk_level: str  # "low" | "medium" | "high"


@dataclass
class ExecutionResult:
    """Represents command execution result."""

    success: bool
    output: str
    error: str
    return_code: int
```

---

## Testing

### Test File Naming

- `test_<module>.py` for each module
- Located in `tests/` directory

```
tests/
├── __init__.py
├── test_ollama.py
├── test_claude.py
├── test_classifier.py
├── test_executor.py
└── test_safety.py
```

### Test Function Naming

- `test_<function>_<scenario>`
- Descriptive names

```python
def test_classify_safe_command_returns_auto():
    ...

def test_classify_dangerous_keyword_returns_user():
    ...

def test_execute_path_traversal_blocked():
    ...
```

### Test Structure (AAA Pattern)

```python
def test_run_prompt_success():
    # Arrange
    prompt = "Hello, world"
    expected = "Response text"

    # Act
    result = run_prompt(prompt)

    # Assert
    assert result == expected
```

---

## Security

### Never Commit Secrets

- Use `.env` for secrets
- Check `.gitignore` includes sensitive files
- Use environment variables in code

```python
# Good
api_key = os.getenv("ANTHROPIC_API_KEY")

# Bad
api_key = "sk-ant-xxxxx"
```

### Input Validation

- Validate all external input
- Use allowlists over denylists
- Sanitize paths and commands

```python
# Good - allowlist
ALLOWED_EXTENSIONS = [".py", ".txt", ".json", ".yaml", ".md", ".sh"]

def is_allowed(path: str) -> bool:
    return Path(path).suffix in ALLOWED_EXTENSIONS

# Bad - denylist (incomplete)
BLOCKED_EXTENSIONS = [".exe", ".sh"]
```

---

## Git Commits

### Commit Message Format

```
<type>: <short description>

<optional body explaining why>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

### Examples

```
feat: Add retry logic to Ollama module

Ollama may timeout while loading models. Added 3 retries
with exponential backoff to handle transient failures.
```

```
fix: Block path traversal in executor

Paths containing ".." were not properly validated,
allowing writes outside the sandbox directory.
```

---

## Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.2.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-PyYAML]
```

---

## Summary Checklist

- [ ] Code formatted with Black
- [ ] Linting passes (Ruff)
- [ ] Type hints on all functions
- [ ] Docstrings on public functions
- [ ] Tests written for new code
- [ ] No secrets in code
- [ ] Commit message follows format
