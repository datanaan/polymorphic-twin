"""Core constraint governance engine.

The Core module is the runtime constraint gatekeeper. It validates model
qualification, enforces physical constraints, executes safe fallback, and
manages evidence admission.
"""

from polytwin.core.rules import (
    combine,
    evaluate_constraint,
    evaluate_domain_of_validity,
    get_validator,
    register_validator,
)
from polytwin.core.types import (
    DriftSample,
    EvidenceAdmissionResult,
    FallbackResult,
    HardGateCheckResult,
    HardGateResult,
    IdentityCheckResult,
    PrescreenResult,
    QuarantineRejection,
    SingleConstraintResult,
    ValidationResult,
)

__all__ = [
    "DriftSample",
    "EvidenceAdmissionResult",
    "FallbackResult",
    "HardGateCheckResult",
    "HardGateResult",
    "IdentityCheckResult",
    "PrescreenResult",
    "QuarantineRejection",
    "SingleConstraintResult",
    "ValidationResult",
    "combine",
    "evaluate_constraint",
    "evaluate_domain_of_validity",
    "get_validator",
    "register_validator",
]
