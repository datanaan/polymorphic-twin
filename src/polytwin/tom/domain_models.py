"""Typed domain models that extend TwinObjectBase.

These models carry the domain-specific payload for various subsystems:
Core validation, Lab exploration, Bridge decision, and audit.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from polytwin.tom.base_models import TwinObjectBase
from polytwin.tom.types import ConstraintStatus

# ── State variables ────────────────────────────────────────────────


class StateVariable(BaseModel):
    """Declaration of a single observable/controllable state variable.

    Attributes:
        name: Unique variable identifier within its domain.
        physical_meaning: Human-readable description of what this measures.
        unit: Physical unit (e.g. "degC", "Pa", "m/s").
        range_min: Lower bound of valid values.
        range_max: Upper bound of valid values.
        observability: How reliably the variable can be measured.
        controllability: How effectively the variable can be influenced.
        measurement_source: Origin of measurement data.
        required: Whether this variable must always be present.
    """

    name: str
    physical_meaning: str = ""
    unit: str = ""
    range_min: float | None = None
    range_max: float | None = None
    observability: str = "direct"
    controllability: str = "direct"
    measurement_source: str = ""
    required: bool = True


class StateSemantics(BaseModel):
    """Current state of a TwinObject expressed as variable values.

    Attributes:
        variables: Mapping of variable name -> StateVariable definition.
        current_values: Mapping of variable name -> current measured value.
    """

    variables: dict[str, StateVariable] = Field(default_factory=dict)
    current_values: dict[str, float | str | bool | None] = Field(default_factory=dict)


# ── Constraint evaluation ──────────────────────────────────────────


class ConstraintEvaluation(BaseModel):
    """Result of evaluating a single constraint against a TwinObject.

    Attributes:
        constraint_id: Reference to the evaluated constraint.
        status: Pass/fail/uncertain result.
        evaluated_at: When the evaluation occurred.
        actual_values: Measured values used in evaluation.
        message: Human-readable explanation.
    """

    constraint_id: str
    status: ConstraintStatus
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actual_values: dict[str, float | str | bool | None] = Field(default_factory=dict)
    message: str = ""


class ConstraintState(BaseModel):
    """Aggregate constraint evaluation state for a TwinObject.

    Attributes:
        active_constraints: Currently enforced constraint IDs.
        suspended_constraints: Temporarily disabled constraint IDs.
        last_evaluation: Most recent evaluation results.
    """

    active_constraints: list[str] = Field(default_factory=list)
    suspended_constraints: list[str] = Field(default_factory=list)
    last_evaluation: list[ConstraintEvaluation] = Field(default_factory=list)


# ── Identity invariants ────────────────────────────────────────────


class IdentityInvariant(BaseModel):
    """A single identity check comparing expected vs actual value.

    Attributes:
        name: Invariant identifier.
        expected_value: What the value should be.
        actual_value: What the value actually is.
        confidence: Confidence in the check result [0, 1].
    """

    name: str
    expected_value: float | str | bool | None
    actual_value: float | str | bool | None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class IdentityInvariants(BaseModel):
    """Collection of identity invariant checks with aggregate status.

    Attributes:
        invariants: Individual invariant checks.
        overall_confidence: Aggregate confidence score [0, 1].
        identity_status: Summary status (e.g. "confirmed", "suspect").
    """

    invariants: list[IdentityInvariant] = Field(default_factory=list)
    overall_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    identity_status: str = "confirmed"


# ── Model governance ───────────────────────────────────────────────


class ModelGovernanceState(BaseModel):
    """Tracks which models are qualified to act on this TwinObject.

    Attributes:
        active_links: IDs of currently qualified models.
        qualification_history: Record of qualification events.
        active_certificates: Currently valid model certificates.
    """

    active_links: list[str] = Field(default_factory=list)
    qualification_history: list[str] = Field(default_factory=list)
    active_certificates: list[str] = Field(default_factory=list)


# ── Knowledge state ────────────────────────────────────────────────


class KnowledgeState(BaseModel):
    """Manages evidence admitted from Lab exploration.

    Attributes:
        admitted_lab_evidence: IDs of evidence accepted into the knowledge base.
        pending_submissions: IDs of evidence awaiting review.
    """

    admitted_lab_evidence: list[str] = Field(default_factory=list)
    pending_submissions: list[str] = Field(default_factory=list)


# ── Action state ───────────────────────────────────────────────────


class ActionState(BaseModel):
    """Available actions for this TwinObject at the current moment.

    Attributes:
        current_safe_action_set: Action IDs that passed safety checks.
        fallback_available: Whether a fallback action is available.
    """

    current_safe_action_set: list[str] = Field(default_factory=list)
    fallback_available: bool = False


# ── Audit trail ────────────────────────────────────────────────────


class AuditEvent(BaseModel):
    """A single recorded audit event.

    Attributes:
        event_id: Unique event identifier.
        event_type: Category of event (e.g. "constraint_evaluated").
        timestamp: When the event occurred.
        actor: Who or what triggered the event.
        detail: Arbitrary detail payload.
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor: str
    detail: dict = Field(default_factory=dict)


class AuditTrail(BaseModel):
    """Ordered log of audit events.

    Attributes:
        events: Chronological list of audit events.
        created_at: When this trail was created.
    """

    events: list[AuditEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ── TwinObjectInternal ─────────────────────────────────────────────


class ActionTemplate(BaseModel):
    """Declares an action that a human operator may perform.

    Attributes:
        template_id: Unique template identifier.
        name: Human-readable action name.
        description: What this action does.
        required_role: Role required to authorise this action.
        parameters: JSON schema describing action parameters.
    """

    template_id: str
    name: str = ""
    description: str = ""
    required_role: str = ""
    parameters: dict = Field(default_factory=dict)


class HumanRole(BaseModel):
    """Declares a human role with permission level.

    Attributes:
        role_id: Unique role identifier.
        name: Human-readable role name.
        permission_level: Authorisation level (e.g. "approve", "observe").
        scope: What this role can act on.
    """

    role_id: str
    name: str = ""
    permission_level: str = ""
    scope: str = ""


class SafeFallback(BaseModel):
    """Declares the safe fallback strategy for emergency retreat.

    Attributes:
        strategy: Name of the fallback strategy.
        target_state: State values to retreat to.
        constraints: Constraint IDs enforced during fallback.
        details: Internal details (hidden from Bridge).
    """

    strategy: str = ""
    target_state: dict[str, float | str | bool | None] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    details: dict = Field(default_factory=dict)


class RigidityRule(BaseModel):
    """Maps a constraint to its rigidity classification.

    Attributes:
        constraint_id: The constraint this rule applies to.
        rigidity: How strictly this constraint is enforced.
        criticality: How critical this constraint is.
    """

    constraint_id: str
    rigidity: str = "absolute"
    criticality: str = "operational"


class ChangeHistory(BaseModel):
    """Tracks changes to a TwinObject over time.

    Attributes:
        entries: Ordered list of change records.
    """

    entries: list[dict] = Field(default_factory=list)


class TwinObjectInternal(TwinObjectBase):
    """Full internal representation of a TwinObject.

    This is the authoritative model used inside Core.  It is never
    exposed directly to external consumers; only projected views
    derived from it leave the system.

    All domain-specific fields are optional because a TwinObject
    starts with just identity + lineage and accumulates state
    over its lifecycle.
    """

    state_semantics: StateSemantics | None = None
    constraint_state: ConstraintState | None = None
    identity_invariants: IdentityInvariants | None = None
    model_governance: ModelGovernanceState | None = None
    knowledge_state: KnowledgeState | None = None
    action_state: ActionState | None = None
    audit_trail: AuditTrail | None = None
    # DomainPack-sourced fields visible to specific views
    action_templates: list[ActionTemplate] = Field(default_factory=list)
    human_roles: list[HumanRole] = Field(default_factory=list)
    safe_fallback: SafeFallback | None = None
    rigidity_rules: list[RigidityRule] = Field(default_factory=list)
    # Certification-only references (CoreCertificationView exclusive)
    audit_benchmark_reference: str | None = None
    hidden_challenge_set_reference: str | None = None
    # Lab-visible reference
    public_eval_set_reference: str | None = None
    # Audit-only history
    change_history: ChangeHistory | None = None
