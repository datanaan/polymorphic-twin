"""Core-specific types for the constraint governance engine.

Defines result models used during constraint evaluation, combination,
hard-gate checks, fallback execution, evidence admission, and identity
monitoring.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from polytwin.tom.types import ConstraintStatus, Criticality, Rigidity

# ── Single constraint evaluation ────────────────────────────────────


class SingleConstraintResult(BaseModel):
    """Outcome of evaluating one constraint card."""

    constraint_id: str
    status: ConstraintStatus = ConstraintStatus.UNCERTAIN
    actual_values: dict[str, float] = Field(default_factory=dict)
    threshold: dict = Field(default_factory=dict)
    rigidity: Rigidity = Rigidity.ABSOLUTE
    criticality: Criticality = Criticality.OPERATIONAL
    message: str = ""


# ── Combined validation result ──────────────────────────────────────


class ValidationResult(BaseModel):
    """Outcome of evaluating and combining multiple constraints."""

    passed: bool = False
    individual_results: list[SingleConstraintResult] = Field(default_factory=list)
    combination_logic: str = "and"
    requires_human_review: bool = False
    safety_fallback_triggered: bool = False
    evaluated_count: int = 0


# ── Hard-gate check ─────────────────────────────────────────────────


class HardGateCheckResult(BaseModel):
    """Result of a single hard-gate check."""

    check_name: str
    passed: bool = False
    details: str = ""


class HardGateResult(BaseModel):
    """Aggregated hard-gate decision linking models to trust levels."""

    granted_links: list[str] = Field(default_factory=list)
    degraded_links: list[str] = Field(default_factory=list)
    denied_links: list[str] = Field(default_factory=list)


# ── Fallback ────────────────────────────────────────────────────────


class FallbackResult(BaseModel):
    """Record of a safe-fallback execution."""

    strategy_used: str = ""
    object_id: str = ""
    violated_constraint: str = ""


# ── Prescreen ───────────────────────────────────────────────────────


class PrescreenResult(BaseModel):
    """Quick prescreen outcome before full evaluation.

    ``is_authoritative`` is **always** False — a prescreen never
    constitutes a final authoritative decision.
    """

    status: ConstraintStatus = ConstraintStatus.UNCERTAIN
    is_authoritative: bool = False  # ALWAYS False


# ── Quarantine ──────────────────────────────────────────────────────


class QuarantineRejection(BaseModel):
    """Reason an object was rejected during quarantine screening."""

    rejected: bool = False
    reason: str = ""
    detail: str = ""


# ── Evidence admission ──────────────────────────────────────────────


class EvidenceAdmissionResult(BaseModel):
    """Outcome of admitting a single piece of evidence."""

    item_id: str
    admitted: bool = False
    reason: str = ""


# ── Identity / drift ───────────────────────────────────────────────


class IdentityCheckResult(BaseModel):
    """Result of an identity-consistency check."""

    identity_status: str = "confirmed"
    drift_values: dict[str, float] = Field(default_factory=dict)
    timestamp: str = ""


class DriftSample(BaseModel):
    """A single drift measurement for an invariant."""

    invariant_name: str
    drift: float = 0.0
    timestamp: str = ""


# ── Certification ──────────────────────────────────────────────────


class Certificate(BaseModel):
    """A qualification certificate issued to a model."""

    model_id: str
    score: float = 0.0


class CertificationResult(BaseModel):
    """Outcome of a certification request."""

    granted: bool = False
    score: float = 0.0
    certificate: Certificate | None = None
    gaps: list[str] = Field(default_factory=list)
