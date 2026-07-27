"""Tests for InMemoryTwinObjectStore: CRUD, snapshots, relationships, change history."""

from __future__ import annotations

import asyncio

import pytest

from polytwin.tom.base_models import Identity, Lineage, Relationship
from polytwin.tom.domain_models import TwinObjectInternal
from polytwin.tom.snapshot import create_snapshot_data
from polytwin.tom.store import InMemoryTwinObjectStore
from polytwin.tom.types import CallerIdentity, ObjectType, RelationType


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_internal(**overrides) -> TwinObjectInternal:
    defaults = dict(
        identity=Identity(type=ObjectType.DEVICE, name="test-device"),
        lineage=Lineage(creator_id="creator-001"),
    )
    defaults.update(overrides)
    return TwinObjectInternal(**defaults)


def _caller() -> CallerIdentity:
    return CallerIdentity(component="core", role="validator")


# ── create + get_by_id round-trip ────────────────────────────────────


class TestCreateAndGetById:
    def test_create_returns_id(self):
        store = InMemoryTwinObjectStore()
        obj = _make_internal()
        obj_id = _run(store.create(obj))
        assert obj_id == obj.identity.id

    def test_get_by_id_returns_stored_object(self):
        store = InMemoryTwinObjectStore()
        obj = _make_internal()
        _run(store.create(obj))
        result = _run(store.get_by_id(obj.identity.id))
        assert result is not None
        assert result.identity.id == obj.identity.id
        assert result.identity.name == "test-device"

    def test_get_by_id_returns_none_for_nonexistent(self):
        store = InMemoryTwinObjectStore()
        result = _run(store.get_by_id("no-such-id"))
        assert result is None


# ── update records change history ────────────────────────────────────


class TestUpdate:
    def test_update_applies_changes(self):
        store = InMemoryTwinObjectStore()
        obj = _make_internal()
        _run(store.create(obj))
        _run(store.update(obj.identity.id, {"version": "2.0.0"}, _caller()))
        result = _run(store.get_by_id(obj.identity.id))
        assert result is not None
        assert result.version == "2.0.0"

    def test_update_records_change_history(self):
        store = InMemoryTwinObjectStore()
        obj = _make_internal()
        _run(store.create(obj))
        _run(store.update(obj.identity.id, {"version": "2.0.0"}, _caller()))
        history = _run(store.get_change_history(obj.identity.id))
        assert len(history) == 1
        assert history[0]["action"] == "update"
        assert "version" in history[0]["fields"]
        assert history[0]["caller_component"] == "core"

    def test_update_nonexistent_raises(self):
        store = InMemoryTwinObjectStore()
        with pytest.raises(ValueError, match="not found"):
            _run(store.update("no-such-id", {"version": "2.0.0"}, _caller()))


# ── snapshot creation and retrieval ──────────────────────────────────


class TestSnapshots:
    def test_create_and_get_snapshot(self):
        store = InMemoryTwinObjectStore()
        obj = _make_internal()
        _run(store.create(obj))
        snapshot_data = create_snapshot_data(obj)
        snap_id = _run(store.create_snapshot(obj.identity.id, snapshot_data))
        assert snap_id.startswith(obj.identity.id)

        retrieved = _run(store.get_snapshot(snap_id))
        assert retrieved is not None
        assert retrieved["identity"]["name"] == "test-device"

    def test_snapshot_is_deep_copy(self):
        """Modifying the original object does not affect the stored snapshot."""
        store = InMemoryTwinObjectStore()
        obj = _make_internal()
        _run(store.create(obj))
        snapshot_data = create_snapshot_data(obj)
        snap_id = _run(store.create_snapshot(obj.identity.id, snapshot_data))

        # Mutate the original object in the store
        _run(store.update(obj.identity.id, {"version": "9.9.9"}, _caller()))

        # Snapshot should still reflect old version
        retrieved = _run(store.get_snapshot(snap_id))
        assert retrieved["version"] == "1.0.0"

    def test_get_snapshot_nonexistent_returns_none(self):
        store = InMemoryTwinObjectStore()
        result = _run(store.get_snapshot("no-such-snap"))
        assert result is None

    def test_create_snapshot_nonexistent_raises(self):
        store = InMemoryTwinObjectStore()
        with pytest.raises(ValueError, match="not found"):
            _run(store.create_snapshot("no-such-id", {}))


# ── query with filters ───────────────────────────────────────────────


class TestQuery:
    def test_query_by_identity_type(self):
        store = InMemoryTwinObjectStore()
        obj1 = _make_internal(identity=Identity(type=ObjectType.DEVICE, name="dev"))
        obj2 = _make_internal(identity=Identity(type=ObjectType.AGENT, name="agent"))
        _run(store.create(obj1))
        _run(store.create(obj2))

        results = _run(store.query(identity__type=ObjectType.DEVICE))
        assert len(results) == 1
        assert results[0].identity.type == ObjectType.DEVICE

    def test_query_no_match_returns_empty(self):
        store = InMemoryTwinObjectStore()
        results = _run(store.query(identity__type=ObjectType.TOOL))
        assert results == []

    def test_query_returns_deep_copies(self):
        store = InMemoryTwinObjectStore()
        obj = _make_internal()
        _run(store.create(obj))
        results = _run(store.query(identity__type=ObjectType.DEVICE))
        results[0].version = "tampered"
        fresh = _run(store.get_by_id(obj.identity.id))
        assert fresh is not None
        assert fresh.version == "1.0.0"


# ── relationships ────────────────────────────────────────────────────


class TestRelationships:
    def test_add_and_get_relationships(self):
        store = InMemoryTwinObjectStore()
        obj = _make_internal()
        _run(store.create(obj))
        rel = Relationship(
            target_id="other-id",
            type=RelationType.DEPENDS_ON,
        )
        _run(store.add_relationship(obj.identity.id, rel))
        rels = _run(store.get_relationships(obj.identity.id))
        assert len(rels) == 1
        assert rels[0].target_id == "other-id"
        assert rels[0].type == RelationType.DEPENDS_ON

    def test_get_relationships_filtered_by_type(self):
        store = InMemoryTwinObjectStore()
        obj = _make_internal()
        _run(store.create(obj))
        rel1 = Relationship(target_id="a", type=RelationType.OWNS)
        rel2 = Relationship(target_id="b", type=RelationType.DEPENDS_ON)
        _run(store.add_relationship(obj.identity.id, rel1))
        _run(store.add_relationship(obj.identity.id, rel2))

        owns_rels = _run(store.get_relationships(obj.identity.id, rel_type="owns"))
        assert len(owns_rels) == 1
        assert owns_rels[0].type == RelationType.OWNS

    def test_get_relationships_empty(self):
        store = InMemoryTwinObjectStore()
        rels = _run(store.get_relationships("no-such-id"))
        assert rels == []


# ── get_by_id returns deep copy ──────────────────────────────────────


class TestDeepCopy:
    def test_get_by_id_returns_deep_copy(self):
        store = InMemoryTwinObjectStore()
        obj = _make_internal()
        _run(store.create(obj))
        result = _run(store.get_by_id(obj.identity.id))
        assert result is not None
        result.version = "tampered"
        fresh = _run(store.get_by_id(obj.identity.id))
        assert fresh is not None
        assert fresh.version == "1.0.0"
