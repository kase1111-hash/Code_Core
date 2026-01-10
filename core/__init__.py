"""
Core modules for Ollama Automation Harness.

Modules:
    ollama: Ollama CLI subprocess wrapper
    claude: Claude API client with fallback
    classifier: Decision classification
    executor: Sandboxed command execution
    safety: Permission management
"""

from core.classifier import Decision, classify
from core.claude import get_response
from core.executor import ExecutionResult, execute
from core.ollama import OllamaError, run_prompt
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
