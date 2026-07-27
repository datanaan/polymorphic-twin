"""TOM routes: TwinObject CRUD, view projection, and snapshot management.

All operations enforce the view-isolation access matrix through the
TwinObjectFacade.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from polytwin.api.deps import get_facade
from polytwin.tom.exceptions import PermissionDeniedError
from polytwin.tom.types import CallerIdentity, ViewType

router = APIRouter()


# ── Request / Response models ───────────────────────────────────────


class CreateObjectRequest(BaseModel):
    """Request body for creating a new TwinObject."""

    identity: dict = Field(default_factory=dict)
    lineage: dict = Field(default_factory=dict)
    state: dict = Field(default_factory=dict)
    state_semantics: dict | None = None
    constraint_state: dict | None = None
    identity_invariants: dict | None = None
    model_governance: dict | None = None
    knowledge_state: dict | None = None
    action_state: dict | None = None
    audit_trail: dict | None = None
    action_templates: list[dict] = Field(default_factory=list)
    human_roles: list[dict] = Field(default_factory=list)
    safe_fallback: dict | None = None
    rigidity_rules: list[dict] = Field(default_factory=list)
    audit_benchmark_reference: str | None = None
    hidden_challenge_set_reference: str | None = None
    public_eval_set_reference: str | None = None
    change_history: dict | None = None


class UpdateObjectRequest(BaseModel):
    """Request body for partially updating a TwinObject."""

    state_semantics: dict | None = None
    constraint_state: dict | None = None
    identity_invariants: dict | None = None
    model_governance: dict | None = None
    knowledge_state: dict | None = None
    action_state: dict | None = None


# ── Dependency: caller identity from headers ─────────────────────────


def _require_caller(
    x_caller_component: str = Header(...),
    x_caller_role: str = Header(...),
    x_caller_session: str | None = Header(default=None),
) -> CallerIdentity:
    """Extract caller identity from required headers."""
    return CallerIdentity(
        component=x_caller_component,
        role=x_caller_role,
        session_id=x_caller_session,
    )


def _optional_caller(
    x_caller_component: str = Header(default="api"),
    x_caller_role: str = Header(default="system"),
    x_caller_session: str | None = Header(default=None),
) -> CallerIdentity:
    """Extract caller identity from optional headers (defaults to api/system)."""
    return CallerIdentity(
        component=x_caller_component,
        role=x_caller_role,
        session_id=x_caller_session,
    )


# ── Helpers ─────────────────────────────────────────────────────────


def _handle_permission(exc: PermissionDeniedError) -> None:
    """Convert a PermissionDeniedError to an HTTPException."""
    raise HTTPException(status_code=403, detail=str(exc))


# ── Routes ──────────────────────────────────────────────────────────


@router.post("/objects", status_code=201)
async def create_object(
    body: CreateObjectRequest,
    caller: CallerIdentity = Depends(_optional_caller),  # noqa: B008
) -> dict:
    """Create a new TwinObject. Only core_runtime and api can create."""
    facade = get_facade()
    try:
        obj_data = body.model_dump(exclude_none=True)
        obj_id = await facade.create(obj_data, caller)
        return {"id": obj_id}
    except PermissionDeniedError as exc:
        _handle_permission(exc)
        raise  # unreachable, keeps type checker happy


@router.get("/objects/{obj_id}")
async def get_object(
    obj_id: str,
    caller: CallerIdentity = Depends(_optional_caller),  # noqa: B008
) -> dict:
    """Get a TwinObject by ID. Returns a default view based on caller."""
    facade = get_facade()

    # Determine default view for caller
    component = facade._caller_component(caller)
    default_view = _DEFAULT_VIEW_MAP.get(component, ViewType.CORE_RUNTIME)

    try:
        view = await facade.get_view(obj_id, default_view, caller)
        return view.model_dump()
    except PermissionDeniedError as exc:
        _handle_permission(exc)
        raise


@router.get("/objects/{obj_id}/views/{view_type}")
async def get_view(
    obj_id: str,
    view_type: str,
    caller: CallerIdentity = Depends(_require_caller),  # noqa: B008
) -> dict:
    """Get a projected view of a TwinObject.

    Enforces the 12-rule access matrix based on caller identity.
    """
    try:
        vt = ViewType(view_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown view type: {view_type}",
        ) from None

    facade = get_facade()
    try:
        view = await facade.get_view(obj_id, vt, caller)
        return view.model_dump()
    except PermissionDeniedError as exc:
        _handle_permission(exc)
        raise


@router.patch("/objects/{obj_id}")
async def update_object(
    obj_id: str,
    body: UpdateObjectRequest,
    caller: CallerIdentity = Depends(_require_caller),  # noqa: B008
) -> dict:
    """Partially update a TwinObject. Only core_runtime and bridge can write."""
    changes = body.model_dump(exclude_none=True)
    if not changes:
        return {"status": "no_changes"}

    facade = get_facade()
    try:
        await facade.update(obj_id, changes, caller)
        return {"status": "updated"}
    except PermissionDeniedError as exc:
        _handle_permission(exc)
        raise


@router.post("/objects/{obj_id}/snapshots", status_code=201)
async def create_snapshot(
    obj_id: str,
    caller: CallerIdentity = Depends(_optional_caller),  # noqa: B008
) -> dict:
    """Create an immutable snapshot of a TwinObject."""
    facade = get_facade()
    try:
        snapshot_id = await facade.create_snapshot(obj_id, caller)
        return {"snapshot_id": snapshot_id}
    except PermissionDeniedError as exc:
        _handle_permission(exc)
        raise


@router.get("/objects/{obj_id}/snapshots")
async def get_snapshot(
    obj_id: str,
    snapshot_id: str | None = None,
    caller: CallerIdentity = Depends(_optional_caller),  # noqa: B008
) -> dict:
    """Retrieve a snapshot. Only core and audit can read snapshots."""
    facade = get_facade()
    try:
        if snapshot_id is None:
            return {"snapshots": []}
        snap = await facade.get_snapshot(snapshot_id, caller)
        return {"snapshot_id": snapshot_id, "data": snap.model_dump()}
    except PermissionDeniedError as exc:
        _handle_permission(exc)
        raise


# ── Default view mapping ────────────────────────────────────────────

_DEFAULT_VIEW_MAP: dict[str, ViewType] = {
    "core_runtime": ViewType.CORE_RUNTIME,
    "core_certification": ViewType.CORE_CERTIFICATION,
    "lab": ViewType.LAB_EXPLORATION,
    "bridge": ViewType.BRIDGE_DECISION,
    "audit": ViewType.AUDIT,
    "api": ViewType.CORE_RUNTIME,
}
