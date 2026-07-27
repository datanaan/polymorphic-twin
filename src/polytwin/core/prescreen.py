"""PrescreenLibrary: stateless constraint verification for Lab use.

Provides non-authoritative constraint verification functions that Lab can
use to quickly check hypotheses before full Core evaluation.  Results are
always marked is_authoritative=False — they are advisory only.
"""
from __future__ import annotations

from polytwin.core.rules.evaluator import evaluate_constraint
from polytwin.core.types import PrescreenResult


class PrescreenLibrary:
    """Stateless constraint prescreen for Lab exploration.

    Reuses the same evaluation logic as Core's constraint evaluator, but
    wraps results in PrescreenResult with is_authoritative=False.  Lab can
    call prescreen() to get quick feedback without going through the full
    Core validation pipeline.
    """

    def prescreen(
        self, state_values: dict[str, float], constraint_cards: list[dict]
    ) -> list[PrescreenResult]:
        """Run constraint validation. Results are PRESCREEN ONLY, NOT AUTHORITATIVE.

        Args:
            state_values: Current state variable values.
            constraint_cards: List of constraint card dicts from DomainPack.

        Returns:
            List of PrescreenResult — one per constraint card.
            Each result has is_authoritative=False.
        """
        results: list[PrescreenResult] = []
        for card in constraint_cards:
            result = evaluate_constraint(card, state_values)
            results.append(
                PrescreenResult(
                    status=result.status,
                    is_authoritative=False,  # ALWAYS False
                )
            )
        return results
