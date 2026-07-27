"""Prometheus metrics for the Polymorphic-Twin API.

Defines eight metrics covering validation, safety fallbacks, Bridge
operations, active objects, WebSocket connections, and audit events.
Gracefully degrades to no-op stubs when prometheus_client is not installed.
"""
from __future__ import annotations

try:
    from prometheus_client import Counter, Gauge, Histogram

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False


if METRICS_AVAILABLE:
    VALIDATION_TOTAL = Counter(
        "pt_validation_total",
        "Total constraint validations",
        ["result"],
    )
    VALIDATION_LATENCY = Histogram(
        "pt_validation_latency_seconds",
        "Validation latency",
    )
    SAFETY_FALLBACK_TOTAL = Counter(
        "pt_safety_fallback_total",
        "Safety fallback triggers",
    )
    BRIDGE_ACTION_SPACE_TOTAL = Counter(
        "pt_bridge_action_space_total",
        "Bridge action space generations",
    )
    BRIDGE_LATENCY = Histogram(
        "pt_bridge_latency_seconds",
        "Bridge latency",
    )
    ACTIVE_OBJECTS = Gauge(
        "pt_active_objects",
        "Active TwinObjects",
    )
    WEBSOCKET_CONNECTIONS = Gauge(
        "pt_websocket_connections",
        "Active WebSocket connections",
    )
    AUDIT_EVENTS_TOTAL = Counter(
        "pt_audit_events_total",
        "Total audit events",
        ["event_type"],
    )
else:
    # No-op stubs when prometheus_client is not installed
    class _Stub:
        """No-op replacement for any Prometheus metric."""

        def labels(self, *a: object) -> _Stub:
            return self

        def observe(self, *a: object) -> None:
            pass

        def inc(self, *a: object) -> None:
            pass

        def dec(self, *a: object) -> None:
            pass

        def set(self, *a: object) -> None:
            pass

    VALIDATION_TOTAL = _Stub()  # type: ignore[assignment]
    VALIDATION_LATENCY = _Stub()  # type: ignore[assignment]
    SAFETY_FALLBACK_TOTAL = _Stub()  # type: ignore[assignment]
    BRIDGE_ACTION_SPACE_TOTAL = _Stub()  # type: ignore[assignment]
    BRIDGE_LATENCY = _Stub()  # type: ignore[assignment]
    ACTIVE_OBJECTS = _Stub()  # type: ignore[assignment]
    WEBSOCKET_CONNECTIONS = _Stub()  # type: ignore[assignment]
    AUDIT_EVENTS_TOTAL = _Stub()  # type: ignore[assignment]
