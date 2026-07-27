"""Tests for TOM base models: Identity, Lineage, Relationship, State, TwinObjectBase."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from polytwin.tom.base_models import (
    AccessStats,
    Identity,
    Lineage,
    ProvenanceEntry,
    Relationship,
    State,
    TwinObjectBase,
)
from polytwin.tom.types import (
    HealthState,
    LifecycleState,
    ObjectType,
    RelationType,
)

# ── Identity ───────────────────────────────────────────────────────


class TestIdentity:
    def test_auto_uuid(self):
        ident = Identity(type=ObjectType.DEVICE)
        assert len(ident.id) == 36  # UUID4 format
        assert ident.id.count("-") == 4

    def test_unique_ids(self):
        ids = {Identity(type=ObjectType.AGENT).id for _ in range(100)}
        assert len(ids) == 100

    def test_default_name_and_tags(self):
        ident = Identity(type=ObjectType.TOOL)
        assert ident.name == ""
        assert ident.tags == []

    def test_custom_name_and_tags(self):
        ident = Identity(type=ObjectType.DEVICE, name="pump-01", tags=["oil", "rotating"])
        assert ident.name == "pump-01"
        assert ident.tags == ["oil", "rotating"]

    def test_serialization_round_trip(self):
        ident = Identity(type=ObjectType.DEVICE, name="sensor-x", tags=["temp"])
        data = ident.model_dump()
        restored = Identity.model_validate(data)
        assert restored == ident

    def test_type_must_be_valid_enum(self):
        ident = Identity(type=ObjectType.DEVICE)
        assert ident.type == ObjectType.DEVICE

    def test_fixture_device_identity(self, device_identity: Identity):
        assert device_identity.type == ObjectType.DEVICE
        assert device_identity.name == "pump-001"
        assert "rotating" in device_identity.tags


# ── ProvenanceEntry ────────────────────────────────────────────────


class TestProvenanceEntry:
    def test_auto_timestamp(self):
        entry = ProvenanceEntry(source="core", action="created", actor="system")
        assert entry.timestamp is not None
        assert entry.timestamp.tzinfo is not None

    def test_custom_fields(self):
        ts = datetime(2025, 1, 1, tzinfo=UTC)
        entry = ProvenanceEntry(source="lab", timestamp=ts, action="explored", actor="explorer-01")
        assert entry.source == "lab"
        assert entry.timestamp == ts
        assert entry.action == "explored"
        assert entry.actor == "explorer-01"


# ── Lineage ────────────────────────────────────────────────────────


class TestLineage:
    def test_minimal_construction(self):
        lin = Lineage(creator_id="c-001")
        assert lin.creator_id == "c-001"
        assert lin.parent_id is None
        assert lin.provenance == []

    def test_with_parent(self):
        lin = Lineage(creator_id="c-001", parent_id="p-001")
        assert lin.parent_id == "p-001"

    def test_with_provenance(self):
        prov = ProvenanceEntry(source="core", action="created", actor="system")
        lin = Lineage(creator_id="c-001", provenance=[prov])
        assert len(lin.provenance) == 1
        assert lin.provenance[0].source == "core"

    def test_serialization_round_trip(self):
        lin = Lineage(
            creator_id="c-001",
            parent_id="p-001",
            provenance=[ProvenanceEntry(source="core", action="created", actor="sys")],
        )
        data = lin.model_dump()
        restored = Lineage.model_validate(data)
        assert restored.creator_id == lin.creator_id

    def test_fixture_sample_lineage(self, sample_lineage: Lineage):
        assert sample_lineage.creator_id == "creator-001"
        assert sample_lineage.parent_id == "parent-001"
        assert len(sample_lineage.provenance) == 1


# ── Relationship ───────────────────────────────────────────────────


class TestRelationship:
    def test_basic_construction(self):
        rel = Relationship(target_id="t-001", type=RelationType.OWNS)
        assert rel.target_id == "t-001"
        assert rel.type == RelationType.OWNS
        assert rel.strength == 1.0
        assert rel.bidirectional is False
        assert rel.metadata == {}

    def test_strength_boundary_zero(self):
        rel = Relationship(target_id="t-001", type=RelationType.REFERENCES, strength=0.0)
        assert rel.strength == 0.0

    def test_strength_boundary_one(self):
        rel = Relationship(target_id="t-001", type=RelationType.SUPPORTS, strength=1.0)
        assert rel.strength == 1.0

    def test_strength_below_zero_raises(self):
        with pytest.raises(ValidationError):
            Relationship(target_id="t-001", type=RelationType.OWNS, strength=-0.1)

    def test_strength_above_one_raises(self):
        with pytest.raises(ValidationError):
            Relationship(target_id="t-001", type=RelationType.OWNS, strength=1.1)

    def test_bidirectional_flag(self):
        rel = Relationship(
            target_id="t-001", type=RelationType.SIMILAR_TO, bidirectional=True
        )
        assert rel.bidirectional is True

    def test_metadata_dict(self):
        rel = Relationship(
            target_id="t-001",
            type=RelationType.DEPENDS_ON,
            metadata={"weight": 0.5, "label": "dependency"},
        )
        assert rel.metadata["weight"] == 0.5

    def test_fixture_owns_relationship(self, owns_relationship: Relationship):
        assert owns_relationship.type == RelationType.OWNS
        assert owns_relationship.strength == 1.0

    def test_fixture_supports_relationship(self, supports_relationship: Relationship):
        assert supports_relationship.type == RelationType.SUPPORTS
        assert supports_relationship.strength == 0.85
        assert "confidence" in supports_relationship.metadata


# ── AccessStats ────────────────────────────────────────────────────


class TestAccessStats:
    def test_defaults(self):
        stats = AccessStats()
        assert stats.view_count == 0
        assert stats.last_viewed_at is None
        assert stats.last_modified_by == ""

    def test_custom_values(self):
        now = datetime.now(UTC)
        stats = AccessStats(view_count=42, last_viewed_at=now, last_modified_by="core")
        assert stats.view_count == 42
        assert stats.last_modified_by == "core"


# ── State ──────────────────────────────────────────────────────────


class TestState:
    def test_defaults(self):
        state = State()
        assert state.lifecycle == LifecycleState.CREATING
        assert state.health == HealthState.UNKNOWN

    def test_custom_values(self):
        state = State(lifecycle=LifecycleState.ACTIVE, health=HealthState.HEALTHY)
        assert state.lifecycle == LifecycleState.ACTIVE
        assert state.health == HealthState.HEALTHY

    def test_fixture_active_healthy(self, active_healthy_state: State):
        assert active_healthy_state.lifecycle == LifecycleState.ACTIVE
        assert active_healthy_state.health == HealthState.HEALTHY


# ── TwinObjectBase ─────────────────────────────────────────────────


class TestTwinObjectBase:
    def test_minimal_construction(self):
        ident = Identity(type=ObjectType.DEVICE)
        lin = Lineage(creator_id="c-001")
        obj = TwinObjectBase(identity=ident, lineage=lin)
        assert obj.identity.type == ObjectType.DEVICE
        assert obj.lineage.creator_id == "c-001"
        assert obj.state.lifecycle == LifecycleState.CREATING
        assert obj.relationships == []
        assert obj.access_stats.view_count == 0
        assert obj.version == "1.0.0"

    def test_auto_timestamps(self):
        ident = Identity(type=ObjectType.AGENT)
        lin = Lineage(creator_id="c-001")
        obj = TwinObjectBase(identity=ident, lineage=lin)
        assert obj.created_at is not None
        assert obj.last_modified is not None
        assert obj.created_at.tzinfo is not None

    def test_created_at_before_last_modified_or_equal(self):
        ident = Identity(type=ObjectType.DEVICE)
        lin = Lineage(creator_id="c-001")
        obj = TwinObjectBase(identity=ident, lineage=lin)
        assert obj.created_at <= obj.last_modified

    def test_with_relationships(self):
        ident = Identity(type=ObjectType.DEVICE)
        lin = Lineage(creator_id="c-001")
        rel = Relationship(target_id="t-001", type=RelationType.OWNS)
        obj = TwinObjectBase(identity=ident, lineage=lin, relationships=[rel])
        assert len(obj.relationships) == 1

    def test_serialization_round_trip(self):
        ident = Identity(type=ObjectType.DEVICE, name="pump-01", tags=["oil"])
        lin = Lineage(creator_id="c-001", parent_id="p-001")
        obj = TwinObjectBase(
            identity=ident,
            lineage=lin,
            state=State(lifecycle=LifecycleState.ACTIVE, health=HealthState.HEALTHY),
            version="2.0.0",
        )
        data = obj.model_dump()
        restored = TwinObjectBase.model_validate(data)
        assert restored.identity.name == "pump-01"
        assert restored.version == "2.0.0"
        assert restored.state.lifecycle == LifecycleState.ACTIVE

    def test_json_round_trip(self):
        ident = Identity(type=ObjectType.DEVICE)
        lin = Lineage(creator_id="c-001")
        obj = TwinObjectBase(identity=ident, lineage=lin)
        json_str = obj.model_dump_json()
        restored = TwinObjectBase.model_validate_json(json_str)
        assert restored.identity.id == obj.identity.id

    def test_fixture_minimal_twin_base(self, minimal_twin_base: TwinObjectBase):
        assert minimal_twin_base.identity.type == ObjectType.DEVICE
        assert minimal_twin_base.identity.name == "pump-001"
        assert minimal_twin_base.lineage.creator_id == "creator-001"

    def test_missing_identity_raises(self):
        with pytest.raises(ValidationError):
            TwinObjectBase(lineage=Lineage(creator_id="c-001"))  # type: ignore[call-arg]

    def test_missing_lineage_raises(self):
        with pytest.raises(ValidationError):
            TwinObjectBase(identity=Identity(type=ObjectType.DEVICE))  # type: ignore[call-arg]

    def test_custom_version(self):
        ident = Identity(type=ObjectType.DEVICE)
        lin = Lineage(creator_id="c-001")
        obj = TwinObjectBase(identity=ident, lineage=lin, version="3.1.4")
        assert obj.version == "3.1.4"
