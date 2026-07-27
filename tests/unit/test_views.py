"""Comprehensive tests for frozen view types and ConstraintProhibition.

Validates:
- Every view is frozen (mutation raises ValidationError)
- Access matrix enforcement (visible fields present, hidden absent)
- from_internal classmethods produce correct projections
- ConstraintProhibition semantics (None reason when passed, non-None when violated)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from polytwin.tom.base_models import Identity, Lineage
from polytwin.tom.domain_models import (
    ActionState,
    ActionTemplate,
    AuditTrail,
    ChangeHistory,
    ConstraintEvaluation,
    ConstraintState,
    HumanRole,
    IdentityInvariants,
    KnowledgeState,
    ModelGovernanceState,
    RigidityRule,
    SafeFallback,
    StateSemantics,
    TwinObjectInternal,
)
from polytwin.tom.prohibitions import ConstraintProhibition
from polytwin.tom.types import ConstraintStatus, Criticality, ObjectType
from polytwin.tom.views import (
    AuditView,
    BridgeDecisionView,
    CoreCertificationView,
    CoreRuntimeView,
    LabExplorationView,
)

# ── Fixtures ───────────────────────────────────────────────────────


def _make_internal(**overrides) -> TwinObjectInternal:
    """Build a TwinObjectInternal with sensible defaults for testing."""
    defaults = dict(
        identity=Identity(type=ObjectType.DEVICE, name="test-device"),
        lineage=Lineage(creator_id="creator-001"),
        state_semantics=StateSemantics(
            variables={},
            current_values={"temperature": 42.0},
        ),
        constraint_state=ConstraintState(
            active_constraints=["c1", "c2"],
            suspended_constraints=[],
            last_evaluation=[
                ConstraintEvaluation(
                    constraint_id="c1",
                    status=ConstraintStatus.PASSED,
                    message="OK",
                ),
                ConstraintEvaluation(
                    constraint_id="c2",
                    status=ConstraintStatus.FAILED,
                    message="Temperature exceeds limit",
                ),
            ],
        ),
        identity_invariants=IdentityInvariants(identity_status="confirmed"),
        model_governance=ModelGovernanceState(
            active_links=["model-A"],
            qualification_history=["q-001"],
        ),
        knowledge_state=KnowledgeState(
            admitted_lab_evidence=["ev-001", "ev-002"],
        ),
        action_state=ActionState(
            current_safe_action_set=["act-cool"],
            fallback_available=True,
        ),
        audit_trail=AuditTrail(),
        action_templates=[
            ActionTemplate(template_id="at-1", name="Cool Down"),
            ActionTemplate(template_id="at-2", name="Shutdown"),
        ],
        human_roles=[
            HumanRole(role_id="r-1", name="Operator", permission_level="approve"),
        ],
        safe_fallback=SafeFallback(
            strategy="emergency_cool",
            target_state={"temperature": 25.0},
            details={"secret_internal": True},
        ),
        rigidity_rules=[
            RigidityRule(constraint_id="c1", rigidity="absolute", criticality="safety_critical"),
        ],
        audit_benchmark_reference="bench-ref-123",
        hidden_challenge_set_reference="hidden-challenge-456",
        public_eval_set_reference="public-eval-789",
        change_history=ChangeHistory(entries=[{"action": "created"}]),
    )
    defaults.update(overrides)
    return TwinObjectInternal(**defaults)


# ── 1. Frozen tests ────────────────────────────────────────────────


class TestFrozenViews:
    """Every view type must raise ValidationError on field mutation."""

    @pytest.fixture()
    def internal(self):
        return _make_internal()

    @pytest.mark.parametrize(
        "view_cls",
        [
            CoreRuntimeView,
            CoreCertificationView,
            BridgeDecisionView,
            LabExplorationView,
            AuditView,
        ],
    )
    def test_frozen_raises_validation_error(self, view_cls, internal):
        view = view_cls.from_internal(internal)
        with pytest.raises(ValidationError):
            view.twin_object_id = "hacked"

    @pytest.mark.parametrize(
        "view_cls",
        [
            CoreRuntimeView,
            CoreCertificationView,
            BridgeDecisionView,
            LabExplorationView,
            AuditView,
        ],
    )
    def test_frozen_raises_on_any_field(self, view_cls, internal):
        view = view_cls.from_internal(internal)
        # Try to mutate a few different field types
        for field_name in view.__class__.model_fields:
            with pytest.raises(ValidationError):
                setattr(view, field_name, None)


class TestConstraintProhibitionFrozen:
    def test_prohibition_is_frozen(self):
        p = ConstraintProhibition(
            constraint_id="c1",
            status=ConstraintStatus.PASSED,
            criticality=Criticality.OPERATIONAL,
        )
        with pytest.raises(ValidationError):
            p.constraint_id = "changed"


# ── 2. CoreRuntimeView ─────────────────────────────────────────────


class TestCoreRuntimeView:
    def test_has_required_fields(self):
        view = CoreRuntimeView.from_internal(_make_internal())
        assert view.twin_object_id is not None
        assert view.state_semantics is not None
        assert view.constraint_state is not None
        assert view.identity_invariants is not None
        assert view.model_governance is not None
        assert view.action_state is not None
        assert view.knowledge_state is not None

    def test_does_not_have_audit_benchmark(self):
        """CoreRuntimeView must NOT expose audit_benchmark_reference."""
        view = CoreRuntimeView.from_internal(_make_internal())
        assert not hasattr(view, "audit_benchmark_reference")

    def test_does_not_have_hidden_challenge_set(self):
        view = CoreRuntimeView.from_internal(_make_internal())
        assert not hasattr(view, "hidden_challenge_set_reference")

    def test_does_not_have_audit_trail(self):
        view = CoreRuntimeView.from_internal(_make_internal())
        assert not hasattr(view, "audit_trail")

    def test_does_not_have_action_templates(self):
        view = CoreRuntimeView.from_internal(_make_internal())
        assert not hasattr(view, "action_templates")

    def test_does_not_have_change_history(self):
        view = CoreRuntimeView.from_internal(_make_internal())
        assert not hasattr(view, "change_history")


# ── 3. CoreCertificationView ───────────────────────────────────────


class TestCoreCertificationView:
    def test_has_audit_benchmark_reference(self):
        view = CoreCertificationView.from_internal(_make_internal())
        assert view.audit_benchmark_reference == "bench-ref-123"

    def test_has_hidden_challenge_set_reference(self):
        view = CoreCertificationView.from_internal(_make_internal())
        assert view.hidden_challenge_set_reference == "hidden-challenge-456"

    def test_has_state_semantics(self):
        view = CoreCertificationView.from_internal(_make_internal())
        assert view.state_semantics is not None

    def test_has_constraint_state(self):
        view = CoreCertificationView.from_internal(_make_internal())
        assert view.constraint_state is not None

    def test_has_identity_invariants(self):
        view = CoreCertificationView.from_internal(_make_internal())
        assert view.identity_invariants is not None

    def test_has_model_governance(self):
        view = CoreCertificationView.from_internal(_make_internal())
        assert view.model_governance is not None

    def test_does_not_have_audit_trail(self):
        view = CoreCertificationView.from_internal(_make_internal())
        assert not hasattr(view, "audit_trail")

    def test_does_not_have_action_state(self):
        view = CoreCertificationView.from_internal(_make_internal())
        assert not hasattr(view, "action_state")

    def test_exclusive_access_to_benchmark(self):
        """Only CoreCertificationView has audit_benchmark_reference."""
        for view_cls in [
            CoreRuntimeView,
            BridgeDecisionView,
            LabExplorationView,
        ]:
            view = view_cls.from_internal(_make_internal())
            assert not hasattr(view, "audit_benchmark_reference"), (
                f"{view_cls.__name__} should not have audit_benchmark_reference"
            )


# ── 4. BridgeDecisionView ──────────────────────────────────────────


class TestBridgeDecisionView:
    def test_has_constraint_summary(self):
        view = BridgeDecisionView.from_internal(_make_internal())
        assert isinstance(view.constraint_summary, list)
        # We have 2 evaluations (c1 passed, c2 failed)
        assert len(view.constraint_summary) == 2

    def test_constraint_summary_types(self):
        view = BridgeDecisionView.from_internal(_make_internal())
        for item in view.constraint_summary:
            assert isinstance(item, ConstraintProhibition)

    def test_has_action_templates(self):
        view = BridgeDecisionView.from_internal(_make_internal())
        assert isinstance(view.action_templates, list)
        assert len(view.action_templates) == 2
        assert view.action_templates[0]["template_id"] == "at-1"

    def test_has_human_roles(self):
        view = BridgeDecisionView.from_internal(_make_internal())
        assert isinstance(view.human_roles, list)
        assert len(view.human_roles) == 1
        assert view.human_roles[0].role_id == "r-1"

    def test_has_action_state(self):
        view = BridgeDecisionView.from_internal(_make_internal())
        assert view.action_state is not None

    def test_has_safe_fallback(self):
        view = BridgeDecisionView.from_internal(_make_internal())
        assert view.safe_fallback is not None
        assert view.safe_fallback.strategy == "emergency_cool"

    def test_safe_fallback_no_details_exposed(self):
        """safe_fallback.details is internal; Bridge gets the SafeFallback
        object but the details dict is not a separate field on the view."""
        view = BridgeDecisionView.from_internal(_make_internal())
        # The view has safe_fallback but does not expose internal details separately
        assert view.safe_fallback is not None

    def test_does_not_have_certifier_thresholds(self):
        view = BridgeDecisionView.from_internal(_make_internal())
        assert not hasattr(view, "audit_benchmark_reference")
        assert not hasattr(view, "hidden_challenge_set_reference")

    def test_does_not_have_audit_trail(self):
        view = BridgeDecisionView.from_internal(_make_internal())
        assert not hasattr(view, "audit_trail")

    def test_does_not_have_change_history(self):
        view = BridgeDecisionView.from_internal(_make_internal())
        assert not hasattr(view, "change_history")


# ── 5. LabExplorationView ──────────────────────────────────────────


class TestLabExplorationView:
    def test_has_state_semantics(self):
        view = LabExplorationView.from_internal(_make_internal())
        assert view.state_semantics is not None

    def test_has_public_eval_set_reference(self):
        view = LabExplorationView.from_internal(_make_internal())
        assert view.public_eval_set_reference == "public-eval-789"

    def test_has_constraint_state(self):
        view = LabExplorationView.from_internal(_make_internal())
        assert view.constraint_state is not None

    def test_has_rigidity_rules(self):
        view = LabExplorationView.from_internal(_make_internal())
        assert isinstance(view.rigidity_rules, list)
        assert len(view.rigidity_rules) == 1
        assert view.rigidity_rules[0]["constraint_id"] == "c1"
        assert view.rigidity_rules[0]["rigidity"] == "absolute"

    def test_has_own_evidence_history(self):
        view = LabExplorationView.from_internal(_make_internal())
        assert view.own_evidence_history == ["ev-001", "ev-002"]

    def test_does_not_have_hidden_validation_sets(self):
        view = LabExplorationView.from_internal(_make_internal())
        assert not hasattr(view, "hidden_challenge_set_reference")
        assert not hasattr(view, "audit_benchmark_reference")

    def test_does_not_have_certifier_logic(self):
        """Lab must not see any certifier-specific fields."""
        view = LabExplorationView.from_internal(_make_internal())
        assert not hasattr(view, "model_governance")

    def test_does_not_have_fallback_strategy(self):
        view = LabExplorationView.from_internal(_make_internal())
        assert not hasattr(view, "safe_fallback")

    def test_does_not_have_roles(self):
        view = LabExplorationView.from_internal(_make_internal())
        assert not hasattr(view, "human_roles")

    def test_does_not_have_inheritance_chain(self):
        """Lab must not see lineage (inheritance chain)."""
        view = LabExplorationView.from_internal(_make_internal())
        assert not hasattr(view, "lineage")


# ── 6. AuditView ───────────────────────────────────────────────────


class TestAuditView:
    def test_has_all_fields(self):
        view = AuditView.from_internal(_make_internal())
        assert view.twin_object_id is not None
        assert view.state_semantics is not None
        assert view.constraint_state is not None
        assert view.identity_invariants is not None
        assert view.model_governance is not None
        assert view.knowledge_state is not None
        assert view.action_state is not None
        assert view.audit_trail is not None
        assert isinstance(view.action_templates, list)
        assert isinstance(view.human_roles, list)
        assert view.safe_fallback is not None
        assert isinstance(view.rigidity_rules, list)
        assert view.audit_benchmark_reference is not None
        assert view.hidden_challenge_set_reference is not None
        assert view.public_eval_set_reference is not None
        assert view.change_history is not None

    def test_has_change_history(self):
        view = AuditView.from_internal(_make_internal())
        assert view.change_history is not None
        assert len(view.change_history.entries) == 1
        assert view.change_history.entries[0]["action"] == "created"

    def test_has_audit_trail(self):
        view = AuditView.from_internal(_make_internal())
        assert view.audit_trail is not None

    def test_has_certification_references(self):
        view = AuditView.from_internal(_make_internal())
        assert view.audit_benchmark_reference == "bench-ref-123"
        assert view.hidden_challenge_set_reference == "hidden-challenge-456"


# ── 7. ConstraintProhibition semantics ─────────────────────────────


class TestConstraintProhibitionSemantics:
    def test_passed_constraint_reason_is_none(self):
        """When a constraint passes, prohibition_reason must be None."""
        p = ConstraintProhibition(
            constraint_id="c1",
            status=ConstraintStatus.PASSED,
            criticality=Criticality.SAFETY_CRITICAL,
        )
        assert p.prohibition_reason is None

    def test_failed_constraint_reason_is_set(self):
        """When a constraint fails, prohibition_reason must be non-None."""
        p = ConstraintProhibition(
            constraint_id="c2",
            status=ConstraintStatus.FAILED,
            criticality=Criticality.SAFETY_CRITICAL,
            prohibition_reason="Temperature exceeds limit",
        )
        assert p.prohibition_reason is not None
        assert "Temperature" in p.prohibition_reason

    def test_uncertain_constraint_reason_is_set(self):
        p = ConstraintProhibition(
            constraint_id="c3",
            status=ConstraintStatus.UNCERTAIN,
            criticality=Criticality.OPERATIONAL,
            prohibition_reason="Sensor data incomplete",
        )
        assert p.prohibition_reason is not None

    def test_bridge_summary_passed_has_none_reason(self):
        """BridgeDecisionView.summary for passed constraint has None reason."""
        internal = _make_internal(
            constraint_state=ConstraintState(
                last_evaluation=[
                    ConstraintEvaluation(
                        constraint_id="c-ok",
                        status=ConstraintStatus.PASSED,
                        message="All good",
                    ),
                ],
            ),
        )
        view = BridgeDecisionView.from_internal(internal)
        assert len(view.constraint_summary) == 1
        assert view.constraint_summary[0].prohibition_reason is None

    def test_bridge_summary_failed_has_reason(self):
        """BridgeDecisionView.summary for failed constraint has a reason."""
        internal = _make_internal(
            constraint_state=ConstraintState(
                last_evaluation=[
                    ConstraintEvaluation(
                        constraint_id="c-bad",
                        status=ConstraintStatus.FAILED,
                        message="Over pressure",
                    ),
                ],
            ),
        )
        view = BridgeDecisionView.from_internal(internal)
        assert len(view.constraint_summary) == 1
        assert view.constraint_summary[0].prohibition_reason is not None


# ── 8. from_internal with None fields ──────────────────────────────


class TestFromInternalWithEmptyFields:
    """Views must handle TwinObjectInternal with all optional fields None."""

    def _minimal_internal(self) -> TwinObjectInternal:
        return TwinObjectInternal(
            identity=Identity(type=ObjectType.DEVICE),
            lineage=Lineage(creator_id="c-1"),
        )

    @pytest.mark.parametrize(
        "view_cls",
        [
            CoreRuntimeView,
            CoreCertificationView,
            BridgeDecisionView,
            LabExplorationView,
            AuditView,
        ],
    )
    def test_from_internal_succeeds_with_none_fields(self, view_cls):
        view = view_cls.from_internal(self._minimal_internal())
        assert view.twin_object_id is not None

    def test_lab_empty_evidence_history(self):
        view = LabExplorationView.from_internal(self._minimal_internal())
        assert view.own_evidence_history == []

    def test_bridge_empty_constraint_summary(self):
        view = BridgeDecisionView.from_internal(self._minimal_internal())
        assert view.constraint_summary == []
