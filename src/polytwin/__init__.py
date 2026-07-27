"""Polymorphic-Twin: Trusted governance infrastructure for digital twin systems.

Public API whitelist -- only symbols listed in __all__ are considered stable.
"""
from __future__ import annotations

# Bridge types
from polytwin.bridge.types import ActionSpace, BridgeOutput

# Configuration
from polytwin.config import EngineConfig

# Core result types
from polytwin.core.types import (
    FallbackResult,
    HardGateResult,
    IdentityCheckResult,
    SingleConstraintResult,
    ValidationResult,
)

# DomainPack types
from polytwin.domainpack.types import ConstraintCard, DomainPack, StateVariable

# Engine (main entry point)
from polytwin.engine import PolymorphicTwinEngine

# Exceptions
from polytwin.exceptions import (
    ConstraintViolationError,
    DomainPackValidationError,
    IdentityDriftError,
    PermissionDeniedError,
    PolymorphicTwinError,
    SafetyFallbackError,
)
from polytwin.exceptions import (
    ValidationError as PTValidationError,
)

# Core types (re-exported)
from polytwin.tom.types import (
    CallerIdentity,
    ConstraintStatus,
    Criticality,
    HealthState,
    LifecycleState,
    ObjectType,
    Rigidity,
    ViewType,
)

__version__ = "0.1.0"

__all__ = [
    # Engine
    "PolymorphicTwinEngine",
    # Configuration
    "EngineConfig",
    # TOM types
    "ObjectType",
    "LifecycleState",
    "HealthState",
    "ViewType",
    "Criticality",
    "Rigidity",
    "ConstraintStatus",
    "CallerIdentity",
    # DomainPack
    "DomainPack",
    "ConstraintCard",
    "StateVariable",
    # Core results
    "ValidationResult",
    "SingleConstraintResult",
    "HardGateResult",
    "FallbackResult",
    "IdentityCheckResult",
    # Bridge
    "ActionSpace",
    "BridgeOutput",
    # Exceptions
    "PolymorphicTwinError",
    "PermissionDeniedError",
    "PTValidationError",
    "DomainPackValidationError",
    "ConstraintViolationError",
    "SafetyFallbackError",
    "IdentityDriftError",
    # Metadata
    "__version__",
]
