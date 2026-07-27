"""In-memory simulation engine for testing DomainPacks.

Allows step-by-step constraint validation against a DomainPack
configuration, with full history tracking and result export.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from polytwin.domainpack.types import DomainPack


class SimulationStep(BaseModel):
    """Result of a single simulation tick."""

    tick: int
    state: dict[str, float]
    passed: bool
    evaluated: int
    safety_fallback: bool
    individual: list[dict[str, Any]] = Field(default_factory=list)


class SimulationEngine:
    """In-memory simulation engine for testing DomainPacks.

    Runs constraint validation steps against a loaded DomainPack
    without requiring PostgreSQL or any external service. Each call
    to :meth:`step` validates the current state against the pack's
    constraint cards and appends the result to the internal history.

    Args:
        domain_pack: A parsed DomainPack instance (or None for an
            empty engine with no constraints).
    """

    def __init__(self, domain_pack: DomainPack | None = None) -> None:
        self._dp = domain_pack
        self._state: dict[str, float] = {}
        self._history: list[dict[str, Any]] = []
        self._tick = 0

    # ── State management ──────────────────────────────────────────────

    def set_state(self, values: dict[str, float]) -> None:
        """Replace the current simulation state."""
        self._state = dict(values)

    def get_state(self) -> dict[str, float]:
        """Return a copy of the current state."""
        return dict(self._state)

    # ── Simulation step ───────────────────────────────────────────────

    async def step(self) -> SimulationStep:
        """Execute one simulation step: validate constraints, record results."""
        self._tick += 1
        cards = self._get_constraint_cards()

        from polytwin.core.engine import ConstraintEngine

        engine = ConstraintEngine()
        result = await engine.validate(self._state, cards)

        individual: list[dict[str, Any]] = [
            {"id": r.constraint_id, "status": r.status.value}
            for r in result.individual_results
        ]

        step_data: dict[str, Any] = {
            "tick": self._tick,
            "state": dict(self._state),
            "passed": result.passed,
            "evaluated": result.evaluated_count,
            "safety_fallback": result.safety_fallback_triggered,
            "individual": individual,
        }
        self._history.append(step_data)
        return SimulationStep(**step_data)

    # ── Constraint card extraction ────────────────────────────────────

    def _get_constraint_cards(self) -> list[dict[str, Any]]:
        """Extract all constraint cards from the DomainPack as dicts."""
        if not self._dp:
            return []
        cards: list[dict[str, Any]] = []
        cc = self._dp.constraint_cards
        for rigidity in ("absolute", "soft", "learnable"):
            for card in cc.get(rigidity, []):
                if hasattr(card, "model_dump"):
                    cards.append(card.model_dump())
                elif isinstance(card, dict):
                    cards.append(card)
        return cards

    # ── History & export ──────────────────────────────────────────────

    def get_history(self) -> list[dict[str, Any]]:
        """Return a copy of the full step history."""
        return list(self._history)

    def export_results(self) -> dict[str, Any]:
        """Export simulation results with a manifest header."""
        return {
            "manifest": {
                "domain_pack": self._dp.domain_id if self._dp else None,
                "ticks": self._tick,
                "exported_at": datetime.now(UTC).isoformat(),
            },
            "history": self._history,
        }
