"""Tests for LabExplorer: four exploration mode orchestrator.

Key tests:
1. Mode 1: Counterexample search produces results
2. Mode 2: Constraint hypothesis generates hypotheses
3. Mode 3: Failure correlation discovers correlations
4. Mode 4: Counterfactual generation produces scenarios
5. Full exploration aggregates results
"""
import pytest

from polytwin.lab.explorer import LabExplorer
from polytwin.lab.strategies.algorithmic import AlgorithmicStrategy
from polytwin.lab.types import (
    CorrelationFinding,
    Counterexample,
    CounterfactualScenario,
    ExplorationBudget,
    ExplorationResult,
    Hypothesis,
)


def _constraint(
    constraint_id: str = "c1",
    variable: str = "temperature",
    max_val: float = 180.0,
) -> dict:
    return {
        "constraint_id": constraint_id,
        "scenario_criticality": "operational",
        "validation": {"method": "range_check", "config": {"variable": variable, "max": max_val}},
    }


class TestLabExplorerMode1Counterexample:
    @pytest.mark.asyncio
    async def test_finds_counterexamples(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        result = await explorer.run_counterexample_search(
            {}, [_constraint()], ExplorationBudget()
        )
        assert len(result) > 0
        assert all(isinstance(ce, Counterexample) for ce in result)

    @pytest.mark.asyncio
    async def test_empty_constraints_no_results(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        result = await explorer.run_counterexample_search({}, [], ExplorationBudget())
        assert result == []

    @pytest.mark.asyncio
    async def test_default_budget(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        result = await explorer.run_counterexample_search({}, [_constraint()])
        assert isinstance(result, list)


class TestLabExplorerMode2Hypothesis:
    @pytest.mark.asyncio
    async def test_generates_hypotheses(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        result = await explorer.run_constraint_hypothesis(
            {}, [_constraint()], ExplorationBudget()
        )
        assert len(result) > 0
        assert all(isinstance(h, Hypothesis) for h in result)

    @pytest.mark.asyncio
    async def test_hypothesis_has_falsification_test(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        result = await explorer.run_constraint_hypothesis(
            {}, [_constraint()], ExplorationBudget()
        )
        for h in result:
            assert len(h.falsification_tests) > 0

    @pytest.mark.asyncio
    async def test_hypothesis_has_statement(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        result = await explorer.run_constraint_hypothesis(
            {}, [_constraint()], ExplorationBudget()
        )
        assert all(len(h.statement) > 0 for h in result)


class TestLabExplorerMode3FailureCorrelation:
    @pytest.mark.asyncio
    async def test_empty_logs_no_results(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        result = await explorer.run_failure_correlation([])
        assert result == []

    @pytest.mark.asyncio
    async def test_single_event_no_correlation(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        logs = [{"variables": {"temperature": 100}}]
        result = await explorer.run_failure_correlation(logs)
        assert result == []

    @pytest.mark.asyncio
    async def test_correlated_events_found(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        logs = [
            {"variables": {"temperature": 100, "pressure": 50}},
            {"variables": {"temperature": 105, "pressure": 52}},
        ]
        result = await explorer.run_failure_correlation(logs)
        assert len(result) > 0
        assert all(isinstance(cf, CorrelationFinding) for cf in result)

    @pytest.mark.asyncio
    async def test_correlation_strength(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        logs = [
            {"variables": {"temperature": 100}},
            {"variables": {"temperature": 105}},
        ]
        result = await explorer.run_failure_correlation(logs)
        assert all(cf.correlation_strength > 0 for cf in result)


class TestLabExplorerMode4Counterfactual:
    @pytest.mark.asyncio
    async def test_generates_scenarios(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        base_state = {"temperature": 100.0}
        constraints = [_constraint(variable="temperature", max_val=180.0)]
        result = await explorer.run_counterfactual_generation(
            base_state, constraints, ExplorationBudget()
        )
        assert len(result) > 0
        assert all(isinstance(cs, CounterfactualScenario) for cs in result)

    @pytest.mark.asyncio
    async def test_scenario_has_divergence(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        base_state = {"temperature": 100.0}
        constraints = [_constraint(variable="temperature", max_val=180.0)]
        result = await explorer.run_counterfactual_generation(
            base_state, constraints, ExplorationBudget()
        )
        assert all(cs.divergence_score >= 0 for cs in result)

    @pytest.mark.asyncio
    async def test_empty_base_state(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        result = await explorer.run_counterfactual_generation(
            {}, [_constraint()], ExplorationBudget()
        )
        assert result == []


class TestLabExplorerFullExploration:
    @pytest.mark.asyncio
    async def test_full_exploration_returns_result(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        data = {"constraints": [_constraint()]}
        result = await explorer.run_full_exploration(
            data, [_constraint()], ExplorationBudget()
        )
        assert isinstance(result, ExplorationResult)

    @pytest.mark.asyncio
    async def test_full_exploration_has_findings(self):
        explorer = LabExplorer(AlgorithmicStrategy())
        data = {"constraints": [_constraint()]}
        result = await explorer.run_full_exploration(
            data, [_constraint()], ExplorationBudget()
        )
        assert len(result.counterexamples) > 0 or len(result.hypotheses) > 0
