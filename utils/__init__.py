"""
Utility modules for Ollama Automation Harness.

Modules:
    config: Centralized configuration
    logger: Audit trail and error logging
"""

from utils.logger import setup_logger, log_action, log_error
from utils.config import (
    SANDBOX_DIR,
    PERMISSIONS_FILE,
    LOG_FILE,
    LOOP_DELAY,
    MAX_REPLY_LENGTH,
    is_dangerous_keyword,
    is_allowed_extension,
    ensure_directories,
    get_config_dict,
)

__all__ = [
    # Logger
    "setup_logger",
    "log_action",
    "log_error",
    # Config
    "SANDBOX_DIR",
    "PERMISSIONS_FILE",
    "LOG_FILE",
    "LOOP_DELAY",
    "MAX_REPLY_LENGTH",
    "is_dangerous_keyword",
    "is_allowed_extension",
    "ensure_directories",
    "get_config_dict",
]
