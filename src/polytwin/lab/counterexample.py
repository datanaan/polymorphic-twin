"""Counterexample finder: discovers constraint boundary violations.

Uses an ExplorationStrategy (typically AlgorithmicStrategy) to probe
state-space boundaries and identify counterexamples where constraints
fail.
"""
from __future__ import annotations

from polytwin.lab.strategies.base import ExplorationStrategy
from polytwin.lab.types import Counterexample, ExplorationBudget, ExplorationResult


class CounterexampleFinder:
    """Finds counterexamples by probing constraint boundaries.

    Wraps an ExplorationStrategy and focuses its output on
    counterexample extraction.
    """

    def __init__(self, strategy: ExplorationStrategy) -> None:
        self._strategy = strategy

    async def find(
        self,
        data: dict,
        constraints: list[dict],
        budget: ExplorationBudget,
    ) -> list[Counterexample]:
        """Find counterexamples in the given data/constraint space.

        Args:
            data: LabExplorationView-compatible data.
            constraints: Constraint card dicts.
            budget: Resource budget.

        Returns:
            List of Counterexample instances.
        """
        result = self._strategy.explore(data, constraints, budget)
        return result.counterexamples

    async def find_with_context(
        self,
        data: dict,
        constraints: list[dict],
        budget: ExplorationBudget,
    ) -> ExplorationResult:
        """Find counterexamples and return full ExplorationResult context."""
        return self._strategy.explore(data, constraints, budget)

    @staticmethod
    def classify_severity(
        counterexample: Counterexample,
        constraints: list[dict],
    ) -> str:
        """Classify a counterexample's severity based on constraint metadata.

        Returns "high" for safety-critical constraint violations,
        "medium" otherwise.
        """
        cid = counterexample.constraint_violated
        for c in constraints:
            if c.get("constraint_id") == cid and c.get("scenario_criticality") == "safety_critical":
                return "high"
        return counterexample.severity
