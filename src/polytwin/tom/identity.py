"""Identity and lineage utilities for TwinObjects.

Provides provenance tracing, trust scoring, and provenance entry
management for the TwinObject lifecycle.
"""

from __future__ import annotations

from datetime import UTC, datetime

from polytwin.tom.base_models import ProvenanceEntry
from polytwin.tom.domain_models import TwinObjectInternal


def trace_provenance(obj: TwinObjectInternal) -> list[ProvenanceEntry]:
    """Return the full provenance chain from lineage.

    Args:
        obj: TwinObjectInternal whose provenance to trace.

    Returns:
        Ordered list of ProvenanceEntry records.
    """
    return list(obj.lineage.provenance)


def compute_trust(obj: TwinObjectInternal) -> float:
    """Compute trust score based on provenance depth.

    Trust decays with distance from the original source.
    Formula: ``base_trust * decay^depth`` where ``decay=0.95`` per level.

    Args:
        obj: TwinObjectInternal to score.

    Returns:
        Trust score in [0, 1].
    """
    depth = len(obj.lineage.provenance)
    base_trust = 1.0
    decay = 0.95
    return base_trust * (decay**depth)


def add_provenance_entry(
    obj: TwinObjectInternal,
    source: str,
    action: str,
    actor: str,
) -> None:
    """Add a provenance entry to the object's lineage (mutates in place).

    Args:
        obj: TwinObjectInternal to update.
        source: Origin system or component.
        action: What was done (e.g. "created", "updated").
        actor: Who or what performed the action.
    """
    entry = ProvenanceEntry(
        source=source,
        timestamp=datetime.now(UTC),
        action=action,
        actor=actor,
    )
    obj.lineage.provenance.append(entry)
