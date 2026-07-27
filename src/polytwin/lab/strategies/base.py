"""ExplorationStrategy abstract base class.

All exploration strategies must implement this interface. Strategies are
pluggable: the Lab can use any combination of them to explore the state
space, generate hypotheses, and find counterexamples.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from polytwin.lab.types import ExplorationBudget, ExplorationResult


class ExplorationStrategy(ABC):
    """Abstract base for all Lab exploration strategies.

    Each strategy must declare its name, constraint awareness level,
    data requirements, exploration space mapping, and health indicators.
    The core entry point is :meth:`explore`.
    """

    @abstractmethod
    def name(self) -> str:
        """Return the strategy's unique name."""
        ...

    @abstractmethod
    def explore(
        self,
        data: dict,
        constraints: list[dict],
        budget: ExplorationBudget,
    ) -> ExplorationResult:
        """Execute the exploration strategy.

        Args:
            data: LabExplorationView-compatible data (dict).
            constraints: Constraint card dicts visible to the Lab.
            budget: Resource budget for this run.

        Returns:
            ExplorationResult with findings, counterexamples, etc.
        """
        ...

    @abstractmethod
    def reproducibility_manifest(self) -> dict:
        """Return a manifest describing how to reproduce the strategy's results."""
        ...

    @abstractmethod
    def constraint_awareness(self) -> str:
        """Return awareness level: 'algorithmic', 'ml', or 'llm'."""
        ...

    @abstractmethod
    def data_requirements(self) -> list[str]:
        """Return a list of required data field names."""
        ...

    @abstractmethod
    def exploration_space_mapping(self) -> dict:
        """Return a description of the strategy's exploration space."""
        ...

    @abstractmethod
    def health_indicators(self) -> dict:
        """Return current health / performance indicators."""
        ...
