"""Core constraint validation performance benchmarks (M7-C2).

Targets (10 constraint cards):
    p50 < 5ms, p95 < 8ms, p99 < 10ms

Measured over 1000 iterations using in-memory ConstraintEngine.
"""

from __future__ import annotations

import time

import pytest

from polytwin.core.audit import AuditLogWriter
from polytwin.core.engine import ConstraintEngine
from polytwin.core.fallback import SafetyFallback

pytestmark = pytest.mark.performance


def _make_constraint_cards(n: int) -> list[dict]:
    """Build n constraint cards with range_check validators."""
    return [
        {
            "constraint_id": f"cc-perf-{i}",
            "scenario_criticality": "operational",
            "rigidity": "absolute",
            "validation": {
                "method": "range_check",
                "config": {
                    "variable": "temperature",
                    "min": 0,
                    "max": 100,
                },
            },
        }
        for i in range(n)
    ]


def _make_safety_critical_cards(n: int) -> list[dict]:
    """Build n constraint cards, first is safety_critical."""
    cards = _make_constraint_cards(n)
    cards[0]["scenario_criticality"] = "safety_critical"
    return cards


class TestCorePerformance:
    """Core constraint engine latency benchmarks."""

    @pytest.mark.asyncio
    async def test_constraint_validation_latency_10_cards(self) -> None:
        """Core constraint validation p99 < 10ms with 10 constraint cards.

        M7-C2 target: p50 < 5ms, p95 < 8ms, p99 < 10ms.
        """
        engine = ConstraintEngine(
            audit_writer=AuditLogWriter(),
            fallback_handler=SafetyFallback(),
        )
        cards = _make_constraint_cards(10)
        state_values = {"temperature": 65.0}

        # Warm up
        for _ in range(10):
            await engine.validate(state_values, cards)

        # Measure 1000 iterations
        latencies: list[float] = []
        for _ in range(1000):
            start = time.monotonic()
            await engine.validate(state_values, cards)
            elapsed_ms = (time.monotonic() - start) * 1000
            latencies.append(elapsed_ms)

        latencies.sort()
        p50 = latencies[500]
        p95 = latencies[950]
        p99 = latencies[990]

        assert p50 < 5.0, f"p50={p50:.2f}ms exceeds 5ms target"
        assert p95 < 8.0, f"p95={p95:.2f}ms exceeds 8ms target"
        assert p99 < 10.0, f"p99={p99:.2f}ms exceeds 10ms target"

    @pytest.mark.asyncio
    async def test_constraint_validation_latency_1_card(self) -> None:
        """Single constraint validation should be very fast."""
        engine = ConstraintEngine(
            audit_writer=AuditLogWriter(),
            fallback_handler=SafetyFallback(),
        )
        cards = _make_constraint_cards(1)
        state_values = {"temperature": 65.0}

        # Warm up
        for _ in range(10):
            await engine.validate(state_values, cards)

        latencies: list[float] = []
        for _ in range(1000):
            start = time.monotonic()
            await engine.validate(state_values, cards)
            elapsed_ms = (time.monotonic() - start) * 1000
            latencies.append(elapsed_ms)

        latencies.sort()
        p99 = latencies[990]
        assert p99 < 5.0, f"Single-card p99={p99:.2f}ms exceeds 5ms"

    @pytest.mark.asyncio
    async def test_safety_critical_interrupt_performance(self) -> None:
        """Safety-critical interrupt should not add significant latency."""
        engine = ConstraintEngine(
            audit_writer=AuditLogWriter(),
            fallback_handler=SafetyFallback(),
        )
        cards = _make_safety_critical_cards(10)
        # Trigger safety-critical failure with out-of-range temperature
        state_values = {"temperature": 150.0}

        # Warm up
        for _ in range(10):
            await engine.validate(state_values, cards)

        latencies: list[float] = []
        for _ in range(1000):
            start = time.monotonic()
            await engine.validate(state_values, cards)
            elapsed_ms = (time.monotonic() - start) * 1000
            latencies.append(elapsed_ms)

        latencies.sort()
        p99 = latencies[990]
        # Safety interrupt should be fast (fewer cards evaluated)
        assert p99 < 10.0, f"Safety-interrupt p99={p99:.2f}ms exceeds 10ms"
