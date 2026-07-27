"""DomainPack runtime module (DP v0.3).

Provides typed models, validation, parsing, registry, and lifecycle
management for DomainPack configuration units.
"""
from .lifecycle import check_inheritance_compatibility
from .parser import DomainPackValidationError, parse_domainpack
from .registry import DomainPackRegistry
from .types import (
    ActionTemplate,
    ConstraintCard,
    DomainOfValidity,
    DomainPack,
    ExceptionRequestAuthority,
    HumanRole,
    IdentityMonitorConfig,
    InheritancePolicy,
    RigidityCriticalityCompatibility,
    SafeFallback,
    StateVariable,
    Tolerance,
    ValidationConfig,
    ValidityCondition,
)
from .validator import ValidationError, validate_domainpack_data

__all__ = [
    # Types
    "ActionTemplate",
    "ConstraintCard",
    "DomainOfValidity",
    "DomainPack",
    "ExceptionRequestAuthority",
    "HumanRole",
    "IdentityMonitorConfig",
    "InheritancePolicy",
    "RigidityCriticalityCompatibility",
    "SafeFallback",
    "StateVariable",
    "Tolerance",
    "ValidityCondition",
    "ValidationConfig",
    # Validator
    "ValidationError",
    "validate_domainpack_data",
    # Parser
    "DomainPackValidationError",
    "parse_domainpack",
    # Registry
    "DomainPackRegistry",
    # Lifecycle
    "check_inheritance_compatibility",
]
