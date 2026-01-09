"""
Core modules for Ollama Automation Harness.

Modules:
    ollama: Ollama CLI subprocess wrapper
    claude: Claude API client with fallback
    classifier: Decision classification
    executor: Sandboxed command execution
    safety: Permission management
"""

from core.ollama import run_prompt, OllamaError
from core.claude import get_response
from core.classifier import classify, Decision
from core.executor import execute, ExecutionResult
from core.safety import check_action, load_permissions

__all__ = [
    "run_prompt",
    "OllamaError",
    "get_response",
    "classify",
    "Decision",
    "execute",
    "ExecutionResult",
    "check_action",
    "load_permissions",
]
