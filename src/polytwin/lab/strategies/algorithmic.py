"""AlgorithmicStrategy: grid-search based exploration.

Iterates over state-variable ranges derived from constraint cards to
find boundary violations. This is the first (and default) exploration
strategy, operating with ``constraint_awareness = "algorithmic"``.
"""
from __future__ import annotations

import uuid

from polytwin.lab.strategies.base import ExplorationStrategy
from polytwin.lab.types import (
    Counterexample,
    ExplorationBudget,
    ExplorationResult,
    Finding,
)


class AlgorithmicStrategy(ExplorationStrategy):
    """Grid-search strategy that tests state-variable boundaries.

    For each constraint with a numeric range (min/max), this strategy
    generates boundary-probing test points to discover violations.
    """

    def name(self) -> str:
        return "algorithmic_grid_search"

    def explore(
        self,
        data: dict,
        constraints: list[dict],
        budget: ExplorationBudget,
    ) -> ExplorationResult:
        findings: list[Finding] = []
        counterexamples: list[Counterexample] = []
        iterations = 0

        for constraint in constraints:
            if iterations >= budget.max_iterations:
                break
            iterations += 1

            validation = constraint.get("validation", {})
            config = validation.get("config", {})
            var = config.get("variable", "")
            if not var:
                continue

            max_val = config.get("max")
            min_val = config.get("min")
            criticality = constraint.get("scenario_criticality", "operational")
            constraint_id = constraint.get("constraint_id", str(uuid.uuid4()))

            # Test boundary above max
            if max_val is not None:
                test_val = max_val + 0.01
                counterexamples.append(
                    Counterexample(
                        counterexample_id=str(uuid.uuid4()),
                        state_at_failure={var: test_val},
                        constraint_violated=constraint_id,
                        severity="high" if criticality == "safety_critical" else "medium",
                    )
                )
                findings.append(
                    Finding(
                        finding_id=str(uuid.uuid4()),
                        type="counterexample",
                        description=f"Variable '{var}' at {test_val} exceeds max {max_val}",
                        confidence=1.0,
                        data={"variable": var, "test_value": test_val, "max": max_val},
                    )
                )

            # Test boundary below min
            if min_val is not None:
                test_val = min_val - 0.01
                counterexamples.append(
                    Counterexample(
                        counterexample_id=str(uuid.uuid4()),
                        state_at_failure={var: test_val},
                        constraint_violated=constraint_id,
                        severity="high" if criticality == "safety_critical" else "medium",
                    )
                )
                findings.append(
                    Finding(
                        finding_id=str(uuid.uuid4()),
                        type="counterexample",
                        description=f"Variable '{var}' at {test_val} below min {min_val}",
                        confidence=1.0,
                        data={"variable": var, "test_value": test_val, "min": min_val},
                    )
                )

        return ExplorationResult(
            findings=findings,
            counterexamples=counterexamples,
            confidence_scores={"boundary_detection": 1.0},
            strategy_manifest=self.reproducibility_manifest(),
        )

    def reproducibility_manifest(self) -> dict:
        return {
            "strategy": self.name(),
            "version": "0.1.0",
            "method": "grid_search_boundary_probing",
            "boundary_offset": 0.01,
            "deterministic": True,
        }

    def constraint_awareness(self) -> str:
        return "algorithmic"

    def data_requirements(self) -> list[str]:
        return ["state_variables", "constraint_cards"]

    def exploration_space_mapping(self) -> dict:
        return {
            "type": "grid",
            "dimensions": "state_variable_count",
            "resolution": "boundary_probing",
        }

    def health_indicators(self) -> dict:
        return {"status": "healthy", "strategy": self.name()}
