"""WebSocket endpoint with ConnectionManager for real-time event streaming.

Supports eight event types:
  tick, validation, action_space, audit, identity, fallback,
  domainpack_update, connection.

The ConnectionManager broadcasts events from the EventBus to all active
WebSocket connections.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from polytwin.api.metrics import WEBSOCKET_CONNECTIONS

router = APIRouter()

# Valid event types that can be broadcast
EVENT_TYPES: set[str] = {
    "tick",
    "validation",
    "action_space",
    "audit",
    "identity",
    "fallback",
    "domainpack_update",
    "connection",
}


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts events."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection and track it."""
        await websocket.accept()
        self.active_connections.append(websocket)
        WEBSOCKET_CONNECTIONS.inc()

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from the active set."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            WEBSOCKET_CONNECTIONS.dec()

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Broadcast an event to all active connections.

        Connections that fail to receive are silently removed.
        """
        payload = json.dumps({"type": event_type, **data})
        stale: list[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload)
            except Exception:
                stale.append(connection)
        for conn in stale:
            self.disconnect(conn)

    @property
    def connection_count(self) -> int:
        """Return the number of active connections."""
        return len(self.active_connections)


# Module-level singleton
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket) -> None:
    """Main WebSocket endpoint.

    Accepts the connection and keeps it alive until the client disconnects.
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# Wire the endpoint into the router
router.websocket("/ws")(websocket_endpoint)
