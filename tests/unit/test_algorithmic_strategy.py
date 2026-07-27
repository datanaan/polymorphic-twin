"""Tests for AlgorithmicStrategy: grid-search exploration.

Key tests:
1. Returns ExplorationResult with correct structure
2. Finds counterexamples for constraints with max boundaries
3. Finds counterexamples for constraints with min boundaries
4. Safety-critical constraints get severity="high"
5. Respects budget limits
6. Strategy manifest is populated
"""

from polytwin.lab.strategies.algorithmic import AlgorithmicStrategy
from polytwin.lab.types import ExplorationBudget, ExplorationResult


def _constraint(
    constraint_id: str = "c1",
    variable: str = "temperature",
    max_val: float | None = 180.0,
    min_val: float | None = None,
    criticality: str = "operational",
) -> dict:
    """Build a minimal constraint card dict."""
    config: dict = {"variable": variable}
    if max_val is not None:
        config["max"] = max_val
    if min_val is not None:
        config["min"] = min_val
    return {
        "constraint_id": constraint_id,
        "scenario_criticality": criticality,
        "validation": {"method": "range_check", "config": config},
    }


class TestAlgorithmicStrategyBasics:
    def test_name(self):
        s = AlgorithmicStrategy()
        assert s.name() == "algorithmic_grid_search"

    def test_constraint_awareness(self):
        s = AlgorithmicStrategy()
        assert s.constraint_awareness() == "algorithmic"

    def test_data_requirements(self):
        s = AlgorithmicStrategy()
        assert "state_variables" in s.data_requirements()
        assert "constraint_cards" in s.data_requirements()


class TestAlgorithmicExploration:
    def test_empty_constraints_no_counterexamples(self):
        s = AlgorithmicStrategy()
        result = s.explore({}, [], ExplorationBudget())
        assert result.counterexamples == []

    def test_finds_max_boundary_violation(self):
        s = AlgorithmicStrategy()
        constraints = [_constraint("c1", "temperature", max_val=180.0)]
        result = s.explore({}, constraints, ExplorationBudget())
        assert len(result.counterexamples) >= 1
        ce = result.counterexamples[0]
        assert ce.constraint_violated == "c1"
        assert ce.state_at_failure["temperature"] == 180.01

    def test_finds_min_boundary_violation(self):
        s = AlgorithmicStrategy()
        constraints = [_constraint("c1", "temperature", min_val=-10.0, max_val=None)]
        result = s.explore({}, constraints, ExplorationBudget())
        assert len(result.counterexamples) >= 1
        ce = result.counterexamples[0]
        assert ce.state_at_failure["temperature"] == -10.01

    def test_finds_both_boundaries(self):
        s = AlgorithmicStrategy()
        constraints = [_constraint("c1", "temperature", max_val=180.0, min_val=-10.0)]
        result = s.explore({}, constraints, ExplorationBudget())
        assert len(result.counterexamples) == 2

    def test_safety_critical_gets_high_severity(self):
        s = AlgorithmicStrategy()
        constraints = [_constraint("c1", "temperature", max_val=180.0, criticality="safety_critical")]
        result = s.explore({}, constraints, ExplorationBudget())
        assert all(ce.severity == "high" for ce in result.counterexamples)

    def test_operational_gets_medium_severity(self):
        s = AlgorithmicStrategy()
        constraints = [_constraint("c1", "temperature", max_val=180.0, criticality="operational")]
        result = s.explore({}, constraints, ExplorationBudget())
        assert all(ce.severity == "medium" for ce in result.counterexamples)

    def test_returns_exploration_result(self):
        s = AlgorithmicStrategy()
        constraints = [_constraint("c1", max_val=100.0)]
        result = s.explore({}, constraints, ExplorationBudget())
        assert isinstance(result, ExplorationResult)

    def test_result_has_findings(self):
        s = AlgorithmicStrategy()
        constraints = [_constraint("c1", "temperature", max_val=100.0)]
        result = s.explore({}, constraints, ExplorationBudget())
        assert len(result.findings) > 0
        assert result.findings[0].type == "counterexample"

    def test_result_has_confidence_scores(self):
        s = AlgorithmicStrategy()
        constraints = [_constraint("c1", max_val=100.0)]
        result = s.explore({}, constraints, ExplorationBudget())
        assert "boundary_detection" in result.confidence_scores
        assert result.confidence_scores["boundary_detection"] == 1.0

    def test_multiple_constraints(self):
        s = AlgorithmicStrategy()
        constraints = [
            _constraint("c1", "temperature", max_val=180.0),
            _constraint("c2", "pressure", max_val=100.0),
        ]
        result = s.explore({}, constraints, ExplorationBudget())
        assert len(result.counterexamples) == 2


class TestAlgorithmicBudget:
    def test_respects_max_iterations(self):
        s = AlgorithmicStrategy()
        constraints = [_constraint(f"c{i}", max_val=float(i)) for i in range(100)]
        budget = ExplorationBudget(max_iterations=5)
        result = s.explore({}, constraints, budget)
        # At most 5 constraints processed
        assert len(result.counterexamples) <= 10  # 5 constraints * 2 boundaries max

    def test_no_variable_skipped(self):
        s = AlgorithmicStrategy()
        constraints = [
            {"constraint_id": "c-no-var", "validation": {"config": {}}},
        ]
        result = s.explore({}, constraints, ExplorationBudget())
        assert len(result.counterexamples) == 0


class TestAlgorithmicManifest:
    def test_manifest_structure(self):
        s = AlgorithmicStrategy()
        manifest = s.reproducibility_manifest()
        assert manifest["strategy"] == "algorithmic_grid_search"
        assert manifest["version"] == "0.1.0"
        assert manifest["deterministic"] is True
        assert "boundary_offset" in manifest

    def test_result_manifest_populated(self):
        s = AlgorithmicStrategy()
        constraints = [_constraint("c1", max_val=100.0)]
        result = s.explore({}, constraints, ExplorationBudget())
        assert result.strategy_manifest["strategy"] == "algorithmic_grid_search"
