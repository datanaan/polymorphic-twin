"""Unified exception hierarchy for the Polymorphic-Twin SDK.

All public exceptions inherit from PolymorphicTwinError, allowing callers
to catch any SDK error with a single except clause or handle specific
subclasses individually.
"""
from __future__ import annotations


class PolymorphicTwinError(Exception):
    """Base exception for all Polymorphic-Twin errors."""

    pass


class PermissionDeniedError(PolymorphicTwinError):
    """Caller does not have permission for the requested operation.

    Raised when view isolation rules, role-based access control, or
    component-level boundaries are violated.
    """

    pass


class ValidationError(PolymorphicTwinError):
    """Data validation failed.

    Raised when input data does not conform to expected schemas or
    fails business-rule validation.
    """

    pass


class DomainPackValidationError(PolymorphicTwinError):
    """DomainPack configuration validation failed.

    Raised when a DomainPack file contains invalid structure, violates
    the rigid-criticality compatibility rule, or fails schema validation.
    """

    pass


class ConstraintViolationError(PolymorphicTwinError):
    """Constraint validation detected a violation.

    Raised when a safety-critical or identity-critical constraint fails
    during validation.
    """

    pass


class SafetyFallbackError(PolymorphicTwinError):
    """Safety fallback was triggered.

    Raised when the system executes a safety fallback strategy in
    response to a constraint violation.
    """

    pass


class IdentityDriftError(PolymorphicTwinError):
    """Identity drift detected beyond tolerance.

    Raised when an identity check reveals that a TwinObject's invariants
    have drifted beyond the configured tolerance threshold.
    """

    pass
