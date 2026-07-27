"""Tests for snapshot module: ID generation and deep-copy isolation."""

from __future__ import annotations

from datetime import UTC, datetime

from polytwin.tom.base_models import Identity, Lineage
from polytwin.tom.domain_models import TwinObjectInternal
from polytwin.tom.snapshot import create_snapshot_data, generate_snapshot_id
from polytwin.tom.types import ObjectType


def _make_internal(**overrides) -> TwinObjectInternal:
    defaults = dict(
        identity=Identity(type=ObjectType.DEVICE, name="test-device"),
        lineage=Lineage(creator_id="creator-001"),
    )
    defaults.update(overrides)
    return TwinObjectInternal(**defaults)


class TestGenerateSnapshotId:
    def test_starts_with_twin_id(self):
        obj = _make_internal()
        ts = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)
        snap_id = generate_snapshot_id(obj, ts)
        assert snap_id.startswith(obj.identity.id)

    def test_contains_timestamp(self):
        obj = _make_internal()
        ts = datetime(2026, 5, 20, 14, 30, 45, 123456, tzinfo=UTC)
        snap_id = generate_snapshot_id(obj, ts)
        assert "20260520T143045123456" in snap_id

    def test_contains_hash(self):
        obj = _make_internal()
        ts = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)
        snap_id = generate_snapshot_id(obj, ts)
        # Format: {twin_id}_{timestamp}_{hash12}
        parts = snap_id.split("_")
        # The hash is the last part
        hash_part = parts[-1]
        assert len(hash_part) == 12

    def test_deterministic_for_same_input(self):
        obj = _make_internal()
        ts = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)
        id1 = generate_snapshot_id(obj, ts)
        id2 = generate_snapshot_id(obj, ts)
        assert id1 == id2

    def test_different_for_different_objects(self):
        obj1 = _make_internal(identity=Identity(type=ObjectType.DEVICE, name="a"))
        obj2 = _make_internal(identity=Identity(type=ObjectType.DEVICE, name="b"))
        ts = datetime(2026, 5, 20, 12, 0, 0, tzinfo=UTC)
        id1 = generate_snapshot_id(obj1, ts)
        id2 = generate_snapshot_id(obj2, ts)
        assert id1 != id2


class TestCreateSnapshotData:
    def test_returns_deep_copy(self):
        obj = _make_internal()
        data = create_snapshot_data(obj)
        assert isinstance(data, dict)
        assert data["identity"]["name"] == "test-device"

    def test_modifying_original_does_not_affect_snapshot(self):
        obj = _make_internal()
        data = create_snapshot_data(obj)

        # Mutate the original
        obj.version = "99.0.0"

        assert data["version"] == "1.0.0"

    def test_modifying_snapshot_does_not_affect_original(self):
        obj = _make_internal()
        data = create_snapshot_data(obj)

        # Mutate the snapshot data
        data["version"] = "0.0.0"

        assert obj.version == "1.0.0"

    def test_contains_all_fields(self):
        obj = _make_internal()
        data = create_snapshot_data(obj)
        assert "identity" in data
        assert "lineage" in data
        assert "state" in data
        assert "created_at" in data
        assert "version" in data
