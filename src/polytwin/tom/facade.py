"""TwinObject facade with 12-rule view access matrix and permission enforcement.

The facade is the single entry point for all TwinObject operations.  It
enforces the view-isolation access matrix at runtime, ensuring that each
caller component can only see the projections it is authorised for.

Backing store is an in-memory dict (swappable for PostgreSQL later).
"""

from __future__ import annotations

import copy
from typing import Any, Protocol

from polytwin.tom.domain_models import TwinObjectInternal
from polytwin.tom.exceptions import PermissionDeniedError
from polytwin.tom.types import CallerIdentity, ViewType
from polytwin.tom.views import (
    AuditView,
    BridgeDecisionView,
    CoreCertificationView,
    CoreRuntimeView,
    LabExplorationView,
)

# ── Type aliases ────────────────────────────────────────────────────

ViewSnapshot = (
    CoreRuntimeView
    | CoreCertificationView
    | BridgeDecisionView
    | LabExplorationView
    | AuditView
)

ChangeRecord = dict[str, Any]

# ── View projection mapping ─────────────────────────────────────────

_VIEW_PROJECTORS: dict[ViewType, type[ViewSnapshot]] = {
    ViewType.CORE_RUNTIME: CoreRuntimeView,
    ViewType.CORE_CERTIFICATION: CoreCertificationView,
    ViewType.BRIDGE_DECISION: BridgeDecisionView,
    ViewType.LAB_EXPLORATION: LabExplorationView,
    ViewType.AUDIT: AuditView,
}

# ── Access matrix (12 rules) ────────────────────────────────────────
#
# Maps (caller_component, view_type) -> bool (True = ALLOW)

_ACCESS_MATRIX: dict[tuple[str, ViewType], bool] = {
    # 1. core_runtime -> CORE_RUNTIME  = ALLOW
    ("core_runtime", ViewType.CORE_RUNTIME): True,
    # 2. core_runtime -> BRIDGE_DECISION  = ALLOW
    ("core_runtime", ViewType.BRIDGE_DECISION): True,
    # 3. core_runtime -> LAB_EXPLORATION  = ALLOW
    ("core_runtime", ViewType.LAB_EXPLORATION): True,
    # 4. core_runtime -> CORE_CERTIFICATION  = DENY
    ("core_runtime", ViewType.CORE_CERTIFICATION): False,
    # 5. core_runtime -> AUDIT  = DENY
    ("core_runtime", ViewType.AUDIT): False,
    # 6. core_certification -> CORE_RUNTIME  = ALLOW
    ("core_certification", ViewType.CORE_RUNTIME): True,
    # 7. core_certification -> CORE_CERTIFICATION  = ALLOW
    ("core_certification", ViewType.CORE_CERTIFICATION): True,
    # 8. lab -> LAB_EXPLORATION  = ALLOW
    ("lab", ViewType.LAB_EXPLORATION): True,
    # 9. lab -> CORE_RUNTIME  = DENY
    ("lab", ViewType.CORE_RUNTIME): False,
    # 10. lab -> CORE_CERTIFICATION  = DENY
    ("lab", ViewType.CORE_CERTIFICATION): False,
    # 11. bridge -> BRIDGE_DECISION  = ALLOW
    ("bridge", ViewType.BRIDGE_DECISION): True,
    # 12. audit -> AUDIT  = ALLOW
    ("audit", ViewType.AUDIT): True,
}

# ── Write permission matrix ─────────────────────────────────────────

_WRITE_ALLOWED_COMPONENTS: frozenset[str] = frozenset({
    "core_runtime",
    "bridge",
})

_CREATE_ALLOWED_COMPONENTS: frozenset[str] = frozenset({
    "core_runtime",
    "api",
})

_SNAPSHOT_ALLOWED_COMPONENTS: frozenset[str] = frozenset({
    "core_runtime",
    "core_certification",
    "audit",
})

_CHANGE_HISTORY_COMPONENTS: frozenset[str] = frozenset({
    "audit",
})


# ── Store protocol ──────────────────────────────────────────────────


class TwinObjectStore(Protocol):
    """Minimal interface that any backing store must implement."""

    async def put(self, obj: TwinObjectInternal) -> None: ...
    async def get(self, obj_id: str) -> TwinObjectInternal | None: ...
    async def put_snapshot(self, snapshot_id: str, obj: TwinObjectInternal) -> None: ...
    async def get_snapshot(self, snapshot_id: str) -> TwinObjectInternal | None: ...
    async def append_change_record(self, obj_id: str, record: ChangeRecord) -> None: ...
    async def get_change_history(self, obj_id: str) -> list[ChangeRecord]: ...


class InMemoryTwinObjectStore:
    """In-memory dict-based store for testing and development.

    Stores deep copies on write and returns deep copies on read so that
    callers cannot mutate stored state without going through the facade.
    """

    def __init__(self) -> None:
        self._objects: dict[str, TwinObjectInternal] = {}
        self._snapshots: dict[str, TwinObjectInternal] = {}
        self._change_history: dict[str, list[ChangeRecord]] = {}

    async def put(self, obj: TwinObjectInternal) -> None:
        self._objects[obj.identity.id] = copy.deepcopy(obj)

    async def get(self, obj_id: str) -> TwinObjectInternal | None:
        obj = self._objects.get(obj_id)
        return copy.deepcopy(obj) if obj is not None else None

    async def put_snapshot(self, snapshot_id: str, obj: TwinObjectInternal) -> None:
        self._snapshots[snapshot_id] = copy.deepcopy(obj)

    async def get_snapshot(self, snapshot_id: str) -> TwinObjectInternal | None:
        obj = self._snapshots.get(snapshot_id)
        return copy.deepcopy(obj) if obj is not None else None

    async def append_change_record(self, obj_id: str, record: ChangeRecord) -> None:
        self._change_history.setdefault(obj_id, []).append(record)

    async def get_change_history(self, obj_id: str) -> list[ChangeRecord]:
        return list(self._change_history.get(obj_id, []))


# ── Facade ──────────────────────────────────────────────────────────


class TwinObjectFacade:
    """Enforces view isolation at runtime.

    Every access to a TwinObject must go through this facade.  It checks
    the caller's identity against the 12-rule access matrix before
    projecting and returning the appropriate frozen view.
    """

    def __init__(self, store: TwinObjectStore | InMemoryTwinObjectStore) -> None:
        self._store = store

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _caller_component(caller: CallerIdentity) -> str:
        """Normalise caller component for matrix lookup.

        The component field in CallerIdentity is generic (e.g. "core").
        The access matrix uses more specific names like "core_runtime"
        and "core_certification".  We use ``role`` to disambiguate:
        - component="core", role="validator"    -> "core_runtime"
        - component="core", role="certifier"    -> "core_certification"
        - component="lab"                       -> "lab"
        - component="bridge"                    -> "bridge"
        - component="audit"                     -> "audit"
        - component="api"                       -> "api"
        """
        comp = caller.component
        role = caller.role
        if comp == "core":
            if role == "certifier":
                return "core_certification"
            return "core_runtime"
        return comp

    def _check_view_access(
        self, caller: CallerIdentity, view_type: ViewType
    ) -> None:
        """Raise PermissionDeniedError if the caller cannot access the view."""
        component = self._caller_component(caller)
        key = (component, view_type)
        allowed = _ACCESS_MATRIX.get(key)
        if allowed is None:
            raise PermissionDeniedError(
                caller=component,
                view_type=view_type.value,
                reason="No access rule defined for this caller/view combination",
            )
        if not allowed:
            raise PermissionDeniedError(
                caller=component,
                view_type=view_type.value,
                reason="Access denied by view isolation policy",
            )

    # ── public API ───────────────────────────────────────────────────

    async def create(self, obj_data: dict, caller: CallerIdentity) -> str:
        """Create a new TwinObject. Only core_runtime and api can create."""
        component = self._caller_component(caller)
        if component not in _CREATE_ALLOWED_COMPONENTS:
            raise PermissionDeniedError(
                caller=component,
                view_type="create",
                reason="Only core_runtime and api can create TwinObjects",
            )
        obj = TwinObjectInternal(**obj_data)
        await self._store.put(obj)
        return obj.identity.id

    async def get_view(
        self, obj_id: str, view_type: ViewType, caller: CallerIdentity
    ) -> ViewSnapshot:
        """Get a projected view of a TwinObject.

        Enforces the 12-rule access matrix.  Returns a frozen
        ViewSnapshot.  Raises PermissionDeniedError if the caller is
        not authorised for the requested view_type.
        """
        self._check_view_access(caller, view_type)

        internal = await self._store.get(obj_id)
        if internal is None:
            raise PermissionDeniedError(
                caller=self._caller_component(caller),
                view_type=view_type.value,
                reason=f"TwinObject '{obj_id}' not found",
            )

        projector = _VIEW_PROJECTORS[view_type]
        return projector.from_internal(internal)

    async def update(self, obj_id: str, changes: dict, caller: CallerIdentity) -> None:
        """Update a TwinObject. Only authorized callers can write."""
        component = self._caller_component(caller)
        if component not in _WRITE_ALLOWED_COMPONENTS:
            raise PermissionDeniedError(
                caller=component,
                view_type="update",
                reason=f"Caller '{component}' does not have write permission",
            )

        internal = await self._store.get(obj_id)
        if internal is None:
            raise PermissionDeniedError(
                caller=component,
                view_type="update",
                reason=f"TwinObject '{obj_id}' not found",
            )

        updated = internal.model_copy(update=changes)
        await self._store.put(updated)

        record: ChangeRecord = {
            "action": "update",
            "caller_component": component,
            "fields": list(changes.keys()),
        }
        await self._store.append_change_record(obj_id, record)

    async def create_snapshot(self, obj_id: str, caller: CallerIdentity) -> str:
        """Create an immutable snapshot. Only core and audit."""
        component = self._caller_component(caller)
        if component not in _SNAPSHOT_ALLOWED_COMPONENTS:
            raise PermissionDeniedError(
                caller=component,
                view_type="create_snapshot",
                reason="Only core_runtime, core_certification, and audit can create snapshots",
            )

        internal = await self._store.get(obj_id)
        if internal is None:
            raise PermissionDeniedError(
                caller=component,
                view_type="create_snapshot",
                reason=f"TwinObject '{obj_id}' not found",
            )

        snapshot_id = f"snap-{obj_id}-{internal.version}"
        await self._store.put_snapshot(snapshot_id, internal)
        return snapshot_id

    async def get_snapshot(
        self, snapshot_id: str, caller: CallerIdentity
    ) -> TwinObjectInternal:
        """Get snapshot data. Only core and audit."""
        component = self._caller_component(caller)
        if component not in _SNAPSHOT_ALLOWED_COMPONENTS:
            raise PermissionDeniedError(
                caller=component,
                view_type="get_snapshot",
                reason="Only core_runtime, core_certification, and audit can read snapshots",
            )

        snap = await self._store.get_snapshot(snapshot_id)
        if snap is None:
            raise PermissionDeniedError(
                caller=component,
                view_type="get_snapshot",
                reason=f"Snapshot '{snapshot_id}' not found",
            )
        return snap

    async def get_change_history(
        self, obj_id: str, caller: CallerIdentity
    ) -> list[ChangeRecord]:
        """Get change history. Only audit."""
        component = self._caller_component(caller)
        if component not in _CHANGE_HISTORY_COMPONENTS:
            raise PermissionDeniedError(
                caller=component,
                view_type="change_history",
                reason="Only audit can read change history",
            )
        return await self._store.get_change_history(obj_id)
