"""API performance tests for the production endpoints.

Benchmarks key API operations against latency targets:
- Object creation < 50ms
- View projection < 50ms
- State update + validation < 100ms
- Audit query < 50ms
- WebSocket broadcast < 20ms
"""
from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from polytwin.api.app import create_app
from polytwin.api.deps import _reset
from polytwin.api.events import EventBus, reset_event_bus
from polytwin.api.websocket import ConnectionManager


@pytest_asyncio.fixture(autouse=True)
async def reset_singletons():
    _reset()
    reset_event_bus()
    yield
    _reset()
    reset_event_bus()


@pytest_asyncio.fixture
async def api_client():
    app = create_app(test_mode=True)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def minimal_twin() -> dict:
    return {
        "identity": {"type": "device", "name": "perf-test-001", "tags": ["perf"]},
        "lineage": {"creator_id": "creator-001", "parent_id": None, "provenance": []},
        "state": {"lifecycle": "active", "health": "healthy"},
    }


pytestmark = pytest.mark.performance


class TestObjectCreationPerformance:
    """TwinObject creation latency."""

    @pytest.mark.asyncio
    async def test_single_creation_under_50ms(
        self, api_client: AsyncClient, minimal_twin: dict
    ) -> None:
        start = time.monotonic()
        resp = await api_client.post(
            "/api/v1/tom/objects",
            json=minimal_twin,
            headers={"x-caller-component": "api", "x-caller-role": "system"},
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        assert resp.status_code == 201
        assert elapsed_ms < 50, f"Creation took {elapsed_ms:.1f}ms"

    @pytest.mark.asyncio
    async def test_batch_creation_100_objects_under_2s(
        self, api_client: AsyncClient
    ) -> None:
        start = time.monotonic()
        for i in range(100):
            twin = {
                "identity": {"type": "device", "name": f"batch-{i:04d}", "tags": ["batch"]},
                "lineage": {"creator_id": "creator-001", "parent_id": None, "provenance": []},
            }
            resp = await api_client.post(
                "/api/v1/tom/objects",
                json=twin,
                headers={"x-caller-component": "api", "x-caller-role": "system"},
            )
            assert resp.status_code == 201
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 2000, f"100 creations took {elapsed_ms:.1f}ms"


class TestViewProjectionPerformance:
    """View projection latency."""

    @pytest.mark.asyncio
    async def test_view_projection_under_50ms(
        self, api_client: AsyncClient, minimal_twin: dict
    ) -> None:
        # Create
        create_resp = await api_client.post(
            "/api/v1/tom/objects",
            json=minimal_twin,
            headers={"x-caller-component": "api", "x-caller-role": "system"},
        )
        obj_id = create_resp.json()["id"]

        # Measure view projection
        start = time.monotonic()
        resp = await api_client.get(
            f"/api/v1/tom/objects/{obj_id}/views/core_runtime",
            headers={"x-caller-component": "core", "x-caller-role": "validator"},
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        assert resp.status_code == 200
        assert elapsed_ms < 50, f"View projection took {elapsed_ms:.1f}ms"


class TestStateUpdatePerformance:
    """State update with validation latency."""

    @pytest.mark.asyncio
    async def test_state_update_under_100ms(
        self, api_client: AsyncClient, minimal_twin: dict
    ) -> None:
        create_resp = await api_client.post(
            "/api/v1/tom/objects",
            json=minimal_twin,
            headers={"x-caller-component": "api", "x-caller-role": "system"},
        )
        obj_id = create_resp.json()["id"]

        start = time.monotonic()
        resp = await api_client.patch(
            f"/api/v1/prod/tom/objects/{obj_id}/state",
            json={
                "current_values": {"temperature": 72.5},
                "validate": True,
                "constraint_cards": [],
            },
            headers={"x-caller-component": "core", "x-caller-role": "validator"},
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        assert resp.status_code == 200
        assert elapsed_ms < 100, f"State update took {elapsed_ms:.1f}ms"


class TestEventBusPerformance:
    """EventBus throughput and latency."""

    @pytest.mark.asyncio
    async def test_publish_latency_under_1ms(self) -> None:
        bus = EventBus()
        bus.subscribe("tick")

        start = time.monotonic()
        for i in range(1000):
            await bus.publish("tick", {"seq": i})
        elapsed_ms = (time.monotonic() - start) * 1000

        per_event_us = (elapsed_ms / 1000) * 1000
        assert per_event_us < 1000, f"Per-event latency: {per_event_us:.1f}us"

    @pytest.mark.asyncio
    async def test_fanout_to_100_subscribers(self) -> None:
        bus = EventBus()
        queues = [bus.subscribe("tick") for _ in range(100)]

        start = time.monotonic()
        await bus.publish("tick", {"value": 42})
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 50, f"Fanout to 100 took {elapsed_ms:.1f}ms"

        # All queues should have the event
        for q in queues:
            event = await asyncio.wait_for(q.get(), timeout=1.0)
            assert event["value"] == 42


class TestWebSocketBroadcastPerformance:
    """WebSocket broadcast latency."""

    @pytest.mark.asyncio
    async def test_broadcast_to_10_connections_under_20ms(self) -> None:
        mgr = ConnectionManager()
        for _ in range(10):
            ws = MagicMock()
            ws.send_text = AsyncMock()
            mgr.active_connections.append(ws)

        start = time.monotonic()
        await mgr.broadcast("tick", {"value": 1})
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 20, f"Broadcast to 10 took {elapsed_ms:.1f}ms"
