"""Tests for WebSocket ConnectionManager and endpoint."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from polytwin.api.websocket import EVENT_TYPES, ConnectionManager


class TestConnectionManager:
    """ConnectionManager manages WebSocket connections."""

    def test_initial_state_empty(self) -> None:
        mgr = ConnectionManager()
        assert mgr.active_connections == []
        assert mgr.connection_count == 0

    @pytest.mark.asyncio
    async def test_connect_adds_connection(self) -> None:
        mgr = ConnectionManager()
        ws = MagicMock()
        ws.accept = AsyncMock()
        await mgr.connect(ws)
        assert ws in mgr.active_connections
        assert mgr.connection_count == 1

    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(self) -> None:
        mgr = ConnectionManager()
        ws = MagicMock()
        ws.accept = AsyncMock()
        await mgr.connect(ws)
        ws.accept.assert_awaited_once()

    def test_disconnect_removes_connection(self) -> None:
        mgr = ConnectionManager()
        ws = MagicMock()
        mgr.active_connections.append(ws)
        mgr.disconnect(ws)
        assert ws not in mgr.active_connections
        assert mgr.connection_count == 0

    def test_disconnect_unknown_connection_no_error(self) -> None:
        mgr = ConnectionManager()
        ws = MagicMock()
        # Should not raise
        mgr.disconnect(ws)

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self) -> None:
        mgr = ConnectionManager()
        ws1 = MagicMock()
        ws1.send_text = AsyncMock()
        ws2 = MagicMock()
        ws2.send_text = AsyncMock()
        mgr.active_connections = [ws1, ws2]

        await mgr.broadcast("tick", {"object_id": "obj-1", "value": 42.0})

        expected = json.dumps({"type": "tick", "object_id": "obj-1", "value": 42.0})
        ws1.send_text.assert_awaited_once_with(expected)
        ws2.send_text.assert_awaited_once_with(expected)

    @pytest.mark.asyncio
    async def test_broadcast_removes_stale_connections(self) -> None:
        mgr = ConnectionManager()
        ws_ok = MagicMock()
        ws_ok.send_text = AsyncMock()
        ws_bad = MagicMock()
        ws_bad.send_text = AsyncMock(side_effect=Exception("connection closed"))
        mgr.active_connections = [ws_ok, ws_bad]

        await mgr.broadcast("validation", {"result": "passed"})

        assert ws_ok in mgr.active_connections
        assert ws_bad not in mgr.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_empty_connections(self) -> None:
        mgr = ConnectionManager()
        # Should not raise
        await mgr.broadcast("tick", {"value": 1})


class TestEventTypes:
    """Validate the set of supported event types."""

    def test_eight_event_types(self) -> None:
        assert len(EVENT_TYPES) == 8

    def test_required_event_types(self) -> None:
        expected = {
            "tick", "validation", "action_space", "audit",
            "identity", "fallback", "domainpack_update", "connection",
        }
        assert expected == EVENT_TYPES


class TestWebsocketEndpoint:
    """websocket_endpoint handles connect/disconnect lifecycle."""

    @pytest.mark.asyncio
    async def test_endpoint_disconnect_cleanup(self) -> None:
        """When client disconnects, connection is removed from manager."""
        mgr = ConnectionManager()
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.receive_text = AsyncMock(side_effect=Exception("disconnect"))

        # Simulate the endpoint logic directly
        await mgr.connect(ws)
        assert ws in mgr.active_connections

        # Simulate disconnect
        mgr.disconnect(ws)
        assert ws not in mgr.active_connections
