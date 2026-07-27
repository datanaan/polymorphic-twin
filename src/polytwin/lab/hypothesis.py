"""Hypothesis generator: produces testable constraint hypotheses.

Generates hypotheses about constraint boundaries and behaviors based
on exploration data. Each hypothesis includes falsification tests
that Core can later verify.
"""
from __future__ import annotations

import uuid

from polytwin.lab.strategies.base import ExplorationStrategy
from polytwin.lab.types import (
    ExplorationBudget,
    Hypothesis,
)


class HypothesisGenerator:
    """Generates testable hypotheses from exploration data.

    Uses an ExplorationStrategy to explore the state space, then
    converts findings into structured Hypothesis objects with
    falsification tests.
    """

    def __init__(self, strategy: ExplorationStrategy) -> None:
        self._strategy = strategy

    async def generate(
        self,
        data: dict,
        constraints: list[dict],
        budget: ExplorationBudget,
    ) -> list[Hypothesis]:
        """Generate hypotheses about constraint behavior.

        Args:
            data: LabExplorationView-compatible data.
            constraints: Constraint card dicts.
            budget: Resource budget.

        Returns:
            List of Hypothesis instances.
        """
        result = self._strategy.explore(data, constraints, budget)
        hypotheses = list(result.hypotheses)

        # Augment findings into hypotheses if no explicit hypotheses
        if not hypotheses and result.findings:
            for finding in result.findings:
                hypotheses.append(
                    Hypothesis(
                        hypothesis_id=str(uuid.uuid4()),
                        statement=f"Based on finding: {finding.description}",
                        falsification_tests=[
                            {"type": "boundary_test", "data": finding.data},
                        ],
                        supporting_evidence=[finding.finding_id],
                        confidence=finding.confidence,
                    )
                )

        return hypotheses

    @staticmethod
    def create_constraint_hypothesis(
        variable: str,
        observed_boundary: float,
        constraint_id: str,
    ) -> Hypothesis:
        """Create a single hypothesis about a constraint boundary.

        Args:
            variable: The state variable name.
            observed_boundary: The observed boundary value.
            constraint_id: Related constraint card id.

        Returns:
            A Hypothesis instance with falsification tests.
        """
        return Hypothesis(
            hypothesis_id=str(uuid.uuid4()),
            statement=(
                f"Variable '{variable}' has an effective boundary "
                f"at {observed_boundary} for constraint '{constraint_id}'"
            ),
            falsification_tests=[
                {
                    "type": "boundary_probe",
                    "variable": variable,
                    "test_value": observed_boundary + 0.01,
                    "expected": "violation",
                },
                {
                    "type": "boundary_probe",
                    "variable": variable,
                    "test_value": observed_boundary - 0.01,
                    "expected": "compliance",
                },
            ],
            supporting_evidence=[],
            confidence=0.8,
        )
