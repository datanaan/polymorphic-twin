"""Tests for Sandbox: isolated execution environment.

Key tests:
1. Accepts dict data
2. Rejects non-dict data (enforcing LabExplorationView)
3. Strategy manifest is injected into result
4. Data access validation detects hidden references
"""
import pytest

from polytwin.lab.sandbox import Sandbox
from polytwin.lab.strategies.algorithmic import AlgorithmicStrategy
from polytwin.lab.types import ExplorationBudget


def _constraint(variable: str = "temperature", max_val: float = 180.0) -> dict:
    return {
        "constraint_id": f"c_{variable}",
        "scenario_criticality": "operational",
        "validation": {"method": "range_check", "config": {"variable": variable, "max": max_val}},
    }


class TestSandboxExecution:
    @pytest.mark.asyncio
    async def test_accepts_dict_data(self):
        sandbox = Sandbox()
        strategy = AlgorithmicStrategy()
        data = {"constraints": [_constraint()]}
        result = await sandbox.execute(strategy, data, ExplorationBudget())
        assert result.strategy_manifest != {}

    @pytest.mark.asyncio
    async def test_rejects_non_dict_data(self):
        sandbox = Sandbox()
        strategy = AlgorithmicStrategy()
        with pytest.raises(TypeError, match="dict data"):
            await sandbox.execute(strategy, "not a dict", ExplorationBudget())

    @pytest.mark.asyncio
    async def test_rejects_list_data(self):
        sandbox = Sandbox()
        strategy = AlgorithmicStrategy()
        with pytest.raises(TypeError, match="dict data"):
            await sandbox.execute(strategy, [1, 2, 3], ExplorationBudget())

    @pytest.mark.asyncio
    async def test_rejects_none_data(self):
        sandbox = Sandbox()
        strategy = AlgorithmicStrategy()
        with pytest.raises(TypeError, match="dict data"):
            await sandbox.execute(strategy, None, ExplorationBudget())

    @pytest.mark.asyncio
    async def test_manifest_injected(self):
        sandbox = Sandbox()
        strategy = AlgorithmicStrategy()
        data = {"constraints": [_constraint()]}
        result = await sandbox.execute(strategy, data, ExplorationBudget())
        assert result.strategy_manifest["strategy"] == "algorithmic_grid_search"

    @pytest.mark.asyncio
    async def test_empty_data_works(self):
        sandbox = Sandbox()
        strategy = AlgorithmicStrategy()
        result = await sandbox.execute(strategy, {}, ExplorationBudget())
        assert result.counterexamples == []

    @pytest.mark.asyncio
    async def test_constraints_extracted_from_data(self):
        sandbox = Sandbox()
        strategy = AlgorithmicStrategy()
        data = {"constraints": [_constraint("temperature", 180.0), _constraint("pressure", 100.0)]}
        result = await sandbox.execute(strategy, data, ExplorationBudget())
        assert len(result.counterexamples) == 2


class TestSandboxDataValidation:
    def test_clean_data_passes(self):
        sandbox = Sandbox()
        data = {"domain_pack_id": "dp-1", "records": []}
        assert sandbox.validate_data_access(data) is True

    def test_hidden_challenge_set_detected(self):
        sandbox = Sandbox()
        data = {"hidden_challenge_set": [1, 2, 3]}
        assert sandbox.validate_data_access(data) is False

    def test_audit_benchmark_detected(self):
        sandbox = Sandbox()
        data = {"audit_benchmark_reference": "secret"}
        assert sandbox.validate_data_access(data) is False

    def test_production_acceptance_detected(self):
        sandbox = Sandbox()
        data = {"production_acceptance_reference": "secret"}
        assert sandbox.validate_data_access(data) is False

    def test_hidden_validation_set_detected(self):
        sandbox = Sandbox()
        data = {"hidden_validation_set": "secret"}
        assert sandbox.validate_data_access(data) is False

    def test_nested_hidden_reference(self):
        sandbox = Sandbox()
        data = {"results": {"inner": "hidden_challenge_set data"}}
        assert sandbox.validate_data_access(data) is False
