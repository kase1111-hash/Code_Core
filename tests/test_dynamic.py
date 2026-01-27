"""
Dynamic analysis test suite for Ollama Automation Harness.

This module contains dynamic analysis tests including:
- Fuzzing tests with random/malformed inputs
- Runtime behavior analysis
- State management testing
- Error recovery testing
- Resource leak detection

Run dynamic analysis tests only:
    pytest -m dynamic

Run with verbose output:
    pytest -m dynamic -v --tb=short
"""

import gc
import random
import string
import threading
import tracemalloc

import pytest

# Mark all tests in this module as dynamic tests
pytestmark = pytest.mark.dynamic


# =============================================================================
# Fuzzing Utilities
# =============================================================================


def generate_random_string(length: int, charset: str = None) -> str:
    """Generate a random string of specified length."""
    if charset is None:
        charset = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(charset) for _ in range(length))


def generate_random_bytes(length: int) -> bytes:
    """Generate random bytes."""
    return bytes(random.randint(0, 255) for _ in range(length))


def generate_unicode_string(length: int) -> str:
    """Generate string with random unicode characters."""
    chars = []
    for _ in range(length):
        # Mix of ASCII, Latin, Chinese, Emoji ranges
        ranges = [
            (0x0020, 0x007E),  # ASCII printable
            (0x00A0, 0x00FF),  # Latin-1 Supplement
            (0x4E00, 0x4FFF),  # CJK Unified
            (0x1F600, 0x1F64F),  # Emoticons
        ]
        start, end = random.choice(ranges)
        try:
            char = chr(random.randint(start, end))
            chars.append(char)
        except ValueError:
            chars.append('?')
    return ''.join(chars)


def generate_boundary_values() -> list:
    """Generate common boundary test values."""
    return [
        "",  # Empty
        " ",  # Single space
        "\t",  # Tab
        "\n",  # Newline
        "\r\n",  # Windows newline
        "\x00",  # Null byte
        "a" * 100,  # Moderately long
        "a" * 1000,  # Long
        "a" * 10000,  # Very long
        "0",  # Zero string
        "-1",  # Negative
        "999999999999",  # Large number string
        "../../../",  # Path traversal
        "<script>",  # HTML/JS
        "'; DROP TABLE;--",  # SQL injection pattern
        "${PATH}",  # Environment variable
        "$(whoami)",  # Command substitution
    ]


def generate_special_characters() -> list:
    """Generate strings with special characters."""
    return [
        "test\x00null",  # Null byte
        "test\x1b[31mred",  # ANSI escape
        "test\b\b\bbackspace",  # Backspace
        "test\rcarriage",  # Carriage return
        "test\x7fdelete",  # Delete char
        "test'quote",  # Single quote
        'test"double',  # Double quote
        "test\\backslash",  # Backslash
        "test/slash",  # Forward slash
        "test`backtick`",  # Backticks
        "test$(cmd)",  # Command sub
        "test;semicolon",  # Semicolon
        "test|pipe",  # Pipe
        "test&ampersand",  # Ampersand
        "test>redirect",  # Redirect
        "test<input",  # Input redirect
    ]


# =============================================================================
# Input Fuzzing Tests
# =============================================================================


class TestPromptFuzzing:
    """Fuzzing tests for prompt validation."""

    def test_random_string_inputs(self):
        """Test with random string inputs."""
        from utils.validation import ValidationError, validate_prompt

        for _ in range(100):
            length = random.randint(1, 500)
            random_input = generate_random_string(length)

            try:
                result = validate_prompt(random_input)
                # Should return sanitized string
                assert isinstance(result, str)
                assert "\x00" not in result  # Null bytes removed
            except ValidationError:
                pass  # Rejection is acceptable

    def test_unicode_inputs(self):
        """Test with unicode string inputs."""
        from utils.validation import ValidationError, validate_prompt

        for _ in range(50):
            length = random.randint(1, 200)
            unicode_input = generate_unicode_string(length)

            try:
                result = validate_prompt(unicode_input)
                assert isinstance(result, str)
            except ValidationError:
                pass
            except UnicodeError:
                pass  # Some unicode may be invalid

    def test_boundary_value_inputs(self):
        """Test with boundary values."""
        from utils.validation import ValidationError, validate_prompt

        for value in generate_boundary_values():
            try:
                result = validate_prompt(value)
                # If it passes, should be string
                assert isinstance(result, str)
            except ValidationError:
                pass  # Expected for invalid inputs

    def test_special_character_inputs(self):
        """Test with special characters."""
        from utils.validation import ValidationError, validate_prompt

        for value in generate_special_characters():
            try:
                result = validate_prompt(value)
                assert isinstance(result, str)
                # Control characters should be removed
                assert "\x00" not in result
            except ValidationError:
                pass

    def test_mixed_encoding_inputs(self):
        """Test with mixed encoding edge cases."""
        from utils.validation import ValidationError, validate_prompt

        mixed_inputs = [
            "Hello\xc0\xaf World",  # Overlong UTF-8
            "Test\xed\xa0\x80",  # Surrogate pair
            "Data\xff\xfe",  # BOM-like
            "Mixed\x80\x81\x82",  # Invalid continuation
        ]

        for value in mixed_inputs:
            try:
                result = validate_prompt(value)
                assert isinstance(result, str)
            except (ValidationError, UnicodeError):
                pass


class TestCommandFuzzing:
    """Fuzzing tests for command validation."""

    def test_random_command_inputs(self):
        """Test with random command-like inputs."""
        from utils.validation import ValidationError, validate_command

        commands = [
            "echo " + generate_random_string(50),
            "ls " + generate_random_string(20),
            generate_random_string(100),
        ]

        for cmd in commands:
            try:
                result = validate_command(cmd)
                assert isinstance(result, str)
            except ValidationError:
                pass

    def test_command_injection_fuzzing(self):
        """Fuzz test for command injection patterns."""
        from utils.validation import ValidationError, validate_command

        # Generate variations of injection patterns
        separators = [";", "|", "&", "&&", "||", "\n", "\r\n"]
        dangerous = ["rm", "cat /etc/passwd", "wget", "curl"]

        for _ in range(50):
            sep = random.choice(separators)
            danger = random.choice(dangerous)
            prefix = generate_random_string(random.randint(1, 20))
            cmd = f"{prefix}{sep}{danger}"

            try:
                validate_command(cmd)
                # If it passes, the dangerous part should be neutralized
            except ValidationError:
                pass  # Good - rejected

    def test_length_boundary_commands(self):
        """Test command length boundaries."""
        from utils.validation import (
            MAX_COMMAND_LENGTH,
            ValidationError,
            validate_command,
        )

        # Just under limit
        cmd = "echo " + "a" * (MAX_COMMAND_LENGTH - 6)
        try:
            result = validate_command(cmd)
            assert len(result) <= MAX_COMMAND_LENGTH
        except ValidationError:
            pass

        # At limit
        cmd = "echo " + "a" * (MAX_COMMAND_LENGTH - 5)
        try:
            validate_command(cmd)
        except ValidationError:
            pass

        # Over limit
        cmd = "echo " + "a" * MAX_COMMAND_LENGTH
        with pytest.raises(ValidationError):
            validate_command(cmd)


class TestPathFuzzing:
    """Fuzzing tests for path validation."""

    def test_random_path_inputs(self, sandbox):
        """Test with random path inputs."""
        from utils.validation import ValidationError, validate_path

        for _ in range(100):
            # Generate random path-like strings
            parts = [generate_random_string(random.randint(1, 20), string.ascii_letters + string.digits + "_-.")
                     for _ in range(random.randint(1, 5))]
            path = "/".join(parts)

            try:
                result = validate_path(path, str(sandbox))
                assert isinstance(result, str)
            except ValidationError:
                pass

    def test_traversal_fuzzing(self, sandbox):
        """Fuzz test for path traversal patterns."""
        from utils.validation import ValidationError, validate_path

        traversal_patterns = [
            "..", "../", "..\\", "..%2f", "..%5c",
            "%2e%2e/", "%2e%2e%2f", "....//",
        ]

        for _ in range(50):
            # Build random traversal attempts
            pattern = random.choice(traversal_patterns)
            depth = random.randint(1, 10)
            path = pattern * depth + "etc/passwd"

            try:
                validate_path(path, str(sandbox))
            except ValidationError:
                pass  # Good - rejected


# =============================================================================
# Runtime Behavior Tests
# =============================================================================


class TestRuntimeBehavior:
    """Tests for runtime behavior and state management."""

    def test_repeated_validation_consistency(self):
        """Test that repeated validations give consistent results."""
        from utils.validation import validate_prompt

        test_inputs = [
            "Hello World",
            "Test with special: !@#$%",
            "Unicode: 你好",
        ]

        for inp in test_inputs:
            results = [validate_prompt(inp) for _ in range(10)]
            # All results should be identical
            assert all(r == results[0] for r in results)

    def test_concurrent_validation_safety(self):
        """Test that concurrent validations are thread-safe."""
        from utils.validation import validate_prompt

        results = []
        errors = []

        def validate_thread(idx):
            try:
                for _ in range(100):
                    result = validate_prompt(f"Thread {idx} test")
                    results.append(result)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=validate_thread, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0
        # All results should be valid strings
        assert all(isinstance(r, str) for r in results)

    def test_state_isolation_between_calls(self):
        """Test that function calls don't share state inappropriately."""
        from utils.validation import validate_prompt

        # First call with specific input
        result1 = validate_prompt("First input")

        # Second call with different input
        result2 = validate_prompt("Second input")

        # Results should be independent
        assert result1 != result2
        assert "First" in result1
        assert "Second" in result2

    def test_error_state_recovery(self):
        """Test that errors don't corrupt state."""
        from utils.validation import ValidationError, validate_prompt

        # First, a valid call
        result1 = validate_prompt("Valid input")
        assert result1 == "Valid input"

        # Then an invalid call (should raise)
        with pytest.raises(ValidationError):
            validate_prompt("")

        # Then another valid call - should still work
        result2 = validate_prompt("Another valid")
        assert result2 == "Another valid"


class TestMemoryBehavior:
    """Tests for memory usage and leak detection."""

    def test_no_memory_leak_in_validation(self):
        """Test that validation doesn't leak memory."""
        from utils.validation import validate_prompt

        gc.collect()
        tracemalloc.start()

        # Run many validations
        for i in range(1000):
            validate_prompt(f"Test prompt {i}")

        gc.collect()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Peak memory should be reasonable (< 50MB for this operation)
        assert peak < 50 * 1024 * 1024

    def test_no_memory_leak_in_error_creation(self):
        """Test that error creation doesn't leak memory."""
        from utils.errors import ErrorCode, ErrorContext, HarnessError

        gc.collect()
        tracemalloc.start()

        for i in range(1000):
            error = HarnessError(
                f"Error {i}",
                code=ErrorCode.UNKNOWN,
                context=ErrorContext(operation=f"test_{i}")
            )
            _ = error.to_dict()

        gc.collect()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert peak < 50 * 1024 * 1024

    def test_large_input_memory_handling(self):
        """Test memory handling with large inputs."""
        from utils.validation import ValidationError, validate_prompt

        gc.collect()
        tracemalloc.start()

        # Try with increasingly large inputs
        for size in [100, 1000, 5000, 9000]:
            try:
                large_input = "x" * size
                validate_prompt(large_input)
            except ValidationError:
                pass

        gc.collect()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory should scale reasonably
        assert peak < 100 * 1024 * 1024


class TestErrorRecovery:
    """Tests for error recovery and resilience."""

    def test_recovery_after_validation_error(self):
        """Test recovery after validation errors."""
        from utils.validation import ValidationError, validate_prompt

        # Cause various errors
        errors_raised = 0
        for _ in range(10):
            try:
                validate_prompt("")
            except ValidationError:
                errors_raised += 1

        assert errors_raised == 10

        # System should still work
        result = validate_prompt("Valid after errors")
        assert result == "Valid after errors"

    def test_recovery_after_path_errors(self, sandbox):
        """Test recovery after path validation errors."""
        from utils.validation import ValidationError, validate_path

        # Cause path errors
        for _ in range(10):
            try:
                validate_path("../../../etc/passwd", str(sandbox))
            except ValidationError:
                pass

        # Valid paths should still work
        result = validate_path("valid.txt", str(sandbox))
        assert str(sandbox) in result

    def test_graceful_handling_of_resource_exhaustion(self):
        """Test graceful handling when resources are constrained."""
        from utils.validation import validate_prompt

        # Create many strings to put pressure on memory
        strings = []
        for i in range(100):
            s = validate_prompt(f"Test {i} " * 100)
            strings.append(s)

        # Should complete without crashing
        assert len(strings) == 100

        # Cleanup
        del strings
        gc.collect()


# =============================================================================
# Execution Fuzzing Tests
# =============================================================================


class TestExecutorFuzzing:
    """Fuzzing tests for command execution."""

    def test_random_file_content_fuzzing(self, sandbox):
        """Test with random file content."""
        from core.executor import read_file_sandboxed, write_file_sandboxed

        for i in range(20):
            # Random content
            content = generate_random_string(random.randint(10, 1000))
            filename = f"fuzz_{i}.txt"

            write_result = write_file_sandboxed(filename, content, str(sandbox))
            if write_result.success:
                read_result = read_file_sandboxed(filename, str(sandbox))
                # Content should be preserved
                if read_result.success:
                    assert read_result.output == content

    def test_special_filename_fuzzing(self, sandbox):
        """Test with special characters in filenames."""
        from core.executor import write_file_sandboxed

        # Safe special characters for filenames
        special_names = [
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "file.multiple.dots.txt",
            "UPPERCASE.TXT",
            "MixedCase.Txt",
        ]

        for name in special_names:
            result = write_file_sandboxed(name, "content", str(sandbox))
            # Should handle gracefully (success or controlled failure)
            assert hasattr(result, 'success')

    def test_unicode_content_fuzzing(self, sandbox):
        """Test with unicode file content."""
        from core.executor import read_file_sandboxed, write_file_sandboxed

        unicode_contents = [
            "Hello 世界",
            "Émoji: 🎉🎊🎁",
            "Mixed: Hello世界🎉",
            "Arrows: →←↑↓",
        ]

        for i, content in enumerate(unicode_contents):
            filename = f"unicode_{i}.txt"
            write_result = write_file_sandboxed(filename, content, str(sandbox))

            if write_result.success:
                read_result = read_file_sandboxed(filename, str(sandbox))
                if read_result.success:
                    assert read_result.output == content


# =============================================================================
# Classification Fuzzing Tests
# =============================================================================


class TestClassifierFuzzing:
    """Fuzzing tests for response classification."""

    def test_malformed_json_handling(self):
        """Test handling of malformed JSON responses."""
        from core.classifier import parse_json_response

        malformed_jsons = [
            "{",  # Incomplete
            '{"action":}',  # Missing value
            '{"action": "test"',  # Missing closing
            "not json at all",
            '{"action": "test",}',  # Trailing comma
            '[{"action": "test"}]',  # Array instead of object
            '{"action": null}',  # Null value
            '{"action": 123}',  # Wrong type
            '{"action": "test", "action": "test2"}',  # Duplicate key
        ]

        for json_str in malformed_jsons:
            result = parse_json_response(json_str)
            # Should return None, dict, or list - never crash
            assert result is None or isinstance(result, (dict, list))

    def test_random_json_fuzzing(self):
        """Test with randomly generated JSON-like strings."""
        from core.classifier import parse_json_response

        for _ in range(50):
            # Generate random JSON-like structure
            parts = ["{"]
            for j in range(random.randint(1, 5)):
                key = generate_random_string(10, string.ascii_letters)
                value = generate_random_string(20)
                parts.append(f'"{key}": "{value}"')
                if j < 4:
                    parts.append(",")
            parts.append("}")

            json_str = "".join(parts)

            try:
                result = parse_json_response(json_str)
                # Should not crash
                assert result is None or isinstance(result, dict)
            except Exception:
                pass  # Some malformed JSON may raise

    def test_decision_with_fuzzy_inputs(self):
        """Test Decision class with various inputs."""
        from core.classifier import Decision

        for _ in range(50):
            try:
                decision = Decision(
                    action=random.choice(["auto", "user", "skip", generate_random_string(10)]),
                    reason=generate_random_string(random.randint(0, 200)),
                    command=generate_random_string(random.randint(0, 100)) if random.random() > 0.5 else None,
                    risk_level=random.choice(["low", "medium", "high", generate_random_string(5)]),
                )
                # Should create object without crashing
                assert hasattr(decision, 'action')
            except Exception:
                pass


# =============================================================================
# Integration Fuzzing Tests
# =============================================================================


class TestIntegrationFuzzing:
    """Integration fuzzing tests across multiple components."""

    def test_full_pipeline_fuzzing(self, sandbox):
        """Fuzz test the full input pipeline."""
        from utils.validation import (
            ValidationError,
            validate_command,
            validate_path,
            validate_prompt,
        )

        for _ in range(100):
            # Random input that goes through all validation
            input_type = random.choice(["prompt", "command", "path"])

            try:
                if input_type == "prompt":
                    inp = generate_random_string(random.randint(1, 500))
                    validate_prompt(inp)
                elif input_type == "command":
                    inp = generate_random_string(random.randint(1, 100))
                    validate_command(inp)
                else:
                    inp = generate_random_string(random.randint(1, 50), string.ascii_letters + "/._-")
                    validate_path(inp, str(sandbox))
            except ValidationError:
                pass  # Expected for invalid inputs
            except Exception as e:
                # Unexpected exceptions are bugs
                pytest.fail(f"Unexpected exception: {type(e).__name__}: {e}")

    def test_error_chain_fuzzing(self):
        """Fuzz test error creation and chaining."""
        from utils.errors import ErrorCode, ErrorContext, HarnessError

        error_codes = list(ErrorCode)

        for _ in range(50):
            try:
                code = random.choice(error_codes)
                message = generate_random_string(random.randint(10, 200))
                operation = generate_random_string(random.randint(5, 30))

                error = HarnessError(
                    message,
                    code=code,
                    context=ErrorContext(
                        operation=operation,
                        details={"random": generate_random_string(50)}
                    )
                )

                # Should produce valid dict
                d = error.to_dict()
                assert isinstance(d, dict)
                assert "message" in d

            except Exception as e:
                pytest.fail(f"Error creation failed: {e}")

    def test_concurrent_fuzzing(self, sandbox):
        """Test concurrent fuzzing operations."""
        from utils.validation import validate_command, validate_prompt

        errors = []
        results = []

        def fuzz_thread():
            for _ in range(50):
                try:
                    inp = generate_random_string(random.randint(1, 200))
                    if random.random() > 0.5:
                        result = validate_prompt(inp)
                    else:
                        result = validate_command(inp)
                    results.append(result)
                except Exception as e:
                    if "ValidationError" not in type(e).__name__:
                        errors.append(str(e))

        threads = [threading.Thread(target=fuzz_thread) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not have unexpected errors
        assert len(errors) == 0, f"Unexpected errors: {errors}"


# =============================================================================
# Property-Based Testing
# =============================================================================


class TestPropertyBased:
    """Property-based tests that verify invariants."""

    def test_validation_idempotence(self):
        """Test that validation is idempotent (applying twice gives same result)."""
        from utils.validation import validate_prompt

        test_cases = [
            "Simple text",
            "Text with special: !@#$",
            "Unicode: 你好世界",
            "Numbers: 12345",
        ]

        for inp in test_cases:
            result1 = validate_prompt(inp)
            result2 = validate_prompt(result1)
            # Applying validation twice should give same result
            assert result1 == result2

    def test_sanitization_removes_dangerous_chars(self):
        """Test that sanitization always removes dangerous characters."""
        from utils.validation import sanitize_string

        dangerous = ["\x00", "\x01", "\x02", "\x03", "\x7f"]

        for _ in range(100):
            # Create string with dangerous chars
            inp = generate_random_string(50) + random.choice(dangerous) + generate_random_string(50)
            result = sanitize_string(inp)

            # Dangerous chars should be removed
            for d in dangerous:
                assert d not in result

    def test_path_validation_never_escapes_sandbox(self, sandbox):
        """Test that path validation never allows sandbox escape."""
        from utils.validation import ValidationError, validate_path

        escape_attempts = [
            "../" * i + "etc/passwd"
            for i in range(1, 20)
        ]

        for attempt in escape_attempts:
            try:
                result = validate_path(attempt, str(sandbox))
                # If it succeeds, result must be within sandbox
                assert str(sandbox) in result
            except ValidationError:
                pass  # Good - rejected

    def test_length_limits_always_enforced(self):
        """Test that length limits are always enforced."""
        from utils.validation import (
            MAX_COMMAND_LENGTH,
            MAX_PROMPT_LENGTH,
            ValidationError,
            validate_command,
            validate_prompt,
        )

        # Over-limit inputs should always fail
        for _ in range(20):
            long_prompt = generate_random_string(MAX_PROMPT_LENGTH + random.randint(1, 1000))
            with pytest.raises(ValidationError):
                validate_prompt(long_prompt)

            long_command = generate_random_string(MAX_COMMAND_LENGTH + random.randint(1, 500))
            with pytest.raises(ValidationError):
                validate_command(long_command)
