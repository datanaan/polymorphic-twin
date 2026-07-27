"""Production audit endpoints: query, export, and statistics.

Provides richer audit querying than the basic Core audit route,
including time-range filtering, statistics, and JSON export.
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from polytwin.api.auth import APIKey, get_current_user
from polytwin.api.deps import get_audit
from polytwin.api.rbac import check_permission

router = APIRouter()


# ── Request / Response models ───────────────────────────────────────


class AuditExportRequest(BaseModel):
    """Request body for audit export."""

    event_type: str | None = None
    actor: str | None = None
    format: str = "json"


class AuditStatsRequest(BaseModel):
    """Request body for audit statistics."""

    group_by: str = "event_type"


# ── Routes ──────────────────────────────────────────────────────────


@router.get("/events")
async def query_audit_events(
    event_type: str | None = None,
    actor: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: APIKey = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Query audit events with filtering and pagination.

    Requires the audit:read permission.
    """
    if not check_permission(current_user.role, "audit:read"):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="audit:read permission required")

    audit = get_audit()
    filters: dict = {}
    if event_type:
        filters["event_type"] = event_type
    if actor:
        filters["actor"] = actor

    events = await audit.query(filters or None)

    # Time-range filtering
    if start_time or end_time:
        filtered = []
        for evt in events:
            ts = evt.get("timestamp", "")
            if start_time and ts < start_time:
                continue
            if end_time and ts > end_time:
                continue
            filtered.append(evt)
        events = filtered

    total = len(events)
    page = events[offset : offset + limit]

    return {
        "events": page,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/export")
async def export_audit_events(
    body: AuditExportRequest,
    current_user: APIKey = Depends(get_current_user),  # noqa: B008
) -> JSONResponse:
    """Export audit events as a downloadable JSON document.

    Requires the audit:export permission.
    """
    if not check_permission(current_user.role, "audit:export"):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="audit:export permission required")

    audit = get_audit()
    filters: dict = {}
    if body.event_type:
        filters["event_type"] = body.event_type
    if body.actor:
        filters["actor"] = body.actor

    events = await audit.query(filters or None)

    export_data = {
        "exported_at": datetime.now(UTC).isoformat(),
        "filters": filters,
        "count": len(events),
        "events": events,
    }

    return JSONResponse(
        content=export_data,
        headers={"Content-Disposition": "attachment; filename=audit_export.json"},
    )


@router.get("/stats")
async def audit_statistics(
    current_user: APIKey = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Return audit event statistics grouped by type.

    Requires the audit:read permission.
    """
    if not check_permission(current_user.role, "audit:read"):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="audit:read permission required")

    audit = get_audit()
    events = await audit.query(None)

    by_type: dict[str, int] = {}
    by_actor: dict[str, int] = {}
    for evt in events:
        et = evt.get("event_type", "unknown")
        actor = evt.get("actor", "unknown")
        by_type[et] = by_type.get(et, 0) + 1
        by_actor[actor] = by_actor.get(actor, 0) + 1

    return {
        "total_events": len(events),
        "by_type": by_type,
        "by_actor": by_actor,
    }
