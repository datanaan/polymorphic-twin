"""Frozen view projections for TwinObjectInternal.

Each view exposes only the fields that a specific caller is allowed
to see, following the access matrix defined in the framework spec (S4).

All views are Pydantic v2 frozen models -- attempting to mutate any
field after construction raises ``ValidationError``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from polytwin.tom.domain_models import (
    ActionState,
    AuditTrail,
    ChangeHistory,
    ConstraintState,
    HumanRole,
    IdentityInvariants,
    KnowledgeState,
    ModelGovernanceState,
    SafeFallback,
    StateSemantics,
    TwinObjectInternal,
)
from polytwin.tom.prohibitions import ConstraintProhibition
from polytwin.tom.types import Criticality

__all__ = [
    "CoreRuntimeView",
    "CoreCertificationView",
    "BridgeDecisionView",
    "LabExplorationView",
    "AuditView",
]


# ── Helpers ────────────────────────────────────────────────────────


def _build_constraint_prohibitions(
    constraint_state: ConstraintState | None,
) -> list[ConstraintProhibition]:
    """Derive prohibition summaries from the last constraint evaluation."""
    if constraint_state is None:
        return []

    prohibitions: list[ConstraintProhibition] = []
    for ev in constraint_state.last_evaluation:
        reason: str | None = None
        if ev.status != "passed":
            reason = ev.message or f"Constraint {ev.constraint_id} {ev.status.value}"
        prohibitions.append(
            ConstraintProhibition(
                constraint_id=ev.constraint_id,
                status=ev.status,
                criticality=Criticality.OPERATIONAL,  # default; callers can enrich
                prohibition_reason=reason,
            )
        )
    return prohibitions


# ── CoreRuntimeView ────────────────────────────────────────────────


class CoreRuntimeView(BaseModel):
    """View projected for the Core runtime (constraint gatekeeper).

    Visible: state_semantics, constraint_state, identity_invariants,
             model_governance, action_state, knowledge_state
    Hidden:  audit_trail details, certification internals,
             audit_benchmark_reference, hidden_challenge_set_reference
    """

    model_config = ConfigDict(frozen=True)

    twin_object_id: str
    state_semantics: StateSemantics | None
    constraint_state: ConstraintState | None
    identity_invariants: IdentityInvariants | None
    model_governance: ModelGovernanceState | None
    action_state: ActionState | None
    knowledge_state: KnowledgeState | None

    @classmethod
    def from_internal(cls, obj: TwinObjectInternal) -> CoreRuntimeView:
        return cls(
            twin_object_id=obj.identity.id,
            state_semantics=obj.state_semantics,
            constraint_state=obj.constraint_state,
            identity_invariants=obj.identity_invariants,
            model_governance=obj.model_governance,
            action_state=obj.action_state,
            knowledge_state=obj.knowledge_state,
        )


# ── CoreCertificationView ──────────────────────────────────────────


class CoreCertificationView(BaseModel):
    """View projected for the Core certification subsystem.

    This is the ONLY view that can see audit_benchmark_reference
    and hidden_challenge_set_reference.

    Visible: state_semantics, constraint_state, identity_invariants,
             model_governance, audit_benchmark_reference,
             hidden_challenge_set_reference
    Hidden:  audit_trail, action_state
    """

    model_config = ConfigDict(frozen=True)

    twin_object_id: str
    state_semantics: StateSemantics | None
    constraint_state: ConstraintState | None
    identity_invariants: IdentityInvariants | None
    model_governance: ModelGovernanceState | None
    audit_benchmark_reference: str | None
    hidden_challenge_set_reference: str | None

    @classmethod
    def from_internal(cls, obj: TwinObjectInternal) -> CoreCertificationView:
        return cls(
            twin_object_id=obj.identity.id,
            state_semantics=obj.state_semantics,
            constraint_state=obj.constraint_state,
            identity_invariants=obj.identity_invariants,
            model_governance=obj.model_governance,
            audit_benchmark_reference=obj.audit_benchmark_reference,
            hidden_challenge_set_reference=obj.hidden_challenge_set_reference,
        )


# ── BridgeDecisionView ─────────────────────────────────────────────


class BridgeDecisionView(BaseModel):
    """View projected for the Bridge decision interface.

    Visible: id, state_semantics (summary), constraint_state (summary with
             prohibition_reasons), action_state, safe_fallback (no details),
             action_templates, human_roles
    Hidden:  certifier logic, hidden validation sets, audit fields,
             certification internals
    """

    model_config = ConfigDict(frozen=True)

    twin_object_id: str
    state_semantics: StateSemantics | None
    constraint_summary: list[ConstraintProhibition]
    action_state: ActionState | None
    safe_fallback: SafeFallback | None
    action_templates: list[dict]
    human_roles: list[HumanRole]

    @classmethod
    def from_internal(cls, obj: TwinObjectInternal) -> BridgeDecisionView:
        return cls(
            twin_object_id=obj.identity.id,
            state_semantics=obj.state_semantics,
            constraint_summary=_build_constraint_prohibitions(obj.constraint_state),
            action_state=obj.action_state,
            safe_fallback=obj.safe_fallback,
            action_templates=[t.model_dump() for t in obj.action_templates],
            human_roles=obj.human_roles,
        )


# ── LabExplorationView ─────────────────────────────────────────────


class LabExplorationView(BaseModel):
    """View projected for the Lab exploration engine.

    Visible: id, state_semantics, constraint_state (no certifier/thresholds),
             rigidity rules, public_eval_set_reference, own_evidence_history
    Hidden:  certifier logic, hidden validation sets, fallback strategy,
             roles, inheritance chain
    """

    model_config = ConfigDict(frozen=True)

    twin_object_id: str
    state_semantics: StateSemantics | None
    constraint_state: ConstraintState | None
    rigidity_rules: list[dict]
    public_eval_set_reference: str | None
    own_evidence_history: list[str]

    @classmethod
    def from_internal(cls, obj: TwinObjectInternal) -> LabExplorationView:
        evidence_history: list[str] = []
        if obj.knowledge_state is not None:
            evidence_history = list(obj.knowledge_state.admitted_lab_evidence)
        return cls(
            twin_object_id=obj.identity.id,
            state_semantics=obj.state_semantics,
            constraint_state=obj.constraint_state,
            rigidity_rules=[r.model_dump() for r in obj.rigidity_rules],
            public_eval_set_reference=obj.public_eval_set_reference,
            own_evidence_history=evidence_history,
        )


# ── AuditView ──────────────────────────────────────────────────────


class AuditView(BaseModel):
    """View projected for the audit subsystem.

    Visible: ALL fields including change_history.
    Hidden:  nothing -- audit sees everything.
    """

    model_config = ConfigDict(frozen=True)

    twin_object_id: str
    state_semantics: StateSemantics | None
    constraint_state: ConstraintState | None
    identity_invariants: IdentityInvariants | None
    model_governance: ModelGovernanceState | None
    knowledge_state: KnowledgeState | None
    action_state: ActionState | None
    audit_trail: AuditTrail | None
    action_templates: list[dict]
    human_roles: list[HumanRole]
    safe_fallback: SafeFallback | None
    rigidity_rules: list[dict]
    audit_benchmark_reference: str | None
    hidden_challenge_set_reference: str | None
    public_eval_set_reference: str | None
    change_history: ChangeHistory | None

    @classmethod
    def from_internal(cls, obj: TwinObjectInternal) -> AuditView:
        return cls(
            twin_object_id=obj.identity.id,
            state_semantics=obj.state_semantics,
            constraint_state=obj.constraint_state,
            identity_invariants=obj.identity_invariants,
            model_governance=obj.model_governance,
            knowledge_state=obj.knowledge_state,
            action_state=obj.action_state,
            audit_trail=obj.audit_trail,
            action_templates=[t.model_dump() for t in obj.action_templates],
            human_roles=obj.human_roles,
            safe_fallback=obj.safe_fallback,
            rigidity_rules=[r.model_dump() for r in obj.rigidity_rules],
            audit_benchmark_reference=obj.audit_benchmark_reference,
            hidden_challenge_set_reference=obj.hidden_challenge_set_reference,
            public_eval_set_reference=obj.public_eval_set_reference,
            change_history=obj.change_history,
        )
