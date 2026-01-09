# User Stories & Acceptance Criteria

## Overview

This document defines user stories and acceptance criteria for the Ollama Automation Harness project.

---

## User Stories

### US-001: Run Ollama Commands

**As a** developer
**I want to** execute prompts through Ollama
**So that** I can get AI-powered decision classification

**Acceptance Criteria:**
- [ ] System can execute Ollama with a given prompt and model name
- [ ] Default model is `llama3`
- [ ] Commands timeout after 60 seconds
- [ ] Failed commands are retried up to 3 times
- [ ] `OllamaError` is raised after all retries fail

---

### US-002: Get Claude Responses

**As a** developer
**I want to** get code generation responses from Claude
**So that** I can receive AI-assisted development suggestions

**Acceptance Criteria:**
- [ ] System can call Claude via Anthropic API when `ANTHROPIC_API_KEY` is set
- [ ] System falls back to Ollama simulation when API key is missing
- [ ] API mode uses `claude-sonnet-4-20250514` model
- [ ] Responses are returned as strings

---

### US-003: Classify Actions

**As a** user
**I want** Claude's responses to be automatically classified
**So that** safe operations can proceed without my intervention

**Acceptance Criteria:**
- [ ] System parses Claude's output and returns a Decision object
- [ ] Decision includes: action (auto/user), reason, command, risk_level
- [ ] Safe operations (read files, run tests, write to sandbox) are classified as "auto"
- [ ] Dangerous operations (deploy, push, delete, sudo) are classified as "user"
- [ ] Keywords `deploy`, `production`, `push`, `sudo`, `rm -rf`, `chmod` force "user" action
- [ ] JSON parse failures default to `Decision(action="user", reason="parse error")`

---

### US-004: Execute Commands Safely

**As a** user
**I want** commands to execute in a sandboxed environment
**So that** my system is protected from accidental damage

**Acceptance Criteria:**
- [ ] All file operations are restricted to the sandbox directory
- [ ] Path traversal attempts (e.g., `../`) are blocked
- [ ] Only allowed file extensions can be written (`.py`, `.txt`, `.json`, `.yaml`, `.md`, `.sh`)
- [ ] Commands timeout after 30 seconds
- [ ] ExecutionResult includes success status, output, error, and return code

---

### US-005: Manage Permissions

**As a** user
**I want to** configure which actions require approval
**So that** I have control over sensitive operations

**Acceptance Criteria:**
- [ ] Permissions are loaded from `config/permissions.yaml`
- [ ] Three permission levels exist: `auto`, `ask`, `deny`
- [ ] `auto` actions proceed without user intervention
- [ ] `ask` actions require user confirmation
- [ ] `deny` actions are blocked entirely
- [ ] YAML overrides can change classifier decisions (e.g., classifier says "auto" but YAML says "ask")
- [ ] Unknown action types use the `default` permission

---

### US-006: Audit Trail Logging

**As a** administrator
**I want** all actions to be logged
**So that** I can audit what the system has done

**Acceptance Criteria:**
- [ ] All actions are logged to `logs/automation.log`
- [ ] Log entries include timestamp, action type, decision, risk level, command, and result
- [ ] Format: `[ISO-TIMESTAMP] ACTION=type DECISION=auto/user RISK=level COMMAND="cmd" RESULT=status`
- [ ] Errors are logged with full context

---

### US-007: Interactive Main Loop

**As a** user
**I want to** interact with the system through a CLI loop
**So that** I can approve, modify, or skip suggested actions

**Acceptance Criteria:**
- [ ] System starts with an initial prompt from CLI input
- [ ] Each iteration: get Claude response -> classify -> execute or ask
- [ ] Auto-classified actions execute immediately
- [ ] User-required actions show a prompt with options: approve (y), modify (m), skip (s), quit (q)
- [ ] Approved actions execute and continue the loop
- [ ] Modified prompts replace the current prompt
- [ ] Skipped actions prompt for a new input
- [ ] Quit exits the loop gracefully
- [ ] Keyboard interrupt (Ctrl+C) exits cleanly
- [ ] Errors are caught, logged, and the loop continues with user prompt

---

### US-008: Handle Errors Gracefully

**As a** user
**I want** the system to handle errors without crashing
**So that** I can continue working even when issues occur

**Acceptance Criteria:**
- [ ] Ollama subprocess failures retry 3 times before raising `OllamaError`
- [ ] JSON parse failures default to user action
- [ ] File operations outside sandbox are blocked and logged
- [ ] Command timeouts kill the process and return an error result
- [ ] Missing API key falls back to simulation mode
- [ ] Unknown action types use default permission
- [ ] All errors are logged with context

---

## Non-Functional Requirements

### NFR-001: Performance
- Loop delay between iterations: configurable (default 1 second)
- Command timeout: 30 seconds
- Ollama timeout: 60 seconds per attempt
- Maximum reply length: 2000 characters (truncated for display)

### NFR-002: Security
- No root access required
- All file operations sandboxed
- Sensitive commands always require user approval
- Audit logging for compliance

### NFR-003: Compatibility
- Python 3.10+
- macOS / Linux / Windows (WSL recommended)
- Ollama installed with `llama3` model

---

## Test Scenarios

| ID | Scenario | Expected Result |
|----|----------|-----------------|
| TS-001 | `rm -rf /` in Claude reply | Classified as "user", blocked |
| TS-002 | File write outside sandbox | Blocked and logged |
| TS-003 | Valid test command | Executes automatically |
| TS-004 | Git push request | Prompts for approval |
| TS-005 | 10+ loop iterations | No crashes |
| TS-006 | Classification accuracy | >90% on test prompts |
