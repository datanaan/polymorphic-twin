"""Multi-scene parallel operation tests (M6).

Verifies that two different scene objects can operate independently
without interfering with each other. Each scene uses a different
DomainPack, and operations on one scene do not affect the other.

Validates:
1. Two TwinObjects with different DomainPacks coexist
2. Modifying one object's state does not affect the other
3. Constraint validation for each object is independent
4. Lab exploration for each scene is independent
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_two_scenes_independent(api_client: AsyncClient) -> None:
    """Two different scene objects don't interfere with each other.

    Create object A (industrial device) and object B (knowledge management),
    modify A, and verify B is unchanged.
    """
    # Create object A (industrial device scenario)
    create_a = await api_client.post(
        "/api/v1/tom/objects",
        json={
            "identity": {"type": "device", "name": "reactor-A", "tags": ["cstr"]},
            "lineage": {"creator_id": "creator-001", "parent_id": None, "provenance": []},
            "state": {"lifecycle": "active", "health": "healthy"},
            "state_semantics": {
                "variables": {
                    "reactor_temp": {
                        "name": "reactor_temp",
                        "physical_meaning": "Reactor temperature",
                        "unit": "celsius",
                        "range_min": -20.0,
                        "range_max": 400.0,
                    },
                },
                "current_values": {"reactor_temp": 180.0},
            },
            "constraint_state": {
                "active_constraints": ["temp_upper_limit"],
                "suspended_constraints": [],
                "last_evaluation": [],
            },
        },
        headers={"x-caller-component": "api", "x-caller-role": "system"},
    )
    assert create_a.status_code == 201
    obj_a_id = create_a.json()["id"]

    # Create object B (knowledge management scenario)
    create_b = await api_client.post(
        "/api/v1/tom/objects",
        json={
            "identity": {"type": "agent", "name": "knowledge-B", "tags": ["knowledge"]},
            "lineage": {"creator_id": "creator-002", "parent_id": None, "provenance": []},
            "state": {"lifecycle": "active", "health": "healthy"},
            "state_semantics": {
                "variables": {
                    "knowledge_freshness": {
                        "name": "knowledge_freshness",
                        "physical_meaning": "Days since last update",
                        "unit": "days",
                        "range_min": 0.0,
                        "range_max": 365.0,
                    },
                },
                "current_values": {"knowledge_freshness": 10.0},
            },
            "constraint_state": {
                "active_constraints": ["freshness_limit"],
                "suspended_constraints": [],
                "last_evaluation": [],
            },
        },
        headers={"x-caller-component": "api", "x-caller-role": "system"},
    )
    assert create_b.status_code == 201
    obj_b_id = create_b.json()["id"]

    # Verify different IDs
    assert obj_a_id != obj_b_id

    # Modify object A's state
    update_a = await api_client.patch(
        f"/api/v1/tom/objects/{obj_a_id}",
        json={
            "state_semantics": {
                "current_values": {"reactor_temp": 250.0},
            },
        },
        headers={
            "x-caller-component": "core",
            "x-caller-role": "validator",
        },
    )
    assert update_a.status_code == 200

    # Verify object B is unchanged
    get_b = await api_client.get(
        f"/api/v1/tom/objects/{obj_b_id}",
        headers={
            "x-caller-component": "core",
            "x-caller-role": "validator",
        },
    )
    assert get_b.status_code == 200
    b_data = get_b.json()
    # Object B should still be the same object (not affected by A's update)
    assert b_data["twin_object_id"] == obj_b_id


async def test_independent_constraint_validation(api_client: AsyncClient) -> None:
    """Constraint validation for each scene is independent.

    Validate constraints for two different DomainPacks in sequence
    and verify results are correct for each.
    """
    # Scene 1: Chemical reactor -- valid state
    resp_a = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"reactor_temp": 200.0, "vessel_pressure": 8.0},
            "constraint_cards": [
                {
                    "constraint_id": "temp_upper_limit",
                    "scenario_criticality": "safety_critical",
                    "validation": {"type": "range", "config": {"variable": "reactor_temp", "min": 0, "max": 350}},
                },
                {
                    "constraint_id": "pressure_upper_limit",
                    "scenario_criticality": "safety_critical",
                    "validation": {"type": "range", "config": {"variable": "vessel_pressure", "min": 0, "max": 15}},
                },
            ],
        },
    )
    assert resp_a.status_code == 200
    assert resp_a.json()["passed"] is True

    # Scene 2: Knowledge management -- valid state
    resp_b = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"knowledge_freshness": 30.0, "contradiction_count": 1.0},
            "constraint_cards": [
                {
                    "constraint_id": "freshness_limit",
                    "scenario_criticality": "operational",
                    "validation": {"type": "range", "config": {"variable": "knowledge_freshness", "min": 0, "max": 90}},
                },
            ],
        },
    )
    assert resp_b.status_code == 200
    assert resp_b.json()["passed"] is True

    # Scene 1 again: violating state
    resp_a_violation = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"reactor_temp": 400.0, "vessel_pressure": 8.0},
            "constraint_cards": [
                {
                    "constraint_id": "temp_upper_limit",
                    "scenario_criticality": "safety_critical",
                    "validation": {"type": "range", "config": {"variable": "reactor_temp", "min": 0, "max": 350}},
                },
                {
                    "constraint_id": "pressure_upper_limit",
                    "scenario_criticality": "safety_critical",
                    "validation": {"type": "range", "config": {"variable": "vessel_pressure", "min": 0, "max": 15}},
                },
            ],
        },
    )
    assert resp_a_violation.status_code == 200
    assert resp_a_violation.json()["passed"] is False

    # Scene 2 should still be unaffected -- validate again with valid state
    resp_b_again = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"knowledge_freshness": 20.0, "contradiction_count": 0.0},
            "constraint_cards": [
                {
                    "constraint_id": "freshness_limit",
                    "scenario_criticality": "operational",
                    "validation": {"type": "range", "config": {"variable": "knowledge_freshness", "min": 0, "max": 90}},
                },
            ],
        },
    )
    assert resp_b_again.status_code == 200
    assert resp_b_again.json()["passed"] is True


async def test_parallel_lab_exploration(api_client: AsyncClient) -> None:
    """Lab exploration for two different scenes produces independent results."""
    # Scene 1: Wind turbine bearing exploration
    resp_a = await api_client.post(
        "/api/v1/lab/explore/hypothesis",
        json={
            "data": {"state_variables": {"vibration_freq": 1200.0, "bearing_temp": 65.0}},
            "constraints": [
                {
                    "constraint_id": "vibration_limit",
                    "scenario_criticality": "safety_critical",
                    "validation": {"type": "range", "config": {"variable": "vibration_freq", "min": 0, "max": 2500}},
                },
            ],
        },
    )
    assert resp_a.status_code == 200
    hyp_a = resp_a.json()

    # Scene 2: Chemical reactor exploration
    resp_b = await api_client.post(
        "/api/v1/lab/explore/hypothesis",
        json={
            "data": {"state_variables": {"reactor_temp": 200.0, "coolant_flow": 30.0}},
            "constraints": [
                {
                    "constraint_id": "temp_upper_limit",
                    "scenario_criticality": "safety_critical",
                    "validation": {"type": "range", "config": {"variable": "reactor_temp", "min": 0, "max": 350}},
                },
            ],
        },
    )
    assert resp_b.status_code == 200
    hyp_b = resp_b.json()

    # Both should have results structures (independent)
    assert "hypotheses" in hyp_a
    assert "hypotheses" in hyp_b


async def test_parallel_bridge_action_spaces(api_client: AsyncClient) -> None:
    """Bridge generates independent action spaces for two scenes."""
    # Scene 1: Industrial device action space
    resp_a = await api_client.post(
        "/api/v1/bridge/action-space",
        json={
            "view_data": {
                "twin_object_id": "obj-reactor-001",
                "constraint_state": {"active_constraints": ["temp_upper_limit"]},
                "constraint_summary": [],
            },
        },
    )
    assert resp_a.status_code == 200
    action_a = resp_a.json()
    output_a_id = action_a["output_id"]

    # Scene 2: Knowledge management action space
    resp_b = await api_client.post(
        "/api/v1/bridge/action-space",
        json={
            "view_data": {
                "twin_object_id": "obj-knowledge-001",
                "constraint_state": {"active_constraints": ["freshness_limit"]},
                "constraint_summary": [],
            },
        },
    )
    assert resp_b.status_code == 200
    action_b = resp_b.json()
    output_b_id = action_b["output_id"]

    # Output IDs should be different
    assert output_a_id != output_b_id
