"""Tests for CounterfactualGenerator: alternative state exploration.

Key tests:
1. Generates scenarios from base state
2. Scenarios have divergence scores
3. Respects budget
4. Compute divergence utility works
"""
import pytest

from polytwin.lab.counterfactual import CounterfactualGenerator
from polytwin.lab.types import CounterfactualScenario, ExplorationBudget


def _constraint(
    constraint_id: str = "c1",
    variable: str = "temperature",
    max_val: float = 180.0,
    min_val: float | None = None,
) -> dict:
    config: dict = {"variable": variable, "max": max_val}
    if min_val is not None:
        config["min"] = min_val
    return {
        "constraint_id": constraint_id,
        "scenario_criticality": "operational",
        "validation": {"method": "range_check", "config": config},
    }


class TestCounterfactualGeneration:
    @pytest.mark.asyncio
    async def test_generates_scenarios(self):
        gen = CounterfactualGenerator()
        base = {"temperature": 100.0}
        result = await gen.generate(base, [_constraint()], ExplorationBudget())
        assert len(result) > 0
        assert all(isinstance(cs, CounterfactualScenario) for cs in result)

    @pytest.mark.asyncio
    async def test_scenario_modifies_base_state(self):
        gen = CounterfactualGenerator()
        base = {"temperature": 100.0}
        result = await gen.generate(base, [_constraint()], ExplorationBudget())
        assert any(cs.modified_state["temperature"] != base["temperature"] for cs in result)

    @pytest.mark.asyncio
    async def test_max_boundary_scenario(self):
        gen = CounterfactualGenerator()
        base = {"temperature": 100.0}
        result = await gen.generate(base, [_constraint(max_val=180.0)], ExplorationBudget())
        assert any(cs.modified_state["temperature"] == 180.0 for cs in result)

    @pytest.mark.asyncio
    async def test_min_boundary_scenario(self):
        gen = CounterfactualGenerator()
        base = {"temperature": 100.0}
        result = await gen.generate(
            base, [_constraint(max_val=180.0, min_val=-10.0)], ExplorationBudget()
        )
        modified_temps = [cs.modified_state["temperature"] for cs in result]
        assert 180.0 in modified_temps
        assert -10.0 in modified_temps

    @pytest.mark.asyncio
    async def test_empty_base_state(self):
        gen = CounterfactualGenerator()
        result = await gen.generate({}, [_constraint()], ExplorationBudget())
        assert result == []

    @pytest.mark.asyncio
    async def test_variable_not_in_base_state(self):
        gen = CounterfactualGenerator()
        base = {"pressure": 50.0}
        result = await gen.generate(base, [_constraint(variable="temperature")], ExplorationBudget())
        assert result == []

    @pytest.mark.asyncio
    async def test_has_divergence_score(self):
        gen = CounterfactualGenerator()
        base = {"temperature": 100.0}
        result = await gen.generate(base, [_constraint(max_val=180.0)], ExplorationBudget())
        assert all(cs.divergence_score >= 0 for cs in result)


class TestCounterfactualBudget:
    @pytest.mark.asyncio
    async def test_respects_iteration_limit(self):
        gen = CounterfactualGenerator()
        base = {f"var_{i}": float(i) for i in range(50)}
        constraints = [
            _constraint(f"c{i}", f"var_{i}", float(i + 100)) for i in range(50)
        ]
        budget = ExplorationBudget(max_iterations=5)
        result = await gen.generate(base, constraints, budget)
        assert len(result) <= 5

    @pytest.mark.asyncio
    async def test_no_budget_uses_default(self):
        gen = CounterfactualGenerator()
        base = {"temperature": 100.0}
        result = await gen.generate(base, [_constraint()], None)
        assert len(result) > 0


class TestDivergenceComputation:
    def test_identical_states_zero(self):
        state = {"temperature": 100.0, "pressure": 50.0}
        assert CounterfactualGenerator.compute_divergence(state, state) == 0.0

    def test_different_states_positive(self):
        base = {"temperature": 100.0}
        modified = {"temperature": 200.0}
        div = CounterfactualGenerator.compute_divergence(base, modified)
        assert div > 0

    def test_empty_states_zero(self):
        assert CounterfactualGenerator.compute_divergence({}, {}) == 0.0
