"""TOM enumerations and CallerIdentity.

Defines every enum and the CallerIdentity value object used across
the TwinObject model layer.  All enums are string enums so their
serialised form is human-readable.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

# ── Object categorisation ──────────────────────────────────────────


class ObjectType(StrEnum):
    """Kind of entity a TwinObject represents."""

    USER = "user"
    AGENT = "agent"
    TOOL = "tool"
    DOC = "doc"
    CODE = "code"
    KNOWLEDGE = "knowledge"
    DEVICE = "device"
    SCENE = "scene"
    DOMAIN_PACK = "domain_pack"
    CONSTRAINT_CARD = "constraint_card"
    HYPOTHESIS = "hypothesis"
    EVIDENCE = "evidence"
    CUSTOM = "custom"


# ── Lifecycle / health ─────────────────────────────────────────────


class LifecycleState(StrEnum):
    """High-level lifecycle stage of a TwinObject."""

    CREATING = "creating"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    DELETED = "deleted"


class HealthState(StrEnum):
    """Operational health indicator."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    UNKNOWN = "unknown"


# ── Relationships ──────────────────────────────────────────────────


class RelationType(StrEnum):
    """Typed relationship between two TwinObjects."""

    OWNS = "owns"
    CREATED = "created"
    DEPENDS_ON = "depends_on"
    REFERENCES = "references"
    PART_OF = "part_of"
    VERSION_OF = "version_of"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    SIMILAR_TO = "similar_to"
    TRIGGERS = "triggers"


# ── Views ──────────────────────────────────────────────────────────


class ViewType(StrEnum):
    """Named projection views for TwinObject data."""

    CORE_RUNTIME = "core_runtime"
    CORE_CERTIFICATION = "core_certification"
    BRIDGE_DECISION = "bridge_decision"
    LAB_EXPLORATION = "lab_exploration"
    AUDIT = "audit"


# ── Constraint classification ──────────────────────────────────────


class Criticality(StrEnum):
    """How critical a constraint is to system safety."""

    SAFETY_CRITICAL = "safety_critical"
    IDENTITY_CRITICAL = "identity_critical"
    OPERATIONAL = "operational"
    INFORMATIONAL = "informational"


class Rigidity(StrEnum):
    """How strictly a constraint is enforced."""

    ABSOLUTE = "absolute"
    SOFT = "soft"
    LEARNABLE = "learnable"


class ConstraintStatus(StrEnum):
    """Evaluation result of a single constraint."""

    PASSED = "passed"
    UNCERTAIN = "uncertain"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


# ── Caller identity ────────────────────────────────────────────────


class CallerIdentity(BaseModel):
    """Identifies the component making a request through the system.

    Attributes:
        component: Logical component name (e.g. "core", "lab", "bridge").
        role: Role within the component (e.g. "validator", "explorer").
        session_id: Optional session correlation id.
    """

    component: str
    role: str
    session_id: str | None = Field(default=None)
