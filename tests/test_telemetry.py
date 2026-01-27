"""
Tests for utils/telemetry.py module.

Comprehensive tests for telemetry collection including:
- TelemetryEvent and SessionInfo dataclasses
- TelemetryClient singleton
- Event tracking
- Privacy-respecting sanitization
"""

import os
from unittest.mock import patch

import pytest


class TestTelemetryEvent:
    """Tests for TelemetryEvent dataclass."""

    def test_telemetry_event_creation(self):
        """Test TelemetryEvent creation."""
        from utils.telemetry import TelemetryEvent
        event = TelemetryEvent(
            name="test_event",
            category="test"
        )
        assert event.name == "test_event"
        assert event.category == "test"

    def test_telemetry_event_defaults(self):
        """Test TelemetryEvent default values."""
        from utils.telemetry import TelemetryEvent
        event = TelemetryEvent(name="test", category="test")
        assert event.session_id == ""
        assert event.properties == {}
        assert event.metrics == {}

    def test_telemetry_event_to_dict(self):
        """Test TelemetryEvent to_dict method."""
        from utils.telemetry import TelemetryEvent
        event = TelemetryEvent(
            name="test",
            category="test",
            properties={"key": "value"}
        )
        data = event.to_dict()
        assert data["name"] == "test"
        assert data["properties"]["key"] == "value"


class TestSessionInfo:
    """Tests for SessionInfo dataclass."""

    def test_session_info_create(self):
        """Test SessionInfo.create factory method."""
        from utils.telemetry import SessionInfo
        session = SessionInfo.create(app_version="1.0.0")
        assert session.session_id != ""
        assert session.app_version == "1.0.0"
        assert session.started_at != ""

    def test_session_info_to_dict(self):
        """Test SessionInfo to_dict method."""
        from utils.telemetry import SessionInfo
        session = SessionInfo.create()
        data = session.to_dict()
        assert "session_id" in data
        assert "platform" in data
        assert "python_version" in data


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_generate_anonymous_id(self):
        """Test anonymous ID generation."""
        from utils.telemetry import generate_anonymous_id
        id1 = generate_anonymous_id()
        id2 = generate_anonymous_id()
        assert len(id1) == 8
        assert id1 != id2  # Should be unique

    def test_get_system_info(self):
        """Test system info collection."""
        from utils.telemetry import get_system_info
        info = get_system_info()
        assert "platform" in info
        assert "python_version" in info
        assert "machine" in info


class TestTelemetryClient:
    """Tests for TelemetryClient singleton."""

    def test_telemetry_client_singleton(self):
        """Test TelemetryClient is singleton."""
        from utils.telemetry import TelemetryClient
        # Reset singleton for test
        TelemetryClient._instance = None
        c1 = TelemetryClient()
        c2 = TelemetryClient()
        assert c1 is c2

    def test_telemetry_client_session_id(self):
        """Test TelemetryClient has session ID."""
        from utils.telemetry import TelemetryClient
        TelemetryClient._instance = None
        client = TelemetryClient()
        assert client.session_id != ""

    def test_telemetry_client_enabled_property(self):
        """Test enabled property."""
        from utils.telemetry import TelemetryClient
        TelemetryClient._instance = None
        client = TelemetryClient()
        assert isinstance(client.enabled, bool)

    def test_telemetry_client_enable_disable(self):
        """Test enable/disable methods."""
        from utils.telemetry import TelemetryClient
        TelemetryClient._instance = None
        client = TelemetryClient()
        client.enable()
        assert client.enabled is True
        client.disable()
        assert client.enabled is False

    def test_telemetry_client_track_event_disabled(self):
        """Test tracking event when disabled."""
        from utils.telemetry import TelemetryClient
        TelemetryClient._instance = None
        client = TelemetryClient()
        client.disable()
        initial_events = len(client._events)
        client.track_event("test", "test")
        # Should not add event when disabled
        assert len(client._events) == initial_events

    def test_telemetry_client_track_event_enabled(self):
        """Test tracking event when enabled."""
        from utils.telemetry import TelemetryClient
        TelemetryClient._instance = None
        client = TelemetryClient()
        client.enable()
        initial_events = len(client._events)
        client.track_event("test_event", "test_category")
        assert len(client._events) > initial_events

    def test_telemetry_client_track_command(self):
        """Test tracking command execution."""
        from utils.telemetry import TelemetryClient
        TelemetryClient._instance = None
        client = TelemetryClient()
        client.enable()
        initial_events = len(client._events)
        client.track_command("test_cmd", success=True, duration_ms=100.0)
        assert len(client._events) > initial_events

    def test_telemetry_client_track_llm_request(self):
        """Test tracking LLM request."""
        from utils.telemetry import TelemetryClient
        TelemetryClient._instance = None
        client = TelemetryClient()
        client.enable()
        initial_events = len(client._events)
        client.track_llm_request(
            provider="anthropic",
            model="claude",
            tokens=100,
            duration_ms=500.0,
            success=True
        )
        assert len(client._events) > initial_events

    def test_telemetry_client_track_error(self):
        """Test tracking error."""
        from utils.telemetry import TelemetryClient
        TelemetryClient._instance = None
        client = TelemetryClient()
        client.enable()
        initial_events = len(client._events)
        client.track_error("TestError", "Error message")
        assert len(client._events) > initial_events

    def test_telemetry_client_track_performance(self):
        """Test tracking performance."""
        from utils.telemetry import TelemetryClient
        TelemetryClient._instance = None
        client = TelemetryClient()
        client.enable()
        initial_events = len(client._events)
        client.track_performance("operation", 100.0)
        assert len(client._events) > initial_events

    def test_telemetry_client_sanitize_message(self):
        """Test message sanitization."""
        from utils.telemetry import TelemetryClient
        TelemetryClient._instance = None
        client = TelemetryClient()

        # Test home path sanitization
        msg = "Error in /home/username/file.py"
        sanitized = client._sanitize_message(msg)
        assert "username" not in sanitized
        assert "[user]" in sanitized

        # Test email sanitization
        msg = "Contact user@example.com"
        sanitized = client._sanitize_message(msg)
        assert "user@example.com" not in sanitized
        assert "[email]" in sanitized

        # Test IP sanitization
        msg = "Server at 192.168.1.100"
        sanitized = client._sanitize_message(msg)
        assert "192.168.1.100" not in sanitized
        assert "[ip]" in sanitized

    def test_telemetry_client_get_session_summary(self):
        """Test getting session summary."""
        from utils.telemetry import TelemetryClient
        TelemetryClient._instance = None
        client = TelemetryClient()
        summary = client.get_session_summary()
        assert "session_id" in summary
        assert "enabled" in summary
        assert "buffered_events" in summary

    def test_telemetry_client_flush(self, tmp_path):
        """Test flushing events to file."""
        from utils.telemetry import TelemetryClient
        TelemetryClient._instance = None
        client = TelemetryClient()
        client.enable()
        client.track_event("test", "test")

        with patch("utils.telemetry.TELEMETRY_DIR", tmp_path):
            client.flush()

        # Events should be cleared after flush
        assert len(client._events) == 0

    def test_telemetry_client_end_session(self, tmp_path):
        """Test ending session."""
        from utils.telemetry import TelemetryClient
        TelemetryClient._instance = None
        client = TelemetryClient()
        client.enable()

        with patch("utils.telemetry.TELEMETRY_DIR", tmp_path):
            client.end_session()

        assert len(client._events) == 0


class TestGlobalFunctions:
    """Tests for module-level convenience functions."""

    def test_get_client(self):
        """Test get_client function."""
        from utils.telemetry import TelemetryClient, get_client
        TelemetryClient._instance = None
        client = get_client()
        assert client is not None
        assert isinstance(client, TelemetryClient)

    def test_is_enabled(self):
        """Test is_enabled function."""
        from utils.telemetry import TelemetryClient, is_enabled
        TelemetryClient._instance = None
        result = is_enabled()
        assert isinstance(result, bool)

    def test_track_event_function(self):
        """Test track_event convenience function."""
        from utils.telemetry import TelemetryClient, get_client, track_event
        TelemetryClient._instance = None
        client = get_client()
        client.enable()
        initial_events = len(client._events)
        track_event("test_event", "test_category", {"key": "value"})
        assert len(client._events) > initial_events

    def test_track_command_function(self):
        """Test track_command convenience function."""
        from utils.telemetry import TelemetryClient, get_client, track_command
        TelemetryClient._instance = None
        client = get_client()
        client.enable()
        initial_events = len(client._events)
        track_command("echo hello", success=True, duration_ms=10.0)
        assert len(client._events) > initial_events

    def test_track_llm_request_function(self):
        """Test track_llm_request convenience function."""
        from utils.telemetry import TelemetryClient, get_client, track_llm_request
        TelemetryClient._instance = None
        client = get_client()
        client.enable()
        initial_events = len(client._events)
        track_llm_request(
            provider="test",
            model="test-model",
            tokens=50,
            duration_ms=200.0,
            success=True
        )
        assert len(client._events) > initial_events

    def test_track_error_function(self):
        """Test track_error convenience function."""
        from utils.telemetry import TelemetryClient, get_client, track_error
        TelemetryClient._instance = None
        client = get_client()
        client.enable()
        initial_events = len(client._events)
        track_error("TestError", "Test message", {"context": "test"})
        assert len(client._events) > initial_events

    def test_track_performance_function(self):
        """Test track_performance convenience function."""
        from utils.telemetry import TelemetryClient, get_client, track_performance
        TelemetryClient._instance = None
        client = get_client()
        client.enable()
        initial_events = len(client._events)
        track_performance("test_op", 50.0, {"metadata": "test"})
        assert len(client._events) > initial_events

    def test_get_telemetry_summary(self):
        """Test get_telemetry_summary function."""
        from utils.telemetry import TelemetryClient, get_telemetry_summary
        TelemetryClient._instance = None
        summary = get_telemetry_summary()
        assert "telemetry" in summary
        assert "metrics" in summary

    def test_flush_function(self, tmp_path):
        """Test flush convenience function."""
        from utils.telemetry import TelemetryClient, flush, get_client
        TelemetryClient._instance = None
        client = get_client()
        client.enable()
        client.track_event("test", "test")

        with patch("utils.telemetry.TELEMETRY_DIR", tmp_path):
            flush()

        assert len(client._events) == 0


class TestTelemetryConfiguration:
    """Tests for telemetry configuration."""

    def test_telemetry_enabled_env_var(self):
        """Test TELEMETRY_ENABLED environment variable."""
        # The default should be false
        from utils.telemetry import TELEMETRY_ENABLED
        # Just check it's a boolean
        assert isinstance(TELEMETRY_ENABLED, bool)

    def test_max_buffer_size(self):
        """Test MAX_BUFFER_SIZE configuration."""
        from utils.telemetry import MAX_BUFFER_SIZE
        assert isinstance(MAX_BUFFER_SIZE, int)
        assert MAX_BUFFER_SIZE > 0

    def test_flush_interval(self):
        """Test FLUSH_INTERVAL configuration."""
        from utils.telemetry import FLUSH_INTERVAL
        assert isinstance(FLUSH_INTERVAL, int)
        assert FLUSH_INTERVAL > 0
