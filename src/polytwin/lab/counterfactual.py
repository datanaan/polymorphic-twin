"""Counterfactual scenario generator: explores alternative state trajectories.

Generates "what-if" scenarios by modifying state variables and measuring
divergence from baseline behavior. This helps understand sensitivity
and robustness of constraint boundaries.
"""
from __future__ import annotations

import uuid

from polytwin.lab.types import CounterfactualScenario, ExplorationBudget


class CounterfactualGenerator:
    """Generates counterfactual scenarios for divergence analysis.

    Takes a base state and systematically modifies individual variables
    to measure how behavior diverges. The Lab uses this to understand
    which variables are most sensitive.
    """

    async def generate(
        self,
        base_state: dict,
        constraints: list[dict],
        budget: ExplorationBudget | None = None,
    ) -> list[CounterfactualScenario]:
        """Generate counterfactual scenarios from a base state.

        Args:
            base_state: The reference state to modify.
            constraints: Constraint card dicts (LabExplorationView).
            budget: Optional resource budget.

        Returns:
            List of CounterfactualScenario instances.
        """
        scenarios: list[CounterfactualScenario] = []
        max_iterations = budget.max_iterations if budget else 1000
        iterations = 0

        for constraint in constraints:
            if iterations >= max_iterations:
                break

            validation = constraint.get("validation", {})
            config = validation.get("config", {})
            var = config.get("variable", "")
            if not var or var not in base_state:
                continue

            base_val = base_state[var]
            max_val = config.get("max")
            min_val = config.get("min")

            # Generate scenario pushing toward max boundary
            if max_val is not None:
                modified = dict(base_state)
                modified[var] = max_val
                scenarios.append(
                    CounterfactualScenario(
                        scenario_id=str(uuid.uuid4()),
                        base_state=dict(base_state),
                        modified_state=modified,
                        divergence_score=abs(max_val - base_val) / max(abs(base_val), 1e-9),
                        models_disagree=max_val < base_val,
                    )
                )
                iterations += 1

            # Generate scenario pushing toward min boundary
            if min_val is not None:
                modified = dict(base_state)
                modified[var] = min_val
                scenarios.append(
                    CounterfactualScenario(
                        scenario_id=str(uuid.uuid4()),
                        base_state=dict(base_state),
                        modified_state=modified,
                        divergence_score=abs(min_val - base_val) / max(abs(base_val), 1e-9),
                        models_disagree=min_val > base_val,
                    )
                )
                iterations += 1

        return scenarios

    @staticmethod
    def compute_divergence(base_state: dict, modified_state: dict) -> float:
        """Compute a normalized divergence score between two states.

        Uses L1 norm divided by the number of changed variables.
        """
        changed = 0
        total_diff = 0.0

        for key in set(base_state.keys()) | set(modified_state.keys()):
            val_a = base_state.get(key, 0.0)
            val_b = modified_state.get(key, 0.0)
            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                diff = abs(val_a - val_b)
                if diff > 0:
                    changed += 1
                    total_diff += diff

        return total_diff / changed if changed > 0 else 0.0
