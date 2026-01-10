# API Reference

This document provides comprehensive documentation for the Ollama Automation Harness APIs, including internal Python modules and external service integrations.

---

## Table of Contents

1. [Overview](#overview)
2. [Core APIs](#core-apis)
   - [Claude Module](#claude-module)
   - [Ollama Module](#ollama-module)
   - [Classifier Module](#classifier-module)
   - [Executor Module](#executor-module)
   - [Safety Module](#safety-module)
3. [Utility APIs](#utility-apis)
   - [Configuration](#configuration)
   - [Validation](#validation)
   - [Logging](#logging)
4. [CLI Interface](#cli-interface)
5. [Data Types](#data-types)
6. [Error Codes](#error-codes)
7. [External APIs](#external-apis)

---

## Overview

The Ollama Automation Harness is a Python CLI application that orchestrates AI-powered development workflows with human oversight. It provides a layered API structure:

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Interface (cli.py)                    │
├─────────────────────────────────────────────────────────────┤
│                   Main Loop (main.py)                        │
├─────────────────────────────────────────────────────────────┤
│    Core APIs: claude | ollama | classifier | executor       │
├─────────────────────────────────────────────────────────────┤
│    Utility APIs: config | validation | logger | safety      │
├─────────────────────────────────────────────────────────────┤
│              External: Anthropic API | Ollama CLI            │
└─────────────────────────────────────────────────────────────┘
```

---

## Core APIs

### Claude Module

**Module:** `core.claude`

Provides AI response generation via Claude API with Ollama fallback.

#### `get_response()`

Get a response from Claude (API or fallback).

```python
def get_response(prompt: str, use_api: bool | None = None) -> str
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `prompt` | `str` | Yes | The prompt to send to the AI model |
| `use_api` | `bool \| None` | No | Force API usage (True), fallback (False), or auto-detect (None) |

**Returns:**
- `str` - Response text from Claude or Ollama fallback

**Raises:**
- `ClaudeError` - If API call fails or authentication error

**Example:**
```python
from core.claude import get_response

# Auto-detect mode (uses API if key available)
response = get_response("Write a Python function to calculate factorial")

# Force API mode
response = get_response("Generate code", use_api=True)

# Force fallback mode
response = get_response("Generate code", use_api=False)
```

---

#### `check_api_available()`

Check if Claude API is configured.

```python
def check_api_available() -> bool
```

**Returns:**
- `bool` - True if ANTHROPIC_API_KEY is set

---

#### `get_model_info()`

Get current model configuration information.

```python
def get_model_info() -> dict[str, str]
```

**Returns:**
```python
{
    "mode": "api" | "fallback",
    "model": "claude-sonnet-4-20250514" | "llama3",
    "max_tokens": "4096",
    "api_key_set": "yes" | "no"
}
```

---

### Ollama Module

**Module:** `core.ollama`

Provides local LLM inference via Ollama CLI subprocess.

#### `run_prompt()`

Execute a prompt using Ollama CLI.

```python
def run_prompt(prompt: str, model: str = OLLAMA_MODEL) -> str
```

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `prompt` | `str` | Yes | - | The prompt to send |
| `model` | `str` | No | `"llama3"` | Model name |

**Returns:**
- `str` - Response text from Ollama

**Raises:**
- `OllamaError` - After MAX_RETRIES (3) failed attempts

**Retry Behavior:**
- Maximum retries: 3
- Retry delay: 1.0 second
- Timeout: 60 seconds per attempt

**Example:**
```python
from core.ollama import run_prompt

response = run_prompt("Explain Python decorators")
response = run_prompt("Code review this", model="codellama")
```

---

#### `check_ollama_available()`

Check if Ollama is installed and running.

```python
def check_ollama_available() -> bool
```

**Returns:**
- `bool` - True if Ollama is available

---

#### `list_models()`

List available Ollama models.

```python
def list_models() -> list[str]
```

**Returns:**
- `list[str]` - List of model names

**Raises:**
- `OllamaError` - If unable to list models

---

### Classifier Module

**Module:** `core.classifier`

Parses AI responses and classifies them into actionable decisions.

#### `classify()`

Classify a Claude response into an action decision.

```python
def classify(response: str) -> Decision
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `response` | `str` | Yes | Raw response from Claude/AI |

**Returns:**
- `Decision` - Decision object with action, reason, command, risk_level

**Classification Rules:**
- **"auto"**: Safe operations (tests, code generation, sandbox writes)
- **"user"**: Dangerous operations (deploy, git push, system changes)
- **"high" risk**: deploy, production, push, sudo, rm -rf, chmod, chown

**Example:**
```python
from core.classifier import classify

decision = classify("Run pytest to test the code: ```bash\npytest tests/\n```")
# Decision(action="auto", reason="Safe test operation",
#          command="pytest tests/", risk_level="low")
```

---

#### `parse_json_response()`

Parse JSON from AI response text.

```python
def parse_json_response(response: str) -> dict | None
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `response` | `str` | Yes | Response text that may contain JSON |

**Returns:**
- `dict | None` - Parsed dictionary or None if parsing fails

**Parsing Strategy:**
1. Direct JSON parse
2. Search for `{...}` pattern
3. Search for JSON in code blocks

---

#### `extract_command()`

Extract shell command from AI response.

```python
def extract_command(response: str) -> str | None
```

**Returns:**
- `str | None` - Extracted command or None

**Detection Patterns:**
- Shell code blocks: ` ```bash ... ``` `
- Inline commands: `$ command`
- Run patterns: `run: command`, `execute: command`

---

### Executor Module

**Module:** `core.executor`

Provides sandboxed command execution with security controls.

#### `execute()`

Execute a command in the sandbox environment.

```python
def execute(command: str, sandbox_root: str = SANDBOX_DIR) -> ExecutionResult
```

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `command` | `str` | Yes | - | Shell command to execute |
| `sandbox_root` | `str` | No | `"./sandbox"` | Root directory for sandboxed execution |

**Returns:**
- `ExecutionResult` - Result with success, output, error, return_code

**Security Features:**
- Command validation
- Sandbox directory restriction
- Timeout enforcement (30 seconds)
- Safe environment variables only

**Example:**
```python
from core.executor import execute

result = execute("pytest tests/unit/")
if result.success:
    print(result.output)
else:
    print(f"Error: {result.error}")
```

---

#### `execute_sandboxed()`

Execute command with list arguments (shell=False for safety).

```python
def execute_sandboxed(
    command: list[str],
    sandbox_root: str = SANDBOX_DIR
) -> ExecutionResult
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `command` | `list[str]` | Yes | Command as list of arguments |
| `sandbox_root` | `str` | No | Root directory for sandbox |

**Example:**
```python
result = execute_sandboxed(["python", "script.py", "--arg", "value"])
```

---

#### `write_file_sandboxed()`

Write file within sandbox with validation.

```python
def write_file_sandboxed(
    path: str,
    content: str,
    sandbox_root: str = SANDBOX_DIR
) -> ExecutionResult
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `str` | Yes | Relative path within sandbox |
| `content` | `str` | Yes | Content to write |
| `sandbox_root` | `str` | No | Root directory for sandbox |

**Validation:**
- Path must resolve within sandbox
- Extension must be in allowed list: `.py`, `.txt`, `.json`, `.yaml`, `.md`, `.sh`

---

#### `read_file_sandboxed()`

Read file within sandbox with validation.

```python
def read_file_sandboxed(
    path: str,
    sandbox_root: str = SANDBOX_DIR
) -> ExecutionResult
```

**Returns:**
- `ExecutionResult` with file content in `output` field

---

#### `validate_sandbox_path()`

Validate that path stays within sandbox.

```python
def validate_sandbox_path(path: str, sandbox_root: str = SANDBOX_DIR) -> bool
```

**Returns:**
- `bool` - True if path is valid and within sandbox

---

### Safety Module

**Module:** `core.safety`

Permission management and policy enforcement.

#### `PermissionManager` Class

```python
class PermissionManager:
    def __init__(self, config_path: str = CONFIG_PATH) -> None
    def check_permission(self, action_type: str) -> str
    def enforce(self, decision: Decision) -> Decision
    def validate_path(self, path: str, sandbox_root: str = "./sandbox") -> bool
```

**Methods:**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `check_permission` | `action_type: str` | `str` | Get permission level for action type |
| `enforce` | `decision: Decision` | `Decision` | Override decision based on policy |
| `validate_path` | `path: str, sandbox_root: str` | `bool` | Check path validity |

**Permission Levels:**
- `"auto"` - Execute without user intervention
- `"ask"` - Require user confirmation
- `"deny"` - Block entirely

**Example:**
```python
from core.safety import PermissionManager
from core.classifier import Decision

manager = PermissionManager()

# Check permission for an action type
permission = manager.check_permission("git_push")  # Returns "ask"

# Enforce policy on a decision
decision = Decision(action="auto", reason="...", command="git push", risk_level="low")
enforced = manager.enforce(decision)
# Decision modified to action="user" due to git_push policy
```

---

#### `load_permissions()`

Load permissions from YAML configuration.

```python
def load_permissions(path: str = CONFIG_PATH) -> dict[str, Any]
```

**Returns:**
```python
{
    "actions": {
        "read_file": "auto",
        "write_file": "ask",
        "git_push": "ask",
        "deploy": "deny"
    },
    "default": "ask",
    "dangerous_keywords": ["deploy", "production", "sudo"],
    "sandbox": {
        "root": "./sandbox",
        "allowed_extensions": [".py", ".txt", ".json"]
    }
}
```

---

#### `get_permission()`

Get permission level for an action type.

```python
def get_permission(action_type: str) -> str
```

---

#### `check_action()`

Check permission level for a classified action.

```python
def check_action(decision: Decision) -> str
```

**Returns:**
- `str` - "auto" or "ask"

---

## Utility APIs

### Configuration

**Module:** `utils.config`

#### Constants

| Constant | Type | Default | Description |
|----------|------|---------|-------------|
| `SANDBOX_DIR` | `str` | `"./sandbox"` | Sandbox directory path |
| `PERMISSIONS_FILE` | `str` | `"./config/permissions.yaml"` | Permissions config path |
| `LOG_FILE` | `str` | `"./logs/automation.log"` | Log file path |
| `OLLAMA_MODEL` | `str` | `"llama3"` | Default Ollama model |
| `CLAUDE_MODEL` | `str` | `"claude-sonnet-4-20250514"` | Claude model |
| `CLAUDE_MAX_TOKENS` | `int` | `4096` | Max tokens for Claude |
| `OLLAMA_TIMEOUT` | `int` | `60` | Ollama timeout (seconds) |
| `COMMAND_TIMEOUT` | `int` | `30` | Command timeout (seconds) |
| `MAX_RETRIES` | `int` | `3` | Max retry attempts |
| `RETRY_DELAY` | `float` | `1.0` | Delay between retries |
| `MAX_REPLY_LENGTH` | `int` | `2000` | Max display length |

#### `get_config_dict()`

Get all configuration as dictionary.

```python
def get_config_dict() -> dict[str, Any]
```

#### `is_dangerous_keyword()`

Check if text contains dangerous keywords.

```python
def is_dangerous_keyword(text: str) -> bool
```

#### `is_allowed_extension()`

Check if file extension is allowed.

```python
def is_allowed_extension(path: str) -> bool
```

---

### Validation

**Module:** `utils.validation`

#### Validation Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `validate_prompt` | `prompt: str` | `str` | Validate prompt (max 10,000 chars) |
| `validate_command` | `command: str` | `str` | Validate command (max 1,000 chars) |
| `validate_response` | `response: str` | `str` | Validate AI response |
| `validate_path` | `path: str, sandbox_root: str` | `str` | Validate file path |
| `validate_risk_level` | `level: str` | `str` | Validate risk level |
| `sanitize_string` | `text: str, allow_newlines: bool` | `str` | Sanitize input string |
| `contains_path_traversal` | `path: str` | `bool` | Check for `../` patterns |

**Raises:**
- `ValidationError` - If validation fails

---

### Logging

**Module:** `utils.logger`

#### `setup_logger()`

Configure the application logger.

```python
def setup_logger(
    log_file: str = LOG_FILE,
    level: int = logging.INFO,
    enable_console: bool = True,
    enable_json: bool = False,
    enable_rotation: bool = True
) -> logging.Logger
```

#### `log_action()`

Log an automation action.

```python
def log_action(
    action_type: str,
    decision: Decision,
    result: ExecutionResult
) -> None
```

**Log Format:**
```
[2024-01-15T10:30:00] ACTION=execute DECISION=auto RISK=low COMMAND="pytest tests/" RESULT=success
```

#### `log_error()`

Log an error with context.

```python
def log_error(error: Exception, operation: str) -> None
```

#### `log_user_decision()`

Log user confirmation decision.

```python
def log_user_decision(decision: Decision, user_choice: str) -> None
```

---

## CLI Interface

**Module:** `cli`

### Commands

#### `run` - Start Automation

```bash
ollama-harness run [OPTIONS]
```

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--prompt` | `-p` | TEXT | Initial prompt to process |
| `--file` | `-f` | PATH | Read prompt from file |
| `--config` | | PATH | Path to permissions config |
| `--sandbox` | | PATH | Path to sandbox directory |
| `--env` | `-e` | CHOICE | Environment (development/staging/production/testing) |
| `--verbose` | `-v` | FLAG | Enable verbose output |
| `--quiet` | `-q` | FLAG | Suppress non-essential output |
| `--dry-run` | | FLAG | Show without executing |
| `--no-confirm` | | FLAG | Auto-approve low-risk actions |
| `--model` | | NAME | Override AI model |
| `--timeout` | | INT | Command timeout in seconds |

**Examples:**
```bash
# Interactive mode
ollama-harness run

# Single prompt
ollama-harness run -p "Create a unit test for auth.py"

# From file with custom config
ollama-harness run -f prompt.txt --config custom-permissions.yaml
```

---

#### `config` - Configuration Management

```bash
ollama-harness config <subcommand>
```

| Subcommand | Description |
|------------|-------------|
| `show` | Display current configuration (secrets masked) |
| `validate` | Check configuration for errors |
| `init [--force]` | Initialize default configuration files |
| `path` | Show configuration file paths |

---

#### `check` - System Health

```bash
ollama-harness check [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--fix` | Attempt to fix issues automatically |
| `--verbose` | Show detailed check results |

**Checks Performed:**
- Python version (requires 3.10+)
- Ollama installation
- Required directories (sandbox, logs, config)
- Required packages (anthropic, PyYAML, python-dotenv)
- Configuration files

---

#### `version` - Version Information

```bash
ollama-harness version
```

Displays:
- Application version
- Python version
- Platform information
- AI model configuration

---

#### `metrics` - Application Metrics

```bash
ollama-harness metrics [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--format` | Output format: text, json, prometheus |
| `--save FILE` | Save metrics to file |

---

#### `status` - Health Status

```bash
ollama-harness status [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--format` | Output format: text, json |
| `--watch` | Continuously watch (refresh every 5s) |

---

## Data Types

### Decision

```python
@dataclass
class Decision:
    action: str        # "auto" | "user"
    reason: str        # Explanation for the decision
    command: str | None  # Command to execute
    risk_level: str    # "low" | "medium" | "high"
```

### ExecutionResult

```python
@dataclass
class ExecutionResult:
    success: bool      # Whether execution succeeded
    output: str        # stdout content
    error: str         # stderr content
    return_code: int   # Process return code
```

---

## Error Codes

**Module:** `utils.errors`

| Code | Name | Description |
|------|------|-------------|
| `1000` | `UNKNOWN` | Unknown error |
| `1001` | `CONFIGURATION` | Configuration error |
| `1002` | `VALIDATION` | Validation error |
| `2001` | `OLLAMA_ERROR` | General Ollama error |
| `2002` | `OLLAMA_TIMEOUT` | Ollama timeout |
| `2003` | `OLLAMA_NOT_FOUND` | Ollama not installed |
| `2011` | `CLAUDE_ERROR` | General Claude error |
| `2012` | `CLAUDE_API_ERROR` | Claude API error |
| `2013` | `CLAUDE_AUTH_ERROR` | Claude authentication error |
| `3001` | `EXECUTION_ERROR` | Command execution error |
| `3002` | `SANDBOX_VIOLATION` | Sandbox path violation |
| `3003` | `PERMISSION_DENIED` | Permission denied |

### Exception Hierarchy

```
HarnessError (Base)
├── ServiceError
│   ├── ClaudeError
│   └── OllamaError
├── ValidationError
└── ConfigError
```

---

## External APIs

### Anthropic Claude API

**Base URL:** `https://api.anthropic.com/v1`

**Authentication:** Bearer token via `ANTHROPIC_API_KEY` environment variable

#### Messages Endpoint

```
POST /messages
```

**Request:**
```json
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 4096,
  "messages": [
    {
      "role": "user",
      "content": "Your prompt here"
    }
  ]
}
```

**Response:**
```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Response text..."
    }
  ],
  "model": "claude-sonnet-4-20250514",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 100,
    "output_tokens": 500
  }
}
```

**SDK Usage:**
```python
from anthropic import Anthropic

client = Anthropic()  # Uses ANTHROPIC_API_KEY env var

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=[{"role": "user", "content": "Hello!"}]
)

print(message.content[0].text)
```

---

### Ollama CLI

**Local inference via subprocess**

#### Run Command

```bash
ollama run <model> [prompt]
```

**Usage in Application:**
```python
import subprocess

result = subprocess.run(
    ["ollama", "run", "llama3"],
    input="Your prompt here",
    capture_output=True,
    text=True,
    timeout=60
)

response = result.stdout.strip()
```

#### List Models

```bash
ollama list
```

**Output:**
```
NAME              ID            SIZE    MODIFIED
llama3:latest     abc123...     4.7 GB  2 days ago
codellama:latest  def456...     3.8 GB  1 week ago
```

---

## Configuration Schema

### permissions.yaml

```yaml
# Permission levels: auto, ask, deny
actions:
  read_file: auto      # Read operations - automatic
  write_file: ask      # Write operations - require confirmation
  delete_file: ask     # Delete operations - require confirmation
  run_tests: auto      # Test execution - automatic
  lint_code: auto      # Linting - automatic
  format_code: auto    # Formatting - automatic
  git_status: auto     # Git status - automatic
  git_diff: auto       # Git diff - automatic
  git_add: ask         # Git staging - require confirmation
  git_commit: ask      # Git commit - require confirmation
  git_push: ask        # Git push - require confirmation
  git_pull: ask        # Git pull - require confirmation
  deploy: deny         # Deployment - blocked
  deploy_production: deny
  system_command: deny
  install_package: ask

# Default for unknown action types
default: ask

# Keywords that always require user approval (overrides action settings)
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

# Risk level thresholds
risk_thresholds:
  auto: low
  ask: medium
  deny: high

# Sandbox configuration
sandbox:
  root: ./sandbox
  allowed_extensions:
    - .py
    - .txt
    - .json
    - .yaml
    - .yml
    - .md
    - .sh
```

### Environment Variables (.env)

```bash
# Environment
ENVIRONMENT=development    # development | staging | production | testing
DEBUG=false

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
SENTRY_DSN=               # Optional: Error tracking

# Models
OLLAMA_MODEL=llama3
CLAUDE_MODEL=claude-sonnet-4-20250514
CLAUDE_MAX_TOKENS=4096

# Paths
SANDBOX_DIR=./sandbox
PERMISSIONS_FILE=./config/permissions.yaml
LOG_FILE=./logs/automation.log

# Timeouts (seconds)
OLLAMA_TIMEOUT=60
COMMAND_TIMEOUT=30
OLLAMA_CHECK_TIMEOUT=5

# Retry settings
MAX_RETRIES=3
RETRY_DELAY=1.0

# Display
LOOP_DELAY=1.0
MAX_REPLY_LENGTH=2000
```

---

## Rate Limits & Quotas

### Claude API

| Tier | RPM | TPM |
|------|-----|-----|
| Free | 5 | 20,000 |
| Build | 50 | 40,000 |
| Scale | 1,000 | 400,000 |

### Ollama (Local)

No rate limits (limited by hardware)

---

## Security Considerations

1. **API Key Protection**: Store `ANTHROPIC_API_KEY` in `.env` file (git-ignored)
2. **Sandbox Enforcement**: All file operations restricted to sandbox directory
3. **Path Traversal Prevention**: `../` patterns are blocked
4. **Extension Whitelist**: Only safe file types allowed
5. **Dangerous Keyword Detection**: Commands containing risky keywords require approval
6. **Timeout Enforcement**: Prevents runaway processes
7. **Audit Logging**: All actions logged with full context

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-01-15 | Initial release |

---

*Last updated: 2024-01-15*
