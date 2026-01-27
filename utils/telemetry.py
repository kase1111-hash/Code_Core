"""
Telemetry collection for Ollama Automation Harness.

Privacy-respecting telemetry for understanding usage patterns and improving
the application. All data collection is opt-in and anonymized.

Features:
- Session tracking (anonymous)
- Event logging
- Performance monitoring
- Error tracking (integrated with Sentry)
- Local-only mode available

Privacy:
- No PII (personally identifiable information) collected
- Anonymous session IDs (not tied to user identity)
- Opt-out via TELEMETRY_ENABLED=false
- All data can be viewed locally before sending
"""

from __future__ import annotations

import json
import os
import platform
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.metrics import get_registry, increment, record

# =============================================================================
# Configuration
# =============================================================================

# Telemetry enabled flag (opt-in)
TELEMETRY_ENABLED = os.environ.get("TELEMETRY_ENABLED", "false").lower() in (
    "true", "1", "yes"
)

# Local storage for telemetry data
TELEMETRY_DIR = Path(os.environ.get("TELEMETRY_DIR", "./logs/telemetry"))

# Maximum events to buffer before flush
MAX_BUFFER_SIZE = int(os.environ.get("TELEMETRY_BUFFER_SIZE", "100"))

# Flush interval in seconds
FLUSH_INTERVAL = int(os.environ.get("TELEMETRY_FLUSH_INTERVAL", "300"))


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TelemetryEvent:
    """A single telemetry event."""

    name: str
    category: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    session_id: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SessionInfo:
    """Anonymous session information."""

    session_id: str
    started_at: str
    platform: str
    python_version: str
    app_version: str
    environment: str

    @classmethod
    def create(cls, app_version: str = "unknown") -> SessionInfo:
        """Create new session info."""
        return cls(
            session_id=generate_anonymous_id(),
            started_at=datetime.utcnow().isoformat(),
            platform=f"{platform.system()} {platform.release()}",
            python_version=platform.python_version(),
            app_version=app_version,
            environment=os.environ.get("ENVIRONMENT", "development"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# =============================================================================
# Helper Functions
# =============================================================================

def generate_anonymous_id() -> str:
    """Generate an anonymous session ID (not tied to user identity)."""
    # Use random UUID - not tied to any user information
    return str(uuid.uuid4())[:8]


def get_system_info() -> dict[str, Any]:
    """Get anonymized system information."""
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "python_version": platform.python_version(),
        "machine": platform.machine(),
    }


# =============================================================================
# Telemetry Client
# =============================================================================

class TelemetryClient:
    """
    Client for collecting and managing telemetry data.

    Thread-safe singleton that handles event collection and storage.
    """

    _instance: TelemetryClient | None = None
    _lock = threading.Lock()

    def __new__(cls) -> TelemetryClient:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._enabled = TELEMETRY_ENABLED
        self._session: SessionInfo | None = None
        self._events: list[TelemetryEvent] = []
        self._event_lock = threading.Lock()
        self._flush_timer: threading.Timer | None = None
        self._initialized = True

        # Initialize session
        self._init_session()

    def _init_session(self) -> None:
        """Initialize telemetry session."""
        try:
            from utils.version import get_version
            app_version = get_version()
        except ImportError:
            app_version = "unknown"

        self._session = SessionInfo.create(app_version)

        # Record session start
        if self._enabled:
            self.track_event("session_started", "lifecycle")

    @property
    def enabled(self) -> bool:
        """Check if telemetry is enabled."""
        return self._enabled

    @property
    def session_id(self) -> str:
        """Get current session ID."""
        return self._session.session_id if self._session else ""

    def enable(self) -> None:
        """Enable telemetry collection."""
        self._enabled = True

    def disable(self) -> None:
        """Disable telemetry collection."""
        self._enabled = False

    def track_event(
        self,
        name: str,
        category: str,
        properties: dict[str, Any] | None = None,
        metrics: dict[str, float] | None = None,
    ) -> None:
        """
        Track a telemetry event.

        Args:
            name: Event name (e.g., "command_executed")
            category: Event category (e.g., "commands", "errors", "performance")
            properties: Optional event properties
            metrics: Optional numeric metrics
        """
        if not self._enabled:
            return

        event = TelemetryEvent(
            name=name,
            category=category,
            session_id=self.session_id,
            properties=properties or {},
            metrics=metrics or {},
        )

        with self._event_lock:
            self._events.append(event)

            # Update metrics
            increment(f"telemetry_events_{category}_total")

            # Auto-flush if buffer is full
            if len(self._events) >= MAX_BUFFER_SIZE:
                self._flush_to_file()

    def track_command(
        self,
        command: str,
        success: bool,
        duration_ms: float | None = None,
    ) -> None:
        """Track command execution."""
        self.track_event(
            name="command_executed",
            category="commands",
            properties={
                "command_type": command,
                "success": success,
            },
            metrics={
                "duration_ms": duration_ms,
            } if duration_ms else {},
        )

        # Update metrics
        increment("commands_executed_total")
        if not success:
            increment("commands_failed_total")
        if duration_ms:
            record("operation_duration_seconds", duration_ms / 1000)

    def track_llm_request(
        self,
        provider: str,
        model: str,
        tokens: int,
        duration_ms: float,
        success: bool,
    ) -> None:
        """Track LLM API request."""
        self.track_event(
            name="llm_request",
            category="llm",
            properties={
                "provider": provider,
                "model": model,
                "success": success,
            },
            metrics={
                "tokens": tokens,
                "duration_ms": duration_ms,
            },
        )

        # Update metrics
        increment("llm_requests_total")
        increment("llm_tokens_total", tokens)
        record("llm_response_time_seconds", duration_ms / 1000)

    def track_error(
        self,
        error_type: str,
        error_message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Track an error (without PII)."""
        # Sanitize error message to remove potential PII
        safe_message = self._sanitize_message(error_message)

        self.track_event(
            name="error_occurred",
            category="errors",
            properties={
                "error_type": error_type,
                "error_message": safe_message[:200],  # Limit length
                **(context or {}),
            },
        )

        increment("requests_errors_total")

    def track_performance(
        self,
        operation: str,
        duration_ms: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Track performance metrics."""
        self.track_event(
            name="performance_metric",
            category="performance",
            properties={
                "operation": operation,
                **(metadata or {}),
            },
            metrics={
                "duration_ms": duration_ms,
            },
        )

        record("operation_duration_seconds", duration_ms / 1000)

    def _sanitize_message(self, message: str) -> str:
        """Remove potential PII from error messages."""
        import re

        # Remove file paths that might contain usernames
        message = re.sub(r"/home/[^/\s]+", "/home/[user]", message)
        message = re.sub(r"/Users/[^/\s]+", "/Users/[user]", message)
        message = re.sub(r"C:\\\\Users\\\\[^\\\\]+", r"C:\\Users\\[user]", message)

        # Remove email-like patterns
        message = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[email]", message)

        # Remove IP addresses
        message = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[ip]", message)

        return message

    def _flush_to_file(self) -> None:
        """Flush events to local file."""
        if not self._events:
            return

        TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = TELEMETRY_DIR / f"events_{self.session_id}_{timestamp}.json"

        with self._event_lock:
            events_to_write = self._events.copy()
            self._events.clear()

        data = {
            "session": self._session.to_dict() if self._session else {},
            "events": [e.to_dict() for e in events_to_write],
            "flushed_at": datetime.utcnow().isoformat(),
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def flush(self) -> None:
        """Manually flush events to storage."""
        self._flush_to_file()

    def get_session_summary(self) -> dict[str, Any]:
        """Get summary of current session."""
        with self._event_lock:
            event_counts = {}
            for event in self._events:
                event_counts[event.category] = event_counts.get(event.category, 0) + 1

        return {
            "session_id": self.session_id,
            "enabled": self._enabled,
            "started_at": self._session.started_at if self._session else None,
            "buffered_events": len(self._events),
            "events_by_category": event_counts,
        }

    def end_session(self) -> None:
        """End the current session and flush data."""
        if self._enabled:
            self.track_event("session_ended", "lifecycle")
        self.flush()


# =============================================================================
# Global Functions
# =============================================================================

_client: TelemetryClient | None = None


def get_client() -> TelemetryClient:
    """Get the global telemetry client."""
    global _client
    if _client is None:
        _client = TelemetryClient()
    return _client


def is_enabled() -> bool:
    """Check if telemetry is enabled."""
    return get_client().enabled


def track_event(
    name: str,
    category: str,
    properties: dict[str, Any] | None = None,
    metrics: dict[str, float] | None = None,
) -> None:
    """Track a telemetry event."""
    get_client().track_event(name, category, properties, metrics)


def track_command(command: str, success: bool, duration_ms: float | None = None) -> None:
    """Track command execution."""
    get_client().track_command(command, success, duration_ms)


def track_llm_request(
    provider: str,
    model: str,
    tokens: int,
    duration_ms: float,
    success: bool,
) -> None:
    """Track LLM API request."""
    get_client().track_llm_request(provider, model, tokens, duration_ms, success)


def track_error(
    error_type: str,
    error_message: str,
    context: dict[str, Any] | None = None,
) -> None:
    """Track an error."""
    get_client().track_error(error_type, error_message, context)


def track_performance(
    operation: str,
    duration_ms: float,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Track performance metrics."""
    get_client().track_performance(operation, duration_ms, metadata)


def get_telemetry_summary() -> dict[str, Any]:
    """Get telemetry summary."""
    client = get_client()
    metrics_registry = get_registry()

    return {
        "telemetry": client.get_session_summary(),
        "metrics": {
            "uptime_seconds": metrics_registry.get_uptime(),
            "total_metrics": len(metrics_registry.get_all_metrics()),
        },
    }


def flush() -> None:
    """Flush telemetry data."""
    get_client().flush()
