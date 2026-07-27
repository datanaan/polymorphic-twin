"""LabExplorer: orchestrates the four Lab exploration modes.

The LabExplorer provides four exploration modes:
1. Counterexample search — find constraint boundary violations
2. Constraint hypothesis — generate testable hypotheses
3. Failure correlation — correlate failure events
4. Counterfactual generation — explore alternative states

All modes operate within Sandbox isolation and only see
LabExplorationView-projected data.
"""
from __future__ import annotations

from polytwin.lab.counterexample import CounterexampleFinder
from polytwin.lab.counterfactual import CounterfactualGenerator
from polytwin.lab.failure_analyzer import FailureAnalyzer
from polytwin.lab.hypothesis import HypothesisGenerator
from polytwin.lab.sandbox import Sandbox
from polytwin.lab.strategies.base import ExplorationStrategy
from polytwin.lab.types import (
    CorrelationFinding,
    Counterexample,
    CounterfactualScenario,
    ExplorationBudget,
    ExplorationResult,
    Hypothesis,
)


class LabExplorer:
    """Main Lab exploration orchestrator.

    Provides four exploration modes, each delegating to a specialized
    component. All exploration happens through the Sandbox.
    """

    def __init__(self, strategy: ExplorationStrategy) -> None:
        self._strategy = strategy
        self._sandbox = Sandbox()
        self._counterexample_finder = CounterexampleFinder(strategy)
        self._hypothesis_generator = HypothesisGenerator(strategy)
        self._failure_analyzer = FailureAnalyzer()
        self._counterfactual_generator = CounterfactualGenerator()

    # ── Mode 1: Counterexample search ──────────────────────────────────

    async def run_counterexample_search(
        self,
        data: dict,
        constraints: list[dict],
        budget: ExplorationBudget | None = None,
    ) -> list[Counterexample]:
        """Mode 1: Find boundary violations.

        Args:
            data: LabExplorationView-compatible data.
            constraints: Constraint card dicts.
            budget: Resource budget (default used if None).

        Returns:
            List of Counterexample instances.
        """
        if budget is None:
            budget = ExplorationBudget()
        return await self._counterexample_finder.find(data, constraints, budget)

    # ── Mode 2: Constraint hypothesis ──────────────────────────────────

    async def run_constraint_hypothesis(
        self,
        data: dict,
        constraints: list[dict],
        budget: ExplorationBudget | None = None,
    ) -> list[Hypothesis]:
        """Mode 2: Generate constraint hypotheses.

        Args:
            data: LabExplorationView-compatible data.
            constraints: Constraint card dicts.
            budget: Resource budget (default used if None).

        Returns:
            List of Hypothesis instances.
        """
        if budget is None:
            budget = ExplorationBudget()
        return await self._hypothesis_generator.generate(data, constraints, budget)

    # ── Mode 3: Failure correlation ────────────────────────────────────

    async def run_failure_correlation(
        self,
        failure_logs: list[dict],
        budget: ExplorationBudget | None = None,
    ) -> list[CorrelationFinding]:
        """Mode 3: Correlate failure events.

        Args:
            failure_logs: Desensitized failure log records.
            budget: Resource budget (default used if None).

        Returns:
            List of CorrelationFinding instances.
        """
        if budget is None:
            budget = ExplorationBudget()
        return await self._failure_analyzer.analyze(failure_logs, budget)

    # ── Mode 4: Counterfactual generation ──────────────────────────────

    async def run_counterfactual_generation(
        self,
        base_state: dict,
        constraints: list[dict],
        budget: ExplorationBudget | None = None,
    ) -> list[CounterfactualScenario]:
        """Mode 4: Explore alternative states.

        Args:
            base_state: The reference state to modify.
            constraints: Constraint card dicts.
            budget: Resource budget (default used if None).

        Returns:
            List of CounterfactualScenario instances.
        """
        if budget is None:
            budget = ExplorationBudget()
        return await self._counterfactual_generator.generate(
            base_state, constraints, budget
        )

    # ── Full exploration run ───────────────────────────────────────────

    async def run_full_exploration(
        self,
        data: dict,
        constraints: list[dict],
        budget: ExplorationBudget | None = None,
    ) -> ExplorationResult:
        """Run all applicable exploration modes and aggregate results.

        Args:
            data: LabExplorationView-compatible data.
            constraints: Constraint card dicts.
            budget: Resource budget (default used if None).

        Returns:
            Aggregated ExplorationResult from all modes.
        """
        if budget is None:
            budget = ExplorationBudget()

        # Execute through sandbox
        result = await self._sandbox.execute(self._strategy, data, budget)

        # Run specialized modes
        counterexamples = await self.run_counterexample_search(data, constraints, budget)
        hypotheses = await self.run_constraint_hypothesis(data, constraints, budget)

        # Merge results
        result.counterexamples.extend(counterexamples)
        result.hypotheses.extend(hypotheses)

        return result
