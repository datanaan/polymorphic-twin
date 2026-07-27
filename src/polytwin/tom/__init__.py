"""TwinObject Model (TOM) package.

Provides the complete data model layer for Polymorphic-Twin:
- types: enumerations and CallerIdentity
- base_models: structural skeleton (Identity, Lineage, State, etc.)
- domain_models: typed domain extensions and TwinObjectInternal
"""

from polytwin.tom.base_models import (
    AccessStats,
    Identity,
    Lineage,
    ProvenanceEntry,
    Relationship,
    State,
    TwinObjectBase,
)
from polytwin.tom.domain_models import (
    ActionState,
    ActionTemplate,
    AuditEvent,
    AuditTrail,
    ChangeHistory,
    ConstraintEvaluation,
    ConstraintState,
    HumanRole,
    IdentityInvariant,
    IdentityInvariants,
    KnowledgeState,
    ModelGovernanceState,
    RigidityRule,
    SafeFallback,
    StateSemantics,
    StateVariable,
    TwinObjectInternal,
)
from polytwin.tom.exceptions import PermissionDeniedError
from polytwin.tom.facade import InMemoryTwinObjectStore, TwinObjectFacade
from polytwin.tom.prohibitions import ConstraintProhibition
from polytwin.tom.types import (
    CallerIdentity,
    ConstraintStatus,
    Criticality,
    HealthState,
    LifecycleState,
    ObjectType,
    RelationType,
    Rigidity,
    ViewType,
)
from polytwin.tom.views import (
    AuditView,
    BridgeDecisionView,
    CoreCertificationView,
    CoreRuntimeView,
    LabExplorationView,
)

__all__ = [
    # Base models
    "AccessStats",
    "Identity",
    "Lineage",
    "ProvenanceEntry",
    "Relationship",
    "State",
    "TwinObjectBase",
    # Domain models
    "ActionState",
    "ActionTemplate",
    "AuditEvent",
    "AuditTrail",
    "ChangeHistory",
    "ConstraintEvaluation",
    "ConstraintState",
    "HumanRole",
    "IdentityInvariant",
    "IdentityInvariants",
    "KnowledgeState",
    "ModelGovernanceState",
    "RigidityRule",
    "SafeFallback",
    "StateSemantics",
    "StateVariable",
    "TwinObjectInternal",
    # Exceptions
    "PermissionDeniedError",
    # Facade
    "InMemoryTwinObjectStore",
    "TwinObjectFacade",
    # Prohibitions
    "ConstraintProhibition",
    # Types
    "CallerIdentity",
    "ConstraintStatus",
    "Criticality",
    "HealthState",
    "LifecycleState",
    "ObjectType",
    "RelationType",
    "Rigidity",
    "ViewType",
    # Views
    "AuditView",
    "BridgeDecisionView",
    "CoreCertificationView",
    "CoreRuntimeView",
    "LabExplorationView",
]
