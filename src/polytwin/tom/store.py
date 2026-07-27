"""TwinObject store layer with abstract base and in-memory implementation.

The store provides CRUD operations, relationship management, change
history tracking, and snapshot support for TwinObjectInternal instances.

PostgreSQL implementation is deferred to M5 (integration tests).
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from polytwin.tom.base_models import Relationship
from polytwin.tom.domain_models import TwinObjectInternal
from polytwin.tom.snapshot import generate_snapshot_id
from polytwin.tom.types import CallerIdentity


class TwinObjectStore(ABC):
    """Abstract base class defining the store contract for TwinObjects.

    Every concrete store (in-memory, PostgreSQL, etc.) must implement
    these methods.
    """

    @abstractmethod
    async def create(self, obj: TwinObjectInternal) -> str:
        """Persist a new TwinObject.

        Args:
            obj: The TwinObjectInternal to store.

        Returns:
            The stored object's ID.
        """
        ...

    @abstractmethod
    async def get_by_id(self, id: str) -> TwinObjectInternal | None:
        """Retrieve a TwinObject by its ID.

        Args:
            id: The TwinObject ID.

        Returns:
            A deep copy of the stored object, or None if not found.
        """
        ...

    @abstractmethod
    async def update(self, id: str, changes: dict, caller: CallerIdentity) -> None:
        """Apply partial updates to a stored TwinObject.

        Records the change in the change history table.

        Args:
            id: The TwinObject ID.
            changes: Field-level updates to apply.
            caller: Identity of the component requesting the update.
        """
        ...

    @abstractmethod
    async def query(self, **filters: Any) -> list[TwinObjectInternal]:
        """Query TwinObjects by field filters.

        Args:
            **filters: Keyword arguments matched against object fields.
                Supports nested dot-notation (e.g. ``identity__type="device"``).

        Returns:
            List of matching TwinObjects (deep copies).
        """
        ...

    @abstractmethod
    async def get_relationships(
        self, object_id: str, rel_type: str | None = None
    ) -> list[Relationship]:
        """Retrieve relationships for a TwinObject.

        Args:
            object_id: The TwinObject ID.
            rel_type: Optional filter by relationship type.

        Returns:
            List of matching Relationship records.
        """
        ...

    @abstractmethod
    async def add_relationship(
        self, source_id: str, rel: Relationship
    ) -> None:
        """Add a relationship to a TwinObject.

        Args:
            source_id: The source TwinObject ID.
            rel: The Relationship to add.
        """
        ...

    @abstractmethod
    async def get_change_history(self, id: str) -> list[dict]:
        """Retrieve change history for a TwinObject.

        Args:
            id: The TwinObject ID.

        Returns:
            Ordered list of change records.
        """
        ...

    @abstractmethod
    async def create_snapshot(self, obj_id: str, snapshot_data: dict) -> str:
        """Create an immutable snapshot of TwinObject state.

        Args:
            obj_id: The TwinObject ID to snapshot.
            snapshot_data: Pre-computed snapshot data dict.

        Returns:
            The generated snapshot ID.
        """
        ...

    @abstractmethod
    async def get_snapshot(self, snapshot_id: str) -> dict | None:
        """Retrieve a snapshot by its ID.

        Args:
            snapshot_id: The snapshot ID.

        Returns:
            Snapshot data dict, or None if not found.
        """
        ...


class InMemoryTwinObjectStore(TwinObjectStore):
    """Complete in-memory implementation of TwinObjectStore.

    Uses plain dicts for storage.  Returns deep copies on reads to
    prevent external mutation of internal state.

    Suitable for testing and development.  Replace with PostgreSQL
    store for production (M5).
    """

    def __init__(self) -> None:
        self._objects: dict[str, TwinObjectInternal] = {}
        self._relationships: dict[str, list[Relationship]] = {}
        self._changes: dict[str, list[dict]] = {}
        self._snapshots: dict[str, dict] = {}

    async def create(self, obj: TwinObjectInternal) -> str:
        obj_id = obj.identity.id
        self._objects[obj_id] = copy.deepcopy(obj)
        self._relationships.setdefault(obj_id, [])
        self._changes.setdefault(obj_id, [])
        return obj_id

    async def get_by_id(self, id: str) -> TwinObjectInternal | None:
        obj = self._objects.get(id)
        return copy.deepcopy(obj) if obj is not None else None

    async def update(self, id: str, changes: dict, caller: CallerIdentity) -> None:
        obj = self._objects.get(id)
        if obj is None:
            raise ValueError(f"TwinObject '{id}' not found")

        # Apply changes via model_copy
        updated = obj.model_copy(update=changes)
        self._objects[id] = updated

        # Record the change
        record = {
            "action": "update",
            "timestamp": datetime.now(UTC).isoformat(),
            "caller_component": caller.component,
            "caller_role": caller.role,
            "fields": list(changes.keys()),
        }
        self._changes.setdefault(id, []).append(record)

    async def query(self, **filters: Any) -> list[TwinObjectInternal]:
        results = []
        for obj in self._objects.values():
            match = True
            for key, expected in filters.items():
                # Support nested lookup via double-underscore
                parts = key.split("__")
                current: Any = obj
                try:
                    for part in parts:
                        current = getattr(current, part)
                except AttributeError:
                    match = False
                    break
                if current != expected:
                    match = False
                    break
            if match:
                results.append(copy.deepcopy(obj))
        return results

    async def get_relationships(
        self, object_id: str, rel_type: str | None = None
    ) -> list[Relationship]:
        rels = self._relationships.get(object_id, [])
        if rel_type is not None:
            rels = [r for r in rels if r.type == rel_type]
        return list(rels)

    async def add_relationship(self, source_id: str, rel: Relationship) -> None:
        self._relationships.setdefault(source_id, []).append(rel)

    async def get_change_history(self, id: str) -> list[dict]:
        return list(self._changes.get(id, []))

    async def create_snapshot(self, obj_id: str, snapshot_data: dict) -> str:
        obj = self._objects.get(obj_id)
        if obj is None:
            raise ValueError(f"TwinObject '{obj_id}' not found")

        ts = datetime.now(UTC)
        snapshot_id = generate_snapshot_id(obj, ts)
        self._snapshots[snapshot_id] = copy.deepcopy(snapshot_data)
        return snapshot_id

    async def get_snapshot(self, snapshot_id: str) -> dict | None:
        snap = self._snapshots.get(snapshot_id)
        return copy.deepcopy(snap) if snap is not None else None
