# Architecture & Data Flow Diagrams

This document contains comprehensive diagrams for the Ollama Automation Harness system architecture, data flows, and component interactions.

> **Note**: These diagrams use Mermaid syntax and can be rendered by GitHub, GitLab, VS Code, and other Markdown tools.

---

## Table of Contents

1. [System Context Diagram](#1-system-context-diagram)
2. [Component Architecture Diagram](#2-component-architecture-diagram)
3. [Module Dependency Diagram](#3-module-dependency-diagram)
4. [Main Workflow Sequence Diagram](#4-main-workflow-sequence-diagram)
5. [Classification Flow Diagram](#5-classification-flow-diagram)
6. [Permission Enforcement Flow](#6-permission-enforcement-flow)
7. [Execution Pipeline Diagram](#7-execution-pipeline-diagram)
8. [Error Handling Flow](#8-error-handling-flow)
9. [Security Layers Diagram](#9-security-layers-diagram)
10. [State Machine Diagram](#10-state-machine-diagram)
11. [Deployment Architecture](#11-deployment-architecture)
12. [Data Model Diagram](#12-data-model-diagram)

---

## 1. System Context Diagram

Shows the harness in relation to external systems and actors.

```mermaid
C4Context
    title System Context Diagram - Ollama Automation Harness

    Person(user, "Developer", "Uses CLI to automate development tasks")

    System(harness, "Ollama Automation Harness", "AI-powered development automation with human oversight")

    System_Ext(claude_api, "Anthropic Claude API", "Primary AI model for code generation")
    System_Ext(ollama, "Ollama", "Local LLM for classification and fallback")
    System_Ext(filesystem, "File System", "Sandbox directory for safe operations")

    Rel(user, harness, "Provides prompts, approves actions", "CLI stdin/stdout")
    Rel(harness, claude_api, "Sends prompts, receives responses", "HTTPS")
    Rel(harness, ollama, "Classifies actions, fallback generation", "CLI subprocess")
    Rel(harness, filesystem, "Executes commands, reads/writes files", "Sandboxed I/O")
```

### Simplified Version (Standard Mermaid)

```mermaid
flowchart TB
    subgraph External
        User[/"Developer"/]
        Claude["Anthropic Claude API<br/>(Remote)"]
        Ollama["Ollama<br/>(Local)"]
        FS[("File System<br/>(Sandbox)")]
    end

    subgraph System["Ollama Automation Harness"]
        CLI["CLI Interface"]
        Core["Core Engine"]
        Safety["Safety Layer"]
    end

    User -->|"prompts & approvals"| CLI
    CLI -->|"responses & requests"| User
    Core -->|"HTTPS API calls"| Claude
    Claude -->|"AI responses"| Core
    Core -->|"subprocess calls"| Ollama
    Ollama -->|"classifications"| Core
    Safety -->|"sandboxed I/O"| FS
```

---

## 2. Component Architecture Diagram

Shows internal components and their relationships.

```mermaid
flowchart TB
    subgraph CLI["CLI Layer"]
        MainPy["main.py<br/>Entry Point"]
        CliPy["cli.py<br/>Subcommands"]
    end

    subgraph Core["Core Modules"]
        Claude["core/claude.py<br/>AI Responses"]
        Classifier["core/classifier.py<br/>Action Classification"]
        Executor["core/executor.py<br/>Sandboxed Execution"]
        Ollama["core/ollama.py<br/>Local LLM"]
        Safety["core/safety.py<br/>Permission Manager"]
    end

    subgraph Utils["Utility Modules"]
        Config["utils/config.py<br/>Configuration"]
        Logger["utils/logger.py<br/>Audit Logging"]
        Validation["utils/validation.py<br/>Input Validation"]
        Errors["utils/errors.py<br/>Error Handling"]
        Secrets["utils/secrets.py<br/>Secure Config"]
        Telemetry["utils/telemetry.py<br/>Metrics"]
    end

    subgraph External["External Dependencies"]
        AnthropicAPI[("Anthropic API")]
        OllamaCLI[("Ollama CLI")]
        FileSystem[("File System")]
        PermYAML[("permissions.yaml")]
    end

    MainPy --> Claude
    MainPy --> Classifier
    MainPy --> Executor
    MainPy --> Safety
    MainPy --> Logger

    CliPy --> MainPy
    CliPy --> Config

    Claude --> AnthropicAPI
    Claude --> Ollama
    Classifier --> Ollama
    Classifier --> Config

    Executor --> Validation
    Executor --> FileSystem

    Safety --> PermYAML
    Safety --> Config

    Ollama --> OllamaCLI

    Logger --> Telemetry
    Config --> Secrets
```

---

## 3. Module Dependency Diagram

Shows import relationships between modules.

```mermaid
flowchart LR
    subgraph Entry["Entry Points"]
        main["main.py"]
        cli["cli.py"]
    end

    subgraph Core["core/"]
        claude["claude"]
        classifier["classifier"]
        executor["executor"]
        ollama["ollama"]
        safety["safety"]
    end

    subgraph Utils["utils/"]
        config["config"]
        validation["validation"]
        logger["logger"]
        errors["errors"]
        secrets["secrets"]
        monitoring["monitoring"]
        telemetry["telemetry"]
        metrics["metrics"]
        version["version"]
    end

    main --> claude
    main --> classifier
    main --> executor
    main --> safety
    main --> logger
    main --> config

    cli --> main
    cli --> config
    cli --> secrets
    cli --> version
    cli --> metrics
    cli --> monitoring

    claude --> ollama
    claude --> config
    claude --> errors

    classifier --> ollama
    classifier --> config
    classifier --> validation

    executor --> config
    executor --> validation

    safety --> config

    ollama --> config
    ollama --> errors

    logger --> config
    logger --> telemetry

    secrets --> config
    monitoring --> metrics
    telemetry --> metrics
```

---

## 4. Main Workflow Sequence Diagram

Shows the complete request-response cycle.

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Main as main.py
    participant Claude as claude.py
    participant API as Claude API
    participant Classifier as classifier.py
    participant Ollama as ollama.py
    participant Safety as safety.py
    participant Executor as executor.py
    participant Logger as logger.py

    User->>Main: Enter prompt
    Main->>Logger: log_startup()

    loop Automation Loop
        Main->>Claude: get_response(prompt)

        alt API Key Available
            Claude->>API: POST /v1/messages
            API-->>Claude: AI response
        else No API Key
            Claude->>Ollama: run_prompt(prompt)
            Ollama-->>Claude: Fallback response
        end

        Claude-->>Main: response text
        Main->>User: Display response

        Main->>Classifier: classify(response)
        Classifier->>Ollama: run_prompt(classification_prompt)
        Ollama-->>Classifier: JSON classification
        Classifier-->>Main: Decision object

        Main->>Safety: enforce(decision)
        Safety-->>Main: Modified decision

        alt action == "auto"
            Main->>Executor: execute(command)
            Executor-->>Main: ExecutionResult
            Main->>Logger: log_action(...)
        else action == "user"
            Main->>User: Request approval
            User-->>Main: approve/reject

            alt Approved
                Main->>Executor: execute(command)
                Executor-->>Main: ExecutionResult
                Main->>Logger: log_action(...)
            else Rejected
                Main->>Logger: log_user_decision(rejected)
            end
        end

        Main->>User: Show result
        User-->>Main: Continue/Exit
    end

    Main->>Logger: log_shutdown()
```

---

## 5. Classification Flow Diagram

Shows how responses are classified into decisions.

```mermaid
flowchart TD
    Start([Claude Response]) --> Sanitize[Sanitize Input]
    Sanitize --> Extract[Extract Command]

    Extract --> DangerCheck{Contains<br/>Dangerous<br/>Keywords?}

    DangerCheck -->|Yes| ForceUser[Force action=user<br/>risk_level=high]
    ForceUser --> FinalDecision

    DangerCheck -->|No| OllamaClassify[Send to Ollama<br/>for Classification]

    OllamaClassify --> ParseJSON{Parse JSON<br/>Response?}

    ParseJSON -->|Success| ValidateFields[Validate Fields]
    ParseJSON -->|Fail| DefaultUser[Default to<br/>action=user]

    ValidateFields --> CommandCheck{Command has<br/>Dangerous<br/>Keywords?}

    CommandCheck -->|Yes| OverrideUser[Override to<br/>action=user<br/>risk_level=high]
    CommandCheck -->|No| UseClassification[Use Ollama<br/>Classification]

    DefaultUser --> FinalDecision
    OverrideUser --> FinalDecision
    UseClassification --> FinalDecision

    FinalDecision([Decision Object])

    style ForceUser fill:#f99
    style OverrideUser fill:#f99
    style DefaultUser fill:#ff9
    style UseClassification fill:#9f9
```

---

## 6. Permission Enforcement Flow

Shows how permissions modify decisions.

```mermaid
flowchart TD
    Start([Decision from Classifier]) --> InferType[Infer Action Type<br/>from Command]

    InferType --> LoadPerms[Load permissions.yaml]

    LoadPerms --> CheckDangerous{Contains<br/>Dangerous<br/>Keywords?}

    CheckDangerous -->|Yes| ForceDeny[Force action=user<br/>risk_level=high<br/>Reason: dangerous keyword]

    CheckDangerous -->|No| GetPermission[Get Permission Level<br/>for Action Type]

    GetPermission --> PermLevel{Permission<br/>Level?}

    PermLevel -->|deny| BlockAction[Force action=user<br/>Reason: denied by policy]

    PermLevel -->|ask| CheckAuto{Was<br/>action=auto?}
    CheckAuto -->|Yes| OverrideAsk[Override to action=user<br/>Reason: requires approval]
    CheckAuto -->|No| PassThrough1[Keep Original Decision]

    PermLevel -->|auto| PassThrough2[Keep Original Decision]

    ForceDeny --> FinalDecision
    BlockAction --> FinalDecision
    OverrideAsk --> FinalDecision
    PassThrough1 --> FinalDecision
    PassThrough2 --> FinalDecision

    FinalDecision([Enforced Decision])

    style ForceDeny fill:#f66
    style BlockAction fill:#f99
    style OverrideAsk fill:#ff9
    style PassThrough1 fill:#9f9
    style PassThrough2 fill:#9f9
```

---

## 7. Execution Pipeline Diagram

Shows the sandboxed execution process.

```mermaid
flowchart TD
    Start([Command to Execute]) --> ValidateCmd[Validate Command<br/>Length & Content]

    ValidateCmd -->|Invalid| CmdError[Return Error:<br/>Command validation failed]

    ValidateCmd -->|Valid| EnsureSandbox[Ensure Sandbox<br/>Directory Exists]

    EnsureSandbox --> PrepareEnv[Prepare Safe<br/>Environment Variables]

    PrepareEnv --> Execute[Execute via subprocess<br/>shell=True, cwd=sandbox]

    Execute --> Timeout{Timeout<br/>Exceeded?}

    Timeout -->|Yes| TimeoutError[Return Error:<br/>Command timed out]

    Timeout -->|No| CheckReturn{Return<br/>Code = 0?}

    CheckReturn -->|Yes| Success[Return Success:<br/>output=stdout]
    CheckReturn -->|No| Failure[Return Failure:<br/>error=stderr]

    CmdError --> Result
    TimeoutError --> Result
    Success --> Result
    Failure --> Result

    Result([ExecutionResult])

    subgraph SafeEnv["Safe Environment"]
        PATH["PATH"]
        HOME["HOME"]
        USER["USER"]
        LANG["LANG"]
        PYTHONPATH["PYTHONPATH"]
    end

    PrepareEnv -.-> SafeEnv

    style CmdError fill:#f66
    style TimeoutError fill:#f99
    style Failure fill:#ff9
    style Success fill:#9f9
```

---

## 8. Error Handling Flow

Shows how errors propagate through the system.

```mermaid
flowchart TD
    subgraph Sources["Error Sources"]
        OllamaErr[OllamaError]
        ClaudeErr[ClaudeError]
        ValidationErr[ValidationError]
        ConfigErr[ConfigError]
        ExecutionErr[ExecutionError]
    end

    subgraph Handling["Error Handling"]
        Retry{Retriable?}
        Fallback{Has Fallback?}
        LogError[Log Error]
        UserNotify[Notify User]
    end

    subgraph Recovery["Recovery Actions"]
        RetryAction[Retry with Backoff]
        FallbackAction[Use Fallback]
        GracefulFail[Graceful Failure]
        Continue[Continue Loop]
    end

    OllamaErr --> Retry
    ClaudeErr --> Fallback
    ValidationErr --> LogError
    ConfigErr --> LogError
    ExecutionErr --> LogError

    Retry -->|Yes, attempts < 3| RetryAction
    Retry -->|No, exhausted| LogError

    Fallback -->|Yes, Ollama available| FallbackAction
    Fallback -->|No| LogError

    RetryAction --> Sources
    FallbackAction --> Continue

    LogError --> UserNotify
    UserNotify --> GracefulFail
    GracefulFail --> Continue
```

---

## 9. Security Layers Diagram

Shows the defense-in-depth security architecture.

```mermaid
flowchart TB
    subgraph Layer1["Layer 1: Input Validation"]
        L1A[Prompt Length Check<br/>max 10,000 chars]
        L1B[Command Length Check<br/>max 1,000 chars]
        L1C[String Sanitization]
        L1D[Path Traversal Detection]
    end

    subgraph Layer2["Layer 2: Keyword Detection"]
        L2A[Dangerous Keywords List]
        L2B[Real-time Scanning]
        L2C[Force User Action]
    end

    subgraph Layer3["Layer 3: AI Classification"]
        L3A[Ollama Risk Assessment]
        L3B[JSON Validation]
        L3C[Risk Level Assignment]
    end

    subgraph Layer4["Layer 4: Permission Enforcement"]
        L4A[YAML Policy Rules]
        L4B[Action Type Matching]
        L4C[Decision Override]
    end

    subgraph Layer5["Layer 5: User Approval"]
        L5A[Interactive Confirmation]
        L5B[Explicit Consent]
        L5C[Rejection Option]
    end

    subgraph Layer6["Layer 6: Sandbox Execution"]
        L6A[Directory Restriction]
        L6B[Extension Whitelist]
        L6C[Timeout Enforcement]
        L6D[Safe Environment]
    end

    subgraph Layer7["Layer 7: Audit Logging"]
        L7A[Action Logging]
        L7B[Decision Logging]
        L7C[Error Logging]
        L7D[User Decision Logging]
    end

    Input([User Input]) --> Layer1
    Layer1 --> Layer2
    Layer2 --> Layer3
    Layer3 --> Layer4
    Layer4 --> Layer5
    Layer5 --> Layer6
    Layer6 --> Layer7
    Layer7 --> Output([Logged Result])

    style Layer1 fill:#e3f2fd
    style Layer2 fill:#fff3e0
    style Layer3 fill:#f3e5f5
    style Layer4 fill:#e8f5e9
    style Layer5 fill:#fce4ec
    style Layer6 fill:#e0f7fa
    style Layer7 fill:#f5f5f5
```

---

## 10. State Machine Diagram

Shows the application states and transitions.

```mermaid
stateDiagram-v2
    [*] --> Initializing: Start

    Initializing --> Ready: Config loaded
    Initializing --> Error: Config error

    Ready --> WaitingForInput: Prompt for input

    WaitingForInput --> ProcessingPrompt: User enters prompt
    WaitingForInput --> Shutdown: User exits

    ProcessingPrompt --> GettingAIResponse: Send to Claude

    GettingAIResponse --> ClassifyingAction: Response received
    GettingAIResponse --> Error: API error

    ClassifyingAction --> EnforcingPermissions: Decision made
    ClassifyingAction --> Error: Classification error

    EnforcingPermissions --> AutoExecuting: action=auto
    EnforcingPermissions --> WaitingForApproval: action=user

    WaitingForApproval --> Executing: User approves
    WaitingForApproval --> WaitingForInput: User rejects

    AutoExecuting --> Executing: Proceed

    Executing --> DisplayingResult: Execution complete
    Executing --> Error: Execution error

    DisplayingResult --> WaitingForInput: Continue
    DisplayingResult --> Shutdown: Exit

    Error --> WaitingForInput: Recover
    Error --> Shutdown: Fatal error

    Shutdown --> [*]: End
```

---

## 11. Deployment Architecture

Shows how the application can be deployed.

```mermaid
flowchart TB
    subgraph Development["Development Environment"]
        DevMachine["Developer Machine"]
        DevPython["Python 3.10+"]
        DevOllama["Ollama (local)"]
        DevVenv["Virtual Environment"]
    end

    subgraph Docker["Docker Deployment"]
        DockerImage["ollama-harness:latest"]
        DockerVolumes["Volumes"]
        DockerEnv[".env file"]

        subgraph Volumes
            SandboxVol["/app/sandbox"]
            LogsVol["/app/logs"]
            ConfigVol["/app/config"]
        end
    end

    subgraph Production["Production Environment"]
        ProdServer["Production Server"]
        ProdDocker["Docker Runtime"]
        ProdOllama["Ollama Service"]
        SecretsMgr["Secrets Manager"]
    end

    subgraph External["External Services"]
        ClaudeAPI["Anthropic API<br/>(api.anthropic.com)"]
        Sentry["Sentry<br/>(Error Tracking)"]
    end

    DevMachine --> DevPython
    DevPython --> DevVenv
    DevVenv --> DevOllama

    DockerImage --> DockerVolumes
    DockerImage --> DockerEnv

    ProdServer --> ProdDocker
    ProdDocker --> DockerImage
    ProdDocker --> ProdOllama
    ProdServer --> SecretsMgr

    DevVenv -.->|HTTPS| ClaudeAPI
    DockerImage -.->|HTTPS| ClaudeAPI
    DockerImage -.->|HTTPS| Sentry
```

---

## 12. Data Model Diagram

Shows key data structures and their relationships.

```mermaid
classDiagram
    class Decision {
        +str action
        +str reason
        +str|None command
        +str risk_level
    }

    class ExecutionResult {
        +bool success
        +str output
        +str error
        +int return_code
    }

    class PermissionConfig {
        +dict actions
        +str default
        +list dangerous_keywords
        +dict sandbox
    }

    class SecureConfig {
        +Environment environment
        +dict secrets
        +validate() list~ConfigError~
        +to_safe_dict() dict
    }

    class HarnessError {
        +str message
        +ErrorCode code
        +ErrorContext context
    }

    class ServiceError {
        +str message
        +ErrorCode code
    }

    class ClaudeError {
        +str message
    }

    class OllamaError {
        +str message
    }

    class ValidationError {
        +str message
        +str field
    }

    class ConfigError {
        +str key
        +str message
        +str severity
    }

    class ErrorContext {
        +str operation
        +str timestamp
        +dict extra
    }

    HarnessError <|-- ServiceError
    ServiceError <|-- ClaudeError
    ServiceError <|-- OllamaError
    HarnessError <|-- ValidationError
    HarnessError *-- ErrorContext

    SecureConfig *-- ConfigError
    PermissionConfig --> Decision : enforces
    Decision --> ExecutionResult : produces
```

---

## Data Flow Summary

### Request Flow

```
User Input → Validation → Claude API → Classification → Permission Check → Execution → Logging → Output
```

### Data Transformation

```mermaid
flowchart LR
    A[String: prompt] --> B[String: AI response]
    B --> C[Decision object]
    C --> D[Enforced Decision]
    D --> E[ExecutionResult]
    E --> F[Log Entry]
```

---

## Diagram Legend

| Symbol | Meaning |
|--------|---------|
| Rectangle | Process/Module |
| Diamond | Decision Point |
| Cylinder | Database/Storage |
| Stadium | Start/End |
| Parallelogram | Input/Output |
| Green Fill | Success Path |
| Yellow Fill | Warning/Caution |
| Red Fill | Error/Block |

---

*Last updated: 2024-01-15*
