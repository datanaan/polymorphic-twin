"""Tests for ExplorationStrategy ABC.

Verifies that the abstract base class cannot be instantiated directly
and that all abstract methods are properly defined.
"""
import pytest

from polytwin.lab.strategies.algorithmic import AlgorithmicStrategy
from polytwin.lab.strategies.base import ExplorationStrategy


class TestExplorationStrategyABC:
    def test_cannot_instantiate_abc(self):
        """ExplorationStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ExplorationStrategy()

    def test_algorithmic_is_subclass(self):
        """AlgorithmicStrategy is a proper subclass."""
        assert issubclass(AlgorithmicStrategy, ExplorationStrategy)

    def test_algorithmic_instantiates(self):
        """AlgorithmicStrategy can be instantiated."""
        strategy = AlgorithmicStrategy()
        assert isinstance(strategy, ExplorationStrategy)

    def test_required_methods_exist(self):
        """All required abstract methods exist on concrete implementation."""
        strategy = AlgorithmicStrategy()
        assert hasattr(strategy, "name")
        assert hasattr(strategy, "explore")
        assert hasattr(strategy, "reproducibility_manifest")
        assert hasattr(strategy, "constraint_awareness")
        assert hasattr(strategy, "data_requirements")
        assert hasattr(strategy, "exploration_space_mapping")
        assert hasattr(strategy, "health_indicators")

    def test_name_is_string(self):
        strategy = AlgorithmicStrategy()
        assert isinstance(strategy.name(), str)

    def test_constraint_awareness_is_string(self):
        strategy = AlgorithmicStrategy()
        awareness = strategy.constraint_awareness()
        assert awareness in ("algorithmic", "ml", "llm")

    def test_data_requirements_is_list(self):
        strategy = AlgorithmicStrategy()
        reqs = strategy.data_requirements()
        assert isinstance(reqs, list)
        assert all(isinstance(r, str) for r in reqs)

    def test_exploration_space_mapping_is_dict(self):
        strategy = AlgorithmicStrategy()
        mapping = strategy.exploration_space_mapping()
        assert isinstance(mapping, dict)

    def test_health_indicators_is_dict(self):
        strategy = AlgorithmicStrategy()
        health = strategy.health_indicators()
        assert isinstance(health, dict)
        assert "status" in health

    def test_reproducibility_manifest_is_dict(self):
        strategy = AlgorithmicStrategy()
        manifest = strategy.reproducibility_manifest()
        assert isinstance(manifest, dict)
        assert "strategy" in manifest
        assert "version" in manifest
