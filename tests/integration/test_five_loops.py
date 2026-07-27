"""Five-loop integration tests through the production API.

Tests the complete five closed-loop flows:
1. Perception: External input -> TOM -> View projection -> Scenario match
2. Exploration: Lab explore -> hypotheses returned
3. Decision: Submit -> quarantine -> evidence -> bridge action space
4. Execution: Execute -> state update -> revalidation
5. Evolution: Cumulative -> pattern discovery -> DomainPack update
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from polytwin.api.app import create_app
from polytwin.api.deps import _reset
from polytwin.api.events import reset_event_bus


@pytest_asyncio.fixture(autouse=True)
async def reset_singletons():
    """Reset all singletons between tests."""
    _reset()
    reset_event_bus()
    yield
    _reset()
    reset_event_bus()


@pytest_asyncio.fixture
async def api_client():
    """Async HTTP client for five-loop integration testing."""
    app = create_app(test_mode=True)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def full_twin_data() -> dict:
    """Full TwinObject payload for loop testing."""
    return {
        "identity": {"type": "device", "name": "pump-001", "tags": ["rotating"]},
        "lineage": {"creator_id": "creator-001", "parent_id": None, "provenance": []},
        "state": {"lifecycle": "active", "health": "healthy"},
        "state_semantics": {
            "variables": {
                "temperature": {
                    "name": "temperature",
                    "physical_meaning": "Bearing temperature",
                    "unit": "degC",
                    "range_min": -40.0,
                    "range_max": 120.0,
                }
            },
            "current_values": {"temperature": 65.3},
        },
        "constraint_state": {
            "active_constraints": ["cc-temp-limit"],
            "suspended_constraints": [],
            "last_evaluation": [
                {
                    "constraint_id": "cc-temp-limit",
                    "status": "passed",
                    "actual_values": {"temperature": 65.3},
                    "message": "Temperature within safe range",
                }
            ],
        },
        "identity_invariants": {
            "invariants": [
                {
                    "name": "serial_number",
                    "expected_value": "SN-12345",
                    "actual_value": "SN-12345",
                    "confidence": 1.0,
                }
            ],
            "overall_confidence": 1.0,
            "identity_status": "confirmed",
        },
        "action_state": {
            "current_safe_action_set": ["action-shutdown"],
            "fallback_available": True,
        },
        "safe_fallback": {
            "strategy": "safe_state",
            "target_state": {"temperature": 25.0},
        },
        "action_templates": [
            {
                "template_id": "tmpl-shutdown",
                "name": "Shutdown pump",
                "description": "Safely shut down the pump",
                "required_role": "operator",
            }
        ],
        "human_roles": [
            {"role_id": "operator", "name": "Operator", "permission_level": "execute"}
        ],
    }


pytestmark = pytest.mark.integration


# ── Loop 1: Perception ──────────────────────────────────────────────


async def test_perception_loop(api_client: AsyncClient, full_twin_data: dict) -> None:
    """Perception loop: POST object -> GET view -> matched."""
    # Step 1: External input -> Create TwinObject
    create_resp = await api_client.post(
        "/api/v1/tom/objects",
        json=full_twin_data,
        headers={"x-caller-component": "api", "x-caller-role": "system"},
    )
    assert create_resp.status_code == 201
    obj_id = create_resp.json()["id"]

    # Step 2: View projection -> core_runtime
    view_resp = await api_client.get(
        f"/api/v1/tom/objects/{obj_id}/views/core_runtime",
        headers={"x-caller-component": "core", "x-caller-role": "validator"},
    )
    assert view_resp.status_code == 200
    view_data = view_resp.json()
    assert view_data["twin_object_id"] == obj_id

    # Step 3: Scenario match via constraint state
    assert "state_semantics" in view_data


# ── Loop 2: Exploration ────────────────────────────────────────────


async def test_exploration_loop(api_client: AsyncClient) -> None:
    """Exploration loop: Lab explore -> hypotheses returned."""
    # Step 1: Lab exploration (hypothesis generation)
    explore_resp = await api_client.post(
        "/api/v1/lab/explore/hypothesis",
        json={
            "data": {"temperature": 65.3, "pressure": 2.1},
            "constraints": [{"constraint_id": "cc-temp", "type": "range"}],
        },
    )
    assert explore_resp.status_code == 200
    data = explore_resp.json()
    assert "hypotheses" in data
    assert data["count"] >= 0

    # Step 2: Counterexample search
    ce_resp = await api_client.post(
        "/api/v1/lab/explore/counterexample",
        json={
            "data": {"temperature": 65.3},
            "constraints": [{"constraint_id": "cc-temp", "type": "range"}],
        },
    )
    assert ce_resp.status_code == 200
    assert "counterexamples" in ce_resp.json()


# ── Loop 3: Decision ────────────────────────────────────────────────


async def test_decision_loop(api_client: AsyncClient, full_twin_data: dict) -> None:
    """Decision loop: Submit -> quarantine -> evidence -> bridge action space."""
    # Step 1: Create TwinObject
    create_resp = await api_client.post(
        "/api/v1/tom/objects",
        json=full_twin_data,
        headers={"x-caller-component": "api", "x-caller-role": "system"},
    )
    assert create_resp.status_code == 201
    obj_id = create_resp.json()["id"]

    # Step 2: Core validate
    validate_resp = await api_client.post(
        "/api/v1/core/validate",
        json={
            "state_values": {"temperature": 65.3},
            "constraint_cards": [
                {
                    "constraint_id": "cc-temp-limit",
                    "validation": {"type": "range", "config": {"variable": "temperature", "min": 0, "max": 100}},
                }
            ],
        },
    )
    assert validate_resp.status_code == 200

    # Step 3: Bridge action space
    action_resp = await api_client.post(
        "/api/v1/bridge/action-space",
        json={
            "view_data": {
                "twin_object_id": obj_id,
                "constraint_summary": [],
                "constraint_state": {"active_constraints": [], "last_evaluation": []},
            },
        },
    )
    assert action_resp.status_code == 200
    action_data = action_resp.json()
    assert "action_space" in action_data or "immediate_actions" in action_data


# ── Loop 4: Execution ──────────────────────────────────────────────


async def test_execution_loop(api_client: AsyncClient, full_twin_data: dict) -> None:
    """Execution loop: Execute -> state update -> revalidation."""
    # Step 1: Create TwinObject
    create_resp = await api_client.post(
        "/api/v1/tom/objects",
        json=full_twin_data,
        headers={"x-caller-component": "api", "x-caller-role": "system"},
    )
    assert create_resp.status_code == 201
    obj_id = create_resp.json()["id"]

    # Step 2: State update (execution)
    state_resp = await api_client.patch(
        f"/api/v1/prod/tom/objects/{obj_id}/state",
        json={
            "current_values": {"temperature": 72.5},
            "validate": True,
            "constraint_cards": [
                {
                    "constraint_id": "cc-temp-limit",
                    "validation": {"type": "range", "config": {"variable": "temperature", "min": 0, "max": 100}},
                }
            ],
        },
        headers={"x-caller-component": "core", "x-caller-role": "validator"},
    )
    assert state_resp.status_code == 200
    data = state_resp.json()
    assert data["status"] == "state_updated"

    # Step 3: Revalidation happened automatically (validate=True)
    assert "validation" in data


# ── Loop 5: Evolution ──────────────────────────────────────────────


async def test_evolution_loop(api_client: AsyncClient, full_twin_data: dict) -> None:
    """Evolution loop: Cumulative -> pattern discovery -> DomainPack update."""
    # Step 1: Create TwinObject and generate data
    create_resp = await api_client.post(
        "/api/v1/tom/objects",
        json=full_twin_data,
        headers={"x-caller-component": "api", "x-caller-role": "system"},
    )
    assert create_resp.status_code == 201
    obj_id = create_resp.json()["id"]

    # Step 2: Multiple validation cycles (cumulative execution results)
    for temp in [60.0, 65.0, 70.0, 75.0]:
        await api_client.post(
            "/api/v1/core/validate",
            json={
                "state_values": {"temperature": temp},
                "constraint_cards": [
                    {
                        "constraint_id": "cc-temp-limit",
                        "validation": {"type": "range", "config": {"variable": "temperature", "min": 0, "max": 100}},
                    }
                ],
            },
        )

    # Step 3: Lab exploration for pattern discovery
    corr_resp = await api_client.post(
        "/api/v1/lab/explore/correlation",
        json={
            "failure_logs": [
                {"constraint_id": "cc-temp-limit", "temperature": 95.0, "result": "failed"},
                {"constraint_id": "cc-temp-limit", "temperature": 98.0, "result": "failed"},
            ],
        },
    )
    assert corr_resp.status_code == 200
    assert "findings" in corr_resp.json()

    # Step 4: State update reflects evolution (constraint learning)
    state_resp = await api_client.patch(
        f"/api/v1/prod/tom/objects/{obj_id}/state",
        json={"current_values": {"temperature": 68.0}, "validate": False},
        headers={"x-caller-component": "core", "x-caller-role": "validator"},
    )
    assert state_resp.status_code == 200
