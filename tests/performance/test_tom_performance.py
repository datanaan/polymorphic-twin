"""TOM view projection and object creation performance benchmarks (M7-C2).

Targets:
    View projection:    p50 < 10ms, p95 < 30ms, p99 < 50ms  (5 views x 1000 times)
    TOM create object:  p50 < 20ms, p95 < 40ms, p99 < 50ms  (500 times)
    Snapshot creation:  p50 < 30ms, p95 < 50ms, p99 < 80ms  (200 times)
"""

from __future__ import annotations

import time
from datetime import UTC

import pytest

from polytwin.tom.domain_models import TwinObjectInternal
from polytwin.tom.facade import InMemoryTwinObjectStore, TwinObjectFacade
from polytwin.tom.snapshot import create_snapshot_data, generate_snapshot_id
from polytwin.tom.types import CallerIdentity, ViewType
from polytwin.tom.views import (
    AuditView,
    BridgeDecisionView,
    CoreCertificationView,
    CoreRuntimeView,
    LabExplorationView,
)

pytestmark = pytest.mark.performance

_CALLER_API = CallerIdentity(component="api", role="system")
_CALLER_CORE = CallerIdentity(component="core", role="validator")
_CALLER_CORE_CERT = CallerIdentity(component="core", role="certifier")
_CALLER_LAB = CallerIdentity(component="lab", role="explorer")
_CALLER_BRIDGE = CallerIdentity(component="bridge", role="decision_maker")
_CALLER_AUDIT = CallerIdentity(component="audit", role="auditor")


def _make_full_internal() -> TwinObjectInternal:
    """Build a full TwinObjectInternal for benchmarking."""
    return TwinObjectInternal(
        identity={
            "type": "device",
            "name": "bench-obj",
            "tags": ["benchmark"],
        },
        lineage={
            "creator_id": "bench-creator",
            "parent_id": None,
            "provenance": [],
        },
        state={"lifecycle": "active", "health": "healthy"},
        state_semantics={
            "variables": {
                "temperature": {
                    "name": "temperature",
                    "physical_meaning": "Bearing temperature",
                    "unit": "degC",
                    "range_min": -40.0,
                    "range_max": 120.0,
                },
            },
            "current_values": {"temperature": 65.3},
        },
        constraint_state={
            "active_constraints": ["cc-temp-limit", "cc-pressure-limit"],
            "suspended_constraints": [],
            "last_evaluation": [
                {
                    "constraint_id": "cc-temp-limit",
                    "status": "passed",
                    "actual_values": {"temperature": 65.3},
                    "message": "OK",
                }
            ],
        },
        identity_invariants={
            "invariants": [
                {
                    "name": "serial",
                    "expected_value": "SN-001",
                    "actual_value": "SN-001",
                    "confidence": 1.0,
                }
            ],
            "overall_confidence": 1.0,
            "identity_status": "confirmed",
        },
        model_governance={
            "active_links": ["model-v1"],
            "qualification_history": [],
            "active_certificates": [],
        },
        knowledge_state={
            "admitted_lab_evidence": ["ev-001"],
            "pending_submissions": [],
        },
        action_state={
            "current_safe_action_set": ["action-shutdown"],
            "fallback_available": True,
        },
        audit_trail={
            "events": [
                {
                    "event_type": "created",
                    "actor": "system",
                    "detail": {},
                }
            ],
        },
        action_templates=[
            {
                "template_id": "tmpl-shutdown",
                "name": "Shutdown",
                "description": "Safe shutdown",
                "required_role": "operator",
            }
        ],
        human_roles=[
            {"role_id": "operator", "name": "Operator", "permission_level": "execute"}
        ],
        safe_fallback={"strategy": "safe_state", "target_state": {"temperature": 25.0}},
        rigidity_rules=[
            {"constraint_id": "cc-temp-limit", "rigidity": "absolute"}
        ],
    )


class TestTOMPerformance:
    """TOM view projection, object creation, and snapshot benchmarks."""

    @pytest.mark.asyncio
    async def test_view_projection_latency(self) -> None:
        """TOM view projection p99 < 50ms (5 views x 1000 iterations).

        M7-C2 target: p50 < 10ms, p95 < 30ms, p99 < 50ms.
        """
        internal = _make_full_internal()
        views_to_project = [
            (CoreRuntimeView, "core_runtime"),
            (CoreCertificationView, "core_certification"),
            (BridgeDecisionView, "bridge_decision"),
            (LabExplorationView, "lab_exploration"),
            (AuditView, "audit"),
        ]

        latencies: list[float] = []
        for _ in range(1000):
            for view_cls, _name in views_to_project:
                start = time.monotonic()
                view_cls.from_internal(internal)
                elapsed_ms = (time.monotonic() - start) * 1000
                latencies.append(elapsed_ms)

        latencies.sort()
        total = len(latencies)
        p50 = latencies[int(total * 0.50)]
        p95 = latencies[int(total * 0.95)]
        p99 = latencies[int(total * 0.99)]

        assert p50 < 10.0, f"p50={p50:.2f}ms exceeds 10ms target"
        assert p95 < 30.0, f"p95={p95:.2f}ms exceeds 30ms target"
        assert p99 < 50.0, f"p99={p99:.2f}ms exceeds 50ms target"

    @pytest.mark.asyncio
    async def test_create_object_latency(self) -> None:
        """TOM create object p99 < 50ms (500 iterations).

        M7-C2 target: p50 < 20ms, p95 < 40ms, p99 < 50ms.
        """
        store = InMemoryTwinObjectStore()
        facade = TwinObjectFacade(store)

        obj_data = {
            "identity": {"type": "device", "name": "bench-create", "tags": []},
            "lineage": {"creator_id": "bench", "parent_id": None, "provenance": []},
            "state_semantics": {
                "variables": {
                    "temperature": {
                        "name": "temperature",
                        "physical_meaning": "Temp",
                        "unit": "degC",
                        "range_min": -40.0,
                        "range_max": 120.0,
                    },
                },
                "current_values": {"temperature": 65.0},
            },
        }

        latencies: list[float] = []
        for i in range(500):
            data = {**obj_data, "identity": {**obj_data["identity"], "name": f"bench-{i}"}}
            start = time.monotonic()
            await facade.create(data, _CALLER_API)
            elapsed_ms = (time.monotonic() - start) * 1000
            latencies.append(elapsed_ms)

        latencies.sort()
        p50 = latencies[250]
        p95 = latencies[475]
        p99 = latencies[495]

        assert p50 < 20.0, f"p50={p50:.2f}ms exceeds 20ms target"
        assert p95 < 40.0, f"p95={p95:.2f}ms exceeds 40ms target"
        assert p99 < 50.0, f"p99={p99:.2f}ms exceeds 50ms target"

    @pytest.mark.asyncio
    async def test_snapshot_creation_latency(self) -> None:
        """Snapshot creation p99 < 80ms (200 iterations).

        M7-C2 target: p50 < 30ms, p95 < 50ms, p99 < 80ms.
        """
        from datetime import datetime

        internal = _make_full_internal()

        latencies: list[float] = []
        for _i in range(200):
            ts = datetime.now(UTC)
            start = time.monotonic()
            generate_snapshot_id(internal, ts)
            create_snapshot_data(internal)
            elapsed_ms = (time.monotonic() - start) * 1000
            latencies.append(elapsed_ms)

        latencies.sort()
        p50 = latencies[100]
        p95 = latencies[190]
        p99 = latencies[198]

        assert p50 < 30.0, f"p50={p50:.2f}ms exceeds 30ms target"
        assert p95 < 50.0, f"p95={p95:.2f}ms exceeds 50ms target"
        assert p99 < 80.0, f"p99={p99:.2f}ms exceeds 80ms target"

    @pytest.mark.asyncio
    async def test_facade_get_view_through_facade(self) -> None:
        """Full facade get_view (with access matrix check) latency."""
        store = InMemoryTwinObjectStore()
        facade = TwinObjectFacade(store)

        obj_id = await facade.create(
            {
                "identity": {"type": "device", "name": "facade-perf", "tags": []},
                "lineage": {"creator_id": "bench", "parent_id": None, "provenance": []},
            },
            _CALLER_API,
        )

        # Warm up
        for _ in range(10):
            await facade.get_view(obj_id, ViewType.CORE_RUNTIME, _CALLER_CORE)

        latencies: list[float] = []
        for _ in range(1000):
            start = time.monotonic()
            await facade.get_view(obj_id, ViewType.CORE_RUNTIME, _CALLER_CORE)
            elapsed_ms = (time.monotonic() - start) * 1000
            latencies.append(elapsed_ms)

        latencies.sort()
        p99 = latencies[990]
        assert p99 < 50.0, f"Facade get_view p99={p99:.2f}ms exceeds 50ms target"
