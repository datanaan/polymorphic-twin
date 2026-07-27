"""Execution loop integration tests (Section 2.4).

Tests the flow: Execute action -> State update -> Core revalidation.

Validates:
1. Execute action -> state update -> Core revalidation
2. Safety_critical violation triggers fallback
3. Identity drift triggers uncertain status
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_execute_action_and_revalidate(
    api_client: AsyncClient, full_twin_data: dict
) -> None:
    """Execute an action, update state, then Core revalidates."""
    # Step 1: Create a TwinObject
    create_resp = await api_client.post(
        "/api/v1/tom/objects",
        json=full_twin_data,
        headers={"x-caller-component": "api", "x-caller-role": "system"},
    )
    assert create_resp.status_code == 201
    obj_id = create_resp.json()["id"]

    # Step 2: Update state (simulating an action execution)
    update_resp = await api_client.patch(
        f"/api/v1/tom/objects/{obj_id}",
        json={
            "state_semantics": {
                "variables": {
                    "temperature": {
                        "name": "temperature",
                        "physical_meaning": "Bearing temperature",
                        "unit": "degC",
                    }
                },
                "current_values": {"temperature": 75.0},
            },
        },
        headers={"x-caller-component": "core", "x-caller-role": "validator"},
    )
    assert update_resp.status_code == 200

    # Step 3: Core revalidates with updated state
    validate_resp = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"temperature": 75.0},
            "constraint_cards": [
                {
                    "constraint_id": "cc-temp-limit",
                    "scenario_criticality": "operational",
                    "rigidity": "absolute",
                    "validation": {
                        "type": "range",
                        "config": {"variable": "temperature", "min": 0, "max": 100},
                    },
                }
            ],
        },
    )
    assert validate_resp.status_code == 200
    validation = validate_resp.json()
    assert validation["passed"] is True


async def test_safety_critical_violation_triggers_fallback(
    api_client: AsyncClient,
) -> None:
    """M2-C2: Safety_critical violation immediately triggers fallback and stops evaluation."""
    # Validate with a safety_critical constraint that will fail
    response = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"temperature": 130.0},
            "constraint_cards": [
                {
                    "constraint_id": "cc-temp-safety",
                    "scenario_criticality": "safety_critical",
                    "rigidity": "absolute",
                    "validation": {
                        "type": "range",
                        "config": {"variable": "temperature", "min": 0, "max": 100},
                    },
                },
                {
                    "constraint_id": "cc-temp-operational",
                    "scenario_criticality": "operational",
                    "rigidity": "absolute",
                    "validation": {
                        "type": "range",
                        "config": {"variable": "temperature", "min": 10, "max": 90},
                    },
                },
            ],
        },
    )
    assert response.status_code == 200
    result = response.json()
    # Safety fallback must be triggered
    assert result["safety_fallback_triggered"] is True
    # Only the safety_critical constraint was evaluated (interrupt after it)
    assert result["evaluated_count"] == 1


async def test_safety_critical_fallback_stops_further_evaluation(
    api_client: AsyncClient,
) -> None:
    """After safety_critical interrupt, no more constraints are checked."""
    response = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"temperature": 150.0},
            "constraint_cards": [
                {
                    "constraint_id": "cc-safety-1",
                    "scenario_criticality": "safety_critical",
                    "rigidity": "absolute",
                    "validation": {
                        "type": "range",
                        "config": {"variable": "temperature", "min": 0, "max": 100},
                    },
                },
                {
                    "constraint_id": "cc-safety-2",
                    "scenario_criticality": "safety_critical",
                    "rigidity": "absolute",
                    "validation": {
                        "type": "range",
                        "config": {"variable": "temperature", "min": -10, "max": 110},
                    },
                },
            ],
        },
    )
    assert response.status_code == 200
    result = response.json()
    # First safety_critical fails -> interrupt -> only 1 evaluated
    assert result["evaluated_count"] == 1
    assert result["safety_fallback_triggered"] is True


async def test_identity_drift_triggers_uncertain(api_client: AsyncClient) -> None:
    """Identity drift beyond tolerance triggers 'uncertain' status."""
    response = await api_client.post(
        "/api/v1/core/identity/check",
        json={
            "obj_id": "obj-drift-test",
            "invariants": {
                "temperature": {"expected": 100.0, "actual": 108.0},  # 8% drift
                "pressure": {"expected": 50.0, "actual": 50.5},  # 1% drift
            },
        },
    )
    assert response.status_code == 200
    result = response.json()
    # 8% drift exceeds default 5% tolerance
    assert result["identity_status"] in ("uncertain", "forked")
    # Temperature drift should be recorded
    assert "temperature" in result["drift_values"]


async def test_identity_confirmed_when_within_tolerance(
    api_client: AsyncClient,
) -> None:
    """Identity confirmed when all invariants are within tolerance."""
    response = await api_client.post(
        "/api/v1/core/identity/check",
        json={
            "obj_id": "obj-ok-test",
            "invariants": {
                "temperature": {"expected": 100.0, "actual": 102.0},  # 2% drift
                "pressure": {"expected": 50.0, "actual": 51.0},  # 2% drift
            },
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["identity_status"] == "confirmed"


async def test_fallback_execution(api_client: AsyncClient) -> None:
    """Direct fallback execution through the API."""
    response = await api_client.post(
        "/api/v1/core/fallback/execute",
        json={
            "obj": {
                "identity": {"id": "obj-fallback-test"},
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
    assert response.status_code == 200
    result = response.json()
    assert result["strategy_used"] == "safe_state"
    assert result["violated_constraint"] == "cc-temp-safety"
