"""Tests for CounterexampleFinder.

Key tests:
1. Finds counterexamples from strategy
2. Classifies severity correctly
3. Returns full context with find_with_context
"""
import pytest

from polytwin.lab.counterexample import CounterexampleFinder
from polytwin.lab.strategies.algorithmic import AlgorithmicStrategy
from polytwin.lab.types import Counterexample, ExplorationBudget


def _constraint(
    constraint_id: str = "c1",
    variable: str = "temperature",
    max_val: float = 180.0,
    criticality: str = "operational",
) -> dict:
    return {
        "constraint_id": constraint_id,
        "scenario_criticality": criticality,
        "validation": {"method": "range_check", "config": {"variable": variable, "max": max_val}},
    }


class TestCounterexampleFinder:
    @pytest.mark.asyncio
    async def test_finds_counterexamples(self):
        finder = CounterexampleFinder(AlgorithmicStrategy())
        result = await finder.find({}, [_constraint()], ExplorationBudget())
        assert len(result) > 0
        assert all(isinstance(ce, Counterexample) for ce in result)

    @pytest.mark.asyncio
    async def test_empty_constraints(self):
        finder = CounterexampleFinder(AlgorithmicStrategy())
        result = await finder.find({}, [], ExplorationBudget())
        assert result == []

    @pytest.mark.asyncio
    async def test_context_result(self):
        finder = CounterexampleFinder(AlgorithmicStrategy())
        result = await finder.find_with_context({}, [_constraint()], ExplorationBudget())
        assert len(result.counterexamples) > 0
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_multiple_constraints(self):
        finder = CounterexampleFinder(AlgorithmicStrategy())
        constraints = [
            _constraint("c1", "temperature", 180.0),
            _constraint("c2", "pressure", 100.0),
        ]
        result = await finder.find({}, constraints, ExplorationBudget())
        assert len(result) == 2


class TestSeverityClassification:
    def test_safety_critical_high(self):
        ce = Counterexample(
            constraint_violated="c1",
            severity="medium",
        )
        constraints = [_constraint("c1", criticality="safety_critical")]
        severity = CounterexampleFinder.classify_severity(ce, constraints)
        assert severity == "high"

    def test_operational_keeps_medium(self):
        ce = Counterexample(
            constraint_violated="c1",
            severity="medium",
        )
        constraints = [_constraint("c1", criticality="operational")]
        severity = CounterexampleFinder.classify_severity(ce, constraints)
        assert severity == "medium"

    def test_unknown_constraint_keeps_original(self):
        ce = Counterexample(
            constraint_violated="c-unknown",
            severity="low",
        )
        severity = CounterexampleFinder.classify_severity(ce, [_constraint("c1")])
        assert severity == "low"
