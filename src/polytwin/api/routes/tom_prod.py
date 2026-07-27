"""Production TOM endpoints: full CRUD with state update and listing.

Extends the basic TOM routes with production-grade features:
- List/search TwinObjects
- Full state update with constraint validation
- Batch operations
- Event publishing on mutations
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from polytwin.api.deps import get_engine, get_facade, get_store
from polytwin.api.events import get_event_bus
from polytwin.api.metrics import ACTIVE_OBJECTS, VALIDATION_TOTAL
from polytwin.tom.exceptions import PermissionDeniedError
from polytwin.tom.types import CallerIdentity

router = APIRouter()


# ── Request / Response models ───────────────────────────────────────


class StateUpdateRequest(BaseModel):
    """Request body for state update with optional validation."""

    current_values: dict[str, float] = Field(default_factory=dict)
    run_validation: bool = True
    constraint_cards: list[dict] = Field(default_factory=list)
    domain_pack: dict | None = None


class BatchStateUpdateRequest(BaseModel):
    """Request body for batch state updates."""

    updates: dict[str, dict[str, float]] = Field(default_factory=dict)
    constraint_cards: list[dict] = Field(default_factory=list)


class DeleteObjectRequest(BaseModel):
    """Request body for TwinObject deletion."""

    reason: str = ""


# ── Dependency helpers ──────────────────────────────────────────────


def _optional_caller(
    x_caller_component: str = Header(default="api"),
    x_caller_role: str = Header(default="system"),
    x_caller_session: str | None = Header(default=None),
) -> CallerIdentity:
    return CallerIdentity(
        component=x_caller_component,
        role=x_caller_role,
        session_id=x_caller_session,
    )


def _require_caller(
    x_caller_component: str = Header(...),
    x_caller_role: str = Header(...),
    x_caller_session: str | None = Header(default=None),
) -> CallerIdentity:
    return CallerIdentity(
        component=x_caller_component,
        role=x_caller_role,
        session_id=x_caller_session,
    )


def _handle_permission(exc: PermissionDeniedError) -> None:
    raise HTTPException(status_code=403, detail=str(exc))


# ── Routes ──────────────────────────────────────────────────────────


@router.get("/objects")
async def list_objects(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    caller: CallerIdentity = Depends(_optional_caller),  # noqa: B008
) -> dict:
    """List TwinObjects with pagination."""
    store = get_store()
    all_ids = list(store._objects.keys())
    page = all_ids[offset : offset + limit]
    return {
        "objects": [{"id": oid} for oid in page],
        "total": len(all_ids),
        "limit": limit,
        "offset": offset,
    }


@router.put("/objects/{obj_id}")
async def replace_object(
    obj_id: str,
    body: dict,
    caller: CallerIdentity = Depends(_require_caller),  # noqa: B008
) -> dict:
    """Replace a TwinObject entirely (full update)."""
    facade = get_facade()
    try:
        # Check write permission by attempting an update
        await facade.update(obj_id, body, caller)
        ACTIVE_OBJECTS.set(len(get_store()._objects))

        # Publish event
        bus = get_event_bus()
        await bus.publish("domainpack_update", {"object_id": obj_id, "action": "replace"})

        return {"status": "replaced", "id": obj_id}
    except PermissionDeniedError as exc:
        _handle_permission(exc)
        raise


@router.patch("/objects/{obj_id}/state")
async def update_state(
    obj_id: str,
    body: StateUpdateRequest,
    caller: CallerIdentity = Depends(_require_caller),  # noqa: B008
) -> dict:
    """Update state values with optional constraint validation."""
    facade = get_facade()

    # Build the state update payload
    changes = {
        "state_semantics": {"current_values": body.current_values},
    }

    try:
        await facade.update(obj_id, changes, caller)
    except PermissionDeniedError as exc:
        _handle_permission(exc)
        raise

    validation_result = None
    if body.run_validation:
        engine = get_engine()
        if body.domain_pack:
            engine.domain_pack = body.domain_pack
        result = await engine.validate(
            state_values=body.current_values,
            constraint_cards=body.constraint_cards,
        )
        validation_result = result.model_dump()
        status_str = "passed" if result.passed else "failed"
        VALIDATION_TOTAL.labels(result=status_str).inc()

    # Publish tick event
    bus = get_event_bus()
    await bus.publish("tick", {"object_id": obj_id, "state": body.current_values})

    return {
        "status": "state_updated",
        "id": obj_id,
        "validation": validation_result,
    }


@router.post("/objects/batch-state")
async def batch_state_update(
    body: BatchStateUpdateRequest,
    caller: CallerIdentity = Depends(_optional_caller),  # noqa: B008
) -> dict:
    """Update state for multiple TwinObjects at once."""
    facade = get_facade()
    results: list[dict] = []
    engine = get_engine()

    for obj_id, values in body.updates.items():
        changes = {"state_semantics": {"current_values": values}}
        try:
            await facade.update(obj_id, changes, caller)
            result = await engine.validate(
                state_values=values,
                constraint_cards=body.constraint_cards,
            )
            results.append({
                "id": obj_id,
                "status": "updated",
                "validation": result.model_dump(),
            })
        except Exception as exc:
            results.append({"id": obj_id, "status": "error", "detail": str(exc)})

    return {"results": results, "count": len(results)}


@router.delete("/objects/{obj_id}")
async def delete_object(
    obj_id: str,
    body: DeleteObjectRequest | None = None,
    caller: CallerIdentity = Depends(_optional_caller),  # noqa: B008
) -> dict:
    """Soft-delete a TwinObject."""
    facade = get_facade()

    changes = {"state": {"lifecycle": "deleted"}}
    try:
        await facade.update(obj_id, changes, caller)
    except PermissionDeniedError as exc:
        _handle_permission(exc)
        raise

    ACTIVE_OBJECTS.set(len(get_store()._objects))

    # Publish event
    bus = get_event_bus()
    await bus.publish("connection", {"object_id": obj_id, "action": "deleted"})

    return {"status": "deleted", "id": obj_id}
