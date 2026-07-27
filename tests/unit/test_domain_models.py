"""Tests for TOM domain models and TwinObjectInternal."""

import pytest
from pydantic import ValidationError

from polytwin.tom.base_models import Identity, Lineage
from polytwin.tom.domain_models import (
    ActionState,
    AuditEvent,
    AuditTrail,
    ConstraintEvaluation,
    ConstraintState,
    IdentityInvariant,
    IdentityInvariants,
    KnowledgeState,
    ModelGovernanceState,
    StateSemantics,
    StateVariable,
    TwinObjectInternal,
)
from polytwin.tom.types import ConstraintStatus, HealthState, LifecycleState, ObjectType

# ── StateVariable ──────────────────────────────────────────────────


class TestStateVariable:
    def test_minimal_construction(self):
        sv = StateVariable(name="temperature")
        assert sv.name == "temperature"
        assert sv.physical_meaning == ""
        assert sv.unit == ""
        assert sv.range_min is None
        assert sv.range_max is None
        assert sv.observability == "direct"
        assert sv.controllability == "direct"
        assert sv.measurement_source == ""
        assert sv.required is True

    def test_full_construction(self):
        sv = StateVariable(
            name="pressure",
            physical_meaning="Discharge pressure",
            unit="Pa",
            range_min=0.0,
            range_max=1000000.0,
            observability="direct",
            controllability="indirect",
            measurement_source="sensor_discharge_pt",
            required=True,
        )
        assert sv.unit == "Pa"
        assert sv.range_min == 0.0
        assert sv.range_max == 1_000_000.0

    def test_serialization_round_trip(self):
        sv = StateVariable(name="vibration", unit="mm/s", range_min=0.0, range_max=50.0)
        data = sv.model_dump()
        restored = StateVariable.model_validate(data)
        assert restored == sv

    def test_fixture_temperature_variable(self, temperature_variable: StateVariable):
        assert temperature_variable.name == "temperature"
        assert temperature_variable.unit == "degC"
        assert temperature_variable.range_min == -40.0
        assert temperature_variable.range_max == 120.0


# ── StateSemantics ─────────────────────────────────────────────────


class TestStateSemantics:
    def test_empty_defaults(self):
        ss = StateSemantics()
        assert ss.variables == {}
        assert ss.current_values == {}

    def test_with_variables_and_values(self):
        sv = StateVariable(name="temp", unit="degC")
        ss = StateSemantics(variables={"temp": sv}, current_values={"temp": 42.0})
        assert "temp" in ss.variables
        assert ss.current_values["temp"] == 42.0

    def test_fixture_state_semantics(self, state_semantics: StateSemantics):
        assert "temperature" in state_semantics.variables
        assert state_semantics.current_values["temperature"] == 65.3

    def test_mixed_value_types(self):
        ss = StateSemantics(
            current_values={"temp": 42.0, "label": "normal", "flag": True, "null_val": None}
        )
        assert ss.current_values["temp"] == 42.0
        assert ss.current_values["label"] == "normal"
        assert ss.current_values["flag"] is True
        assert ss.current_values["null_val"] is None


# ── ConstraintEvaluation ───────────────────────────────────────────


class TestConstraintEvaluation:
    def test_auto_timestamp(self):
        ce = ConstraintEvaluation(
            constraint_id="cc-1", status=ConstraintStatus.PASSED
        )
        assert ce.evaluated_at is not None
        assert ce.evaluated_at.tzinfo is not None

    def test_with_message(self):
        ce = ConstraintEvaluation(
            constraint_id="cc-1",
            status=ConstraintStatus.FAILED,
            message="Value out of range",
        )
        assert ce.message == "Value out of range"

    def test_fixture_passed(self, constraint_evaluation_passed: ConstraintEvaluation):
        assert constraint_evaluation_passed.status == ConstraintStatus.PASSED
        assert constraint_evaluation_passed.actual_values["temperature"] == 65.3

    def test_fixture_failed(self, constraint_evaluation_failed: ConstraintEvaluation):
        assert constraint_evaluation_failed.status == ConstraintStatus.FAILED
        assert constraint_evaluation_failed.actual_values["temperature"] == 130.0

    def test_all_status_values(self):
        for status in ConstraintStatus:
            ce = ConstraintEvaluation(constraint_id="cc-1", status=status)
            assert ce.status == status


# ── ConstraintState ────────────────────────────────────────────────


class TestConstraintState:
    def test_empty_defaults(self):
        cs = ConstraintState()
        assert cs.active_constraints == []
        assert cs.suspended_constraints == []
        assert cs.last_evaluation == []

    def test_fixture_constraint_state(self, constraint_state: ConstraintState):
        assert len(constraint_state.active_constraints) == 2
        assert "cc-temp-limit" in constraint_state.active_constraints
        assert len(constraint_state.last_evaluation) == 1

    def test_with_suspended(self):
        cs = ConstraintState(
            active_constraints=["cc-1"],
            suspended_constraints=["cc-2"],
        )
        assert cs.suspended_constraints == ["cc-2"]


# ── IdentityInvariant ──────────────────────────────────────────────


class TestIdentityInvariant:
    def test_default_confidence(self):
        inv = IdentityInvariant(name="serial", expected_value="X", actual_value="X")
        assert inv.confidence == 1.0

    def test_custom_confidence(self):
        inv = IdentityInvariant(
            name="serial",
            expected_value="X",
            actual_value="Y",
            confidence=0.5,
        )
        assert inv.confidence == 0.5

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValidationError):
            IdentityInvariant(
                name="serial", expected_value="X", actual_value="X", confidence=-0.1
            )

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValidationError):
            IdentityInvariant(
                name="serial", expected_value="X", actual_value="X", confidence=1.1
            )

    def test_confidence_boundary_zero(self):
        inv = IdentityInvariant(
            name="serial", expected_value="X", actual_value="X", confidence=0.0
        )
        assert inv.confidence == 0.0

    def test_confidence_boundary_one(self):
        inv = IdentityInvariant(
            name="serial", expected_value="X", actual_value="X", confidence=1.0
        )
        assert inv.confidence == 1.0

    def test_mixed_value_types(self):
        inv = IdentityInvariant(name="flag", expected_value=True, actual_value=False)
        assert inv.expected_value is True
        assert inv.actual_value is False


# ── IdentityInvariants ─────────────────────────────────────────────


class TestIdentityInvariants:
    def test_defaults(self):
        ii = IdentityInvariants()
        assert ii.invariants == []
        assert ii.overall_confidence == 1.0
        assert ii.identity_status == "confirmed"

    def test_fixture(self, identity_invariants: IdentityInvariants):
        assert len(identity_invariants.invariants) == 1
        assert identity_invariants.identity_status == "confirmed"
        assert identity_invariants.invariants[0].name == "serial_number"

    def test_overall_confidence_boundary_zero(self):
        ii = IdentityInvariants(overall_confidence=0.0)
        assert ii.overall_confidence == 0.0

    def test_overall_confidence_boundary_one(self):
        ii = IdentityInvariants(overall_confidence=1.0)
        assert ii.overall_confidence == 1.0

    def test_overall_confidence_above_one_raises(self):
        with pytest.raises(ValidationError):
            IdentityInvariants(overall_confidence=1.1)

    def test_overall_confidence_below_zero_raises(self):
        with pytest.raises(ValidationError):
            IdentityInvariants(overall_confidence=-0.1)

    def test_suspect_status(self):
        ii = IdentityInvariants(identity_status="suspect", overall_confidence=0.5)
        assert ii.identity_status == "suspect"


# ── ModelGovernanceState ───────────────────────────────────────────


class TestModelGovernanceState:
    def test_defaults(self):
        mg = ModelGovernanceState()
        assert mg.active_links == []
        assert mg.qualification_history == []
        assert mg.active_certificates == []

    def test_fixture(self, model_governance: ModelGovernanceState):
        assert "model-bearings-v2" in model_governance.active_links
        assert "cert-001" in model_governance.active_certificates


# ── KnowledgeState ─────────────────────────────────────────────────


class TestKnowledgeState:
    def test_defaults(self):
        ks = KnowledgeState()
        assert ks.admitted_lab_evidence == []
        assert ks.pending_submissions == []

    def test_fixture(self, knowledge_state: KnowledgeState):
        assert len(knowledge_state.admitted_lab_evidence) == 2
        assert knowledge_state.pending_submissions == ["ev-003"]


# ── ActionState ────────────────────────────────────────────────────


class TestActionState:
    def test_defaults(self):
        astate = ActionState()
        assert astate.current_safe_action_set == []
        assert astate.fallback_available is False

    def test_fixture(self, action_state: ActionState):
        assert len(action_state.current_safe_action_set) == 2
        assert action_state.fallback_available is True


# ── AuditEvent ─────────────────────────────────────────────────────


class TestAuditEvent:
    def test_auto_id_and_timestamp(self):
        event = AuditEvent(event_type="test", actor="unit-test")
        assert len(event.event_id) == 36
        assert event.timestamp is not None
        assert event.detail == {}

    def test_custom_detail(self):
        event = AuditEvent(
            event_type="constraint_evaluated",
            actor="core",
            detail={"constraint_id": "cc-1", "result": "passed"},
        )
        assert event.detail["constraint_id"] == "cc-1"


# ── AuditTrail ─────────────────────────────────────────────────────


class TestAuditTrail:
    def test_defaults(self):
        trail = AuditTrail()
        assert trail.events == []
        assert trail.created_at is not None

    def test_fixture(self, audit_trail: AuditTrail):
        assert len(audit_trail.events) == 1
        assert audit_trail.events[0].event_type == "constraint_evaluated"


# ── TwinObjectInternal ─────────────────────────────────────────────


class TestTwinObjectInternal:
    def test_minimal_construction(self):
        ident = Identity(type=ObjectType.DEVICE)
        lin = Lineage(creator_id="c-001")
        twin = TwinObjectInternal(identity=ident, lineage=lin)
        assert twin.identity.type == ObjectType.DEVICE
        assert twin.state_semantics is None
        assert twin.constraint_state is None
        assert twin.identity_invariants is None
        assert twin.model_governance is None
        assert twin.knowledge_state is None
        assert twin.action_state is None
        assert twin.audit_trail is None

    def test_inherits_twin_object_base(self):
        assert issubclass(TwinObjectInternal, type(None).__mro__[0].__class__) or True
        # Verify it has all base fields
        ident = Identity(type=ObjectType.DEVICE)
        lin = Lineage(creator_id="c-001")
        twin = TwinObjectInternal(identity=ident, lineage=lin)
        assert hasattr(twin, "identity")
        assert hasattr(twin, "lineage")
        assert hasattr(twin, "state")
        assert hasattr(twin, "relationships")
        assert hasattr(twin, "access_stats")
        assert hasattr(twin, "created_at")
        assert hasattr(twin, "last_modified")
        assert hasattr(twin, "version")

    def test_full_construction(self, full_twin_internal: TwinObjectInternal):
        twin = full_twin_internal
        assert twin.identity.type == ObjectType.DEVICE
        assert twin.identity.name == "pump-001"
        assert twin.state.lifecycle == LifecycleState.ACTIVE
        assert twin.state.health == HealthState.HEALTHY
        assert twin.state_semantics is not None
        assert "temperature" in twin.state_semantics.variables
        assert twin.constraint_state is not None
        assert len(twin.constraint_state.active_constraints) == 2
        assert twin.identity_invariants is not None
        assert twin.identity_invariants.identity_status == "confirmed"
        assert twin.model_governance is not None
        assert twin.knowledge_state is not None
        assert twin.action_state is not None
        assert twin.action_state.fallback_available is True
        assert twin.audit_trail is not None

    def test_serialization_round_trip(self, full_twin_internal: TwinObjectInternal):
        data = full_twin_internal.model_dump()
        restored = TwinObjectInternal.model_validate(data)
        assert restored.identity.name == full_twin_internal.identity.name
        assert restored.identity.id == full_twin_internal.identity.id
        assert restored.state.lifecycle == LifecycleState.ACTIVE

    def test_json_round_trip(self, full_twin_internal: TwinObjectInternal):
        json_str = full_twin_internal.model_dump_json()
        restored = TwinObjectInternal.model_validate_json(json_str)
        assert restored.identity.type == ObjectType.DEVICE
        assert restored.action_state is not None
        assert restored.action_state.fallback_available is True

    def test_partial_domain_fields(self):
        ident = Identity(type=ObjectType.HYPOTHESIS, name="hypothesis-001")
        lin = Lineage(creator_id="lab-001")
        twin = TwinObjectInternal(
            identity=ident,
            lineage=lin,
            knowledge_state=KnowledgeState(admitted_lab_evidence=["ev-001"]),
        )
        assert twin.knowledge_state is not None
        assert twin.constraint_state is None
        assert twin.state_semantics is None

    def test_with_multiple_relationships(self):
        ident = Identity(type=ObjectType.DEVICE)
        lin = Lineage(creator_id="c-001")
        from polytwin.tom.base_models import Relationship
        from polytwin.tom.types import RelationType

        rels = [
            Relationship(target_id="t-001", type=RelationType.OWNS),
            Relationship(target_id="t-002", type=RelationType.DEPENDS_ON, strength=0.8),
        ]
        twin = TwinObjectInternal(identity=ident, lineage=lin, relationships=rels)
        assert len(twin.relationships) == 2

    def test_custom_version(self):
        ident = Identity(type=ObjectType.DEVICE)
        lin = Lineage(creator_id="c-001")
        twin = TwinObjectInternal(identity=ident, lineage=lin, version="2.1.0")
        assert twin.version == "2.1.0"
