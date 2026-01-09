"""
Utility modules for Ollama Automation Harness.

Modules:
    config: Centralized configuration
    logger: Audit trail and error logging
    validation: Input validation and sanitation
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
from utils.validation import (
    ValidationError,
    validate_prompt,
    sanitize_string,
    validate_command,
    contains_shell_injection,
    get_command_risk_level,
    validate_path,
    contains_path_traversal,
    validate_extension,
    validate_config_value,
    validate_permission_level,
    validate_risk_level,
    validate_response,
    truncate_response,
    validate_user_choice,
    sanitize_log_message,
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
    # Validation
    "ValidationError",
    "validate_prompt",
    "sanitize_string",
    "validate_command",
    "contains_shell_injection",
    "get_command_risk_level",
    "validate_path",
    "contains_path_traversal",
    "validate_extension",
    "validate_config_value",
    "validate_permission_level",
    "validate_risk_level",
    "validate_response",
    "truncate_response",
    "validate_user_choice",
    "sanitize_log_message",
]
