"""Generic base-layer models shared by every TwinObject.

These models capture identity, lineage, relationships, access stats,
and state -- the structural skeleton that all domain-specific
TwinObjects extend.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from polytwin.tom.types import (
    HealthState,
    LifecycleState,
    ObjectType,
    RelationType,
)

# ── Identity ───────────────────────────────────────────────────────


class Identity(BaseModel):
    """Uniquely identifies a TwinObject.

    Attributes:
        id: Auto-generated UUID4.
        type: Categorisation of the object.
        name: Optional human-readable name.
        tags: Free-form string labels for search/filter.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ObjectType
    name: str = ""
    tags: list[str] = Field(default_factory=list)


# ── Provenance / Lineage ───────────────────────────────────────────


class ProvenanceEntry(BaseModel):
    """A single provenance record in the lineage chain.

    Attributes:
        source: Origin system or component.
        timestamp: When the action occurred.
        action: What was done (e.g. "created", "updated").
        actor: Who or what performed the action.
    """

    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    action: str
    actor: str


class Lineage(BaseModel):
    """Tracks creation chain and provenance history.

    Attributes:
        creator_id: ID of the TwinObject that created this one.
        parent_id: Optional parent TwinObject ID for version chains.
        provenance: Ordered list of provenance entries.
    """

    creator_id: str
    parent_id: str | None = None
    provenance: list[ProvenanceEntry] = Field(default_factory=list)


# ── Relationships ──────────────────────────────────────────────────


class Relationship(BaseModel):
    """A typed edge from this TwinObject to another.

    Attributes:
        target_id: The related TwinObject's ID.
        type: Semantic relationship type.
        strength: Normalised confidence [0, 1].
        bidirectional: If True, the reverse edge is implied.
        metadata: Arbitrary extra key-value pairs.
    """

    target_id: str
    type: RelationType
    strength: float = Field(default=1.0, ge=0.0, le=1.0)
    bidirectional: bool = False
    metadata: dict = Field(default_factory=dict)


# ── Access stats ───────────────────────────────────────────────────


class AccessStats(BaseModel):
    """Usage metrics for a TwinObject.

    Attributes:
        view_count: Total number of times viewed.
        last_viewed_at: Timestamp of most recent view.
        last_modified_by: ID of the last modifier.
    """

    view_count: int = 0
    last_viewed_at: datetime | None = None
    last_modified_by: str = ""


# ── State ──────────────────────────────────────────────────────────


class State(BaseModel):
    """Current lifecycle and health of a TwinObject.

    Attributes:
        lifecycle: Which lifecycle stage the object is in.
        health: Operational health indicator.
    """

    lifecycle: LifecycleState = LifecycleState.CREATING
    health: HealthState = HealthState.UNKNOWN


# ── TwinObjectBase ─────────────────────────────────────────────────


def _utc_now() -> datetime:
    return datetime.now(UTC)


class TwinObjectBase(BaseModel):
    """Root structural model that all concrete TwinObjects extend.

    Attributes:
        identity: Unique identification and typing.
        lineage: Creation chain and provenance.
        state: Lifecycle and health.
        relationships: Edges to other TwinObjects.
        access_stats: Usage metrics.
        created_at: Creation timestamp (UTC).
        last_modified: Last modification timestamp (UTC).
        version: Semantic version string.
    """

    identity: Identity
    lineage: Lineage
    state: State = Field(default_factory=State)
    relationships: list[Relationship] = Field(default_factory=list)
    access_stats: AccessStats = Field(default_factory=AccessStats)
    created_at: datetime = Field(default_factory=_utc_now)
    last_modified: datetime = Field(default_factory=_utc_now)
    version: str = "1.0.0"
