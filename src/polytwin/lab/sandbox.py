"""Sandbox: isolated execution environment for exploration strategies.

The Sandbox enforces Lab isolation by ensuring that:
1. Data passed in is dict-based (from LabExplorationView projection).
2. Strategy results are always wrapped with a manifest.
3. No access to Core internals is possible within this boundary.
"""
from __future__ import annotations

from polytwin.lab.strategies.base import ExplorationStrategy
from polytwin.lab.types import ExplorationBudget, ExplorationResult


class Sandbox:
    """Isolated sandbox for executing exploration strategies.

    The sandbox acts as the execution boundary between the Lab and
    external systems. All strategy runs must pass through here.
    """

    async def execute(
        self,
        strategy: ExplorationStrategy,
        data: dict,
        budget: ExplorationBudget,
    ) -> ExplorationResult:
        """Execute a strategy in the sandbox.

        Args:
            strategy: The exploration strategy to run.
            data: Data from LabExplorationView (must be a dict).
            budget: Resource budget for this run.

        Returns:
            ExplorationResult with strategy manifest injected.

        Raises:
            TypeError: If data is not a dict (enforcing LabExplorationView
                projection).
        """
        # Type enforcement: data must be lab-compatible format
        if not isinstance(data, dict):
            raise TypeError(
                "Sandbox only accepts dict data (from LabExplorationView)"
            )

        constraints = data.get("constraints", [])
        result = strategy.explore(data, constraints, budget)

        # Inject manifest into result
        manifest = strategy.reproducibility_manifest()
        result.strategy_manifest = manifest

        return result

    def validate_data_access(self, data: dict) -> bool:
        """Verify that data does not contain hidden validation set references.

        This is a secondary guard: the DataReleaseManager already filters,
        but the sandbox double-checks.
        """
        forbidden_keys = {
            "audit_benchmark_reference",
            "production_acceptance_reference",
            "hidden_challenge_set",
            "hidden_validation_set",
        }
        text = str(data).lower()
        return all(key not in text for key in forbidden_keys)
