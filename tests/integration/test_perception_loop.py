"""Perception loop integration tests (Section 2.1).

Tests the flow: External input -> TOM -> View projection -> Scenario match.

Validates:
1. TwinObject creation returns 201
2. View projection with authorized caller returns 200
3. View projection with unauthorized caller returns 403
4. Response time for view projection < 50ms
"""

from __future__ import annotations

import time

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_create_twin_object_201(
    api_client: AsyncClient, minimal_twin_data: dict
) -> None:
    """Create TwinObject -> 201 with valid data and authorized caller."""
    response = await api_client.post(
        "/api/v1/tom/objects",
        json=minimal_twin_data,
        headers={
            "x-caller-component": "api",
            "x-caller-role": "system",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["id"]  # non-empty ID


async def test_get_core_runtime_view_200(
    api_client: AsyncClient, full_twin_data: dict
) -> None:
    """Get view with core_runtime caller -> 200."""
    # Create object first
    create_resp = await api_client.post(
        "/api/v1/tom/objects",
        json=full_twin_data,
        headers={
            "x-caller-component": "api",
            "x-caller-role": "system",
        },
    )
    assert create_resp.status_code == 201
    obj_id = create_resp.json()["id"]

    # Get core_runtime view
    response = await api_client.get(
        f"/api/v1/tom/objects/{obj_id}/views/core_runtime",
        headers={
            "x-caller-component": "core",
            "x-caller-role": "validator",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["twin_object_id"] == obj_id
    # core_runtime view should contain state_semantics
    assert data.get("state_semantics") is not None


async def test_lab_cannot_access_core_runtime_view_403(
    api_client: AsyncClient, full_twin_data: dict
) -> None:
    """Lab caller tries to access core_runtime view -> 403.

    This verifies view isolation: lab -> core_runtime = DENY (rule 9).
    """
    # Create object
    create_resp = await api_client.post(
        "/api/v1/tom/objects",
        json=full_twin_data,
        headers={
            "x-caller-component": "api",
            "x-caller-role": "system",
        },
    )
    assert create_resp.status_code == 201
    obj_id = create_resp.json()["id"]

    # Lab tries to access core_runtime view
    response = await api_client.get(
        f"/api/v1/tom/objects/{obj_id}/views/core_runtime",
        headers={
            "x-caller-component": "lab",
            "x-caller-role": "explorer",
        },
    )
    assert response.status_code == 403


async def test_lab_can_access_lab_exploration_view_200(
    api_client: AsyncClient, full_twin_data: dict
) -> None:
    """Lab caller accesses lab_exploration view -> 200.

    This verifies: lab -> lab_exploration = ALLOW (rule 8).
    """
    # Create object
    create_resp = await api_client.post(
        "/api/v1/tom/objects",
        json=full_twin_data,
        headers={
            "x-caller-component": "api",
            "x-caller-role": "system",
        },
    )
    assert create_resp.status_code == 201
    obj_id = create_resp.json()["id"]

    # Lab accesses its own view
    response = await api_client.get(
        f"/api/v1/tom/objects/{obj_id}/views/lab_exploration",
        headers={
            "x-caller-component": "lab",
            "x-caller-role": "explorer",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["twin_object_id"] == obj_id


async def test_view_projection_response_time(
    api_client: AsyncClient, full_twin_data: dict
) -> None:
    """View projection response time < 50ms."""
    # Create object
    create_resp = await api_client.post(
        "/api/v1/tom/objects",
        json=full_twin_data,
        headers={
            "x-caller-component": "api",
            "x-caller-role": "system",
        },
    )
    assert create_resp.status_code == 201
    obj_id = create_resp.json()["id"]

    # Measure view projection time
    start = time.monotonic()
    response = await api_client.get(
        f"/api/v1/tom/objects/{obj_id}/views/core_runtime",
        headers={
            "x-caller-component": "core",
            "x-caller-role": "validator",
        },
    )
    elapsed_ms = (time.monotonic() - start) * 1000

    assert response.status_code == 200
    assert elapsed_ms < 50, f"View projection took {elapsed_ms:.1f}ms (>50ms)"


async def test_bridge_can_access_bridge_decision_view(
    api_client: AsyncClient, full_twin_data: dict
) -> None:
    """Bridge caller accesses bridge_decision view -> 200."""
    # Create object
    create_resp = await api_client.post(
        "/api/v1/tom/objects",
        json=full_twin_data,
        headers={
            "x-caller-component": "api",
            "x-caller-role": "system",
        },
    )
    obj_id = create_resp.json()["id"]

    response = await api_client.get(
        f"/api/v1/tom/objects/{obj_id}/views/bridge_decision",
        headers={
            "x-caller-component": "bridge",
            "x-caller-role": "decision_maker",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "constraint_summary" in data
    assert "action_templates" in data
