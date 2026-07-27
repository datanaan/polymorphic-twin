"""Bridge action space generation performance benchmarks (M7-C2).

Targets:
    p50 < 200ms, p95 < 350ms, p99 < 500ms

Measured over 100 iterations using ActionSpaceBuilder.
"""

from __future__ import annotations

import time

import pytest

from polytwin.bridge.action_space import ActionSpaceBuilder

pytestmark = pytest.mark.performance


def _make_complex_view_data(n_constraints: int = 20, n_templates: int = 10) -> dict:
    """Build moderately complex view data for benchmarking."""
    constraint_summary = []
    statuses = ["passed", "passed", "passed", "failed", "uncertain"]
    criticalities = ["safety_critical", "identity_critical", "operational", "informational"]

    for i in range(n_constraints):
        constraint_summary.append({
            "constraint_id": f"cc-perf-{i}",
            "status": statuses[i % len(statuses)],
            "criticality": criticalities[i % len(criticalities)],
            "constraint_id_prohibition_reason": "Test constraint",
        })

    templates = []
    for i in range(n_templates):
        templates.append({
            "action_type_id": f"action-perf-{i}",
            "name": f"Performance test action {i}",
            "description_template": f"Action {i} for benchmarking",
            "typical_prerequisites": [f"prereq-{i}"] if i % 3 == 0 else [],
            "applicable_when": [f"cc-perf-{i}"],
        })

    return {
        "twin_object_id": "obj-perf-test",
        "constraint_summary": constraint_summary,
        "action_templates": templates,
        "human_roles": [
            {"role_id": "operator", "name": "Operator", "permission_level": "execute"},
            {"role_id": "supervisor", "name": "Supervisor", "permission_level": "approve"},
        ],
    }


def _make_domain_pack() -> dict:
    """Build a DomainPack config for benchmarking."""
    return {
        "domain_version": "1.0.0",
        "action_templates": {
            f"action-perf-{i}": {"name": f"Action {i}"}
            for i in range(10)
        },
        "human_roles": [
            {"role_id": "operator", "name": "Operator", "permission_level": "execute"},
        ],
    }


class TestBridgePerformance:
    """Bridge action space generation latency benchmarks."""

    def test_action_space_generation_latency(self) -> None:
        """Bridge action space generation p99 < 500ms.

        M7-C2 target: p50 < 200ms, p95 < 350ms, p99 < 500ms.
        """
        builder = ActionSpaceBuilder()
        view_data = _make_complex_view_data()
        domain_pack = _make_domain_pack()

        # Warm up
        for _ in range(5):
            builder.build(view_data, domain_pack)

        # Measure 100 iterations
        latencies: list[float] = []
        for _ in range(100):
            start = time.monotonic()
            builder.build(view_data, domain_pack)
            elapsed_ms = (time.monotonic() - start) * 1000
            latencies.append(elapsed_ms)

        latencies.sort()
        p50 = latencies[50]
        p95 = latencies[95]
        p99 = latencies[99]

        assert p50 < 200.0, f"p50={p50:.2f}ms exceeds 200ms target"
        assert p95 < 350.0, f"p95={p95:.2f}ms exceeds 350ms target"
        assert p99 < 500.0, f"p99={p99:.2f}ms exceeds 500ms target"

    def test_action_space_empty_constraints(self) -> None:
        """Action space with no constraints should be very fast."""
        builder = ActionSpaceBuilder()
        view_data = {
            "twin_object_id": "obj-empty",
            "constraint_summary": [],
            "action_templates": [],
        }

        latencies: list[float] = []
        for _ in range(100):
            start = time.monotonic()
            builder.build(view_data, None)
            elapsed_ms = (time.monotonic() - start) * 1000
            latencies.append(elapsed_ms)

        latencies.sort()
        p99 = latencies[99]
        assert p99 < 50.0, f"Empty-action-space p99={p99:.2f}ms exceeds 50ms"

    def test_action_space_large_constraint_set(self) -> None:
        """Action space with 50 constraints should still meet targets."""
        builder = ActionSpaceBuilder()
        view_data = _make_complex_view_data(n_constraints=50, n_templates=20)
        domain_pack = _make_domain_pack()

        latencies: list[float] = []
        for _ in range(100):
            start = time.monotonic()
            builder.build(view_data, domain_pack)
            elapsed_ms = (time.monotonic() - start) * 1000
            latencies.append(elapsed_ms)

        latencies.sort()
        p99 = latencies[99]
        assert p99 < 500.0, f"50-constraint p99={p99:.2f}ms exceeds 500ms target"
