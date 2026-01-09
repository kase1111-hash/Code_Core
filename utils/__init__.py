"""
Utility modules for Ollama Automation Harness.

Modules:
    logger: Audit trail and error logging
"""

from utils.logger import setup_logger, log_action, log_error

__all__ = [
    "setup_logger",
    "log_action",
    "log_error",
]
