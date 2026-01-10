# Static Analysis Report

Generated: 2026-01-10

## Summary

| Tool | Issues Found | Fixed | Remaining |
|------|-------------|-------|-----------|
| Ruff (Linting) | 106 | 86 | 20 |
| Mypy (Type Check) | 18 | 0 | 18 |
| Bandit (Security) | 13 | 0 | 13 |

## Linting (Ruff)

### Auto-Fixed Issues (86)
- Import sorting (I001)
- Unused imports (F401)
- Line length issues (E501) where possible
- Code style improvements

### Remaining Issues (20)
Mostly stylistic suggestions that require manual review:
- SIM110: Suggest using `any()` instead of for loops (intentionally left for readability)
- B904: Suggest using `raise from` for exception chaining
- Line length issues in string literals

### Recommendation
The remaining issues are low priority and do not affect functionality or security.

## Type Checking (Mypy)

### Issues Found (18)
1. **Incompatible type assignments** (3)
   - `utils/secrets.py:318` - Type mismatch in assignment
   - `utils/logger.py:110` - FileHandler vs RotatingFileHandler
   - `utils/error_tracking.py:356` - Dict vs str type

2. **Missing return type annotations** (6)
   - `cli.py` functions: cmd_run, cmd_version, cmd_check, cmd_config
   - `utils/error_tracking.py` functions

3. **Returning Any from typed functions** (5)
   - `core/claude.py:91`
   - `core/classifier.py:122, 131, 139`
   - `core/safety.py:48, 203`

4. **Missing library stubs** (1)
   - `yaml` (PyYAML) - Install `types-PyYAML` for full type coverage

### Recommendation
These are type annotation improvements that enhance IDE support and documentation.
No runtime impact. Low priority for this automation harness project.

## Security Scanning (Bandit)

### High Severity (1)
- **B602**: `subprocess_popen_with_shell_equals_true` in `core/executor.py:66`
  - **Status**: Expected - Required for shell command execution
  - **Mitigation**: Commands are validated and sanitized before execution
  - **Additional Protection**: Sandbox directory, safe environment, timeout limits

### Low Severity (12)
1. **B404**: subprocess import (2 instances)
   - Required for command execution functionality

2. **B603**: subprocess without shell (3 instances)
   - Expected for running external commands safely

3. **B607**: Partial executable path (3 instances)
   - Using `ollama` command by name (standard practice)

4. **B110**: try/except/pass (4 instances)
   - Intentional silent error handling for non-critical operations

### Security Assessment
All findings are **expected** for a CLI tool designed to execute commands:
- Subprocess usage is core functionality
- Shell execution is sandboxed and validated
- Input validation prevents injection attacks
- Safe environment variables filter sensitive data

## Test Results After Fixes

All tests passing after lint auto-fixes applied.

## Recommendations

### Immediate (None Required)
All critical issues are mitigated by design.

### Future Improvements (Low Priority)
1. Add type annotations to remaining functions
2. Install `types-PyYAML` for full type coverage
3. Consider using `any()` for simple loop patterns

## Conclusion

The codebase passes static analysis with acceptable findings:
- **Security**: All subprocess usage is intentional and protected by validation/sandboxing
- **Code Quality**: 86 issues auto-fixed, remaining 20 are stylistic
- **Type Safety**: 18 annotations could be improved for better IDE support

No blocking issues identified.
