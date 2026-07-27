"""Webhook registration, event bus integration, and batch state endpoints.

Provides webhook registration/management, manual event publishing,
and batch state update endpoints.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from polytwin.api.auth import APIKey, get_current_user
from polytwin.api.events import get_event_bus
from polytwin.api.rbac import check_permission
from polytwin.api.websocket import EVENT_TYPES
from polytwin.api.websocket import manager as ws_manager

router = APIRouter()


# ── Models ──────────────────────────────────────────────────────────


class WebhookRegistration(BaseModel):
    """Request body for registering a webhook."""

    url: str
    event_types: list[str] = Field(default_factory=list)
    secret: str = ""


class WebhookResponse(BaseModel):
    """Webhook registration response."""

    webhook_id: str
    url: str
    event_types: list[str]


class PublishEventRequest(BaseModel):
    """Request body for manually publishing an event."""

    event_type: str
    data: dict = Field(default_factory=dict)


class BatchStateRequest(BaseModel):
    """Request body for batch state update via webhooks channel."""

    updates: list[dict] = Field(default_factory=list)


# ── In-memory webhook store ─────────────────────────────────────────

_webhooks: dict[str, dict[str, Any]] = {}


# ── Routes ──────────────────────────────────────────────────────────


@router.post("/register")
async def register_webhook(
    body: WebhookRegistration,
    current_user: APIKey = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Register a new webhook endpoint.

    Requires admin role.
    """
    if not check_permission(current_user.role, "domainpack:manage"):
        raise HTTPException(status_code=403, detail="Admin permission required")

    webhook_id = f"wh_{uuid.uuid4().hex[:12]}"
    _webhooks[webhook_id] = {
        "webhook_id": webhook_id,
        "url": body.url,
        "event_types": body.event_types,
        "secret": body.secret,
        "active": True,
    }

    return {"webhook_id": webhook_id, "url": body.url, "event_types": body.event_types}


@router.get("/list")
async def list_webhooks(
    current_user: APIKey = Depends(get_current_user),  # noqa: B008
) -> dict:
    """List all registered webhooks."""
    if not check_permission(current_user.role, "audit:read"):
        raise HTTPException(status_code=403, detail="audit:read permission required")

    return {
        "webhooks": list(_webhooks.values()),
        "count": len(_webhooks),
    }


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user: APIKey = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Delete a registered webhook."""
    if not check_permission(current_user.role, "domainpack:manage"):
        raise HTTPException(status_code=403, detail="Admin permission required")

    if webhook_id not in _webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")

    del _webhooks[webhook_id]
    return {"status": "deleted", "webhook_id": webhook_id}


@router.post("/publish")
async def publish_event(
    body: PublishEventRequest,
    current_user: APIKey = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Manually publish an event to the event bus and WebSocket connections.

    Validates event_type against the known set.
    """
    if body.event_type not in EVENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type: {body.event_type}. "
            f"Valid types: {sorted(EVENT_TYPES)}",
        )

    # Publish to EventBus
    bus = get_event_bus()
    await bus.publish(body.event_type, body.data)

    # Broadcast to WebSocket connections
    await ws_manager.broadcast(body.event_type, body.data)

    return {
        "status": "published",
        "event_type": body.event_type,
        "subscribers": bus.subscriber_count(body.event_type),
        "ws_connections": ws_manager.connection_count,
    }


@router.post("/batch-state")
async def batch_state_update(
    body: BatchStateRequest,
    current_user: APIKey = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Batch state update with event publishing.

    Accepts multiple state updates and publishes events for each.
    """
    if not check_permission(current_user.role, "tom:write"):
        raise HTTPException(status_code=403, detail="tom:write permission required")

    bus = get_event_bus()
    results: list[dict] = []

    for update in body.updates:
        obj_id = update.get("object_id", "unknown")
        state = update.get("state", {})
        await bus.publish("tick", {"object_id": obj_id, "state": state})
        results.append({"object_id": obj_id, "status": "published"})

    return {"results": results, "count": len(results)}
