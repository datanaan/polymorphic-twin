"""Tests for HypothesisGenerator.

Key tests:
1. Generates hypotheses from exploration data
2. Creates constraint hypotheses from variable boundaries
3. Hypotheses have falsification tests
"""
import pytest

from polytwin.lab.hypothesis import HypothesisGenerator
from polytwin.lab.strategies.algorithmic import AlgorithmicStrategy
from polytwin.lab.types import ExplorationBudget, Hypothesis


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


class TestHypothesisGeneration:
    @pytest.mark.asyncio
    async def test_generates_hypotheses_from_findings(self):
        gen = HypothesisGenerator(AlgorithmicStrategy())
        result = await gen.generate({}, [_constraint()], ExplorationBudget())
        assert len(result) > 0
        assert all(isinstance(h, Hypothesis) for h in result)

    @pytest.mark.asyncio
    async def test_hypotheses_have_statements(self):
        gen = HypothesisGenerator(AlgorithmicStrategy())
        result = await gen.generate({}, [_constraint()], ExplorationBudget())
        assert all(len(h.statement) > 0 for h in result)

    @pytest.mark.asyncio
    async def test_hypotheses_have_falsification_tests(self):
        gen = HypothesisGenerator(AlgorithmicStrategy())
        result = await gen.generate({}, [_constraint()], ExplorationBudget())
        assert all(len(h.falsification_tests) > 0 for h in result)

    @pytest.mark.asyncio
    async def test_empty_constraints(self):
        gen = HypothesisGenerator(AlgorithmicStrategy())
        result = await gen.generate({}, [], ExplorationBudget())
        assert result == []

    @pytest.mark.asyncio
    async def test_confidence_scores(self):
        gen = HypothesisGenerator(AlgorithmicStrategy())
        result = await gen.generate({}, [_constraint()], ExplorationBudget())
        assert all(h.confidence >= 0 for h in result)


class TestCreateConstraintHypothesis:
    def test_creates_hypothesis(self):
        h = HypothesisGenerator.create_constraint_hypothesis(
            variable="temperature",
            observed_boundary=180.0,
            constraint_id="c1",
        )
        assert isinstance(h, Hypothesis)
        assert h.hypothesis_id != ""
        assert "temperature" in h.statement
        assert "180.0" in h.statement
        assert len(h.falsification_tests) == 2

    def test_falsification_test_structure(self):
        h = HypothesisGenerator.create_constraint_hypothesis(
            variable="pressure",
            observed_boundary=100.0,
            constraint_id="c2",
        )
        for test in h.falsification_tests:
            assert "type" in test
            assert "variable" in test
            assert test["variable"] == "pressure"

    def test_default_confidence(self):
        h = HypothesisGenerator.create_constraint_hypothesis(
            "temp", 180.0, "c1"
        )
        assert h.confidence == 0.8
