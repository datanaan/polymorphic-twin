"""Performance benchmarks for M5-C2 and M5-C3.

M5-C2: Safety fallback < 200ms
M5-C3: Bridge action space generation < 1s
"""

from __future__ import annotations

import time

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.performance]


async def test_safety_fallback_under_200ms(api_client: AsyncClient) -> None:
    """M5-C2: Safety fallback execution must complete in under 200ms."""
    # Warm up (first call may include import overhead)
    await api_client.post(
        "/api/v1/core/fallback/execute",
        json={
            "obj": {"identity": {"id": "warmup"}},
            "constraint_result": {"violated_constraint": "cc-warmup"},
            "domain_pack": {},
        },
    )

    # Measure multiple runs
    times_ms: list[float] = []
    for _ in range(10):
        start = time.monotonic()
        response = await api_client.post(
            "/api/v1/core/fallback/execute",
            json={
                "obj": {
                    "identity": {"id": "obj-perf-test"},
                    "state_semantics": {"current_values": {"temperature": 130.0}},
                },
                "constraint_result": {"violated_constraint": "cc-temp-safety"},
                "domain_pack": {
                    "safe_fallback": {
                        "unavailable_action": "safe_state",
                        "target_state": {"temperature": 25.0},
                    }
                },
            },
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        times_ms.append(elapsed_ms)

        assert response.status_code == 200

    avg_ms = sum(times_ms) / len(times_ms)
    max_ms = max(times_ms)

    assert avg_ms < 200, f"Average fallback time {avg_ms:.1f}ms exceeds 200ms"
    assert max_ms < 200, f"Max fallback time {max_ms:.1f}ms exceeds 200ms"


async def test_bridge_action_space_under_1s(api_client: AsyncClient) -> None:
    """M5-C3: Bridge action space generation must complete in under 1s."""
    # Warm up
    await api_client.post(
        "/api/v1/bridge/action-space",
        json={"view_data": {"twin_object_id": "warmup"}},
    )

    # Build a moderately complex view
    view_data = {
        "twin_object_id": "obj-perf-test",
        "constraint_state": {
            "active_constraints": [
                "cc-temp-limit",
                "cc-pressure-limit",
                "cc-vibration-limit",
                "cc-flow-rate",
                "cc-power-consumption",
            ],
        },
        "constraint_summary": [
            {
                "constraint_id": "cc-temp-limit",
                "status": "passed",
                "criticality": "safety_critical",
            },
            {
                "constraint_id": "cc-pressure-limit",
                "status": "passed",
                "criticality": "safety_critical",
            },
            {
                "constraint_id": "cc-vibration-limit",
                "status": "uncertain",
                "criticality": "operational",
            },
            {
                "constraint_id": "cc-flow-rate",
                "status": "failed",
                "criticality": "operational",
            },
            {
                "constraint_id": "cc-power-consumption",
                "status": "passed",
                "criticality": "informational",
            },
        ],
        "action_templates": [
            {"action_type_id": "adjust-flow", "name": "Adjust flow rate"},
            {"action_type_id": "reduce-vibration", "name": "Reduce vibration"},
            {"action_type_id": "observe", "name": "Observe system"},
        ],
        "human_roles": [
            {"role_id": "operator", "name": "Operator", "permission_level": "execute"},
            {"role_id": "supervisor", "name": "Supervisor", "permission_level": "approve"},
        ],
    }

    domain_pack = {
        "domain_version": "1.0.0",
        "action_templates": {
            "adjust": {"name": "Adjust parameters"},
            "observe": {"name": "Observe state"},
        },
    }

    times_ms: list[float] = []
    for _ in range(10):
        start = time.monotonic()
        response = await api_client.post(
            "/api/v1/bridge/action-space",
            json={"view_data": view_data, "domain_pack": domain_pack},
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        times_ms.append(elapsed_ms)

        assert response.status_code == 200

    avg_ms = sum(times_ms) / len(times_ms)
    max_ms = max(times_ms)

    assert avg_ms < 1000, f"Average action space time {avg_ms:.1f}ms exceeds 1s"
    assert max_ms < 1000, f"Max action space time {max_ms:.1f}ms exceeds 1s"


async def test_core_validation_under_200ms(api_client: AsyncClient) -> None:
    """Core constraint validation should complete in under 200ms."""
    constraint_cards = [
        {
            "constraint_id": f"cc-constraint-{i}",
            "scenario_criticality": "operational",
            "rigidity": "absolute",
            "validation": {
                "type": "range",
                "config": {"variable": "temperature", "min": 0, "max": 100},
            },
        }
        for i in range(10)
    ]

    # Warm up
    await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"temperature": 50.0},
            "constraint_cards": constraint_cards[:1],
        },
    )

    times_ms: list[float] = []
    for _ in range(10):
        start = time.monotonic()
        response = await api_client.post(
            "/api/v1/core/validate",
            json={
                "state_values": {"temperature": 50.0},
                "constraint_cards": constraint_cards,
            },
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        times_ms.append(elapsed_ms)

        assert response.status_code == 200

    avg_ms = sum(times_ms) / len(times_ms)
    assert avg_ms < 200, f"Average validation time {avg_ms:.1f}ms exceeds 200ms"


async def test_view_projection_performance(api_client: AsyncClient, full_twin_data: dict) -> None:
    """TOM view projection should be fast under repeated access."""
    # Create object
    create_resp = await api_client.post(
        "/api/v1/tom/objects",
        json=full_twin_data,
        headers={"x-caller-component": "api", "x-caller-role": "system"},
    )
    obj_id = create_resp.json()["id"]

    # Warm up
    await api_client.get(
        f"/api/v1/tom/objects/{obj_id}/views/core_runtime",
        headers={"x-caller-component": "core", "x-caller-role": "validator"},
    )

    times_ms: list[float] = []
    for _ in range(50):
        start = time.monotonic()
        response = await api_client.get(
            f"/api/v1/tom/objects/{obj_id}/views/core_runtime",
            headers={"x-caller-component": "core", "x-caller-role": "validator"},
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        times_ms.append(elapsed_ms)
        assert response.status_code == 200

    avg_ms = sum(times_ms) / len(times_ms)
    p95_ms = sorted(times_ms)[int(len(times_ms) * 0.95)]

    assert avg_ms < 20, f"Average view projection {avg_ms:.1f}ms exceeds 20ms"
    assert p95_ms < 50, f"P95 view projection {p95_ms:.1f}ms exceeds 50ms"
