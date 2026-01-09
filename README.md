# Ollama Automation Harness — Implementation Spec

## Overview

A Python CLI harness that pairs Claude (code generation) with Ollama (decision classification) to automate development workflows with human oversight on sensitive operations.

---

## Project Structure

```
ollama-harness/
├── main.py                 # Entry point, main loop
├── config/
│   └── permissions.yaml    # Action permission rules
├── core/
│   ├── __init__.py
│   ├── claude.py           # Claude integration
│   ├── ollama.py           # Ollama integration
│   ├── classifier.py       # Action classification logic
│   ├── executor.py         # Command/file execution
│   └── safety.py           # Permission enforcement
├── utils/
│   ├── __init__.py
│   ├── logger.py           # Audit logging
│   └── prompts.py          # Prompt templates
├── sandbox/                # Restricted execution directory
├── logs/
│   └── automation.log
├── requirements.txt
└── tests/
    ├── test_classifier.py
    ├── test_executor.py
    └── test_safety.py
```

---

## Data Structures

### Decision Object (JSON)

```json
{
  "action": "auto" | "user",
  "reason": "string explaining classification",
  "command": "optional extracted command",
  "risk_level": "low" | "medium" | "high"
}
```

### Permissions Schema (YAML)

```yaml
permissions:
  git_push: ask
  git_commit: ask
  file_write: auto
  file_delete: ask
  shell_exec: auto
  deploy: deny
  default: ask

sandbox:
  root: "./sandbox"
  allowed_extensions: [".py", ".txt", ".json", ".yaml", ".md"]

limits:
  max_retries: 3
  loop_delay_seconds: 1
  max_reply_length: 2000
```

---

## Core Modules

### 1. `core/ollama.py`

```python
def run_ollama(prompt: str, model: str = "llama3") -> str:
    """
    Execute Ollama with given prompt.
    
    Args:
        prompt: Input text for the model
        model: Ollama model name (default: llama3)
    
    Returns:
        Model response as string
    
    Raises:
        OllamaError: On subprocess failure after retries
    
    Implementation:
        - subprocess.run(["ollama", "run", model], input=prompt, capture_output=True)
        - Retry up to 3 times on failure
        - Timeout: 60 seconds per attempt
    """
```

### 2. `core/claude.py`

```python
def run_claude(prompt: str, use_api: bool = False) -> str:
    """
    Get response from Claude.
    
    Args:
        prompt: User/system prompt
        use_api: If True, use Anthropic API; else simulate via Ollama
    
    Returns:
        Claude's response string
    
    Implementation:
        - API mode: anthropic.Client().messages.create(model="claude-sonnet-4-20250514", ...)
        - Simulation mode: run_ollama(prompt, model="llama3")
        - API key from env: ANTHROPIC_API_KEY
    """
```

### 3. `core/classifier.py`

```python
@dataclass
class Decision:
    action: Literal["auto", "user"]
    reason: str
    command: str | None = None
    risk_level: Literal["low", "medium", "high"] = "low"

def classify_action(claude_reply: str) -> Decision:
    """
    Analyze Claude's output and classify required action.
    
    Args:
        claude_reply: Raw text from Claude
    
    Returns:
        Decision object with classification
    
    Implementation:
        1. Build classification prompt (see CLASSIFICATION_PROMPT)
        2. Call run_ollama() with prompt
        3. Parse JSON response
        4. Fallback: return Decision(action="user", reason="parse error")
    
    Sensitive keywords that force "user" action:
        - deploy, push, rm -rf, sudo, chmod, production
    """

CLASSIFICATION_PROMPT = '''
Analyze this AI response and classify the required action.

Response to analyze:
"""
{claude_reply}
"""

Output ONLY valid JSON:
{{"action": "auto" or "user", "reason": "brief explanation", "command": "extracted command or null", "risk_level": "low/medium/high"}}

Rules:
- "auto": Safe operations (run tests, generate code, read files, write to sandbox)
- "user": Dangerous operations (git push, deploy, delete, modify system files)
- Always "user" for: deploy, production, push, sudo, rm -rf, chmod
'''
```

### 4. `core/executor.py`

```python
@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: str | None = None
    return_code: int = 0

def execute_autonomous(decision: Decision, sandbox_root: str) -> ExecutionResult:
    """
    Execute classified autonomous action.
    
    Args:
        decision: Classified Decision object
        sandbox_root: Path to sandbox directory
    
    Returns:
        ExecutionResult with stdout/stderr
    
    Implementation:
        - Validate command against permissions
        - Ensure all file ops stay within sandbox_root
        - subprocess.run() with timeout=30s, shell=False
        - Capture and return stdout/stderr
    """

def write_file_sandboxed(path: str, content: str, sandbox_root: str) -> bool:
    """Write file only if path resolves within sandbox."""

def run_command_sandboxed(command: list[str], sandbox_root: str) -> ExecutionResult:
    """Execute command with cwd set to sandbox."""
```

### 5. `core/safety.py`

```python
class PermissionManager:
    def __init__(self, config_path: str = "config/permissions.yaml"):
        """Load permissions from YAML config."""
    
    def check_permission(self, action_type: str) -> Literal["auto", "ask", "deny"]:
        """
        Check permission level for action type.
        
        Returns:
            "auto" - proceed without asking
            "ask" - require user confirmation  
            "deny" - block entirely
        """
    
    def enforce(self, decision: Decision) -> Decision:
        """
        Override decision based on permission rules.
        
        If YAML says "ask" but classifier said "auto", 
        return modified Decision with action="user".
        """
    
    def validate_path(self, path: str) -> bool:
        """Ensure path is within sandbox and has allowed extension."""
```

### 6. `utils/logger.py`

```python
def log_action(
    action_type: str,
    decision: Decision,
    user_input: str | None,
    result: ExecutionResult | None
) -> None:
    """
    Append to automation.log with timestamp.
    
    Format:
        [2025-01-09T14:30:00] ACTION=shell_exec DECISION=auto RISK=low
        COMMAND="python test.py" RESULT=success
    """
```

---

## Main Loop (`main.py`)

```python
def main():
    # 1. Initialize
    permissions = PermissionManager("config/permissions.yaml")
    current_prompt = get_initial_prompt()  # CLI input
    
    # 2. Main loop
    while True:
        try:
            # Get Claude's response
            claude_reply = run_claude(current_prompt)
            print(f"\n[Claude]: {truncate(claude_reply, 500)}")
            
            # Classify action
            decision = classify_action(claude_reply)
            decision = permissions.enforce(decision)  # Apply YAML overrides
            
            print(f"[Decision]: {decision.action} ({decision.reason})")
            
            if decision.action == "auto":
                # Execute and continue
                result = execute_autonomous(decision, SANDBOX_ROOT)
                log_action("auto_exec", decision, None, result)
                current_prompt = build_continuation_prompt(claude_reply, result)
                
            else:  # "user"
                # Get user approval/modification
                print(f"\n⚠️  User action required: {decision.reason}")
                user_input = input("Approve (y), modify (m), skip (s), quit (q): ")
                
                if user_input == "q":
                    break
                elif user_input == "y":
                    result = execute_autonomous(decision, SANDBOX_ROOT)
                    log_action("user_approved", decision, "y", result)
                    current_prompt = build_continuation_prompt(claude_reply, result)
                elif user_input == "m":
                    modification = input("Enter modified prompt: ")
                    current_prompt = modification
                else:  # skip
                    current_prompt = input("Enter next prompt: ")
            
            time.sleep(LOOP_DELAY)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            log_action("error", None, None, str(e))
            print(f"[Error]: {e}. Defaulting to user prompt.")
            current_prompt = input("Enter next prompt: ")

if __name__ == "__main__":
    main()
```

---

## Error Handling

| Error Type | Response |
|------------|----------|
| Ollama subprocess fails | Retry 3x, then raise `OllamaError` |
| JSON parse fails | Default to `Decision(action="user", reason="parse error")` |
| File outside sandbox | Block and log, return error result |
| Command timeout (>30s) | Kill process, return timeout error |
| API key missing | Fall back to Ollama simulation mode |
| Unknown action type | Apply `default` permission from YAML |

---

## Configuration

### Environment Variables

```bash
ANTHROPIC_API_KEY=sk-...      # Optional: for real Claude API
OLLAMA_MODEL=llama3           # Default controller model
SANDBOX_ROOT=./sandbox        # Execution sandbox path
LOG_LEVEL=INFO                # DEBUG, INFO, WARN, ERROR
```

### Default `permissions.yaml`

```yaml
permissions:
  git_push: ask
  git_commit: ask
  git_pull: auto
  file_write: auto
  file_delete: ask
  file_read: auto
  shell_exec: auto
  test_run: auto
  deploy: deny
  default: ask

sandbox:
  root: "./sandbox"
  allowed_extensions:
    - ".py"
    - ".txt"
    - ".json"
    - ".yaml"
    - ".md"
    - ".sh"

limits:
  max_retries: 3
  loop_delay_seconds: 1
  command_timeout_seconds: 30
  max_reply_length: 2000
```

---

## Requirements

### `requirements.txt`

```
anthropic>=0.18.0
pyyaml>=6.0
gitpython>=3.1.0  # optional
```

### System Requirements

- Python 3.10+
- Ollama installed with `llama3` model pulled
- macOS / Linux / Windows (WSL recommended)
- No root access required

---

## Testing Criteria

### Unit Tests

| Test | Coverage |
|------|----------|
| `test_classifier.py` | JSON parsing, fallback behavior, keyword detection |
| `test_executor.py` | Sandbox enforcement, command execution, timeout handling |
| `test_safety.py` | Permission loading, override logic, path validation |

### Integration Tests

- 10+ loop iterations without crash
- Classification accuracy >90% on test prompts
- Dangerous commands never execute without user approval

### Manual Test Scenarios

1. Simulate `rm -rf /` in Claude reply → must classify as "user"
2. Attempt file write outside sandbox → must block
3. Valid test command → executes automatically
4. Git push request → prompts for approval per YAML

---

## Implementation Order

1. **`core/ollama.py`** — subprocess wrapper with retry logic
2. **`core/safety.py`** — YAML loader and permission checks
3. **`core/classifier.py`** — prompt template and JSON parsing
4. **`core/executor.py`** — sandboxed execution
5. **`utils/logger.py`** — audit trail
6. **`core/claude.py`** — API/simulation toggle
7. **`main.py`** — orchestration loop
8. **Tests** — validate each module
9. **Polish** — error messages, CLI UX
