"""Production API integration tests.

Tests the production TOM CRUD endpoints, audit queries, and webhook
operations through the full FastAPI stack.
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
    """Async HTTP client for production API testing."""
    app = create_app(test_mode=True)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def auth_headers() -> dict:
    """Create admin auth headers."""
    from polytwin.api.auth import get_key_manager

    mgr = get_key_manager()
    _, raw_key = mgr.create_key(role="admin", name="test-admin")
    return {"Authorization": f"Bearer {raw_key}"}


@pytest.fixture
def viewer_headers() -> dict:
    """Create viewer auth headers."""
    from polytwin.api.auth import get_key_manager

    mgr = get_key_manager()
    _, raw_key = mgr.create_key(role="viewer", name="test-viewer")
    return {"Authorization": f"Bearer {raw_key}"}


@pytest.fixture
def minimal_twin() -> dict:
    """Minimal TwinObject creation payload."""
    return {
        "identity": {"type": "device", "name": "pump-001", "tags": ["test"]},
        "lineage": {"creator_id": "creator-001", "parent_id": None, "provenance": []},
        "state": {"lifecycle": "active", "health": "healthy"},
    }


pytestmark = pytest.mark.integration


# ── TOM Production CRUD ─────────────────────────────────────────────


async def test_crud_cycle(api_client: AsyncClient, minimal_twin: dict) -> None:
    """Full CRUD cycle: create -> read -> update -> read -> delete."""
    # Create
    create_resp = await api_client.post(
        "/api/v1/tom/objects",
        json=minimal_twin,
        headers={"x-caller-component": "api", "x-caller-role": "system"},
    )
    assert create_resp.status_code == 201
    obj_id = create_resp.json()["id"]

    # Read
    read_resp = await api_client.get(
        f"/api/v1/tom/objects/{obj_id}",
        headers={"x-caller-component": "core", "x-caller-role": "validator"},
    )
    assert read_resp.status_code == 200

    # Update
    update_resp = await api_client.patch(
        f"/api/v1/tom/objects/{obj_id}",
        json={"state_semantics": {"variables": {}, "current_values": {"temp": 50.0}}},
        headers={"x-caller-component": "core", "x-caller-role": "validator"},
    )
    assert update_resp.status_code == 200

    # Read again
    read_resp2 = await api_client.get(
        f"/api/v1/tom/objects/{obj_id}",
        headers={"x-caller-component": "core", "x-caller-role": "validator"},
    )
    assert read_resp2.status_code == 200

    # Delete (use request() since httpx delete() does not accept json=)
    delete_resp = await api_client.request(
        "DELETE",
        f"/api/v1/prod/tom/objects/{obj_id}",
        json={"reason": "test cleanup"},
        headers={"x-caller-component": "core", "x-caller-role": "validator"},
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "deleted"


async def test_state_update_with_validation(
    api_client: AsyncClient, minimal_twin: dict
) -> None:
    """State update triggers constraint validation."""
    # Create object
    create_resp = await api_client.post(
        "/api/v1/tom/objects",
        json=minimal_twin,
        headers={"x-caller-component": "api", "x-caller-role": "system"},
    )
    assert create_resp.status_code == 201
    obj_id = create_resp.json()["id"]

    # Update state with validation
    state_resp = await api_client.patch(
        f"/api/v1/prod/tom/objects/{obj_id}/state",
        json={
            "current_values": {"temperature": 65.0},
            "validate": True,
            "constraint_cards": [],
        },
        headers={"x-caller-component": "core", "x-caller-role": "validator"},
    )
    assert state_resp.status_code == 200
    data = state_resp.json()
    assert data["status"] == "state_updated"
    assert "validation" in data


async def test_list_objects(
    api_client: AsyncClient, minimal_twin: dict
) -> None:
    """List objects returns paginated results."""
    # Create a few objects
    for i in range(3):
        twin = {**minimal_twin, "identity": {**minimal_twin["identity"], "name": f"pump-{i:03d}"}}
        await api_client.post(
            "/api/v1/tom/objects",
            json=twin,
            headers={"x-caller-component": "api", "x-caller-role": "system"},
        )

    # List
    list_resp = await api_client.get(
        "/api/v1/prod/tom/objects?limit=2&offset=0",
        headers={"x-caller-component": "api", "x-caller-role": "system"},
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] >= 3
    assert len(data["objects"]) <= 2


# ── Audit Production ────────────────────────────────────────────────


async def test_audit_query_returns_events(
    api_client: AsyncClient, auth_headers: dict
) -> None:
    """Audit query returns events."""
    # Write an audit event via core validate to generate an event
    await api_client.post(
        "/api/v1/core/validate",
        json={"state_values": {"temp": 50.0}, "constraint_cards": []},
    )

    # Query audit
    query_resp = await api_client.get(
        "/api/v1/prod/audit/events",
        headers=auth_headers,
    )
    assert query_resp.status_code == 200
    data = query_resp.json()
    assert "events" in data
    assert "total" in data


async def test_audit_export_returns_json(
    api_client: AsyncClient, auth_headers: dict
) -> None:
    """Audit export returns downloadable JSON."""
    export_resp = await api_client.post(
        "/api/v1/prod/audit/export",
        json={"format": "json"},
        headers=auth_headers,
    )
    assert export_resp.status_code == 200
    data = export_resp.json()
    assert "events" in data
    assert "exported_at" in data


async def test_audit_stats(
    api_client: AsyncClient, auth_headers: dict
) -> None:
    """Audit stats returns grouped counts."""
    stats_resp = await api_client.get(
        "/api/v1/prod/audit/stats",
        headers=auth_headers,
    )
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert "total_events" in data
    assert "by_type" in data


# ── Webhooks ────────────────────────────────────────────────────────


async def test_webhook_register_and_list(
    api_client: AsyncClient, auth_headers: dict
) -> None:
    """Register a webhook and list it."""
    # Register
    reg_resp = await api_client.post(
        "/api/v1/prod/webhooks/register",
        json={
            "url": "https://example.com/webhook",
            "event_types": ["tick", "validation"],
        },
        headers=auth_headers,
    )
    assert reg_resp.status_code == 200
    wh_id = reg_resp.json()["webhook_id"]

    # List
    list_resp = await api_client.get(
        "/api/v1/prod/webhooks/list",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] >= 1

    # Delete
    del_resp = await api_client.delete(
        f"/api/v1/prod/webhooks/{wh_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 200


async def test_publish_event(
    api_client: AsyncClient, auth_headers: dict
) -> None:
    """Publish an event via the webhooks channel."""
    pub_resp = await api_client.post(
        "/api/v1/prod/webhooks/publish",
        json={"event_type": "tick", "data": {"value": 42.0}},
        headers=auth_headers,
    )
    assert pub_resp.status_code == 200
    data = pub_resp.json()
    assert data["status"] == "published"
    assert data["event_type"] == "tick"


async def test_publish_invalid_event_type(
    api_client: AsyncClient, auth_headers: dict
) -> None:
    """Publishing an invalid event type returns 400."""
    pub_resp = await api_client.post(
        "/api/v1/prod/webhooks/publish",
        json={"event_type": "invalid_type", "data": {}},
        headers=auth_headers,
    )
    assert pub_resp.status_code == 400
