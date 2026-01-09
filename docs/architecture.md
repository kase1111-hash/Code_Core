# System Architecture

## Overview

The Ollama Automation Harness is a CLI application that orchestrates AI-powered development workflows with human oversight. It combines Claude's code generation capabilities with Ollama's local classification to provide safe, auditable automation.

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER (CLI)                                  │
│                         stdin / stdout / stderr                          │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                             MAIN LOOP                                    │
│                           (main.py)                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Prompt    │→ │   Claude    │→ │  Classify   │→ │   Execute   │    │
│  │   Input     │  │   Response  │  │   Action    │  │  or Ask     │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────────┐
          │                           │                               │
          ▼                           ▼                               ▼
┌─────────────────┐       ┌─────────────────┐           ┌─────────────────┐
│   core/claude   │       │ core/classifier │           │  core/executor  │
│                 │       │                 │           │                 │
│ - get_response()│       │ - classify()    │           │ - execute()     │
│ - API/Fallback  │       │ - Decision      │           │ - sandbox ops   │
└────────┬────────┘       └────────┬────────┘           └────────┬────────┘
         │                         │                              │
         ▼                         ▼                              ▼
┌─────────────────┐       ┌─────────────────┐           ┌─────────────────┐
│  Anthropic API  │       │  core/ollama    │           │  core/safety    │
│  (Remote)       │       │                 │           │                 │
│                 │       │ - run_prompt()  │           │ - permissions   │
│  claude-sonnet  │       │ - retry logic   │           │ - path checks   │
└─────────────────┘       └────────┬────────┘           └────────┬────────┘
                                   │                              │
                                   ▼                              ▼
                          ┌─────────────────┐           ┌─────────────────┐
                          │  Ollama CLI     │           │  config/        │
                          │  (Local)        │           │  permissions.yml│
                          │                 │           │                 │
                          │  llama3 model   │           │  YAML rules     │
                          └─────────────────┘           └─────────────────┘

                                      │
                                      ▼
                          ┌─────────────────────────────────────┐
                          │           utils/logger              │
                          │                                     │
                          │  logs/automation.log                │
                          │  [timestamp] ACTION DECISION RESULT │
                          └─────────────────────────────────────┘
```

---

## Component Architecture

### 1. Main Loop (`main.py`)

**Responsibility:** Orchestrate the automation workflow

```
┌────────────────────────────────────────────────────────────┐
│                        main.py                              │
├────────────────────────────────────────────────────────────┤
│ Functions:                                                  │
│   main() → None                                            │
│   process_iteration(prompt: str) → str | None              │
│   handle_user_action(decision: Decision) → str | None      │
│   display_response(response: str) → None                   │
├────────────────────────────────────────────────────────────┤
│ Flow:                                                       │
│   1. Parse CLI arguments                                   │
│   2. Initialize logger                                     │
│   3. Get initial prompt                                    │
│   4. Loop:                                                 │
│      a. Get Claude response                                │
│      b. Classify action                                    │
│      c. Execute (auto) or prompt (user)                    │
│      d. Log result                                         │
│      e. Continue or exit                                   │
└────────────────────────────────────────────────────────────┘
```

### 2. Ollama Module (`core/ollama.py`)

**Responsibility:** Execute local LLM inference via Ollama CLI

```
┌────────────────────────────────────────────────────────────┐
│                     core/ollama.py                          │
├────────────────────────────────────────────────────────────┤
│ Classes:                                                    │
│   OllamaError(Exception)                                   │
│                                                            │
│ Functions:                                                  │
│   run_prompt(prompt: str, model: str = "llama3") → str     │
│                                                            │
│ Constants:                                                  │
│   DEFAULT_MODEL = "llama3"                                 │
│   TIMEOUT = 60                                             │
│   MAX_RETRIES = 3                                          │
├────────────────────────────────────────────────────────────┤
│ Behavior:                                                   │
│   - Spawns subprocess: ollama run <model> "<prompt>"       │
│   - Captures stdout, returns response                      │
│   - Retries on failure (up to 3 times)                     │
│   - Raises OllamaError after all retries fail              │
└────────────────────────────────────────────────────────────┘
```

### 3. Claude Module (`core/claude.py`)

**Responsibility:** Get AI responses for code generation

```
┌────────────────────────────────────────────────────────────┐
│                     core/claude.py                          │
├────────────────────────────────────────────────────────────┤
│ Functions:                                                  │
│   get_response(prompt: str) → str                          │
│   _call_api(prompt: str) → str                             │
│   _fallback_ollama(prompt: str) → str                      │
│                                                            │
│ Constants:                                                  │
│   MODEL = "claude-sonnet-4-20250514"                       │
│   MAX_TOKENS = 4096                                        │
├────────────────────────────────────────────────────────────┤
│ Behavior:                                                   │
│   - Check for ANTHROPIC_API_KEY                            │
│   - If present: call Claude API                            │
│   - If missing: fall back to Ollama simulation             │
│   - Return response as string                              │
└────────────────────────────────────────────────────────────┘
```

### 4. Classifier Module (`core/classifier.py`)

**Responsibility:** Parse responses and classify actions

```
┌────────────────────────────────────────────────────────────┐
│                   core/classifier.py                        │
├────────────────────────────────────────────────────────────┤
│ Dataclasses:                                                │
│   @dataclass                                               │
│   Decision:                                                │
│     action: str        # "auto" | "user"                   │
│     reason: str        # Explanation                       │
│     command: str       # Command to execute                │
│     risk_level: str    # "low" | "medium" | "high"         │
│                                                            │
│ Functions:                                                  │
│   classify(response: str) → Decision                       │
│   _parse_json(response: str) → dict                        │
│   _check_dangerous_keywords(command: str) → bool           │
│                                                            │
│ Constants:                                                  │
│   DANGEROUS_KEYWORDS = ["deploy", "production", "push",    │
│                         "sudo", "rm -rf", "chmod"]         │
├────────────────────────────────────────────────────────────┤
│ Behavior:                                                   │
│   - Parse Claude's JSON output                             │
│   - Check for dangerous keywords → force "user"            │
│   - Apply Ollama classification                            │
│   - Return Decision object                                 │
│   - Default to user action on parse errors                 │
└────────────────────────────────────────────────────────────┘
```

### 5. Executor Module (`core/executor.py`)

**Responsibility:** Safely execute commands in sandbox

```
┌────────────────────────────────────────────────────────────┐
│                    core/executor.py                         │
├────────────────────────────────────────────────────────────┤
│ Dataclasses:                                                │
│   @dataclass                                               │
│   ExecutionResult:                                         │
│     success: bool                                          │
│     output: str                                            │
│     error: str                                             │
│     return_code: int                                       │
│                                                            │
│ Functions:                                                  │
│   execute(command: str) → ExecutionResult                  │
│   _validate_path(path: str) → bool                         │
│   _is_allowed_extension(path: str) → bool                  │
│                                                            │
│ Constants:                                                  │
│   SANDBOX_DIR = "./sandbox"                                │
│   TIMEOUT = 30                                             │
│   ALLOWED_EXTENSIONS = [".py", ".txt", ".json",            │
│                         ".yaml", ".md", ".sh"]             │
├────────────────────────────────────────────────────────────┤
│ Behavior:                                                   │
│   - Validate all paths stay within sandbox                 │
│   - Block path traversal (../)                             │
│   - Check file extension whitelist                         │
│   - Execute with timeout                                   │
│   - Return structured result                               │
└────────────────────────────────────────────────────────────┘
```

### 6. Safety Module (`core/safety.py`)

**Responsibility:** Permission management and policy enforcement

```
┌────────────────────────────────────────────────────────────┐
│                     core/safety.py                          │
├────────────────────────────────────────────────────────────┤
│ Functions:                                                  │
│   load_permissions(path: str) → dict                       │
│   get_permission(action_type: str) → str                   │
│   check_action(decision: Decision) → str                   │
│                                                            │
│ Permission Levels:                                          │
│   "auto" → Execute without user intervention               │
│   "ask"  → Require user confirmation                       │
│   "deny" → Block entirely                                  │
├────────────────────────────────────────────────────────────┤
│ Behavior:                                                   │
│   - Load permissions.yaml on startup                       │
│   - YAML can override classifier decisions                 │
│   - Unknown actions use "default" permission               │
│   - Return final permission level                          │
└────────────────────────────────────────────────────────────┘
```

### 7. Logger Module (`utils/logger.py`)

**Responsibility:** Audit trail and error logging

```
┌────────────────────────────────────────────────────────────┐
│                     utils/logger.py                         │
├────────────────────────────────────────────────────────────┤
│ Functions:                                                  │
│   setup_logger() → logging.Logger                          │
│   log_action(action_type: str, decision: Decision,         │
│              result: ExecutionResult) → None               │
│   log_error(error: Exception, context: str) → None         │
│                                                            │
│ Constants:                                                  │
│   LOG_FILE = "logs/automation.log"                         │
│   LOG_FORMAT = "[{timestamp}] ACTION={type} ..."           │
├────────────────────────────────────────────────────────────┤
│ Output Format:                                              │
│   [2024-01-15T10:30:00] ACTION=execute DECISION=auto       │
│   RISK=low COMMAND="pytest tests/" RESULT=success          │
└────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Main Loop Flow

```
┌─────────┐     ┌─────────┐     ┌──────────┐     ┌─────────┐     ┌────────┐
│  User   │────▶│  Main   │────▶│  Claude  │────▶│Classify │────▶│Execute │
│  Input  │     │  Loop   │     │  Module  │     │ Module  │     │  or    │
│         │     │         │     │          │     │         │     │  Ask   │
└─────────┘     └────┬────┘     └──────────┘     └────┬────┘     └───┬────┘
                     │                                │              │
                     │         ┌──────────┐          │              │
                     │         │  Logger  │◀─────────┴──────────────┘
                     │         │  Module  │
                     │         └──────────┘
                     │
                     ▼
              ┌─────────────┐
              │ Continue or │
              │    Exit     │
              └─────────────┘
```

### Classification Flow

```
┌──────────────┐
│Claude Response│
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│ Parse JSON   │────▶│Check Keywords│
└──────┬───────┘     └──────┬───────┘
       │                    │
       │ fail               │ dangerous
       ▼                    ▼
┌──────────────┐     ┌──────────────┐
│Default: user │     │Force: user   │
└──────────────┘     └──────────────┘
       │                    │
       │ success            │ safe
       ▼                    ▼
┌──────────────┐     ┌──────────────┐
│ Ollama       │     │ Check YAML   │
│ Classify     │────▶│ Permissions  │
└──────────────┘     └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Decision   │
                    │   Object     │
                    └──────────────┘
```

### Execution Flow

```
┌──────────────┐
│   Command    │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│ Validate     │─No─▶│   Block &    │
│ Sandbox Path │     │   Log Error  │
└──────┬───────┘     └──────────────┘
       │ Yes
       ▼
┌──────────────┐     ┌──────────────┐
│ Check File   │─No─▶│   Block &    │
│ Extension    │     │   Log Error  │
└──────┬───────┘     └──────────────┘
       │ Yes
       ▼
┌──────────────┐
│ Execute with │
│ Timeout      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Execution    │
│ Result       │
└──────────────┘
```

---

## API Specifications

### Internal APIs

#### `core.ollama.run_prompt()`
```python
def run_prompt(prompt: str, model: str = "llama3") -> str:
    """
    Execute a prompt using Ollama CLI.

    Args:
        prompt: The prompt to send to Ollama
        model: Model name (default: "llama3")

    Returns:
        Response text from Ollama

    Raises:
        OllamaError: After 3 failed retry attempts
    """
```

#### `core.claude.get_response()`
```python
def get_response(prompt: str) -> str:
    """
    Get a response from Claude (API or fallback).

    Args:
        prompt: The prompt to send

    Returns:
        Response text from Claude or Ollama fallback
    """
```

#### `core.classifier.classify()`
```python
def classify(response: str) -> Decision:
    """
    Classify a Claude response into an action decision.

    Args:
        response: Raw response from Claude

    Returns:
        Decision object with action, reason, command, risk_level
    """
```

#### `core.executor.execute()`
```python
def execute(command: str) -> ExecutionResult:
    """
    Execute a command in the sandbox environment.

    Args:
        command: Shell command to execute

    Returns:
        ExecutionResult with success, output, error, return_code
    """
```

#### `core.safety.check_action()`
```python
def check_action(decision: Decision) -> str:
    """
    Check permission level for a classified action.

    Args:
        decision: Decision object from classifier

    Returns:
        Permission level: "auto", "ask", or "deny"
    """
```

---

## Configuration Schema

### `config/permissions.yaml`
```yaml
# Permission levels: auto, ask, deny

actions:
  read_file: auto
  write_file: ask
  run_tests: auto
  git_commit: ask
  git_push: ask
  deploy: deny
  delete_file: ask
  system_command: deny

# Default for unknown action types
default: ask

# Keywords that always require user approval
dangerous_keywords:
  - deploy
  - production
  - sudo
  - rm -rf
  - chmod
  - chown
```

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: Input Validation                                  │
│  ├── Keyword detection (dangerous commands)                 │
│  └── JSON schema validation                                 │
│                                                             │
│  Layer 2: Classification                                    │
│  ├── Ollama risk assessment                                 │
│  └── YAML permission overrides                              │
│                                                             │
│  Layer 3: User Approval                                     │
│  ├── "ask" actions require confirmation                     │
│  └── "deny" actions blocked entirely                        │
│                                                             │
│  Layer 4: Sandbox Execution                                 │
│  ├── Path validation (no traversal)                         │
│  ├── Extension whitelist                                    │
│  └── Timeout enforcement                                    │
│                                                             │
│  Layer 5: Audit Logging                                     │
│  └── All actions logged with full context                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Error Handling Strategy

| Component | Error Type | Handling |
|-----------|------------|----------|
| Ollama | Subprocess failure | Retry 3x, then raise OllamaError |
| Ollama | Timeout | Kill process, retry |
| Claude | API error | Fall back to Ollama |
| Claude | Missing API key | Use Ollama simulation |
| Classifier | JSON parse error | Default to user action |
| Executor | Path traversal | Block and log |
| Executor | Invalid extension | Block and log |
| Executor | Timeout | Kill process, return error |
| Safety | Missing config | Use default permissions |
| Main | Any exception | Log, prompt user, continue |
