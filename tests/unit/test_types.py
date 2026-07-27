"""Tests for TOM enumerations and CallerIdentity."""

import pytest
from pydantic import ValidationError

from polytwin.tom.types import (
    CallerIdentity,
    ConstraintStatus,
    Criticality,
    HealthState,
    LifecycleState,
    ObjectType,
    RelationType,
    Rigidity,
    ViewType,
)

# ── ObjectType ─────────────────────────────────────────────────────


class TestObjectType:
    def test_all_members_are_strings(self):
        for member in ObjectType:
            assert isinstance(member.value, str)

    def test_expected_members(self):
        expected = {
            "user", "agent", "tool", "doc", "code", "knowledge",
            "device", "scene", "domain_pack", "constraint_card",
            "hypothesis", "evidence", "custom",
        }
        assert {m.value for m in ObjectType} == expected

    def test_lookup_by_value(self):
        assert ObjectType("device") is ObjectType.DEVICE

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            ObjectType("nonexistent")


# ── LifecycleState ─────────────────────────────────────────────────


class TestLifecycleState:
    def test_expected_members(self):
        expected = {"creating", "active", "deprecated", "archived", "deleted"}
        assert {m.value for m in LifecycleState} == expected

    def test_string_comparison(self):
        assert LifecycleState.ACTIVE.value == "active"
        assert LifecycleState.ACTIVE == "active"

    def test_all_members_are_strings(self):
        for member in LifecycleState:
            assert isinstance(member.value, str)


# ── HealthState ────────────────────────────────────────────────────


class TestHealthState:
    def test_expected_members(self):
        expected = {"healthy", "degraded", "failing", "unknown"}
        assert {m.value for m in HealthState} == expected

    def test_default_like_value(self):
        assert HealthState.UNKNOWN.value == "unknown"


# ── RelationType ───────────────────────────────────────────────────


class TestRelationType:
    def test_expected_members(self):
        expected = {
            "owns", "created", "depends_on", "references", "part_of",
            "version_of", "contradicts", "supports", "similar_to", "triggers",
        }
        assert {m.value for m in RelationType} == expected

    def test_lookup_by_value(self):
        assert RelationType("depends_on") is RelationType.DEPENDS_ON

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            RelationType("invalid_relation")


# ── ViewType ───────────────────────────────────────────────────────


class TestViewType:
    def test_expected_members(self):
        expected = {
            "core_runtime", "core_certification", "bridge_decision",
            "lab_exploration", "audit",
        }
        assert {m.value for m in ViewType} == expected

    def test_string_equality(self):
        assert ViewType.CORE_RUNTIME == "core_runtime"


# ── Criticality ────────────────────────────────────────────────────


class TestCriticality:
    def test_expected_members(self):
        expected = {
            "safety_critical", "identity_critical", "operational", "informational",
        }
        assert {m.value for m in Criticality} == expected

    def test_ordering_not_relevant(self):
        # Criticality values are just labels, no ordering semantics
        assert Criticality.SAFETY_CRITICAL.value == "safety_critical"


# ── Rigidity ───────────────────────────────────────────────────────


class TestRigidity:
    def test_expected_members(self):
        expected = {"absolute", "soft", "learnable"}
        assert {m.value for m in Rigidity} == expected


# ── ConstraintStatus ───────────────────────────────────────────────


class TestConstraintStatus:
    def test_expected_members(self):
        expected = {"passed", "uncertain", "failed", "not_applicable"}
        assert {m.value for m in ConstraintStatus} == expected

    def test_lookup_by_value(self):
        assert ConstraintStatus("failed") is ConstraintStatus.FAILED


# ── CallerIdentity ─────────────────────────────────────────────────


class TestCallerIdentity:
    def test_basic_construction(self):
        cid = CallerIdentity(component="core", role="validator")
        assert cid.component == "core"
        assert cid.role == "validator"
        assert cid.session_id is None

    def test_with_session_id(self):
        cid = CallerIdentity(component="lab", role="explorer", session_id="sess-42")
        assert cid.session_id == "sess-42"

    def test_serialization_round_trip(self):
        cid = CallerIdentity(component="bridge", role="decision_maker", session_id="s-1")
        data = cid.model_dump()
        restored = CallerIdentity.model_validate(data)
        assert restored == cid

    def test_missing_required_fields_raises(self):
        with pytest.raises(ValidationError):
            CallerIdentity()  # type: ignore[call-arg]

    def test_missing_component_raises(self):
        with pytest.raises(ValidationError):
            CallerIdentity(role="validator")  # type: ignore[call-arg]

    def test_json_round_trip(self):
        cid = CallerIdentity(component="core", role="validator", session_id="abc")
        json_str = cid.model_dump_json()
        restored = CallerIdentity.model_validate_json(json_str)
        assert restored == cid

    def test_fixture_caller_core(self, caller_core: CallerIdentity):
        assert caller_core.component == "core"
        assert caller_core.role == "validator"
        assert caller_core.session_id is None

    def test_fixture_caller_lab(self, caller_lab: CallerIdentity):
        assert caller_lab.session_id == "sess-001"
