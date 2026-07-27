"""Pydantic models for DomainPack structure (DP v0.3).

These models define the typed schema for DomainPack configuration units.
A DomainPack declares scenario-specific parameters: state variables, constraint
cards, safe fallback strategies, action templates, and human roles.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ── ValidityCondition ──────────────────────────────────────────────────


class ValidityCondition(BaseModel):
    """A single condition within a domain_of_validity block.

    Supports condition types:
    - state_range: variable value within [min, max]
    - state_enum: variable value in a set of values
    - sensor_status: a sensor has a required status
    - identity_confidence: minimum identity confidence threshold
    - composite: boolean combination of sub_conditions
    """

    type: str
    variable: str | None = None
    min: float | None = None
    max: float | None = None
    inclusive: bool = True
    values: list[str] | None = None
    sensor_id: str | None = None
    required_status: str | None = None
    operator: str | None = None
    sub_conditions: list[ValidityCondition] | None = None
    min_confidence: float | None = None

    model_config = {"extra": "allow"}


class DomainOfValidity(BaseModel):
    """Domain of validity: when a constraint or policy applies."""

    conditions: list[ValidityCondition] = Field(default_factory=list)
    match_mode: str = "all"


# ── ValidationConfig ──────────────────────────────────────────────────


class ValidationConfig(BaseModel):
    """How a constraint card is validated."""

    method: str
    config: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


# ── Tolerance ─────────────────────────────────────────────────────────


class Tolerance(BaseModel):
    """Tolerance specification for a constraint card."""

    absolute: float | None = None
    percentage: float | None = None

    model_config = {"extra": "allow"}


# ── ConstraintCard ────────────────────────────────────────────────────


class ConstraintCard(BaseModel):
    """A single constraint card defining a boundary condition."""

    constraint_id: str
    scenario_criticality: str
    domain_of_validity: DomainOfValidity = Field(default_factory=DomainOfValidity)
    validation: ValidationConfig
    tolerance: Tolerance | None = None
    violation_priority: int = 99
    weight: float | None = None
    audit_config: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


# ── StateVariable ─────────────────────────────────────────────────────


class StateVariable(BaseModel):
    """A state variable in the state_semantics_template."""

    name: str
    physical_meaning: str
    unit: str
    range_min: float = 0.0
    range_max: float = 0.0
    observability: str = "observable"
    controllability: str = "uncontrollable"
    measurement_source: str | None = None
    required: bool = True

    model_config = {"extra": "allow"}


# ── SafeFallback ──────────────────────────────────────────────────────


class SafeFallback(BaseModel):
    """Safe fallback strategy definition."""

    policy_id: str
    domain_of_validity: DomainOfValidity = Field(default_factory=DomainOfValidity)
    target_state: dict[str, Any] | None = None
    trajectory_constraints: dict[str, Any] | None = None
    max_duration: str = "PT0S"
    unavailable_action: str = "safe_shutdown"
    post_fallback_action: str = "hold"
    verification_record: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


# ── ActionTemplate ────────────────────────────────────────────────────


class ActionTemplate(BaseModel):
    """An action template definition."""

    action_type_id: str
    description_template: str = ""
    applicable_when: list[str] = Field(default_factory=list)
    monitoring_requirements: list[str] = Field(default_factory=list)
    fallback_if_fails: str = "hold"
    typical_prerequisites: list[str] = Field(default_factory=list)
    risk_profile: dict[str, Any] | None = None
    typical_prohibition_reasons: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


# ── HumanRole ─────────────────────────────────────────────────────────


class ExceptionRequestAuthority(BaseModel):
    """Authority granted to a human role for exception requests."""

    can_request_review: bool = False
    can_request_recertification: bool = False
    can_request_constraint_revision: bool = False
    can_initiate_human_takeover: bool = False
    can_initiate_safe_shutdown: bool = False

    model_config = {"extra": "allow"}


class HumanRole(BaseModel):
    """A human role definition with permissions."""

    role_id: str
    role_name: str = ""
    authorized_action_types: list[str] = Field(default_factory=list)
    exception_request_authority: ExceptionRequestAuthority | None = None
    approval_required_for: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


# ── InheritancePolicy ─────────────────────────────────────────────────


class InheritancePolicy(BaseModel):
    """Inheritance policy for DomainPack versioning."""

    can_relax_parent_absolute_constraints: bool = False
    can_lower_parent_criticality: bool = False
    conflict_resolution: str = "stricter_wins"
    parent_update_action: str = "require_recertification"
    parent_retirement_action_by_reason: dict[str, str] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


# ── RigidityCriticalityCompatibility ──────────────────────────────────


class RigidityCriticalityCompatibility(BaseModel):
    """Rigidity-criticality compatibility rules."""

    safety_critical: str = "must_be_absolute"
    identity_critical: str = "absolute_or_strictly_audited"
    operational: str = "absolute_or_soft_or_learnable"
    informational: str = "soft_or_learnable"

    model_config = {"extra": "allow"}


# ── IdentityMonitorConfig ─────────────────────────────────────────────


class IdentityMonitorConfig(BaseModel):
    """Identity monitoring configuration."""

    identity_check_interval: float = 1.0
    drift_tolerance: float = 0.05
    drift_trend_window: int = 100
    drift_trend_threshold: float = 0.02
    identity_uncertain_timeout: float = 30.0

    model_config = {"extra": "allow"}


# ── DomainPack (root model) ───────────────────────────────────────────


class DomainPack(BaseModel):
    """Complete DomainPack configuration unit.

    A DomainPack is a lightweight configuration unit that declares
    scenario-specific parameters for a digital twin governance scenario.
    It references existing external knowledge bases rather than creating
    new domain knowledge.
    """

    domain_id: str
    domain_name: str
    domain_version: str = "0.1.0"
    inheritance_policy: InheritancePolicy = Field(default_factory=InheritancePolicy)
    rigidity_criticality_compatibility: RigidityCriticalityCompatibility = Field(
        default_factory=RigidityCriticalityCompatibility
    )
    state_semantics_template: dict[str, Any] = Field(default_factory=dict)
    constraint_cards: dict[str, Any] = Field(default_factory=dict)
    safe_fallback: SafeFallback
    action_templates: dict[str, Any] = Field(default_factory=dict)
    human_roles: list[HumanRole] = Field(default_factory=list)
    validation_sets: dict[str, str] = Field(default_factory=dict)
    identity_monitor_config: IdentityMonitorConfig | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

    @property
    def variables(self) -> list[StateVariable]:
        """Parse state_semantics_template.variables into StateVariable models."""
        raw_vars = self.state_semantics_template.get("variables", [])
        return [StateVariable(**v) for v in raw_vars]

    @property
    def variable_names(self) -> set[str]:
        """Return set of defined state variable names."""
        return {v.name for v in self.variables}
