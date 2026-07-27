"""Constraint prohibition model for view projections.

Used by BridgeDecisionView to summarise constraint violations
with human-readable prohibition reasons.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from polytwin.tom.types import ConstraintStatus, Criticality


class ConstraintProhibition(BaseModel):
    """Summarises why a constraint is prohibited (or passed) for Bridge consumers.

    Attributes:
        constraint_id: Reference to the constraint.
        status: Evaluation result (passed / uncertain / failed / not_applicable).
        criticality: How critical the constraint is.
        prohibition_reason: Human-readable reason. ``None`` when the
            constraint passed; non-``None`` when violated or uncertain.
    """

    model_config = ConfigDict(frozen=True)

    constraint_id: str
    status: ConstraintStatus
    criticality: Criticality
    prohibition_reason: str | None = None
